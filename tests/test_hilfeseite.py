"""Die Hilfeseite verspricht nichts, was der Programmordner nicht hält.

Aus der Kanzlei: „kannst du bitte auch noch eine website kreierien die die app
erklärt und bei einrichtungen und probleme hilft".

`HILFE.html` liegt neben dem Programm und wird mit einem Doppelklick geöffnet.
Zwei Dinge können daran schiefgehen, und beide fallen ohne Prüfung erst dem
Anwender auf:

**Sie nennt eine Datei, die es nicht gibt.** „Lassen Sie ORDNER-PRUEFEN.bat
laufen" ist eine Sackgasse, wenn die Datei anders heißt. Eine Hilfe, die
danebengreift, ist schlimmer als keine – sie kostet erst Zeit und dann
Vertrauen.

**Sie braucht das Internet.** Eine Schriftart oder ein Skript von außen macht
aus einer Hilfeseite, die im Störungsfall gebraucht wird, eine Seite, die genau
dann nicht mehr lesbar ist. Deshalb steht alles in der Datei selbst.

Dazu die Selbstverständlichkeit, die trotzdem geprüft gehört: Die Seite darf
weitergegeben werden, also stehen dort **keine Zugangsdaten, keine echten
Aktenzeichen und keine Mandantennamen**.

Die Darstellung selbst ist in echtem Chromium gemessen, bei 1280 und bei 390 px:
kein waagerechter Überlauf, kein Konsolenfehler, und die Suche in den Störungen
findet, klappt auf und räumt wieder zusammen.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
SEITE = WURZEL / "HILFE.html"


@pytest.fixture(scope="module")
def quelle() -> str:
    return SEITE.read_text(encoding="utf-8")


def test_die_hilfeseite_liegt_neben_dem_programm() -> None:
    assert SEITE.is_file(), "HILFE.html fehlt im Programmordner"


def test_jede_genannte_startdatei_gibt_es_auch(quelle: str) -> None:
    genannt = sorted(set(re.findall(r"<code>([A-ZÄÖÜ0-9-]+\.bat)</code>", quelle)))
    assert genannt, "Die Seite nennt keine einzige Datei zum Doppelklicken"
    fehlend = [name for name in genannt if not (WURZEL / name).is_file()]
    assert not fehlend, f"Die Hilfeseite nennt Dateien, die es nicht gibt: {fehlend}"


def test_jede_genannte_beschreibung_gibt_es_auch(quelle: str) -> None:
    genannt = sorted(set(re.findall(r"<code>([A-ZÄÖÜ0-9-]+\.md)</code>", quelle)))
    fehlend = [name for name in genannt if not (WURZEL / name).is_file()]
    assert not fehlend, f"Die Hilfeseite verweist auf Dateien, die es nicht gibt: {fehlend}"


def test_die_seite_braucht_kein_internet(quelle: str) -> None:
    # Gesucht wird, was der Browser nachladen würde - nicht, was im Text steht.
    geladen = re.findall(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", quelle)
    auswaerts = [
        ziel
        for ziel in geladen
        if not ziel.startswith("#") and not ziel.startswith("data:")
    ]
    assert not auswaerts, f"Die Hilfeseite lädt von außen nach: {auswaerts}"


def test_jeder_verweis_im_inhalt_trifft_einen_abschnitt(quelle: str) -> None:
    ziele = set(re.findall(r'id="([^"]+)"', quelle))
    sprungmarken = set(re.findall(r'href="#([^"]+)"', quelle))
    ins_leere = sorted(sprungmarken - ziele)
    assert not ins_leere, f"Das Inhaltsverzeichnis springt ins Leere: {ins_leere}"


def test_es_stehen_keine_zugangsdaten_darin(quelle: str) -> None:
    verraeterisch = {
        "AWS-Schlüssel": r"AKIA[0-9A-Z]{8,}",
        "Token": r"(?i)\btoken\s*[:=]\s*\S{8,}",
        "Geheimnis": r"(?i)secret[_-]?access[_-]?key",
        "Guardrail-Kennung": r"JUSPERFECT_GUARDRAIL_ID\s*=\s*[0-9a-z]{6,}",
    }
    gefunden = [name for name, muster in verraeterisch.items() if re.search(muster, quelle)]
    assert not gefunden, f"Die Hilfeseite enthält Zugangsdaten: {gefunden}"


def test_es_stehen_keine_echten_aktenzeichen_darin(quelle: str) -> None:
    # Die Kanzlei führt ihre Akten als d-001-2026 und th-001-2026; der Pfad zum
    # Aktenordner gehört ebenso wenig auf eine Seite, die weitergegeben wird.
    muster = {
        "Aktenzeichen der Kanzlei": r"(?i)\b(?:d|th)-\d{3}-20\d{2}\b",
        "Pfad zum Aktenbestand": r"(?i)[A-Z]:\\\\?Akten",
        "Adresse der Schnittstelle": r"(?i)jur-nodes\.net",
    }
    gefunden = [name for name, m in muster.items() if re.search(m, quelle)]
    assert not gefunden, f"Die Hilfeseite enthält echte Kanzleidaten: {gefunden}"


def test_die_seite_sagt_dem_browser_wie_sie_zu_lesen_ist(quelle: str) -> None:
    assert '<html lang="de">' in quelle
    assert '<meta charset="utf-8">' in quelle
    assert 'name="viewport"' in quelle, "Ohne viewport-Zeile ist die Seite am Handy unlesbar"


def test_die_suche_findet_die_offene_405(quelle: str) -> None:
    # Der Punkt, nach dem gerade wirklich gesucht wird. Faellt er aus der Seite,
    # sucht die Kanzlei die Erklaerung dort, wo keine mehr steht.
    abschnitt = quelle.split('id="stoerungen"', 1)[-1].split('id="dateien"', 1)[0]
    assert "405" in abschnitt
    assert "JURNODES-PRUEFEN.bat" in abschnitt


def test_die_nummern_laufen_lueckenlos_durch(quelle: str) -> None:
    """Am 05.10.2026 kamen drei Abschnitte dazu, und alles Spätere musste
    umnummeriert werden. Eine übersprungene Zahl sieht aus wie ein verlorener
    Abschnitt."""
    nummern = [int(n) for n in re.findall(r'<h2><span class="nr">(\d+)</span>', quelle)]
    assert nummern == list(range(1, len(nummern) + 1)), nummern


def test_die_leiste_zeigt_jeden_abschnitt_und_keinen_zu_viel(quelle: str) -> None:
    leiste = re.findall(r'<nav class="seitlich".*?</nav>', quelle, re.S)[0]
    verwiesen = re.findall(r'href="#([^"]+)"', leiste)
    vorhanden = re.findall(r'<section id="([^"]+)"', quelle)
    assert verwiesen == vorhanden, (verwiesen, vorhanden)


def test_auch_die_verweise_im_text_treffen_einen_abschnitt(quelle: str) -> None:
    """Abschnitt 4 verweist weiter auf 5, 6 und 9 – die sind neu."""
    ziele = set(re.findall(r'<section id="([^"]+)"', quelle))
    im_text = set(re.findall(r'<a href="#([^"]+)">', quelle))
    assert im_text <= ziele, im_text - ziele


def test_sie_beschreibt_die_liste_mit_haken_und_nicht_mehr_das_ziehen(quelle: str) -> None:
    """Den Zwei-Fenster-Explorer zum Ziehen gibt es seit Wochen nicht mehr.

    Eine Anleitung, die eine Bedienung beschreibt, die es nicht gibt, kostet
    erst Zeit und dann Vertrauen – genau wie eine Datei, die es nicht gibt.
    """
    assert "Zwei-Fenster-Explorer" not in quelle
    assert "alle anhaken" in quelle
    assert "Angehakt heißt" in quelle


def test_sie_sagt_was_wie_lange_bleibt(quelle: str) -> None:
    """Die Frage, die bei einem KI-Programm zuerst zu stellen ist."""
    assert 'id="speicherung"' in quelle
    abschnitt = quelle.split('<section id="speicherung">')[1].split("</section>")[0]
    for muss in ("Aktengedächtnis", "Entwürfe", "jur|nodes",
                 "weg, sobald das schwarze Serverfenster zugeht",
                 "nur ein Vermerk"):
        assert muss in abschnitt, muss


def test_sie_sagt_dass_vergessen_nicht_rueckgaengig_zu_machen_ist(quelle: str) -> None:
    abschnitt = quelle.split('<section id="gedaechtnis">')[1].split("</section>")[0]
    # Ohne Zeilenumbrueche vergleichen: Wo im Quelltext umgebrochen wird, ist
    # eine Frage der Spaltenbreite und keine Aussage ueber den Text.
    fliess = " ".join(abschnitt.split())
    assert "Es gibt kein Rückgängig" in fliess
    assert "kostet aber ein neues Einlesen" in fliess
    assert "holt die gelöschten Antworten und Zeitstrahleinträge nicht wieder" in fliess


def test_sie_erklaert_den_gelben_hinweis_ueber_der_analyse(quelle: str) -> None:
    """Er sieht aus wie ein Fehler und ist keiner."""
    stoerungen = quelle.split('<section id="stoerungen">')[1].split("</section>")[0]
    assert "gelben Hinweis" in stoerungen
    assert "Kein Fehler" in stoerungen
