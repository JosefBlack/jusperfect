"""Keine Prüfung erbt die Zugänge des Rechners — Befund N08.

Dritte Zweitprüfung vom 12.10.2026. `test_ohne_angabe_wird_sie_genommen` hieß
„ohne Angabe" und meinte damit: ohne das Argument `--beschreibung`. Die
**Adresse** nahm der Test aus der Umgebung des Rechners — und auf einem
Kanzleirechner steht sie dort.

Also lief er an der lokalen Beschreibungsprüfung vorbei weiter in die echte
Aktensuche und die echte Statusabfrage, mit dem echten Zugang der Kanzlei.
Beim ersten Prüflauf des externen Prüfers ist genau das passiert: 1.861 Tests
grün, einer rot, und der Grund war, dass sein Rechner
jur|nodes-Umgebungsvariablen gesetzt hatte. Ob einzelne Anfragen den Server
erreichten, ließ sich hinterher nicht mehr feststellen.

**Das ist mehr als ein unsauberer Test.** Eine Prüfung, die den echten Server
erreicht, misst auf jedem Rechner etwas anderes — und sie kann fremde Mandate
anfassen. Die Hausregel dazu ist alt: *Niemals jur|nodes-Nummern
durchprobieren.* Ein Test, der mit dem Kanzleischlüssel sucht, tut genau das,
nur ungewollt.

**Die Abhilfe liegt deshalb nicht im einzelnen Test, sondern in
`tests/conftest.py`:** Es gibt in der Umgebung nichts mehr zu erben, und nach
draußen ist zu. Was hier geprüft wird, ist dieser Riegel selbst — eine Sperre,
die stillschweigend ausfällt, ist schlimmer als keine.
"""

from __future__ import annotations

import os
import socket

import pytest

from tests.conftest import (
    AWS_PRUEFWERTE, AeussereVerbindung, KANZLEI_VORSAETZE, VERMITTLER_NAMEN,
)


class TestDieUmgebungIstLeer:
    def test_keine_kanzleivariable_steht_mehr_da(self) -> None:
        geerbt = [n for n in os.environ if n.startswith(("JUSPERFECT_", "JURNODES_"))]
        assert geerbt == [], geerbt

    def test_die_aws_werte_sind_pruefwerte(self) -> None:
        """Nicht gelöscht, sondern ersetzt: moto und botocore brauchen welche,
        und feste Werte heißen, dass jede Prüfung dasselbe vorfindet."""
        for name, wert in AWS_PRUEFWERTE.items():
            assert os.environ.get(name) == wert

    def test_botocore_findet_keine_echte_zugangsdatei(self) -> None:
        for name in ("AWS_SHARED_CREDENTIALS_FILE", "AWS_CONFIG_FILE"):
            pfad = os.environ.get(name, "")
            assert pfad, name
            assert not os.path.exists(pfad), pfad

    def test_die_vorsaetze_decken_ab_was_die_kanzlei_setzt(self) -> None:
        """Alle drei, sonst hat der Riegel ein Loch."""
        assert KANZLEI_VORSAETZE == ("JUSPERFECT_", "JURNODES_", "AWS_")

    def test_kein_vermittler_steht_mehr_in_der_umgebung(self) -> None:
        """Beim Bauen des Riegels aufgefallen, und kein Nebensatz.

        Steht ein Vermittler in der Umgebung, baut `httpx` die Verbindung **zu
        ihm** auf — oft auf diesem Rechner selbst. Die Sperre sieht dann eine
        Loopback-Verbindung und lässt sie durch, während die Anfrage in
        Wahrheit hinausgeht. In genau dieser Umgebung ist das aufgetreten: Der
        erste Entwurf der Prüfung darunter bekam ein „403 Forbidden" von einem
        Vermittler zurück, statt an der Sperre zu scheitern.
        """
        for name in VERMITTLER_NAMEN:
            assert name not in os.environ, name


class TestNachDraussenIstZu:
    def test_eine_aeussere_verbindung_wird_abgewiesen(self) -> None:
        with pytest.raises(AeussereVerbindung):
            socket.create_connection(("beispiel.invalid", 443), timeout=1)

    def test_auch_ueber_den_socket_unmittelbar(self) -> None:
        """Gemessen am Socket, nicht an der Bibliothek: httpx, botocore und
        urllib gehen alle hier durch, und was morgen dazukommt, auch."""
        s = socket.socket()
        try:
            with pytest.raises(AeussereVerbindung):
                s.connect(("93.184.216.34", 80))
        finally:
            s.close()

    def test_auch_connect_ex_das_keinen_fehler_wirft(self) -> None:
        """`connect_ex` gibt sonst nur eine Zahl zurück - und wäre ein Loch."""
        s = socket.socket()
        try:
            with pytest.raises(AeussereVerbindung):
                s.connect_ex(("93.184.216.34", 80))
        finally:
            s.close()

    def test_httpx_kommt_auch_nicht_durch(self) -> None:
        """Der Weg, den das Programm wirklich nimmt."""
        httpx = pytest.importorskip("httpx")
        with pytest.raises(Exception) as fehler:
            httpx.Client(timeout=1).get("https://beispiel.invalid/")
        # httpx verpackt den Fehler; der Grund muss darin erkennbar bleiben.
        assert "Befund N08" in str(fehler.value), repr(fehler.value)

    def test_der_eigene_rechner_bleibt_erreichbar(self) -> None:
        """Manches braucht einen eigenen Server im selben Prozess."""
        horcher = socket.socket()
        horcher.bind(("127.0.0.1", 0))
        horcher.listen(1)
        try:
            s = socket.create_connection(horcher.getsockname(), timeout=2)
            s.close()
        finally:
            horcher.close()

    @pytest.mark.echtes_netz
    def test_mit_der_marke_geht_es_hinaus(self) -> None:
        """Die Marke hebt die Sperre auf - und sagt, dass sie es tut.

        Verbunden wird hier nichts: Geprüft wird, dass **die Sperre** nicht
        mehr greift. Der Fehler, der dann kommt, ist der des Netzes.
        """
        with pytest.raises(Exception) as fehler:
            socket.create_connection(("beispiel.invalid", 9), timeout=1)
        assert not isinstance(fehler.value, AeussereVerbindung)


class TestDerPruefbogenLaeuftOhneAdresseNichtHinaus:
    """Der Test, an dem der Befund hing — jetzt beweist er seine Zusage."""

    def test_ohne_adresse_wird_kein_client_gebaut(self, monkeypatch, capsys) -> None:
        import httpx

        from jusperfect import jurnodestest

        def niemals(*args, **kwargs):
            raise AssertionError(
                "Der Prüfbogen hat ohne Adresse einen HTTP-Client gebaut. "
                "Genau das war Befund N08.")

        monkeypatch.setattr(httpx, "Client", niemals)
        ende = jurnodestest._ablauf([])
        ausgabe = capsys.readouterr().out
        assert "85 Pfade stehen darin" in ausgabe
        assert ende in (0, 2)

    def test_und_er_sagt_dass_keine_adresse_da_ist(self, capsys) -> None:
        from jusperfect import jurnodestest

        jurnodestest._ablauf([])
        ausgabe = capsys.readouterr().out
        assert "nicht gesetzt" in ausgabe
