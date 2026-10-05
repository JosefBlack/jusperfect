"""Speichergrenze für das dauerhafte Aktengedächtnis."""

from __future__ import annotations

from typing import Protocol

from jusperfect.domain.models import Aktengedaechtnis


class GedaechtnisFehler(RuntimeError):
    pass


class GedaechtnisSpeicher(Protocol):
    def lesen(self, akte_id: str) -> Aktengedaechtnis | None: ...
    def ablegen(self, gedaechtnis: Aktengedaechtnis) -> None: ...
    def loeschen(self, akte_id: str) -> None: ...
    def auflisten(self) -> list[Aktengedaechtnis]:
        """Alle vorhandenen Aktengedächtnisse – für die Aufsicht.

        Die Kennung der Akte steht nur im Inhalt, nicht im Objektnamen; die
        Liste muss deshalb lesen, nicht nur auflisten.
        """
        ...
