"""Modellantworten dürfen keine Rauten und Sternchen zeigen.

Sprachmodelle schreiben Markdown, ob man sie darum bittet oder nicht. Die
Oberfläche setzte den Text bisher roh - in der Kanzlei stand dann „## Ergebnis"
und „**04.05.2026**" mitten im Schriftsatz.

Geprüft wird die Quelle, nicht die Darstellung im Browser: Die Darstellung
selbst ist in scratchpad/satz.mjs an einem echten Chromium gemessen worden.
Hier bleibt festgehalten, was dabei nicht verlorengehen darf.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parent.parent / "jusperfect" / "static" / "app.js"
CSS = Path(__file__).resolve().parent.parent / "jusperfect" / "static" / "styles.css"


@pytest.fixture(scope="module")
def app() -> str:
    return APP.read_text(encoding="utf-8")


def test_es_gibt_einen_textsatz(app: str) -> None:
    assert "function antworttext(" in app
    assert "function inlineMitBelegen(" in app


@pytest.mark.parametrize("muster", ["UEBERSCHRIFT", "AUFZAEHLUNG", "NUMMERIERT", "TRENNLINIE", "INLINE"])
def test_die_muster_stehen_fest(app: str, muster: str) -> None:
    assert re.search(rf"^const {muster} = /", app, re.M)


def test_jede_modellantwort_geht_durch_den_satz(app: str) -> None:
    """Wer eine Antwort künftig ohne Satz einsetzt, lässt die Sternchen zurück.

    Wohin gesetzt wird, ist gleichgültig: Seit dem 13.10.2026 setzt das
    Vorschaufenster den Entwurf in einen eigenen Block statt in die
    Chatkarte. Geprüft wird, DASS der Text durch ``antworttext`` geht - nicht,
    in welches Element.
    """
    for stelle in ("antwort.text", "qa.antwort", "g.lebenssachverhalt", "e.text",
                   't.kernaussage || ""', "entwurfVorschautext"):
        assert re.search(rf"antworttext\([A-Za-z]+, {re.escape(stelle)}\)", app), stelle


def test_kein_innerhtml_im_satz(app: str) -> None:
    """Der Text kommt mittelbar aus der Akte und darf nie Markup werden."""
    anfang = app.index("function inlineMitBelegen(")
    ende = app.index("function fusszeile(")
    assert "innerHTML" not in app[anfang:ende]


def test_hinter_der_letzten_fundstelle_kein_leerzeichen(app: str) -> None:
    """Sonst steht im Satz „… zu D-202-S1-P1 ." - der Punkt rutscht ab."""
    anfang = app.index("function textMitBelegen(")
    ende = app.index("function fusszeile(")
    block = app[anfang:ende]
    assert "i < kennungen.length - 1" in block
    assert 'ziel.append(chip, document.createTextNode(" "))' not in block


def test_die_formatvorlagen_gibt_es(app: str) -> None:
    css = CSS.read_text(encoding="utf-8")
    for klasse in (".abschnitt", ".aufzaehlung"):
        assert f".karte-c .inhalt {klasse}" in css, klasse
    assert ".karte-c .inhalt code" in css


def test_ueberschriften_bleiben_klein(app: str) -> None:
    """h1 mitten im Gespräch verschöbe die Gliederung der Seite."""
    anfang = app.index("function antworttext(")
    ende = app.index("function textMitBelegen(")
    block = app[anfang:ende]
    assert 'createElement("h4")' in block
    for gross in ('createElement("h1")', 'createElement("h2")', 'createElement("h3")'):
        assert gross not in block
