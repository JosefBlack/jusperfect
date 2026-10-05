import unittest

from jusperfect.ocr.textract import TextractOcr, _seiten_aus_bloecken
from jusperfect.ocr.base import OcrFehler


class FakeS3:
    def __init__(self):
        self.objekte = {}

    def put_object(self, Bucket, Key, Body, **kw):
        self.objekte[Key] = Body

    def delete_object(self, Bucket, Key):
        self.objekte.pop(Key, None)


class FakeTextract:
    def __init__(self, status_folge):
        self.status_folge = list(status_folge)

    def start_document_text_detection(self, DocumentLocation):
        self.ort = DocumentLocation
        return {"JobId": "j1"}

    def get_document_text_detection(self, JobId, NextToken=None):
        status = self.status_folge.pop(0)
        if status == "SUCCEEDED":
            return {"JobStatus": "SUCCEEDED", "Blocks": [
                {"BlockType": "LINE", "Page": 1, "Text": "Zeile eins"},
                {"BlockType": "WORD", "Page": 1, "Text": "ignoriert"},
                {"BlockType": "LINE", "Page": 2, "Text": "Zeile zwei"},
            ]}
        return {"JobStatus": status}

    def detect_document_text(self, Document):
        return {"Blocks": [{"BlockType": "LINE", "Page": 1, "Text": "Bildzeile"}]}


class Textract(unittest.TestCase):
    def test_bloecke_zu_seiten(self):
        seiten = _seiten_aus_bloecken([{"BlockType": "LINE", "Page": 2, "Text": "b"}, {"BlockType": "LINE", "Page": 1, "Text": "a"}])
        self.assertEqual([(s.nummer, s.text) for s in seiten], [(1, "a"), (2, "b")])

    def test_pdf_asynchron_und_scan_geloescht(self):
        s3, tx = FakeS3(), FakeTextract(["IN_PROGRESS", "SUCCEEDED"])
        ocr = TextractOcr("eu-central-1", "b", textract=tx, s3=s3, schlafen=lambda s: None)
        seiten = ocr.erkennen(b"%PDF", "application/pdf", "s1", "D1")
        self.assertEqual([s.text for s in seiten], ["Zeile eins", "Zeile zwei"])
        self.assertEqual(s3.objekte, {}, "Der Scan muss nach der Erkennung gelöscht sein.")
        self.assertEqual(tx.ort["S3Object"]["Name"], "sitzungen/s1/scan/D1.pdf")

    def test_fehlschlag_loescht_trotzdem(self):
        s3, tx = FakeS3(), FakeTextract(["FAILED"])
        ocr = TextractOcr("eu-central-1", "b", textract=tx, s3=s3, schlafen=lambda s: None)
        with self.assertRaises(OcrFehler):
            ocr.erkennen(b"%PDF", "application/pdf", "s1", "D1")
        self.assertEqual(s3.objekte, {})

    def test_bild_synchron(self):
        ocr = TextractOcr("eu-central-1", "b", textract=FakeTextract([]), s3=FakeS3())
        self.assertEqual(ocr.erkennen(b"png", "image/png", "s1", "D1")[0].text, "Bildzeile")


def _pdf(seiten: int) -> bytes:
    """Ein echtes PDF mit so vielen leeren Seiten."""
    import io

    from pypdf import PdfWriter

    schreiber = PdfWriter()
    for _ in range(seiten):
        schreiber.add_blank_page(width=200, height=200)
    puffer = io.BytesIO()
    schreiber.write(puffer)
    return puffer.getvalue()


