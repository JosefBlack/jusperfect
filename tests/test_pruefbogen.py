"""Der Prüfbogen misst richtig – auch das muss geprüft sein.

Aus der Kanzlei: „Ich würde gerne nochmal schauen, wie akkurat das System
funktioniert anhand von Testakten."

`werkzeug/pruefbogen.py` nimmt dem Nutzer diese Arbeit ab: Es hält einen echten
Lauf gegen `testdaten/grosse-akte/AUFLOESUNG.md` und sagt, welcher der fünf
eingebauten Funde benannt wurde. Damit entscheidet ein Stück Programm darüber,
ob das Ergebnis gut war – und ein Messgerät, das falsch misst, ist schlimmer
als keines: Es gibt Sicherheit, wo keine ist.

Deshalb wird hier das Messgerät selbst an Ergebnissen geprüft, deren richtige
Antwort feststeht. Ein Modell wird dafür nicht gebraucht.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkzeug"))

import grosse_testakte as vorlage  # noqa: E402
import pruefbogen as pb  # noqa: E402


def _quelle(dokument: str) -> dict:
    nummer = int(dokument.split("-")[1])
    return {"kennung": f"D{nummer}-S1-P1", "dokument_id": dokument, "dokument_titel": "egal"}


def _analyse(**felder) -> dict:
    grund = {"chronologie": [], "beteiligte": [], "forderungen": [], "beweismittel": [],
             "offene_punkte": [], "widersprueche": [], "hinweise": [], "modell": "probe",
             "kosten": {}}
    return grund | felder


class Schreibweisen(unittest.TestCase):
    """Dasselbe anders geschrieben muss als dasselbe gelten."""

    def test_datum_in_allen_ueblichen_formen(self):
        for form in ("14.08.2025", "14.8.2025", "14. August 2025", "14. august 2025"):
            self.assertTrue(pb._enthalten(pb._normalisieren(f"Abnahme am {form}."), "14.08.2025"),
                            form)

    def test_mass_in_allen_ueblichen_formen(self):
        for form in ("24 cm", "24cm", "24 Zentimeter"):
            self.assertTrue(pb._enthalten(pb._normalisieren(f"Geschuldet sind {form}."), "24 cm"),
                            form)

    def test_betrag_in_allen_ueblichen_formen(self):
        for form in ("486.500,00 EUR", "486.500 EUR", "486500 EUR", "486.500,00 €"):
            self.assertTrue(pb._enthalten(pb._normalisieren(f"Werklohn {form}."), "486.500,00 EUR"),
                            form)

    def test_falsche_zahl_gilt_nicht_als_treffer(self):
        text = pb._normalisieren("Werklohn 48.650,00 EUR.")
        self.assertFalse(pb._enthalten(text, "486.500,00 EUR"))


class FundeBewerten(unittest.TestCase):
    """Benannt, belegt, oder gar nicht – die drei Urteile müssen sitzen."""

    def setUp(self) -> None:
        self.fund = vorlage.FUNDE[0]        # Abnahmedatum, D-012 gegen D-039

    def test_benannt_und_belegt_gilt_als_gefunden(self):
        analyse = _analyse(widersprueche=[{
            "beschreibung": "Das Abnahmeprotokoll nennt den 14.08.2025, die "
                            "Schlussrechnung den 02.07.2025.",
            "quellen": [_quelle("D-012"), _quelle("D-039")]}])
        ergebnis = pb.messen(analyse)
        self.assertEqual("gefunden", ergebnis["funde"][0]["urteil"])
        self.assertEqual(["D-012", "D-039"], ergebnis["funde"][0]["belegt"])
        self.assertEqual(1, ergebnis["gefunden"])

    def test_richtig_aber_nur_halb_belegt_ist_kein_treffer(self):
        """Die Belegpflicht ist der Kern des Programms – hier wird sie gemessen."""
        analyse = _analyse(widersprueche=[{
            "beschreibung": "Abnahme laut Protokoll 14.08.2025, laut Rechnung 02.07.2025.",
            "quellen": [_quelle("D-012")]}])
        ergebnis = pb.messen(analyse)
        self.assertEqual("ohne Beleg", ergebnis["funde"][0]["urteil"])
        self.assertEqual(["D-039"], ergebnis["funde"][0]["fehlende_belege"])
        self.assertEqual(0, ergebnis["gefunden"])

    def test_vage_benannt_zaehlt_nicht(self):
        """„Es gibt Unstimmigkeiten beim Abnahmedatum" ist kein Fund."""
        analyse = _analyse(widersprueche=[{
            "beschreibung": "Beim Abnahmedatum bestehen Unstimmigkeiten.",
            "quellen": [_quelle("D-012"), _quelle("D-039")]}])
        self.assertEqual("nicht benannt", pb.messen(analyse)["funde"][0]["urteil"])

    def test_bausteine_vorhanden_aber_nicht_zusammengezogen(self):
        """Der Fall des fünften Fundes: Alles da, nur nicht als Widerspruch."""
        analyse = _analyse(chronologie=[
            {"datum": "2025-08-14", "ereignis": "Abnahme am 14.08.2025", "quellen": []},
            {"datum": "2025-07-02", "ereignis": "Abnahme behauptet 02.07.2025", "quellen": []}])
        fund = pb.messen(analyse)["funde"][0]
        self.assertEqual("nicht benannt", fund["urteil"])
        self.assertIn("2 von 2", fund["bausteine"])


