"""Dauerhaftes Gedächtnis in S3, serverseitig mit dem Kanzlei-KMS-Schlüssel verschlüsselt.

Der Inhalt liegt gepackt (siehe ``gedaechtnis/packen.py``) und ist über
``ContentEncoding: gzip`` als solcher gekennzeichnet. Der Objektname behält die
Endung ``.json``: Objekte aus früheren Fassungen bleiben so auffindbar und
lesbar, und ``entpacken`` erkennt an den ersten Bytes, was es vor sich hat.
"""

from __future__ import annotations

import hashlib
from typing import Any

from jusperfect.domain.models import Aktengedaechtnis
from jusperfect.gedaechtnis.base import GedaechtnisFehler
from jusperfect.gedaechtnis.packen import entpacken, packen

#: Wie lange auf den Ablageort gewartet wird, bevor aufgegeben wird.
#:
#: Fünf Sekunden statt der sechzig, die boto3 von Haus aus nimmt. Der Grund
#: steht im Kalender: Am 02.10.2026 meldete die Kanzlei, die Aktenanalyse habe
#: nach vier Minuten noch nichts gezeigt. Sie arbeitete auch nicht - sie wartete
#: auf S3, dreimal hintereinander sechzig Sekunden, weil das Kanzleinetz die
#: Adresse nicht erreichte.
#:
#: Ein Ablageort im selben Rechenzentrum antwortet in Millisekunden. Antwortet
#: er nach fünf Sekunden nicht, antwortet er auch nach sechzig nicht - dann ist
#: der Weg versperrt, und das soll man in zehn Sekunden erfahren statt in vier
#: Minuten.
VERBINDUNGSZEIT_SEKUNDEN = 5
LESEZEIT_SEKUNDEN = 30
VERSUCHE = 2


#: Woran ein misslungener Zugriff auf den Ablageort zu erkennen ist.
#:
#: Hier stand nur der Name der Ausnahme: "nicht erreichbar
#: (EndpointConnectionError)". Das ist richtig und hilft niemandem - es sagt
#: nicht, ob der Ablageort fehlt, die Berechtigung fehlt oder der Weg dorthin
#: versperrt ist, und das sind drei verschiedene Handgriffe an drei
#: verschiedenen Stellen.
_GRUENDE: tuple[tuple[str, str], ...] = (
    ("endpointconnection",
     "Der Rechner erreicht den Ablageort nicht. Das ist KEIN Berechtigungsfehler: "
     "Die Adresse von S3 antwortet überhaupt nicht. Meist sperrt die Firewall "
     "oder der Zugangsrechner des Kanzleinetzes sie; das Modell läuft über eine "
     "andere Adresse und ist deshalb nicht betroffen. "
     "GEDAECHTNIS-AWS-PRUEFEN.bat sagt, woran es liegt."),
    ("connecttimeout",
     "Der Ablageort antwortet nicht innerhalb der Wartezeit. Meist sperrt die "
     "Firewall oder der Zugangsrechner des Kanzleinetzes die Adresse von S3."),
    ("nosuchbucket",
     "Diesen Ablageort gibt es nicht. Der Name in der Startdatei und der Name in "
     "der S3-Konsole müssen Zeichen für Zeichen übereinstimmen."),
    ("accessdenied",
     "Das Ablegen ist nicht erlaubt. Gebraucht werden s3:PutObject und "
     "s3:GetObject auf diesen Ablageort (siehe AWS-EINRICHTEN.md)."),
    ("permanentredirect",
     "Der Ablageort liegt in einer anderen Region. jusperfect arbeitet in "
     "Frankfurt; ein Ablageort lässt sich nicht verschieben."),
)


def _nicht_erreichbar(fehler: Exception) -> str:
    """Aus einem misslungenen Zugriff einen Satz machen, der weiterhilft.

    Der Wortlaut von AWS geht nicht hinaus - erkannt wird am Namen der Ausnahme
    und am Fehlercode, und beide tragen selbst keinen Inhalt.
    """
    code = ""
    antwort = getattr(fehler, "response", None)
    if isinstance(antwort, dict):
        code = str(antwort.get("Error", {}).get("Code", ""))
    klein = f"{type(fehler).__name__} {code}".lower()
    for merkmal, erklaerung in _GRUENDE:
        if merkmal in klein:
            return erklaerung
    return f"AWS-Gedächtnis ist nicht erreichbar ({type(fehler).__name__})."


