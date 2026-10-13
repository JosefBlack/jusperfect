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


def schreiben(ort: Path, neue: list[str],
              ersetzen: bool = False) -> tuple[Path, int]:
    """Die Liste schreiben - Kopf, dann je Wort eine Zeile.

    Vorhandene Woerter bleiben; doppelte werden einmal geschrieben. Gibt den
    Ort und die Zahl der Woerter zurueck.

    ``ersetzen`` wirft das Vorhandene weg und schreibt nur die neuen Woerter.

    **Aus der Kanzlei am 13.10.2026: „Ich habe jetzt die falschen Woerter
    eingetragen, kann ich das aendern?"** Konnte man nicht. Dieses Programm
    kannte nur Hinzufuegen - und ein Wort, das einmal drinstand, blieb drin.

    Der Ausweg war, die Datei im Explorer zu loeschen und neu anzufangen. Das
    geht, aber es ist kein Ausweg, den man jemandem anbieten sollte: Ein
    Werkzeug, das seinen eigenen Fehler nicht zuruecknehmen kann, schickt den
    Benutzer an Stellen, an denen er mehr kaputt machen kann als die eine
    Zeile - und der naheliegende Griff daneben, die Datei im Notepad zu
    berichtigen, speichert sie womoeglich in der falschen Zeichenkodierung.
    Dann steht dort Buchstabensalat, die Suche findet nichts, und der
    Prueflauf ist gruen, obwohl er blind ist.
    """
    bestand = [] if ersetzen else (list(woerter(ort)) if ort.is_file() else [])
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

    ersetzen = False
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
        ziel = vorhanden
        print()
        print("  [1] Ergaenzen - was jetzt eingegeben wird, kommt dazu.")
        print("  [2] Neu anfangen - die Liste oben wird weggeworfen.")
        print()
        print("      [2] ist der Weg, wenn ein Wort falsch eingetippt wurde.")
        print("      Ein Wort einzeln herausnehmen kann dieses Programm nicht;")
        print("      bei vier Woertern ist Neueingeben schneller als jede")
        print("      Zeilenverwaltung.")
        print()
        try:
            wahl = input("  1 oder 2 (Eingabetaste = 1): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            _sagen("!", "Abgebrochen. Es wurde nichts geaendert.")
            return 1
        if wahl == "2":
            ersetzen = True
            print()
            _sagen("!", f"Die {len(bestand)} vorhandenen Woerter werden "
                        f"weggeworfen. Geben Sie ALLE ein, die gelten sollen.")
        elif wahl in ("", "1"):
            _sagen(" ", "Ergaenzen. Doppeltes wird einmal geschrieben.")
        else:
            print()
            _sagen("!", f"\u201e{wahl[:20]}\u201c ist weder 1 noch 2. "
                        f"Es wurde nichts geaendert.")
            return 1
    else:
        ziel = orte()[0]
        _sagen(" ", "Es gibt noch keine Liste. Sie wird angelegt unter:")
        _sagen(" ", f"     {ziel}")
    print()
    print("  Ein Name je Zeile, dann Eingabetaste.")
    print("  FERTIG: Eingabetaste druecken, ohne etwas zu schreiben.")
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
            # Aus der Kanzlei am 13.10.2026: "Er fragt nach Name 5, wie kann
            # ich den Vorgang beenden?" Die Anleitung stand oben, vier Zeilen
            # und vier Eingaben weiter oben - und damit ausserhalb des Blicks.
            # Eine Frage muss sagen, wie man sie beendet, und zwar an der
            # Stelle, an der sie gestellt wird.
            eingabe = input(f"  Name {len(neue) + 1} "
                            f"(oder Eingabetaste = fertig): ").strip()
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
        if ersetzen:
            # Nicht stillschweigend alles wegwerfen: Wer "neu anfangen" waehlt
            # und dann nichts eingibt, hat sich vertippt oder es sich anders
            # ueberlegt. Eine leere Liste prueft nichts.
            _sagen("!", "Kein Wort eingegeben - die Liste bleibt unveraendert.")
            return 1
        if vorhanden is not None:
            _sagen(" ", "Nichts dazugekommen. Die Liste bleibt, wie sie war.")
            return 0
        _sagen("!", "Kein Name eingegeben - es wurde nichts angelegt.")
        return 1

    print()
    try:
        ort, anzahl = schreiben(ziel, neue, ersetzen=ersetzen)
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
    # Berichtigt am 13.10.2026: Hier stand PRUEFBOGEN.bat. Das ist der
    # Messlauf ueber die grosse Testakte und kostet einige Euro - eine
    # Auskunft, die Geld kostet, holt sich niemand.
    _sagen(" ", "Zum Nachsehen: SPERRLISTE-PRUEFEN.bat. Sie durchsucht den")
    _sagen(" ", "Programmordner nach den Namen und kostet nichts.")
    print()
    _sagen("!", "Auf dem ZWEITEN Kanzleirechner dasselbe noch einmal - die")
    _sagen(" ", "Liste liegt je Rechner und wird nicht mitgeschickt.")
    return 0




# ── Die Suche selbst, und warum sie hier steht ─────────────────────────────
#
# Sie stand bis zum 13.10.2026 nur in `tests/test_keine_echten_akten.py`. Das
# hiess: Nachsehen konnte nur, wer pytest hat. Und ich habe der Kanzlei
# zweimal gesagt, sie solle dafür `PRUEFBOGEN.bat` starten — das ist der
# Messlauf über die große Testakte und **kostet einige Euro**. Eine Auskunft,
# die Geld kostet, holt sich niemand, und ein Riegel, den niemand nachsieht,
# ist keiner.
#
# Deshalb liegt die Suche jetzt im Programm. `SPERRLISTE-PRUEFEN.bat` ruft
# sie, ohne pytest und ohne einen einzigen Modellaufruf. Die Prüfung
# darüber benutzt dieselbe Funktion — eine Quelle, nicht zwei.

#: Die Aktenzeichen der Kanzlei: D wie Dortschy, T wie Thunert, drei Ziffern,
#: Jahr. Was so aussieht, gehoert zu einer echten Akte des Hauses.
#:
#: Die Regel in einem Satz: Ein Aktenzeichen im Bestand beginnt mit X.
AKTENZEICHEN = __import__("re").compile(r"\b[DT]-\d{3}-\d{4}\b")

#: Die Datei des Herstellers wird nicht angefasst - ihre Beispiele sind seine.
#: Sie fuehrt selbst einen der gesperrten Namen; deshalb steht sie hier.
UNBERUEHRT = frozenset({"schnittstelle/jurnodes-api-1.0.2.json"})

#: Was nie zum Bestand gehoert - Arbeitsspuren, nicht Programm.
NICHT_BESTAND = frozenset({
    ".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules",
    ".jusperfect-gedaechtnis", "build", "dist",
})


def dateien() -> list[str]:
    """Jede Datei des Bestands, relativ zum Programmordner.

    **Zuerst git, dann der Ordner.** Ein Paket fuer einen Dritten enthaelt
    kein ``.git``, und dort ist ein echter Name am teuersten - genau dort
    brach die Suche am 12.10.2026 ab.

    ``--others`` ist seit dem 13.10.2026 dabei: ``git ls-files`` allein nennt
    nur, was git schon **kennt**, also keine neu angelegte Datei. Und die neue
    Datei ist die, in der der Fehler frisch ist. ``--exclude-standard`` laesst
    aus, was in ``.gitignore`` steht, sonst liefe die Suche durch ``.venv``.
    """
    import os
    import subprocess

    try:
        roh = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=PROGRAMMORDNER, capture_output=True, text=True,
            check=True).stdout.split()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        roh = []
        for ordner, unter, gefunden in os.walk(PROGRAMMORDNER):
            unter[:] = [u for u in unter if u not in NICHT_BESTAND]
            for name in gefunden:
                roh.append(str(Path(ordner, name)
                               .relative_to(PROGRAMMORDNER).as_posix()))
    return [n for n in roh if n not in UNBERUEHRT]


