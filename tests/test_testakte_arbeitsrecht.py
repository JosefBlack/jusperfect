"""Die Testakte 115/26 AR – ihre Widersprüche sind der Zweck, nicht Beiwerk.

Sie ist so gebaut, dass die Analyse etwas zu finden hat: fünf Widersprüche,
eine Frist, mehrere Beteiligte. Wer die Dateien später aufräumt oder glättet,
nimmt ihr genau das. Diese Tests halten fest, was drinstehen muss.

Geprüft wird der *Text der Akte*, nicht die Antwort eines Modells. Ob das
Programm die Widersprüche findet, entscheidet der Mensch beim Ausprobieren –
die Auflösung dazu steht in testdaten/AUFLOESUNG.md.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.hilfen import TESTAKTEN, client, dienste

AKTE = "AR-2026-0115"
ORDNER = TESTAKTEN / AKTE


def _text(dateiname: str) -> str:
    return (ORDNER / dateiname).read_text(encoding="utf-8")


def _fliesstext(dateiname: str) -> str:
    """Wie _text, aber ohne Zeilenumbrüche im Satz.

    Die Schriftsätze sind auf 78 Zeichen umbrochen; ein gesuchter Satz steht
    deshalb oft über zwei Zeilen. Für die Prüfung auf Formulierungen zählt der
    Wortlaut, nicht der Umbruch.
    """
    return " ".join(_text(dateiname).split())


class AufbauDerAkte(unittest.TestCase):
    def setUp(self) -> None:
        self.daten = json.loads((ORDNER / "akte.json").read_text(encoding="utf-8"))

    def test_jedes_verzeichnete_dokument_liegt_auch_da(self):
        for dokument in self.daten["dokumente"]:
            with self.subTest(dokument=dokument["id"]):
                self.assertTrue((ORDNER / dokument["dateiname"]).is_file())

    def test_keine_datei_bleibt_unverzeichnet(self):
        """Sonst geht ein Dokument beim Öffnen der Akte stillschweigend verloren."""
        verzeichnet = {d["dateiname"] for d in self.daten["dokumente"]}
        vorhanden = {p.name for p in ORDNER.glob("*.txt")}
        self.assertEqual(vorhanden - verzeichnet, set())

    def test_die_akte_ist_umfangreich_genug_um_etwas_zu_zeigen(self):
        zeichen = sum(len(_text(d["dateiname"])) for d in self.daten["dokumente"])
        self.assertGreaterEqual(len(self.daten["dokumente"]), 8)
        self.assertGreater(zeichen, 5_000)

    def test_beteiligte_und_frist_sind_hinterlegt(self):
        rollen = " ".join(b["rolle"] for b in self.daten["beteiligte"])
        self.assertIn("Zeuge", rollen)
        self.assertIn("Mandantin", rollen)
        self.assertEqual(len(self.daten["fristen"]), 1)
        self.assertIn("KSchG", self.daten["fristen"][0]["bezeichnung"])


class DieEingebautenWidersprueche(unittest.TestCase):
    """Fünf Stück. Verschwindet einer, verliert die Akte ihren Zweck."""

    def test_1_tatdatum_weicht_zwischen_kuendigung_und_vermerk_ab(self):
        self.assertIn("27.04.2026", _text("02_kuendigungsschreiben.txt"))
        self.assertIn("28.04.2026", _text("01_erstgespraech_mandantin.txt"))

    def test_2_der_vorwurf_faellt_in_genehmigten_urlaub(self):
        self.assertIn("27.04.2026", _text("06_urlaubsplan_auszug.txt"))
        self.assertIn("Erholungsurlaub", _text("06_urlaubsplan_auszug.txt"))

    def test_3_die_anhoerung_datiert_nach_der_kuendigung(self):
        self.assertIn("04.05.2026", _text("02_kuendigungsschreiben.txt"))
        self.assertIn("06.05.2026", _text("03_anhoerung_betriebsrat.txt"))

    def test_4_der_zeuge_ist_unsicher_die_anhoerung_stellt_es_sicher_dar(self):
        """Der schwierigste Widerspruch: aus einer unsicheren Beobachtung
        wird in der Anhörung eine feste Tatsachenbehauptung."""
        zeuge = _fliesstext("05_zeugenaussage_salzwedel.txt")
        self.assertIn("Genau erkannt habe ich sie nicht", zeuge)
        self.assertIn("da will ich mich nicht festlegen", zeuge)
        self.assertIn("beobachtet", _text("03_anhoerung_betriebsrat.txt"))

    def test_5_der_betriebsrat_wusste_angeblich_von_nichts(self):
        self.assertIn("05.05.2026", _text("01_erstgespraech_mandantin.txt"))
        self.assertIn("erst durch sie", _fliesstext("01_erstgespraech_mandantin.txt"))

    def test_die_aufloesung_beschreibt_alle_fuenf(self):
        text = (TESTAKTEN.parent / "AUFLOESUNG.md").read_text(encoding="utf-8")
        for stichwort in ("Tatdatum", "Urlaub", "Reihenfolge", "Der Zeuge", "Kenntnis"):
            with self.subTest(stichwort=stichwort):
                self.assertIn(stichwort, text)


class ImProgramm(unittest.TestCase):
    def test_die_akte_laesst_sich_oeffnen_und_laden(self):
        c = client(dienste(), "ra-weber")
        antwort = c.post("/api/sitzungen", json={"akte_id": AKTE})
        self.assertEqual(antwort.status_code, 201, antwort.text)
        daten = antwort.json()
        self.assertEqual(len(daten["dokumente"]), 8)
        self.assertEqual(len(daten["beteiligte"]), 7)
        sid = daten["sitzung"]["id"]
        geladen = c.post(f"/api/sitzungen/{sid}/dokumente",
                         json={"dokument_ids": [d["id"] for d in daten["dokumente"]]}).json()
        self.assertEqual(geladen["kostenschaetzung"]["dokumente"], 8)
        self.assertGreater(len(c.get(f"/api/sitzungen/{sid}/passagen").json()["passagen"]), 5)


if __name__ == "__main__":
    unittest.main()
