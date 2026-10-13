"""Weniger ist mehr – was von der Oberfläche verschwunden ist, bleibt verschwunden.

Aus der Kanzlei: „Fürs Motto weniger ist mehr. Weil man sonst den Benutzer
überfordert."

Auf der Arbeitsfläche waren über zwanzig Dinge anklickbar, bevor man die erste
Frage gestellt hatte. Diese Datei hält fest, was weggenommen wurde – nicht weil
das Weggenommene falsch war, sondern weil es an dieser Stelle nicht gebraucht
wird. Ohne solche Tests wächst so etwas ganz von allein wieder nach: Jeder
einzelne Knopf hat schließlich einen guten Grund.
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


def test_die_mittlere_spalte_traegt_keine_ueberschrift(html: str) -> None:
    """„Cowork" sagte einem Anwalt nichts; das Eingabefeld erklärt die Spalte."""
    spalte = html[html.index('<section class="spalte cowork">'):html.index('<div id="thread"')]
    # Ohne die Kommentare - dort steht die Begruendung, und in ihr das Wort.
    sichtbar = re.sub(r"<!--.*?-->", "", spalte, flags=re.S)
    assert "Cowork" not in sichtbar
    kopf = re.search(r'<div class="spalte-kopf">(.*?)<div class="aktionen">', sichtbar, re.S)
    assert kopf is not None
    assert "<span>" not in kopf.group(1), "Die Spalte braucht keine Beschriftung über den Knöpfen."


def test_die_startseite_traegt_keinen_abgeschalteten_schalter(html: str, css: str) -> None:
    """Perfect Shield stand als „nicht aktiv" an der prominentesten Stelle.

    Die Konzeptentscheidung bleibt – die Einstellung `perfect_shield_aktiv`
    gibt es weiter. Nur ein Schalter, der nichts tut, gehört nicht dorthin, wo
    der Bearbeiter jeden Morgen anfängt.
    """
    for kennung in ("perfect-shield", "ps-stand", "Vorschaltstufe"):
        assert kennung not in html, kennung
    for kennung in (".vorschaltstufe", ".ps-stand"):
        assert kennung not in css, kennung


def test_der_nachweis_steht_bei_der_verwaltung_und_nicht_in_der_akte(html: str) -> None:
    """Rechenschaft über alle Akten ist keine Handlung in einer Akte."""
    menue = re.search(r'<div id="mehr-menue".*?</div>', html, re.S).group(0)
    assert 'data-aktion="nachweis"' not in menue
    verwaltung = html[html.index('class="verwaltungszeile"'):html.index("</section>", html.index('class="verwaltungszeile"'))]
    assert 'id="nachweis-oeffnen"' in verwaltung


def test_das_gedaechtnisfenster_zeigt_einen_satz_statt_einer_tabelle(app_js: str) -> None:
    """Fünf Zahlen in einer Spalte von 300 Pixeln beantworten keine Frage."""
    anfang = app_js.index("function gedaechtnisFensterZeigen(")
    block = app_js[anfang:app_js.index("function gedaechtnisExplorerOeffnen(")]
    assert "ged-satz" in block
    for zeile in ('zeile("Umfang"', 'zeile("Frühere Fragen"', 'zeile("Ereignisse"'):
        assert zeile not in block, zeile


def test_die_meldung_liegt_weder_ueber_der_eingabe_noch_ueber_den_knoepfen(css: str) -> None:
    """Unten mittig lag sie über dem Frageeingabefeld, oben mittig über der
    Knopfreihe. Beides sind Stellen, an denen gearbeitet wird."""
    zeile = next(z for z in css.splitlines() if z.startswith(".meldung {"))
    assert "right:" in zeile
    assert "left: 50%" not in zeile
    assert "translateX(-50%)" not in zeile


