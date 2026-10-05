"""Was liegt im Aktengedächtnis, wie groß ist es, und was fehlt noch?

Ein dauerhafter Speicher, in den niemand hineinsehen kann, ist eine Zusage ohne
Nachweis. Die Übersicht ist dieser Nachweis – und die Grundlage dafür, dass in
der Kanzlei jemand entscheiden kann, was aufgenommen wird und was nicht.
"""

from __future__ import annotations

import json
import tempfile
import unittest

from jusperfect.providers.base import Nutzung, ProviderAntwort
from tests.hilfen import client, dienste, einstellungen


class SkriptProvider:
    modell_id = "skript"

    def __init__(self, antworten):
        self.antworten = list(antworten)
        self.aufrufe = []

    def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        self.aufrufe.append({"material": material, "aufgabe": aufgabe, "modell": modell_id})
        return ProviderAntwort(text=self.antworten.pop(0), nutzung=Nutzung(1000, 200),
                               modell=modell_id or self.modell_id)


def _chronologie(eintraege, hinweise=()) -> str:
    return json.dumps({"chronologie": eintraege, "hinweise": list(hinweise)})


UNFALL = {"datum": "2026-03-13", "ereignis": "Unfall auf der Kreuzung", "quellen": ["D1-S1-P1"]}


class Umfang(unittest.TestCase):
    def _mit_gedaechtnis(self, provider=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp.name)
        d = dienste(einstellungen=e, provider=provider or SkriptProvider([]))
        return d, client(d)

    def test_uebersicht_nennt_zeichen_und_jedes_dokument_einzeln(self):
        d, c = self._mit_gedaechtnis()
        sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        antwort = c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]}).json()
        g = antwort["gedaechtnis"]
        self.assertTrue(g["vorhanden"])
        self.assertEqual(len(g["eintraege"]), 1)
        eintrag = g["eintraege"][0]
        self.assertEqual(eintrag["dokument_id"], "D-001")
        self.assertGreater(eintrag["zeichen"], 0)
        self.assertGreaterEqual(eintrag["seiten"], 1)
        # Der Gesamtumfang ist die Summe – nicht eine zweite, abweichende Zahl.
        self.assertEqual(g["zeichen"], sum(x["zeichen"] for x in g["eintraege"]))

    def test_leeres_gedaechtnis_meldet_null_statt_zu_fehlen(self):
        """Die Oberfläche rechnet mit den Feldern; sie dürfen nicht fehlen."""
        d, c = self._mit_gedaechtnis()
        r = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()
        self.assertEqual(r["gedaechtnis"]["zeichen"], 0)
        self.assertEqual(r["gedaechtnis"]["eintraege"], [])

    def test_dokumentliste_der_akte_erlaubt_den_vergleich_mit_dem_gedaechtnis(self):
        """Was fehlt, ergibt sich aus beiden Listen – die Antwort trägt beide."""
        d, c = self._mit_gedaechtnis()
        sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        antwort = c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]}).json()
        in_akte = {x["id"] for x in antwort["dokumente"]}
        im_gedaechtnis = {x["dokument_id"] for x in antwort["gedaechtnis"]["eintraege"]}
        self.assertIn("D-001", im_gedaechtnis)
        self.assertTrue(in_akte - im_gedaechtnis, "Die Testakte hat mehr Dokumente als geladen wurden.")


