"""Den jur|nodes-Zugang hinterlegen – Adresse, Benutzer, Schlüssel.

**Warum dafür ein eigenes Programm nötig ist.** Der Schlüssel darf in keine
Datei des Programmordners, denn der wird als ZIP weitergegeben, und er darf
erst recht nicht in die Versionsverwaltung. Er gehört in die Umgebung des
Windows-Benutzers – dorthin, wo ihn nur dieses Windows-Konto sieht.

Der Weg dahin heißt ``setx`` und ist für einen Anwender keiner: Er verlangt
eine Eingabeaufforderung, drei fehlerträchtige Befehle und die Kenntnis, dass
die Werte erst in einem **neuen** Fenster gelten. Genau daran ist in dieser
Kanzlei schon die AWS-Einrichtung hängengeblieben, weshalb es dafür
``jusperfect.zugang`` gibt. Hier ist es dasselbe noch einmal.

Der Schlüssel wird verdeckt eingegeben und nirgends ausgegeben – auch nicht
zur Bestätigung. Was im schwarzen Fenster steht, liest der Nächste mit.

Gespeichert werden drei Werte:

* ``JUSPERFECT_JURNODES_URL`` – die Adresse der Schnittstelle
* ``JURNODES_API_USER``      – der Benutzername
* ``JURNODES_API_KEY``       – der Schlüssel
* ``JUSPERFECT_GUARDRAIL_ID`` – die Kennung des Schutzgeländers

Das Schutzgeländer ist kein Geheimnis. Es steht hier trotzdem, weil es aus
demselben Grund hierhergehört: Was in einer Datei des Programmordners steht,
ist beim nächsten Auspacken weg.

Wer je Bereich einen eigenen Schlüssel bekommt, kann ihn zusätzlich unter
``JURNODES_API_KEY_AKTEN``, ``..._DATEISYSTEM``, ``..._BEZIEHUNGEN`` oder
``..._TODO`` hinterlegen; ohne einen solchen gilt der allgemeine.
"""

from __future__ import annotations

import getpass
import os
import re
import subprocess
import sys
from pathlib import Path

TRENNER = "=" * 60

#: Die Werte, die gespeichert werden - Name, Frage, verdeckt?
#:
#: Das Schutzgelaender steht hier, obwohl es zu AWS gehoert und kein
#: Geheimnis ist. Grund: Am 25.09.2026 stand seine Kennung in
#: START-JURNODES.bat, also in einer Datei des Programmordners - und die
#: wird beim Auspacken einer neuen Fassung ueberschrieben. Die Kanzlei
#: bekam daraufhin "Es fehlt das Schutzgelaender" und kam nicht mehr an
#: die echten Akten. Was eine Einrichtung ueberleben soll, gehoert nicht
#: in den Ordner, den wir austauschen.
FELDER = (
    ("JUSPERFECT_JURNODES_URL", "Adresse der Schnittstelle", False),
    ("JURNODES_API_USER", "Benutzername", False),
    ("JURNODES_API_KEY", "Token (wird nicht angezeigt)", True),
    ("JUSPERFECT_GUARDRAIL_ID", "Kennung des Schutzgelaenders (Bedrock)", False),
)


#: Wie die Kennung in einer alten START-JURNODES.bat aussah.
_GELAENDER_ZEILE = re.compile(
    r"^\s*set\s+\"?JUSPERFECT_GUARDRAIL_ID=([^\"\r\n]+)\"?\s*$",
    re.IGNORECASE | re.MULTILINE)


def _sagen(zeichen: str, text: str) -> None:
    print(f"  {zeichen}  {text}")


