import os
import unittest
from datetime import datetime, timezone

from jusperfect.domain.models import Akte, Entwurf, EntwurfArt, Nutzungseintrag, Sitzung
from jusperfect.security.tempstore import TemporaerSpeicher
from jusperfect.speicher.lokal import LokalerSpeicher


def _sitzung(sid="s1", nutzer="ra-weber"):
    return Sitzung(id=sid, nutzer_id=nutzer, akte_id="A-1", akte=Akte(id="A-1", aktenzeichen="1/26", bezeichnung="Test"))


def _eintrag(betrag):
    return Nutzungseintrag(zeitpunkt=datetime(2026, 9, 3, tzinfo=timezone.utc), nutzer_id="u", akte_id="A-1",
                           funktion="frage", modell="m", eingabe_tokens=1, ausgabe_tokens=1, betrag_eur=betrag)


class Temporaerspeicher(unittest.TestCase):
    def test_ablauf_und_loeschen(self):
        zeit = [0.0]
        s = TemporaerSpeicher(ttl_sekunden=10, uhr=lambda: zeit[0])
        s.ablegen("k", "geheim", gruppe="g")
        self.assertEqual(s.lesen("k"), "geheim")
        zeit[0] = 11
        self.assertIsNone(s.lesen("k"))
        s.ablegen("k2", "x", gruppe="g")
        self.assertEqual(s.loeschen_gruppe("g"), 1)
        self.assertEqual(len(s), 0)

    def test_verschluesselt_im_speicher(self):
        s = TemporaerSpeicher(ttl_sekunden=10)
        s.ablegen("k", "Mandant Thomas Testmann")
        roh = s._eintraege["k"].geheimtext
        self.assertNotIn(b"Testmann", roh)


class Lokal(unittest.TestCase):
    def test_sitzung_texte_und_ablauf(self):
        zeit = [0.0]
        s = LokalerSpeicher(sitzung_ttl=100, uhr=lambda: zeit[0])
        s.sitzung_ablegen(_sitzung())
        s.text_ablegen("s1", "D1", "Text")
        self.assertEqual(s.text_lesen("s1", "D1"), "Text")
        zeit[0] = 101
        self.assertIsNone(s.sitzung_lesen("s1"))
        self.assertIsNone(s.text_lesen("s1", "D1"))

    def test_schliessen_loescht_texte(self):
        s = LokalerSpeicher()
        s.sitzung_ablegen(_sitzung())
        s.text_ablegen("s1", "D1", "Text")
        s.sitzung_loeschen("s1")
        self.assertIsNone(s.text_lesen("s1", "D1"))
        self.assertEqual(s.anzahl_texte(), 0)

    def test_nutzung_summiert(self):
        s = LokalerSpeicher()
        self.assertAlmostEqual(s.nutzung_verbuchen(_eintrag(0.5)), 0.5)
        self.assertAlmostEqual(s.nutzung_verbuchen(_eintrag(0.25)), 0.75)
        self.assertAlmostEqual(s.nutzung_monat("2026-09"), 0.75)


try:
    import boto3
    from moto import mock_aws
except ImportError:  # pragma: no cover
    mock_aws = None


@unittest.skipIf(mock_aws is None, "moto nicht installiert")
class Aws(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("AWS_DEFAULT_REGION", "eu-central-1")
        os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
        self.mock = mock_aws()
        self.mock.start()
        self.addCleanup(self.mock.stop)
        from jusperfect.speicher.aws import AwsSpeicher

        dynamodb = boto3.resource("dynamodb", region_name="eu-central-1")
        dynamodb.create_table(TableName="t", BillingMode="PAY_PER_REQUEST",
                              AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}, {"AttributeName": "sk", "AttributeType": "S"}],
                              KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}, {"AttributeName": "sk", "KeyType": "RANGE"}])
        s3 = boto3.client("s3", region_name="eu-central-1")
        s3.create_bucket(Bucket="copilot-test-sitzungen", CreateBucketConfiguration={"LocationConstraint": "eu-central-1"})
        self.s3 = s3
        self.s = AwsSpeicher("t", "copilot-test-sitzungen", "eu-central-1", dynamodb=dynamodb, s3=s3, sitzung_ttl=100)

    def test_sitzung_und_text(self):
        self.s.sitzung_ablegen(_sitzung())
        self.s.text_ablegen("s1", "D1", "Text ü")
        self.assertEqual(self.s.sitzung_lesen("s1").akte_id, "A-1")
        self.assertEqual(self.s.text_lesen("s1", "D1"), "Text ü")
        self.assertIsNone(self.s.text_lesen("s1", "D9"))
        self.s.sitzung_loeschen("s1")
        self.assertIsNone(self.s.sitzung_lesen("s1"))
        self.assertEqual(self.s3.list_objects_v2(Bucket="copilot-test-sitzungen").get("KeyCount", 0), 0)

    def test_text_ohne_sitzung_unsichtbar(self):
        self.s.text_ablegen("s2", "D1", "Text")
        self.assertIsNone(self.s.text_lesen("s2", "D1"))

    def test_entwurf_und_nutzung(self):
        e = Entwurf(id="e1", akte_id="A-1", art=EntwurfArt.MANDANT, betreff="B", text="T", erstellt_von="u")
        self.s.entwurf_ablegen(e)
        self.assertEqual(self.s.entwurf_lesen("e1").text, "T")
        self.s.entwurf_loeschen("e1")
        self.assertIsNone(self.s.entwurf_lesen("e1"))
        self.assertAlmostEqual(self.s.nutzung_verbuchen(_eintrag(0.5)), 0.5)
        self.assertAlmostEqual(self.s.nutzung_verbuchen(_eintrag(0.26)), 0.76)
        self.assertAlmostEqual(self.s.nutzung_monat("2026-09"), 0.76)
        self.assertEqual(self.s.nutzung_monat("2026-08"), 0.0)

    def test_nachweis_lesen(self):
        jetzt = datetime.now(timezone.utc)
        self.s.nutzung_verbuchen(Nutzungseintrag(
            zeitpunkt=jetzt, nutzer_id="u", akte_id="A-1", funktion="frage", modell="m",
            eingabe_tokens=10, ausgabe_tokens=5, betrag_eur=0.01,
            sitzung_id="S1", material_kennung="abc123abc123:42", aufgabe_kennung="def456:7",
            passagen=3, antwort_zeichen=88))
        eintraege = self.s.nachweis_lesen(10)
        self.assertEqual(len(eintraege), 1)
        e = eintraege[0]
        self.assertEqual(e.material_kennung, "abc123abc123:42")
        self.assertEqual(e.passagen, 3)
        self.assertEqual(e.antwort_zeichen, 88)
        self.assertEqual(e.sitzung_id, "S1")
