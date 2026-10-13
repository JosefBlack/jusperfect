"""START.bat – ein Einstieg für den, der nicht weiß, welche Datei er nehmen soll.

Aus der Kanzlei am 13.10.2026: „Warum heißt die Startdatei START-JURNODES –
ist doch unlogisch, und die Eingabeaufforderung schreibt, ich kann START-AWS
benutzen."

Beides stimmt. Die vier Startdateien sind nacheinander entstanden und jede
nach etwas anderem benannt:

| Datei | benannt nach | was sie tut |
|---|---|---|
| `START-DEMO.bat` | dem Zweck | erfundene Akten, ohne KI |
| `START-AWS.bat` | dem Modellanbieter | erfundene Akten, mit KI |
| `START-KANZLEI.bat` | dem Ort | echte Akten übers Laufwerk |
| `START-JURNODES.bat` | der Schnittstelle | **echte Akten, der tägliche Weg** |

Keiner der Namen sagt das Einzige, worauf es ankommt – echte Akten oder
erfundene. Und „AWS" trennt nach etwas, das gar nicht trennt: Das Modell kommt
in allen vier Fällen von dort.

Entschieden wurde, die Namen zu **lassen** (eine Verknüpfung, ein zweiter
Rechner, rund 240 Stellen in den Unterlagen) und `START.bat` danebenzulegen.

**Sie trägt keine eigenen Einstellungen.** Eine zweite Stelle mit denselben
Werten wäre genau der Fehler, den `tests/test_starter.py` seit dem 25.09.2026
verbietet: eine Verbesserung an der einen und nicht an der anderen, und
niemand sieht es.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
START = WURZEL / "START.bat"


class SieRuftDieAndereAufUndSonstNichts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.roh = START.read_bytes()
        cls.text = cls.roh.decode("ascii")

    def test_sie_ruft_den_echten_weg(self):
        self.assertIn('call "%~dp0START-JURNODES.bat"', self.text)

    def test_sie_setzt_keine_einzige_einstellung(self):
        """Sonst stünden dieselben Werte an zwei Stellen."""
        gesetzt = re.findall(r"(?m)^\s*set\s+\"?(JUSPERFECT_\w+|JURNODES_\w+)",
                             self.text)
        self.assertEqual(gesetzt, [], gesetzt)

    def test_sie_legt_keine_arbeitsumgebung_an(self):
        self.assertNotIn("_UMGEBUNG.bat", self.text)
        self.assertNotIn("-m venv", self.text)

    def test_sie_oeffnet_den_browser_nicht_selbst(self):
        """Das tut die Datei, die sie ruft - und nur die."""
        self.assertNotIn("JUSPERFECT_BROWSER_OEFFNEN", self.text)

    def test_windows_zeilenenden(self):
        self.assertEqual(self.roh.count(b"\n"), self.roh.count(b"\r\n"))

    def test_sie_ist_reiner_ascii_text(self):
        """Wie jede .bat hier - Windows liest sie sonst in einer anderen Tabelle."""
        self.roh.decode("ascii")

    def test_sie_sagt_im_kopf_warum_es_sie_gibt(self):
        self.assertIn("echte Akten", self.text.replace("ECHTEN", "echten"))


class DerIrrefuehrendeSatzIstWeg(unittest.TestCase):
    """Der zweite Teil der Meldung aus der Kanzlei.

    Dort stand „fuer die erfundenen Testakten START-AWS.bat" – gemeint war
    eine Abgrenzung, gelesen wurde ein Angebot.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = (WURZEL / "START-JURNODES.bat").read_text(encoding="ascii")

    def test_die_anderen_dateien_stehen_als_NICHT_dafuer_da(self):
        self.assertIn("NICHT fuer Ihre Akten", self.text)

    def test_jede_der_drei_wird_mit_ihrem_zweck_genannt(self):
        for datei, zweck in (("START-AWS.bat", "erfundene Testakten"),
                             ("START-DEMO.bat", "Vorfuehrung"),
                             ("START-KANZLEI.bat", "Laufwerk")):
            with self.subTest(datei=datei):
                zeile = [z for z in self.text.splitlines() if datei in z
                         and z.strip().startswith("echo")]
                self.assertTrue(zeile, f"{datei} wird nicht mehr genannt.")
                self.assertIn(zweck, " ".join(zeile))

    def test_der_neue_einstieg_wird_genannt(self):
        self.assertIn("START.bat daneben tut genau dasselbe", self.text)


if __name__ == "__main__":
    unittest.main()
