"""Der dateibasierte jur|nodes-Adapter: <Wurzel>/<Anwalt>/<Jahr>/<Akte>."""

import tempfile
import unittest
from pathlib import Path

from tests.hilfen import client, dienste

from jusperfect.jurnodes.base import AkteNichtGefunden, DokumentNichtGefunden
from jusperfect.jurnodes.webdav_adapter import WebDavJurNodesAdapter
from jusperfect.security.approval import Freigabestelle
from jusperfect.services.gedaechtnis import Gedaechtnisdienst


class WebDavAdapter(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.wurzel = Path(self._tmp.name)
        # Nachbau der echten Struktur: J:/Akten/Dortschy/2026/X-107-2026 ohne Name wer gegen wen
        self.akte = self.wurzel / "Dortschy" / "2026" / "X-107-2026 ohne Name wer gegen wen"
        (self.akte / "Schriftsaetze").mkdir(parents=True)
        (self.akte / "Klageschrift.txt").write_text("Klage des Mandanten gegen den Unfallgegner.", encoding="utf-8")
        (self.akte / "Schriftsaetze" / "Erwiderung.md").write_text("Erwiderung der Gegenseite.", encoding="utf-8")
        (self.akte / "beweisfoto.jpg").write_bytes(b"\xff\xd8\xff\x00egal")
        (self.akte / "unwichtig.zip").write_bytes(b"PK\x03\x04")  # kein Dokumenttyp
        # zweite Akte, anderer Anwalt/Jahr
        (self.wurzel / "Thunert" / "2025" / "X-109-2025 Miete Beispiel").mkdir(parents=True)
        self.a = WebDavJurNodesAdapter(self.wurzel, Freigabestelle(), schreibbar=True)

    def test_suche_liefert_aktenzeichen_und_bezeichnung(self):
        akten = {a.aktenzeichen: a for a in self.a.akten_suchen()}
        self.assertIn("X-107-2026", akten)
        self.assertEqual(akten["X-107-2026"].bezeichnung, "ohne Name wer gegen wen")
        self.assertEqual(akten["X-107-2026"].sachbearbeiter, "Dortschy")
        self.assertEqual(akten["X-109-2025"].bezeichnung, "Miete Beispiel")
        self.assertEqual(akten["X-109-2025"].sachbearbeiter, "Thunert")

    def test_ohne_kennung_ist_die_akte_laufend(self):
        """In jurnodes wird von Hand archiviert; ohne Kennung ist nichts archiviert."""
        for akte in self.a.akten_suchen():
            self.assertEqual(akte.status, "laufend")
        self.assertEqual(
            Gedaechtnisdienst._aufbewahrungsgrund(self.a.akte("X-107-2026").status),
            "laufende_mandatsbearbeitung",
        )

    def test_ohne_konvention_bleibt_der_status_unbekannt(self):
        """Ist keine Kennung eingestellt, darf kein Status behauptet werden.

        „unbekannt" führt zum Aufbewahrungsgrund „nicht löschen"; die Akte
        bleibt für die Admin-Übersicht als ungeklärt erkennbar.
        """
        ohne = WebDavJurNodesAdapter(self.wurzel, Freigabestelle(), archiv_kennung="")
        self.assertEqual(ohne.akte("X-107-2026").status, "unbekannt")
        self.assertEqual(
            Gedaechtnisdienst._aufbewahrungsgrund(ohne.akte("X-107-2026").status),
            "status_ungeklaert_nicht_loeschen",
        )

    def test_suche_filtert(self):
        self.assertEqual([a.aktenzeichen for a in self.a.akten_suchen("miete")], ["X-109-2025"])
        self.assertEqual([a.aktenzeichen for a in self.a.akten_suchen("dortschy")], ["X-107-2026"])

    def test_dokumente_aus_akte_und_unterordner_ohne_fremdtypen(self):
        dok = {d.id: d for d in self.a.dokumente("X-107-2026")}
        self.assertIn("Klageschrift.txt", dok)
        self.assertIn("Schriftsaetze/Erwiderung.md", dok)
        self.assertIn("beweisfoto.jpg", dok)
        self.assertNotIn("unwichtig.zip", dok)  # kein Dokumenttyp
        self.assertEqual(dok["Schriftsaetze/Erwiderung.md"].kategorie, "Schriftsaetze")

    def test_dokument_laden_liest_bytes(self):
        dokument, daten = self.a.dokument_laden("X-107-2026", "Klageschrift.txt")
        self.assertEqual(dokument.titel, "Klageschrift")
        self.assertIn("Unfallgegner", daten.decode("utf-8"))

    def test_unbekannte_akte_und_dokument(self):
        with self.assertRaises(AkteNichtGefunden):
            self.a.akte("X-999-2099")
        with self.assertRaises(DokumentNichtGefunden):
            self.a.dokument_laden("X-107-2026", "../../../etc/passwd")

    def test_vermerke_sind_kein_aktenmaterial(self):
        (self.akte / "Vermerke").mkdir()
        (self.akte / "Vermerke" / "alt.md").write_text("früherer Vermerk", encoding="utf-8")
        ids = [d.id for d in self.a.dokumente("X-107-2026")]
        self.assertNotIn("Vermerke/alt.md", ids)


class ArchivierteAkten(unittest.TestCase):
    """In jurnodes wird die Akte von Hand archiviert; die Kennung steht im Ordnernamen."""

    def _adapter(self, *ordnernamen: str, kennung: str = "archiviert"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        wurzel = Path(tmp.name)
        for name in ordnernamen:
            (wurzel / "Dortschy" / "2026" / name).mkdir(parents=True)
        return WebDavJurNodesAdapter(wurzel, Freigabestelle(), archiv_kennung=kennung)

    def test_kennung_hinten_setzt_status_und_faellt_aus_der_bezeichnung(self):
        a = self._adapter("X-107-2026 Testmann gegen Musterhaft archiviert")
        akte = a.akte("X-107-2026")
        self.assertEqual(akte.status, "archiviert")
        self.assertEqual(akte.bezeichnung, "Testmann gegen Musterhaft")

    def test_kennung_vorn_wird_nicht_als_aktenzeichen_gelesen(self):
        a = self._adapter("archiviert X-107-2026 Testmann gegen Musterhaft")
        akte = a.akte("X-107-2026")
        self.assertEqual(akte.aktenzeichen, "X-107-2026")
        self.assertEqual(akte.status, "archiviert")
        self.assertEqual(akte.bezeichnung, "Testmann gegen Musterhaft")

    def test_kennung_in_klammern_und_gross_geschrieben(self):
        a = self._adapter("X-107-2026 Meier (ARCHIVIERT) gegen Musterhaft")
        akte = a.akte("X-107-2026")
        self.assertEqual(akte.status, "archiviert")
        self.assertEqual(akte.bezeichnung, "Testmann gegen Musterhaft")

    def test_teilwort_ist_keine_kennung(self):
        """„Archivierungsstreit" ist ein Aktenname, kein Status."""
        a = self._adapter("X-107-2026 Streit um Archivierungskosten")
        self.assertEqual(a.akte("X-107-2026").status, "laufend")

    def test_archivierte_akte_verlangt_abschlusspruefung_statt_loeschung(self):
        a = self._adapter("X-107-2026 Meier archiviert")
        self.assertEqual(
            Gedaechtnisdienst._aufbewahrungsgrund(a.akte("X-107-2026").status),
            "abschlusspruefung_erforderlich",
        )

    def test_suche_findet_archivierte_akten(self):
        a = self._adapter("D-1-2026 Meier archiviert", "D-2-2026 Schulze")
        self.assertEqual([x.aktenzeichen for x in a.akten_suchen("archiviert")], ["D-1-2026"])


class WebDavImApp(unittest.TestCase):
    """Der Adapter durch die ganze Anwendung: Liste mit Namen, laden, fragen."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        wurzel = Path(self._tmp.name)
        akte = wurzel / "Dortschy" / "2026" / "X-107-2026 Testmann gegen Musterhaft"
        akte.mkdir(parents=True)
        (akte / "Klageschrift.txt").write_text(
            "Der Mandant Testmann macht Schmerzensgeld geltend. Der Unfall war am 13.03.2026.", encoding="utf-8")
        fs = Freigabestelle()
        self.d = dienste(freigabestelle=fs, adapter=WebDavJurNodesAdapter(wurzel, fs, schreibbar=True))
        self.c = client(self.d, "ra-weber")

    def test_aktenliste_zeigt_namen(self):
        akten = self.c.get("/api/akten").json()
        self.assertEqual(len(akten), 1)
        self.assertEqual(akten[0]["aktenzeichen"], "X-107-2026")
        self.assertEqual(akten[0]["bezeichnung"], "Testmann gegen Musterhaft")
        self.assertEqual(akten[0]["sachbearbeiter"], "Dortschy")

    def test_sitzung_dokumente_und_frage(self):
        sid = self.c.post("/api/sitzungen", json={"akte_id": "X-107-2026"}).json()["sitzung"]["id"]
        # Dokumentliste aus dem Ordner
        sitzung = self.c.get(f"/api/sitzungen/{sid}").json()
        dok_ids = [g["dokument_id"] for g in sitzung["sitzung"].get("geladen", [])]
        self.assertEqual(dok_ids, [])  # noch nichts geladen
        r = self.c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["Klageschrift.txt"]})
        self.assertEqual(r.status_code, 200)
        passagen = self.c.get(f"/api/sitzungen/{sid}/passagen").json()["passagen"]
        self.assertTrue(any("Testmann" in p["text"] for p in passagen))
        antwort = self.c.post(f"/api/sitzungen/{sid}/frage", json={"frage": "Was macht der Mandant geltend?"}).json()
        self.assertTrue(antwort["quellen"])


if __name__ == "__main__":
    unittest.main()
