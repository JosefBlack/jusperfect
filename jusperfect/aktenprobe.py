"""Welcher Eintrag dieser Akte lässt sich nicht lesen? – die Aktenprobe.

Aus der Kanzlei am 13.10.2026: „Akte öffnen nicht möglich Vorgang wurde
abgebrochen interner Fehler 2e2e3bd1."

Seit demselben Tag kostet ein einzelner Eintrag nicht mehr die ganze Akte: Was
ausfällt, fällt allein aus und steht in der Anzeige. Damit ist die Akte
benutzbar – **welcher** Eintrag es ist, sagt sie damit noch nicht genau.

Diese Probe sagt es. Sie geht denselben Weg wie das Programm beim Öffnen, aber
Eintrag für Eintrag und mit einer Zeile je Eintrag:

* die Stammdaten der Akte,
* den Dateiordner und jede Datei darin,
* das Korrespondenzverzeichnis, jeden Vermerk und jede Mail mit ihren Anlagen,
* zuletzt denselben Aufruf, den das Programm macht, mit seinen Zählern.

**Sie kostet keinen Modellaufruf und keine Texterkennung.** Gelesen wird nur,
was das Öffnen auch liest; der Inhalt der Dokumente wird **nicht** geholt. Was
das Laden eines Dokuments kostet (Texterkennung bei Scans), fällt hier nicht
an – und ein Fehler beim *Laden* ist deshalb auch nicht Gegenstand dieser
Probe.

**Sie schreibt nichts.** Kein Vermerk, keine Datei, kein Ordner – und das
Aktengedächtnis wird nicht einmal gelesen. Das ist Absicht: Die Probe muss
auch dann arbeiten, wenn gerade das Gedächtnis das Problem ist.

**Die Ausgabe enthält keinen Akteninhalt.** Kein Betreff, kein Dateiname, kein
Beteiligter, kein Text – nur Art, Richtung, Datum, Anzahlen und im Fehlerfall
die Ausnahmekette (Typen und Codestellen). Kennungen stehen verdeckt. Diese
Ausgabe lässt sich weitergeben.

Aufruf:  python -m jusperfect.aktenprobe [--akte AKTENZEICHEN]
Windows: AKTE-PRUEFEN.bat
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from typing import Any

from jusperfect.config import Einstellungen, KonfigurationsFehler
from jusperfect.fehlergrenze import ausnahmekette, protokolle_eindaemmen
from jusperfect.jurnodes.base import JurNodesFehler

GUT = "✓"
SCHLECHT = "✗"
PUNKT = "·"
WARNUNG = "!"


def _sagen(zeichen: str, text: str) -> None:
    print(f"  {zeichen}  {text}")


def _ueberschrift(text: str) -> None:
    print()
    print(f"  {text}")
    print("  " + "-" * max(len(text), 20))


def verdeckt(wert: Any) -> str:
    """Wiedererkennbar, aber nicht lesbar - wie im Prüfbogen der Schnittstelle.

    ``m-4711`` wird zu ``m-4…(6)``. Das genügt, um zwei Einträge auseinander
    zu halten, und nennt keine fremde Akte beim Namen.
    """
    text = str(wert)
    return f"{text[:3]}…({len(text)})" if len(text) > 3 else f"…({len(text)})"


def _richtung(eintrag: Mapping[str, Any]) -> str:
    """1 = Eingang, 0 = Ausgang, -1 = unbekannt (so steht es in der API 1.0.2)."""
    roh = eintrag.get("isInbox")
    if roh in (1, "1", True):
        return "Eingang"
    if roh in (0, "0", False):
        return "Ausgang"
    return "Richtung unbekannt"


def _tag(eintrag: Mapping[str, Any]) -> str:
    """Nur der Tag, nicht die Uhrzeit - und nie etwas anderes aus dem Feld."""
    for name in ("created", "date", "documentDate", "lastModified"):
        wert = eintrag.get(name)
        if wert:
            return str(wert)[:10]
    return "ohne Datum"


class Probe:
    """Der Lauf selbst. Zählt mit, damit am Ende ein Urteil dastehen kann."""

    def __init__(self) -> None:
        self.gut = 0
        self.schlecht = 0
        self.ketten: dict[str, int] = {}

    def versuchen(self, was: str, arbeit) -> tuple[bool, Any]:
        """Einen Schritt tun und sagen, wie er ausging. Nie werfen.

        Gibt ``(gelungen, Ergebnis)`` zurueck und nicht nur das Ergebnis: Ein
        Schritt, der ``None`` zurueckgibt, ist deshalb nicht gescheitert.
        """
        try:
            ergebnis = arbeit()
        except Exception as fehler:  # noqa: BLE001 - genau das ist der Zweck
            self.schlecht += 1
            kette = ausnahmekette(fehler)
            self.ketten[kette] = self.ketten.get(kette, 0) + 1
            _sagen(SCHLECHT, f"{was}: {kette}")
            return False, None
        self.gut += 1
        return True, ergebnis


def _adapter(e: Einstellungen):
    from jusperfect.security.approval import Freigabestelle
    from jusperfect.web import _adapter_bauen

    # Derselbe Weg, den das Programm nimmt. Ein eigener waere eine zweite
    # Wahrheit - und die Probe soll gerade das messen, was beim Oeffnen
    # geschieht.
    return _adapter_bauen(e, Freigabestelle())


def _dateien_pruefen(probe: Probe, adapter: Any, akte_id: str) -> None:
    from jusperfect.jurnodes.http_adapter import dokument_aus_json, ist_gedaechtnis_datei

    _ueberschrift("Der Dateiordner der Akte")
    if not hasattr(adapter, "_roh_akte"):
        _sagen(PUNKT, "Diese Anbindung kennt keinen Dateiordner - "
                      "Eintrag fuer Eintrag geht nur ueber die Schnittstelle.")
        return
    gelungen, roh = probe.versuchen("Stammdaten der Akte",
                                    lambda: adapter._roh_akte(akte_id))
    if not gelungen or not isinstance(roh, Mapping):
        return
    ordner_id = roh.get("fileFolderId")
    if not ordner_id:
        _sagen(WARNUNG, "Diese Akte nennt keinen Dateiordner (fileFolderId fehlt). "
                        "Die Dateien fehlen dann; die E-Akte nicht.")
        return
    _sagen(GUT, f"Dateiordner vorhanden: {verdeckt(ordner_id)}")
    gelungen, eintraege = probe.versuchen(
        "Ordnerbaum durchgehen", lambda: adapter._ordner_durchgehen(ordner_id))
    if not gelungen:
        return
    _sagen(PUNKT, f"{len(eintraege)} Eintrag/Einträge im Baum.")
    for nr, (pfad, eintrag) in enumerate(eintraege, 1):
        datei = eintrag.get("file") if isinstance(eintrag, Mapping) else None
        if datei is None and isinstance(eintrag, Mapping) and eintrag.get("type") == "folder":
            continue
        inhalt = datei or eintrag
        if isinstance(inhalt, Mapping) and ist_gedaechtnis_datei(adapter._ganzer_name(inhalt)):
            _sagen(PUNKT, f"[{nr}] das Aktengedächtnis selbst - kein Dokument der Akte")
            continue
        was = f"[{nr}] Datei, Ordnertiefe {pfad.count('/')}"
        gelungen, _ = probe.versuchen(
            was, lambda i=inhalt, p=pfad: dokument_aus_json(akte_id, i, ordner=p))
        if gelungen:
            _sagen(GUT, was)


def _eakte_pruefen(probe: Probe, adapter: Any, akte_id: str) -> None:
    from jusperfect.jurnodes.http_adapter import vermerk_als_dokument

    _ueberschrift("Die E-Akte (Korrespondenz und Vermerke)")
    if not getattr(adapter, "_korrespondenz", True):
        _sagen(WARNUNG, "Die E-Akte ist abgeschaltet (JUSPERFECT_KORRESPONDENZ=aus).")
        return
    if not hasattr(adapter, "korrespondenz"):
        _sagen(PUNKT, "Diese Anbindung kennt kein Korrespondenzverzeichnis.")
        return
    gelungen, eintraege = probe.versuchen("Korrespondenzverzeichnis lesen",
                                          lambda: adapter.korrespondenz(akte_id))
    if not gelungen or eintraege is None:
        return
    arten: dict[str, int] = {}
    for eintrag in eintraege:
        art = str(eintrag.get("type", "")).lower() if isinstance(eintrag, Mapping) else "?"
        arten[art] = arten.get(art, 0) + 1
    _sagen(GUT, f"{len(eintraege)} Eintrag/Einträge: "
                + ", ".join(f"{n}× {a or 'ohne Art'}" for a, n in sorted(arten.items())))

    for nr, eintrag in enumerate(eintraege, 1):
        if not isinstance(eintrag, Mapping):
            _sagen(SCHLECHT, f"[{nr}] Eintrag ist kein Verzeichnis, sondern "
                             f"{type(eintrag).__name__}")
            probe.schlecht += 1
            continue
        art = str(eintrag.get("type", "")).lower()
        kopf = f"[{nr}] {art or 'ohne Art'}, {_richtung(eintrag)}, {_tag(eintrag)}"
        if art == "note":
            nummer = eintrag.get("referenceNote")
            if nummer is None:
                _sagen(WARNUNG, f"{kopf} - Vermerk ohne referenceNote, wird ausgelassen")
                continue
            gelungen, _ = probe.versuchen(
                kopf, lambda n=nummer, e=eintrag: vermerk_als_dokument(akte_id, n, e))
            if gelungen:
                _sagen(GUT, kopf)
        elif art == "mail":
            if not hasattr(adapter, "_eine_mail"):
                _sagen(PUNKT, f"{kopf} - diese Anbindung holt keine Mails")
                continue
            # Derselbe Weg wie beim Oeffnen, nur fuer diese eine Mail. Der
            # Brieftext und jede Anlage landen in `sammler` und werden
            # gezaehlt - gelesen wird davon nichts.
            sammler: list[Any] = []
            gelungen, _ = probe.versuchen(
                kopf, lambda e=eintrag, s=sammler: adapter._eine_mail(akte_id, e, s))
            if gelungen:
                _sagen(GUT, f"{kopf} - {len(sammler)} Dokument(e) daraus")
        else:
            # beA, Post, Fax, SMS, Dateien: hier gibt es noch keinen Inhalt.
            # Gezaehlt wird das vom Programm selbst; ein Fehler ist es nicht.
            _sagen(PUNKT, f"{kopf} - noch kein Inhalt angebunden")


def _wie_das_programm(probe: Probe, adapter: Any, akte_id: str) -> None:
    _ueberschrift("Und jetzt derselbe Aufruf, den das Öffnen macht")
    gelungen, dokumente = probe.versuchen("dokumente()",
                                          lambda: adapter.dokumente(akte_id))
    if not gelungen or dokumente is None:
        _sagen(SCHLECHT, "Das Öffnen der Akte scheitert also im Ganzen, nicht nur "
                         "an einem Eintrag. Die Kette steht oben.")
        return
    _sagen(GUT, f"{len(dokumente)} Dokument(e) in der Liste.")
    zaehler = (
        ("Einträge, die ausgefallen sind", getattr(adapter, "letzte_eintraege_mit_fehler", {})),
        ("aus den Mails nicht übernommen", getattr(adapter, "letzte_mail_ausgelassen", {})),
    )
    for name, werte in zaehler:
        if werte:
            _sagen(WARNUNG, f"{name}: "
                            + ", ".join(f"{n}× {grund}" for grund, n in werte.items()))
    einzeln = (
        ("Mails über der Größengrenze", "letzte_mails_zu_gross"),
        ("Mails über dem Gesamtmaß", "letzte_mails_ueber_budget"),
        ("Mails ohne Antwort", "letzte_mails_ohne_antwort"),
        ("Anlagen aus Mails", "letzte_mail_anhaenge"),
        ("Einträge ohne Inhalt", "letzte_korrespondenz_ohne_inhalt"),
    )
    for name, feld in einzeln:
        wert = getattr(adapter, feld, 0)
        if wert:
            _sagen(PUNKT, f"{name}: {wert}")


def _urteil(probe: Probe) -> int:
    _ueberschrift("Das Ergebnis")
    if not probe.schlecht:
        _sagen(GUT, f"{probe.gut} Schritt(e) gelesen, keiner gescheitert.")
        print()
        print("     Das Öffnen dieser Akte sollte gehen. Scheitert es dennoch,")
        print("     liegt es nicht am Lesen der Akte - dann bitte die Zeile mit")
        print("     „fehler_abgefangen“ aus dem schwarzen Fenster schicken.")
        return 0
    _sagen(SCHLECHT, f"{probe.schlecht} Schritt(e) gescheitert, {probe.gut} gelesen.")
    print()
    print("     Bitte diese Angaben weitergeben - sie enthalten keinen")
    print("     Akteninhalt:")
    for kette, anzahl in probe.ketten.items():
        print(f"       {anzahl}× {kette}")
    return 1


def main(argv: list[str] | None = None, adapter: Any = None) -> int:
    """Der Lauf von der Kommandozeile.

    ``adapter`` setzt die Anbindung von aussen - dafuer gibt es Pruefungen.

    Im Betrieb bleibt er leer; dann baut die Probe sie genauso, wie das
    Programm sie baut.
    """
    protokolle_eindaemmen()
    zerleger = argparse.ArgumentParser(
        description="Welcher Eintrag dieser Akte laesst sich nicht lesen?")
    zerleger.add_argument("--akte", default="", help="Aktenzeichen oder Aktenkennung")
    args = zerleger.parse_args(argv)

    print()
    print("  ==============================================================")
    print("     Welcher Eintrag dieser Akte laesst sich nicht lesen?")
    print("  ==============================================================")
    print()
    print("  Diese Probe LIEST NUR. Sie schreibt nichts, holt keinen")
    print("  Dokumentinhalt, kostet keinen Modellaufruf und keine")
    print("  Texterkennung. In der Ausgabe steht kein Akteninhalt.")
    print()

    try:
        e = Einstellungen.aus_umgebung()
    except KonfigurationsFehler as fehler:
        _sagen(SCHLECHT, f"Die Einstellungen stimmen nicht: {fehler}")
        return 2
    # Wenn eine Anbindung von aussen gesetzt ist, steht SIE da und nicht die
    # Einstellung - sonst behauptet die Ausgabe etwas, das nicht gemessen wird.
    if adapter is not None:
        _sagen(PUNKT, f"Anbindung: {type(adapter).__name__} (von aussen gesetzt)")
    else:
        _sagen(PUNKT, f"Anbindung: {e.jurnodes_adapter}")
    if adapter is None and e.jurnodes_adapter != "http":
        _sagen(WARNUNG, "Das ist nicht die echte Schnittstelle. Gemessen wird, "
                        "was eingestellt ist - fuer die Kanzleiakten bitte "
                        "START-JURNODES.bat verwenden.")

    akte_id = args.akte.strip()
    if not akte_id:
        print()
        print("  Welche Akte soll geprueft werden? Zum Beispiel  X-100-2026")
        print("  Das Aktenzeichen steht nur in dieser eigenen Ausgabe, und dort")
        print("  verdeckt.")
        print()
        try:
            akte_id = input("  Aktenzeichen: ").strip()
        except EOFError:
            akte_id = ""
    if not akte_id:
        _sagen(SCHLECHT, "Ohne Akte gibt es nichts zu pruefen.")
        return 2
    _sagen(PUNKT, f"Akte: {verdeckt(akte_id)}")

    if adapter is None:
        try:
            adapter = _adapter(e)
        except (KonfigurationsFehler, JurNodesFehler) as fehler:
            _sagen(SCHLECHT, f"Die Anbindung liess sich nicht herstellen: {fehler}")
            return 2

    probe = Probe()
    _ueberschrift("Die Stammdaten")
    gelungen, _ = probe.versuchen("Akte lesen", lambda: adapter.akte(akte_id))
    if gelungen:
        _sagen(GUT, "Stammdaten gelesen.")
    for name, arbeit in (("Beteiligte", adapter.beteiligte), ("Fristen", adapter.fristen)):
        gelungen, werte = probe.versuchen(name, lambda a=arbeit: a(akte_id))
        if gelungen:
            _sagen(GUT, f"{name}: {len(werte or [])}")

    _dateien_pruefen(probe, adapter, akte_id)
    _eakte_pruefen(probe, adapter, akte_id)
    _wie_das_programm(probe, adapter, akte_id)
    ergebnis = _urteil(probe)
    print()
    return ergebnis


if __name__ == "__main__":
    sys.exit(main())
