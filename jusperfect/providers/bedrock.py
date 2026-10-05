"""AWS Bedrock über die Converse API – mit Guardrail und Prompt-Cache.

Das ist die einzige Stelle, an der Aktentext das eigene AWS-Konto in
Richtung Modell verlässt. Sie bekommt genau drei Dinge: Systemanweisung,
Material (ausgewählte Passagen) und Aufgabe (Frage oder Auftrag). Dateien,
Dateinamen, Nutzerkennungen oder die ganze Akte erreichen sie nicht.

Zwei Bausteine der Converse API werden gezielt genutzt:

* ``cachePoint`` hinter dem Material: Wer fünf Fragen zur selben Akte stellt,
  bezahlt das Material einmal voll und danach zum Cache-Preis.
* ``guardContent`` um die Aufgabe: Die Guardrail prüft die Eingabe des
  Nutzers und die Antwort des Modells – nicht das 200-seitige Dokument, das
  sonst je Aufruf so viel kostet wie das Modell selbst.

Zugangsdaten kommen aus der Lambda-Rolle bzw. dem AWS-Profil, nie aus dem
Code. Region: eu-central-1, einstellbar. Welche Modellkennung das Konto
tatsächlich freigeschaltet hat (direkte Kennung oder EU-Inferenzprofil),
gehört zum AWS-Zugangstest in Phase 0.
"""

from __future__ import annotations

from typing import Any

from jusperfect.aws_handlung import mit_handlung
from jusperfect.providers.base import GuardrailEingriff, Nutzung, ProviderAntwort, ProviderFehler


# Warum eine eigene Zeitgrenze noetig ist
# ---------------------------------------
# botocore wartet voreingestellt 60 Sekunden auf die Antwort. Fuer den
# Frage-Weg genuegt das, denn der stroemt: es kommt laufend etwas an, die Uhr
# faengt immer wieder von vorn an. Die Aktenanalyse holt ihre Antwort dagegen
# in einem Stueck - bis zu 8000 Token, aus denen das Modell mehrere Minuten
# lang JSON baut, waehrend die Leitung stumm bleibt. Nach einer Minute bricht
# botocore ab und versucht es erneut; der Browser haengt derweil und meldet
# schliesslich nur "Failed to fetch". Der Fehler traf also ausgerechnet die
# teuerste Anfrage, und die Meldung sagte nichts ueber die Ursache.
#
# Fuenf Minuten reichen mit Abstand: 8000 Token entstehen in etwa drei
# Minuten. Hoeher zu gehen waere nicht vorsichtiger, sondern schlechter -
# botocore wiederholt auch nach einem Zeitueberlauf, und drei Versuche zu je
# fuenfzehn Minuten liessen die Kanzlei eine Dreiviertelstunde vor einem
# haengenden Fenster sitzen. So ist der schlimmste Fall auf eine Viertelstunde
# begrenzt. Die drei Versuche bleiben, weil sie den haeufigen Fall abfangen,
# fuer den sie da sind: ThrottlingException, wenn AWS gerade ausgelastet ist.
LESEZEIT_SEKUNDEN = 300
VERBINDUNGSZEIT_SEKUNDEN = 20


