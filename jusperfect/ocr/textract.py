"""Texterkennung mit Amazon Textract.

Bilder gehen unmittelbar. **Ein PDF wird auf diesem Rechner Seite für Seite in
ein Bild umgewandelt**, und jedes Bild geht für sich direkt an Textract – ohne
S3, ohne Bucket, ohne einen weiteren Ort, an dem Akteninhalt liegt. Das gilt
unabhängig davon, wie viele Seiten der Scan hat.

Übrig bleibt der Weg über S3 nur noch für ein PDF, das sich nicht öffnen lässt
– beschädigt oder kennwortgeschützt. Dafür wird der Scan kurz in den
Sitzungs-Bucket gelegt, die asynchrone Erkennung gestartet, abgewartet und der
Scan danach sofort gelöscht; der Bucket-Lebenszyklus räumt Reste nach einem Tag
ab, falls ein Lauf abbricht. Ohne eingerichteten Bucket sagt das Programm, was
fehlt.

**Warum umgewandelt und nicht zerlegt wird – der Fehler vom 02.10.2026.**
Bis dahin zerlegte dieses Modul das PDF in einseitige PDFs und schickte jedes
davon als ``Bytes``. Das sah richtig aus, war aber falsch: AWS beschreibt das
Feld eindeutig, und die Beschreibung wird mit ``boto3`` selbst ausgeliefert –

    *"The document bytes must be in PNG or JPEG format."*
    (``botocore/data/textract/2018-06-27/service-2.json``, Shape ``Document``,
    Member ``Bytes``)

PDF und TIFF nimmt Textract nur über ``S3Object`` an. Der Aufruf lief trotzdem
ohne Fehlermeldung durch – er lieferte **nichts**. Ein Scan wäre also lautlos
als "kein Text gefunden" durchgegangen, und das sieht in einer Akte aus wie ein
schlechter Scan und nicht wie ein Programmfehler.

Gefunden hat es ``TEXTERKENNUNG-PRUEFEN.bat`` am Tag seiner Einführung, beim
ersten Lauf in der Kanzlei: *"AWS hat geantwortet, aber das Probewort kam nicht
zurück."* Genau dafür gibt es die Probe – ein Blatt, dessen Inhalt man vorher
kennt, ist der einzige Weg, "nichts gefunden" von "nichts gelesen" zu
unterscheiden.

**Zweimal dieselbe Lehre an derselben Datei.** Am 01.10.2026 stand im Kopf
dieses Moduls ein Satz über mehrseitige PDFs, den der Quelltext nicht hielt.
Am 02.10.2026 stand im Quelltext ein Weg, den die Schnittstelle nicht hält.
Eine Beschreibung, die mehr verspricht als der Quelltext hält, wird geglaubt –
und ein Quelltext, der mehr verspricht als die Gegenseite hält, auch.
"""

from __future__ import annotations

import io
import time
from typing import Any

from jusperfect.aws_handlung import mit_handlung
from jusperfect.domain.models import Seite
from jusperfect.ocr.base import OcrFehler

_WARTEN_SEKUNDEN = 2.0
_MAX_WARTEN_SEKUNDEN = 600.0


def _seiten_aus_bloecken(bloecke: list[dict[str, Any]]) -> list[Seite]:
    zeilen: dict[int, list[str]] = {}
    for block in bloecke:
        if block.get("BlockType") == "LINE" and block.get("Text"):
            zeilen.setdefault(int(block.get("Page", 1)), []).append(block["Text"])
    return [Seite(nummer=nr, text="\n".join(zeilen[nr])) for nr in sorted(zeilen)]


