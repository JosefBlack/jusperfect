"""Die Startdateien sind das, was die Kanzlei tatsächlich doppelklickt.

Eine Einstellung darin, die das Programm nicht annimmt, fällt sonst erst am
schwarzen Fenster auf – und dort steht sie zwischen Installationsmeldungen.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from jusperfect.config import Einstellungen

WURZEL = Path(__file__).resolve().parent.parent


def _einstellungen_aus(datei: str, **zusatz: str) -> Einstellungen:
    env: dict[str, str] = {}
    for zeile in (WURZEL / datei).read_text(encoding="utf-8").splitlines():
        # Beide Formen sind eine Voreinstellung: "set X=..." und
        # "if not defined X set X=..." - letztere laesst eine per setx
        # hinterlegte Einrichtung (etwa das AWS-Gedaechtnis) bestehen.
        treffer = re.match(r"\s*(?:if not defined \w+\s+)?set\s+(JUSPERFECT_[A-Z_]+)=(.*)$", zeile)
        if treffer:
            env[treffer.group(1)] = treffer.group(2).strip().replace("\\", "/")
    env.update(zusatz)
    # Der AWS-Starter wählt den Anbieter erst zur Laufzeit über die Prüfung.
    env.setdefault("JUSPERFECT_ANBIETER", "demo")
    return Einstellungen.aus_umgebung(env)


class DieAusgabeMussLesbarSein(unittest.TestCase):
    """Sonderzeichen in der Ausgabe dürfen den Befehl nicht zum Abbruch bringen.

    Die Werkzeuge schreiben Haken, Kreuze und Striche. Geht ihre Ausgabe nicht
    auf den Bildschirm, sondern in eine Datei oder durch eine Pipe, nimmt Python
    unter Windows die alte Zeichentabelle – und bricht beim ersten dieser
    Zeichen ab, also in der ersten Zeile. Wer das sieht, sieht gar nichts.
    """

    #: Startdateien, die Python mit solcher Ausgabe aufrufen.
    MIT_AUSGABE = ("START-DEMO.bat", "START-AWS.bat", "MODELLE-ANZEIGEN.bat",
                   "ZUGANG-EINTRAGEN.bat", "ZUGANG-PRUEFEN.bat",
                   "PRUEFBOGEN.bat", "FUNKTIONSPROBE.bat", "GEDAECHTNIS-PROBE.bat",
                   "AUFBEWAHRUNG-BEISPIELE.bat", "JURNODES-PRUEFEN.bat",
                   "ORDNER-PRUEFEN.bat", "START-KANZLEI.bat",
                   "ABLAGE-PRUEFEN.bat")

    def test_jede_startdatei_stellt_die_zeichentabelle_um(self):
        for datei in self.MIT_AUSGABE:
            with self.subTest(datei=datei):
                t = (WURZEL / datei).read_text(encoding="utf-8")
                self.assertIn("chcp 65001", t)

    def test_wo_die_ausgabe_umgeleitet_wird_reicht_die_zeichentabelle_nicht(self):
        """chcp wirkt auf das Fenster. In eine Datei schreibt Python anders."""
        for datei, befehl in (("ZUGANG-PRUEFEN.bat", "-m jusperfect.awstest"),
                              ("JURNODES-PRUEFEN.bat", "-m jusperfect.jurnodestest"),
                              ("ORDNER-PRUEFEN.bat", "-m jusperfect.ordnerpruefung")):
            with self.subTest(datei=datei):
                t = (WURZEL / datei).read_text(encoding="utf-8")
                self.assertIn("PYTHONUTF8=1", t)
                self.assertLess(t.index("PYTHONUTF8=1"), t.index(befehl))

    def test_der_zugangstest_hat_einen_doppelklick(self):
        """Er wird gebraucht, wenn etwas klemmt – dann ist ein Befehl zum
        Abtippen das Letzte, was hilft."""
        t = (WURZEL / "ZUGANG-PRUEFEN.bat").read_text(encoding="utf-8")
        self.assertIn("-m jusperfect.awstest", t)
        # Ohne pause schliesst sich das Fenster, und der Befund ist weg.
        self.assertIn("pause", t)

    def test_der_befund_bleibt_zum_nachlesen_stehen(self):
        t = (WURZEL / "ZUGANG-PRUEFEN.bat").read_text(encoding="utf-8")
        self.assertIn("zugangstest.txt", t)


class Aufbaupruefung(unittest.TestCase):
    """Es muss auffallen, wenn die Dateien falsch liegen – an einer Stelle.

    In der Kanzlei war beim Auspacken der INNERE Ordner „jusperfect" genommen
    worden statt des äußeren. Dann liegt web.py neben der Startdatei statt in
    einem Unterordner. pip läuft anscheinend durch, installiert aber nichts
    Brauchbares – und der Fehler zeigt sich erst zwei Schritte später als
    „No module named 'jusperfect'". Wer das liest, sucht an der falschen
    Stelle; es hat einen halben Nachmittag gekostet.

    **Bis zum 28.09.2026 stand diese Prüfung in drei Startdateien**, und eine
    der drei Fassungen war schon schwächer: START-JURNODES.bat unterschied
    nicht, ob web.py neben der Startdatei liegt – also den einen Fall, in dem
    man dem Anwender genau sagen kann, was er falsch gemacht hat. So laufen
    Kopien auseinander: nicht durch eine falsche Zeile, sondern dadurch, dass
    eine Verbesserung nur an einer Stelle ankommt.

    Sie steht jetzt in `_UMGEBUNG.bat`, und die Prüfungen halten das fest.
    """

    def _text(self, datei: str) -> str:
        return (WURZEL / datei).read_text(encoding="utf-8")

    def test_die_umgebung_prueft_ob_sich_das_programm_laden_laesst(self):
        t = self._text("_UMGEBUNG.bat")
        self.assertIn('-c "import jusperfect"', t)
        self.assertIn("if not errorlevel 1 goto aufbau_geprueft", t)

    def test_die_pruefung_steht_vor_dem_start(self):
        """Sonst meldet sie sich erst, wenn schon alles schiefgegangen ist.

        In `_UMGEBUNG.bat` heißt „vor dem Start": vor dem Ende der Datei, denn
        gestartet wird erst danach. Geprüft wird deshalb, dass jede Startdatei
        die Umgebung aufruft, **bevor** sie das Programm anwirft.
        """
        for datei, spaeter in (("START-DEMO.bat", "-m jusperfect"),
                               ("START-AWS.bat", "-m jusperfect.awstest"),
                               ("START-JURNODES.bat", "-m jusperfect.awstest")):
            with self.subTest(datei=datei):
                t = self._text(datei)
                self.assertLess(t.index("_UMGEBUNG.bat"), t.index(spaeter))

    def test_die_meldung_nennt_den_haeufigen_fall_beim_namen(self):
        """Eine Meldung, die nur „geht nicht" sagt, hilft niemandem."""
        t = self._text("_UMGEBUNG.bat")
        self.assertIn('if not exist "web.py" goto aufbau_fehlt', t)
        self.assertIn("inner", t.lower())

    def test_die_meldung_nennt_keine_datei_die_niemand_gestartet_hat(self):
        """`%~nx0` hieße hier „_UMGEBUNG.bat" – die klickt niemand an.

        In START-DEMO.bat stand einmal START-AWS.bat in der Meldung, und das
        hat verwirrt. Dieselbe Falle, nur umgekehrt: Der Name der Datei, in der
        eine Meldung steht, ist nicht der Name der Datei, die der Anwender
        gestartet hat.
        """
        block = self._text("_UMGEBUNG.bat")
        anfang = block.index('-c "import jusperfect"')
        self.assertNotIn("%~nx0", block[anfang:])
        self.assertIn("- oder eine andere Startdatei", block)

    def test_ohne_klammernbloecke(self):
        """cmd wertet in Klammernblöcken früher aus, als man denkt.

        Genau daran ist in diesem Projekt schon einmal die Python-Erkennung
        gescheitert. Die Prüfung ist deshalb mit Sprungmarken gebaut.
        """
        t = self._text("_UMGEBUNG.bat")
        anfang = t.index('-c "import jusperfect"')
        ende = t.index(":aufbau_geprueft")
        self.assertNotIn("(", t[anfang:ende])

    def test_keine_startdatei_haelt_eine_eigene_kopie(self):
        """Der eigentliche Punkt: Es darf nur eine Stelle geben.

        Weder die Aufbauprüfung noch die Python-Erkennung noch das Anlegen der
        `.venv` gehört in eine Startdatei. Wer eine davon dort einbaut, bekommt
        hier ein rotes Ergebnis – und nicht erst Wochen später, wenn eine
        Verbesserung in einer der Kopien fehlt.
        """
        verboten = ('-c "import jusperfect"', "py -3.12", "-m venv .venv",
                    ":aufbau_geprueft", ":store_attrappe")
        for pfad in sorted(WURZEL.glob("*.bat")):
            if pfad.name == "_UMGEBUNG.bat":
                continue
            text = pfad.read_text(encoding="ascii")
            for zeichenfolge in verboten:
                with self.subTest(datei=pfad.name, was=zeichenfolge):
                    self.assertNotIn(zeichenfolge, text)

    def test_jede_startdatei_sagt_wie_viele_schritte_sie_hat(self):
        """„[1/4]" bei zwei Schritten ist eine Unwahrheit, die man liest.

        Die Prüfdateien zeigten „[1/4] … [2/4]" und hatten nie einen dritten
        Schritt. Wer das sieht, wartet auf etwas, das nicht kommt.
        """
        erwartet = {"START-DEMO.bat": "3", "START-AWS.bat": "4",
                    "START-JURNODES.bat": "2", "START-KANZLEI.bat": "2",
                    "JURNODES-PRUEFEN.bat": "2", "ABLAGE-PRUEFEN.bat": "2"}
        for datei, zahl in erwartet.items():
            with self.subTest(datei=datei):
                t = self._text(datei)
                self.assertIn('call "%%~dp0_UMGEBUNG.bat" %s' % zahl, t)
        # Und die Datei selbst muss die Zahl auch benutzen.
        umgebung = self._text("_UMGEBUNG.bat")
        self.assertIn("[1/%SCHRITTE%]", umgebung)
        self.assertIn("[2/%SCHRITTE%]", umgebung)

    def test_zeilenenden_bleiben_windowstauglich(self):
        """Eine .bat mit Unix-Zeilenenden bricht auf manchen Rechnern ab."""
        for datei in ("START-DEMO.bat", "START-AWS.bat", "_UMGEBUNG.bat"):
            with self.subTest(datei=datei):
                roh = (WURZEL / datei).read_bytes()
                self.assertEqual(roh.count(b"\n"), roh.count(b"\r\n"))


