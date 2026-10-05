import unittest

from jusperfect.domain.models import Dokument, Passage, Seite
from jusperfect.services.json_ausgabe import AusgabeUnbrauchbar, json_extrahieren
from jusperfect.services.passagen import budget_anwenden, passagen_bilden, relevante_passagen
from jusperfect.services.quellen import index_bauen, quellen_aus_kennungen, zitate_aufloesen


def _p(k, text, dok="D-1"):
    return Passage(kennung=k, dokument_id=dok, dokument_titel="T", seite=1, text=text)


class Passagen(unittest.TestCase):
    def test_bilden_kennungen(self):
        dok = Dokument(id="D-1", akte_id="A", titel="T", dateiname="t.txt")
        seiten = [Seite(nummer=1, text="A\n\nB"), Seite(nummer=2, text="C")]
        ps = passagen_bilden(2, dok, seiten, max_zeichen=1000)
        self.assertEqual([p.kennung for p in ps], ["D2-S1-P1", "D2-S2-P1"])

    def test_bilden_teilt_lange_absaetze(self):
        dok = Dokument(id="D-1", akte_id="A", titel="T", dateiname="t.txt")
        text = " ".join(f"Satz {i} endet hier." for i in range(200))
        ps = passagen_bilden(1, dok, [Seite(nummer=1, text=text)], max_zeichen=300)
        self.assertGreater(len(ps), 5)
        self.assertTrue(all(len(p.text) <= 320 for p in ps))

    def test_relevanz(self):
        ps = [_p("D1-S1-P1", "Der Mandant fuhr etwa 90 km/h auf der B 27."),
              _p("D1-S1-P2", "Der Kostenvoranschlag beläuft sich auf 4.925,17 EUR."),
              _p("D1-S1-P3", "Die Versicherung schätzt die Geschwindigkeit auf 120 km/h.")]
        auswahl = relevante_passagen("Welche Geschwindigkeit fuhr der Mandant?", ps, max_anzahl=2)
        self.assertEqual([p.kennung for p in auswahl], ["D1-S1-P1", "D1-S1-P3"])

    def test_budget(self):
        ps = [_p("a", "x" * 100), _p("b", "y" * 100), _p("c", "z" * 100)]
        auswahl, gekuerzt = budget_anwenden(ps, 250)
        self.assertEqual(([p.kennung for p in auswahl], gekuerzt), (["a", "b"], True))


class Quellen(unittest.TestCase):
    def test_bekannte_und_unbekannte_belege(self):
        index = index_bauen([_p("D1-S1-P1", "Passage eins"), _p("D1-S1-P2", "Passage zwei")])
        text, quellen, hinweise = zitate_aufloesen("A [Q: D1-S1-P1]. B [Q: D1-S1-P2, D9-S9-P9]. C [Q: D7-S1-P1]", index)
        self.assertEqual([q.kennung for q in quellen], ["D1-S1-P1", "D1-S1-P2"])
        self.assertIn("[Q: ohne Beleg]", text)
        self.assertEqual(len(hinweise), 2)

    def test_ohne_belege_hinweis(self):
        _, quellen, hinweise = zitate_aufloesen("Keine Belege.", {})
        self.assertEqual(quellen, [])
        self.assertIn("keine Belege", hinweise[0])

    def test_kennungen_liste(self):
        index = index_bauen([_p("D1-S1-P1", "x")])
        hinweise = []
        q = quellen_aus_kennungen(["D1-S1-P1", "D1-S1-P1", "falsch"], index, hinweise)
        self.assertEqual(len(q), 1)
        self.assertEqual(len(hinweise), 1)


class Json(unittest.TestCase):
    def test_varianten(self):
        self.assertEqual(json_extrahieren('{"a": 1}')["a"], 1)
        self.assertEqual(json_extrahieren('Hier:\n```json\n{"a": 2}\n```')["a"], 2)
        self.assertEqual(json_extrahieren('Text davor {"a": 3} Text danach')["a"], 3)
        with self.assertRaises(AusgabeUnbrauchbar):
            json_extrahieren("[1, 2]")
