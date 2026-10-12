"""Das Aktengedächtnis-Fenster ist nach Ordnern gegliedert — und zwar zuerst.

Aus der Kanzlei, 12.10.2026: „Erst kommt das Aktengedächtnis mit anhaken."

Die Gliederung nach Ordnern stand seit dem 12.10.2026 im Dokumentfenster
(`explorer-dialog`). Angehakt wird im Arbeitsablauf aber **zuerst** im
Aktengedächtnis-Fenster (`ged-dialog`): Ohne Gedächtnis hat die Arbeitsakte
nichts, woraus sie schöpfen könnte. Dort standen die 55 Einträge aus acht
Ordnern weiter in einer Reihe — an der Stelle also, an der die Gliederung am
meisten trägt.

**Was hier anders ist als im Dokumentfenster:** Die Zahl neben der
Überschrift sagt nicht, wie groß der Ordner ist, sondern wie viele darin
**noch fehlen** — das ist die Frage, die man in diesem Fenster hat. Und der
Stapelknopf nimmt nur die fehlenden: Was schon im Gedächtnis liegt, darf
nicht ein zweites Mal aufgenommen werden, sonst zahlt die Kanzlei das Einlesen
doppelt.

**Nebenbei behoben:** „alle fehlenden" nahm bisher die ganze Akte, auch wenn
der Filter nur den Gegner stehen ließ. Im Dokumentfenster ist genau das seit
dem 29.09.2026 ausdrücklich geprüft; hier war es nie geprüft und war falsch.

Geprüft wird nicht nur der Wortlaut des Quelltextes: Die beiden Funktionen
werden mit einem winzigen Ersatz-DOM in node ausgeführt und ihr Ergebnis
gemessen. Ein Quelltext, der die richtigen Wörter enthält und das Falsche tut,
käme sonst durch.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"


@pytest.fixture(scope="module")
def app_js() -> str:
    return (STATISCH / "app.js").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def html() -> str:
    return (STATISCH / "index.html").read_text(encoding="utf-8")


def _funktion(js: str, name: str) -> str:
    """Den Quelltext einer Funktion der obersten Ebene herausschneiden.

    Von ``function name(`` bis zu der Zeile, die allein aus ``}`` besteht —
    das ist in dieser Datei das Ende einer Funktion der obersten Ebene.
    """
    treffer = re.search(rf"^function {re.escape(name)}\(.*?^\}}$", js,
                        re.S | re.M)
    assert treffer is not None, f"Die Funktion {name} steht nicht in app.js."
    return treffer.group(0)


# Ein Ersatz-DOM. Es kann nur, was die beiden Funktionen anfassen; alles
# andere soll es auch nicht koennen, sonst prueft es sich selbst.
_ERSATZ_DOM = """
function _el(tag) {
  return {
    tag, kinder: [], className: "", textContent: "", title: "", type: "",
    klick: null,
    classList: { liste: [], add(k) { this.liste.push(k); } },
    append(...k) { this.kinder.push(...k); },
    appendChild(k) { this.kinder.push(k); return k; },
    addEventListener(art, fn) { if (art === "click") this.klick = fn; },
  };
}
const document = { createElement: _el };
let gedAuswahl = new Set();
let neuGezeichnet = 0;
function gedExplorerZeichnen() { neuGezeichnet++; }

/** Was von einer Ordnerzeile zu sehen ist. */
function _lesen(li) {
  const knopf = li.kinder.find((k) => k.tag === "button") || null;
  return {
    name: li.kinder[0].textContent,
    zahl: li.kinder[1].textContent,
    klasse: li.className,
    wurzel: li.classList.liste.includes("wurzel"),
    knopf: knopf ? { text: knopf.textContent, titel: knopf.title } : null,
    _knopf: knopf,
  };
}

