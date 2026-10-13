"""Berechnete Fristdaten aus der Ausgabe nehmen.

Der Grundsatz steht seit Anfang an im Auftragstext: „Sie erkennen
Fristauslöser und benennen sie mit Beleg. Sie berechnen keine Fristen und
nennen kein berechnetes Datum." Im ersten Durchgang an einer echten Akte hat
das Modell ihn trotzdem gebrochen:

    „Die Klagefrist endet am 26.05.2026 – Klage muss sofort eingereicht
     werden"

Das Ergebnis war richtig. Genau das ist die Gefahr: Ein Werkzeug, das neunmal
richtig rechnet, wird beim zehnten Mal geglaubt. Und die Fundstelle trug
nicht – als Beleg stand das Kündigungsschreiben, in dem dieses Datum nirgends
vorkommt. Die Belegpflicht prüft die Kennung, nicht ob der Inhalt die Aussage
stützt; hier sieht man ihre Grenze.

Deshalb steht die Regel jetzt auch im Code. Der Prüfstein ist einfach und
belastbar: **Ein Datum, das in keiner mitgeschickten Passage steht, kann nicht
aus der Akte stammen.** Es wird ersetzt, nicht der ganze Satz gestrichen -
dass eine Klagefrist läuft, ist der wichtige Teil und soll stehen bleiben;
falsch ist nur die Anmutung, das Programm kenne den Tag.

Die Fristenkontrolle bleibt in jur|nodes. Das ist keine Bequemlichkeit,
sondern die Arbeitsteilung, auf der das ganze Programm beruht.

---

## Der Umbau vom 05.10.2026 (Befund F09 der Zweitprüfung)

Die Sperre hing an einer Wortliste. Erst wenn in der Umgebung des Datums ein
Fristwort stand, wurde überhaupt geprüft; und das Datum selbst musste eine der
vier Schreibweisen treffen, die das Muster kannte. Drei Sätze kamen deshalb
unverändert durch, obwohl keiner von ihnen ein Datum aus der Akte nannte:

    „Die Klagefrist endet am 26.05.26."        - zweistelliges Jahr
    „Die Klagefrist endet am 26. Mai."         - Monatsname ohne Jahr
    „Die Klage muss bis zum 26.05.2026 ..."    - kein Wort der Fristliste

Der Prüfbericht sagt dazu das Richtige: Eine größere Wortliste verbessert
einzelne Fälle und stellt die Zusage über beliebige natürliche Sprache
trotzdem nicht her. Die Zusage bleibt; der Nachweis ist ein anderer geworden.

**Umgekehrte Beweisrichtung.** Nicht mehr „ein Datum fällt, wenn ein Fristwort
danebensteht", sondern: **Jedes Datum in der Ausgabe muss sich auf eine Stelle
zurückführen lassen, die das Programm selbst mitgeschickt hat** - eine Passage,
die Kopfzeile einer Passage (Titel und Dokumentdatum) oder den Fristenkalender
aus jur|nodes. Findet sich dort nichts, wird es ersetzt, ganz ohne Wortliste.
Denn woher sollte es sonst kommen.

Die Wortlisten sind damit nicht verschwunden, aber sie entscheiden nicht mehr
über die Zusage. Sie tun jetzt zwei engere Dinge:

* ``_FRISTENDE`` verschärft: Behauptet der Satz ein **Ende**, genügt das bloße
  Vorkommen in der Akte nicht mehr; die Akte muss das Datum selbst als
  Endpunkt führen. Fällt die Liste hier aus, wird weniger streng geprüft -
  aber das Datum steht dann immerhin in der Akte.
* ``_FRISTWORT`` wählt nur noch den **Wortlaut des Ersatzes**: Bei einer
  Fristaussage der Hinweis auf den Fristenkalender, sonst der schlichte
  Hinweis, dass die Stelle fehlt.

Was dadurch strenger wird und bedacht sein muss: Ein erfundenes Datum fällt
jetzt auch dann, wenn es nach keiner Frist klingt - „Die Besprechung findet am
12.09.2026 statt" ohne jede Stelle in der Akte ist ebenfalls erfunden. Damit
kein richtiges Datum mitgerissen wird, zählt als Stelle ausdrücklich auch die
Kopfzeile: Das Dokumentdatum steht in den Stammdaten und fast nie im Text, und
das Modell soll es nennen.
"""

from __future__ import annotations

