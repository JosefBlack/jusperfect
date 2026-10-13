"""Ein Gedächtnis, das sich nicht einlesen lässt, hält die Akte nicht zu.

Aus der Kanzlei am 13.10.2026: „Akte öffnen nicht möglich Vorgang wurde
abgebrochen interner Fehler 2e2e3bd1."

Für das misslungene **Sichern** war die Lehre am 25.09.2026 gezogen – damals
riss ein fehlgeschlagenes Ablegen das ganze Öffnen mit, und seitdem kommt es
als Hinweis zurück (`Gedaechtnisdienst._nachtragen`). Für das **Lesen** war sie
nicht gezogen: Was dort unerwartet scheiterte, kam als Programmfehler heraus –
eine Vorgangsnummer ohne Satz, und die Akte blieb zu.

Diese Datei hält drei Dinge fest:

1. **Die Akte geht auf.** Die Dokumente stehen in jurnodes; das Gedächtnis ist
   eine Arbeitshilfe, keine Bedingung.
2. **Es wird nichts überschrieben.** Jeder schreibende Weg liest zuerst und
   bricht ab. Ein Stand, den wir nicht lesen konnten, ist der einzige, an dem
   sich noch feststellen lässt, was ihm fehlte.
3. **Der Weg hinaus steht im Satz** – „Gedächtnis verwerfen", dann „Akte
   einlesen". Das Verwerfen liest nicht, es löscht, und funktioniert deshalb
   auch hier.
"""

from __future__ import annotations

import tempfile
import unittest
from unittest import mock

from jusperfect.gedaechtnis.base import GedaechtnisFehler
from tests.hilfen import client, dienste, einstellungen

AKTE = "MV-2026-0007"


def _mit_gedaechtnis(tmp: str):
    e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp)
    d = dienste(einstellungen=e)
    c = client(d)
    sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
    c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-101"]})
    return d, c, sid


def _unlesbar(d):
    """Der Speicher liest nicht mehr - mit einer Ausnahme, die niemand kennt.

    Welche echte Gestalt ein unlesbares Gedächtnis hat, weiß hier niemand; der
    Fall aus der Kanzlei ist noch nicht gelesen. Die Zusage lautet auch nicht
    „dieser eine Fehler wird behandelt", sondern „was beim Lesen unerwartet
    scheitert, hält die Akte nicht zu".
    """
    return mock.patch.object(type(d.gedaechtnis._speicher), "lesen",
                             side_effect=ValueError("erfundenes Unheil"))