function _dok(id, ordner) { return { id, ordner, titel: id + ".pdf" }; }
function _drin(...ids) { return new Map(ids.map((i) => [i, { dokument_id: i }])); }
"""


def _node(js: str, programm: str) -> dict:
    """Die echten Funktionen aus app.js mit dem Ersatz-DOM laufen lassen."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node ist auf diesem Rechner nicht vorhanden")
    quelle = "\n".join([
        _ERSATZ_DOM,
        _funktion(js, "explorerNachOrdnern"),
        _funktion(js, "gedOrdnerzeile"),
        'const EAKTE_ORDNER = "E-Akte";',
        programm,
    ])
    ergebnis = subprocess.run([node, "--input-type=module", "-e", quelle],
                              capture_output=True, text=True)
    assert ergebnis.returncode == 0, ergebnis.stderr
    return json.loads(ergebnis.stdout)


class TestDieUeberschriftSagtWasNochFehlt:
    """Die Zahl beantwortet die Frage, die man in diesem Fenster hat."""

    def test_von_drei_dokumenten_fehlen_zwei(self, app_js: str) -> None:
        erg = _node(app_js, """
          const dazu = [_dok("a", "Gericht"), _dok("b", "Gericht"), _dok("c", "Gericht")];
          const li = gedOrdnerzeile("Gericht", dazu, _drin("b"));
          console.log(JSON.stringify(_lesen(li)));
        """)
        assert erg["name"] == "Gericht"
        assert erg["zahl"] == "2 von 3 fehlen"

    def test_liegt_alles_drin_steht_es_da(self, app_js: str) -> None:
        erg = _node(app_js, """
          const dazu = [_dok("a", "Gericht"), _dok("b", "Gericht")];
          const li = gedOrdnerzeile("Gericht", dazu, _drin("a", "b"));
          console.log(JSON.stringify(_lesen(li)));
        """)
        assert erg["zahl"] == "2 Dokumente · im Gedächtnis"

    def test_ein_einzelnes_dokument_heisst_nicht_dokumente(self, app_js: str) -> None:
        erg = _node(app_js, """
          const li = gedOrdnerzeile("Gericht", [_dok("a", "Gericht")], _drin("a"));
          console.log(JSON.stringify(_lesen(li)));
        """)
        assert erg["zahl"] == "1 Dokument · im Gedächtnis"

    def test_der_aktenordner_selbst_hat_einen_namen(self, app_js: str) -> None:
        """Ein leerer Ordner ist kein Ordner, sondern die Akte."""
        erg = _node(app_js, """
          const li = gedOrdnerzeile("", [_dok("a", "")], _drin());
          console.log(JSON.stringify(_lesen(li)));
        """)
        assert erg["name"] == "Unmittelbar im Aktenordner"
        assert erg["wurzel"] is True


class TestDerStapelknopf:
    """Er nimmt die fehlenden — und nur die."""

    def test_er_hakt_nur_die_fehlenden_an(self, app_js: str) -> None:
        """Was schon im Gedächtnis liegt, würde sonst doppelt eingelesen."""
        erg = _node(app_js, """
          const dazu = [_dok("a", "Gericht"), _dok("b", "Gericht"), _dok("c", "Gericht")];
          const li = gedOrdnerzeile("Gericht", dazu, _drin("b"));
          _lesen(li)._knopf.klick();
          console.log(JSON.stringify({ gewaehlt: [...gedAuswahl].sort(),
                                       gezeichnet: neuGezeichnet }));
        """)
        assert erg["gewaehlt"] == ["a", "c"]
        assert erg["gezeichnet"] == 1, "Nach dem Klick muss neu gezeichnet werden."

    def test_ohne_fehlende_gibt_es_keinen_knopf(self, app_js: str) -> None:
        """Ein Knopf ohne Wirkung ist ein Versprechen, das nicht hält."""
        erg = _node(app_js, """
          const dazu = [_dok("a", "Gericht"), _dok("b", "Gericht")];
          const li = gedOrdnerzeile("Gericht", dazu, _drin("a", "b"));
          console.log(JSON.stringify(_lesen(li)));
        """)
        assert erg["knopf"] is None

    def test_beim_zweiten_mal_nimmt_er_die_haken_weg(self, app_js: str) -> None:
        erg = _node(app_js, """
          const dazu = [_dok("a", "Gericht"), _dok("b", "Gericht")];
          const drin = _drin();
          _lesen(gedOrdnerzeile("Gericht", dazu, drin))._knopf.klick();
          const zweite = _lesen(gedOrdnerzeile("Gericht", dazu, drin));
          const text = zweite.knopf.text;
          zweite._knopf.klick();
          console.log(JSON.stringify({ text, danach: [...gedAuswahl] }));
        """)
        assert erg["text"] == "Haken entfernen"
        assert erg["danach"] == []

    def test_er_nennt_den_ordner_im_hinweis(self, app_js: str) -> None:
        """Acht Ordner, acht gleich beschriftete Knöpfe — ohne Namen ein Rätsel."""
        erg = _node(app_js, """
          const li = gedOrdnerzeile("Schriftsätze/Gegenseite", [_dok("a", "x")], _drin());
          console.log(JSON.stringify(_lesen(li)));
        """)
        assert "Schriftsätze/Gegenseite" in erg["knopf"]["titel"]

    def test_er_schliesst_den_dialog_nicht(self, app_js: str) -> None:
        """Das Formular trägt method="dialog" — ein Knopf ohne type schließt."""
        knopf = _funktion(app_js, "gedOrdnerzeile")
        assert 'knopf.type = "button"' in knopf


