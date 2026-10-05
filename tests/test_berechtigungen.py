import unittest

from jusperfect.domain.models import Akte, Nutzer
from jusperfect.security.berechtigungen import DateiBerechtigungen, UnbekannterNutzer, ZugriffVerweigert
from jusperfect.security.identitaet import Identitaet, NichtAngemeldet, aus_cognito_ereignis, aus_kopfzeile


class Berechtigungen(unittest.TestCase):
    def setUp(self):
        self.b = DateiBerechtigungen([Nutzer(id="anwalt", name="A", akten=["*"]), Nutzer(id="refa", name="R", akten=["A-1"])])

    def test_pruefen_und_filtern(self):
        self.b.pruefen(Identitaet("refa"), "A-1")
        with self.assertRaises(ZugriffVerweigert):
            self.b.pruefen(Identitaet("refa"), "A-2")
        akten = [Akte(id="A-1", aktenzeichen="1", bezeichnung="x"), Akte(id="A-2", aktenzeichen="2", bezeichnung="y")]
        self.assertEqual([a.id for a in self.b.filtern(Identitaet("refa"), akten)], ["A-1"])
        self.assertEqual(len(self.b.filtern(Identitaet("anwalt"), akten)), 2)

    def test_unbekannt(self):
        with self.assertRaises(UnbekannterNutzer):
            self.b.pruefen(Identitaet("fremd"), "A-1")

    def test_cognito_gruppe_alle_akten(self):
        ident = Identitaet("fremd-sub", "x@y", gruppen=("alle-akten",))
        self.b.pruefen(ident, "A-99")
        ident2 = Identitaet("refa", gruppen=("alle-akten",))
        self.b.pruefen(ident2, "A-99")


class Identitaeten(unittest.TestCase):
    def test_cognito_ereignis(self):
        ereignis = {"requestContext": {"authorizer": {"jwt": {"claims": {"sub": "abc", "email": "a@b", "cognito:groups": "[alle-akten]"}}}}}
        ident = aus_cognito_ereignis(ereignis)
        self.assertEqual((ident.nutzer_id, ident.anzeigename, ident.gruppen), ("abc", "a@b", ("alle-akten",)))

    def test_ohne_anspruch(self):
        with self.assertRaises(NichtAngemeldet):
            aus_cognito_ereignis({})
        with self.assertRaises(NichtAngemeldet):
            aus_cognito_ereignis({"requestContext": {"authorizer": {"jwt": {"claims": {"sub": ""}}}}})
        with self.assertRaises(NichtAngemeldet):
            aus_kopfzeile("  ")
