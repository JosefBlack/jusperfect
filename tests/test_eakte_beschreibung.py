"""Die Beschreibung des Herstellers lesen, statt Pfade zu erfinden.

Aus der Kanzlei am 05.10.2026: „Die Korrespondenz bei jurnodes und die Vermerke
finden sich in der E-Akte. Vielleicht ist das die Lösung."

Damit ist es **eine** Frage und nicht zwei. Zwei Dinge standen offen — wo die
Vermerke liegen (Aufgabe 2, seit dem 28.09.2026) und warum der
Korrespondenzordner fremde Schriftstücke führt (Befund vom 05.10.2026). Liegen
beide in der E-Akte, erklärt das auch den zweiten Punkt: Das Feld
`correspondenceFolderId` zeigt dann gar nicht auf die Korrespondenz dieser
Akte, weil die Korrespondenz überhaupt nicht im Dateisystem liegt.

**Geraten wird deshalb trotzdem nicht.** Sechzehn Pfadnamen für die E-Akte sind
am 01.10.2026 geprüft worden, alle 404; die Pfade für die Beschreibung ebenso —
sechs unterhalb der Zugangskennung und vierundzwanzig darüber. Regel 10 gilt: bei Dritten warten, nicht raten.

Was es stattdessen gibt: **Die Kanzlei hat die Beschreibung.** Am 23.09.2026
hat sie die OpenAPI-Beschreibung ihres Servers geliefert; daraus sind die
Pfade abgeschrieben, mit denen das Programm heute arbeitet. Liegt diese Datei
noch auf einem Rechner, beantwortet sie die Frage in einem Lauf — ohne Netz,
ohne Zugang und ohne den Hersteller.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from jusperfect.jurnodes.http_adapter import Endpunkte
from jusperfect.jurnodestest import (
    _beschreibung_aus_datei,
    _beschreibung_auswerten,
    _EAKTE_WOERTER,
    _ohne_trenner,
)

ENDPUNKTE = Endpunkte()


def _beschreibung(*pfade: str) -> dict:
    return {"openapi": "3.0.1", "paths": {pfad: {"get": {}} for pfad in pfade}}


def _datei(ordner: Path, inhalt) -> str:
    ziel = ordner / "beschreibung.json"
    ziel.write_text(json.dumps(inhalt), encoding="utf-8")
    return str(ziel)


class TestSieFindetDieEAkte:
    def test_sie_erkennt_den_pfad_auch_mit_bindestrich(self, capsys) -> None:
        """Der Fund vom 05.10.2026.

        Der Hersteller schreibt `electronic-file`, die Wortliste hieß
        `electronicfile` — und damit ging beim ersten Versuch genau der Pfad
        durch, auf den es ankam. Verglichen wird seitdem ohne Trennzeichen.
        """
        _beschreibung_auswerten(_beschreibung("/electronic-file/search"), ENDPUNKTE)
        assert "/electronic-file/search" in capsys.readouterr().out

    @pytest.mark.parametrize("pfad", [
        "/electronic-file/search", "/electronicFile/search", "/record/efile",
        "/record/correspondence/search", "/korrespondenz/search",
        "/record/note", "/mail/search", "/record/history",
    ])
    def test_sie_hebt_hervor_was_nach_e_akte_klingt(self, pfad: str, capsys) -> None:
        _beschreibung_auswerten(_beschreibung("/record/search", pfad), ENDPUNKTE)
        ausgabe = capsys.readouterr().out
        hervorgehoben = ausgabe.split("klingen:")[1]
        assert pfad in hervorgehoben
        assert "/record/search" not in hervorgehoben

    def test_sie_sagt_es_auch_wenn_nichts_passt(self, capsys) -> None:
        """Schweigen läse sich wie „nicht nachgesehen"."""
        _beschreibung_auswerten(_beschreibung("/record/search", "/todo/search"),
                                ENDPUNKTE)
        ausgabe = capsys.readouterr().out
        assert "Kein Pfad traegt eines dieser Woerter" in ausgabe
        # Und nennt die Wörter, nach denen gesucht wurde – sonst ist der Befund
        # nicht nachprüfbar.
        assert "korrespondenz" in ausgabe

    def test_sie_zeigt_jeden_pfad_nicht_nur_die_treffer(self, capsys) -> None:
        """Wer die Liste sieht, erkennt auch einen Pfad, an den die Wortliste
        nicht gedacht hat."""
        _beschreibung_auswerten(
            _beschreibung("/record/search", "/todo/search", "/zettelkasten"),
            ENDPUNKTE)
        ausgabe = capsys.readouterr().out
        assert "3 Pfade stehen darin" in ausgabe
        for pfad in ("/record/search", "/todo/search", "/zettelkasten"):
            assert pfad in ausgabe

    def test_sie_nennt_die_verfahren_je_pfad(self, capsys) -> None:
        daten = {"openapi": "3.0.1",
                 "paths": {"/record/note": {"get": {}, "post": {}}}}
        _beschreibung_auswerten(daten, ENDPUNKTE)
        zeile = [z for z in capsys.readouterr().out.splitlines()
                 if "/record/note" in z and "GET" in z][0]
        assert "GET" in zeile and "POST" in zeile