class GedaechtnisVoreinstellung(unittest.TestCase):
    """Wer das AWS-Gedaechtnis per setx eingerichtet hat, darf es beim Start
    nicht wieder verlieren. Der AWS-Starter setzt deshalb nur eine
    Voreinstellung; ein Wert aus der Umgebung geht vor."""

    def test_aws_starter_ueberschreibt_die_umgebung_nicht(self):
        t = (WURZEL / "START-AWS.bat").read_text(encoding="utf-8")
        self.assertIn("if not defined JUSPERFECT_GEDAECHTNIS set JUSPERFECT_GEDAECHTNIS=lokal", t)
        self.assertNotRegex(t, r"^\s*set JUSPERFECT_GEDAECHTNIS=", "harte Zuweisung gefunden")

    def test_die_voreinstellung_bleibt_lokal(self):
        e = _einstellungen_aus("START-AWS.bat")
        self.assertEqual(e.gedaechtnis, "lokal")

    def test_mit_setx_wird_es_aws(self):
        """Dieselbe Startdatei, aber die Umgebung sagt aws - dann gilt aws."""
        e = _einstellungen_aus(
            "START-AWS.bat",
            JUSPERFECT_GEDAECHTNIS="aws",
            JUSPERFECT_GEDAECHTNIS_BUCKET="jusperfect-test-gedaechtnis-000000000000",
            JUSPERFECT_KMS_SCHLUESSEL_ID="alias/jusperfect-gedaechtnis",
        )
        self.assertEqual(e.gedaechtnis, "aws")


class Startdateien(unittest.TestCase):
    def test_beide_starter_schalten_das_gedaechtnis_ein(self):
        """Ohne Gedächtnis lebt eine Sitzung 15 Minuten – ein Mandat länger."""
        for datei in ("START-DEMO.bat", "START-AWS.bat"):
            with self.subTest(datei=datei):
                e = _einstellungen_aus(datei)
                self.assertEqual(e.gedaechtnis, "lokal")
                self.assertEqual(str(e.gedaechtnis_pfad), ".jusperfect-gedaechtnis")

    def test_beide_starter_bleiben_bei_den_testakten(self):
        for datei in ("START-DEMO.bat", "START-AWS.bat"):
            with self.subTest(datei=datei):
                self.assertEqual(_einstellungen_aus(datei).jurnodes_adapter, "fixture")

    def test_der_aktenordner_laesst_sich_vorher_setzen(self):
        """Sonst ist die grosse Testakte auf dem beschriebenen Weg nicht zu oeffnen.

        GROSSE-TESTAKTE.bat endet mit der Anweisung

            set JUSPERFECT_FIXTURE_PFAD=testdaten\\grosse-akte
            START-AWS.bat

        Das ging ins Leere: In beiden Startern stand ein unbedingtes ``set``,
        das die eigene Wahl still ueberschrieb. In der Aktenliste standen
        danach wieder nur die vier kleinen Akten, ohne einen Hinweis darauf,
        warum.
        """
        for datei in ("START-DEMO.bat", "START-AWS.bat"):
            with self.subTest(datei=datei):
                for name in ("JUSPERFECT_FIXTURE_PFAD", "JUSPERFECT_NUTZER_DATEI"):
                    zeilen = [z.strip() for z in (WURZEL / datei).read_text(encoding="utf-8").splitlines()
                              if re.match(rf"\s*(?:if not defined \w+\s+)?set\s+{name}=", z)]
                    self.assertEqual(len(zeilen), 1, f"{name} mehrfach gesetzt")
                    self.assertTrue(zeilen[0].startswith(f"if not defined {name} "),
                                    f"{name} wird unbedingt gesetzt: {zeilen[0]}")

    def test_der_weg_zur_grossen_testakte_stimmt(self):
        """Die Anleitung in GROSSE-TESTAKTE.bat und der Ordner muessen zusammenpassen."""
        anleitung = (WURZEL / "GROSSE-TESTAKTE.bat").read_text(encoding="utf-8")
        self.assertIn("set JUSPERFECT_FIXTURE_PFAD=testdaten\\grosse-akte", anleitung)
        gesetzt = _einstellungen_aus("START-AWS.bat",
                                     JUSPERFECT_FIXTURE_PFAD="testdaten/grosse-akte")
        self.assertEqual(str(gesetzt.fixture_pfad).replace("\\", "/"), "testdaten/grosse-akte")

    def test_der_gedaechtnisordner_ist_von_der_versionsverwaltung_ausgenommen(self):
        """Sonst landete der Testspeicher im nächsten ZIP und im Repository."""
        self.assertIn(".jusperfect-gedaechtnis/",
                      (WURZEL / ".gitignore").read_text(encoding="utf-8"))

    def test_startdateien_sind_reines_ascii(self):
        """cmd.exe stellt Umlaute je nach Codepage falsch dar."""
        for datei in ("START-DEMO.bat", "START-AWS.bat", "GEDAECHTNIS-LEEREN.bat",
                      "ZUGANG-EINTRAGEN.bat"):
            with self.subTest(datei=datei):
                (WURZEL / datei).read_text(encoding="ascii")

    def test_leeren_fragt_nach_und_trifft_nur_den_testspeicher(self):
        text = (WURZEL / "GEDAECHTNIS-LEEREN.bat").read_text(encoding="ascii")
        self.assertIn("set /p ANTWORT", text, "Löschen ohne Rückfrage wäre unhöflich.")
        # Genau ein rmdir, und zwar auf den Testspeicher.
        gefunden = re.findall(r"rmdir\s+/s\s+/q\s+\"([^\"]+)\"", text)
        self.assertEqual(gefunden, [".jusperfect-gedaechtnis"])


