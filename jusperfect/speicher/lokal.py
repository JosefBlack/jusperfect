"""Sitzungsspeicher im Arbeitsspeicher – für lokalen Betrieb und Tests.

Die Texte liegen im verschlüsselten ``TemporaerSpeicher``; Sitzungen und
Entwürfe in einfachen Wörterbüchern mit Ablaufzeit.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from jusperfect.domain.models import Entwurf, Nutzungseintrag, Sitzung
from jusperfect.security.tempstore import TemporaerSpeicher


class LokalerSpeicher:
    def __init__(self, sitzung_ttl: int = 900, entwurf_ttl: int = 7 * 24 * 3600,
                 uhr: Callable[[], float] = time.monotonic) -> None:
        self._uhr = uhr
        self._sitzung_ttl = sitzung_ttl
        self._entwurf_ttl = entwurf_ttl
        self._texte = TemporaerSpeicher(sitzung_ttl, uhr)
        self._sitzungen: dict[str, tuple[Sitzung, float]] = {}
        self._entwuerfe: dict[str, tuple[Entwurf, float]] = {}
        self._nutzung: dict[str, float] = {}
        self.eintraege: list[Nutzungseintrag] = []
        self._sperre = threading.Lock()

    def _aufraeumen(self) -> None:
        jetzt = self._uhr()
        for d in (self._sitzungen, self._entwuerfe):
            for k in [k for k, (_, ablauf) in d.items() if ablauf <= jetzt]:
                del d[k]
        self._texte.aufraeumen()

    def sitzung_ablegen(self, sitzung: Sitzung) -> None:
        with self._sperre:
            self._sitzungen[sitzung.id] = (sitzung, self._uhr() + self._sitzung_ttl)
        self._texte.verlaengern(sitzung.id)

    def sitzung_lesen(self, sitzung_id: str) -> Sitzung | None:
        with self._sperre:
            self._aufraeumen()
            eintrag = self._sitzungen.get(sitzung_id)
        return eintrag[0] if eintrag else None

    def sitzung_loeschen(self, sitzung_id: str) -> None:
        with self._sperre:
            self._sitzungen.pop(sitzung_id, None)
        self._texte.loeschen_gruppe(sitzung_id)

    def text_ablegen(self, sitzung_id: str, dokument_id: str, text: str) -> None:
        self._texte.ablegen(f"{sitzung_id}/{dokument_id}", text, gruppe=sitzung_id)

    def text_lesen(self, sitzung_id: str, dokument_id: str) -> str | None:
        return self._texte.lesen(f"{sitzung_id}/{dokument_id}")

    def text_loeschen(self, sitzung_id: str, dokument_id: str) -> None:
        self._texte.loeschen(f"{sitzung_id}/{dokument_id}")

    def entwurf_ablegen(self, entwurf: Entwurf) -> None:
        with self._sperre:
            self._entwuerfe[entwurf.id] = (entwurf, self._uhr() + self._entwurf_ttl)

    def entwurf_lesen(self, entwurf_id: str) -> Entwurf | None:
        with self._sperre:
            self._aufraeumen()
            eintrag = self._entwuerfe.get(entwurf_id)
        return eintrag[0] if eintrag else None

    def entwurf_loeschen(self, entwurf_id: str) -> None:
        with self._sperre:
            self._entwuerfe.pop(entwurf_id, None)

    def sitzungen_der_akte(self, akte_id: str) -> list[str]:
        with self._sperre:
            self._aufraeumen()
            return [s.id for s, _ in self._sitzungen.values() if s.akte_id == akte_id]

    def entwuerfe_der_akte(self, akte_id: str) -> list[str]:
        with self._sperre:
            self._aufraeumen()
            return [e.id for e, _ in self._entwuerfe.values() if e.akte_id == akte_id]

    def nutzung_verbuchen(self, eintrag: Nutzungseintrag) -> float:
        monat = eintrag.zeitpunkt.strftime("%Y-%m")
        with self._sperre:
            self.eintraege.append(eintrag)
            self._nutzung[monat] = self._nutzung.get(monat, 0.0) + eintrag.betrag_eur
            return self._nutzung[monat]

    def nutzung_monat(self, monat: str) -> float:
        with self._sperre:
            return self._nutzung.get(monat, 0.0)

    def nachweis_lesen(self, limit: int = 25) -> list[Nutzungseintrag]:
        with self._sperre:
            return list(reversed(self.eintraege[-limit:]))

    def anzahl_texte(self) -> int:
        return len(self._texte)
