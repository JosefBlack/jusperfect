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

import json
import os
import re
import shutil
import tempfile
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


#: Dieselbe Auskunft an beiden Stellen, an denen sie auffallen kann.
_KEIN_RUMPF = ("In der Vorlage fehlt der Dokumentrumpf (w:body). Bitte die Datei "
               "in Word oeffnen und als .docx speichern.")

#: Eine Fehlermeldung, die nur „fehlt" sagt, hilft niemandem.
_FEHLT = ("Es ist kein Briefbogen hinterlegt. Die Datei „{name}“ gehoert "
          "neben den Programmordner ({ordner}) - dort ueberlebt sie ein neues ZIP. "
          "BRIEFBOGEN-HINTERLEGEN.bat fuehrt hin.")


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


def _absatz(zeile: str, schrift: str = "", abstand: str = "") -> str:
    """Eine Zeile als Word-Absatz. Leere Zeilen bleiben leere Absaetze.

    Ohne eigene Formatierung: Welche Schrift, welcher Abstand und welcher
    Rand gelten, steht in der Vorlage der Kanzlei. Ein hier gesetzter Wert
    wuerde ihn ueberschreiben, und zwar unsichtbar.
    """
    pruefmass = f"<w:pPr>{abstand}</w:pPr>" if abstand else ""
    if not zeile.strip():
        return f"<w:p>{pruefmass}</w:p>" if pruefmass else "<w:p/>"
    return (f"<w:p>{pruefmass}<w:r>{schrift}" + '<w:t xml:space="preserve">'
            + _xml_text(zeile) + "</w:t></w:r></w:p>")


def _rumpf_ersetzen(xml: str, text: str, vorlauf_mm: float = 0.0,
                    bild: dict[str, object] | None = None) -> str:
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
        raise BriefbogenFehler(_KEIN_RUMPF) from fehler
    alt = xml[anfang:ende]
    sect = ""
    stelle = alt.rfind("<w:sectPr")
    if stelle >= 0:
        sect = alt[stelle:]
    schrift, abstand = _wortform(bild)
    absaetze = [_absatz(z, schrift, abstand) for z in text.replace("\r\n", "\n").split("\n")]
    if absaetze and vorlauf_mm > 0:
        absaetze[0] = _mit_vorlauf(absaetze[0], vorlauf_mm)
    return xml[:anfang] + "".join(absaetze) + sect + xml[ende:]


def _wortform(bild: dict[str, object] | None) -> tuple[str, str]:
    """Schrift und Zeilenabstand als Word-Bausteine - nur, was abweicht.

    Was die Vorlage ohnehin vorgibt, wird nicht noch einmal hingeschrieben.
    Eine Angabe, die dasselbe sagt wie die Formatvorlage, ist kein Fehler -
    aber sie haelt die Vorlage fest: Aendert die Kanzlei spaeter ihre
    Schrift, aendert sich der Brief dann nicht mit.
    """
    if not bild:
        return "", ""
    gesetzt = bild.get("einstellungen") or {}
    jetzt = bild.get("grundschrift") or {}
    teile = []
    if gesetzt.get("schrift"):
        name = _xml_text(str(jetzt.get("name", "")))
        teile.append(f'<w:rFonts w:ascii="{name}" w:hAnsi="{name}" w:cs="{name}"/>')
    if gesetzt.get("groesse_pt"):
        halbe = round(float(jetzt.get("groesse_pt", 10)) * 2)
        teile.append(f'<w:sz w:val="{halbe}"/><w:szCs w:val="{halbe}"/>')
    schrift = f"<w:rPr>{''.join(teile)}</w:rPr>" if teile else ""
    abstand = ""
    if gesetzt.get("zeilenabstand"):
        # 240 Zwanzigstelpunkte sind einfacher Zeilenabstand.
        zeilen = round(float(jetzt.get("zeilenabstand", 1.0)) * 240)
        abstand = f'<w:spacing w:line="{zeilen}" w:lineRule="auto"/>'
    return schrift, abstand


