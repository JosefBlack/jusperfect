"""Was jede Prüfung vorfindet – damit sie hier misst wie in der Kanzlei.

**Die große Testakte wird erzeugt, nicht mitgeliefert.** 880.000 Zeichen
Fülltext gehören nicht in ein Programmpaket; bei fester Saat entsteht jedes
Mal dieselbe Akte. Das ist richtig so – nur fehlte sie deshalb auf einem
frisch ausgecheckten Stand, und das hieß für zwei Prüfungen Verschiedenes:

* ``test_schriftstueckdatum`` las ``akte.json`` und brach mit
  ``FileNotFoundError`` ab. Auf GitHub lief der Prüflauf damit seit dem
  28.09.2026 jedes Mal rot, während er örtlich grün war – weil hier die Akte
  von einem früheren Lauf herumlag.
* ``pruefbogen._ist_routine`` fragt die Akte, welche Bautagebuchtage ein
  besonderes Vorkommnis tragen. Ohne Akte bleibt diese Menge leer und der
  Rauschwert fällt strenger aus. Das ist die ungefährliche Richtung, aber es
  heißt: **Dieselbe Prüfung misst auf zwei Rechnern Verschiedenes.**

Der zweite Punkt ist der schwerere, und er ist dieselbe Form, die dieses
Projekt seit September verfolgt: Eine Probe, die anderswo anders antwortet,
prüft etwas anderes. Deshalb steht die Akte jetzt vor jedem Lauf bereit –
erzeugt in Bruchteilen einer Sekunde, genau wie ``PRUEFBOGEN.bat`` es tut.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkzeug"))

#: Die Akte, die der Prüfbogen misst.
GROSSE_AKTE = WURZEL / "testdaten" / "grosse-akte" / "BA-2026-0044"


@pytest.fixture(scope="session", autouse=True)
def grosse_testakte() -> Path:
    """Die große Testakte bereitstellen, falls sie fehlt."""
    if not (GROSSE_AKTE / "akte.json").is_file():
        import grosse_testakte as vorlage

        vorlage.erzeugen(GROSSE_AKTE)
    return GROSSE_AKTE


# ── Befund N08 der dritten Zweitprüfung vom 12.10.2026 ──────────────────────
#
# `test_ohne_angabe_wird_sie_genommen` heißt „ohne Angabe" und meinte damit:
# ohne das Argument `--beschreibung`. Die **Adresse** nahm der Test aus der
# Umgebung des Rechners — und auf einem Kanzleirechner steht sie dort. Also
# lief der Test an der lokalen Beschreibungsprüfung vorbei weiter in die
# echte Aktensuche und Statusabfrage, mit dem echten Zugang der Kanzlei.
#
# Beim ersten Prüflauf des externen Prüfers ist genau das passiert: 1.861
# Tests grün, einer rot, und der Grund war, dass sein Rechner
# jur|nodes-Umgebungsvariablen gesetzt hatte. Ob einzelne Anfragen den Server
# erreichten, ließ sich nachträglich nicht mehr feststellen.
#
# **Zwei Riegel, und beide hier**, denn eine Zusage, die an der Sorgfalt des
# einzelnen Tests hängt, hält nicht:
#
# 1. Keine Prüfung erbt die Umgebung der Kanzlei. Nicht „dieser Test räumt
#    auf", sondern: Es gibt dort nichts aufzuräumen.
# 2. Keine Prüfung baut eine Verbindung nach draußen. Loopback bleibt offen —
#    manches braucht einen eigenen Server im selben Prozess.
#
# Beides ist absichtlich stumpf. Ein echter Integrationstest gegen einen
# Testmandanten braucht die Marke `echtes_netz` und sagt damit, was er tut.

#: Die Vorsätze, unter denen die Kanzlei ihre Zugänge in die Umgebung legt.
KANZLEI_VORSAETZE = ("JUSPERFECT_", "JURNODES_", "AWS_")

#: Und die Namen, unter denen ein Rechner einen Vermittler einträgt.
#:
#: Beim Bauen dieses Riegels aufgefallen, und es ist kein Nebensatz: Steht ein
#: Vermittler in der Umgebung, baut `httpx` die Verbindung **zu ihm** auf -
#: oft auf diesem Rechner selbst. Die Sperre unten sieht dann eine
#: Loopback-Verbindung und laesst sie durch, waehrend die Anfrage in Wahrheit
#: hinausgeht. Eine Sperre, die so ausfaellt, ist schlimmer als keine, weil
#: sie gruen aussieht.
VERMITTLER_NAMEN = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
                    "FTP_PROXY", "http_proxy", "https_proxy", "all_proxy",
                    "no_proxy", "ftp_proxy", "REQUESTS_CA_BUNDLE",
                    "CURL_CA_BUNDLE", "SSL_CERT_FILE")

#: Was stattdessen dasteht. Feste Werte, damit jede Prüfung dasselbe
#: vorfindet - und keine davon gehört zu einem Konto, das es gibt.
AWS_PRUEFWERTE = {
    "AWS_ACCESS_KEY_ID": "AKIAPRUEFPRUEFPRUEF0",
    "AWS_SECRET_ACCESS_KEY": "pruefwert-kein-echter-schluessel",
    "AWS_SESSION_TOKEN": "pruefwert",
    "AWS_DEFAULT_REGION": "eu-central-1",
    "AWS_REGION": "eu-central-1",
    "AWS_EC2_METADATA_DISABLED": "true",
}


@pytest.fixture(autouse=True)
def ohne_kanzleiumgebung(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keine Prüfung erbt die Zugänge des Rechners, auf dem sie läuft."""
    import os

    for name in list(os.environ):
        if name.startswith(KANZLEI_VORSAETZE):
            monkeypatch.delenv(name, raising=False)
    for name in VERMITTLER_NAMEN:
        monkeypatch.delenv(name, raising=False)
    for name, wert in AWS_PRUEFWERTE.items():
        monkeypatch.setenv(name, wert)
    # Auch die Dateien, aus denen botocore sonst echte Zugänge liest.
    for name in ("AWS_SHARED_CREDENTIALS_FILE", "AWS_CONFIG_FILE"):
        monkeypatch.setenv(name, str(tmp_path / "gibt-es-nicht"))


