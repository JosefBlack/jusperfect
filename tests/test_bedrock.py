import unittest

from botocore.exceptions import ClientError

from jusperfect.providers.base import GuardrailEingriff, ProviderFehler
from jusperfect.providers.bedrock import BedrockProvider


class MitschreibenderClient:
    def __init__(self, antworten):
        self.antworten = list(antworten)
        self.anfragen = []

    def converse(self, **anfrage):
        self.anfragen.append(anfrage)
        antwort = self.antworten.pop(0)
        if isinstance(antwort, Exception):
            raise antwort
        return antwort

    # Der stroemende Weg ist ein eigener Code-Pfad mit eigener
    # Fehlerbehandlung. Was fuer den einen gilt, muss auch fuer den anderen
    # gelten - sonst faellt der Unterschied erst im Betrieb auf.
    converse_stream = converse


def _antwort(text="Antwort [Q: D1-S1-P1]", stop="end_turn"):
    return {"output": {"message": {"content": [{"text": text}]}}, "stopReason": stop,
            "usage": {"inputTokens": 100, "outputTokens": 20, "cacheReadInputTokens": 50, "cacheWriteInputTokens": 0}}


class Bedrock(unittest.TestCase):
    def test_anfrage_mit_guardrail_und_cache(self):
        c = MitschreibenderClient([_antwort()])
        p = BedrockProvider("modell", guardrail_id="g1", guardrail_version="2", client=c)
        a = p.fragen("SYS", "MATERIAL", "AUFGABE")
        anfrage = c.anfragen[0]
        inhalt = anfrage["messages"][0]["content"]
        self.assertEqual(inhalt[0], {"text": "MATERIAL"})
        self.assertEqual(inhalt[1], {"cachePoint": {"type": "default"}})
        self.assertEqual(inhalt[2], {"guardContent": {"text": {"text": "AUFGABE"}}})
        self.assertEqual(anfrage["guardrailConfig"]["guardrailIdentifier"], "g1")
        self.assertEqual(anfrage["system"], [{"text": "SYS"}])
        self.assertEqual(a.nutzung.cache_lese_tokens, 50)
        self.assertEqual(a.text, "Antwort [Q: D1-S1-P1]")

    def test_ohne_guardrail_kein_guardcontent(self):
        c = MitschreibenderClient([_antwort()])
        BedrockProvider("modell", client=c).fragen("S", "M", "A")
        inhalt = c.anfragen[0]["messages"][0]["content"]
        self.assertEqual(inhalt[-1], {"text": "A"})
        self.assertNotIn("guardrailConfig", c.anfragen[0])

    def test_guardrail_eingriff(self):
        c = MitschreibenderClient([_antwort("blockiert", "guardrail_intervened")])
        with self.assertRaises(GuardrailEingriff):
            BedrockProvider("modell", guardrail_id="g", client=c).fragen("S", "M", "A")

    def test_cache_nicht_unterstuetzt_wiederholt_ohne(self):
        fehler = ClientError({"Error": {"Code": "ValidationException", "Message": "cachePoint is not supported"}}, "Converse")
        c = MitschreibenderClient([fehler, _antwort(), _antwort()])
        p = BedrockProvider("modell", client=c)
        p.fragen("S", "M", "A")
        p.fragen("S", "M", "A")
        self.assertEqual(len(c.anfragen), 3)
        self.assertNotIn("cachePoint", str(c.anfragen[1]))
        self.assertNotIn("cachePoint", str(c.anfragen[2]))

    def test_fehler_ohne_inhalt(self):
        """In der Ablehnung von AWS steht mitunter ein Stück der Anfrage.

        Dieser Test hat einen Entwurf gefangen, der den Wortlaut von AWS
        durchreichen wollte, um die Meldung hilfreicher zu machen. Hilfreicher
        wäre sie geworden – und hätte Aktentext getragen.
        """
        fehler = ClientError({"Error": {"Code": "AccessDeniedException", "Message": "Mandant Testmann"}}, "Converse")
        c = MitschreibenderClient([fehler])
        with self.assertRaises(ProviderFehler) as cm:
            BedrockProvider("modell", client=c).fragen("S", "M", "A")
        self.assertIn("AccessDeniedException", str(cm.exception))
        self.assertNotIn("Testmann", str(cm.exception))

    def test_auch_im_strom_bleibt_der_wortlaut_drinnen(self):
        fehler = ClientError({"Error": {"Code": "AccessDeniedException", "Message": "Mandant Testmann"}}, "ConverseStream")
        c = MitschreibenderClient([fehler])
        with self.assertRaises(ProviderFehler) as cm:
            list(BedrockProvider("modell", client=c).fragen_stream("S", "M", "A"))
        self.assertNotIn("Testmann", str(cm.exception))

    def test_ein_nicht_zugeteiltes_modell_wird_als_solches_benannt(self):
        """Derselbe Code steht für drei verschiedene Handgriffe.

        Aus der Kanzlei: „AccessDeniedException – anthropic.claude-opus-5 is not
        available for this account." Vorher stand im Programm nur der Code, und
        man sucht dann an der eigenen Einrichtung, wo nichts zu finden ist.
        """
        fehler = ClientError({"Error": {"Code": "AccessDeniedException",
                                        "Message": "anthropic.claude-opus-5 is not available for this account."}},
                             "Converse")
        c = MitschreibenderClient([fehler])
        with self.assertRaises(ProviderFehler) as cm:
            BedrockProvider("eu.anthropic.claude-opus-5", client=c).fragen("S", "M", "A")
        text = str(cm.exception)
        self.assertIn("nicht zugeteilt", text)
        self.assertIn("MODELLE-ANZEIGEN.bat", text)
        self.assertIn("eu.anthropic.claude-opus-5", text)

    def test_eine_fehlende_berechtigung_wird_unterschieden(self):
        fehler = ClientError({"Error": {"Code": "AccessDeniedException",
                                        "Message": "User arn:… is not authorized to perform: bedrock:InvokeModel"}},
                             "Converse")
        c = MitschreibenderClient([fehler])
        with self.assertRaises(ProviderFehler) as cm:
            BedrockProvider("modell", client=c).fragen("S", "M", "A")
        self.assertIn("Zugriffsrichtlinie", str(cm.exception))
        self.assertNotIn("arn:", str(cm.exception))

    def test_eine_abgekuerzte_kennung_wird_als_solche_benannt(self):
        """Aus der Kanzlei: „Das Einlesen ist fehlgeschlagen – Bedrock hat die
        Anfrage abgelehnt."

        Ursache war eine abgekuerzte Modellkennung in der Startdatei. Eine
        echte Bedrock-Kennung traegt Datum und Fassung; „claude-opus-4-6"
        allein gibt es nicht. AWS antwortet darauf mit ValidationException,
        und das Programm sagte nur genau das – ein Satz, mit dem in einer
        Kanzlei niemand etwas anfangen kann. Vor allem sagte er nicht, worin
        der Unterschied zu einem nicht freigeschalteten Modell liegt: Dort
        sucht man dann bei den Freischaltungen, wo nichts zu finden ist.
        """
        for wortlaut in ("The provided model identifier is invalid.",
                         "Invalid model identifier"):
            fehler = ClientError({"Error": {"Code": "ValidationException",
                                            "Message": wortlaut}}, "Converse")
            c = MitschreibenderClient([fehler])
            with self.assertRaises(ProviderFehler) as cm:
                BedrockProvider("eu.anthropic.claude-opus-4-6", client=c).fragen("S", "M", "A")
            text = str(cm.exception)
            self.assertIn("kennt AWS nicht", text, wortlaut)
            self.assertIn("eu.anthropic.claude-opus-4-6", text, wortlaut)
            self.assertIn("MODELLE-ANZEIGEN.bat", text, wortlaut)
            self.assertNotIn("nicht zugeteilt", text,
                             "Das ist der andere Fall und fuehrt an die falsche Stelle.")

    def test_die_cache_ausnahme_bleibt_von_der_neuen_regel_unberuehrt(self):
        """Auch das ist eine ValidationException – und sie darf nicht melden,
        sondern muss den Aufruf ohne Zwischenspeicher wiederholen."""
        fehler = ClientError({"Error": {"Code": "ValidationException",
                                        "Message": "cachePoint is not supported"}}, "Converse")
        c = MitschreibenderClient([fehler, _antwort()])
        a = BedrockProvider("modell", client=c).fragen("S", "M", "A")
        self.assertEqual("Antwort [Q: D1-S1-P1]", a.text)

    def test_anderes_modell_je_aufruf(self):
        c = MitschreibenderClient([_antwort()])
        a = BedrockProvider("gross", client=c).fragen("S", "M", "A", modell_id="klein")
        self.assertEqual(c.anfragen[0]["modelId"], "klein")
        self.assertEqual(a.modell, "klein")

    def test_ein_abgewiesener_zugang_wird_nicht_dem_modell_angelastet(self):
        """Aus der Kanzlei am 01.10.2026: „Bedrock hat die Anfrage abgelehnt
        (UnrecognizedClientException)."

        Der Zugriffsschluessel stand in AWS auf „inaktiv" - mit dem Modell
        hatte das nichts zu tun. Die Meldung nannte aber nur den Code, und
        darunter standen die fuenf Modellkennungen. Gesucht wurde daraufhin
        beim Modell, bei den Freischaltungen und beim Tagesvolumen; gefunden
        wurde dort nichts, denn dort war nichts.

        Der Selbsttest erklaert denselben Code seit Monaten im Klartext. Die
        Pruefung haelt fest, dass der Anbieter dieselbe Auskunft gibt - und
        dass er dabei den Wortlaut von AWS drinnen laesst.
        """
        for code in ("UnrecognizedClientException", "InvalidClientTokenId"):
            fehler = ClientError({"Error": {"Code": code,
                                            "Message": "The security token included in the "
                                                       "request is invalid. Mandant Testmann"}},
                                 "Converse")
            c = MitschreibenderClient([fehler])
            with self.assertRaises(ProviderFehler) as cm:
                BedrockProvider("eu.anthropic.claude-opus-4-6-v1", client=c).fragen("S", "M", "A")
            text = str(cm.exception)
            self.assertIn("Access Key ID", text, code)
            self.assertIn("Sicherheitsanmeldeinformationen", text, code)
            self.assertNotIn("Testmann", text, code)
            self.assertNotIn("nicht zugeteilt", text,
                             "Das fuehrt zu den Freischaltungen - der falschen Stelle.")

    def test_eine_unpassende_unterschrift_bleibt_davon_unterschieden(self):
        """Derselbe Handgriff waere der falsche: Hier kennt AWS die Kennung,
        nur die Unterschrift passt nicht - geheimer Schluessel oder die Uhr
        des Rechners."""
        fehler = ClientError({"Error": {"Code": "SignatureDoesNotMatch",
                                        "Message": "The request signature we calculated does not match"}},
                             "Converse")
        c = MitschreibenderClient([fehler])
        with self.assertRaises(ProviderFehler) as cm:
            BedrockProvider("modell", client=c).fragen("S", "M", "A")
        text = str(cm.exception)
        self.assertIn("Unterschrift", text)
        self.assertNotIn("Access Key ID kennt AWS nicht", text)

    def test_ein_modellfehler_wird_weiterhin_als_solcher_gemeldet(self):
        """Die Gegenprobe. Waere jeder unbekannte Code ein Zugangsfehler,
        schickte eine Mengengrenze den Anwender neuerdings in die
        Schluesselverwaltung - also wieder an die falsche Stelle, nur in die
        andere Richtung."""
        fehler = ClientError({"Error": {"Code": "ThrottlingException",
                                        "Message": "Too many tokens per day"}}, "Converse")
        c = MitschreibenderClient([fehler])
        with self.assertRaises(ProviderFehler) as cm:
            BedrockProvider("modell", client=c).fragen("S", "M", "A")
        text = str(cm.exception)
        self.assertIn("ThrottlingException", text)
        self.assertNotIn("Access Key ID", text)
