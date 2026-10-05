import unittest

from jusperfect.security.approval import Freigabe, FreigabeUngueltig, Freigabestelle


class Freigaben(unittest.TestCase):
    def setUp(self):
        self.stelle = Freigabestelle()

    def test_gueltige_freigabe(self):
        f = self.stelle.erteilen("e1", "A-1", "ra-weber", "Text")
        self.assertIs(self.stelle.pruefen(f, "A-1", "Text"), f)

    def test_geaenderter_text(self):
        f = self.stelle.erteilen("e1", "A-1", "ra-weber", "Text")
        with self.assertRaises(FreigabeUngueltig):
            self.stelle.pruefen(f, "A-1", "Text.")

    def test_andere_akte(self):
        f = self.stelle.erteilen("e1", "A-1", "ra-weber", "Text")
        with self.assertRaises(FreigabeUngueltig):
            self.stelle.pruefen(f, "A-2", "Text")

    def test_nachgebaute_freigabe(self):
        f = self.stelle.erteilen("e1", "A-1", "ra-weber", "Text")
        falsch = Freigabe(f.entwurf_id, f.akte_id, "eindringling", f.text_pruefsumme, f.zeitpunkt, f.signatur)
        with self.assertRaises(FreigabeUngueltig):
            self.stelle.pruefen(falsch, "A-1", "Text")

    def test_anderer_prozesslauf(self):
        f = Freigabestelle().erteilen("e1", "A-1", "ra-weber", "Text")
        with self.assertRaises(FreigabeUngueltig):
            self.stelle.pruefen(f, "A-1", "Text")

    def test_kein_objekt(self):
        with self.assertRaises(FreigabeUngueltig):
            self.stelle.pruefen({"signatur": "x"}, "A-1", "Text")
        with self.assertRaises(FreigabeUngueltig):
            self.stelle.erteilen("e1", "A-1", "", "Text")
