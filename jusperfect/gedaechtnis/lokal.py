"""Dateibasierter Gedächtnisspeicher – für den örtlichen Betrieb, Demo und Tests.

Die Ablage ist gepackt (``…json.gz``, siehe ``gedaechtnis/packen.py``). Ein
Gedächtnis aus früheren Fassungen liegt noch ungepackt daneben (``…json``); es
wird weiter gelesen und beim nächsten Speichern gepackt abgelegt. Die
ungepackte Datei wird dabei entfernt – zwei Stände desselben Gedächtnisses
nebeneinander wären eine Fehlerquelle, und der ungepackte wäre zugleich der
lesbarere.
"""

from __future__ import annotations

import hashlib
import os
import threading
from pathlib import Path

from jusperfect.domain.models import Aktengedaechtnis
from jusperfect.gedaechtnis.base import GedaechtnisFehler
from jusperfect.gedaechtnis.packen import entpacken, packen

ENDUNG = ".json.gz"
ENDUNG_ALT = ".json"


class LokalerGedaechtnisSpeicher:
    def __init__(self, ordner: Path) -> None:
        self._ordner = ordner.resolve()
        self._ordner.mkdir(parents=True, exist_ok=True)
        self._sperre = threading.Lock()

    def _name(self, akte_id: str) -> str:
        # Aktenzeichen gehören weder in Objekt- noch in Dateinamen. Der Hash
        # verhindert zugleich, dass eine übergebene Kennung den Ordner verlässt.
        return hashlib.sha256(akte_id.encode("utf-8")).hexdigest()

    def _pfad(self, akte_id: str, endung: str = ENDUNG) -> Path:
        pfad = (self._ordner / (self._name(akte_id) + endung)).resolve()
        if pfad.parent != self._ordner:
            raise GedaechtnisFehler("Ungültige Aktenkennung für das Gedächtnis.")
        return pfad

    def _lesen(self, pfad: Path) -> Aktengedaechtnis:
        try:
            return entpacken(pfad.read_bytes())
        except GedaechtnisFehler:
            raise
        except Exception as e:
            raise GedaechtnisFehler(
                f"Lokales Aktengedächtnis ist nicht lesbar ({type(e).__name__})."
            ) from e

    def lesen(self, akte_id: str) -> Aktengedaechtnis | None:
        for endung in (ENDUNG, ENDUNG_ALT):
            pfad = self._pfad(akte_id, endung)
            if pfad.is_file():
                return self._lesen(pfad)
        return None

    def ablegen(self, gedaechtnis: Aktengedaechtnis) -> None:
        pfad = self._pfad(gedaechtnis.akte_id)
        temporaer = pfad.with_name(pfad.name + ".tmp")
        try:
            with self._sperre:
                temporaer.write_bytes(packen(gedaechtnis))
                os.replace(temporaer, pfad)
                # Der ungepackte Vorgaenger darf nicht liegen bleiben.
                self._pfad(gedaechtnis.akte_id, ENDUNG_ALT).unlink(missing_ok=True)
        except Exception as e:
            raise GedaechtnisFehler(
                f"Lokales Aktengedächtnis konnte nicht gespeichert werden ({type(e).__name__})."
            ) from e

    def auflisten(self) -> list[Aktengedaechtnis]:
        gepackt = {p.name[: -len(ENDUNG)]: p for p in self._ordner.glob("*" + ENDUNG)}
        ungepackt = {p.name[: -len(ENDUNG_ALT)]: p for p in self._ordner.glob("*" + ENDUNG_ALT)
                     if not p.name.endswith(ENDUNG)}
        # Liegt beides vor, gilt der gepackte Stand - er ist der neuere.
        pfade = {**ungepackt, **gepackt}
        return [self._lesen(pfad) for _, pfad in sorted(pfade.items())]

    def loeschen(self, akte_id: str) -> None:
        try:
            for endung in (ENDUNG, ENDUNG_ALT):
                self._pfad(akte_id, endung).unlink(missing_ok=True)
        except Exception as e:
            raise GedaechtnisFehler(
                f"Lokales Aktengedächtnis konnte nicht gelöscht werden ({type(e).__name__})."
            ) from e