class ChronologieBefehl(unittest.TestCase):
    def _aufbau(self, antworten):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp.name,
                          JUSPERFECT_MODELL_ID="gross", JUSPERFECT_MODELL_ID_KLEIN="klein")
        p = SkriptProvider(antworten)
        d = dienste(einstellungen=e, provider=p)
        c = client(d)
        sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
        return p, d, c, sid

    def test_nutzt_das_kleine_modell_und_nur_die_chronologieaufgabe(self):
        p, d, c, sid = self._aufbau([_chronologie([UNFALL])])
        r = c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([x["ereignis"] for x in r.json()["chronologie"]], ["Unfall auf der Kreuzung"])
        self.assertEqual(p.aufrufe[0]["modell"], "klein")
        self.assertIn("AUFGABE: CHRONOLOGIE", p.aufrufe[0]["aufgabe"])

    def test_zweiter_knopfdruck_ohne_neues_dokument_kostet_nichts(self):
        """Der eigentliche Zweck des Befehls: nur Neues durchsehen."""
        p, d, c, sid = self._aufbau([_chronologie([UNFALL])])
        c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren")
        zweite = c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren").json()
        self.assertEqual(len(p.aufrufe), 1, "Ohne neue Passage darf kein Modellaufruf erfolgen.")
        self.assertEqual(zweite["neue_passagen"], 0)
        # Der Zeitstrahl kommt trotzdem vollständig zurück.
        self.assertEqual([x["ereignis"] for x in zweite["chronologie"]], ["Unfall auf der Kreuzung"])

    def test_neues_dokument_loest_genau_einen_weiteren_lauf_aus(self):
        # Das zweite Dokument ist D2 – die Kennungen zählen die Akte durch, nicht
        # die mitgeschickte Auswahl. Siehe den Test darunter.
        p, d, c, sid = self._aufbau([_chronologie([UNFALL]),
                                     _chronologie([{"datum": "2026-04-08",
                                                    "ereignis": "Antwort der Versicherung",
                                                    "quellen": ["D2-S1-P1"]}])])
        c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren")
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-004"]})
        dritte = c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren").json()
        self.assertEqual(len(p.aufrufe), 2)
        self.assertEqual(dritte["neue_passagen"], len(p.aufrufe[1]["material"].split("### Passage")) - 1)
        self.assertEqual([x["ereignis"] for x in dritte["chronologie"]],
                         ["Unfall auf der Kreuzung", "Antwort der Versicherung"])

    def test_nur_die_neuen_passagen_gehen_mit_und_behalten_ihre_kennung(self):
        """Der Kern der Ersparnis – und die Falle darin.

        Beim zweiten Lauf geht nur das neue Dokument hinaus. Seine Kennungen
        bleiben aber die der ganzen Akte (D2-…), nicht die der Auswahl (D1-…).
        Würden sie umnummeriert, zeigten alle gespeicherten Belege ins Leere.
        """
        p, d, c, sid = self._aufbau([_chronologie([UNFALL]), _chronologie([])])
        c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren")
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-004"]})
        c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren")
        zweites_material = p.aufrufe[1]["material"]
        self.assertIn("### Passage D2-S1-P1", zweites_material)
        self.assertNotIn("### Passage D1-", zweites_material,
                         "Das bereits gesehene Dokument darf nicht noch einmal bezahlt werden.")

    def test_bekannte_ereignisse_stehen_im_auftrag(self):
        """Das Modell soll nicht beisteuern, was schon vermerkt ist."""
        p, d, c, sid = self._aufbau([_chronologie([UNFALL]), _chronologie([])])
        c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren")
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-004"]})
        c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren")
        self.assertIn("BEREITS VERMERKT", p.aufrufe[1]["aufgabe"])
        self.assertIn("Unfall auf der Kreuzung", p.aufrufe[1]["aufgabe"])

    def test_lauf_ohne_fund_gilt_trotzdem_als_erledigt(self):
        """Ein Schreiben ohne datierbares Ereignis darf nicht ewig neu kosten."""
        p, d, c, sid = self._aufbau([_chronologie([])])
        c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren")
        zweite = c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren").json()
        self.assertEqual(len(p.aufrufe), 1)
        self.assertEqual(zweite["neue_passagen"], 0)

    def test_unbelegtes_ereignis_faellt_auch_hier_heraus(self):
        p, d, c, sid = self._aufbau([_chronologie([
            UNFALL, {"datum": "2026-04-08", "ereignis": "Erfunden", "quellen": ["D9-S1-P1"]}])])
        r = c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren").json()
        self.assertEqual([x["ereignis"] for x in r["chronologie"]], ["Unfall auf der Kreuzung"])
        self.assertTrue(any("Beleg" in h for h in r["hinweise"]))

    def test_vergessenes_dokument_setzt_auch_die_marke_zurueck(self):
        """Sonst gälte eine Passage als gesehen, die es nicht mehr gibt."""
        p, d, c, sid = self._aufbau([_chronologie([UNFALL])])
        c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren")
        self.assertTrue(d.gedaechtnis.lesen("VU-2026-0042").chronologie_passagen)
        d.gedaechtnis.dokument_vergessen("VU-2026-0042", "D-001")
        self.assertEqual(d.gedaechtnis.lesen("VU-2026-0042").chronologie_passagen, [])


class Probelauf(unittest.TestCase):
    """Der Weg, auf dem die Kanzlei das Programm kennenlernt, muss laufen."""

    def test_chronologie_aktualisieren_funktioniert_ohne_ki(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp.name)
        c = client(dienste(einstellungen=e))          # Demo-Anbieter, kein Modell
        sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
        r = c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["chronologie"], "Der Probelauf soll einen Zeitstrahl liefern.")


if __name__ == "__main__":
    unittest.main()
