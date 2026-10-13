"""Belege prüfen: Jede Kennung, die das Modell nennt, muss es wirklich geben.

Ein Modell kann Kennungen erfinden wie alles andere. Deshalb wird jeder
Beleg gegen die tatsächlich mitgeschickten Passagen aufgelöst; unbekannte
Kennungen werden markiert und als Hinweis gemeldet, nicht stillschweigend
angezeigt.
"""

from __future__ import annotations

import re

from jusperfect.domain.models import Passage, Quelle
from jusperfect.services.fundstelle import treffer_finden

ZITAT_RE = re.compile(r"\[Q:\s*([^\]]+?)\s*\]")


def ohne_belege(text: str) -> str:
    """Der Text ohne die Belegmarken ``[Q: …]``.

    Fuer alles, was das Haus verlaesst. Die Marken sind das Werkzeug der
    Pruefung - im Programm anklickbar, auf einem Schreiben an die Gegenseite
    ein Fremdkoerper. Der Auftragstext sagt es dem Modell auch so: „die
    Kanzlei entfernt sie nach der Pruefung."

    Das Leerzeichen davor faellt mit, der Satzpunkt dahinter bleibt stehen.
    """
    sauber = ZITAT_RE.sub("", text)
    # "geschlossen . Mehr" -> "geschlossen. Mehr"
    sauber = re.sub(r"[ \t]+([.,;:!?)])", r"\1", sauber)
    return re.sub(r"[ \t]{2,}", " ", sauber)


def bis_zum_letzten_beleg(roh: str) -> str:
    """Der Teil eines Rohtextes, der mit einer abgeschlossenen Aussage endet.

    Der Auftragstext verlangt, dass jede Tatsachenaussage mit ``[Q: …]``
    endet. Solange kein vollständiger Beleg dasteht, ist die Aussage nicht
    fertig – und was nicht fertig ist, ist nicht zu prüfen.

    Steht hier und nicht bei einem der beiden Aufrufer: Frage und Entwurf
    strömen beide, und beide dürfen nur Geprüftes zeigen (Befund F05 der
    Zweitprüfung, 05.10.2026). Eine zweite Abschrift wäre eine zweite
    Stelle, an der diese Regel auseinanderlaufen kann.
    """
    letzter = None
    for letzter in ZITAT_RE.finditer(roh):
        pass
    return roh[:letzter.end()] if letzter else ""


def index_bauen(passagen: list[Passage]) -> dict[str, Passage]:
    return {p.kennung: p for p in passagen}


def _quelle(p: Passage, aussage: str = "") -> Quelle:
    """Eine Quelle – und, wenn die Aussage bekannt ist, die genaue Stelle darin.

    Ohne Aussage bleibt es beim Anfang der Passage, wie bisher. Mit Aussage
    wird die Stelle gesucht, die sie trägt: Dann steht im Beleg der Satz, um
    den es geht, statt der ersten 240 Zeichen des Absatzes. Wer nachliest,
    soll nicht noch einmal suchen müssen.
    """
    treffer = treffer_finden(aussage, p.text) if aussage else None
    if treffer is not None:
        zitat = treffer.zitat.replace("\n", " ")
        return Quelle(kennung=p.kennung, dokument_id=p.dokument_id, dokument_titel=p.dokument_titel,
                      seite=p.seite, zitat=zitat[:240] + ("…" if len(zitat) > 240 else ""),
                      treffer_start=treffer.start, treffer_ende=treffer.ende,
                      marken=[list(m) for m in treffer.marken])
    zitat = p.text.strip().replace("\n", " ")
    return Quelle(kennung=p.kennung, dokument_id=p.dokument_id, dokument_titel=p.dokument_titel,
                  seite=p.seite, zitat=zitat[:240] + ("…" if len(zitat) > 240 else ""))


def quellen_aus_kennungen(kennungen: list[str], index: dict[str, Passage], hinweise: list[str],
                          aussagen: dict[str, str] | None = None) -> list[Quelle]:
    """``aussagen`` ordnet einer Kennung den Satz zu, der sie zitiert.

    Sie ist optional: Aufrufer, die den Satz nicht kennen (die Eingangsprüfung
    etwa nennt nur die wichtigsten Kennungen), bekommen die Quelle wie bisher.
    """
    ergebnis: list[Quelle] = []
    gesehen: set[str] = set()
    for roh in kennungen:
        kennung = str(roh).strip()
        if kennung in gesehen:
            continue
        gesehen.add(kennung)
        p = index.get(kennung)
        if p is None:
            hinweise.append(f"Beleg {kennung} verweist auf keine mitgelieferte Passage.")
            continue
        ergebnis.append(_quelle(p, (aussagen or {}).get(kennung, "")))
    return ergebnis


def zitate_aufloesen(text: str, index: dict[str, Passage]) -> tuple[str, list[Quelle], list[str]]:
    """Gibt den Text (unbekannte Belege markiert), die Quellen und Hinweise zurück."""
    hinweise: list[str] = []
    gefunden: list[str] = []
    # Der Satz vor dem Beleg ist die Aussage, die er tragen soll. Genau sie
    # brauchen wir, um in der Passage die richtige Stelle zu finden - im
    # Entwurf ist das Nachpruefen die eigentliche Arbeit.
    aussagen: dict[str, str] = {}
    letzte = 0

    def ersetzen(m: re.Match[str]) -> str:
        nonlocal letzte
        aussage = text[letzte:m.start()]
        letzte = m.end()
        kennungen = [k.strip() for k in m.group(1).split(",") if k.strip()]
        gueltig = [k for k in kennungen if k in index]
        for k in kennungen:
            if k not in index:
                hinweise.append(f"Beleg {k} verweist auf keine mitgelieferte Passage.")
        for k in gueltig:
            aussagen.setdefault(k, aussage)
        gefunden.extend(gueltig)
        return f"[Q: {', '.join(gueltig)}]" if gueltig else "[Q: ohne Beleg]"

    neuer_text = ZITAT_RE.sub(ersetzen, text)
    quellen = quellen_aus_kennungen(gefunden, index, [], aussagen)
    if not quellen and ZITAT_RE.search(text) is None:
        hinweise.append("Die Antwort enthält keine Belege.")
    return neuer_text, quellen, hinweise