class Zeitstrahl(unittest.TestCase):

    def test_erwartete_tage_werden_erkannt(self):
        analyse = _analyse(chronologie=[
            {"datum": tag, "ereignis": was, "quellen": []} for tag, was in vorlage.CHRONOLOGIE])
        c = pb.messen(analyse)["chronologie"]
        self.assertEqual(len(vorlage.CHRONOLOGIE), len(c["getroffen"]))
        self.assertEqual([], c["fehlend"])
        self.assertEqual(0, c["routine"])

    def test_bautagebuchtage_zaehlen_als_rauschen(self):
        analyse = _analyse(chronologie=[
            {"datum": "2025-03-04", "ereignis": "04.03.2025 – windig, 13 °C",
             "quellen": [{"kennung": "D30-S1-P2", "dokument_titel": "Bautagebuch, März 2025"}]},
            {"datum": "2025-06-20", "ereignis": "Mängelanzeige",
             "quellen": [{"kennung": "D8-S1-P1", "dokument_titel": "Mängelanzeige der Bauherrin"}]}])
        c = pb.messen(analyse)["chronologie"]
        self.assertEqual(1, c["routine"], "Der Bautagebuchtag ist Rauschen.")
        self.assertEqual(["20.06.2025"], c["getroffen"])

    def test_ein_tragender_tag_aus_dem_bautagebuch_ist_kein_rauschen(self):
        """Der 11.06.2025 steht im Bautagebuch – und gehört trotzdem hinein."""
        analyse = _analyse(chronologie=[{
            "datum": "2025-06-11", "ereignis": "11.06.2025 – Polier nicht erschienen",
            "quellen": [{"kennung": "D17-S1-P1", "dokument_titel": "Bautagebuch, Juni 2025"}]}])
        self.assertEqual(0, pb.messen(analyse)["chronologie"]["routine"])


class Fristensperre(unittest.TestCase):

    def test_ausloeser_benennen_ist_erlaubt(self):
        analyse = _analyse(offene_punkte=[{
            "beschreibung": "Prüfung der Verjährungsfrage abhängig vom korrekten "
                            "Abnahmedatum (02.07.2025 oder 14.08.2025).", "quellen": []}])
        self.assertTrue(pb.messen(analyse)["fristensperre"]["haelt"])

    def test_gerechnetes_enddatum_ist_ein_verstoss(self):
        analyse = _analyse(offene_punkte=[{
            "beschreibung": "Die Verjährung der Mängelansprüche endet am 02.07.2030.",
            "quellen": []}])
        sperre = pb.messen(analyse)["fristensperre"]
        self.assertFalse(sperre["haelt"])
        self.assertEqual(1, len(sperre["verstoesse"]))


