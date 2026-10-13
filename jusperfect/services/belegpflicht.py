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
* Kurze Felder (Kernaussage, ein Hinweis, ein Schritt): dieselbe Prüfung, nur
  fällt hier das ganze Feld, statt eine Marke zu hinterlassen.
* Entwürfe: ein eigener Maßstab, siehe ``entwurf_fail_closed``.

---

## Wie weit ein Beleg zurückreicht (Befund F04, 05.10.2026)

Bis zum 05.10.2026 galt: alles seit dem vorigen Beleg. Damit nahm ein Beleg
auch mit, was Absätze vorher stand:

    Die Gegenseite hat den Anspruch in voller Höhe anerkannt.

    Der Vertrag ist unterschrieben [Q: D1-S1-P1].

Der erste Absatz steht in keiner Passage. Er kam vollständig durch, und
``verworfen`` zählte null. Die Prüfung war **nach** dem letzten Beleg streng
und **vor** jedem Beleg großzügig – eine Unsymmetrie, die niemandem auffiel,
weil alle Prüfungen nach erfundenen Belegen suchten und keine nach fehlenden.

**Ein Beleg reicht jetzt bis zur nächsten Einheitsgrenze zurück**, nicht
weiter: bis zur Leerzeile davor, bis zum Beginn des Aufzählungspunktes, bis
zur Überschrift. Was davor steht, ist eine eigene Aussage und braucht einen
eigenen Beleg.

Die Grenze ist bewusst der **Absatz** und nicht der Satz. Die Anweisung an das
Modell lautet, jede Tatsachenaussage mit einem Beleg zu schließen; schreibt es
zwei Sätze und setzt den Beleg ans Ende, ist das die vorgesehene Form. Ein
Satzmaßstab würde fast jede richtige Antwort zerschneiden. Das bleibt eine
Grenze dieser Prüfung, und sie steht hier, statt verschwiegen zu werden.
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

# Woran eine neue Aussageeinheit beginnt. Drei Formen, und jede musste
# einzeln hin: Eine Leerzeile trennt Absaetze; eine Zeile, die mit einem
# Aufzaehlungszeichen oder einer Ueberschrift anfaengt, beginnt selbst eine;
# und eine Ueberschrift beendet ihre Einheit auch dann, wenn die naechste
# Zeile gewoehnlicher Text ist. Die dritte fehlte im ersten Entwurf, und
# "## Behauptung\nBelegter Satz [Q: …]" kam damit vollstaendig durch.
_GRENZMUSTER = (
    # (Muster, ob der ganze Treffer der Trenner ist)
    (re.compile(r"\n[^\S\n]*\n"), True),
    (re.compile(r"\n(?=[^\S\n]*(?:[-*\u2022\u2013]\s|\d+[.)]\s|#{1,6}\s))"), True),
    (re.compile(r"(?m)^[^\S\n]*#{1,6}\s[^\n]*\n"), False),
)


def _einheiten(koerper: str) -> list[str]:
    """Der Rumpf vor einem Beleg, zerlegt in Einheiten samt Trennern.

    Gerade Stellen sind Einheiten, ungerade die Trenner dazwischen. Die
    **letzte** Einheit ist die, die der Beleg traegt; alles davor ist eine
    eigene Aussage. Die Trenner bleiben erhalten, sonst klebte eine Liste nach
    der Pruefung zusammen.
    """
    grenzen: list[tuple[int, int]] = []
    for muster, ganz in _GRENZMUSTER:
        for treffer in muster.finditer(koerper):
            grenzen.append((treffer.start(), treffer.end()) if ganz
                           else (treffer.end() - 1, treffer.end()))
    if not grenzen:
        return [koerper]
    teile: list[str] = []
    stelle = 0
    for anfang, ende in sorted(set(grenzen)):
        if anfang < stelle:          # ueberlappende Grenzen: die erste gilt
            continue
        teile.append(koerper[stelle:anfang])
        teile.append(koerper[anfang:ende])
        stelle = ende
    teile.append(koerper[stelle:])
    return teile


UNBELEGT_HINWEIS = "Aussage ohne belastbaren Beleg entfernt (genannt: —)."


