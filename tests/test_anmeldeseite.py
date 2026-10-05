"""Die erste Seite: Wer arbeitet hier?

Die Nutzerkennung stand als Eingabefeld in der rechten oberen Ecke, zwischen
Kostenanzeige und Verbindungszustand. Sie ist aber die erste Frage des
Programms und keine Anzeige unter mehreren. Aus der Kanzlei: „das ist für mich
irgendwie nicht übersichtlich".

Jetzt gibt es dafür eine eigene Seite, und die Aktenliste kommt erst danach.
Zwei Dinge müssen dabei stimmen, und beide stehen hier:

* **Die Auswahl ist kein Kennwort.** Örtlich sagt der Kopf der Anfrage, wer da
  ist; wer an diesem Rechner sitzt, kann jeden Namen wählen. Das muss auf der
  Seite stehen, sonst hält es jemand für einen Schutz, der es nicht ist.
* **Die Liste der Kanzleiangehörigen gibt es nur örtlich.** Im AWS-Betrieb
  stellt Cognito die Identität fest, und wer noch nicht angemeldet ist, hat
  keinen Anspruch darauf zu erfahren, wer in dieser Kanzlei arbeitet.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.hilfen import client, dienste, einstellungen

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"


@pytest.fixture(scope="module")
def app_js() -> str:
    return (STATISCH / "app.js").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def html() -> str:
    return (STATISCH / "index.html").read_text(encoding="utf-8")


# ── Die Liste der Benutzer ───────────────────────────────────────────────────

def test_oertlich_gibt_es_die_auswahl() -> None:
    c = client(dienste(), nutzer=None)
    antwort = c.get("/api/nutzer")
    assert antwort.status_code == 200, antwort.text
    kennungen = [n["id"] for n in antwort.json()["nutzer"]]
    assert "ra-weber" in kennungen and "refa-lorenz" in kennungen


def test_die_auswahl_braucht_selbst_keine_kennung() -> None:
    """Sie steht vor der Anmeldung – sonst käme man nicht an sie heran."""
    c = client(dienste(), nutzer=None)
    assert c.get("/api/nutzer").status_code == 200


def test_sie_nennt_namen_und_kennung_und_sonst_nichts() -> None:
    """Welche Akten jemand sehen darf, geht niemanden vor der Anmeldung an."""
    c = client(dienste(), nutzer=None)
    for eintrag in c.get("/api/nutzer").json()["nutzer"]:
        assert set(eintrag) == {"id", "name"}


def test_mit_cognito_gibt_es_diesen_weg_nicht() -> None:
    """404 und nicht 403: Der Weg existiert dort nicht, statt verboten zu sein."""
    e = einstellungen(JUSPERFECT_IDENTITAET="cognito")
    c = client(dienste(einstellungen=e), nutzer=None)
    assert c.get("/api/nutzer").status_code == 404


# ── Die Seite selbst ─────────────────────────────────────────────────────────

def test_die_anmeldeseite_steht_vor_der_aktenliste(html: str) -> None:
    assert html.index('id="anmelden"') < html.index('id="einstieg"')
    # Beide starten verborgen; erst das Programm entscheidet, welche gilt.
    for kennung in ('<section id="anmelden" class="anmelden" hidden>',
                    '<section id="einstieg" class="einstieg" hidden>'):
        assert kennung in html, kennung


def test_die_kennung_steht_nicht_mehr_in_der_ecke(html: str) -> None:
    kopf = html[html.index('class="kopf-rechts"'):html.index("</header>")]
    assert 'id="nutzerfeld"' not in kopf
    assert 'placeholder="z. B. ra-weber"' not in kopf


def test_die_seite_sagt_dass_die_auswahl_kein_kennwort_ist(html: str) -> None:
    """Ein Feld, das wie eine Anmeldung aussieht, aber keine ist, ist gefährlicher
    als gar keines."""
    karte = html[html.index('id="anmelden-lokal"'):html.index('id="anmelden-aws"')]
    assert "kein Kennwort" in karte
    assert "schützt nichts" in karte


def test_die_auswahl_fuehrt_erst_nach_geglueckter_pruefung_weiter(app_js: str) -> None:
    """Eine unbekannte Kennung darf nicht in die Aktenliste durchfallen."""
    anfang = app_js.index("async function benutzerWaehlen(")
    block = app_js[anfang:app_js.index("async function benutzerWechseln(")]
    assert "if (!(await ladeStatus()))" in block
    assert block.index("ladeStatus()") < block.index("einstiegZeigen()")


def test_der_benutzerwechsel_schliesst_die_offene_sitzung(app_js: str) -> None:
    """Sonst arbeitete der nächste Benutzer in den Texten des vorigen weiter."""
    anfang = app_js.index("async function benutzerWechseln(")
    block = app_js[anfang:app_js.index("// ── Zuletzt geöffnet")]
    assert "if (sitzung) await sitzungSchliessen();" in block
    assert block.index("sitzungSchliessen()") < block.index("anmeldenZeigen()")


# ── Zuletzt geöffnet ─────────────────────────────────────────────────────────

def test_der_verlauf_liegt_nur_im_browser_und_je_benutzer(app_js: str) -> None:
    anfang = app_js.index("function verlaufSchluessel(")
    block = app_js[anfang:app_js.index("function verlaufMerken(")]
    assert "jusperfect.verlauf." in block
    assert '$("nutzer").value' in block, "Zwei Benutzer an einem Rechner sehen sonst dieselbe Liste."


def test_der_verlauf_merkt_nur_die_akte_und_keinen_inhalt(app_js: str) -> None:
    anfang = app_js.index("function verlaufMerken(")
    block = app_js[anfang:app_js.index("function verlaufLeeren(")]
    for feld in ("id:", "aktenzeichen:", "bezeichnung:", "wann:"):
        assert feld in block, feld
    for verboten in ("passagen", "antwort", "frage", "text"):
        assert verboten not in block, verboten


def test_der_verlauf_laesst_sich_leeren(app_js: str, html: str) -> None:
    assert 'id="verlauf-leeren"' in html
    assert "localStorage.removeItem(verlaufSchluessel())" in app_js


def test_eine_geoeffnete_akte_landet_im_verlauf(app_js: str) -> None:
    anfang = app_js.index("async function akteOeffnen(")
    block = app_js[anfang:anfang + 400]
    assert "verlaufMerken(sitzung.sitzung.akte)" in block


# ── Verwaltung ───────────────────────────────────────────────────────────────

def test_die_verwaltung_steht_abgesetzt_und_nicht_in_der_suchzeile(html: str) -> None:
    suchzeile = html[html.index('class="suchzeile"'):html.index('id="aktenliste"')]
    assert "aufsicht-oeffnen" not in suchzeile
    assert 'class="verwaltungszeile"' in html


def test_die_aufbewahrung_zeigt_an_ob_etwas_zu_entscheiden_ist(app_js: str, html: str) -> None:
    """Ohne Zahl ist der Knopf nur eine Beschriftung."""
    assert 'id="aufsicht-marke"' in html
    anfang = app_js.index("async function aufsichtMarkeLaden(")
    block = app_js[anfang:app_js.index("// ── Akten und Sitzung")]
    assert "daten.handlungsbedarf" in block
    assert "catch" in block, "Die Aktenliste darf nicht an dieser Nebensache hängen."


# ── Wenn niemand antwortet ───────────────────────────────────────────────────
#
# Aus der Kanzlei: „Erkennt den Bearbeiter nicht an. Failed to fetch."
#
# Das war keine abgelehnte Kennung, sondern ein Programm, das nicht mehr
# antwortete – und der Browser sagte es auf Englisch. „Failed to fetch"
# beantwortet keine der beiden Fragen, die der Bearbeiter dann hat: Woran liegt
# es, und was tue ich jetzt?


def _koerper(js: str, kopf: str) -> str:
    anfang = js.index(kopf)
    return js[anfang:js.index("\n}", anfang)]


def test_die_englische_browsermeldung_erreicht_den_bearbeiter_nicht(app_js):
    """`fetch` muss in einen eigenen Satz laufen, nicht ungefiltert hinaus."""
    koerper = _koerper(app_js, "async function api(")
    assert "try {" in koerper
    assert "NICHT_ERREICHBAR" in koerper


def test_der_satz_sagt_was_zu_tun_ist(app_js):
    anfang = app_js.index("const NICHT_ERREICHBAR =")
    satz = app_js[anfang:app_js.index(";", anfang)]
    for teil in ("antwortet nicht", "schwarze Fenster", "neu laden"):
        assert teil in satz


def test_der_satz_nennt_alle_startdateien(app_js):
    """Er nannte zwei von vier — und zwar die beiden für die Testakten.

    Am 23.09.2026 stand die Kanzlei vor genau dieser Meldung, nachdem sie
    START-JURNODES.bat gestartet hatte. Der Rat, START-DEMO.bat oder
    START-AWS.bat zu starten, wäre dort falsch gewesen: Beide arbeiten mit den
    erfundenen Testakten.
    """
    anfang = app_js.index("const NICHT_ERREICHBAR =")
    satz = app_js[anfang:app_js.index(";", anfang)]
    for name in ("START-DEMO", "START-AWS", "START-KANZLEI", "START-JURNODES"):
        assert name in satz, f"{name} fehlt in der Meldung."


def test_er_nennt_die_haeufigste_ursache_zuerst(app_js):
    """Die Startdateien öffnen den Browser, BEVOR das Programm bereit ist.
    Die erste Seite läuft deshalb regelmäßig ins Leere, und ein Neuladen
    genügt. Wer stattdessen die Startdatei neu ausführt, hat danach zwei
    Programme auf demselben Anschluss."""
    anfang = app_js.index("const NICHT_ERREICHBAR =")
    satz = app_js[anfang:app_js.index(";", anfang)]
    assert satz.index("neu laden") < satz.index("erneut ausfuehren")


def test_der_satz_steht_an_einer_stelle(app_js):
    """Anmeldeseite und Kopfzeile dürfen nicht zweierlei sagen."""
    assert app_js.count("const NICHT_ERREICHBAR =") == 1
    assert app_js.count("NICHT_ERREICHBAR") >= 3


def test_oben_in_der_ecke_steht_die_kurze_fassung(app_js):
    """Der ganze Satz sprengt die Kopfzeile – dort ist Platz für drei Wörter."""
    anfang = app_js.index("const NICHT_ERREICHBAR_KURZ =")
    kurz = app_js[anfang:app_js.index(";", anfang)]
    assert len(kurz.split('"')[1]) < 30


def test_die_leere_nutzerliste_bleibt_nicht_unerklaert(app_js):
    """Ohne Antwort stand die Anmeldeseite leer da, ohne ein Wort dazu."""
    assert "anmeldeFehler(NICHT_ERREICHBAR)" in _koerper(app_js, "async function nutzerlisteLaden(")


# ── Ein abgerissener Antwortstrom ────────────────────────────────────────────
#
# Der strömende Text ist die UNGEPRÜFTE Fassung; erst das Ereignis „fertig"
# bringt die belegte. Bricht der Strom vorher ab, blieb der Rohtext als
# scheinbar fertige Antwort stehen – ohne Beleg, ohne Fusszeile, ohne Warnung
# (PRUEFBERICHT-2026-09-16.md, Befund 3; im Browser nachgestellt).


def test_ohne_geprueftes_ende_bleibt_kein_rohtext_stehen(app_js):
    koerper = _koerper(app_js, "async function frageStellen(")
    assert "gepruefteAntwort" in koerper
    assert "if (!gepruefteAntwort)" in koerper
    # Entfernt werden muss er auch, nicht nur beklagt.
    nach = koerper[koerper.index("if (!gepruefteAntwort)"):]
    assert "strom.remove()" in nach


def test_der_abbruch_wird_gesagt_nicht_verschwiegen(app_js):
    """Eine still verschwundene Antwort sähe aus wie ein Bedienfehler."""
    koerper = _koerper(app_js, "async function frageStellen(")
    nach = koerper[koerper.index("if (!gepruefteAntwort)"):]
    assert "unvollständig" in nach
    assert "Belegprüfung" in nach


def test_auch_eine_abgerissene_verbindung_zaehlt_als_kein_ende(app_js):
    """Ohne try bliebe der Rohtext bei einem Netzabbruch stehen."""
    koerper = _koerper(app_js, "async function frageStellen(")
    leser = koerper[koerper.index("resp.body.getReader()"):]
    assert "try {" in leser
    assert "catch" in leser


# ── Eine leere Benutzerliste ─────────────────────────────────────────────────
#
# Aus der Kanzlei: „Wer arbeitet hier? *" – und darunter nichts. Eine leere
# Liste ohne ein Wort dazu lässt den Bearbeiter vor einer Seite stehen, die
# aussieht, als sei sie kaputt. Im AWS-Betrieb (404) ist sie richtig so, dort
# tippt man die Kennung. Örtlich ist sie ein Fehler.


def test_eine_leere_liste_bleibt_nicht_unerklaert(app_js):
    koerper = _koerper(app_js, "async function nutzerlisteLaden(")
    assert "if (!liste.length" in koerper
    assert "JUSPERFECT_NUTZER_DATEI" in koerper


def test_im_aws_betrieb_ist_die_leere_liste_richtig(app_js):
    """Dort gibt es diesen Weg nicht; der Server antwortet mit 404."""
    koerper = _koerper(app_js, "async function nutzerlisteLaden(")
    assert "404" in koerper


def test_der_hinweis_nennt_den_ausweg(app_js):
    """Eine Meldung, die nur klagt, hilft niemandem aus der Sackgasse."""
    koerper = _koerper(app_js, "async function nutzerlisteLaden(")
    assert "von Hand" in koerper
    assert "ra-weber" in koerper


# ── Die Anlaufzeit ───────────────────────────────────────────────────────────
#
# Aus der Kanzlei, 23.09.2026: „Am Anfang ist dieses Bild irritierend. F5 und
# es ist weg."
#
# Gemeint war der rote Kasten beim allerersten Aufruf. Die Startdateien öffnen
# den Browser, BEVOR das Programm bereit ist; beim ersten Start dauert das,
# weil Python und die Arbeitsumgebung erst hochkommen. Die Seite war also
# schneller als der Server – und meldete das als Störung.
#
# Wer eine Störung sieht, tut in aller Regel das Falsche: Er startet die
# Startdatei noch einmal und hat danach zwei Programme auf demselben Anschluss.


def test_die_seite_wartet_kurz_auf_das_programm(app_js):
    anfang = app_js.index("async function nutzerlisteLaden(")
    block = app_js[anfang:app_js.index("\n}", anfang)]
    assert "ANLAEUFE" in block, "Ein einziger Versuch ist beim ersten Start zu wenig."
    assert "setTimeout" in block


def test_sie_wartet_nicht_endlos(app_js):
    """Nach ein paar Sekunden ist es keine Anlaufzeit mehr, sondern ein Fehler
    – und dann soll er dastehen."""
    anfang = app_js.index("async function nutzerlisteLaden(")
    block = app_js[anfang:app_js.index("\n}", anfang)]
    assert "versuch === ANLAEUFE" in block
    assert "NICHT_ERREICHBAR" in block


def test_das_warten_ist_kein_roter_kasten(app_js, html):
    """Ein Programm, das gerade startet, ist keine Störung. Die Farbe soll
    erst wechseln, wenn es eine ist."""
    assert "function anmeldeHinweis(" in app_js
    anfang = app_js.index("function anmeldeHinweis(")
    block = app_js[anfang:app_js.index("\n}", anfang)]
    assert '"wartet"' in block
    styles = (STATISCH / "styles.css").read_text(encoding="utf-8")
    assert ".anmelde-fehler.wartet" in styles


def test_ein_echter_fehler_nimmt_die_wartefarbe_wieder_ab(app_js):
    """Sonst stünde die Störung in gedämpftem Grau da."""
    anfang = app_js.index("function anmeldeFehler(")
    block = app_js[anfang:app_js.index("\n}", anfang)]
    assert 'classList.remove("wartet")' in block
