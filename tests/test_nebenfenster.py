"""Ein Fenster auf den zweiten Bildschirm.

Aus der Kanzlei am 05.10.2026: „Vorschlag wäre auch Öffnen von Nebenfenstern in
eigener Ansicht, da ich in der Regel mit zwei Bildschirmen arbeite und die
Oberfläche mit drei Fenstern zu klein wird."

Gebaut als **Spiegel**, nicht als zweite Arbeitsfläche. Das Nebenfenster öffnet
keine eigene Sitzung, holt nichts selbst und schickt nichts zurück: Es zeigt,
was das Hauptfenster ihm durchgibt.

Der dritte Grund dafür ist der eigentliche: In einer Mandatsakte muss jederzeit
klar sein, **wo** gearbeitet wird. Ein zweites Fenster, in dem man auch
arbeiten kann, wäre ein zweiter Ort, an dem etwas geschieht – und der
Bearbeiter müsste beide im Kopf behalten. Am 02.10.2026 hat dieses Projekt
erlebt, was zwei gleichzeitige Vorgänge auf einer Akte anrichten.
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


class TestDerKnopf:
    def test_jedes_der_drei_fenster_laesst_sich_herausloesen(self, html: str) -> None:
        for name in ("chronologie", "gedaechtnis", "belege"):
            assert f'data-fenster-los="{name}"' in html, name

    def test_die_dokumentspalte_nicht(self, html: str) -> None:
        """Sie holt ihren Text selbst nach – ein Spiegel, der nachholen muss,
        ist kein Spiegel mehr. Später, wenn die Kanzlei es braucht."""
        assert 'data-fenster-los="dokument"' not in html

    def test_er_sagt_wofuer_er_da_ist(self, html: str) -> None:
        assert "zweiten Bildschirm" in html

    def test_herausloesen_klappt_im_hauptfenster_zu(self, app: str) -> None:
        """Das ist der Zweck: Platz schaffen. Bliebe es offen, hätte man
        dasselbe Fenster zweimal und keinen Zentimeter gewonnen."""
        block = re.search(r"function nebenfensterOeffnen\(name\) \{(.*?)\n\}",
                          app, re.S).group(1)
        assert "fensterSchliessen(name)" in block


class TestDerSpiegel:
    def test_das_nebenfenster_oeffnet_keine_eigene_sitzung(self, app: str) -> None:
        block = re.search(r"function alsNebenfensterEinrichten\(\) \{(.*?)\n\}",
                          app, re.S).group(1)
        assert "ladeStatus" not in block
        assert "api(" not in block

    def test_es_schickt_nur_zwei_nachrichten_und_beide_aendern_nichts(self, app: str) -> None:
        """Die Nachfrage beim Aufgehen und die Abmeldung beim Zugehen.

        Mehr darf von hier nicht ausgehen. Alles, was eine Akte ändern würde,
        gehört ins Hauptfenster – das ist der Unterschied zwischen einem
        Spiegel und einer zweiten Arbeitsfläche.
        """
        block = re.search(r"function alsNebenfensterEinrichten\(\) \{(.*?)\n\}",
                          app, re.S).group(1)
        gesendet = sorted(set(re.findall(r'postMessage\(\{ was: "([a-z-]+)"', block)))
        assert gesendet == ["bitte-stand", "ende"]

    def test_das_hauptfenster_antwortet_auf_die_nachfrage(self, app: str) -> None:
        """Es weiß nicht, dass es ein Nebenfenster gibt – also fragt dieses."""
        assert '=== "bitte-stand") nebenfensterGleichziehen()' in app

    def test_im_nebenfenster_wird_nichts_durchgegeben(self, app: str) -> None:
        """Sonst spiegelten sich zwei Fenster gegenseitig im Kreis."""
        block = re.search(r"function nebenfensterGleichziehen\(\) \{(.*?)\n\}",
                          app, re.S).group(1)
        assert "if (nebenfenster || !kanal) return;" in block


class TestWasDurchgegebenWird:
    """Nicht nur die Sitzung – sonst fehlen genau die neuen Zeilen."""

    def test_die_eintraege_der_analyse_gehen_mit(self, app: str) -> None:
        """Die Chronologie zeichnet aus ``sitzung`` **und** ``chronoAusAnalyse``.

        Ginge nur die Sitzung hinaus, zeigte das Nebenfenster eine Chronologie,
        der genau die Zeilen fehlen, die eine Analyse gerade gefunden hat – und
        das fällt niemandem auf, weil sie gefüllt aussieht.
        """
        block = re.search(r"function nebenfensterGleichziehen\(\) \{(.*?)\n\}",
                          app, re.S).group(1)
        for was in ("chronoAusAnalyse", "passagenIndex", "belegKennungen", "belegQuellen"):
            assert was in block, was

    def test_und_kommen_drueben_an(self, app: str) -> None:
        block = re.search(r"kanal\.onmessage = \(nachricht\) => \{(.*?)\n  \};",
                          app, re.S).group(1)
        for was in ("chronoAusAnalyse =", "passagenIndex =", "belegKennungen =", "belegQuellen ="):
            assert was in block, was

    def test_eine_menge_bleibt_eine_menge(self, app: str) -> None:
        """``belegKennungen`` ist ein Set; über den Kanal geht nur eine Liste."""
        hin = re.search(r"function nebenfensterGleichziehen\(\) \{(.*?)\n\}",
                        app, re.S).group(1)
        her = re.search(r"kanal\.onmessage = \(nachricht\) => \{(.*?)\n  \};",
                        app, re.S).group(1)
        assert "[...belegKennungen]" in hin
        assert "new Set(inhalt.belegKennungen || [])" in her


class TestDasFensterGehtZuUndWiederAuf:
    """Aus der Kanzlei am 05.10.2026: „Durch das Schließen des Fensters sollen
    natürlich keine Daten verloren gehen und ich kann es jederzeit wieder
    öffnen."

    Verlieren kann das Nebenfenster nichts – es hält nichts, es zeigt nur.
    Verloren war aber die **Ansicht**: Beim Herauslösen klappt das Hauptfenster
    sie zu, und wer das Nebenfenster dann schließt, stünde vor einer
    Oberfläche, in der die Chronologie fehlt und nichts sagt, warum.
    """

    def test_das_nebenfenster_meldet_sich_ab(self, app: str) -> None:
        block = re.search(r"function alsNebenfensterEinrichten\(\) \{(.*?)\n\}",
                          app, re.S).group(1)
        assert "beforeunload" in block
        assert 'was: "ende", name: nebenfenster' in block

    def test_und_das_hauptfenster_klappt_die_ansicht_wieder_auf(self, app: str) -> None:
        assert 'inhalt.was === "ende" && inhalt.name) fensterOeffnen(inhalt.name)' in app

    def test_ein_zweiter_klick_oeffnet_kein_zweites_fenster(self, app: str) -> None:
        """Der Browser gibt bei gleichem Namen dasselbe Fenster zurück.

        Es muss nur nach vorn geholt werden – sonst klickt jemand zweimal und
        sucht danach das Fenster, das hinter dem Hauptfenster liegt.
        """
        block = re.search(r"function nebenfensterOeffnen\(name\) \{(.*?)\n\}",
                          app, re.S).group(1)
        assert "`jusperfect-${name}`" in block
        assert "fenster.focus()" in block

    def test_nach_einem_neuladen_findet_das_nebenfenster_zurueck(self, app: str) -> None:
        """Ein Nebenfenster, das offen stand, fragt von sich aus nicht noch
        einmal nach – also meldet sich das Hauptfenster beim Start."""
        assert 'postMessage({ was: "hallo" })' in app
        block = re.search(r"kanal\.onmessage = \(nachricht\) => \{(.*?)\n  \};",
                          app, re.S).group(1)
        assert '=== "hallo"' in block
        hallo = block[block.index('=== "hallo"'):]
        assert 'was: "bitte-stand"' in hallo


class TestWennDieAkteZugeht:
    def test_das_hauptfenster_sagt_es(self, app: str) -> None:
        """Ein Nebenfenster, das weiter eine geschlossene Akte zeigt, wäre bei
        Mandatsakten die gefährlichste Art von Anzeige."""
        block = re.search(r"async function sitzungSchliessen\(\) \{(.*?)\n\}",
                          app, re.S).group(1)
        assert 'postMessage({ was: "zu" })' in block

    def test_und_das_nebenfenster_raeumt_alles_weg(self, app: str) -> None:
        block = re.search(r"kanal\.onmessage = \(nachricht\) => \{(.*?)\n  \};",
                          app, re.S).group(1)
        zu = block[block.index('=== "zu"'):]
        assert "sitzung = null" in zu
        for was in ("chronoAusAnalyse = []", "passagenIndex = {}",
                    "belegKennungen = new Set()", "belegQuellen = {}"):
            assert was in zu, was

    def test_und_sagt_dem_leser_was_los_ist(self, html: str) -> None:
        """Ein leeres Fenster ohne Erklärung sieht aus wie ein Fehler."""
        assert 'id="neben-leer"' in html
        assert "im Hauptfenster geöffnet" in html


class TestDieAnsicht:
    def test_genau_ein_abschnitt_je_nebenfenster(self, css: str) -> None:
        """Auch dann, wenn das Hauptfenster im gespeicherten Stand drei offen hat."""
        assert ":root[data-nebenfenster] .fenster { display: none !important; }" in css
        for wahl, id_ in (("chronologie", "fenster-chronologie"),
                          ("belege", "fenster-belege"),
                          ("gedaechtnis", "gedaechtnis-fenster")):
            assert f':root[data-nebenfenster="{wahl}"] #{id_}' in css

    def test_die_arbeitsflaeche_wird_erzwungen(self, css: str) -> None:
        """Derselbe Code zeigt beim Start erst die Anmeldeseite und blendet die
        Arbeitsfläche weg. Ein Stil, der mit ihm um ``hidden`` ringt, verliert
        irgendwann; einer, der ihn überschreibt, nicht."""
        block = re.search(r":root\[data-nebenfenster\] #flaeche,\s*"
                          r":root\[data-nebenfenster\] #spalte-rechts \{([^}]*)\}", css).group(1)
        assert "!important" in block

    def test_die_knoepfe_am_kopf_verschwinden(self, app: str, css: str) -> None:
        """Zuklappen und Herauslösen können hier nichts bewirken."""
        assert ":root[data-nebenfenster] .fenster-zu" in css
        block = re.search(r"function alsNebenfensterEinrichten\(\) \{(.*?)\n\}",
                          app, re.S).group(1)
        assert "data-fenster-zu=" in block and "data-fenster-los=" in block


class TestWennDerBrowserNichtMitmacht:
    def test_ohne_broadcastchannel_gibt_es_kein_nebenfenster(self, app: str) -> None:
        block = re.search(r"function nebenkanal\(\) \{(.*?)\n\}", app, re.S).group(1)
        assert 'typeof BroadcastChannel === "function"' in block
        assert "catch" in block

    def test_und_das_programm_sagt_es_statt_zu_schweigen(self, app: str) -> None:
        block = re.search(r"function nebenfensterOeffnen\(name\) \{(.*?)\n\}",
                          app, re.S).group(1)
        assert "keine Nebenfenster verbinden" in block

    def test_ein_unterdruecktes_fenster_wird_gemeldet(self, app: str) -> None:
        """Pop-up-Blocker sind der Normalfall, nicht die Ausnahme."""
        block = re.search(r"function nebenfensterOeffnen\(name\) \{(.*?)\n\}",
                          app, re.S).group(1)
        assert "Pop-ups" in block


class TestNichtsGehtNachDraussen:
    def test_der_kanal_bleibt_im_browser(self, app: str) -> None:
        """BroadcastChannel ist auf denselben Rechner und dieselbe Herkunft
        beschränkt. Für eine Mandatsakte ist das der ganze Punkt: Der Stand
        geht an das Fenster nebenan, nicht über das Netz."""
        assert 'const NEBENKANAL = "jusperfect-nebenfenster";' in app
        block = re.search(r"function nebenkanal\(\) \{(.*?)\n\}", app, re.S).group(1)
        assert "fetch(" not in block and "WebSocket" not in block

    def test_das_nebenfenster_laeuft_unter_derselben_adresse(self, app: str) -> None:
        block = re.search(r"function nebenfensterOeffnen\(name\) \{(.*?)\n\}",
                          app, re.S).group(1)
        assert "location.pathname" in block
        assert "http" not in block.replace("https", "")
