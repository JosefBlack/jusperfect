"""Die Chronologie steht dauerhaft und wird fortgeschrieben.

Ein Mandat läuft über Wochen: Ein Schriftsatz geht hinaus, drei Wochen später
kommt die Antwort. Ohne dauerhafte Chronologie entstünde der Zeitstrahl bei
jedem Durchgang neu – ein voller Modellaufruf über die ganze Akte für zwei neue
Zeilen –, und zwischendurch wäre er ohnehin weg: Eine Sitzung lebt fünfzehn
Minuten.
"""

from __future__ import annotations

import json
import tempfile
import unittest

from jusperfect.providers.base import Nutzung, ProviderAntwort
from jusperfect.services.gedaechtnis import _gleicher_vorgang
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


def _analyse(chronologie) -> str:
    return json.dumps({
        "chronologie": chronologie, "beteiligte": [], "forderungen": [], "beweismittel": [],
        "offene_punkte": [], "widersprueche": [], "hinweise": [],
    })


UNFALL = {"datum": "2026-03-13", "ereignis": "Unfall auf der Kreuzung", "quellen": ["D1-S1-P1"]}


class Fortschreiben(unittest.TestCase):
    """Der zweite Durchgang ergänzt, er ersetzt nicht."""

    def test_spaetere_analyse_ergaenzt_statt_zu_ersetzen(self):
        with tempfile.TemporaryDirectory() as tmp:
            e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp)
            spaeter = {"datum": "2026-04-08", "ereignis": "Antwort der Versicherung",
                       "quellen": ["D1-S1-P1"]}
            p = SkriptProvider([_analyse([UNFALL]), _analyse([spaeter])])
            c = client(dienste(einstellungen=e, provider=p))
            sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
            c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})

            erste = c.post(f"/api/sitzungen/{sid}/analyse").json()
            self.assertEqual([x["ereignis"] for x in erste["chronologie"]], ["Unfall auf der Kreuzung"])

            # Drei Wochen später, zweiter Durchgang: Das Modell nennt nur das
            # neue Ereignis. Der Zeitstrahl muss trotzdem beide tragen.
            zweite = c.post(f"/api/sitzungen/{sid}/analyse").json()
            self.assertEqual([x["ereignis"] for x in zweite["chronologie"]],
                             ["Unfall auf der Kreuzung", "Antwort der Versicherung"])

    def test_dieselbe_analyse_zweimal_erzeugt_keine_doppelung(self):
        with tempfile.TemporaryDirectory() as tmp:
            e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp)
            p = SkriptProvider([_analyse([UNFALL]), _analyse([UNFALL])])
            c = client(dienste(einstellungen=e, provider=p))
            sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
            c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
            c.post(f"/api/sitzungen/{sid}/analyse")
            zweite = c.post(f"/api/sitzungen/{sid}/analyse").json()
            self.assertEqual(len(zweite["chronologie"]), 1)

    def test_andere_formulierung_desselben_vorgangs_zaehlt_nicht_doppelt(self):
        """Ein Modell schreibt denselben Vorgang beim zweiten Mal anders auf."""
        with tempfile.TemporaryDirectory() as tmp:
            e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp)
            anders = {"datum": "2026-03-13", "ereignis": "Kreuzung: Unfall ereignet",
                      "quellen": ["D1-S1-P1"]}
            p = SkriptProvider([_analyse([UNFALL]), _analyse([anders])])
            c = client(dienste(einstellungen=e, provider=p))
            sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
            c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
            c.post(f"/api/sitzungen/{sid}/analyse")
            zweite = c.post(f"/api/sitzungen/{sid}/analyse").json()
            self.assertEqual(len(zweite["chronologie"]), 1)

    def test_gleiches_ereignis_an_anderem_datum_bleibt_eigener_eintrag(self):
        """Zwei Mahnungen sind zwei Vorgänge, auch wortgleich."""
        with tempfile.TemporaryDirectory() as tmp:
            e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp)
            zweite_mahnung = dict(UNFALL, datum="2026-05-02")
            p = SkriptProvider([_analyse([UNFALL]), _analyse([zweite_mahnung])])
            c = client(dienste(einstellungen=e, provider=p))
            sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
            c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
            c.post(f"/api/sitzungen/{sid}/analyse")
            self.assertEqual(len(c.post(f"/api/sitzungen/{sid}/analyse").json()["chronologie"]), 2)

    def test_chronologie_bleibt_nach_datum_sortiert(self):
        with tempfile.TemporaryDirectory() as tmp:
            e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp)
            frueher = {"datum": "2026-01-05", "ereignis": "Mandat erteilt", "quellen": ["D1-S1-P1"]}
            p = SkriptProvider([_analyse([UNFALL]), _analyse([frueher])])
            c = client(dienste(einstellungen=e, provider=p))
            sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
            c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
            c.post(f"/api/sitzungen/{sid}/analyse")
            daten = c.post(f"/api/sitzungen/{sid}/analyse").json()["chronologie"]
            # Das nachgetragene, ältere Ereignis steht vorn – nicht hinten.
            self.assertEqual([x["datum"] for x in daten], ["2026-01-05", "2026-03-13"])