class EinBlattBrauchtKeinenAblageort(unittest.TestCase):
    """Bis zum 01.10.2026 ging jedes PDF über S3 – auch ein Rückschein.

    Der Dateikopf sagte schon damals „mehrseitige PDFs verlangt Textract aus
    S3". Der Quelltext schickte alle. Die Folge war keine falsche Erkennung,
    sondern eine falsche Voraussetzung: Die Kanzlei hätte einen Bucket
    einrichten, sichern und in der DSFA als Ablageort führen müssen, um
    siebzehn Rückscheine zu lesen – von denen die meisten ein Blatt haben.
    """

    def test_ein_einseitiges_pdf_geht_unmittelbar(self):
        s3, tx = FakeS3(), FakeTextract([])
        ocr = TextractOcr("eu-central-1", "b", textract=tx, s3=s3)
        seiten = ocr.erkennen(_pdf(1), "application/pdf", "s1", "D1")
        self.assertEqual([s.text for s in seiten], ["Bildzeile"])
        self.assertEqual(s3.objekte, {}, "Ein Blatt gehört nicht nach S3.")
        self.assertFalse(hasattr(tx, "ort"), "Der asynchrone Weg wurde gar nicht erst betreten.")

    def test_ein_einseitiges_pdf_geht_auch_ohne_bucket(self):
        """Der eigentliche Gewinn: kein Ablageort, kein Eintrag in der DSFA."""
        ocr = TextractOcr("eu-central-1", "", textract=FakeTextract([]), s3=FakeS3())
        self.assertEqual(ocr.erkennen(_pdf(1), "application/pdf", "s1", "D1")[0].text,
                         "Bildzeile")

    def test_auch_ein_mehrseitiges_pdf_geht_ohne_ablageort(self):
        """Aus der Kanzlei am 01.10.2026: „Was gilt bei vielen Seiten?"

        Bis dahin: ein Ablageort in S3. Seitdem nicht mehr – das PDF wird auf
        dem Rechner der Kanzlei Seite für Seite zum Bild gemacht, und jedes
        Bild geht für sich unmittelbar an Textract.

        Der Unterschied ist kein technischer, sondern ein
        datenschutzrechtlicher: zwischen einem Auftragsverarbeiter, der
        Akteninhalt **verarbeitet**, und einem, der ihn **speichert**. Der
        zweite will eingerichtet, verschlüsselt, mit einem Lebenszyklus
        versehen und in der DSFA genannt werden.
        """
        s3, tx = FakeS3(), FakeTextract([])
        ocr = TextractOcr("eu-central-1", "", textract=tx, s3=s3)
        seiten = ocr.erkennen(_pdf(3), "application/pdf", "s1", "D1")
        self.assertEqual(3, len(seiten))
        self.assertEqual(s3.objekte, {}, "Kein Blatt gehört nach S3.")
        self.assertFalse(hasattr(tx, "ort"), "Der asynchrone Weg bleibt unbetreten.")

    def test_die_seitenzahlen_bleiben_die_des_ganzen_dokuments(self):
        """Sonst trägt die Belegpflicht nicht.

        Textract zählt in jedem Aufruf wieder bei 1. Würde das durchgereicht,
        zeigte jede Fundstelle eines mehrseitigen Scans auf Seite 1 – und eine
        Kennung D3-S1-P1, die auf Seite 7 gehört, ist schlimmer als keine: Sie
        sieht aus wie ein Beleg.
        """
        ocr = TextractOcr("eu-central-1", "", textract=FakeTextract([]), s3=FakeS3())
        seiten = ocr.erkennen(_pdf(4), "application/pdf", "s1", "D1")
        self.assertEqual([1, 2, 3, 4], [s.nummer for s in seiten])

    def test_ein_unoeffenbares_pdf_sagt_was_fehlt(self):
        """Der einzige Fall, der noch einen Ablageort braucht.

        Beschädigt oder kennwortgeschützt – dann lässt es sich nicht öffnen.
        Das Programm sagt es, statt einen Fehler von S3 durchzureichen, der
        nach einem Programmfehler aussieht.
        """
        ocr = TextractOcr("eu-central-1", "", textract=FakeTextract([]), s3=FakeS3())
        with self.assertRaises(OcrFehler) as fehler:
            ocr.erkennen(b"kein lesbares PDF", "application/pdf", "s1", "D1")
        text = str(fehler.exception)
        self.assertIn("nicht öffnen", text)
        self.assertIn("AWS-EINRICHTEN.md", text)
        self.assertIn("gleich wie viele Seiten", text)

    def test_ein_unlesbares_pdf_nimmt_den_vorsichtigen_weg(self):
        """Lässt es sich nicht öffnen, geht es über S3 – sofern einer da ist."""
        from jusperfect.ocr.textract import seiten_als_bild, seitenzahl

        self.assertEqual(0, seitenzahl(b"kein PDF"))
        self.assertEqual([], seiten_als_bild(b"kein PDF"))
        s3, tx = FakeS3(), FakeTextract(["SUCCEEDED"])
        ocr = TextractOcr("eu-central-1", "b", textract=tx, s3=s3, schlafen=lambda s: None)
        ocr.erkennen(b"kein PDF", "application/pdf", "s1", "D1")
        self.assertEqual(tx.ort["S3Object"]["Name"], "sitzungen/s1/scan/D1.pdf")

    def test_die_seitenzahl_stimmt(self):
        from jusperfect.ocr.textract import seitenzahl

        for anzahl in (1, 2, 5):
            with self.subTest(anzahl=anzahl):
                self.assertEqual(anzahl, seitenzahl(_pdf(anzahl)))


