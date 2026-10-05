"""JSON aus einer Modellantwort holen – auch wenn das Modell doch geplaudert hat."""

from __future__ import annotations

import json
import re
from typing import Any


class AusgabeUnbrauchbar(ValueError):
    pass


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def json_extrahieren(text: str) -> dict[str, Any]:
    kandidaten = [m.group(1) for m in _FENCE_RE.finditer(text)]
    kandidaten.append(text)
    anfang, ende = text.find("{"), text.rfind("}")
    if anfang != -1 and ende > anfang:
        kandidaten.append(text[anfang:ende + 1])
    for k in kandidaten:
        try:
            daten = json.loads(k.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(daten, dict):
            return daten
    raise AusgabeUnbrauchbar("Die Antwort des Modells enthält kein JSON-Objekt.")
