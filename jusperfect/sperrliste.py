"""Die Liste der gesperrten Namen - und wo sie liegt.

**Befund N01 der dritten Zweitpruefung vom 12.10.2026, Variante A.**

Am 11.10.2026 standen echte Namen aus echten Akten im Bestand. Dagegen gibt
es seit dem 12.10.2026 eine Pruefung: ``tests/test_keine_echten_akten.py``
durchsucht jede Datei nach ihnen. Nur muss diese Pruefung wissen, **wonach**
sie sucht - und bis zum 13.10.2026 standen die Namen deshalb in ihr, zerlegt
in zwei Stuecke, damit sie nicht durch sich selbst durchfiel.

Das war kein Ausweg. Die Namen standen damit weiter im Bestand, nur in zwei
Stuecken, und die Kommentare sagten dazu, wer Mandant und wer Gegner ist. Der
Riegel gegen das Verbreiten von Namen war selbst das Leck - und so ist er in
einem Pruefpaket aus dem Haus gegangen.

**Entscheidung der Kanzlei vom 13.10.2026:** Die Liste liegt **ausserhalb des
Programmordners**, auf den Rechnern der Kanzlei. Diese Datei sagt, wo, und
legt sie auf Wunsch an. Sie ist die eine Quelle fuer den Ort; die Pruefung
liest ihn hier und nicht noch einmal bei sich.

**Was diese Datei nie tut:** die Woerter irgendwohin schreiben ausser in die
Liste selbst. Kein Protokoll, keine Meldung, keine Bestaetigung im Wortlaut.
Bestaetigt wird verdeckt - erster Buchstabe und Laenge -, damit ein Blick auf
den Bildschirm genuegt und ein Bildschirmfoto nichts verraet.
"""

from __future__ import annotations

from pathlib import Path

#: Der Name der Datei. Immer derselbe, an beiden Orten.
SPERRLISTE_NAME = "jusperfect-sperrwoerter.txt"

#: Der Programmordner - zwei Ebenen ueber dieser Datei.
PROGRAMMORDNER = Path(__file__).resolve().parent.parent


def orte() -> tuple[Path, ...]:
    """Wo nach der Liste gesucht wird - in dieser Reihenfolge.

    Beide Orte liegen **ausserhalb** des Programmordners, und das ist der
    ganze Punkt: Eine Datei im Programmordner waere in jedem ZIP, das die
    Kanzlei herunterlaedt - genau der Fehler, den Variante A behebt.

    Erst daneben, dann im Benutzerordner. Auf einem Windows-Arbeitsplatz ist
    das meist dasselbe Verzeichnis; auf einem Server, auf dem das Programm
    anderswo liegt, nicht.
    """
    gefunden: list[Path] = []
    for ort in (PROGRAMMORDNER.parent / SPERRLISTE_NAME,
                Path.home() / SPERRLISTE_NAME):
        if ort not in gefunden:
            gefunden.append(ort)
    return tuple(gefunden)


def finden() -> Path | None:
    """Die Liste - oder ``None``, wenn es keine gibt."""
    for ort in orte():
        try:
            if ort.is_file():
                return ort
        except OSError:             # ein Pfad, den dieses System nicht mag
            continue
    return None


def woerter(ort: Path | None = None) -> tuple[str, ...]:
    """Ein Wort je Zeile; ``#`` beginnt einen Kommentar, Leerzeilen zaehlen nicht.

    **Faellt die Datei aus, faellt die Pruefung aus** - nicht still gruen. Eine
    Liste, die sich nicht lesen laesst, ist etwas anderes als keine Liste: Im
    ersten Fall ist etwas kaputt, im zweiten ist es Absicht. Deshalb wird hier
    nichts abgefangen.
    """
    ort = ort or finden()
    if ort is None:
        return ()
    gefunden: list[str] = []
    for zeile in ort.read_text(encoding="utf-8").splitlines():
        zeile = zeile.split("#", 1)[0].strip()
        if zeile and zeile not in gefunden:
            gefunden.append(zeile)
    return tuple(gefunden)