class Feldnamen(unittest.TestCase):
    """Der Bogen muss dort suchen, wo die Analyse ihre Texte hinschreibt.

    Aus der Kanzlei, Lauf vom 16.09.2026: Der Bogen meldete „✗ 402,00 m²
    Dämmfläche". Die Zahl stand in der Analyse, mit Beleg aus dem
    Leistungsverzeichnis – im Feld „gegenstand" der Forderung. Gesucht hatte
    der Bogen in einem Feld „bezeichnung", das es dort nie gab. Ein falscher
    Feldname wirft keinen Fehler, er liefert stillschweigend nichts; das
    Ergebnis war ein richtiges Ergebnis, das als falsch ausgewiesen wurde.

    Die beiden folgenden Prüfungen halten den Bogen deshalb unmittelbar an die
    Datenstruktur der Analyse, statt Feldnamen ein zweites Mal abzuschreiben.
    """

    def test_jedes_gesuchte_feld_gibt_es_wirklich(self):
        from jusperfect.domain.models import Aktenanalyse

        for abschnitt, felder in pb._TEXTFELDER.items():
            eintragsmodell = Aktenanalyse.model_fields[abschnitt].annotation.__args__[0]
            for feld in felder:
                self.assertIn(feld, eintragsmodell.model_fields,
                              f"{abschnitt}.{feld} steht so nicht in der Analyse.")

    def test_kein_abschnitt_mit_text_wird_uebersehen(self):
        from jusperfect.domain.models import Aktenanalyse

        ohne_eigenen_text = {"hinweise", "modell", "kosten"}
        fehlend = set(Aktenanalyse.model_fields) - ohne_eigenen_text - set(pb._TEXTFELDER)
        self.assertEqual(set(), fehlend,
                         "Ein Abschnitt der Analyse wird vom Bogen gar nicht gelesen.")

    def test_eine_zahl_im_gegenstand_einer_forderung_wird_gefunden(self):
        """Genau der Fall aus der Kanzlei, mit den echten Feldnamen."""
        analyse = _analyse(forderungen=[{
            "gegenstand": "Wärmedämmverbundsystem, Dämmstärke 24 cm, 402,00 m²",
            "betrag": "88,60 EUR je m²", "status": "laut Leistungsverzeichnis Position 6.40",
            "quellen": [_quelle("D-002")]}])
        zahlen = {z["wofuer"]: z["steht_da"] for z in pb.messen(analyse)["zahlen"]}
        self.assertTrue(zahlen["Dämmfläche"])
        self.assertFalse(zahlen["Werklohn brutto"], "Was nicht dasteht, darf nicht zählen.")

    def test_ein_name_bei_den_beteiligten_wird_gefunden(self):
        analyse = _analyse(beteiligte=[
            {"bezeichnung": "Marlies Kettenbach", "rolle": "Mandant", "quellen": []}])
        self.assertTrue(pb._enthalten(pb._alle_texte(analyse), "Marlies Kettenbach"))


