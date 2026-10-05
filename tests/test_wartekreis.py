"""Der Kreis, der sich füllt, während die KI arbeitet.

Aus der Kanzlei: „Auch bei der Analyse mache einen Kreis, der sich füllt, neben
dem Wort Analyse, damit der Bearbeiter sieht, dass die KI für die Bearbeitung
Zeit braucht."

Bis dahin wurde der Knopf während der Arbeit nur grau. Eine Aktenanalyse über
ein volles Gedächtnis dauert aber eine halbe Minute und länger, und ein grauer
Knopf heißt in jedem anderen Programm „geht nicht". Der Kreis heißt „es läuft".

Zwei Dinge dürfen dabei nicht verlorengehen, und beide sind hier festgehalten:
Er erscheint erst nach einer kurzen Frist, damit ein Knopf, der nur ein Fenster
öffnet, nicht jedesmal aufblitzt. Und er füllt sich nie ganz von allein - er
bleibt kurz vor dem Rand stehen, bis die Antwort wirklich da ist. Eine Anzeige,
die „fertig" sagt, bevor etwas fertig ist, ist schlimmer als keine.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"


@pytest.fixture(scope="module")
def app() -> str:
    return (STATISCH / "app.js").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def css() -> str:
    return (STATISCH / "styles.css").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def kreis(app: str) -> str:
    return re.search(r"function wartekreis\(knopf\) \{(.*?)\n\}\n", app, re.S).group(1)


class TestAmKnopf:
    def test_jeder_knopf_mit_arbeit_bekommt_ihn(self, app: str) -> None:
        """mitKnopf trägt jede Arbeit, die dauern kann – Analyse eingeschlossen."""
        block = re.search(r"async function mitKnopf\(knopf, arbeit\) \{(.*?)\n\}", app, re.S).group(1)
        assert "wartekreis(knopf)" in block
        assert "if (fertig) fertig();" in block

    def test_die_analyse_geht_ueber_mitKnopf(self, app: str) -> None:
        assert 'b.dataset.aktion === "analyse") mitKnopf(b, analyseStarten)' in app

    def test_er_sitzt_im_knopf_neben_dem_wort(self, kreis: str) -> None:
        """Nicht als eigener Balken irgendwo – dort, wo der Blick beim Drücken ist."""
        assert "knopf.appendChild(kreis)" in kreis


class TestWasErVerspricht:
    def test_er_erscheint_nicht_sofort(self, app: str, kreis: str) -> None:
        assert "const WARTE_VERZUG = 400;" in app
        assert "setTimeout(() => {" in kreis
        assert "WARTE_VERZUG" in kreis

    def test_er_bleibt_vor_dem_rand_stehen(self, app: str, kreis: str) -> None:
        """92 Prozent heißt „es läuft noch" und nie „gleich fertig"."""
        assert "const WARTE_DECKEL = 92;" in app
        assert "Math.min(WARTE_DECKEL," in kreis

    def test_erst_die_antwort_schliesst_ihn(self, kreis: str) -> None:
        assert 'kreis.style.setProperty("--anteil", "100")' in kreis

    def test_er_lernt_aus_der_letzten_dauer(self, app: str) -> None:
        """Der zweite Lauf einer Akte zeigt eine ehrlichere Geschwindigkeit."""
        assert "function warteDauer(" in app and "function warteMerken(" in app
        merken = re.search(r"function warteMerken\(schluessel, sekunden\) \{(.*?)\n\}", app, re.S).group(1)
        assert "sekunden > 1" in merken, "Ein sofort abgewiesener Aufruf ist keine Messung."
        assert "0.6 * warteDauer(schluessel) + 0.4 * sekunden" in merken

    def test_ein_privater_browser_bringt_ihn_nicht_zu_fall(self, app: str) -> None:
        """localStorage wirft in manchen Einstellungen – das darf nichts kosten."""
        dauer = re.search(r"function warteDauer\(schluessel\) \{(.*?)\n\}", app, re.S).group(1)
        assert "try {" in dauer and "catch" in dauer
        assert "return WARTE_VORGABE;" in dauer


class TestAussehen:
    def test_es_ist_ein_ring_kein_kuchen(self, css: str) -> None:
        block = css[css.index(".warte-kreis {"):]
        block = block[:block.index("}")]
        assert "conic-gradient" in block
        assert "mask:" in block

    def test_der_wartende_knopf_wird_nicht_blass(self, css: str) -> None:
        """Er ist gesperrt – aber der Kreis ist das Einzige, was etwas zu sagen hat."""
        assert ".mini.wartet, .knopf.wartet:disabled { opacity: 1;" in css
