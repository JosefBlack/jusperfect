"""Der Laufwerksweg zu jur|nodes – der letzte Schritt vor der ersten echten Akte.

Aus der Kanzlei: „Die Einbindung von jurnodes erfolgt entweder über API oder
durch Einbindung durch das Laufwerk, da es sich um einen WEB-DAV Server
handelt. Wir wollten den letzten Schritt vornehmen."

Damit hängt alles am Ordnerbaum:

    <Wurzel>/<Anwalt>/<Jahr>/<Aktenzeichen Bezeichnung>/<Dokumente>

Stimmt er nicht, findet jusperfect **null Akten** – und eine leere Liste sagt
nicht, woran es liegt. Die alte Ordnerprüfung zählte nur Akten und meldete bei
null Akten, es sei keine archivierte darunter; dass der ganze Baum anders
gebaut war, erfuhr niemand.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jusperfect.config import Einstellungen
from jusperfect.ordnerpruefung import aufbau_pruefen, dateien_zaehlen, schreibprobe

WURZEL = Path(__file__).resolve().parent.parent


def _baum(wurzel: Path, *akten: str) -> None:
    for pfad in akten:
        (wurzel / pfad).mkdir(parents=True, exist_ok=True)


class DerAufbauWirdBenannt(unittest.TestCase):
    def setUp(self) -> None:
        self._ordner = TemporaryDirectory()
        self.wurzel = Path(self._ordner.name)
        self.addCleanup(self._ordner.cleanup)

    def _saetze(self) -> str:
        return " ".join(s for _, s in aufbau_pruefen(self.wurzel))

    def _zeichen(self) -> set[str]:
        return {z for z, _ in aufbau_pruefen(self.wurzel)}

    def test_ein_richtiger_baum_geht_durch(self):
        _baum(self.wurzel, "Dortschy/2026/X-107-2026 Testmann", "Thunert/2025/X-109-2025 Beispiel")
        self.assertNotIn("✗", self._zeichen())

    def test_ein_leerer_ordner_wird_benannt(self):
        self.assertIn("✗", self._zeichen())
        self.assertIn("kein einziger Unterordner", self._saetze())

    def test_vertauschte_ebenen_werden_benannt(self):
        """Jahr oben, Anwalt darunter – der naheliegende Irrtum."""
        _baum(self.wurzel, "2026/Dortschy/D-132")
        saetze = self._saetze()
        self.assertIn("✗", self._zeichen())
        self.assertIn("kein Jahresordner", saetze)
        self.assertIn("Dortschy", saetze, "Was stattdessen dasteht, gehört in die Meldung.")

    def test_akten_ohne_jahresebene_werden_benannt(self):
        """Ein Anwalt hat Jahresordner, der andere nicht – der wird übersprungen."""
        _baum(self.wurzel, "Dortschy/2026/X-107-2026 Testmann", "Thunert/Alte Akten/T-1")
        saetze = self._saetze()
        self.assertNotIn("✗", self._zeichen(), "Ein Ordner mit Jahren genügt zum Weitermachen.")
        self.assertIn("!", self._zeichen())
        self.assertIn("Thunert", saetze)


class DieDokumenteWerdenGezaehlt(unittest.TestCase):
    def setUp(self) -> None:
        self._ordner = TemporaryDirectory()
        self.wurzel = Path(self._ordner.name)
        self.addCleanup(self._ordner.cleanup)
        akte = self.wurzel / "Dortschy" / "2026" / "X-107-2026 Testmann"
        akte.mkdir(parents=True)
        for name in ("a.txt", "b.pdf", "c.docx", "d.msg", "e.zip"):
            (akte / name).write_text("x", encoding="utf-8")
        (akte / "Vermerke").mkdir()
        (akte / "Vermerke" / "eigener.txt").write_text("eigener Vermerk", encoding="utf-8")

    def test_lesbar_und_uebersprungen_werden_getrennt(self):
        """Eine Akte, die zur Hälfte aus .msg besteht, ist halb bearbeitet –
        und das soll man wissen, bevor man sich darauf verlässt."""
        lesbar, uebersprungen, _ = dateien_zaehlen(self.wurzel)
        self.assertEqual({".txt": 1, ".pdf": 1, ".docx": 1}, dict(lesbar))
        self.assertEqual({".msg": 1, ".zip": 1}, dict(uebersprungen))

    def test_eigene_vermerke_zaehlen_nicht_mit(self):
        """Sie sind kein Aktenmaterial – sonst zählt sich das Programm selbst."""
        lesbar, _, _ = dateien_zaehlen(self.wurzel)
        self.assertEqual(3, sum(lesbar.values()))

    def test_die_textmenge_wird_gemessen(self):
        _, _, bytes_gesamt = dateien_zaehlen(self.wurzel)
        self.assertEqual(3, bytes_gesamt, "je eine Datei mit einem Zeichen")


class DieSchreibprobe(unittest.TestCase):
    def test_sie_raeumt_hinter_sich_auf(self):
        """Sie darf im Aktenbestand der Kanzlei nichts hinterlassen."""
        with TemporaryDirectory() as ordner:
            wurzel = Path(ordner)
            darf, grund = schreibprobe(wurzel)
            self.assertTrue(darf)
            self.assertEqual("", grund)
            self.assertEqual([], list(wurzel.iterdir()), "Es ist etwas liegengeblieben.")

    def test_ohne_schreibrecht_sagt_sie_das(self):
        with TemporaryDirectory() as ordner:
            wurzel = Path(ordner) / "gibtsnicht"
            darf, grund = schreibprobe(wurzel)
            self.assertFalse(darf)
            self.assertTrue(grund)


class DerStarterFuerEchteAkten(unittest.TestCase):
    """START-KANZLEI.bat – hier müssen vier Einstellungen zugleich stimmen."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = (WURZEL / "START-KANZLEI.bat").read_text(encoding="utf-8")

    def _umgebung(self, **zusatz: str) -> dict[str, str]:
        env: dict[str, str] = {}
        for zeile in self.text.splitlines():
            treffer = re.match(r"\s*set\s+(JUSPERFECT_[A-Z_]+)=(.*)$", zeile)
            if treffer:
                env[treffer.group(1)] = treffer.group(2).strip()
        return {k: v for k, v in (env | zusatz).items() if v}

    def test_die_beiden_pflichtangaben_sind_leer(self):
        """Sie gehören der Kanzlei. Ein Beispielpfad, den jemand stehenlässt,
        wäre schlimmer als eine Lücke."""
        env = {}
        for zeile in self.text.splitlines():
            treffer = re.match(r"\s*set\s+(JUSPERFECT_[A-Z_]+)=(.*)$", zeile)
            if treffer:
                env[treffer.group(1)] = treffer.group(2).strip()
        self.assertEqual("", env["JUSPERFECT_JURNODES_WEBDAV"])
        self.assertEqual("", env["JUSPERFECT_GUARDRAIL_ID"])

    def test_er_bricht_ab_bevor_etwas_laeuft(self):
        """Sonst bekäme der Bearbeiter eine Python-Meldung zu sehen –
        richtig und unbrauchbar."""
        for marke in (":kein_ordner", ":kein_gelaender"):
            self.assertIn(marke, self.text, marke)
        self.assertLess(self.text.index("if not defined JUSPERFECT_JURNODES_WEBDAV"),
                        self.text.index("-m jusperfect.awstest"))

    def test_mit_beiden_angaben_ist_die_aufstellung_zulaessig(self):
        """Die eigentliche Probe: Vier Einstellungen müssen zugleich passen."""
        with TemporaryDirectory() as ordner:
            e = Einstellungen.aus_umgebung(self._umgebung(
                JUSPERFECT_JURNODES_WEBDAV=ordner,
                JUSPERFECT_GUARDRAIL_ID="gr-abcd1234"))
            self.assertEqual("webdav", e.jurnodes_adapter)
            self.assertEqual("bedrock", e.anbieter)
            self.assertEqual("gr-abcd1234", e.guardrail_id)
            self.assertEqual("eu-central-1", e.aws_region)

    def test_das_gedaechtnis_liegt_in_der_akte(self):
        """Beim Laufwerksweg die saubere Wahl: kein zweiter Aufbewahrungsort.

        „lokal" wäre mit echten Akten unzulässig – das Programm weist es ab.
        """
        with TemporaryDirectory() as ordner:
            e = Einstellungen.aus_umgebung(self._umgebung(
                JUSPERFECT_JURNODES_WEBDAV=ordner,
                JUSPERFECT_GUARDRAIL_ID="gr-1"))
            self.assertEqual("akte", e.gedaechtnis)

    def test_dieselben_modelle_wie_im_testbetrieb(self):
        """Sonst misst der Prüfbogen etwas anderes, als die Kanzlei benutzt."""
        with TemporaryDirectory() as ordner:
            e = Einstellungen.aus_umgebung(self._umgebung(
                JUSPERFECT_JURNODES_WEBDAV=ordner, JUSPERFECT_GUARDRAIL_ID="gr-1"))
            for funktion in ("frage", "analyse", "entwurf", "gedaechtnis"):
                with self.subTest(funktion=funktion):
                    self.assertIn("opus", e.modell_fuer(funktion))
            self.assertIn("haiku", e.modell_fuer("triage"))