class EineAbweisungSagtWoranEsLiegt(unittest.TestCase):
    """„Textract nicht verfügbar (ClientError)" stand hier vorher.

    Damit beginnt dieselbe Suche wie am 01.10.2026 beim Modell: Der häufigste
    Grund ist eine fehlende Berechtigung, und der Fehlercode allein sagt das
    nicht. Dort hat es einen Abend gekostet.
    """

    @staticmethod
    def _fehler(code: str, text: str):
        from botocore.exceptions import ClientError

        return ClientError({"Error": {"Code": code, "Message": text}}, "DetectDocumentText")

    def _ocr(self, fehler):
        class _Tx:
            @staticmethod
            def detect_document_text(Document):
                raise fehler

        return TextractOcr("eu-central-1", "", textract=_Tx(), s3=FakeS3())

    def test_die_fehlende_berechtigung_wird_benannt(self):
        fehler = self._fehler(
            "AccessDeniedException",
            "User: arn:aws:iam::579138738703:user/jusperfect-test is not authorized "
            "to perform: textract:DetectDocumentText")
        with self.assertRaises(OcrFehler) as gefangen:
            self._ocr(fehler).erkennen(_pdf(1), "application/pdf", "s1", "D1")
        text = str(gefangen.exception)
        self.assertIn("textract:DetectDocumentText", text)
        self.assertIn("iam-nur-claude.json", text)
        self.assertNotIn("579138738703", text, "Der Wortlaut von AWS bleibt drinnen.")

    def test_ein_unlesbares_blatt_kostet_nicht_die_akte(self):
        fehler = self._fehler("UnsupportedDocumentException", "Request has unsupported document format")
        with self.assertRaises(OcrFehler) as gefangen:
            self._ocr(fehler).erkennen(_pdf(1), "application/pdf", "s1", "D1")
        self.assertIn("bleibt ungelesen, die uebrigen nicht",
                      str(gefangen.exception).replace("übrigen", "uebrigen"))

    def test_ein_unbekannter_fehler_nennt_wenigstens_den_code(self):
        fehler = self._fehler("IrgendwasNeues", "etwas, das wir nicht kennen")
        with self.assertRaises(OcrFehler) as gefangen:
            self._ocr(fehler).erkennen(_pdf(1), "application/pdf", "s1", "D1")
        self.assertIn("IrgendwasNeues", str(gefangen.exception))

    def test_der_wortlaut_von_aws_geht_nie_hinaus(self):
        """In einer Abweisung steht mitunter ein Stück der Anfrage – hier ein
        gescanntes Blatt aus einer Mandatsakte."""
        fehler = self._fehler("AccessDeniedException",
                              "is not authorized to perform – Mandant Reinhold-Özdemir")
        with self.assertRaises(OcrFehler) as gefangen:
            self._ocr(fehler).erkennen(_pdf(1), "application/pdf", "s1", "D1")
        self.assertNotIn("Reinhold", str(gefangen.exception))
