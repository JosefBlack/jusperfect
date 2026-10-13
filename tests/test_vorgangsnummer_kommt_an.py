"""Die Vorgangsnummer in der Antwort hat eine Zeile im Fenster – nachgemessen.

Aus der Kanzlei am 13.10.2026: „Akte öffnen nicht möglich Vorgang wurde
abgebrochen interner Fehler 2e2e3bd1."

Die Nummer kam an. **Die Zeile dazu nicht.** `tests/test_fehlergrenze.py` hält
seit dem 05.10.2026 fest, dass die Nummer in Antwort *und* Protokoll steht –
gemessen mit `assertLogs(level=INFO)`, also mit einer Stufe, die der Test
selbst setzt. Im Betrieb setzt sie niemand:

* Uvicorn richtet nur seine eigenen Kanäle ein (`disable_existing_loggers` ist
  aus, der Wurzelkanal bleibt unberührt).
* Unsere Einträge steigen zum Wurzelkanal, der keinen Empfänger hat. Dann
  greift `logging.lastResort`, und der nimmt erst ab WARNUNG.
* `ereignis` schrieb auf INFO.

Die Zeile entstand und ging nirgendwohin. Eine Vorgangsnummer ohne Zeile ist
keine Auskunft, sondern eine Zumutung – der Bearbeiter hat etwas in der Hand,
womit niemand etwas anfangen kann.

Diese Datei misst deshalb nicht, was der Kanal bekommt, sondern **was im
Fenster steht**: in einem eigenen Prozess, mit Uvicorns eigener
Protokolleinrichtung und ohne jede Stufe von Hand.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import unittest

MARKER = "Mandantin Kraemer, HWS-Distorsion"

#: Läuft in einem eigenen Prozess: Protokolleinrichtung ist Prozesszustand,
#: und ein Test, der sie im Testlauf umstellt, trifft alle anderen mit.
SKRIPT = r"""
import asyncio, logging, logging.config, uvicorn.config
logging.config.dictConfig(uvicorn.config.LOGGING_CONFIG)

from jusperfect.fehlergrenze import Fehlergrenze, protokolle_eindaemmen
protokolle_eindaemmen()

MARKER = %r

async def platzt(scope, receive, send):
    raise ValueError(MARKER)

grenze = Fehlergrenze(platzt, status_fuer=lambda exc: (500, "Interner Fehler."))
gesendet = []

async def senden(nachricht):
    gesendet.append(nachricht)

async def empfangen():
    return {"type": "http.request", "body": b"", "more_body": False}

asyncio.run(grenze({"type": "http", "method": "POST",
                    "path": "/api/sitzungen/VU-2026-0042/frage"},
                   empfangen, senden))

print(gesendet[1]["body"].decode("utf-8"))
""" % MARKER


class WasImFensterSteht(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        lauf = subprocess.run([sys.executable, "-I", "-c", SKRIPT],
                              capture_output=True, text=True, timeout=120)
        if lauf.returncode != 0:
            raise AssertionError(f"Der Teilprozess brach ab:\n{lauf.stderr}")
        cls.antwort = lauf.stdout
        cls.fenster = lauf.stderr

    def test_die_antwort_nennt_eine_vorgangsnummer(self):
        self.assertIn("Vorgangsnummer", self.antwort)
        self.assertNotIn(MARKER, self.antwort)

    def test_die_antwort_sagt_auch_wohin_mit_der_nummer(self):
        """Eine Nummer ohne Anweisung ist fuer den Bearbeiter nichts wert."""
        self.assertIn("schwarzen Fenster", self.antwort)

    def test_dieselbe_nummer_steht_im_fenster(self):
        import re

        treffer = re.search(r"Vorgangsnummer ([0-9a-f]{8})", self.antwort)
        self.assertIsNotNone(treffer, self.antwort)
        nummer = treffer.group(1)
        self.assertIn(nummer, self.fenster,
                      "Die Nummer steht in der Antwort und nirgends sonst – "
                      "genau der Zustand vom 13.10.2026.")
        self.assertIn("fehler_abgefangen", self.fenster)

    def test_die_zeile_nennt_die_kette_und_nicht_den_wortlaut(self):
        self.assertIn("ValueError", self.fenster, "Ohne die Kette ist die Zeile nutzlos.")
        self.assertNotIn(MARKER, self.fenster)
        self.assertNotIn("VU-2026-0042", self.fenster, "Kein Pfad, keine Aktenkennung.")

    def test_im_fenster_steht_kein_traceback(self):
        self.assertNotIn("Traceback", self.fenster)
        self.assertNotIn('File "', self.fenster)


class DerWegHinaus(unittest.TestCase):
    """Warum ERROR und nicht INFO – die Messung, die dahinter steht."""

    def test_der_letzte_empfaenger_nimmt_erst_ab_warnung(self):
        self.assertEqual(logging.lastResort.level, logging.WARNING)

    def test_stoerung_schreibt_darueber_und_ereignis_darunter(self):
        from jusperfect.security.protokoll import ereignis, protokoll, stoerung

        log = protokoll("probe")
        with self.assertLogs(log, level=logging.INFO) as auf:
            ereignis(log, "leise", zahl=1)
            stoerung(log, "laut", zahl=2)
        stufen = [e.levelno for e in auf.records]
        self.assertEqual(stufen, [logging.INFO, logging.ERROR])
        self.assertGreaterEqual(stufen[1], logging.lastResort.level)

    def test_stoerung_weist_dieselben_felder_ab_wie_ereignis(self):
        from jusperfect.security.protokoll import ProtokollVerstoss, protokoll, stoerung

        with self.assertRaises(ProtokollVerstoss):
            stoerung(protokoll("probe"), "laut", text="Akteninhalt")


if __name__ == "__main__":
    unittest.main()