def _mit_vorlauf(absatz: str, vorlauf_mm: float) -> str:
    """Dem ersten Absatz den Abstand unter den Briefkopf setzen.

    Ein Abstand und keine leeren Absaetze: Der Abstand steht als ein Wert da
    und bleibt richtig, wenn jemand die Schriftgroesse der Vorlage aendert.
    Leere Absaetze waeren eine Schaetzung in Zeilen, und eine Schaetzung, die
    um zwei danebenliegt, schiebt den Brief auf die zweite Seite.
    """
    twips = round(vorlauf_mm * TWIPS_JE_MM)
    if absatz == "<w:p/>":
        return f'<w:p><w:pPr><w:spacing w:before="{twips}"/></w:pPr></w:p>'
    if "<w:spacing " in absatz:
        # Steht schon ein Abstandselement da (Zeilenabstand), bekommt es das
        # Merkmal dazu. Ein zweites `w:spacing` daneben waere kein Fehler
        # beim Oeffnen - Word naehme einfach das letzte, und der Vorlauf
        # waere lautlos weg.
        return absatz.replace("<w:spacing ", f'<w:spacing w:before="{twips}" ', 1)
    if absatz.startswith("<w:p><w:pPr>"):
        # Zwei `w:pPr` in einem Absatz sind kein gueltiges Word-Dokument.
        return absatz.replace("<w:p><w:pPr>",
                              f'<w:p><w:pPr><w:spacing w:before="{twips}"/>', 1)
    return absatz.replace("<w:p>", f'<w:p><w:pPr><w:spacing w:before="{twips}"/></w:pPr>', 1)


# ── Was die Kanzlei am Blatt einstellen kann ───────────────────────────────
#
# Aus der Kanzlei am 14.10.2026: „Stellt sich auch die Frage, ob die KI das
# Schreiben inklusive Briefbogen generieren kann, so dass die Vorschau besser
# anpassbar ist."
#
# Der Briefbogen bleibt eine Datei - die Begruendung steht im Kopf dieses
# Moduls. Anpassbar wird stattdessen das, was zwischen Briefbogen und Text
# liegt und sich von Haus zu Haus unterscheidet: wo der Text anfaengt, in
# welcher Schrift, in welcher Groesse, mit welchem Zeilenabstand.
#
# Vier Werte, keiner davon erfunden: Jeder ist leer voreingestellt und
# bedeutet dann „wie in der Vorlage". Wer einen setzt, setzt ihn fuer die
# Ansicht UND fuer die Word-Datei - eine Ansicht, die anders aussieht als das
# Blatt, waere schlimmer als gar keine.

#: Die Datei mit den Einstellungen. Neben dem Briefbogen, aus demselben Grund.
EINSTELLUNGEN_NAME = "jusperfect-blatt.json"

#: Was eingestellt werden kann, und was „nicht eingestellt" heisst.
EINSTELLUNGEN_LEER: dict[str, object] = {
    "textbeginn_mm": None,   # vom oberen Blattrand; None = aus dem Briefkopf
    "schrift": "",           # "" = wie in der Vorlage
    "groesse_pt": None,      # None = wie in der Vorlage
    "zeilenabstand": None,   # None = wie in der Vorlage; 1.0 = einfach
}


def einstellungen_ort() -> Path:
    """Neben dem Briefbogen, sonst neben dem Programmordner."""
    vorhanden = finden()
    return (vorhanden.parent if vorhanden else orte()[0].parent) / EINSTELLUNGEN_NAME