def gelaender_aus_alter_fassung(start: Path | None = None) -> tuple[str, Path] | None:
    """Die Kennung des Schutzgelaenders in einem alten Programmordner suchen.

    Aus der Kanzlei am 25.09.2026: Die Kennung stand in START-JURNODES.bat
    und war nach dem Auspacken der neuen Fassung weg. Die Anweisung lautete
    daraufhin: alten Ordner suchen, die .bat mit Rechtsklick bearbeiten,
    Zeile 25, hinter dem Gleichheitszeichen markieren, kopieren, nicht
    speichern. Darauf kam die Antwort "aender du das" - zu Recht.

    **Eine Anleitung, die den Anwender in eine Programmdatei schauen
    laesst, ist keine Loesung, sondern eine Zumutung.** Was dieses Programm
    selbst finden kann, sucht es selbst.

    Gesucht wird nur dort, wo ein ausgepackter Ordner liegt: neben dem
    eigenen, und in Downloads, auf dem Schreibtisch und in Dokumenten.
    Gelesen wird ausschliesslich START-JURNODES.bat, und nur diese eine
    Zeile. Geschrieben wird nichts.
    """
    hier = (start or Path(__file__).resolve().parent.parent)
    orte = [hier.parent]
    zuhause = Path.home()
    for name in ("Downloads", "Desktop", "Documents", "Dokumente",
                 "Schreibtisch"):
        orte.append(zuhause / name)

    gesehen: set[Path] = set()
    for ort in orte:
        try:
            if not ort.is_dir():
                continue
        except OSError:
            continue
        # Eine Ebene tief: ein ausgepackter Ordner liegt direkt darin.
        kandidaten = [ort / "START-JURNODES.bat"]
        try:
            for kind in sorted(ort.iterdir()):
                if kind.is_dir():
                    kandidaten.append(kind / "START-JURNODES.bat")
        except OSError:
            continue
        for datei in kandidaten:
            if datei in gesehen or datei.parent == hier:
                continue
            gesehen.add(datei)
            try:
                if not datei.is_file():
                    continue
                text = datei.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            treffer = _GELAENDER_ZEILE.search(text)
            if treffer:
                wert = treffer.group(1).strip().strip('"').strip()
                # Die neue Fassung traegt dort eine leere Hilfsvariable.
                if wert and not wert.startswith("%"):
                    return wert, datei
    return None


def _maskiert(wert: str) -> str:
    """Nur so viel, dass man zwei Schlüssel unterscheiden kann."""
    return f"{wert[:3]}…{wert[-3:]}" if len(wert) > 8 else "…"


def hinweise_zur_adresse(wert: str) -> list[str]:
    """Was an einer eingegebenen Adresse auffällt – Hinweis, kein Abbruch.

    Eine Adresse mit Leerzeichen oder ohne ``https://`` weist das Programm
    später ab; das dann zu erfahren, kostet einen Anlauf. Dieselbe Falle wie
    beim Aktenordner, wo ein Leerzeichen vor ``J:`` einen Nachmittag gekostet
    hat – auf einem schwarzen Schirm sieht man es nicht.
    """
    hinweise = []
    if not wert.startswith("https://"):
        hinweise.append("Die Adresse muss mit https:// beginnen – "
                        "jusperfect weist alles andere ab.")
    if wert != wert.strip() or any(z.isspace() for z in wert):
        hinweise.append("Es steckt ein Leerzeichen darin – das gehört nicht dazu.")
    if wert.rstrip("/").endswith(("/record", "/record/search")):
        hinweise.append("Das sieht nach einem einzelnen Pfad aus. Gebraucht wird "
                        "die Adresse davor, auf der alle Pfade aufsetzen.")
    return hinweise


#: Beschriftungen, die beim Kopieren aus einer Anzeige mitkommen.
_BESCHRIFTUNGEN = (
    "schnittstelle", "adresse", "benutzer", "benutzername", "token",
    "schluessel", "schlüssel", "schutzgelaender", "schutzgeländer",
    "kennung", "guardrail", "url",
)


def ohne_beschriftung(wert: str) -> str:
    """``Benutzer:        user_2`` zu ``user_2``.

    Aus der Kanzlei am 25.09.2026: Genau das stand im Windows-Konto - die
    ganze Zeile aus der Uebersicht des Starters, mitsamt Beschriftung und
    Leerzeichen. jur|nodes kennt keinen Benutzer dieses Namens und lehnte
    mit 401 ab; die Meldung sprach von fehlenden Rechten, und die Suche ging
    eine Stunde in die Rechteverwaltung.

    **Wer eine Uebersicht auf den Schirm schreibt, muss damit rechnen, dass
    sie kopiert wird.** Das ist kein Bedienfehler, sondern das Naechstliegende:
    Dort steht der Wert, den das Programm haben will.

    Abgeschnitten wird nur, wenn vor dem Doppelpunkt eine bekannte
    Beschriftung steht. Eine Adresse traegt selbst einen ("https:"), und die
    darf nicht verlorengehen.
    """
    wert = wert.strip()
    if ":" not in wert:
        return wert
    vorn, hinten = wert.split(":", 1)
    if vorn.strip().lower() in _BESCHRIFTUNGEN and hinten.strip():
        return hinten.strip()
    return wert


