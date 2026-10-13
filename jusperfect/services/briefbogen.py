"""Den Entwurf auf den Briefbogen der Kanzlei setzen.

Aus der Kanzlei am 13.10.2026:

    „Entwurf-Funktion funktioniert noch nicht, jur|nodes lehnt ab, was ich
    erstmal nicht so schlimm finde. Koennen wir hier einen Briefbogen
    hinterlegen?"

Dazu kam die Briefbogen-Datei selbst: ein Word-Dokument mit Kopf- und
Fusszeilen, Logo, Schriften und Raendern - und einem leeren Rumpf.

**Deshalb wird der Briefbogen nicht nachgebaut, sondern benutzt.** Ein
Briefbogen ist mehr als Name und Anschrift: Er traegt Logos, Randmasse, eine
erste Seite, die anders aussieht als die folgenden, Schriftarten und eine
Fusszeile mit dem Partnerschaftsregister. Das alles nachzuzeichnen, waere
eine Faelschung des eigenen Briefbogens - aehnlich genug, um es nicht zu
merken, und irgendwo falsch. Dieses Modul oeffnet stattdessen die Datei der
Kanzlei und schreibt den Entwurfstext in ihren leeren Rumpf. Alles andere -
jede Kopfzeile, jedes Bild, jede Masseinheit - bleibt Byte fuer Byte, wie es
war.

**Das Programm schreibt nichts auf die Platte.** Das fertige Dokument
entsteht im Arbeitsspeicher und geht an den Browser; es landet dort, wo der
Bearbeiter es hinspeichert. Kein Ordner, keine Datei, kein Vermerk - der
Grundsatz gilt hier wie ueberall.

**Wo die Vorlage liegt: ausserhalb des Programmordners.** Denselben Weg
gehen Sperrliste und Promptbibliothek (Befund N01 vom 12.10.2026): Der
Briefbogen der Kanzlei hat in keiner ZIP etwas zu suchen, und er soll ein
neues ZIP ueberleben.
"""

from __future__ import annotations

import re
import shutil
import zipfile
from io import BytesIO
from pathlib import Path

#: Der Name der Vorlage. Immer derselbe, an beiden Orten.
DATEINAME = "jusperfect-briefbogen.docx"

#: Der Programmordner - zwei Ebenen ueber dieser Datei.
PROGRAMMORDNER = Path(__file__).resolve().parent.parent.parent

#: Der Rumpf des Word-Dokuments. Alles davor und danach bleibt unberuehrt.
RUMPF = "word/document.xml"

#: Zeichen, die XML 1.0 nicht kennt. Ein einziges davon macht das fertige
#: Dokument unlesbar - Word meldet dann nur "Die Datei ist beschaedigt" und
#: sagt nicht, warum.
_VERBOTEN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


class BriefbogenFehler(Exception):
    """Es gibt keine Vorlage, oder sie ist keine brauchbare Word-Datei."""


def orte() -> tuple[Path, ...]:
    """Wo gesucht wird - erst neben dem Programmordner, dann im Benutzerordner."""
    gefunden: list[Path] = []
    for ort in (PROGRAMMORDNER.parent / DATEINAME, Path.home() / DATEINAME):
        if ort not in gefunden:
            gefunden.append(ort)
    return tuple(gefunden)


def finden() -> Path | None:
    """Die hinterlegte Vorlage - oder ``None``, wenn es keine gibt."""
    for ort in orte():
        try:
            if ort.is_file():
                return ort
        except OSError:              # ein Pfad, den dieses System nicht mag
            continue
    return None


def hinterlegen(quelle: Path, ziel: Path | None = None) -> Path:
    """Eine Word-Datei als Briefbogen der Kanzlei ablegen.

    Geprueft wird vorher, ob sie sich ueberhaupt beschreiben laesst - eine
    Vorlage, die erst beim ersten Entwurf auffaellt, faellt zur
    unguenstigsten Zeit auf.
    """
    _rumpf_lesen(quelle)             # wirft, wenn es keine brauchbare Datei ist
    ziel = ziel or (finden() or orte()[0])
    try:
        shutil.copyfile(quelle, ziel)
    except OSError as fehler:
        raise BriefbogenFehler(
            f"Der Briefbogen liess sich nicht nach {ziel} legen: {fehler}") from fehler
    return ziel


# ── Der gefuehrte Weg ──────────────────────────────────────────────────────
#
# Aus der Kanzlei gelernt, mehrfach: Ein Nichtprogrammierer soll keine Datei
# mit einem abgezaehlten Namen an einen abgezaehlten Pfad kopieren muessen.
# Deshalb fragt das Programm und legt selbst ab.

def _sagen(zeichen: str, text: str) -> None:
    print(f"  {zeichen:<2} {text}")