if __name__ == "__main__":
    unittest.main()


class Zugangsdatei(unittest.TestCase):
    """Der Weg zu den AWS-Schluesseln darf nicht an einem Download haengen."""

    def test_es_gibt_einen_weg_ohne_die_aws_cli(self):
        self.assertTrue((WURZEL / "ZUGANG-EINTRAGEN.bat").is_file())

    def test_der_zugangstest_nennt_diesen_weg(self):
        """Wer hier strandet, liest genau diese Meldung."""
        quelle = (WURZEL / "jusperfect" / "awstest.py").read_text(encoding="utf-8")
        self.assertIn("ZUGANG-EINTRAGEN.bat", quelle)
        self.assertNotIn("aws configure", quelle)

    def test_der_aws_starter_nennt_ihn_ebenfalls(self):
        self.assertIn("ZUGANG-EINTRAGEN.bat",
                      (WURZEL / "START-AWS.bat").read_text(encoding="ascii"))


class Pythonwahl(unittest.TestCase):
    """Auf einem frischen Rechner bietet python.org 3.13 und neuer an.

    ``py -3`` nimmt die neueste Installation. Ohne gezielte Abfrage liefe die
    Einrichtung genau dort auf, wo sie am teuersten ist: beim allerersten
    Doppelklick, mit einer Meldung, die nichts über die Ursache sagt.
    """

    def _text(self, datei: str) -> str:
        return (WURZEL / datei).read_text(encoding="ascii")

    def test_starter_fragen_gezielt_nach_311_oder_312(self):
        # Nur noch _UMGEBUNG.bat: Der Block ist am 25.09.2026 dorthin gewandert,
        # damit START-JURNODES.bat die Umgebung selbst anlegen kann, statt den
        # Anwender erst zu den Testakten zu schicken. START-DEMO.bat behielt
        # bis zum 28.09.2026 eine eigene Kopie und wich schon ab.
        for datei in ("_UMGEBUNG.bat",):
            with self.subTest(datei=datei):
                text = self._text(datei)
                self.assertIn("py -3.12", text)
                self.assertIn("py -3.11", text)
                # "py -3" darf nur noch zur Unterscheidung der Fehlermeldung
                # dienen, nicht mehr zur Auswahl.
                self.assertNotIn('set "PYCMD=py -3"', text)

    def test_die_versionsgrenze_stimmt_mit_pyproject_ueberein(self):
        """Sonst driften Startdatei und Paketangabe auseinander."""
        pyproject = (WURZEL / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('requires-python = ">=3.11,<3.13"', pyproject)
        for datei in ("_UMGEBUNG.bat",):
            with self.subTest(datei=datei):
                self.assertIn("(3,11) <= sys.version_info < (3,13)", self._text(datei))

    def test_zwei_verschiedene_meldungen_fuer_zwei_verschiedene_lagen(self):
        """„Python fehlt“ wäre falsch und teuer, wenn Python längst da ist."""
        for datei in ("_UMGEBUNG.bat",):
            with self.subTest(datei=datei):
                text = self._text(datei)
                self.assertIn(":falsche_fassung", text)
                self.assertIn(":kein_python", text)
                self.assertIn("kann bleiben, sie stoert nicht", text)


class Funktionsprobe(unittest.TestCase):
    """Der Weg, auf dem die Kanzlei vor AWS alles einmal durchgeht.

    Aus der Kanzlei: „bevor wir AWS einrichten, erst alle Funktionen mit einer
    Testakte ausprobieren, oder?" Mit vierzig Mausklicks macht das nach der
    dritten Änderung niemand mehr; als ein Aufruf schon.
    """

    WURZEL = Path(__file__).resolve().parent.parent

    def test_der_starter_gibt_es_und_hat_crlf(self):
        pfad = self.WURZEL / "FUNKTIONSPROBE.bat"
        self.assertTrue(pfad.is_file())
        self.assertIn(b"\r\n", pfad.read_bytes())

    def test_er_ruft_das_werkzeug(self):
        text = (self.WURZEL / "FUNKTIONSPROBE.bat").read_text(encoding="utf-8")
        self.assertIn("werkzeug\\funktionsprobe.py", text)

    def test_er_sagt_es_wenn_etwas_fehlschlaegt(self):
        """Ein Probelauf, dessen Ergebnis man übersieht, ist keiner."""
        text = (self.WURZEL / "FUNKTIONSPROBE.bat").read_text(encoding="utf-8")
        self.assertIn("errorlevel", text)
        self.assertIn("fehlgeschlagen", text)

    def test_das_werkzeug_meldet_fehlschlaege_nach_aussen(self):
        quelle = (self.WURZEL / "werkzeug" / "funktionsprobe.py").read_text(encoding="utf-8")
        self.assertIn("return 1 if fehler else 0", quelle)

    def test_es_sagt_was_es_nicht_pruefen_kann(self):
        """Sonst hält man 34 Haken für den Beweis, dass die Inhalte stimmen."""
        quelle = (self.WURZEL / "werkzeug" / "funktionsprobe.py").read_text(encoding="utf-8")
        self.assertIn("NICHT geprüft", quelle)
        self.assertIn("entscheidet das Modell", quelle)


class DieModelleInDerStartdatei(unittest.TestCase):
    """Welches Modell welche Arbeit tut – so, wie es die Kanzlei doppelklickt.

    Aus der Kanzlei: „Das Programm soll je nach Aufgabe unterschiedliche
    Modelle eintragen." Eine Kennung in der falschen Form fällt sonst erst beim
    ersten Aufruf auf, und dann sieht sie aus wie eine fehlende Freischaltung.
    """

    def setUp(self) -> None:
        self.e = _einstellungen_aus("START-AWS.bat", JUSPERFECT_ANBIETER="bedrock")

    def test_das_starke_modell_tut_die_denkende_arbeit(self):
        for funktion in ("frage", "analyse", "entwurf"):
            with self.subTest(funktion=funktion):
                self.assertIn("opus", self.e.modell_fuer(funktion))

    def test_die_eingangspruefung_bekommt_das_kleine_modell(self):
        """Sie ist Fliessbandarbeit – dort ist nichts zu verlieren."""
        self.assertIn("haiku", self.e.modell_fuer("triage"))

    def test_das_aktengedaechtnis_bekommt_das_starke_modell(self):
        """Hier stand einmal Haiku, aus Kostengründen. Gemessen am 17.09.2026:

        Zwei Läufe über die große Testakte, sonst gleich, Unterschied allein das
        einlesende Modell. Mit Haiku 3 von 5 Funden, mit Opus 5 von 5. Im
        Haiku-Lauf fehlten im gesamten Ergebnis zwei Dokumente – D-002, das
        Leistungsverzeichnis, und D-008, die Mängelanzeige. Der Vertrag und die
        Rüge.

        Die Analyse liest danach nur noch das Gedächtnis, nicht mehr die
        Dokumente. Was hier wegfällt, findet später kein Modell mehr, so stark
        es sei: Der Lauf mit dem schlechteren Ergebnis hatte das bessere
        Analysemodell.

        Mehrkosten 2,05 € – einmal je Akte, nicht je Frage. Wer das zurückdreht,
        soll wissen, was er aufgibt; deshalb steht es hier und nicht nur in
        einem Kommentar.
        """
        self.assertIn("opus", self.e.modell_fuer("gedaechtnis"))

    def test_jede_kennung_hat_die_bedrock_form(self):
        """Ein blosses „claude-opus-5" ist die Kennung der Anthropic-Schnittstelle.

        Bedrock weist sie ab – und zwar mit derselben Meldung wie eine fehlende
        Freischaltung, weshalb man an der falschen Stelle sucht.
        """
        for funktion, kennung in self.e.modelle_uebersicht().items():
            with self.subTest(funktion=funktion):
                self.assertTrue(kennung.startswith("eu.anthropic.claude-"), kennung)

    def test_die_richtlinie_deckt_sie_alle_ab(self):
        from jusperfect.services.selbsttest import Selbsttest, UNGEPRUEFT

        zeilen = Selbsttest(self.e).ausfuehren().modelle
        for zeile in zeilen:
            with self.subTest(modell=zeile.kennung):
                self.assertEqual(UNGEPRUEFT, zeile.zustand, zeile.satz)


class DasMessgeraetMisstDenBetrieb(unittest.TestCase):
    """PRUEFBOGEN.bat muss dieselben Modelle setzen wie die Startdateien.

    Der Anspruch steht in PRUEFBOGEN.bat selbst: „gemessen wird, womit die
    Kanzlei arbeitet." Bis zum 28.09.2026 war er unerfüllt. Die Datei löschte
    ``JUSPERFECT_MODELL_GEDAECHTNIS``, der Bogen fiel auf das kleine Modell
    zurück und las mit Haiku ein – während alle drei Startdateien Opus setzen.

    Der Lauf vom 28.09.2026 verlor daraufhin die 402,00 m² Dämmfläche aus
    D-002, genau wie der Haiku-Lauf vom 17.09.2026: dieselben 0,51 € Einlesen,
    dieselben 4 von 5 Zahlen. Gemeldet wurde das nicht als Modellunterschied,
    sondern als Mangel des Programms – und danach hätte jemand gesucht.

    Es ist der Fehler, der in diesem Projekt an einem Tag fünfmal aufgetreten
    ist: **Eine Probe, die anders fragt als der Betrieb, prüft etwas anderes
    als den Betrieb.** Ein Messgerät, das falsch misst, ist schlimmer als
    keines – es gibt Sicherheit, wo keine ist.

    Deshalb hält diese Prüfung die Dateien gegeneinander, statt in jeder
    einzeln einen Wert abzufragen. Wird der Betrieb umgestellt, fällt der
    Bogen auf, solange er noch das alte Modell misst.
    """

    def setUp(self) -> None:
        self.bogen = _einstellungen_aus("PRUEFBOGEN.bat", JUSPERFECT_ANBIETER="bedrock")
        self.betrieb = _einstellungen_aus("START-AWS.bat", JUSPERFECT_ANBIETER="bedrock")

    def test_jede_der_sechs_arbeiten_bekommt_dasselbe_modell(self):
        self.assertEqual(self.betrieb.modelle_uebersicht(),
                         self.bogen.modelle_uebersicht())

    def test_auch_das_einlesen_das_teuerste_und_folgenreichste(self):
        """Ausdrücklich noch einmal allein: Hier ist es schiefgegangen.

        Die Analyse arbeitet danach nur mit dem, was das Einlesen behalten hat.
        Ein Unterschied an dieser Stelle verfälscht jede Zahl des Bogens, ohne
        dass er es meldet.
        """
        self.assertEqual(self.betrieb.modell_fuer("gedaechtnis"),
                         self.bogen.modell_fuer("gedaechtnis"))
        self.assertIn("opus", self.bogen.modell_fuer("gedaechtnis"))

    def test_der_bogen_setzt_das_einlesemodell_selbst(self):
        """Leer heisst „nimm das kleine" – und genau das war der Fehler.

        Ein Messgerät darf keine Einstellung dem Zufall oder einer dauerhaften
        Windows-Einrichtung überlassen. Diese Prüfung liest die Datei im
        Wortlaut, weil eine leere Zeile über ``Einstellungen`` nicht mehr von
        einer fehlenden zu unterscheiden ist.
        """
        text = (WURZEL / "PRUEFBOGEN.bat").read_text(encoding="utf-8")
        gesetzt = [z.strip() for z in text.splitlines()
                   if z.strip().startswith("set JUSPERFECT_MODELL_GEDAECHTNIS=")]
        self.assertEqual(1, len(gesetzt), gesetzt)
        self.assertTrue(gesetzt[0].endswith("anthropic.claude-opus-4-6-v1"), gesetzt[0])


class DasSchutzgelaenderInDerStartdatei(unittest.TestCase):
    """Die Zeile für die Guardrail-Kennung muss in beiden Startern stehen.

    In `AWS-EINRICHTEN.md`, Schritt 9, heißt es, die Kennung sei „in
    START-AWS.bat einzutragen, bei den übrigen set-Zeilen". Dort gab es die
    Zeile aber gar nicht — wer der Anleitung folgte, suchte sie und musste sie
    selbst anlegen. Eine Anleitung, die auf eine Zeile zeigt, die es nicht
    gibt, ist schlimmer als keine: Sie lässt den Leser an sich selbst zweifeln.
    """

    def test_beide_starter_haben_die_zeile(self):
        for datei in ("START-AWS.bat", "START-KANZLEI.bat"):
            with self.subTest(datei=datei):
                text = (WURZEL / datei).read_text(encoding="utf-8")
                self.assertTrue(
                    re.search(r"^set JUSPERFECT_GUARDRAIL_ID=", text, re.MULTILINE),
                    f"{datei} hat keine Zeile zum Eintragen")

    def test_bei_den_testakten_darf_sie_leer_bleiben(self):
        """Ohne echte Akten ist das Geländer freiwillig – sonst stünde vor dem
        ersten Doppelklick eine AWS-Konsole."""
        e = _einstellungen_aus("START-AWS.bat", JUSPERFECT_ANBIETER="bedrock")
        self.assertIsNone(e.guardrail_id)
        e.pruefen()

    def test_die_eingetragene_kennung_kommt_an(self):
        e = _einstellungen_aus("START-AWS.bat", JUSPERFECT_ANBIETER="bedrock",
                               JUSPERFECT_GUARDRAIL_ID="gr7k2m9qx4vp")
        self.assertEqual("gr7k2m9qx4vp", e.guardrail_id)
        # Ohne eigene Angabe nimmt jusperfect den Arbeitsstand; eine Version
        # muss in der Konsole also nicht veröffentlicht werden.
        self.assertEqual("DRAFT", e.guardrail_version)

    def test_die_anleitung_zeigt_auf_die_richtige_datei(self):
        """Der Satz in Schritt 9 und die Startdatei müssen zusammenpassen."""
        schritt9 = (WURZEL / "AWS-EINRICHTEN.md").read_text(encoding="utf-8")
        self.assertIn("set JUSPERFECT_GUARDRAIL_ID=", schritt9)
        self.assertIn("START-AWS.bat", schritt9)


class DerStarterFuerDieSchnittstelle(unittest.TestCase):
    """START-JURNODES.bat – echte Akten über die REST-Schnittstelle.

    Hier müssen vier Einstellungen zugleich stimmen, und drei Angaben liegen
    ausserhalb der Datei: Adresse, Benutzer und Token stehen in der Umgebung
    des Windows-Kontos. Sie gehören nicht in den Programmordner – der wird als
    ZIP weitergegeben.
    """

    def _text(self) -> str:
        return (WURZEL / "START-JURNODES.bat").read_text(encoding="ascii")

    def test_es_gibt_ihn_und_er_ist_windowstauglich(self):
        roh = (WURZEL / "START-JURNODES.bat").read_bytes()
        self.assertEqual(roh.count(b"\n"), roh.count(b"\r\n"), "Eine .bat braucht CRLF.")

    def test_kein_token_in_der_datei(self):
        """Der Programmordner wird weitergegeben."""
        text = self._text()
        self.assertNotIn("set JURNODES_API_KEY=", text)
        self.assertNotIn("set JUSPERFECT_JURNODES_URL=", text)
        self.assertIn("JURNODES-ZUGANG.bat", text)

    def test_er_bricht_ab_bevor_etwas_laeuft(self):
        text = self._text()
        for name in ("JUSPERFECT_GUARDRAIL_ID", "JUSPERFECT_JURNODES_URL",
                     "JURNODES_API_USER", "JURNODES_API_KEY"):
            with self.subTest(name=name):
                self.assertIn(f"if not defined {name} goto", text)

    def test_die_aufstellung_ist_zulaessig(self):
        """Vier Einstellungen müssen einander vertragen – das fällt sonst
        erst der Kanzlei auf."""
        e = _einstellungen_aus("START-JURNODES.bat",
                               JUSPERFECT_ANBIETER="bedrock",
                               JUSPERFECT_GUARDRAIL_ID="gr7k2m9qx4vp",
                               JUSPERFECT_JURNODES_URL="https://x.jur-nodes.net/api/extern/v1/x")
        self.assertEqual("http", e.jurnodes_adapter)
        e.pruefen()

    def test_das_gedaechtnis_liegt_in_aws(self):
        """Eingeschaltet am 01.10.2026 auf ausdrückliche Anweisung der Kanzlei.

        Vorher stand hier „aus". Der Grund dafür ist nicht entfallen, sondern
        erledigt: In die jur|nodes-Akte wird nach wie vor nichts geschrieben —
        jur|nodes ersetzt eine vorhandene Datei nicht, und das Recht „Datei
        löschen" gälte für jede Datei des Bestands. Das Gedächtnis liegt
        stattdessen in S3, verschlüsselt mit dem Schlüssel der Kanzlei.

        **Was sich rechtlich ändert:** jusperfect legt damit erstmals dauerhaft
        Akteninhalt außerhalb von jur|nodes ab — Mandatsgut, kein Protokoll.
        Derselbe Auftragsverarbeiter wie für die Verarbeitung, also kein neuer
        AV-Vertrag; Ziffer 6.2 des Verarbeitungsverzeichnisses muss es aber
        nennen, und die ist offen.
        """
        e = _einstellungen_aus("START-JURNODES.bat",
                               JUSPERFECT_ANBIETER="bedrock",
                               JUSPERFECT_GUARDRAIL_ID="gr7k2m9qx4vp",
                               JUSPERFECT_JURNODES_URL="https://x.jur-nodes.net/api/x")
        self.assertEqual("aws", e.gedaechtnis)

    def test_ablageort_und_schluessel_sind_keine_platzhalter(self):
        """Ein Platzhalter ist schlimmer als eine Lücke — Lehre vom 25.09.2026.

        Stünde hier noch HIER-DEN-BUCKETNAMEN, liefe das Programm an und
        scheiterte erst beim ersten Ablegen, mit einer Meldung von S3.
        """
        e = _einstellungen_aus("START-JURNODES.bat",
                               JUSPERFECT_ANBIETER="bedrock",
                               JUSPERFECT_GUARDRAIL_ID="gr7k2m9qx4vp",
                               JUSPERFECT_JURNODES_URL="https://x.jur-nodes.net/api/x")
        self.assertEqual("dortschy-thunert-jusperfect-aktengedaechtnis", e.gedaechtnis_bucket)
        self.assertTrue(e.kms_schluessel_id)
        for wort in ("HIER-", "PLATZHALTER", "IHRE-"):
            self.assertNotIn(wort, e.gedaechtnis_bucket + (e.kms_schluessel_id or ""))

    def test_der_weg_zurueck_steht_daneben(self):
        """Eine Einstellung, die etwas Dauerhaftes anlegt, braucht den Satz,
        wie man sie wieder abstellt - sonst sucht in drei Monaten jemand im
        Quelltext."""
        text = (WURZEL / "START-JURNODES.bat").read_text(encoding="ascii")
        self.assertIn("Zurueckgeschaltet wird", text)
        self.assertIn("GEDAECHTNIS-LEEREN.bat", text)
        self.assertIn("JUSPERFECT_GEDAECHTNIS_BUCKET", text)

    def test_ein_lokales_gedaechtnis_waere_unzulaessig(self):
        """Es schreibt unverschlüsselten Klartext auf die Platte. Mit echten
        Akten weist das Programm es ab – die Sperre soll halten, auch wenn
        jemand die Zeile in dieser Datei ändert."""
        from jusperfect.config import KonfigurationsFehler
        with self.assertRaises(KonfigurationsFehler):
            _einstellungen_aus("START-JURNODES.bat",
                               JUSPERFECT_ANBIETER="bedrock",
                               JUSPERFECT_GUARDRAIL_ID="gr7k2m9qx4vp",
                               JUSPERFECT_JURNODES_URL="https://x.jur-nodes.net/api/x",
                               JUSPERFECT_GEDAECHTNIS="lokal")

    def test_er_warnt_vor_dem_ersten_echten_aktentext(self):
        text = self._text()
        self.assertIn("ECHTER Aktentext", text)
        self.assertIn("pause", text)


class WerInDieserKanzleiArbeitet(unittest.TestCase):
    """Aus der Kanzlei, 23.09.2026: „Sehr merkwürdig sind auch die Testnutzer
    als Anwälte."

    Auf dem Anmeldebild standen „RA Dr. Weber (Testnutzer)", „RAin Kaminski"
    und „ReFa Lorenz" – erfundene Leute, neben echten Akten. Beide Starter für
    den Echtbetrieb setzten `JUSPERFECT_NUTZER_DATEI` nicht und fielen damit
    auf `testdaten/nutzer.json` zurück.

    Das ist nicht nur unschön. Der gewählte Name steht im
    Verarbeitungsnachweis jedes Modellaufrufs (`domain/models.py`,
    `Nutzungseintrag`), und er entscheidet, welche Akten sichtbar sind. Ein
    erfundener Name an dieser Stelle macht den Nachweis wertlos.
    """

    def test_beide_echtbetriebs_starter_nennen_die_kanzleidatei(self):
        for datei in ("START-KANZLEI.bat", "START-JURNODES.bat"):
            with self.subTest(datei=datei):
                text = (WURZEL / datei).read_text(encoding="ascii")
                self.assertIn("set JUSPERFECT_NUTZER_DATEI=nutzer-kanzlei.json", text)

    def test_die_testakten_starter_bleiben_bei_den_testnutzern(self):
        """Dort gehören sie hin – und dort stört kein erfundener Name."""
        for datei in ("START-DEMO.bat", "START-AWS.bat"):
            with self.subTest(datei=datei):
                e = _einstellungen_aus(datei)
                self.assertEqual("testdaten/nutzer.json", str(e.nutzer_datei).replace("\\", "/"))

    def test_die_kanzleidatei_gibt_es_und_sie_ist_lesbar(self):
        import json
        daten = json.loads((WURZEL / "nutzer-kanzlei.json").read_text(encoding="utf-8"))
        kennungen = [n["id"] for n in daten["nutzer"]]
        self.assertIn("dortschy", kennungen)
        self.assertIn("thunert", kennungen)

    def test_jede_kennung_kommt_nur_einmal_vor(self):
        """Zwei Thunert in der Kanzlei: Der Anwalt und Marie Thunert. Waeren
        beide „thunert", arbeitete die eine unter dem Namen des anderen - und
        der Verarbeitungsnachweis wiese es so aus."""
        import json
        daten = json.loads((WURZEL / "nutzer-kanzlei.json").read_text(encoding="utf-8"))
        kennungen = [n["id"] for n in daten["nutzer"]]
        self.assertEqual(len(kennungen), len(set(kennungen)), kennungen)

    def test_der_gastzugang_sieht_alle_akten(self):
        """Ich hatte ihn vorsichtshalber auf keine Akte gesetzt – ein Gast ist
        sonst jemand, dem man etwas Bestimmtes zeigt. Die Kanzlei hat am
        23.09.2026 aufgeklärt: Es ist kein Gast, sondern ein **wechselnder
        Mitarbeiter**. Dann gilt für ihn, was für die übrigen gilt.

        Der Name bleibt trotzdem der schwächste Punkt der Liste: Unter
        „Gastzugang" im Verarbeitungsnachweis steht nicht, wer gearbeitet hat.
        Wer das genauer braucht, legt die Person mit ihrem Namen an."""
        from jusperfect.security.berechtigungen import DateiBerechtigungen

        gast = DateiBerechtigungen.aus_datei(WURZEL / "nutzer-kanzlei.json")._laden("gast")
        self.assertIsNotNone(gast, "Der Gastzugang fehlt.")
        self.assertTrue(gast.darf_akte("X-105-2026"))

    def test_die_mitarbeiter_sehen_alle_akten(self):
        """So von der Kanzlei entschieden, 23.09.2026."""
        from jusperfect.security.berechtigungen import DateiBerechtigungen

        b = DateiBerechtigungen.aus_datei(WURZEL / "nutzer-kanzlei.json")
        for kennung in ("lehmann", "pfeifer", "kuhn", "m.thunert",
                        "derakhshan", "uckermark"):
            with self.subTest(kennung=kennung):
                self.assertTrue(b._laden(kennung).darf_akte("egal"))

    def test_sie_traegt_keinen_erfundenen_namen(self):
        text = (WURZEL / "nutzer-kanzlei.json").read_text(encoding="utf-8")
        for erfunden in ("Weber", "Kaminski", "Lorenz", "Testnutzer"):
            self.assertNotIn(erfunden, text, f"{erfunden} gehört zu den Testakten.")

    def test_sie_sagt_selbst_wie_man_jemanden_hinzufuegt(self):
        """Eine JSON-Datei, die ein Nichtprogrammierer bearbeiten soll, muss
        die Anleitung bei sich tragen."""
        import json
        daten = json.loads((WURZEL / "nutzer-kanzlei.json").read_text(encoding="utf-8"))
        hinweis = " ".join(daten["_hinweis"])
        self.assertIn("hinzufuegen", hinweis)
        self.assertIn("kein Kennwort", hinweis.replace("KEIN", "kein"))

    def test_das_programm_nimmt_sie_an(self):
        from jusperfect.security.berechtigungen import DateiBerechtigungen

        b = DateiBerechtigungen.aus_datei(WURZEL / "nutzer-kanzlei.json")
        kennungen = {n.id for n in b.auflisten()}
        # Nicht die ganze Liste abschreiben: Sie waechst, und ein Test, der
        # bei jeder neuen Mitarbeiterin bricht, wird irgendwann angepasst,
        # ohne dass jemand hinsieht. Geprueft wird, dass die Datei ankommt.
        self.assertIn("dortschy", kennungen)
        self.assertIn("gast", kennungen)
        self.assertGreaterEqual(len(kennungen), 2)


# ---------------------------------------------------------------------------
# Was eine Einrichtung ueberleben soll, gehoert nicht in den Programmordner
#
# Am 25.09.2026 stand die Kennung des Schutzgelaenders in START-JURNODES.bat.
# Die Kanzlei packte eine neue Fassung aus, die Datei wurde ueberschrieben,
# und der Start meldete "Es fehlt das Schutzgelaender" - an einem Tag, an dem
# es um etwas ganz anderes ging. Dieselbe Falle wartet auf jede Angabe, die
# wir kuenftig in eine .bat schreiben.
# ---------------------------------------------------------------------------


def test_das_gelaender_wird_nicht_mehr_in_die_startdatei_getippt() -> None:
    """In der Startdatei steht kein ausgefuellter Wert mehr - und sie sagt,
    wohin er stattdessen gehoert."""
    text = (WURZEL / "START-JURNODES.bat").read_text(encoding="utf-8")
    assert "JURNODES-ZUGANG.bat" in text, \
        "Die Startdatei muss sagen, wo die Kennung eingetragen wird."
    for zeile in text.splitlines():
        blank = zeile.strip()
        if blank.lower().startswith("set jusperfect_guardrail_id="):
            rest = blank.split("=", 1)[1].strip().strip('"')
            assert rest.startswith("%"), \
                f"Ein fester Wert in der Startdatei geht beim Auspacken verloren: {blank!r}"


def test_der_zugang_hinterlegt_auch_das_gelaender() -> None:
    """Sonst bliebe es beim Eintippen von Hand."""
    from jusperfect.jurnodeszugang import FELDER

    namen = [name for name, _, _ in FELDER]
    assert "JUSPERFECT_GUARDRAIL_ID" in namen
    text = (WURZEL / "JURNODES-ZUGANG.bat").read_text(encoding="utf-8")
    assert "Schutzgelaender" in text, \
        "Wer die Datei oeffnet, muss sehen, dass sie auch dafuer da ist."


# ---------------------------------------------------------------------------
# Die alte Kennung sucht das Programm selbst
#
# Die erste Anweisung an die Kanzlei lautete: alten Ordner suchen, die .bat
# mit Rechtsklick bearbeiten, Zeile 25, hinter dem Gleichheitszeichen
# markieren, kopieren, schliessen ohne zu speichern. Die Antwort darauf war
# "aender du das". Eine Anleitung, die den Anwender in eine Programmdatei
# schauen laesst, ist keine Loesung.
# ---------------------------------------------------------------------------


def _alter_ordner(wurzel, name: str, zeile: str):
    ordner = wurzel / name
    ordner.mkdir()
    (ordner / "START-JURNODES.bat").write_text(
        "@echo off\nREM Beispiel\n" + zeile + "\nset JUSPERFECT_ANBIETER=bedrock\n",
        encoding="utf-8")
    return ordner


def test_die_kennung_wird_im_nachbarordner_gefunden(tmp_path) -> None:
    """Der haeufigste Fall: neben dem neuen Ordner liegt der alte."""
    from jusperfect.jurnodeszugang import gelaender_aus_alter_fassung

    _alter_ordner(tmp_path, "jusperfect-alt",
                  "set JUSPERFECT_GUARDRAIL_ID=gr7k2m9qx4vp")
    neu = tmp_path / "jusperfect-neu"
    neu.mkdir()
    gefunden = gelaender_aus_alter_fassung(neu)
    assert gefunden is not None
    assert gefunden[0] == "gr7k2m9qx4vp"


def test_anfuehrungszeichen_und_leerzeichen_stoeren_nicht(tmp_path) -> None:
    """Beides kommt beim Einfuegen aus einer Zwischenablage mit und ist auf
    dem Schirm nicht zu sehen."""
    from jusperfect.jurnodeszugang import gelaender_aus_alter_fassung

    _alter_ordner(tmp_path, "alt", 'set "JUSPERFECT_GUARDRAIL_ID=xy99  "')
    neu = tmp_path / "neu"
    neu.mkdir()
    gefunden = gelaender_aus_alter_fassung(neu)
    assert gefunden is not None
    assert gefunden[0] == "xy99"


def test_eine_leere_zeile_gilt_nicht_als_fund(tmp_path) -> None:
    """Sonst schluege die Suche bei jedem frisch ausgepackten Ordner an und
    trueg eine leere Kennung ein - schlimmer als gar kein Fund."""
    from jusperfect.jurnodeszugang import gelaender_aus_alter_fassung

    _alter_ordner(tmp_path, "alt", "set JUSPERFECT_GUARDRAIL_ID=")
    neu = tmp_path / "neu"
    neu.mkdir()
    assert gelaender_aus_alter_fassung(neu) is None


def test_eine_hilfsvariable_gilt_nicht_als_fund(tmp_path) -> None:
    """Die neue Fassung setzt die Kennung aus einer Variablen. Was mit %
    beginnt, ist ein Platzhalter und keine Kennung."""
    from jusperfect.jurnodeszugang import gelaender_aus_alter_fassung

    _alter_ordner(tmp_path, "alt",
                  'set "JUSPERFECT_GUARDRAIL_ID=%GELAENDER_VON_HAND%"')
    neu = tmp_path / "neu"
    neu.mkdir()
    assert gelaender_aus_alter_fassung(neu) is None


def test_der_eigene_ordner_wird_uebersprungen(tmp_path) -> None:
    """Sonst faende sich das Programm selbst und meldete einen Fund, der
    keiner ist."""
    from jusperfect.jurnodeszugang import gelaender_aus_alter_fassung

    eigen = _alter_ordner(tmp_path, "hier",
                          "set JUSPERFECT_GUARDRAIL_ID=nichtnehmen")
    assert gelaender_aus_alter_fassung(eigen) is None


def test_die_suche_schreibt_nichts(tmp_path) -> None:
    """Sie sieht in fremde Ordner. Sie fasst dort nichts an."""
    from jusperfect.jurnodeszugang import gelaender_aus_alter_fassung

    alt = _alter_ordner(tmp_path, "alt", "set JUSPERFECT_GUARDRAIL_ID=abc")
    datei = alt / "START-JURNODES.bat"
    vorher = datei.read_bytes()
    bestand = sorted(q.name for q in tmp_path.rglob("*"))
    neu = tmp_path / "neu"
    neu.mkdir()
    gelaender_aus_alter_fassung(neu)
    assert datei.read_bytes() == vorher
    assert sorted(q.name for q in tmp_path.rglob("*")) == sorted(bestand + ["neu"])


def test_bei_fehlenden_angaben_wird_der_stand_gezeigt() -> None:
    """Sonst bleibt nur Raten.

    Am 25.09.2026 sagte die Meldung "es fehlt das Schutzgelaender" und
    danach, wie man es eintraegt. Nach dem Eintragen kam sie wieder - und
    die Kanzlei konnte nicht sehen, ob der Wert gar nicht angekommen war
    oder das Fenster nur zu alt. Zwei ganz verschiedene Ursachen, eine
    Meldung.
    """
    text = (WURZEL / "START-JURNODES.bat").read_text(encoding="utf-8")
    assert ":stand_zeigen" in text
    assert "in Ihrem Windows-Konto" in text
    for zeile in ("Adresse:", "Benutzer:", "Token:", "Schutzgelaender:"):
        assert zeile in text, f"Die Uebersicht muss {zeile!r} nennen."
    assert "FEHLT" in text, "Was fehlt, muss als fehlend dastehen."
    assert "%JURNODES_API_KEY%" not in text, \
        "Der Token gehoert nicht auf den Schirm - nur, DASS er da ist."


# ---------------------------------------------------------------------------
# Ein Platzhalter ist schlimmer als eine Luecke
#
# Am 25.09.2026 stand im Windows-Konto der Kanzlei "IHRE-KENNUNG" - woertlich
# der Platzhalter aus der Anleitung. Die Pruefung "ist etwas eingetragen?" war
# zufrieden, das Programm startete, und erst der erste Modellaufruf scheiterte:
# im Browser eine graue Flaeche ohne Grund. Wer eine Anleitung schreibt, muss
# damit rechnen, dass sie befolgt wird.
# ---------------------------------------------------------------------------


def test_der_platzhalter_aus_der_anleitung_wird_erkannt() -> None:
    from jusperfect.config import KonfigurationsFehler

    for wert in ("IHRE-KENNUNG", "ihre-kennung", " Abcd1234efgh ", "TODO"):
        try:
            _einstellungen_aus("START-AWS.bat", JUSPERFECT_ANBIETER="bedrock",
                               JUSPERFECT_GUARDRAIL_ID=wert)
        except KonfigurationsFehler as fehler:
            assert "Platzhalter" in str(fehler)
            assert "Guardrail ID" in str(fehler), \
                "Die Meldung muss sagen, wo die echte steht."
        else:
            raise AssertionError(f"{wert!r} haette auffallen muessen.")


def test_eine_echte_kennung_kommt_weiterhin_durch() -> None:
    """Die Liste darf nicht so breit sein, dass sie Richtiges abweist."""
    e = _einstellungen_aus("START-AWS.bat", JUSPERFECT_ANBIETER="bedrock",
                           JUSPERFECT_GUARDRAIL_ID="gr7k2m9qx4vp")
    assert e.guardrail_id == "gr7k2m9qx4vp"


def test_die_anleitung_traegt_kein_wort_aus_der_sperrliste_als_beispiel() -> None:
    """Sonst schreibt der Naechste wieder genau das ab, was nicht geht -
    und bekommt eine Meldung, die auf die Anleitung zeigt, aus der es stammt."""
    from jusperfect.config import PLATZHALTER_GELAENDER

    text = (WURZEL / "AWS-EINRICHTEN.md").read_text(encoding="utf-8")
    for zeile in text.splitlines():
        if "JUSPERFECT_GUARDRAIL_ID=" in zeile:
            wert = zeile.split("JUSPERFECT_GUARDRAIL_ID=", 1)[1].strip().strip('`"')
            assert wert.lower() not in PLATZHALTER_GELAENDER or not wert, \
                (f"{wert!r} steht als Beispiel in der Anleitung und wird vom "
                 "Programm abgewiesen. Eines von beiden ist falsch.")


# ---------------------------------------------------------------------------
# Die vier Werte duerfen nicht verrutschen
#
# Am 25.09.2026 landete der Benutzername in der Adresse. Vermutlich kam beim
# Einfuegen aus der Zwischenablage ein Zeilenumbruch mit, der gleich die
# naechste Frage beantwortete - auf einem schwarzen Schirm sieht man das
# nicht. Der Server lehnte danach mit 401 ab, und das sah aus wie ein
# fehlendes Recht. Die Suche ging in die voellig falsche Richtung.
# ---------------------------------------------------------------------------


def test_eine_adresse_im_benutzerfeld_faellt_auf() -> None:
    from jusperfect.jurnodeszugang import was_daran_nicht_stimmt

    haken = was_daran_nicht_stimmt(
        "JURNODES_API_USER",
        "https://dortschy-thunert.jur-nodes.net/api/extern/v1/abc/")
    assert haken
    assert "user_2" in haken, "Die Meldung muss sagen, was gemeint ist."


def test_ein_benutzername_im_adressfeld_faellt_auf() -> None:
    from jusperfect.jurnodeszugang import was_daran_nicht_stimmt

    haken = was_daran_nicht_stimmt("JUSPERFECT_JURNODES_URL", "user_2")
    assert haken
    assert "https://" in haken


def test_die_arn_statt_der_kennung_faellt_auf() -> None:
    """Auf der AWS-Seite stehen beide untereinander, und die ARN ist die
    auffaelligere von beiden."""
    from jusperfect.jurnodeszugang import was_daran_nicht_stimmt

    haken = was_daran_nicht_stimmt(
        "JUSPERFECT_GUARDRAIL_ID",
        "arn:aws:bedrock:eu-central-1:579138738703:guardrail/jeico9orinss")
    assert "ARN" in haken


def test_richtige_werte_kommen_durch() -> None:
    """Die Pruefung darf nicht so streng sein, dass sie Richtiges abweist."""
    from jusperfect.jurnodeszugang import was_daran_nicht_stimmt

    richtig = {
        "JUSPERFECT_JURNODES_URL":
            "https://dortschy-thunert.jur-nodes.net/api/extern/v1/abc/",
        "JURNODES_API_USER": "user_2",
        "JURNODES_API_KEY": "Xy7-2k9_Qm4pZ",
        "JUSPERFECT_GUARDRAIL_ID": "jeico9orinss",
    }
    for name, wert in richtig.items():
        assert was_daran_nicht_stimmt(name, wert) == "", \
            f"{name}={wert!r} ist richtig und wurde trotzdem beanstandet."


def test_jedes_feld_wird_geprueft() -> None:
    """Sonst bleibt eine Luecke, durch die genau der Wert rutscht, den
    niemand mehr kontrolliert."""
    from jusperfect.jurnodeszugang import FELDER, was_daran_nicht_stimmt

    for name, _, _ in FELDER:
        assert was_daran_nicht_stimmt(name, "https://irgendwo.de/pfad/") or \
            name == "JUSPERFECT_JURNODES_URL", \
            f"{name} nimmt eine Adresse an, ohne zu widersprechen."


# ---------------------------------------------------------------------------
# Wer eine Uebersicht auf den Schirm schreibt, muss damit rechnen, dass sie
# kopiert wird
#
# Am 25.09.2026 stand im Windows-Konto der Kanzlei woertlich
# "Benutzer:        user_2" - die ganze Zeile aus der Uebersicht des Starters,
# mitsamt Beschriftung und Leerzeichen. Das ist kein Bedienfehler, sondern das
# Naechstliegende: Dort steht der Wert, den das Programm haben will.
#
# jur|nodes lehnte mit 401 ab. Die Meldung sprach von fehlenden Rechten, und
# die Suche ging eine Stunde in die Rechteverwaltung des Herstellers.
# ---------------------------------------------------------------------------


def test_eine_mitkopierte_beschriftung_wird_abgeschnitten() -> None:
    from jusperfect.jurnodeszugang import ohne_beschriftung

    assert ohne_beschriftung("Benutzer:        user_2") == "user_2"
    assert ohne_beschriftung("Schutzgelaender: jeico9orinss") == "jeico9orinss"
    assert ohne_beschriftung("Token: abc123") == "abc123"


def test_eine_adresse_verliert_ihr_https_nicht() -> None:
    """Sie traegt selbst einen Doppelpunkt. Wer stumpf davor abschneidet,
    macht aus einer richtigen Adresse eine unbrauchbare."""
    from jusperfect.jurnodeszugang import ohne_beschriftung

    adresse = "https://dortschy-thunert.jur-nodes.net/api/extern/v1/abc/"
    assert ohne_beschriftung(adresse) == adresse
    assert ohne_beschriftung(f"Schnittstelle:   {adresse}") == adresse


def test_ein_doppelpunkt_ohne_bekannte_beschriftung_bleibt_stehen() -> None:
    """Ein Token darf einen enthalten. Abgeschnitten wird nur, was vorn als
    Beschriftung erkennbar ist."""
    from jusperfect.jurnodeszugang import ohne_beschriftung

    assert ohne_beschriftung("6Gu:xyz:SZK") == "6Gu:xyz:SZK"


def test_ein_leerzeichen_im_benutzernamen_faellt_auf() -> None:
    """Der Fall, der durchrutschte: kein Schraegstrich, kein https - und
    trotzdem falsch."""
    from jusperfect.jurnodeszugang import was_daran_nicht_stimmt

    haken = was_daran_nicht_stimmt("JURNODES_API_USER", "Benutzer user_2")
    assert "Leerzeichen" in haken


def test_kein_wert_darf_ein_leerzeichen_tragen() -> None:
    """Auf einem schwarzen Schirm sieht man keines - deshalb muss jedes Feld
    danach fragen, nicht nur das, an dem es zuletzt aufgefallen ist."""
    from jusperfect.jurnodeszugang import FELDER, was_daran_nicht_stimmt

    for name, _, _ in FELDER:
        if name == "JUSPERFECT_JURNODES_URL":
            continue          # die prueft hinweise_zur_adresse
        assert was_daran_nicht_stimmt(name, "abc def"), \
            f"{name} nimmt einen Wert mit Leerzeichen an."
