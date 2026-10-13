"""Fristen werden erkannt, nie berechnet.

Der Grundsatz steht seit jeher im Auftragstext. Im Durchgang an einer echten
Akte hat das Modell ihn gebrochen:

    „Die Klagefrist endet am 26.05.2026 – Klage muss sofort eingereicht werden"

Das Ergebnis war richtig, und genau das ist die Gefahr: Ein Werkzeug, das
neunmal richtig rechnet, wird beim zehnten Mal geglaubt. Die Fundstelle trug
nicht – als Beleg stand das Kündigungsschreiben, in dem dieses Datum nirgends
vorkommt.

Der Prüfstein: Ein Datum, das in keiner mitgeschickten Passage steht, kann
nicht aus der Akte stammen. In einem Fristsatz ist es gerechnet.
"""

from __future__ import annotations

import unittest

from jusperfect.domain.models import ChronologieEintrag, OffenerPunkt, Passage
from jusperfect.services import prompts
from jusperfect.services.fristen import (
    ERSATZ, ERSATZ_UNBELEGT, entschaerfen, felder_entschaerfen, hinweis,
)

KUENDIGUNG = (
    "Gelsenkirchen, den 04.05.2026\n"
    "hiermit kündigen wir das Arbeitsverhältnis fristlos, hilfsweise ordentlich "
    "zum nächstmöglichen Termin, das ist der 30.09.2026.\n"
    "Begründung: Am 27.04.2026 hat die Mitarbeiterin einen Werkzeugkoffer entwendet."
)


def _index() -> dict[str, Passage]:
    return {"D2-S1-P1": Passage(kennung="D2-S1-P1", dokument_id="D-202",
                                dokument_titel="Kündigung", seite=1, text=KUENDIGUNG)}


class GerechneteFristen(unittest.TestCase):
    def test_der_fall_aus_der_kanzlei(self):
        satz = "Die Klagefrist endet am 26.05.2026 - Klage muss sofort eingereicht werden."
        neu, zahl = entschaerfen(satz, _index())
        self.assertEqual(zahl, 1)
        self.assertNotIn("26.05.2026", neu)
        self.assertIn(ERSATZ, neu)
        # Die Warnung selbst bleibt stehen - dass eine Klagefrist laeuft, ist
        # der wichtige Teil.
        self.assertIn("Klagefrist", neu)
        self.assertIn("sofort eingereicht", neu)

    def test_auch_die_andere_formulierung(self):
        neu, zahl = entschaerfen(
            "Klagefrist § 4 KSchG läuft am 26.05.2026 ab - Klage unverzüglich erheben.", _index())
        self.assertEqual(zahl, 1)

    def test_verschiedene_schreibweisen(self):
        for datum in ("26.05.2026", "26.5.2026", "2026-05-26", "26. Mai 2026"):
            with self.subTest(datum=datum):
                _, zahl = entschaerfen(f"Die Frist endet am {datum}.", _index())
                self.assertEqual(zahl, 1)


