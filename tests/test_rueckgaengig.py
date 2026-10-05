"""Rückgängig: nur für Handgriffe, die sich wirklich zurücknehmen lassen.

Ein Rückgängig, das dann doch nicht zurückkann, ist schlimmer als keines - es
verleitet dazu, sorgloser zu klicken. Deshalb hält dieser Test fest, welche
Zusagen die Oberfläche macht und dass sie sie halten kann.

Der Durchgang durch die Oberfläche selbst ist an einem echten Chromium
gemessen (scratchpad/rueck.mjs): Leiste erscheint, Strg+Z stellt das Dokument
wieder her, und im Eingabefeld bleibt Strg+Z dem Text.
"""

from __future__ import annotations

from pathlib import Path

import pytest

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"


@pytest.fixture(scope="module")
def app() -> str:
    return (STATISCH / "app.js").read_text(encoding="utf-8")


def test_die_leiste_gibt_es(app: str) -> None:
    html = (STATISCH / "index.html").read_text(encoding="utf-8")
    for kennung in ('id="rueckgaengig"', 'id="rueckgaengig-text"',
                    'id="rueckgaengig-tun"', 'id="rueckgaengig-zu"'):
        assert kennung in html, kennung
    assert ".rueckgaengig {" in (STATISCH / "styles.css").read_text(encoding="utf-8")


def test_die_leiste_laeuft_nicht_von_selbst_ab(app: str) -> None:
    """Wer danebengegriffen hat, merkt es oft erst beim Blick in die Akte."""
    anfang = app.index("function rueckgaengigAnbieten(")
    ende = app.index("function melden(")
    assert "setTimeout" not in app[anfang:ende]


def test_das_angebot_wird_vor_dem_ausfuehren_zurueckgezogen(app: str) -> None:
    """Sonst holt ein zweiter Klick auf eine langsame Antwort doppelt zurück."""
    anfang = app.index("async function rueckgaengigMachen(")
    ende = app.index("function melden(")
    block = app[anfang:ende]
    assert block.index("rueckgaengigVerbergen()") < block.index("await tun()")


def test_strg_z_laesst_eingabefelder_in_ruhe(app: str) -> None:
    """In einem Feld gehört Strg+Z dem Text, nicht der Akte."""
    stelle = app.index('ev.key.toLowerCase() !== "z"')
    block = app[stelle:stelle + 700]
    assert '"INPUT"' in block and '"TEXTAREA"' in block and "isContentEditable" in block


def test_geschlossene_sitzung_nimmt_das_angebot_mit(app: str) -> None:
    """Ein Rückgängig auf eine geschlossene Sitzung griffe ins Leere."""
    anfang = app.index("async function sitzungSchliessen(")
    ende = app.index("\n}", anfang)
    assert "rueckgaengigVerbergen()" in app[anfang:ende]


def test_beide_zerstoerenden_handgriffe_sind_angeschlossen(app: str) -> None:
    for stelle in ("Verworfen: ", "Aus der Arbeitsakte genommen: "):
        assert f'rueckgaengigAnbieten(`{stelle}' in app or f'`{stelle}' in app, stelle


def test_das_zurueckholen_hat_einen_endpunkt() -> None:
    web = (Path(__file__).resolve().parent.parent / "jusperfect" / "web.py").read_text(encoding="utf-8")
    assert '/api/posteingang/{eintrag_id}/zurueckholen' in web