def muster(liste: tuple[str, ...]) -> tuple:
    """Als ganzes Wort, Gross- und Kleinschreibung zaehlt.

    Viele deutsche Nachnamen sind auch gewoehnliche Woerter: "sauer" ist ein
    Adjektiv, "Sauerstoff" ein Gas. Ohne Wortgrenze waere jeder zweite Satz
    ein Treffer und die Pruefung nach einer Woche abgeschaltet.
    """
    import re as _re

    return tuple(_re.compile(rf"\b{_re.escape(w)}\b") for w in liste)


def treffer(gesucht: tuple) -> dict[str, list[str]]:
    """Welche Datei welches Muster traegt. Leer heisst: nichts gefunden."""
    gefunden: dict[str, list[str]] = {}
    for name in dateien():
        try:
            text = (PROGRAMMORDNER / name).read_text(encoding="utf-8")
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError, OSError):
            continue
        dabei = [m.pattern for m in gesucht if m.search(text)]
        if dabei:
            gefunden[name] = dabei
    return gefunden


def pruefen() -> int:
    """Nachsehen - ohne pytest, ohne Kosten, ohne einen Modellaufruf."""
    print()
    print("=" * 62)
    print("   Steht ein echter Name oder ein echtes Aktenzeichen im")
    print("   Programmordner?")
    print("=" * 62)
    print()
    bestand = dateien()
    _sagen(" ", f"{len(bestand)} Dateien angesehen - versionierte und neue.")
    print()

    # Das Aktenzeichenmuster braucht keine Liste und laeuft immer.
    nummern = treffer((AKTENZEICHEN,))
    if nummern:
        _sagen("✗", f"ECHTE AKTENZEICHEN in {len(nummern)} Datei(en):")
        for name in sorted(nummern):
            _sagen(" ", f"     {name}")
        _sagen(" ", "Ein Aktenzeichen beginnt hier mit X - die Kanzlei")
        _sagen(" ", "fuehrt D und T.")
    else:
        _sagen("✓", "Kein echtes Aktenzeichen (Muster D-nnn-jjjj / T-nnn-jjjj).")

    ort = finden()
    if ort is None:
        print()
        _sagen("!", "KEINE Sperrliste gefunden - nach NAMEN wurde NICHT gesucht.")
        _sagen(" ", "Gesucht wurde an:")
        for stelle in orte():
            _sagen(" ", f"     {stelle}")
        _sagen(" ", "Anlegen: SPERRLISTE-ANLEGEN.bat")
        _sagen(" ", "")
        _sagen(" ", "In einem Pruefpaket fuer einen Dritten ist das der")
        _sagen(" ", "vorgesehene Zustand. Auf einem Rechner der Kanzlei")
        _sagen(" ", "fehlt die Datei.")
        return 2

    try:
        liste = woerter(ort)
    except (OSError, UnicodeDecodeError) as fehler:
        print()
        _sagen("✗", f"Die Sperrliste liegt da, laesst sich aber nicht lesen: {fehler}")
        _sagen(" ", f"Ort: {ort}")
        return 2
    if not liste:
        print()
        _sagen("✗", "Die Sperrliste ist leer - dann prueft sie nichts.")
        _sagen(" ", f"Ort: {ort}")
        return 2

    print()
    _sagen("✓", f"Sperrliste gefunden: {len(liste)} Wort/Woerter.")
    _sagen(" ", f"Ort: {ort}")
    for wort in liste:
        _sagen(" ", f"     {verdeckt(wort)}")
    print()
    namen = treffer(muster(liste))
    if namen:
        _sagen("✗", f"GESPERRTE NAMEN in {len(namen)} Datei(en):")
        for name in sorted(namen):
            _sagen(" ", f"     {name}")
        print()
        _sagen(" ", "Diese Dateien bitte berichtigen, BEVOR der Ordner")
        _sagen(" ", "weitergegeben oder als ZIP heruntergeladen wird.")
        return 1

    _sagen("✓", "Kein gesperrter Name im Programmordner.")
    print()
    if nummern:
        return 1
    _sagen(" ", "Beides sauber. Der Ordner darf weitergegeben werden,")
    _sagen(" ", "soweit es um Namen und Aktenzeichen geht.")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(pruefen() if "--pruefen" in sys.argv else main())
