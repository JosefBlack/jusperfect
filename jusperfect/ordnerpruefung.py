"""Die Laufwerksprobe: Taugt der jurnodes-Ordnerexport für jusperfect?

``python -m jusperfect.ordnerpruefung "J:\\Akten"`` – oder ORDNER-PRUEFEN.bat.

**Warum diese Probe der letzte Schritt vor der ersten echten Akte ist.**
jur|nodes lässt sich auf zwei Wegen anbinden: über die REST-Schnittstelle, für
die uns die Dokumentation fehlt, oder über das eingebundene Laufwerk – es ist
ein WebDAV-Server. Die Kanzlei hat den Laufwerksweg gewählt. Damit hängt alles
daran, ob der Ordnerbaum so aussieht, wie jusperfect ihn erwartet:

    <Wurzel>/<Anwalt>/<Jahr>/<Aktenzeichen Bezeichnung>/<Dokumente>

Stimmt das nicht, findet das Programm **null Akten** – und eine leere Liste
sagt nicht, woran es liegt. Genau das beantwortet diese Probe, und zwar bevor
jemand vor einem leeren Bildschirm sitzt.

Sie sieht nur nach. Sie ändert nichts, legt nichts an und löscht nichts; die
Schreibprobe schreibt eine einzelne Datei in einen eigenen Ordner und entfernt
sie sofort wieder.

**Kein Akteninhalt in der Ausgabe** – Aktenzeichen und Bezeichnungen erscheinen
nur als Beispiele, und die stehen ohnehin im Ordnernamen. Wer die Ausgabe
weitergibt, prüfe diese Zeilen kurz durch.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from typing import Callable

from jusperfect.bericht import mitschreiben, nur_schirm
from jusperfect.config import Einstellungen
from jusperfect.jurnodes.base import GEDAECHTNIS_DATEI, JurNodesFehler
from jusperfect.jurnodes.webdav_adapter import (DOKUMENT_ENDUNGEN, VERMERK_ORDNER,
                                                WebDavJurNodesAdapter)
from jusperfect.security.approval import Freigabestelle

BEISPIELE = 5
TRENNER = "─" * 70
#: Der Befund zum Nachlesen und Weitergeben.
BERICHT = "ordnerpruefung.txt"


def _sagen(zeichen: str, text: str) -> None:
    print(f"  {zeichen}  {text}")


def _fastreffer(kennung: str) -> re.Pattern[str] | None:
    """Namen, die nach Archiv aussehen, aber nicht die Kennung sind.

    Der Wortstamm ohne Endung fängt „Archiv", „Archivierung", „archiv."
    – die Fälle, in denen die Konvention leise abweicht.
    """
    stamm = kennung.rstrip("t").rstrip("ier") or kennung
    return re.compile(re.escape(stamm), re.IGNORECASE) if stamm else None


# ── Der Aufbau des Ordnerbaums ───────────────────────────────────────────────

def aufbau_pruefen(wurzel: Path) -> list[tuple[str, str]]:
    """Wo der erwartete Baum abweicht – als Liste aus (Zeichen, Satz).

    Das ist der Teil, der in der alten Fassung fehlte. Sie zählte Akten und
    meldete bei null Akten nur, es sei keine archivierte darunter – während in
    Wahrheit der ganze Baum anders gebaut war und niemand es erfuhr.
    """
    befunde: list[tuple[str, str]] = []
    try:
        ebene1 = [p for p in wurzel.iterdir() if p.is_dir() and not p.name.startswith(".")]
    except OSError as fehler:
        return [("✗", f"Der Ordner ist nicht lesbar ({type(fehler).__name__}). "
                      "Ist das Laufwerk verbunden?")]

    if not ebene1:
        return [("✗", "Im Aktenordner liegt kein einziger Unterordner. Erwartet wird "
                      "auf der ersten Ebene je ein Ordner Anwalt.")]
    befunde.append(("✓", f"Erste Ebene (Anwalt): {len(ebene1)} Ordner, "
                         f"z. B. {', '.join(sorted(p.name for p in ebene1)[:3])}."))

    mit_jahr, ohne_jahr = [], []
    for anwalt in ebene1:
        try:
            unter = [p for p in anwalt.iterdir() if p.is_dir() and not p.name.startswith(".")]
        except OSError:
            continue
        (mit_jahr if any(p.name.isdigit() for p in unter) else ohne_jahr).append(anwalt)

    if not mit_jahr:
        beispiel = ""
        if ohne_jahr:
            try:
                namen = [p.name for p in sorted(ohne_jahr[0].iterdir())[:3] if p.is_dir()]
                beispiel = f" Gefunden wurde dort: {', '.join(namen)}." if namen else ""
            except OSError:
                pass
        befunde.append(("✗", "Auf der zweiten Ebene steht kein Jahresordner. Erwartet "
                             "wird eine reine Jahreszahl wie „2026“." + beispiel))
        befunde.append((" ", "Ohne diese Ebene findet jusperfect keine einzige Akte."))
        return befunde

    befunde.append(("✓", f"Zweite Ebene (Jahr): bei {len(mit_jahr)} von {len(ebene1)} "
                         "Anwaltsordnern gefunden."))
    if ohne_jahr:
        befunde.append(("!", f"Ohne Jahresordner und damit übersprungen: "
                             f"{', '.join(sorted(p.name for p in ohne_jahr)[:BEISPIELE])}."))
    return befunde


def doppelte_aktenzeichen(wurzel: Path,
                          adapter: WebDavJurNodesAdapter,
                          ) -> tuple[int, dict[str, list[Path]]]:
    """Aktenordner zählen und die Aktenzeichen finden, die mehrfach vorkommen.

    Aus der Kanzlei, 23.09.2026: „die akten von herrn thunert sind jedoch
    zahlen und auch keine namen des mandanten." Damit heißt eine Akte zum
    Beispiel schlicht ``0101``.

    Warum das zählt: Der Adapter führt seinen Index unter dem Aktenzeichen
    (``_baum``), und dort gewinnt das erste Vorkommen. Eine reine Zahl wird
    aber gern je Jahrgang neu vergeben – ``0101`` von 2024 und ``0101`` von
    2025 sind dann zwei verschiedene Akten mit demselben Schlüssel. Die
    zweite verschwindet **lautlos**: Sie steht in keiner Liste, und wer sie
    sucht, bekommt die andere.

    Genau das darf eine Kanzlei nicht erst bemerken, wenn eine Akte fehlt.
    Gezählt wird deshalb hier, mit derselben Zerlegung, die auch der Betrieb
    benutzt – sonst misst die Probe etwas anderes als das, was später läuft.
    """
    ordner_gesamt = 0
    nach_kennung: dict[str, list[Path]] = {}
    try:
        anwaelte = [p for p in wurzel.iterdir() if p.is_dir() and not p.name.startswith(".")]
    except OSError:
        return 0, {}
    for anwalt in anwaelte:
        try:
            jahre = [p for p in anwalt.iterdir() if p.is_dir() and p.name.isdigit()]
        except OSError:
            continue
        for jahr in jahre:
            try:
                akten = [p for p in jahr.iterdir() if p.is_dir() and not p.name.startswith(".")]
            except OSError:
                continue
            for akte in akten:
                ordner_gesamt += 1
                _, name = adapter._status_aus_name(akte.name)
                kennung, _ = adapter._teile(name)
                nach_kennung.setdefault(kennung, []).append(akte)
    doppelte = {k: v for k, v in nach_kennung.items() if len(v) > 1}
    return ordner_gesamt, doppelte


# ── Was in den Akten liegt ───────────────────────────────────────────────────

def dateien_zaehlen(wurzel: Path,
                    lebenszeichen: Callable[[int], None] | None = None,
                    ) -> tuple[Counter, Counter, int]:
    """Endungen der lesbaren und der übersprungenen Dateien, und die Bytes.

    Die Kanzlei soll vorher wissen, was NICHT durchgeht. Eine Akte, die zur
    Hälfte aus .msg-Dateien besteht, ist mit jusperfect nur zur Hälfte
    bearbeitet – und das soll man erfahren, bevor man sich darauf verlässt.

    ``lebenszeichen`` bekommt die Zahl der bisher gesehenen Dateien gemeldet.
    Das ist kein Schmuck: Dieser Durchgang fasst **jede** Datei des Laufwerks
    einmal an, und auf einem WebDAV-Laufwerk ist jeder dieser Griffe ein Gang
    über das Netz. Bei einem gewachsenen Aktenbestand dauert das Minuten. Ohne
    ein Lebenszeichen sieht das aus wie ein hängendes Programm – und wer ein
    hängendes Programm vor sich zu haben glaubt, bricht ab.
    """
    lesbar, uebersprungen = Counter(), Counter()
    bytes_gesamt = 0
    gesehen = 0
    for pfad in wurzel.rglob("*"):
        gesehen += 1
        if lebenszeichen and gesehen % 250 == 0:
            lebenszeichen(gesehen)
        if not pfad.is_file() or pfad.name.startswith("."):
            continue
        if VERMERK_ORDNER in pfad.parts:
            continue
        endung = pfad.suffix.lower() or "(ohne Endung)"
        if endung in DOKUMENT_ENDUNGEN:
            lesbar[endung] += 1
            try:
                bytes_gesamt += pfad.stat().st_size
            except OSError:
                pass
        else:
            uebersprungen[endung] += 1
    return lesbar, uebersprungen, bytes_gesamt


def schreibprobe(wurzel: Path) -> tuple[bool, str]:
    """Darf jusperfect einen Vermerk ablegen? Schreibt und entfernt eine Datei.

    Ohne Schreibrecht funktioniert alles – bis zu dem Tag, an dem jemand einen
    freigegebenen Vermerk zurückschreiben will. Das ist der schlechteste
    Zeitpunkt, es zu erfahren.
    """
    probe = wurzel / ".jusperfect-schreibprobe"
    try:
        probe.write_text("Probe von jusperfect. Diese Datei wird sofort entfernt.\n",
                         encoding="utf-8")
    except OSError as fehler:
        return False, f"{type(fehler).__name__}"
    try:
        probe.unlink()
    except OSError:
        return True, "geschrieben, aber nicht wieder entfernt"
    return True, ""


def main(argv: list[str]) -> int:
    """Führt die Probe aus und schreibt den Bericht - auf den Schirm und in
    die Datei, beides zugleich."""
    with mitschreiben(BERICHT) as geschrieben:
        ende = _ablauf(argv)
    if geschrieben:
        print(f"  Der Befund steht auch in {BERICHT}.")
        print()
    return ende


def _ablauf(argv: list[str]) -> int:
    e = Einstellungen.aus_umgebung()
    wurzel_text = argv[0] if argv else e.jurnodes_webdav_pfad

    print(TRENNER)
    print("  jusperfect – taugt der Aktenordner?")
    print(TRENNER)
    print()

    if not wurzel_text:
        _sagen("✗", "Kein Aktenordner angegeben.")
        _sagen(" ", "Den Pfad als Argument übergeben oder "
                    "JUSPERFECT_JURNODES_WEBDAV setzen.")
        return 2

    # Leerzeichen und Anfuehrungszeichen weg, bevor daraus ein Pfad wird.
    # In der Kanzlei ist genau das passiert: Beim Eintippen rutschte ein
    # Leerzeichen vor das "J:". cmd gibt es bei "set /p" unveraendert weiter,
    # und " J:\Akten" gibt es nicht. Die Meldung lautete darauf "Diesen Ordner
    # gibt es nicht - ist das Laufwerk verbunden?" - richtig und irrefuehrend
    # zugleich, denn das Laufwerk war verbunden. Ein Leerzeichen sieht man auf
    # einem schwarzen Schirm nicht.
    # Die Anfuehrungszeichen kommen aus dem Explorer: "Als Pfad kopieren" legt
    # sie mit in die Zwischenablage.
    wurzel_text = wurzel_text.strip().strip('"').strip()
    if not wurzel_text:
        _sagen("✗", "Kein Aktenordner angegeben.")
        return 2

    wurzel = Path(wurzel_text)
    # In Anfuehrungszeichen, damit ein Leerzeichen am Rand zu sehen ist.
    _sagen(" ", f"Aktenordner: \"{wurzel}\"")
    if not wurzel.is_dir():
        print()
        _sagen("✗", "Diesen Ordner gibt es nicht oder er ist nicht erreichbar.")
        _sagen(" ", "Drei Dinge kommen in Frage:")
        _sagen(" ", "1. Der Pfad ist anders geschrieben. Oben steht er in")
        _sagen(" ", "   Anführungszeichen, genau so, wie er angekommen ist.")
        _sagen(" ", "2. Das Laufwerk ist nicht verbunden. Netzlaufwerke sind je")
        _sagen(" ", "   Windows-Konto verbunden – im neuen Konto fehlt es zunächst.")
        _sagen(" ", "3. Der Ordner heißt anders. Im Explorer nachsehen.")
        return 1

    print()
    print("AUFBAU DES ORDNERBAUMS")
    print(TRENNER)
    _sagen(" ", "Erwartet: <Wurzel>/<Anwalt>/<Jahr>/<Aktenzeichen Bezeichnung>/")
    print()
    aufbau = aufbau_pruefen(wurzel)
    for zeichen, satz in aufbau:
        _sagen(zeichen, satz)
    if any(z == "✗" for z, _ in aufbau):
        print()
        print(TRENNER)
        _sagen("✗", "Der Aufbau passt nicht. Solange das so ist, findet")
        _sagen(" ", "jusperfect keine Akte – und zwar unabhängig von allem anderen.")
        _sagen(" ", "Bitte diese Ausgabe an die Entwicklung schicken; der Adapter")
        _sagen(" ", "lässt sich an einen anderen Aufbau anpassen, aber nicht raten.")
        print(TRENNER)
        return 1

    kennung = e.archiv_kennung
    try:
        adapter = WebDavJurNodesAdapter(wurzel, Freigabestelle(), schreibbar=False,
                                        archiv_kennung=kennung)
        akten = adapter.akten_suchen()
    except JurNodesFehler as fehler:
        print()
        _sagen("✗", f"Der Aktenordner ist nicht lesbar: {fehler}")
        return 1

    print()
    print("AKTEN")
    print(TRENNER)
    archiviert = [a for a in akten if a.status == "archiviert"]
    laufend = [a for a in akten if a.status == "laufend"]
    _sagen("✓" if akten else "✗", f"Gefunden: {len(akten)} Akte(n).")

    # Der Adapter fuehrt seinen Index unter dem Aktenzeichen; das erste
    # Vorkommen gewinnt. Kommt eines zweimal vor, ist eine Akte lautlos weg.
    ordner_gesamt, doppelte = doppelte_aktenzeichen(wurzel, adapter)
    if doppelte:
        verloren = sum(len(v) - 1 for v in doppelte.values())
        print()
        _sagen("✗", f"{ordner_gesamt} Aktenordner, aber nur {len(akten)} verschiedene")
        _sagen(" ", f"Aktenzeichen. {verloren} Akte(n) sind damit nicht erreichbar.")
        _sagen(" ", "jusperfect führt seine Akten unter dem Aktenzeichen. Kommt eines")
        _sagen(" ", "zweimal vor, zeigt es die erste und die zweite gar nicht - ohne")
        _sagen(" ", "Meldung. Das fällt sonst erst auf, wenn eine Akte fehlt.")
        _sagen(" ", "Typisch ist das bei reinen Zahlen, die je Jahrgang neu vergeben")
        _sagen(" ", "werden: 0101 aus 2024 und 0101 aus 2025 sind zwei Akten.")
        print()
        _sagen(" ", "Betroffen (bis zu 5 Beispiele, mit ihren Jahrgängen):")
        for kennung, pfade in sorted(doppelte.items())[:BEISPIELE]:
            jahre = ", ".join(sorted(x.parent.name + "/" + x.parent.parent.name for x in pfade))
            _sagen(" ", f"     {kennung:<16} {len(pfade)}x - {jahre}")
        print()
        _sagen(" ", "Das ist zu beheben, bevor mit echten Akten gearbeitet wird.")
        _sagen(" ", "Bitte melden - der Adapter kann die Akte auch unter")
        _sagen(" ", "Anwalt/Jahr/Aktenzeichen führen; dann ist sie eindeutig.")
    elif ordner_gesamt:
        _sagen("✓", "Jedes Aktenzeichen kommt genau einmal vor.")

    if not akten:
        _sagen(" ", "Der Baum stimmt, aber in den Jahresordnern liegt keine Akte.")
        _sagen(" ", "Ist das Jahr richtig gewählt? Liegen die Akten eine Ebene tiefer?")
    else:
        _sagen(" ", f"davon als archiviert erkannt: {len(archiviert)}, als laufend: {len(laufend)}")
        for titel, liste in (("Archiviert", archiviert), ("Laufend", laufend)):
            if liste:
                print()
                _sagen(" ", f"{titel} (bis zu {BEISPIELE} Beispiele):")
                for a in liste[:BEISPIELE]:
                    _sagen(" ", f"     {a.aktenzeichen:<16} {a.bezeichnung}  [{a.sachbearbeiter}]")

    print()
    print("DIE ARCHIV-KENNUNG")
    print(TRENNER)
    _sagen(" ", f"Gesucht wird „{kennung}“ im Ordnernamen "
                "(ganzes Wort, Groß- und Kleinschreibung egal).")
    _sagen(" ", "An ihr hängt die Aufbewahrung: Nur eine archivierte Akte bekommt")
    _sagen(" ", "eine Löschfrist. Ist der Status unbekannt, wird nichts gelöscht.")
    muster = _fastreffer(kennung) if kennung else None
    verdaechtig = [a for a in laufend if muster.search(a.bezeichnung)] if muster else []
    if not kennung:
        _sagen("!", "JUSPERFECT_ARCHIV_KENNUNG ist leer – der Status bleibt für alle")
        _sagen(" ", "Akten unbekannt. Gelöscht wird dann nie; das ist die sichere Seite.")
    elif verdaechtig:
        _sagen("!", "Diese Akten gelten als laufend, ihr Name sieht aber nach Archiv aus:")
        for a in verdaechtig[:BEISPIELE]:
            _sagen(" ", f"     {a.aktenzeichen:<16} {a.bezeichnung}")
        _sagen(" ", "Wird die Kennung dort anders geschrieben? Dann")
        _sagen(" ", "JUSPERFECT_ARCHIV_KENNUNG auf die tatsächliche Schreibweise setzen.")
    elif not archiviert and akten:
        _sagen("!", "Keine einzige archivierte Akte erkannt. Entweder ist keine")
        _sagen(" ", "archiviert, oder die Kennung wird anders geschrieben.")
    else:
        _sagen("✓", "Die Kennung wird im Bestand erkannt.")

    print()
    print("DIE DOKUMENTE")
    print(TRENNER)
    # Nur auf den Schirm: Im Bericht waeren vierzig Zwischenstaende Ballast.
    schirm = nur_schirm()

    def lebenszeichen(gesehen: int) -> None:
        schirm.write(f"\r     … {gesehen} Dateien gesehen")
        schirm.flush()

    lesbar, uebersprungen, bytes_gesamt = dateien_zaehlen(wurzel, lebenszeichen)
    if sum(lesbar.values()) + sum(uebersprungen.values()):
        schirm.write("\r" + " " * 40 + "\r")
        schirm.flush()
    gesamt = sum(lesbar.values()) + sum(uebersprungen.values())
    if not gesamt:
        _sagen("!", "In den Akten liegt keine Datei.")
    else:
        anteil = round(100 * sum(lesbar.values()) / gesamt)
        _sagen("✓" if anteil >= 80 else "!",
               f"{sum(lesbar.values())} von {gesamt} Dateien sind lesbar ({anteil} %).")
        _sagen(" ", "Lesbar: " + ", ".join(f"{k} {v}" for k, v in lesbar.most_common(8)))
        if uebersprungen:
            _sagen("!", "Übersprungen – daraus holt jusperfect keinen Text:")
            _sagen(" ", "     " + ", ".join(f"{k} {v}" for k, v in uebersprungen.most_common(8)))
            _sagen(" ", "Häufig sind das .msg (Outlook) und .eml. Wer sie braucht,")
            _sagen(" ", "sagt Bescheid – sie lassen sich aufnehmen.")
        # Hier stand einmal "Textmenge: rund 53490.8 MB ... Zum Vergleich: Die
        # grosse Testakte hat 882 kB und kostet rund 2,50 EUR." Beides war fuer
        # sich richtig und nebeneinander falsch: Gemessen wird die DATEIGROESSE,
        # verglichen wurde mit reinem TEXT. Ein eingescanntes PDF besteht fast
        # ganz aus Bild; von 18 MB Akte sind vielleicht 100 kB Text. Wer die
        # beiden Zahlen nebeneinander liest, rechnet sich fuenfzig Euro je Akte
        # aus und legt das Vorhaben weg. Eine Zahl, die zur falschen
        # Entscheidung fuehrt, ist schlimmer als keine.
        if akten:
            je_akte = bytes_gesamt / len(akten) / 1_000_000
            _sagen(" ", f"Umfang der lesbaren Dateien: rund {bytes_gesamt/1_000_000_000:.1f} GB, "
                        f"im Mittel {je_akte:.1f} MB je Akte.")
            _sagen(" ", "Das ist die Dateigröße, NICHT die Textmenge. Ein")
            _sagen(" ", "eingescanntes PDF besteht fast ganz aus Bild; der Text")
            _sagen(" ", "darin ist ein Bruchteil davon. Aus dieser Zahl lassen sich")
            _sagen(" ", "die Kosten deshalb nicht ableiten.")
            bilder = sum(v for k, v in lesbar.items()
                         if k in (".jpg", ".jpeg", ".png", ".tif", ".tiff"))
            if bilder:
                anteil_bilder = round(100 * bilder / sum(lesbar.values()))
                print()
                _sagen("!", f"{bilder} Bilddateien ({anteil_bilder} % der lesbaren). Dazu")
                _sagen(" ", "kommen eingescannte PDF, die von aussen nicht zu erkennen")
                _sagen(" ", "sind. Sie brauchen eine Texterkennung (AWS Textract), und")
                _sagen(" ", "die kostet je Seite - getrennt vom Modell.")
            print()
            _sagen(" ", "Was eine Akte wirklich kostet, sagt erst ein Einlesen. Nehmen")
            _sagen(" ", "Sie dafür eine mittelgroße Akte: Der Kostenzähler im Programm")
            _sagen(" ", "nennt den Betrag auf den Cent, bevor etwas Weiteres geschieht.")

    print()
    print("SCHREIBRECHT: VERMERK UND AKTENGEDÄCHTNIS")
    print(TRENNER)
    # Zwei Stellen, nicht eine. Aus der Kanzlei: "Mit dem Zurueckschreiben
    # fehlt, dass das Programm das Aktengedaechtnis auf den Server schreiben
    # darf." Das ist richtig und war eine Luecke: Geprueft wurde nur die
    # WURZEL. Geschrieben wird aber IN DER AKTE - der freigegebene Vermerk
    # nach <Akte>/Vermerke/, das Aktengedaechtnis als einzelne Datei daneben.
    # Auf einem WebDAV-Server koennen die Rechte je Ebene verschieden sein;
    # eine schreibbare Wurzel sagt nichts ueber den Aktenordner.
    _sagen(" ", "Geschrieben wird an zwei Stellen: der freigegebene Vermerk nach")
    _sagen(" ", f"<Akte>/{VERMERK_ORDNER}/, das Gedächtnis als eine einzelne")
    _sagen(" ", f"Datei ({GEDAECHTNIS_DATEI}) in der Akte selbst.")
    print()

    stellen: list[tuple[str, Path]] = [("Die Wurzel des Aktenordners", wurzel)]
    if akten:
        try:
            # _ordner ist der einzige Weg von der Aktenkennung zum Ordner;
            # oeffentlich gibt der Adapter ihn nicht heraus, weil ihn sonst
            # niemand braucht.
            stellen.append((f"Der Aktenordner (Beispiel: {akten[0].aktenzeichen})",
                            adapter._ordner(akten[0].id)))
        except JurNodesFehler as fehler:
            # Nicht stillschweigend uebergehen: Ohne diese Zeile fehlt die
            # zweite Probe im Befund, und niemand weiss, ob sie bestanden oder
            # gar nicht stattgefunden hat. Genau so ist es am 23.09.2026 in der
            # Kanzlei ausgegangen.
            _sagen("!", f"Der Aktenordner liess sich nicht anfassen: {fehler}")
            _sagen(" ", "Damit ist NUR die Wurzel geprüft, nicht die Akte selbst.")
            print()

    alles_darf = True
    for name, ordner in stellen:
        darf, grund = schreibprobe(ordner)
        alles_darf = alles_darf and darf
        if darf and not grund:
            _sagen("✓", f"{name}: jusperfect darf schreiben.")
        elif darf:
            _sagen("!", f"{name}: geschrieben, aber {grund}.")
            _sagen(" ", "Bitte .jusperfect-schreibprobe von Hand entfernen.")
        else:
            _sagen("✗", f"{name}: kein Schreibrecht ({grund}).")

    if alles_darf:
        _sagen(" ", "Die Probedateien wurden angelegt und sofort wieder entfernt.")
    else:
        print()
        _sagen(" ", "Lesen und Arbeiten geht trotzdem, aber zwei Dinge nicht:")
        _sagen(" ", "Ein freigegebener Vermerk liesse sich nicht zurückschreiben,")
        _sagen(" ", "und das Gedächtnis liesse sich nicht in der Akte ablegen.")
        _sagen(" ", "Beides fiele sonst erst beim ersten Versuch auf – beim")
        _sagen(" ", "Gedächtnis womöglich erst Wochen später.")

    print()
    print(TRENNER)
    _sagen("✓", "Die Probe ist durchgelaufen. Es wurde nichts verändert.")
    _sagen(" ", "Nächster Schritt: das Schutzgeländer (AWS-EINRICHTEN.md, Schritt 9).")
    _sagen(" ", "Ohne es startet das Programm mit echten Akten nicht.")
    print(TRENNER)
    print()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