def verdeckt(wort: str) -> str:
    """Erster Buchstabe, Punkte, Laenge - genug zum Wiedererkennen, nicht mehr."""
    wort = wort.strip()
    if not wort:
        return "(leer)"
    if len(wort) == 1:
        return f"{wort} (1 Zeichen)"
    return f"{wort[0]}{'.' * (len(wort) - 1)} ({len(wort)} Zeichen)"


KOPF = """\
# Gesperrte Namen - jusperfect
#
# Ein Wort je Zeile. Alles hinter einem # ist Erklaerung.
#
# WOZU: tests/test_keine_echten_akten.py durchsucht jede Datei des
# Programmordners nach diesen Woertern. Findet sie eines, faellt der Prueflauf
# rot aus. So kommt kein echter Name aus einer Akte in das Programm, in eine
# ZIP oder in ein Pruefpaket fuer einen Dritten.
#
# WARUM DIESE DATEI HIER LIEGT UND NICHT IM PROGRAMMORDNER: Sie wuerde sonst
# mit jedem ZIP mitgehen - und dann stuenden die Namen in genau dem Paket, das
# sie heraushalten sollen. Das ist am 12.10.2026 passiert (Befund N01).
#
# DIESE DATEI NICHT in den Programmordner kopieren, nicht in eine ZIP legen,
# nicht weitergeben. Sie gehoert auf die Rechner der Kanzlei und nirgends
# sonst. Eine Sicherung des Benutzerordners nimmt sie mit; das ist in Ordnung,
# solange die Sicherung im Haus bleibt.
#
# Angelegt mit SPERRLISTE-ANLEGEN.bat.
"""


def schreiben(ort: Path, neue: list[str]) -> tuple[Path, int]:
    """Die Liste schreiben - Kopf, dann je Wort eine Zeile.

    Vorhandene Woerter bleiben; doppelte werden einmal geschrieben. Gibt den
    Ort und die Zahl der Woerter zurueck.
    """
    bestand = list(woerter(ort)) if ort.is_file() else []
    for wort in neue:
        wort = wort.strip()
        if wort and wort not in bestand:
            bestand.append(wort)
    ort.write_text(KOPF + "\n" + "\n".join(bestand) + "\n", encoding="utf-8")
    return ort, len(bestand)


# ── Der geführte Weg ───────────────────────────────────────────────────────
#
# Aus der Kanzlei gelernt, mehrfach: Ein Nichtprogrammierer soll keine Datei
# mit der richtigen Zeichenkodierung an einem abgezählten Pfad anlegen müssen.
# Notepad hängt ein zweites ".txt" an, speichert nach Laune in ANSI, und ein
# Umlaut in ANSI heißt: Die Prüfung findet den Namen nicht und ist grün.
#
# Deshalb fragt das Programm und schreibt selbst.

def _sagen(zeichen: str, text: str) -> None:
    print(f"  {zeichen:<2} {text}")


