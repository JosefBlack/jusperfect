"""„Welche Modelle darf dieses Konto?" – gefragt, nicht geraten.

Aus der Kanzlei: Im Modellkatalog stand weder „Access granted" noch
„Available to request". Die AWS-Konsole baut diese Seite regelmäßig um; wer
dort sucht, sucht je nach Woche woanders. Das Konto selbst weiß es genau.
"""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from jusperfect import modelle


class _Bedrock:
    def __init__(self, summaries, fehler: str | None = None):
        self._summaries = summaries
        self._fehler = fehler
        self.aufrufe = []

    def list_foundation_models(self, **kw):
        self.aufrufe.append(kw)
        if self._fehler:
            from botocore.exceptions import ClientError
            raise ClientError({"Error": {"Code": self._fehler}}, "ListFoundationModels")
        return {"modelSummaries": self._summaries}


def _modell(kennung, wege, status="ACTIVE"):
    return {"modelId": kennung, "inferenceTypesSupported": wege,
            "modelLifecycleStatus": {"status": status}}


def _lauf(bedrock, umgebung=None, argv=("--ohne-aufruf",)):
    """Standardmaessig ohne Anprobe – die Katalogausgabe ist hier gemeint."""
    puffer = io.StringIO()
    with patch("boto3.client", return_value=bedrock), \
         patch.dict("os.environ", umgebung or {}, clear=False), \
         redirect_stdout(puffer):
        code = modelle.main(list(argv))
    return code, puffer.getvalue()


def _mit_anprobe(bedrock, ergebnisse, umgebung=None):
    """``ergebnisse``: Kennung -> (geht, Grund)."""
    puffer = io.StringIO()
    def anprobe(region, kennung):
        return ergebnisse.get(kennung, (False, "unbekannt"))
    with patch("boto3.client", return_value=bedrock), \
         patch.object(modelle, "_anprobieren", anprobe), \
         patch.dict("os.environ", umgebung or {}, clear=False), \
         redirect_stdout(puffer):
        code = modelle.main([])
    return code, puffer.getvalue()


