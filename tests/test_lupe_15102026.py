"""Die Lupe – in den Dokumenten und im Chat.

Aus der Kanzlei am 15.10.2026: „Im Text Dokumente suchen genügt eine Lupe. Die
Lupe hätte übrigens auch gerne für den Chat."

Zwei Dinge in einem Satz.

**Das erste** ist eine Wegnahme. Der Platzhalter „Im Text dieser Dokumente
suchen – z. B. Antrag" nahm die ganze Breite des Feldes und war bei
vierhundert Pixeln Spalte trotzdem abgeschnitten. Was er sagte, sagt das
Zeichen in einem Fünftel des Platzes. Der Satz ist nicht verschwunden — er
steht als ``title`` am Feld und als ``aria-label`` darin.

**Das zweite** ist eine Zugabe. Seit dem 13.10.2026 stehen im Chat *alle*
früheren Fragen und nicht mehr die letzten fünf („Der Chat steht im
Vordergrund"). Damit ist er zurückverfolgbar — aber hundert Fragen
durchzublättern ist kein Wiederfinden.

Beide Suchen kosten nichts: Gesucht wird in dem, was ohnehin schon da ist. Es
geht keine Anfrage hinaus, kein Modell wird gefragt, und nichts vom Gesuchten
verlässt den Rechner.
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


class DieLupeImDokumentfeld(_Quelle):
    """„Im Text Dokumente suchen genügt eine Lupe."""

    def test_der_lange_platzhalter_ist_weg(self):
        """Er nahm die Breite des Feldes und war trotzdem abgeschnitten."""
        self.assertNotIn('placeholder="Im Text dieser Dokumente suchen', self.html)

    def test_das_zeichen_steht_an_seiner_stelle(self):
        feld = self.html[self.html.index('id="dok-suche"') - 600:self.html.index('id="dok-suche"')]
        self.assertIn('class="lupe"', feld)
        self.assertIn('class="suchfeld"', feld)

    def test_was_das_feld_sucht_steht_weiter_da(self):
        """Nur nicht mehr im Weg: am Feld zum Daraufhalten, darin zum Vorlesen."""
        self.assertIn('title="Im Text dieser Dokumente suchen', self.html)
        self.assertIn('aria-label="Im Text dieser Dokumente suchen"', self.html)

    def test_das_zeichen_faengt_keine_klicks_ab(self):
        """Wer auf die Lupe zielt, trifft das Feld."""
        regel = self.css[self.css.index(".suchfeld .lupe {"):]
        self.assertIn("pointer-events: none", regel[:regel.index("}")])

    def test_der_text_faengt_hinter_dem_zeichen_an(self):
        regel = self.css[self.css.index(".suchfeld .dok-suche {"):]
        self.assertIn("padding-left", regel[:regel.index("}")])


class DieLupeImChat(_Quelle):
    """„Die Lupe hätte ich übrigens auch gerne für den Chat."""

    def test_sie_steht_in_der_kopfzeile_des_chats(self):
        kopf = self.html[self.html.index('<h1 class="chat-titel">'):]
        kopf = kopf[:kopf.index("</div>")]
        self.assertIn('id="chat-lupe"', kopf)

    def test_die_ueberschrift_bleibt_eine_ueberschrift(self):
        """Aus der Kanzlei am 14.10.2026: „eine große Überschrift Chat ohne
        Auswahlfunktion." Die Lupe ist ein Knopf, kein Umschalter — und die
        Suchzeile klappt erst darunter auf, wenn sie gebraucht wird."""
        self.assertIn('<h1 class="chat-titel">Chat</h1>', self.html)
        zeile = self.html[self.html.index('id="chat-suche-zeile"'):]
        self.assertIn("hidden", zeile[:zeile.index(">")])

    def test_die_zeile_traegt_feld_zaehler_und_fluchtweg(self):
        zeile = self.html[self.html.index('id="chat-suche-zeile"'):]
        zeile = zeile[:zeile.index('<div id="thread"')]
        for stueck in ('id="chat-suche"', 'id="chat-treffer"', 'id="chat-suche-zu"'):
            self.assertIn(stueck, zeile)

    def test_sie_sucht_beim_tippen(self):
        self.assertRegex(self.js, r'\$\("chat-suche"\)[\s\S]{0,300}addEventListener\("input", chatSuchen\)')

    def test_esc_schliesst_sie(self):
        self.assertRegex(self.js, r'"Escape"[\s\S]{0,80}chatSucheZeigen\(false\)')

    def test_sie_steht_als_zweite_reihe_desselben_balkens(self):
        regel = self.css[self.css.index(".chat-suche-zeile {"):]
        self.assertIn("flex: 1 0 100%", regel[:regel.index("}")])


class SieKostetNichts(_Quelle):
    """Derselbe Grundsatz wie bei der Suche im Dokumenttext."""

    def test_kein_aufruf_im_suchen(self):
        suchen = self._funktion("chatSuchen")
        self.assertNotIn("api(", suchen)
        self.assertNotIn("fetch(", suchen)
        self.assertNotIn("await", suchen)

    def test_gesucht_wird_in_dem_was_schon_auf_dem_schirm_steht(self):
        self.assertIn('$("thread")', self._funktion("chatSuchen"))


class WieSieSucht(_Quelle):
    def test_jedes_wort_muss_vorkommen(self):
        """„versicherung frist" findet den Beitrag, in dem beides steht."""
        self.assertIn("begriffe.every((b) => text.includes(b))", self._funktion("chatSuchen"))

    def test_gross_und_kleinschreibung_ist_gleich(self):
        self.assertIn("toLowerCase()", self._funktion("chatSuchwoerter"))
        self.assertIn("toLowerCase()", self._funktion("chatSuchen"))

    def test_gefiltert_wird_in_beitraegen_nicht_in_karten(self):
        """Die Frage eröffnet, die Antwort darunter gehört dazu.

        Bliebe nur die Antwort stehen, läse der Bearbeiter eine Auskunft, ohne
        zu wissen, worauf sie antwortet — in einer Mandatsakte die gefährliche
        Hälfte."""
        suchen = self._funktion("chatSuchen")
        self.assertIn("beitraege", suchen)
        self.assertIn('el.classList.contains("user")', suchen)

    def test_kein_treffer_ist_eine_auskunft(self):
        """Ohne diese Zeile sähe „nichts gefunden" aus wie ein leerer Chat."""
        self.assertIn("kein Treffer in", self._funktion("chatSuchen"))
        self.assertIn("ohne-treffer", self._funktion("chatSuchen"))


