"""Welche Berechtigung AWS vermisst – und sonst nichts.

Am 02.10.2026 meldete das Programm: „Die Zugriffsrichtlinie erlaubt diesen
Aufruf nicht." Welcher Aufruf, stand nicht dabei – und damit beginnt dieselbe
Suche wie am Tag zuvor beim Modell: ein halbes Dutzend Handlungen kommen in
Frage, geraten wird reihum.

Die Angabe steht in der Meldung von AWS. Sie geht trotzdem nicht als Ganzes
hinaus: In einer Ablehnung steht mitunter ein Stück der Anfrage, und das ist
Aktentext. Herausgelöst wird deshalb **nur der Name der Handlung** – ein
Dienstkürzel aus einer festen Liste, ein Doppelpunkt, ein Wort aus Buchstaben.

Diese Prüfungen halten beides fest: dass der Name ankommt, und dass sonst
nichts mitkommt.
"""

from __future__ import annotations

import unittest

from jusperfect.aws_handlung import handlung, mit_handlung


def _fehler(meldung: str, code: str = "AccessDeniedException") -> Exception:
    f = Exception("abgelehnt")
    f.response = {"Error": {"Code": code, "Message": meldung}}
    return f


ECHT = (
    "User: arn:aws:iam::579138738703:user/jusperfect-test is not authorized to "
    "perform: bedrock:ApplyGuardrail on resource: arn:aws:bedrock:eu-central-1:"
    "579138738703:guardrail/abc123 because no identity-based policy allows the "
    "bedrock:ApplyGuardrail action"
)


class DerNameKommtAn(unittest.TestCase):
    def test_aus_einer_echten_meldung(self):
        self.assertEqual("bedrock:ApplyGuardrail", handlung(_fehler(ECHT)))

    def test_auch_fuer_textract(self):
        self.assertEqual(
            "textract:DetectDocumentText",
            handlung(_fehler("User: x is not authorized to perform: "
                             "textract:DetectDocumentText on resource: *")))

    def test_gross_und_kleinschreibung_schadet_nicht(self):
        self.assertEqual(
            "s3:PutObject",
            handlung(_fehler("Is Not Authorized To Perform: s3:PutObject")))

    def test_er_wird_an_den_eigenen_satz_gehaengt(self):
        satz = mit_handlung("Die Richtlinie erlaubt das nicht.", _fehler(ECHT))
        self.assertIn("Es fehlt: bedrock:ApplyGuardrail.", satz)
        self.assertTrue(satz.startswith("Die Richtlinie erlaubt das nicht."))


class SonstKommtNichtsMit(unittest.TestCase):
    """Der eigentliche Zweck dieser Datei."""

    def test_der_wortlaut_von_aws_bleibt_drinnen(self):
        satz = mit_handlung("Eigener Satz.", _fehler(ECHT))
        for stueck in ("arn:aws:iam", "579138738703", "identity-based",
                       "on resource", "jusperfect-test"):
            self.assertNotIn(stueck, satz)

    def test_ein_unbekannter_dienst_geht_nicht_hinaus(self):
        """Eine feste Liste, kein ``\\w+`` – sonst reicht jeder Text durch."""
        self.assertEqual("", handlung(_fehler(
            "is not authorized to perform: dynamodb:GetItem")))

    def test_was_nicht_wie_eine_handlung_aussieht_geht_nicht_hinaus(self):
        for meldung in (
            "is not authorized to perform: bedrock:Invoke Model Testmann ./2026",
            "is not authorized to perform: bedrock:",
            "is not authorized to perform: Mandant Testmann",
            "Zugriff verweigert",
        ):
            with self.subTest(meldung=meldung):
                name = handlung(_fehler(meldung))
                self.assertNotIn("Testmann", name)
                self.assertNotIn(" ", name)

    def test_ohne_antwort_von_aws_bleibt_der_satz_wie_er_ist(self):
        self.assertEqual("Eigener Satz.", mit_handlung("Eigener Satz.", Exception("x")))

    def test_eine_handlung_kann_keinen_aktentext_tragen(self):
        """Das Muster lässt nur Buchstaben zu – kein Leerzeichen, keine Ziffer.

        Darauf beruht die ganze Zusage. Wäre hier ein ``.*``, stünde eines
        Tages ein Dateiname aus einer Mandatsakte auf dem Bildschirm.
        """
        name = handlung(_fehler(
            "is not authorized to perform: bedrock:ApplyGuardrail "
            "beim Schriftsatz Testmann vom 02.10.2026"))
        self.assertEqual("bedrock:ApplyGuardrail", name)


class AmEchtenWeg(unittest.TestCase):
    def test_bedrock_nennt_die_handlung(self):
        from jusperfect.providers.bedrock import _abgelehnt

        satz = _abgelehnt(_fehler(ECHT), "eu.anthropic.claude-opus-4-6-v1")
        self.assertIn("Es fehlt: bedrock:ApplyGuardrail.", satz)
        self.assertNotIn("arn:aws:iam", satz)

    def test_textract_nennt_die_handlung(self):
        from jusperfect.ocr.textract import _warum

        satz = _warum(_fehler(
            "User: x is not authorized to perform: textract:DetectDocumentText"))
        self.assertIn("Es fehlt: textract:DetectDocumentText.", satz)


if __name__ == "__main__":
    unittest.main()
