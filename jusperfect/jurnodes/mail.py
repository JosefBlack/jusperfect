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

---

## Umgebaut am 12.10.2026, Befunde N03 und N04 der dritten Zweitpruefung

Drei Wege, auf denen Akteninhalt lautlos verschwand:

**N03 - der Text einer weitergeleiteten Mail.** Hier stand die Annahme, der
Text einer angehaengten Nachricht stehe schon im Brieftext der aeusseren
zitiert. Geprueft wurde sie nie. Eine Mail mit „Zur Kenntnis" und einer
angehaengten ``message/rfc822`` verlor damit **die ganze uebermittelte
Erklaerung** - und die Anlagenliste war leer, der Verlustzaehler null. Der
Anwalt analysierte eine vermeintlich vollstaendige Mail ohne die Aussage, auf
die es ankam. Jetzt gilt: Jede angehaengte Nachricht kommt mit eigenen
Kopfzeilen und eigenem Text in das Dokument. Weggelassen wird nur, was
**nachweislich** schon im aeusseren Text steht - nicht, was tief liegt.

**N04 - zwei Anlagen, die keine sein durften, und ein Zaehler, der nicht
ankam.** Ein PDF mit ``Content-ID`` und ``inline`` wurde wie ein Signaturbild
aussortiert, ohne dass die Medienart geprueft wurde; manche Programme
bezeichnen jede Anlage so. Ein PDF **ohne Dateinamen** galt als Brieftext,
war aber keiner - es fiel durch beide Zweige und wurde nicht einmal gezaehlt.