class Modellliste(unittest.TestCase):
    def setUp(self):
        try:
            import boto3  # noqa: F401
        except ImportError:
            self.skipTest("boto3 ist in dieser Umgebung nicht installiert.")

    def test_trennt_unmittelbare_von_profilgebundenen_modellen(self):
        """Die eine Unterscheidung, an der die Einrichtung haengt."""
        bedrock = _Bedrock([
            _modell("anthropic.claude-haiku-4-5", ["ON_DEMAND"]),
            _modell("anthropic.claude-opus-5", ["INFERENCE_PROFILE"]),
        ])
        code, ausgabe = _lauf(bedrock)
        self.assertEqual(code, 0)
        self.assertIn("anthropic.claude-haiku-4-5", ausgabe)
        # Profilgebundene erscheinen MIT dem Vorsatz - so muss man sie eintragen.
        self.assertIn("eu.anthropic.claude-opus-5", ausgabe)

    def test_fragt_nur_nach_anthropic(self):
        bedrock = _Bedrock([_modell("anthropic.claude-opus-5", ["ON_DEMAND"])])
        _lauf(bedrock)
        self.assertEqual(bedrock.aufrufe[0]["byProvider"], "anthropic")

    def test_ausgemusterte_modelle_werden_verschwiegen(self):
        """Eine Liste voller Altlasten hilft niemandem beim Einrichten."""
        bedrock = _Bedrock([
            _modell("anthropic.claude-v1", ["ON_DEMAND"], status="LEGACY"),
            _modell("anthropic.claude-opus-5", ["ON_DEMAND"]),
        ])
        code, ausgabe = _lauf(bedrock)
        self.assertNotIn("claude-v1", ausgabe)
        self.assertIn("claude-opus-5", ausgabe)

    def test_unbekannte_kennung_bekommt_einen_vorschlag(self):
        bedrock = _Bedrock([_modell("anthropic.claude-haiku-4-5", ["ON_DEMAND"])])
        code, ausgabe = _lauf(bedrock, {"JUSPERFECT_MODELL_ID": "anthropic.claude-erfunden"})
        self.assertIn("steht in keiner der beiden Listen", ausgabe)
        self.assertIn("set JUSPERFECT_MODELL_ID=anthropic.claude-haiku-4-5", ausgabe)
        # Beide Fensterarten - aus dem Explorer landet man oft in PowerShell.
        self.assertIn('$env:JUSPERFECT_MODELL_ID="anthropic.claude-haiku-4-5"', ausgabe)

    def test_bekannte_kennung_verweist_auf_die_richtlinie(self):
        """Vorhanden heisst nicht aufrufbar – der Unterschied muss dastehen.

        Die Freischaltseite hat AWS abgeschafft; bleibt als Ursache die
        Richtlinie am Benutzer.
        """
        bedrock = _Bedrock([_modell("anthropic.claude-opus-5", ["INFERENCE_PROFILE"])])
        code, ausgabe = _lauf(bedrock, {"JUSPERFECT_MODELL_ID": "eu.anthropic.claude-opus-5"})
        self.assertIn("steht in der Liste", ausgabe)
        self.assertIn("Berechtigungen", ausgabe)


    def test_profilkennung_wird_als_bekannt_erkannt(self):
        bedrock = _Bedrock([_modell("anthropic.claude-opus-5", ["INFERENCE_PROFILE"])])
        code, ausgabe = _lauf(bedrock, {"JUSPERFECT_MODELL_ID": "eu.anthropic.claude-opus-5"})
        self.assertIn("steht in der Liste", ausgabe)

    def test_anprobe_trennt_zugeteilt_von_nicht_zugeteilt(self):
        """Der Kern: „vorhanden" und „darf ich" sind zwei verschiedene Fragen.

        Der Katalog nannte in der Kanzlei dreizehn Modelle. Aufrufbar war
        genau eines. Diesen Unterschied haben wir dreimal für einen
        Einrichtungsfehler gehalten.
        """
        bedrock = _Bedrock([
            _modell("anthropic.claude-opus-5", ["INFERENCE_PROFILE"]),
            _modell("anthropic.claude-haiku-4-5", ["INFERENCE_PROFILE"]),
        ])
        code, ausgabe = _mit_anprobe(bedrock, {
            "eu.anthropic.claude-opus-5": (False, "diesem Konto nicht zugeteilt"),
            "eu.anthropic.claude-haiku-4-5": (True, ""),
        })
        self.assertEqual(code, 0)
        self.assertIn("✓  eu.anthropic.claude-haiku-4-5", ausgabe)
        self.assertIn("✗  eu.anthropic.claude-opus-5", ausgabe)
        self.assertIn("nicht zugeteilt", ausgabe)

    def test_anprobe_schlaegt_ein_brauchbares_modell_vor(self):
        bedrock = _Bedrock([_modell("anthropic.claude-haiku-4-5", ["INFERENCE_PROFILE"])])
        code, ausgabe = _mit_anprobe(
            bedrock, {"eu.anthropic.claude-haiku-4-5": (True, "")},
            {"JUSPERFECT_MODELL_ID": "eu.anthropic.claude-opus-5"})
        self.assertIn("ist nicht dabei", ausgabe)
        self.assertIn('$env:JUSPERFECT_MODELL_ID="eu.anthropic.claude-haiku-4-5"', ausgabe)
        self.assertIn("START-AWS.bat", ausgabe)

    def test_anprobe_bestaetigt_das_eingestellte_modell(self):
        bedrock = _Bedrock([_modell("anthropic.claude-haiku-4-5", ["INFERENCE_PROFILE"])])
        code, ausgabe = _mit_anprobe(
            bedrock, {"eu.anthropic.claude-haiku-4-5": (True, "")},
            {"JUSPERFECT_MODELL_ID": "eu.anthropic.claude-haiku-4-5"})
        self.assertIn("funktioniert", ausgabe)
        self.assertIn("Nichts zu tun", ausgabe)

    def test_wenn_gar_nichts_geht_ist_es_kein_einrichtungsfehler(self):
        """Die wichtigste Auskunft überhaupt – sonst sucht man weiter."""
        bedrock = _Bedrock([_modell("anthropic.claude-opus-5", ["INFERENCE_PROFILE"])])
        code, ausgabe = _mit_anprobe(
            bedrock, {"eu.anthropic.claude-opus-5": (False, "diesem Konto nicht zugeteilt")})
        self.assertIn("kein Einrichtungsfehler", ausgabe)

    def test_profilgebundene_werden_mit_vorsatz_angeprobiert(self):
        """Ohne „eu." wäre die Anprobe wertlos – so sind sie nicht aufrufbar."""
        bedrock = _Bedrock([_modell("anthropic.claude-opus-5", ["INFERENCE_PROFILE"])])
        versucht = []
        def anprobe(region, kennung):
            versucht.append(kennung)
            return (True, "")
        puffer = io.StringIO()
        with patch("boto3.client", return_value=bedrock), \
             patch.object(modelle, "_anprobieren", anprobe), \
             redirect_stdout(puffer):
            modelle.main([])
        self.assertEqual(versucht, ["eu.anthropic.claude-opus-5"])

    def test_ohne_aufruf_bleibt_es_beim_katalog(self):
        """Wer nichts ausgeben will, soll die Wahl haben."""
        bedrock = _Bedrock([_modell("anthropic.claude-opus-5", ["INFERENCE_PROFILE"])])
        code, ausgabe = _lauf(bedrock)
        self.assertNotIn("Probiere jedes Modell", ausgabe)

    def test_leere_region_wird_erklaert(self):
        code, ausgabe = _lauf(_Bedrock([]))
        self.assertEqual(code, 1)
        self.assertIn("eu-central-1", ausgabe)

    def test_fehlende_leseberechtigung_nennt_die_stelle(self):
        code, ausgabe = _lauf(_Bedrock([], fehler="AccessDeniedException"))
        self.assertEqual(code, 2)
        self.assertIn("ListFoundationModels", ausgabe)

    def test_es_wird_kein_modell_aufgerufen(self):
        """Der Befehl darf nichts kosten – sonst taugt er nicht zum Nachsehen."""
        bedrock = _Bedrock([_modell("anthropic.claude-opus-5", ["ON_DEMAND"])])
        _lauf(bedrock)
        self.assertFalse(hasattr(bedrock, "converse"),
                         "Das Testdouble kennt converse gar nicht – gut so.")
        self.assertEqual(len(bedrock.aufrufe), 1)


if __name__ == "__main__":
    unittest.main()
