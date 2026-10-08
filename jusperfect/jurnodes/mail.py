"""Eine E-Mail in ihren Text und ihre Anhaenge zerlegen.

**Die Vorgabe der Kanzlei vom 08.10.2026, woertlich:** „Text der Mail immer,
Anhänge als eigene Dokumente daneben, jedes einzeln abwählbar wie die Dateien
aus dem Aktenordner."

Damit ist entschieden, was diese Datei zu tun hat. ``POST /mail/download``
liefert eine ``.eml`` - gemessen am 08.10.2026 an zwei Akten, der Server nennt
den Namen selbst (``Content-Disposition: inline; filename="Mail.eml"``). Eine
``.eml`` ist kein Brief, sondern ein Paket: Brieftext, oft derselbe Text noch
einmal als HTML, die Bilder der Signatur, und die eigentlichen Anlagen.

**Warum das Zerlegen hier steht und nicht im Adapter.** Es braucht kein Netz,
keinen Zugang und keine Akte - nur Bytes hinein, Text und Anhaenge heraus. So
laesst es sich mit erfundenen Mails bis in die Ecken pruefen, ohne je eine
echte anzufassen. Der Adapter holt die Bytes, diese Datei versteht sie.

**Was NICHT als Anhang gilt**, und warum das wichtig ist: Die Bilder einer
Signatur sind keine Anlagen. Sie tragen eine ``Content-ID``, mit der das HTML
sie einbindet, und heissen oft ``image001.png``. Kaeme jedes davon als eigenes
Dokument in die Aktenliste, stuenden nach zwanzig Mails achtzig Zeilen
„image001.png" darin, und die eine Anlage, auf die es ankommt, ginge darin
unter.
"""

from __future__ import annotations

import email
import email.policy
from dataclasses import dataclass
from email.header import decode_header, make_header
from email.message import Message
from typing import Iterator

#: Was eine Mail an Text hergibt, wenn sie gar keinen hat.
KEIN_TEXT = "(Diese Nachricht hat keinen lesbaren Text.)"

#: Wie viele Anhaenge eine einzelne Mail hoechstens beisteuert.
#:
#: Keine Begrenzung waere eine offene Tuer: Eine Mail mit zweihundert
#: eingebetteten Bildern wuerde die Dokumentliste der Akte unbrauchbar machen.
#: Was darueber liegt, wird gezaehlt und gemeldet, nicht verschwiegen.
HOECHSTENS_ANHAENGE = 50


@dataclass(frozen=True)
class Anhang:
    """Eine Anlage aus einer E-Mail - mit Namen, Art und Inhalt."""

    name: str
    mime_typ: str
    inhalt: bytes

    @property
    def groesse(self) -> int:
        return len(self.inhalt)


@dataclass(frozen=True)
class Zerlegt:
    """Das Ergebnis: der Brieftext, seine Art, die Anlagen - und was fehlt."""

    text: str
    mime_typ: str
    anhaenge: tuple[Anhang, ...]
    #: Anhaenge, die wegen HOECHSTENS_ANHAENGE nicht uebernommen wurden.
    uebersprungen: int = 0
    #: Eingebettete Bilder (Signatur) - gezaehlt, nicht uebernommen.
    eingebettet: int = 0


def _klartext(wert: object) -> str:
    """Einen Kopfzeilenwert lesbar machen.

    Ein Dateiname in einer Mail steht oft verschluesselt da, etwa
    ``=?utf-8?B?U2NocmlmdHNhdHouxYY=?=``. Wer das ungelesen in eine
    Aktenliste schreibt, zeigt dem Anwalt Buchstabensalat statt
    „Schriftsatz.pdf".
    """
    if wert is None:
        return ""
    try:
        return str(make_header(decode_header(str(wert)))).strip()
    except Exception:
        # Eine kaputte Kopfzeile darf die ganze Mail nicht kosten.
        return str(wert).strip()


def _teile(nachricht: Message, tiefe: int = 0) -> Iterator[tuple[Message, int]]:
    """Alle Teile einer Nachricht - und wie tief verschachtelt jeder liegt.

    ``tiefe`` zaehlt, durch wie viele **weitergeleitete Mails** man gehen
    musste, nicht durch wie viele Hierarchiestufen. Ein ``multipart`` ist nur
    Verpackung derselben Nachricht; ein ``message/rfc822`` ist eine zweite.

    **Warum das unterschieden wird.** Aus einer weitergeleiteten Mail ist die
    **Anlage** wichtig - der Schriftsatz, der dort haengt, gehoert in die
    Akte. Ihr **Text** steht dagegen fast immer schon zitiert im Brieftext der
    aeusseren Mail. Wer beides nimmt, schreibt denselben Absatz zweimal ins
    Aktengedaechtnis, und die Analyse zaehlt ihn als zwei Belege.
    """
    if nachricht.is_multipart():
        for teil in nachricht.get_payload():
            if isinstance(teil, Message):
                art = (teil.get_content_type() or "").lower()
                yield from _teile(teil, tiefe + 1 if art == "message/rfc822" else tiefe)
    else:
        yield nachricht, tiefe