def _ist_loopback(ziel: object) -> bool:
    """Geht diese Verbindung an diesen Rechner selbst?"""
    if not isinstance(ziel, (tuple, list)) or not ziel:
        return False        # ein Unix-Socket oder etwas Unbekanntes
    wirt = str(ziel[0] or "")
    return wirt in ("127.0.0.1", "::1", "localhost", "", "0.0.0.0") \
        or wirt.startswith("127.")


class AeussereVerbindung(RuntimeError):
    """Eine Prüfung wollte nach draußen. Siehe Befund N08."""


#: Ob die laufende Prüfung nach draußen darf. Die Marke `echtes_netz` setzt
#: es; alles andere nicht. Ein Modulwert, weil die Sperre für den ganzen Lauf
#: steht und die Marke an der einzelnen Prüfung hängt.
_NETZ_ERLAUBT = False


@pytest.fixture(autouse=True)
def netz_nur_mit_marke(request: pytest.FixtureRequest) -> object:
    """Nur eine Prüfung mit der Marke ``echtes_netz`` darf hinaus.

    Sie sagt damit, was sie tut. Ohne Marke ist draußen zu.
    """
    global _NETZ_ERLAUBT
    vorher = _NETZ_ERLAUBT
    _NETZ_ERLAUBT = request.node.get_closest_marker("echtes_netz") is not None
    try:
        yield None
    finally:
        _NETZ_ERLAUBT = vorher


@pytest.fixture(scope="session", autouse=True)
def kein_aeusseres_netz() -> object:
    """Keine Verbindung nach draußen - für den ganzen Lauf.

    Gemessen wird am Socket, nicht an der Bibliothek: ``httpx``, ``botocore``
    und ``urllib`` gehen alle hier durch, und was morgen dazukommt, auch.
    """
    import socket

    alt_connect = socket.socket.connect
    alt_connect_ex = socket.socket.connect_ex
    alt_create = socket.create_connection

    def pruefen(ziel: object) -> None:
        if not _NETZ_ERLAUBT and not _ist_loopback(ziel):
            raise AeussereVerbindung(
                "Diese Prüfung wollte eine Verbindung nach draußen aufbauen. "
                "Prüfungen laufen ohne Netz (Befund N08 vom 12.10.2026): Ein "
                "Test, der den echten Server erreicht, misst auf jedem Rechner "
                "etwas anderes und kann fremde Mandate anfassen. Gebraucht wird "
                "ein Mock - oder die Marke 'echtes_netz' und ein Testmandant.")

    def connect(selbst, ziel):                      # type: ignore[no-untyped-def]
        pruefen(ziel)
        return alt_connect(selbst, ziel)

    def connect_ex(selbst, ziel):                   # type: ignore[no-untyped-def]
        pruefen(ziel)
        return alt_connect_ex(selbst, ziel)

    def create_connection(ziel, *args, **kwargs):   # type: ignore[no-untyped-def]
        pruefen(ziel)
        return alt_create(ziel, *args, **kwargs)

    socket.socket.connect = connect                 # type: ignore[method-assign]
    socket.socket.connect_ex = connect_ex           # type: ignore[method-assign]
    socket.create_connection = create_connection    # type: ignore[assignment]
    try:
        yield None
    finally:
        socket.socket.connect = alt_connect         # type: ignore[method-assign]
        socket.socket.connect_ex = alt_connect_ex   # type: ignore[method-assign]
        socket.create_connection = alt_create       # type: ignore[assignment]
