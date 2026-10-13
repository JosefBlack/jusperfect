"""START-JUSPERFECT.bat – ein Einstieg für den, der nicht weiß, welche Datei er nehmen soll.

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
Rechner, rund 240 Stellen in den Unterlagen) und `START-JUSPERFECT.bat` danebenzulegen. Zuerst hieß sie `START.bat`;
aus der Kanzlei nachgereicht: „bitte benenne den startbutton
start-jusperfect“ – ein Name, der in einem Ordner voller START-Dateien
nichts unterscheidet, tut es nicht.

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
START = WURZEL / "START-JUSPERFECT.bat"


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
        self.assertIn("START-JUSPERFECT.bat daneben tut genau dasselbe", self.text)


if __name__ == "__main__":
    unittest.main()


class DieVerknuepfungZeigtAufDieEchtenAkten(unittest.TestCase):
    """Sie zeigte auf die erfundenen Testakten – und hieß dabei „jusperfect".

    Aus der Kanzlei am 13.10.2026: „erstelle auch die Möglichkeit einer
    Verknüpfung." Es gab sie – nur zeigte die erste, schlicht „jusperfect"
    genannte, auf `START-AWS.bat`. Wer sie vom Schreibtisch nahm, arbeitete mit
    Akten, die es nicht gibt, und merkte es erst an den Namen darin.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = (WURZEL / "VERKNUEPFUNG.bat").read_text(encoding="ascii")

    def _angelegt(self) -> list[str]:
        return [z for z in self.text.splitlines() if z.startswith("call :verknuepfen")]

    def test_die_erste_verknuepfung_fuehrt_zu_den_echten_akten(self):
        zeile = [z for z in self._angelegt() if z.startswith('call :verknuepfen "jusperfect"')]
        self.assertEqual(len(zeile), 1, self.text)
        self.assertIn("START-JUSPERFECT.bat", zeile[0])
        self.assertIn("ECHTEN", zeile[0])

    def test_keine_verknuepfung_zeigt_mehr_auf_die_testakten(self):
        for zeile in self._angelegt():
            self.assertNotIn("START-AWS.bat", zeile)

    def test_die_demo_bleibt_als_zweite_und_sagt_was_sie_ist(self):
        zeile = [z for z in self._angelegt() if "START-DEMO.bat" in z]
        self.assertEqual(len(zeile), 1)
        self.assertIn("erfundene Akten", zeile[0])

    def test_sie_sucht_die_datei_die_sie_verknuepft(self):
        """Fehlt sie, soll die Meldung ihren Namen nennen – nicht einen anderen."""
        self.assertIn('if exist "%ORDNER%\\START-JUSPERFECT.bat" goto gefunden', self.text)

    def test_kein_senkrechter_strich_in_den_angelegten_zeilen(self):
        """Er geht durch cmd UND durch PowerShell; eine der beiden stolpert."""
        for zeile in self._angelegt():
            self.assertNotIn("|", zeile, zeile)