def unbelegt_satz(verworfen: int, genannt: list[str]) -> str:
    """EINE Zeile fuer alle zurueckgehaltenen Aussagen, nicht eine je Aussage.

    Aus der Kanzlei am 13.10.2026:

        „Aussage ohne belastbaren Beleg entfernt (genannt: —)." steht im
        Programm und nimmt unnoetig Platz weg – vielleicht lieber zaehlen
        oder ganz weglassen, da man die Aussage sowieso nicht anklicken kann.

    Hier stand eine Zeile je zurueckgehaltener Aussage, bei fuenfzehn also
    fuenfzehnmal derselbe Satz. Eine Stelle las sich sogar
    ``hinweise += [UNBELEGT_HINWEIS] * vorlauf_verworfen`` - die Wiederholung
    war ausgeschrieben.

    **Weggelassen wird sie trotzdem nicht.** Dass etwas zurueckgehalten wurde,
    ist die Belegpflicht selbst; eine Antwort, die stillschweigend kuerzer
    wird, waere genau der Zustand, den dieses Programm verhindert. Gezaehlt
    wird also, wie es die Kanzlei vorgeschlagen hat.

    Was dabei bleibt: die Kennungen, die das Modell GENANNT hat, obwohl es sie
    nicht gibt. Das ist kein Rauschen, sondern der Nachweis einer Erfindung.
    Ein Gedankenstrich dagegen sagt nichts und faellt weg.
    """
    if verworfen <= 0:
        return ""
    satz = ("Eine Aussage wurde" if verworfen == 1
            else f"{verworfen} Aussagen wurden") + " ohne belastbaren Beleg entfernt."
    echte = sorted({g for g in genannt if g and g != "—"})
    if echte:
        satz += (" Dabei war eine Fundstelle genannt, die es nicht gibt: "
                 if len(echte) == 1 else
                 " Dabei waren Fundstellen genannt, die es nicht gibt: ")
        satz += ", ".join(echte) + "."
    return satz


def _marken_glaetten(text: str) -> str:
    """Mehrere Marken hintereinander werden eine; eine Marke bekommt Luft."""
    text = re.sub(rf"(?:{re.escape(ENTFERNT)}\s*){{2,}}", ENTFERNT + " ", text)
    # Sonst klebt die Marke am vorigen Beleg: "[Q: D1-S1-P1][Aussage ohne …]".
    text = re.sub(rf"(?<=\S)(?={re.escape(ENTFERNT)})", " ", text)
    return text.strip()


def _vorlauf_pruefen(stuecke: list[str]) -> tuple[str, int]:
    """Die Einheiten vor der belegten: zurückhalten, was Substanz hat.

    Gerade Stellen sind Einheiten, ungerade die Trenner. Die Trenner bleiben
    stehen, damit eine Liste nach der Prüfung noch eine Liste ist.
    """
    teile: list[str] = []
    verworfen = 0
    for i, stueck in enumerate(stuecke):
        if i % 2:
            teile.append(stueck)              # Trenner
        elif stueck.strip():
            teile.append(ENTFERNT)
            verworfen += 1
        else:
            teile.append(stueck)              # nur Leerraum
    return "".join(teile), verworfen


@dataclass
class Belegergebnis:
    text: str
    quellen: list[Quelle]
    hinweise: list[str] = field(default_factory=list)
    verworfen: int = 0