def test_die_leiste_trennt_arbeiten_von_ansehen(html: str) -> None:
    """Zwei Arten von Knopf, getrennt – und seit dem 13.10.2026 in zwei Spalten.

    Analyse, Entwurf und Gedächtnis tun etwas an der Akte. Die vier daneben tun
    nichts; sie entscheiden nur, was zu sehen ist. Stünden sie in einer Reihe,
    müsste man bei jedem Klick überlegen, welcher von beiden Sorten er ist.

    Die Trennung war zuerst ein Strich, dann die Stelle in der Leiste (die
    Fensterknöpfe an den Rändern, die Arbeit in der Mitte). Jetzt ist es die
    Spalte. Aus der Kanzlei am 13.10.2026:

        Chat teilte sich das Fenster mit Analyse und Eingangsprüfung, Entwurf
        usw. Das ist meines Erachtens nicht gut. Der Chat steht im
        Vordergrund. Die Funktionen sollen wählbar sein, aber zum rechten
        Fenster gehören und anklickbar sein.

    Die Arbeitsknöpfe stehen deshalb oben in der rechten Spalte – und zwar in
    einer Leiste, die stehen bleibt, wenn die drei Fenster darunter zu sind.
    Ein Knopf, der mit dem Fenster verschwindet, in dem er steht, wäre eine
    Falle.
    """
    # In der Kopfzeile des Chats steht keine Arbeit mehr.
    aktionen = re.search(r'<div class="aktionen">(.*?)</div>\s*</div>\s*<div id="thread"',
                         html, re.S).group(1)
    assert "arbeitsknoepfe" not in aktionen
    for aktion in ("analyse", "entwurf", "gedaechtnis", "triage"):
        assert f'data-aktion="{aktion}"' not in aktionen, aktion

    # Sie steht in der rechten Spalte, VOR dem ersten Fenster.
    rechts = html[html.index('<aside class="spalte rechts"'):html.index("</aside>")]
    assert rechts.index('class="rechts-aktionen"') < rechts.index('class="fenster ')
    arbeit = rechts[rechts.index('class="arbeitsknoepfe"'):rechts.index('class="mehr"')]
    assert arbeit.count("<button") == 3, "Analyse, Entwurf und Gedächtnis."
    for aktion in ("analyse", "entwurf", "gedaechtnis"):
        assert f'data-aktion="{aktion}"' in arbeit, aktion


def test_die_leiste_der_funktionen_bleibt_wenn_die_fenster_zugehen(app_js: str) -> None:
    """Sonst wäre Analyse weg, sobald jemand die Belege zuklappt."""
    assert "rechts.hidden = false" in app_js
    assert 'rechts.classList.toggle("nur-leiste"' in app_js


def test_jedes_fenster_laesst_sich_zuklappen(html: str, app_js: str) -> None:
    """Der Sinn der Sache: Was aus ist, gibt seinen Platz an die Mitte ab."""
    for name in ("dokument", "chronologie", "gedaechtnis", "belege"):
        assert f'data-fenster="{name}"' in html, name
    assert "ohne-links" in app_js and "ohne-rechts" in app_js


def test_zwei_fenster_gehen_von_selbst_auf(app_js: str) -> None:
    """Ein Klick, der ins Leere zu gehen scheint, ist schlimmer als ein Fenster
    zu viel: die Belege, sobald es welche gibt, und das Dokument beim Klick auf
    eine Fundstelle."""
    belege = app_js[app_js.index("function belegeMerken("):app_js.index("function zeigeBelege(")]
    assert 'fensterOeffnen("belege")' in belege
    markieren = app_js[app_js.index("function passageMarkieren("):app_js.index("// ── Fenster")]
    assert 'fensterOeffnen("dokument")' in markieren


def test_der_benutzername_ist_selbst_der_weg_zurueck(html: str, app_js: str) -> None:
    """Ein eigener Knopf „Benutzer wechseln" stand dauerhaft für etwas Seltenes.

    Die Beschriftung kommt nicht zurück - der Name selbst bleibt der Weg. Er
    muss aber danach aussehen: Aus der Kanzlei am 25.09.2026 "zu klein und
    nicht so intuitiv". Ein Knopf, den man für eine Beschriftung hält, ist
    keiner.
    """
    kopf = html[html.index('class="kopf-rechts"'):html.index("</header>")]
    sichtbar = re.sub(r"<!--.*?-->", "", kopf, flags=re.S)   # ohne die Begruendung
    assert "Benutzer wechseln" not in sichtbar
    assert 'id="nutzer-wechseln"' in kopf
    assert 'wer.textContent = s.nutzer.name' in app_js
    # Der Name steht in einem eigenen Feld, damit Sinnbild und Zusatz beim
    # Setzen nicht mitgeloescht werden.
    assert 'id="nutzer-name"' in kopf
    assert '$("nutzer-name")' in app_js


