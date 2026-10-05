"""Freigaben für das Zurückschreiben nach jur|nodes.

jusperfect schreibt nie von sich aus. Eine Freigabe entsteht nur, wenn ein
benannter Nutzer einen konkreten Text ausdrücklich bestätigt. Sie ist an
diesen Text gebunden (Prüfsumme) und an diesen Prozesslauf (Signaturschlüssel
im Speicher). Ein nachträglich geänderter Text, eine nachgebaute Freigabe
oder eine aus einem anderen Lauf werden abgewiesen, bevor jur|nodes auch nur
angesprochen wird.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone


class FreigabeUngueltig(PermissionError):
    """Die Freigabe passt nicht zu Text, Akte oder Prozesslauf."""


def text_pruefsumme(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Freigabe:
    entwurf_id: str
    akte_id: str
    nutzer_id: str
    text_pruefsumme: str
    zeitpunkt: datetime
    signatur: str


class Freigabestelle:
    """Erteilt und prüft Freigaben. Genau eine Instanz je Prozess."""

    def __init__(self) -> None:
        self._schluessel = secrets.token_bytes(32)

    def _signieren(self, entwurf_id: str, akte_id: str, nutzer_id: str, pruefsumme: str, zeitpunkt: datetime) -> str:
        nachricht = "\x1f".join([entwurf_id, akte_id, nutzer_id, pruefsumme, zeitpunkt.isoformat()])
        return hmac.new(self._schluessel, nachricht.encode("utf-8"), hashlib.sha256).hexdigest()

    def erteilen(self, entwurf_id: str, akte_id: str, nutzer_id: str, text: str) -> Freigabe:
        if not nutzer_id:
            raise FreigabeUngueltig("Eine Freigabe braucht einen benannten Nutzer.")
        if not text.strip():
            raise FreigabeUngueltig("Ein leerer Text kann nicht freigegeben werden.")
        zeitpunkt = datetime.now(timezone.utc)
        pruefsumme = text_pruefsumme(text)
        return Freigabe(
            entwurf_id=entwurf_id,
            akte_id=akte_id,
            nutzer_id=nutzer_id,
            text_pruefsumme=pruefsumme,
            zeitpunkt=zeitpunkt,
            signatur=self._signieren(entwurf_id, akte_id, nutzer_id, pruefsumme, zeitpunkt),
        )

    def pruefen(self, freigabe: object, akte_id: str, text: str) -> Freigabe:
        if not isinstance(freigabe, Freigabe):
            raise FreigabeUngueltig("Schreiben nach jur|nodes nur mit einer Freigabe.")
        if freigabe.akte_id != akte_id:
            raise FreigabeUngueltig("Die Freigabe gehört zu einer anderen Akte.")
        if not hmac.compare_digest(freigabe.text_pruefsumme, text_pruefsumme(text)):
            raise FreigabeUngueltig("Der Text wurde nach der Freigabe verändert.")
        erwartet = self._signieren(
            freigabe.entwurf_id, freigabe.akte_id, freigabe.nutzer_id,
            freigabe.text_pruefsumme, freigabe.zeitpunkt,
        )
        if not hmac.compare_digest(freigabe.signatur, erwartet):
            raise FreigabeUngueltig("Die Freigabe stammt nicht aus diesem Programmlauf.")
        return freigabe
