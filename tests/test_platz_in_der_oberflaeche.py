"""Fünf Wünsche aus der Kanzlei am 14.10.2026 – alle vom selben Übel.

    „Promptbibliothek unten versperrt den Chat. Die Schrift im Chat und bei
    den Dokumenten verkleinern, was die Übersicht verstärkt. Bekommen wir
    links einen einheitlichen Balken hin. Zweimal Gedächtnis? Auch die obere
    Zeile jusperfect nimmt viel Platz und sollte ausklappbar sein, wenn man
    auf jusperfect drückt."

Fünf Sätze, ein Befund: Das Programm hat über die Wochen Leisten, Balken und
Knöpfe angesetzt, und jedes Stück war für sich begründet. Zusammen nehmen sie
der Arbeit den Platz.

Was dagegen gebaut ist, folgt einer Regel: **Was selten gebraucht wird, klappt
zu; was dauernd gelesen wird, wird kleiner; und was gleich heißt, heißt nicht
mehr gleich.**
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
HTML = (WURZEL / "jusperfect" / "static" / "index.html").read_text(encoding="utf-8")
CSS = (WURZEL / "jusperfect" / "static" / "styles.css").read_text(encoding="utf-8")
JS = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")


def _regel(wahl: str) -> str:
    treffer = re.search(rf"^{re.escape(wahl)} \{{([^}}]*)\}}", CSS, re.M)
    assert treffer is not None, f"Regel für {wahl} fehlt."
    return treffer.group(1)


class DieBibliothekVersperrtNichtsMehr(unittest.TestCase):
    """„Promptbibliothek unten versperrt den Chat."

    Vier Gruppen und neununddreißig Prompts standen dauerhaft über dem
    Eingabefeld, auch wenn gerade nur gefragt wurde.
    """

    def test_sie_ist_eine_lade(self):
        self.assertIn('<details id="bibliothek"', HTML)
        self.assertIn('<summary class="bib-kopf">', HTML)

    def test_zugeklappt_ist_die_voreinstellung(self):
        """Der Chat steht im Vordergrund; die Bibliothek ist Werkzeug."""
        block = re.search(r'<details id="bibliothek"[^>]*>', HTML).group(0)
        self.assertNotIn(" open", block)
        self.assertIn('localStorage.getItem("jusperfect.bib.offen") === "ja"', JS)

    def test_die_anzahl_steht_an_der_ueberschrift(self):
        """Sonst müsste man aufklappen, um zu sehen, ob sich das lohnt."""
        self.assertIn('id="bib-anzahl"', HTML)
        self.assertIn('$("bib-anzahl").textContent', JS)

    def test_rechtsgebiet_und_neu_stehen_innen(self):
        """In einer summary würfe ein Klick auf das Auswahlfeld die Lade zu."""
        kopf = HTML[HTML.index('<summary class="bib-kopf">'):HTML.index("</summary>")]
        self.assertNotIn('id="bib-gebietswahl"', kopf)
        self.assertNotIn('id="bib-neu"', kopf)
        self.assertIn('id="bib-gebietswahl"', HTML)

    def test_ein_ausgefallener_speicher_haelt_nichts_auf(self):
        block = JS[JS.index("function bibLadeHerstellen"):JS.index("function bibZu()")]
        self.assertEqual(block.count("catch"), 2, block)


class DieSchriftWirdKleiner(unittest.TestCase):
    """„Die Schrift im Chat und bei den Dokumenten verkleinern, was die
    Übersicht verstärkt."

    Eine Akte liest man anders als eine Bedienoberfläche: Dort zählt, wie
    viel auf einmal im Blick ist.
    """

    def test_der_chat_ist_kleiner_als_die_oberflaeche(self):
        grund = float(re.search(r"font: (\d+(?:\.\d+)?)px/", _regel("body")).group(1))
        chat = float(re.search(r"font-size: (\d+(?:\.\d+)?)px", _regel(".karte-c .inhalt")).group(1))
        self.assertLess(chat, grund, (chat, grund))

    def test_die_dokumente_sind_kleiner_als_die_oberflaeche(self):
        grund = float(re.search(r"font: (\d+(?:\.\d+)?)px/", _regel("body")).group(1))
        dok = float(re.search(r"font-size: (\d+(?:\.\d+)?)px", _regel(".dok-text")).group(1))
        self.assertLess(dok, grund, (dok, grund))

    def test_beide_bleiben_lesbar(self):
        """Kleiner heisst nicht klein: Unter dreizehn Punkt liest in einer
        Kanzlei niemand mehr eine Akte."""
        for wahl in (".karte-c .inhalt", ".dok-text"):
            with self.subTest(wahl=wahl):
                groesse = float(re.search(r"font-size: (\d+(?:\.\d+)?)px", _regel(wahl)).group(1))
                self.assertGreaterEqual(groesse, 13.0)

    def test_der_zeilenabstand_geht_mit(self):
        """Kleinere Schrift im alten Abstand sieht verloren aus."""
        for wahl in (".karte-c .inhalt", ".dok-text"):
            with self.subTest(wahl=wahl):
                self.assertIn("line-height", _regel(wahl))


class LinksIstEinBalken(unittest.TestCase):
    """„Bekommen wir links einen einheitlichen Balken hin."

    Die Suchzeile hatte eine eigene Hintergrundfarbe und eine eigene
    Trennlinie und sah aus wie ein zweiter Kopf.
    """

    def test_die_suchzeile_steht_im_kopf(self):
        kopf = HTML[HTML.index('<div class="spalte-kopf dokument-kopf">'):]
        kopf = kopf[:kopf.index('<div id="dok-text"')]
        self.assertIn('class="dok-suche-zeile"', kopf)
        self.assertEqual(kopf.count("</div>"), kopf.count("<div"), kopf[-400:])

    def test_sie_hat_keinen_eigenen_rahmen_mehr(self):
        regel = _regel(".dok-suche-zeile")
        self.assertNotIn("border-bottom", regel)
        self.assertNotIn("background", regel)

    def test_sie_bekommt_eine_eigene_reihe(self):
        """Nebeneinander waere der Balken zu eng - die Spalte ist schmal."""
        self.assertIn("flex: 1 0 100%", _regel(".dok-suche-zeile"))


class NichtsHeisstZweimalGleich(unittest.TestCase):
    """„Zweimal Gedächtnis?"

    Derselbe Fehler wie bei „Entwurf" und „Vorschau": Ein Knopf schreibt den
    jetzigen Stand ins Gedächtnis, der andere klappt das Fenster auf, das
    zeigt, was darin liegt.
    """

    def _beschriftungen(self) -> list[str]:
        return [b.strip() for b in re.findall(
            r'data-(?:aktion|fenster)="[a-z]+"[^>]*>([^<]+)</button>', HTML)]

    def test_keine_zwei_knoepfe_heissen_gleich(self):
        namen = self._beschriftungen()
        doppelt = {n for n in namen if namen.count(n) > 1}
        self.assertEqual(doppelt, set(), doppelt)

    def test_der_knopf_sagt_was_er_tut(self):
        """Er schreibt den jetzigen Stand ins Gedächtnis."""
        self.assertIn('data-aktion="gedaechtnis" class="mini">Gedächtnis sichern</button>', HTML)

    def test_das_fenster_heisst_weiter_gedaechtnis(self):
        """Es zeigt, was darin liegt - das ist der Name der Sache."""
        self.assertRegex(HTML, r'data-fenster="gedaechtnis"[^>]*>Gedächtnis</button>')


class DieKopfzeileKlapptZu(unittest.TestCase):
    """„Auch die obere Zeile jusperfect nimmt viel Platz und sollte
    ausklappbar sein, wenn man auf jusperfect drückt."
    """

    def test_die_marke_ist_der_schalter(self):
        self.assertIn('id="kopf-schalter" class="marke"', HTML)
        self.assertIn('aria-expanded="true"', HTML[HTML.index('id="kopf-schalter"'):][:300])

    def test_schmal_bleibt_die_akte_stehen(self):
        """Weg sind Verbrauch, Verbindungsstand und Benutzer - drei Angaben,
        die man einmal am Tag braucht und den ganzen Tag ansieht."""
        self.assertIn("display: none", _regel(".kopf.schmal .kopf-rechts"))
        self.assertNotIn(".kopf.schmal .kopf-mitte { display: none", CSS)

    def test_schmal_ist_wirklich_schmaler(self):
        ganz = re.search(r"padding: (\d+)px", _regel(".kopf")).group(1)
        schmal = re.search(r"padding: (\d+)px", _regel(".kopf.schmal")).group(1)
        self.assertLess(int(schmal), int(ganz))

    def test_der_stand_ueberlebt_das_neuladen(self):
        self.assertIn('localStorage.getItem("jusperfect.kopf")', JS)
        block = JS[JS.index("function kopfzeileHerstellen"):]
        self.assertIn("catch", block[:1600])


if __name__ == "__main__":
    unittest.main()
