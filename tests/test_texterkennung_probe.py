"""Die Probe, die fragt, ob AWS die Texterkennung annimmt.

Geprüft wird hier, was ohne AWS prüfbar ist: dass das Probeblatt ein
brauchbares PDF ist, dass die Probe denselben Weg geht wie der Betrieb, und
dass sie eine Abweisung erkennbar macht, ohne den Wortlaut von AWS
weiterzureichen.
"""

import io
import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkzeug"))

import texterkennung_probe as probe  # noqa: E402
from jusperfect.domain.models import Seite  # noqa: E402


class DasProbeblatt(unittest.TestCase):
    def test_ist_ein_pdf_mit_genau_einer_seite(self):
        from pypdf import PdfReader

        leser = PdfReader(io.BytesIO(probe.probeblatt()))
        self.assertEqual(1, len(leser.pages))

    def test_traegt_das_probewort(self):
        from pypdf import PdfReader

        leser = PdfReader(io.BytesIO(probe.probeblatt()))
        self.assertIn(probe.PROBEWORT, leser.pages[0].extract_text())

    def test_laesst_sich_zum_bild_machen(self):
        # Denselben Weg geht der Betrieb: erst zum Bild machen, dann je Seite
        # unmittelbar an Textract. Ein Probeblatt, das sich nicht umwandeln
        # laesst, wuerde den asynchronen Weg nehmen und einen Bucket
        # verlangen - und damit etwas anderes pruefen als den Betrieb.
        from jusperfect.ocr.textract import seiten_als_bild

        bilder = seiten_als_bild(probe.probeblatt())
        self.assertEqual(1, len(bilder))
        self.assertTrue(bilder[0].startswith(b"\x89PNG"),
                        "Textract nimmt ueber Bytes nur PNG und JPEG an.")

    def test_das_bild_ist_nicht_leer(self):
        # Der Fehler vom 02.10.2026 war genau dieser: Der Aufruf ging durch
        # und brachte nichts zurueck. Ein weisses Blatt wuerde dasselbe tun -
        # und wieder waere nicht zu unterscheiden, ob die Erkennung schweigt
        # oder das Blatt leer ist.
        from PIL import Image
        from jusperfect.ocr.textract import seiten_als_bild

        bild = Image.open(io.BytesIO(seiten_als_bild(probe.probeblatt())[0]))
        dunkel = sum(1 for punkt in bild.convert("L").tobytes() if punkt < 128)
        self.assertGreater(dunkel, 1000, "Auf dem Probeblatt steht nichts.")

    def test_das_wort_steht_vollstaendig_auf_der_seite(self):
        """Die Probe vom 02.10.2026, nachmittags – und was sie gekostet hat.

        Das Probewort war ``JUSPERFECT TEXTERKENNUNG PROBE``, bei 36 Punkt rund
        594 Punkt breit, beginnend bei x=60 auf einer 595 Punkt breiten Seite.
        AWS las davon 23 Zeichen: ``JUSPERFECT TEXTERKENNUN``. Berechtigung,
        Umwandlung und Erkennung arbeiteten alle richtig – der Satz lief rechts
        aus dem Blatt.

        Gemessen wird deshalb am gerenderten Bild und nicht an einer Schätzung
        der Zeichenbreite. Eine Schätzung war der Fehler.
        """
        from PIL import Image, ImageOps
        from jusperfect.ocr.textract import seiten_als_bild

        bild = Image.open(io.BytesIO(seiten_als_bild(probe.probeblatt())[0])).convert("L")
        links, oben, rechts, unten = ImageOps.invert(bild).getbbox()
        breite, hoehe = bild.size
        self.assertGreater(links, 0, "Das Wort beginnt am Blattrand.")
        self.assertLess(rechts, breite * 0.95, "Das Wort läuft rechts aus dem Blatt.")
        self.assertGreater(oben, 0, "Das Wort beginnt am oberen Rand.")
        self.assertLess(unten, hoehe, "Das Wort läuft unten aus dem Blatt.")

    def test_auch_ein_laengeres_wort_haette_noch_platz(self):
        """Rand, nicht Punktlandung.

        Ein Probewort, das gerade eben passt, ist dasselbe Risiko noch einmal:
        Die nächste Änderung – eine andere Schrift, ein Zeichen mehr – schiebt
        es wieder hinaus, und die Prüfung darüber merkte es erst hinterher.
        """
        from PIL import Image, ImageOps
        from jusperfect.ocr.textract import seiten_als_bild

        laenger = probe.PROBEWORT + " XXXXXXXX"
        bild = Image.open(io.BytesIO(seiten_als_bild(probe.probeblatt(laenger))[0]))
        _, _, rechts, _ = ImageOps.invert(bild.convert("L")).getbbox()
        self.assertLess(rechts, bild.size[0] * 0.95)

    def test_enthaelt_nichts_aus_einer_akte(self):
        # Die Probe baut ihr Blatt selbst. Stuende hier je ein Dateiname,
        # ein Aktenzeichen oder ein Name, ginge Akteninhalt an AWS - und
        # eine Probe, die das tut, darf es nicht geben.
        self.assertEqual("JUSPERFECT PROBE", probe.PROBEWORT)


