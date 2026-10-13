"""Die eine Datei, die jusperfect in einer Akte führen darf.

Aus der Kanzlei: „Ich möchte das Gedächtnis in der Akte haben. Ich möchte nicht
lange nach dem Gedächtnis suchen müssen."

Beide Adapter, die Akten als Ordner sehen – das eingebundene Laufwerk und der
Testaktenordner –, legen sie auf dieselbe Weise ab. Deshalb steht die Logik
hier einmal und nicht zweimal.

Der Dateiname steht fest (``GEDAECHTNIS_DATEI``) und lässt sich von außen nicht
beeinflussen. Das ist der Kern der Zusage: Über diesen Weg kann genau eine
Datei entstehen, und keine andere. Wer einen Vermerk in die Akte schreiben
will, geht weiterhin über ``vermerk_schreiben`` und braucht eine Freigabe.
"""

from __future__ import annotations

import os
from pathlib import Path

from jusperfect.jurnodes.base import GEDAECHTNIS_DATEI, JurNodesFehler


def _pfad(ordner: Path) -> Path:
    return ordner / GEDAECHTNIS_DATEI


def lesen(ordner: Path) -> bytes | None:
    pfad = _pfad(ordner)
    if not pfad.is_file():
        return None
    try:
        return pfad.read_bytes()
    except Exception as e:
        raise JurNodesFehler(
            f"Das Gedächtnis in der Akte ist nicht lesbar ({type(e).__name__})."
        ) from e


def ablegen(ordner: Path, rohdaten: bytes, schreibbar: bool) -> None:
    # Stillschweigen waere hier gefaehrlich: Der Nutzer bekaeme gemeldet, sein
    # Aktengedaechtnis sei gesichert, und es waere nichts geschehen. Bei einem
    # Vermerk faellt das auf - beim Gedaechtnis erst Wochen spaeter.
    if not schreibbar:
        raise JurNodesFehler(
            "Dieser Aktenzugang ist schreibgeschützt; das Gedächtnis kann "
            "nicht in der Akte abgelegt werden."
        )
    pfad = _pfad(ordner)
    temporaer = pfad.with_name(pfad.name + ".tmp")
    try:
        # Erst vollstaendig danebenschreiben, dann umbenennen. Bricht der
        # Vorgang ab - Netzlaufwerk weg, Rechner aus -, bleibt der bisherige
        # Stand stehen statt einer halben Datei.
        temporaer.write_bytes(rohdaten)
        os.replace(temporaer, pfad)
    except Exception as e:
        try:
            temporaer.unlink(missing_ok=True)
        except OSError:
            pass
        raise JurNodesFehler(
            f"Das Gedächtnis konnte nicht in der Akte abgelegt werden ({type(e).__name__})."
        ) from e


def loeschen(ordner: Path, schreibbar: bool) -> None:
    if not schreibbar:
        raise JurNodesFehler(
            "Dieser Aktenzugang ist schreibgeschützt; das Gedächtnis kann "
            "nicht aus der Akte entfernt werden."
        )
    try:
        _pfad(ordner).unlink(missing_ok=True)
    except Exception as e:
        raise JurNodesFehler(
            f"Das Gedächtnis konnte nicht aus der Akte entfernt werden ({type(e).__name__})."
        ) from e