Daraus die Lehre fuer diese Datei: **Jeder Teil, der nicht uebernommen wird,
wird mit Grund gezaehlt**, und der Grund geht bis in die Oberflaeche. Ein
Zaehler, den nur der Parser kennt, ist kein Zaehler. ``ausgelassen`` ist die
eine Quelle dafuer; ``uebersprungen`` und ``eingebettet`` lesen daraus, damit
nicht zwei Zaehlungen auseinanderlaufen koennen.
"""

from __future__ import annotations

import email
import email.policy
import html
import mimetypes
import re
from collections import Counter
from dataclasses import dataclass, field
from email.header import decode_header, make_header
from email.message import Message
from typing import Iterator, Mapping

#: Was eine Mail an Text hergibt, wenn sie gar keinen hat.
KEIN_TEXT = "(Diese Nachricht hat keinen lesbaren Text.)"

#: Wie viele Anhaenge eine einzelne Mail hoechstens beisteuert.
#:
#: Keine Begrenzung waere eine offene Tuer: Eine Mail mit zweihundert
#: eingebetteten Bildern wuerde die Dokumentliste der Akte unbrauchbar machen.
#: Was darueber liegt, wird gezaehlt und gemeldet, nicht verschwiegen.
HOECHSTENS_ANHAENGE = 50

#: Wie viele angehaengte Nachrichten eine Mail hoechstens beisteuert.
#: Eine Weiterleitungskette ist in der Kanzlei selten laenger; eine Mail, die
#: sich selbst zweihundertfach enthaelt, ist kein Schriftverkehr.
HOECHSTENS_NACHRICHTEN = 20

#: Ab welcher Laenge der Text einer angehaengten Nachricht als „steht schon
#: oben" gelten darf. Ein „ok" steht in jedem zweiten Brieftext; es doppelt
#: mitzunehmen kostet nichts, es falsch wegzuwerfen kostet eine Aussage.
DOPPELT_AB_ZEICHEN = 25

#: Warum ein Teil einer Mail nicht als Text oder Dokument in die Akte kam.
#:
#: Die Gruende stehen als Text da, weil sie bis in die Oberflaeche
#: durchgereicht werden: Der Bearbeiter soll nicht „3 ausgelassen" lesen,
#: sondern warum.
GRUND_ZU_VIELE = f"mehr als {HOECHSTENS_ANHAENGE} Anlagen"
GRUND_LEER = "Anlage leer oder nicht lesbar"
GRUND_SIGNATURBILD = "eingebettetes Bild (Signatur)"
GRUND_DOPPELT = "Text stand schon in der äußeren Mail"
GRUND_ZU_TIEF = f"mehr als {HOECHSTENS_NACHRICHTEN} angehängte Nachrichten"
GRUND_ANDERER_TEIL = "Teil weder Brieftext noch Anlage"

#: Was ein Signaturbild von einer Anlage unterscheidet, ohne das ein PDF
#: mitaussortiert wuerde (Befund N04): die Medienart.
SIGNATUR_MEDIENART = "image"


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
    #: Was nicht uebernommen wurde: Grund -> Anzahl.
    #:
    #: Die **eine** Quelle fuer alles Ausgelassene (Befund N04). Vorher gab es
    #: zwei Zaehler, und drei Faelle gab es gar nicht.
    ausgelassen: Mapping[str, int] = field(default_factory=dict)
    #: Angehaengte Nachrichten, deren Text mit uebernommen wurde.
    nachrichten: int = 0

    @property
    def uebersprungen(self) -> int:
        """Anlagen, die wegen ``HOECHSTENS_ANHAENGE`` nicht mitkamen."""
        return self.ausgelassen.get(GRUND_ZU_VIELE, 0)

    @property
    def eingebettet(self) -> int:
        """Signaturbilder - gezaehlt, nicht uebernommen, und kein Verlust."""
        return self.ausgelassen.get(GRUND_SIGNATURBILD, 0)

    @property
    def verloren(self) -> int:
        """Was fehlt und fehlen sollte nicht.

        Das Bild einer Signatur ist kein Verlust; alles andere ist einer. Diese
        Zahl ist die, die der Bearbeiter sehen muss - die Signaturbilder
        wuerden sie nur verrauschen.
        """
        return sum(anzahl for grund, anzahl in self.ausgelassen.items()
                   if grund != GRUND_SIGNATURBILD)

    def gruende(self) -> tuple[str, ...]:
        """Die Gruende des Verlusts, mit Anzahl, in Lesereihenfolge."""
        return tuple(f"{anzahl}× {grund}"
                     for grund, anzahl in sorted(self.ausgelassen.items())
                     if grund != GRUND_SIGNATURBILD and anzahl)


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


def _ist_nachricht(teil: Message) -> bool:
    return (teil.get_content_type() or "").lower() == "message/rfc822"


def _innere(teil: Message) -> Message | None:
    """Die Nachricht, die in einem ``message/rfc822``-Teil steckt."""
    try:
        inhalt = teil.get_payload()
    except Exception:
        return None
    if isinstance(inhalt, list):
        for eines in inhalt:
            if isinstance(eines, Message):
                return eines
        return None
    return inhalt if isinstance(inhalt, Message) else None


def _eigene_teile(nachricht: Message) -> Iterator[Message]:
    """Die Teile **dieser** Nachricht - ohne die einer angehaengten.

    Ein ``multipart`` ist nur Verpackung derselben Nachricht und wird
    durchschritten. Ein ``message/rfc822`` ist eine zweite Nachricht; sie
    kommt gesondert, mit eigenen Kopfzeilen (Befund N03).
    """
    if not nachricht.is_multipart():
        yield nachricht
        return
    try:
        teile = nachricht.get_payload()
    except Exception:
        return
    if not isinstance(teile, list):
        return
    for teil in teile:
        if not isinstance(teil, Message) or _ist_nachricht(teil):
            continue
        yield from _eigene_teile(teil)


def _angehaengte_nachrichten(nachricht: Message) -> Iterator[Message]:
    """Jede angehaengte Nachricht, beliebig tief, in Lesereihenfolge."""
    if not nachricht.is_multipart():
        return
    try:
        teile = nachricht.get_payload()
    except Exception:
        return
    if not isinstance(teile, list):
        return
    for teil in teile:
        if not isinstance(teil, Message):
            continue
        if _ist_nachricht(teil):
            innen = _innere(teil)
            if innen is not None:
                yield innen
                yield from _angehaengte_nachrichten(innen)
        else:
            yield from _angehaengte_nachrichten(teil)


def _ist_signaturbild(teil: Message) -> bool:
    """Das eingebundene Bild einer Signatur - und nur das.

    Befund N04: Hier wurde allein auf ``Content-ID`` und ``inline`` gesehen.
    Ein PDF, das der Absender „inline" nennt - manche Programme tun das mit
    **jeder** Anlage -, war damit aussortiert, ohne gezaehlt zu werden. Die
    Medienart entscheidet mit: Ein Schriftsatz ist kein Bild.
    """
    if (teil.get_content_maintype() or "").lower() != SIGNATUR_MEDIENART:
        return False
    if not teil.get("Content-ID"):
        return False
    return "inline" in str(teil.get("Content-Disposition", "")).lower()


def _ist_anhang(teil: Message) -> bool:
    """Ist dieser Teil eine Anlage - oder gehoert er zum Brieftext?

    In dieser Reihenfolge:

    1. **Verpackung** (``multipart``, ``message``) - weder noch.
    2. **Das eingebundene Bild einer Signatur** - keine Anlage, siehe
       ``_ist_signaturbild``.
    3. **Ein Dateiname** - Anlage. Auch ein PDF, das „inline" heisst.
    4. **„attachment" in der Lage** - Anlage, auch ohne Namen.
    5. **Alles, was kein Text ist** - Anlage (Befund N04). Ein PDF ohne
       Dateinamen ist ein PDF; es als Brieftext zu behandeln hiess vorher, es
       lautlos zu verlieren. Es bekommt einen Ersatznamen.
    6. Sonst: Brieftext.
    """
    if (teil.get_content_maintype() or "").lower() in ("multipart", "message"):
        return False
    if _ist_signaturbild(teil):
        return False
    if teil.get_filename():
        return True
    if "attachment" in str(teil.get("Content-Disposition", "")).lower():
        return True
    return (teil.get_content_maintype() or "").lower() != "text"


def _ersatzname(teil: Message, nummer: int) -> str:
    """Ein Name fuer eine Anlage, die keinen mitbringt.

    Mit Endung, soweit die Medienart eine hergibt: ``_art`` in
    ``services/extraktion.py`` sieht zuerst auf den MIME-Typ, aber ein Name
    ohne Endung sieht in der Aktenliste aus wie ein Fehler.
    """
    art = (teil.get_content_type() or "").lower()
    endung = mimetypes.guess_extension(art) or ""
    if endung == ".jpe":        # was mimetypes fuer image/jpeg mitunter sagt
        endung = ".jpg"
    return f"Anlage-{nummer}{endung}"


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


def _lesen(nachricht: Message, anhaenge: list[Anhang],
           ausgelassen: Counter) -> tuple[list[str], list[str]]:
    """Die eigenen Teile einer Nachricht lesen.

    Anlagen wandern in ``anhaenge``, Ausgelassenes mit Grund in
    ``ausgelassen``. Zurueck kommen die Texte - als Klartext und als HTML.
    """
    klartexte: list[str] = []
    htmltexte: list[str] = []
    for teil in _eigene_teile(nachricht):
        art = (teil.get_content_type() or "").lower()
        if _ist_anhang(teil):
            if len(anhaenge) >= HOECHSTENS_ANHAENGE:
                ausgelassen[GRUND_ZU_VIELE] += 1
                continue
            try:
                inhalt = teil.get_payload(decode=True) or b""
            except Exception:
                inhalt = b""
            if not inhalt:
                # Vorher ein stilles `continue`. Eine Anlage, die der Absender
                # geschickt hat und die hier nicht lesbar ist, ist genau der
                # Fall, in dem der Bearbeiter nachfragen muss.
                ausgelassen[GRUND_LEER] += 1
                continue
            name = _klartext(teil.get_filename()) or _ersatzname(teil, len(anhaenge) + 1)
            anhaenge.append(Anhang(name=name,
                                   mime_typ=art or "application/octet-stream",
                                   inhalt=inhalt))
            continue
        if _ist_signaturbild(teil):
            ausgelassen[GRUND_SIGNATURBILD] += 1
            continue
        if art == "text/plain":
            klartexte.append(_text_von(teil))
        elif art == "text/html":
            htmltexte.append(_text_von(teil))
        else:
            # Ein Kalendereintrag, eine Visitenkarte: Text, aber keiner, den
            # diese Datei zu lesen verspricht. Gezaehlt statt verschwiegen.
            ausgelassen[GRUND_ANDERER_TEIL] += 1
    return klartexte, htmltexte


_LEERRAUM = re.compile(r"\s+")


def _vergleichbar(text: str) -> str:
    """Zum Vergleich: ohne Leerraum, ohne Gross- und Kleinschreibung.

    Ein zitierter Absatz steht im aeusseren Text mit „> " davor und anderen
    Umbruechen. Verglichen wird deshalb der Buchstabenbestand.
    """
    return _LEERRAUM.sub(" ", text.replace(">", " ")).strip().lower()


def _steht_schon_da(innen: str, aussen: str) -> bool:
    """Steht der Text der angehaengten Nachricht nachweislich schon oben?

    Befund N03: Vorher wurde das **angenommen** und der Text weggeworfen.
    Angenommen wird hier nichts mehr - verglichen wird. Und bei kurzem Text
    gar nicht: Ein „ok" steht in jedem zweiten Brieftext, und es doppelt
    mitzunehmen kostet nichts, es falsch wegzuwerfen eine Aussage.
    """
    innen = _vergleichbar(innen)
    if len(innen) < DOPPELT_AB_ZEICHEN:
        return False
    return innen in _vergleichbar(aussen)


def _bloecke_bauen(nachricht: Message, anhaenge: list[Anhang],
                   ausgelassen: Counter) -> tuple[list[tuple[str, str]], int]:
    """Die Textbloecke des Dokuments: die Mail selbst, dann die angehaengten.

    Ein Block ist ein Paar aus Medienart (``text/plain`` oder ``text/html``)
    und Inhalt. Welches Format das fertige Dokument hat, entscheidet erst
    ``_zusammensetzen`` - sonst muesste hier geraten werden.
    """
    klartexte, htmltexte = _lesen(nachricht, anhaenge, ausgelassen)
    kopf = _kopfzeilen(nachricht)
    aussen_klar = "\n\n".join(t for t in klartexte if t.strip())
    aussen_html = "\n".join(t for t in htmltexte if t.strip())

    bloecke: list[tuple[str, str]] = []
    if aussen_klar:
        bloecke.append(("text/plain", kopf + aussen_klar))
    elif aussen_html:
        bloecke.append(("text/plain", kopf) if kopf else ("text/html", ""))
        bloecke.append(("text/html", aussen_html))
    else:
        bloecke.append(("text/plain", kopf + KEIN_TEXT))
    bloecke = [(art, inhalt) for art, inhalt in bloecke if inhalt]

    uebernommen = 0
    for nummer, innen in enumerate(_angehaengte_nachrichten(nachricht), start=1):
        if nummer > HOECHSTENS_NACHRICHTEN:
            ausgelassen[GRUND_ZU_TIEF] += 1
            continue
        innen_klar, innen_html = _lesen(innen, anhaenge, ausgelassen)
        rumpf_klar = "\n\n".join(t for t in innen_klar if t.strip())
        rumpf_html = "\n".join(t for t in innen_html if t.strip())
        if not rumpf_klar and not rumpf_html:
            continue
        if rumpf_klar and _steht_schon_da(rumpf_klar, aussen_klar + " " + aussen_html):
            ausgelassen[GRUND_DOPPELT] += 1
            continue
        uebernommen += 1
        trenner = f"── Angehängte Nachricht {uebernommen} ──\n"
        bloecke.append(("text/plain", trenner + _kopfzeilen(innen) + rumpf_klar))
        if rumpf_html and not rumpf_klar:
            bloecke.append(("text/html", rumpf_html))
    return [(art, inhalt) for art, inhalt in bloecke if inhalt.strip()], uebernommen


def _zusammensetzen(bloecke: list[tuple[str, str]]) -> tuple[str, str]:
    """Aus den Bloecken ein Dokument - in **einem** Format.

    Liegt alles als Klartext vor, bleibt es Klartext. Ist ein Block nur als
    HTML da, wird das ganze Dokument HTML, und die Klartextbloecke werden
    maskiert. Das ist auch der Grund, warum die Kopfzeilen nicht mehr roh in
    HTML geschrieben werden: ``html.escape`` laeuft ueber sie, und ein Betreff
    ``<style>`` kann den folgenden Text nicht mehr verschlucken.
    """
    if not bloecke:
        return KEIN_TEXT, "text/plain"
    if all(art == "text/plain" for art, _ in bloecke):
        return "\n\n".join(inhalt for _, inhalt in bloecke), "text/plain"
    teile = []
    for art, inhalt in bloecke:
        teile.append(inhalt if art == "text/html"
                     else f"<pre>{html.escape(inhalt)}</pre>")
    return "\n<hr>\n".join(teile), "text/html"


def zerlegen(roh: bytes) -> Zerlegt:
    """Aus den Bytes einer ``.eml`` den Text und die Anlagen holen.

    **Diese Funktion wirft nicht.** Was sie nicht versteht, meldet sie als
    leeren Text - denn eine unverstaendliche Mail darf nicht die Analyse der
    ganzen Akte kosten. **Was sie weglaesst, zaehlt sie, mit Grund.**

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

    anhaenge: list[Anhang] = []
    ausgelassen: Counter = Counter()
    try:
        bloecke, nachrichten = _bloecke_bauen(nachricht, anhaenge, ausgelassen)
    except Exception:
        # Dieselbe Zusage wie oben: Eine Mail, an der diese Datei scheitert,
        # darf die Akte nicht kosten. Dass etwas fehlt, steht dann da.
        return Zerlegt(text=KEIN_TEXT, mime_typ="text/plain",
                       anhaenge=tuple(anhaenge),
                       ausgelassen={GRUND_ANDERER_TEIL: 1})
    text, mime_typ = _zusammensetzen(bloecke)
    return Zerlegt(text=text, mime_typ=mime_typ, anhaenge=tuple(anhaenge),
                   ausgelassen=dict(ausgelassen), nachrichten=nachrichten)


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
