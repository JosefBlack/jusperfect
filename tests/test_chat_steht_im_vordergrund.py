"""Der Chat ist die Hauptsache – und er zeigt den ganzen Verlauf.

Aus der Kanzlei am 13.10.2026:

    5 Fragen im Chat sind zu wenig – eigentlich sollte der Chat scrollbar und
    zurückverfolgbar sein. Der Chat steht im Vordergrund. Der Rest ist nur
    Hilfsmittel.

Nachgemessen, bevor etwas geändert wurde:

| Was | Wo | Wie viel |
|---|---|---|
| Fragen samt Antworten und Fundstellen | im Gedächtnis, dauerhaft | die letzten **100** |
| Davon im Chat wieder sichtbar | `gedaechtnisImThreadZeigen` | **5** |
| Zusammenhang für Rückfragen | `dialog_max_runden` | 6 Runden |

**Abgeschnitten wurde also beim Anzeigen, nicht beim Speichern.** Der Verlauf
war da und nicht zu sehen. Die Fünf waren eine Vorsicht ohne Anlass: Die
Spalte scrollt längst, und die Fundstellen in den alten Antworten sind
anklickbar wie in den neuen – beides steht hier als Prüfung.
"""

from __future__ import annotations

import unittest
from pathlib import Path

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"


class DerGanzeVerlaufStehtDa(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        js = (STATISCH / "app.js").read_text(encoding="utf-8")
        teil = js[js.index("function gedaechtnisImThreadZeigen"):]
        cls.funktion = teil[:teil.index("\n}\n")]
        cls.js = js

    def test_es_wird_nicht_mehr_auf_fuenf_gekuerzt(self):
        self.assertNotIn("slice(-5)", self.funktion)

    def test_alle_gespeicherten_fragen_werden_gezeichnet(self):
        self.assertIn("const frueher = g.fragen_antworten || []", self.funktion)
        self.assertIn("for (const qa of frueher)", self.funktion)

    def test_die_alten_antworten_gehen_durch_denselben_satzbau(self):
        """`antworttext` macht die Fundstellen anklickbar - auch im Alten."""
        self.assertIn("antworttext(antwortText, qa.antwort)", self.funktion)

    def test_eine_linie_trennt_frueher_von_heute(self):
        self.assertIn("thread-trennung", self.funktion)
        css = (STATISCH / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".thread-trennung", css)

    def test_der_blick_faellt_auf_das_juengste(self):
        """Bei hundert Fragen stünde sonst die älteste im Bild."""
        self.assertIn("t.scrollTop = t.scrollHeight", self.funktion)

    def test_die_spalte_scrollt_ueberhaupt(self):
        """Ohne das wäre „alle anzeigen" keine Verbesserung, sondern ein Verlust."""
        css = (STATISCH / "styles.css").read_text(encoding="utf-8")
        thread = [z for z in css.splitlines() if z.startswith(".thread {")]
        self.assertTrue(thread, css[:200])
        self.assertIn("overflow: auto", thread[0])

    def test_die_karten_schrumpfen_nicht_statt_zu_scrollen(self):
        """Genau daran war es am 29.09.2026 schon einmal gescheitert."""
        css = (STATISCH / "styles.css").read_text(encoding="utf-8")
        karte = [z for z in css.splitlines() if z.startswith(".karte-c {")]
        self.assertTrue(karte)
        self.assertIn("flex: none", karte[0])


if __name__ == "__main__":
    unittest.main()
