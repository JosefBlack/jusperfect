"""Aus Seiten werden Passagen, aus Passagen wird eine Auswahl.

Eine Passage ist die Einheit, die das Modell zitieren kann: klein genug, dass
ein Beleg etwas bedeutet, groß genug, dass der Zusammenhang erhalten bleibt.
Für Fragen wird nach Stichwortnähe ausgewählt; für die Vollanalyse geht alles
mit, bis zur Zeichen-Obergrenze je Aufruf.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from jusperfect.domain.models import Dokument, Passage, Seite

_STOPP = frozenset("""
der die das und oder aber nicht ist sind war waren wird werden wurde wurden hat haben hatte hatten
ein eine einer eines einem einen im in am an auf aus bei mit nach von vor zu zum zur für über unter
den dem des dass sich auch noch nur schon wie was wer wo wann als bis durch gegen ohne um seit
ich sie er es wir ihr sein ihre ihres ihrem ihren dieser diese dieses jener welche welcher welches
wurde bitte hier dort dann also sehr mehr kann können soll sollen muss müssen darf dürfen
""".split())

_UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def _woerter(text: str) -> list[str]:
    roh = re.findall(r"[a-zA-ZäöüÄÖÜß0-9]{3,}", text.lower())
    ergebnis = []
    for w in roh:
        w = w.translate(_UMLAUTE)
        if w in _STOPP:
            continue
        # sehr grobe Stammbildung: Flexionsendungen kappen
        for endung in ("ungen", "ung", "en", "er", "es", "em", "e", "n", "s"):
            if len(w) > 5 and w.endswith(endung):
                w = w[: -len(endung)]
                break
        ergebnis.append(w)
    return ergebnis


def passagen_bilden(dokument_nr: int, dokument: Dokument, seiten: list[Seite], max_zeichen: int = 1500) -> list[Passage]:
    ergebnis: list[Passage] = []
    for seite in seiten:
        absaetze = [a.strip() for a in re.split(r"\n\s*\n", seite.text) if a.strip()]
        stuecke: list[str] = []
        aktuell = ""
        for absatz in absaetze:
            # Überlange Absätze an Satzgrenzen teilen
            teile = [absatz] if len(absatz) <= max_zeichen else re.split(r"(?<=[.!?])\s+", absatz)
            for teil in teile:
                if aktuell and len(aktuell) + len(teil) + 2 > max_zeichen:
                    stuecke.append(aktuell)
                    aktuell = teil
                else:
                    aktuell = f"{aktuell}\n\n{teil}" if aktuell else teil
        if aktuell:
            stuecke.append(aktuell)
        for nr, text in enumerate(stuecke, start=1):
            ergebnis.append(Passage(
                kennung=f"D{dokument_nr}-S{seite.nummer}-P{nr}",
                dokument_id=dokument.id, dokument_titel=dokument.titel, seite=seite.nummer, text=text,
                dokument_datum=dokument.datum,
            ))
    return ergebnis


@dataclass(frozen=True, slots=True)
class Auswahl:
    """Was ausgewählt wurde – und ob die Frage überhaupt angeschlagen hat.

    Das zweite ist wichtiger, als es aussieht: Trifft kein Fragewort auf eine
    Passage, nimmt die Auswahl ersatzweise den Anfang der Akte. Das ist als
    Rückfall vertretbar, darf dem Bearbeiter aber nicht verschwiegen werden –
    er hielte sonst eine Antwort über den Aktenanfang für eine Antwort auf
    seine Frage.
    """
    passagen: list[Passage]
    treffer: bool
    durchsucht: int


def relevante_passagen(frage: str, passagen: list[Passage], max_anzahl: int = 14) -> list[Passage]:
    """Nur die Auswahl – für Aufrufer, die den Befund nicht brauchen."""
    return passagen_waehlen(frage, passagen, max_anzahl).passagen


def passagen_waehlen(frage: str, passagen: list[Passage], max_anzahl: int = 14) -> Auswahl:
    """Stichwortnähe mit Seltenheitsgewichtung; Reihenfolge der Akte bleibt erhalten."""
    if len(passagen) <= max_anzahl:
        # Es geht ohnehin alles mit; die Frage musste nichts aussortieren.
        return Auswahl(list(passagen), True, len(passagen))
    frage_woerter = set(_woerter(frage))
    if not frage_woerter:
        return Auswahl(list(passagen[:max_anzahl]), False, len(passagen))
    dokument_haeufigkeit: Counter[str] = Counter()
    passagen_woerter: list[set[str]] = []
    for p in passagen:
        ws = set(_woerter(p.text))
        passagen_woerter.append(ws)
        dokument_haeufigkeit.update(ws)
    n = len(passagen)
    bewertung: list[tuple[float, int]] = []
    for i, ws in enumerate(passagen_woerter):
        punkte = sum((1.0 + (n / (1 + dokument_haeufigkeit[w]))) for w in frage_woerter if w in ws)
        bewertung.append((punkte, i))
    bewertung.sort(key=lambda t: (-t[0], t[1]))
    gewaehlt = sorted(i for punkte, i in bewertung[:max_anzahl] if punkte > 0)
    if not gewaehlt:
        return Auswahl([passagen[i] for i in range(min(max_anzahl, n))], False, n)
    return Auswahl([passagen[i] for i in gewaehlt], True, n)


def budget_anwenden(passagen: list[Passage], max_zeichen: int) -> tuple[list[Passage], bool]:
    """Nimmt Passagen in Aktenreihenfolge, bis das Zeichenbudget erschöpft ist."""
    auswahl: list[Passage] = []
    summe = 0
    for p in passagen:
        if summe + len(p.text) > max_zeichen:
            return auswahl, True
        auswahl.append(p)
        summe += len(p.text)
    return auswahl, False