def einstellungen() -> dict[str, object]:
    """Die eingestellten Werte - fehlende bleiben leer.

    Faellt die Datei aus, faellt nur sie aus: Dann gilt die Vorlage, und das
    ist der Zustand, in dem alles angefangen hat. Ein Briefbogen, der wegen
    einer kaputten Einstellungsdatei gar nicht mehr geht, waere der
    schlechtere Tausch.
    """
    gesetzt = dict(EINSTELLUNGEN_LEER)
    try:
        roh = json.loads(einstellungen_ort().read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return gesetzt
    if not isinstance(roh, dict):
        return gesetzt
    for name in EINSTELLUNGEN_LEER:
        wert = roh.get(name)
        if name == "schrift":
            gesetzt[name] = " ".join(str(wert).split())[:80] if wert else ""
        elif isinstance(wert, (int, float)) and not isinstance(wert, bool):
            gesetzt[name] = float(wert)
    return _einstellungen_begrenzen(gesetzt)


def _einstellungen_begrenzen(gesetzt: dict[str, object]) -> dict[str, object]:
    """Werte, mit denen kein Blatt entsteht, werden nicht uebernommen.

    Ein Textbeginn von 400 Millimetern ergaebe ein leeres Blatt und eine
    Word-Datei, in der der Brief auf Seite zwei anfaengt - ohne dass
    irgendwo stuende, warum.
    """
    grenzen = {"textbeginn_mm": (0.0, 250.0), "groesse_pt": (6.0, 24.0),
               "zeilenabstand": (0.8, 3.0)}
    for name, (klein, gross) in grenzen.items():
        wert = gesetzt.get(name)
        if isinstance(wert, float) and not (klein <= wert <= gross):
            gesetzt[name] = None
    return gesetzt


def einstellungen_speichern(neu: dict[str, object]) -> dict[str, object]:
    """Die Werte ablegen - erst daneben schreiben, dann umbenennen."""
    gesetzt = dict(EINSTELLUNGEN_LEER)
    for name in EINSTELLUNGEN_LEER:
        wert = neu.get(name)
        if name == "schrift":
            gesetzt[name] = " ".join(str(wert).split())[:80] if wert else ""
        elif isinstance(wert, (int, float)) and not isinstance(wert, bool):
            gesetzt[name] = float(wert)
    gesetzt = _einstellungen_begrenzen(gesetzt)
    ort = einstellungen_ort()
    try:
        ort.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False,
                                         dir=str(ort.parent),
                                         prefix=ort.name + ".", suffix=".neu") as datei:
            datei.write(json.dumps(gesetzt, ensure_ascii=False, indent=2) + "\n")
            vorlaeufig = Path(datei.name)
        os.replace(vorlaeufig, ort)
    except OSError as fehler:
        raise BriefbogenFehler(
            f"Die Blatteinstellungen liessen sich nicht nach {ort} schreiben: {fehler}"
        ) from fehler
    return gesetzt


# ── Das Blatt ansehen, ohne Word zu oeffnen ────────────────────────────────
#
# Aus der Kanzlei am 13.10.2026: „Kann der Entwurf nicht gleich das fertige
# Schreiben mit Briefkopf angeben? Schliesslich muss auch optisch zum Teil
# aktualisiert werden."
#
# Richtig, und es war ein echter Mangel: Bis hierher war der Entwurf im
# Programm ein Fliesstext und wurde erst zum Blatt, nachdem man ihn
# heruntergeladen und in Word geoeffnet hatte. Wie lang er ist, wo er
# umbricht, ob er in die Anschrift laeuft - all das sah man erst dort, und
# jede Aenderung kostete denselben Weg noch einmal.
#
# **Was hier entsteht, ist eine Ansicht und kein zweiter Briefbogen.** Sie
# wird aus der Datei der Kanzlei GELESEN - Seitenmass, Raender, die
# festgesetzten Stuecke des Kopfes mit ihren Massen, der Text in den
# Textfeldern, die Bilder. Nichts davon ist nachgezeichnet; aendert die
# Kanzlei ihren Briefbogen, aendert sich die Ansicht mit. Was Word daraus
# setzt, bleibt die Wahrheit: Schriftschnitt und Zeilenumbruch koennen
# geringfuegig abweichen, und die Ansicht sagt das auch.

#: 36000 EMU sind ein Millimeter, 1440 Twips sind ein Zoll.
EMU_JE_MM = 36000
TWIPS_JE_MM = 1440 / 25.4

#: Luft zwischen dem untersten Stueck des Briefkopfes und dem ersten Satz.
ABSTAND_NACH_KOPF_MM = 6.0

_ANKER_RE = re.compile(r"<wp:anchor\b.*?</wp:anchor>", re.S)
_H_RE = re.compile(r'<wp:positionH relativeFrom="([^"]+)">\s*<wp:posOffset>(-?\d+)')
_V_RE = re.compile(r'<wp:positionV relativeFrom="([^"]+)">\s*<wp:posOffset>(-?\d+)')
_EXTENT_RE = re.compile(r'<wp:extent cx="(\d+)" cy="(\d+)"')
_EMBED_RE = re.compile(r'r:embed="([^"]+)"')
_TXBX_RE = re.compile(r"<w:txbxContent>(.*?)</w:txbxContent>", re.S)
_ABSATZ_RE = re.compile(r"<w:p\b[^>]*/>|<w:p\b.*?</w:p>", re.S)
_LAUF_RE = re.compile(r"<w:t(?: [^>]*)?>(.*?)</w:t>", re.S)
_GROESSE_RE = re.compile(r'<w:sz w:val="(\d+)"')
_AUSRICHTUNG_RE = re.compile(r'<w:jc w:val="([a-z]+)"')
_BEZIEHUNG_RE = re.compile(r'Id="([^"]+)"[^>]*Target="([^"]+)"')