class AwsGedaechtnisSpeicher:
    def __init__(self, bucket: str, region: str, kms_schluessel_id: str, s3: Any | None = None) -> None:
        if not kms_schluessel_id:
            raise GedaechtnisFehler("Das AWS-Gedächtnis benötigt einen KMS-Schlüssel.")
        if s3 is None:
            import boto3
            from botocore.config import Config

            s3 = boto3.client("s3", region_name=region, config=Config(
                connect_timeout=VERBINDUNGSZEIT_SEKUNDEN,
                read_timeout=LESEZEIT_SEKUNDEN,
                retries={"max_attempts": VERSUCHE, "mode": "standard"},
            ))
        self._s3 = s3
        self._bucket = bucket
        self._kms = kms_schluessel_id

    @staticmethod
    def _schluessel(akte_id: str) -> str:
        # Auch verschlüsselte Buckets verraten Objektnamen in Verwaltungsdaten.
        # Deshalb wird keine fachliche Aktenkennung in den Schlüssel geschrieben.
        return f"akten/{hashlib.sha256(akte_id.encode('utf-8')).hexdigest()}/gedaechtnis.json"

    def lesen(self, akte_id: str) -> Aktengedaechtnis | None:
        try:
            antwort = self._s3.get_object(Bucket=self._bucket, Key=self._schluessel(akte_id))
        except Exception as e:
            code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404", "NotFound") or type(e).__name__ == "NoSuchKey":
                return None
            raise GedaechtnisFehler(_nicht_erreichbar(e)) from e
        try:
            gedaechtnis = entpacken(antwort["Body"].read())
        except Exception as e:
            raise GedaechtnisFehler(f"AWS-Gedächtnis ist nicht lesbar ({type(e).__name__}).") from e
        if gedaechtnis.akte_id != akte_id:
            raise GedaechtnisFehler("Das geladene Gedächtnis gehört zu einer anderen Akte.")
        # Die Revision gehoert an DIESES Objekt, nicht in eine Tabelle des
        # Speichers - siehe `Aktengedaechtnis._revision` und Befund F03.
        gedaechtnis._revision = antwort.get("ETag")
        return gedaechtnis

    def ablegen(self, gedaechtnis: Aktengedaechtnis) -> None:
        try:
            schluessel = self._schluessel(gedaechtnis.akte_id)
            # Erwartet wird die Revision, mit der DIESER Stand gelesen wurde.
            # Ohne Revision ist es ein neues Gedaechtnis: dann darf es noch
            # nichts geben.
            bedingung = ({"IfMatch": gedaechtnis._revision}
                         if gedaechtnis._revision else {"IfNoneMatch": "*"})
            antwort = self._s3.put_object(
                Bucket=self._bucket,
                Key=schluessel,
                Body=packen(gedaechtnis),
                ContentType="application/json; charset=utf-8",
                ContentEncoding="gzip",
                ServerSideEncryption="aws:kms",
                SSEKMSKeyId=self._kms,
                **bedingung,
            )
        except Exception as e:
            code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
            if code in ("PreconditionFailed", "412", "ConditionalRequestConflict"):
                raise GedaechtnisFehler(
                    "Das Gedächtnis wurde zwischenzeitlich von einer anderen Stelle "
                    "geändert. Ihr Stand ist nicht gespeichert worden. Bitte die Akte neu "
                    "laden und den Vorgang wiederholen."
                ) from e
            raise GedaechtnisFehler(f"AWS-Gedächtnis konnte nicht gespeichert werden ({type(e).__name__}).") from e
        gedaechtnis._revision = antwort.get("ETag")

    def auflisten(self) -> list[Aktengedaechtnis]:
        ergebnis: list[Aktengedaechtnis] = []
        fortsetzung: str | None = None
        try:
            while True:
                argumente: dict[str, Any] = {"Bucket": self._bucket, "Prefix": "akten/"}
                if fortsetzung:
                    argumente["ContinuationToken"] = fortsetzung
                antwort = self._s3.list_objects_v2(**argumente)
                for objekt in antwort.get("Contents", []):
                    if not objekt["Key"].endswith("/gedaechtnis.json"):
                        continue
                    inhalt = self._s3.get_object(Bucket=self._bucket, Key=objekt["Key"])
                    ergebnis.append(entpacken(inhalt["Body"].read()))
                if not antwort.get("IsTruncated"):
                    return ergebnis
                fortsetzung = antwort.get("NextContinuationToken")
        except Exception as e:
            raise GedaechtnisFehler(_nicht_erreichbar(e)) from e

    def loeschen(self, akte_id: str) -> None:
        try:
            self._s3.delete_object(Bucket=self._bucket, Key=self._schluessel(akte_id))
        except Exception as e:
            raise GedaechtnisFehler(f"AWS-Gedächtnis konnte nicht gelöscht werden ({type(e).__name__}).") from e