class TestDieGliederungIstDieselbeWieNebenan:
    """Zwei Fenster, eine Lesereihenfolge — sonst sucht man zweimal anders."""

    def test_die_eakte_steht_hinten_und_der_aktenordner_vorn(self, app_js: str) -> None:
        erg = _node(app_js, """
          const sichtbar = [_dok("m", "E-Akte"), _dok("g", "Gericht"),
                            _dok("w", ""), _dok("a", "Abrechnung")];
          console.log(JSON.stringify(explorerNachOrdnern(sichtbar).map((g) => g[0])));
        """)
        assert erg == ["", "Abrechnung", "Gericht", "E-Akte"]

    def test_das_fenster_benutzt_dieselbe_gruppierung(self, app_js: str) -> None:
        zeichnen = _funktion(app_js, "gedExplorerZeichnen")
        assert "explorerNachOrdnern(sichtbar)" in zeichnen
        assert "gedOrdnerzeile" in zeichnen

    def test_ein_einziger_ordner_ist_keine_gliederung(self, app_js: str) -> None:
        zeichnen = _funktion(app_js, "gedExplorerZeichnen")
        assert "gruppen.length > 1" in zeichnen


class TestAlleFehlendenNimmtNurDieSichtbaren:
    """„Gegner" im Filter und dann ein Klick hieß: die ganze Akte."""

    def test_der_knopf_geht_von_den_sichtbaren_aus(self, app_js: str) -> None:
        block = re.search(
            r'\$\("ged-alle-fehlenden"\)\.addEventListener\("click", \(\) => \{(.*?)\n  \}\);',
            app_js, re.S).group(1)
        assert "gedSichtbarFehlende()" in block
        assert "gedFehlende()" not in block

    def test_die_sichtbaren_fehlenden_gehen_durch_den_filter(self, app_js: str) -> None:
        funktion = _funktion(app_js, "gedSichtbarFehlende")
        assert 'suchbegriffe("ged-suche")' in funktion
        assert "dokumentPasst" in funktion

    def test_der_satz_zaehlt_weiter_die_ganze_akte(self, app_js: str) -> None:
        """„3 fehlen noch" darf nicht vom Filter abhängen — das wäre gelogen."""
        fenster = _funktion(app_js, "gedaechtnisFensterZeigen")
        assert "gedFehlende()" in fenster
        assert "gedSichtbarFehlende()" not in fenster


class TestDasFensterSagtEsAuch:
    """Was man nicht liest, findet man nicht."""

    def test_der_hinweis_nennt_die_gliederung(self, html: str) -> None:
        ged = html[html.index('<dialog id="ged-dialog"'):
                   html.index('<dialog id="referenzen-dialog"')]
        sichtbar = re.sub(r"<!--.*?-->", "", ged, flags=re.S)
        assert "nach Ordnern" in sichtbar

    def test_der_filter_nennt_den_ordner(self, html: str) -> None:
        ged = html[html.index('<dialog id="ged-dialog"'):
                   html.index('<dialog id="referenzen-dialog"')]
        platzhalter = re.search(r'id="ged-suche".*?placeholder="([^"]*)"', ged, re.S)
        assert platzhalter is not None
        assert "Ordner" in platzhalter.group(1)
