"""Die Eingabetaste fragt – Umschalt+Eingabe macht eine neue Zeile.

Aus der Kanzlei am 13.10.2026: „Fragen mit Returntaste auslösen."

Bisher brauchte es **Strg+Eingabe**. Das ist eine Abkürzung, die man kennen
muss; in einem Chat erwartet jeder, dass die Eingabetaste abschickt. Und der
Chat steht hier im Vordergrund — das ist der Satz desselben Tages, an dem sich
die Oberfläche messen lassen soll.
"""

from __future__ import annotations

import unittest
from pathlib import Path

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"


class DieTasteFragt(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        js = (STATISCH / "app.js").read_text(encoding="utf-8")
        anfang = js.index('$("frage").addEventListener("keydown"')
        cls.block = js[anfang:js.index("});", anfang)]
        cls.html = (STATISCH / "index.html").read_text(encoding="utf-8")

    def test_eine_blanke_eingabetaste_schickt_ab(self):
        self.assertIn("frageStellen", self.block)
        self.assertNotIn("ctrlKey || ev.metaKey) { ev.preventDefault()", self.block)

    def test_umschalt_eingabe_macht_eine_neue_zeile(self):
        self.assertIn("if (ev.shiftKey) return;", self.block)

    def test_sie_unterbricht_keine_laufende_frage(self):
        """Zwei Fragen zugleich wären zwei Modellaufrufe für eine Absicht."""
        self.assertIn('$("senden").disabled', self.block)

    def test_sie_stoert_keine_umlauteingabe(self):
        """`isComposing` – wer Zeichen zusammensetzt, schickt nicht ab."""
        self.assertIn("ev.isComposing", self.block)

    def test_das_eingabefeld_sagt_es_von_selbst(self):
        """Eine Taste, die man kennen muss, ist keine Hilfe."""
        self.assertIn("Eingabetaste fragt", self.html)
        self.assertIn("Umschalt+Eingabe", self.html)

    def test_der_knopf_bleibt_daneben_stehen(self):
        """Nicht jeder tippt; der Weg mit der Maus bleibt."""
        self.assertIn('id="senden"', self.html)


if __name__ == "__main__":
    unittest.main()
