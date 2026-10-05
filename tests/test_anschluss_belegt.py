"""Wenn jusperfect schon läuft: sagen, dass es schon läuft.

Aus der Kanzlei am 02.10.2026 kam dieses Bild:

    ERROR: [Errno 10048] error while attempting to bind on address
    ('127.0.0.1', 8765): normalerweise darf jede socketadresse nur jeweils
    einmal verwendet werden

Rot, englisch, mit einer Fehlernummer – und der harmloseste denkbare Grund:
Es lief noch ein Fenster. Wer so etwas liest, sucht im Programm.

Die Meldung von uvicorn kommt erst, wenn der Server sich schon gestartet hat
und gleich wieder herunterfährt; davor und danach stehen vier Zeilen „INFO"
auf dem Schirm. Gefragt wird deshalb vorher.
"""

from __future__ import annotations

import socket
import unittest
from unittest import mock

from jusperfect.__main__ import _SCHON_DA, anschluss_belegt, main


class DieFrage(unittest.TestCase):
    def test_hoert_jemand_dann_ja(self):
        horcher = socket.socket()
        horcher.bind(("127.0.0.1", 0))
        horcher.listen(1)
        try:
            self.assertTrue(anschluss_belegt("127.0.0.1", horcher.getsockname()[1]))
        finally:
            horcher.close()

    def test_hoert_niemand_dann_nein(self):
        frei = socket.socket()
        frei.bind(("127.0.0.1", 0))
        port = frei.getsockname()[1]
        frei.close()
        self.assertFalse(anschluss_belegt("127.0.0.1", port))

    def test_die_zuhoeradresse_wird_zur_anrufadresse(self):
        """0.0.0.0 ist eine Angabe fürs Zuhören, keine zum Anrufen."""
        with mock.patch("socket.create_connection") as anruf:
            anschluss_belegt("0.0.0.0", 8765)
        self.assertEqual(("127.0.0.1", 8765), anruf.call_args.args[0])


class DerStart(unittest.TestCase):
    def test_bei_belegtem_anschluss_startet_nichts(self):
        """Weder der Server noch der Browser – und die Meldung steht da."""
        with mock.patch("jusperfect.__main__.anschluss_belegt", return_value=True), \
             mock.patch("jusperfect.__main__.Einstellungen") as e, \
             mock.patch("jusperfect.__main__.app_erstellen") as bauen, \
             mock.patch("uvicorn.run") as laufen, \
             mock.patch("builtins.print") as sagen:
            e.aus_umgebung.return_value = mock.Mock(host="127.0.0.1", port=8765)
            with self.assertRaises(SystemExit) as ende:
                main()
        self.assertEqual(1, ende.exception.code)
        bauen.assert_not_called()
        laufen.assert_not_called()
        self.assertIn("jusperfect laeuft bereits", sagen.call_args.args[0])

    def test_bei_freiem_anschluss_laeuft_alles_wie_bisher(self):
        with mock.patch("jusperfect.__main__.anschluss_belegt", return_value=False), \
             mock.patch("jusperfect.__main__.Einstellungen") as e, \
             mock.patch("jusperfect.__main__.app_erstellen"), \
             mock.patch("uvicorn.run") as laufen:
            e.aus_umgebung.return_value = mock.Mock(host="127.0.0.1", port=8765)
            main()
        laufen.assert_called_once()


class DieMeldung(unittest.TestCase):
    def test_sie_nennt_beide_wege(self):
        text = _SCHON_DA.format(port=8765, ziel="127.0.0.1")
        self.assertIn("http://127.0.0.1:8765", text)
        self.assertIn("schliessen", text)

    def test_sie_warnt_vor_der_demo(self):
        """Das laufende Fenster könnte START-DEMO.bat sein.

        Jemanden stillschweigend auf erfundene Akten zu führen, während er an
        echten arbeiten will, wäre die gefährlichste Art zu helfen. Deshalb
        wird der Browser hier auch nicht von selbst geöffnet.
        """
        self.assertIn("START-DEMO.bat", _SCHON_DA)

    def test_sie_sagt_dass_es_kein_programmfehler_ist(self):
        self.assertIn("Am Programm liegt es nicht", _SCHON_DA)

    def test_sie_kennt_den_fall_ohne_sichtbares_fenster(self):
        """Ein Fenster, das weggeklickt wurde, läuft weiter."""
        self.assertIn("Task-Manager", _SCHON_DA)


if __name__ == "__main__":
    unittest.main()