def was_daran_nicht_stimmt(name: str, wert: str) -> str:
    """Passt dieser Wert ueberhaupt zu diesem Feld? Leer heisst: ja.

    Aus der Kanzlei am 25.09.2026: "auch aendert er die adresse zu user_2
    also die werte sind irgendwie falsch". Die Werte waren um eine Frage
    verrutscht - vermutlich, weil beim Einfuegen aus der Zwischenablage ein
    Zeilenumbruch mitkam und damit gleich die naechste Frage beantwortete.
    Auf einem schwarzen Schirm sieht man das nicht.

    Die Folge war eine Ablehnung des Servers (401), die aussah wie ein
    fehlendes Recht - und die Suche ging in die voellig falsche Richtung.

    **Die vier Werte sehen so verschieden aus, dass eine Verwechslung
    auffallen muss.** Eine Adresse faengt mit https:// an, ein Benutzername
    tut das nie. Was nicht passt, wird nicht gespeichert, sondern noch
    einmal gefragt.
    """
    wert = wert.strip()
    if name == "JUSPERFECT_JURNODES_URL":
        if not wert.startswith("https://"):
            return ("Eine Adresse faengt mit https:// an. Das sieht nicht "
                    "danach aus - gehoert das vielleicht in ein anderes Feld?")
    elif name == "JURNODES_API_USER":
        if wert.startswith(("http://", "https://")) or "/" in wert:
            return ("Ein Benutzername ist keine Adresse. Gemeint ist der "
                    "kurze Name aus jur|nodes, etwa user_2.")
        if any(z.isspace() for z in wert):
            return ("Darin steckt ein Leerzeichen. Ein Benutzername hat "
                    "keines - gemeint ist nur der Name selbst, etwa user_2.")
        if len(wert) > 60:
            return "Fuer einen Benutzernamen ist das ungewoehnlich lang."
    elif name == "JURNODES_API_KEY":
        if wert.startswith(("http://", "https://")) or "/" in wert:
            return "Ein Token ist keine Adresse."
        if any(z.isspace() for z in wert):
            return "Darin steckt ein Leerzeichen. Ein Token hat keines."
    elif name == "JUSPERFECT_GUARDRAIL_ID":
        # Die ARN zuerst: Sie enthaelt einen Schraegstrich und liefe sonst in
        # die Adressmeldung - die hier nichts erklaert. Auf der AWS-Seite
        # stehen beide untereinander, und die ARN ist die auffaelligere.
        if wert.lower().startswith("arn:"):
            return ("Das ist die ARN. Gebraucht wird die kurze Guardrail ID "
                    "darueber - nur Buchstaben und Ziffern.")
        if wert.startswith(("http://", "https://")) or "/" in wert:
            return "Die Kennung des Schutzgelaenders ist keine Adresse."
        if any(z.isspace() for z in wert):
            return "Darin steckt ein Leerzeichen. Die Kennung hat keines."
    return ""