def _client_bauen(region: str) -> Any:
    import boto3  # erst hier, damit Tests und Demo ohne AWS-SDK-Aufbau auskommen
    from botocore.config import Config

    return boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(
            read_timeout=LESEZEIT_SEKUNDEN,
            connect_timeout=VERBINDUNGSZEIT_SEKUNDEN,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


# Woran eine Ablehnung zu erkennen ist - und was sie fuer die Kanzlei heisst.
# Die Merkmale sind feste Wendungen von AWS und tragen selbst keinen Inhalt;
# der erklaerende Satz ist unserer. Was AWS sonst schreibt, bleibt drinnen:
# In der Antwort steht mitunter ein Stueck der Anfrage.
_KENNUNG_UNBEKANNT = (
    "Die Modellkennung „{modell}“ kennt AWS nicht. Das ist etwas anderes als ein "
    "nicht freigeschaltetes Modell: Die Kennung selbst gibt es so nicht. Eine "
    "vollstaendige Bedrock-Kennung traegt Datum und Fassung. Welche Kennungen dieses "
    "Konto wirklich aufrufen darf, zeigt MODELLE-ANZEIGEN.bat – eine davon Zeichen "
    "fuer Zeichen in START-AWS.bat eintragen."
)

_ABLEHNUNGEN: tuple[tuple[str, str], ...] = (
    ("not available for this account",
     "Das Modell \u201e{modell}\u201c ist diesem AWS-Konto nicht zugeteilt. An der "
     "Einrichtung liegt es nicht: Zugangsdaten, Richtlinie und Region stimmen. "
     "Welche Modelle das Konto wirklich aufrufen darf, zeigt MODELLE-ANZEIGEN.bat; "
     "eines davon in START-AWS.bat unter JUSPERFECT_MODELL_ID eintragen."),
    ("is not authorized to perform",
     "Die Zugriffsrichtlinie erlaubt diesen Aufruf nicht. Sie haengt entweder nicht "
     "am Benutzer, oder ihr fehlt eine Berechtigung (IAM \u2192 Richtlinien \u2192 "
     "jusperfect-nur-claude \u2192 Bearbeiten; siehe infra/IAM.md)."),
    ("with an explicit deny",
     "Die Zugriffsrichtlinie verbietet diesen Aufruf ausdruecklich \u2013 meist, weil "
     "das Modell oder die Region nicht abgedeckt ist (siehe infra/IAM.md)."),
    ("on-demand throughput isn",
     "Dieses Modell verlangt in dieser Region das europaeische Inferenzprofil. Die "
     "Kennung muss mit \u201eeu.\u201c beginnen; das setzt das Programm selbst, wenn "
     "sie mit \u201eanthropic.\u201c eingetragen ist."),
    # Nicht „nicht zugeteilt“, sondern „gibt es so nicht“: AWS kennt die
    # Kennung ueberhaupt nicht. Das trifft vor allem eine abgekuerzte Schreibweise
    # - eine echte Bedrock-Kennung traegt Datum und Fassung, etwa
    # „anthropic.claude-sonnet-4-5-20250929-v1:0“. Wer hier den Unterschied
    # nicht gesagt bekommt, sucht bei den Freischaltungen, wo nichts zu finden ist.
    # AWS schreibt den Fall mal "The provided model identifier is invalid.",
    # mal "Invalid model identifier". Gemeinsam ist beiden nur diese Wendung -
    # und sie traegt selbst keinen Inhalt aus der Anfrage.
    ("model identifier", _KENNUNG_UNBEKANNT),
)


# Ein abgewiesener Zugang ist keine Ablehnung des Modells. Diese Codes stehen
# fuer einen Schluessel, den AWS nicht kennt, eine Unterschrift, die nicht
# passt, oder einen abgelaufenen Zugang - und keiner davon hat mit dem Modell
# zu tun. Was sie heissen, steht in ``selbsttest.zugangsfehler``; hier wird es
# geholt und nicht ein zweites Mal aufgeschrieben.
#
# Am 01.10.2026 brach der Pruefbogen mit "Bedrock hat die Anfrage abgelehnt
# (UnrecognizedClientException)" ab. Der Zugriffsschluessel stand in AWS auf
# "inaktiv". Das Startbild erklaert genau diesen Fall seit Monaten im Klartext
# - hier stand nur der Code, und die Suche ging zum Modell, zu den
# Freischaltungen und zum Tagesvolumen, also dreimal dorthin, wo nichts zu
# finden war.
#
# Die Lehre ist nicht neu, nur neu bezahlt: Dasselbe Wissen an zwei Stellen
# ist eine Stelle zu wenig, sobald es nur an einer gepflegt wird.
_ZUGANGSCODES = frozenset((
    "UnrecognizedClientException",
    "InvalidClientTokenId",
    "SignatureDoesNotMatch",
    "InvalidSignatureException",
    "ExpiredToken",
))


def _abgelehnt(fehler: Exception, modell: str) -> str:
    """Aus der Ablehnung von AWS einen Satz machen, der weiterhilft.

    Hier stand nur der Fehlercode: „Bedrock hat die Anfrage abgelehnt
    (AccessDeniedException)." Derselbe Code steht fuer ein nicht zugeteiltes
    Modell, eine fehlende Berechtigung und ein ausdrueckliches Verbot in der
    Richtlinie - drei verschiedene Handgriffe. AWS schreibt den Unterschied in
    die Antwort hinein; genau dieser Satz ging verloren.

    **Der Wortlaut von AWS wird dabei nicht durchgereicht.** Der erste Entwurf
    tat das, und ein eigener Test hat es gefangen: In der Ablehnung steht
    mitunter ein Stueck der Anfrage, und das ist Aktentext. Was hier
    hinausgeht, sind eigene Saetze - ausgeloest von Merkmalen, die selbst
    keinen Inhalt tragen.
    """
    antwort = getattr(fehler, "response", None)
    code, satz = "ClientError", ""
    if isinstance(antwort, dict):
        code = str(antwort.get("Error", {}).get("Code", "")) or code
        satz = str(antwort.get("Error", {}).get("Message", "")).strip()

    # Ohne Ruecksicht auf Gross- und Kleinschreibung: AWS beginnt denselben
    # Satz mal mit grossem, mal mit kleinem Anfangsbuchstaben, und eine
    # Meldung, die daran scheitert, faellt auf den nichtssagenden Fehlercode
    # zurueck. Die Merkmale unten stehen deshalb durchweg klein.
    klein = satz.lower()
    for merkmal, erklaerung in _ABLEHNUNGEN:
        if merkmal in klein:
            # Der Name der vermissten Handlung ist die einzige Angabe aus der
            # Meldung von AWS, die hinausgeht - und die einzige, die den
            # Unterschied zwischen "irgendeine Berechtigung fehlt" und einem
            # Handgriff ausmacht. Warum sie gefahrlos ist, steht in
            # jusperfect/aws_handlung.py.
            return mit_handlung(erklaerung.format(modell=modell), fehler)

    # Erst hier geholt: Der Selbsttest gehoert zu den Diensten, und ein
    # Anbieter soll beim Laden nichts davon brauchen.
    if code in _ZUGANGSCODES:
        from jusperfect.services.selbsttest import zugangsfehler
        was, abhilfe = zugangsfehler(fehler)
        return f"{was} {abhilfe}"

    return f"Bedrock hat die Anfrage abgelehnt ({code})."


class BedrockProvider:
    def __init__(
        self,
        modell_id: str,
        region: str = "eu-central-1",
        guardrail_id: str | None = None,
        guardrail_version: str = "DRAFT",
        prompt_cache: bool = True,
        client: Any | None = None,
    ) -> None:
        self.modell_id = modell_id
        self.region = region
        self.guardrail_id = guardrail_id
        self.guardrail_version = guardrail_version
        self._cache_gewuenscht = prompt_cache
        self._cache_moeglich: dict[str, bool] = {}
        if client is None:
            client = _client_bauen(region)
        self._client = client

    def _anfrage(self, system: str, material: str, aufgabe: str, max_tokens: int,
                 modell: str, mit_cache: bool) -> dict[str, Any]:
        inhalt: list[dict[str, Any]] = [{"text": material}]
        if mit_cache:
            inhalt.append({"cachePoint": {"type": "default"}})
        if self.guardrail_id:
            inhalt.append({"guardContent": {"text": {"text": aufgabe}}})
        else:
            inhalt.append({"text": aufgabe})
        anfrage: dict[str, Any] = {
            "modelId": modell,
            "system": [{"text": system}],
            "messages": [{"role": "user", "content": inhalt}],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.2},
        }
        if self.guardrail_id:
            anfrage["guardrailConfig"] = {
                "guardrailIdentifier": self.guardrail_id,
                "guardrailVersion": self.guardrail_version,
                "trace": "disabled",
            }
        return anfrage

    def fragen(self, system: str, material: str, aufgabe: str, *, max_tokens: int = 8000,
               modell_id: str | None = None) -> ProviderAntwort:
        modell = modell_id or self.modell_id
        try:
            from botocore.exceptions import BotoCoreError, ClientError
        except ImportError:  # pragma: no cover – nur ohne boto3
            BotoCoreError = ClientError = Exception  # type: ignore[misc,assignment]

        mit_cache = self._cache_gewuenscht and self._cache_moeglich.get(modell, True)
        try:
            try:
                antwort = self._client.converse(**self._anfrage(system, material, aufgabe, max_tokens, modell, mit_cache))
            except ClientError as e:  # type: ignore[misc]
                fehler = getattr(e, "response", {}).get("Error", {})
                # Nicht jedes Modell kennt Cache-Punkte: einmal ohne wiederholen und merken.
                if mit_cache and fehler.get("Code") == "ValidationException" and "cache" in str(fehler.get("Message", "")).lower():
                    self._cache_moeglich[modell] = False
                    antwort = self._client.converse(**self._anfrage(system, material, aufgabe, max_tokens, modell, False))
                else:
                    raise
        except ClientError as e:  # type: ignore[misc]
            raise ProviderFehler(_abgelehnt(e, modell)) from e
        except BotoCoreError as e:  # type: ignore[misc]
            raise ProviderFehler(f"Bedrock nicht erreichbar ({type(e).__name__}).") from e

        stop = str(antwort.get("stopReason", "end_turn"))
        roh = antwort.get("usage", {}) or {}
        nutzung = Nutzung(
            eingabe_tokens=int(roh.get("inputTokens", 0)),
            ausgabe_tokens=int(roh.get("outputTokens", 0)),
            cache_lese_tokens=int(roh.get("cacheReadInputTokens", 0)),
            cache_schreib_tokens=int(roh.get("cacheWriteInputTokens", 0)),
        )
        if stop == "guardrail_intervened":
            raise GuardrailEingriff("Die Guardrail hat die Anfrage oder Antwort blockiert.")
        inhalte = (antwort.get("output", {}).get("message", {}) or {}).get("content", []) or []
        text = "".join(block.get("text", "") for block in inhalte if isinstance(block, dict))
        if not text.strip():
            raise ProviderFehler("Bedrock hat keinen Text geliefert.")
        if stop == "max_tokens":
            text += "\n\n[Hinweis: Die Antwort wurde wegen der Längenbegrenzung abgeschnitten.]"
        return ProviderAntwort(text=text, nutzung=nutzung, modell=modell, stop_grund=stop)

    def fragen_stream(self, system: str, material: str, aufgabe: str, *, max_tokens: int = 8000,
                      modell_id: str | None = None):
        modell = modell_id or self.modell_id
        try:
            from botocore.exceptions import BotoCoreError, ClientError
        except ImportError:  # pragma: no cover – nur ohne boto3
            BotoCoreError = ClientError = Exception  # type: ignore[misc,assignment]

        mit_cache = self._cache_gewuenscht and self._cache_moeglich.get(modell, True)
        try:
            try:
                antwort = self._client.converse_stream(**self._anfrage(system, material, aufgabe, max_tokens, modell, mit_cache))
            except ClientError as e:  # type: ignore[misc]
                fehler = getattr(e, "response", {}).get("Error", {})
                if mit_cache and fehler.get("Code") == "ValidationException" and "cache" in str(fehler.get("Message", "")).lower():
                    self._cache_moeglich[modell] = False
                    antwort = self._client.converse_stream(**self._anfrage(system, material, aufgabe, max_tokens, modell, False))
                else:
                    raise
        except ClientError as e:  # type: ignore[misc]
            raise ProviderFehler(_abgelehnt(e, modell)) from e
        except BotoCoreError as e:  # type: ignore[misc]
            raise ProviderFehler(f"Bedrock nicht erreichbar ({type(e).__name__}).") from e

        teile: list[str] = []
        stop = "end_turn"
        nutzung = Nutzung()
        for stueck in antwort.get("stream", []):
            if "contentBlockDelta" in stueck:
                delta = (stueck["contentBlockDelta"].get("delta", {}) or {}).get("text", "")
                if delta:
                    teile.append(delta)
                    yield delta
            elif "messageStop" in stueck:
                stop = str(stueck["messageStop"].get("stopReason", "end_turn"))
            elif "metadata" in stueck:
                roh = stueck["metadata"].get("usage", {}) or {}
                nutzung = Nutzung(
                    eingabe_tokens=int(roh.get("inputTokens", 0)),
                    ausgabe_tokens=int(roh.get("outputTokens", 0)),
                    cache_lese_tokens=int(roh.get("cacheReadInputTokens", 0)),
                    cache_schreib_tokens=int(roh.get("cacheWriteInputTokens", 0)),
                )
        if stop == "guardrail_intervened":
            raise GuardrailEingriff("Die Guardrail hat die Anfrage oder Antwort blockiert.")
        text = "".join(teile)
        if not text.strip():
            raise ProviderFehler("Bedrock hat keinen Text geliefert.")
        if stop == "max_tokens":
            text += "\n\n[Hinweis: Die Antwort wurde wegen der Längenbegrenzung abgeschnitten.]"
        yield ProviderAntwort(text=text, nutzung=nutzung, modell=modell, stop_grund=stop)