def _entschaerfen(roh: str) -> str:
    """XML-Entitaeten zurueck in Text. Nur die fuenf, die es gibt."""
    for muster, zeichen in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'),
                            ("&apos;", "'"), ("&amp;", "&")):
        roh = roh.replace(muster, zeichen)
    return roh


def _absatz_zeilen(absatz: str) -> list[dict[str, object]]:
    """Ein Absatz als Zeilen: Text, Groesse, Ausrichtung.

    Ein Absatz kann aus vielen Laeufen bestehen (Word teilt beim Tippen).
    Fuer eine Ansicht zaehlt der Text, nicht die Teilung - aber ein
    ausdruecklicher Zeilenumbruch (``w:br``) zaehlt: Ohne ihn stuende
    „Partner mbB" und „Sitz: Hamburg" in einer Zeile.
    """
    form = {
        "fett": "<w:b/>" in absatz or '<w:b w:val="1"/>' in absatz,
        "groesse_pt": (lambda m: int(m.group(1)) / 2 if m else 0.0)(_GROESSE_RE.search(absatz)),
        "ausrichtung": (lambda m: {"center": "mitte", "right": "rechts"}.get(
            m.group(1) if m else "", "links"))(_AUSRICHTUNG_RE.search(absatz)),
    }
    teile = re.split(r"<w:br\b[^>]*/>", absatz)
    zeilen = [{"text": _absatz_text(teil), **form} for teil in teile]
    return zeilen or [{"text": "", **form}]


def _absatz_text(absatz: str) -> str:
    text = _entschaerfen("".join(_LAUF_RE.findall(absatz))).strip()
    # Feldbefehle wie DATE \@ "dd.MM.yyyy" stehen als Text im Absatz und
    # daneben das zuletzt berechnete Ergebnis. Der Befehl selbst gehoert
    # nicht aufs Blatt.
    return re.sub(r"\s*DATE\s+\\@\s*\"[^\"]*\"\s*\\\*\s*MERGEFORMAT\s*", " ", text).strip()


def _beziehungen(paket: zipfile.ZipFile, teil: str) -> dict[str, str]:
    """Die r:id-Zuordnung eines Teils - ohne sie ist ``r:embed`` nur ein Name."""
    ordner, _, name = teil.rpartition("/")
    pfad = f"{ordner}/_rels/{name}.rels"
    try:
        roh = paket.read(pfad).decode("utf-8")
    except KeyError:
        return {}
    return {kennung: (ziel if ziel.startswith("/") else f"{ordner}/{ziel}")
            for kennung, ziel in _BEZIEHUNG_RE.findall(roh)}


