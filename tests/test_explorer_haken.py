"""Häkchen statt Ziehen.

Aus der Kanzlei: „wenn man eine Akte auswählt, dass man immer noch entweder
durch den Button alle Akten überzieht oder durch Drag and Drop. Ich finde so
etwas wie Häkchen intuitiver."

Der Explorer zeigte zwei Spalten – links jur|nodes, rechts die Arbeitsakte –
und man schob Dokumente mit der Maus oder einem Pfeil hinüber. Die Bedeutung
war richtig, der Handgriff ungewohnt: Niemand wählt sonst so aus. Jetzt ist es
eine Liste mit Häkchen, und angehakt heißt „liegt in der Arbeitsakte".

Zwei Dinge kommen dabei aus der offenen Liste mit dazu, weil sie erst bei
fünfzig Dokumenten wirklich fehlen: die Stapelauswahl nach Kategorie und die
sichtbare Zeichenzahl der Arbeitsakte.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"


@pytest.fixture(scope="module")
def html() -> str:
    return (STATISCH / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def app_js() -> str:
    return (STATISCH / "app.js").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def css() -> str:
    return (STATISCH / "styles.css").read_text(encoding="utf-8")


def test_es_gibt_nur_noch_eine_liste(html: str) -> None:
    explorer = html[html.index('<dialog id="explorer-dialog"'):html.index('<dialog id="ged-dialog"')]
    assert 'id="quelle-liste"' in explorer
    assert 'id="arbeit-liste"' not in explorer, "Die zweite Spalte ist der halbe Handgriff."


def test_jede_zeile_traegt_ein_haekchen(app_js: str) -> None:
    block = app_js[app_js.index("function explorerEintrag("):app_js.index("function explorerVerschieben(")]
    assert 'haken.type = "checkbox"' in block
    assert "explorerVerschieben(d.id, haken.checked)" in block


def test_das_ziehen_ist_wirklich_weg(app_js: str, css: str) -> None:
    """Ein halb entfernter Handgriff ist schlimmer als der alte.

    **Die Grenze läuft bei ``dragstart``, seit dem 16.10.2026.** Was der
    Kanzlei ungewohnt war, ist das Aufheben *im Programm*: ein Dokument aus
    einer Liste nehmen und in eine andere legen. Deshalb hebt das Programm
    nichts auf – ``dragstart`` kommt nirgends vor.

    Eine Datei aus dem Windows-Explorer auf ein Fenster fallen zu lassen ist
    etwas anderes: Aufgehoben wird sie dort, der Handgriff ist überall
    derselbe, und er ist nie der einzige Weg – die Klammer am Eingabefeld
    tut dasselbe. Entgegennehmen darf deshalb genau eine Stelle: der Verlauf.
    """
    assert "dragstart" not in app_js, "Das Programm hebt nichts auf."
    for rest in ("dragover", "dataTransfer", "explorer-pfeil"):
        assert rest not in _explorer(app_js), rest
    for rest in (".explorer-pfeil", ".explorer-liste.ueber"):
        assert rest not in css, rest


def _explorer(app_js: str) -> str:
    """Der Teil der Oberfläche, der die Auswahl aus jur|nodes macht."""
    return app_js[app_js.index("function explorerArtenZeichnen("):
                  app_js.index("function explorerVerschieben(")]


def test_entgegengenommen_wird_nur_im_verlauf(app_js: str) -> None:
    """Eine fallen gelassene Datei landet im Chat – und sonst nirgends."""
    block = app_js[app_js.index("function einfuegenPerAblegen("):
                   app_js.index("function nutzerkarte(")]
    assert 'const thread = $("thread")' in block
    assert 'thread.addEventListener("drop"' in block
    # Und außerhalb dieser einen Funktion nimmt nichts etwas entgegen.
    assert app_js.count('addEventListener("drop"') == 1


def test_stapelauswahl_nach_kategorie(app_js: str, html: str) -> None:
    """Bei acht Dokumenten hakt man einzeln, bei fünfzig nicht mehr."""
    assert 'id="explorer-arten"' in html
    block = app_js[app_js.index("function explorerArtenZeichnen("):app_js.index("// Wie voll ist die Arbeitsakte?")]
    assert "d.kategorie" in block
    assert "alleDrin" in block, "Ein zweiter Klick muss die Kategorie wieder abwählen."


def test_eine_einzige_kategorie_ergibt_keine_auswahl(app_js: str) -> None:
    block = app_js[app_js.index("function explorerArtenZeichnen("):app_js.index("// Wie voll ist die Arbeitsakte?")]
    assert "if (arten.length < 2) return;" in block


def test_die_zeichenzahl_der_arbeitsakte_ist_sichtbar(app_js: str, html: str) -> None:
    assert 'id="explorer-umfang"' in html
    block = app_js[app_js.index("function explorerUmfangZeigen("):app_js.index("function explorerEintrag(")]
    assert "K.maxPassagenZeichen" in block
    assert "noch nicht gelesen" in block, "Ungelesene Dokumente dürfen nicht als 0 Zeichen durchgehen."


def test_die_grenze_kommt_aus_der_einstellung_nicht_aus_der_oberflaeche() -> None:
    """Eine fest eingetragene Zahl löge, sobald die Einstellung sich ändert."""
    web = (Path(__file__).resolve().parent.parent / "jusperfect" / "web.py").read_text(encoding="utf-8")
    assert '"max_passagen_zeichen": e.max_passagen_zeichen' in web


def test_alle_anhaken_trifft_nur_die_sichtbaren(app_js: str) -> None:
    """Sonst legt „Gegner" + „alle anhaken" doch die ganze Akte hinein.

    Geprüft wird die Zusage, nicht der Wortlaut: Der Knopf geht von
    ``explorerSichtbar()`` aus – also von dem, was der Filter übrig lässt –
    und niemals von der ganzen Karte.
    """
    block = re.search(r'\$\("alle-rein"\)\.addEventListener\("click", \(\) => \{(.*?)\n  \}\);',
                      app_js, re.S).group(1)
    assert "explorerSichtbar()" in block
    assert "explorer.karte" not in block


def test_die_beschriftung_sagt_was_ein_haken_bedeutet(html: str) -> None:
    explorer = html[html.index('<dialog id="explorer-dialog"'):html.index('<dialog id="ged-dialog"')]
    sichtbar = re.sub(r"<!--.*?-->", "", explorer, flags=re.S)
    assert "Angehakt heißt" in sichtbar
    assert "Ziehen oder Pfeile" not in sichtbar


def test_was_schon_im_gedaechtnis_liegt_ist_ausgegraut(app_js: str, css: str) -> None:
    """Aus der Kanzlei: „damit es keine Doppelung im Aktengedächtnis gibt,
    graue die Akten, die schon im Aktengedächtnis sind, aus."""
    block = app_js[app_js.index("function gedExplorerZeichnen("):app_js.index("function gedUmfangZeigen(")]
    assert "schon-drin" in block
    assert "box.disabled = !fehlt" in block, "Ausgegraut heißt auch: nicht noch einmal wählbar."
    assert ".explorer-zeile.schon-drin" in css


def test_auch_die_arbeitsakte_zeigt_es(app_js: str) -> None:
    """Sonst sieht man beim Übernehmen nicht, was ohnehin schon gelesen ist."""
    block = app_js[app_js.index("function explorerEintrag("):app_js.index("function gedaechtnisKennt(")]
    assert "gedaechtnisKennt(d.id)" in block
    assert "schon im Gedächtnis" in block


def test_ohne_gedaechtnis_stoert_es_nicht(app_js: str) -> None:
    """Ist keines eingeschaltet, darf nichts ausgegraut sein."""
    block = app_js[app_js.index("function gedaechtnisKennt("):app_js.index("function explorerVerschieben(")]
    assert "(sitzung && sitzung.gedaechtnis) || {}" in block
    assert "(g.eintraege || [])" in block
