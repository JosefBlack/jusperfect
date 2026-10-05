"""Die Rückfrage vor dem Schließen.

Aus der Kanzlei am 05.10.2026: „Können wir noch einbauen, dass ein
versehentliches Schließen ausgeschlossen ist, wenn der Tab angesprochen wird,
Rückfrage, wollen Sie das Fenster wirklich schließen" – und nachgeschoben:
„Dieses gilt insbesondere bei laufenden Vorgängen."

Zwei Dinge gehen dabei **nicht**, und sie gehören hier festgehalten, damit sie
nicht später als Fehler gesucht werden:

* **Den Wortlaut bestimmt der Browser.** Jeder Versuch, einen eigenen Satz zu
  setzen, wird seit Jahren von allen Browsern verworfen. Es erscheint ihre
  Standardfrage, nicht unsere.
* **Sie erscheint erst nach einer Geste.** Ein Fenster, in dem niemand geklickt
  oder getippt hat, geht ohne Nachfrage zu. Beides ist Absicht der Browser
  gegen Seiten, die sich nicht schließen lassen.

Deshalb wird nicht immer gefragt, sondern nur, wenn wirklich etwas auf dem
Spiel steht. Eine Rückfrage, die bei jedem Schließen kommt, wird nach einer
Woche weggeklickt, ohne gelesen zu werden – und schützt dann genau dann nicht
mehr, wenn es darauf ankommt.
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
def spiel(app: str) -> str:
    return re.search(r"function etwasStehtAufDemSpiel\(\) \{(.*?)\n\}", app, re.S).group(1)


class TestWannGefragtWird:
    def test_waehrend_etwas_laeuft(self, spiel: str) -> None:
        """Der ausdrückliche Wunsch: „insbesondere bei laufenden Vorgängen"."""
        assert "laufendeArbeiten > 0 || liestGerade" in spiel

    def test_und_solange_eine_akte_offen_ist(self, spiel: str) -> None:
        assert "return !!(sitzung && sitzung.sitzung);" in spiel

    def test_der_handler_haengt_an_beforeunload(self, app: str) -> None:
        block = re.search(r'window\.addEventListener\("beforeunload", \(ereignis\) => \{(.*?)\n\}\);',
                          app, re.S).group(1)
        assert "if (!etwasStehtAufDemSpiel()) return;" in block
        assert "ereignis.preventDefault();" in block
        # Aeltere Browser verlangen zusaetzlich returnValue.
        assert 'ereignis.returnValue = "";' in block


class TestWannNichtGefragtWird:
    def test_nicht_auf_der_leeren_startseite(self, spiel: str) -> None:
        """Ohne offene Akte ist nichts zu verlieren."""
        assert "return !!(sitzung && sitzung.sitzung);" in spiel

    def test_nicht_im_nebenfenster(self, spiel: str) -> None:
        """Ein Spiegel hält nichts – dort wäre die Frage eine Unwahrheit."""
        assert "if (nebenfenster) return false;" in spiel
        assert spiel.index("nebenfenster") < spiel.index("laufendeArbeiten")

    def test_nicht_beim_gewollten_weggang(self, spiel: str, app: str) -> None:
        """An- und Abmeldung führen über eine fremde Adresse.

        Eine Rückfrage dort wäre eine Warnung vor dem, was der Anwender gerade
        selbst angeklickt hat.
        """
        assert "if (gewolltesVerlassen) return false;" in spiel
        assert app.count("gewolltesVerlassen = true;") == 2


class TestDerZaehler:
    def test_er_sitzt_an_der_einen_stelle_durch_die_alles_geht(self, app: str) -> None:
        """Analyse, Entwurf, Einlesen, Übernehmen – alle laufen über mitKnopf.

        Ein eigener Zähler je Vorgang liefe irgendwann auseinander; genau
        solche Doppelungen hat dieses Projekt am 28.09.2026 schon einmal
        gekostet.
        """
        block = re.search(r"async function mitKnopf\(knopf, arbeit\) \{(.*?)\n\}", app, re.S).group(1)
        assert "laufendeArbeiten++" in block

    def test_er_wird_auch_bei_einem_fehler_zurueckgezaehlt(self, app: str) -> None:
        """Sonst bliebe die Rückfrage für den Rest des Tages stehen."""
        block = re.search(r"async function mitKnopf\(knopf, arbeit\) \{(.*?)\n\}", app, re.S).group(1)
        nach = block[block.index("finally"):]
        assert "laufendeArbeiten = Math.max(0, laufendeArbeiten - 1);" in nach

    def test_und_faellt_nie_unter_null(self, app: str) -> None:
        assert "Math.max(0, laufendeArbeiten - 1)" in app


class TestWasNichtVersprochenWird:
    def test_kein_eigener_wortlaut(self, app: str) -> None:
        """Ein gesetzter Text wird von jedem Browser verworfen.

        Stünde hier einer, läse man ihn im Quelltext und hielte ihn für das,
        was der Anwender sieht – und suchte dann den Fehler an der falschen
        Stelle.
        """
        block = re.search(r'window\.addEventListener\("beforeunload", \(ereignis\) => \{(.*?)\n\}\);',
                          app, re.S).group(1)
        assert 'returnValue = ""' in block
        assert not re.search(r'returnValue = "[^"]+"', block)

    def test_die_grenzen_stehen_im_quelltext(self, app: str) -> None:
        stelle = app[app.index("// Die Rueckfrage vor dem Schliessen."):]
        kopf = stelle[:stelle.index("window.addEventListener")]
        assert "Wortlaut" in kopf
        assert "geklickt oder getippt" in kopf
