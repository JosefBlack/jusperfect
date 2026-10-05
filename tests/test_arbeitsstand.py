"""Woran zuletzt gearbeitet wurde - beim Öffnen der Akte.

Aus der Kanzlei am 25.09.2026: "beim Öffnen der Akte sehen, was man als
Letztes gemacht hat, sodass man dann wieder daran ansetzen kann."

Alles dafür lag schon im Aktengedaechtnis; es wurde nur nie gezeigt. Das
Gedaechtnisfenster sagt, WAS darin liegt - nicht, WAS ZULETZT GETAN wurde.
"""

from __future__ import annotations

import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jusperfect.domain.models import (Aktengedaechtnis, ChronologieEintrag,
                                      GedaechtnisAntwort, GedaechtnisDokument)
from jusperfect.services.gedaechtnis import Gedaechtnisdienst

WURZEL = Path(__file__).resolve().parent.parent
FRUEHER = datetime(2026, 9, 20, 9, tzinfo=timezone.utc)


def _frage(text: str, wann: datetime) -> GedaechtnisAntwort:
    return GedaechtnisAntwort(frage=text, antwort="...", zeitpunkt=wann)


class DerStandZeigtDieEigenenFragen(unittest.TestCase):

    def test_die_juengste_frage_steht_oben(self):
        """Wer gestern dreimal gefragt hat, will die letzte Frage sehen."""
        g = Aktengedaechtnis(akte_id="a", fragen_antworten=[
            _frage("zuerst", FRUEHER),
            _frage("zuletzt", FRUEHER + timedelta(hours=5)),
            _frage("dazwischen", FRUEHER + timedelta(hours=2)),
        ])
        stand = Gedaechtnisdienst.arbeitsstand(g)
        self.assertEqual(["zuletzt", "dazwischen", "zuerst"],
                         [f["frage"] for f in stand["fragen"]])

    def test_es_werden_nicht_alle_gezeigt(self):
        """Eine Leiste mit dreissig Fragen ist keine Hilfe, sondern ein Archiv."""
        g = Aktengedaechtnis(akte_id="a", fragen_antworten=[
            _frage(f"Frage {i}", FRUEHER + timedelta(minutes=i)) for i in range(30)])
        stand = Gedaechtnisdienst.arbeitsstand(g)
        self.assertEqual(3, len(stand["fragen"]))
        self.assertEqual(30, stand["fragen_gesamt"])

    def test_der_wortlaut_bleibt_unveraendert(self):
        """Keine Zusammenfassung - an der eigenen Frage erkennt man sich wieder."""
        wortlaut = "Ist die Schlussrechnung vom 02.09.2025 fällig?"
        g = Aktengedaechtnis(akte_id="a",
                             fragen_antworten=[_frage(wortlaut, FRUEHER)])
        self.assertEqual(wortlaut,
                         Gedaechtnisdienst.arbeitsstand(g)["fragen"][0]["frage"])


class DerStandKostetNichts(unittest.TestCase):

    def test_kein_modellaufruf_im_quelltext(self):
        """Eine geschriebene Zusammenfassung kostete bei JEDEM Öffnen Geld.

        Und sie könnte danebenliegen. Deshalb wird nur gelesen, was ohnehin
        im Gedächtnis steht.
        """
        quelle = (WURZEL / "jusperfect" / "services" / "gedaechtnis.py").read_text(encoding="utf-8")
        anfang = quelle.index("def arbeitsstand(")
        ende = quelle.index("def uebersicht(")
        koerper = quelle[anfang:ende]
        for verdacht in ("self._ausgang", "provider", "antworten(", "aufrufen("):
            self.assertNotIn(verdacht, koerper, verdacht)


class OhneVorgeschichteBleibtEsStill(unittest.TestCase):

    def test_ohne_gedaechtnis_nichts(self):
        self.assertFalse(Gedaechtnisdienst.arbeitsstand(None)["vorhanden"])

    def test_beim_ersten_oeffnen_nichts(self):
        """Eine leere Leiste nimmt Platz und sagt nichts."""
        self.assertFalse(
            Gedaechtnisdienst.arbeitsstand(Aktengedaechtnis(akte_id="a"))["vorhanden"])


