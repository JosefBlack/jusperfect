"""Eigene Aufträge als Dateien: Trennlinie, Ordnergrenze, Entwurfsvorlage."""

import tempfile
import unittest
from pathlib import Path

from tests.hilfen import client, dienste, einstellungen

from jusperfect.providers.base import Nutzung, ProviderAntwort
from jusperfect.services.auftraege import AuftragFehler, Auftragsdienst, zerlege


class Trennlinie(unittest.TestCase):
    def test_ohne_trennlinie_ist_alles_anweisung(self):
        anw, mat = zerlege("Entwirf ein Schreiben an die Versicherung.")
        self.assertEqual(anw, "Entwirf ein Schreiben an die Versicherung.")
        self.assertEqual(mat, "")

    def test_trennt_anweisung_und_material(self):
        anw, mat = zerlege("Entwirf ein Anspruchsschreiben.\n\n--- Rechtslage ---\n\nDer BGH hat entschieden ...")
        self.assertEqual(anw, "Entwirf ein Anspruchsschreiben.")
        self.assertIn("BGH", mat)


class Auftragsordner(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ordner = Path(self._tmp.name)
        (self.ordner / "Verkehrsrecht").mkdir()
        (self.ordner / "Verkehrsrecht" / "Anspruch.txt").write_text(
            "Entwirf ein Anspruchsschreiben an die Haftpflichtversicherung.\n\n"
            "--- Rechtslage ---\n\nZum Nutzungsausfall: Der BGH hat entschieden ...", encoding="utf-8")
        (self.ordner / "Kurz.md").write_text("Fasse den Sachstand in drei Sätzen zusammen.", encoding="utf-8")
        (self.ordner / "notiz.rtf").write_text("kein Auftrag", encoding="utf-8")  # falsche Endung
        self.dienst = Auftragsdienst(str(self.ordner))

    def test_liste_findet_wurzel_und_kategorie(self):
        namen = {e["name"]: e for e in self.dienst.liste()}
        self.assertIn("Kurz.md", namen)
        self.assertIn("Verkehrsrecht/Anspruch.txt", namen)
        self.assertNotIn("notiz.rtf", namen)  # falsche Endung übergangen
        self.assertEqual(namen["Verkehrsrecht/Anspruch.txt"]["kategorie"], "Verkehrsrecht")
        self.assertEqual(namen["Verkehrsrecht/Anspruch.txt"]["label"], "Anspruch")
        self.assertTrue(namen["Verkehrsrecht/Anspruch.txt"]["hat_material"])
        self.assertFalse(namen["Kurz.md"]["hat_material"])

    def test_laden_trennt_anweisung_und_material(self):
        a = self.dienst.laden("Verkehrsrecht/Anspruch.txt")
        self.assertIn("Anspruchsschreiben", a.anweisung)
        self.assertIn("BGH", a.material)

    def test_kein_ausbruch_aus_dem_ordner(self):
        (self.ordner.parent / "geheim.txt").write_text("streng geheim, lang genug fuer die Pruefung", encoding="utf-8")
        for boese in ("../geheim.txt", "..\\geheim.txt", "/etc/passwd", "a/b/c.txt", ".versteckt.txt"):
            with self.assertRaises(AuftragFehler):
                self.dienst.laden(boese)

    def test_nicht_text_wird_abgelehnt(self):
        with self.assertRaises(AuftragFehler):
            self.dienst.laden("Verkehrsrecht/Anspruch.pdf")

    def test_zu_kurze_anweisung(self):
        (self.ordner / "leer.txt").write_text("Hi", encoding="utf-8")
        with self.assertRaises(AuftragFehler):
            self.dienst.laden("leer.txt")

    def test_inaktiv_ohne_ordner(self):
        self.assertFalse(Auftragsdienst("").aktiv)
        self.assertTrue(self.dienst.aktiv)


class _SpyProvider:
    modell_id = "spy"

    def __init__(self):
        self.gesehen_aufgabe = ""

    def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        self.gesehen_aufgabe = aufgabe
        # Mit Beleg: Seit dem 05.10.2026 (Befund F04) wird ein Entwurf ohne
        # einen einzigen tragenden Beleg nicht mehr ausgegeben. Geprueft wird
        # hier das Muster im Prompt, nicht die Belegpflicht.
        return ProviderAntwort(text='{"betreff": "Test", "text": "Ein Entwurf [Q: D1-S1-P1]."}',
                               nutzung=Nutzung(), modell=self.modell_id)

    def fragen_stream(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        yield self.fragen(system, material, aufgabe)


class AuftragImEntwurf(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        ordner = Path(self._tmp.name)
        (ordner / "Anspruch.txt").write_text(
            "Entwirf ein Anspruchsschreiben an die Haftpflichtversicherung.\n\n"
            "--- Rechtslage ---\n\nZum Nutzungsausfall gilt: EINDEUTIGES-MERKMAL-4711.", encoding="utf-8")
        self.spy = _SpyProvider()
        self.d = dienste(einstellungen=einstellungen(JUSPERFECT_AUFTRAG_ORDNER=str(ordner)), provider=self.spy)
        self.c = client(self.d, "ra-weber")
        self.sid = self.c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        self.c.post(f"/api/sitzungen/{self.sid}/dokumente", json={"dokument_ids": ["D-001", "D-002"]})

    def test_liste_und_vorbelegung(self):
        liste = self.c.get("/api/auftraege").json()
        self.assertTrue(liste["aktiv"])
        self.assertEqual(len(liste["eintraege"]), 1)
        a = self.c.get("/api/auftraege/Anspruch.txt").json()
        self.assertIn("Anspruchsschreiben", a["anweisung"])
        self.assertTrue(a["hat_material"])
        self.assertNotIn("EINDEUTIGES-MERKMAL", a["anweisung"])  # Material bleibt im Dienst

    def test_entwurf_zieht_material_als_muster_heran(self):
        r = self.c.post(f"/api/sitzungen/{self.sid}/entwuerfe",
                        json={"art": "versicherung", "anweisung": "Anspruch geltend machen.",
                              "auftrag": "Anspruch.txt"})
        self.assertEqual(r.status_code, 201)
        # Das Material des Auftrags ist im Prompt gelandet, den der Anbieter sah.
        self.assertIn("EINDEUTIGES-MERKMAL-4711", self.spy.gesehen_aufgabe)

    def test_unbekannter_auftrag_422(self):
        r = self.c.post(f"/api/sitzungen/{self.sid}/entwuerfe",
                        json={"art": "versicherung", "anweisung": "X", "auftrag": "../weg.txt"})
        self.assertEqual(r.status_code, 422)


if __name__ == "__main__":
    unittest.main()
