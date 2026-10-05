"""Schreibt AWS die Modellaufrufe mit? – Prüfung beim Start.

Grundsatz 5 des Sicherheitsmodells sagt: „Bedrock-Modellaufrufprotokollierung
bleibt aus." Das war bisher eine Absichtserklärung. Geprüft hat es niemand.

Warum das mehr ist als eine Formalie: Ist die Modellaufrufprotokollierung
eingeschaltet, schreibt AWS **den vollständigen Prompt und die vollständige
Antwort** in eine CloudWatch-Protokollgruppe oder einen S3-Bucket. Der Prompt
ist der Aktentext. Damit läge das Mandantengeheimnis ein zweites Mal neben der
Akte – an einer Stelle, die niemand als Aktenablage ansieht, die anders
gesichert ist und die von der Löschung beim Aktenabschluss nicht erfasst wird.
Eingeschaltet wird sie kontoweit mit zwei Klicks, und man sieht es dem
laufenden Programm nicht an.

Die Richtlinie der Kanzlei verbietet dem Programmbenutzer, daran etwas zu
ändern (`PutModelInvocationLoggingConfiguration` steht unter Deny, siehe
`infra/iam-nur-claude.json`). Lesen darf er es. Genau das tut dieses Modul.

**Fail closed, aber nicht blind.** Drei Ausgänge:

* ``AUS`` – es wird nichts mitgeschrieben. Das Programm läuft.
* ``AN``  – es wird mitgeschrieben. Das Programm startet nicht, gleich mit
  welchen Akten. Abschalten ist eine Sache von Sekunden; weiterlaufen wäre
  eine Sache von Jahren.
* ``UNBEKANNT`` – die Frage ließ sich nicht beantworten (fehlendes Leserecht,
  AWS nicht erreichbar). Hier entscheidet, was auf dem Spiel steht: Mit echten
  Akten ist Ungewissheit ein Nein, mit den erfundenen Testakten ein Hinweis.
  Sonst stünde die Kanzlei bei einer Netzstörung vor einem Programm, das nicht
  mehr startet, obwohl in den Akten nichts als Erfundenes steht.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from jusperfect.config import Einstellungen, KonfigurationsFehler

AUS = "aus"
AN = "an"
UNBEKANNT = "unbekannt"

# Die Schalter, die Inhalte hinaustragen. Text ist der Aktentext; Bild betrifft
# gescannte Seiten. „embedding" und „video" stehen mit dabei, weil beides aus
# demselben Material entsteht und keine Ausnahme verdient.
_INHALTSSCHALTER = {
    "textDataDeliveryEnabled": "Text (der Aktentext selbst)",
    "imageDataDeliveryEnabled": "Bilder (gescannte Seiten)",
    "embeddingDataDeliveryEnabled": "Einbettungen (aus dem Aktentext berechnet)",
    "videoDataDeliveryEnabled": "Video",
}

_ZIELE = {
    "cloudWatchConfig": "CloudWatch-Protokollgruppe",
    "s3Config": "S3-Bucket",
}


@dataclass(frozen=True, slots=True)
class Befund:
    """Was die Prüfung ergeben hat – in ganzen Sätzen, nicht als Code."""

    zustand: str
    satz: str
    einzelheiten: tuple[str, ...] = field(default_factory=tuple)

    @property
    def unbedenklich(self) -> bool:
        return self.zustand == AUS


def _auswerten(konfiguration: dict | None) -> Befund:
    """Aus der Antwort von AWS einen Befund machen.

    Eine leere oder fehlende Konfiguration heißt: nichts eingerichtet, nichts
    wird mitgeschrieben. Ist etwas eingerichtet, zählt nicht das Vorhandensein,
    sondern ob Inhalte ausgeliefert werden – eine Konfiguration, bei der jeder
    Inhaltsschalter aus ist, trägt keinen Aktentext hinaus.
    """
    if not konfiguration:
        return Befund(AUS, "AWS schreibt die Modellaufrufe nicht mit.")

    inhalte = [text for schluessel, text in _INHALTSSCHALTER.items()
               if konfiguration.get(schluessel)]
    ziele = [text for schluessel, text in _ZIELE.items() if konfiguration.get(schluessel)]

    if not inhalte:
        return Befund(
            AUS,
            "AWS schreibt keine Inhalte mit; eine Protokollierung ist zwar "
            "eingerichtet, liefert aber weder Text noch Bilder aus.",
            tuple(f"eingerichtetes Ziel: {ziel}" for ziel in ziele),
        )

    return Befund(
        AN,
        "AWS schreibt die Modellaufrufe mit – und damit den Aktentext.",
        tuple([f"mitgeschrieben wird: {teil}" for teil in inhalte]
              + [f"Ziel: {ziel}" for ziel in ziele]),
    )


def pruefen(region: str, *, client=None) -> Befund:
    """Einmal bei AWS nachfragen. Kostet nichts und schickt nichts hin."""
    if client is None:
        try:
            import boto3
        except ImportError:
            return Befund(UNBEKANNT, "Der AWS-Baustein boto3 fehlt.")
        client = boto3.Session(region_name=region).client("bedrock")
    try:
        antwort = client.get_model_invocation_logging_configuration()
    except Exception as fehler:  # ClientError, Netz, Proxy, abgelaufener Zugang
        code = ""
        antwort_feld = getattr(fehler, "response", None)
        if isinstance(antwort_feld, dict):
            code = str(antwort_feld.get("Error", {}).get("Code", ""))
        if code == "ResourceNotFoundException":
            # AWS antwortet so, wenn im Konto nie eine Protokollierung
            # eingerichtet wurde. Das ist die Antwort „aus", nicht ein Fehler.
            return Befund(AUS, "Im Konto ist keine Modellaufrufprotokollierung eingerichtet.")
        if code in ("AccessDeniedException", "AccessDenied"):
            return Befund(
                UNBEKANNT,
                "Ob AWS die Modellaufrufe mitschreibt, lässt sich nicht feststellen: "
                "Das Leserecht dafür fehlt.",
                ("In der Richtlinie fehlt bedrock:GetModelInvocationLoggingConfiguration "
                 "(siehe infra/iam-nur-claude.json, Abschnitt „ModelleAnsehen“).",),
            )
        return Befund(
            UNBEKANNT,
            "Ob AWS die Modellaufrufe mitschreibt, lässt sich nicht feststellen: "
            f"Die Abfrage ist fehlgeschlagen ({code or type(fehler).__name__}).",
        )
    return _auswerten(antwort.get("loggingConfig"))


def beim_start_pruefen(e: Einstellungen, *, client=None) -> Befund | None:
    """Die Prüfung, wie sie beim Start greift. ``None`` heißt: nicht zuständig.

    Ohne Bedrock gibt es keine Modellaufrufe, die mitgeschrieben werden
    könnten; der Demo-Anbieter rechnet auf diesem Rechner.
    """
    if e.anbieter != "bedrock":
        return None
    befund = pruefen(e.aws_region, client=client)

    if befund.zustand == AN:
        raise KonfigurationsFehler(
            _mit_einzelheiten(
                "AWS schreibt die Modellaufrufe mit. Damit ginge der Aktentext in eine "
                "Protokollablage neben der Akte – jusperfect startet deshalb nicht.\n"
                "Abhilfe: AWS-Konsole → Bedrock → Einstellungen → Modellaufrufprotokollierung "
                "abschalten. Danach erneut starten.",
                befund))

    if befund.zustand == UNBEKANNT and e.jurnodes_adapter != "fixture":
        raise KonfigurationsFehler(
            _mit_einzelheiten(
                f"{befund.satz}\n"
                "Mit echten Akten ist das ein Nein: Es ist nicht auszuschließen, dass der "
                "Aktentext mitgeschrieben wird. jusperfect startet deshalb nicht.\n"
                "Mit den erfundenen Testakten (JUSPERFECT_JURNODES_ADAPTER=fixture) läuft "
                "es weiter und gibt nur einen Hinweis aus.",
                befund))

    return befund


def _mit_einzelheiten(satz: str, befund: Befund) -> str:
    if not befund.einzelheiten:
        return satz
    return satz + "\n" + "\n".join(f"  – {teil}" for teil in befund.einzelheiten)
