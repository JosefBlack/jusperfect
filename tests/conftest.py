"""Was jede Prüfung vorfindet – damit sie hier misst wie in der Kanzlei.

**Die große Testakte wird erzeugt, nicht mitgeliefert.** 880.000 Zeichen
Fülltext gehören nicht in ein Programmpaket; bei fester Saat entsteht jedes
Mal dieselbe Akte. Das ist richtig so – nur fehlte sie deshalb auf einem
frisch ausgecheckten Stand, und das hieß für zwei Prüfungen Verschiedenes:

* ``test_schriftstueckdatum`` las ``akte.json`` und brach mit
  ``FileNotFoundError`` ab. Auf GitHub lief der Prüflauf damit seit dem
  28.09.2026 jedes Mal rot, während er örtlich grün war – weil hier die Akte
  von einem früheren Lauf herumlag.
* ``pruefbogen._ist_routine`` fragt die Akte, welche Bautagebuchtage ein
  besonderes Vorkommnis tragen. Ohne Akte bleibt diese Menge leer und der
  Rauschwert fällt strenger aus. Das ist die ungefährliche Richtung, aber es
  heißt: **Dieselbe Prüfung misst auf zwei Rechnern Verschiedenes.**

Der zweite Punkt ist der schwerere, und er ist dieselbe Form, die dieses
Projekt seit September verfolgt: Eine Probe, die anderswo anders antwortet,
prüft etwas anderes. Deshalb steht die Akte jetzt vor jedem Lauf bereit –
erzeugt in Bruchteilen einer Sekunde, genau wie ``PRUEFBOGEN.bat`` es tut.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkzeug"))

#: Die Akte, die der Prüfbogen misst.
GROSSE_AKTE = WURZEL / "testdaten" / "grosse-akte" / "BA-2026-0044"


@pytest.fixture(scope="session", autouse=True)
def grosse_testakte() -> Path:
    """Die große Testakte bereitstellen, falls sie fehlt."""
    if not (GROSSE_AKTE / "akte.json").is_file():
        import grosse_testakte as vorlage

        vorlage.erzeugen(GROSSE_AKTE)
    return GROSSE_AKTE