class WasStehenBleibt(unittest.TestCase):
    def test_der_ausloeser_mit_beleg_bleibt(self):
        """So hatte es der vorige Durchgang richtig gemacht - das darf nicht fallen."""
        satz = "Klagefrist § 4 KSchG: Drei Wochen ab Zugang der Kündigung (Zugang am 04.05.2026)."
        neu, zahl = entschaerfen(satz, _index())
        self.assertEqual(zahl, 0)
        self.assertEqual(neu, satz)

    def test_fristlos_ist_kein_fristwort(self):
        """Eine fristlose Kündigung zum 30.09.2026 ist eine Tatsache, keine Rechnung."""
        satz = "Kündigung fristlos, hilfsweise ordentlich zum 30.09.2026."
        _, zahl = entschaerfen(satz, _index())
        self.assertEqual(zahl, 0)

    def test_ein_datum_aus_der_akte_bleibt_auch_ohne_fristwort(self):
        """Ein Termin oder Zugangstag wird nicht angetastet - dort waere das
        Streichen der schwerere Fehler.

        Bis zum 05.10.2026 stand hier der 12.09.2026, der in der Akte nirgends
        vorkommt, und diese Pruefung verlangte, dass er stehen bleibt: Ohne
        Fristwort wurde gar nicht geprueft. Genau daran hing Befund F09 - mit
        „Die Klage muss bis zum 26.05.2026 eingereicht werden" kam durch
        dieselbe Luecke ein erfundener Fristablauf durch.

        Die Zusage lautet seitdem anders und zugleich enger: Ein Datum **aus
        der Akte** bleibt ohne Fristwort unangetastet. Eines, das in keiner
        Passage steht, faellt - der naechste Test.
        """
        _, zahl = entschaerfen("Die Besprechung fand am 27.04.2026 statt.", _index())
        self.assertEqual(zahl, 0)

    def test_ein_datum_das_nirgends_steht_faellt_auch_ohne_fristwort(self):
        neu, zahl = entschaerfen("Die Besprechung findet am 12.09.2026 statt.", _index())
        self.assertEqual(zahl, 1)
        self.assertIn(ERSATZ_UNBELEGT, neu)
        # Kein Hinweis auf den Fristenkalender: Hier geht es um keine Frist.
        self.assertNotIn("Fristenkalender", neu)

    def test_ein_belegtes_datum_im_fristsatz_bleibt(self):
        """Steht das Datum in der Akte, ist es keine Rechnung."""
        _, zahl = entschaerfen("Die Kündigungsfrist endet am 30.09.2026.", _index())
        self.assertEqual(zahl, 0)

    def test_leerer_text(self):
        self.assertEqual(entschaerfen("", _index()), ("", 0))


class InDenListen(unittest.TestCase):
    def test_offene_punkte_werden_geprueft(self):
        punkte = [
            OffenerPunkt(beschreibung="Klagefrist § 4 KSchG läuft am 26.05.2026 ab"),
            OffenerPunkt(beschreibung="Vergleichsangebot mit Mandantin besprechen"),
        ]
        zahl = felder_entschaerfen(punkte, "beschreibung", _index())
        self.assertEqual(zahl, 1)
        self.assertIn(ERSATZ, punkte[0].beschreibung)
        self.assertEqual(punkte[1].beschreibung, "Vergleichsangebot mit Mandantin besprechen")

    def test_chronologie_wird_geprueft(self):
        eintraege = [ChronologieEintrag(datum="2026-05-26", ereignis="Ablauf der Klagefrist am 26.05.2026")]
        self.assertEqual(felder_entschaerfen(eintraege, "ereignis", _index()), 1)


class Scans(unittest.TestCase):
    """Die Scan-Testakte 031/26 SC hat es gezeigt: Ein Datum, das im Scan als
    „3O.09.2026" steht, wurde als erfunden gestrichen. Eine Fristensperre,
    die an Erkennungsfehlern scheitert, tilgt bei echten Scans jeden Termin."""

    def _scan_index(self) -> dict[str, Passage]:
        text = ("Goettingen, den l5.03.2026\n"
                "hiermit kuendige ich das Mietverhaeltnis ordentlich zum 3O.09.2026.\n"
                "Der Rueckstand betraegt 2OO,00 EUR.")
        return {"D2-S1-P1": Passage(kennung="D2-S1-P1", dokument_id="D-402",
                                    dokument_titel="Kündigung (Scan)", seite=1, text=text)}

    def test_null_als_o_gilt_als_belegt(self):
        neu, zahl = entschaerfen("Die Kündigungsfrist endet am 30.09.2026.", self._scan_index())
        self.assertEqual(zahl, 0, neu)

    def test_eins_als_l_gilt_als_belegt(self):
        neu, zahl = entschaerfen("Die Frist läuft ab dem 15.03.2026.", self._scan_index())
        self.assertEqual(zahl, 0, neu)

    def test_ein_wirklich_gerechnetes_datum_faellt_trotzdem(self):
        """Die Glättung darf die Sperre nicht aufweichen."""
        _, zahl = entschaerfen("Die Widerspruchsfrist endet am 31.07.2026.", self._scan_index())
        self.assertEqual(zahl, 1)

    def test_woerter_werden_nicht_geglaettet(self):
        """Nur Zahlenketten: Aus „Ilse" darf kein „11se" werden."""
        from jusperfect.services.fristen import _ocr_glaetten
        self.assertEqual(_ocr_glaetten("Ilse Kraemer, Ol"), "Ilse Kraemer, Ol")
        self.assertEqual(_ocr_glaetten("am 3O.09.2026 und 2OO,00 EUR"), "am 30.09.2026 und 200,00 EUR")


