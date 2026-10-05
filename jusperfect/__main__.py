"""Startet den lokalen Server: ``python -m jusperfect``."""

from __future__ import annotations

import os
import socket
import threading
import time
import webbrowser

import uvicorn

from jusperfect.config import Einstellungen
from jusperfect.web import app_erstellen

# Wie lange auf den Server gewartet wird, bevor der Browser aufgegeben wird.
# Grosszuegig: Der erste Start nach dem Auspacken dauert laenger als jeder
# spaetere, und ein Browser, der zu frueh aufgeht, ist genau der Fehler,
# der hier behoben wird.
BROWSER_FRIST = 60.0


def browser_oeffnen_wenn_bereit(host: str, port: int,
                                frist: float = BROWSER_FRIST) -> bool:
    """Öffnet den Browser erst, wenn der Server die Verbindung annimmt.

    Bis zum 25.09.2026 öffneten die Startdateien den Browser, *bevor* der
    Server lief. Die Folge war jedesmal dieselbe: erst eine Fehlerseite, dann
    ein Klick auf Neuladen. Aus der Kanzlei gemeldet.

    Eine feste Wartezeit wäre nur die halbe Antwort - sie ist auf einem
    langsamen Rechner zu kurz und auf einem schnellen zu lang. Gefragt wird
    deshalb der Port selbst.

    Gibt zurück, ob geöffnet wurde. Kommt der Server nicht hoch, unterbleibt
    auch der Browser: Eine Fehlerseite hilft niemandem beim Lesen der
    Meldung, die im schwarzen Fenster steht.
    """
    # 0.0.0.0 ist eine Angabe fuers Zuhoeren, keine zum Anrufen.
    ziel = "127.0.0.1" if host in ("0.0.0.0", "::", "") else host
    ende = time.monotonic() + frist
    while time.monotonic() < ende:
        try:
            with socket.create_connection((ziel, port), timeout=0.5):
                webbrowser.open(f"http://{ziel}:{port}")
                return True
        except OSError:
            time.sleep(0.2)
    return False


def anschluss_belegt(host: str, port: int) -> bool:
    """Hört auf diesem Anschluss schon jemand?

    Gefragt wird, indem angerufen wird: Nimmt jemand ab, ist der Anschluss
    vergeben. Das ist dieselbe Frage wie beim Browser weiter oben, nur mit
    der umgekehrten Erwartung.
    """
    ziel = "127.0.0.1" if host in ("0.0.0.0", "::", "") else host
    try:
        with socket.create_connection((ziel, port), timeout=0.5):
            return True
    except OSError:
        return False


#: Was dasteht, wenn der Anschluss schon vergeben ist.
#:
#: Aus der Kanzlei am 02.10.2026 kam dieses Bild:
#:
#:     ERROR: [Errno 10048] error while attempting to bind on address
#:     ('127.0.0.1', 8765): normalerweise darf jede socketadresse nur
#:     jeweils einmal verwendet werden
#:
#: Rot, englisch, mit einer Fehlernummer - und der Grund ist der harmloseste
#: denkbare: Es lief noch ein Fenster. Wer das liest, sucht im Programm.
#:
#: Ausdruecklich NICHT getan wird hier das Naheliegende: den Browser auf das
#: laufende Fenster zu richten. Welche Startdatei dort laeuft, weiss dieses
#: Fenster nicht - es koennte START-DEMO.bat sein, also die erfundenen Akten.
#: Jemanden stillschweigend dorthin zu fuehren, waere die gefaehrlichste Art
#: zu helfen.
_SCHON_DA = """
============================================================
  jusperfect laeuft bereits.
============================================================

  Auf diesem Rechner hoert schon ein Fenster auf Anschluss {port}.
  Zweimal geht es nicht: Beide wollen denselben Anschluss, und den
  gibt Windows nur einmal aus. Am Programm liegt es nicht.

  Zwei Wege:

  1. Das vorhandene Fenster benutzen. Im Browser:
     http://{ziel}:{port}

     Sehen Sie dort vorher nach, WELCHE Startdatei laeuft - es
     koennte START-DEMO.bat sein, und das sind die erfundenen
     Akten, nicht die der Kanzlei.

  2. Das andere Fenster schliessen und diese Datei erneut starten.

  Ist kein Fenster mehr zu sehen, laeuft es im Verborgenen weiter:
  Task-Manager oeffnen (Strg+Umschalt+Esc), unter "Details" den
  Eintrag "python.exe" beenden.
"""


def main() -> None:
    einstellungen = Einstellungen.aus_umgebung()
    # Vor dem Start gefragt, nicht hinterher: uvicorn meldet den Fall selbst,
    # aber rot, englisch und mit einer Fehlernummer. Die Meldung sieht aus wie
    # ein Programmfehler und ist keiner.
    if anschluss_belegt(einstellungen.host, einstellungen.port):
        ziel = ("127.0.0.1" if einstellungen.host in ("0.0.0.0", "::", "")
                else einstellungen.host)
        print(_SCHON_DA.format(port=einstellungen.port, ziel=ziel))
        raise SystemExit(1)
    app = app_erstellen(einstellungen)
    # Nur die Startdateien auf dem Arbeitsplatz setzen das. Auf einem Server
    # gibt es keinen Browser, und niemand soll ihn dort suchen.
    if os.environ.get("JUSPERFECT_BROWSER_OEFFNEN", "").strip() == "1":
        threading.Thread(
            target=browser_oeffnen_wenn_bereit,
            args=(einstellungen.host, einstellungen.port),
            daemon=True,
        ).start()
    uvicorn.run(
        app,
        host=einstellungen.host,
        port=einstellungen.port,
        # Zugriffsprotokolle enthalten Pfade und Abfragen; sie bleiben aus.
        access_log=False,
    )


if __name__ == "__main__":
    main()
