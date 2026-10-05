"""Der AWS-Zugangstest: Er soll die Ursache nennen, nicht nur scheitern.

Geprüft wird vor allem der Weg, der ohne ihn teuer wäre: Wenn der einfache
Aufruf durchgeht und nur die strömende Antwort abgewiesen wird, bestünde ein
oberflächlicher Test – und die erste Frage in der Oberfläche scheiterte mit
einer Meldung, die nicht sagt, dass eine Berechtigung fehlt.
"""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

from jusperfect import awstest


class _Fehler(Exception):
    """Ersatz für botocore.exceptions.ClientError."""

    def __init__(self, code: str, meldung: str = "") -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code, "Message": meldung}}


ANTWORT = {
    "output": {"message": {"content": [{"text": "bereit"}]}},
    "usage": {"inputTokens": 12, "outputTokens": 1},
}


class _BedrockClient:
    def __init__(self, stream_fehler: str | None = None, fehler: str | None = None,
                 meldung: str = "") -> None:
        self._meldung = meldung
        self._stream_fehler = stream_fehler
        self._fehler = fehler
        self.aufrufe: list[str] = []

    def converse(self, **_):
        self.aufrufe.append("converse")
        if self._fehler:
            raise _Fehler(self._fehler, self._meldung)
        return ANTWORT

    def converse_stream(self, **_):
        self.aufrufe.append("converse_stream")
        if self._stream_fehler:
            raise _Fehler(self._stream_fehler)
        return {"stream": iter([{"contentBlockDelta": {}}])}


class _Sitzung:
    def __init__(self, bedrock: _BedrockClient, zugang: object | None = object()) -> None:
        self._bedrock = bedrock
        self._zugang = zugang

    def get_credentials(self):
        return self._zugang

    def client(self, name: str, **_):
        if name == "sts":
            return mock.Mock(get_caller_identity=lambda: {"Arn": "arn:aws:iam::1:user/test"})
        return self._bedrock


def _lauf(bedrock: _BedrockClient, zugang: object | None = object()) -> tuple[int, str]:
    """Führt den Test mit einer erfundenen AWS-Sitzung aus."""
    boto3 = mock.Mock(Session=lambda **_: _Sitzung(bedrock, zugang))
    ausnahmen = mock.Mock(ClientError=_Fehler, NoCredentialsError=_Fehler)
    module = {"boto3": boto3, "botocore": mock.Mock(), "botocore.exceptions": ausnahmen}
    puffer = io.StringIO()
    with mock.patch.dict("sys.modules", module), redirect_stdout(puffer):
        code = awstest.main([])
    return code, puffer.getvalue()


class Zugangstest(unittest.TestCase):
    def test_vollstaendiger_zugang_meldet_beide_wege(self):
        bedrock = _BedrockClient()
        code, ausgabe = _lauf(bedrock)
        self.assertEqual(code, 0)
        self.assertEqual(bedrock.aufrufe, ["converse", "converse_stream"])
        self.assertIn("Der Zugang steht", ausgabe)

    def test_fehlende_stroemende_berechtigung_wird_benannt(self):
        """Der Fall, den ein oberflächlicher Test durchgehen ließe."""
        code, ausgabe = _lauf(_BedrockClient(stream_fehler="AccessDeniedException"))
        self.assertEqual(code, 1)
        self.assertIn("InvokeModelWithResponseStream", ausgabe)
        self.assertNotIn("Der Zugang steht", ausgabe)

    def test_der_wortlaut_von_aws_wird_durchgereicht(self):
        """Der Code allein ist zu grob – der Satz von AWS entscheidet.

        „AccessDeniedException" steht für ein nicht freigeschaltetes Modell,
        für eine fehlende Berechtigung UND für ein ausdrückliches Verbot in
        der Richtlinie. Ohne den Wortlaut wird geraten statt gelesen; genau
        das ist in der Kanzlei passiert.
        """
        code, ausgabe = _lauf(_BedrockClient(
            fehler="AccessDeniedException",
            meldung="You don't have access to the model with the specified model ID."))
        self.assertIn("AWS schreibt dazu", ausgabe)
        self.assertIn("don't have access to the model", ausgabe)

    def test_ohne_wortlaut_bleibt_die_ausgabe_sauber(self):
        """Schickt AWS keinen Satz mit, soll keine leere Zeile dastehen."""
        code, ausgabe = _lauf(_BedrockClient(fehler="AccessDeniedException"))
        self.assertNotIn("AWS schreibt dazu", ausgabe)

    def test_fehlende_freischaltung_nennt_die_ursachen_der_reihe_nach(self):
        """Der haeufigste Abbruch ueberhaupt – die Meldung muss weiterhelfen."""
        code, ausgabe = _lauf(_BedrockClient(fehler="AccessDeniedException"))
        self.assertEqual(code, 1)
        self.assertIn("nicht freigeschaltet", ausgabe)
        # AWS hat die Freischaltseite abgeschafft. Wer dort "has been retired"
        # liest, soll wissen, dass damit diese Ursache ausscheidet - sonst
        # sucht er weiter an der Stelle, an der es nichts mehr zu tun gibt.
        self.assertIn("retired", ausgabe)
        # Die Voreinstellung traegt in Europa inzwischen den Profilvorsatz.
        # Dann ist die zweite Spur nicht mehr das Profil, sondern die
        # Kontonummer in der Richtlinie - sie kommt zweimal vor, und eine
        # uebersehene zweite Stelle weist genau den Profilaufruf ab.
        self.assertIn("ZWEIMAL", ausgabe)
        self.assertIn("Richtlinie", ausgabe)


    def test_der_umstellbefehl_gilt_fuer_beide_fensterarten(self):
        """Aus dem Explorer heraus landet man je nach Windows in PowerShell.

        Dort ist die „set“-Zeile nicht wirkungslos, sondern ein Fehler – und
        man steht vor einer Meldung, die mit der Sache nichts zu tun hat.
        """
        code, ausgabe = _lauf(_BedrockClient(fehler="ValidationException"))
        self.assertIn("set JUSPERFECT_MODELL_ID=eu.", ausgabe)
        self.assertIn('$env:JUSPERFECT_MODELL_ID="eu.', ausgabe)

    def test_falsche_modellkennung_weist_auf_das_inferenzprofil(self):
        code, ausgabe = _lauf(_BedrockClient(fehler="ValidationException"))
        self.assertEqual(code, 1)
        self.assertIn("Inferenzprofil", ausgabe)

    def test_ohne_zugangsdaten_kommt_kein_aufruf_zustande(self):
        bedrock = _BedrockClient()
        code, ausgabe = _lauf(bedrock, zugang=None)
        self.assertEqual(code, 2)
        self.assertEqual(bedrock.aufrufe, [])
        # Der Hinweis muss den Weg nennen, der ohne die AWS CLI auskommt -
        # sie liess sich in der Kanzlei nicht herunterladen, und gebraucht
        # wird sie ohnehin nicht.
        self.assertIn("ZUGANG-EINTRAGEN.bat", ausgabe)


if __name__ == "__main__":
    unittest.main()
