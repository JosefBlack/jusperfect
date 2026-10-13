"""Die Fensterknöpfe stehen auf der Seite, auf der ihr Fenster aufgeht.

Aus der Kanzlei: „dass die Auswahlbuttons in der Mitte waren und sich rechts
oder links Fenster öffneten. Dieses wäre noch zu verbessern."

Sie standen alle vier in einer Reihe in der Mitte der Arbeitsfläche. Einer
schaltete die linke Spalte, drei die rechte – und nichts sagte, welcher welche.
Wer „Belege" drückte, sah links nach.

Jetzt steht der Knopf dort, wo etwas geschieht: „‹ Dokumente" am linken Rand der
Leiste, unmittelbar neben der Dokumentspalte; „Chronologie ›", „Gedächtnis ›"
und „Belege ›" am rechten, unmittelbar neben der rechten Spalte. Der Pfeil sagt
es noch einmal.

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
def leiste() -> str:
    t = HTML.read_text(encoding="utf-8")
    return t[t.index('<div class="aktionen">'):t.index('<div id="thread"')]


def _gruppe(leiste: str, seite: str) -> str:
    anfang = leiste.index(f'<span class="fenster-knoepfe {seite}">')
    return leiste[anfang:leiste.index("</span>", anfang)]


def test_links_schaltet_nur_die_linke_spalte(leiste: str) -> None:
    links = _gruppe(leiste, "links")
    assert 'data-fenster="dokument"' in links
    for rechts in ("chronologie", "gedaechtnis", "belege"):
        assert f'data-fenster="{rechts}"' not in links, rechts


def test_rechts_schaltet_nur_die_rechte_spalte(leiste: str) -> None:
    rechts = _gruppe(leiste, "rechts")
    for fenster in ("chronologie", "gedaechtnis", "belege"):
        assert f'data-fenster="{fenster}"' in rechts, fenster
    assert 'data-fenster="dokument"' not in rechts


def test_die_reihenfolge_im_quelltext_ist_die_reihenfolge_im_bild(leiste: str) -> None:
    """Sonst hilft die beste Ausrichtung nichts.

    Seit dem 13.10.2026 stehen in dieser Leiste nur noch die Fensterknoepfe:
    links der fuer die Dokumente, rechts die drei fuer die rechte Spalte. Die
    Arbeitsknoepfe sind in die rechte Spalte gewandert. Aus der Kanzlei: "Der
    Chat steht im Vordergrund. Die Funktionen sollen waehlbar sein, aber zum
    rechten Fenster gehoeren."
    """
    assert leiste.index('fenster-knoepfe links') < leiste.index('fenster-knoepfe rechts')
    assert "arbeitsknoepfe" not in leiste, "Die Funktionen gehoeren nicht mehr hierher."


def test_der_pfeil_zeigt_zur_spalte(leiste: str) -> None:
    assert "‹ Dokumente" in leiste
    for fenster in ("Chronologie ›", "Gedächtnis ›", "Belege ›"):
        assert fenster in leiste, fenster


def test_jedes_fenster_hat_genau_einen_knopf(leiste: str) -> None:
    """Zwei Knöpfe für dasselbe Fenster wären schlimmer als keiner."""
    for fenster in ("dokument", "chronologie", "gedaechtnis", "belege"):
        assert len(re.findall(f'data-fenster="{fenster}"', leiste)) == 1, fenster


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