def test_der_benutzerknopf_sieht_aus_wie_ein_knopf(html: str, css: str) -> None:
    """Ein Rahmen, der erst beim Daraufzeigen erscheint, kommt zu spät.

    Wer mit der Maus nicht zufällig darüberfährt, sieht nur blassen Text und
    hält ihn für die Anzeige, wer angemeldet ist.
    """
    kopf = html[html.index('class="kopf-rechts"'):html.index("</header>")]
    sichtbar = re.sub(r"<!--.*?-->", "", kopf, flags=re.S)
    # Das Sinnbild sagt "Person", bevor der Name gelesen ist.
    assert 'class="nutzer-bild"' in sichtbar
    # Und daneben steht, was beim Klicken geschieht.
    assert "wechseln</span>" in sichtbar

    regel = css[css.index(".nutzer-knopf {"):css.index(".nutzer-knopf:hover")]
    assert "border: 1px solid var(--linie-stark)" in regel, "Rahmen nicht dauerhaft"
    assert "background: var(--flaeche-2)" in regel, "Flaeche nicht dauerhaft"
    assert "transparent" not in regel, "Der Knopf ist wieder unsichtbar"


def test_die_arbeitsakte_steht_bei_den_dokumenten(html: str) -> None:
    """Aus der Kanzlei: „dann hast du in der Leiste oben auch noch mal
    Arbeitsakte, und das halte ich für doppelt gemoppelt."""
    kopf = html[html.index('<section class="spalte dokument"'):html.index('id="dok-text"')]
    assert 'data-aktion="dokumente"' in kopf


def test_der_pfeil_steht_rechts_in_der_kopfzeile(html: str) -> None:
    """„Wenn der Pfeil nicht links ist, sondern rechts, ist er besser zu sehen."""
    kopf = html[html.index('<section class="spalte dokument"'):html.index('id="dok-text"')]
    assert kopf.index("<span>Dokument</span>") < kopf.index('data-fenster-zu="dokument"')


def test_alle_pfeile_zeigen_in_dieselbe_richtung(html: str) -> None:
    """Aus der Kanzlei: „bei belegen und gedächtnis mache den pfeil nach links
    statt nach rechts."

    Der Pfeil zeigte anfangs dorthin, wohin das Fenster verschwindet - links am
    Dokument nach links, rechts an Chronologie, Gedächtnis und Belegen nach
    rechts. Logisch gedacht, in der Kanzlei aber nicht so gelesen: Wer links
    das Zeichen „‹" als „zu" gelernt hat, erwartet rechts dasselbe Zeichen und
    nicht dessen Spiegelbild. Vier Pfeile, eine Bedeutung.
    """
    pfeile = re.findall(r'data-fenster-zu="[a-z]+"[^>]*>(.)</button>', html, re.S)
    assert len(pfeile) == 4, pfeile
    assert set(pfeile) == {"‹"}, pfeile


# ── Der Inhalt des Aktengedächtnisses: einschaltbar, nicht aufgedrängt ──────
# Aus der Kanzlei: „zeig auch den Inhalt in dieser Ansicht … als einschaltbare
# Funktion." Beides zählt. Die tägliche Frage ist „ist die Akte vollständig
# drin?", und die beantworten die beiden Spalten. Wer wissen will, was das
# Programm daraus gemacht hat, schaltet es dazu – und findet es so wieder vor.