#: Woran eine Abweisung von AWS zu erkennen ist - und was sie heisst.
#:
#: "Textract nicht verfuegbar (ClientError)" stand hier vorher, und damit
#: beginnt dieselbe Suche wie am 01.10.2026 beim Modell: Der haeufigste Grund
#: ist eine fehlende Berechtigung, und der Code allein sagt das nicht. Die
#: Merkmale sind feste Wendungen von AWS; der erklaerende Satz ist unserer.
#:
#: Der Wortlaut von AWS wird NICHT durchgereicht. In einer Abweisung steht
#: mitunter ein Stueck der Anfrage, und das ist hier ein gescanntes Blatt aus
#: einer Mandatsakte.
_ABWEISUNGEN: tuple[tuple[str, str], ...] = (
    ("is not authorized to perform",
     "Der Zugriffsrichtlinie fehlt das Recht textract:DetectDocumentText. "
     "Es steht in infra/iam-nur-claude.json unter TexterkennungFuerScans; "
     "die Richtlinie muss in AWS durch die neue Fassung ersetzt werden "
     "(IAM -> Richtlinien -> jusperfect-nur-claude -> Bearbeiten)."),
    ("explicit deny",
     "Die Zugriffsrichtlinie verbietet den Aufruf ausdruecklich - meist, weil "
     "die Region nicht abgedeckt ist (siehe infra/IAM.md)."),
    ("unsupporteddocument",
     "Dieses Blatt kann Textract nicht lesen - es ist weder ein Bild noch ein "
     "lesbares PDF. Das Dokument bleibt ungelesen, die uebrigen nicht."),
    ("security token",
     "Der AWS-Zugang wird nicht erkannt. ZUGANG-PRUEFEN.bat sagt, woran es "
     "liegt."),
    ("provisionedthroughput",
     "AWS weist gerade zu viele Anfragen zugleich ab. Der naechste Versuch "
     "geht meist durch."),
)


def _warum(fehler: Exception) -> str:
    """Aus einer Abweisung von AWS einen Satz machen, der weiterhilft."""
    antwort = getattr(fehler, "response", None)
    code, satz = type(fehler).__name__, ""
    if isinstance(antwort, dict):
        code = str(antwort.get("Error", {}).get("Code", "")) or code
        satz = str(antwort.get("Error", {}).get("Message", "")).strip()
    klein = f"{code} {satz}".lower()
    for merkmal, erklaerung in _ABWEISUNGEN:
        if merkmal in klein:
            return mit_handlung(erklaerung, fehler)
    return f"Textract nicht verfügbar ({code})."


#: Auflösung, mit der eine PDF-Seite zum Bild wird.
#:
#: 200 Punkte je Zoll ist das, was ein Kanzleiscanner üblicherweise liefert,
#: und Textract nennt 150 als Untergrenze für brauchbare Erkennung. Höher
#: hiesse groessere Bilder ohne besseren Text; das Feld ``Bytes`` nimmt
#: höchstens 5 MB.
PUNKTE_JE_ZOLL = 200


def seiten_als_bild(daten: bytes, punkte_je_zoll: int = PUNKTE_JE_ZOLL) -> list[bytes]:
    """Jede Seite eines PDFs als PNG – der Weg an S3 vorbei.

    Textract nimmt über ``Bytes`` ausschliesslich PNG und JPEG an; PDF nur
    über einen Ablageort in S3. Wandelt man die Seiten vorher auf diesem
    Rechner um, verlangt Textract keinen mehr.

    Das ist kein Kunstgriff, sondern der Unterschied zwischen einem
    Auftragsverarbeiter, der Akteninhalt **verarbeitet**, und einem, der ihn
    **speichert**. Der zweite will eingerichtet, verschlüsselt, mit einem
    Lebenszyklus versehen und in der DSFA genannt werden.

    Umgewandelt wird mit PDFium – derselben Maschine, mit der Chrome PDFs
    anzeigt. Sie bringt die Standardschriften selbst mit; eine Seite, die am
    Bildschirm lesbar ist, ist es danach auch als Bild.

    Leere Liste, wenn sich das PDF nicht öffnen lässt. Dann bleibt der Weg
    über S3, der auch mit einem beschädigten Blatt zurechtkommt.
    """
    try:
        import pypdfium2 as pdfium

        bilder: list[bytes] = []
        dokument = pdfium.PdfDocument(io.BytesIO(daten))
        try:
            for seite in dokument:
                puffer = io.BytesIO()
                seite.render(scale=punkte_je_zoll / 72).to_pil().save(puffer, format="PNG")
                bilder.append(puffer.getvalue())
        finally:
            dokument.close()
        return bilder
    except Exception:
        return []


def seitenzahl(daten: bytes) -> int:
    """Wie viele Seiten hat dieses PDF? 0, wenn es sich nicht lesen lässt.

    Die Zahl entscheidet über den Weg – und damit darüber, ob überhaupt ein
    Ablageort gebraucht wird. Lässt sich das PDF nicht öffnen, ist 0 die
    vorsichtige Antwort: Dann geht es den asynchronen Weg, der auch mit einem
    kaputten Blatt zurechtkommt.
    """
    try:
        from pypdf import PdfReader

        return len(PdfReader(io.BytesIO(daten)).pages)
    except Exception:
        return 0


