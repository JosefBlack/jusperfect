"""Suche im Text der Dokumente – ohne Aufruf, ohne Kosten.

Aus der Kanzlei am 13.10.2026: „Eine Suchfunktion in den Dokumenten wäre sehr
gut, da ich z. B. schnell Anträge finden muss."

Es gab schon ein Suchfeld — im Fenster „Auswahl". Das sucht über **Titel,
Datum, Ordner und Kategorie** und findet einen Antrag nur, wenn das Dokument
so heißt. Was fehlte, war die Suche **im Text**.

Sie kostet nichts: `passagenIndex` trägt den Text aller geladenen Dokumente
bereits im Programm. Es geht keine Anfrage hinaus, und kein Modell wird
gefragt — derselbe Grundsatz wie bei `services/fundstelle.py`: „Es fragt kein
Modell. Der Vergleich läuft im Programm, kostet nichts und ist
nachvollziehbar."
"""

from __future__ import annotations

import unittest
from pathlib import Path

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"


class _Quelle(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.js = (STATISCH / "app.js").read_text(encoding="utf-8")
        cls.html = (STATISCH / "index.html").read_text(encoding="utf-8")
        cls.css = (STATISCH / "styles.css").read_text(encoding="utf-8")

    def _funktion(self, name: str) -> str:
        teil = self.js[self.js.index(f"function {name}("):]
        return teil[:teil.index("\n}\n")]


class DasFeldIstDa(_Quelle):
    def test_es_steht_ueber_dem_text_und_nicht_in_der_kopfzeile(self):
        """In der Kopfzeile stehen schon vier Dinge."""
        self.assertIn('id="dok-suche"', self.html)
        self.assertLess(self.html.index('id="dok-suche"'), self.html.index('id="dok-text"'))

    def test_es_sagt_wonach_es_sucht(self):
        self.assertIn("Im Text dieser Dokumente suchen", self.html)

    def test_es_zeichnet_beim_tippen_neu(self):
        self.assertRegex(self.js, r'\$\("dok-suche"\)[\s\S]{0,200}addEventListener\("input"')


class SieKostetNichts(_Quelle):
    def test_kein_aufruf_im_zeichnen(self):
        zeigen = self._funktion("zeigeDokument")
        self.assertNotIn("api(", zeigen)
        self.assertNotIn("await", zeigen)

    def test_gesucht_wird_in_dem_was_schon_da_ist(self):
        self.assertIn("passagenIndex", self._funktion("zeigeDokument"))


class WieSieSucht(_Quelle):
    def test_jedes_wort_muss_vorkommen(self):
        """„antrag frist" findet die Passage, in der beides steht."""
        self.assertIn("begriffe.every((b) => klein.includes(b))",
                      self._funktion("zeigeDokument"))

    def test_gross_und_kleinschreibung_ist_gleich(self):
        self.assertIn("toLowerCase()", self._funktion("dokSuchwoerter"))
        self.assertIn("text.toLowerCase()", self._funktion("zeigeDokument"))

    def test_die_treffer_werden_hervorgehoben(self):
        self.assertIn("mitHervorhebung(satz, text, begriffe)", self._funktion("zeigeDokument"))
        self.assertIn(".passage .satz mark", self.css)


class DerAktentextWirdNichtZuHtml(_Quelle):
    """Ein Dokument, das wie HTML aussieht, darf nicht als HTML enden."""

    def test_die_hervorhebung_setzt_text_und_kein_markup(self):
        heben = self._funktion("mitHervorhebung")
        self.assertNotIn("innerHTML", heben)
        self.assertIn("createTextNode", heben)
        self.assertIn("m.textContent", heben)

    def test_nirgends_im_zeichnen_wird_html_gesetzt(self):
        self.assertNotIn("innerHTML", self._funktion("zeigeDokument"))


class KeinTrefferIstEineAuskunft(_Quelle):
    def test_die_zahl_steht_daneben(self):
        zeigen = self._funktion("zeigeDokument")
        self.assertIn("kein Treffer in", zeigen)
        self.assertIn("von ${durchsucht}", zeigen)

    def test_ohne_suchwort_steht_dort_nichts(self):
        """Eine Zahl an jedem Fenster wäre keine Auskunft."""
        self.assertIn('marke.textContent = !begriffe.length ? ""',
                      self._funktion("zeigeDokument"))

    def test_null_treffer_sieht_man_an(self):
        self.assertIn(".dok-treffer.ohne-treffer", self.css)


if __name__ == "__main__":
    unittest.main()
