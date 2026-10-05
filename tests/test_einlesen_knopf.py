"""Der Weg für die große Akte – und dass die Meldung ihn nennt.

Aus der Kanzlei, nach dem Versuch, die 50-Dokumente-Akte zu analysieren: „gibt
es einen besseren Weg für den Benutzer?"

Es gab ihn schon – das abschnittsweise Einlesen ins Aktengedächtnis –, nur
wusste die Meldung nichts davon und riet stattdessen, Dokumente aus der
Arbeitsakte zu nehmen. Bei einer Akte, die man ganz lesen will, ist das ein Rat
und keine Lösung.

Gemessen an der großen Testakte (882.158 Zeichen, 50 Dokumente): sieben
Portionen, 663 Passagen, nichts offen geblieben, Fundstellen von D1-S1-P1 bis
D50-S1-P13. Im echten Chromium durchgeklickt.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from jusperfect.services.analyse import _zu_gross
from jusperfect.services.passagen import passagen_bilden
from jusperfect.domain.models import Dokument, Seite

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"


@pytest.fixture(scope="module")
def html() -> str:
    return (STATISCH / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def app_js() -> str:
    return (STATISCH / "app.js").read_text(encoding="utf-8")


def _passagen(dokumente: int):
    alle = []
    for nr in range(1, dokumente + 1):
        d = Dokument(id=f"D-{nr:03d}", akte_id="A", titel=f"Schriftsatz {nr}", dateiname=f"{nr}.txt")
        alle += passagen_bilden(nr, d, [Seite(nummer=1, text="Vertrag Kuendigung Frist " * 900)])
    return alle


class TestDieMeldungNenntDenWeg:
    def test_mit_gedaechtnis_steht_der_knopf_darin(self) -> None:
        alle = _passagen(50)
        text = _zu_gross("Aktenanalyse", alle[:9], alle, 160_000, gedaechtnis_aktiv=True)
        assert "Akte einlesen" in text
        assert "Portionen" in text
        assert "im Explorer weniger Dokumente" not in text, "Das ist nicht mehr der beste Rat."

    def test_die_zahl_der_portionen_wird_geschaetzt_genannt(self) -> None:
        alle = _passagen(50)
        text = _zu_gross("Aktenanalyse", alle[:9], alle, 160_000, gedaechtnis_aktiv=True)
        assert re.search(r"etwa \d+ \n?Portionen|etwa \d+ Portionen", text)

    def test_ohne_gedaechtnis_wird_es_nicht_versprochen(self) -> None:
        """Ein Weg, den es in diesem Betrieb nicht gibt, gehört nicht in die Meldung."""
        alle = _passagen(50)
        text = _zu_gross("Aktenanalyse", alle[:9], alle, 160_000, gedaechtnis_aktiv=False)
        assert "der Knopf" not in text
        assert "nicht eingeschaltet" in text, "Dass es den Weg gäbe, darf man trotzdem sagen."

    def test_die_frage_bleibt_in_beiden_faellen_der_sofortige_ausweg(self) -> None:
        alle = _passagen(50)
        for aktiv in (True, False):
            text = _zu_gross("Aktenanalyse", alle[:9], alle, 160_000, gedaechtnis_aktiv=aktiv)
            assert "Frage" in text


class TestDerKnopf:
    def test_er_steht_im_gedaechtnisfenster(self, html: str) -> None:
        fenster = html[html.index('id="gedaechtnis-fenster"'):html.index('id="fenster-belege"')]
        assert 'id="ged-einlesen"' in fenster
        assert "Akte einlesen" in fenster

    def test_er_fragt_vorher_und_nennt_den_preis(self, app_js: str) -> None:
        """Er kostet so viele Modellaufrufe, wie Portionen nötig sind."""
        block = app_js[app_js.index("async function gedaechtnisEinlesen("):app_js.index("function hinweisImThread(")]
        assert "confirm(" in block
        assert "Modellaufruf" in block
        assert block.index("confirm(") < block.index("gedaechtnis/aktualisieren")

    def test_gelesen_wird_portion_fuer_portion(self, app_js: str) -> None:
        """Ein einziger Aufruf über alle Portionen könnte keinen Fortschritt
        melden – er kommt erst am Ende zurück."""
        block = app_js[app_js.index("async function gedaechtnisEinlesen("):app_js.index("function hinweisImThread(")]
        assert "while (!einlesenAbbrechen)" in block
        assert "gedaechtnis/aktualisieren" in block

    def test_das_ergebnis_wird_beziffert(self, app_js: str) -> None:
        block = app_js[app_js.index("async function gedaechtnisEinlesen("):app_js.index("function hinweisImThread(")]
        for zahl in ("lauf.passagen", "lauf.offene_passagen", "lauf.kosten"):
            assert zahl in block, zahl

    def test_ein_unvollstaendiger_lauf_sieht_nicht_aus_wie_ein_ganzer(self, app_js: str) -> None:
        block = app_js[app_js.index("async function gedaechtnisEinlesen("):app_js.index("function hinweisImThread(")]
        assert "Passagen blieben offen" in block
        assert "angehalten" in block


class TestDerFortschritt:
    """Aus der Kanzlei: „wie bei einem Download … fünf von fünfzig Dokumenten
    wurden eingelesen, dann eine ungefähre Dauereinschätzung."
    """

    def test_der_balken_und_die_zahlen_stehen_im_fenster(self, html: str) -> None:
        for kennung in ('id="ged-fortschritt"', 'id="ged-balken"',
                        'id="ged-fortschritt-text"', 'id="ged-fortschritt-dauer"'):
            assert kennung in html, kennung

    def test_gezaehlt_wird_in_dokumenten_und_prozent(self, app_js: str) -> None:
        block = app_js[app_js.index("function einlesenFortschritt("):app_js.index("function dauerText(")]
        assert "von ${gesamt} Dokumenten eingelesen" in block
        assert "${anteil} %" in block

    def test_die_dauer_wird_geschaetzt_und_als_schaetzung_benannt(self, app_js: str) -> None:
        block = app_js[app_js.index("function einlesenFortschritt("):app_js.index("function dauerText(")]
        assert "noch etwa" in block

    def test_die_schaetzung_kommt_aus_dem_bisherigen_durchschnitt(self, app_js: str) -> None:
        """Vor der ersten Portion weiß niemand, wie lange eine dauert."""
        block = app_js[app_js.index("async function gedaechtnisEinlesen("):app_js.index("function hinweisImThread(")]
        assert "verstrichen / schritte" in block

    def test_anhalten_ist_moeglich_und_verliert_nichts(self, app_js: str, html: str) -> None:
        assert 'id="ged-abbrechen"' in html
        assert "einlesenAbbrechen = true" in app_js
        block = app_js[app_js.index("async function gedaechtnisEinlesen("):app_js.index("function hinweisImThread(")]
        assert "Gelesenes bleibt erhalten" in block

    def test_die_laufende_portion_wird_zu_ende_gelesen(self, app_js: str) -> None:
        """Sie ist bezahlt; ihr Ergebnis wegzuwerfen wäre die teuerste Art anzuhalten."""
        stelle = app_js.index('$("ged-abbrechen").addEventListener')
        assert "nach dieser Portion" in app_js[stelle:stelle + 500]

    def test_der_balken_verschwindet_auch_bei_einem_fehler(self, app_js: str) -> None:
        """Sonst bliebe er stehen und behauptete, es liefe noch."""
        block = app_js[app_js.index("async function gedaechtnisEinlesen("):app_js.index("function hinweisImThread(")]
        assert "} finally {" in block
        assert '$("ged-fortschritt").hidden = true;' in block

    def test_die_hinweise_bleiben_stehen(self, app_js: str) -> None:
        """Portionen ohne belegte Aussage sind die Stellen, an denen etwas fehlt –
        eine Meldung, die nach drei Sekunden verschwindet, wäre dafür zu wenig."""
        block = app_js[app_js.index("async function gedaechtnisEinlesen("):app_js.index("function hinweisImThread(")]
        assert "hinweisImThread(hinweis)" in block

    def test_das_fenster_sagt_ob_die_akte_gelesen_ist(self, app_js: str) -> None:
        """Die Dokumentzahl allein verrät es nicht: Ein Auszug liegt im Gedächtnis,
        sobald er eingelesen wurde – im Lebenssachverhalt steht er erst danach."""
        block = app_js[app_js.index("function gedaechtnisFensterZeigen("):app_js.index("// Die grosse Akte")]
        assert "Noch nicht gelesen" in block
        assert "Ganz gelesen" in block