if __name__ == "__main__":
    unittest.main()


class DieProbeSagtWasSieTut(unittest.TestCase):
    """Der ganze Durchlauf – so, wie ihn die Kanzlei doppelklickt.

    Zwei Befunde aus dem ersten Lauf auf einem echten Kanzleilaufwerk haben
    diese Prüfungen veranlasst.
    """

    def _durchlauf(self) -> tuple[str, Path]:
        """Führt die Probe in einem eigenen Arbeitsordner aus und gibt den
        Bericht zurück."""
        import io
        import os
        from contextlib import redirect_stdout

        from jusperfect import ordnerpruefung

        ordner = TemporaryDirectory()
        self.addCleanup(ordner.cleanup)
        wurzel = Path(ordner.name) / "Akten"
        _baum(wurzel, "Dortschy/2026/X-107-2026 Testmann")
        (wurzel / "Dortschy/2026/X-107-2026 Testmann/schriftsatz.txt").write_text(
            "Etwas Text.", encoding="utf-8")

        vorher = Path.cwd()
        os.chdir(ordner.name)
        self.addCleanup(os.chdir, vorher)
        schirm = io.StringIO()
        with redirect_stdout(schirm):
            ordnerpruefung.main([str(wurzel)])
        return schirm.getvalue(), Path(ordner.name) / ordnerpruefung.BERICHT

    def test_das_schreibrecht_wird_auch_in_der_akte_geprueft(self):
        """Aus der Kanzlei: „Mit dem Zurückschreiben fehlt, dass das Programm
        das Aktengedächtnis auf den Server schreiben darf."

        Zu Recht: Geprüft wurde nur die Wurzel. Geschrieben wird aber IN DER
        AKTE – der freigegebene Vermerk nach `<Akte>/Vermerke/`, das
        Aktengedächtnis als eine Datei daneben. Auf einem WebDAV-Server können
        die Rechte je Ebene verschieden sein; eine schreibbare Wurzel sagt über
        den Aktenordner nichts.
        """
        ausgabe, _ = self._durchlauf()
        self.assertIn("Die Wurzel des Aktenordners", ausgabe)
        self.assertIn("Der Aktenordner (Beispiel: X-107-2026)", ausgabe)

    def test_das_aktengedaechtnis_wird_beim_namen_genannt(self):
        """Wer nur „Schreibrecht für Vermerke" liest, prüft die falsche Zusage."""
        from jusperfect.jurnodes.base import GEDAECHTNIS_DATEI

        ausgabe, _ = self._durchlauf()
        self.assertIn("AKTENGEDÄCHTNIS", ausgabe)
        self.assertIn(GEDAECHTNIS_DATEI, ausgabe)

    def test_der_befund_steht_auf_dem_schirm_und_in_der_datei(self):
        """Vorher schrieb die Startdatei erst die Datei und gab sie danach mit
        `type` aus. Auf einem echten Laufwerk blieb der Schirm damit
        minutenlang leer – und niemand konnte erkennen, ob die Probe arbeitet
        oder steht. Genau das ist in der Kanzlei passiert.
        """
        ausgabe, bericht = self._durchlauf()
        self.assertIn("taugt der Aktenordner", ausgabe)
        self.assertTrue(bericht.is_file(), "Der Bericht fehlt.")
        self.assertIn("taugt der Aktenordner", bericht.read_text(encoding="utf-8"))

    def test_die_zwischenstaende_landen_nicht_im_bericht(self):
        """Das Lebenszeichen gehört auf den Schirm, nicht in eine Datei, die
        weitergegeben wird."""
        _, bericht = self._durchlauf()
        self.assertNotIn("Dateien gesehen", bericht.read_text(encoding="utf-8"))

    def test_die_startdatei_leitet_die_ausgabe_nicht_mehr_um(self):
        """Sonst wäre der Schirm wieder still."""
        bat = (WURZEL / "ORDNER-PRUEFEN.bat").read_text(encoding="utf-8")
        self.assertNotIn("> ordnerpruefung.txt", bat)
        self.assertIn("-m jusperfect.ordnerpruefung", bat)