class Fristenkalender(unittest.TestCase):
    """Der Kalender in jurnodes ist die eine Stelle, an der Fristen gerechnet
    werden dürfen. Ein Datum von dort ist keine Erfindung des Modells."""

    def test_ein_kalenderdatum_bleibt_stehen(self):
        from datetime import date
        from types import SimpleNamespace
        kalender = [SimpleNamespace(datum=date(2026, 7, 31), bezeichnung="Widerspruchsfrist")]
        neu, zahl = entschaerfen("Die Widerspruchsfrist endet am 31.07.2026.", _index(), kalender)
        self.assertEqual(zahl, 0, neu)

    def test_iso_text_geht_auch(self):
        _, zahl = entschaerfen("Frist bis 31.07.2026.", _index(), ["2026-07-31"])
        self.assertEqual(zahl, 0)

    def test_ein_anderes_datum_faellt_weiterhin(self):
        _, zahl = entschaerfen("Frist bis 15.08.2026.", _index(), ["2026-07-31"])
        self.assertEqual(zahl, 1)

    def test_die_listen_reichen_den_kalender_durch(self):
        punkte = [OffenerPunkt(beschreibung="Widerspruchsfrist läuft am 31.07.2026 ab")]
        self.assertEqual(felder_entschaerfen(punkte, "beschreibung", _index(), ["2026-07-31"]), 0)


class DerHinweisSagtEsDeutlich(unittest.TestCase):
    def test_er_nennt_jurnodes(self):
        self.assertIn("jurnodes", hinweis(1))
        self.assertIn("rechnet keine Fristen", hinweis(1))