def _stuecke(paket: zipfile.ZipFile, teil: str, kopf_oben_mm: float,
             rand_links_mm: float) -> list[dict[str, object]]:
    """Was in Kopf- oder Fusszeile steht - festgesetzt und im Fluss."""
    try:
        xml = paket.read(teil).decode("utf-8")
    except (KeyError, UnicodeDecodeError):
        return []
    rels = _beziehungen(paket, teil)
    gefunden: list[dict[str, object]] = []

    for treffer in _ANKER_RE.finditer(xml):
        anker = treffer.group(0)
        mass = _EXTENT_RE.search(anker)
        if mass is None:
            continue
        breite = int(mass.group(1)) / EMU_JE_MM
        hoehe = int(mass.group(2)) / EMU_JE_MM
        waagerecht, senkrecht = _H_RE.search(anker), _V_RE.search(anker)
        if waagerecht is None or senkrecht is None:
            continue
        # "page" zaehlt vom Blattrand, alles andere vom Satzspiegel
        # beziehungsweise vom Kopfbereich. Genauer geht es ohne Umbruch nicht,
        # und genauer muss es fuer eine Ansicht auch nicht sein.
        x = int(waagerecht.group(2)) / EMU_JE_MM
        if waagerecht.group(1) != "page":
            x += rand_links_mm
        y = int(senkrecht.group(2)) / EMU_JE_MM
        if senkrecht.group(1) != "page":
            y += kopf_oben_mm
        gemeinsam = {"x_mm": x, "y_mm": y, "breite_mm": breite, "hoehe_mm": hoehe}
        bild = _EMBED_RE.search(anker)
        kasten = _TXBX_RE.search(anker)
        if kasten is not None:
            zeilen = [z for a in _ABSATZ_RE.findall(kasten.group(1))
                      for z in _absatz_zeilen(a)]
            gefunden.append({"art": "text", **gemeinsam, "zeilen": zeilen})
        elif bild is not None and bild.group(1) in rels:
            gefunden.append({"art": "bild", **gemeinsam, "bild": rels[bild.group(1)]})
        elif hoehe <= 0.5:
            # Eine Falz- oder Lochmarke: ein Strich ohne Hoehe.
            gefunden.append({"art": "linie", **gemeinsam})

    # Der Fluss: alles, was nicht in einem Anker steckt.
    # Word legt zu jeder Zeichnung eine Ersatzdarstellung fuer aeltere
    # Fassungen daneben (mc:AlternateContent, w:pict). Bleibt sie stehen,
    # steht der Inhalt des Anschriftenfeldes zweimal auf dem Blatt - einmal
    # an seinem Platz und einmal mitten im Fliesstext.
    fluss = re.sub(r"<mc:AlternateContent>.*?</mc:AlternateContent>", "", xml, flags=re.S)
    fluss = _ANKER_RE.sub("", fluss)
    fluss = re.sub(r"<w:drawing>.*?</w:drawing>", "", fluss, flags=re.S)
    fluss = re.sub(r"<w:pict>.*?</w:pict>", "", fluss, flags=re.S)
    zeilen = [z for a in _ABSATZ_RE.findall(fluss) for z in _absatz_zeilen(a)]
    if any(z["text"] for z in zeilen):
        gefunden.append({"art": "fluss", "zeilen": zeilen})
    return gefunden


