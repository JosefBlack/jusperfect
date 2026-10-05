"""Temporärer Textspeicher: verschlüsselt, mit kurzer Lebensdauer.

Extrahierte Dokumenttexte liegen hier nur so lange, wie eine Aktensitzung
sie braucht. Sie sind im Speicher mit AES-256-GCM verschlüsselt (Schlüssel
nur in diesem Prozess), laufen nach der eingestellten Zeit ab und werden
beim Schließen der Sitzung sofort gelöscht. Auf die Platte schreibt dieser
Speicher nichts.
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass
class _Eintrag:
    nonce: bytes
    geheimtext: bytes
    ablauf: float
    gruppe: str | None


class TemporaerSpeicher:
    def __init__(self, ttl_sekunden: int = 900, uhr: Callable[[], float] = time.monotonic) -> None:
        if ttl_sekunden <= 0:
            raise ValueError("Die Lebensdauer muss positiv sein.")
        self.ttl_sekunden = ttl_sekunden
        self._uhr = uhr
        self._aesgcm = AESGCM(AESGCM.generate_key(bit_length=256))
        self._eintraege: dict[str, _Eintrag] = {}
        self._sperre = threading.Lock()

    def ablegen(self, schluessel: str, text: str, gruppe: str | None = None) -> None:
        nonce = os.urandom(12)
        geheimtext = self._aesgcm.encrypt(nonce, text.encode("utf-8"), schluessel.encode("utf-8"))
        with self._sperre:
            self._eintraege[schluessel] = _Eintrag(nonce, geheimtext, self._uhr() + self.ttl_sekunden, gruppe)

    def lesen(self, schluessel: str) -> str | None:
        with self._sperre:
            eintrag = self._eintraege.get(schluessel)
            if eintrag is None:
                return None
            if eintrag.ablauf <= self._uhr():
                del self._eintraege[schluessel]
                return None
        klartext = self._aesgcm.decrypt(eintrag.nonce, eintrag.geheimtext, schluessel.encode("utf-8"))
        return klartext.decode("utf-8")

    def verlaengern(self, gruppe: str) -> None:
        """Eine aktive Sitzung hält ihre Texte am Leben."""
        with self._sperre:
            neu = self._uhr() + self.ttl_sekunden
            for eintrag in self._eintraege.values():
                if eintrag.gruppe == gruppe:
                    eintrag.ablauf = neu

    def loeschen(self, schluessel: str) -> None:
        with self._sperre:
            self._eintraege.pop(schluessel, None)

    def loeschen_gruppe(self, gruppe: str) -> int:
        with self._sperre:
            treffer = [k for k, e in self._eintraege.items() if e.gruppe == gruppe]
            for k in treffer:
                del self._eintraege[k]
        return len(treffer)

    def aufraeumen(self) -> int:
        jetzt = self._uhr()
        with self._sperre:
            abgelaufen = [k for k, e in self._eintraege.items() if e.ablauf <= jetzt]
            for k in abgelaufen:
                del self._eintraege[k]
        return len(abgelaufen)

    def __len__(self) -> int:
        with self._sperre:
            return len(self._eintraege)
