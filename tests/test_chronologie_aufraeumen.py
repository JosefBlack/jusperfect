"""Die Chronologie darf kein abgeschriebener Dokumenttext sein.

Der erste Durchgang an einer echten Akte lieferte achtundvierzig Zeilen, von
denen rund dreißig kein Ereignis waren, sondern Rohtext – Briefkopfzeilen,
Zeilen aus einem Urlaubsplan, mitten im Satz abgeschnittene Stellen. Alle
erwarteten Ereignisse waren enthalten; man musste sie nur suchen. Bei einer
Akte mit vierhundert Dokumenten sucht sie niemand mehr.

Die Fälle hier sind wörtlich aus jenem Durchgang übernommen.
"""

from __future__ import annotations

import unittest
from datetime import date

from jusperfect.domain.models import ChronologieEintrag, Passage, Quelle
from jusperfect.services import prompts
from jusperfect.services.chronologie import (LAUFENDE_AUFZEICHNUNGSARTEN,
                                            aufraeumen, gleicher_vorgang)

# Ein Auszug aus dem Kündigungsschreiben und dem Urlaubsplan, so wie er in den
# Passagen steht. Daran misst sich, was Abschrift ist und was Beschreibung.
KUENDIGUNG = (
    "Gelsenkirchen, den 04.05.2026\n"
    "Sehr geehrte Frau Reinhold-Özdemir,\n"
    "hiermit kündigen wir das mit Ihnen bestehende Arbeitsverhältnis fristlos, "
    "hilfsweise ordentlich zum nächstmöglichen Termin, das ist nach unserer "
    "Berechnung der 30.09.2026.\n"
    "Begründung: Am 27.04.2026 hat die Mitarbeiterin einen Werkzeugkoffer im Wert "
    "von 480,00 EUR entwendet. Ein Mitarbeiter hat dies beobachtet und uns am "
    "29.04.2026 gemeldet."
)
URLAUBSPLAN = (
    "Urlaubsplan 2026 – Stand: 15.03.2026\n"
    "Reinhold-Özdemir, Tanja\n"
    "- 27.04.2026 bis 30.04.2026 (4 Tage)\n"
    "- 04.05.2026 bis 08.05.2026 (5 Tage)\n"
    "- 13.07.2026 bis 31.07.2026 (15 Tage)\n"
    "Genehmigt am 15.03.2026 durch Herrn Kalkbrenner."
)


def _index() -> dict[str, Passage]:
    return {
        "D2-S1-P1": Passage(kennung="D2-S1-P1", dokument_id="D-202", dokument_titel="Kündigung",
                            seite=1, text=KUENDIGUNG),
        "D6-S1-P1": Passage(kennung="D6-S1-P1", dokument_id="D-206", dokument_titel="Urlaubsplan",
                            seite=1, text=URLAUBSPLAN),
    }


def _eintrag(datum: str, ereignis: str, kennung: str = "D2-S1-P1") -> ChronologieEintrag:
    return ChronologieEintrag(
        datum=datum, ereignis=ereignis,
        quellen=[Quelle(kennung=kennung, dokument_id="D-202", dokument_titel="Kündigung",
                        seite=1, zitat="")],
    )