def _ist_anhang(teil: Message) -> bool:
    """Ist dieser Teil eine Anlage - oder gehoert er zum Brieftext?

    Drei Faelle, in dieser Reihenfolge:

    1. **Kein Dateiname** - dann ist es Brieftext, kein Anhang.
    2. **Eine Content-ID und als „inline" bezeichnet** - dann bindet das HTML
       es ein. Das ist die Signatur, nicht die Anlage.
    3. Sonst: Anhang. Auch ein PDF, das der Absender „inline" nennt - manche
       Programme tun das, und ein Schriftsatz bleibt ein Schriftsatz.
    """
    if not teil.get_filename():
        return False
    lage = str(teil.get("Content-Disposition", "")).lower()
    if teil.get("Content-ID") and "inline" in lage:
        return False
    return True


def _text_von(teil: Message) -> str:
    """Den Text eines Teils, ohne an einer falschen Zeichentabelle zu scheitern."""
    try:
        roh = teil.get_payload(decode=True)
    except Exception:
        return ""
    if roh is None:
        return ""
    if isinstance(roh, str):
        return roh
    kodierung = teil.get_content_charset() or "utf-8"
    try:
        return roh.decode(kodierung, errors="replace")
    except (LookupError, ValueError):
        # Eine erfundene Zeichentabelle ("utf8mb4") darf den Text nicht kosten.
        return roh.decode("utf-8", errors="replace")


def zerlegen(roh: bytes) -> Zerlegt:
    """Aus den Bytes einer ``.eml`` den Text und die Anlagen holen.

    **Diese Funktion wirft nicht.** Was sie nicht versteht, meldet sie als
    leeren Text - denn eine unverstaendliche Mail darf nicht die Analyse der
    ganzen Akte kosten. Was sie weglaesst, zaehlt sie.

    Der Text wird bevorzugt als reiner Text genommen; gibt es nur HTML, kommt
    HTML zurueck. Beides liest ``services/extraktion.py`` bereits, und der
    ``mime_typ`` sagt ihr, welches von beidem vorliegt.
    """
    if not roh:
        return Zerlegt(text=KEIN_TEXT, mime_typ="text/plain", anhaenge=())
    try:
        nachricht = email.message_from_bytes(roh, policy=email.policy.compat32)
    except Exception:
        return Zerlegt(text=KEIN_TEXT, mime_typ="text/plain", anhaenge=())

    klartexte: list[str] = []
    htmltexte: list[str] = []
    anhaenge: list[Anhang] = []
    uebersprungen = 0
    eingebettet = 0

    for teil, tiefe in _teile(nachricht):
        art = (teil.get_content_type() or "").lower()
        if _ist_anhang(teil):
            if len(anhaenge) >= HOECHSTENS_ANHAENGE:
                uebersprungen += 1
                continue
            try:
                inhalt = teil.get_payload(decode=True) or b""
            except Exception:
                inhalt = b""
            if not inhalt:
                continue
            name = _klartext(teil.get_filename()) or f"Anlage-{len(anhaenge) + 1}"
            anhaenge.append(Anhang(name=name, mime_typ=art or
                                   "application/octet-stream", inhalt=inhalt))
            continue
        if teil.get_filename() and teil.get("Content-ID"):
            eingebettet += 1
            continue
        if tiefe:
            # Text aus einer weitergeleiteten Mail - siehe _teile.
            continue
        if art == "text/plain":
            klartexte.append(_text_von(teil))
        elif art == "text/html":
            htmltexte.append(_text_von(teil))

    kopf = _kopfzeilen(nachricht)
    if any(t.strip() for t in klartexte):
        rumpf = "\n\n".join(t for t in klartexte if t.strip())
        return Zerlegt(text=kopf + rumpf, mime_typ="text/plain",
                       anhaenge=tuple(anhaenge), uebersprungen=uebersprungen,
                       eingebettet=eingebettet)
    if any(t.strip() for t in htmltexte):
        rumpf = "\n".join(t for t in htmltexte if t.strip())
        # Der Kopf als HTML, damit die Textgewinnung ihn nicht als Markierung
        # missversteht und wegwirft.
        vorsatz = kopf.replace("\n", "<br>\n")
        return Zerlegt(text=f"<p>{vorsatz}</p>\n{rumpf}", mime_typ="text/html",
                       anhaenge=tuple(anhaenge), uebersprungen=uebersprungen,
                       eingebettet=eingebettet)
    return Zerlegt(text=kopf + KEIN_TEXT, mime_typ="text/plain",
                   anhaenge=tuple(anhaenge), uebersprungen=uebersprungen,
                   eingebettet=eingebettet)


def _kopfzeilen(nachricht: Message) -> str:
    """Von, An, Datum, Betreff - vor den Text gesetzt.

    **Warum das mitmuss.** Die Analyse arbeitet mit Belegen: Jede Aussage
    nennt Dokument, Seite und Passage. Bei einem Schriftsatz steht der
    Absender im Briefkopf; bei einer E-Mail steht er nur in den Kopfzeilen,
    und ohne ihn ist aus dem Text nicht zu erkennen, wer was wann geschrieben
    hat. Eine Mail ohne Absender ist als Beleg wertlos.
    """
    zeilen = []
    for name, beschriftung in (("From", "Von"), ("To", "An"), ("Cc", "Kopie"),
                               ("Date", "Datum"), ("Subject", "Betreff")):
        wert = _klartext(nachricht.get(name))
        if wert:
            zeilen.append(f"{beschriftung}: {wert}")
    return ("\n".join(zeilen) + "\n\n") if zeilen else ""
