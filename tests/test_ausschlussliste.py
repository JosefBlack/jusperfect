"""Was nicht von selbst in die Arbeitsakte kommt – und damit nicht ins Gedächtnis.

Aus der Kanzlei am 05.10.2026: „Grundsätzlich gehört die Rechnung nicht ins
Aktengedächtnis und Korrespondenz mit der RSV."

Zwei Dinge geschehen hier bewusst **nicht**:

* **Es wird nichts weggelassen.** Das Dokument steht im Fenster, nur ohne
  Haken, mit dem Grund daneben. Ein Programm, das Akteninhalt heimlich
  auslässt, ist schlimmer als eines, das zu viel mitnimmt — was fehlt, fällt
  niemandem auf.
* **Es wird nicht gedeutet.** Geprüft wird der **Titel**, nicht der Inhalt.
  Eine Rechnung, die „Schreiben vom 14.03." heißt, geht durch. Eine Hilfe,
  keine Gewähr.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"
GRUND = {"JUSPERFECT_ANBIETER": "demo", "JUSPERFECT_BETRIEBSART": "lokal",
         "JUSPERFECT_JURNODES_ADAPTER": "fixture"}


@pytest.fixture(scope="module")
def app() -> str:
    return (STATISCH / "app.js").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def css() -> str:
    return (STATISCH / "styles.css").read_text(encoding="utf-8")


class TestDieListe:
    def test_sie_nennt_rechnung_und_rsv(self) -> None:
        from jusperfect.config import Einstellungen

        liste = Einstellungen.aus_umgebung(GRUND).nicht_vorwaehlen
        assert "Rechnung" in liste
        assert "RSV" in liste

    def test_sie_laesst_sich_ersetzen(self) -> None:
        from jusperfect.config import Einstellungen

        e = Einstellungen.aus_umgebung({**GRUND,
                                        "JUSPERFECT_NICHT_VORWAEHLEN": " Rechnung , RSV "})
        assert e.nicht_vorwaehlen == ("Rechnung", "RSV")

    def test_ein_leerer_wert_schaltet_ab(self) -> None:
        """Leer ist eine Angabe, nicht das Fehlen einer Angabe."""
        from jusperfect.config import Einstellungen

        e = Einstellungen.aus_umgebung({**GRUND, "JUSPERFECT_NICHT_VORWAEHLEN": ""})
        assert e.nicht_vorwaehlen == ()

    def test_ohne_angabe_gilt_die_vorgabe(self) -> None:
        from jusperfect.config import Einstellungen

        assert Einstellungen.aus_umgebung(GRUND).nicht_vorwaehlen == Einstellungen.nicht_vorwaehlen

    def test_sie_geht_an_die_oberflaeche(self) -> None:
        """Als Liste, nicht als fertiges Ergebnis – der Anwender soll sehen,
        welches Wort gegriffen hat."""
        web = (Path(__file__).resolve().parent.parent / "jusperfect" / "web.py"
               ).read_text(encoding="utf-8")
        assert '"nicht_vorwaehlen": list(e.nicht_vorwaehlen)' in web


class TestDiePruefung:
    def test_sie_sieht_nur_den_titel_an(self, app: str) -> None:
        block = re.search(r"function nichtVorwaehlenGrund\(d\) \{(.*?)\n\}", app, re.S).group(1)
        assert "d.titel" in block
        assert "d.text" not in block

    def test_gross_und_kleinschreibung_schadet_nicht(self, app: str) -> None:
        block = re.search(r"function nichtVorwaehlenGrund\(d\) \{(.*?)\n\}", app, re.S).group(1)
        assert block.count("toLowerCase()") == 2

    def test_sie_gibt_das_wort_zurueck_nicht_nur_ja(self, app: str) -> None:
        """Damit auf der Zeile steht, WELCHES Wort gegriffen hat."""
        block = re.search(r"function nichtVorwaehlenGrund\(d\) \{(.*?)\n\}", app, re.S).group(1)
        assert "return wort;" in block


class TestNichtsVerschwindetStillschweigend:
    def test_das_dokument_steht_weiter_im_fenster(self, app: str) -> None:
        """Gefiltert wird die Vorauswahl, nicht die Liste."""
        block = re.search(r"function explorerSichtbar\(\) \{(.*?)\n\}", app, re.S).group(1)
        assert "nichtVorwaehlen" not in block

    def test_der_grund_steht_daneben(self, app: str) -> None:
        block = re.search(r"function explorerEintrag\(d, drin\) \{(.*?)\n\}", app, re.S).group(1)
        assert "nicht vorgewählt: ${grund}" in block

    def test_und_es_sieht_anders_aus(self, css: str) -> None:
        assert ".explorer-eintrag.nicht-vorgewaehlt" in css

    def test_wer_anhakt_sieht_den_hinweis_nicht_mehr(self, app: str) -> None:
        """Ein Dokument, das drin ist, ist drin – der Grund ist dann erledigt."""
        block = re.search(r"function explorerEintrag\(d, drin\) \{(.*?)\n\}", app, re.S).group(1)
        assert "grund && !drin" in block


class TestAlleAnhaken:
    def test_es_laesst_die_ausgeschlossenen_aus(self, app: str) -> None:
        block = re.search(r'\$\("alle-rein"\)\.addEventListener\("click", \(\) => \{(.*?)\n  \}\);',
                          app, re.S).group(1)
        assert "!nichtVorwaehlenGrund(d)" in block

    def test_ein_zweiter_klick_holt_sie_doch(self, app: str) -> None:
        """Sonst wäre die Liste eine Sperre statt einer Vorauswahl."""
        block = re.search(r'\$\("alle-rein"\)\.addEventListener\("click", \(\) => \{(.*?)\n  \}\);',
                          app, re.S).group(1)
        assert "offen.every((d) => explorer.gewaehlt.has(d.id)) ? sichtbar : offen" in block

    def test_und_der_erste_klick_sagt_es(self, app: str) -> None:
        block = re.search(r'\$\("alle-rein"\)\.addEventListener\("click", \(\) => \{(.*?)\n  \}\);',
                          app, re.S).group(1)
        assert "nicht vorgewählt" in block
        assert "noch einmal klicken" in block


class TestAuchAmSchmalenFenster:
    """Der Fund aus dem Browserlauf vom 05.10.2026.

    Bei 430 Pixel Breite war „nicht vorgewählt: Rechnung" länger als die
    übrige Beschriftung, hat die ganze Zeile eingenommen und den Dokument‑
    titel auf **null Breite** gedrückt. Das Dokument stand ohne Namen da –
    also genau das stillschweigende Verschwinden, das diese Liste nicht tun
    soll. Gemessen am geöffneten Fenster, nicht geschätzt.
    """

    def test_der_titel_hat_eine_untergrenze(self, css: str) -> None:
        assert ".explorer-wahl .explorer-name { min-width:" in css

    def test_und_die_beschriftung_rutscht_darunter(self, css: str) -> None:
        schmal = css.split("@media (max-width: 560px) {")[-1]
        assert "flex-wrap: wrap" in schmal
        assert ".explorer-wahl .meta" in schmal
