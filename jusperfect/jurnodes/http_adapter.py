"""Anbindung an die jur|nodes-REST-API.

Die Pfade und Feldnamen der jur|nodes-API sind der wichtigste Prüfpunkt von
Phase 0 (siehe Konzept). Deshalb sind beide hier nicht fest verdrahtet,
sondern in ``Endpunkte`` und den ``_aus_json``-Funktionen an einer Stelle
gesammelt und anpassbar, ohne den Rest des Programms anzufassen.

Das Token kommt aus der Umgebung – der Name der Variablen ist konfigurierbar,
der Wert steht nirgends im Code oder in einer eingecheckten Datei.
"""

from __future__ import annotations

import time
import threading

import json
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from jusperfect.config import Einstellungen, KonfigurationsFehler
from jusperfect.jurnodes.mail import Anhang as MailAnhang
from jusperfect.jurnodes.mail import Zerlegt, zerlegen
from jusperfect.domain.models import Akte, Beteiligter, Dokument, Frist
from jusperfect.jurnodes.base import (GEDAECHTNIS_DATEI, AkteNichtGefunden,
                                       DokumentNichtGefunden, JurNodesFehler,
                                       gedaechtnis_dateiname, gedaechtnis_stand,
                                       ist_gedaechtnis_datei, serverwort)
from jusperfect.security.approval import Freigabe, Freigabestelle


