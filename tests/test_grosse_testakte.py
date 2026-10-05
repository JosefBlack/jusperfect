"""Die große Testakte widerspricht sich nicht selbst.

Aus der Kanzlei: „Sie können nicht unterscheiden, ob eine falsche Angabe vom
Programm kommt oder aus den Fülldaten."

Genau das war der Zustand: Beim Erzeugen der 45 Fülldokumente wurden Absender,
Datum und Inhalt unabhängig voneinander gewürfelt. Im Bautagebuch für August
2025 standen Einträge aus dem März, als Absender die Bauherrin statt der
Bauleitung, und ein Ergänzungsgutachten kam vom Gericht statt vom
Sachverständigen. Für die Frage „findet das Programm die fünf Funde" war das
gleichgültig. Für die Frage „stimmt der Inhalt" war es tödlich: An einem
krummen Maßstab lässt sich Güte nicht messen.

Diese Datei ist der Maßstab für den Maßstab. Sie prüft die erzeugte Akte auf
die drei Eigenschaften, die eine Messung überhaupt erst zulassen – und sie
prüft zugleich, dass die fünf eingebauten Funde dabei unversehrt bleiben.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkzeug"))

import grosse_testakte as g  # noqa: E402

# Die Belege, an denen die fünf Funde hängen. Verschwindet einer davon, ist die
# Akte als Prüfstein wertlos - dann misst man nur noch das Nichts.
BELEGE = {
    "D-002": "24 cm", "D-031": "18 cm",
    "D-008": "20.06.2025", "D-044": "2026",
    "D-009": "21.06.2025", "D-027": "03.07.2025",
    "D-012": "14.08.2025", "D-039": "02.07.2025",
    "D-017": "NICHT auf der Baustelle erschienen", "D-046": "11.06.2025",
}


class GrosseTestakte(unittest.TestCase):
    """Erzeugt die Akte einmal und prüft sie von mehreren Seiten."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._ordner = tempfile.TemporaryDirectory()
        cls.ziel = Path(cls._ordner.name)
        cls.akte = g.erzeugen(cls.ziel)
        cls.text = {d["id"]: (cls.ziel / d["dateiname"]).read_text(encoding="utf-8")
                    for d in cls.akte["dokumente"]}

    @classmethod
    def tearDownClass(cls) -> None:
        cls._ordner.cleanup()

    def test_bautagebuecher_tragen_die_tage_ihres_monats(self):
        """Ein Bautagebuch für August enthält keinen Eintrag aus dem März."""
        geprueft = 0
        for d in self.akte["dokumente"]:
            if not d["titel"].startswith("Bautagebuch"):
                continue
            geprueft += 1
            monat = g._monat_aus_titel(d["titel"], date.fromisoformat(d["datum"]))
            fremd = sorted(t for t in g._genannte_tage(self.text[d["id"]])
                           if (t.year, t.month) != (monat.year, monat.month))
            self.assertEqual(
                [], fremd,
                f"{d['id']} „{d['titel']}“ nennt Tage außerhalb seines Monats: {fremd[:5]}")
        self.assertEqual(6, geprueft, "Es sollen sechs Bautagebücher in der Akte liegen.")

    def test_titel_mit_datum_traegt_dieses_datum(self):
        """„Protokoll Baubesprechung 12.03.2025" ist auf den 12.03.2025 datiert."""
        geprueft = 0
        for d in self.akte["dokumente"]:
            treffer = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", d["titel"])
            if not treffer:
                continue
            geprueft += 1
            self.assertEqual(
                f"{treffer.group(3)}-{treffer.group(2)}-{treffer.group(1)}", d["datum"],
                f"{d['id']} „{d['titel']}“ trägt ein anderes Datum als seinen Titel.")
        self.assertEqual(4, geprueft)

    def test_jeder_absender_ist_ein_beteiligter(self):
        """Wer ein Dokument schreibt, steht auch unter den Beteiligten."""
        bekannt = {b["name"] for b in self.akte["beteiligte"]} | {g.GERICHT, g.BEHOERDE}
        for titel, _datum, absender, _kat, _thema in g.ROUTINE:
            for name in absender.split(" / "):
                self.assertIn(name, bekannt,
                              f"„{titel}“ kommt von {name} – der fehlt unter den Beteiligten.")

    def test_bautagebuch_kommt_von_der_bauleitung(self):
        """Nicht von der Bauherrin: Das Bautagebuch führt die Bauleitung."""
        for titel, _datum, absender, _kat, thema in g.ROUTINE:
            if thema == "tagebuch":
                self.assertEqual(g.ARCHITEKT, absender, f"„{titel}“")
        for d in self.akte["dokumente"]:
            if d["titel"].startswith("Bautagebuch"):
                self.assertIn(f"Geführt von: {g.ARCHITEKT}", self.text[d["id"]],
                              f"{d['id']} nennt die Bauleitung nicht als Führende.")

    def test_gutachten_kommen_vom_sachverstaendigen(self):
        """Ein Ergänzungsgutachten schreibt nicht das Gericht.

        Eine „Stellungnahme zum Gutachten" ist dagegen ein Anwaltsschriftsatz
        und gehört ausdrücklich nicht hierher.
        """
        vom_sachverstaendigen = {"Ergänzungsgutachten",
                                 "Kostenrechnung des Sachverständigen",
                                 "Protokoll des Ortstermins"}
        gefunden = set()
        for titel, _datum, absender, kategorie, _thema in g.ROUTINE:
            if titel in vom_sachverstaendigen:
                gefunden.add(titel)
                self.assertEqual(g.GUTACHTER, absender, f"„{titel}“")
                self.assertEqual("Sachverständige", kategorie, f"„{titel}“")
            else:
                self.assertNotEqual(g.GUTACHTER, absender, f"„{titel}“")
        self.assertEqual(vom_sachverstaendigen, gefunden)

    def test_die_fuenf_funde_liegen_unversehrt_und_weit_auseinander(self):
        """Der eigentliche Zweck der Akte darf durch keine Aufräumarbeit leiden."""
        self.assertEqual(5, len(g.FUNDE))
        for fund in g.FUNDE:
            for kennung in (fund.erste, fund.zweite):
                self.assertIn(BELEGE[kennung], self.text[kennung],
                              f"Fund „{fund.name}“: Der Beleg in {kennung} fehlt.")
            abstand = abs(int(fund.zweite[2:]) - int(fund.erste[2:]))
            self.assertGreaterEqual(
                abstand, 18,
                f"Fund „{fund.name}“ liegt nur {abstand} Dokumente auseinander – "
                "das wäre womöglich eine einzige Portion und bewiese nichts.")
            self.assertTrue(fund.merkmale, f"Fund „{fund.name}“ ist nicht messbar.")
            for merkmal in fund.merkmale:
                self.assertTrue(
                    any(merkmal in self.text[k] for k in (fund.erste, fund.zweite)),
                    f"Fund „{fund.name}“: „{merkmal}“ steht in keinem seiner Dokumente – "
                    "dann misst der Prüfbogen etwas, das die Akte gar nicht hergibt.")

    def test_umfang_bleibt_der_versprochene(self):
        """50 Dokumente zu je mindestens zehn Seiten, zusammen rund 880.000 Zeichen."""
        self.assertEqual(50, len(self.akte["dokumente"]))
        laengen = [len(t) for t in self.text.values()]
        self.assertGreaterEqual(min(laengen), g.MINDESTZEICHEN)
        self.assertGreater(sum(laengen), 850_000)

    def test_dieselbe_saat_ergibt_dieselbe_akte(self):
        """Ohne das wäre kein Vergleich zwischen zwei Läufen möglich."""
        with tempfile.TemporaryDirectory() as zweiter:
            nochmal = g.erzeugen(Path(zweiter))
            self.assertEqual(self.akte["dokumente"], nochmal["dokumente"])
            for d in nochmal["dokumente"]:
                self.assertEqual(self.text[d["id"]],
                                 (Path(zweiter) / d["dateiname"]).read_text(encoding="utf-8"))

    def test_akte_json_und_dateien_stimmen_ueberein(self):
        """Jedes verzeichnete Dokument liegt auch wirklich im Ordner."""
        for d in self.akte["dokumente"]:
            self.assertTrue((self.ziel / d["dateiname"]).is_file(), d["dateiname"])
        vorhanden = {p.name for p in self.ziel.glob("*.txt")}
        self.assertEqual({d["dateiname"] for d in self.akte["dokumente"]}, vorhanden)


if __name__ == "__main__":
    unittest.main()