class UeberDieSitzungHinaus(unittest.TestCase):
    def test_zeitstrahl_steht_nach_wochen_ohne_neuen_modellaufruf(self):
        """Der eigentliche Zweck: Wiederaufnahme kostet nichts."""
        with tempfile.TemporaryDirectory() as tmp:
            e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp)
            p = SkriptProvider([_analyse([UNFALL])])
            c1 = client(dienste(einstellungen=e, provider=p))
            sid = c1.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
            c1.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
            c1.post(f"/api/sitzungen/{sid}/analyse")
            c1.delete(f"/api/sitzungen/{sid}")

            # Neuer Prozess, neuer Sitzungsspeicher, kein Provider-Aufruf mehr.
            leer = SkriptProvider([])
            neu = client(dienste(einstellungen=e, provider=leer))
            daten = neu.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()
            self.assertEqual([x["ereignis"] for x in daten["gedaechtnis"]["chronologie"]],
                             ["Unfall auf der Kreuzung"])
            self.assertEqual(leer.aufrufe, [], "Der Zeitstrahl darf nichts kosten.")

    def test_ohne_gedaechtnis_bleibt_die_analyse_unveraendert(self):
        """Ausgeschaltetes Gedächtnis darf die Analyse nicht beschädigen."""
        p = SkriptProvider([_analyse([UNFALL]), _analyse([])])
        c = client(dienste(provider=p))
        sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
        self.assertEqual(len(c.post(f"/api/sitzungen/{sid}/analyse").json()["chronologie"]), 1)
        # Nichts wird aufbewahrt: Der zweite Durchgang liefert, was das Modell sagt.
        self.assertEqual(c.post(f"/api/sitzungen/{sid}/analyse").json()["chronologie"], [])


class Belegpflicht(unittest.TestCase):
    def test_unbelegtes_ereignis_gelangt_nicht_in_die_dauerhafte_chronologie(self):
        with tempfile.TemporaryDirectory() as tmp:
            e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp)
            erfunden = {"datum": "2026-04-08", "ereignis": "Frei erfunden", "quellen": ["D9-S1-P1"]}
            p = SkriptProvider([_analyse([UNFALL, erfunden])])
            d = dienste(einstellungen=e, provider=p)
            c = client(d)
            sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
            c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
            c.post(f"/api/sitzungen/{sid}/analyse")
            g = d.gedaechtnis.lesen("VU-2026-0042")
            self.assertEqual([x.ereignis for x in g.chronologie], ["Unfall auf der Kreuzung"])

    def test_vergessenes_dokument_nimmt_die_chronologie_mit(self):
        """Ein Ereignis, das nur dieses Dokument belegt, bleibt nicht stehen.

        Früher fiel hier der ganze Zeitstrahl, weil die Kennungen durchzählten
        und sich nach einem Wegfall alle verschoben. Seit jeder Auszug eine
        feste Nummer trägt, fällt nur noch, was dieses Dokument zitiert – hier
        ist das der einzige Eintrag.
        """
        with tempfile.TemporaryDirectory() as tmp:
            e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp)
            p = SkriptProvider([_analyse([UNFALL])])
            d = dienste(einstellungen=e, provider=p)
            c = client(d)
            sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
            c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
            c.post(f"/api/sitzungen/{sid}/analyse")
            self.assertTrue(d.gedaechtnis.lesen("VU-2026-0042").chronologie)

            d.gedaechtnis.dokument_vergessen("VU-2026-0042", "D-001")
            self.assertEqual(d.gedaechtnis.lesen("VU-2026-0042").chronologie, [],
                             "Ein Zeitstrahl mit falschen Fundstellen ist schlimmer als keiner.")


class GleicherVorgang(unittest.TestCase):
    def test_erkennt_umstellung_und_fuellwoerter(self):
        self.assertTrue(_gleicher_vorgang("Unfall auf der Kreuzung",
                                          "Kreuzung: Unfall ereignet"))

    def test_erkennt_deutsche_beugung(self):
        """Ohne Stammkürzung wären „Betriebsrat" und „Betriebsrats" zwei Wörter."""
        self.assertTrue(_gleicher_vorgang("Anhoerung des Betriebsrats",
                                          "Anhoerung der Betriebsraete"))
        self.assertTrue(_gleicher_vorgang("Kuendigung zugestellt",
                                          "Kuendigungen zugestellt"))

    def test_verschiedene_ereignisse_bleiben_verschieden(self):
        self.assertFalse(_gleicher_vorgang("Kuendigung ist zugegangen",
                                           "Betriebsrat wurde angehoert"))

    def test_umschreibung_mit_anderem_wortstamm_wird_nicht_erkannt(self):
        """Die bekannte Grenze – ausdrücklich festgehalten, nicht verschwiegen.

        „zugegangen" und „Zugang" teilen keinen Stamm der ersten fünf Zeichen.
        Der Eintrag steht dann doppelt im Speicher. Das ist die gewollte
        Richtung: lieber eine Doppelung als ein verlorenes Ereignis – und in der
        Anzeige fallen beide unter dasselbe Datum zusammen.
        """
        self.assertFalse(_gleicher_vorgang("Kuendigung ist zugegangen",
                                           "Zugang der Kuendigung"))

    def test_kurze_woerter_allein_werden_woertlich_verglichen(self):
        """Ohne Wörter ab vier Zeichen bliebe nur der Wortlaut."""
        self.assertTrue(_gleicher_vorgang("A B C", "A B C"))
        self.assertFalse(_gleicher_vorgang("A B C", "D E F"))


if __name__ == "__main__":
    unittest.main()