def test_die_laufwerksprobe_nennt_ihren_programmstand() -> None:
    """Zweimal ist in der Kanzlei an der falschen Stelle gesucht worden, weil
    niemand sagen konnte, welcher Stand gerade lief — am 16.09.2026 bei einem
    gemischten Ordner, am 23.09.2026 bei der stummen Laufwerksprobe. Die
    übrigen Startdateien zeigen den Stand längst; diese nicht.
    """
    bat = (WURZEL / "ORDNER-PRUEFEN.bat").read_text(encoding="utf-8")
    assert "FASSUNG.txt" in bat
    assert "Programmstand: %FASSUNG%" in bat
    # Vor der Frage nach dem Ordner, nicht danach.
    assert bat.index("Programmstand:") < bat.index("set /p ORDNER")


class DerPfadWirdBereinigt(unittest.TestCase):
    """Aus der Kanzlei, 23.09.2026: Beim Eintippen rutschte ein Leerzeichen vor
    das „J:". cmd gibt es bei `set /p` unverändert weiter, und `" J:\\Akten"`
    gibt es nicht.

    Die Meldung lautete darauf „Diesen Ordner gibt es nicht – ist das Laufwerk
    verbunden?" Sie war richtig und irreführend zugleich: Das Laufwerk war
    verbunden. Ein Leerzeichen sieht auf einem schwarzen Schirm niemand, und
    der Pfad stand ohne Anführungszeichen da.
    """

    def _durchlauf(self, eingabe: str) -> str:
        import io
        import os
        from contextlib import redirect_stdout

        from jusperfect import ordnerpruefung

        ordner = TemporaryDirectory()
        self.addCleanup(ordner.cleanup)
        wurzel = Path(ordner.name) / "Akten"
        _baum(wurzel, "Dortschy/2026/X-107-2026 Testmann")

        vorher = Path.cwd()
        os.chdir(ordner.name)
        self.addCleanup(os.chdir, vorher)
        schirm = io.StringIO()
        with redirect_stdout(schirm):
            self.ende = ordnerpruefung.main([eingabe.replace("{wurzel}", str(wurzel))])
        return schirm.getvalue()

    def test_ein_leerzeichen_davor_macht_den_pfad_nicht_unbrauchbar(self):
        self._durchlauf(" {wurzel}")
        self.assertNotEqual(1, self.ende, "Der Ordner wurde nicht gefunden.")

    def test_auch_eines_dahinter_nicht(self):
        self._durchlauf("{wurzel} ")
        self.assertNotEqual(1, self.ende)

    def test_anfuehrungszeichen_aus_dem_explorer_stoeren_nicht(self):
        """„Als Pfad kopieren" legt sie mit in die Zwischenablage."""
        self._durchlauf('"{wurzel}"')
        self.assertNotEqual(1, self.ende)

    def test_der_pfad_steht_in_anfuehrungszeichen_auf_dem_schirm(self):
        """Damit ein Leerzeichen am Rand überhaupt zu sehen wäre."""
        ausgabe = self._durchlauf("{wurzel}")
        self.assertIn('Aktenordner: "', ausgabe)

    def test_ein_wirklich_falscher_pfad_nennt_mehr_als_das_laufwerk(self):
        """Vorher legte die Meldung eine einzige Ursache nahe – die falsche."""
        ausgabe = self._durchlauf("{wurzel}/gibtsnicht")
        self.assertEqual(1, self.ende)
        self.assertIn("Drei Dinge kommen in Frage", ausgabe)
        self.assertIn("anders geschrieben", ausgabe)


