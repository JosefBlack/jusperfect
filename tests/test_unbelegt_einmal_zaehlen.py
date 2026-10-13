"""Eine Zeile für alle zurückgehaltenen Aussagen, nicht eine je Aussage.

Aus der Kanzlei am 13.10.2026:

    „Aussage ohne belastbaren Beleg entfernt (genannt: —)." steht im Programm
    und nimmt unnötig Platz weg – vielleicht lieber zählen oder ganz
    weglassen, da man die Aussage sowieso nicht anklicken kann.

Beides stimmte: Es stand einmal je zurückgehaltener Aussage da, bei fünfzehn
also fünfzehnmal derselbe Satz. Eine Stelle las sich sogar
`hinweise += [UNBELEGT_HINWEIS] * vorlauf_verworfen` — die Wiederholung war
ausgeschrieben.

**Weggelassen wird sie trotzdem nicht**, und das ist die eine Stelle, an der
ich dem Vorschlag nicht ganz folge: Dass etwas zurückgehalten wurde, **ist**
die Belegpflicht. Eine Antwort, die stillschweigend kürzer wird, wäre genau
der Zustand, den dieses Programm verhindern soll. Gezählt wird also — wie
vorgeschlagen —, aber nicht verschwiegen.

Was bleibt: die Fundstellen, die das Modell **genannt** hat, obwohl es sie
nicht gibt. Das ist kein Rauschen, sondern der Nachweis einer Erfindung. Der
Gedankenstrich dagegen sagte nichts und fällt weg.
"""

from __future__ import annotations

import unittest

from jusperfect.services.belegpflicht import unbelegt_satz


class EineZeileStattVieler(unittest.TestCase):
    def test_ohne_zurueckgehaltenes_steht_nichts_da(self):
        self.assertEqual(unbelegt_satz(0, []), "")

    def test_eine_aussage_im_singular(self):
        satz = unbelegt_satz(1, [])
        self.assertIn("Eine Aussage wurde", satz)
        self.assertNotIn("1 Aussagen", satz)

    def test_viele_aussagen_sind_eine_zeile_mit_zahl(self):
        satz = unbelegt_satz(15, [])
        self.assertIn("15 Aussagen wurden", satz)
        self.assertEqual(satz.count("entfernt"), 1, satz)

    def test_der_gedankenstrich_faellt_weg(self):
        """Er sagte nichts und stand in jeder Zeile."""
        self.assertNotIn("—", unbelegt_satz(3, ["—", "", "—"]))
        self.assertNotIn("genannt:", unbelegt_satz(3, []))


class ErfundeneFundstellenBleibenStehen(unittest.TestCase):
    """Sie sind der Nachweis, nicht das Rauschen."""

    def test_eine_genannte_wird_benannt(self):
        satz = unbelegt_satz(1, ["D9-S1-P1"])
        self.assertIn("D9-S1-P1", satz)
        self.assertIn("die es nicht gibt", satz)

    def test_mehrere_stehen_einmal_und_sortiert(self):
        satz = unbelegt_satz(3, ["D9-S1-P1", "D2-S1-P1", "D9-S1-P1"])
        self.assertIn("D2-S1-P1, D9-S1-P1", satz)
        self.assertEqual(satz.count("D9-S1-P1"), 1, satz)

    def test_singular_und_plural_stimmen(self):
        self.assertIn("eine Fundstelle genannt", unbelegt_satz(1, ["D1-S1-P1"]))
        self.assertIn("Fundstellen genannt", unbelegt_satz(2, ["D1-S1-P1", "D2-S1-P1"]))


class AmGanzenDurchlauf(unittest.TestCase):
    """Die Probe am wirklichen Weg, nicht nur am Satzbauer."""

    def test_drei_unbelegte_ergeben_einen_hinweis(self):
        from jusperfect.services.belegpflicht import aussage_fail_closed
        from jusperfect.services.passagen import Passage

        passage = Passage(kennung="D1-S1-P1", dokument_nr=1, dokument_id="D-1",
                          dokument_titel="Brief", seite=1, text="Der Vertrag wurde geschlossen.")
        # Der Prüfer erwartet ein Verzeichnis Kennung -> Passage, keine Liste.
        index = {passage.kennung: passage}
        text = ("Eins [Q: D9-S1-P1]. Zwei [Q: D8-S1-P1]. Drei [Q: D7-S1-P1]. "
                "Vier [Q: D1-S1-P1].")
        ergebnis = aussage_fail_closed(text, index)
        self.assertEqual(ergebnis.verworfen, 3)
        zeilen = [h for h in ergebnis.hinweise if "ohne belastbaren Beleg" in h]
        self.assertEqual(len(zeilen), 1, ergebnis.hinweise)
        self.assertIn("3 Aussagen", zeilen[0])
        for erfunden in ("D7-S1-P1", "D8-S1-P1", "D9-S1-P1"):
            self.assertIn(erfunden, zeilen[0])


if __name__ == "__main__":
    unittest.main()