import re
from datetime import date
from functools import lru_cache

from jusperfect.domain.models import Passage

# Was an die Stelle des gerechneten Datums tritt. Kein leerer Raum: Wer die
# Zeile liest, soll sehen, dass hier etwas entfernt wurde und wohin er sieht.
ERSATZ = "[Datum entfernt – nicht belegt, Fristenkalender in jurnodes]"

# Dasselbe fuer ein Datum, das gar nicht nach einer Frist klingt. Der Hinweis
# auf den Fristenkalender waere dort irrefuehrend - die Akte kennt diesen Tag
# einfach nicht.
ERSATZ_UNBELEGT = "[Datum entfernt – steht in keiner Passage dieser Akte]"

_MONATE = {
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5,
    "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
    "november": 11, "dezember": 12,
}
_MONATSNAMEN = "|".join(_MONATE)

# Wie weit eine zweistellige Jahresangabe in die Zukunft gelesen wird. „26" ist
# 2026, „98" ist 1998. Die Grenze liegt zwanzig Jahre vor uns: Ein Mietvertrag
# laeuft so lange, ein Schriftsatz nicht.
JAHRESSPANNE = 20

# Die Schreibweisen, in denen ein Datum vorkommt:
#   26.05.2026 · 26.5.2026 · 26.05.26 · 2026-05-26 · 26. Mai 2026 · 26. Mai
#   und - nur hinter einem Datumsanlass - 26.05.
#
# Die letzte Form ist die heikle: „2.1." ist auch eine Ziffer eines Vertrages,
# und eine Vertragsziffer zu streichen waere ein schwerer Fehler. Sie gilt
# deshalb nur, wenn davor etwas steht, das ein Datum ankuendigt (``am", „bis
# zum", „Frist ..."). Mit Jahr - auch zweistellig - braucht es diese Stuetze
# nicht.
_DATUM = re.compile(
    r"\b(?P<t1>\d{1,2})\.\s*(?P<m1>\d{1,2})\.\s*(?P<j1>\d{4}|\d{2})(?!\d)"
    r"|\b(?P<j2>\d{4})-(?P<m2>\d{2})-(?P<t2>\d{2})\b"
    r"|\b(?P<t3>\d{1,2})\.\s*(?P<m3>" + _MONATSNAMEN + r")"
    r"(?:\s+(?P<j3>\d{4}|\d{2}))?\b"
    r"|\b(?P<t4>\d{1,2})\.\s*(?P<m4>\d{1,2})\.(?![.\d])",
    re.IGNORECASE,
)

# Woran man erkennt, dass die naechste Zahl ein Datum sein soll und keine
# Ziffer eines Vertrages. Gelesen werden die Zeichen unmittelbar davor.
_DATUMSANLASS = re.compile(
    r"\b(?:am|an|bis|zum|zur|ab|vom|von|seit|dem|den|per|"
    r"sp(?:ä|ae)testens)\s*$"
    r"|(?:frist|termin|datum|ablauf|f(?:ä|ae)llig|verj(?:ä|ae)hr)[^.]{0,20}$",
    re.IGNORECASE,
)
ANLASSFENSTER = 40

# Woerter, die einen Satz zu einer Fristaussage machen. Seit dem 05.10.2026
# entscheiden sie nur noch den Wortlaut des Ersatzes, nicht mehr, ob geprueft
# wird. Bewusst eng: "fristlos" und "fristgerecht" gehoeren NICHT dazu - eine
# fristlose Kuendigung zum 30.09.2026 ist eine Tatsache aus dem Schreiben.
_FRISTWORT = re.compile(
    r"\bfrist\b|\bfristen\b|frist(?:ablauf|ende|beginn)|klagefrist|"
    r"kündigungsfrist|ausschlussfrist|verjähr|"
    r"läuft\s+(?:am\s+\S+\s+)?ab\b|endet\s+am\b|abgelaufen|fällig\s+am\b|"
    r"bis\s+zum\b|sp(?:ä|ae)testens\b",
    re.IGNORECASE,
)