def main() -> int:
    print()
    print("=" * 62)
    print("   Briefbogen hinterlegen")
    print("=" * 62)
    print()
    print("  Auf diesen Briefbogen setzt jusperfect einen Entwurf, wenn Sie")
    print("  beim Entwurf auf „Auf Briefbogen (Word)“ klicken.")
    print()
    print("  Gebraucht wird Ihre eigene Word-Vorlage (.docx) mit Kopfzeile,")
    print("  Fusszeile und Logo - und einem leeren Rumpf. Alles darin bleibt,")
    print("  wie es ist; nur der leere Rumpf bekommt den Text.")
    print()
    print("  Die Datei bleibt auf diesem Rechner, NEBEN dem Programmordner.")
    print("  Sie kommt nicht in eine ZIP und ueberlebt damit ein neues ZIP.")
    print()

    vorhanden = finden()
    if vorhanden is not None:
        _sagen("✓", f"Es liegt schon ein Briefbogen: {vorhanden}")
        print()
        antwort = input("  Ersetzen? [j/N] ").strip().lower()
        if antwort not in ("j", "ja"):
            _sagen(" ", "Es bleibt alles, wie es war.")
            return 1

    print()
    print("  Ziehen Sie die .docx-Datei in dieses Fenster (dann steht der")
    print("  Pfad von selbst da) und druecken Sie die Eingabetaste.")
    print()
    roh = input("  Datei: ").strip().strip('"').strip("'")
    if not roh:
        _sagen(" ", "Nichts angegeben. Es wurde nichts hinterlegt.")
        return 1
    quelle = Path(roh).expanduser()
    if not quelle.is_file():
        _sagen("✗", f"Dort liegt keine Datei: {quelle}")
        return 2
    try:
        ziel = hinterlegen(quelle)
    except BriefbogenFehler as fehler:
        _sagen("✗", str(fehler))
        return 2
    print()
    _sagen("✓", f"Briefbogen hinterlegt: {ziel}")
    _sagen(" ", "Beim naechsten Entwurf steht er zur Verfuegung.")
    return 0


def _rumpf_lesen(vorlage: Path) -> str:
    try:
        with zipfile.ZipFile(vorlage) as paket:
            return paket.read(RUMPF).decode("utf-8")
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError) as fehler:
        raise BriefbogenFehler(
            f"{vorlage.name} laesst sich nicht als Word-Dokument lesen ({fehler}). "
            "Bitte die Datei in Word oeffnen und als .docx speichern."
        ) from fehler


def _xml_text(wert: str) -> str:
    sauber = _VERBOTEN.sub("", wert)
    return (sauber.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _absatz(zeile: str) -> str:
    """Eine Zeile als Word-Absatz. Leere Zeilen bleiben leere Absaetze.

    Ohne eigene Formatierung: Welche Schrift, welcher Abstand und welcher
    Rand gelten, steht in der Vorlage der Kanzlei. Ein hier gesetzter Wert
    wuerde ihn ueberschreiben, und zwar unsichtbar.
    """
    if not zeile.strip():
        return "<w:p/>"
    return ('<w:p><w:r><w:t xml:space="preserve">'
            + _xml_text(zeile) + "</w:t></w:r></w:p>")


def _rumpf_ersetzen(xml: str, text: str) -> str:
    """Den leeren Rumpf durch den Entwurfstext ersetzen.

    Der Abschnittsblock ``w:sectPr`` am Ende bleibt stehen, und das ist der
    entscheidende Teil: In ihm stehen die Verweise auf Kopf- und Fusszeilen,
    die Randmasse und die Angabe, dass die erste Seite anders aussieht.
    Faellt er weg, bleibt ein leeres weisses Blatt mit dem richtigen Text und
    ohne Briefbogen - der Fehler waere auf dem Bildschirm kaum zu sehen und
    auf dem Papier nicht mehr zu heilen.
    """
    try:
        anfang = xml.index("<w:body>") + len("<w:body>")
        ende = xml.index("</w:body>")
    except ValueError as fehler:
        raise BriefbogenFehler(
            "In der Vorlage fehlt der Dokumentrumpf (w:body). Bitte die Datei "
            "in Word oeffnen und als .docx speichern.") from fehler
    alt = xml[anfang:ende]
    sect = ""
    stelle = alt.rfind("<w:sectPr")
    if stelle >= 0:
        sect = alt[stelle:]
    absaetze = "".join(_absatz(z) for z in text.replace("\r\n", "\n").split("\n"))
    return xml[:anfang] + absaetze + sect + xml[ende:]


def erzeugen(text: str, vorlage: Path | None = None) -> bytes:
    """Der Entwurf auf dem Briefbogen - als Word-Datei im Arbeitsspeicher.

    Jede andere Datei des Pakets wird unveraendert uebernommen: Kopfzeilen,
    Fusszeilen, Bilder, Schriften, Formatvorlagen. Geaendert wird genau eine,
    ``word/document.xml``, und in ihr genau der leere Rumpf.
    """
    vorlage = vorlage or finden()
    if vorlage is None:
        raise BriefbogenFehler(
            "Es ist kein Briefbogen hinterlegt. Die Datei "
            f"„{DATEINAME}“ gehoert neben den Programmordner "
            f"({orte()[0].parent}) - dort ueberlebt sie ein neues ZIP.")
    neuer_rumpf = _rumpf_ersetzen(_rumpf_lesen(vorlage), text)
    puffer = BytesIO()
    try:
        with zipfile.ZipFile(vorlage) as alt, \
             zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as neu:
            for eintrag in alt.infolist():
                inhalt = (neuer_rumpf.encode("utf-8") if eintrag.filename == RUMPF
                          else alt.read(eintrag.filename))
                neu.writestr(eintrag, inhalt)
    except (OSError, zipfile.BadZipFile) as fehler:
        raise BriefbogenFehler(
            f"Der Briefbogen liess sich nicht beschreiben: {fehler}") from fehler
    return puffer.getvalue()


if __name__ == "__main__":
    raise SystemExit(main())
