import logging
import unittest

from jusperfect.security.protokoll import ProtokollVerstoss, ereignis, kurzkennung, protokoll


class Protokoll(unittest.TestCase):
    def test_inhaltsfelder_abgewiesen(self):
        log = protokoll("test")
        for feld in ("text", "prompt", "Frage", "antwort", "entwurf"):
            with self.assertRaises(ProtokollVerstoss):
                ereignis(log, "x", **{feld: "Mandant Testmann"})

    def test_lange_werte_abgewiesen(self):
        with self.assertRaises(ProtokollVerstoss):
            ereignis(protokoll("test"), "x", grund="a" * 201)

    def test_kurzkennung_verraet_nichts(self):
        k = kurzkennung("Thomas Testmann hat Nackenschmerzen")
        self.assertNotIn("Testmann", k)
        self.assertRegex(k, r"^[0-9a-f]{12}:\d+$")

    def test_eintrag_ist_json(self):
        log = protokoll("test")
        with self.assertLogs(log, level="INFO") as cm:
            ereignis(log, "sitzung_eroeffnet", sitzung="s1", akte="A-1")
        self.assertIn('"ereignis": "sitzung_eroeffnet"', cm.output[0])