class DieZahlenBeantwortenDieFrageVonMorgens(unittest.TestCase):

    def test_bis_wann_der_zeitstrahl_reicht(self):
        """"Sind die neuen Schriftsätze schon drin?" - das beantwortet sich so."""
        g = Aktengedaechtnis(akte_id="a",
                             fragen_antworten=[_frage("x", FRUEHER)],
                             chronologie=[
                                 ChronologieEintrag(datum="2025-02-14", ereignis="a"),
                                 ChronologieEintrag(datum="2026-04-08", ereignis="b"),
                                 ChronologieEintrag(datum="", ereignis="ohne Datum"),
                             ])
        self.assertEqual("2026-04-08", Gedaechtnisdienst.arbeitsstand(g)["chronologie_bis"])

    def test_wieviele_dokumente_im_gedaechtnis_liegen(self):
        # "zeichen" ist am Dokument keine Angabe, sondern wird aus den Seiten
        # gerechnet - ein Wert im Erzeuger wird stillschweigend verworfen.
        g = Aktengedaechtnis(akte_id="a", fragen_antworten=[_frage("x", FRUEHER)],
                             dokumente=[GedaechtnisDokument(dokument_id=f"D-{i}",
                                                            titel="t")
                                        for i in range(42)])
        stand = Gedaechtnisdienst.arbeitsstand(g)
        self.assertEqual(42, stand["dokumente"])
        self.assertEqual(sum(d.zeichen for d in g.dokumente), stand["zeichen"])


class DieUebersichtTraegtIhnMit(unittest.TestCase):

    def test_die_oberflaeche_bekommt_ihn_ohne_zweite_anfrage(self):
        g = Aktengedaechtnis(akte_id="a", fragen_antworten=[_frage("x", FRUEHER)])
        self.assertTrue(Gedaechtnisdienst.uebersicht(g)["arbeitsstand"]["vorhanden"])

    def test_auch_wenn_es_gar_keines_gibt(self):
        """Sonst müsste die Oberfläche zwei Fälle unterscheiden."""
        self.assertIn("arbeitsstand", Gedaechtnisdienst.uebersicht(None))


class DieLeisteStehtInDerOberflaeche(unittest.TestCase):

    @property
    def html(self) -> str:
        return (WURZEL / "jusperfect" / "static" / "index.html").read_text(encoding="utf-8")

    @property
    def app_js(self) -> str:
        return (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")

    def test_sie_steht_vor_der_arbeitsflaeche(self):
        html = self.html
        self.assertLess(html.index('id="arbeitsstand"'), html.index('<main id="flaeche"'))

    def test_sie_wird_beim_oeffnen_gefuellt(self):
        js = self.app_js
        oeffnen = js[js.index("async function arbeitsflaecheOeffnen("):]
        self.assertIn("arbeitsstandZeigen()", oeffnen[:1500])

    def test_sie_laesst_sich_wegklicken(self):
        """Sie beantwortet eine Frage, die man morgens hat - danach ist sie im Weg."""
        self.assertIn('id="arbeitsstand-zu"', self.html)
        self.assertIn("arbeitsstandSchliessen", self.app_js)

    def test_sie_bleibt_leer_statt_leer_dazustehen(self):
        js = self.app_js
        funktion = js[js.index("function arbeitsstandZeigen("):js.index("function arbeitsstandSchliessen(")]
        self.assertIn("leiste.hidden = true", funktion)

    def test_kein_zweites_aside_vor_der_rechten_spalte(self):
        """Prüfungen schneiden die rechte Spalte am ersten </aside> ab."""
        html = self.html
        vorher = html[:html.index('<aside class="spalte rechts"')]
        self.assertNotIn("<aside", vorher)


if __name__ == "__main__":
    unittest.main()