def _setzen(name: str, wert: str) -> bool:
    """Den Wert dauerhaft in die Umgebung dieses Windows-Kontos schreiben."""
    os.environ[name] = wert          # damit er in DIESEM Fenster sofort gilt
    if os.name != "nt":
        return False
    try:
        # setx schreibt in die Registry des Benutzers, nicht ins Dateisystem.
        ergebnis = subprocess.run(["setx", name, wert], capture_output=True, text=True)
    except OSError as fehler:  # pragma: no cover - nur auf kaputtem Windows
        _sagen("✗", f"setx liess sich nicht aufrufen ({fehler}).")
        return False
    if ergebnis.returncode != 0:
        _sagen("✗", f"{name} liess sich nicht hinterlegen.")
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    print(TRENNER)
    print("  jusperfect – den Zugang hinterlegen")
    print(TRENNER)
    print()
    _sagen(" ", "Diese Angaben bleiben auf diesem Rechner, in Ihrem eigenen")
    _sagen(" ", "Windows-Konto. Sie kommen in keine Datei des Programmordners")
    _sagen(" ", "und damit auch in keine ZIP, die Sie weitergeben.")
    print()

    werte: dict[str, str] = {}
    for name, frage, verdeckt in FELDER:
        vorhanden = os.environ.get(name, "").strip()
        if not vorhanden and name == "JUSPERFECT_GUARDRAIL_ID":
            gefunden = gelaender_aus_alter_fassung()
            if gefunden:
                vorhanden, woher = gefunden
                print()
                _sagen("✓", "Die Kennung des Schutzgeländers stand noch in einer")
                _sagen(" ", f"älteren Fassung: {woher.parent.name}")
                _sagen(" ", "Sie ist unten schon eingetragen - Eingabetaste genügt.")
        if vorhanden:
            gezeigt = _maskiert(vorhanden) if verdeckt else vorhanden
            _sagen(" ", f"Bisher hinterlegt: {gezeigt}")
        zusatz = " (Eingabetaste behält den bisherigen Wert)" if vorhanden else ""
        eingabe = (getpass.getpass(f"  {frage}{zusatz}: ") if verdeckt
                   else input(f"  {frage}{zusatz}: "))
        # Leerzeichen und Anfuehrungszeichen weg: Beides kommt beim Einfuegen
        # aus einer Zwischenablage mit und ist auf dem Schirm nicht zu sehen.
        eingabe = ohne_beschriftung(eingabe.strip().strip('"'))
        if not eingabe and vorhanden:
            werte[name] = vorhanden
            continue
        if not eingabe:
            print()
            _sagen("✗", f"{frage} fehlt. Es wurde nichts hinterlegt.")
            return 1
        # Passt der Wert ueberhaupt zu diesem Feld? Sonst noch einmal, statt
        # ihn zu speichern und den Fehler erst am Server zu erleben.
        haken = was_daran_nicht_stimmt(name, eingabe)
        while haken:
            _sagen("!", haken)
            zweite = (getpass.getpass(f"  {frage}: ") if verdeckt
                      else input(f"  {frage}: "))
            zweite = ohne_beschriftung(zweite.strip().strip('"'))
            if not zweite:
                print()
                _sagen("✗", "Es wurde nichts hinterlegt.")
                return 1
            eingabe = zweite
            haken = was_daran_nicht_stimmt(name, eingabe)
        werte[name] = eingabe

    print()
    for hinweis in hinweise_zur_adresse(werte["JUSPERFECT_JURNODES_URL"]):
        _sagen("!", hinweis)

    geschrieben = all(_setzen(name, werte[name]) for name, _, _ in FELDER)

    print()
    print(TRENNER)
    if geschrieben:
        _sagen("✓", "Hinterlegt. Die Werte gelten ab dem NÄCHSTEN Fenster.")
        print()
        _sagen(" ", "So steht es jetzt da:")
        for name, frage, verdeckt in FELDER:
            gezeigt = _maskiert(werte[name]) if verdeckt else werte[name]
            _sagen(" ", f"    {frage.split(' (')[0]}: {gezeigt}")
        print()
        _sagen(" ", "Steht etwas in der falschen Zeile, diese Datei einfach")
        _sagen(" ", "noch einmal starten - nichts geht dabei verloren.")
        _sagen(" ", "Das ist keine Schikane von Windows, sondern die Art, wie")
        _sagen(" ", "setx arbeitet: Ein offenes Fenster kennt sie noch nicht.")
    else:
        _sagen("!", "Dauerhaft hinterlegen geht nur unter Windows.")
        _sagen(" ", "In diesem Fenster gelten die Werte trotzdem.")
    print()
    _sagen(" ", "Als Nächstes: JURNODES-PRUEFEN.bat. Sie fragt die Schnittstelle")
    _sagen(" ", "einmal ab und liest dabei nur.")
    print(TRENNER)
    print()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
