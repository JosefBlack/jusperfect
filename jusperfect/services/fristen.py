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
aus der Akte stammen.** Kommt es in einem Satz vor, der von einer Frist
handelt, ist es gerechnet. Es wird ersetzt, nicht der ganze Satz gestrichen -
dass eine Klagefrist läuft, ist der wichtige Teil und soll stehen bleiben;
falsch ist nur die Anmutung, das Programm kenne den Tag.

Die Fristenkontrolle bleibt in jur|nodes. Das ist keine Bequemlichkeit,
sondern die Arbeitsteilung, auf der das ganze Programm beruht.
"""

from __future__ import annotations

import re

from jusperfect.domain.models import Passage

# Was an die Stelle des gerechneten Datums tritt. Kein leerer Raum: Wer die
# Zeile liest, soll sehen, dass hier etwas entfernt wurde und wohin er sieht.
ERSATZ = "[Datum entfernt – nicht belegt, Fristenkalender in jur|nodes]"

_MONATE = {
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5,
    "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
    "november": 11, "dezember": 12,
}

# 26.05.2026 · 26.5.2026 · 2026-05-26 · 26. Mai 2026
_DATUM = re.compile(
    r"\b(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\b"
    r"|\b(\d{4})-(\d{2})-(\d{2})\b"
    r"|\b(\d{1,2})\.\s*(" + "|".join(_MONATE) + r")\s+(\d{4})\b",
    re.IGNORECASE,
)

# Woerter, die einen Satz zu einer Fristaussage machen. Bewusst eng: "fristlos"
# und "fristgerecht" gehoeren NICHT dazu - eine fristlose Kuendigung zum
# 30.09.2026 ist eine Tatsache aus dem Schreiben, keine Berechnung.
_FRISTWORT = re.compile(
    r"\bfrist\b|\bfristen\b|frist(?:ablauf|ende|beginn)|klagefrist|"
    r"kündigungsfrist|ausschlussfrist|verjähr|"
    r"läuft\s+(?:am\s+\S+\s+)?ab\b|endet\s+am\b|abgelaufen|fällig\s+am\b",
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
    r"frist\s+bis\s+zum\b",
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


def _varianten(tag: int, monat: int, jahr: int) -> set[str]:
    """Dasselbe Datum in den Schreibweisen, die in Akten vorkommen."""
    monatsname = [n for n, z in _MONATE.items() if z == monat and "ae" not in n]
    formen = {
        f"{tag:02d}.{monat:02d}.{jahr}",
        f"{tag}.{monat}.{jahr}",
        f"{tag}. {monat}. {jahr}",
        f"{jahr}-{monat:02d}-{tag:02d}",
    }
    for name in monatsname:
        formen.add(f"{tag}. {name} {jahr}")
        formen.add(f"{tag}.{name} {jahr}")
    return {f.lower() for f in formen}


def _zerlegen(treffer: re.Match) -> tuple[int, int, int] | None:
    g = treffer.groups()
    if g[0]:
        return int(g[0]), int(g[1]), int(g[2])
    if g[3]:
        return int(g[5]), int(g[4]), int(g[3])
    if g[6]:
        return int(g[6]), _MONATE[g[7].lower()], int(g[8])
    return None


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
    return _ocr_glaetten("\n".join(p.text for p in index.values())).lower()


def _als_fristende_belegt(varianten: set[str], akte: str) -> bool:
    """Steht dieses Datum in der Akte selbst an einer Stelle, die ein Ende meint?

    Nicht: kommt es irgendwo vor. Ein Besprechungstag, ein Rechnungsdatum und
    ein Fristablauf sehen als Zeichenkette gleich aus; erst der Satz darum
    sagt, was gemeint ist. Gelesen wird dasselbe Fenster wie in der Antwort -
    was dort als Nachweis taugt, muss auch hier gelten.
    """
    for variante in varianten:
        stelle = 0
        while True:
            i = akte.find(variante, stelle)
            if i < 0:
                break
            umfeld = akte[max(0, i - FENSTER): i + len(variante) + FENSTER]
            if _ENDPUNKT_IN_AKTE.search(umfeld):
                return True
            stelle = i + 1
    return False


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


def entschaerfen(text: str, index: dict[str, Passage], kalender=()) -> tuple[str, int]:
    """Gerechnete Fristdaten ersetzen. Gibt den Text und die Zahl der Funde.

    Geprüft wird im Umfeld jedes Datums: Nur wo eine Frist im Spiel ist, wird
    es beanstandet. Ein Datum ohne Fristwort - ein Zugangstag, ein Termin -
    bleibt unangetastet, auch wenn es nicht wörtlich in der Akte steht; dort
    wäre das Streichen der schwerere Fehler.

    ``kalender`` sind die Fristen aus jur|nodes. Ein Datum von dort gilt als
    belegt - der Kalender ist die Stelle, an der gerechnet werden darf.
    """
    if not text:
        return text, 0
    akte = _aktentext(index)
    erlaubt = _kalenderdaten(kalender)
    gefunden = 0

    def ersetzen(treffer: re.Match) -> str:
        nonlocal gefunden
        zerlegt = _zerlegen(treffer)
        if zerlegt is None:
            return treffer.group(0)
        if zerlegt in erlaubt:
            return treffer.group(0)          # steht im Fristenkalender
        umfeld = text[max(0, treffer.start() - FENSTER): treffer.end() + FENSTER]
        if not _FRISTWORT.search(umfeld):
            return treffer.group(0)          # kein Fristsatz - nicht anfassen
        varianten = _varianten(*zerlegt)
        steht_in_akte = any(v in akte for v in varianten)
        # Behauptet der Satz ein ENDE, genuegt das Vorkommen nicht mehr: Dann
        # muss die Akte dieses Datum selbst als Ende fuehren. Sonst reicht das
        # Vorkommen wie bisher - ein Fristbeginn ist eine Tatsache aus der
        # Akte, und ihn zu streichen waere der schwerere Fehler.
        if _FRISTENDE.search(umfeld):
            if _als_fristende_belegt(varianten, akte):
                return treffer.group(0)
        elif steht_in_akte:
            return treffer.group(0)
        gefunden += 1
        return ERSATZ

    return _DATUM.sub(ersetzen, text), gefunden


def hinweis(anzahl: int) -> str:
    return (
        f"{anzahl} berechnete(s) Fristdatum entfernt: Das Programm erkennt "
        f"Fristauslöser, es rechnet keine Fristen. Maßgeblich ist der "
        f"Fristenkalender in jur|nodes."
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