# Die Teilmenge der Fristwoerter, die ein ENDE behaupten. Hier liegt die
# Gefahr: Ein Fristende ist fast immer gerechnet. Ein Fristbeginn dagegen ist
# eine Tatsache aus der Akte - der Tag, an dem das Schreiben zuging -, und ihn
# zu streichen waere der schwerere Fehler.
#
# Aus einer Gegenprobe von aussen (PRUEFBERICHT-2026-09-16.md, Befund 2): Die
# Quelle nannte nur "Eine Besprechung fand am 26.05.2026 statt", die Antwort
# machte daraus "Die Klagefrist endet am 26.05.2026" - und kam durch, weil das
# Datum irgendwo im Aktenbestand vorkam. Es war nicht gerechnet, es war
# umetikettiert. Dagegen half die alte Pruefung nicht.
# „läuft ab" ist zweierlei, und der Unterschied ist der ganze Punkt:
#   „Die Frist läuft ab."            - sie endet.
#   „Die Frist läuft ab dem 15.03."  - sie beginnt.
# Der erste Entwurf hat beides als Ende gelesen und einen Fristbeginn aus dem
# Scan gestrichen. Ein Artikel dahinter macht daraus einen Anfang.
_FRISTENDE = re.compile(
    r"endet?\s+am\b|endete\s+am\b|frist(?:ablauf|ende)\b|"
    r"l(?:ä|ae)uft\s+(?!\S*\s*ab\s+(?:dem|den|diesem))(?:am\s+\S+\s+)?ab\b|"
    r"abgelaufen\b|"
    r"verj(?:ä|ae)hr|f(?:ä|ae)llig\s+am\b|sp(?:ä|ae)testens\s+(?:am|bis)\b|"
    r"frist\s+bis\s+zum\b|"
    r"muss\s+bis\s+zum\b|bis\s+zum\b.{0,40}(?:eingereicht|erhoben|"
    r"eingelegt|zugestellt|gezahlt|eingegangen)",
    re.IGNORECASE,
)

# Woran man in der AKTE erkennt, dass ein Datum ein Endpunkt ist. Weiter
# gefasst als _FRISTENDE: Ein Schreiben sagt nicht „die Frist endet am", es
# sagt „gekündigt zum" oder „zahlbar bis". Zu eng gefasst striche die Sperre
# richtige Daten - und das ist hier der schwerere Fehler.
_ENDPUNKT_IN_AKTE = re.compile(
    r"\bzum\b|\bbis\b|\bfrist|\bablauf|endet?\b|endend|"
    r"\bwirksam\b|\btermin\b|k(?:ü|ue)ndig|"
    r"sp(?:ä|ae)testens|f(?:ä|ae)llig|verj(?:ä|ae)hr|\bletzter\b",
    re.IGNORECASE,
)

# Statt nach Saetzen zu trennen, wird um jedes Datum ein Fenster gelesen.
# Die Satztrennung war der naheliegende Weg und der falsche: Ein deutsches
# Datum enthaelt selbst Punkte, "Die Frist endet am 26. Mai 2026." zerfiel
# hinter dem Tag in zwei Stuecke, und in keinem davon standen Fristwort und
# Datum noch beisammen. Ein Fenster kennt dieses Problem nicht.
FENSTER = 150


def _jahr(text: str) -> int:
    """Eine Jahresangabe lesen, zwei- oder vierstellig."""
    zahl = int(text)
    if len(text) == 4:
        return zahl
    return 2000 + zahl if 2000 + zahl <= date.today().year + JAHRESSPANNE else 1900 + zahl


def _zerlegen(treffer: re.Match) -> tuple[int, int, int | None] | None:
    """Tag, Monat und - wenn dabei - Jahr. ``None``, wenn es kein Datum ist.

    Geprueft wird auch die Plausibilitaet: „1.13.2024" ist eine Versionsnummer
    und kein Datum, „0.5." gar nichts.
    """
    g = treffer.groupdict()
    for tagname, monatname, jahrname in (("t1", "m1", "j1"), ("t2", "m2", "j2"),
                                         ("t3", "m3", "j3"), ("t4", "m4", None)):
        if g.get(tagname) is None:
            continue
        rohmonat = g[monatname]
        monat = int(rohmonat) if rohmonat.isdigit() else _MONATE[rohmonat.lower()]
        tag = int(g[tagname])
        if not (1 <= tag <= 31 and 1 <= monat <= 12):
            return None
        jahr = _jahr(g[jahrname]) if jahrname and g.get(jahrname) else None
        return tag, monat, jahr
    return None