class Abschriften(unittest.TestCase):
    def test_briefkopfzeile_faellt_heraus(self):
        behalten, hinweise = aufraeumen([_eintrag("2026-05-04", "Gelsenkirchen, den 04.05.2026")], _index())
        self.assertEqual(behalten, [])
        self.assertTrue(hinweise, "Das Streichen muss genannt werden.")

    def test_zeile_aus_einem_urlaubsplan_faellt_heraus(self):
        behalten, _ = aufraeumen(
            [_eintrag("2026-07-13", "- 13.07.2026 bis 31.07.2026 (15 Tage)", "D6-S1-P1")], _index())
        self.assertEqual(behalten, [])

    def test_kopfzeile_stand_faellt_heraus(self):
        behalten, _ = aufraeumen([_eintrag("2026-03-15", "Stand: 15.03.2026", "D6-S1-P1")], _index())
        self.assertEqual(behalten, [])

    def test_abgeschnittener_satz_faellt_heraus(self):
        for text in ("beobachtet und uns am 29.04.2026 gemeldet.",
                     "Begründung: Am 27.04.2026 hat die Mitarbeiterin einen Werkzeugkoffer im Wert",
                     "nächstmöglichen Termin, das ist nach unserer Berechnung der 30.09.2026."):
            with self.subTest(text=text):
                behalten, _ = aufraeumen([_eintrag("2026-04-29", text)], _index())
                self.assertEqual(behalten, [])

    def test_eine_beschreibung_bleibt(self):
        gut = "Laut Kündigungsschreiben: Angebliche Entwendung eines Werkzeugkoffers durch Mandantin"
        behalten, hinweise = aufraeumen([_eintrag("2026-04-27", gut)], _index())
        self.assertEqual([e.ereignis for e in behalten], [gut])
        self.assertEqual(hinweise, [])

    def test_kurzes_ereignis_bleibt_auch_wenn_das_wort_im_text_steht(self):
        """„Unfall" steht natürlich auch im Dokument – es deswegen zu streichen wäre falsch.

        Diesen Fehler hatte die erste Fassung: eine Mindestlänge, unterhalb
        derer jeder Eintrag als Fetzen galt. Die Testsammlung hat ihn gefangen.
        """
        behalten, _ = aufraeumen([_eintrag("2026-04-27", "Kündigung")], _index())
        self.assertEqual(len(behalten), 1)


class Doppelungen(unittest.TestCase):
    def test_gleicher_vorgang_am_gleichen_tag_wird_zusammengefasst(self):
        a = _eintrag("2026-05-04", "Übergabe des Kündigungsschreibens an die Mandantin")
        b = _eintrag("2026-05-04", "Übergabe des Kündigungsschreibens an Mandantin durch Kalkbrenner",
                     "D6-S1-P1")
        behalten, hinweise = aufraeumen([a, b], _index())
        self.assertEqual(len(behalten), 1)
        # Kein Beleg geht verloren, nur die Zeile.
        self.assertEqual({q.kennung for q in behalten[0].quellen}, {"D2-S1-P1", "D6-S1-P1"})
        self.assertTrue(any("doppelt" in h.lower() or "zusammengefasst" in h for h in hinweise))

    def test_naeherung_weicht_dem_genauen_datum(self):
        vage = _eintrag("Anfang Mai 2026", "Übergabe des Kündigungsschreibens an die Mandantin")
        genau = _eintrag("2026-05-04", "Übergabe des Kündigungsschreibens an die Mandantin")
        behalten, _ = aufraeumen([vage, genau], _index())
        self.assertEqual(len(behalten), 1)
        self.assertEqual(behalten[0].datum, "2026-05-04")

    def test_zwei_verschiedene_tage_bleiben_zwei_eintraege(self):
        """Derselbe Wortlaut an zwei Tagen kann ein wiederholter Vorgang sein."""
        behalten, _ = aufraeumen(
            [_eintrag("2026-05-04", "Schreiben der Gegenseite geht ein"),
             _eintrag("2026-05-26", "Schreiben der Gegenseite geht ein")], _index())
        self.assertEqual(len(behalten), 2)

    def test_verschiedene_vorgaenge_bleiben_getrennt(self):
        behalten, _ = aufraeumen(
            [_eintrag("2026-05-04", "Übergabe des Kündigungsschreibens an die Mandantin"),
             _eintrag("2026-05-04", "Betriebsrat widerspricht der beabsichtigten Kündigung")], _index())
        self.assertEqual(len(behalten), 2)