class TestSieLiestAuchDenParameterDerVermerke:
    def test_der_pflichtparameter_steht_mit_art_dabei(self, capsys) -> None:
        """Die Frage, an der zwei Prüfbogenläufe hängengeblieben sind: Welche
        Zahl ist mit `id` gemeint?"""
        daten = {"openapi": "3.0.1", "paths": {ENDPUNKTE.vermerke: {"get": {
            "parameters": [{"name": "id", "in": "query", "required": True,
                            "schema": {"type": "integer"}}]}}}}
        _beschreibung_auswerten(daten, ENDPUNKTE)
        ausgabe = capsys.readouterr().out
        assert "id [query, integer] (Pflicht)" in ausgabe


class TestSieBrauchtWederNetzNochZugang:
    def test_eine_datei_genuegt(self, tmp_path: Path, capsys) -> None:
        pfad = _datei(tmp_path, _beschreibung("/electronic-file/search"))
        assert _beschreibung_aus_datei(pfad, ENDPUNKTE) is True
        assert "/electronic-file/search" in capsys.readouterr().out

    def test_eine_fehlende_datei_sagt_das_und_bricht_nicht_ab(
        self, tmp_path: Path, capsys
    ) -> None:
        assert _beschreibung_aus_datei(str(tmp_path / "gibtsnicht.json"),
                                       ENDPUNKTE) is False
        assert "Die Datei gibt es nicht." in capsys.readouterr().out

    def test_eine_datei_die_kein_json_ist_sagt_was_zu_tun_ist(
        self, tmp_path: Path, capsys
    ) -> None:
        """YAML ist bei OpenAPI genauso üblich wie JSON."""
        ziel = tmp_path / "beschreibung.yaml"
        ziel.write_text("openapi: 3.0.1\npaths:\n  /record: {}\n", encoding="utf-8")
        assert _beschreibung_aus_datei(str(ziel), ENDPUNKTE) is False
        assert "als JSON speichern" in capsys.readouterr().out

    def test_eine_datei_ohne_pfade_wird_erkannt(self, tmp_path: Path, capsys) -> None:
        pfad = _datei(tmp_path, {"openapi": "3.0.1"})
        _beschreibung_aus_datei(pfad, ENDPUNKTE)
        assert "keinen Abschnitt" in capsys.readouterr().out


class TestDerSchalterStehtInDerStartdatei:
    def test_die_probe_kennt_ihn(self) -> None:
        from jusperfect import jurnodestest

        quelle = Path(jurnodestest.__file__).read_text(encoding="utf-8")
        assert '"--beschreibung"' in quelle

    def test_die_bat_erklaert_ihn(self) -> None:
        """Ein Schalter, von dem niemand weiß, ist kein Weg."""
        bat = (Path(__file__).resolve().parent.parent / "JURNODES-PRUEFEN.bat"
               ).read_bytes().decode("cp1252")
        assert "beschreibung" in bat.lower()


class TestDieWortlisteBleibtNachpruefbar:
    def test_sie_ist_kleingeschrieben_und_ohne_trennzeichen(self) -> None:
        """Sonst findet der Vergleich sie nie – er normalisiert beide Seiten."""
        for wort in _EAKTE_WOERTER:
            assert wort == _ohne_trenner(wort), wort

    def test_sie_deckt_beide_sprachen_ab(self) -> None:
        for wort in ("eakte", "efile", "electronic", "korrespondenz",
                     "correspondence", "vermerk", "note"):
            assert wort in _EAKTE_WOERTER


def test_die_mitgelieferte_beschreibung_ist_da() -> None:
    """Seit dem 05.10.2026 liegt sie im Programmordner."""
    from jusperfect.jurnodestest import BEILIEGENDE_BESCHREIBUNG

    assert BEILIEGENDE_BESCHREIBUNG.is_file(), BEILIEGENDE_BESCHREIBUNG


def test_ohne_angabe_wird_sie_genommen(capsys) -> None:
    """Aus der Kanzlei am 05.10.2026: „Datei mit der Schnittstellenbeschreibung
    wird angefragt bei JURNODES-PRUEFEN.bat."

    Sie lag zu dem Zeitpunkt schon daneben. Ein Werkzeug, das nach etwas fragt,
    was danebenliegt, ist eine Hürde ohne Zweck.
    """
    from jusperfect import jurnodestest

    ende = jurnodestest._ablauf([])
    ausgabe = capsys.readouterr().out
    assert "jurnodes-api-1.0.2.json" in ausgabe
    assert "85 Pfade stehen darin" in ausgabe
    # Ohne Adresse endet die Probe danach sauber, statt ins Leere zu laufen.
    assert ende in (0, 2)


def test_die_bat_zeigt_die_mitgelieferte_an_statt_zu_fragen() -> None:
    bat = (Path(__file__).resolve().parent.parent / "JURNODES-PRUEFEN.bat"
           ).read_bytes().decode("cp1252")
    assert "schnittstelle\\jurnodes-api-1.0.2.json" in bat
    assert "if exist" in bat
    # Und die Sprungmarken, ohne die cmd nicht weiterkommt.
    for marke in (":beschreibung_da", ":beschreibung_fertig"):
        assert marke in bat, marke
        assert f"goto {marke[1:]}" in bat, marke