def main() -> int:
    print()
    print("=" * 62)
    print("   Gesperrte Namen hinterlegen")
    print("=" * 62)
    print()
    print("  Diese Liste sagt dem Prueflauf, nach welchen Namen er suchen")
    print("  soll. Findet er einen im Programmordner, faellt er rot aus -")
    print("  so kommt kein echter Name in eine ZIP oder in ein Pruefpaket.")
    print()
    print("  Die Liste bleibt auf diesem Rechner. Sie kommt NICHT in den")
    print("  Programmordner und NICHT in eine ZIP - deshalb liegt sie")
    print("  daneben und nicht darin.")
    print()

    vorhanden = finden()
    if vorhanden is not None:
        try:
            bestand = woerter(vorhanden)
        except (OSError, UnicodeDecodeError) as fehler:
            _sagen("✗", f"Die Liste liegt da, laesst sich aber nicht lesen: {fehler}")
            _sagen(" ", f"Ort: {vorhanden}")
            _sagen(" ", "Bitte die Datei loeschen und diesen Weg erneut gehen.")
            return 2
        _sagen("✓", f"Es gibt schon eine Liste mit {len(bestand)} Wort/Woertern.")
        _sagen(" ", f"Ort: {vorhanden}")
        for wort in bestand:
            _sagen(" ", f"     {verdeckt(wort)}")
        print()
        print("  Was jetzt eingegeben wird, kommt dazu. Doppeltes wird einmal")
        print("  geschrieben. Soll nichts dazukommen: einfach Eingabetaste.")
        ziel = vorhanden
    else:
        ziel = orte()[0]
        _sagen(" ", "Es gibt noch keine Liste. Sie wird angelegt unter:")
        _sagen(" ", f"     {ziel}")
    print()
    print("  Ein Name je Zeile, dann Eingabetaste. Fertig: leere Zeile.")
    print()
    # Das Beispiel ist einer der ERFUNDENEN Namen aus den Testakten.
    #
    # Hier stand zuerst der echte - zum sechsten Mal dasselbe Muster, und
    # diesmal in der Zeile, die das Muster erklaert. Gefangen hat es ein
    # Nachlauf mit der Liste, nicht meine Aufmerksamkeit.
    print("  Umlaute bitte in BEIDEN Schreibweisen - einmal „Kraemer“")
    print("  und einmal „Krämer“. In Dateinamen steht oft die eine,")
    print("  im Text die andere, und gesucht wird Zeichen fuer Zeichen.")
    print()

    neue: list[str] = []
    while True:
        try:
            eingabe = input(f"  Name {len(neue) + 1}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            _sagen("!", "Abgebrochen. Es wurde nichts geschrieben.")
            return 1
        if not eingabe:
            break
        if eingabe.startswith("#"):
            _sagen("!", "Ein Name faengt nicht mit # an - das ist das")
            _sagen(" ", "Zeichen fuer eine Erklaerung. Bitte noch einmal.")
            continue
        if len(eingabe) < 3:
            # Ein zu kurzes Wort faengt halb Deutschland. "Ei" stuende in
            # jedem zweiten Satz, und eine Pruefung, die immer rot ist, wird
            # nach einer Woche abgeschaltet.
            _sagen("!", "Das ist mit zwei Zeichen zu kurz - es wuerde in")
            _sagen(" ", "zu vielen gewoehnlichen Woertern stecken. Nicht")
            _sagen(" ", "uebernommen.")
            continue
        neue.append(eingabe)
        _sagen("✓", f"     uebernommen: {verdeckt(eingabe)}")

    if not neue:
        if vorhanden is not None:
            _sagen(" ", "Nichts dazugekommen. Die Liste bleibt, wie sie war.")
            return 0
        _sagen("!", "Kein Name eingegeben - es wurde nichts angelegt.")
        return 1

    print()
    try:
        ort, anzahl = schreiben(ziel, neue)
    except OSError as fehler:
        _sagen("✗", f"Die Liste liess sich nicht schreiben: {fehler}")
        _sagen(" ", f"Versucht wurde: {ziel}")
        return 2

    # Nachgelesen, nicht behauptet: geschrieben ist erst, was sich wieder
    # lesen laesst - und mit falscher Zeichenkodierung tut es das nicht.
    try:
        zurueck = woerter(ort)
    except (OSError, UnicodeDecodeError) as fehler:
        _sagen("✗", f"Geschrieben, aber nicht wieder lesbar: {fehler}")
        return 2
    if len(zurueck) != anzahl:
        _sagen("✗", f"Geschrieben wurden {anzahl}, gelesen {len(zurueck)}.")
        return 2

    _sagen("✓", f"{anzahl} Wort/Woerter stehen in der Liste.")
    _sagen(" ", f"Ort: {ort}")
    print()
    _sagen(" ", "Zum Nachsehen: PRUEFBOGEN.bat starten. Steht am Ende KEIN")
    _sagen(" ", "Hinweis auf eine fehlende Sperrliste, hat der Prueflauf sie")
    _sagen(" ", "gefunden und sucht wieder nach Namen.")
    print()
    _sagen("!", "Auf dem ZWEITEN Kanzleirechner dasselbe noch einmal - die")
    _sagen(" ", "Liste liegt je Rechner und wird nicht mitgeschickt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