class DieRegelStehtImAuftrag(unittest.TestCase):
    def test_beide_auftraege_tragen_dieselbe_regel(self):
        """Sonst laufen die volle Analyse und der schmale Weg auseinander."""
        self.assertIn(prompts.CHRONOLOGIE_REGEL, prompts.aufgabe_analyse())
        self.assertIn(prompts.CHRONOLOGIE_REGEL, prompts.aufgabe_chronologie())

    def test_die_regel_verlangt_eine_beschreibung(self):
        self.assertIn("BESCHREIBT", prompts.CHRONOLOGIE_REGEL)

    def test_ein_schriftstueck_ist_selbst_ein_ereignis(self):
        """Gemessen an der grossen Testakte, drei Laeufe, drei Modelle.

        In allen drei fehlten dieselben fuenf Tage: 14.02.2025
        Leistungsverzeichnis, 02.09.2025 Schlussrechnung, 18.02.2026 Gutachten,
        11.03.2026 Schriftsatz der Gegenseite, 08.04.2026 Zeugenbenennung. Drei
        Modelle, dasselbe Loch - also keine Modellschwaeche, sondern diese Regel.

        Die Ursache stand in der Regel selbst: „Keine Briefkopf- und
        Kopfzeilen". Das Datum eines Schriftstuecks STEHT im Briefkopf. Gemeint
        war, dass ein Eintrag mehr sagen muss als „Goettingen, den 04.05.2026" -
        gewirkt hat es als Verbot, das Schriftstueck ueberhaupt zu vermerken.

        Fuer eine Kanzlei ist das die falsche Auswahl: Wann ein Schriftsatz bei
        Gericht war, ist eine eigene Tatsache, und Fristen haengen daran.
        """
        regel = prompts.CHRONOLOGIE_REGEL
        self.assertIn("SELBST EIN EREIGNIS", regel)
        self.assertIn("SEINEM EIGENEN", regel)
        # Gegen die gemeinsame Liste, nicht gegen eine Schreibweise: Auftrag
        # und Filter muessen von denselben Dokumentarten sprechen.
        self.assertIn(prompts.SCHRIFTSTUECKE_MIT_EIGENEM_DATUM, regel)
        for art in ("Schriftsatz", "Gutachten", "Zeugenbenennung",
                    "Leistungsverzeichnis", "Klageschrift", "Schlussrechnung"):
            with self.subTest(art=art):
                self.assertIn(art, prompts.SCHRIFTSTUECKARTEN, art)
                self.assertIn(art, regel)

    def test_das_beispiel_zeigt_die_zwei_eintraege(self):
        """Ohne das Beispiel bleibt „eigenes Datum" eine Behauptung.

        Die Schlussrechnung vom 02.09.2025 behauptet eine Abnahme am
        02.07.2025. Beide Tage gehoeren hinein, und sie sind nicht dasselbe.
        """
        regel = prompts.CHRONOLOGIE_REGEL
        self.assertIn("02.09.2025", regel)
        self.assertIn("02.07.2025", regel)
        self.assertIn("ZWEIMAL", regel)

    def test_die_routine_bleibt_ausgenommen(self):
        """Der Rauschfilter stand bei 0 Prozent - das darf die neue Regel nicht
        zurueckholen. Ein Aufmassblatt treibt den Fall nicht voran."""
        regel = prompts.CHRONOLOGIE_REGEL
        self.assertIn("Nicht selbst ein Ereignis", regel)
        for art in ("Bautagebücher", "Aufmaßblätter", "Lichtbildmappen"):
            with self.subTest(art=art):
                self.assertIn(art, regel)

    def test_das_datum_allein_ist_kein_eintrag(self):
        self.assertIn("bloße Datum ist kein", prompts.CHRONOLOGIE_REGEL)


