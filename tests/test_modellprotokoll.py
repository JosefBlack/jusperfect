"""Schreibt AWS die Modellaufrufe mit? – die Prüfung beim Start.

Grundsatz 5 des Sicherheitsmodells sagt seit jeher „Bedrock-Modell­aufruf­proto­kol­lie­rung
bleibt aus". Geprüft hat es bis hierher niemand, und man sieht es dem laufenden
Programm nicht an: Ist sie eingeschaltet, schreibt AWS den vollständigen Prompt
mit – und der Prompt ist der Aktentext.

Aus der Kanzlei: „Ich möchte bald loslegen und erste Versuche mit echten Akten
machen." Genau dafür ist diese Prüfung da. Deshalb prüft diese Datei nicht nur,
ob der Zustand richtig erkannt wird, sondern vor allem, **was bei Ungewissheit
geschieht** – und dass der Unterschied an den Akten hängt, nicht an einer
Einstellung, die man wegklicken kann.
"""

from __future__ import annotations

import unittest

from jusperfect import modellprotokoll
from jusperfect.config import KonfigurationsFehler
from jusperfect.modellprotokoll import AN, AUS, UNBEKANNT, Befund, beim_start_pruefen, pruefen
from tests.hilfen import einstellungen


class _Client:
    """Ein Bedrock-Client, der genau eine Frage beantwortet."""

    def __init__(self, antwort: dict | None = None, fehler: Exception | None = None) -> None:
        self._antwort, self._fehler = antwort or {}, fehler
        self.gefragt = 0

    def get_model_invocation_logging_configuration(self) -> dict:
        self.gefragt += 1
        if self._fehler:
            raise self._fehler
        return self._antwort


def _aws_fehler(code: str) -> Exception:
    fehler = RuntimeError(code)
    fehler.response = {"Error": {"Code": code, "Message": code}}
    return fehler


def _bedrock(**extra):
    return einstellungen(JUSPERFECT_ANBIETER="bedrock", **extra)


class WasDerBefundSagt(unittest.TestCase):

    def test_ohne_konfiguration_wird_nichts_mitgeschrieben(self):
        b = pruefen("eu-central-1", client=_Client({}))
        self.assertEqual(AUS, b.zustand)
        self.assertTrue(b.unbedenklich)

    def test_nie_eingerichtet_ist_eine_antwort_kein_fehler(self):
        """AWS meldet „ResourceNotFoundException", wenn nie etwas eingerichtet wurde."""
        b = pruefen("eu-central-1", client=_Client(fehler=_aws_fehler("ResourceNotFoundException")))
        self.assertEqual(AUS, b.zustand)

    def test_eingeschaltete_textauslieferung_ist_an(self):
        b = pruefen("eu-central-1", client=_Client({"loggingConfig": {
            "textDataDeliveryEnabled": True,
            "cloudWatchConfig": {"logGroupName": "bedrock"}}}))
        self.assertEqual(AN, b.zustand)
        self.assertIn("Aktentext", b.satz)
        self.assertTrue(any("CloudWatch" in t for t in b.einzelheiten))

    def test_auch_gescannte_seiten_zaehlen(self):
        """Bilder sind bei einer Scanakte der Aktentext."""
        b = pruefen("eu-central-1", client=_Client({"loggingConfig": {
            "imageDataDeliveryEnabled": True, "s3Config": {"bucketName": "x"}}}))
        self.assertEqual(AN, b.zustand)

    def test_eingerichtet_aber_ohne_inhalte_traegt_nichts_hinaus(self):
        b = pruefen("eu-central-1", client=_Client({"loggingConfig": {
            "textDataDeliveryEnabled": False, "imageDataDeliveryEnabled": False,
            "s3Config": {"bucketName": "x"}}}))
        self.assertEqual(AUS, b.zustand)

    def test_fehlendes_leserecht_ist_ungewissheit_kein_ja_und_kein_nein(self):
        b = pruefen("eu-central-1", client=_Client(fehler=_aws_fehler("AccessDeniedException")))
        self.assertEqual(UNBEKANNT, b.zustand)
        self.assertTrue(any("GetModelInvocationLoggingConfiguration" in t for t in b.einzelheiten),
                        "Der Satz muss sagen, welches Recht fehlt - sonst sucht die Kanzlei.")

    def test_gestoertes_netz_ist_ebenfalls_ungewissheit(self):
        b = pruefen("eu-central-1", client=_Client(fehler=TimeoutError("kein Netz")))
        self.assertEqual(UNBEKANNT, b.zustand)


