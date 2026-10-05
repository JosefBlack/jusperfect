"""Archivierte Akten sind erkennbar.

In MORGEN.md stand, über die Schnittstelle sei nicht zu sehen, ob eine Akte
archiviert ist. Die Beschreibung des Herstellers sagt etwas anderes: Die
Aktensuche kennt einen Wert "status" mit active, archived und deleted - und
der Adapter liest ihn seit dem 23.09.2026 mit. Gezeigt wurde er nie.

Bis zum 25.09.2026 sah eine abgelegte Akte deshalb aus wie eine laufende.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from jusperfect.jurnodes.http_adapter import akte_aus_json

WURZEL = Path(__file__).resolve().parent.parent
STATISCH = WURZEL / "jusperfect" / "static"


class DerServerSagtEsUndWirLesenEs(unittest.TestCase):

    def test_archived_wird_zu_archiviert(self):
        """So nennt es jur|nodes in seiner Beschreibung."""
        a = akte_aus_json({"identifier": "1", "recordSign": "D-1",
                           "recordStatus": "archived"})
        self.assertEqual("archiviert", a.status)

    def test_auch_das_deutsche_wort(self):
        """Ein Server, der anders antwortet als seine eigene Beschreibung, ist
        heute schon viermal vorgekommen."""
        a = akte_aus_json({"identifier": "1", "recordSign": "D-1",
                           "status": "archiviert"})
        self.assertEqual("archiviert", a.status)

    def test_die_laufenden_woerter_gelten_als_laufend(self):
        """„active" ist das Wort, das der Bestand führt – gemessen am 02.10.2026.

        300 Akten angesehen: 290 „archived", 10 „active". Mehr gibt es nicht.
        """
        for roh in ({"recordStatus": "active"}, {"recordStatus": "aktiv"},
                    {"recordStatus": "offen"}, {"recordStatus": "open"}):
            with self.subTest(roh=roh):
                self.assertEqual("laufend", akte_aus_json(
                    {"identifier": "1", "recordSign": "D-1", **roh}).status)

    def test_ein_unbekanntes_wort_heisst_unbekannt(self):
        """Und nicht „laufend" – das war bis zum 02.10.2026 so, und es war still.

        Führt der Hersteller morgen ein drittes Wort ein, sähe eine
        abgeschlossene Akte aus wie eine laufende: Die Aufbewahrung liefe nie
        an, und niemand bekäme es zu sehen. „unbekannt" schaltet stattdessen
        ``services/aufsicht.py`` ein, die einen Menschen entscheiden lässt.

        Gelöscht wird dabei nichts – „unbekannt" steht nicht in ABSCHLUSSSTATUS.
        """
        for roh in ({"recordStatus": "irgendwas"}, {"recordStatus": "closed"},
                    {"recordStatus": ""}, {}):
            with self.subTest(roh=roh):
                self.assertEqual("unbekannt", akte_aus_json(
                    {"identifier": "1", "recordSign": "D-1", **roh}).status)

    def test_unbekannt_loest_keine_loeschung_aus(self):
        from jusperfect.services.abschluss import ABSCHLUSSSTATUS

        self.assertNotIn("unbekannt", ABSCHLUSSSTATUS)
        self.assertNotIn("laufend", ABSCHLUSSSTATUS)


class DieMarkeStehtInDerOberflaeche(unittest.TestCase):

    @property
    def app_js(self) -> str:
        return (STATISCH / "app.js").read_text(encoding="utf-8")

    @property
    def css(self) -> str:
        return (STATISCH / "styles.css").read_text(encoding="utf-8")

    def test_die_aktenliste_zeigt_sie(self):
        js = self.app_js
        liste = js[js.index("async function aktenSuchen("):js.index("// ── Zwei-Fenster-Explorer")]
        self.assertIn('a.status === "archiviert"', liste)
        self.assertIn("archivMarke()", liste)

    def test_die_kopfleiste_zeigt_sie_auch(self):
        """Eine Akte kann archiviert worden sein, seit sie zuletzt offen war."""
        js = self.app_js
        oeffnen = js[js.index("async function arbeitsflaecheOeffnen("):]
        self.assertIn("archivMarke()", oeffnen[:2000])

    def test_es_steht_ein_wort_da_nicht_nur_eine_farbe(self):
        """Wer eine Liste überfliegt, liest eher als dass er Farben
        unterscheidet - und eine Farbe allein trägt für jemanden mit
        Farbsehschwäche gar nichts."""
        js = self.app_js
        marke = js[js.index("function archivMarke("):js.index("async function aktenSuchen(")]
        self.assertIn('"archiviert"', marke)
        self.assertIn("marke.title", marke)

    def test_die_marke_hat_eine_gestaltung(self):
        self.assertIn(".archivmarke", self.css)


if __name__ == "__main__":
    unittest.main()
