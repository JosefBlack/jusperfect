import unittest

from jusperfect.config import Einstellungen, KonfigurationsFehler
from tests.hilfen import einstellungen


class Konfiguration(unittest.TestCase):
    def test_lokal_standard(self):
        e = einstellungen()
        self.assertEqual(e.betriebsart, "lokal")
        self.assertEqual(e.identitaet, "header")
        self.assertEqual(e.speicher, "lokal")
        self.assertEqual(e.aws_region, "eu-central-1")

    def test_lokales_gedaechtnis_nur_mit_testakten(self):
        """Es schreibt Klartext auf die Platte – echte Akten dürfen da nicht hin.

        Der Weg dorthin wäre kurz: In einer Startdatei den Adapter auf das
        Kanzleilaufwerk stellen und vergessen, das Gedächtnis abzuschalten.
        """
        with self.assertRaises(KonfigurationsFehler) as fehler:
            einstellungen(JUSPERFECT_GEDAECHTNIS="lokal",
                          JUSPERFECT_JURNODES_ADAPTER="webdav",
                          JUSPERFECT_JURNODES_WEBDAV="/tmp")
        self.assertIn("Testakten", str(fehler.exception))
        self.assertIn("unverschlüsselt", str(fehler.exception))

    def test_lokales_gedaechtnis_mit_testakten_ist_zulaessig(self):
        """Genau die Einstellung, die in START-DEMO.bat und START-AWS.bat steht."""
        e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal")
        self.assertEqual(e.gedaechtnis, "lokal")
        self.assertEqual(e.jurnodes_adapter, "fixture")

    def test_echte_akten_verlangen_ein_guardrail_auch_oertlich(self):
        """Die Lücke, durch die der erste echte Versuch gegangen wäre.

        Das Guardrail war nur in der AWS-Aufstellung zwingend. Der Weg zur
        ersten echten Akte führt aber über den örtlichen Betrieb: in der
        Startdatei den Adapter auf das Kanzleilaufwerk stellen, fertig. Genau
        dort griff die Regel nicht, und das Programm lief ohne Schutzgeländer.
        """
        for adapter, zusatz in (("webdav", {"JUSPERFECT_JURNODES_WEBDAV": "/tmp"}),
                                ("http", {"JUSPERFECT_JURNODES_URL": "https://j"})):
            with self.subTest(adapter=adapter):
                with self.assertRaises(KonfigurationsFehler) as fehler:
                    einstellungen(JUSPERFECT_ANBIETER="bedrock", JUSPERFECT_GEDAECHTNIS="aus",
                                  JUSPERFECT_JURNODES_ADAPTER=adapter, **zusatz)
                self.assertIn("Guardrail", str(fehler.exception))
                self.assertIn("JUSPERFECT_GUARDRAIL_ID", str(fehler.exception))

    def test_mit_guardrail_laeuft_derselbe_aufbau(self):
        e = einstellungen(JUSPERFECT_ANBIETER="bedrock", JUSPERFECT_GEDAECHTNIS="aus",
                          JUSPERFECT_JURNODES_ADAPTER="webdav", JUSPERFECT_JURNODES_WEBDAV="/tmp",
                          JUSPERFECT_GUARDRAIL_ID="gr-1")
        self.assertEqual("gr-1", e.guardrail_id)

    def test_die_testakten_brauchen_keines(self):
        """Sonst käme niemand mehr zum Ausprobieren – und darin steht nichts Echtes."""
        e = einstellungen(JUSPERFECT_ANBIETER="bedrock", JUSPERFECT_GEDAECHTNIS="aus")
        self.assertIsNone(e.guardrail_id)
        self.assertEqual("fixture", e.jurnodes_adapter)

    def test_ohne_modell_gibt_es_nichts_zu_schuetzen(self):
        """Der Demo-Anbieter rechnet auf dem Rechner; es geht nichts hinaus.

        Eine echte Akte nur zu lesen, ohne dass etwas den Rechner verlässt,
        bleibt deshalb zulässig. Ein Schutzgeländer vor einem Modell, das gar
        nicht gefragt wird, wäre eine Hürde ohne Nutzen.
        """
        e = einstellungen(JUSPERFECT_ANBIETER="demo", JUSPERFECT_GEDAECHTNIS="aus",
                          JUSPERFECT_JURNODES_ADAPTER="webdav", JUSPERFECT_JURNODES_WEBDAV="/tmp")
        self.assertIsNone(e.guardrail_id)

    def test_in_europa_wird_das_inferenzprofil_vorausgesetzt(self):
        """Der Fehler, der die Kanzlei einen Vormittag gekostet hat.

        Anthropic gibt seine Modelle in Frankfurt nur über Inferenzprofile
        frei. Eine Abfrage dort ergab: von dreizehn Claude-Modellen genau
        eines unmittelbar aufrufbar, alle übrigen nur über ein Profil. Die
        Voreinstellung trug die Kennung ohne Vorsatz und konnte deshalb gar
        nicht funktionieren – abgewiesen mit AccessDeniedException, also mit
        derselben Meldung wie eine fehlende Berechtigung.
        """
        # Geprueft wird der Vorsatz, nicht die Kennung: Welches Modell die
        # Voreinstellung nennt, haengt daran, was das Konto der Kanzlei fuehrt,
        # und das aendert sich. Die Regel darunter aendert sich nicht.
        self.assertEqual(einstellungen().modell_id, f"eu.{Einstellungen.modell_id}")
        self.assertTrue(Einstellungen.modell_id.startswith("anthropic."))

    def test_eigene_anthropic_kennung_bekommt_den_vorsatz_ebenfalls(self):
        e = einstellungen(JUSPERFECT_MODELL_ID="anthropic.claude-sonnet-5")
        self.assertEqual(e.modell_id, "eu.anthropic.claude-sonnet-5")

    def test_was_schon_richtig_ist_bleibt_unberuehrt(self):
        """Kein doppelter Vorsatz, keine verbogene ARN."""
        from jusperfect.config import _modellkennung
        self.assertEqual(
            einstellungen(JUSPERFECT_MODELL_ID="eu.anthropic.claude-sonnet-5").modell_id,
            "eu.anthropic.claude-sonnet-5")
        arn = "arn:aws:bedrock:eu-central-1:1:inference-profile/eigen"
        self.assertEqual(einstellungen(JUSPERFECT_MODELL_ID=arn).modell_id, arn)
        # Ausserhalb Europas gilt die Regel nicht - dort gibt es die Profile
        # unter diesem Namen nicht. (Der Betrieb ist dort ohnehin gesperrt;
        # die Funktion selbst muss trotzdem stimmen.)
        self.assertEqual(_modellkennung("anthropic.claude-opus-5", "us-east-1"),
                         "anthropic.claude-opus-5")

    def test_fremde_anbieter_bleiben_unberuehrt(self):
        from jusperfect.config import _modellkennung
        self.assertEqual(_modellkennung("meta.llama-3", "eu-central-1"), "meta.llama-3")

    #: Eine vollständige, zulässige Produktivkonfiguration.
    ECHTBETRIEB = {
        "JUSPERFECT_BETRIEBSART": "aws", "JUSPERFECT_DYNAMODB_TABELLE": "t", "JUSPERFECT_S3_BUCKET": "b",
        "JUSPERFECT_JURNODES_ADAPTER": "http", "JUSPERFECT_JURNODES_URL": "https://j",
        "JUSPERFECT_GUARDRAIL_ID": "gr-1", "JUSPERFECT_KMS_SCHLUESSEL_ID": "kms-1",
    }

    def test_aws_setzt_sichere_vorgaben(self):
        e = Einstellungen.aus_umgebung(dict(self.ECHTBETRIEB))
        self.assertEqual((e.identitaet, e.speicher, e.anbieter, e.ocr), ("cognito", "aws", "bedrock", "textract"))

    def test_echtbetrieb_verlangt_guardrail_echte_akten_und_verschluesselung(self):
        """Fail closed: Eine halb eingerichtete Produktivumgebung startet nicht."""
        for weglassen, erwartet in (
            ("JUSPERFECT_GUARDRAIL_ID", "Guardrail"),
            ("JUSPERFECT_KMS_SCHLUESSEL_ID", "verschlüsselt"),
        ):
            with self.subTest(fehlt=weglassen):
                umgebung = dict(self.ECHTBETRIEB)
                del umgebung[weglassen]
                with self.assertRaises(KonfigurationsFehler) as f:
                    Einstellungen.aus_umgebung(umgebung)
                self.assertIn(erwartet, str(f.exception))

    def test_echtbetrieb_verbietet_testakten(self):
        umgebung = dict(self.ECHTBETRIEB)
        umgebung["JUSPERFECT_JURNODES_ADAPTER"] = "fixture"
        with self.assertRaises(KonfigurationsFehler) as f:
            Einstellungen.aus_umgebung(umgebung)
        self.assertIn("Testakten", str(f.exception))

    def test_aws_verbietet_kopfzeile_und_demo(self):
        with self.assertRaises(KonfigurationsFehler):
            Einstellungen.aus_umgebung({"JUSPERFECT_BETRIEBSART": "aws", "JUSPERFECT_IDENTITAET": "header",
                                        "JUSPERFECT_DYNAMODB_TABELLE": "t", "JUSPERFECT_S3_BUCKET": "b"})
        with self.assertRaises(KonfigurationsFehler):
            Einstellungen.aus_umgebung({"JUSPERFECT_BETRIEBSART": "aws", "JUSPERFECT_ANBIETER": "demo",
                                        "JUSPERFECT_DYNAMODB_TABELLE": "t", "JUSPERFECT_S3_BUCKET": "b"})

    def test_nur_eu_regionen(self):
        with self.assertRaises(KonfigurationsFehler):
            einstellungen(JUSPERFECT_AWS_REGION="us-east-1")

    def test_aws_speicher_braucht_tabelle_und_bucket(self):
        with self.assertRaises(KonfigurationsFehler):
            einstellungen(JUSPERFECT_SPEICHER="aws")

    def test_unbekannte_wahl(self):
        with self.assertRaises(KonfigurationsFehler):
            einstellungen(JUSPERFECT_ANBIETER="openai")

    def test_gedaechtnis_ist_opt_in_und_aws_braucht_bucket_und_kms(self):
        self.assertEqual(einstellungen().gedaechtnis, "aus")
        with self.assertRaises(KonfigurationsFehler):
            einstellungen(JUSPERFECT_GEDAECHTNIS="aws")
        e = einstellungen(
            JUSPERFECT_GEDAECHTNIS="aws", JUSPERFECT_GEDAECHTNIS_BUCKET="g",
            JUSPERFECT_KMS_SCHLUESSEL_ID="k",
        )
        self.assertEqual(e.gedaechtnis, "aws")
        self.assertEqual(e.sitzung_ttl_sekunden, 7 * 24 * 3600)

    def test_gedaechtnismodell_nimmt_kleines_modell(self):
        e = einstellungen(JUSPERFECT_MODELL_ID="gross", JUSPERFECT_MODELL_ID_KLEIN="klein")
        self.assertEqual(e.modell_fuer("gedaechtnis"), "klein")