@lru_cache(maxsize=1024)
def _muster(tag: int, monat: int, jahr: int | None) -> re.Pattern:
    """Dasselbe Datum als Muster über alle Schreibweisen, die in Akten vorkommen.

    Vorher wurde eine Menge von Zeichenketten gebildet und einzeln gesucht.
    Das trug die Schreibweisen nicht, die seit dem 05.10.2026 dazugehoeren -
    ein Datum ohne Jahr hat keine endliche Menge von Formen. Ein Muster hat
    dieses Problem nicht.
    """
    namen = "|".join(n for n, z in _MONATE.items() if z == monat)
    if jahr is None:
        # Ohne Jahr gilt jedes Jahr als dieselbe Stelle - mehr ist nicht zu
        # wissen, und weniger waere geraten.
        j_zahl = r"(?:\s*\d{2}(?:\d{2})?\b)?"
        j_iso = r"\d{4}"
        j_name = r"(?:\s+\d{2}(?:\d{2})?\b)?"
    else:
        zwei = f"{jahr % 100:02d}"
        j_zahl = rf"\s*(?:{jahr}|{zwei})\b"
        j_iso = str(jahr)
        j_name = rf"\s+(?:{jahr}|{zwei})\b"
    return re.compile(
        rf"\b0?{tag}\.\s*0?{monat}\.{j_zahl}"
        rf"|\b{j_iso}-0*{monat}-0*{tag}\b"
        rf"|\b0?{tag}\.\s*(?:{namen}){j_name}",
        re.IGNORECASE,
    )


# Texterkennung verwechselt in Zahlen die Null mit dem O, die Eins mit l, I
# und dem senkrechten Strich. Ein Scan traegt dann "3O.09.2026" - und das
# Modell liest daraus zu Recht den 30.09.2026. Ohne Glaettung hielte der
# Vergleich dieses Datum fuer erfunden und striche es: Eine Fristensperre, die
# an Erkennungsfehlern scheitert, wuerde bei echten Scans jeden Termin tilgen.
# Die Scan-Testakte 031/26 SC hat genau das gezeigt.
#
# Geglaettet werden nur Zeichenketten, die wie Zahlen aussehen - ein Wort aus
# Buchstaben bleibt ein Wort.
_ZIFFERNKETTE = re.compile(r"[0-9OoIl|][0-9OoIl|.,/\-]{3,}[0-9OoIl|]")
_OCR_ZIFFERN = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1"})


def _ocr_glaetten(text: str) -> str:
    return _ZIFFERNKETTE.sub(lambda m: m.group(0).translate(_OCR_ZIFFERN), text)


def _aktentext(index: dict[str, Passage]) -> str:
    """Der Text der Passagen selbst - der Inhalt der Akte."""
    return _ocr_glaetten("\n".join(p.text for p in index.values())).lower()


def _stammdatentext(index: dict[str, Passage]) -> str:
    """Die Kopfzeilen der Passagen: Titel und Dokumentdatum.

    Das Material nennt sie dem Modell ausdruecklich („Passage D2-S1-P1
    (Dokument: „Kündigung", datiert 04.05.2026, Seite 1)"), und der Auftrag
    verlangt, dass es das Datum eines Schriftstuecks nennt. Ein Datum von dort
    ist also keine Erfindung - es gilt als Stelle.

    Getrennt vom Aktentext, und das ist der Punkt: Als **Endpunkt** taugt eine
    Kopfzeile nicht. „Kündigung, datiert 04.05.2026" wuerde sonst jede
    behauptete Kuendigungsfrist zum Briefdatum belegen.
    """
    teile = []
    for p in index.values():
        teile.append(p.dokument_titel or "")
        datum = getattr(p, "dokument_datum", None)
        if datum is not None:
            teile.append(datum.strftime("%d.%m.%Y"))
    return _ocr_glaetten("\n".join(teile)).lower()


def _kalenderdaten(kalender) -> set[tuple[int, int, int]]:
    """Die Daten des Fristenkalenders als (Tag, Monat, Jahr).

    Der Kalender in jur|nodes ist die eine Stelle, an der Fristen gerechnet
    werden duerfen - und werden. Ein Datum von dort ist keine Erfindung des
    Modells, auch wenn es in keiner Passage steht; es steht im Material unter
    "Fristen laut Fristenkalender". Nimmt man ISO-Text oder date-Objekte.
    """
    daten: set[tuple[int, int, int]] = set()
    for eintrag in kalender or ():
        wert = getattr(eintrag, "datum", eintrag)
        text = wert.isoformat() if hasattr(wert, "isoformat") else str(wert)
        treffer = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
        if treffer:
            daten.add((int(treffer.group(3)), int(treffer.group(2)), int(treffer.group(1))))
    return daten


