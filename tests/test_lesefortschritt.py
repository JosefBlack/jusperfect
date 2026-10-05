"""Der Balken, während die Dokumente gelesen werden.

Aus der Kanzlei am 02.10.2026: „55 Dokumente werden gelesen ... Dauert sehr
lange. Es wäre schön, wenn hier ein witziger Ladebalken erzeugt werden könnte."

Gebaut sind zwei Dinge, und das erste ist das wichtigere: **Der Balken zeigt
gezählte Dokumente, keine Schätzung.** Dafür liest die Oberfläche in Portionen
statt in einem Zug – ein Aufruf, der erst am Ende zurückkommt, kann unterwegs
nichts sagen.

Warum das hier festgehalten wird: Derselbe Tag hat zweimal vorgeführt, was eine
Anzeige wert ist, die nicht misst. Erst ein Aufruf, der ohne Fehlermeldung
nichts lieferte; dann ein Probewort, das rechts aus dem Blatt lief und von dem
nur 23 Zeichen ankamen. Ein Balken, der bloß läuft, wäre dasselbe noch einmal –
nur dass ihn niemand je dabei erwischt.
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
def html() -> str:
    return (STATISCH / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def css() -> str:
    return (STATISCH / "styles.css").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def lesen(app: str) -> str:
    treffer = re.search(r"async function dokumenteInPortionenLesen\(dazu\) \{(.*?)\n\}\n",
                        app, re.S)
    assert treffer, "Die Funktion gibt es nicht mehr."
    return treffer.group(1)


class TestErZaehlt:
    def test_gelesen_wird_hochgezaehlt_und_nicht_geschaetzt(self, lesen: str) -> None:
        assert "gelesen += teil.length" in lesen

    def test_je_portion_geht_ein_eigener_aufruf_hinaus(self, lesen: str) -> None:
        """Sonst gäbe es nichts zu zählen – das ist der ganze Umbau."""
        assert "dazu.slice(i, i + LESEPORTION)" in lesen
        assert "dokument_ids: teil" in lesen

    def test_der_anteil_kommt_aus_den_zahlen(self, app: str) -> None:
        block = re.search(r"function lesefortschritt\(.*?\) \{(.*?)\n\}", app, re.S).group(1)
        assert "Math.round((gelesen / gesamt) * 100)" in block
        assert "von ${gesamt} Dokumenten gelesen" in block

    def test_die_erste_portion_schaetzt_noch_keine_dauer(self, lesen: str) -> None:
        """Sie trägt den Verbindungsaufbau mit und ist regelmäßig die langsamste.

        Eine Restzeit aus einer einzigen Messung schwankt um ein Vielfaches.
        Lieber nichts anzeigen als eine Zahl, der niemand glauben kann.
        """
        assert "portionen > 1 ? verstrichen / gelesen : 0" in lesen

    def test_ohne_messung_steht_keine_dauer_da(self, app: str) -> None:
        block = re.search(r"function lesefortschritt\(.*?\) \{(.*?)\n\}", app, re.S).group(1)
        assert "sekundenJeDokument && offen > 0" in block


class TestErVerschwindetAuchBeiEinemFehler:
    def test_das_aufraeumen_steht_im_finally(self, lesen: str) -> None:
        """Sonst bliebe ein Balken stehen, hinter dem nichts mehr arbeitet."""
        nach = lesen[lesen.index("} finally {"):]
        assert '$("lesefortschritt").hidden = true' in nach
        assert '$("lese-balken").style.width = "0%"' in nach


class TestFuerWenigeDokumenteLohntErNicht:
    def test_bis_zwei_genuegt_die_meldung(self, lesen: str) -> None:
        """Ein Balken, der einmal aufblitzt, ist Unruhe und keine Auskunft."""
        assert "if (gesamt <= 2)" in lesen
        assert "laeuft(" in lesen


class TestAnhalten:
    def test_die_laufende_portion_wird_zu_ende_gelesen(self, app: str) -> None:
        """Sie ist bezahlt – bei einem Scan sogar mit Texterkennung."""
        block = re.search(r'\$\("lese-anhalten"\)\.addEventListener\("click", \(ev\) => \{(.*?)\n  \}\);',
                          app, re.S).group(1)
        assert "lesenAbbrechen = true" in block
        assert "ev.target.disabled = true" in block

    def test_die_schleife_fragt_vor_jeder_portion(self, lesen: str) -> None:
        assert "!lesenAbbrechen" in lesen

    def test_das_gelesene_bleibt_und_wird_gesagt(self, lesen: str) -> None:
        assert "bleiben in der Arbeitsakte" in lesen


class TestKeinDurcheinanderBeimAktenwechsel:
    """Aus der Kanzlei am 02.10.2026: „Bin in dem Programm gesprungen während
    des Downloads, danach hatte ich das Gefühl, dass es Chaos gab. Keine
    saubere Trennung."

    Das Gefühl war richtig, und es ist eine Folge der Änderung vom selben Tag.
    Vorher ging der ganze Stapel in **einem** Aufruf hinaus – wer dazwischen
    klickte, hatte ein Fenster von Sekunden. Seit in Portionen gelesen wird,
    dauert es Minuten.

    Inhaltlich konnte dabei nichts Fremdes in eine Akte geraten: Der Server
    prüft bei jedem Dokument, ob es zu der Akte gehört, deren Sitzung gefragt
    wird. Auf dem Schirm sah es trotzdem nach Durcheinander aus – und eine
    Oberfläche, die bei Mandatsakten so aussieht, ist nicht hinnehmbar.

    Drei Riegel, und alle drei stehen hier fest.
    """

    def test_der_vorgang_merkt_sich_seine_sitzung(self, lesen: str) -> None:
        """Er schickt an die Sitzung, mit der er begonnen hat – nicht an die aktuelle."""
        assert "const meine = sitzung.sitzung.id" in lesen
        assert "/api/sitzungen/${meine}/dokumente" in lesen

    def test_eine_antwort_zur_falschen_akte_wird_verworfen(self, lesen: str) -> None:
        """Zwischen Absenden und Antwort liegen Sekunden."""
        assert "sitzung.sitzung.id !== meine" in lesen
        # Erst pruefen, DANN uebernehmen - andersherum waere die Pruefung Zierde.
        assert lesen.index("!== meine") < lesen.index("sitzung = antwort")

    def test_die_wege_aus_der_akte_werden_gesperrt(self, lesen: str) -> None:
        assert "wegeSperren(true)" in lesen
        assert "wegeSperren(false)" in lesen

    def test_die_sperre_wird_auch_bei_einem_fehler_geloest(self, lesen: str) -> None:
        nach = lesen[lesen.index("} finally {"):]
        assert "wegeSperren(false)" in nach
        assert 'liestGerade = ""' in nach

    def test_gesperrt_werden_nur_die_beiden_wege_hinaus(self, app: str) -> None:
        """Lesen, Blättern und Nachsehen stören nicht und bleiben offen."""
        block = re.search(r"function wegeSperren\(sperren\) \{(.*?)\n\}",
                          app, re.S).group(1)
        assert '"akte-wechseln", "sitzung-schliessen"' in block

    def test_der_aktenwechsel_hat_einen_eigenen_riegel(self, app: str) -> None:
        """Ein gesperrter Knopf ist eine Bitte; das hier ist die Zusage.

        Wer den Knopf über die Tastatur oder einen zweiten Tab doch erreicht,
        läuft in diese Prüfung.
        """
        block = re.search(r"async function akteWechseln\(\) \{(.*?)\n\}",
                          app, re.S).group(1)
        assert "if (liestGerade)" in block
        assert block.index("liestGerade") < block.index("sitzungSchliessen")

    def test_und_sagt_was_zu_tun_ist(self, app: str) -> None:
        block = re.search(r"async function akteWechseln\(\) \{(.*?)\n\}",
                          app, re.S).group(1)
        assert "anhalten" in block

    def test_ein_gesperrter_knopf_sieht_auch_so_aus(self, css: str) -> None:
        """Erst nicht beachtet, im Browser aufgefallen.

        Die beiden Knöpfe waren gesperrt und von den offenen nicht zu
        unterscheiden. Ein Klick, auf den nichts geschieht, sieht aus wie ein
        hängendes Programm – und davon hatte dieser Tag genug.
        """
        block = re.search(r"\.akte-wechseln:disabled \{([^}]*)\}", css).group(1)
        assert "opacity" in block
        assert "not-allowed" in block

    def test_und_leuchtet_nicht_mehr_beim_darueberfahren(self, css: str) -> None:
        assert ".akte-wechseln:hover:not(:disabled)" in css


class TestDieSprueche:
    """Sie vertreiben die Zeit – und sagen nebenbei, warum es dauert."""

    def test_es_gibt_genug_davon(self, app: str) -> None:
        block = re.search(r"const LESESPRUECHE = \[(.*?)\n\];", app, re.S).group(1)
        assert block.count('",') + 1 >= 8

    def test_keiner_handelt_von_einer_akte(self, app: str) -> None:
        """Auf diesem Schirm steht nichts Erfundenes über ein Mandat.

        Ein Spruch, der klingt wie aus der Akte, ist auf dem Bildschirm einer
        Kanzlei kein Scherz, sondern eine Verwechslungsgefahr.
        """
        block = re.search(r"const LESESPRUECHE = \[(.*?)\n\];", app, re.S).group(1).lower()
        for wort in ("mandant", "gegner", "beklagt", "kläger", "klaeger",
                     "aktenzeichen", "€", "euro"):
            assert wort not in block, f"Das Wort {wort!r} steht in einem Spruch."

    def test_sie_wechseln_mit_jeder_portion(self, lesen: str) -> None:
        assert "sprueche[portionen % sprueche.length]" in lesen


class TestDieAnzeige:
    def test_sie_steht_im_html_und_ist_zuerst_verborgen(self, html: str) -> None:
        assert 'id="lesefortschritt"' in html
        assert re.search(r'id="lesefortschritt"[^>]*\bhidden\b', html)

    def test_vorleseprogramme_bekommen_sie_mit(self, html: str) -> None:
        """Eine Zahl, die sich ändert, ohne dass es jemand erfährt, ist keine."""
        zeile = re.search(r'<div id="lesefortschritt"[^>]*>', html).group(0)
        assert 'role="status"' in zeile
        assert 'aria-live="polite"' in zeile

    def test_der_platz_fuer_den_spruch_steht_fest(self, css: str) -> None:
        """Sonst springt die Anzeige, sobald ein kürzerer Satz kommt."""
        block = re.search(r"\.lese-spruch \{([^}]*)\}", css).group(1)
        assert "min-height" in block

    def test_wer_keine_bewegung_will_bekommt_keine(self, css: str) -> None:
        assert "prefers-reduced-motion" in css
