"""Wenn der Ablageort nicht erreichbar ist: schnell aufgeben und sagen, warum.

Aus der Kanzlei am 02.10.2026, zwei Meldungen in einem Satz:

    „wenn ich erneut Aktengedächtnis anklicke, ist das AWS-Aktengedächtnis
    nicht erreichbar (EndpointConnectionError) – Analyse funktioniert
    anscheinend auch nicht – warte schon seit 4 Minuten"

Es waren nicht zwei Fehler, sondern einer. Die Analyse arbeitete nicht, sie
**wartete**: boto3 nimmt von Haus aus sechzig Sekunden Verbindungszeit und
versucht es mehrfach. Ein Weg, der gesperrt ist, kostete so vier Minuten, bevor
überhaupt eine Meldung kam.

Zweierlei ist daran zu ändern, und beides steht hier fest: Es muss **schnell**
aufgeben, und die Meldung muss den häufigsten Grund nennen. „nicht erreichbar
(EndpointConnectionError)" ist richtig und hilft niemandem – es unterscheidet
nicht zwischen einem fehlenden Ablageort, einer fehlenden Berechtigung und
einem versperrten Weg, und das sind drei Handgriffe an drei Stellen.
"""

from __future__ import annotations

import unittest

from jusperfect.gedaechtnis.aws import (
    LESEZEIT_SEKUNDEN,
    VERBINDUNGSZEIT_SEKUNDEN,
    VERSUCHE,
    AwsGedaechtnisSpeicher,
    _nicht_erreichbar,
)
from jusperfect.gedaechtnis.base import GedaechtnisFehler


class EndpointConnectionError(Exception):
    """Trägt denselben Namen wie die Ausnahme von botocore – darauf kommt es an."""


class DieWartezeit(unittest.TestCase):
    def test_sie_ist_kurz(self):
        """Ein Ablageort im selben Rechenzentrum antwortet in Millisekunden.

        Antwortet er nach fünf Sekunden nicht, antwortet er auch nach sechzig
        nicht. Sechzig war die Voreinstellung von boto3 und der Grund für die
        vier Minuten.
        """
        self.assertLessEqual(VERBINDUNGSZEIT_SEKUNDEN, 10)
        self.assertLessEqual(VERSUCHE, 3)
        self.assertLessEqual(VERBINDUNGSZEIT_SEKUNDEN * VERSUCHE, 30,
                             "Im schlimmsten Fall soll es in einer halben Minute vorbei sein.")

    def test_lesen_darf_laenger_dauern_als_verbinden(self):
        self.assertGreater(LESEZEIT_SEKUNDEN, VERBINDUNGSZEIT_SEKUNDEN)


class DieMeldung(unittest.TestCase):
    def test_der_versperrte_weg_wird_benannt(self):
        satz = _nicht_erreichbar(EndpointConnectionError("egal"))
        self.assertIn("KEIN Berechtigungsfehler", satz)
        self.assertIn("Firewall", satz)
        self.assertIn("GEDAECHTNIS-AWS-PRUEFEN.bat", satz)

    def test_sie_sagt_warum_das_modell_trotzdem_laeuft(self):
        """Genau diese Gleichzeitigkeit verwirrt: Fragen gehen, Gedächtnis nicht.

        Das Modell läuft über eine andere Adresse. Wer das nicht weiß, hält den
        Zugang für kaputt, obwohl er steht.
        """
        self.assertIn("andere Adresse", _nicht_erreichbar(EndpointConnectionError("x")))

    def test_ein_fehlender_ablageort_wird_anders_benannt(self):
        fehler = Exception("x")
        fehler.response = {"Error": {"Code": "NoSuchBucket"}}
        self.assertIn("gibt es nicht", _nicht_erreichbar(fehler))

    def test_eine_fehlende_berechtigung_wird_anders_benannt(self):
        fehler = Exception("x")
        fehler.response = {"Error": {"Code": "AccessDenied"}}
        self.assertIn("s3:PutObject", _nicht_erreichbar(fehler))

    def test_der_wortlaut_von_aws_geht_nie_hinaus(self):
        """Erkannt wird am Namen der Ausnahme und am Code – beide tragen nichts."""
        fehler = Exception("Mandant Testmann, Schriftsatz vom 02.10.2026")
        fehler.response = {"Error": {"Code": "AccessDenied",
                                     "Message": "Mandant Testmann"}}
        self.assertNotIn("Testmann", _nicht_erreichbar(fehler))

    def test_unbekanntes_bleibt_beim_namen_der_ausnahme(self):
        self.assertIn("ValueError", _nicht_erreichbar(ValueError("x")))


class _S3Sperrt:
    def get_object(self, **kw):
        raise EndpointConnectionError("Could not connect to the endpoint URL")

    def put_object(self, **kw):
        raise EndpointConnectionError("Could not connect to the endpoint URL")


class AmEchtenWeg(unittest.TestCase):
    def test_lesen_sagt_was_los_ist(self):
        speicher = AwsGedaechtnisSpeicher("eimer", "eu-central-1", "schluessel",
                                          s3=_S3Sperrt())
        with self.assertRaises(GedaechtnisFehler) as gefangen:
            speicher.lesen("X-100-2026")
        self.assertIn("Firewall", str(gefangen.exception))

    def test_und_die_aktenkennung_steht_nicht_in_der_meldung(self):
        speicher = AwsGedaechtnisSpeicher("eimer", "eu-central-1", "schluessel",
                                          s3=_S3Sperrt())
        with self.assertRaises(GedaechtnisFehler) as gefangen:
            speicher.lesen("X-100-2026")
        self.assertNotIn("X-100-2026", str(gefangen.exception))


if __name__ == "__main__":
    unittest.main()
