from __future__ import annotations

from typing import Protocol

from jusperfect.domain.models import Seite


class OcrFehler(RuntimeError):
    pass


class OcrNichtVerfuegbar(OcrFehler):
    """Kein OCR eingerichtet – der Scan bleibt außen vor, mit Hinweis."""


class OcrDienst(Protocol):
    def erkennen(self, daten: bytes, mime_typ: str, sitzung_id: str, dokument_id: str) -> list[Seite]: ...


class KeinOcr:
    def erkennen(self, daten: bytes, mime_typ: str, sitzung_id: str, dokument_id: str) -> list[Seite]:
        raise OcrNichtVerfuegbar("Für gescannte Dokumente ist keine Texterkennung eingerichtet (JUSPERFECT_OCR=textract).")