def aussage_fail_closed(text: str, index: dict[str, Passage],
                        verlangt_alle: bool = False) -> Belegergebnis:
    """Freitext fail closed. ``verlangt_alle`` verschärft den Maßstab.

    Gewöhnlich genügt **ein** tragender Beleg: Nennt das Modell neben einer
    richtigen Kennung eine erfundene, bleibt die Aussage mit der richtigen
    stehen.

    Beim Aufräumen nach einem gelöschten Dokument ist das falsch, und zwar
    genau umgekehrt (Befund F02.2 der Zweitprüfung vom 05.10.2026): Dort waren
    beim Schreiben **alle** Kennungen gültig. Löst eine nicht mehr auf, gehört
    sie zum entfernten Dokument. Die Aussage stand dann auf zwei Grundlagen,
    und eine fehlt – dass die andere sie allein trägt, weiß niemand. Mit
    ``verlangt_alle`` fällt sie deshalb ganz, wie ein Chronologieeintrag auch.
    """
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
    #: Was das Modell als Beleg genannt hat, obwohl es die Stelle nicht gibt.
    genannt_gesammelt: list[str] = []
    hat_gueltig = False
    letzte = 0
    for m in ZITAT_RE.finditer(text):
        # Nicht mehr alles seit dem vorigen Beleg: nur die letzte Einheit.
        # Was davor steht, ist eine eigene Aussage ohne eigenen Beleg und
        # faellt wie jede andere auch (Befund F04, siehe Modulkopf).
        stuecke = _einheiten(text[letzte:m.start()])
        koerper = stuecke[-1]
        vorlauf, vorlauf_verworfen = _vorlauf_pruefen(stuecke[:-1])
        if vorlauf:
            teile.append(vorlauf)
        if vorlauf_verworfen:
            verworfen += vorlauf_verworfen
        kennungen = [k.strip() for k in m.group(1).split(",") if k.strip()]
        gueltig = [k for k in kennungen if k in index]
        traegt = bool(gueltig) and (len(gueltig) == len(kennungen) or not verlangt_alle)
        if traegt:
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
            genannt_gesammelt.extend(kennungen)
        letzte = m.end()

    if not hat_gueltig:
        schluss = [x for x in (unbelegt_satz(verworfen, genannt_gesammelt),) if x]
        return Belegergebnis(VERZICHT, [],
                             hinweise + schluss
                             + ["Keine Aussage war belegt; die Antwort wurde zurückgehalten."],
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
    satz = unbelegt_satz(verworfen, genannt_gesammelt)
    if satz:
        hinweise.append(satz)

    neuer_text = "".join(teile)
    # Mehrere zurückgehaltene Abschnitte hintereinander werden zu einer Marke.
    neuer_text = _marken_glaetten(neuer_text)
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


def feld_fail_closed(text: str, index: dict[str, Passage]) -> Belegergebnis | None:
    """Ein kurzes Feld: Kernaussage, ein Hinweis, ein Schritt.

    Befund F04 der Zweitprüfung vom 05.10.2026: Die Belegpflicht galt für die
    Antwort auf eine Frage und für die strukturierten Listen – nicht für die
    Kernaussage der Eingangsprüfung und nicht für die Hinweise, die das Modell
    liefert. *„Das Wort ‚Hinweis' macht einen vom Modell gelieferten
    Sachverhalt nicht automatisch zu einem ungefährlichen Systemhinweis."*

    Der Unterschied zur Antwort ist nur die Folge, nicht der Maßstab: Hier
    fällt das **ganze Feld**, statt eine Marke zu hinterlassen. Ein einzelner
    Hinweis, von dem nur noch „[Aussage ohne belastbaren Beleg entfernt]"
    übrig wäre, ist keine Auskunft, sondern Lärm.

    Gibt ``None`` zurück, wenn nichts bleibt.
    """
    if not text or not text.strip():
        return None
    ergebnis = aussage_fail_closed(text, index)
    if not ergebnis.quellen:
        return None
    return ergebnis


def entwurf_fail_closed(text: str, index: dict[str, Passage]) -> Belegergebnis:
    """Ein Entwurf – derselbe Grundsatz, ein anderer Maßstab. Und warum.

    Ein Entwurf ist kein Bericht über die Akte, sondern ein Brief. Die
    Anweisung an das Modell sagt es ausdrücklich: *„Sachverhaltsangaben im
    Entwurf tragen Belege [Q: ...] am Satzende"* – Anrede, Grußformel und die
    Formulierung des Anliegens tragen keine. Die strenge Prüfung der Antwort
    würde daraus einen Brief machen, in dem „Sehr geehrte Damen und Herren"
    durch eine Entfernungsmarke ersetzt ist.

    Geprüft wird deshalb zweierlei, und beides ist hart:

    1. **Jeder Beleg muss tragen.** Löst er auf keine mitgelieferte Passage
       auf, fällt die Aussage, die er tragen sollte – nicht nur der Beleg.
       Bisher blieb sie stehen und bekam die Marke „[Q: ohne Beleg]".
    2. **Ein Entwurf ohne einen einzigen tragenden Beleg ist keiner.** Genau
       das war der reproduzierte Fall: ein vollständig erfundener Entwurf,
       HTTP 201, leere Quellenliste. Die leere Quellenliste sagt es dem
       Programm; gesehen hat sie niemand.

    Was bleibt und bewusst bleibt: ein Satz ohne Beleg, der auch keinen
    beansprucht. Er ist die Form des Briefes, nicht seine Tatsachenbehauptung.
    Diese Grenze ist mit dem Auge zu ziehen – deshalb geht ein Entwurf nie
    ohne menschliche Freigabe hinaus, und deshalb steht sie hier.
    """
    teile: list[str] = []
    gefunden: list[str] = []
    hinweise: list[str] = []
    aussagen: dict[str, str] = {}
    verworfen = 0
    genannt_gesammelt: list[str] = []
    letzte = 0
    for m in ZITAT_RE.finditer(text):
        stuecke = _einheiten(text[letzte:m.start()])
        koerper = stuecke[-1]
        teile.append("".join(stuecke[:-1]))
        kennungen = [k.strip() for k in m.group(1).split(",") if k.strip()]
        gueltig = [k for k in kennungen if k in index]
        if gueltig:
            teile.append(koerper + f"[Q: {', '.join(gueltig)}]")
            gefunden.extend(gueltig)
            for k in gueltig:
                aussagen.setdefault(k, koerper)
        else:
            teile.append(ENTFERNT)
            verworfen += 1
            genannt_gesammelt.extend(kennungen)
        letzte = m.end()
    teile.append(text[letzte:])
    satz = unbelegt_satz(verworfen, genannt_gesammelt)
    if satz:
        hinweise.append(satz)

    neuer_text = "".join(teile)
    neuer_text = _marken_glaetten(neuer_text)
    quellen = quellen_aus_kennungen(gefunden, index, [], aussagen)
    return Belegergebnis(neuer_text, quellen, hinweise, verworfen)
