"""Der Browser darf erst aufgehen, wenn der Server antwortet.

Aus der Kanzlei gemeldet am 25.09.2026: Nach dem Doppelklick erscheint zuerst
"Die Website kann nicht geladen werden"; erst ein Klick auf Neuladen bringt
jusperfect. Ursache war ein ``start`` in den Startdateien, das den Browser
öffnete, bevor der Server überhaupt gestartet war.
"""

from __future__ import annotations

import re
import socket
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from jusperfect.__main__ import browser_oeffnen_wenn_bereit

WURZEL = Path(__file__).resolve().parent.parent

#: Die vier Startdateien, die einen Browser aufmachen sollen.
MIT_BROWSER = ("START-DEMO.bat", "START-AWS.bat", "START-KANZLEI.bat",
               "START-JURNODES.bat")


def _freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class DerBrowserWartetAufDenServer(unittest.TestCase):

    def test_er_oeffnet_erst_wenn_der_port_antwortet(self):
        """Der Kern der Sache: geöffnet wird nach dem Zuhören, nicht davor."""
        port = _freier_port()
        geoeffnet: list[float] = []
        lauscht = threading.Event()

        def spaet_aufmachen():
            # Erst eine Weile gar nichts - so verhält sich ein Server, der
            # noch hochfaehrt.
            time.sleep(0.6)
            with socket.socket() as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", port))
                s.listen(1)
                lauscht.set()
                time.sleep(2.0)

        faden = threading.Thread(target=spaet_aufmachen, daemon=True)
        faden.start()
        try:
            with mock.patch("jusperfect.__main__.webbrowser.open",
                            side_effect=lambda *_: geoeffnet.append(time.monotonic())):
                self.assertTrue(
                    browser_oeffnen_wenn_bereit("127.0.0.1", port, frist=5.0))
            self.assertEqual(1, len(geoeffnet))
            self.assertTrue(lauscht.is_set(),
                            "Der Browser ging auf, bevor der Server zuhoerte.")
        finally:
            faden.join(timeout=5)

    def test_ohne_server_geht_gar_kein_browser_auf(self):
        """Eine Fehlerseite hilft niemandem beim Lesen der Meldung im Fenster."""
        port = _freier_port()
        with mock.patch("jusperfect.__main__.webbrowser.open") as auf:
            self.assertFalse(
                browser_oeffnen_wenn_bereit("127.0.0.1", port, frist=0.6))
        auf.assert_not_called()

    def test_auf_alle_adressen_hoeren_heisst_nicht_dorthin_rufen(self):
        """0.0.0.0 ist eine Angabe fuers Zuhoeren, keine zum Anrufen."""
        port = _freier_port()
        with socket.socket() as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", port))
            s.listen(1)
            with mock.patch("jusperfect.__main__.webbrowser.open") as auf:
                self.assertTrue(
                    browser_oeffnen_wenn_bereit("0.0.0.0", port, frist=3.0))
        auf.assert_called_once_with(f"http://127.0.0.1:{port}")


class DieStartdateienOeffnenNichtSelbst(unittest.TestCase):

    def test_keine_startdatei_ruft_den_browser_vor_dem_server(self):
        """Genau diese Zeile war der Fehler."""
        for datei in MIT_BROWSER:
            text = (WURZEL / datei).read_text(encoding="ascii")
            with self.subTest(datei=datei):
                self.assertNotRegex(
                    text, r'start\s+""\s+http://127\.0\.0\.1',
                    "Der Browser wird vor dem Server geoeffnet.")
                self.assertNotIn(
                    "Start-Sleep", text,
                    "Eine feste Wartezeit ist ein Rateschluss.")

    def test_jede_dieser_startdateien_schaltet_den_browser_ein(self):
        for datei in MIT_BROWSER:
            text = (WURZEL / datei).read_text(encoding="ascii")
            with self.subTest(datei=datei):
                self.assertIn("set JUSPERFECT_BROWSER_OEFFNEN=1", text)

    def test_die_zeile_steht_vor_dem_start_des_programms(self):
        """Danach gesetzt wuerde sie nichts mehr bewirken."""
        for datei in MIT_BROWSER:
            text = (WURZEL / datei).read_text(encoding="ascii")
            with self.subTest(datei=datei):
                schalter = text.index("set JUSPERFECT_BROWSER_OEFFNEN=1")
                # Nicht "-m jusperfect.awstest" - das ist die Pruefung
                # davor, nicht der Start des Programms.
                start = re.search(r'"%V?PY%"\s+-m jusperfect\s*\r?$',
                                  text, re.MULTILINE)
                self.assertIsNotNone(start, "Kein Programmstart gefunden.")
                self.assertLess(schalter, start.start())

    def test_wer_nicht_startet_schaltet_ihn_auch_nicht_ein(self):
        """Auf einem Server gibt es keinen Browser; niemand soll ihn suchen."""
        for pfad in sorted(WURZEL.glob("*.bat")):
            if pfad.name in MIT_BROWSER:
                continue
            with self.subTest(datei=pfad.name):
                self.assertNotIn("JUSPERFECT_BROWSER_OEFFNEN",
                                 pfad.read_text(encoding="ascii"))


if __name__ == "__main__":
    unittest.main()