class Abbruch(unittest.TestCase):
    """Bricht ein Lauf ab, muss dastehen, womit er gearbeitet hat.

    Aus der Kanzlei, zweimal an einem Abend: „Das Einlesen ist fehlgeschlagen."
    Beim zweiten Mal nannte die Meldung die Kennung – aber nicht, aus welcher
    der sechs Einstellungen sie stammte. Dabei lag genau darin die Auskunft:
    Die Kennung war die alte, also lief eine alte Startdatei, und keine
    Änderung am Programm hätte etwas geholfen.
    """

    def _abbruchtext(self, **umgebung) -> str:
        from jusperfect.config import Einstellungen
        grund = {"JUSPERFECT_ANBIETER": "bedrock", "JUSPERFECT_GEDAECHTNIS": "lokal"}
        e = Einstellungen.aus_umgebung(grund | umgebung)
        return (pb._abbruchtext("Das Einlesen", "ProviderFehler: abgewiesen", e))

    def test_die_kennung_steht_da_und_woher_sie_kommt(self):
        text = self._abbruchtext(
            JUSPERFECT_MODELL_ID="anthropic.gross",
            JUSPERFECT_MODELL_ID_KLEIN="anthropic.klein")
        self.assertIn("Das Einlesen ist fehlgeschlagen", text)
        self.assertIn("eu.anthropic.klein", text)
        self.assertIn("JUSPERFECT_MODELL_ID_KLEIN", text)
        self.assertIn("eu.anthropic.gross", text)
        self.assertIn("JUSPERFECT_MODELL_ID", text)

    def test_jede_funktion_wird_benannt(self):
        text = self._abbruchtext(JUSPERFECT_MODELL_ID="anthropic.gross")
        for name in ("Fragen", "Analyse", "Eingangsprüfung", "Entwürfe", "Aktengedächtnis"):
            self.assertIn(name, text, name)

    def test_eine_eigene_wahl_wird_ihr_zugeschrieben(self):
        """Sonst schickt die Meldung den Nutzer an die falsche Zeile."""
        text = self._abbruchtext(
            JUSPERFECT_MODELL_ID="anthropic.gross",
            JUSPERFECT_MODELL_ID_KLEIN="anthropic.klein",
            JUSPERFECT_MODELL_GEDAECHTNIS="anthropic.eigen")
        zeilen = text.splitlines()
        stelle = next(i for i, z in enumerate(zeilen) if "Aktengedächtnis" in z)
        self.assertIn("eu.anthropic.eigen", zeilen[stelle])
        self.assertIn("JUSPERFECT_MODELL_GEDAECHTNIS", zeilen[stelle + 1])


class Programmstand(unittest.TestCase):
    """Welcher Stand des Programms hat diesen Bogen erzeugt?

    Am 16.09.2026 lief in der Kanzlei ein Ordner, in dem der Programmteil neu
    und die Startdateien alt waren. Von aussen sah das aus wie ein Fehler im
    Programm; gesucht wurde zweimal an der falschen Stelle.
    """

    def test_der_stand_ist_immer_eine_verwertbare_auskunft(self):
        """Zwei Umgebungen, zwei richtige Antworten.

        Im Arbeitsbaum steht in FASSUNG.txt die unersetzte Vorlage – dort füllt
        niemand die Datei, und die Auskunft lautet „Arbeitsverzeichnis". In
        einem ausgepackten ZIP hat Git sie gefüllt; dann steht dort Nummer und
        Datum.

        Hier stand einmal nur der erste Fall. Der Test schlug deshalb fehl,
        sobald jemand die Prüfungen aus einer ZIP laufen liess – und das tut,
        wer das Programm zum ersten Mal in die Hand bekommt. Ein Test, der nur
        beim Entwickler grün ist, misst den Entwickler.
        """
        stand = pb.programmstand()
        self.assertTrue(
            stand == "Arbeitsverzeichnis"
            or re.fullmatch(r"[0-9a-f]{7,40} \d{4}-\d{2}-\d{2}", stand),
            f"unbrauchbare Auskunft: {stand!r}")
        self.assertNotIn("$Format", stand, "Die Vorlage darf nicht durchscheinen.")

    def test_aus_einer_zip_steht_nummer_und_datum(self):
        import unittest.mock
        with unittest.mock.patch.object(
                type(pb.WURZEL / "FASSUNG.txt"), "read_text",
                return_value="f539804 2026-09-16\n"):
            self.assertEqual("f539804 2026-09-16", pb.programmstand())

    def test_der_stand_steht_im_bogen(self):
        text = pb.bogen(pb.messen(_analyse()), {"portionen": 1, "passagen": 1}, "demo")
        self.assertIn("Programmstand:", text)

    def test_der_stand_steht_auch_im_abbruch(self):
        """Dort ist die Frage am dringendsten – und dort fehlte sie."""
        from jusperfect.config import Einstellungen
        e = Einstellungen.aus_umgebung({"JUSPERFECT_ANBIETER": "bedrock",
                                        "JUSPERFECT_GEDAECHTNIS": "lokal"})
        self.assertIn("Programmstand:", (pb._abbruchtext("Das Einlesen", "abgewiesen", e)))


