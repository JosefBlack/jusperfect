"""Protokollierung ohne Inhalte.

Das Konzept verlangt: vollständige Dokumenttexte und Prompts stehen
standardmäßig nicht in Anwendungslogs. Dieses Modul macht das technisch
verbindlich – ein Protokolleintrag besteht aus einem Ereignisnamen und
kurzen, benannten Feldern. Felder, die nach Inhalt aussehen, werden
abgewiesen; lange Werte ebenfalls. Wer Text nachvollziehen muss, bekommt eine
Kurzkennung (Prüfsumme und Länge), nie den Text.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

VERBOTENE_FELDER = frozenset({
    "text", "prompt", "inhalt", "frage", "antwort", "passage", "passagen",
    "dokumenttext", "system", "nachricht", "entwurf", "body", "content",
})
MAX_WERT_LAENGE = 200


class ProtokollVerstoss(ValueError):
    pass


def kurzkennung(text: str) -> str:
    """Prüfsumme und Länge – erlaubt Wiedererkennung, verrät nichts."""
    return f"{hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]}:{len(text)}"


def protokoll(name: str) -> logging.Logger:
    return logging.getLogger(f"jusperfect.{name}")


def _pruefen(felder: dict[str, Any]) -> None:
    for feld, wert in felder.items():
        if feld.lower() in VERBOTENE_FELDER:
            raise ProtokollVerstoss(f"Feld {feld!r} darf nicht protokolliert werden.")
        if isinstance(wert, str) and len(wert) > MAX_WERT_LAENGE:
            raise ProtokollVerstoss(f"Feld {feld!r} ist zu lang für das Protokoll ({len(wert)} Zeichen).")
        if isinstance(wert, (list, dict)) and len(json.dumps(wert, ensure_ascii=False)) > MAX_WERT_LAENGE:
            raise ProtokollVerstoss(f"Feld {feld!r} ist zu umfangreich für das Protokoll.")


def ereignis(logger: logging.Logger, name: str, **felder: Any) -> None:
    _pruefen(felder)
    logger.info(json.dumps({"ereignis": name, **felder}, ensure_ascii=False, default=str))


def stoerung(logger: logging.Logger, name: str, **felder: Any) -> None:
    """Wie `ereignis`, aber auf der Stufe, die im schwarzen Fenster ankommt.

    Aus der Kanzlei am 13.10.2026: „Akte oeffnen nicht moeglich Vorgang wurde
    abgebrochen interner Fehler 2e2e3bd1." Die Nummer stand da, die Zeile
    dazu nirgends.

    Gemessen: Uvicorn richtet nur seine eigenen Kanaele ein. Unsere Eintraege
    steigen zum Wurzelkanal, und der hat keinen Empfaenger - dann greift
    `logging.lastResort`, und der nimmt erst ab WARNUNG. `ereignis` schreibt
    auf INFO. Die Zeile entstand also und ging nirgendwohin.

    Eine Vorgangsnummer ohne Zeile ist keine Auskunft, sondern eine Zumutung:
    Der Bearbeiter hat etwas in der Hand, womit niemand etwas anfangen kann.
    Deshalb hat die abgefangene Stoerung ihre eigene Stufe.
    """
    _pruefen(felder)
    logger.error(json.dumps({"ereignis": name, **felder}, ensure_ascii=False, default=str))