class DieBelegeBleibenHeil(_Quelle):
    """Hervorgehoben wird in Textknoten — nie über den Inhalt hinweg."""

    def test_nicht_mit_innerhtml(self):
        for name in ("markenSetzen", "markenEntfernen"):
            self.assertNotIn("innerHTML", self._funktion(name))

    def test_nur_textknoten_werden_angefasst(self):
        setzen = self._funktion("markenSetzen")
        self.assertIn("NodeFilter.SHOW_TEXT", setzen)
        self.assertIn("createTreeWalker", setzen)

    def test_die_hervorhebung_laesst_sich_rueckstandslos_entfernen(self):
        entfernen = self._funktion("markenEntfernen")
        self.assertIn("mark.chat-treffer", entfernen)
        self.assertIn("normalize()", entfernen)


class KeineKarteBleibtVersteckt(_Quelle):
    """Ein halber Verlauf, dessen Grund nicht mehr zu sehen ist, sieht aus wie
    ein verlorener Verlauf."""

    def test_eine_neue_karte_beendet_die_suche(self):
        """Sonst fragt der Bearbeiter — und sieht nichts."""
        karte = self._funktion("threadKarte")
        self.assertIn('$("chat-suche")', karte)
        self.assertIn("chatSucheZeigen(false)", karte)

    def test_zuklappen_stellt_den_ganzen_verlauf_wieder_her(self):
        zeigen = self._funktion("chatSucheZeigen")
        self.assertIn('feld.value = ""', zeigen)
        self.assertIn("chatSuchen()", zeigen)

    def test_ein_neuer_verlauf_faengt_ohne_suchwort_an(self):
        self.assertIn("chatSucheZeigen(false)", self._funktion("threadWillkommen"))


if __name__ == "__main__":
    unittest.main()