class DieRegelnStehenImAuftrag(unittest.TestCase):
    def test_alle_vier(self):
        a = prompts.aufgabe_analyse()
        for name in ("CHRONOLOGIE_REGEL", "ROLLEN_REGEL", "FORDERUNGS_REGEL", "WIDERSPRUCHS_REGEL"):
            with self.subTest(regel=name):
                self.assertIn(getattr(prompts, name), a)

    def test_die_rollenregel_nennt_den_fehler_beim_namen(self):
        """Die gegnerische Kanzlei wurde als „RSV" gefuehrt."""
        self.assertIn("RSV", prompts.ROLLEN_REGEL)
        self.assertIn("Gegenseite", prompts.ROLLEN_REGEL)

    def test_die_widerspruchsregel_nennt_alle_fuenf_arten(self):
        """Jede Art steht dort, weil sie in einer echten Akte gefehlt hat.

        Der Lauf über die große Testakte fand genau die vier Arten, die in der
        Regel standen – und die fünfte nicht. Die Liste ist also nicht Beiwerk,
        sondern die Grenze dessen, wonach überhaupt gesucht wird.
        """
        for art in ("Reihenfolge", "Kenntnis", "Sicherheit", "Anwesenheit", "Maß und Menge"):
            with self.subTest(art=art):
                self.assertIn(art, prompts.WIDERSPRUCHS_REGEL)

    def test_die_widerspruchsregel_laesst_drei_passagen_zu(self):
        """Fund 5 der großen Testakte ist ein Dreiecksfund.

        24 cm geschuldet (Leistungsverzeichnis), 18 cm gemessen (Gutachten),
        24 cm abgerechnet (Schlussrechnung). Solange die Regel „zwei Passagen"
        verlangte, war er durch sie selbst ausgeschlossen.
        """
        self.assertIn("drei Passagen", prompts.WIDERSPRUCHS_REGEL)
        self.assertNotIn("nur, wenn zwei Passagen", prompts.WIDERSPRUCHS_REGEL)

    def test_die_chronologieregel_wehrt_gleichfoermige_tageseintraege_ab(self):
        """Achtundsechzig Zeilen, davon vierzig Kolonnenstärken.

        Jede belegt und richtig – und zusammen verdrängten sie die dreizehn
        Zeilen, auf die es ankommt. Der Grundsatz „nur Ereignisse, die etwas
        bedeuten" stand schon da, als das geschah; deshalb steht es jetzt mit
        Beispiel dort.
        """
        regel = prompts.CHRONOLOGIE_REGEL
        self.assertIn("Bautagebücher", regel)
        self.assertIn("besonderes Vorkommnis", regel)
        self.assertIn("Kolonne", regel, "Ohne Beispiel bleibt es ein Grundsatz.")

    def test_die_chronologieregel_streicht_nicht_den_besonderen_tag(self):
        """Der 11.06.2025 steht im Bautagebuch – und gehört hinein.

        Eine Regel, die Bautagebücher pauschal aussperrt, nähme den Kern eines
        der eingebauten Funde mit. Sie muss also unterscheiden, nicht verbieten.
        """
        regel = prompts.CHRONOLOGIE_REGEL
        self.assertIn("Abwesenheit", regel)
        self.assertNotIn("Bautagebücher gehören nicht", regel)

    def test_der_lebenssachverhalt_schreibt_keine_positionslisten_ab(self):
        """Er hatte Aufmaßblätter seitenweise mitgeschrieben."""
        auftrag = prompts.aufgabe_gedaechtnis()
        self.assertIn("Positionslisten", auftrag)
        self.assertIn("Aufmaßblättern", auftrag)
        self.assertIn("Fundstelle führt", auftrag,
                      "Es soll auch dastehen, warum die Einzelheiten nicht verloren sind.")

    def test_ein_geburtsdatum_gehoert_zu_den_beteiligten(self):
        """Sonst beginnt die Chronologie einer Mietsache im Jahr 1948.

        Im Mietvertrag der Akte 31/26 SC steht „Frau Ilse Kraemer, geb.
        12.O4.1948". Das bezeichnet die Mieterin im Rubrum; ein Ereignis des
        Falls ist es nicht.
        """
        self.assertIn("Geburtsdatum", prompts.ROLLEN_REGEL)
        self.assertIn("geb.", prompts.ROLLEN_REGEL)
        self.assertIn("Geburtsdatum", prompts.CHRONOLOGIE_REGEL)

    def test_das_programm_berichtigt_scanfehler_nicht_stillschweigend(self):
        """Aus der Scanakte 31/26 SC: „l5.03.2026" wurde stumm zu „15.03.2026".

        Der Leser sah dann nicht mehr, was auf dem Papier steht – und bei einer
        Scanakte ist gerade das die Frage.
        """
        self.assertIn("Texterkennungsfehler", prompts.SYSTEM)
        self.assertIn("im Scan:", prompts.SYSTEM)
        self.assertIn("stillschweigend", prompts.SYSTEM)

    def test_die_forderungsregel_verbietet_eigene_rechnung(self):
        self.assertIn("Keine eigene Berechnung", prompts.FORDERUNGS_REGEL)

    def test_zwei_betraege_fuer_dieselbe_sache_stehen_nebeneinander(self):
        """In der Mietsache 31/26 SC ist der Unterschied der Fall selbst.

        850,00 EUR stehen im Mietvertrag, 950,00 EUR verlangt der Vermieter
        seit Januar 2026 mündlich – ohne schriftliches Erhöhungsverlangen. Wer
        einen der beiden Beträge auswählt, löscht den Streit aus der Akte.
        """
        regel = prompts.FORDERUNGS_REGEL
        self.assertIn("nehmen Sie beide auf", regel)
        self.assertIn("Wählen Sie nicht aus", regel)
        self.assertIn("rechnen Sie nicht zusammen", regel)
        self.assertIn("status", regel,
                      "Ohne Herkunft stehen zwei Zahlen da, und niemand weiß, welche gilt.")


if __name__ == "__main__":
    unittest.main()