def test_der_inhalt_ist_zugeklappt_bis_man_ihn_aufmacht(html: str) -> None:
    block = re.search(r'<details class="ged-inhalt" id="ged-inhalt"(.*?)>', html)
    assert block, "Der Inhaltsblock ist kein aufklappbarer Abschnitt mehr."
    assert "open" not in block.group(1), (
        "Der Inhalt ist voreingestellt aufgeklappt – er soll sich niemandem aufdrängen."
    )


def test_der_schalter_wird_gemerkt(app_js: str) -> None:
    assert "jusperfect.gedinhalt." in app_js, (
        "Der Schalter wird nicht gemerkt; er stünde bei jedem Öffnen wieder auf zu."
    )
    assert "gedInhaltSchalterLaden()" in app_js


def test_der_inhalt_zeigt_alle_drei_teile(html: str) -> None:
    for kennung in ("ged-block-sachverhalt", "ged-block-chronologie", "ged-block-fragen"):
        assert kennung in html, f"Im Inhalt fehlt {kennung}."


def test_die_knopfzeile_des_dialogs_bleibt_stehen(css: str) -> None:
    """Der Inhalt machte den Dialog länger als den Bildschirm hoch."""
    regel = re.search(r"\.explorer-form > \.dialog-knoepfe \{([^}]*)\}", css)
    assert regel, "Die Knopfzeile des Dialogs hat keine eigene Regel mehr."
    assert "position: sticky" in regel.group(1), (
        "Ohne klebende Knopfzeile schiebt ein langer Inhalt „Schließen“ aus dem Bild."
    )


# ── Zwei Beträge für dieselbe Sache brauchen ihre Grundlage ─────────────────
# In der Mietsache 31/26 SC stehen 850,00 EUR im Vertrag und 950,00 EUR im
# Schreiben der Gegenseite. Beide gehören in die Forderungen. Ohne die Spalte
# „Grundlage" stünden dort zwei Zeilen „Grundmiete monatlich" mit verschiedenen
# Zahlen und ohne Erklärung – das wäre schlechter als eine Zeile.

def test_die_forderungen_zeigen_die_grundlage(app_js: str) -> None:
    assert "forderungenMitGrundlage" in app_js
    assert '"Grundlage"' in app_js


def test_die_spalte_erscheint_nur_wenn_es_etwas_zu_sagen_gibt(app_js: str) -> None:
    """Eine leere Spalte in jeder Akte wäre der falsche Preis dafür."""
    treffer = re.search(r"const forderungenMitGrundlage = ([^\n]+)", app_js)
    assert treffer, "Der Schalter für die Spalte fehlt."
    assert ".some(" in treffer.group(1), (
        "Die Spalte erscheint offenbar immer, statt nur bei Einträgen mit Grundlage."
    )


def test_rechts_steht_der_pfeil_links_in_der_kopfzeile(html: str) -> None:
    """Aus der Kanzlei: „zum Schließen von Chronologie von den Seiten rechts ist
    der Pfeil zum Schließen des Fensters immer noch rechts und nicht links,
    finde ich intuitiver."

    Das widerspricht dem Dokument-Fenster nicht, es ergänzt es. Dort hieß es
    „wenn der Pfeil nicht links ist, sondern rechts, ist er besser zu sehen" –
    und rechts ist am linken Fenster die INNERE Kante, die zur Arbeitsfläche
    zeigt. An den rechten Fenstern ist die innere Kante die linke. Eine Regel,
    vier Pfeile: Sie stehen zur Mitte hin, und dorthin faltet sich das Fenster.
    """
    rechts = html[html.index('<aside class="spalte rechts"'):html.index("</aside>")]
    for schluessel, titel in (("chronologie", "Chronologie"),
                              ("gedaechtnis", "Gedächtnis"),
                              ("belege", "Belege")):
        assert (rechts.index(f'data-fenster-zu="{schluessel}"')
                < rechts.index(f"<span>{titel}</span>")), schluessel

    # Am Dokument bleibt er rechts - dort ist das die innere Kante.
    dok = html[html.index('<section class="spalte dokument"'):html.index('id="dok-text"')]
    assert dok.index("<span>Dokument</span>") < dok.index('data-fenster-zu="dokument"')