class WasBeimStartGeschieht(unittest.TestCase):

    def test_ohne_bedrock_wird_gar_nicht_gefragt(self):
        """Der Demo-Anbieter rechnet hier; es gibt keinen Aufruf mitzuschreiben."""
        client = _Client({})
        self.assertIsNone(beim_start_pruefen(einstellungen(), client=client))
        self.assertEqual(0, client.gefragt)

    def test_eingeschaltete_protokollierung_haelt_das_programm_an(self):
        client = _Client({"loggingConfig": {"textDataDeliveryEnabled": True}})
        with self.assertRaises(KonfigurationsFehler) as fehler:
            beim_start_pruefen(_bedrock(), client=client)
        self.assertIn("startet deshalb nicht", str(fehler.exception))
        self.assertIn("abschalten", str(fehler.exception))

    def test_sie_haelt_auch_bei_den_testakten_an(self):
        """Hier gibt es keine Abstufung: Abschalten dauert Sekunden."""
        client = _Client({"loggingConfig": {"textDataDeliveryEnabled": True}})
        with self.assertRaises(KonfigurationsFehler):
            beim_start_pruefen(_bedrock(JUSPERFECT_JURNODES_ADAPTER="fixture"), client=client)

    def test_ungewissheit_haelt_bei_echten_akten_an(self):
        client = _Client(fehler=_aws_fehler("AccessDeniedException"))
        with self.assertRaises(KonfigurationsFehler) as fehler:
            beim_start_pruefen(
                # Mit echten Akten verlangen die Einstellungen ein Guardrail;
                # ohne das kaeme dieser Aufbau gar nicht erst zustande.
                _bedrock(JUSPERFECT_JURNODES_ADAPTER="webdav",
                         JUSPERFECT_JURNODES_WEBDAV="J:\\Akten",
                         JUSPERFECT_GUARDRAIL_ID="gr-1",
                         JUSPERFECT_GEDAECHTNIS="aus"),
                client=client)
        self.assertIn("Mit echten Akten ist das ein Nein", str(fehler.exception))

    def test_ungewissheit_haelt_bei_den_testakten_nicht_an(self):
        """Sonst stünde die Kanzlei bei einer Netzstörung vor einem toten Programm –
        wegen erfundener Akten."""
        client = _Client(fehler=TimeoutError("kein Netz"))
        befund = beim_start_pruefen(_bedrock(), client=client)
        self.assertEqual(UNBEKANNT, befund.zustand)

    def test_alles_in_ordnung_gibt_einen_befund_zurueck(self):
        befund = beim_start_pruefen(_bedrock(), client=_Client({}))
        self.assertEqual(AUS, befund.zustand)


class DerBefundStehtImStatus(unittest.TestCase):
    """Die Kanzlei soll nachsehen können, ohne jemanden zu fragen."""

    def test_ohne_bedrock_steht_dort_nichts(self):
        from tests.hilfen import client as testclient, dienste
        antwort = testclient(dienste()).get("/api/status").json()
        self.assertIn("modellprotokoll", antwort)
        self.assertIsNone(antwort["modellprotokoll"])

    def test_ein_befund_wird_durchgereicht(self):
        from fastapi.testclient import TestClient

        from jusperfect.web import app_erstellen
        from tests.hilfen import dienste

        d = dienste()
        app = app_erstellen(d.einstellungen, d)
        d.modellprotokoll = Befund(AUS, "AWS schreibt die Modellaufrufe nicht mit.")
        c = TestClient(app, headers={"X-Jusperfect-Nutzer": "ra-weber"})
        self.assertEqual("aus", c.get("/api/status").json()["modellprotokoll"]["zustand"])


