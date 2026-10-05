"""Explorer-Suche und die sichtbare Fundstelle.

Aus der Kanzlei: „Setze eine Explorer-Suche um" - bei acht Dokumenten scrollt
man, bei fünfzig nicht mehr. Und: „noch besser wäre es, wenn der Mausklick auf
die Quelle den Abschnitt farblich markieren würde." Das tat er bereits - in
einem zarten Türkis, das in einem langen Dokument nicht auffiel; und stand der
Dokumentfilter auf einem anderen Dokument, kam statt der Markierung eine rote
Meldung.

Beides ist an einem echten Chromium gemessen (scratchpad/suche_markierung.mjs,
markierung.mjs): „gegner" filtert 50 auf 20, „bautagebuch juni" auf genau
eines, „alle ->" nimmt nur die Sichtbaren; der Klick auf einen Beleg schaltet
den Filter auf das richtige Dokument um und markiert bernsteinfarben.
Hier bleibt festgehalten, was dabei nicht verlorengehen darf.
"""

from __future__ import annotations

import re
import unittest
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


class TestSuche:
    def test_beide_explorer_haben_ein_suchfeld(self, html: str) -> None:
        assert 'id="explorer-suche"' in html
        assert 'id="ged-suche"' in html

    def test_ein_suchfeld_ist_ein_suchfeld(self, html: str) -> None:
        """type=search bringt das kleine x zum Leeren mit."""
        assert 'type="search" id="explorer-suche"' in html

    def test_jedes_wort_muss_passen(self, app: str) -> None:
        """„gegner 2026-05" meint beides, nicht eines von beiden."""
        anfang = app.index("function dokumentPasst(")
        block = app[anfang:anfang + 400]
        assert "begriffe.every(" in block
        for feld in ("titel", "datum", "kategorie"):
            assert feld in block

    def test_alle_rein_nimmt_nur_die_sichtbaren(self, app: str) -> None:
        """Sonst legt „Gegner" + „alle ->" doch die ganze Akte hinein."""
        block = re.search(r'\$\("alle-rein"\)\.addEventListener\("click", \(\) => \{(.*?)\n  \}\);',
                          app, re.S).group(1)
        assert "explorerSichtbar()" in block
        assert "explorer.karte" not in block
        assert 'for (const d of explorerSichtbar()) explorer.gewaehlt.delete(d.id)' in app
        assert "for (const id of explorer.karte.keys()) explorer.gewaehlt.add(id)" not in app

    def test_die_zahl_zeigt_gefiltert_von_gesamt(self, app: str, css: str) -> None:
        assert "`${sichtbar}/${gesamt}`" in app
        assert ".explorer-kopf .zahl.gefiltert" in css

    def test_die_suche_faengt_beim_oeffnen_leer_an(self, app: str) -> None:
        """Ein Filter von gestern darf heute nicht unbemerkt die halbe Akte ausblenden."""
        stelle = app.index('$("explorer-dialog").showModal();')
        davor = app[max(0, stelle - 200):stelle]
        assert 'suche.value = ""' in davor

    def test_der_gedaechtnis_explorer_filtert_beide_spalten(self, app: str) -> None:
        anfang = app.index("function gedExplorerZeichnen(")
        ende = app.index("function gedUmfangZeigen(")
        block = app[anfang:ende]
        assert block.count("dokumentPasst(") == 2


class TestMarkierung:
    def test_bernstein_statt_tuerkis(self, css: str) -> None:
        """Dieselbe Farbe wie der Punkt auf dem j: der Beleg."""
        stelle = css.index(".passage.markiert {")
        zeile = css[stelle:stelle + 120]
        assert "var(--amber-hell)" in zeile
        assert "var(--amber)" in zeile
        assert "var(--akzent-hell)" not in zeile

    def test_ein_kurzer_puls_beim_anspringen(self, css: str) -> None:
        assert "@keyframes fundstelle-puls" in css
        assert ".passage.markiert.puls" in css

    def test_der_klick_schaltet_auf_das_richtige_dokument_um(self, app: str) -> None:
        """Statt der roten Meldung „nicht sichtbar"."""
        anfang = app.index("function passageMarkieren(")
        ende = app.index("function fusszeile(")
        block = app[anfang:ende]
        assert "filter.value = passagenIndex[kennung].dokument_id" in block
        assert "zeigeDokument(filter.value)" in block
        assert "im geladenen Text nicht sichtbar" not in block

    def test_der_angeklickte_beleg_bleibt_erkennbar(self, app: str, css: str) -> None:
        assert 'chip.classList.add("aktiv")' in app
        assert ".beleg.aktiv" in css
        assert "passageMarkieren(kennung, chip, aussage)" in app

    def test_nur_eine_markierung_zugleich(self, app: str) -> None:
        """Das Aufräumen liegt jetzt in markierungenLoeschen – es muss aber
        weiterhin am Anfang jedes Markierens stehen, und es muss den gefärbten
        Text der vorigen Passage zurücksetzen."""
        anfang = app.index("function passageMarkieren(")
        block = app[anfang:anfang + 400]
        assert "markierungenLoeschen()" in block
        loeschen = app[app.index("function markierungenLoeschen("):app.index("function passageMarkieren(")]
        assert 'querySelectorAll(".passage.markiert")' in loeschen
        assert "satzEl.textContent = p.text" in loeschen, "Sonst bliebe die Färbung der vorigen Stelle stehen."
        assert 'querySelectorAll(".beleg.aktiv")' in app


class FilterBeimOeffnen(unittest.TestCase):
    """Der Filter der vorigen Akte darf nicht in der nächsten weiterwirken.

    Aus der Kanzlei: „bei der großen akte … nimmt auch nur 4 dokumente rüber
    von den 50". Die Reihenfolge war verkehrt herum:

        explorerRendern();
        const suche = $("explorer-suche"); if (suche) suche.value = "";

    Gezeichnet wurde also noch nach dem alten Filter, und erst danach wurde
    das Feld geleert. Man sah eine Handvoll Dokumente, daneben ein leeres
    Suchfeld – und keinen Grund für die Lücke.
    """

    def test_geleert_wird_vor_dem_zeichnen(self):
        js = (Path(__file__).resolve().parent.parent
              / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")
        block = re.search(r"function explorerStarten\(initial\) \{(.*?)\n\}", js, re.S).group(1)
        leeren = block.index('suche.value = ""')
        zeichnen = block.index("explorerRendern()")
        self.assertLess(leeren, zeichnen,
                        "Der Filter wird erst nach dem Zeichnen geleert.")