class Aehnlichkeit(unittest.TestCase):
    def test_beugung_und_umstellung_gelten_als_derselbe_vorgang(self):
        self.assertTrue(gleicher_vorgang(
            "Betriebsrat widerspricht der Kündigung",
            "Der Betriebsrats widerspricht den Kündigungen"))

    def test_verschiedene_vorgaenge_nicht(self):
        self.assertFalse(gleicher_vorgang(
            "Betriebsrat widerspricht der Kündigung",
            "Mandantin erteilt der Kanzlei das Mandat"))


if __name__ == "__main__":
    unittest.main()


# ── Die laufende Aufzeichnung an ihrem eigenen Datum ────────────────────────
#
# Die drei Eintraege stammen woertlich aus dem Pruefbogenlauf vom 01.10.2026,
# 19:24 Uhr. Der Bogen zaehlte alle drei als Rauschen; zwei davon verlangt der
# Auftrag ausdruecklich.

TAGEBUCH_MAERZ = (
    "Bautagebuch März 2025\n"
    "06.03.2025 (Donnerstag) – bedeckt\n"
    "Arbeitszeit 07:00 bis 16:30 Uhr. Bauleitung anwesend ja.\n"
    "Besondere Vorkommnisse: Anlieferung verspätet.\n"
)
TAGEBUCH_APRIL = (
    "Bautagebuch April 2025\n"
    "30.04.2025 (Mittwoch) – heiter\n"
    "Das Bautagebuch für April wird abgeschlossen und der Bauherrin übergeben.\n"
)


def _tagebuchindex() -> dict[str, Passage]:
    return {
        "D30-S1-P3": Passage(kennung="D30-S1-P3", dokument_id="D-030",
                             dokument_titel="Bautagebuch, März 2025", seite=1,
                             text=TAGEBUCH_MAERZ, dokument_datum=date(2025, 3, 31)),
        "D16-S1-P1": Passage(kennung="D16-S1-P1", dokument_id="D-016",
                             dokument_titel="Bautagebuch, April 2025", seite=1,
                             text=TAGEBUCH_APRIL, dokument_datum=date(2025, 4, 30)),
    }


def _tagebucheintrag(datum: str, ereignis: str, kennung: str) -> ChronologieEintrag:
    return ChronologieEintrag(
        datum=datum, ereignis=ereignis,
        quellen=[Quelle(kennung=kennung, dokument_id=kennung.split("-")[0],
                        dokument_titel="Bautagebuch", seite=1, zitat="")],
    )