class DieAkteGehtAuf(unittest.TestCase):
    def test_eine_neue_sitzung_laesst_sich_eroeffnen(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, c, sid = _mit_gedaechtnis(tmp)
            with _unlesbar(d):
                antwort = c.post("/api/sitzungen", json={"akte_id": AKTE})
            self.assertEqual(antwort.status_code, 201, antwort.text)

    def test_die_dokumente_der_akte_stehen_vollstaendig_da(self):
        """Sie kommen aus jur|nodes und haben mit dem Gedächtnis nichts zu tun."""
        with tempfile.TemporaryDirectory() as tmp:
            d, c, sid = _mit_gedaechtnis(tmp)
            ohne = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["dokumente"]
            with _unlesbar(d):
                mit = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()
            self.assertEqual(len(mit["dokumente"]), len(ohne))

    def test_der_hinweis_nennt_den_weg_hinaus(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, c, sid = _mit_gedaechtnis(tmp)
            with _unlesbar(d):
                neu = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()
            hinweise = " ".join(neu["sitzung"]["hinweise"])
            self.assertIn("Gedächtnis verwerfen", hinweise)
            self.assertIn("Akte einlesen", hinweise)
            self.assertIn("jurnodes ist", hinweise)

    def test_der_hinweis_nennt_die_stelle_und_keinen_wortlaut(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, c, sid = _mit_gedaechtnis(tmp)
            with _unlesbar(d):
                neu = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()
            hinweise = " ".join(neu["sitzung"]["hinweise"])
            self.assertIn("ValueError", hinweise)
            self.assertNotIn("erfundenes Unheil", hinweise,
                             "Der Wortlaut einer Ausnahme kann Akteninhalt tragen.")
            self.assertNotIn(AKTE, hinweise)

    def test_die_uebersicht_kommt_als_nicht_vorhanden_mit_grund(self):
        """Ohne sie zeichnet die Oberfläche kein einziges Fenster."""
        with tempfile.TemporaryDirectory() as tmp:
            d, c, sid = _mit_gedaechtnis(tmp)
            with _unlesbar(d):
                neu = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()
            self.assertFalse(neu["gedaechtnis"]["vorhanden"])
            self.assertIn("unlesbar", neu["gedaechtnis"])
            self.assertIn("ValueError", neu["gedaechtnis"]["unlesbar"])


class EsWirdNichtsUeberschrieben(unittest.TestCase):
    """Der Stand, den wir nicht lesen konnten, ist der letzte Zeuge."""

    def test_sichern_legt_nichts_ab(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, c, sid = _mit_gedaechtnis(tmp)
            with _unlesbar(d), \
                 mock.patch.object(type(d.gedaechtnis._speicher), "ablegen") as ablegen:
                antwort = c.post(f"/api/sitzungen/{sid}/gedaechtnis/sichern")
            self.assertEqual(antwort.status_code, 422, antwort.text)
            ablegen.assert_not_called()

    def test_einlesen_legt_nichts_ab(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, c, sid = _mit_gedaechtnis(tmp)
            with _unlesbar(d), \
                 mock.patch.object(type(d.gedaechtnis._speicher), "ablegen") as ablegen:
                antwort = c.post(f"/api/sitzungen/{sid}/gedaechtnis/einlesen")
            self.assertEqual(antwort.status_code, 422, antwort.text)
            ablegen.assert_not_called()

    def test_die_antwort_nennt_keinen_internen_fehler(self):
        """Das war der ganze Mangel: ein Fehler ohne Satz."""
        with tempfile.TemporaryDirectory() as tmp:
            d, c, sid = _mit_gedaechtnis(tmp)
            with _unlesbar(d):
                antwort = c.post(f"/api/sitzungen/{sid}/gedaechtnis/sichern")
            self.assertNotIn("Vorgangsnummer", antwort.text)
            self.assertIn("Gedächtnis verwerfen", antwort.json()["fehler"])


class DasVerwerfenGehtTrotzdem(unittest.TestCase):
    """Es liest nicht, es löscht - deshalb ist es hier der einzige Weg."""

    def test_der_loeschweg_antwortet(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, c, sid = _mit_gedaechtnis(tmp)
            with _unlesbar(d):
                antwort = c.delete(f"/api/akten/{AKTE}/gedaechtnis")
            self.assertEqual(antwort.status_code, 204, antwort.text)

    def test_danach_ist_die_akte_wieder_ganz_normal(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, c, sid = _mit_gedaechtnis(tmp)
            c.delete(f"/api/akten/{AKTE}/gedaechtnis")
            neu = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()
            self.assertEqual(neu["sitzung"]["hinweise"], [])
            self.assertFalse(neu["gedaechtnis"]["vorhanden"])
            self.assertNotIn("unlesbar", neu["gedaechtnis"])


class EinFremdesGedaechtnisBleibtEineSperre(unittest.TestCase):
    """Nicht alles, was hier auffällt, ist ein Fall für „weiter trotzdem"."""

    def test_ein_gedaechtnis_einer_anderen_akte_haelt_die_akte_zu(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, c, sid = _mit_gedaechtnis(tmp)
            fremd = d.gedaechtnis.lesen(AKTE)
            fremd.akte_id = "eine-andere-akte"
            with mock.patch.object(type(d.gedaechtnis._speicher), "lesen",
                                   return_value=fremd):
                antwort = c.post("/api/sitzungen", json={"akte_id": AKTE})
            self.assertEqual(antwort.status_code, 422)
            self.assertIn("anderen Akte", antwort.json()["fehler"])


if __name__ == "__main__":
    unittest.main()