class DoppelteAktenzeichen(unittest.TestCase):
    """Aus der Kanzlei, 23.09.2026: „die akten von herrn thunert sind jedoch
    zahlen und auch keine namen des mandanten."

    Eine Akte heißt dann schlicht `0101`. Der Adapter führt seinen Index unter
    dem Aktenzeichen und lässt das erste Vorkommen gewinnen
    (`webdav_adapter._baum`). Eine reine Zahl wird aber gern je Jahrgang neu
    vergeben — `0101` von 2024 und `0101` von 2025 sind dann zwei Akten mit
    demselben Schlüssel, und die zweite verschwindet lautlos: keine Liste,
    keine Meldung. Wer sie sucht, bekommt die andere und merkt es nicht.
    """

    def _adapter(self, wurzel: Path):
        from jusperfect.jurnodes.webdav_adapter import WebDavJurNodesAdapter
        from jusperfect.security.approval import Freigabestelle
        return WebDavJurNodesAdapter(wurzel, Freigabestelle(), schreibbar=False,
                                     archiv_kennung="archiviert")

    def test_ein_zweimal_vergebenes_aktenzeichen_faellt_auf(self):
        from jusperfect.ordnerpruefung import doppelte_aktenzeichen

        with TemporaryDirectory() as ordner:
            wurzel = Path(ordner)
            _baum(wurzel, "Thunert/2024/0101", "Thunert/2025/0101", "Thunert/2025/0102")
            gesamt, doppelte = doppelte_aktenzeichen(wurzel, self._adapter(wurzel))
            self.assertEqual(3, gesamt)
            self.assertEqual(["0101"], sorted(doppelte))
            self.assertEqual(2, len(doppelte["0101"]))

    def test_eindeutige_kennungen_melden_nichts(self):
        from jusperfect.ordnerpruefung import doppelte_aktenzeichen

        with TemporaryDirectory() as ordner:
            wurzel = Path(ordner)
            _baum(wurzel, "Dortschy/2026/X-108-2026 Testmann", "Thunert/2026/0101")
            gesamt, doppelte = doppelte_aktenzeichen(wurzel, self._adapter(wurzel))
            self.assertEqual(2, gesamt)
            self.assertEqual({}, doppelte)

    def test_der_adapter_verliert_die_zweite_akte_tatsaechlich(self):
        """Die Prüfung misst keinen ausgedachten Fall: Genau das passiert."""
        with TemporaryDirectory() as ordner:
            wurzel = Path(ordner)
            _baum(wurzel, "Thunert/2024/0101", "Thunert/2025/0101")
            akten = self._adapter(wurzel).akten_suchen()
            self.assertEqual(1, len(akten), "Erwartet war der Verlust – sonst ist die Warnung falsch.")

    def test_die_probe_sagt_es_im_klartext(self):
        import io
        import os
        from contextlib import redirect_stdout

        from jusperfect import ordnerpruefung

        with TemporaryDirectory() as ordner:
            wurzel = Path(ordner) / "Akten"
            _baum(wurzel, "Thunert/2024/0101", "Thunert/2025/0101")
            vorher = Path.cwd()
            os.chdir(ordner)
            try:
                schirm = io.StringIO()
                with redirect_stdout(schirm):
                    ordnerpruefung.main([str(wurzel)])
            finally:
                os.chdir(vorher)
            ausgabe = schirm.getvalue()
            self.assertIn("nicht erreichbar", ausgabe)
            self.assertIn("0101", ausgabe)