class TextractOcr:
    def __init__(self, region: str, bucket: str, kms_schluessel_id: str | None = None,
                 textract: Any | None = None, s3: Any | None = None, warten: float = _WARTEN_SEKUNDEN,
                 schlafen: Any = time.sleep) -> None:
        if textract is None or s3 is None:
            import boto3

            textract = textract or boto3.client("textract", region_name=region)
            s3 = s3 or boto3.client("s3", region_name=region)
        self._textract = textract
        self._s3 = s3
        self._bucket = bucket
        self._kms = kms_schluessel_id
        self._warten = warten
        self._schlafen = schlafen

    def erkennen(self, daten: bytes, mime_typ: str, sitzung_id: str, dokument_id: str) -> list[Seite]:
        try:
            # Ein Bild geht unmittelbar - PNG und JPEG sind genau das, was
            # das Feld Bytes annimmt. Das spart den Bucket und damit einen
            # Ablageort, der sonst eingerichtet, gesichert und in der DSFA
            # genannt werden muesste.
            if mime_typ.startswith("image/"):
                antwort = self._textract.detect_document_text(Document={"Bytes": daten})
                return _seiten_aus_bloecken(antwort.get("Blocks", []))

            # Seite für Seite, auf diesem Rechner zum Bild gemacht. Jedes
            # Bild geht einzeln und unmittelbar an Textract; S3 wird nicht
            # gebraucht.
            einzeln = seiten_als_bild(daten)
            if einzeln:
                seiten: list[Seite] = []
                for nummer, blatt in enumerate(einzeln, 1):
                    antwort = self._textract.detect_document_text(Document={"Bytes": blatt})
                    for seite in _seiten_aus_bloecken(antwort.get("Blocks", [])):
                        # Textract zählt in jedem Aufruf wieder bei 1. Die Nummer
                        # muss die des GANZEN Dokuments sein - sonst zeigt jede
                        # Fundstelle auf Seite 1, und die Belegpflicht trägt nicht.
                        seiten.append(Seite(nummer=nummer, text=seite.text))
                return seiten

            # Nur noch der Fall, dass sich das PDF nicht öffnen lässt.
            return self._asynchron(daten, sitzung_id, dokument_id)
        except OcrFehler:
            raise
        except Exception as e:
            raise OcrFehler(_warum(e)) from e

    def _asynchron(self, daten: bytes, sitzung_id: str, dokument_id: str) -> list[Seite]:
        # Ohne Ablageort sagt das Programm, was fehlt - statt einen Fehler von
        # S3 durchzureichen, der nach einem Programmfehler aussieht.
        if not self._bucket:
            raise OcrFehler(
                "Dieses PDF lässt sich nicht öffnen – "
                "vermutlich ist es beschädigt oder kennwortgeschützt. Für diesen "
                "Fall verlangt Textract einen Ablageort in S3; einzurichten mit "
                "JUSPERFECT_S3_BUCKET (siehe AWS-EINRICHTEN.md). Lesbare PDFs "
                "brauchen ihn nicht, gleich wie viele Seiten sie haben."
            )
        schluessel = f"sitzungen/{sitzung_id}/scan/{dokument_id}.pdf"
        argumente = {"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": self._kms} if self._kms else {"ServerSideEncryption": "AES256"}
        self._s3.put_object(Bucket=self._bucket, Key=schluessel, Body=daten, **argumente)
        try:
            start = self._textract.start_document_text_detection(
                DocumentLocation={"S3Object": {"Bucket": self._bucket, "Name": schluessel}}
            )
            auftrag = start["JobId"]
            gewartet = 0.0
            bloecke: list[dict[str, Any]] = []
            token: str | None = None
            while True:
                argumente_get = {"JobId": auftrag}
                if token:
                    argumente_get["NextToken"] = token
                antwort = self._textract.get_document_text_detection(**argumente_get)
                status = antwort.get("JobStatus")
                if status == "IN_PROGRESS":
                    if gewartet >= _MAX_WARTEN_SEKUNDEN:
                        raise OcrFehler("Textract hat innerhalb der Wartezeit nicht geantwortet.")
                    self._schlafen(self._warten)
                    gewartet += self._warten
                    continue
                if status != "SUCCEEDED":
                    raise OcrFehler(f"Textract meldet Status {status}.")
                bloecke.extend(antwort.get("Blocks", []))
                token = antwort.get("NextToken")
                if not token:
                    break
            return _seiten_aus_bloecken(bloecke)
        finally:
            self._s3.delete_object(Bucket=self._bucket, Key=schluessel)