def seitenbild(vorlage: Path | None = None) -> dict[str, object]:
    """Alles, was es braucht, um das Blatt zu zeigen - aus der Datei gelesen.

    Wirft ``BriefbogenFehler``, wenn keine Vorlage hinterlegt ist; die
    Meldung sagt dann, wohin die Datei gehoert.
    """
    vorlage = vorlage or finden()
    if vorlage is None:
        raise BriefbogenFehler(_FEHLT.format(name=DATEINAME, ordner=orte()[0].parent))
    xml = _rumpf_lesen(vorlage)
    if "<w:sectPr" not in xml or "</w:body>" not in xml:
        raise BriefbogenFehler(_KEIN_RUMPF)
    sect = xml[xml.rfind("<w:sectPr"):xml.index("</w:body>")]

    def _twips(muster: str, standard: float) -> float:
        treffer = re.search(muster, sect)
        return int(treffer.group(1)) / TWIPS_JE_MM if treffer else standard

    seite = {"breite": _twips(r'<w:pgSz w:w="(\d+)"', 210.0),
             "hoehe": _twips(r'<w:pgSz[^>]*w:h="(\d+)"', 297.0)}
    raender = {
        "oben": _twips(r'<w:pgMar w:top="(-?\d+)"', 25.4),
        "rechts": _twips(r'<w:pgMar[^>]*w:right="(\d+)"', 25.4),
        "unten": _twips(r'<w:pgMar[^>]*w:bottom="(-?\d+)"', 25.4),
        "links": _twips(r'<w:pgMar[^>]*w:left="(\d+)"', 25.4),
        "kopf": _twips(r'<w:pgMar[^>]*w:header="(\d+)"', 12.7),
    }
    # Hat die Vorlage eine eigene erste Seite, gilt deren Kopf - und nur der
    # zaehlt: Ein Entwurf faengt auf Seite eins an.
    erste_seite = "<w:titlePg/>" in sect
    arten = ("first", "default") if erste_seite else ("default",)

    def _verweis(wort: str) -> str:
        for art in arten:
            treffer = re.search(rf'<w:{wort}Reference w:type="{art}" r:id="([^"]+)"', sect)
            if treffer:
                return treffer.group(1)
        return ""

    with zipfile.ZipFile(vorlage) as paket:
        rels = _beziehungen(paket, RUMPF)
        stuecke: list[dict[str, object]] = []
        kopfteil = rels.get(_verweis("header"), "")
        fussteil = rels.get(_verweis("footer"), "")
        if kopfteil:
            stuecke += _stuecke(paket, kopfteil, raender["kopf"], raender["links"])
        if fussteil:
            # Die Fusszeile beginnt unten; ihre Flussabsaetze werden dort
            # ausgerichtet, ihre festgesetzten Stuecke stehen ohnehin absolut.
            for stueck in _stuecke(paket, fussteil, seite["hoehe"] - raender["unten"],
                                   raender["links"]):
                stueck["fuss"] = True
                stuecke.append(stueck)

    # Wie weit der Text unter dem oberen Rand beginnt.
    #
    # Das ist nicht Zierrat, sondern eine Berichtigung: Bis hierher setzte
    # `erzeugen` den Entwurf an den oberen Rand - also quer durch das
    # Anschriftenfeld, das auf diesem Briefbogen bis weit ins Blatt reicht.
    # In Word faellt das erst auf dem Papier auf.
    #
    # Gezaehlt wird nur, was im Textspalt steht: Eine Falzmarke am linken
    # Blattrand schiebt nichts.
    links, rechts = raender["links"], seite["breite"] - raender["rechts"]
    #: 0.0 heisst: im Textspalt steht gar nichts, der Text faengt oben an.
    #: Der Abstand kommt erst dazu, wenn es etwas gibt, wovon er abstehen
    #: soll - sonst bekaeme auch ein Briefbogen ohne Kopf sechs Millimeter
    #: Luft, die niemand bestellt hat.
    unterkante = 0.0
    for stueck in stuecke:
        if stueck.get("fuss") or stueck["art"] == "fluss":
            continue
        anfang = float(stueck["x_mm"])
        ende = anfang + float(stueck["breite_mm"])
        if ende <= links or anfang >= rechts:
            continue
        unterkante = max(unterkante, float(stueck["y_mm"]) + float(stueck["hoehe_mm"]))
    vorlauf = (max(0.0, unterkante + ABSTAND_NACH_KOPF_MM - raender["oben"])
               if unterkante else 0.0)

    aus_vorlage = _grundschrift(vorlage)
    gesetzt = einstellungen()
    # Was eingestellt ist, gilt; was nicht, kommt aus der Vorlage. Beides
    # steht in der Antwort: Die Oberflaeche zeigt im Einstellfenster den Wert
    # der Vorlage als Voreinstellung an, damit niemand raten muss.
    schrift = {
        "name": str(gesetzt["schrift"] or aus_vorlage["name"]),
        "groesse_pt": float(gesetzt["groesse_pt"] or aus_vorlage["groesse_pt"]),
        "zeilenabstand": float(gesetzt["zeilenabstand"] or 1.0),
    }
    textbeginn = (float(gesetzt["textbeginn_mm"]) if gesetzt["textbeginn_mm"] is not None
                  else round(raender["oben"] + vorlauf, 1))
    return {"seite_mm": seite, "raender_mm": raender, "stuecke": stuecke,
            "vorlauf_mm": round(max(0.0, textbeginn - raender["oben"]), 1),
            "textbeginn_mm": round(textbeginn, 1),
            "erste_seite_eigen": erste_seite,
            "grundschrift": schrift,
            "aus_vorlage": {"textbeginn_mm": round(raender["oben"] + vorlauf, 1),
                            **aus_vorlage, "zeilenabstand": 1.0},
            "einstellungen": gesetzt, "datei": vorlage.name}