class DasLeserechtStehtInDerRichtlinie(unittest.TestCase):
    """Ohne das Recht liefe die Prüfung immer in die Ungewissheit."""

    def test_die_richtlinie_erlaubt_das_lesen(self):
        import json
        from pathlib import Path

        richtlinie = json.loads(
            (Path(__file__).resolve().parent.parent / "infra" / "iam-nur-claude.json")
            .read_text(encoding="utf-8"))
        erlaubt = [aktion for satz in richtlinie["Statement"] if satz["Effect"] == "Allow"
                   for aktion in satz["Action"]]
        self.assertIn("bedrock:GetModelInvocationLoggingConfiguration", erlaubt)

    def test_das_aendern_bleibt_verboten(self):
        import json
        from pathlib import Path

        richtlinie = json.loads(
            (Path(__file__).resolve().parent.parent / "infra" / "iam-nur-claude.json")
            .read_text(encoding="utf-8"))
        verboten = [aktion for satz in richtlinie["Statement"] if satz["Effect"] == "Deny"
                    for aktion in (satz.get("Action") if isinstance(satz.get("Action"), list)
                                   else [satz.get("Action")])]
        self.assertIn("bedrock:PutModelInvocationLoggingConfiguration", verboten)
        self.assertIn("bedrock:DeleteModelInvocationLoggingConfiguration", verboten)


if __name__ == "__main__":
    unittest.main()