class DieKostenzahlDarfNichtTaeuschen(unittest.TestCase):
    """Im Befund der Kanzlei vom 23.09.2026 stand:

        Textmenge: rund 53490.8 MB, im Mittel 18244 kB je Akte.
        Zum Vergleich: Die grosse Testakte hat 882 kB und kostet
        beim einmaligen Einlesen rund 2,50 €.

    Jede Zeile für sich war richtig, nebeneinander waren sie falsch. Gemessen
    wird die **Dateigröße**, verglichen wurde mit reinem **Text**. Ein
    eingescanntes PDF besteht fast ganz aus Bild; von 18 MB Akte sind
    vielleicht hundert Kilobyte Text. Wer beide Zahlen nebeneinander liest,
    rechnet sich fünfzig Euro je Akte aus und legt das Vorhaben weg.

    Eine Zahl, die zur falschen Entscheidung führt, ist schlimmer als keine.
    """

    def _ausgabe(self, *dateien: str) -> str:
        import io
        import os
        from contextlib import redirect_stdout

        from jusperfect import ordnerpruefung

        ordner = TemporaryDirectory()
        self.addCleanup(ordner.cleanup)
        wurzel = Path(ordner.name) / "Akten"
        akte = wurzel / "Dortschy/2026/X-107-2026 Testmann"
        akte.mkdir(parents=True)
        for name in dateien:
            (akte / name).write_bytes(b"x" * 1000)

        vorher = Path.cwd()
        os.chdir(ordner.name)
        self.addCleanup(os.chdir, vorher)
        schirm = io.StringIO()
        with redirect_stdout(schirm):
            ordnerpruefung.main([str(wurzel)])
        return schirm.getvalue()

    def test_die_dateigroesse_heisst_nicht_textmenge(self):
        ausgabe = self._ausgabe("a.pdf")
        self.assertNotIn("Textmenge: rund", ausgabe)
        self.assertIn("Umfang der lesbaren Dateien", ausgabe)

    def test_sie_sagt_ausdruecklich_dass_daraus_keine_kosten_folgen(self):
        ausgabe = self._ausgabe("a.pdf")
        self.assertIn("NICHT die Textmenge", ausgabe)
        self.assertIn("Kosten deshalb nicht ableiten", ausgabe)

    def test_bilddateien_werden_gezaehlt_denn_sie_brauchen_texterkennung(self):
        """Textract kostet je Seite und getrennt vom Modell. Im Bestand der
        Kanzlei lagen 9127 Bilddateien – das gehört in die Rechnung."""
        ausgabe = self._ausgabe("a.jpg", "b.png", "c.pdf")
        self.assertIn("Bilddateien", ausgabe)
        self.assertIn("Textract", ausgabe)

    def test_ohne_bilder_schweigt_sie_davon(self):
        ausgabe = self._ausgabe("a.docx")
        self.assertNotIn("Textract", ausgabe)


def test_die_befunde_bleiben_aus_der_versionsverwaltung() -> None:
    """In `ordnerpruefung.txt` stehen Aktenzeichen und Bezeichnungen aus dem
    echten Bestand — am 23.09.2026 waren es die von 2932 Akten. Solche Dateien
    entstehen bei jedem Lauf im Programmordner; ohne diese Zeilen landen sie
    beim nächsten `git add -A` im Verzeichnis, und dort stehen sie dann für
    immer. Der Weg zurück ist keiner.
    """
    from jusperfect import jurnodestest, ordnerpruefung

    ignoriert = (WURZEL / ".gitignore").read_text(encoding="utf-8")
    for datei in (ordnerpruefung.BERICHT, jurnodestest.BERICHT, "zugangstest.txt"):
        assert datei in ignoriert, f"{datei} wird nicht ausgenommen."