def _grundschrift(vorlage: Path) -> dict[str, object]:
    """Schrift und Groesse, in denen der Brief wirklich gesetzt wird.

    **Hier stand zuerst nur ``w:docDefaults``, und das war falsch.** Aus der
    Kanzlei am 14.10.2026: „Schrift ist Franklin Gothic Book." In den
    docDefaults dieser Vorlage steht Times New Roman - und daneben, in der
    Standard-Absatzformatvorlage (``w:default="1"``), steht Franklin Gothic
    Book in zwoelf Punkt. Word setzt nach der Formatvorlage; die
    docDefaults sind nur das, was gilt, wenn gar nichts anderes dasteht.

    Die Groesse ist dabei so wichtig wie der Name: Eine Ansicht in zehn
    statt zwoelf Punkt zeigt einen Brief, der auf eine Seite passt, obwohl
    er auf zwei geht - und das Abschaetzen der Laenge ist der Grund, warum
    die Ansicht ueberhaupt da ist.
    """
    try:
        with zipfile.ZipFile(vorlage) as paket:
            stile = paket.read("word/styles.xml").decode("utf-8")
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError):
        return {"name": "", "groesse_pt": 10.0}
    # Erst die Standard-Absatzformatvorlage, dann die docDefaults.
    standard = re.search(
        r'<w:style [^>]*w:type="paragraph"[^>]*w:default="1".*?</w:style>', stile, re.S)
    grund = re.search(r"<w:docDefaults>.*?</w:docDefaults>", stile, re.S)
    name, groesse = "", 0.0
    for block in (standard, grund):
        roh = block.group(0) if block else ""
        if not name:
            treffer = re.search(r'<w:rFonts[^>]*w:ascii="([^"]+)"', roh)
            name = treffer.group(1) if treffer else ""
        if not groesse:
            treffer = _GROESSE_RE.search(roh)
            groesse = int(treffer.group(1)) / 2 if treffer else 0.0
    return {"name": name, "groesse_pt": groesse or 10.0}


def bild_lesen(kennung: str, vorlage: Path | None = None) -> tuple[bytes, str]:
    """Ein Bild aus der Vorlage - nur eines, das wirklich darin liegt.

    Die Kennung kommt aus ``seitenbild`` zurueck und geht unveraendert
    wieder hinein. Gelesen wird trotzdem nur, was das Paket selbst
    auffuehrt: Sonst waere dieser Weg ein Pfad, den der Browser bestimmt.
    """
    vorlage = vorlage or finden()
    if vorlage is None:
        raise BriefbogenFehler(_FEHLT.format(name=DATEINAME, ordner=orte()[0].parent))
    try:
        with zipfile.ZipFile(vorlage) as paket:
            if kennung not in paket.namelist():
                raise BriefbogenFehler("Dieses Bild gibt es in der Vorlage nicht.")
            inhalt = paket.read(kennung)
    except (OSError, zipfile.BadZipFile) as fehler:
        raise BriefbogenFehler(f"Die Vorlage liess sich nicht lesen: {fehler}") from fehler
    endung = kennung.rsplit(".", 1)[-1].lower()
    art = {"png": "image/png", "jpeg": "image/jpeg", "jpg": "image/jpeg",
           "gif": "image/gif", "bmp": "image/bmp", "tiff": "image/tiff",
           "emf": "image/emf", "wmf": "image/wmf"}.get(endung, "application/octet-stream")
    return inhalt, art


def erzeugen(text: str, vorlage: Path | None = None) -> bytes:
    """Der Entwurf auf dem Briefbogen - als Word-Datei im Arbeitsspeicher.

    Jede andere Datei des Pakets wird unveraendert uebernommen: Kopfzeilen,
    Fusszeilen, Bilder, Schriften, Formatvorlagen. Geaendert wird genau eine,
    ``word/document.xml``, und in ihr genau der leere Rumpf.
    """
    vorlage = vorlage or finden()
    if vorlage is None:
        raise BriefbogenFehler(_FEHLT.format(name=DATEINAME, ordner=orte()[0].parent))
    # Wie weit der Text unter dem oberen Rand beginnt, in welcher Schrift und
    # mit welchem Zeilenabstand - alles aus demselben Aufruf wie die Ansicht.
    # Zwei Rechenwege waeren zwei Ergebnisse, und das eine davon stuende auf
    # dem Bildschirm und das andere auf dem Papier.
    bild = seitenbild(vorlage)
    neuer_rumpf = _rumpf_ersetzen(_rumpf_lesen(vorlage), text,
                                  float(bild["vorlauf_mm"]), bild)
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
