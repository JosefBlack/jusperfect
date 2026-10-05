"""Workflow-Packs: welcher Beweis fehlt, welcher Schritt folgt.

Ein Pack ist das Beweisprofil eines Rechtsgebiets – ein austauschbares JSON,
kein Code. Es wird deterministisch gegen den geladenen Aktentext geprüft:
Jede Anforderung sucht ihre Stichworte in den Passagen. Findet sie sich,
gilt sie als belegt vorhanden – mit der Fundstelle als Beleg. Findet sie
sich nicht, ist sie offen, und der Pack nennt den nächsten Schritt.

Kein Modellaufruf: Die Prüfung ist reproduzierbar, kostenlos und läuft auch
ohne KI-Zugang. Das trägt den Flow (was fehlt der Akte?) und passt zur
Belegpflicht (kein Fund ohne Fundstelle).
"""

from __future__ import annotations

import re
from pathlib import Path

from jusperfect.domain.models import (
    PackBefund, PackErgebnis, Passage, Quelle, Workflowpack,
)

STANDARD_VERZEICHNIS = Path(__file__).resolve().parent.parent / "packs"
_MAX_BELEGE = 3


class WorkflowFehler(RuntimeError):
    pass


class PackNichtGefunden(WorkflowFehler):
    pass


def _quelle(p: Passage) -> Quelle:
    zitat = p.text.strip().replace("\n", " ")
    return Quelle(kennung=p.kennung, dokument_id=p.dokument_id, dokument_titel=p.dokument_titel,
                  seite=p.seite, zitat=zitat[:200] + ("…" if len(zitat) > 200 else ""))


class Workflowdienst:
    def __init__(self, verzeichnis: Path | None = None) -> None:
        verzeichnis = Path(verzeichnis) if verzeichnis else STANDARD_VERZEICHNIS
        self._packs: dict[str, Workflowpack] = {}
        if verzeichnis.is_dir():
            for datei in sorted(verzeichnis.glob("*.json")):
                pack = Workflowpack.model_validate_json(datei.read_text(encoding="utf-8"))
                self._packs[pack.id] = pack

    def liste(self) -> list[Workflowpack]:
        return list(self._packs.values())

    def pack(self, pack_id: str) -> Workflowpack:
        try:
            return self._packs[pack_id]
        except KeyError:
            raise PackNichtGefunden(f"Kein Workflow-Pack mit der Kennung {pack_id!r}.") from None

    def vorschlag(self, rechtsgebiet: str) -> Workflowpack | None:
        """Das Pack, dessen Rechtsgebiet am besten zur Akte passt."""
        rg = (rechtsgebiet or "").strip().lower()
        if not rg:
            return None
        for pack in self._packs.values():
            p = pack.rechtsgebiet.strip().lower()
            if p and (p in rg or rg in p):
                return pack
        return None

    def pruefen(self, pack: Workflowpack, passagen: list[Passage]) -> PackErgebnis:
        befunde: list[PackBefund] = []
        for anf in pack.anforderungen:
            belege: list[Quelle] = []
            if anf.stichworte:
                # Wortanfang gebunden (\b), damit ein Stichwort nicht mitten in
                # einem anderen Wort auslöst; Stämme wie "befuhr" bleiben offen.
                muster = re.compile("|".join(rf"\b{re.escape(w)}" for w in anf.stichworte), re.IGNORECASE)
                for p in passagen:
                    if muster.search(p.text):
                        belege.append(_quelle(p))
                        if len(belege) >= _MAX_BELEGE:
                            break
            vorhanden = len(belege) >= anf.min_treffer
            befunde.append(PackBefund(
                anforderung_id=anf.id, titel=anf.titel, pflicht=anf.pflicht,
                status="vorhanden" if vorhanden else "fehlt",
                belege=belege, hinweis="" if vorhanden else anf.fehlt_hinweis,
            ))
        vorhanden = sum(1 for b in befunde if b.status == "vorhanden")
        fehlt_pflicht = sum(1 for b in befunde if b.status == "fehlt" and b.pflicht)
        offene = [b.hinweis for b in befunde if b.status == "fehlt" and b.pflicht and b.hinweis]
        return PackErgebnis(pack_id=pack.id, titel=pack.titel, befunde=befunde,
                            vorhanden=vorhanden, fehlt_pflicht=fehlt_pflicht, offene_schritte=offene)