class Bogen(unittest.TestCase):

    def test_beide_kostenposten_stehen_im_bogen(self):
        """Der Bogen wies nur die Analyse aus - den kleineren Posten.

        Am 16.09.2026 meldete er „0,14 €" für einen Lauf, in dem vorher 882.000
        Zeichen durch ein Modell gegangen waren. Wer danach entscheidet, ob ein
        stärkeres Modell zu teuer ist, entscheidet auf einer Zahl, die den
        teuren Teil gar nicht enthält.
        """
        analyse = _analyse(kosten={"eingabe_tokens": 9_571, "ausgabe_tokens": 7_777,
                                   "betrag_eur": 0.14})
        lauf = {"portionen": 7, "passagen": 676,
                "kosten": {"eingabe_tokens": 230_000, "ausgabe_tokens": 30_000,
                           "betrag_eur": 0.41}}
        text = pb.bogen(pb.messen(analyse), lauf, "bedrock")
        self.assertIn("Einlesen der 50 Dokumente", text)
        self.assertIn("0.41 €", text)
        self.assertIn("Analyse über das Gedächtnis", text)
        self.assertIn("0.14 €", text)
        self.assertIn("0.55 €", text)

    def test_ohne_kostenangaben_bleibt_der_bogen_lesbar(self):
        """Der Demo-Anbieter kostet nichts und liefert keine Zahlen."""
        text = pb.bogen(pb.messen(_analyse()), {"portionen": 1, "passagen": 1}, "demo")
        self.assertIn("Zusammen:", text)
        self.assertIn("0.00 €", text)

    def test_jede_arbeit_steht_mit_ihrem_modell_im_kopf(self):
        """Ein Bogen, der nur ein Modell nennt, verbirgt die anderen fünf.

        Aus der Kanzlei, 17.09.2026, 12:32 Uhr: Die Startdatei meldete
        „Modell: anthropic.claude-opus-4-6-v1", der Bogen darunter
        „eu.anthropic.claude-opus-4-5-…". Beides stimmte und meinte
        Verschiedenes – dazwischen lag eine dauerhafte Windows-Einstellung für
        die Analyse allein. Sichtbar wird das nur, wenn jede Arbeit mit ihrem
        Modell dasteht.
        """
        modelle = {"frage": "eu.a.gross", "analyse": "eu.a.anders",
                   "triage": "eu.a.klein", "entwurf": "eu.a.gross",
                   "gedaechtnis": "eu.a.klein"}
        text = pb.bogen(pb.messen(_analyse()), {"portionen": 1, "passagen": 1},
                        "bedrock", modelle)
        self.assertIn("eu.a.anders", text)
        self.assertIn("Analyse:", text)
        self.assertIn("Fragen, Entwürfe:", text, "Gleiches Modell gehört in eine Zeile.")
        self.assertIn("Eingangsprüfung, Aktengedächtnis:", text)

    def test_ohne_modellangaben_bleibt_der_kopf_kurz(self):
        text = pb.bogen(pb.messen(_analyse()), {"portionen": 1, "passagen": 1}, "demo")
        self.assertNotIn("Eingangsprüfung:", text)

    def test_der_bogen_laesst_sich_drucken(self):
        analyse = _analyse(widersprueche=[{
            "beschreibung": "Abnahme 14.08.2025 gegen 02.07.2025.",
            "quellen": [_quelle("D-012"), _quelle("D-039")]}])
        text = pb.bogen(pb.messen(analyse), {"portionen": 7, "passagen": 670}, "bedrock")
        self.assertIn("PRÜFBOGEN", text)
        self.assertIn("1 von 5 Funden", text)
        self.assertNotIn("ACHTUNG", text, "Der Demo-Hinweis gehört nur in einen Demo-Lauf.")

    def test_demo_lauf_wird_ausdruecklich_gekennzeichnet(self):
        text = pb.bogen(pb.messen(_analyse()), {"portionen": 7, "passagen": 670}, "demo")
        self.assertIn("ohne KI", text)


if __name__ == "__main__":
    unittest.main()