class EinDatumIstNichtSchonDeshalbEineFrist(unittest.TestCase):
    """Befund 2 aus PRUEFBERICHT-2026-09-16.md, von aussen gegengeprüft.

    Die Quelle nannte nur „Eine Besprechung fand am 26.05.2026 statt"; die
    Antwort machte daraus „Die Klagefrist endet am 26.05.2026" – und kam
    durch, weil das Datum **irgendwo** im Aktenbestand vorkam. Es war nicht
    gerechnet, es war umetikettiert. Dagegen half die alte Prüfung nicht: Sie
    fragte nach der Zeichenkette, nicht nach dem, was dort gemeint war.

    Die Unterscheidung, um die es geht:

    * Ein **Fristbeginn** ist eine Tatsache aus der Akte – der Tag, an dem das
      Schreiben zuging. Ihn zu streichen wäre der schwerere Fehler.
    * Ein **Fristende** ist fast immer gerechnet. Es muss in der Akte selbst
      als Endpunkt geführt sein, sonst fällt es.

    Die zweite Hälfte dieser Klasse ist die wichtigere: Sie hält fest, was
    **stehen bleiben muss**. Der erste Entwurf dieser Sperre hat drei richtige
    Daten gestrichen, darunter einen Fristbeginn aus der Scanakte.
    """

    def _lauf(self, quelle: str, antwort: str, kalender=()) -> int:
        index = {"D1-S1-P1": Passage(kennung="D1-S1-P1", dokument_id="D-1",
                                     dokument_titel="T", seite=1, text=quelle)}
        return entschaerfen(antwort, index, kalender)[1]

    # ── Was fallen muss ────────────────────────────────────────────────────

    def test_ein_besprechungstag_wird_nicht_zur_klagefrist(self):
        self.assertEqual(1, self._lauf("Eine Besprechung fand am 26.05.2026 statt.",
                                       "Die Klagefrist endet am 26.05.2026."))

    def test_ein_rechnungsdatum_wird_nicht_zur_verjaehrung(self):
        self.assertEqual(1, self._lauf("Die Rechnung datiert vom 31.12.2022.",
                                       "Der Anspruch verjährt am 31.12.2022."))

    def test_ein_wirklich_gerechnetes_datum_faellt_weiterhin(self):
        self.assertEqual(1, self._lauf("Die Kündigung ging am 04.05.2026 zu.",
                                       "Die Klagefrist endet am 25.05.2026."))

    # ── Was bleiben muss ───────────────────────────────────────────────────

    def test_ein_fristbeginn_aus_der_akte_bleibt(self):
        """Der Tag des Zugangs steht in der Akte; er ist nicht gerechnet."""
        self.assertEqual(0, self._lauf("Die Kündigung ging der Mandantin am 04.05.2026 zu.",
                                       "Die Klagefrist beginnt mit dem Zugang am 04.05.2026."))

    def test_laeuft_ab_dem_datum_ist_ein_anfang_kein_ende(self):
        """„läuft ab" und „läuft ab dem 15.03." sind zweierlei.

        Der erste Entwurf las beides als Ende und strich das Briefdatum.
        """
        self.assertEqual(0, self._lauf("Göttingen, den 15.03.2026",
                                       "Die Frist läuft ab dem 15.03.2026."))

    def test_eine_kuendigung_zum_termin_belegt_das_fristende(self):
        """Ein Schreiben sagt nicht „die Frist endet am" – es sagt „zum"."""
        self.assertEqual(0, self._lauf(
            "hiermit kündigen wir ordentlich zum nächstmöglichen Termin, das ist der 30.09.2026.",
            "Die Kündigungsfrist endet am 30.09.2026."))

    def test_zahlbar_bis_belegt_ebenfalls(self):
        self.assertEqual(0, self._lauf("Die Rechnung ist zahlbar bis zum 14.08.2025.",
                                       "Die Zahlungsfrist endet am 14.08.2025."))

    def test_eine_gesetzte_frist_belegt_sich_selbst(self):
        self.assertEqual(0, self._lauf("Der Beschluss setzt eine Frist bis zum 26.05.2026.",
                                       "Die Frist endet am 26.05.2026."))

    def test_der_fristenkalender_bleibt_die_eine_stelle_die_rechnen_darf(self):
        class _Eintrag:
            datum = "2026-05-26"

        self.assertEqual(0, self._lauf("Ohne Datumsangabe.",
                                       "Die Frist endet am 26.05.2026.", (_Eintrag(),)))

    def test_ohne_fristwort_wird_nichts_angefasst(self):
        self.assertEqual(0, self._lauf("Der Ortstermin fand am 27.01.2026 statt.",
                                       "Der Ortstermin fand am 27.01.2026 statt."))


