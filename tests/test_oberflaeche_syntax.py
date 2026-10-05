"""Lässt sich das JavaScript der Oberfläche überhaupt lesen?

Am 25.09.2026 stand in der Kanzlei stundenlang eine graue Seite. Der Server
lief, der AWS-Zugangstest war grün, die Startdatei zeigte alle Angaben
richtig an – und im Browser stand nichts als „verbinde …".

Die Ursache war ein einziges fehlendes Pluszeichen:

    laeuft("Erster Teil. "
           "Zweiter Teil.");

In Python werden zwei Zeichenketten untereinander zu einer. In JavaScript
ist das ein Syntaxfehler, und ein Syntaxfehler macht die **ganze** Datei
unbrauchbar – nicht nur die eine Zeile. Die Seite lädt, das Gerüst steht,
und kein einziger Knopf tut etwas.

**1176 Prüfungen waren grün, während das Programm im Betrieb nicht startete.**
Genau das Muster aus der Übergabe: Was nicht geprüft wird, ist nicht heil,
egal wie viele Prüfungen daneben laufen. Geprüft wurde, was das JavaScript
sagt – nie, ob es sich lesen lässt.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"
SKRIPTE = sorted(STATISCH.glob("*.js"))


def test_es_gibt_ueberhaupt_skripte() -> None:
    """Sonst liefe die Prüfung darunter ins Leere und wäre still grün."""
    assert SKRIPTE, f"Keine .js-Datei in {STATISCH}."


@pytest.mark.parametrize("datei", SKRIPTE, ids=lambda d: d.name)
def test_das_skript_laesst_sich_lesen(datei: Path) -> None:
    """Der eigentliche Fang: ein Parser über die ganze Datei."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node ist auf diesem Rechner nicht vorhanden")
    ergebnis = subprocess.run([node, "--check", str(datei)],
                              capture_output=True, text=True)
    assert ergebnis.returncode == 0, \
        f"{datei.name} hat einen Syntaxfehler:\n{ergebnis.stderr}"


#: Eine Zeichenkette, die eine Zeile beendet, und darunter gleich die
#: naechste - ohne + dazwischen. In Python eine Verkettung, in JavaScript
#: ein Fehler.
_KLEBENDE_TEXTE = re.compile(
    r'"[^"\n]*"[ \t]*\r?\n[ \t]*"', re.MULTILINE)


@pytest.mark.parametrize("datei", SKRIPTE, ids=lambda d: d.name)
def test_zwei_zeichenketten_untereinander_brauchen_ein_plus(datei: Path) -> None:
    """Derselbe Fang ohne node - dieser Griff sitzt zu locker, um sich auf
    ein Werkzeug zu verlassen, das auf dem Kanzleirechner fehlen kann."""
    text = datei.read_text(encoding="utf-8")
    treffer = _KLEBENDE_TEXTE.search(text)
    if treffer:
        zeile = text[:treffer.start()].count("\n") + 1
        raise AssertionError(
            f"{datei.name}, Zeile {zeile}: Zwei Zeichenketten untereinander "
            "ohne +. In Python wäre das eine Verkettung, in JavaScript ist es "
            "ein Syntaxfehler - und der legt die ganze Datei lahm."
        )


# ---------------------------------------------------------------------------
# Siebzehn Zeilen sind keine Auskunft, sondern eine Wand
#
# Aus der Kanzlei am 25.09.2026: "auch die fehler meldung geht jetzt nicht
# mehr weg und blende sie nur ein". Beim Oeffnen einer echten Akte standen
# siebzehn Zeilen mit demselben Satz auf der Arbeitsflaeche - einmal je
# gescanntem Dokument. Die Bilanz darueber sagte schon alles.
# ---------------------------------------------------------------------------


def test_die_einzelheiten_stehen_zugeklappt() -> None:
    html = (STATISCH / "index.html").read_text(encoding="utf-8")
    assert '<details id="uebernahme-mehr"' in html, \
        "Die Einzelheiten gehoeren in einen Bereich, der sich zuklappen laesst."
    js = (STATISCH / "app.js").read_text(encoding="utf-8")
    assert "mehr.open = false" in js, \
        "Zugeklappt ist der Anfangszustand, nicht der, den der Browser sich merkt."


def test_die_einzelheiten_bleiben_erreichbar() -> None:
    """Wer wissen will, WELCHES Dokument fehlt, braucht sie. Zuklappen heisst
    verstecken, nicht wegwerfen."""
    js = (STATISCH / "app.js").read_text(encoding="utf-8")
    assert "uebernahme-liste" in js
    assert "Einzelheiten dazu" in js, \
        "Der Aufklapper muss sagen, was darunter liegt, und wie viel."


def test_ohne_einzelheiten_gibt_es_keinen_aufklapper() -> None:
    """Ein leerer Aufklapper waere ein Versprechen ohne Inhalt."""
    js = (STATISCH / "app.js").read_text(encoding="utf-8")
    assert "mehr.hidden = einzeln.length === 0" in js
