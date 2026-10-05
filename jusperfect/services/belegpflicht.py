"""Belegpflicht – fail closed. Was keinen Beleg hat, wird nicht behauptet.

Die Belegprüfung (quellen.py) löste Kennungen auf und markierte unbelegte
Stellen. jusperfect geht den Schritt weiter, den das Konzept verlangt: eine
Aussage ohne belastbaren Beleg fällt aus dem Ergebnis, statt neben einem
Warnhinweis stehen zu bleiben. Ein Modell kann eine Kennung erfinden wie
alles andere; eine erfundene Kennung trägt hier nichts.

Zwei Formen:

* Freitext (Antwort auf eine Frage): Eine Aussage ist der Textabschnitt, der
  mit einem ``[Q: …]`` endet. Löst der Beleg auf keine mitgelieferte Passage
  auf, wird der Abschnitt zurückgehalten – sichtbar, nicht stillschweigend.
  Trägt die ganze Antwort keinen einzigen gültigen Beleg, tritt an ihre
  Stelle ein klarer Verzicht, damit kein unbelegter Schluss über die freien
  Textstellen hereinkommt.
* Strukturierte Einträge (Chronologie, Beteiligte, Widersprüche …): Ein
  Eintrag ohne gültige Quelle wird nicht aufgenommen.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from jusperfect.domain.models import Passage, Quelle
from jusperfect.services.quellen import ZITAT_RE, quellen_aus_kennungen

VERZICHT = "Zu dieser Frage liegt in den geladenen Dokumenten kein belastbarer Beleg vor."
ENTFERNT = "[Aussage ohne belastbaren Beleg entfernt]"

# Was nach dem letzten Beleg noch zum belegten Satz gehoert: sein Schlusszeichen
# und der Leerraum dahinter. Bewusst eng gefasst - alles andere ist eine neue
# Aussage und braucht einen eigenen Beleg.
_SATZSCHLUSS = re.compile(r"[\s.,;:!?)\]\}\"\u201c\u201d\u201e\u00bb\u00ab\u2013\u2014-]*")


@dataclass
class Belegergebnis:
    text: str
    quellen: list[Quelle]
    hinweise: list[str] = field(default_factory=list)
    verworfen: int = 0


def aussage_fail_closed(text: str, index: dict[str, Passage]) -> Belegergebnis:
    if ZITAT_RE.search(text) is None:
        return Belegergebnis(VERZICHT, [], ["Die Antwort trug keinen Beleg und wurde zurückgehalten."], 1)

    teile: list[str] = []
    gefunden: list[str] = []
    hinweise: list[str] = []
    # Welcher Satz welchen Beleg zitiert. Damit laesst sich in der Passage die
    # Stelle finden, die ihn traegt - statt den ganzen Absatz zu markieren und
    # den Leser darin suchen zu lassen.
    aussagen: dict[str, str] = {}
    verworfen = 0
    hat_gueltig = False
    letzte = 0
    for m in ZITAT_RE.finditer(text):
        koerper = text[letzte:m.start()]
        kennungen = [k.strip() for k in m.group(1).split(",") if k.strip()]
        gueltig = [k for k in kennungen if k in index]
        if gueltig:
            teile.append(koerper + f"[Q: {', '.join(gueltig)}]")
            gefunden.extend(gueltig)
            for k in gueltig:
                aussagen.setdefault(k, koerper)
            hat_gueltig = True
        else:
            # Der Abschnitt (Behauptung samt erfundenem Beleg) fällt weg; an
            # seine Stelle tritt eine sichtbare Marke.
            teile.append(ENTFERNT)
            verworfen += 1
            genannt = ", ".join(kennungen) or "—"
            hinweise.append(f"Aussage ohne belastbaren Beleg entfernt (genannt: {genannt}).")
        letzte = m.end()

    if not hat_gueltig:
        return Belegergebnis(VERZICHT, [],
                             hinweise + ["Keine Aussage war belegt; die Antwort wurde zurückgehalten."],
                             verworfen)

    # Was nach dem letzten Beleg noch kommt.
    #
    # Hier stand `teile.append(text[letzte:])` - der Rest ging unveraendert
    # durch. Die Belegpflicht griff damit fuer jeden Satz VOR einem Beleg und
    # fuer keinen danach: „Der Vertrag wurde unterschrieben [Q: D1-S1-P1]. Der
    # Gegner hat die Forderung voll anerkannt." kam vollstaendig heraus,
    # verworfen = 0. Gefunden bei einer Gegenprobe von aussen; keiner unserer
    # Tests hatte danach gefragt, weil sie alle erfundene BELEGE prueften und
    # nicht fehlende.
    #
    # Der Satzschluss gehoert noch zum belegten Satz und bleibt. Alles, was
    # danach eine eigene Aussage waere, wird zurueckgehalten wie jede andere
    # unbelegte auch.
    rest = text[letzte:]
    schluss = _SATZSCHLUSS.match(rest)
    teile.append(rest[:schluss.end()])
    nachsatz = rest[schluss.end():]
    if nachsatz.strip():
        teile.append(ENTFERNT)
        verworfen += 1
        hinweise.append("Aussage ohne belastbaren Beleg entfernt (genannt: —).")

    neuer_text = "".join(teile)
    # Mehrere zurückgehaltene Abschnitte hintereinander werden zu einer Marke.
    neuer_text = re.sub(rf"(?:{re.escape(ENTFERNT)}\s*){{2,}}", ENTFERNT + " ", neuer_text).strip()
    quellen = quellen_aus_kennungen(gefunden, index, [], aussagen)
    return Belegergebnis(neuer_text, quellen, hinweise, verworfen)


def eintraege_fail_closed(
    eintraege: list,
    roh_liste: list,
    index: dict[str, Passage],
    kennungen_fn: Callable[[object], list[str]],
) -> tuple[list, int]:
    """Behält nur Einträge mit mindestens einer gültigen Quelle.

    Gibt die behaltenen Einträge (mit gesetzten ``quellen``) und die Zahl der
    verworfenen zurück.
    """
    behalten = []
    for eintrag, roh in zip(eintraege, roh_liste):
        kennungen = kennungen_fn(roh)
        # Auch hier bestimmt der Text des Eintrags die Stelle in der Passage:
        # Ein Chronologieeintrag "Kuendigung zugegangen" soll auf den Satz
        # zeigen, in dem die Kuendigung zugeht, nicht auf den ganzen Absatz.
        aussage = _eintragstext(roh)
        aussagen = {k: aussage for k in kennungen} if aussage else None
        quellen = quellen_aus_kennungen(kennungen, index, [], aussagen)
        if quellen:
            eintrag.quellen = quellen
            behalten.append(eintrag)
    return behalten, len(eintraege) - len(behalten)


def _eintragstext(roh: object) -> str:
    """Die Textfelder eines Eintrags, aneinandergereiht.

    Welche Felder ein Eintrag hat, ist je nach Liste verschieden - Ereignis,
    Beschreibung, Gegenstand, Bezeichnung. Statt sie einzeln aufzuzaehlen und
    beim naechsten neuen Feld wieder zu vergessen, gehen alle Zeichenketten
    mit, ausser den Quellen selbst.
    """
    if not isinstance(roh, dict):
        return ""
    return " ".join(str(w) for k, w in roh.items()
                    if k != "quellen" and isinstance(w, str) and w.strip())
