"""Die Kopfzeile: Was sie zeigt, wenn der Platz nicht für alles reicht.

Aus der Kanzlei, notiert am 16.09.2026: „Die Kopfzeile läuft bei 1024 px über,
wenn die Modellkennung lang ist." Beim Nachsehen in echtem Chromium war es
etwas anderes und Schlimmeres: Sie lief nicht über – das Flexbox-Layout hielt
sie zusammen –, sie **quetschte die Aktenbezeichnung**. Gemessen bei 1024 px
mit langer Bezeichnung:

    vorher   Aktenbezeichnung  34 px breit  („44…")
    nachher  Aktenbezeichnung 187 px breit  („44/26 BA · Kettenbach ./. …")

Die Kennung `eu.anthropic.claude-opus-4-6-v1` nahm den Platz, den das
Aktenzeichen braucht. Und sie sagt einer Anwältin nichts: „-20251001-v1:0" ist
eine Angabe für die Einrichtung, nicht für den Arbeitstag. Die genauen
Kennungen zeigt der Selbsttest.

Hier wird die Quelle geprüft. Die Darstellung selbst ist in echtem Chromium bei
1024, 1280 und 1920 px gemessen und fotografiert worden.
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


@pytest.fixture(scope="module")
def css() -> str:
    return CSS.read_text(encoding="utf-8")


def test_die_kopfzeile_zeigt_die_verkuerzte_kennung(app: str) -> None:
    assert "kurzeKennung(s.modell)" in app


def test_die_vollstaendige_kennung_bleibt_im_tooltip(app: str) -> None:
    """Sie darf nicht verschwinden – bei einer Abweisung braucht man sie genau."""
    assert re.search(r'\$\("status"\)\.title\s*=.*s\.modell', app)


def test_der_modellname_weicht_und_nicht_die_aktenleiste(css: str) -> None:
    """Zweite Absicherung: Wird es doch zu eng, kürzt sich der Status."""
    abschnitt = css[css.index(".status {"):]
    abschnitt = abschnitt[:abschnitt.index("}")]
    for regel in ("min-width: 0", "overflow: hidden", "text-overflow: ellipsis"):
        assert regel in abschnitt, regel


def test_die_verkuerzung_trifft_die_kennungen_des_kontos() -> None:
    """Nachgerechnet gegen die fünf Kennungen, die das Konto wirklich führt.

    Die Kennungen folgen keinem Muster – Opus 4.6 trägt „-v1" ohne Datum,
    Haiku 4.5 Datum und Fassung, Sonnet 4.6 keines von beidem. Die Verkürzung
    muss alle drei Bauarten treffen.
    """
    fuer = _verkuerzung()
    assert fuer("eu.anthropic.claude-opus-4-6-v1") == "Opus 4.6"
    assert fuer("eu.anthropic.claude-opus-4-5-20251101-v1:0") == "Opus 4.5"
    assert fuer("eu.anthropic.claude-sonnet-4-6") == "Sonnet 4.6"
    assert fuer("eu.anthropic.claude-sonnet-4-5-20250929-v1:0") == "Sonnet 4.5"
    assert fuer("eu.anthropic.claude-haiku-4-5-20251001-v1:0") == "Haiku 4.5"


def test_was_nicht_passt_bleibt_unveraendert() -> None:
    """Eine falsch verkürzte Kennung wäre schlimmer als eine lange.

    Wer eine ARN oder ein Modell eines anderen Anbieters eingetragen hat, soll
    genau das lesen – und nicht etwas, das danebenliegt.
    """
    fuer = _verkuerzung()
    arn = "arn:aws:bedrock:eu-central-1:1:inference-profile/eigen"
    assert fuer(arn) == arn
    assert fuer("meta.llama-3") == "meta.llama-3"
    assert fuer("") == ""


def _verkuerzung():
    """Die Funktion aus app.js, hier in Python nachgebaut – gleiche Regel.

    Kein Node im Prüflauf: Die Regel ist ein Ausdruck, und den kann Python
    ebenso auswerten. Dass beide dasselbe tun, hält
    `test_die_regel_ist_dieselbe_wie_in_app_js` fest.
    """
    muster = re.compile(r"^(?:eu\.|us\.)?anthropic\.claude-([a-z]+)-(\d+)-(\d+)\b")

    def kurz(kennung: str) -> str:
        roh = str(kennung or "")
        treffer = muster.match(roh)
        if not treffer:
            return roh
        name, gross, klein = treffer.groups()
        return f"{name.capitalize()} {gross}.{klein}"

    return kurz


def test_die_regel_ist_dieselbe_wie_in_app_js(app: str) -> None:
    """Sonst messen der Test und das Programm Verschiedenes."""
    assert r"^(?:eu\.|us\.)?anthropic\.claude-([a-z]+)-(\d+)-(\d+)\b" in app
