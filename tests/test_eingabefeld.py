"""Die Eingabe liegt über dem Verlauf, nicht darunter.

Aus der Kanzlei: „kein Chat wie bei WhatsApp, sondern ein vorgelegtes
Eingabefenster wie bei Claude oder ChatGPT" – der Verlauf soll hinter der
Eingabe durchscrollen.

Das ist Gestaltung und deshalb nur begrenzt prüfbar. Was hier steht, sind die
drei Voraussetzungen, ohne die es nicht funktioniert und deren Verlust beim
nächsten Umbau niemandem auffiele.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
CSS = (WURZEL / "jusperfect" / "static" / "styles.css").read_text(encoding="utf-8")
HTML = (WURZEL / "jusperfect" / "static" / "index.html").read_text(encoding="utf-8")


class Eingabefeld(unittest.TestCase):
    def test_eingabe_schwebt_ueber_dem_verlauf(self):
        block = re.search(r"\.eingabe \{([^}]*)\}", CSS)
        self.assertIsNotNone(block, "Regel für .eingabe fehlt.")
        self.assertIn("position: absolute", block.group(1))
        self.assertIn("bottom: 0", block.group(1))

    def test_die_spalte_ist_bezugsrahmen(self):
        """Ohne position: relative bezöge sich die Eingabe aufs ganze Fenster."""
        self.assertRegex(CSS, r"\.spalte\.cowork \{[^}]*position: relative")

    def test_der_verlauf_haelt_unten_platz_frei(self):
        """Sonst verschwände die letzte Karte hinter der Eingabe."""
        block = re.search(r"\n\.thread \{([^}]*)\}", CSS)
        self.assertIsNotNone(block)
        polster = re.search(r"padding: [\d.]+px [\d.]+px (\d+)px", block.group(1))
        self.assertIsNotNone(polster, "Der Verlauf braucht ein unteres Polster.")
        self.assertGreaterEqual(int(polster.group(1)), 90)

    def test_karten_schrumpfen_nicht(self):
        """Der Fehler, der beim Umbau sichtbar wurde – und leicht zurückkehrt.

        ``.thread`` ist eine Flexspalte. Ohne ``flex: none`` schrumpfen die
        Karten, sobald der Inhalt höher wird als das Fenster; weil sie
        ``overflow: hidden`` tragen, wird der Text dann stillschweigend
        abgeschnitten, statt dass der Verlauf scrollt.
        """
        block = re.search(r"\.karte-c \{([^}]*)\}", CSS)
        self.assertIsNotNone(block)
        self.assertIn("flex: none", block.group(1))

    def test_der_ausblendverlauf_faengt_keine_klicks_ab(self):
        """Belege unter dem Ausblenden müssen anklickbar bleiben."""
        block = re.search(r"\.eingabe \{([^}]*)\}", CSS)
        self.assertIn("pointer-events: none", block.group(1))
        self.assertRegex(CSS, r"\.eingabe > \* \{[^}]*pointer-events: auto")

    def test_gestapelt_klebt_die_eingabe_statt_zu_schweben(self):
        """Und die Regel muss NACH der Grundregel stehen, sonst wirkt sie nicht."""
        grund = CSS.index(".eingabe { position: absolute")
        eng = [m.start() for m in re.finditer(r"@media \(max-width: 760px\)", CSS)
               if "position: sticky" in CSS[m.start():m.start() + 400]]
        self.assertTrue(eng, "Kein Abschnitt für schmale Fenster gefunden.")
        self.assertGreater(eng[-1], grund,
                           "Bei gleicher Spezifität gewinnt die spätere Regel.")

    def test_die_eingabe_ist_ein_eigener_block_im_html(self):
        self.assertIn('<div class="eingabe">', HTML)
        # Frageform und Kostenschätzung gehören mit hinein, sonst schwebt nur
        # die Hälfte.
        block = HTML[HTML.index('<div class="eingabe">'):]
        block = block[:block.index("</div>")]
        self.assertIn('id="frage-form"', block)
        self.assertIn('id="schaetzung"', block)


if __name__ == "__main__":
    unittest.main()
