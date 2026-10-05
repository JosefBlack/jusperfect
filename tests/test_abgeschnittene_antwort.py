"""Eine abgeschnittene Antwort ist etwas anderes als eine unbrauchbare.

Aus der Kanzlei, 17.09.2026: Ein Prüfbogenlauf über fünfzig Dokumente scheiterte
nach dem bezahlten Einlesen an der Meldung „Das Modell hat kein verwertbares
Ergebnis geliefert. Bitte erneut versuchen."

Das Modell hatte aber sauber gearbeitet. Es war an eine Grenze des Programms
gestoßen: `max_ausgabe_tokens`. Die Antwort brach mitten im JSON ab, und was
folgte, war kein Modellfehler, sondern eine Einstellung. Der Lauf davor nutzte
6.753 von 8.000 Ausgabetoken, der vom Vortag 7.777 – es war eine Frage der Zeit.

Zwei Dinge hält diese Datei fest: dass der Fall beim Namen genannt wird, und
dass kein zweiter, ebenso teurer Versuch unternommen wird, der in dieselbe
Grenze liefe.
"""

from __future__ import annotations

import unittest

from jusperfect.domain.models import Aktenanalyse
from jusperfect.providers.base import Nutzung, ProviderAntwort
from jusperfect.services.analyse import AnalyseFehler, Analysedienst
from jusperfect.security.identitaet import Identitaet
from jusperfect.services.ausgang import Ausgangskontext, Durchgang
from tests.hilfen import einstellungen


class _Ausgang:
    """Zählt die Aufrufe und liefert eine abgeschnittene Antwort."""

    def __init__(self, stop_grund: str) -> None:
        self.aufrufe = 0
        self._stop = stop_grund

    def fragen(self, kontext, system, material, aufgabe, modell_id=None) -> Durchgang:
        self.aufrufe += 1
        # Abgeschnitten mitten im JSON - genau so kommt es bei max_tokens an.
        text = '{"chronologie": [{"datum": "2025-06-11", "erei'
        return Durchgang(
            antwort=ProviderAntwort(text=text, nutzung=Nutzung(), modell="m",
                                    stop_grund=self._stop),
            kosten=None)


KONTEXT = Ausgangskontext(Identitaet("ra-weber"), "s1", "a1", "analyse")


def _dienst(stop_grund: str) -> tuple[Analysedienst, _Ausgang]:
    ausgang = _Ausgang(stop_grund)
    return Analysedienst(ausgang, einstellungen()), ausgang


class AbgeschnitteneAntwort(unittest.TestCase):
    def test_die_meldung_nennt_die_laengengrenze(self):
        dienst, ausgang = _dienst("max_tokens")
        with self.assertRaises(AnalyseFehler) as fehler:
            dienst._strukturiert(KONTEXT, "M", "A", Aktenanalyse)
        text = str(fehler.exception)
        self.assertIn("abgeschnitten", text)
        self.assertIn("JUSPERFECT_MAX_AUSGABE_TOKENS", text)
        self.assertIn(str(einstellungen().max_ausgabe_tokens), text,
                      "Die geltende Grenze gehört in die Meldung, sonst rät man.")

    def test_kein_zweiter_teurer_versuch(self):
        """Er liefe in dieselbe Grenze und kostete noch einmal Geld."""
        dienst, ausgang = _dienst("max_tokens")
        with self.assertRaises(AnalyseFehler):
            dienst._strukturiert(KONTEXT, "M", "A", Aktenanalyse)
        self.assertEqual(1, ausgang.aufrufe)

    def test_unbrauchbar_ohne_abschneiden_bleibt_beim_zweiten_versuch(self):
        """Der andere Fall ist unverändert: einmal erinnern, dann aufgeben."""
        dienst, ausgang = _dienst("end_turn")
        with self.assertRaises(AnalyseFehler) as fehler:
            dienst._strukturiert(KONTEXT, "M", "A", Aktenanalyse)
        self.assertEqual(2, ausgang.aufrufe)
        self.assertNotIn("abgeschnitten", str(fehler.exception))


class DieGrenzeSelbst(unittest.TestCase):
    def test_sie_traegt_reserve_fuer_eine_grosse_akte(self):
        """Gemessen: 6.753 und 7.777 Ausgabetoken über fünfzig Dokumente.

        Eine Grenze, die zu 97 Prozent ausgereizt wird, ist keine Reserve.
        """
        self.assertGreaterEqual(einstellungen().max_ausgabe_tokens, 12_000)

    def test_sie_laesst_sich_einstellen(self):
        self.assertEqual(
            20_000, einstellungen(JUSPERFECT_MAX_AUSGABE_TOKENS="20000").max_ausgabe_tokens)


if __name__ == "__main__":
    unittest.main()