class F09DatumsUndSprachvarianten(unittest.TestCase):
    """Befund F09 der Zweitprüfung vom 05.10.2026, Gegenprobe 10.

    Die Sperre hing an zwei Wortlisten. Drei Sätze kamen unverändert durch,
    obwohl keiner von ihnen ein Datum aus der Akte nannte – die Quelle sprach
    allein von einem Zugang am 05.05.2026:

        „Die Klagefrist endet am 26.05.26."        zweistelliges Jahr
        „Die Klagefrist endet am 26. Mai."         Monatsname ohne Jahr
        „Die Klage muss bis zum 26.05.2026 ..."    kein Wort der Fristliste

    Die Belegpflicht hielt sie nicht auf: `[Q: D1-S1-P1]` war eine gültige
    Kennung, nur stützte die Passage die Aussage nicht. Und die Fristensperre
    sah hin, weil das Muster die erste und zweite Schreibweise nicht kannte
    und bei der dritten kein Fristwort danebenstand.

    Was dagegen gebaut wurde, ist **keine größere Wortliste** – der Bericht
    sagt zu Recht, dass die über beliebige natürliche Sprache nichts beweist.
    Die Beweisrichtung ist umgekehrt: Jedes Datum muss sich auf eine Stelle
    zurückführen lassen, die das Programm selbst mitgeschickt hat. Ob ein
    Fristwort danebensteht, entscheidet nur noch den Wortlaut des Ersatzes.

    Diese Klasse ist die Gegenprobe in richtiger Polarität: grün heißt, die
    Lücke ist zu. Die zweite Hälfte ist die wichtigere – sie hält fest, was
    durch die Verschärfung **nicht** mitgerissen werden darf.
    """

    def _lauf(self, antwort: str, quelle: str = "Zugang am 05.05.2026.",
              kalender=(), datum=None) -> tuple[str, int]:
        p = Passage(kennung="D1-S1-P1", dokument_id="D1",
                    dokument_titel="Kündigung", seite=1, text=quelle,
                    dokument_datum=datum)
        return entschaerfen(antwort, {p.kennung: p}, kalender)

    # ── Die drei Umgehungen ───────────────────────────────────────────────

    def test_ein_zweistelliges_jahr_umgeht_die_sperre_nicht_mehr(self):
        neu, zahl = self._lauf("Die Klagefrist endet am 26.05.26 [Q: D1-S1-P1].")
        self.assertEqual(zahl, 1, neu)
        self.assertNotIn("26.05.26", neu)
        self.assertIn(ERSATZ, neu)
        self.assertIn("Klagefrist", neu, "Die Warnung selbst bleibt stehen.")

    def test_ein_monatsname_ohne_jahr_umgeht_die_sperre_nicht_mehr(self):
        neu, zahl = self._lauf("Die Klagefrist endet am 26. Mai [Q: D1-S1-P1].")
        self.assertEqual(zahl, 1, neu)
        self.assertNotIn("26. Mai", neu)

    def test_ein_fristende_ohne_fristwort_umgeht_die_sperre_nicht_mehr(self):
        neu, zahl = self._lauf(
            "Die Klage muss bis zum 26.05.2026 eingereicht werden [Q: D1-S1-P1].")
        self.assertEqual(zahl, 1, neu)
        self.assertNotIn("26.05.2026", neu)

    def test_ein_datum_ohne_jahr_hinter_einem_anlass_wird_geprueft(self):
        """„endet am 26.05." ist dieselbe Umgehung in der dritten Schreibweise."""
        _, zahl = self._lauf("Die Frist endet am 26.05.")
        self.assertEqual(zahl, 1)

    # ── Was nicht mitgerissen werden darf ─────────────────────────────────

    def test_ein_zweistelliges_jahr_aus_der_akte_bleibt(self):
        """Die Akte schreibt vierstellig, die Antwort zweistellig – dasselbe Datum."""
        neu, zahl = self._lauf(
            "Die Kündigungsfrist endet am 30.09.26.",
            "hiermit kündigen wir ordentlich zum 30.09.2026.")
        self.assertEqual(zahl, 0, neu)

    def test_ein_monatsname_ohne_jahr_aus_der_akte_bleibt(self):
        neu, zahl = self._lauf(
            "Die Kündigungsfrist endet am 30. September.",
            "hiermit kündigen wir ordentlich zum 30.09.2026.")
        self.assertEqual(zahl, 0, neu)

    def test_eine_vertragsziffer_ist_kein_datum(self):
        """„Ziffer 2.1." sieht aus wie ein Datum ohne Jahr.

        Eine Vertragsziffer aus dem Text zu streichen wäre der schwerere
        Fehler. Ohne einen Anlass davor – „am", „bis zum", „Frist" – wird die
        Zahl deshalb nicht als Datum gelesen.
        """
        satz = "Die Ziffer 2.1. des Mietvertrages regelt die Kaution."
        neu, zahl = self._lauf(satz)
        self.assertEqual(zahl, 0, neu)
        self.assertEqual(neu, satz)

    def test_eine_versionsnummer_ist_kein_datum(self):
        satz = "Die Fassung 1.13.2024 ist freigegeben."
        neu, zahl = self._lauf(satz)
        self.assertEqual(zahl, 0, neu)
        self.assertEqual(neu, satz)

    def test_das_dokumentdatum_aus_der_kopfzeile_bleibt(self):
        """Es steht in den Stammdaten und fast nie im Text.

        Das Material nennt es in der Kopfzeile der Passage, und der Auftrag
        verlangt ausdrücklich, dass das Modell es nennt. Es als unbelegt zu
        streichen hätte genau die fünf Tage wieder getilgt, die am 28.09.2026
        in fünf Prüfbogenläufen gefehlt haben.
        """
        from datetime import date as _date

        neu, zahl = self._lauf("Das Kündigungsschreiben datiert vom 04.05.2026.",
                               "hiermit kündigen wir das Arbeitsverhältnis.",
                               datum=_date(2026, 5, 4))
        self.assertEqual(zahl, 0, neu)

    def test_die_kopfzeile_belegt_aber_kein_fristende(self):
        """Sonst belegte das Briefdatum jede behauptete Frist.

        „Kündigung, datiert 04.05.2026" würde als Endpunkt durchgehen, weil in
        der Kopfzeile das Wort „Kündigung" steht. Die Kopfzeile zählt deshalb
        als Stelle für eine Tatsache und nie als Nachweis eines Fristendes.
        """
        from datetime import date as _date

        neu, zahl = self._lauf("Die Kündigungsfrist endet am 04.05.2026.",
                               "hiermit kündigen wir das Arbeitsverhältnis.",
                               datum=_date(2026, 5, 4))
        self.assertEqual(zahl, 1, neu)

    def test_der_fristenkalender_gilt_auch_fuer_ein_datum_ohne_jahr(self):
        neu, zahl = self._lauf("Die Frist endet am 31. Juli.", kalender=["2026-07-31"])
        self.assertEqual(zahl, 0, neu)


class DieJahreszahlWirdNichtGeraten(unittest.TestCase):
    """Zweistellig ist zweideutig: „26" ist 2026, „98" ist 1998.

    Die Grenze liegt zwanzig Jahre vor uns – ein Mietvertrag läuft so lange,
    ein Schriftsatz nicht. Sie steht als `JAHRESSPANNE` im Modul, damit sie
    nachlesbar ist und nicht im Muster versteckt.
    """

    def test_das_naheliegende_jahrhundert(self):
        from jusperfect.services.fristen import JAHRESSPANNE, _jahr
        from datetime import date as _date

        self.assertEqual(_jahr("2026"), 2026)
        self.assertEqual(_jahr("26"), 2026)
        self.assertEqual(_jahr("98"), 1998)
        # Die Grenze selbst, aus dem heutigen Tag gerechnet.
        grenze = _date.today().year + JAHRESSPANNE
        self.assertEqual(_jahr(f"{grenze % 100:02d}"), grenze)
        self.assertEqual(_jahr(f"{(grenze + 1) % 100:02d}"), 1900 + (grenze + 1) % 100)