def _im_kalender(zerlegt: tuple[int, int, int | None],
                 erlaubt: set[tuple[int, int, int]]) -> bool:
    tag, monat, jahr = zerlegt
    if jahr is None:
        return any(t == tag and m == monat for t, m, _ in erlaubt)
    return (tag, monat, jahr) in erlaubt


def entschaerfen(text: str, index: dict[str, Passage], kalender=()) -> tuple[str, int]:
    """Unbelegte und gerechnete Daten ersetzen. Gibt den Text und die Zahl der Funde.

    Die Beweisrichtung ist umgekehrt (siehe Modulkopf, Befund F09): Jedes Datum
    muss sich auf eine Stelle zurückführen lassen, die das Programm selbst
    mitgeschickt hat - eine Passage, deren Kopfzeile oder den Fristenkalender.
    Sonst fällt es, ohne dass ein Fristwort danebenstehen muss.

    Steht das Datum in der Akte und behauptet der Satz ein **Ende**, genügt das
    Vorkommen nicht: Dann muss die Akte selbst dieses Datum als Endpunkt
    führen. Ein Fristbeginn dagegen ist eine Tatsache aus der Akte, und ihn zu
    streichen wäre der schwerere Fehler.

    ``kalender`` sind die Fristen aus jur|nodes. Ein Datum von dort gilt als
    belegt - der Kalender ist die Stelle, an der gerechnet werden darf.
    """
    if not text:
        return text, 0
    akte = _aktentext(index)
    stammdaten = _stammdatentext(index)
    erlaubt = _kalenderdaten(kalender)
    gefunden = 0

    def ersetzen(treffer: re.Match) -> str:
        nonlocal gefunden
        zerlegt = _zerlegen(treffer)
        if zerlegt is None:
            return treffer.group(0)
        if treffer.group("t4") is not None:
            davor = text[max(0, treffer.start() - ANLASSFENSTER): treffer.start()]
            if not _DATUMSANLASS.search(davor):
                return treffer.group(0)      # „Ziffer 2.1." ist kein Datum
        if _im_kalender(zerlegt, erlaubt):
            return treffer.group(0)          # steht im Fristenkalender
        muster = _muster(*zerlegt)
        stellen = list(muster.finditer(akte))
        umfeld = text[max(0, treffer.start() - FENSTER): treffer.end() + FENSTER]
        if stellen:
            if not _FRISTENDE.search(umfeld):
                return treffer.group(0)      # belegt, und kein Ende behauptet
            # Behauptet der Satz ein ENDE, genuegt das Vorkommen nicht mehr:
            # Dann muss die Akte dieses Datum selbst als Ende fuehren.
            for stelle in stellen:
                nachbarschaft = akte[max(0, stelle.start() - FENSTER):
                                     stelle.end() + FENSTER]
                if _ENDPUNKT_IN_AKTE.search(nachbarschaft):
                    return treffer.group(0)
        elif muster.search(stammdaten) and not _FRISTENDE.search(umfeld):
            # Das Dokumentdatum aus der Kopfzeile. Als Tatsache ja, als
            # Endpunkt nicht - siehe _stammdatentext.
            return treffer.group(0)
        gefunden += 1
        return ERSATZ if _FRISTWORT.search(umfeld) else ERSATZ_UNBELEGT

    return _DATUM.sub(ersetzen, text), gefunden


def hinweis(anzahl: int) -> str:
    return (
        f"{anzahl} Datum/Daten aus der Ausgabe entfernt: Sie stehen in keiner "
        f"mitgeschickten Passage und in keinem Eintrag des Fristenkalenders. "
        f"Das Programm erkennt Fristauslöser, es rechnet keine Fristen. "
        f"Maßgeblich ist der Fristenkalender in jurnodes."
    )


def felder_entschaerfen(eintraege, feld: str, index: dict[str, Passage], kalender=()) -> int:
    """Dasselbe für ein Textfeld einer Liste von Einträgen."""
    gefunden = 0
    for eintrag in eintraege:
        wert = getattr(eintrag, feld, "") or ""
        neu, zahl = entschaerfen(wert, index, kalender)
        if zahl:
            setattr(eintrag, feld, neu)
            gefunden += zahl
    return gefunden
