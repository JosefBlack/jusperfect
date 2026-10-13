"""Das ganze Aktengedächtnis einer Akte verwerfen – und warum es den Weg braucht.

Aus der Kanzlei am 13.10.2026: Eine Akte habe bereits eine Arbeitsakte mit
falschen Unterlagen, ob man die löschen könne.

Einzeln ging das seit dem 05.10.2026, ganz nicht: Der Löschweg bestand in der
Schnittstelle (`DELETE /api/akten/{akte}/gedaechtnis`) und hatte keinen Knopf.
Eine Funktion ohne Weg dorthin ist keine.

Und „Sitzung schließen" hilft nicht, auch wenn es so aussieht – das hält die
erste Prüfung hier fest: Beim nächsten Öffnen legt `bei_eroeffnen` jedes
Dokument des Gedächtnisses wieder in die Arbeitsakte. Was falsch im Gedächtnis
steht, kommt zurück.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.hilfen import client, dienste, einstellungen

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"


def _aufbau(tmp: str):
    e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp)
    d = dienste(einstellungen=e)
    c = client(d)
    sid = c.post("/api/sitzungen", json={"akte_id": "MV-2026-0007"}).json()["sitzung"]["id"]
    c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-101"]})
    return d, c, sid


class SitzungSchliessenGenuegtNicht(unittest.TestCase):
    def test_nach_dem_schliessen_liegt_das_dokument_wieder_in_der_arbeitsakte(self):
        """Der Grund für den Knopf: Schließen nimmt nichts aus dem Gedächtnis."""
        with tempfile.TemporaryDirectory() as tmp:
            d, c, sid = _aufbau(tmp)
            self.assertEqual(
                [g["dokument_id"] for g in c.get(f"/api/sitzungen/{sid}").json()["sitzung"]["geladen"]],
                ["D-101"])

            c.delete(f"/api/sitzungen/{sid}")
            neu = c.post("/api/sitzungen", json={"akte_id": "MV-2026-0007"}).json()
            self.assertEqual([g["dokument_id"] for g in neu["sitzung"]["geladen"]], ["D-101"],
                             "Schließen hat das Dokument nicht aus dem Gedächtnis genommen.")


class VerwerfenWirktDauerhaft(unittest.TestCase):
    def test_nach_dem_verwerfen_ist_die_neue_sitzung_leer(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, c, sid = _aufbau(tmp)

            self.assertEqual(c.delete("/api/akten/MV-2026-0007/gedaechtnis").status_code, 204)
            self.assertIsNone(d.gedaechtnis.lesen("MV-2026-0007"))

            c.delete(f"/api/sitzungen/{sid}")
            neu = c.post("/api/sitzungen", json={"akte_id": "MV-2026-0007"}).json()
            self.assertEqual(neu["sitzung"]["geladen"], [])
            self.assertFalse(neu["gedaechtnis"]["vorhanden"])

    def test_die_offene_sitzung_traegt_es_noch_und_gibt_es_einzeln_her(self):
        """Deshalb räumt die Oberfläche nach dem Verwerfen die Arbeitsakte auf.

        Das Verwerfen betrifft das Gedächtnis. Die schon offene Sitzung hat das
        Dokument beim Öffnen hineingelegt bekommen und behält es – ein Fenster,
        das zeigt, was es nicht mehr hat. Der Weg hinaus ist derselbe wie im
        Explorer: ein DELETE je Dokument.
        """
        with tempfile.TemporaryDirectory() as tmp:
            d, c, sid = _aufbau(tmp)
            c.delete("/api/akten/MV-2026-0007/gedaechtnis")

            offen = c.get(f"/api/sitzungen/{sid}").json()
            self.assertEqual([g["dokument_id"] for g in offen["sitzung"]["geladen"]], ["D-101"])

            danach = c.delete(f"/api/sitzungen/{sid}/dokumente/D-101").json()
            self.assertEqual(danach["sitzung"]["geladen"], [])

    def test_die_akte_in_jurnodes_bleibt_unberuehrt(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, c, sid = _aufbau(tmp)
            vorher = len(c.get(f"/api/sitzungen/{sid}").json()["dokumente"])
            c.delete("/api/akten/MV-2026-0007/gedaechtnis")
            nachher = c.get(f"/api/sitzungen/{sid}").json()["dokumente"]
            self.assertEqual(len(nachher), vorher)
            self.assertTrue(any(x["id"] == "D-101" for x in nachher))


class DerKnopfIstDa(unittest.TestCase):
    """Eine Funktion ohne Weg dorthin ist keine – das war hier der Befund."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (STATISCH / "index.html").read_text(encoding="utf-8")
        cls.js = (STATISCH / "app.js").read_text(encoding="utf-8")

    def test_er_steht_im_gedaechtnisfenster_neben_der_auswahl(self):
        kopf = self.html[self.html.index('id="ged-oeffnen"'):]
        kopf = kopf[:kopf.index("</span></div>")]
        self.assertIn('id="ged-ganz-loeschen"', kopf)
        self.assertIn("Gedächtnis verwerfen", kopf)

    def test_er_sieht_nicht_aus_wie_ein_knopf_der_etwas_holt(self):
        zeile = [z for z in self.html.splitlines() if 'id="ged-ganz-loeschen"' in z][0]
        self.assertIn("gefahr", zeile)
        css = (STATISCH / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".mini.gefahr", css)

    def test_er_haengt_an_der_funktion_und_die_funktion_am_loeschweg(self):
        self.assertRegex(
            self.js,
            r'\$\("ged-ganz-loeschen"\)[\s\S]{0,200}gedaechtnisGanzVerwerfen')
        funktion = self.js[self.js.index("async function gedaechtnisGanzVerwerfen"):]
        funktion = funktion[:funktion.index("\n}\n")]
        self.assertIn('api("DELETE", `/api/akten/${akte}/gedaechtnis`)', funktion)

    def test_er_fragt_vorher_und_sagt_was_herausfaellt(self):
        funktion = self.js[self.js.index("async function gedaechtnisGanzVerwerfen"):]
        funktion = funktion[:funktion.index("\n}\n")]
        self.assertLess(funktion.index("confirm("), funktion.index('api("DELETE"'),
                        "Erst fragen, dann löschen.")
        self.assertIn("Lebenssachverhalt", funktion)
        self.assertIn("Zeitstrahl", funktion)
        self.assertIn("jur|nodes bleibt unberührt", funktion)

    def test_danach_raeumt_er_die_arbeitsakte_der_offenen_sitzung_auf(self):
        funktion = self.js[self.js.index("async function gedaechtnisGanzVerwerfen"):]
        funktion = funktion[:funktion.index("\n}\n")]
        self.assertIn("/dokumente/${pfad}", funktion)
        self.assertIn("ausDemGedaechtnis.has", funktion)


if __name__ == "__main__":
    unittest.main()