class DieRichtlinieBleibtEineRichtlinie(unittest.TestCase):
    """Ein fremdes Feld macht sie unbrauchbar – und das fällt erst in AWS auf.

    Beim Eintragen der Texterkennung am 01.10.2026 stand beinahe ein Feld
    `Comment` in der Anweisung – gut gemeint, als Begründung daneben. AWS kennt
    in einer Richtlinie kein solches Feld und weist sie ab. Die Kanzlei hätte
    die Datei eingefügt und eine Fehlermeldung bekommen, die nicht sagt, woher
    sie kommt.

    Begründungen gehören nach `infra/IAM.md`, nicht in die Richtlinie.
    """

    ERLAUBTE_FELDER = {"Sid", "Effect", "Action", "NotAction",
                       "Resource", "NotResource", "Condition", "Principal"}

    def _richtlinie(self):
        import json
        from pathlib import Path

        return json.loads(
            (Path(__file__).resolve().parent.parent / "infra" / "iam-nur-claude.json")
            .read_text(encoding="utf-8"))

    def test_keine_fremden_felder(self):
        for satz in self._richtlinie()["Statement"]:
            with self.subTest(sid=satz.get("Sid")):
                self.assertLessEqual(set(satz), self.ERLAUBTE_FELDER)

    def test_die_texterkennung_steht_darin(self):
        erlaubt = []
        for satz in self._richtlinie()["Statement"]:
            if satz["Effect"] != "Allow":
                continue
            aktion = satz["Action"]
            erlaubt += aktion if isinstance(aktion, list) else [aktion]
        self.assertIn("textract:DetectDocumentText", erlaubt)

    def test_der_mehrseitige_weg_bleibt_draussen(self):
        """Er verlangt einen Ablageort in S3 – ein Ort mehr, an dem Akten liegen."""
        from pathlib import Path

        text = (Path(__file__).resolve().parent.parent
                / "infra" / "iam-nur-claude.json").read_text(encoding="utf-8")
        self.assertNotIn("StartDocumentTextDetection", text)

    def test_die_beschreibung_nennt_sie_auch(self):
        """Zwei Dateien, die dasselbe beschreiben, laufen sonst auseinander."""
        from pathlib import Path

        text = (Path(__file__).resolve().parent.parent
                / "infra" / "IAM.md").read_text(encoding="utf-8")
        self.assertIn("TexterkennungFuerScans", text)
        self.assertIn("textract:DetectDocumentText", text)

    def test_das_schutzgelaender_darf_angewandt_werden(self):
        """Ohne dieses Recht geht KEIN Modellaufruf durch.

        Aus der Kanzlei am 02.10.2026: „Akte einlesen funktioniert nicht – IAM
        lässt dieses nicht zu." Das Programm schickt bei jedem Aufruf das
        Schutzgeländer mit, und AWS verlangt dafür ein eigenes Recht; es
        genügt nicht, ``bedrock:InvokeModel`` zu dürfen.
        """
        erlaubt = []
        for satz in self._richtlinie()["Statement"]:
            if satz["Effect"] != "Allow":
                continue
            aktion = satz["Action"]
            erlaubt += aktion if isinstance(aktion, list) else [aktion]
        self.assertIn("bedrock:ApplyGuardrail", erlaubt)

    def test_das_recht_gilt_nur_fuer_gelaender_in_der_eu(self):
        """Eng gefasst, und ohne Platzhalter.

        Geprüft wird die **Zusage**, nicht der Wortlaut: Am 05.10.2026 ist aus
        der einen Zeile ``arn:aws:bedrock:eu-*:*:guardrail/*`` eine Liste
        geworden — die sechs EU- und EWR-Regionen, je für ``guardrail`` und
        ``guardrail-profile``. Ein Test, der die alte Zeile wörtlich verlangte,
        hätte die Verbesserung zum Fehler erklärt.

        Der Platzhalter ``AWS-KONTONUMMER`` in den beiden anderen Anweisungen
        hat am 02.10.2026 in der Kanzlei eine rote Zeile erzeugt. Eine Angabe,
        die eingetragen werden **muss**, ist eine Fehlerquelle – hier wird
        keine gebraucht.
        """
        from jusperfect.config import EU_EWR_REGIONEN

        satz = next(s for s in self._richtlinie()["Statement"]
                    if s.get("Sid") == "SchutzgelaenderAnwenden")
        ressourcen = satz["Resource"]
        self.assertIsInstance(ressourcen, list)
        for eintrag in ressourcen:
            # Nur Geländer, nur in einer der namentlich genannten Regionen,
            # und ohne Platzhalter.
            self.assertRegex(eintrag, r":(guardrail|guardrail-profile)/\*$")
            self.assertIn(eintrag.split(":")[3], EU_EWR_REGIONEN)
            self.assertNotIn("AWS-KONTONUMMER", eintrag)
        # "eu-*" haette Zuerich und London eingeschlossen.
        self.assertNotIn("eu-*", " ".join(ressourcen))

    def test_aendern_und_loeschen_bleibt_verboten(self):
        """Anwenden ist etwas anderes als verwalten.

        ``KeineModellverwaltung`` verbietet ``DeleteGuardrail`` und
        ``UpdateGuardrail``. Das neue Recht weitet daran nichts auf – wer
        prüfen lässt, darf deshalb noch lange nicht abschalten.
        """
        verboten = []
        for satz in self._richtlinie()["Statement"]:
            if satz["Effect"] != "Deny":
                continue
            aktion = satz.get("Action", [])
            verboten += aktion if isinstance(aktion, list) else [aktion]
        self.assertIn("bedrock:DeleteGuardrail", verboten)
        self.assertIn("bedrock:UpdateGuardrail", verboten)

    def test_die_beschreibung_nennt_auch_das_gelaender(self):
        from pathlib import Path

        text = (Path(__file__).resolve().parent.parent
                / "infra" / "IAM.md").read_text(encoding="utf-8")
        self.assertIn("SchutzgelaenderAnwenden", text)
        self.assertIn("bedrock:ApplyGuardrail", text)

    def test_die_zahl_der_anweisungen_stimmt_mit_der_beschreibung(self):
        """„Was die sechs Anweisungen tun" bei sieben Anweisungen ist falsch.

        Eine Zahl im Fließtext ist die Stelle, an der zwei Dateien zuerst
        auseinanderlaufen – sie fällt niemandem auf.
        """
        from pathlib import Path

        wort = {6: "sechs", 7: "sieben", 8: "acht", 9: "neun"}
        anzahl = len(self._richtlinie()["Statement"])
        text = (Path(__file__).resolve().parent.parent
                / "infra" / "IAM.md").read_text(encoding="utf-8")
        self.assertIn(f"Was die {wort[anzahl]} Anweisungen tun", text)
