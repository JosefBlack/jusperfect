"""jurnodes-Ersatz aus einem Ordner mit Testakten.

Für Entwicklung, Tests und die Vorführung ohne Kanzleianbindung. Jede Akte
ist ein Unterordner mit ``akte.json`` (Stammdaten, Dokumentliste, Beteiligte,
Fristen) und den Dokumentdateien. Zurückgeschrieben wird – nur mit Freigabe –
in den Unterordner ``vermerke``.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from jusperfect.domain.models import Akte, Beteiligter, Dokument, Frist
from jusperfect.jurnodes import gedaechtnisdatei
from jusperfect.jurnodes.base import AkteNichtGefunden, DokumentNichtGefunden, JurNodesFehler
from jusperfect.security.approval import Freigabe, Freigabestelle

MIME_NACH_ENDUNG = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class FixtureJurNodesAdapter:
    def __init__(self, wurzel: Path, freigabestelle: Freigabestelle, schreibbar: bool = False) -> None:
        self._wurzel = Path(wurzel)
        self._freigabestelle = freigabestelle
        self._schreibbar = schreibbar
        self.geschriebene_vermerke: list[dict] = []
        if not self._wurzel.is_dir():
            raise JurNodesFehler(f"Testaktenordner nicht gefunden: {self._wurzel}")

    # ── Lesen ──────────────────────────────────────────────────────────────

    def _akten_ordner(self) -> list[Path]:
        return sorted(p for p in self._wurzel.iterdir() if (p / "akte.json").is_file())

    def _laden(self, ordner: Path) -> dict:
        return json.loads((ordner / "akte.json").read_text(encoding="utf-8"))

    def _ordner(self, akte_id: str) -> Path:
        for ordner in self._akten_ordner():
            if self._laden(ordner)["akte"]["id"] == akte_id:
                return ordner
        raise AkteNichtGefunden(f"Akte {akte_id} nicht gefunden.")

    def akten_suchen(self, suchbegriff: str = "") -> list[Akte]:
        begriff = suchbegriff.strip().lower()
        treffer = []
        for ordner in self._akten_ordner():
            akte = Akte.model_validate(self._laden(ordner)["akte"])
            haystack = " ".join([akte.aktenzeichen, akte.bezeichnung, akte.rechtsgebiet]).lower()
            if not begriff or begriff in haystack:
                treffer.append(akte)
        return treffer

    def akte(self, akte_id: str) -> Akte:
        return Akte.model_validate(self._laden(self._ordner(akte_id))["akte"])

    def dokumente(self, akte_id: str) -> list[Dokument]:
        ordner = self._ordner(akte_id)
        ergebnis = []
        for eintrag in self._laden(ordner).get("dokumente", []):
            datei = ordner / eintrag["dateiname"]
            ergebnis.append(Dokument(
                akte_id=akte_id,
                mime_typ=eintrag.get("mime_typ") or MIME_NACH_ENDUNG.get(datei.suffix.lower(), "application/octet-stream"),
                groesse_bytes=datei.stat().st_size if datei.is_file() else None,
                **{k: v for k, v in eintrag.items() if k not in ("mime_typ", "akte_id")},
            ))
        return ergebnis

    def dokument_laden(self, akte_id: str, dokument_id: str) -> tuple[Dokument, bytes]:
        ordner = self._ordner(akte_id)
        for dokument in self.dokumente(akte_id):
            if dokument.id == dokument_id:
                datei = ordner / dokument.dateiname
                if not datei.is_file():
                    raise DokumentNichtGefunden(f"Datei zu Dokument {dokument_id} fehlt.")
                return dokument, datei.read_bytes()
        raise DokumentNichtGefunden(f"Dokument {dokument_id} nicht in Akte {akte_id}.")

    def beteiligte(self, akte_id: str) -> list[Beteiligter]:
        return [Beteiligter.model_validate(b) for b in self._laden(self._ordner(akte_id)).get("beteiligte", [])]

    def fristen(self, akte_id: str) -> list[Frist]:
        return [Frist.model_validate(f) for f in self._laden(self._ordner(akte_id)).get("fristen", [])]

    # ── Schreiben – nur mit Freigabe ───────────────────────────────────────

    def vermerk_schreiben(self, akte_id: str, titel: str, text: str, freigabe: Freigabe) -> str:
        self._freigabestelle.pruefen(freigabe, akte_id, text)
        ordner = self._ordner(akte_id)
        zeit = datetime.now(timezone.utc)
        kennung = f"VM-{zeit.strftime('%Y%m%d-%H%M%S')}-{freigabe.entwurf_id[:8]}"
        self.geschriebene_vermerke.append({
            "kennung": kennung, "akte_id": akte_id, "titel": titel,
            "nutzer_id": freigabe.nutzer_id, "zeitpunkt": zeit.isoformat(), "text": text,
        })
        if self._schreibbar:
            ziel = ordner / "vermerke"
            ziel.mkdir(exist_ok=True)
            sicherer_titel = re.sub(r"[^A-Za-z0-9ÄÖÜäöüß_-]+", "_", titel)[:60]
            (ziel / f"{kennung}_{sicherer_titel}.md").write_text(
                f"# {titel}\n\nFreigegeben von {freigabe.nutzer_id} am {zeit.isoformat()}\n\n{text}\n",
                encoding="utf-8",
            )
        return kennung

    # ── Das Aktengedächtnis in der Akte ─────────────────────────────────────

    def gedaechtnis_lesen(self, akte_id: str) -> bytes | None:
        return gedaechtnisdatei.lesen(self._ordner(akte_id))

    def gedaechtnis_ablegen(self, akte_id: str, rohdaten: bytes) -> None:
        gedaechtnisdatei.ablegen(self._ordner(akte_id), rohdaten, self._schreibbar)

    def inhalte_vergessen(self, akte_id: str | None = None,
                          dokument_id: str | None = None) -> None:
        """Nichts zu tun: Dieser Adapter puffert keinen Akteninhalt.

        Steht hier ausdruecklich und nicht als fehlende Methode - sonst waere
        beim naechsten Adapter nicht zu erkennen, ob der Puffer vergessen
        wurde oder keiner da ist (Befund N10).
        """

    def gedaechtnis_loeschen(self, akte_id: str) -> None:
        gedaechtnisdatei.loeschen(self._ordner(akte_id), self._schreibbar)