class DerVergleich(unittest.TestCase):
    def test_findet_das_wort_auch_ueber_zeilen_verteilt(self):
        seiten = [Seite(nummer=1, text="JUSPERFECT\nPROBE")]
        self.assertTrue(probe._gefunden(seiten, probe.PROBEWORT))

    def test_findet_es_nicht_wenn_etwas_anderes_zurueckkommt(self):
        seiten = [Seite(nummer=1, text="irgendetwas")]
        self.assertFalse(probe._gefunden(seiten, probe.PROBEWORT))

    def test_leeres_ergebnis_gilt_nicht_als_treffer(self):
        self.assertFalse(probe._gefunden([], probe.PROBEWORT))


class _Abweisend:
    """Ein Textract, das jeden Aufruf mit fehlendem Recht abweist."""

    def detect_document_text(self, Document):
        fehler = Exception("boom")
        fehler.response = {"Error": {
            "Code": "AccessDeniedException",
            "Message": "User: arn:aws:iam::1234:user/x is not authorized to "
                       "perform: textract:DetectDocumentText",
        }}
        raise fehler


class _Annehmend:
    def detect_document_text(self, Document):
        return {"Blocks": [{"BlockType": "LINE", "Page": 1,
                            "Text": probe.PROBEWORT}]}


class DieProbeAmEchtenWeg(unittest.TestCase):
    """Nicht ein eigener Aufruf, sondern TextractOcr.erkennen selbst."""

    def _erkennung(self, textract):
        from jusperfect.ocr.textract import TextractOcr

        return TextractOcr(region="eu-central-1", bucket="",
                           textract=textract, s3=object())

    def test_ein_angenommenes_blatt_kommt_mit_dem_wort_zurueck(self):
        seiten = self._erkennung(_Annehmend()).erkennen(
            probe.probeblatt(), "application/pdf", "probe", "probeblatt")
        self.assertTrue(probe._gefunden(seiten, probe.PROBEWORT))

    def test_die_fehlende_berechtigung_wird_beim_namen_genannt(self):
        from jusperfect.ocr.base import OcrFehler

        with self.assertRaises(OcrFehler) as gefangen:
            self._erkennung(_Abweisend()).erkennen(
                probe.probeblatt(), "application/pdf", "probe", "probeblatt")
        self.assertIn("textract:DetectDocumentText", str(gefangen.exception))

    def test_der_wortlaut_von_aws_geht_nie_hinaus(self):
        # Dieselbe Regel wie im Betrieb: In einer Abweisung steht mitunter ein
        # Stueck der Anfrage, und das waere hier ein gescanntes Blatt.
        from jusperfect.ocr.base import OcrFehler

        with self.assertRaises(OcrFehler) as gefangen:
            self._erkennung(_Abweisend()).erkennen(
                probe.probeblatt(), "application/pdf", "probe", "probeblatt")
        self.assertNotIn("arn:aws:iam", str(gefangen.exception))
        self.assertNotIn("is not authorized", str(gefangen.exception))

    def test_sie_verlangt_keinen_ablageort(self):
        # Ohne Bucket, und trotzdem geht sie durch: Das ist der Punkt des
        # Zerlegens. Verlangte die Probe einen Bucket, pruefte sie eine
        # Einrichtung, die der Betrieb gar nicht braucht.
        erkennung = self._erkennung(_Annehmend())
        self.assertEqual("", erkennung._bucket)


if __name__ == "__main__":
    unittest.main()