class EinTagMitVorkommnisIstKeinRauschen(unittest.TestCase):
    """Der Lauf vom 01.10.2026 wies 5 % Rauschen aus – zu Unrecht.

    Drei Einträge aus Bautagebüchern wurden gezählt. Zwei davon verlangt der
    Auftrag ausdrücklich: Er sagt, ein Tag aus einem laufenden Tagesbericht
    gehöre hinein, wenn er ein besonderes Vorkommnis trägt – „eine
    Abwesenheit, ... eine abweichende Lieferung". Die große Testakte stellt
    genau solche Vorkommnisse her, gewürfelt: 60 der 126 Tage tragen eines.

    Der Bogen maß damit die Befolgung der Anweisung als Fehler. Wäre man ihm
    gefolgt, hätte man die Gegenliste gegen „Abwesenheit" geschärft – und
    Fund 3 verloren, der an genau diesem Wort hängt.
    """

    TAGEBUCH = (
        "Bautagebuch März 2025\n"
        "\n05.03.2025 (Mittwoch) – bedeckt\n"
        "Arbeitszeit 07:00 bis 16:30 Uhr. Bauleitung anwesend ja.\n"
        "Gewerk Fenster: Kolonne 6 Personen. Arbeiten fortgesetzt.\n"
        "Besondere Vorkommnisse: keine.\n"
        "\n06.03.2025 (Donnerstag) – Regen\n"
        "Arbeitszeit 07:00 bis 16:30 Uhr. Bauleitung anwesend ja.\n"
        "Besondere Vorkommnisse: Anlieferung verspätet.\n"
        "\n11.03.2025 (Dienstag) – heiter\n"
        "Arbeitszeit 07:00 bis 16:30 Uhr. Bauleitung anwesend nein.\n"
        "Besondere Vorkommnisse: keine.\n"
    )

    def test_die_vorlage_erkennt_die_besonderen_tage(self):
        import tempfile
        with tempfile.TemporaryDirectory() as ordner:
            (Path(ordner) / "30_bautagebuch.txt").write_text(self.TAGEBUCH, encoding="utf-8")
            tage = vorlage.besondere_tage(Path(ordner))
        self.assertEqual({"2025-03-06", "2025-03-11"}, tage,
                         "Der 05.03. ist ein Tag wie jeder andere und gehört nicht dazu.")

    def test_der_bogen_zaehlt_sie_nicht_als_rauschen(self):
        """Die beiden Einträge im Wortlaut des Laufs vom 01.10.2026."""
        alt = pb._BESONDERE
        pb._BESONDERE = {"2025-03-06", "2025-03-11"}
        try:
            analyse = _analyse(chronologie=[
                {"datum": "2025-03-06", "ereignis": "Bautagebuch März: Anlieferung verspätet",
                 "quellen": [{"kennung": "D30-S1-P3", "dokument_titel": "Bautagebuch, März 2025"}]},
                {"datum": "2025-03-11",
                 "ereignis": "Bautagebuch März: Bauleitung nicht anwesend; Anlieferung verspätet",
                 "quellen": [{"kennung": "D30-S1-P4", "dokument_titel": "Bautagebuch, März 2025"}]}])
            self.assertEqual(0, pb.messen(analyse)["chronologie"]["routine"])
        finally:
            pb._BESONDERE = alt

    def test_ein_tag_ohne_vorkommnis_bleibt_rauschen(self):
        """Die Gegenprobe. Sonst wäre die Änderung keine Berichtigung des
        Maßstabs, sondern seine Abschaffung."""
        alt = pb._BESONDERE
        pb._BESONDERE = {"2025-03-06"}
        try:
            analyse = _analyse(chronologie=[{
                "datum": "2025-03-05",
                "ereignis": "Gewerk Fenster, Kolonne 6 Personen, Arbeiten fortgesetzt",
                "quellen": [{"kennung": "D30-S1-P2", "dokument_titel": "Bautagebuch, März 2025"}]}])
            self.assertEqual(1, pb.messen(analyse)["chronologie"]["routine"])
        finally:
            pb._BESONDERE = alt