@dataclass(frozen=True)
class Endpunkte:
    """Die Pfade der jur|nodes-Schnittstelle.

    **Seit dem 23.09.2026 sind das keine Annahmen mehr.** Bis dahin stand hier
    ein geratener Satz Pfade (``/akten``, ``/akten/{akte_id}`` und so fort),
    weil der Hersteller die Dokumentation nur auf dem Kundenserver bereitstellt.
    An diesem Tag hat die Kanzlei die OpenAPI-Beschreibung ihres Servers
    geliefert - jur|nodes API 1.0.1 - und die Schnittstelle freischalten lassen.
    Was hier steht, ist von dort abgeschrieben.

    Zwei Dinge sehen anders aus, als geraten worden war, und beide hätten den
    ersten Versuch scheitern lassen:

    * Die Akte wird **nicht** über einen Pfadbestandteil angesprochen, sondern
      über einen Abfrageparameter ``identifier``. Der Identifier ist auch nicht
      das Aktenzeichen - das heißt ``recordSign`` und ist ein eigenes Feld.
    * Die Dokumente hängen nicht an der Akte, sondern am **Dateiordner**: Die
      Akte nennt eine ``fileFolderId``, deren Inhalt man getrennt abfragt.

    Die Einstellbarkeit bleibt trotzdem: Jeder Pfad lässt sich ohne Änderung am
    Programm richtigstellen, über eine kleine Datei, auf die
    JUSPERFECT_JURNODES_ENDPUNKTE zeigt. Eine Beschreibung ist kein laufender
    Server, und wo beide auseinandergehen, gilt der Server.
    """

    akten_suche: str = "/record/search"              # GET ?sign=&shortRubrum=&page=
    akte: str = "/record"                            # GET ?identifier=
    ordner_inhalt: str = "/file-system/folder/content"   # GET ?folderId=&page=
    datei_download: str = "/file-system/file/download"   # GET ?identifier= (Binärdaten)
    beteiligte: str = "/relation/search"             # GET
    fristen: str = "/todo/search"                    # GET
    vermerke: str = "/record/note"                   # POST {model: RecordNote}
    datei_hinzufuegen: str = "/file-system/add-file"  # POST (multipart)
    # Die E-Akte. Seit dem 05.10.2026 belegt, nicht geraten: Die Kanzlei hat
    # die Beschreibung des Herstellers geliefert (Fassung 1.0.2, 85 Pfade),
    # sie liegt unter schnittstelle/jurnodes-api-1.0.2.json.
    #
    # Sie heisst dort "Korrespondenz" und umfasst Mails, beA, Post, Fax, SMS,
    # Dateien - und VERMERKE. Ein eigener Ordnerbaum mit eigenen Nummern,
    # getrennt vom Dateisystem; genau das war der Fehler vom 02.10.2026.
    korrespondenz_suche: str = "/correspondence/search"   # POST {recordIdentifier, page}
    korrespondenz: str = "/correspondence"                # GET ?identifier=
    korrespondenz_ordner: str = "/correspondence/folder"  # GET ?id=
    #: Die abgelegte Fassung einer E-Mail. POST {mailIdentifier} -> .eml
    #:
    #: Gemessen am 08.10.2026 an zwei Akten: Status 200, Content-Type
    #: application/octet-stream, und der Server nennt den Namen selbst -
    #: Content-Disposition: inline; filename="Mail.eml".
    #:
    #: Das ist ein Aufruf an jur|nodes und holt die DORT abgelegte Fassung.
    #: Kein Postfachzugriff - Vorgabe der Kanzlei vom 07.10.2026.
    mail_download: str = "/mail/download"                 # POST {mailIdentifier}

    #: Die Abfrageparameter. Auch sie stehen in der Beschreibung des Herstellers.
    suchparameter: str = "sign"           # Suche nach Aktenzeichen
    rubrumparameter: str = "shortRubrum"  # Suche nach Kurzrubrum
    kennungparameter: str = "identifier"  # Die Akte bzw. die Datei selbst
    ordnerparameter: str = "folderId"     # Der Dateiordner einer Akte
    akteparameter: str = "recordIdentifier"   # Beziehungen und Fristen einer Akte
    fristenart: str = "frist"             # /todo/search kennt auch task und resubmit
    #: GET /record/note braucht ZWEI Pflichtparameter, nicht einen. Daran ist
    #: die Suche nach den Vermerken vier Wochen lang gescheitert: Zwanzig
    #: Parameternamen wurden probiert, jeder mit EINEM Wert, und der Server
    #: antwortete jedes Mal "Bitte Daten angeben". Das war woertlich zu
    #: nehmen - es fehlten Daten, nicht der richtige Name.
    vermerkparameter: str = "id"          # die Nummer des Vermerks
    vermerkakteparameter: str = "record"  # der Identifier der Akte, zusaetzlich

    @classmethod
    def aus_datei(cls, pfad: "Path | str | None") -> "Endpunkte":
        """Die Pfade aus einer JSON-Datei, soweit sie darin stehen.

        Fehlt die Datei oder der Eintrag, gilt die Vorgabe. So lässt sich ein
        einzelner Pfad richtigstellen, ohne die übrigen abzuschreiben.
        """
        if not pfad:
            return cls()
        datei = Path(pfad)
        if not datei.is_file():
            raise KonfigurationsFehler(
                f"Die Datei mit den jur|nodes-Pfaden fehlt: {datei}")
        try:
            daten = json.loads(datei.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as fehler:
            raise KonfigurationsFehler(
                f"Die Datei mit den jur|nodes-Pfaden ist unlesbar ({datei}): {fehler}") from fehler
        if not isinstance(daten, Mapping):
            raise KonfigurationsFehler(
                f"Die Datei mit den jur|nodes-Pfaden muss ein JSON-Objekt sein: {datei}")
        # Zeilen, die mit einem Unterstrich anfangen, sind Erklaerung und kein
        # Pfad. Eine Datei, die ein Nichtprogrammierer bearbeiten soll, muss
        # ihre Anleitung bei sich tragen duerfen - sonst steht sie woanders und
        # wird nicht gefunden. Dasselbe haelt es nutzer-kanzlei.json.
        daten = {k: v for k, v in daten.items() if not k.startswith("_")}
        bekannt = {f.name for f in fields(cls)}
        fremd = sorted(set(daten) - bekannt)
        if fremd:
            raise KonfigurationsFehler(
                f"Unbekannte Einträge in {datei}: {', '.join(fremd)}. "
                f"Erlaubt sind: {', '.join(sorted(bekannt))}.")
        falsch = sorted(k for k, v in daten.items() if not isinstance(v, str) or not v.strip())
        if falsch:
            raise KonfigurationsFehler(
                f"Diese Einträge in {datei} sind keine brauchbaren Pfade: {', '.join(falsch)}.")
        return cls(**{k: v.strip() for k, v in daten.items()})


def _erstes(daten: Mapping[str, Any], *namen: str, standard: Any = "") -> Any:
    for name in namen:
        if name in daten and daten[name] is not None:
            return daten[name]
    return standard


def _datum(wert: Any) -> date | None:
    if not wert:
        return None
    try:
        return date.fromisoformat(str(wert)[:10])
    except ValueError:
        return None


#: Der Aktenstatus, wie jur|nodes ihn nennt, auf den von jusperfect.
#: jusperfect kennt drei: "laufend", "archiviert", "unbekannt". Alles, was
#: nicht eindeutig nach Archiv aussieht, gilt als laufend - und eine laufende
#: Akte wird nie geloescht. Das ist die sichere Seite.
#: Die Woerter, die jur|nodes im Aktenstatus fuehrt - gemessen, nicht geraten.
#:
#: Am 02.10.2026 hat die Probe 300 Akten des Bestands angesehen: 290 tragen
#: "archived", 10 "active". Mehr gibt es nicht.
#:
#: Bis dahin kannte diese Tabelle nur die beiden Archivwoerter, und JEDES
#: andere Wort wurde still zu "laufend". Fuer "active" war das zufaellig
#: richtig - und fuer ein drittes Wort, das der Hersteller morgen einfuehrt,
#: waere es falsch: Eine abgeschlossene Akte saehe aus wie eine laufende, die
#: Aufbewahrung liefe nie an, und niemand bekaeme es zu sehen.
#:
#: Deshalb steht hier jetzt beides, und alles Uebrige wird "unbekannt" -
#: woraufhin services/aufsicht.py einen Menschen einschaltet, statt zu raten.
#: Das Netz, das dafuer gebaut war, konnte vorher gar nicht ausloesen.
_STATUS = {
    "archiviert": "archiviert", "archived": "archiviert",
    "active": "laufend", "aktiv": "laufend",
    "open": "laufend", "offen": "laufend", "laufend": "laufend",
}


def _status_uebersetzen(wert: Any) -> str:
    """Das Wort von jur|nodes in eines der drei Woerter des Programms.

    "unbekannt" ist kein Fehler, sondern eine Vorlage zur Entscheidung: Es
    wird dann nichts geloescht, und die Aufsicht zeigt die Akte an.
    """
    return _STATUS.get(str(wert or "").strip().lower(), "unbekannt")


def akte_aus_json(d: Mapping[str, Any]) -> Akte:
    """Eine Akte aus der Antwort von ``/record`` oder ``/record/search``.

    Die Feldnamen stehen seit dem 23.09.2026 fest (jur|nodes API 1.0.1):
    ``identifier`` ist der Schluessel, ``recordSign`` das Aktenzeichen,
    ``shortRubrum`` das Kurzrubrum - und damit das, was die Kanzlei lesen
    will. Ueber das eingebundene Laufwerk gibt es das Kurzrubrum nicht; im
    Ordnernamen steht nur das Aktenzeichen. Das ist der sichtbarste Gewinn
    dieser Anbindung.

    Die frueher geratenen deutschen Namen bleiben als zweite Wahl stehen. Sie
    kosten nichts und fangen einen Server, der anders antwortet als seine
    eigene Beschreibung.
    """
    return Akte(
        id=str(_erstes(d, "identifier", "id", "aktenId", "akte_id")),
        aktenzeichen=str(_erstes(d, "recordSign", "sign", "aktenzeichen", "az", "nummer")),
        bezeichnung=str(_erstes(d, "shortRubrum", "bezeichnung", "kurzbezeichnung", "titel", "name")),
        rechtsgebiet=str(_erstes(d, "lawCategory", "rechtsgebiet", "sachgebiet")),
        sachbearbeiter=str(_erstes(d, "sachbearbeiter", "bearbeiter")),
        status=_status_uebersetzen(_erstes(d, "recordStatus", "status", standard="")),
    )


def _identitaet_pruefen(angefragt: str, daten: Mapping[str, Any]) -> None:
    """Die zurückgegebene Akte muss die angefragte sein.

    Befund F08 der Zweitprüfung vom 05.10.2026. Der Client fragte
    ``EIGENE-AKTE`` ab; die Antwort trug ausdrücklich ``identifier:
    FREMDE-AKTE`` samt deren ``fileFolderId``. Geprüft wurde nichts: Die
    Ordnerdatei wurde geladen, und ``dokument_aus_json`` trug dabei die
    **angefragte** eigene Akte ein. Fremder Inhalt stand damit unter der
    richtigen Aktennummer, und jede spätere Prüfung sah eine in sich
    stimmige Liste.

    Das ist nicht derselbe Fall wie der Korrespondenzordner vom 02.10.2026 –
    dort lag unser eigener Fehler, weil zwei Nummernkreise verwechselt
    wurden. Hier geht es um die Antwort selbst.

    **Was diese Prüfung nicht kann:** Ein Server, der eine falsche
    Zugehörigkeit durchweg stimmig ausgibt, lässt sich damit nicht entlarven.
    Sie fängt die Antwort, die sich selbst widerspricht – und das ist der Fall,
    der sich am Client überhaupt erkennen lässt.

    Fehlt die Kennung ganz, bricht sie ebenfalls ab. Eine Aktenantwort ohne
    Kennung ist nach der Beschreibung des Herstellers (API 1.0.2) keine; ihr
    stillschweigend zu glauben hieße, die Prüfung auf Zuruf abzuschalten.
    """
    zurueck = str(_erstes(daten, "identifier", "id", "aktenId", "akte_id", standard="")).strip()
    if zurueck and zurueck.casefold() == str(angefragt).strip().casefold():
        return
    # Die fremde Kennung geht NICHT in die Meldung: Sie gehoert zu einer
    # anderen Akte, und eine fremde Aktenkennung ist Mandantengeheimnis.
    raise JurNodesFehler(
        "jur|nodes hat auf die Anfrage nach dieser Akte eine andere Akte "
        "geantwortet" + ("" if zurueck else " – die Antwort trug überhaupt keine "
                         "Aktenkennung") + ". Der Vorgang wurde abgebrochen; es "
        "wurde nichts geladen. Bitte die Kanzleiverwaltung verständigen.")


#: Woran eine Vermerkkennung zu erkennen ist.
#:
#: Die Vermerke zaehlen in jur|nodes in einem EIGENEN Nummernkreis: Ein
#: Vermerk 17 und eine Datei 17 haben nichts miteinander zu tun. Ohne diesen
#: Vorsatz waere das Laden eine Verwechslung, die niemandem auffiele - genau
#: die Art Fehler, die am 02.10.2026 fremde Schriftstuecke in eine Bausache
#: gebracht hat.
VERMERK_VORSATZ = "vermerk:"

#: Unter welchem Namen die E-Akte im Dokumentfenster steht.
#:
#: Mails, ihre Anlagen und Vermerke kommen aus dem Korrespondenzbaum, nicht
#: aus dem Dateiordner. Sie dort einzureihen hiesse, zwei Baeume zu einem zu
#: machen - und genau diese Verwechslung hat am 02.10.2026 drei fremde
#: Schriftstuecke in eine Bausache gebracht.
EAKTE_ORDNER = "E-Akte"

#: Wie ein Vermerk heisst, wenn er keinen Betreff traegt.
#:
#: Aus der Huelle kommt immer "note" - ob es eine Telefonnotiz ist, steht erst
#: im Vermerk selbst (``RecordNote.type``), und der wird fuer die Liste nicht
#: geladen. Hundert Vermerke zu laden, um drei anzuhaken, waeren hundert
#: Anfragen fuer nichts. In der Liste heisst deshalb jeder "Vermerk"; die
#: Unterscheidung steht dem offen, der ihn uebernimmt.
_VERMERKARTEN = {"phonecall": "Telefonnotiz", "note": "Vermerk"}


def vermerk_als_dokument(akte_id: str, nummer: Any, huelle: Mapping[str, Any]) -> Dokument:
    """Aus einem Korrespondenzeintrag der Art „note" ein Dokument machen.

    Der Betreff und das Datum stehen in der Huelle; der Inhalt wird erst beim
    Laden geholt (``GET /record/note``). Die Endung entscheidet, womit die
    Texterkennung ihn liest - der Hersteller fuehrt ``contentType`` html oder
    text, und beides kann ``services/extraktion.py`` bereits.

    Weil die Huelle den ``contentType`` nicht nennt, steht hier ``.html``:
    Ein HTML-Leser kommt mit reinem Text zurecht, umgekehrt stuenden die
    Markierungen im Aktentext.
    """
    betreff = str(_erstes(huelle, "subject", "betreff", standard="")).strip()
    art = _VERMERKARTEN.get(str(huelle.get("type", "")).lower(), "Vermerk")
    return Dokument(
        id=f"{VERMERK_VORSATZ}{nummer}",
        akte_id=akte_id,
        titel=betreff or f"{art} {nummer}",
        dateiname=f"vermerk-{nummer}.html",
        mime_typ="text/html",
        datum=_datum(_erstes(huelle, "created", "postmark", standard=None)),
        kategorie=art,
        ordner=EAKTE_ORDNER,
    )


#: Kennung eines Mail-Dokuments: "mail:<mailIdentifier>".
MAIL_VORSATZ = "mail:"

#: Was die Mail von ihrer Anlage trennt: "mail:<kennung>::3".
#:
#: Zwei Doppelpunkte, weil der mailIdentifier des Herstellers eine
#: Zeichenkette ist und einen einzelnen tragen koennte.
ANHANG_TRENNER = "::"


#: Was ``isInbox`` bedeutet - Wortlaut des Herstellers.
#:
#: ``CorrespondenceModel.isInbox`` in ``jurnodes-api-1.0.2.json``:
#: *„1 = Eingang, 0 = Ausgang, -1 = Neutral/Unbekannt"*. Gleichlautend im
#: Schreibschema ``Correspondence``.
#:
#: **Der dritte Wert ist der Grund, warum hier eine Tabelle steht und kein
#: ``if``.** Die Vermutung bis zum 11.10.2026 lautete „1 heisst eingegangen,
#: 0 ausgegangen" - richtig, aber unvollstaendig. Wer das Feld als Ja/Nein
#: liest, schreibt ueber jedes neutrale Schreiben „Ausgang".
_ISINBOX = {1: "Eingang", 0: "Ausgang", -1: ""}


def _richtung(huelle: Mapping[str, Any]) -> str:
    """Die Kategorie einer Mail, mit der Richtung, soweit sie feststeht.

    Gibt „E-Mail (Eingang)", „E-Mail (Ausgang)" oder - bei ``-1``, bei einem
    fehlenden und bei einem unbekannten Wert - „E-Mail" ohne Zusatz zurueck.

    **Was hier bewusst nicht geschieht: raten.** Ein falsch herum
    beschriftetes Schreiben in einer Handakte ist teurer als ein gar nicht
    beschriftetes. Jeder Wert ausser 1, 0 und -1 waere ein Wert, den der
    Hersteller nicht beschrieben hat; er fuehrt deshalb auf denselben Weg wie
    -1, naemlich auf keine Angabe.
    """
    roh = huelle.get("isInbox")
    try:
        richtung = _ISINBOX.get(int(roh))        # auch "1" aus einer JSON-Zeichenkette
    except (TypeError, ValueError):
        richtung = None
    return f"E-Mail ({richtung})" if richtung else "E-Mail"


#: Woran der Bearbeiter sieht, dass von dieser Mail nur die Huelle da ist.
#:
#: **Vorgabe der Kanzlei vom 08.10.2026:** „Obergrenze sollte festgelegt
#: werden, bei Überschreitung sollte der Bearbeiter gewarnt werden und
#: aufmerksam gemacht werden."
#:
#: Eine Zahl in einer Fusszeile ist keine Warnung - sie wird uebersehen.
#: Deshalb steht es in der **Zeile selbst**, dort, wo der Bearbeiter den
#: Haken setzt oder nicht.
#:
#: Zweiter Wert ist der kurze Grund fuer die Kategorie. Die **Richtung steht
#: davor** und faellt hier nicht weg: Wenn der Inhalt fehlt, ist sie das
#: Einzige, woran der Bearbeiter das Schreiben noch einordnen kann.
MAIL_OHNE_INHALT = {
    "zu_gross": ("⚠ Inhalt nicht geladen: zu groß", "zu groß"),
    "budget": ("⚠ Inhalt nicht geladen: Gesamtmaß der Akte erreicht", "Gesamtmaß"),
    "status": ("⚠ Inhalt nicht geladen: jur|nodes hat ihn nicht herausgegeben", "abgewiesen"),
    "netz": ("⚠ Inhalt nicht geladen: die Schnittstelle war nicht erreichbar", "kein Netz"),
}


def mail_als_dokument(akte_id: str, kennung: str, huelle: Mapping[str, Any],
                      mime_typ: str = "text/plain", grund: str = "",
                      verlust: tuple[str, ...] = ()) -> Dokument:
    """Aus einem Korrespondenzeintrag der Art „mail" ein Dokument machen.

    Der Betreff und der Poststempel stehen in der Huelle; der Text kommt aus
    der ``.eml``, die ``POST /mail/download`` liefert (gemessen am
    08.10.2026: Status 200, ``Content-Disposition: filename="Mail.eml"``).

    ``grund`` ist gesetzt, wenn der Inhalt **nicht** geholt werden konnte.
    Die Mail bleibt dann in der Liste - mit Betreff, Datum und einer Warnung
    im Titel. Sie verschwinden zu lassen waere das Schlimmere: Was fehlt,
    faellt nur auf, wenn es dasteht.

    ``verlust`` steht fuer das Umgekehrte: Der Inhalt **ist** da, aber beim
    Zerlegen kam nicht alles mit - eine Anlage ohne lesbaren Inhalt, mehr als
    fuenfzig Anlagen, ein Teil, der weder Brieftext noch Anlage war. Befund
    N04 der dritten Zweitpruefung vom 12.10.2026: Diese Zahlen kannte der
    Parser und niemand sonst. Jetzt stehen sie in der Zeile der Mail, denn
    dort sucht man sie, wenn eine Anlage fehlt.
    """
    betreff = str(_erstes(huelle, "subject", "betreff", standard="")).strip()
    endung = "txt" if mime_typ == "text/plain" else "html"
    titel = betreff or "E-Mail ohne Betreff"
    kategorie = _richtung(huelle)
    if grund:
        warnung, kurz = MAIL_OHNE_INHALT.get(
            grund, (f"⚠ Inhalt nicht geladen ({grund})", grund))
        kategorie = f"{kategorie} – Inhalt fehlt ({kurz})"
        titel = f"{titel}  [{warnung}]"
    elif verlust:
        titel = f"{titel}  [⚠ nicht alles übernommen: {', '.join(verlust)}]"
        kategorie = f"{kategorie} – unvollständig"
    return Dokument(
        id=f"{MAIL_VORSATZ}{kennung}",
        akte_id=akte_id,
        titel=titel,
        dateiname=f"mail-{_dateiname_teil(kennung)}.{endung}",
        mime_typ=mime_typ,
        datum=_datum(_erstes(huelle, "postmark", "created", standard=None)),
        kategorie=kategorie,
        ordner=EAKTE_ORDNER,
    )


def anhang_als_dokument(akte_id: str, kennung: str, nummer: int,
                        anhang: "MailAnhang",
                        huelle: Mapping[str, Any]) -> Dokument:
    """Eine Anlage einer E-Mail als eigenes Dokument.

    **Vorgabe der Kanzlei vom 08.10.2026:** „Anhänge als eigene Dokumente
    daneben, jedes einzeln abwählbar wie die Dateien aus dem Aktenordner."
    Genau das heisst eigenes Dokument: eigene Kennung, eigener Haken, eigene
    Zeile in der Liste.

    Der Titel traegt den Dateinamen und dahinter den Betreff der Mail. Ohne
    ihn stuenden in der Liste drei Zeilen „Anlage 1.pdf" nebeneinander, und
    keine sagte, wozu sie gehoert.
    """
    betreff = str(_erstes(huelle, "subject", "betreff", standard="")).strip()
    titel = anhang.name
    if betreff:
        titel = f"{anhang.name} (aus: {betreff})"
    # Die Anlage erbt die Richtung ihrer Mail: Sie ist mit ihr gekommen oder
    # mit ihr hinausgegangen. Wer "alles, was eingegangen ist" anhakt, meint
    # die Anlagen mit.
    richtung = _richtung(huelle).removeprefix("E-Mail")
    return Dokument(
        id=f"{MAIL_VORSATZ}{kennung}{ANHANG_TRENNER}{nummer}",
        akte_id=akte_id,
        titel=titel,
        dateiname=anhang.name,
        mime_typ=anhang.mime_typ,
        datum=_datum(_erstes(huelle, "postmark", "created", standard=None)),
        kategorie=f"Anlage zur E-Mail{richtung}",
        ordner=EAKTE_ORDNER,
    )


def _dateiname_teil(kennung: str) -> str:
    """Aus einer Kennung etwas machen, das als Dateiname taugt."""
    sauber = "".join(z if z.isalnum() or z in "-_" else "-" for z in str(kennung))
    return sauber[:40] or "ohne-kennung"


#: Wie der Ordner heisst, wenn der Hersteller keinen Namen mitgibt.
#:
#: Dann steht die Nummer da. Ein Ordner ohne Bezeichnung ist unschoen, ein
#: Ordner, der mit anderen namenlosen zu einem Haufen verschmilzt, ist falsch:
#: Zwei Register der Akte saehen aus wie eines.
def _ordnerpfad(bisher: str, ordner: Mapping[str, Any], nummer: Any) -> str:
    """Den Pfad eines Unterordners aus dem seines Elternordners bilden."""
    name = str(_erstes(ordner, "folderName", "name", "bezeichnung",
                       standard="")).strip()
    if not name:
        name = f"Ordner {nummer}"
    # Ein "/" im Namen wuerde eine Ebene vortaeuschen, die es nicht gibt.
    name = name.replace("/", "-")
    return f"{bisher}/{name}" if bisher else name


def dokument_aus_json(akte_id: str, d: Mapping[str, Any],
                      ordner: str = "") -> Dokument:
    """Ein Dokument aus einem ``file``-Eintrag von ``/file-system/folder/content``.

    jur|nodes fuehrt Namen und Endung getrennt (``fileName`` ohne, ``fileExtension``
    daneben). Fuer jusperfect ist der Dateiname der zusammengesetzte - daran
    haengt die Erkennung, was sich auslesen laesst und was nicht.
    """
    name = str(_erstes(d, "fileName", "dateiname", "filename", "datei"))
    endung = str(_erstes(d, "fileExtension", standard="")).lstrip(".")
    dateiname = f"{name}.{endung}" if endung and not name.lower().endswith("." + endung.lower()) else name
    return Dokument(
        id=str(_erstes(d, "identifier", "id", "dokumentId", "dokument_id")),
        akte_id=akte_id,
        titel=str(_erstes(d, "titel", "bezeichnung", "name", standard=name)) or name,
        dateiname=dateiname,
        mime_typ=str(_erstes(d, "mime_typ", "mimeType", "contentType", standard="application/octet-stream")),
        datum=_datum(_erstes(d, "addedDate", "datum", "erstelltAm", "date", standard=None)),
        kategorie=str(_erstes(d, "kategorie", "typ", "art")),
        ordner=ordner,
        groesse_bytes=_erstes(d, "size", "groesse_bytes", "groesse", standard=None),
    )


def beteiligter_aus_json(d: Mapping[str, Any]) -> Beteiligter:
    return Beteiligter(
        id=str(_erstes(d, "id", "beteiligterId")),
        name=str(_erstes(d, "name", "bezeichnung")),
        rolle=str(_erstes(d, "rolle", "beteiligungsart", "typ")),
        organisation=str(_erstes(d, "organisation", "firma")),
        kontakt=str(_erstes(d, "kontakt", "email")),
    )


def frist_aus_json(d: Mapping[str, Any]) -> Frist:
    return Frist(
        id=str(_erstes(d, "id", "fristId")),
        bezeichnung=str(_erstes(d, "bezeichnung", "titel", "art")),
        datum=_datum(_erstes(d, "datum", "faelligAm", "ablauf")) or date.min,
        status=str(_erstes(d, "status", standard="offen")),
    )


#: Welcher Pfad zu welchem Bereich gehoert.
#:
#: jur|nodes vergibt die Zugaenge NICHT als einen Schluessel mit mehreren
#: Haken, sondern je Bereich einen eigenen - mit eigenen Unterrechten (read,
#: search, write). Auskunft der Kanzlei vom 23.09.2026.
#:
#: Fuer jusperfect heisst das: Der Schluessel haengt an der Frage, nicht an der
#: Verbindung. Eine Anfrage nach den Dokumenten braucht den Schluessel des
#: Dateisystems, eine nach der Akte den der Akten. Wer nur einen hinterlegt,
#: bekommt bei den uebrigen eine Ablehnung - und die sieht aus wie ein
#: falscher Schluessel, nicht wie ein fehlender.
#:
#: Die Reihenfolge zaehlt: Der erste passende Anfang gewinnt. "/record/note"
#: steht deshalb nicht eigens da - es gehoert zu den Akten.
BEREICHE: tuple[tuple[str, str], ...] = (
    ("/file-system", "dateisystem"),
    ("/file-upload", "dateisystem"),
    ("/relation", "beziehungen"),
    ("/todo", "todo"),
    ("/config", "konfiguration"),
    ("/record", "akten"),
)


#: Bei welcher Zahl die Seitenzaehlung anfaengt: ueberall bei 1.
#:
#: **Hier stand eine 0 fuer /record/search und /todo/search**, weil die
#: Beschreibung des Herstellers das sagt. Der Server der Kanzlei sagt etwas
#: anderes, und zwar in ganzen Worten. Gemessen am 28.09.2026 mit
#: JURNODES-PRUEFEN.bat, Akte X-100-2026:
#:
#:     mit Platzhalter, ohne Seitenangabe: 1 Eintrag, amountTotal 1
#:     mit Platzhalter und page=0:         Status 405
#:        Der Server sagt dazu: Bitte geben Sie eine Seitenzahl > 0 an
#:     mit Platzhalter und page=1:         1 Eintrag, amountTotal 1
#:
#: Wenn 0 keine gueltige Seite ist, dann ist 1 die erste. Damit war die 0 hier
#: ein stiller Verlust: Die erste Anfrage geht ohne "page" hinaus und bringt
#: Seite 1; die Schleife zaehlte dann von 0 auf 1 weiter und holte **Seite 1
#: noch einmal**. Seite 2 wurde nie geholt, und ``gelesen`` zaehlte die
#: Doppelung als zweite Seite - der Adapter hielt die Akte fuer vollstaendig.
#:
#: Bei einer Aktensuche mit mehr als einer Seite fehlte damit alles ab der
#: zweiten. Zum dritten Mal dieselbe Form: **Was nicht da ist, faellt nicht
#: auf** - nach dem doppelt vergebenen Aktenzeichen und den Dokumenten, die
#: das schwache Modell beim Einlesen weggelassen hat.
#:
#: Im Zweifel gilt der Server, nicht seine Beschreibung. Dieselbe Entscheidung
#: wie bei der ersten Anfrage ohne Seitenangabe, und aus demselben Grund.
ERSTE_SEITE: tuple[tuple[str, int], ...] = (
    ("/file-system", 1),
    ("/relation", 1),
    ("/record/search", 1),
    ("/todo", 1),
)

#: Notbremse gegen eine Antwort, die immer weiter zaehlt. 500 Seiten sind bei
#: 50 je Seite 25.000 Eintraege - mehr hat keine Akte und keine Kanzlei.
SEITEN_GRENZE = 500


def erste_seite(pfad: str) -> int:
    for anfang, nummer in ERSTE_SEITE:
        if pfad.startswith(anfang):
            return nummer
    return 1


def bereich_von(pfad: str) -> str:
    """Zu welchem Bereich gehoert dieser Pfad? Leer, wenn keiner passt."""
    for anfang, name in BEREICHE:
        if pfad.startswith(anfang):
            return name
    return ""


class HttpJurNodesAdapter:
    def __init__(
        self,
        basis_url: str,
        token: str,
        freigabestelle: Freigabestelle,
        endpunkte: Endpunkte = Endpunkte(),
        timeout_sekunden: float = 30.0,
        transport: httpx.BaseTransport | None = None,
        benutzer: str = "",
        schluessel: "Mapping[str, str] | None" = None,
        korrespondenz: bool = False,
        mail_grenze_mb: int = 20,
        mail_gesamt_mb: int = 100,
    ) -> None:
        if not basis_url.startswith("https://") and not basis_url.startswith("http://localhost") \
                and not basis_url.startswith("http://127.0.0.1"):
            raise KonfigurationsFehler("Die jur|nodes-URL muss mit https:// beginnen.")
        if not token:
            raise KonfigurationsFehler("Kein jur|nodes-Schlüssel vorhanden.")
        self._endpunkte = endpunkte
        self._freigabestelle = freigabestelle
        self._korrespondenz = korrespondenz
        # Zwei Kopfzeilen, nicht ein Bearer-Token (jur|nodes API 1.0.1). Hier
        # stand bis zum 23.09.2026 "Authorization: Bearer ..." - die
        # naheliegende Annahme, und die falsche. Ein Zugang, der abgelehnt
        # wird, sieht aus wie ein falscher Schluessel; gesucht haette man dann
        # beim Hersteller statt im eigenen Quelltext.
        # Ein Schluessel je Bereich, mit dem allgemeinen als Rueckfall. Wer
        # nur einen hat, gibt ihn als token an und ist fertig; wer je Bereich
        # einen bekommt, traegt sie in schluessel ein.
        self._schluessel = dict(schluessel or {})
        self._grundschluessel = token
        #: (Akte, Zeitpunkt, Liste) - siehe LISTE_GILT_SEKUNDEN.
        self._liste_puffer: tuple[str, float, list[Dokument]] = ("", 0.0, [])
        #: Akten und Ordnerinhalte, kurz gehalten - siehe PUFFER_SEKUNDEN.
        self._kurzpuffer: dict[tuple[str, str], tuple[float, Any]] = {}
        #: Die zerlegten Mails dieser Akte, nach mailIdentifier.
        #:
        #: Eine Mail wird EINMAL geholt. Aus derselben ``.eml`` kommen der
        #: Brieftext und jede Anlage; sie ein zweites Mal zu holen, waere ein
        #: zweiter Aufruf fuer dasselbe Paket. Begrenzt durch
        #: ``mail_grenze_bytes`` je Mail und ``mail_gesamt_bytes`` je Akte.
        self._mails: dict[str, Zerlegt] = {}
        self._mails_akte: str = ""
        self._mail_grenze = int(mail_grenze_mb) * 1024 * 1024
        self._mail_gesamt = int(mail_gesamt_mb) * 1024 * 1024
        self._client = httpx.Client(
            base_url=basis_url.rstrip("/"),
            headers={"X-Auth-User": benutzer, "Accept": "application/json"},
            timeout=timeout_sekunden,
            transport=transport,
        )
        # Der Hersteller laesst je IP-Adresse GENAU EINE Anfrage zugleich zu
        # (Auskunft vom 23.09.2026, dazu hoechstens 100 je Sekunde). Eine
        # zweite Anfrage waehrend einer laufenden wird abgewiesen - und ein
        # Einlesen von fuenfzig Dokumenten besteht aus fuenfzig Anfragen. Die
        # Sperre hier ist deshalb kein Beiwerk, sondern die Bedingung dafuer,
        # dass die Anbindung unter Last nicht auseinanderfaellt. Sie gilt fuer
        # jede Anfrage, auch die schreibende.
        self._nacheinander = threading.Lock()

    @classmethod
    def aus_einstellungen(
        cls, einstellungen: Einstellungen, freigabestelle: Freigabestelle, token: str,
        transport: httpx.BaseTransport | None = None, benutzer: str = "",
        schluessel: "Mapping[str, str] | None" = None,
    ) -> "HttpJurNodesAdapter":
        if not einstellungen.jurnodes_url:
            raise KonfigurationsFehler("JUSPERFECT_JURNODES_URL ist nicht gesetzt.")
        return cls(
            einstellungen.jurnodes_url, token, freigabestelle,
            endpunkte=Endpunkte.aus_datei(einstellungen.jurnodes_endpunkte_datei),
            timeout_sekunden=einstellungen.jurnodes_timeout_sekunden, transport=transport,
            benutzer=benutzer, schluessel=schluessel,
            korrespondenz=einstellungen.korrespondenz,
            mail_grenze_mb=einstellungen.mail_grenze_mb,
            mail_gesamt_mb=einstellungen.mail_gesamt_mb,
        )

    # ── Hilfen ─────────────────────────────────────────────────────────────

    def _kopf(self, pfad: str) -> dict[str, str]:
        """Der Schluessel, der zu diesem Pfad gehoert."""
        bereich = bereich_von(pfad)
        return {"X-Auth-Key": self._schluessel.get(bereich, self._grundschluessel)}

    def _get(self, pfad: str, nicht_gefunden: type[JurNodesFehler], **params: Any) -> httpx.Response:
        try:
            # Eine Anfrage zugleich - siehe die Begruendung im Erzeuger.
            with self._nacheinander:
                antwort = self._client.get(pfad, params=params or None,
                                           headers=self._kopf(pfad))
        except httpx.HTTPError as e:
            raise JurNodesFehler(f"jur|nodes nicht erreichbar ({type(e).__name__}).") from e
        if antwort.status_code == 404:
            raise nicht_gefunden(f"In jur|nodes nicht gefunden (GET {pfad}).")
        if antwort.status_code in (401, 403):
            raise JurNodesFehler(
                f"jur|nodes hat den Zugriff abgelehnt (GET {pfad}, Status "
                f"{antwort.status_code}). Dem Schlüssel fehlt der Bereich "
                f"{bereich_von(pfad) or pfad} oder ein Recht darin.")
        if antwort.status_code >= 400:
            # Kein Antworttext ins Protokoll oder an die Oberflaeche - aber der
            # Pfad gehoert hinein. "Status 405" allein sagt nicht, WELCHER
            # Aufruf abgewiesen wurde, und in einer Sitzung laufen ein halbes
            # Dutzend. Am 24.09.2026 hat genau das eine Stunde gekostet.
            # Ein Pfad ist fest verdrahtet und enthaelt keinen Akteninhalt.
            raise JurNodesFehler(
                f"jur|nodes antwortete auf GET {pfad} mit Status {antwort.status_code}.")
        return antwort

    def _alle_seiten(self, pfad: str, nicht_gefunden: type[JurNodesFehler],
                     *schluessel: str, **params: Any) -> list[Mapping[str, Any]]:
        """Alle Seiten einer Suche, nicht nur die erste.

        Die Schnittstelle gibt hoechstens 50 oder 100 Eintraege je Seite
        zurueck. Wer nur die erste holt, bekommt bei einer Akte mit 120
        Dokumenten 100 davon - und die uebrigen 20 fehlen lautlos. Genau diese
        Art von Fehler ist in diesem Programm schon zweimal aufgetreten und
        beide Male teuer gewesen: Was nicht da ist, faellt nicht auf.

        Gelesen wird nacheinander; der Hersteller laesst je IP eine Anfrage
        zugleich zu.
        """
        # Die ERSTE Anfrage geht ohne "page". Das ist kein Schoenheitsfehler,
        # sondern das einzige, was am Server der Kanzlei nachweislich
        # funktioniert hat: Die Probe am 23.09.2026 fragte ohne Seitenangabe
        # und bekam Antwort; mit page=0 kam nichts zurueck. Der Hersteller
        # schreibt, die erste Seite sei 0 - sein Server sieht das
        # offensichtlich anders, und im Zweifel gilt der Server.
        #
        # Von der zweiten Seite an wird gezaehlt, und zwar ab der Zahl, die
        # der Hersteller nennt. Das ist die Stelle, an der seine Angabe
        # gebraucht wird und stimmen kann.
        seite = erste_seite(pfad)
        alle: list[Mapping[str, Any]] = []
        erste_anfrage = True
        while seite - erste_seite(pfad) < SEITEN_GRENZE:
            seitenangabe: dict[str, Any] = {} if erste_anfrage else {"page": seite}
            erste_anfrage = False
            daten = self._get(pfad, nicht_gefunden, **seitenangabe, **params).json()
            teil = self._liste(daten, *schluessel)
            alle.extend(teil)
            if not teil:
                break
            seiten = 0
            if isinstance(daten, Mapping):
                try:
                    seiten = int(daten.get("pagesTotal") or 0)
                except (TypeError, ValueError):
                    seiten = 0
            gelesen = seite - erste_seite(pfad) + 1
            if seiten and gelesen >= seiten:
                break
            if not seiten:
                # Ein Server ohne Seitenangabe: solange holen, bis nichts mehr
                # kommt. Die Grenze oben faengt eine Antwort, die nie endet.
                pass
            seite += 1
        return alle

    def _lesen_per_post(self, pfad: str, nicht_gefunden: type[JurNodesFehler],
                        **koerper: Any) -> httpx.Response:
        """Eine **lesende** Abfrage, die der Hersteller als POST führt.

        Das Korrespondenzverzeichnis ist eine Suche und holt nichts als Daten –
        der Hersteller verlangt dafür trotzdem POST mit einem JSON-Körper
        (API 1.0.2, ``CorrespondenceSearchRequest``). Das Verfahren macht den
        Aufruf nicht schreibend, und deshalb steht diese Stelle hier getrennt
        von ``vermerk_schreiben``: **Welche POST-Aufrufe lesend sind, soll man
        an einer Hand abzählen können.** Es sind diese Suche und sonst keine.
        """
        try:
            with self._nacheinander:
                antwort = self._client.post(pfad, json=koerper, headers=self._kopf(pfad))
        except httpx.HTTPError as e:
            raise JurNodesFehler(f"jur|nodes nicht erreichbar ({type(e).__name__}).") from e
        if antwort.status_code == 404:
            raise nicht_gefunden(f"In jur|nodes nicht gefunden (POST {pfad}).")
        if antwort.status_code in (401, 403):
            raise JurNodesFehler(
                f"jur|nodes hat den Zugriff abgelehnt (POST {pfad}, Status "
                f"{antwort.status_code}). Dem Schlüssel fehlt der Bereich "
                f"{bereich_von(pfad) or pfad} oder ein Recht darin.")
        if antwort.status_code >= 400:
            raise JurNodesFehler(
                f"jur|nodes antwortete auf POST {pfad} mit Status {antwort.status_code}.")
        return antwort

    def _alle_seiten_post(self, pfad: str, nicht_gefunden: type[JurNodesFehler],
                          *schluessel: str, **koerper: Any) -> list[Mapping[str, Any]]:
        """Wie ``_alle_seiten``, nur mit dem Körper statt der Abfrageparameter.

        Die Seitenzählung ist dieselbe, aus demselben Grund: Wer nur die erste
        Seite holt, bekommt bei einer Akte mit 120 Schriftstücken 100 davon –
        und die übrigen 20 fehlen lautlos.
        """
        seite = erste_seite(pfad)
        alle: list[Mapping[str, Any]] = []
        erste_anfrage = True
        while seite - erste_seite(pfad) < SEITEN_GRENZE:
            seitenangabe: dict[str, Any] = {} if erste_anfrage else {"page": seite}
            erste_anfrage = False
            daten = self._lesen_per_post(pfad, nicht_gefunden, **seitenangabe, **koerper).json()
            teil = self._liste(daten, *schluessel)
            alle.extend(teil)
            if not teil:
                break
            seiten = 0
            if isinstance(daten, Mapping):
                try:
                    seiten = int(daten.get("pagesTotal") or 0)
                except (TypeError, ValueError):
                    seiten = 0
            gelesen = seite - erste_seite(pfad) + 1
            if seiten and gelesen >= seiten:
                break
            seite += 1
        return alle

    @staticmethod
    def _liste(daten: Any, *schluessel: str) -> list[Mapping[str, Any]]:
        if isinstance(daten, list):
            return daten
        if isinstance(daten, Mapping):
            for s in schluessel:
                if isinstance(daten.get(s), list):
                    return daten[s]
        raise JurNodesFehler("Unerwartetes Antwortformat von jur|nodes.")

    # ── Schnittstelle ──────────────────────────────────────────────────────

    def akten_suchen(self, suchbegriff: str = "") -> list[Akte]:
        """Akten suchen - ueber das Aktenzeichen UND das Kurzrubrum.

        Das ist der Gewinn gegenueber dem Laufwerk. Dort steht im Ordnernamen
        nur das Aktenzeichen; wer "Testmann" sucht, findet nichts. jur|nodes
        fuehrt daneben das Kurzrubrum, und danach laesst sich fragen.

        Zwei Anfragen statt einer, weil die Schnittstelle je Feld sucht. Sie
        laufen nacheinander - eine zugleich je IP-Adresse ist die Vorgabe des
        Herstellers.
        """
        begriff = self._platzhalter(suchbegriff)
        felder: tuple[dict[str, Any], ...] = (
            ({self._endpunkte.suchparameter: begriff},) if not suchbegriff else
            ({self._endpunkte.suchparameter: begriff},
             {self._endpunkte.rubrumparameter: begriff}))
        gefunden: dict[str, Akte] = {}
        for feld in felder:
            for a in self._alle_seiten(self._endpunkte.akten_suche, AkteNichtGefunden,
                                       "elements", "akten", "items", "data", **feld):
                akte = akte_aus_json(a)
                gefunden.setdefault(akte.id, akte)
        return sorted(gefunden.values(), key=lambda a: a.aktenzeichen)

    @staticmethod
    def _platzhalter(suchbegriff: str) -> str:
        """Den Suchbegriff so stellen, wie jur|nodes ihn erwartet.

        Zwei Dinge, die beide erst der Betrieb gezeigt hat:

        **Eine Suche ohne Kriterium weist der Server ab.** Die Aktenliste
        fragt beim Oeffnen ohne Begriff - und bekam einen Fehlerstatus. Der
        Hersteller schreibt zu ``sign`` und ``shortRubrum`` dasselbe:
        "%-Zeichen fuer Suchbefehl verwenden". Ein blosses ``%`` ist damit die
        Frage nach allem, und genau die war gemeint.

        **Ein Begriff ohne Platzhalter trifft nur genau.** Die Kanzlei sucht
        aber nach "Testmann" und meint die Akte "Testmann ./. Musterhaft". Deshalb
        steht der Begriff zwischen zwei Prozentzeichen - es sei denn, jemand
        hat selbst welche gesetzt; dann weiss er, was er tut, und wir fassen
        es nicht an.
        """
        begriff = suchbegriff.strip()
        if not begriff:
            return "%"
        return begriff if "%" in begriff else f"%{begriff}%"

    def akte(self, akte_id: str) -> Akte:
        return akte_aus_json(self._roh_akte(akte_id))

    def _roh_akte(self, akte_id: str) -> Mapping[str, Any]:
        """Die Akte selbst - waehrend eines Arbeitsgangs nur einmal geholt.

        Beim Oeffnen einer Akte wird sie dreimal gebraucht: fuer die Akte,
        fuer den Dateiordner der Dokumentliste und fuer den des
        Aktengedaechtnisses. Das waren drei Anfragen ueber die Leitung, jede
        nacheinander - der Hersteller laesst je IP nur eine zugleich zu.
        """
        gepuffert = self._kurz_holen(("akte", akte_id))
        if gepuffert is not None:
            return gepuffert
        daten = self._get(self._endpunkte.akte, AkteNichtGefunden,
                          **{self._endpunkte.kennungparameter: akte_id}).json()
        if not isinstance(daten, Mapping):
            raise JurNodesFehler("Unerwartetes Antwortformat von jur|nodes.")
        _identitaet_pruefen(akte_id, daten)
        self._kurz_merken(("akte", akte_id), daten)
        return daten

    def _ordner_inhalt(self, ordner_id: Any) -> list[Mapping[str, Any]]:
        """Der Inhalt eines Ordners - waehrend eines Arbeitsgangs einmal.

        Der Wurzelordner wurde beim Oeffnen zweimal gelesen: einmal fuer die
        Dokumentliste und einmal, um das Aktengedaechtnis zu finden. Aus der
        Kanzlei am 25.09.2026: "es dauert 8 Sekunden, damit sich das Fenster
        oeffnet, um die Dateien anzukreuzen - das ist zu lang."
        """
        gepuffert = self._kurz_holen(("ordner", str(ordner_id)))
        if gepuffert is not None:
            return gepuffert
        eintraege = self._alle_seiten(
            self._endpunkte.ordner_inhalt, AkteNichtGefunden,
            "elements", "dokumente", "items", "data",
            **{self._endpunkte.ordnerparameter: ordner_id})
        self._kurz_merken(("ordner", str(ordner_id)), eintraege)
        return eintraege

    def _fremde_dateien_aussondern(self, ordner_id: Any,
                                   eintraege: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
        """Eine Datei muss in dem Ordner liegen, dessen Inhalt gefragt war.

        Die zweite Hälfte von Befund F08. Die Akte selbst wird jetzt gegen die
        angefragte Kennung geprüft; für die einzelne Datei gibt es kein Feld,
        das die Akte nennt – der Hersteller führt an ``File`` nur
        ``folderId`` (API 1.0.2). Genau das lässt sich aber prüfen: Wer den
        Inhalt von Ordner 42 abfragt, bekommt Dateien aus Ordner 42.

        Mehr ist am Client nicht zu holen, und das steht hier, damit niemand
        die Prüfung für mehr hält, als sie ist.
        """
        behalten: list[Mapping[str, Any]] = []
        for eintrag in eintraege:
            datei = eintrag.get("file") if isinstance(eintrag, Mapping) else None
            fremd = (isinstance(datei, Mapping) and datei.get("folderId") is not None
                     and str(datei.get("folderId")) != str(ordner_id))
            if fremd:
                self.letzte_dateien_aussortiert += 1
                continue
            behalten.append(eintrag)
        return behalten

    def _kurz_holen(self, schluessel: tuple[str, str]) -> Any:
        """Was noch frisch genug ist - sonst None."""
        eintrag = self._kurzpuffer.get(schluessel)
        if eintrag is None:
            return None
        stand, wert = eintrag
        if time.monotonic() - stand >= self.PUFFER_SEKUNDEN:
            return None
        return wert

    def _kurz_merken(self, schluessel: tuple[str, str], wert: Any) -> None:
        self._kurzpuffer[schluessel] = (time.monotonic(), wert)

    def _puffer_leeren(self) -> None:
        """Nach jedem Schreiben. Was sich geaendert hat, darf nicht aus dem
        Puffer kommen - eine falsche Antwort ist schlimmer als eine langsame."""
        self._kurzpuffer.clear()
        self._liste_puffer = ("", 0.0, [])

    #: Wie tief in Unterordner hinabgestiegen wird.
    #:
    #: Gemessen am 25.09.2026 in der Kanzlei: eine Akte mit 29 Dateien im
    #: Wurzelordner und 2 Unterordnern. Bis dahin las das Programm nur den
    #: Wurzelordner - was in den Unterordnern lag, fehlte lautlos. Genau die
    #: Art Fehler, die in diesem Programm schon dreimal teuer war: Was nicht
    #: da ist, faellt nicht auf.
    #:
    #: Fuenf Stufen sind mehr, als eine Aktenablage ueblicherweise hat, und
    #: wenig genug, dass ein versehentlich verschachtelter Bestand nicht in
    #: hunderte Anfragen laeuft - der Hersteller laesst je IP eine zugleich.
    ORDNER_TIEFE = 5

    #: Wie viele Ordner je Akte hoechstens gelesen werden.
    ORDNER_HOECHSTZAHL = 60

    #: Wie viele Unterordner beim letzten Lesen uebersprungen werden mussten
    #: - weil der Schluessel sie nicht lesen darf oder es sie nicht gibt.
    letzte_ordner_uebersprungen: int = 0
    #: Dateien, die der Server in einem anderen Ordner verortet, als
    #: abgefragt wurde. Siehe _fremde_dateien_aussondern (Befund F08).
    letzte_dateien_aussortiert: int = 0

    #: Korrespondenzeintraege, deren Inhalt noch nicht angebunden ist - beA,
    #: Post, Fax, SMS. -1 heisst: Das Verzeichnis war nicht zu lesen.
    #: Was fehlt, soll sichtbar fehlen.
    letzte_korrespondenz_ohne_inhalt: int = 0

    #: Mails, die groesser waren als die Grenze - gezaehlt, nicht verschwiegen.
    letzte_mails_zu_gross: int = 0
    #: Mails, die das Gesamtmass der Akte gesprengt haetten.
    letzte_mails_ueber_budget: int = 0
    #: Mails, die sich nicht holen liessen (Status, Netz).
    letzte_mails_ohne_antwort: int = 0
    #: Wie viele Anlagen aus den Mails dieser Akte dazugekommen sind.
    letzte_mail_anhaenge: int = 0
    #: Was beim Zerlegen der Mails nicht uebernommen wurde: Grund -> Anzahl.
    #:
    #: Befund N04 der dritten Zweitpruefung vom 12.10.2026: Der Parser kannte
    #: diese Zahlen und gab sie zurueck - der Adapter nahm sie nicht. Die 51.
    #: Anlage wurde gezaehlt und war nirgends zu sehen. Ein Zaehler, den nur
    #: der Parser kennt, ist kein Zaehler; angezeigt wurden allein die
    #: angenommenen Anlagen, und die sahen vollstaendig aus.
    letzte_mail_ausgelassen: dict[str, int] = field(default_factory=dict)
    #: Angehaengte Nachrichten, deren Text mit in die Dokumente kam (N03).
    letzte_mail_nachrichten: int = 0

    def _ordner_durchgehen(self, wurzel: Any) -> list[tuple[str, Mapping[str, Any]]]:
        """Alle Eintraege einer Akte - auch die in Unterordnern.

        Die Beschreibung des Herstellers fuehrt jeden Eintrag als "folder"
        oder "file"; ein Ordner nennt seine Nummer in ``folder.id``, seinen
        Namen in ``folder.folderName`` und sagt mit ``canRead``, ob er gelesen
        werden darf. Ein Ordner, den der Schluessel nicht lesen darf, wird
        uebersprungen statt einen Fehler zu werfen - er gehoert dann jemand
        anderem.

        Gegen Schleifen: Jede Ordnernummer wird nur einmal besucht.

        **Zu jedem Eintrag kommt sein Ordner zurueck**, als Pfad unter dem
        Aktenordner ("Schriftsaetze/Gegenseite"); der Wurzelordner selbst ist
        die leere Zeichenkette. Ohne das steht die Akte spaeter in einer
        Reihe - in X-100-2026 waren das 55 Eintraege aus acht Ordnern.
        """
        gesehen: set[str] = set()
        self.letzte_ordner_uebersprungen = 0
        self.letzte_dateien_aussortiert = 0
        alle: list[tuple[str, Mapping[str, Any]]] = []
        offen: list[tuple[Any, int, str]] = [(wurzel, 0, "")]
        while offen and len(gesehen) < self.ORDNER_HOECHSTZAHL:
            ordner_id, tiefe, pfad = offen.pop(0)
            if str(ordner_id) in gesehen:
                continue
            gesehen.add(str(ordner_id))
            try:
                eintraege = self._ordner_inhalt(ordner_id)
            except JurNodesFehler:
                # Ein einzelner Unterordner, der nicht zu lesen ist, darf
                # nicht die ganze Dokumentliste kosten. Der Wurzelordner
                # dagegen schon - ohne ihn gibt es nichts zu zeigen, und ein
                # stiller leerer Bestand waere schlimmer als ein Fehler.
                if tiefe == 0:
                    raise
                self.letzte_ordner_uebersprungen += 1
                continue
            alle.extend((pfad, e) for e in
                        self._fremde_dateien_aussondern(ordner_id, eintraege))
            if tiefe >= self.ORDNER_TIEFE:
                continue
            for eintrag in eintraege:
                if not isinstance(eintrag, Mapping) or eintrag.get("type") != "folder":
                    continue
                unter = eintrag.get("folder")
                if not isinstance(unter, Mapping):
                    continue
                if unter.get("canRead") is False:
                    continue
                nummer = unter.get("id")
                if nummer is not None and str(nummer) not in gesehen:
                    offen.append((nummer, tiefe + 1, _ordnerpfad(pfad, unter, nummer)))
        return alle

    def dokumente(self, akte_id: str) -> list[Dokument]:
        """Die Dokumente einer Akte - ueber ihren Dateiordner.

        Anders als geraten haengen die Dokumente nicht an der Akte. Die Akte
        nennt eine ``fileFolderId``; deren Inhalt wird getrennt abgefragt und
        enthaelt Ordner und Dateien gemischt. Nur die Dateien zaehlen hier.
        """
        roh = self._roh_akte(akte_id)
        ordner_id = roh.get("fileFolderId")
        if not ordner_id:
            return []
        eintraege = self._ordner_durchgehen(ordner_id)
        # Die Akte nennt einen ZWEITEN Ordner: den fuer die Korrespondenz.
        #
        # Eingebaut am 25.09.2026. Aus der Kanzlei: "er muss auch die Mails
        # beruecksichtigen, die verfasst wurden." Das Programm las bis dahin
        # nur den Dateiordner; alles Geschriebene fehlte lautlos.
        #
        # **Seit dem 05.10.2026 wird er NICHT mehr gelesen**, auf
        # ausdrueckliche Anweisung der Kanzlei. Am 02.10. fielen in einer
        # Bausache drei Schriftstuecke aus einer fremden Verkehrsunfallsache
        # auf; drei Laeufe an drei Akten zeigten dasselbe Muster. Der
        # Dateiordner passt jedesmal zur Akte, der Korrespondenzordner nie -
        # seine Nummer ist niedrig und alt, unabhaengig vom Alter der Akte,
        # und befuellt wurde er stets 2022/23. Das Feld zeigt offenbar nicht
        # auf die Korrespondenz DIESER Akte. Worauf dann, weiss nur der
        # Hersteller; bis dahin wird nicht geraten.
        #
        # Fremde Schriftstuecke in einer Arbeitsakte sind teurer als fehlende:
        # Was fehlt, faellt auf; was zu viel ist, wird mitanalysiert, zitiert
        # und ins Aktengedaechtnis geschrieben.
        #
        # Zurueck mit JUSPERFECT_KORRESPONDENZ=ein - aber erst mit der Antwort.
        #
        # Faellt der Ordner aus - es gibt ihn nicht, oder der Schluessel darf
        # ihn nicht lesen -, kostet das nicht die uebrigen Dokumente. Er ist
        # eine Ergaenzung, keine Bedingung.
        # ~~correspondenceFolderId~~ war der falsche Weg, und zwar unser eigener
        # Fehler: Die Nummer gehoert in den Ordnerbaum der KORRESPONDENZ und
        # wurde gegen den Baum des DATEISYSTEMS abgefragt. Zwei Nummernkreise,
        # dieselbe Zahl, fremde Akte. Der Hersteller hat einen eigenen Weg je
        # Akte, und den nimmt das Programm seit dem 06.10.2026:
        # POST /correspondence/search mit recordIdentifier.
        dokumente: list[Dokument] = []
        for pfad, eintrag in eintraege:
            datei = eintrag.get("file") if isinstance(eintrag, Mapping) else None
            if datei is None and isinstance(eintrag, Mapping) and eintrag.get("type") == "folder":
                continue
            roh = datei or eintrag
            # Das Aktengedaechtnis ist KEIN Dokument der Akte.
            #
            # Es ist die Arbeitsdatei des Programms und lag bis zum
            # 25.09.2026 unbemerkt in der Dokumentliste - in einer Akte, in
            # der sonst nichts im Wurzelordner liegt, war es sogar das
            # einzige. Aus der Kanzlei an diesem Tag: "es wurde auch nur ein
            # Dokument von der Akte angezeigt."
            #
            # Vorher konnte es nicht auffallen: Ohne Zurueckschreiben gab es
            # die Datei gar nicht.
            if isinstance(roh, Mapping) and ist_gedaechtnis_datei(self._ganzer_name(roh)):
                continue
            dokumente.append(dokument_aus_json(akte_id, roh, ordner=pfad))
        if self._korrespondenz:
            dokumente += self._vermerke(akte_id)
        return dokumente

    # ── Die E-Akte: Korrespondenz und Vermerke ─────────────────────────────

    def korrespondenz(self, akte_id: str) -> list[Mapping[str, Any]]:
        """Das Korrespondenzverzeichnis dieser Akte.

        Der Hersteller fuehrt die Korrespondenz in einem **eigenen** Baum mit
        eigenen Nummern - Mails, beA, Post, Fax, SMS, Dateien und Vermerke
        (API 1.0.2, ``CorrespondenceModel``). Abgefragt wird sie je Akte ueber
        ``recordIdentifier``, nicht ueber eine Ordnernummer. Genau das war der
        Fehler vom 02.10.2026: ``correspondenceFolderId`` zeigt in den anderen
        Baum, und gegen das Dateisystem abgefragt kam eine fremde Akte heraus.

        Ein Eintrag ist eine **Huelle**: Betreff, Art, Richtung, Datum und ein
        Verweis darauf, wo der Inhalt liegt. Die Huelle allein ist kein
        Dokument - deshalb wird sie hier zurueckgegeben und nicht in die
        Dokumentliste gestellt.
        """
        return self._alle_seiten_post(
            self._endpunkte.korrespondenz_suche, AkteNichtGefunden,
            "elements", "korrespondenz", "items", "data",
            **{self._endpunkte.akteparameter: akte_id})

    def _vermerke(self, akte_id: str) -> list[Dokument]:
        """Die Vermerke der Akte als Dokumente - und nur sie.

        Aus der Kanzlei am 05.10.2026: „Die Korrespondenz bei jurnodes und die
        Vermerke finden sich in der E-Akte." Von allem, was dort liegt, ist der
        **Vermerk** der einzige, dessen Inhalt die Beschreibung des Herstellers
        als Text zusagt (``GET /record/note`` -> ``RecordNote.content``, mit
        ``contentType`` html oder text).

        **Was bei Mail, beA und Post fehlt, ist weniger, als es zuerst
        aussah** (nachgesehen am 06.10.2026). Die Beschreibung nennt den
        Download sehr wohl: ``POST /mail/download`` mit ``{mailIdentifier}``
        gibt ``application/octet-stream`` zurueck. Offen sind zwei kleinere
        Dinge, und beide lassen sich nicht herbeidenken:

        1. **Welche Dateiart** diese Bytes sind - .eml, .msg, PDF. Ohne sie
           weiss die Texterkennung nicht, womit sie lesen soll. (Am Inhalt
           erkennbar, aber erst, wenn einer vorliegt.)
        2. **Woher die zweite Nummer kommt**, die beA und Post brauchen:
           ``attachmentId`` beim beA, ``postFileUniqueKey`` bei der Post. Die
           Beschreibung nennt sie als Pflicht und sagt nicht, welcher Aufruf
           sie liefert.

        Beides beantwortet ein Lauf am Server der Kanzlei; der Pruefbogen misst
        es und gibt dabei **keinen Inhalt** aus, nur Status, Laenge und die
        Signatur der ersten Bytes. Bis dahin wird nicht geraten - die Eintraege
        stehen in der Zahl unten, damit nichts lautlos fehlt.

        **Kein Postfach.** Aus der Kanzlei am 07.10.2026: Ein Zugriff auf das
        E-Mail-Postfach und auf das beA-Postfach ist nicht erforderlich, weil
        alles in der E-Akte abgelegt wird. Das Programm hat auch keinen: es
        spricht ausschliesslich die jur|nodes-Schnittstelle an
        (``JUSPERFECT_JURNODES_URL``). Auch ``POST /mail/download`` ist ein
        Aufruf an jur|nodes und holt die dort abgelegte Fassung - kein
        IMAP, kein SMTP, kein beA-Zugang. Die offenen Fragen 1 und 2 betreffen
        nur, wie die E-Akte diese Fassung herausgibt.
        """
        self.letzte_korrespondenz_ohne_inhalt = 0
        try:
            eintraege = self.korrespondenz(akte_id)
        except JurNodesFehler:
            # Die Korrespondenz ist eine Ergaenzung, keine Bedingung. Faellt
            # sie aus, kostet das nicht die Dokumente des Dateisystems.
            self.letzte_korrespondenz_ohne_inhalt = -1
            return []
        dokumente: list[Dokument] = []
        for eintrag in eintraege:
            if not isinstance(eintrag, Mapping):
                continue
            art = str(eintrag.get("type", "")).lower()
            nummer = eintrag.get("referenceNote")
            if art != "note" or nummer is None:
                # Dateien der Korrespondenz liegen im Dateisystem und sind
                # oben schon dabei; die Mails holt _mail_dokumente gleich
                # darunter. Alles uebrige - beA, Post, Fax, SMS - hat hier
                # noch keinen Inhalt und wird gezaehlt, damit es sichtbar
                # fehlt statt lautlos.
                if art not in ("file", "", "mail"):
                    self.letzte_korrespondenz_ohne_inhalt += 1
                continue
            dokumente.append(vermerk_als_dokument(akte_id, nummer, eintrag))
        dokumente += self._mail_dokumente(akte_id, eintraege)
        return dokumente

    def _mail_dokumente(self, akte_id: str,
                        eintraege: list[Mapping[str, Any]]) -> list[Dokument]:
        """Die E-Mails der Akte als Dokumente - Text und Anlagen getrennt.

        **Vorgabe der Kanzlei vom 08.10.2026, woertlich:** „Text der Mail
        immer, Anhänge als eigene Dokumente daneben, jedes einzeln abwählbar
        wie die Dateien aus dem Aktenordner."

        **Warum hier schon geholt wird und nicht erst beim Lesen.** Welche
        Anlagen eine Mail traegt, steht in keinem Verzeichnis des Herstellers.
        Fuer die Post gibt es ``POST /post/get-files``, fuer das beA
        ``GET /bea`` - fuer die Mail nichts dergleichen. Die Anlagen stehen
        allein in der ``.eml``. Wer sie vor dem Herunterladen auflisten will,
        muesste raten.

        Also wird geholt - einmal je Mail, und das Ergebnis bleibt gepuffert.
        Gemessen am 08.10.2026: 22 Mails in X-100-2026, davon eine mit
        8,7 MB und der Rest klein; neun in X-101-2026, die geoeffnete 5,4 KB.

        **Zwei Grenzen halten das in Schach**, und beide melden, was sie
        weglassen: ``mail_grenze_mb`` je Mail und ``mail_gesamt_mb`` je Akte.
        Was darueber liegt, steht trotzdem in der Liste - mit Betreff und
        Datum, ohne Inhalt. Ein Programm, das Akteninhalt lautlos weglaesst,
        ist schlimmer als eines, das zu viel zeigt.
        """
        self.letzte_mails_zu_gross = 0
        self.letzte_mails_ueber_budget = 0
        self.letzte_mails_ohne_antwort = 0
        self.letzte_mail_anhaenge = 0
        self.letzte_mail_ausgelassen = {}
        self.letzte_mail_nachrichten = 0
        if self._mails_akte != akte_id:
            self._mails.clear()
            self._mails_akte = akte_id

        dokumente: list[Dokument] = []
        verbraucht = 0
        for eintrag in eintraege:
            if str(eintrag.get("type", "")).lower() != "mail":
                continue
            kennung = eintrag.get("referenceMail")
            if not kennung:
                self.letzte_korrespondenz_ohne_inhalt += 1
                continue
            kennung = str(kennung)
            zerlegt = self._mails.get(kennung)
            if zerlegt is None:
                if verbraucht >= self._mail_gesamt:
                    self.letzte_mails_ueber_budget += 1
                    dokumente.append(mail_als_dokument(akte_id, kennung, eintrag,
                                                       grund="budget"))
                    continue
                zerlegt, groesse, grund = self._mail_holen(kennung)
                verbraucht += groesse
                if zerlegt is None:
                    if grund == "zu_gross":
                        self.letzte_mails_zu_gross += 1
                    else:
                        self.letzte_mails_ohne_antwort += 1
                    dokumente.append(mail_als_dokument(akte_id, kennung, eintrag,
                                                       grund=grund))
                    continue
                self._mails[kennung] = zerlegt

            # Was diese Mail an Teilen verloren hat, steht in ihrer eigenen
            # Zeile - dort sucht man es, wenn eine Anlage fehlt. Die Summe
            # ueber die Akte steht zusaetzlich oben in der Liste.
            dokumente.append(mail_als_dokument(akte_id, kennung, eintrag,
                                               zerlegt.mime_typ,
                                               verlust=zerlegt.gruende()))
            for grund, anzahl in zerlegt.ausgelassen.items():
                if anzahl:
                    self.letzte_mail_ausgelassen[grund] = (
                        self.letzte_mail_ausgelassen.get(grund, 0) + anzahl)
            self.letzte_mail_nachrichten += zerlegt.nachrichten
            for nr, anhang in enumerate(zerlegt.anhaenge):
                dokumente.append(anhang_als_dokument(akte_id, kennung, nr,
                                                     anhang, eintrag))
                self.letzte_mail_anhaenge += 1
        return dokumente

    def _mail_holen(self, kennung: str) -> tuple[Zerlegt | None, int, str]:
        """Eine ``.eml`` holen und zerlegen - mit der Groessengrenze davor.

        Die Grenze wird an ``Content-Length`` geprueft, **bevor** die Bytes
        ueber die Leitung gehen: ``httpx`` gibt die Kopfzeilen frei, sobald
        sie da sind, und ein Abbruch an dieser Stelle kostet nur sie. Nennt
        der Server keine Laenge, wird mitgezaehlt und bei Ueberschreitung
        abgebrochen.
        """
        koerper = {"mailIdentifier": kennung}
        try:
            with self._nacheinander:
                with self._client.stream("POST", self._endpunkte.mail_download,
                                         json=koerper,
                                         headers=self._kopf(self._endpunkte.mail_download)
                                         ) as antwort:
                    if antwort.status_code >= 400:
                        return None, 0, "status"
                    gemeldet = antwort.headers.get("content-length")
                    if gemeldet and gemeldet.isdigit() and int(gemeldet) > self._mail_grenze:
                        return None, 0, "zu_gross"
                    teile: list[bytes] = []
                    gelesen = 0
                    for stueck in antwort.iter_bytes():
                        gelesen += len(stueck)
                        if gelesen > self._mail_grenze:
                            return None, gelesen, "zu_gross"
                        teile.append(stueck)
        except httpx.HTTPError:
            # Eine Mail, die nicht kommt, kostet nicht die uebrigen.
            return None, 0, "netz"
        roh = b"".join(teile)
        return zerlegen(roh), len(roh), ""

    def _vermerk_laden(self, akte_id: str, nummer: str) -> tuple[Mapping[str, Any], bytes]:
        """Einen Vermerk samt Inhalt - mit der Pruefung aus Befund F08.

        ``RecordNote`` traegt das Feld ``record``. Anders als bei einer Datei
        laesst sich hier also nachsehen, ob die Antwort zur angefragten Akte
        gehoert; genau das wird getan.
        """
        antwort = self._get(self._endpunkte.vermerke, DokumentNichtGefunden,
                            **{self._endpunkte.vermerkparameter: nummer,
                               self._endpunkte.vermerkakteparameter: akte_id})
        daten = antwort.json()
        if isinstance(daten, Mapping) and isinstance(daten.get("model"), Mapping):
            daten = daten["model"]
        if not isinstance(daten, Mapping):
            raise JurNodesFehler("Unerwartetes Antwortformat von jur|nodes.")
        zurueck = str(daten.get("record", "")).strip()
        if zurueck and zurueck.casefold() != str(akte_id).strip().casefold():
            raise JurNodesFehler(
                "jur|nodes hat auf die Anfrage nach einem Vermerk dieser Akte einen "
                "Vermerk einer anderen Akte geantwortet. Der Vorgang wurde abgebrochen.")
        inhalt = str(daten.get("content", "") or "")
        return daten, inhalt.encode("utf-8")

    #: Wie lange die Dokumentliste einer Akte wiederverwendet wird.
    #:
    #: dokument_laden braucht die Metadaten des einen Dokuments und holte
    #: dafuer die ganze Liste. Seit die Unterordner mitgelesen werden, ist
    #: das nicht mehr eine Anfrage, sondern eine je Ordner - und das bei
    #: JEDEM Dokument. Beim Uebernehmen von dreissig Dokumenten waren es
    #: ueber hundert Anfragen, alle nacheinander, weil der Hersteller je IP
    #: nur eine zugleich zulaesst.
    #:
    #: Waehrend eines Uebernehmens aendert sich die Akte nicht. Eine halbe
    #: Minute ist lang genug dafuer und kurz genug, dass ein neu
    #: eingegangener Schriftsatz nicht lange fehlt.
    LISTE_GILT_SEKUNDEN = 30.0

    #: Wie lange eine Akte oder ein Ordnerinhalt wiederverwendet wird.
    #: Kurz genug, dass ein neuer Schriftsatz nicht lange fehlt; lang genug
    #: fuer einen Arbeitsgang, waehrend dessen sich nichts aendert.
    PUFFER_SEKUNDEN = 30.0

    def _dokumente_gepuffert(self, akte_id: str) -> list[Dokument]:
        """Die Dokumentliste, ohne sie fuer jedes Dokument neu zu holen."""
        jetzt = time.monotonic()
        akte, stand, liste = self._liste_puffer
        if akte == akte_id and jetzt - stand < self.LISTE_GILT_SEKUNDEN:
            return liste
        liste = self.dokumente(akte_id)
        self._liste_puffer = (akte_id, jetzt, liste)
        return liste

    def dokument_laden(self, akte_id: str, dokument_id: str) -> tuple[Dokument, bytes]:
        dokument = next((d for d in self._dokumente_gepuffert(akte_id) if d.id == dokument_id), None)
        if dokument is None:
            raise DokumentNichtGefunden(f"Dokument {dokument_id} nicht in Akte {akte_id}.")
        # Ein Vermerk kommt nicht aus dem Dateisystem. Die Kennung sagt es:
        # "vermerk:17" statt einer Dateikennung - siehe vermerk_als_dokument.
        if dokument_id.startswith(VERMERK_VORSATZ):
            _, inhalt = self._vermerk_laden(akte_id, dokument_id[len(VERMERK_VORSATZ):])
            return dokument, inhalt
        # Eine Mail und ihre Anlagen kommen aus EINER .eml - sie wurde beim
        # Aufbau der Liste geholt und zerlegt. Hier wird nur noch
        # herausgegriffen, ohne zweiten Aufruf an jur|nodes.
        if dokument_id.startswith(MAIL_VORSATZ):
            return dokument, self._mail_teil(akte_id, dokument_id)
        antwort = self._get(self._endpunkte.datei_download, DokumentNichtGefunden,
                            **{self._endpunkte.kennungparameter: dokument_id})
        return dokument, antwort.content

    def _mail_teil(self, akte_id: str, dokument_id: str) -> bytes:
        """Den Brieftext oder eine Anlage aus der gepufferten ``.eml`` holen.

        **Kein zweiter Aufruf.** Die Mail wurde beim Aufbau der Dokumentliste
        geholt; aus derselben Zerlegung kommen der Text und jede Anlage. Ist
        der Puffer leer - etwa weil das Programm zwischendurch neu gestartet
        wurde -, wird sie einmal nachgeholt.
        """
        rest = dokument_id[len(MAIL_VORSATZ):]
        kennung, _, nummer = rest.partition(ANHANG_TRENNER)
        zerlegt = self._mails.get(kennung) if self._mails_akte == akte_id else None
        if zerlegt is None:
            zerlegt, _, grund = self._mail_holen(kennung)
            if zerlegt is None:
                raise DokumentNichtGefunden(
                    f"Der Inhalt dieser E-Mail ist nicht zu holen ({grund or 'unbekannt'}).")
            if self._mails_akte != akte_id:
                self._mails.clear()
                self._mails_akte = akte_id
            self._mails[kennung] = zerlegt

        if not nummer:
            return zerlegt.text.encode("utf-8")
        try:
            return zerlegt.anhaenge[int(nummer)].inhalt
        except (ValueError, IndexError):
            raise DokumentNichtGefunden(
                f"Diese Anlage gibt es in der E-Mail nicht mehr ({dokument_id}).") from None

    def beteiligte(self, akte_id: str) -> list[Beteiligter]:
        # recordIdentifier ist hier kein Beiwerk: Ohne ihn liefert die Suche
        # ALLE Beziehungen der Kanzlei statt der einen Akte. Die alte Vorgabe
        # trug die Akte im Pfad und haette ihn nicht mitgeschickt.
        return [beteiligter_aus_json(b)
                for b in self._alle_seiten(self._endpunkte.beteiligte, AkteNichtGefunden,
                                           "elements", "beteiligte", "items", "data",
                                           **{self._endpunkte.akteparameter: akte_id})]

    def fristen(self, akte_id: str) -> list[Frist]:
        # type=frist: Die Suche kennt daneben Aufgaben und Wiedervorlagen.
        # jusperfect erkennt Fristen, es berechnet keine - was hier
        # hereinkommt, ist Material, kein Rechenergebnis (SICHERHEIT.md,
        # Grundsatz 8).
        return [frist_aus_json(f)
                for f in self._alle_seiten(self._endpunkte.fristen, AkteNichtGefunden,
                                           "elements", "fristen", "items", "data",
                                           **{self._endpunkte.akteparameter: akte_id,
                                              "type": self._endpunkte.fristenart})]

    def vermerk_schreiben(self, akte_id: str, titel: str, text: str, freigabe: Freigabe) -> str:
        # Der einzige schreibende Weg des ganzen Programms, und er bleibt es:
        # Die Freigabe wird zuerst geprueft, gegen Nutzer, Akte und
        # Textpruefsumme. Ohne sie gibt es hier keinen Durchgang.
        self._freigabestelle.pruefen(freigabe, akte_id, text)
        # Aufbau nach jur|nodes API 1.0.1: ein Umschlag "model" um den
        # Vermerk. "id": None heisst neu anlegen; contentType bleibt Text -
        # etwas anderes laesst die Schnittstelle ueber die API nicht zu.
        # Wer hier faelschlich "titel"/"text" schickt, bekommt einen Fehler,
        # der nach einem Serverproblem aussieht.
        vermerk = {
            "id": None,
            "record": akte_id,
            "type": "note",
            "subject": titel,
            "contentType": "text",
            "content": text,
            "effectiveDate": freigabe.zeitpunkt.isoformat(),
        }
        try:
            with self._nacheinander:
                antwort = self._client.post(self._endpunkte.vermerke,
                                            json={"model": vermerk, "onlyValidate": False},
                                            headers=self._kopf(self._endpunkte.vermerke))
        except httpx.HTTPError as e:
            raise JurNodesFehler(f"jur|nodes nicht erreichbar ({type(e).__name__}).") from e
        if antwort.status_code >= 400:
            raise JurNodesFehler(f"jur|nodes hat den Vermerk abgelehnt (Status {antwort.status_code}).")
        daten = antwort.json() if antwort.content else {}
        return str(_erstes(daten, "id", "vermerkId", "kennung", standard="ohne-kennung"))

    def schliessen(self) -> None:
        self._client.close()

    # ── Das Aktengedächtnis in der Akte ─────────────────────────────────────
    # Noch nicht gebaut: Wie jur|nodes eine eigene Datei je Akte fuehrt, sagt
    # die REST-Schnittstelle, und die liegt noch nicht vor. Geraten wird hier
    # nicht - eine erfundene Adresse schriebe das Gedaechtnis ins Leere oder,
    # schlimmer, an eine falsche Stelle. Bis dahin fuehrt das Laufwerk die
    # Datei (webdav_adapter) oder das Gedaechtnis liegt getrennt (lokal, aws).

    # ── Das Aktengedächtnis in der Akte ────────────────────────────────────
    #
    # Eine einzige Datei je Akte, und ihr Name steht fest (GEDAECHTNIS_DATEI).
    # Das ist der Kern der Zusage: Ueber diesen Weg kann genau eine Datei
    # entstehen, und keine andere.
    #
    # Der Weg ueber die Schnittstelle hat eine Eigenheit, die der ueber das
    # Laufwerk nicht hat. Dort wird die Datei einfach ueberschrieben. Hier gibt
    # es nur "hinzufuegen", und der Hersteller sagt in seiner Beschreibung
    # nicht, was mit einer gleichnamigen Datei geschieht: Wird sie ersetzt oder
    # landet eine zweite daneben? Geraten wird das nicht - es wird nach dem
    # Ablegen NACHGESEHEN. Liegen zwei da, bricht jusperfect mit einem ganzen
    # Satz ab, statt bei jedem Sichern eine weitere anzulegen.

    def _gedaechtnis_eintrag(self, akte_id: str) -> Mapping[str, Any] | None:
        """Der Eintrag der Gedaechtnisdatei im Dateiordner der Akte."""
        ordner_id = self._roh_akte(akte_id).get("fileFolderId")
        if not ordner_id:
            return None
        gefunden = self._gedaechtnis_dateien(ordner_id)
        # Ohne zweite Abfrage: Die Liste liegt hier ohnehin vor.
        self.letzte_fassungen = len(gefunden)
        # Mehrere sind seit dem 25.09.2026 der Regelfall, nicht der Fehler:
        # jur|nodes ersetzt eine vorhandene Datei nicht, also bekommt jede
        # Fassung einen eigenen Zeitstempel. Gelesen wird die juengste.
        return gefunden[-1] if gefunden else None

    @staticmethod
    def _ganzer_name(datei: Mapping[str, Any]) -> str:
        """Name und Endung, wie jur|nodes sie getrennt fuehrt."""
        name = str(datei.get("fileName", ""))
        endung = str(datei.get("fileExtension", "")).lstrip(".")
        return f"{name}.{endung}" if endung else name

    def _gedaechtnis_dateien(self, ordner_id: Any) -> list[Mapping[str, Any]]:
        eintraege = self._ordner_inhalt(ordner_id)
        gefunden = []
        for eintrag in eintraege:
            datei = eintrag.get("file") if isinstance(eintrag, Mapping) else None
            datei = datei or (eintrag if isinstance(eintrag, Mapping) else {})
            ganz = self._ganzer_name(datei)
            name = str(datei.get("fileName", ""))
            if ist_gedaechtnis_datei(ganz) or ist_gedaechtnis_datei(name):
                gefunden.append(datei)
        # Die juengste zuletzt. Sortiert wird nach dem Zeitstempel IM Namen,
        # nicht nach dem Namen selbst: "-" steht im Zeichensatz vor ".", also
        # stuende die alte feste Datei sonst hinter allen neuen - und die
        # aelteste waere die juengste.
        gefunden.sort(key=lambda d: gedaechtnis_stand(self._ganzer_name(d))
                      or gedaechtnis_stand(str(d.get("fileName", ""))))
        return gefunden

    #: Wie viele Fassungen beim letzten Lesen in der Akte lagen. Der
    #: Gedaechtnisdienst macht daraus einen Hinweis, wenn es zu viele werden.
    letzte_fassungen: int = 0

    #: Ab wie vielen Fassungen darauf hingewiesen wird.
    #: Zwanzig sind rund zwanzig Sitzungen an derselben Akte - lange genug,
    #: dass niemand wegen einer zweiten Datei beunruhigt wird, und frueh
    #: genug, dass Aufraeumen eine Kleinigkeit bleibt.
    FASSUNGEN_HINWEIS = 20

    def gedaechtnis_lesen(self, akte_id: str) -> bytes | None:
        eintrag = self._gedaechtnis_eintrag(akte_id)
        if eintrag is None:
            return None
        kennung = str(eintrag.get("identifier", ""))
        if not kennung:
            return None
        return self._get(self._endpunkte.datei_download, DokumentNichtGefunden,
                         **{self._endpunkte.kennungparameter: kennung}).content

    def gedaechtnis_ablegen(self, akte_id: str, rohdaten: bytes) -> None:
        ordner_id = self._roh_akte(akte_id).get("fileFolderId")
        if not ordner_id:
            raise JurNodesFehler(
                "Diese Akte nennt keinen Dateiordner; das Aktengedächtnis "
                "lässt sich dort nicht ablegen.")
        # EINE Datei je Akte, unter einem festen Namen.
        #
        # Vom 25.09.2026 gab es hier kurz einen Zeitstempel je Fassung, weil
        # jur|nodes eine vorhandene Datei nicht ersetzt, sondern abweist. Aus
        # der Kanzlei am selben Tag: "Loesung B ist bloed, aendere das bitte
        # wieder." Zu Recht - in einer Mandatsakte sammelten sich Fassungen
        # neben den Schriftsaetzen, und das ist der falsche Ort dafuer.
        #
        # GELESEN werden die Fassungen mit Zeitstempel weiter: Wo welche
        # liegen, sollen sie nicht verlorengehen. Nur geschrieben wird wieder
        # unter dem einen Namen.
        #
        # Die Folge, bewusst in Kauf genommen: Liegt schon eine Datei da,
        # laesst sich keine neue ablegen. Das Programm sagt es und arbeitet
        # weiter - die Akte wird dann neu eingelesen.
        name = GEDAECHTNIS_DATEI
        if self._gedaechtnis_dateien(ordner_id):
            raise JurNodesFehler(
                "In dieser Akte liegt bereits ein Aktengedächtnis, und "
                "jur|nodes ersetzt eine vorhandene Datei nicht - es weist sie "
                f"ab. Solange {GEDAECHTNIS_DATEI} dort liegt, lässt sich keine "
                "neue Fassung ablegen. Es geht nichts verloren: Die Akte wird "
                "beim nächsten Mal neu eingelesen. Abhilfe: die Datei in "
                "jur|nodes entfernen, oder das Aktengedächtnis an einem "
                "anderen Ort führen (JUSPERFECT_GEDAECHTNIS).")
        pfad = self._endpunkte.datei_hinzufuegen
        try:
            with self._nacheinander:
                antwort = self._client.post(
                    pfad,
                    # autoRenameIfExist=false: Eine zweite Datei daneben waere
                    # das Gegenteil dessen, was gemeint ist. Laesst der Server
                    # das Ersetzen nicht zu, soll er abweisen - dann merken wir
                    # es hier und nicht in drei Wochen an zwanzig Dateien.
                    headers={**self._kopf(pfad),
                             "folderId": str(ordner_id),
                             "autoRenameIfExist": "false"},
                    files={"file": (name, rohdaten, "application/gzip")},
                )
        except httpx.HTTPError as e:
            raise JurNodesFehler(f"jur|nodes nicht erreichbar ({type(e).__name__}).") from e
        if antwort.status_code in (401, 403):
            raise JurNodesFehler(
                f"jur|nodes lässt das Ablegen der Datei nicht zu (POST {pfad}, "
                f"Status {antwort.status_code}). Dem Schlüssel fehlt im Bereich "
                "Dateisystem das Recht zum Erzeugen einer Datei.")
        if antwort.status_code == 405:
            # 405 heisst bei jur|nodes NICHT "den Pfad gibt es nicht fuer
            # diese Methode". Seine eigene Beschreibung fuehrt den Code
            # 94mal - jedesmal als "Ungueltige Eingabe", keinmal anders. Ein
            # fehlendes Recht beantwortet derselbe Server mit 401.
            #
            # Bis zum 25.09.2026 wurde die Zahl nach der Norm gelesen. Daraus
            # folgte zwei Tage lang die Suche nach dem Pfad - und der war die
            # ganze Zeit richtig; OPTIONS nennt fuer diesen Pfad ausdruecklich
            # POST. Die Zahl zeigt auf einen einzelnen Wert, nicht auf den Weg.
            #
            # Welcher es ist, sagt der Server im Feld "error". Der Wortlaut
            # wird hier mitgegeben, aber nicht angezeigt: Er kommt von einem
            # fremden Server, und hier stehen echte Akten daneben. Die
            # Ablageprobe holt ihn sich ab - siehe werkzeug/ablageprobe.py.
            erlaubt = antwort.headers.get("allow", "").strip()
            wenn_erlaubt = (f" Der Server nimmt dort an: {erlaubt}." if erlaubt
                            else " Der Server sagt nicht, was er dort annimmt.")
            raise JurNodesFehler(
                f"jur|nodes hat das Ablegen abgelehnt (POST {pfad}, Status "
                "405). Bei diesem Hersteller heißt 405 nicht 'falscher Weg', "
                "sondern 'ungültige Eingabe' - eine der mitgeschickten "
                "Angaben nimmt der Server nicht an." + wenn_erlaubt +
                " Was genau ihm fehlt, sagt er im Wortlaut; den zeigt "
                "ABLAGE-PRUEFEN.bat. Weicht der Pfad wider Erwarten doch ab, "
                "lässt er sich ohne Programmänderung richtigstellen - in der "
                "Datei unter JUSPERFECT_JURNODES_ENDPUNKTE, Eintrag "
                "datei_hinzufuegen.",
                serverwort=serverwort(antwort))
        if antwort.status_code >= 400:
            raise JurNodesFehler(
                f"jur|nodes hat das Aktengedächtnis abgelehnt "
                f"(POST {pfad}, Status {antwort.status_code}).",
                serverwort=serverwort(antwort))
        # Was gerade geschrieben wurde, darf nicht aus dem Puffer kommen.
        self._puffer_leeren()

        # Keine Nachpruefung mehr. Sie kostete eine zweite Abfrage, und was
        # sie feststellte - "es liegen jetzt zwei da" - ist seit dem
        # 25.09.2026 der gewollte Zustand und kein Fehler.
        #
        # Wie viele Fassungen es sind, faellt beim naechsten LESEN ohnehin an
        # (siehe letzte_fassungen); daraus macht der Gedaechtnisdienst einen
        # Hinweis, wenn es zu viele werden.

    def gedaechtnis_loeschen(self, akte_id: str) -> None:
        # Loeschen gibt es ueber diese Schnittstelle nicht, und das ist eine
        # Festlegung und kein Versaeumnis: Das Recht "Datei loeschen" gaelte
        # fuer JEDE Datei der Kanzlei, nicht nur fuer diese eine. Dafuer ist
        # der Preis zu hoch.
        #
        # Der Abschlussworkflow braucht das Loeschen. Wer es ueber diesen Weg
        # braucht, muss es in jur|nodes von Hand tun - eine Datei, ein
        # bekannter Name, und der Nachweis darueber entsteht ohnehin dort.
        raise JurNodesFehler(
            "Über die jur|nodes-Schnittstelle löscht jusperfect nichts – auch "
            "das Aktengedächtnis nicht. Es liegt als Datei "
            f"{GEDAECHTNIS_DATEI} im Dateiordner der Akte und ist dort von "
            "Hand zu entfernen.")
