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


def ereignis(logger: logging.Logger, name: str, **felder: Any) -> None:
    for feld, wert in felder.items():
        if feld.lower() in VERBOTENE_FELDER:
            raise ProtokollVerstoss(f"Feld {feld!r} darf nicht protokolliert werden.")
        if isinstance(wert, str) and len(wert) > MAX_WERT_LAENGE:
            raise ProtokollVerstoss(f"Feld {feld!r} ist zu lang für das Protokoll ({len(wert)} Zeichen).")
        if isinstance(wert, (list, dict)) and len(json.dumps(wert, ensure_ascii=False)) > MAX_WERT_LAENGE:
            raise ProtokollVerstoss(f"Feld {feld!r} ist zu umfangreich für das Protokoll.")
    logger.info(json.dumps({"ereignis": name, **felder}, ensure_ascii=False, default=str))
