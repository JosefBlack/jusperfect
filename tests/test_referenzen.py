"""Referenzen: veröffentlichtes Material im Kontext – getrennt, belegt, begrenzt."""

import tempfile
import unittest
from pathlib import Path

from tests.hilfen import client, dienste, einstellungen

from jusperfect.ocr.base import KeinOcr
from jusperfect.services.referenzen import ReferenzFehler, Referenzendienst


class Referenzendienst_(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ordner = Path(self._tmp.name)
        (self.ordner / "Arbeitsrecht").mkdir()
        (self.ordner / "Arbeitsrecht" / "BAG-Urteil.txt").write_text(
            "Leitsatz: Die Kündigung ist unwirksam.\n\nDas BAG hat entschieden, dass ...", encoding="utf-8")
        (self.ordner / "BGB-241.md").write_text("§ 241 BGB: Pflichten aus dem Schuldverhältnis.", encoding="utf-8")
        self.dienst = Referenzendienst(str(self.ordner), KeinOcr())

    def test_liste_findet_wurzel_und_kategorie(self):
        namen = {e["name"]: e for e in self.dienst.liste()}
        self.assertIn("BGB-241.md", namen)
        self.assertIn("Arbeitsrecht/BAG-Urteil.txt", namen)
        self.assertEqual(namen["Arbeitsrecht/BAG-Urteil.txt"]["kategorie"], "Arbeitsrecht")
        self.assertEqual(namen["Arbeitsrecht/BAG-Urteil.txt"]["label"], "BAG-Urteil")

    def test_passagen_tragen_r_kennung(self):
        passagen = self.dienst.passagen(["BGB-241.md", "Arbeitsrecht/BAG-Urteil.txt"])
        self.assertTrue(passagen)
        for p in passagen:
            self.assertTrue(p.kennung.startswith("R"), p.kennung)
        volltext = " ".join(p.text for p in passagen)
        self.assertIn("241 BGB", volltext)
        self.assertIn("BAG", volltext)

    def test_kein_ausbruch_aus_dem_ordner(self):
        (self.ordner.parent / "geheim.txt").write_text("streng geheim", encoding="utf-8")
        for boese in ("../geheim.txt", "/etc/passwd", "a/b/c.txt", ".x.txt"):
            with self.assertRaises(ReferenzFehler):
                self.dienst.passagen([boese])

    def test_inaktiv_ohne_ordner(self):
        self.assertFalse(Referenzendienst("", KeinOcr()).aktiv)
        self.assertEqual(Referenzendienst("", KeinOcr()).passagen(["x.txt"]), [])
        self.assertTrue(self.dienst.aktiv)


class ReferenzenImKontext(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        ordner = Path(self._tmp.name)
        (ordner / "Nutzungsausfall.txt").write_text(
            "Zum Nutzungsausfall: Der BGH gewaehrt eine Entschaedigung von EINDEUTIG-9911 pro Tag.",
            encoding="utf-8")
        self.d = dienste(einstellungen=einstellungen(JUSPERFECT_REFERENZ_ORDNER=str(ordner)))
        self.c = client(self.d, "ra-weber")
        self.sid = self.c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        self.c.post(f"/api/sitzungen/{self.sid}/dokumente", json={"dokument_ids": ["D-001", "D-002", "D-004"]})

    def test_verfuegbar_und_waehlen(self):
        self.assertTrue(self.c.get("/api/status").json()["referenzen_aktiv"])
        liste = self.c.get("/api/referenzen").json()
        self.assertTrue(liste["aktiv"])
        self.assertEqual(len(liste["eintraege"]), 1)
        r = self.c.put(f"/api/sitzungen/{self.sid}/referenzen", json={"namen": ["Nutzungsausfall.txt"]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["namen"], ["Nutzungsausfall.txt"])
        # bleibt an der Sitzung
        self.assertEqual(self.c.get(f"/api/sitzungen/{self.sid}/referenzen").json()["namen"], ["Nutzungsausfall.txt"])

    def test_gewaehlte_referenz_geht_in_die_frage_ein(self):
        self.c.put(f"/api/sitzungen/{self.sid}/referenzen", json={"namen": ["Nutzungsausfall.txt"]})
        antwort = self.c.post(f"/api/sitzungen/{self.sid}/frage",
                              json={"frage": "Was gilt zum Nutzungsausfall?"}).json()
        # Der Demo-Anbieter zitiert Passagen; die Referenz trägt eine R-Kennung.
        kennungen = [q["kennung"] for q in antwort["quellen"]]
        self.assertTrue(any(k.startswith("R") for k in kennungen),
                        f"keine Referenz zitiert: {kennungen}")

    def test_unbekannte_referenz_wird_abgelehnt(self):
        r = self.c.put(f"/api/sitzungen/{self.sid}/referenzen", json={"namen": ["../weg.txt"]})
        self.assertEqual(r.status_code, 422)


if __name__ == "__main__":
    unittest.main()
