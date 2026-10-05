"""Warum nimmt jur|nodes das Aktengedächtnis nicht an? Ein Versuch, eine Antwort.

Am 24.09.2026 antwortete der Server der Kanzlei auf das Ablegen des
Aktengedächtnisses mit **405**. Zwei Tage lang wurde die Zahl nach der Norm
gelesen - "den Pfad gibt es, aber nicht mit POST" - und deshalb der Pfad
gesucht. Der war die ganze Zeit richtig: OPTIONS nennt für ihn ausdrücklich
POST, und die Beschreibung des Herstellers führt den Code 405 in allen 85
Pfaden als **"Ungültige Eingabe"**, keinmal anders. Ein fehlendes Recht
beantwortet derselbe Server mit 401.

Es ist also ein einzelner Wert, den er nicht annimmt - und **er sagt selbst,
welcher**, im Feld ``error`` seiner Antwort. Nur hat bisher niemand zugehört.

Dieses Werkzeug hört zu. Es geht **genau den Weg des Betriebs**: derselbe
Adapter, dieselben Kopfzeilen, dieselbe Datei. Eine Probe, die anders fragt
als der Betrieb, prüft etwas anderes als den Betrieb - dieser Satz hat an
einem einzigen Tag fünfmal zugeschlagen.

**Dieses Werkzeug schreibt.** Das ist der Unterschied zu JURNODES-PRUEFEN.bat
und deshalb steht es hier und nicht dort. Was dabei geschieht:

* Es legt in der genannten Akte **das Aktengedächtnis** ab - dieselbe Datei,
  die der Betrieb dort führt, mit demselben festen Namen. Über diesen Weg
  kann nichts anderes in die Akte gelangen.
* Der Inhalt ist eine einzige Zeile: Datum und Zweck. Kein Akteninhalt, kein
  Mandantenname.
* **Wird sie abgewiesen** - der erwartete Fall -, ist nichts geschrieben
  worden, und der Wortlaut des Servers steht auf dem Schirm.
* **Geht sie durch**, ist das Rätsel gelöst; in der Akte liegt dann eine
  kleine Datei, die jusperfect ohnehin dort führen soll. Löschen lässt sie
  sich in jur|nodes jederzeit.

Ohne ausdrückliches "ja" im Fenster geschieht nichts.

Aufruf:  python3 werkzeug/ablageprobe.py AKTENZEICHEN
Windows: ABLAGE-PRUEFEN.bat
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from jusperfect.config import Einstellungen, KonfigurationsFehler  # noqa: E402
from jusperfect.domain.models import Aktengedaechtnis  # noqa: E402
from jusperfect.gedaechtnis.packen import packen  # noqa: E402
from jusperfect.jurnodes.base import GEDAECHTNIS_DATEI, JurNodesFehler  # noqa: E402
from jusperfect.jurnodes.http_adapter import HttpJurNodesAdapter  # noqa: E402
from jusperfect.security.approval import Freigabestelle  # noqa: E402

TRENNER = "─" * 72


def _sagen(zeichen: str, text: str) -> None:
    print(f"  {zeichen}  {text}")


def probeninhalt(akte_id: str, heute: date | None = None) -> bytes:
    """Der Inhalt der Probedatei: ein leeres, aber gültiges Aktengedächtnis.

    **Hier stand am 25.09.2026 ein selbstgebautes JSON** mit den Feldern
    "probe", "datum" und "zweck". Der Server nahm es an - und danach lag in
    einer echten Akte eine Datei, die den Namen des Aktengedächtnisses trug
    und keines war. Beim nächsten Öffnen dieser Akte bricht das Lesen ab.

    Derselbe Fehler wie immer, nur andersherum: **Eine Probe, die etwas
    anderes ablegt als der Betrieb, prüft etwas anderes als den Betrieb** -
    und hier hat sie zusätzlich Schaden angerichtet.

    Jetzt wird abgelegt, was der Betrieb ablegt: ein Aktengedächtnis, durch
    dieselbe Funktion gepackt. Es ist leer bis auf die Kennung der Akte und
    einen Vermerk im Lebenssachverhalt. Damit ist es in jedem Fall harmlos:
    lesbar, der richtigen Akte zugeordnet, und beim ersten echten Sichern
    wird es überschrieben.
    """
    g = Aktengedaechtnis(
        akte_id=akte_id,
        lebenssachverhalt=(
            f"Ablageprobe vom {(heute or date.today()).isoformat()}. "
            "Geprüft wurde nur, ob jur|nodes diese Datei annimmt. "
            "Sie enthält nichts aus der Akte und wird beim nächsten "
            "Sichern überschrieben."),
    )
    return packen(g)


def bereichsschluessel(umgebung) -> dict[str, str]:
    """jur|nodes vergibt je Bereich einen eigenen Schlüssel.

    Wer erst einen hat, kommt damit durch; die übrigen Bereiche antworten
    dann mit einer Ablehnung. Dieselbe Sammlung wie in JURNODES-PRUEFEN.bat.
    """
    gefunden: dict[str, str] = {}
    for bereich in ("akten", "akte", "dateisystem", "beziehungen", "todo"):
        wert = umgebung.get(f"JURNODES_API_KEY_{bereich.upper()}", "").strip()
        if wert:
            gefunden[bereich] = wert
    return gefunden


def adapter_bauen(e: Einstellungen, token: str, benutzer: str,
                  schluessel: dict[str, str] | None = None) -> HttpJurNodesAdapter:
    """Derselbe Weg wie im Betrieb - nicht ein zweiter, der ähnlich aussieht.

    ``aus_einstellungen`` ist, was die Oberfläche aufruft. Es zieht auch die
    abweichenden Pfade aus der Datei unter JUSPERFECT_JURNODES_ENDPUNKTE.
    Wer hier von Hand einen Adapter zusammensetzt, prüft etwas anderes als
    den Betrieb.

    Die Freigabestelle wird nur vom Vermerk gebraucht. Das Aktengedächtnis
    läuft nicht über sie - es ist die eine Datei, die jusperfect ohne
    Einzelfreigabe führen darf.
    """
    return HttpJurNodesAdapter.aus_einstellungen(
        e, Freigabestelle(), token,
        benutzer=benutzer, schluessel=schluessel or {})


def kennung_suchen(adapter: HttpJurNodesAdapter, aktenzeichen: str) -> str:
    """Vom Aktenzeichen zur Kennung.

    jur|nodes führt beides getrennt: ``recordSign`` ist das Aktenzeichen,
    ``identifier`` die Kennung. Wer das eine für das andere einsetzt, bekommt
    404 und hält einen richtigen Pfad für falsch. Das ist am 23.09.2026
    passiert und steht seitdem in der Übergabe.
    """
    for akte in adapter.akten_suchen(aktenzeichen):
        return akte.id
    return ""


def main(argv: list[str] | None = None) -> int:
    argumente = list(argv if argv is not None else sys.argv[1:])
    print(TRENNER)
    print("  jusperfect – nimmt jur|nodes das Aktengedächtnis an?")
    print(TRENNER)
    print()

    if not argumente:
        _sagen("!", "Es fehlt das Aktenzeichen.")
        _sagen(" ", "Aufruf: ABLAGE-PRUEFEN.bat  (fragt danach)")
        return 2
    aktenzeichen = argumente[0].strip()

    try:
        e = Einstellungen.aus_umgebung()
    except KonfigurationsFehler as fehler:
        _sagen("✗", str(fehler))
        return 1
    if not e.jurnodes_url:
        _sagen("✗", "Es ist keine Adresse für jur|nodes hinterlegt.")
        _sagen(" ", "Einzutragen mit JURNODES-ZUGANG.bat.")
        return 1
    # Genau die Wege, die auch die Oberflaeche geht: zwei Kopfzeilen, und je
    # Bereich ein eigener Schluessel mit dem allgemeinen als Rueckfall.
    token = os.environ.get(e.jurnodes_token_var, "").strip()
    benutzer = os.environ.get(e.jurnodes_benutzer_var, "").strip()
    schluessel = bereichsschluessel(os.environ)
    if not token or not benutzer:
        _sagen("✗", "Es ist kein Zugang hinterlegt.")
        _sagen(" ", f"Gebraucht werden {e.jurnodes_benutzer_var} und "
                    f"{e.jurnodes_token_var}.")
        _sagen(" ", "Einzutragen mit JURNODES-ZUGANG.bat.")
        return 1

    for zeile in (
            f"Dieses Werkzeug legt in der Akte {aktenzeichen} die Datei",
            f"{GEDAECHTNIS_DATEI} ab - dieselbe, die jusperfect dort ohnehin",
            "führt. Darin steht eine Zeile: Datum und Zweck. Kein Akteninhalt.",
            "",
            "Wird sie abgewiesen, ist nichts geschrieben worden, und der",
            "Wortlaut des Servers steht danach hier.",
            "Geht sie durch, liegt sie in der Akte und lässt sich in jur|nodes",
            "löschen."):
        _sagen(" ", zeile)
    print()
    if input("  Ablegen? Bitte 'ja' eintippen: ").strip().lower() != "ja":
        print()
        _sagen("·", "Abgebrochen. Es wurde nichts geschrieben.")
        return 0

    print()
    adapter = adapter_bauen(e, token, benutzer, schluessel)
    try:
        kennung = kennung_suchen(adapter, aktenzeichen)
    except JurNodesFehler as fehler:
        _sagen("✗", str(fehler))
        return 1
    if not kennung:
        _sagen("✗", f"Zum Aktenzeichen {aktenzeichen} wurde keine Akte gefunden.")
        _sagen(" ", "Geschrieben wurde nichts.")
        return 1
    _sagen(" ", f"Kennung der Akte: {kennung}")

    try:
        adapter.gedaechtnis_ablegen(kennung, probeninhalt(kennung))
    except JurNodesFehler as fehler:
        _sagen("✗", str(fehler))
        wort = getattr(fehler, "serverwort", "")
        if wort:
            print()
            _sagen("→", f"Der Server sagt dazu: {wort}")
            print()
            _sagen(" ", "Das ist die Auskunft, auf die es ankommt.")
            _sagen(" ", "Bitte diese Zeile weitergeben.")
        else:
            print()
            _sagen("!", "Der Server hat keinen Wortlaut mitgeschickt.")
            _sagen(" ", "Dann hilft nur noch der Hersteller.")
        return 1

    print()
    _sagen("✓", "Angenommen. Das Aktengedächtnis lässt sich ablegen.")
    _sagen(" ", f"In der Akte liegt jetzt {GEDAECHTNIS_DATEI}.")
    _sagen(" ", "Damit ist der letzte offene Punkt am Programm erledigt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
