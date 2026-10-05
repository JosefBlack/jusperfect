"""Welche Stelle einer Passage trägt eine bestimmte Aussage?

Eine Fundstelle (``D1-S1-P3``) zeigt auf eine **Passage** – einen Absatz von bis
zu 1.500 Zeichen. Für die Belegpflicht ist das richtig: klein genug, dass ein
Beleg etwas bedeutet, groß genug, dass der Zusammenhang erhalten bleibt. Zum
Nachlesen ist es zu grob.

Aus der Kanzlei: „Da wird nur zum Beispiel eine Seite markiert und nicht genau
die Information, die man braucht. Das Überprüfen dauert bisher ja immer noch zu
lange, um effizienter zu arbeiten." Genau diese Arbeit soll das Programm
abnehmen, nicht verursachen.

Dieses Modul sucht in der Passage die Stelle, die eine Aussage wirklich trägt –
und darin die harten Angaben: das Datum, den Betrag, den Ortsnamen. Zwei Dinge
sind daran wichtig:

* **Es fragt kein Modell.** Der Vergleich läuft im Programm, kostet nichts und
  ist nachvollziehbar. Er kann auch nichts erfinden: Markiert wird ausschließlich
  Text, der in der Passage steht.
* **Es rät nicht.** Findet sich keine hinreichend gute Stelle, gibt es keinen
  Treffer – dann bleibt es bei der ganzen Passage. Eine falsch markierte Stelle
  wäre schlimmer als eine unmarkierte: Sie führt den Blick weg von dem, was
  wirklich dasteht.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from jusperfect.services.passagen import _woerter

# Satzgrenzen, ohne an Datumsangaben und Beträgen zu zerbrechen: Ein Punkt
# trennt nur, wenn Leerraum und ein Großbuchstabe folgen. „04.05.2026" bleibt
# dadurch zusammen, „… zu. Der Betriebsrat …" wird geteilt.
_TRENNER = re.compile(r"(?<=[.!?:;])\s+(?=[A-ZÄÖÜ„\"'(])|\n+")

# Die harten Angaben – das, wonach ein Anwalt im Text sucht.
_HART = re.compile(
    r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b"                       # 04.05.2026
    r"|\b\d{4}-\d{2}-\d{2}\b"                               # 2026-05-04
    r"|\b\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?\s?(?:EUR|€)"      # 3.940,00 EUR
    r"|\b\d{1,3}(?:\.\d{3})*,\d{1,2}\b"                     # 3.940,00
    r"|\b\d+\s?(?:%|km/h|km|m²|qm|cm|Stunden|Monate|Wochen|Tage)\b"
    r"|\b§+\s?\d+[a-z]?\b"                                   # § 626, §§ 558
)

# Dieselben Angaben, wie eine Texterkennung sie manchmal ausliest.
#
# Aus der Kanzlei, zur Scanakte 31/26 SC: Dort steht „l5.03.2026" mit einem
# kleinen L, „3O.09.2026" mit einem grossen O und „85O,00". Das Modell liest
# das richtig und schreibt den richtigen Wert - die Markierung aber suchte
# danach im Originaltext und fand ihn nicht, weil dort eben der Buchstabe
# steht. Die Folge: Der Verweis sprang nicht hin, und ausgerechnet bei einer
# Scanakte, wo das Nachsehen am noetigsten ist.
#
# Uebersetzt wird nur innerhalb eines Zeichens, das nach Datum oder Betrag
# aussieht, und nur wenn wenigstens eine echte Ziffer darin steht. Ein Wort
# aus Buchstaben kann so nicht versehentlich zur Zahl werden.
_SCAN_ZIFFERN = str.maketrans({"l": "1", "I": "1", "|": "1", "O": "0", "o": "0",
                               "S": "5", "B": "8", "Z": "2"})
_HART_SCAN = re.compile(
    r"\b[\dlI|OoSBZ]{1,2}\.[\dlI|OoSBZ]{1,2}\.[\dlI|OoSBZ]{2,4}\b"   # l5.03.2026
    r"|\b[\dlI|OoSBZ]{1,3}(?:\.[\dlI|OoSBZ]{3})*,[\dlI|OoSBZ]{1,2}\b"  # 85O,00
)


def _entziffern(zeichen: str) -> str | None:
    """Ein Scanfehler-Zeichen als das, was es meint – oder ``None``."""
    if not any(z.isdigit() for z in zeichen):
        return None
    beziffert = zeichen.translate(_SCAN_ZIFFERN)
    return beziffert if _HART.fullmatch(beziffert) else None


# Ein Eigenname trägt oft die eigentliche Auskunft („Fahrtrichtung Stuttgart").
_NAME = re.compile(r"\b[A-ZÄÖÜ][\wäöüß\-]{3,}\b")

#: Ab dieser Punktzahl gilt eine Stelle als gefunden. Darunter bleibt es bei der
#: ganzen Passage – lieber grob als falsch.
SCHWELLE = 3

#: Um so viel muss die beste Stelle die zweitbeste übertreffen.
#:
#: Aus der Kanzlei: „wenn ein Wort häufiger in einem Text vorkommt, dann ist es
#: ja, als würde man ein Wort suchen. Jetzt müsste natürlich die Information,
#: die markiert wird, perfekt zu der Textstelle passen."
#:
#: Genau das ist der Fall, in dem eine Punktzahl allein nicht trägt: Stehen
#: dieselben Wörter in zwei Sätzen gleich oft, gewänne sonst schlicht der
#: erste – und in der Hälfte der Fälle wäre es der falsche. Liegen zwei
#: Stellen zu dicht beieinander, gibt es deshalb gar keine: Dann bleibt die
#: ganze Passage markiert, und der Leser entscheidet selbst.
ABSTAND = 2

#: Eine wörtlich übereinstimmende Wortfolge ab dieser Länge ist das stärkste
#: Zeichen, das es ohne Modell gibt: Zufällig treffen sich drei Wörter in
#: derselben Reihenfolge nicht.
FOLGE_MINDESTENS = 3


@dataclass(frozen=True, slots=True)
class Treffer:
    """Eine Stelle in der Passage, in Zeichen ab deren Anfang gezählt."""

    start: int
    ende: int
    zitat: str
    #: Die harten Angaben darin, ebenfalls in Zeichen ab Passagenanfang.
    marken: tuple[tuple[int, int], ...] = field(default=())
    punkte: int = 0


def _stuecke(text: str) -> list[tuple[int, int]]:
    """Satzgrenzen als (Anfang, Ende), Leerraum bereits abgeschnitten."""
    grenzen: list[tuple[int, int]] = []
    pos = 0
    for trenner in list(_TRENNER.finditer(text)) + [None]:
        ende = trenner.start() if trenner is not None else len(text)
        stueck = text[pos:ende]
        vorn = len(stueck) - len(stueck.lstrip())
        hinten = len(stueck) - len(stueck.rstrip())
        if ende - hinten > pos + vorn:
            grenzen.append((pos + vorn, ende - hinten))
        pos = trenner.end() if trenner is not None else ende
    return grenzen


_DEUTSCH = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$")


def _normal(angabe: str) -> str:
    """Dieselbe Angabe in derselben Schreibweise.

    Die Analyse liefert Daten als ``2026-05-04``, die Dokumente schreiben
    ``04.05.2026`` – dasselbe Datum. Ohne diese Umrechnung fände ein
    Chronologieeintrag seine eigene Stelle im Dokument nicht wieder.
    """
    ohne = angabe.replace(" ", "")
    m = _DEUTSCH.match(ohne)
    if not m:
        return ohne
    tag, monat, jahr = m.groups()
    if len(jahr) == 2:
        # Zweistellige Jahre gibt es in Akten noch; 26 meint 2026, nicht 1926.
        jahr = "20" + jahr
    return f"{jahr}-{int(monat):02d}-{int(tag):02d}"


def _harte(text: str) -> set[str]:
    """Die harten Angaben eines Textes, Scanfehler eingerechnet.

    Ein Scan, der „l5.03.2026" hergibt, meint denselben Tag wie die Analyse mit
    ihrem „15.03.2026". Beide Formen stehen im Ergebnis, damit sich Aussage und
    Originalstelle auch dann treffen, wenn nur eine von beiden den Buchstaben
    trägt.
    """
    gefunden = {_normal(m.group(0)) for m in _HART.finditer(text)}
    for m in _HART_SCAN.finditer(text):
        beziffert = _entziffern(m.group(0))
        if beziffert is not None:
            gefunden.add(_normal(beziffert))
    return gefunden


def _laengste_folge(a: list[str], b: list[str]) -> int:
    """Wie viele Wörter beide Texte in derselben Reihenfolge gemeinsam haben.

    Der stärkste Hinweis, den ein Vergleich ohne Modell geben kann: Einzelne
    Wörter treffen sich zufällig, drei Wörter in derselben Reihenfolge nicht.
    """
    if not a or not b:
        return 0
    laengste = 0
    vorige = [0] * (len(b) + 1)
    for wort in a:
        aktuelle = [0] * (len(b) + 1)
        for j, anderes in enumerate(b, start=1):
            if wort == anderes:
                aktuelle[j] = vorige[j - 1] + 1
                laengste = max(laengste, aktuelle[j])
        vorige = aktuelle
    return laengste


def treffer_finden(aussage: str, passage_text: str) -> Treffer | None:
    """Die Stelle der Passage, die ``aussage`` trägt – oder ``None``.

    Bewertet wird jeder Satz der Passage:

    * eine harte Angabe (Datum, Betrag, Paragraph), die auch in der Aussage
      steht, zählt dreifach;
    * ein gemeinsames Inhaltswort zählt einfach;
    * eine wörtlich übereinstimmende Wortfolge zählt doppelt je Wort – sie ist
      das stärkste Zeichen dafür, dass es wirklich diese Stelle ist.

    Der beste Satz gewinnt nur, wenn er die Schwelle erreicht **und** den
    zweitbesten deutlich übertrifft. Stehen zwei Stellen gleich gut da, wäre
    jede Wahl geraten; dann gibt es keinen Treffer und die ganze Passage bleibt
    markiert.
    """
    if not aussage.strip() or not passage_text.strip():
        return None
    harte_aussage = _harte(aussage)
    folge_aussage = _woerter(aussage)
    woerter_aussage = set(folge_aussage)
    namen_aussage = {m.group(0) for m in _NAME.finditer(aussage)}
    if not (harte_aussage or woerter_aussage):
        return None

    stuecke = _stuecke(passage_text)
    bewertet: list[tuple[int, Treffer]] = []
    for nr, (start, ende) in enumerate(stuecke):
        satz = passage_text[start:ende]
        harte_treffer = harte_aussage & _harte(satz)
        folge_satz = _woerter(satz)
        gemeinsam = woerter_aussage & set(folge_satz)
        folge = _laengste_folge(folge_aussage, folge_satz)
        punkte = 3 * len(harte_treffer) + len(gemeinsam) + (2 * folge if folge >= FOLGE_MINDESTENS else 0)
        if punkte < SCHWELLE:
            continue
        bewertet.append((nr, Treffer(start=start, ende=ende, zitat=satz, punkte=punkte,
                                     marken=_marken(passage_text, start, ende, harte_treffer,
                                                    namen_aussage))))
    if not bewertet:
        return None
    bewertet.sort(key=lambda x: (-x[1].punkte, x[1].start))
    if len(bewertet) == 1:
        return bewertet[0][1]

    (nr_a, bester), (nr_b, zweiter) = bewertet[0], bewertet[1]
    if abs(nr_a - nr_b) == 1:
        # Zwei benachbarte Saetze: Die Aussage steht in beiden - "Am 04.05.2026
        # sei sie gerufen worden. Dort habe man ihr ein Schreiben ueberreicht."
        # Hier ist nicht zweideutig, welcher gemeint ist; gemeint sind beide.
        # Sie werden zusammengefasst statt verworfen.
        return _zusammenfassen(passage_text, bester, zweiter)
    if bester.punkte - zweiter.punkte < ABSTAND:
        # Zwei entfernte Stellen passen gleich gut. Eine davon zu markieren
        # hiesse raten, und der Leser saehe der Markierung nicht an, dass
        # geraten wurde.
        return None
    return bester


def _zusammenfassen(text: str, a: Treffer, b: Treffer) -> Treffer:
    erst, dann = (a, b) if a.start <= b.start else (b, a)
    start, ende = erst.start, dann.ende
    marken = tuple(sorted(set(erst.marken) | set(dann.marken)))
    return Treffer(start=start, ende=ende, zitat=text[start:ende],
                   marken=marken, punkte=erst.punkte + dann.punkte)


def _marken(text: str, start: int, ende: int, harte: set[str],
            namen: set[str]) -> tuple[tuple[int, int], ...]:
    """Wo im Satz die harten Angaben und die gemeinsamen Eigennamen stehen."""
    gefunden: list[tuple[int, int]] = []
    satz = text[start:ende]
    for m in _HART.finditer(satz):
        if _normal(m.group(0)) in harte:
            gefunden.append((start + m.start(), start + m.end()))
    for m in _NAME.finditer(satz):
        if m.group(0) in namen:
            gefunden.append((start + m.start(), start + m.end()))
    # Ohne Sortierung und Zusammenfassung ueberlappten sich die Marken beim
    # Einfaerben - eine Angabe, die zugleich Name und harte Angabe ist, kaeme
    # zweimal vor.
    gefunden.sort()
    zusammen: list[tuple[int, int]] = []
    for anfang, schluss in gefunden:
        if zusammen and anfang <= zusammen[-1][1]:
            zusammen[-1] = (zusammen[-1][0], max(zusammen[-1][1], schluss))
        else:
            zusammen.append((anfang, schluss))
    return tuple(zusammen)
