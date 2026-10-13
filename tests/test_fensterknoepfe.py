"""Jeder Fensterknopf steht bei dem Fenster, das er schaltet.

Aus der Kanzlei: „dass die Auswahlbuttons in der Mitte waren und sich rechts
oder links Fenster öffneten. Dieses wäre noch zu verbessern."

Sie standen alle vier in einer Reihe in der Mitte der Arbeitsfläche. Einer
schaltete die linke Spalte, drei die rechte – und nichts sagte, welcher welche.
Wer „Belege" drückte, sah links nach.

Erster Schritt: Der Knopf für die Dokumente an den linken Rand der Leiste, die
drei anderen an den rechten, jeweils mit einem Pfeil zur Spalte hin.

**Zweiter Schritt, 13.10.2026**, aus der Kanzlei: „Knöpfe Chronologie,
Gedächtnis und Belege nach rechts verschieben, sonst verwirrend." Der Rand der
Chatleiste reichte nicht. Die drei stehen jetzt IN der rechten Spalte, in
derselben Leiste wie Analyse und Entwurf – also dort, wo sie wirken. Der Pfeil
ist damit entbehrlich geworden und weg: Er zeigte auf die Spalte, in der der
Knopf nun selbst steht.

Der Knopf für die Dokumente bleibt in der Chatleiste. Die linke Spalte hat
keine Leiste, die stehen bliebe, wenn sie zugeht; ohne ihn käme man an ein
zugeklapptes Dokumentenfenster nicht mehr heran.

Geprüft wird die Quelle. Die Darstellung selbst ist in echtem Chromium bei 1024
und 1280 px gemessen: Die Gruppen stehen in der richtigen Reihenfolge, und die
Leiste läuft in keiner der beiden Breiten über.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

HTML = Path(__file__).resolve().parent.parent / "jusperfect" / "static" / "index.html"
CSS = Path(__file__).resolve().parent.parent / "jusperfect" / "static" / "styles.css"


@pytest.fixture(scope="module")
def quelle() -> str:
    return HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def leiste(quelle: str) -> str:
    """Die Kopfzeile des Chats."""
    return quelle[quelle.index('<div class="aktionen">'):quelle.index('<div id="thread"')]


@pytest.fixture(scope="module")
def rechte_leiste(quelle: str) -> str:
    """Die Leiste der rechten Spalte - sie bleibt stehen, wenn alles zu ist."""
    anfang = quelle.index('<div class="rechts-aktionen">')
    return quelle[anfang:quelle.index("<section", anfang)]


def test_die_chatleiste_schaltet_nur_die_linke_spalte(leiste: str) -> None:
    assert 'data-fenster="dokument"' in leiste
    for rechts in ("chronologie", "gedaechtnis", "belege"):
        assert f'data-fenster="{rechts}"' not in leiste, rechts


def test_rechts_schaltet_nur_die_rechte_spalte(rechte_leiste: str) -> None:
    """„Knoepfe Chronologie, Gedaechtnis und Belege nach rechts verschieben."""
    for fenster in ("chronologie", "gedaechtnis", "belege"):
        assert f'data-fenster="{fenster}"' in rechte_leiste, fenster
    assert 'data-fenster="dokument"' not in rechte_leiste


def test_die_drei_stehen_in_der_leiste_die_stehen_bleibt(quelle: str) -> None:
    """Nicht in einem der Fenster, die sie schalten - sonst waeren sie weg,
    sobald alle drei zu sind. Ein Knopf, der mit dem Fenster verschwindet, in
    dem er steht, ist eine Falle."""
    anfang = quelle.index('<div class="rechts-aktionen">')
    erstes_fenster = quelle.index("<section", anfang)
    for fenster in ("chronologie", "gedaechtnis", "belege"):
        assert quelle.index(f'data-fenster="{fenster}"') < erstes_fenster, fenster


def test_die_reihenfolge_im_quelltext_ist_die_reihenfolge_im_bild(leiste: str) -> None:
    """Sonst hilft die beste Ausrichtung nichts.

    In der Chatleiste steht seit dem 13.10.2026 nur noch der Knopf fuer die
    Dokumente. Die Arbeitsknoepfe und die drei Fensterknoepfe der rechten
    Spalte sind dorthin gewandert, wo sie wirken.
    """
    assert "fenster-knoepfe links" in leiste
    assert "arbeitsknoepfe" not in leiste, "Die Funktionen gehoeren nicht mehr hierher."
    assert "fenster-knoepfe rechts" not in leiste, "Die drei gehoeren nicht mehr hierher."


def test_der_pfeil_zeigt_zur_spalte(leiste: str, rechte_leiste: str) -> None:
    """Nur noch links: Die drei anderen stehen in der Spalte, auf die der
    Pfeil zeigte - er sagte dort nichts mehr und stand nur im Weg."""
    assert "‹ Dokumente" in leiste
    for fenster in ("Chronologie", "Gedächtnis", "Belege"):
        assert f">{fenster}<" in rechte_leiste, fenster
        assert f"{fenster} ›" not in rechte_leiste, fenster


def test_jedes_fenster_hat_genau_einen_knopf(quelle: str) -> None:
    """Zwei Knöpfe für dasselbe Fenster wären schlimmer als keiner."""
    for fenster in ("dokument", "chronologie", "gedaechtnis", "belege"):
        assert len(re.findall(f'data-fenster="{fenster}"', quelle)) == 1, fenster


def test_die_gruppen_brechen_nicht_untereinander_um() -> None:
    """Mit flex-wrap rutschte die mittlere Gruppe in eine zweite Zeile.

    Dann standen „links" und „rechts" nebeneinander – gemessen bei 1280 px:
    links 389 px, rechts 485 px, die Arbeit darunter bei 692 px. Genau die
    Zuordnung, um die es hier geht, war damit dahin. Umbrechen darf innerhalb
    einer Gruppe, nicht zwischen ihnen.
    """
    css = CSS.read_text(encoding="utf-8")
    abschnitt = css[css.index(".aktionen {"):]
    abschnitt = abschnitt[:abschnitt.index("}")]
    assert "flex-wrap: nowrap" in abschnitt
