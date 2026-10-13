"""„Es wäre gut, wenn angezeigt wird, dass das Programm arbeitet."

Aus der Kanzlei am 13.10.2026: „Bei Auswahl dauert es lange, bis eingelesen
wird. Es wäre gut, wenn hier angezeigt wird, dass das Programm arbeitet."

Im Fenster **Auswahl** stand hinter „Ausgewählte aufnehmen" **ein** Aufruf
über alle angehakten Dokumente. Der holt jede Datei, schickt jeden Scan durch
die Texterkennung und schreibt alles ins Gedächtnis — bei einer ganzen Akte
Minuten. Auf dem Schirm geschah nichts: Der Dialog war zu, und es gab keinen
Knopf mehr, an dem ein Wartekreis hätte hängen können.

**Der Weg dafür war seit dem 29.09.2026 da.** `dokumenteInPortionenLesen`
liest Portion für Portion, mit Balken, Zeitschätzung und „Anhalten". Das
Dokumentfenster nimmt ihn; dieses Fenster tat es nicht.

> Eine zweite Stelle, die dasselbe tut, hat die Verbesserung der ersten nicht.

Diese Datei hält fest, dass **beide** Wege denselben nehmen — und dass die
Meldung danach zählt, was wirklich ankam, und nicht, was angehakt war.
"""

from __future__ import annotations

import unittest
from pathlib import Path

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"


class BeideFensterNehmenDenselbenWeg(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.js = (STATISCH / "app.js").read_text(encoding="utf-8")

    def _funktion(self, name: str) -> str:
        teil = self.js[self.js.index(f"async function {name}("):]
        return teil[:teil.index("\n}\n")]

    def test_das_gedaechtnisfenster_liest_in_portionen(self):
        self.assertIn("dokumenteInPortionenLesen(ids)",
                      self._funktion("gedaechtnisAufnehmen"))

    def test_das_dokumentfenster_auch_weiterhin(self):
        self.assertIn("dokumenteInPortionenLesen(dazu)",
                      self._funktion("explorerUebernehmen"))

    def test_keines_der_beiden_schickt_noch_alles_in_einem_zug(self):
        """Der eine Aufruf über alles war der ganze Fehler."""
        for name in ("gedaechtnisAufnehmen", "explorerUebernehmen"):
            with self.subTest(funktion=name):
                self.assertNotIn("dokument_ids: ids", self._funktion(name))

    def test_der_balken_gehoert_zum_portionenlesen(self):
        """Ohne ihn wäre „in Portionen" nur innen anders und außen gleich."""
        lesen = self._funktion("dokumenteInPortionenLesen")
        self.assertIn("lesefortschritt(", lesen)
        self.assertIn("lese-anhalten", lesen)

    def test_fuer_ein_zwei_dokumente_blitzt_er_nicht_auf(self):
        """Da lohnt der Aufbau nicht - dann genügt ein Satz."""
        lesen = self._funktion("dokumenteInPortionenLesen")
        self.assertIn("gesamt <= 2", lesen)
        self.assertIn("laeuft(", lesen)


class DieMeldungZaehltWasAnkam(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        js = (STATISCH / "app.js").read_text(encoding="utf-8")
        teil = js[js.index("async function gedaechtnisAufnehmen("):]
        cls.funktion = teil[:teil.index("\n}\n")]

    def test_sie_vergleicht_vorher_und_nachher(self):
        self.assertIn("const vorher =", self.funktion)
        self.assertIn("eintraege || []).length - vorher", self.funktion)

    def test_sie_nennt_beide_zahlen_wenn_sie_auseinandergehen(self):
        """Ein unlesbarer Scan wurde vorher stillschweigend mitgezählt."""
        self.assertIn("von ${ids.length}", self.funktion)

    def test_und_zeigt_dann_die_hinweise_der_sitzung(self):
        """Der Grund steht dort - nicht in einer Meldung, die verschwindet."""
        self.assertIn("hinweiseZeigen(sitzung.sitzung.hinweise", self.funktion)


if __name__ == "__main__":
    unittest.main()


class EinStehengebliebenerFilterKostetDokumente(unittest.TestCase):
    """„nur 2 Dokumente … und zwar die, die ich vorher ausgewählt hatte."

    Das Suchfeld des Fensters **Auswahl** wurde beim Öffnen nicht geleert. Ein
    stehengebliebener Filter ist hier teurer als anderswo: Die Liste zeigt
    dann vier von hundert Dokumenten, „alle fehlenden" hakt genau diese vier
    an, und der Bearbeiter sieht nicht, warum. Er bezahlt das Einlesen und
    bekommt vier Dokumente.

    Im Dokumentfenster ist genau das seit dem 12.10.2026 berichtigt — mit
    demselben Satz im Kommentar. **Zwei Fenster, die dasselbe tun, und die
    Verbesserung nur im einen.** Dieselbe Form wie beim Balken darüber.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.js = (STATISCH / "app.js").read_text(encoding="utf-8")

    def _funktion(self, name: str) -> str:
        teil = self.js[self.js.index(f"function {name}(")  :]
        return teil[:teil.index("\n}\n")]

    def test_das_gedaechtnisfenster_leert_sein_suchfeld(self):
        oeffnen = self._funktion("gedaechtnisExplorerOeffnen")
        self.assertIn('$("ged-suche")', oeffnen)
        self.assertIn('value = ""', oeffnen)

    def test_es_geschieht_vor_dem_zeichnen(self):
        """Sonst steht die gefilterte Liste da, während das Feld leer aussieht."""
        oeffnen = self._funktion("gedaechtnisExplorerOeffnen")
        self.assertLess(oeffnen.index('$("ged-suche")'),
                        oeffnen.index("gedExplorerZeichnen()"))

    def test_das_dokumentfenster_tut_es_weiterhin(self):
        self.assertIn('const suche = $("explorer-suche"); if (suche) suche.value = "";',
                      self.js)

    def test_alle_fehlenden_nimmt_weiterhin_nur_die_sichtbaren(self):
        """Das ist gewollt und bleibt - nur darf der Filter nicht von selbst dastehen."""
        self.assertIn("gedSichtbarFehlende()", self.js)
