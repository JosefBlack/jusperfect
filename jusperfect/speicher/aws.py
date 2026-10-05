"""Sitzungsspeicher in AWS: DynamoDB für Zustand, S3 für Texte.

Eine DynamoDB-Tabelle mit ``pk``/``sk`` und TTL-Attribut ``ablauf``:

    SITZUNG#<id>   META            Sitzung als JSON, Ablauf = Sitzungs-TTL
    ENTWURF#<id>   META            Entwurf als JSON, Ablauf = Entwurfs-TTL
    NUTZUNG#JJJJ-MM SUMME          Monatssumme in Cent (atomar erhöht)
    NUTZUNG#JJJJ-MM E#<zeit>#<id>  Einzeleintrag ohne Inhalte, Ablauf 400 Tage

Texte liegen in S3 unter ``sitzungen/<sitzung>/<dokument>.txt`` mit SSE-KMS.
Eine Lebenszyklusregel des Buckets löscht Reste nach einem Tag; das Schließen
der Sitzung löscht sofort. Bucket-Versionierung bleibt aus, damit Gelöschtes
gelöscht ist.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from jusperfect.domain.models import Entwurf, Nutzungseintrag, Sitzung
from jusperfect.speicher.base import SpeicherFehler

_NUTZUNG_TTL = 400 * 24 * 3600


class AwsSpeicher:
    def __init__(
        self,
        tabelle: str,
        bucket: str,
        region: str,
        kms_schluessel_id: str | None = None,
        sitzung_ttl: int = 900,
        entwurf_ttl: int = 7 * 24 * 3600,
        dynamodb: Any | None = None,
        s3: Any | None = None,
    ) -> None:
        if dynamodb is None or s3 is None:
            import boto3

            dynamodb = dynamodb or boto3.resource("dynamodb", region_name=region)
            s3 = s3 or boto3.client("s3", region_name=region)
        self._tabelle = dynamodb.Table(tabelle)
        self._s3 = s3
        self._bucket = bucket
        self._kms = kms_schluessel_id
        self._sitzung_ttl = sitzung_ttl
        self._entwurf_ttl = entwurf_ttl

    # ── Hilfen ─────────────────────────────────────────────────────────────

    @staticmethod
    def _ablauf(sekunden: int) -> int:
        return int(time.time()) + sekunden

    def _lesen(self, pk: str, sk: str) -> dict[str, Any] | None:
        try:
            antwort = self._tabelle.get_item(Key={"pk": pk, "sk": sk})
        except Exception as e:  # botocore-Fehler ohne Inhalte weiterreichen
            raise SpeicherFehler(f"DynamoDB nicht erreichbar ({type(e).__name__}).") from e
        eintrag = antwort.get("Item")
        if not eintrag:
            return None
        # DynamoDB-TTL löscht verzögert; abgelaufene Einträge zählen nicht.
        if int(eintrag.get("ablauf", 0)) <= int(time.time()):
            return None
        return eintrag

    def _schreiben(self, eintrag: dict[str, Any]) -> None:
        try:
            self._tabelle.put_item(Item=eintrag)
        except Exception as e:
            raise SpeicherFehler(f"DynamoDB nicht erreichbar ({type(e).__name__}).") from e

    def _s3_argumente(self) -> dict[str, str]:
        if self._kms:
            return {"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": self._kms}
        return {"ServerSideEncryption": "AES256"}

    @staticmethod
    def _schluessel(sitzung_id: str, dokument_id: str) -> str:
        return f"sitzungen/{sitzung_id}/{dokument_id}.txt"

    # ── Sitzung ────────────────────────────────────────────────────────────

    def sitzung_ablegen(self, sitzung: Sitzung) -> None:
        self._schreiben({
            "pk": f"SITZUNG#{sitzung.id}", "sk": "META",
            "daten": sitzung.model_dump_json(), "nutzer_id": sitzung.nutzer_id,
            "akte_id": sitzung.akte_id,
            "ablauf": self._ablauf(self._sitzung_ttl),
        })

    def sitzung_lesen(self, sitzung_id: str) -> Sitzung | None:
        eintrag = self._lesen(f"SITZUNG#{sitzung_id}", "META")
        return Sitzung.model_validate_json(eintrag["daten"]) if eintrag else None

    def sitzung_loeschen(self, sitzung_id: str) -> None:
        praefix = f"sitzungen/{sitzung_id}/"
        try:
            antwort = self._s3.list_objects_v2(Bucket=self._bucket, Prefix=praefix)
            objekte = [{"Key": o["Key"]} for o in antwort.get("Contents", [])]
            if objekte:
                self._s3.delete_objects(Bucket=self._bucket, Delete={"Objects": objekte, "Quiet": True})
            self._tabelle.delete_item(Key={"pk": f"SITZUNG#{sitzung_id}", "sk": "META"})
        except Exception as e:
            raise SpeicherFehler(f"Löschen der Sitzung fehlgeschlagen ({type(e).__name__}).") from e

    # ── Texte ──────────────────────────────────────────────────────────────

    def text_ablegen(self, sitzung_id: str, dokument_id: str, text: str) -> None:
        try:
            self._s3.put_object(
                Bucket=self._bucket, Key=self._schluessel(sitzung_id, dokument_id),
                Body=text.encode("utf-8"), ContentType="text/plain; charset=utf-8",
                **self._s3_argumente(),
            )
        except Exception as e:
            raise SpeicherFehler(f"S3 nicht erreichbar ({type(e).__name__}).") from e

    def text_lesen(self, sitzung_id: str, dokument_id: str) -> str | None:
        # Ohne gültige Sitzung kein Text – auch wenn S3 die Lebenszyklusregel noch nicht angewandt hat.
        if self.sitzung_lesen(sitzung_id) is None:
            return None
        try:
            antwort = self._s3.get_object(Bucket=self._bucket, Key=self._schluessel(sitzung_id, dokument_id))
        except self._s3.exceptions.NoSuchKey:
            return None
        except Exception as e:
            raise SpeicherFehler(f"S3 nicht erreichbar ({type(e).__name__}).") from e
        return antwort["Body"].read().decode("utf-8")

    def text_loeschen(self, sitzung_id: str, dokument_id: str) -> None:
        try:
            self._s3.delete_object(Bucket=self._bucket, Key=self._schluessel(sitzung_id, dokument_id))
        except Exception as e:
            raise SpeicherFehler(f"S3 nicht erreichbar ({type(e).__name__}).") from e

    # ── Entwürfe ───────────────────────────────────────────────────────────

    def entwurf_ablegen(self, entwurf: Entwurf) -> None:
        self._schreiben({
            "pk": f"ENTWURF#{entwurf.id}", "sk": "META",
            "daten": entwurf.model_dump_json(), "nutzer_id": entwurf.erstellt_von,
            "akte_id": entwurf.akte_id,
            "ablauf": self._ablauf(self._entwurf_ttl),
        })

    def entwurf_lesen(self, entwurf_id: str) -> Entwurf | None:
        eintrag = self._lesen(f"ENTWURF#{entwurf_id}", "META")
        return Entwurf.model_validate_json(eintrag["daten"]) if eintrag else None

    def entwurf_loeschen(self, entwurf_id: str) -> None:
        try:
            self._tabelle.delete_item(Key={"pk": f"ENTWURF#{entwurf_id}", "sk": "META"})
        except Exception as e:
            raise SpeicherFehler(f"DynamoDB nicht erreichbar ({type(e).__name__}).") from e

    # ── Was zu einer Akte gehört ───────────────────────────────────────────

    def _kennungen_der_akte(self, praefix: str, akte_id: str) -> list[str]:
        """Sucht Einträge eines Typs zu einer Akte.

        Ein voller Durchlauf der Tabelle ist hier vertretbar: Er läuft nur
        beim bestätigten Abschluss einer Akte, nicht im Alltag, und der
        Bestand einer Kanzlei ist klein. Ein eigener Index dafür würde jeden
        Schreibvorgang verteuern.
        """
        from boto3.dynamodb.conditions import Attr

        kennungen: list[str] = []
        start: dict[str, Any] | None = None
        try:
            while True:
                argumente: dict[str, Any] = {
                    "FilterExpression": Attr("akte_id").eq(akte_id) & Attr("pk").begins_with(praefix),
                    "ProjectionExpression": "pk",
                }
                if start:
                    argumente["ExclusiveStartKey"] = start
                antwort = self._tabelle.scan(**argumente)
                kennungen.extend(x["pk"][len(praefix):] for x in antwort.get("Items", []))
                start = antwort.get("LastEvaluatedKey")
                if not start:
                    return sorted(set(kennungen))
        except Exception as e:
            raise SpeicherFehler(f"DynamoDB nicht erreichbar ({type(e).__name__}).") from e

    def sitzungen_der_akte(self, akte_id: str) -> list[str]:
        return self._kennungen_der_akte("SITZUNG#", akte_id)

    def entwuerfe_der_akte(self, akte_id: str) -> list[str]:
        return self._kennungen_der_akte("ENTWURF#", akte_id)

    # ── Nutzung ────────────────────────────────────────────────────────────

    def nutzung_verbuchen(self, eintrag: Nutzungseintrag) -> float:
        monat = eintrag.zeitpunkt.strftime("%Y-%m")
        cent = int(round(eintrag.betrag_eur * 100))
        self._schreiben({
            "pk": f"NUTZUNG#{monat}",
            "sk": f"E#{eintrag.zeitpunkt.strftime('%Y%m%dT%H%M%S')}#{uuid.uuid4().hex[:8]}",
            "nutzer_id": eintrag.nutzer_id, "akte_id": eintrag.akte_id, "funktion": eintrag.funktion,
            "modell": eintrag.modell, "eingabe_tokens": eintrag.eingabe_tokens,
            "ausgabe_tokens": eintrag.ausgabe_tokens, "cent": cent,
            # Nachweis-Felder (ohne Inhalte)
            "sitzung_id": eintrag.sitzung_id, "material_kennung": eintrag.material_kennung,
            "aufgabe_kennung": eintrag.aufgabe_kennung, "passagen": eintrag.passagen,
            "antwort_zeichen": eintrag.antwort_zeichen,
            "ablauf": self._ablauf(_NUTZUNG_TTL),
        })
        try:
            antwort = self._tabelle.update_item(
                Key={"pk": f"NUTZUNG#{monat}", "sk": "SUMME"},
                UpdateExpression="ADD cent :c SET ablauf = :a",
                ExpressionAttributeValues={":c": Decimal(cent), ":a": self._ablauf(_NUTZUNG_TTL)},
                ReturnValues="UPDATED_NEW",
            )
        except Exception as e:
            raise SpeicherFehler(f"DynamoDB nicht erreichbar ({type(e).__name__}).") from e
        return int(antwort["Attributes"]["cent"]) / 100

    def nutzung_monat(self, monat: str) -> float:
        try:
            antwort = self._tabelle.get_item(Key={"pk": f"NUTZUNG#{monat}", "sk": "SUMME"})
        except Exception as e:
            raise SpeicherFehler(f"DynamoDB nicht erreichbar ({type(e).__name__}).") from e
        eintrag = antwort.get("Item")
        return int(eintrag["cent"]) / 100 if eintrag else 0.0

    def nachweis_lesen(self, limit: int = 25) -> list[Nutzungseintrag]:
        """Die jüngsten Einzeleinträge des laufenden Monats, neueste zuerst.

        Gelesen wird die Monatspartition ``NUTZUNG#JJJJ-MM``, nur die
        Einzeleinträge (``sk`` beginnt mit ``E#``), rückwärts sortiert. Für
        eine Übersicht reicht der laufende Monat; ein vollständiger Export über
        mehrere Monate ist ein eigener, verwalteter Weg.
        """
        from boto3.dynamodb.conditions import Key

        monat = datetime.now(timezone.utc).strftime("%Y-%m")
        try:
            antwort = self._tabelle.query(
                KeyConditionExpression=Key("pk").eq(f"NUTZUNG#{monat}") & Key("sk").begins_with("E#"),
                ScanIndexForward=False, Limit=limit,
            )
        except Exception as e:
            raise SpeicherFehler(f"DynamoDB nicht erreichbar ({type(e).__name__}).") from e
        eintraege: list[Nutzungseintrag] = []
        for item in antwort.get("Items", []):
            eintraege.append(Nutzungseintrag(
                zeitpunkt=_zeit_aus_sk(str(item.get("sk", ""))),
                nutzer_id=str(item.get("nutzer_id", "")), akte_id=str(item.get("akte_id", "")),
                funktion=str(item.get("funktion", "")), modell=str(item.get("modell", "")),
                eingabe_tokens=int(item.get("eingabe_tokens", 0)), ausgabe_tokens=int(item.get("ausgabe_tokens", 0)),
                betrag_eur=int(item.get("cent", 0)) / 100,
                sitzung_id=str(item.get("sitzung_id", "")), material_kennung=str(item.get("material_kennung", "")),
                aufgabe_kennung=str(item.get("aufgabe_kennung", "")), passagen=int(item.get("passagen", 0)),
                antwort_zeichen=int(item.get("antwort_zeichen", 0)),
            ))
        return eintraege


def _zeit_aus_sk(sk: str) -> datetime:
    """``E#20260903T170432#ab12cd34`` -> Zeitpunkt; fällt auf jetzt zurück."""
    try:
        return datetime.strptime(sk.split("#")[1], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
    except (IndexError, ValueError):
        return datetime.now(timezone.utc)


def jetzt() -> datetime:
    return datetime.now(timezone.utc)