class LaufendeAufzeichnungen(unittest.TestCase):
    """Ein Bautagebuch an seinem eigenen Datum ist kein Ereignis – ein Tag darin schon."""

    def test_das_abgeschlossene_tagebuch_faellt_heraus(self):
        """Woertlich aus dem Lauf vom 01.10.2026: „Bautagebuch April
        abgeschlossen und der Bauherrin übergeben", am 30.04.2025 – dem Datum
        des Bautagebuchs selbst. Der Auftrag sagte das seit dem 22.09. in
        Worten; durchgesetzt hat es niemand."""
        behalten, hinweise = aufraeumen(
            [_tagebucheintrag("2025-04-30",
                              "Bautagebuch April abgeschlossen und der Bauherrin übergeben",
                              "D16-S1-P1")],
            _tagebuchindex())
        self.assertEqual(behalten, [])
        self.assertTrue(any("laufende Aufzeichnung" in h for h in hinweise),
                        "Wer eine Chronologie zur Fristenpruefung nimmt, muss wissen, "
                        "dass gestrichen wurde.")

    def test_ein_tag_mit_vorkommnis_bleibt(self):
        """Derselbe Lauf, derselbe Dokumenttyp – und dieser Eintrag muss
        bleiben. Das Bautagebuch ist vom 31.03.2025, der Eintrag vom
        06.03.2025: ein Tag DARIN, nicht das Dokument selbst."""
        behalten, _ = aufraeumen(
            [_tagebucheintrag("2025-03-06", "Bautagebuch März: Anlieferung verspätet",
                              "D30-S1-P3")],
            _tagebuchindex())
        self.assertEqual(len(behalten), 1)

    def test_fund_drei_ueberlebt_die_neue_regel(self):
        """Die Gegenprobe, und sie ist der Grund für die enge Fassung.

        Fund 3 der großen Testakte – der Polier, der am 11.06.2025 nicht auf
        der Baustelle war – stammt aus einem Bautagebuch. Wer die Quelle allein
        zum Maßstab nimmt statt Quelle UND eigenes Datum, streicht einen der
        fünf Funde mit und merkt es erst beim nächsten Lauf für drei Euro.
        """
        behalten, _ = aufraeumen(
            [_tagebucheintrag("2025-06-11",
                              "Polier Hasso Wendtland ist nicht auf der Baustelle",
                              "D30-S1-P3")],
            _tagebuchindex())
        self.assertEqual(len(behalten), 1)

    def test_ein_schriftstueck_an_seinem_datum_bleibt_unberuehrt(self):
        """Die Regel gilt nur für laufende Aufzeichnungen. Eine Schlussrechnung
        an ihrem eigenen Datum ist der Kern der Berichtigung vom 28.09.2026 und
        darf von der neuen Regel nicht wieder eingesammelt werden."""
        index = {"D9-S1-P1": Passage(kennung="D9-S1-P1", dokument_id="D-009",
                                     dokument_titel="Schlussrechnung", seite=1,
                                     text="Schlussrechnung vom 02.09.2025",
                                     dokument_datum=date(2025, 9, 2))}
        behalten, _ = aufraeumen(
            [_tagebucheintrag("2025-09-02",
                              "Schlussrechnung der Auftragnehmerin geht ein",
                              "D9-S1-P1")],
            index)
        self.assertEqual(len(behalten), 1)


    def test_das_empfangsbekenntnis_bleibt_an_seinem_eigenen_datum(self):
        """Der Fall, der den ersten Entwurf dieser Regel widerlegt hat.

        „Empfangsbekenntnis" stand bis zum 01.10.2026 bei den laufenden
        Aufzeichnungen – sein eigenes Datum sollte also nichts tragen. Beim
        Nachrechnen des Laufs vom 01.10.2026 hätte der neue Filter damit den
        21.06.2025 gestrichen: 12 von 13 Tagen statt 13 von 13.

        Für eine Kanzlei ist die alte Einordnung falsch herum. Das Datum eines
        Empfangsbekenntnisses IST das Ereignis, denn an ihm beginnen Fristen –
        hier trägt es den Zugang der Mängelrüge und damit zwei der fünf Funde.
        """
        index = {"D21-S1-P1": Passage(
            kennung="D21-S1-P1", dokument_id="D-021",
            dokument_titel="Empfangsbekenntnis und E-Mail-Verkehr", seite=1,
            text="Bestätigung des Erhalts", dokument_datum=date(2025, 6, 21))}
        behalten, _ = aufraeumen(
            [_tagebucheintrag("2025-06-21",
                              "Empfangsbekenntnis des Geschäftsführers über den Erhalt "
                              "der Mängelanzeige", "D21-S1-P1")],
            index)
        self.assertEqual(len(behalten), 1,
                         "Ein gestrichener Tag ist eine verlorene Frist.")


class DieListenSprechenVonDenselbenArten(unittest.TestCase):
    def test_der_auftrag_nennt_jede_art_aus_der_liste_des_filters(self):
        """Zwei handgeschriebene Listen laufen auseinander. Am 28.09.2026 hat
        genau das den Filter gegen den Auftrag arbeiten lassen."""
        for einzahl, mehrzahl in LAUFENDE_AUFZEICHNUNGSARTEN:
            self.assertIn(mehrzahl, prompts.LAUFENDE_AUFZEICHNUNGEN, einzahl)
            self.assertIn(mehrzahl, prompts.CHRONOLOGIE_REGEL, einzahl)
