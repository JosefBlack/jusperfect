"""Antwortet die jur|nodes-Schnittstelle – und wie heißen die Felder?

**Warum es dieses Werkzeug gibt.** Der Hersteller bestätigt eine offene
REST-Schnittstelle, stellt die Dokumentation aber auf dem jeweiligen
Kundenserver bereit; uns liegt sie nicht vor. Die Pfade in
``jurnodes/http_adapter.py::Endpunkte`` sind deshalb eine plausible Annahme und
ausdrücklich keine Zusage.

Geraten wird hier nichts. Stattdessen wird **gefragt**: Dieses Programm ruft
jeden Pfad einmal auf, sagt, was geantwortet hat, und schreibt die Feldnamen
hin, die in der Antwort stehen. Aus „wir brauchen erst die Dokumentation" wird
damit „starten Sie das und schicken Sie mir die Ausgabe" – fünf Minuten statt
einer Woche Wartezeit.

**Es liest nur.** Kein Schreiben, kein Anlegen, kein Löschen. Der einzige
schreibende Pfad der Schnittstelle (der Vermerk) wird ausdrücklich nicht
angefasst; er steht nur als Zeile in der Aufstellung, damit man sieht, dass er
vorgesehen ist.

**Kein Akteninhalt in der Ausgabe.** Sie wird verschickt – an die Entwicklung,
vielleicht an den Hersteller. Deshalb erscheinen hier Feld*namen*, Anzahl und
Datentyp, niemals Werte. Ein Aktenzeichen, das als Beispiel gebraucht wird,
gibt der Bearbeiter selbst an; es steht dann in seiner eigenen Ausgabe.

Aufruf:

    python -m jusperfect.jurnodestest                 # nur Aktensuche
    python -m jusperfect.jurnodestest --akte 115/26   # auch die Akte selbst
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jusperfect.jurnodes.base import serverwort

TRENNER = "─" * 70


def _sagen(zeichen: str, text: str) -> None:
    print(f"  {zeichen}  {text}")


def _umbrechen(text: str, breite: int = 64) -> list[str]:
    zeilen, zeile = [], ""
    for wort in text.split():
        if len(zeile) + len(wort) + 1 > breite:
            zeilen.append(zeile)
            zeile = wort
        else:
            zeile = f"{zeile} {wort}".strip()
    if zeile:
        zeilen.append(zeile)
    return zeilen


def felder(daten: Any, tiefe: int = 0) -> list[str]:
    """Die Feldnamen einer Antwort – Namen und Arten, keine Werte.

    Das ist der eigentliche Zweck: Ob jur|nodes ein Aktenzeichen „aktenzeichen",
    „az" oder „fileNumber" nennt, entscheidet über die Zuordnung in
    ``http_adapter.py`` – und steht in keiner Vermutung, sondern nur in einer
    echten Antwort.
    """
    if isinstance(daten, list):
        if not daten:
            return ["(leere Liste)"]
        return felder(daten[0], tiefe)
    if not isinstance(daten, Mapping):
        return [f"({type(daten).__name__})"]
    zeilen = []
    for name, wert in list(daten.items())[:40]:
        art = type(wert).__name__
        if isinstance(wert, Mapping):
            art = "Objekt"
        elif isinstance(wert, list):
            # Wovon eine Liste ist, entscheidet hier alles.
            #
            # "todoFolder (Liste[1])" stand am 01.10.2026 im Bericht, und die
            # Probe ging nicht hinein: Sie steigt nur in Listen von Objekten
            # ab. Steht darin eine Ordnernummer, fuehrt sie zum Vermerk - und
            # genau das war nicht zu sehen. Eine Liste ohne Angabe ihres
            # Inhalts ist eine Auskunft, die keine ist.
            inhalt = type(wert[0]).__name__ if wert else ""
            art = f"Liste[{len(wert)}]" + (f" von {inhalt}" if inhalt and not
                                           isinstance(wert[0], (Mapping, list)) else "")
        zeilen.append(f"{name} ({art})")

    # In die Trefferliste hineinsehen, nicht nur auf die Huelle.
    #
    # Eine Seitenantwort dieses Herstellers lautet {amountTotal, pagesTotal,
    # elements}. Genau das stand bisher im Bericht - drei Zeilen, die ueber
    # jede Akte dasselbe sagen. Die Feldnamen, derentwegen die Probe
    # ueberhaupt laeuft, stehen eine Ebene tiefer.
    #
    # Am 28.09.2026 wurde deshalb die Frage "wie heisst die Zahl, die
    # /record/note haben will?" nicht beantwortet, obwohl die Antwort
    # vermutlich schon auf dem Schirm stand - eine Ebene unter dem, was
    # gezeigt wurde.
    # Zwei Ebenen, nicht eine.
    #
    # Am 01.10.2026 brachte /todo/search mit type=task zehn Eintraege zu einer
    # Akte - und darin "todoFolder (Liste[1])". Was in diesem Ordner steht,
    # koennte der gesuchte Vermerk sein; gezeigt wurde nur, DASS es ihn gibt.
    # Eine Probe, die eine Ebene zu frueh aufhoert, beantwortet die Frage
    # knapp daneben.
    if tiefe < 2:
        for name, wert in daten.items():
            if isinstance(wert, list) and wert and isinstance(wert[0], Mapping):
                zeilen.append(f"{name}[0] enthält:")
                zeilen += [f"   {z}" for z in felder(wert[0], tiefe + 1)]
                break
            if isinstance(wert, Mapping) and wert:
                zeilen.append(f"{name} enthält:")
                zeilen += [f"   {z}" for z in felder(wert, tiefe + 1)]
                break
    return zeilen


def _pruefen(client: Any, name: str, pfad: str, **params: Any) -> bool:
    """Einen Pfad aufrufen und in ganzen Sätzen sagen, was geschah."""
    import httpx

    print()
    _sagen("→", f"{name}: GET {pfad}" + (f"  ?{params}" if params else ""))
    try:
        antwort = client.get(pfad, params=params or None)
    except httpx.HTTPError as fehler:
        _sagen("✗", f"Nicht erreichbar ({type(fehler).__name__}).")
        return False

    if antwort.status_code == 404:
        _sagen("✗", "Status 404 – diesen Pfad gibt es so nicht.")
        _sagen(" ", "Das ist der erwartete Fall, solange die Pfade geraten sind.")
        _sagen(" ", "Den richtigen Pfad in die Datei unter "
                    "JUSPERFECT_JURNODES_ENDPUNKTE eintragen.")
        return False
    if antwort.status_code in (401, 403):
        _sagen("✗", f"Status {antwort.status_code} – abgelehnt (Token oder Berechtigung).")
        _wortlaut(antwort)
        return False
    if antwort.status_code >= 400:
        _sagen("✗", f"Status {antwort.status_code}.")
        if antwort.status_code == 405:
            _sagen(" ", HINWEIS_405)
        _wortlaut(antwort)
        return False

    try:
        daten = antwort.json()
    except ValueError:
        _sagen("!", f"Status {antwort.status_code}, aber die Antwort ist kein JSON "
                    f"({antwort.headers.get('content-type', 'ohne Angabe')}).")
        return False

    anzahl = len(daten) if isinstance(daten, list) else 1
    _sagen("✓", f"Status {antwort.status_code}, {anzahl} Eintrag/Einträge.")
    _sagen(" ", "Felder des ersten Eintrags:")
    for zeile in felder(daten):
        _sagen(" ", f"     {zeile}")
    return True


_serverwort = serverwort


def _wortlaut(antwort: Any) -> None:
    """Den Satz des Servers ausgeben, falls er einen mitgeschickt hat."""
    satz = _serverwort(antwort)
    if satz:
        _sagen(" ", f"Der Server sagt dazu: {satz}")


#: Was die Zahl 405 bei diesem Hersteller bedeutet - und was nicht.
HINWEIS_405 = ("405 heisst bei jur|nodes nicht \"diesen Weg gibt es nicht\", "
               "sondern \"ungueltige Eingabe\".")


def _methoden(client: Any, name: str, pfad: str) -> None:
    """Fragt mit OPTIONS, welche Methoden ein Pfad annimmt. Schreibt nichts."""
    try:
        antwort = client.request("OPTIONS", pfad)
    except Exception as fehler:
        _sagen("!", f"{name} ({pfad}): {type(fehler).__name__}")
        return
    erlaubt = antwort.headers.get("allow", "").strip()
    if erlaubt:
        _sagen("✓", f"{name} ({pfad}): {erlaubt}")
    else:
        _sagen("!", f"{name} ({pfad}): Status {antwort.status_code}, "
                    "keine Auskunft ueber die Methoden")


def _zaehlen(client: Any, was: str, pfad: str, zeige_felder: bool = False,
             **params: Any) -> None:
    """Eine Abfrage stellen und sagen, wie viele Eintraege kamen.

    ``zeige_felder`` nennt zusaetzlich die Feldnamen des ersten Treffers. Das
    ist nicht ueberall erwuenscht - beim Zaehlen von Dokumenten waeren es
    fuenfzig gleiche Bloecke -, aber dort, wo ein Pfad zum ersten Mal etwas
    herausgibt, ist es das Einzige, worauf es ankommt.
    """
    try:
        antwort = client.get(pfad, params=params)
    except Exception as fehler:
        _sagen("✗", f"{was}: {type(fehler).__name__}")
        return
    if antwort.status_code >= 400:
        _sagen("✗", f"{was}: Status {antwort.status_code}")
        _wortlaut(antwort)
        return
    try:
        daten = antwort.json()
    except ValueError:
        _sagen("!", f"{was}: Status {antwort.status_code}, keine JSON-Antwort")
        return
    eintraege = daten.get("elements") if isinstance(daten, Mapping) else daten
    anzahl = len(eintraege) if isinstance(eintraege, list) else 0
    gesamt = daten.get("amountTotal") if isinstance(daten, Mapping) else None
    zusatz = f", amountTotal {gesamt}" if gesamt is not None else ""
    _sagen("✓" if anzahl else "!", f"{was}: {anzahl} Eintrag/Einträge{zusatz}")
    if zeige_felder and anzahl:
        for zeile in felder(daten):
            _sagen(" ", f"     {zeile}")


#: Namen, unter denen GET /record/note die Akte annehmen koennte.
#:
#: Zusammengetragen aus dem Wortschatz des Herstellers selbst, nicht erfunden:
#:
#: * ``id`` und ``record`` stehen in SEINER Beschreibung zu diesem Pfad. ``id``
#:   war am 28.09.2026 noch nie probiert - ein Versaeumnis, denn es ist der
#:   erste Kandidat ueberhaupt.
#: * ``recordIdentifier`` nennen /relation/search und /todo/search.
#: * ``identifier`` nennt /record.
#: * ``sign`` nennt /record/search, ``recordSign`` heisst das Feld in der
#:   Antwort.
#: * ``recordId``, ``noteIdentifier``, ``note`` sind die naheliegenden
#:   Schreibweisen daneben.
#: * ``data`` steht hier, weil die Abweisung wortwoertlich "Bitte Daten
#:   angeben" lautet. Vielleicht meint sie genau das.
_VERMERK_NAMEN = ("id", "record", "recordIdentifier", "identifier", "recordId",
                  "noteIdentifier", "note", "sign", "recordSign", "data")


#: Felder, unter denen ein Eintrag seine Akte nennen koennte.
#:
#: Zusammengetragen aus dem Wortschatz des Herstellers, nicht erfunden:
#: ``recordIdentifier`` nennen /relation/search und /todo/search,
#: ``identifier`` nennt /record, ``recordSign`` heisst das Aktenzeichen in der
#: Antwort. Der Rest sind die naheliegenden Schreibweisen daneben.
_AKTENFELDER = ("recordIdentifier", "recordId", "recordSign", "record",
                "caseId", "caseIdentifier", "akte", "parentRecord")

#: Felder, in denen ein Eintrag seinen UEBERGEORDNETEN Ordner nennt.
#:
#: ``parentFolder`` steht an erster Stelle, weil es der Name ist, den der
#: Server wirklich fuehrt - der Lauf vom 02.10.2026 hat ihn gezeigt. In der
#: ersten Fassung dieser Liste stand er NICHT, und damit lief die Pruefung
#: "liegt dieser Ordner wirklich dort, wo wir ihn gefunden haben?" ins Leere,
#: ohne es zu sagen.
#:
#: Dieselbe Form wie so oft an diesem Tag: Eine Probe, die nach einem Namen
#: sucht, den es nicht gibt, meldet nicht "nichts gefunden", sondern
#: schweigt - und Schweigen liest sich wie Entwarnung.
_ELTERNFELDER = ("parentFolder", "parentFolderId", "parentId", "parent",
                 "folderParentId", "upperFolderId")


def _verdeckt(wert: Any) -> str:
    """Einen Wert so zeigen, dass man ihn wiedererkennt, aber nicht liest.

    ``041234/22`` wird zu ``041…(9)``. Das genuegt, um zwei Werte zu
    unterscheiden und um zu sehen, dass einer nicht zur gefragten Akte gehoert
    - und es nennt keine fremde Akte beim Namen. Diese Ausgabe wird
    verschickt.
    """
    text = str(wert)
    return f"{text[:3]}…({len(text)})" if len(text) > 3 else f"…({len(text)})"


def _erste(eintrag: Any, namen: tuple[str, ...]) -> tuple[str, Any] | None:
    """Das erste dieser Felder, das im Eintrag steht - samt seinem Wert."""
    if not isinstance(eintrag, Mapping):
        return None
    for name in namen:
        if name in eintrag and eintrag[name] not in (None, ""):
            wert = eintrag[name]
            if isinstance(wert, Mapping):
                for innen in ("identifier", "id", "recordSign"):
                    if innen in wert:
                        return f"{name}.{innen}", wert[innen]
                continue
            return name, wert
    return None


#: Die Schreibweisen, in denen jur|nodes ein Datum liefert.
#:
#: ``addedDate`` kommt als ISO (``2022-12-15T09:14:00``). ``creationDate``
#: kommt als Wortform - und zwar in der von JavaScript, mit dem Jahr VOR der
#: Uhrzeit:
#:
#:     Thu Jul 30 2026 17:42:18 GMT+0000 (Coordinated Universal Time)
#:
#: Die Java-Form stellt das Jahr dagegen ans Ende (``Thu Jul 30 00:00:00 CEST
#: 2026``). Beide werden gelesen: Welche ein Server schickt, ist seine Sache,
#: und am 05.10.2026 hat die Annahme "das Jahr steht hinten" einen Lauf
#: gekostet.
_MONATE = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
#: Wochentag, Monat, Tag - dann entweder gleich das Jahr (JavaScript) oder
#: die Uhrzeit und das Jahr am Ende (Java).
_WORTFORM = re.compile(
    r"^[A-Za-z]{3}\s+([A-Za-z]{3})\s+(\d{1,2})\s+"
    r"(?:(\d{4})\b|\d{1,2}:\d{2}.*?(\d{4})(?:\s|$))")


def _als_tag(wert: Any) -> str:
    """Aus einem Datum des Servers ``JJJJ-MM-TT`` machen - oder „" .

    Leer heisst: nicht verstanden. Dann wird damit nicht gerechnet. Das ist
    der Punkt dieser Funktion, und er hat am 05.10.2026 einen Fehlalarm
    gekostet: Die ersten zehn Zeichen von ``Thu Jul 30 00:00:00 CEST 2026``
    sind ``Thu Jul 30``, und ein Vergleich Zeichen gegen Zeichen stellt jede
    Ziffer vor jeden Buchstaben. Damit galt jeder Ordner als aelter als die
    Akte - auch die, die es erst seit 2026 gibt.
    """
    text = str(wert or "").strip()
    treffer = _ISO.match(text)
    if treffer:
        return f"{treffer.group(1)}-{treffer.group(2)}-{treffer.group(3)}"
    treffer = _WORTFORM.match(text)
    if treffer:
        monat = _MONATE.get(treffer.group(1).lower())
        jahr = treffer.group(3) or treffer.group(4)
        if monat and jahr:
            return f"{jahr}-{monat:02d}-{int(treffer.group(2)):02d}"
    return ""


def _ordnerbaum(client: Any, endpunkte: Any, kennung: str,
                tiefe_hoechstens: int = 6, ordner_hoechstens: int = 60) -> None:
    """Welchen Ordnerbaum geht das Programm ab - und bleibt er in der Akte?

    **Warum es diese Probe gibt.** Aus der Kanzlei am 02.10.2026: In der
    Arbeitsakte einer Bausache standen drei Schriftstuecke aus einer fremden
    Verkehrsunfallsache. „Es ist nicht ersichtlich, wie diese Sachen
    hineingekommen sind."

    Das Programm holt die Dokumente nicht ueber die Akte, sondern ueber deren
    Dateiordner, und steigt in Unterordner hinab. Zwei Erklaerungen sind
    moeglich, und sie verlangen entgegengesetzte Handgriffe:

    1. Die Schriftstuecke liegen wirklich dort - dann ist in jur|nodes falsch
       abgelegt worden, und am Programm ist nichts zu aendern.
    2. Der Durchlauf verlaesst die Akte - etwa weil der Inhalt eines Ordners
       auch den UEBERGEORDNETEN Ordner auffuehrt. Dann steigt er einmal hinauf
       und von dort in fremde Akten hinab. Das waere ein schwerer Fehler, und
       zwar meiner.

    Diese Probe entscheidet das. Sie geht denselben Weg wie der Betrieb und
    schreibt auf, was sie dabei sieht.

    **Kein Akteninhalt in der Ausgabe.** Keine Dateinamen, keine Titel. Was ein
    Eintrag ueber seine Akte sagt, erscheint verdeckt (``041…(9)``) - das
    genuegt, um „gehoert nicht zur gefragten Akte" zu zeigen, und nennt keine
    fremde Akte beim Namen.
    """
    print()
    _sagen(" ", "Der Ordnerbaum dieser Akte - derselbe Weg wie im Betrieb:")

    try:
        antwort = client.get(endpunkte.akte,
                             params={endpunkte.kennungparameter: kennung})
        akte = antwort.json() if antwort.status_code < 400 else None
    except Exception as fehler:
        _sagen("✗", f"Die Akte liess sich nicht lesen ({type(fehler).__name__}).")
        return
    if not isinstance(akte, Mapping):
        _sagen("✗", "Die Akte antwortet nicht mit einem Datensatz.")
        return

    wurzeln = [(name, akte.get(name)) for name in
               ("fileFolderId", "correspondenceFolderId") if akte.get(name)]
    if not wurzeln:
        _sagen("!", "Die Akte nennt keinen Dateiordner - nichts zu durchlaufen.")
        return
    for name, wert in wurzeln:
        _sagen(" ", f"     {name}: {wert}")
    # Die Probe zeigt beide Ordner, der Betrieb liest seit dem 05.10.2026 nur
    # einen. Ohne diesen Satz liest jemand den Baum und schliesst daraus auf
    # die Arbeitsakte - und zaehlt Dokumente mit, die dort nicht ankommen.
    if any(name == "correspondenceFolderId" for name, _ in wurzeln):
        _sagen(" ", "     (Den Korrespondenzordner zeigt diese Probe, der Betrieb")
        _sagen(" ", "      liest ihn seit dem 05.10.2026 nicht mehr mit.)")
    # Wann wurde die Akte angelegt? Ein Datum, kein Akteninhalt - und die
    # Angabe, gegen die sich alles andere messen laesst. Eine Datei kann nicht
    # abgelegt worden sein, bevor es die Akte gab.
    roh_datum = str(akte.get("creationDate") or "")
    angelegt = _als_tag(roh_datum)
    if angelegt:
        _sagen(" ", f"     Akte angelegt am: {angelegt}")
    elif roh_datum:
        # Kein Urteil ohne verstandenes Datum. Am 05.10.2026 stand hier
        # "Thu Jul 30" - die ersten zehn Zeichen von "Thu Jul 30 00:00:00
        # CEST 2026" -, und der Vergleich lief Zeichen gegen Zeichen statt
        # Datum gegen Datum. Jede Ziffer steht vor jedem Buchstaben, also galt
        # JEDER Ordner als aelter als die Akte, auch die aus 2026.
        _sagen("!", "Das Anlagedatum der Akte ist nicht zu lesen: "
                    f"\u201e{roh_datum[:40]}\u201c")
        _sagen(" ", "     Ohne verstandenes Datum wird hier nichts verglichen.")

    # Die eigenen Kennungen der Akte, gegen die verglichen wird.
    eigene = {str(akte.get(f)) for f in ("identifier", "recordSign", "id")
              if akte.get(f)} | {str(kennung)}

    # Wurzel fuer Wurzel, nicht beide in einer Schlange.
    #
    # Der Lauf vom 05.10.2026 hat gezeigt, dass das ein Unterschied ist: Die
    # Probe ging erst beide Wurzeln ab, dann deren Unterordner, und nummerierte
    # danach. dokumente() im Betrieb geht den Dateiordner VOLLSTAENDIG ab und
    # dann erst die Korrespondenz. Bei der Akte X-100-2026 glichen sich die
    # Unterschiede zufaellig wieder aus - ab D40 stand in beiden dasselbe. Auf
    # diesen Zufall ist kein Verlass: Eine Probe, die anders zaehlt als der
    # Betrieb, nennt irgendwann den falschen Ordner, und niemand merkt es.
    gesehen: set[str] = set()
    schlangen: list[list[tuple[Any, int, Any]]] = [[(w, 0, "(Akte)")] for _, w in wurzeln]
    offen: list[tuple[Any, int, Any]] = []
    dateien = fremde = ohne_angabe = 0
    fremde_werte: dict[str, int] = {}
    elternverweise: list[str] = []
    dateifelder: list[str] = []
    #: Je Ordner die Tage, an denen dort abgelegt wurde.
    daten_je_ordner: dict[str, list[str]] = {}
    #: Welche Dokumentnummern aus welchem Ordner stammen.
    #:
    #: Das Programm nummeriert in der Reihenfolge, in der es liest - erst der
    #: Dateiordner mit seinen Unterordnern, dann die Korrespondenz. Wer eine
    #: Fundstelle wie D47 vor sich hat, soll hier ablesen koennen, in welchem
    #: Ordner sie liegt, statt es nachrechnen zu muessen.
    nummern: list[tuple[Any, int, int]] = []
    laufend = 0
    zeilen = 0

    while (offen or schlangen) and len(gesehen) < ordner_hoechstens:
        if not offen:
            offen = schlangen.pop(0)
            continue
        ordner_id, tiefe, von = offen.pop(0)
        if str(ordner_id) in gesehen:
            continue
        gesehen.add(str(ordner_id))
        try:
            antwort = client.get(endpunkte.ordner_inhalt,
                                 params={endpunkte.ordnerparameter: ordner_id,
                                         "page": 1})
            daten = antwort.json() if antwort.status_code < 400 else None
        except Exception as fehler:
            _sagen("✗", f"     Ordner {ordner_id}: {type(fehler).__name__}")
            continue
        if daten is None:
            _sagen("!", f"     Ordner {ordner_id}: Status {antwort.status_code}")
            continue
        eintraege = daten.get("elements") if isinstance(daten, Mapping) else daten
        eintraege = eintraege if isinstance(eintraege, list) else []

        unterordner = [e for e in eintraege
                       if isinstance(e, Mapping) and e.get("type") == "folder"]
        dateieintraege = [e for e in eintraege if e not in unterordner]
        if dateieintraege:
            nummern.append((ordner_id, laufend + 1, laufend + len(dateieintraege)))
            laufend += len(dateieintraege)
        if zeilen < 40:
            zeilen += 1
            _sagen(" ", f"     Tiefe {tiefe}, Ordner {ordner_id} (aus {von}): "
                        f"{len(dateieintraege)} Datei(en), "
                        f"{len(unterordner)} Unterordner")

        for eintrag in dateieintraege:
            dateien += 1
            roh = eintrag.get("file") if isinstance(eintrag, Mapping) else None
            quelle = roh if isinstance(roh, Mapping) else eintrag
            # Einmal zeigen, WELCHE Felder eine Datei ueberhaupt hat. Ohne das
            # bleibt "nennt ihre Akte nicht" eine Behauptung: Vielleicht heisst
            # das Feld nur anders, als diese Probe erwartet - genau das ist mit
            # parentFolder passiert.
            if not dateifelder and isinstance(quelle, Mapping):
                dateifelder.extend(sorted(quelle))
            # WANN wurde abgelegt? Das ist die Angabe, die ein falsch
            # einsortierter Ordner verraet: Dateien von 2022 in einer Akte
            # von 2026. Ein Datum ist kein Akteninhalt - es nennt weder
            # Mandanten noch Gegenstand - und beantwortet hier die Frage,
            # die ein Dateiname auch nicht besser beantworten wuerde.
            wann = quelle.get("addedDate") if isinstance(quelle, Mapping) else None
            tag = _als_tag(wann)
            if tag:
                daten_je_ordner.setdefault(str(ordner_id), []).append(tag)
            treffer = _erste(quelle, _AKTENFELDER)
            if treffer is None:
                ohne_angabe += 1
                continue
            _, wert = treffer
            if str(wert) not in eigene:
                fremde += 1
                marke = _verdeckt(wert)
                fremde_werte[marke] = fremde_werte.get(marke, 0) + 1

        if tiefe >= tiefe_hoechstens:
            continue
        for eintrag in unterordner:
            unter = eintrag.get("folder")
            if not isinstance(unter, Mapping):
                continue
            # Nennt der Eintrag einen uebergeordneten Ordner? Dann steht genau
            # hier die Antwort auf die Frage des Tages.
            eltern = _erste(unter, _ELTERNFELDER) or _erste(eintrag, _ELTERNFELDER)
            if eltern and str(eltern[1]) == str(ordner_id):
                pass            # der erwartete Fall: er nennt den, in dem er liegt
            elif eltern:
                elternverweise.append(
                    f"Ordner {unter.get('id')} nennt {eltern[0]}={eltern[1]}, "
                    f"liegt aber in {ordner_id}")
            if unter.get("canRead") is False:
                continue
            nummer = unter.get("id")
            if nummer is not None and str(nummer) not in gesehen:
                offen.append((nummer, tiefe + 1, ordner_id))

    print()
    # Ordner, in denen abgelegt wurde, BEVOR es die Akte gab.
    #
    # Aus der Kanzlei am 05.10.2026: In der Arbeitsakte einer Bausache standen
    # Schriftstuecke aus einer fremden Verkehrsunfallsache. Der Lauf zeigte,
    # dass der ganze Korrespondenzzweig aus 2022/23 stammt, waehrend der
    # Dateiordner aus 2026 ist - und die Akte selbst eine von 2026.
    #
    # Die Folgerung ist schlicht und haelt: Eine Datei kann nicht in eine Akte
    # gelegt worden sein, die es noch nicht gab. Wo das trotzdem dasteht, ist
    # der Ordner nicht fuer diese Akte angelegt worden.
    zu_alt = [(o, min(t)) for o, t in daten_je_ordner.items()
              if angelegt and min(t) < angelegt]
    if zu_alt:
        _sagen("✗", f"{len(zu_alt)} Ordner wurden befuellt, BEVOR es diese Akte gab "
                    f"(angelegt {angelegt}):")
        for ordner_id, frueheste in sorted(zu_alt, key=lambda x: x[1]):
            _sagen(" ", f"     Ordner {ordner_id}: erste Ablage {frueheste}")
        _sagen(" ", "     Eine Datei kann nicht in eine Akte gelegt worden sein,")
        _sagen(" ", "     die es noch nicht gab. Diese Ordner sind nicht fuer")
        _sagen(" ", "     diese Akte angelegt worden - zu klaeren in jur|nodes.")
        print()
    if nummern:
        _sagen(" ", "Welche Dokumentnummer aus welchem Ordner stammt:")
        for ordner_id, von_nr, bis_nr in nummern:
            spanne = f"D{von_nr}" if von_nr == bis_nr else f"D{von_nr}–D{bis_nr}"
            tage = sorted(daten_je_ordner.get(str(ordner_id), []))
            wann = ""
            if tage:
                wann = (f"  abgelegt {tage[0]}" if tage[0] == tage[-1]
                        else f"  abgelegt {tage[0]} bis {tage[-1]}")
            _sagen(" ", f"     Ordner {ordner_id}: {spanne}{wann}")
        _sagen(" ", "     (Reihenfolge wie beim Lesen. Ein uebersprungenes")
        _sagen(" ", "      Dokument verschiebt alles danach um eins.)")
        print()
    if dateifelder:
        _sagen(" ", "Felder, die eine Datei fuehrt (nur Namen):")
        _sagen(" ", f"     {', '.join(dateifelder)}")
        print()
    _sagen(" ", f"Durchlaufen: {len(gesehen)} Ordner, {dateien} Datei(en).")
    if ohne_angabe:
        _sagen(" ", f"     {ohne_angabe} Datei(en) nennen ihre Akte gar nicht -")
        _sagen(" ", "     bei diesen kann die Probe nichts entscheiden.")
    if fremde:
        _sagen("✗", f"{fremde} Datei(en) nennen eine ANDERE Akte als die gefragte.")
        for marke, anzahl in sorted(fremde_werte.items(), key=lambda x: -x[1]):
            _sagen(" ", f"     {marke}: {anzahl}×")
        _sagen(" ", "     Damit verlaesst der Durchlauf die Akte. Das ist ein")
        _sagen(" ", "     Fehler des Programms und keine falsche Ablage.")
    elif dateien and not ohne_angabe:
        _sagen("✓", "Keine Datei nennt eine andere Akte - der Durchlauf bleibt drin.")
        _sagen(" ", "     Liegen trotzdem fremde Schriftstuecke in der Arbeitsakte,")
        _sagen(" ", "     sind sie in jur|nodes in dieser Akte abgelegt.")
    if elternverweise:
        print()
        _sagen("!", "Ordner, die anderswo zu liegen angeben, als sie gefunden wurden:")
        for zeile in elternverweise[:10]:
            _sagen(" ", f"     {zeile}")
    if len(gesehen) >= ordner_hoechstens:
        _sagen("!", f"Bei {ordner_hoechstens} Ordnern abgebrochen - der Baum ist groesser.")


def _statuswoerter(client: Any, endpunkte: Any, seiten: int = 3) -> None:
    """Welche Woerter fuehrt der Bestand im Aktenstatus - und wie oft?

    **Das ist der Probelauf fuer Ziffer 6.2 des Verarbeitungsverzeichnisses.**

    Die Aufbewahrung folgt dem Aktenstatus. Welche Woerter das Programm kennt,
    steht an genau einer Stelle: ``_STATUS`` in
    ``jusperfect/jurnodes/http_adapter.py``. Diese Probe fragt **jene** Tabelle
    und fuehrt keine eigene Liste mehr.

    **Warum nicht mehr.** Bis zum 07.10.2026 stand hier die Liste doppelt, und
    zwar in der alten Fassung: Sie kannte nur "archiviert" und "archived".
    Der Lauf vom 07.10.2026 meldete deshalb ``active: 10  <- kennt das
    Programm NICHT`` - obwohl ``_STATUS`` "active" seit dem 02.10.2026 fuehrt.
    Ein falscher Alarm in einem Bericht, der zur Entscheidung vorgelegt wird,
    ist schlimmer als keiner: Er kostet Vertrauen in die richtigen Zeilen
    daneben. Eine Kopie einer Tabelle veraltet; eine Abfrage nicht.

    Ein Wort, das ``_STATUS`` nicht kennt, wird im Programm "unbekannt" - nicht
    "laufend". Dann wird nichts geloescht, und ``services/aufsicht.py`` legt
    die Akte einem Menschen vor. Das ist der gewollte Weg, kein Mangel.

    Welche Woerter der Server wirklich fuehrt, stand in keinem Bericht: Die
    Probe zeigte den Feldnamen, nicht den Wert. Gefragt wird deshalb die
    Aktenliste, nicht eine einzelne Akte - hundert Akten je Seite, und damit
    in drei Anfragen ein Querschnitt des Bestands statt einer Stichprobe von
    eins.

    Gezaehlt wird, nicht gelesen: Status und Anzahl, kein Aktenzeichen, kein
    Rubrum, kein Inhalt.
    """
    _sagen(" ", "Welche Woerter fuehrt der Aktenstatus im Bestand?")
    _sagen(" ", "(Ziffer 6.2: daran haengt die Aufbewahrung. Nur Wort und Anzahl.)")
    gezaehlt: dict[str, int] = {}
    gesehen = 0
    for seite in range(1, seiten + 1):
        try:
            antwort = client.get(endpunkte.akten_suche,
                                 params={endpunkte.suchparameter: "%", "page": seite})
            daten = antwort.json() if antwort.status_code < 400 else None
        except Exception as fehler:
            _sagen("!", f"Seite {seite}: {type(fehler).__name__}")
            break
        if not isinstance(daten, Mapping):
            break
        eintraege = daten.get("elements") or []
        if not eintraege:
            break
        for eintrag in eintraege:
            if not isinstance(eintrag, Mapping):
                continue
            gesehen += 1
            wort = str(eintrag.get("status", "")).strip() or "(leer)"
            gezaehlt[wort[:40]] = gezaehlt.get(wort[:40], 0) + 1

    if not gezaehlt:
        _sagen("!", "Der Bestand gab keinen Status heraus.")
        return
    # Die Tabelle des Programms, nicht eine Kopie davon.
    from jusperfect.jurnodes.http_adapter import _STATUS

    _sagen("✓", f"{gesehen} Akten angesehen:")
    for wort, anzahl in sorted(gezaehlt.items(), key=lambda p: -p[1]):
        uebersetzt = _STATUS.get(wort.lower())
        _sagen("✓" if uebersetzt else "!",
               f"     {wort}: {anzahl}"
               + (f"   -> {uebersetzt}" if uebersetzt
                  else "   <- kennt das Programm NICHT"))
    unbekannt = [w for w in gezaehlt if w.lower() not in _STATUS]
    if unbekannt:
        _sagen(" ", "Woerter mit Pfeil werden im Programm „unbekannt\": Eine solche")
        _sagen(" ", "Akte wird NICHT geloescht, und die Aufsicht legt sie einem")
        _sagen(" ", "Menschen vor. Ist ein Wort ein abgeschlossener Zustand, gehoert")
        _sagen(" ", "es in _STATUS und in Ziffer 6.2 - sonst bleibt es beim Vorlegen.")


def _zahlen_der_akte(client: Any, endpunkte: Any, kennung: str) -> list[tuple[str, int]]:
    """Die Zahlen, die der Server SELBST zu dieser Akte fuehrt.

    Der Server sagte am 28.09.2026 zu ``id``: "Value (...) cannot be parsed
    into number." Er kennt den Parameter also und will eine Zahl. Die Akte hat
    zwei Kennungen, und keine davon ist eine - die Zahl muss woanders stehen.

    **Durchgezaehlt wird nicht.** 1, 2, 3 ... waere schnell geschrieben und in
    einer Mandatsakte das Falsche: Jede dieser Zahlen gehoert zu IRGENDEINER
    Akte des Hauses, und wer sie abruft, liest Vermerke fremder Mandate. Was
    hier probiert wird, sind allein die Zahlen, die der Server zu DIESER Akte
    selbst herausgibt.
    """
    pfad = getattr(endpunkte, "akte", "")
    name = getattr(endpunkte, "kennungparameter", "")
    if not pfad or not name:
        return []
    try:
        antwort = client.get(pfad, params={name: kennung})
        daten = antwort.json() if antwort.status_code < 400 else None
    except Exception:
        return []
    if not isinstance(daten, Mapping):
        return []

    gefunden: list[tuple[str, int]] = []
    gesehen: set[int] = set()

    def sammeln(raum: Mapping, vorsatz: str, tiefe: int) -> None:
        for name, wert in raum.items():
            # bool ist in Python eine Zahl - als Kennung ist es keine.
            if isinstance(wert, int) and not isinstance(wert, bool):
                if wert not in gesehen:
                    gesehen.add(wert)
                    gefunden.append((f"{vorsatz}{name}", wert))
            elif isinstance(wert, Mapping) and tiefe < 1:
                sammeln(wert, f"{vorsatz}{name}.", tiefe + 1)
    sammeln(daten, "", 0)
    return gefunden


#: Wo eine OpenAPI-Beschreibung ueblicherweise liegt.
#:
#: Der Hersteller stellt sie nur auf dem Kundenserver bereit - uns liegt sie
#: nicht vor, und die Regel lautet: bei Dritten warten, nicht raten. Der
#: Server der Kanzlei hat sie aber, und am 23.09.2026 hat die Kanzlei sie
#: schon einmal von dort geholt. Dann fragen wir ihn eben selbst, statt einen
#: weiteren Parameternamen zu erfinden.
_BESCHREIBUNGSPFADE = (
    "/openapi.json", "/swagger.json", "/v3/api-docs", "/api-docs",
    "/openapi", "/swagger/v1/swagger.json",
)


#: Woerter, an denen die E-Akte in einer Beschreibung zu erkennen waere.
#:
#: Aus der Kanzlei am 05.10.2026: "Die Korrespondenz bei jurnodes und die
#: Vermerke finden sich in der E-Akte." Damit ist es EINE Frage und nicht
#: zwei: Wer den Weg in die E-Akte kennt, hat beides.
#:
#: Gesucht wird in der Beschreibung des HERSTELLERS, nicht geraten. Wonach
#: gesucht wird, steht hier, damit es nachvollziehbar ist; was gefunden wird,
#: entscheidet die Datei und nicht diese Liste.
#: Verglichen wird ohne Trennzeichen: "/electronic-file/search" wird zu
#: "electronicfilesearch". Ohne diesen Schritt ging am 05.10.2026 beim ersten
#: Versuch genau der Pfad durch, auf den es ankam - der Hersteller schreibt
#: "electronic-file", die Liste hiess "electronicfile".
_EAKTE_WOERTER = (
    "eakte", "efile", "electronic", "elektronisch",
    "korrespondenz", "correspondence", "vermerk", "note", "mail", "posteingang",
    "schriftverkehr", "schriftstueck", "journal", "verlauf", "history",
)


def _ohne_trenner(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


#: Welches Recht ein Aufruf braucht - aus der Beschreibung gelesen.
#:
#: Der Hersteller nennt es zu JEDEM der 94 Aufrufe, aber im Fliesstext des
#: Feldes "description", hinter der Erlaeuterung:
#:
#:   "Listet alle Korrespondenzen (derzeit einer Akte) auf.
#:    Benoetigte Rechte: search:correspondence"
#:
#: Dort stand es vier Wochen lang, und dort wurde nicht gesucht. Der Lauf vom
#: 07.10.2026 bekam auf genau diesen Aufruf ein 401, und die Beschreibung
#: sagt zu 401: "Authentifizierung ungueltig". Die Antwort lag die ganze Zeit
#: in der Datei im Programmordner.
#:
#: Deshalb wird sie jetzt ausgelesen und mitgedruckt: Ein 401 soll nicht mehr
#: nach einem Raetsel aussehen, sondern das Recht beim Namen nennen.
_RECHTE: dict[tuple[str, str], str] = {}

_RECHTEMUSTER = re.compile(r"Ben[oö]tigte\s+Rechte:\s*(.+)", re.IGNORECASE)


def recht_fuer(pfad: str, art: str = "post") -> str:
    """Das Recht, das die Beschreibung zu diesem Aufruf nennt - oder "".

    Der Pfad wird auch ohne fuehrenden Schraegstrich gefunden: Bei einem von
    85 Pfaden fehlt er in der Beschreibung des Herstellers selbst
    (correspondence/get-by-reference).
    """
    for schluessel in ((pfad, art.lower()), (pfad.lstrip("/"), art.lower())):
        if schluessel in _RECHTE:
            return _RECHTE[schluessel]
    return ""


def _rechte_sammeln(pfade: Mapping) -> None:
    """Die Rechte aus den Beschreibungstexten herausloesen."""
    _RECHTE.clear()
    for pfad, eintrag in pfade.items():
        if not isinstance(eintrag, Mapping):
            continue
        for art, inhalt in eintrag.items():
            if not isinstance(inhalt, Mapping):
                continue
            # Nur "description". Haengte man "summary" an, stuende hinter
            # dem Recht noch die Ueberschrift des Aufrufs ("Korrespondenzen
            # Suchen") und der Verwalter suchte in jur|nodes nach einem
            # Rechtenamen, den es nicht gibt.
            treffer = _RECHTEMUSTER.search(str(inhalt.get("description") or ""))
            if not treffer:
                treffer = _RECHTEMUSTER.search(str(inhalt.get("summary") or ""))
            if treffer:
                # Nur der erste Satz - dahinter steht oft noch Erlaeuterung.
                recht = treffer.group(1).strip().split(". ")[0].strip()
                _RECHTE[(str(pfad), str(art).lower())] = recht


#: Die Verfahren, mit denen diese Probe fragt. Beide brauchen den Schluessel.
VERFAHREN = ("get", "post")


def _schluessel_anhaengen(client: Any, token: str,
                          eigene: Mapping[str, str] | None = None) -> None:
    """Jeder Anfrage den Schluessel mitgeben - GET **und** POST.

    **Der Fehler vom 07.10.2026.** Hier stand nur ``client.get`` gewrappt. Die
    Grundkopfzeilen des Clients tragen ``X-Auth-User``, aber nicht
    ``X-Auth-Key``; den hing allein dieser Wrapper an. Jeder ``client.post``
    ging damit **ohne Schluessel** hinaus, und der Server antwortete, voellig
    zu Recht, mit **401 „Authentifizierung ungueltig"**.

    Im Lauf vom 07.10.2026 war genau ein POST dabei:
    ``/correspondence/search``. Er bekam 401, alle sechs uebrigen Aufrufe
    waren GET und antworteten mit 200. Daraus wurde geschlossen, dem
    Schluessel fehle das Recht ``search:correspondence`` - und die Kanzlei
    bekam eine Aufgabe, die keine war. Es fehlte nicht das Recht, sondern die
    Kopfzeile.

    **Der Betrieb war nie betroffen.** ``http_adapter.py`` gibt den Kopf bei
    jedem Aufruf mit, bei GET und bei POST (``self._kopf(pfad)``). Der Fehler
    lag allein im Pruefbogen - also in dem Werkzeug, das Vertrauen schaffen
    soll.

    Deshalb wird jetzt ueber ``VERFAHREN`` geschleift statt eine Zeile je
    Verfahren zu schreiben: Ein drittes Verfahren kann dann nicht mehr
    stillschweigend ohne Schluessel hinausgehen.
    """
    from jusperfect.jurnodes.http_adapter import bereich_von

    eigene = dict(eigene or {})

    def _bauen(echtes):
        def _mit_schluessel(pfad, **kw):
            kw.setdefault("headers", {})
            kw["headers"] = {**kw["headers"],
                             "X-Auth-Key": eigene.get(bereich_von(pfad), token)}
            return echtes(pfad, **kw)
        return _mit_schluessel

    for verfahren in VERFAHREN:
        setattr(client, verfahren, _bauen(getattr(client, verfahren)))


def _rechte_zeigen(endpunkte: Any) -> None:
    """Welches Recht jeder Aufruf braucht, den diese Probe benutzt.

    Damit ist ein 401 im Bericht kein Raetsel mehr, sondern eine Zeile mit
    einem Namen, den der Verwalter in jur|nodes suchen kann.
    """
    gebraucht = [
        ("GET", getattr(endpunkte, "akten_suche", "/record/search")),
        ("GET", getattr(endpunkte, "akte", "/record")),
        ("GET", getattr(endpunkte, "vermerke", "/record/note")),
        ("POST", getattr(endpunkte, "korrespondenz_suche", "/correspondence/search")),
        ("GET", getattr(endpunkte, "ordner_inhalt", "/file-system/folder/content")),
        ("GET", getattr(endpunkte, "datei_download", "/file-system/file/download")),
        ("GET", getattr(endpunkte, "fristen", "/todo/search")),
    ]
    zeilen = [(art, pfad, recht_fuer(pfad, art)) for art, pfad in gebraucht]
    if not any(recht for _, _, recht in zeilen):
        return
    print()
    _sagen("✓", "Welches Recht jeder benutzte Aufruf braucht (aus der")
    _sagen(" ", "Beschreibung, Feld „description“):")
    for art, pfad, recht in zeilen:
        _sagen(" ", f"     {art:4} {pfad:38} {recht or '(nicht genannt)'}")
    _sagen(" ", "Weist der Server einen davon mit 401 ab, waehrend die")
    _sagen(" ", "uebrigen antworten, dann fehlt genau dieses Recht.")


def _beschreibung_auswerten(daten: Mapping, endpunkte: Any) -> None:
    """Was in einer vorliegenden OpenAPI-Beschreibung steht.

    Gedruckt werden **Pfade und Parameternamen** - die Beschreibung des
    Herstellers, kein Akteninhalt. Eine Schnittstellenbeschreibung enthaelt
    keine Mandantendaten; sie sagt nur, was es gibt.
    """
    pfade = daten.get("paths")
    if not isinstance(pfade, Mapping):
        _sagen("!", "Die Datei hat keinen Abschnitt „paths“.")
        return

    _rechte_sammeln(pfade)
    namen = sorted(str(name) for name in pfade)
    _sagen("✓", f"{len(namen)} Pfade stehen darin. Alle, der Reihe nach:")
    for name in namen:
        eintrag = pfade.get(name)
        verfahren = ""
        if isinstance(eintrag, Mapping):
            verfahren = " ".join(sorted(v.upper() for v in eintrag
                                        if isinstance(v, str) and len(v) < 8))
        print(f"        {name}    {verfahren}")

    # Die eigentliche Frage: Wo ist die E-Akte?
    treffer = [name for name in namen
               if any(wort in _ohne_trenner(name) for wort in _EAKTE_WOERTER)]
    print()
    if treffer:
        _sagen("✓", "Pfade, die nach E-Akte, Korrespondenz oder Vermerk klingen:")
        for name in treffer:
            print(f"        {name}")
        _sagen(" ", "Diese Pfade sind der naechste Schritt - mit der Akte gefragt.")
        _rechte_zeigen(endpunkte)
    else:
        _sagen("!", "Kein Pfad traegt eines dieser Woerter im Namen:")
        _sagen(" ", "  " + ", ".join(_EAKTE_WOERTER))
        _sagen(" ", "Dann liegt die E-Akte nicht in dieser Beschreibung - und")
        _sagen(" ", "die Frage an den Hersteller bleibt. Sie steht unten.")

    eintrag = pfade.get(endpunkte.vermerke)
    if not isinstance(eintrag, Mapping):
        _sagen("!", f"Zu {endpunkte.vermerke} steht darin nichts.")
        return
    print()
    _sagen(" ", f"Und zu {endpunkte.vermerke} im einzelnen:")
    for verfahren, inhalt in eintrag.items():
        if not isinstance(inhalt, Mapping):
            continue
        _sagen(" ", f"   {verfahren.upper()} {endpunkte.vermerke}:")
        vorgaben = inhalt.get("parameters")
        if not isinstance(vorgaben, list) or not vorgaben:
            _sagen(" ", "      (keine Abfrageparameter genannt)")
            continue
        for vorgabe in vorgaben:
            if not isinstance(vorgabe, Mapping):
                continue
            art = vorgabe.get("schema")
            art = art.get("type") if isinstance(art, Mapping) else None
            pflicht = " (Pflicht)" if vorgabe.get("required") else ""
            _sagen(" ", f"      {vorgabe.get('name')} "
                        f"[{vorgabe.get('in')}, {art or 'ohne Art'}]{pflicht}")


#: Die mitgelieferte Beschreibung des Herstellers.
#:
#: Seit dem 05.10.2026 liegt sie im Programmordner. Wer die Probe aufruft,
#: soll sie nicht erst suchen muessen - ein Werkzeug, das nach etwas fragt,
#: was danebenliegt, ist eine Huerde ohne Zweck.
BEILIEGENDE_BESCHREIBUNG = (Path(__file__).resolve().parent.parent
                            / "schnittstelle" / "jurnodes-api-1.0.2.json")


#: Sieht die Eingabe nach einem Aktenzeichen der Kanzlei aus? X-100-2026.
_AKTENZEICHEN = re.compile(r"^[A-Za-z]{1,3}[-/ ]?\d{1,5}[-/ ]?\d{2,4}$")


def _wie_ein_aktenzeichen(text: str) -> bool:
    """Damit die Probe sagen kann, WARUM die Datei fehlt."""
    return bool(_AKTENZEICHEN.match(text.strip()))


def _beschreibung_aus_datei(pfad: str, endpunkte: Any) -> bool:
    """Die Beschreibung von der Festplatte lesen - ohne Netz, ohne Raten.

    Der Server der Kanzlei gibt seine Beschreibung nicht heraus (sechs uebliche
    Pfade unterhalb der Zugangskennung, vierundzwanzig darueber, alle 404 -
    gemessen am 01. und 05.10.2026). **Die Kanzlei hat sie
    trotzdem:** Am 23.09.2026 hat sie die OpenAPI-Beschreibung ihres Servers
    geliefert, und daraus sind die Pfade abgeschrieben, mit denen das Programm
    heute arbeitet.

    Liegt diese Datei noch auf einem Rechner der Kanzlei, beantwortet sie die
    Frage nach der E-Akte in einem Lauf - und niemand muss auf den Hersteller
    warten.
    """
    datei = Path(pfad).expanduser()
    _sagen(" ", f"Beschreibung aus der Datei: {datei}")
    if not datei.is_file():
        _sagen("✗", "Die Datei gibt es nicht.")
        # **Der Lauf vom 08.10.2026.** Die Startdatei fragt zweimal
        # hintereinander: erst nach dem Aktenzeichen, dann nach einer anderen
        # Beschreibung. In die zweite Zeile wurde ein Aktenzeichen getippt -
        # was naheliegt, wenn zwei Eingabezeilen untereinander stehen.
        #
        # Die Folge war still und teuer: Die Probe lief ohne Beschreibung
        # weiter. Es fehlten die 85 Pfade, die Rechteuebersicht und die Namen
        # der Pflichtparameter - also gerade das, wofuer der Lauf gemacht
        # wird. Im Bericht stand davon nur eine Zeile, drei Seiten weiter oben.
        #
        # Jetzt wird zurueckgefallen auf die beiliegende Datei, statt ohne
        # weiterzulaufen. Eine Tippfehlerzeile darf keinen Lauf entwerten.
        if _wie_ein_aktenzeichen(pfad):
            _sagen("!", "Das sieht nach einem Aktenzeichen aus, nicht nach einem")
            _sagen(" ", "Dateipfad. Das Aktenzeichen gehoert in die Zeile DAVOR.")
        if BEILIEGENDE_BESCHREIBUNG.is_file() and datei != BEILIEGENDE_BESCHREIBUNG:
            _sagen("✓", "Es wird die beiliegende Beschreibung genommen:")
            _sagen(" ", f"   {BEILIEGENDE_BESCHREIBUNG.name}")
            return _beschreibung_aus_datei(str(BEILIEGENDE_BESCHREIBUNG), endpunkte)
        return False
    try:
        daten = json.loads(datei.read_text(encoding="utf-8"))
    except Exception as fehler:
        _sagen("✗", f"Sie laesst sich nicht als JSON lesen: {type(fehler).__name__}")
        _sagen(" ", "Liegt sie als YAML vor, bitte einmal als JSON speichern.")
        return False
    if not isinstance(daten, Mapping):
        _sagen("✗", "Das ist keine OpenAPI-Beschreibung.")
        return False
    _beschreibung_auswerten(daten, endpunkte)
    return True


def _beschreibung_suchen(client: Any, endpunkte: Any) -> bool:
    """Die OpenAPI-Beschreibung beim Server selbst holen - und auslesen.

    Sie beantwortet die Frage nach dem Parameter der Vermerke endgueltig und
    ohne Raten: Dort steht, wie er heisst und von welcher Art er ist.
    """
    _sagen(" ", "Hat der Server seine eigene Beschreibung? Dann steht der")
    _sagen(" ", "Name des Parameters dort - und muss nicht erraten werden.")
    for pfad in _BESCHREIBUNGSPFADE:
        try:
            antwort = client.get(pfad)
        except Exception as fehler:
            _sagen("!", f"{pfad}: {type(fehler).__name__}")
            continue
        if antwort.status_code >= 400:
            _sagen("✗", f"{pfad}: Status {antwort.status_code}")
            continue
        try:
            daten = antwort.json()
        except ValueError:
            _sagen("!", f"{pfad}: Status {antwort.status_code}, kein JSON")
            continue
        if not isinstance(daten, Mapping) or "paths" not in daten:
            _sagen("!", f"{pfad}: JSON, aber keine OpenAPI-Beschreibung")
            continue

        _sagen("✓", f"{pfad}: die Beschreibung liegt vor.")
        _beschreibung_auswerten(daten, endpunkte)
        return True
    # Noch nicht aufgeben: Die Beschreibung muss nicht unter der Kennung der
    # Kanzlei liegen. Sie gehoert zum Server, nicht zum Mandanten - also auch
    # eine Ebene hoeher suchen, bis zur Wurzel.
    #
    # Am 01.10.2026 antworteten alle sechs Pfade unter
    # .../api/extern/v1/<Kennung>/ mit 404. Das heisst nicht, dass es keine
    # Beschreibung gibt, sondern dass sie dort nicht liegt.
    basis = str(getattr(client, "base_url", "") or "")
    gefragt: set[str] = set()
    while basis.count("/") > 2:
        basis = basis.rstrip("/").rsplit("/", 1)[0]
        for pfad in _BESCHREIBUNGSPFADE:
            adresse = basis + pfad
            if adresse in gefragt:
                continue
            gefragt.add(adresse)
            try:
                antwort = client.get(adresse)
            except Exception:
                continue
            if antwort.status_code >= 400:
                continue
            try:
                daten = antwort.json()
            except ValueError:
                continue
            if isinstance(daten, Mapping) and "paths" in daten:
                _sagen("✓", f"{adresse}: die Beschreibung liegt hier.")
                _sagen(" ", "Sie gehoert zum Server, nicht zur Kennung der Kanzlei.")
                _beschreibung_auswerten(daten, endpunkte)
                return True

    _sagen("!", f"Keiner der ueblichen Pfade traegt eine Beschreibung "
                f"({len(_BESCHREIBUNGSPFADE)} unter der Kennung, "
                f"{len(gefragt)} darueber).")
    # Die Kanzlei hat sie trotzdem: am 23.09.2026 schon einmal geliefert.
    _sagen(" ", "Liegt die Beschreibung als Datei vor, liest die Probe sie:")
    _sagen(" ", "  JURNODES-PRUEFEN.bat ... --beschreibung PFAD\\ZUR\\DATEI.json")
    return False


#: Die Arten, die /todo/search kennt. "frist" steht in den Endpunkten, die
#: beiden anderen nennt die Beschreibung des Herstellers daneben.
_TODO_ARTEN = ("frist", "task", "resubmit")


#: Feldnamen, deren Werte eine ART bezeichnen und keinen Akteninhalt.
#:
#: Die Probe zeigt sonst grundsaetzlich keine Werte. Hier ist die Ausnahme
#: eng und begruendet: "task", "frist", "offen" sind Schluesselwoerter des
#: Herstellers. Ob ein Eintrag ein Vermerk ist, steht genau in diesen Feldern
#: - und ohne sie bleibt die Frage offen, obwohl die Antwort vorlag.
#: Ein Betreff ("todoSubject") faellt NICHT darunter: Der traegt den Fall.
_ARTFELDER = ("todoType", "todoDeadlineType", "todoDeadlineStatus", "type", "status",
              "recordStatus", "recordType")


def _arten_zeigen(daten: Any) -> None:
    """Die unterschiedlichen Werte der Art-Felder nennen - sonst nichts."""
    eintraege = daten.get("elements") if isinstance(daten, Mapping) else daten
    if isinstance(daten, Mapping) and not isinstance(eintraege, list):
        eintraege = [daten]          # eine einzelne Akte ist auch ein Eintrag
    if not isinstance(eintraege, list) or not eintraege:
        return
    for feld in _ARTFELDER:
        werte = sorted({str(e.get(feld)) for e in eintraege
                        if isinstance(e, Mapping) and e.get(feld) is not None})
        werte = [w[:40] for w in werte][:10]
        if werte:
            _sagen(" ", f"     {feld}: {', '.join(werte)}")


def _vermerke_als_todo(client: Any, endpunkte: Any, kennung: str) -> None:
    """Vielleicht sind Vermerke gar keine Vermerke, sondern Aufgaben.

    ``/todo/search`` nimmt eine ``type``-Angabe und kennt ausser "frist" noch
    "task" und "resubmit". Gefragt wurde bisher nur nach Fristen - und die
    Akte hat keine. Ein Pfad, der drei Arten fuehrt und nur nach einer gefragt
    wird, ist nicht geprueft, sondern angeschnitten.
    """
    _sagen(" ", "Fuehrt der Aufgabenpfad die Vermerke? Er kennt drei Arten,")
    _sagen(" ", "gefragt wurde bisher nur nach Fristen:")
    for art in _TODO_ARTEN:
        _zaehlen(client, f"type={art}", endpunkte.fristen, zeige_felder=True,
                 **{endpunkte.akteparameter: kennung, "type": art})
    _zaehlen(client, "ohne type (alle Arten)", endpunkte.fristen, zeige_felder=True,
             **{endpunkte.akteparameter: kennung})

    # Welche Arten stehen wirklich darin? Nur die Art-Felder, keine Betreffs.
    try:
        antwort = client.get(endpunkte.fristen, params={endpunkte.akteparameter: kennung})
        daten = antwort.json() if antwort.status_code < 400 else None
    except Exception:
        daten = None
    if daten is not None:
        _sagen(" ", "Welche Arten fuehrt der Aufgabenpfad zu dieser Akte?")
        _sagen(" ", "(nur die Art-Felder - ein Betreff traegt den Fall und bleibt drinnen)")
        _arten_zeigen(daten)

    # Und die Zahlen, die in den Aufgaben stehen. Die Akte selbst hat keine
    # hergegeben, die /record/note angenommen haette - die Aufgaben vielleicht.
    # Jede Aufgabe nennt einen Ordner. Liegt der Vermerk als Datei darin?
    ordner = _ordner_der_aufgaben(daten)
    if ordner:
        _sagen(" ", f"Jede Aufgabe nennt einen Ordner ({len(ordner)} verschiedene).")
        _sagen(" ", "Was liegt im ersten davon?")
        _zaehlen(client, f"folderId={ordner[0]}", endpunkte.ordner_inhalt,
                 zeige_felder=True, **{endpunkte.ordnerparameter: ordner[0]})

    zahlen = _zahlen_aus_eintraegen(daten)
    if zahlen:
        _sagen(" ", "Zahlen aus den Aufgaben dieser Akte, auf /record/note probiert:")
        for feld, zahl in zahlen:
            _zaehlen(client, f"id={zahl} (aus {feld})", endpunkte.vermerke,
                     zeige_felder=True, **{"id": zahl})


def _ordner_der_aufgaben(daten: Any) -> list[int]:
    """Die Ordnernummern, die in ``todoFolder`` stehen.

    Jede Aufgabe traegt eine Liste mit einem Eintrag. Steht darin eine
    Ordnernummer, liegt der eigentliche Vermerk vermutlich als Datei darin -
    und der Weg dorthin ist derselbe, der die Dokumente einer Akte holt.
    """
    eintraege = daten.get("elements") if isinstance(daten, Mapping) else daten
    if not isinstance(eintraege, list):
        return []
    gefunden: list[int] = []
    for eintrag in eintraege:
        if not isinstance(eintrag, Mapping):
            continue
        for wert in (eintrag.get("todoFolder") or []):
            if isinstance(wert, int) and not isinstance(wert, bool) and wert not in gefunden:
                gefunden.append(wert)
            elif isinstance(wert, Mapping):
                nummer = wert.get("id")
                if isinstance(nummer, int) and nummer not in gefunden:
                    gefunden.append(nummer)
    return gefunden


def _zahlen_aus_eintraegen(daten: Any) -> list[tuple[str, int]]:
    """Die Zahlen aus einer Trefferliste - je Wert einmal.

    Die Akte selbst gab fuenf Zahlen her, und keine nahm /record/note an. Die
    Aufgaben einer Akte tragen eigene (todoGroup, todoDeadlineId); sie gehoeren
    zu DIESER Akte und sind damit so erlaubt wie die der Akte selbst.
    """
    eintraege = daten.get("elements") if isinstance(daten, Mapping) else daten
    if not isinstance(eintraege, list):
        return []
    gefunden: list[tuple[str, int]] = []
    gesehen: set[int] = set()
    for eintrag in eintraege[:20]:
        if not isinstance(eintrag, Mapping):
            continue
        for name, wert in eintrag.items():
            if isinstance(wert, int) and not isinstance(wert, bool) and wert not in gesehen:
                gesehen.add(wert)
                gefunden.append((name, wert))
    return gefunden[:12]


#: Pfade, unter denen die E-Akte liegen koennte.
#:
#: Am 01.10.2026 hat die Kanzlei die Akte X-100-2026 in jur|nodes geoeffnet
#: und damit die Vermutung widerlegt, die zehn "task"-Eintraege seien die
#: Vermerke: Das ist die To-Do-Liste ("Aufgabe Sonstiges", drei offene und
#: sieben erledigte). Die Vermerke stehen in einem eigenen Bereich namens
#: E-AKTE, zusammen mit Mails - der oberste Eintrag dort lautet woertlich
#: "Vermerk", 25.09.2026 10:43.
#:
#: Ein Blick in die Oberflaeche hat damit in zehn Sekunden geklaert, woran
#: zwei Pruefbogenlaeufe und zwanzig Parameternamen vorbeigelaufen sind. Wer
#: eine Schnittstelle absucht, sollte vorher wissen, wonach.
#:
#: Geraten wird hier nicht ins Blaue: Gefragt wird mit OPTIONS, und der Server
#: unterscheidet sauber - 404 fuer "gibt es nicht", eine Allow-Zeile fuer
#: "gibt es". Was er selbst beantwortet, muss der Hersteller nicht beantworten.
_EAKTE_PFADE = (
    "/record/process", "/process", "/process/search",
    "/record/entry", "/record/entry/search",
    "/record/history", "/history/search",
    "/efile", "/efile/search", "/record/efile",
    "/record/activity/search", "/record/item/search",
    "/record/mail/search", "/mail/search",
    "/record/document/search", "/document/search",
)


def _korrespondenz_lesen(client: Any, endpunkte: Any, kennung: str) -> bool:
    """Die E-Akte - jetzt auf dem Weg, den der Hersteller beschreibt.

    **Seit dem 05.10.2026 wird hier nicht mehr geraten.** Die Kanzlei hat die
    OpenAPI-Beschreibung geliefert (Fassung 1.0.2, 85 Pfade). Darin steht:

      POST /correspondence/search  {"recordIdentifier": "...", "page": 1}

    Das ist die E-Akte. Sie fuehrt Mails, beA, Post, Fax, SMS, Dateien - und
    die Vermerke, als Eintraege vom Typ "note" mit einer Nummer in
    "referenceNote".

    Gezeigt werden Anzahl, Arten, Ordnernummern und Zeitraum. **Kein
    Betreff** - der traegt den Fall.
    """
    _sagen(" ", "Die E-Akte heisst in der Schnittstelle KORRESPONDENZ.")
    _sagen(" ", f"{endpunkte.korrespondenz_suche}, Seite 1:")
    try:
        antwort = client.post(endpunkte.korrespondenz_suche,
                              json={"recordIdentifier": kennung, "page": 1})
    except Exception as fehler:
        _sagen("✗", f"Korrespondenz: {type(fehler).__name__}")
        return
    if antwort.status_code >= 400:
        _sagen("✗", f"Korrespondenz: Status {antwort.status_code}")
        _wortlaut(antwort)
        _eakte_urteil(0, 0, 0, abweisung=antwort.status_code,
                      pfad=endpunkte.korrespondenz_suche)
        return False
    try:
        daten = antwort.json()
    except ValueError:
        _sagen("!", "Korrespondenz: keine JSON-Antwort")
        _eakte_urteil(0, 0, 0, abweisung=antwort.status_code,
                      pfad=endpunkte.korrespondenz_suche)
        return False

    eintraege = daten.get("elements") if isinstance(daten, Mapping) else None
    if not isinstance(eintraege, list):
        _sagen("!", "Korrespondenz: keine Liste „elements“ in der Antwort.")
        _eakte_urteil(0, 0, 0, abweisung=antwort.status_code,
                      pfad=endpunkte.korrespondenz_suche)
        return False
    gesamt = daten.get("amountTotal")
    seiten = daten.get("pagesTotal")
    _sagen("✓", f"{len(eintraege)} Eintrag/Einträge auf Seite 1, "
                f"amountTotal {gesamt}, pagesTotal {seiten}")
    if not eintraege:
        _sagen(" ", "Diese Akte hat keine Korrespondenz - oder das Recht fehlt.")
        _eakte_urteil(0, 0, 0)
        return False

    _sagen(" ", "Die Feldnamen des ersten Eintrags:")
    for zeile in felder({"elements": eintraege}):
        _sagen(" ", f"     {zeile}")
    _arten_zeigen(daten)

    # Die Ordnernummern - der Punkt, an dem sich der Fehler vom 02.10.2026
    # zeigen muss: Sie gehoeren in den KORRESPONDENZbaum, nicht in den
    # Dateibaum, und die Akte nennt ihren eigenen in correspondenceFolderId.
    ordner = sorted({str(e.get("folderId")) for e in eintraege
                     if isinstance(e, Mapping) and e.get("folderId") is not None})
    if ordner:
        _sagen(" ", f"Ordnernummern (Korrespondenzbaum): {', '.join(ordner[:12])}")

    tage = sorted(_als_tag(e.get("postmark")) for e in eintraege
                  if isinstance(e, Mapping) and _als_tag(e.get("postmark")))
    if tage:
        _sagen(" ", f"Poststempel von {tage[0]} bis {tage[-1]}")

    vermerke = [e for e in eintraege
                if isinstance(e, Mapping) and e.get("type") == "note"]
    _sagen("✓" if vermerke else " ",
           f"Davon Vermerke (type=note): {len(vermerke)}")
    ohne_inhalt = [e for e in eintraege if isinstance(e, Mapping)
                   and str(e.get("type", "")).lower() not in ("note", "file", "")]
    if ohne_inhalt:
        arten = sorted({str(e.get("type")) for e in ohne_inhalt})
        _sagen(" ", f"Noch ohne Inhalt im Programm: {len(ohne_inhalt)} "
                    f"({', '.join(arten)}). Sie stehen nicht in der Dokumentliste.")
    gelungen = _vermerke_lesen(client, endpunkte, kennung, vermerke)
    _download_messen(client, eintraege)
    _eakte_urteil(len(eintraege), len(vermerke), gelungen)
    return True


#: Woran eine Datei an ihren ersten Bytes zu erkennen ist.
#:
#: Kein Inhalt - eine Signatur ist der Fingerabdruck des FORMATS, nicht des
#: Textes. "%PDF" steht in jeder PDF-Datei dieser Welt.
_SIGNATUREN = (
    (b"%PDF", "PDF"),
    (b"\xd0\xcf\x11\xe0", "Outlook-Nachricht (.msg) oder altes Office"),
    (b"PK\x03\x04", "ZIP-Behaelter (.docx, .zip)"),
    (b"Received:", "E-Mail (.eml)"),
    (b"Return-Path:", "E-Mail (.eml)"),
    (b"From:", "E-Mail (.eml)"),
    (b"Delivered-To:", "E-Mail (.eml)"),
    (b"{", "JSON"),
    (b"<", "HTML oder XML"),
)


def _dateiart(roh: bytes) -> str:
    """Welche Dateiart diese Bytes sind - oder „unbekannt"."""
    for muster, name in _SIGNATUREN:
        if roh.startswith(muster):
            return name
    return "unbekannt"


def _download_messen(client: Any, eintraege: list) -> None:
    """Was ``/mail/download`` zurueckgibt - gemessen, nicht geraten.

    **Die eine Frage, die das Programm nicht selbst beantworten kann.** Die
    Beschreibung des Herstellers sagt, dass hier ``application/octet-stream``
    zurueckkommt. Sie sagt nicht, WELCHE Dateiart - und ohne die weiss die
    Texterkennung nicht, womit sie lesen soll. Sie kann .eml, .msg und PDF;
    sie muss nur wissen, welches davon.

    **Ausgegeben wird kein Inhalt.** Status, Laenge und die Signatur der
    ersten Bytes, mehr nicht. Eine Signatur ist der Fingerabdruck des Formats,
    nicht des Textes.
    """
    mails = [e for e in eintraege if isinstance(e, Mapping)
             and str(e.get("type", "")).lower() == "mail" and e.get("referenceMail")]
    if not mails:
        _sagen(" ", "Keine Mail in dieser Akte - /mail/download bleibt ungeprueft.")
        return
    kennung = mails[0].get("referenceMail")
    _sagen(" ", "POST /mail/download mit referenceMail aus dem Verzeichnis:")
    try:
        antwort = client.post("/mail/download", json={"mailIdentifier": kennung})
    except Exception as fehler:
        _sagen("✗", f"/mail/download: {type(fehler).__name__}")
        return
    if antwort.status_code >= 400:
        _sagen("✗", f"/mail/download: Status {antwort.status_code}")
        if antwort.status_code in (400, 405):
            _sagen(" ", "   Dann ist referenceMail nicht die Nummer, die dort "
                        "hineingehoert. Das waere eine Frage an den Hersteller.")
        return
    roh = antwort.content[:64]
    _sagen("✓", f"/mail/download: Status 200, {len(antwort.content)} Bytes, "
                f"Dateiart: {_dateiart(roh)}")
    _sagen(" ", f"   Content-Type laut Server: "
                f"{antwort.headers.get('content-type', '(keiner)')}")
    name = antwort.headers.get("content-disposition", "")
    _sagen(" ", f"   Dateiname laut Server: {name or '(keiner)'}")
    _sagen(" ", "   (Kein Inhalt ausgegeben - nur Format und Laenge.)")


def _eakte_urteil(eintraege: int, vermerke: int, gelungen: int,
                  abweisung: int | None = None, pfad: str = "") -> None:
    """Der Satz, auf den es ankommt: Kann die E-Akte eingeschaltet werden?

    Ein Pruefbogen, der zwanzig Zeilen Befund ausgibt und die Frage nicht
    beantwortet, laesst den Leser dieselbe Arbeit noch einmal machen. Hier
    steht sie beantwortet - und zwar aus dem, was in diesem Lauf wirklich
    geschehen ist, nicht aus einer Erwartung.

    **Auch eine Abweisung ist eine Antwort** (nachgetragen am 07.10.2026).
    Der Lauf vom selben Tag bekam auf ``/correspondence/search`` ein Status
    401 - und damit endete der Abschnitt, ohne die Frage zu beantworten. Der
    Leser musste aus zwanzig Zeilen selbst schliessen, was das heisst. Genau
    das sollte dieser Satz ihm abnehmen. ``abweisung`` traegt deshalb den
    Status, mit dem der Server abgewiesen hat.
    """
    _sagen(" ", "")
    _sagen(" ", "--- Kann die E-Akte eingeschaltet werden? ---")
    if abweisung is not None:
        if abweisung in (401, 403):
            recht = recht_fuer(pfad or "", "post")
            _sagen("✗", f"NEIN - noch nicht. Der Server weist das Verzeichnis "
                        f"mit Status {abweisung} ab, waehrend er auf jeden "
                        f"anderen Pfad in diesem Lauf geantwortet hat.")
            _sagen(" ", "   Der Zugang als solcher steht also; abgewiesen wird")
            _sagen(" ", "   dieser eine Pfad - es fehlt ein Recht am Schluessel.")
            if recht:
                _sagen(" ", "")
                _sagen("✓", f"   Die Beschreibung nennt es: {recht}")
                _sagen(" ", "   In jur|nodes dem Schnittstellenbenutzer genau")
                _sagen(" ", "   dieses Recht geben. Danach diesen Lauf noch einmal.")
            else:
                _sagen(" ", "   Welches, sagt die Beschreibung zu diesem Pfad -")
                _sagen(" ", "   im Feld „description“, hinter „Benoetigte Rechte:“.")
            _sagen(" ", "   Am Programm ist dafuer nichts zu tun.")
            _sagen(" ", "   Alles Weitere: schnittstelle/ANFRAGE-HERSTELLER.md")
            return
        if abweisung == 404:
            _sagen("✗", "NEIN. Diese Einrichtung kennt den Pfad nicht (404), "
                        "obwohl die Beschreibung 1.0.2 ihn fuehrt. Das ist eine "
                        "Frage nach der Fassung des Servers.")
            return
        _sagen("!", f"Unentschieden: Der Server antwortete mit Status "
                    f"{abweisung}. Der Wortlaut steht darueber; er kommt von "
                    f"ihm, nicht von hier.")
        return
    if not eintraege:
        _sagen("!", "Unentschieden: Diese Akte hat keine Korrespondenz. Bitte den "
                    "Lauf an einer Akte mit Schriftverkehr wiederholen.")
        return
    if not vermerke:
        _sagen("!", "Unentschieden: Korrespondenz gelesen, aber kein Vermerk darin. "
                    "Der Weg steht; ob /record/note traegt, zeigt erst eine Akte "
                    "mit Vermerk.")
        return
    if gelungen:
        _sagen("✓", f"JA. Das Verzeichnis ist lesbar und {gelungen} Vermerk(e) "
                    f"wurden abgerufen.")
        _sagen(" ", "   Sie ist seit dem 08.10.2026 von Haus aus ein - es ist")
        _sagen(" ", "   nichts einzutragen. Die Vermerke stehen als Dokumente in")
        _sagen(" ", "   der Aktenliste.")
        _sagen(" ", "   Mail, beA und Post bleiben vorerst draussen. Nicht mehr,")
        _sagen(" ", "   weil etwas fehlt - der Weg ist gemessen -, sondern weil")
        _sagen(" ", "   zwei Dinge zu entscheiden sind: eine Obergrenze je Mail")
        _sagen(" ", "   und ob der Anhang mit ins Aktengedaechtnis soll.")
        return
    _sagen("✗", "NEIN. Das Verzeichnis ist lesbar, aber kein Vermerk liess sich "
                "abrufen. Die Zeilen darueber nennen den Status; meist fehlt dem "
                "Schluessel das Recht auf /record/note.")


def _vermerke_lesen(client: Any, endpunkte: Any, kennung: str,
                    vermerke: list) -> int:
    """Hoechstens drei Vermerke abrufen - zum Nachweis, nicht zum Auslesen.

    GET /record/note braucht ZWEI Pflichtparameter: die Nummer des Vermerks
    UND den Identifier der Akte. Daran ist die Suche vier Wochen lang
    gescheitert; zwanzig Parameternamen wurden probiert, jeder mit EINEM Wert.

    Gezeigt werden Feldnamen, Art und LAENGE des Inhalts - nicht der Inhalt.
    """
    if not vermerke:
        _sagen(" ", "Ohne Vermerk in dieser Akte bleibt /record/note ungeprueft.")
        return 0
    gelungen = 0
    _sagen(" ", f"{endpunkte.vermerke} mit BEIDEN Pflichtparametern "
                f"({endpunkte.vermerkparameter} + {endpunkte.vermerkakteparameter}):")
    for eintrag in vermerke[:3]:
        nummer = eintrag.get("referenceNote")
        if nummer is None:
            _sagen("!", "Ein Eintrag vom Typ note ohne referenceNote.")
            continue
        try:
            antwort = client.get(endpunkte.vermerke, params={
                endpunkte.vermerkparameter: nummer,
                endpunkte.vermerkakteparameter: kennung})
        except Exception as fehler:
            _sagen("✗", f"Vermerk {nummer}: {type(fehler).__name__}")
            continue
        if antwort.status_code >= 400:
            _sagen("✗", f"Vermerk {nummer}: Status {antwort.status_code}")
            _wortlaut(antwort)
            continue
        try:
            vermerk = antwort.json()
        except ValueError:
            _sagen("!", f"Vermerk {nummer}: keine JSON-Antwort")
            continue
        if not isinstance(vermerk, Mapping):
            _sagen("!", f"Vermerk {nummer}: unerwartete Form")
            continue
        art = vermerk.get("type")
        laenge = len(str(vermerk.get("content") or ""))
        gelungen += 1
        _sagen("✓", f"Vermerk {nummer}: type={art}, contentType="
                    f"{vermerk.get('contentType')}, {laenge} Zeichen Inhalt")
        _sagen(" ", f"     Felder: {', '.join(sorted(vermerk))}")
        # Die Pruefung aus Befund F08, hier am echten Server: Gehoert der
        # Vermerk zu der Akte, nach der gefragt wurde? RecordNote traegt das
        # Feld, also laesst es sich nachsehen.
        zurueck = str(vermerk.get("record", "")).strip()
        if zurueck and zurueck.casefold() != str(kennung).strip().casefold():
            _sagen("✗", f"Vermerk {nummer} gehoert zu einer ANDEREN Akte. "
                        f"Das Programm wuerde ihn abweisen.")
    return gelungen


def _eakte_suchen(client: Any, endpunkte: Any, kennung: str) -> None:
    """Wo liegt die E-Akte? Dort stehen die Vermerke, nicht in der To-Do-Liste.

    Es wird nur gefragt, welche Pfade es gibt (OPTIONS), und die gefundenen
    werden gelesen. Geschrieben wird nichts.
    """
    _sagen(" ", "Die Vermerke stehen in der E-Akte - das zeigt die Oberflaeche.")
    _sagen(" ", "Welcher Pfad fuehrt dorthin? Gefragt, nicht geraten:")
    gefunden: list[str] = []
    for pfad in _EAKTE_PFADE:
        try:
            antwort = client.request("OPTIONS", pfad)
        except Exception as fehler:
            _sagen("!", f"{pfad}: {type(fehler).__name__}")
            continue
        if antwort.status_code == 404:
            continue
        erlaubt = antwort.headers.get("allow", "").strip()
        _sagen("✓", f"{pfad}: {erlaubt or f'Status {antwort.status_code}'}")
        gefunden.append(pfad)

    if not gefunden:
        _sagen("!", f"Keiner der {len(_EAKTE_PFADE)} Pfade gibt es - alle 404.")
        _sagen(" ", "Dann weiss es nur der Hersteller. Die Frage steht unten.")
        return

    _sagen(" ", "Die gefundenen Pfade, mit der Akte gefragt:")
    for pfad in gefunden:
        for name in (endpunkte.akteparameter, endpunkte.kennungparameter):
            _zaehlen(client, f"{pfad} mit {name}", pfad, zeige_felder=True,
                     **{name: kennung})


def _vermerke_suchen(client: Any, endpunkte: Any, kennung: str,
                     aktenzeichen: str = "") -> None:
    """Wie kommt man an die Vermerke einer Akte?

    Aus der Kanzlei am 25.09.2026: "Vermerke, auch Telefonvermerke waeren
    wichtig."

    **Was der Lauf vom 28.09.2026 geklaert hat.** OPTIONS auf /record/note
    antwortet ``GET,HEAD,POST`` - der Pfad ist da und nimmt GET an.
    ``/record/note/search`` und ``/note/search`` antworten mit 404; die
    Vermutung "jede Liste heisst <ding>/search" ist damit widerlegt. Es fehlt
    also nicht der Pfad, sondern der **Name des Parameters**: Alle fuenf
    probierten Formen bekamen 405 und "Bitte Daten angeben", und das heisst bei
    diesem Hersteller "ungueltige Eingabe", nicht "Weg gibt es nicht".

    **Zwei Achsen werden jetzt durchprobiert**, denn beides kann falsch sein:
    der Name (siehe ``_VERMERK_NAMEN``) und die Form des Wertes. Die Akte hat
    zwei Kennungen, und dieser Hersteller haelt sie streng getrennt -
    ``identifier`` ist der Schluessel (FL6BDPWJ...), ``recordSign`` das
    Aktenzeichen (X-100-2026). Wer das eine fuer das andere einsetzt, bekommt
    404 und haelt einen richtigen Pfad fuer falsch; das ist am 23.09.2026
    genau so passiert.

    Es wird nur gelesen. Der schreibende Pfad (POST) wird nicht angefasst -
    auch nicht "zum Ausprobieren": Ein Vermerk in einer Mandatsakte ist nicht
    zurueckzunehmen.
    """
    # **Seit dem 08.10.2026 zuerst der Weg, der steht.**
    #
    # Vier Wochen lang begann dieser Abschnitt mit dem Erraten: zwanzig
    # Parameternamen, zehn Zahlen, sechzehn Pfade, sechs Beschreibungsorte.
    # Das war richtig, solange niemand wusste, wo die Vermerke liegen.
    #
    # Jetzt steht es: POST /correspondence/search gibt die Liste, und
    # GET /record/note?id=..&record=.. den Vermerk. Der Lauf vom 08.10.2026
    # hat beides an X-100-2026 gemessen.
    #
    # Das Erraten laeuft deshalb nur noch, wenn der bekannte Weg NICHT
    # traegt. Ein Bericht, der auf drei Seiten nach etwas sucht, das zwei
    # Seiten weiter unten gefunden wird, laesst den Leser zweimal dasselbe
    # pruefen - und am 08.10.2026 ist genau das passiert.
    gelungen = _korrespondenz_lesen(client, endpunkte, kennung)
    if gelungen:
        _sagen(" ", "")
        _sagen("✓", "Der Weg zu den Vermerken steht - es wird nicht mehr")
        _sagen(" ", "danach gesucht. Was frueher hier an Namen, Zahlen und")
        _sagen(" ", "Pfaden durchprobiert wurde, entfaellt.")
        _was_offen_bleibt()
        return

    _sagen(" ", "")
    _sagen("!", "Der bekannte Weg traegt in dieser Akte nicht. Deshalb wird")
    _sagen(" ", "jetzt gesucht - so, wie es bis zum 08.10.2026 immer lief.")
    _vermerke_erraten(client, endpunkte, kennung, aktenzeichen)
    _vermerke_als_todo(client, endpunkte, kennung)
    _eakte_suchen(client, endpunkte, kennung)
    _beschreibung_suchen(client, endpunkte)
    # Auch wer suchen musste, bekommt den Schlussatz - sonst endet der
    # Bericht gerade dort ohne Auskunft, wo sie am noetigsten ist.
    _was_offen_bleibt()


def _was_offen_bleibt() -> None:
    """Was offen BLEIBT - und das ist seit dem 08.10.2026 wenig."""
    _sagen(" ", "")
    _sagen(" ", "Was noch offen ist, steht fertig formuliert in")
    _sagen(" ", "schnittstelle/ANFRAGE-HERSTELLER.md. Der Kern, zum Mitlesen:")
    print()
    print("      Beantwortet und nicht mehr zu fragen: der Weg zur E-Akte")
    print("      (POST /correspondence/search), die Vermerke darin")
    print("      (GET /record/note?id=..&record=.. mit BEIDEN Pflicht-")
    print("      parametern), die Dateiart hinter POST /mail/download")
    print("      (.eml, der Server nennt den Namen selbst), die Herkunft")
    print("      von attachmentId (GET /bea) und postFileUniqueKey")
    print("      (POST /post/get-files), und wofuer correspondenceFolderId")
    print("      steht - jene Nummer gehoert in den Korrespondenzbaum.")
    print("      Seit dem 11.10.2026 auch, was isInbox bedeutet: die")
    print("      Beschreibung sagt 1 = Eingang, 0 = Ausgang, -1 = Neutral.")
    print()
    print("      Offen sind nur noch zwei Kleinigkeiten: ob der Pfad")
    print("      wirklich correspondence/get-by-reference ohne fuehrenden")
    print("      Schraegstrich heisst, und ob es eine neuere Fassung als")
    print("      1.0.2 gibt.")


def _vermerke_erraten(client: Any, endpunkte: Any, kennung: str,
                      aktenzeichen: str = "") -> None:
    """Die Suche von Hand - nur noch als Rueckfall.

    Dieser Abschnitt hat die Antwort gefunden und darf deshalb nicht
    verschwinden: Antwortet ein Server nach einem Update anders, faengt die
    Suche wieder von vorn an, und dann soll sie hier stehen.
    """

    _sagen(" ", "Wie kommt man an die Vermerke? OPTIONS sagte GET,HEAD,POST -")
    _sagen(" ", "der Pfad ist da. Gesucht wird der Name des Parameters.")

    werte = [("der Kennung", kennung)]
    if aktenzeichen and aktenzeichen != kennung:
        werte.append(("dem Aktenzeichen", aktenzeichen))

    for beschriftung, wert in werte:
        _sagen(" ", f"Mit {beschriftung} „{wert}“:")
        for name in _VERMERK_NAMEN:
            _zaehlen(client, f"{name}", endpunkte.vermerke, **{name: wert})

    # Der Server kennt "id" und will dazu eine Zahl. Welche?
    #
    # "Given parameter id is invalid. Value (FL6BDPWJ940ALEY4BVP0) cannot be
    # parsed into number." - gemessen am 28.09.2026. Von zehn Namen antwortete
    # genau dieser anders als alle uebrigen. Das ist kein Zufall, sondern die
    # Spur.
    zahlen = _zahlen_der_akte(client, endpunkte, kennung)
    if zahlen:
        _sagen(" ", "„id“ will eine Zahl. Diese Zahlen führt der Server")
        _sagen(" ", "selbst zu dieser Akte - nur sie werden probiert:")
        for feld, zahl in zahlen:
            _zaehlen(client, f"id={zahl} (aus {feld})", endpunkte.vermerke,
                     zeige_felder=True, **{"id": zahl})

        # Und nun die Form, die die Beschreibung wirklich verlangt.
        #
        # Nachgetragen am 07.10.2026. GET /record/note fuehrt ZWEI
        # Pflichtparameter, "id" (Zahl) UND "record" (Zeichenkette) - so
        # steht es in 1.0.2, und der Lauf vom 07.10.2026 hat es oben selbst
        # ausgegeben. Probiert wurde bis dahin jeder Name EINZELN. "Bitte
        # Daten angeben" war damit kein Raetsel, sondern die zutreffende
        # Klage des Servers: Es fehlte jedes Mal der zweite Wert.
        #
        # Geraten wird dabei nicht: Es werden ausschliesslich die Zahlen
        # genommen, die der Server selbst zu DIESER Akte herausgibt. Jede
        # andere Nummer gehoert einer fremden Akte; sie zu probieren waere
        # ein Blick in die Unterlagen eines anderen Mandanten.
        _sagen(" ", "Und die Form, die die Beschreibung verlangt: id UND record")
        _sagen(" ", "zusammen (beide Pflicht). Nur die Zahlen dieser Akte:")
        for feld, zahl in zahlen:
            _zaehlen(client, f"id={zahl} (aus {feld}) + record",
                     endpunkte.vermerke, zeige_felder=True,
                     **{"id": zahl, "record": kennung})
    else:
        _sagen("!", "Die Akte gibt keine einzige Zahl heraus - dann steht die")
        _sagen(" ", "Zahl für „id“ woanders. Die Frage unten geht an den Hersteller.")

    # Der Server verlangt bei /record/search eine Seitenzahl groesser 0
    # ("Bitte geben Sie eine Seitenzahl > 0 an", gemessen am 28.09.2026).
    # Vielleicht will auch dieser Pfad eine - dann waere "Bitte Daten angeben"
    # nicht die Klage ueber den Namen, sondern ueber die fehlende Seite.
    _sagen(" ", "Dieselben Namen noch einmal mit page=1:")
    for name in ("id", "record", "recordIdentifier"):
        _zaehlen(client, f"{name} + page=1", endpunkte.vermerke,
                 **{name: kennung, "page": 1})

    # Und die Liste, so wie sie bei allen anderen heisst. Am 28.09.2026 gab es
    # darauf 404; die Zeilen bleiben stehen, weil ein Server nach einem Update
    # anders antworten kann und es dann eine Zeile im Bericht ist.
    _sagen(" ", "Die Liste - am 28.09.2026 gab es sie nicht (404):")
    for pfad in (f"{endpunkte.vermerke}/search", "/note/search"):
        _methoden(client, f"Nimmt {pfad} etwas an?", pfad)
        _zaehlen(client, f"{pfad} mit recordIdentifier", pfad,
                 **{"recordIdentifier": kennung})



def _ordner_aufteilen(client: Any, endpunkte: Any, ordner_id: str,
                      tiefe: int = 0, gesehen: set[str] | None = None,
                      sammlung: dict[str, Any] | None = None) -> dict[str, Any]:
    """Was in diesem Ordner liegt - und in seinen Unterordnern.

    Aus der Kanzlei am 25.09.2026: Der Wurzelordner einer Akte enthielt nur
    lesbare Formate (pdf 21, docx 8), und trotzdem blieben im Betrieb 14 von
    38 Dokumenten ungelesen. Die Erklaerung lag in den Unterordnern - die
    zaehlte diese Probe nicht mit.

    **Eine Probe, die anders fragt als der Betrieb, prueft etwas anderes als
    den Betrieb.** Der Satz steht seit Wochen in der Uebergabe, und diese
    Probe hat ihn gebrochen: Sie sah den Wurzelordner, waehrend das Programm
    den ganzen Baum liest. Schlimmer noch, sie sagte dazu "was darin liegt,
    liest das Programm heute nicht mit" - das stimmte, bis die Unterordner am
    selben Tag dazukamen, und danach war es eine falsche Auskunft.

    Keine Dateinamen in der Ausgabe - nur Zahlen und Endungen. Der Befund
    wird weitergegeben.
    """
    from jusperfect.jurnodes.base import ist_gedaechtnis_datei

    oberste = sammlung is None
    if oberste:
        sammlung = {"ordner": 0, "dateien": 0, "gedaechtnis": 0,
                    "arten": {}, "unlesbar": 0, "probe": None}
        gesehen = set()
    assert sammlung is not None and gesehen is not None
    if str(ordner_id) in gesehen or len(gesehen) >= 60:
        return sammlung
    gesehen.add(str(ordner_id))

    try:
        antwort = client.get(endpunkte.ordner_inhalt,
                             params={endpunkte.ordnerparameter: ordner_id})
        if antwort.status_code >= 400:
            sammlung["unlesbar"] += 1
            eintraege: list[Any] = []
        else:
            daten = antwort.json()
            roh = daten.get("elements") if isinstance(daten, Mapping) else daten
            eintraege = roh if isinstance(roh, list) else []
    except Exception:
        sammlung["unlesbar"] += 1
        eintraege = []

    unter: list[Any] = []
    for eintrag in eintraege:
        if not isinstance(eintrag, Mapping):
            continue
        datei = eintrag.get("file")
        if datei is None and eintrag.get("type") == "folder":
            sammlung["ordner"] += 1
            kind = eintrag.get("folder")
            if isinstance(kind, Mapping) and kind.get("canRead") is not False:
                nummer = kind.get("id")
                if nummer is not None:
                    unter.append(nummer)
            continue
        roh_datei = datei or eintrag
        name = str(roh_datei.get("fileName", ""))
        endung = str(roh_datei.get("fileExtension", "")).lstrip(".")
        ganz = f"{name}.{endung}" if endung else name
        if ist_gedaechtnis_datei(ganz) or ist_gedaechtnis_datei(name):
            sammlung["gedaechtnis"] += 1
        else:
            sammlung["dateien"] += 1
            art = endung.lower() or "ohne Endung"
            sammlung["arten"][art] = sammlung["arten"].get(art, 0) + 1
            # Eine einzige Kennung je Ordner merken. Nicht der Name, nicht
            # der Inhalt - nur der Schluessel, mit dem sich gleich pruefen
            # laesst, ob das Herunterladen ueberhaupt erlaubt ist.
            if sammlung["probe"] is None:
                schluessel = str(roh_datei.get("identifier", "")
                                 or roh_datei.get("id", ""))
                if schluessel:
                    sammlung["probe"] = (schluessel, art)

    # Dieselbe Grenze wie im Betrieb: fuenf Stufen tief.
    if tiefe < 5:
        for nummer in unter:
            _ordner_aufteilen(client, endpunkte, nummer, tiefe + 1, gesehen, sammlung)

    if not oberste:
        return sammlung

    _sagen(" ", f"     Ordner gesamt (mit Unterordnern): "
                f"{sammlung['ordner']} Unterordner, {sammlung['dateien']} Dateien, "
                f"Aktengedächtnis: {sammlung['gedaechtnis']}")
    if sammlung["arten"]:
        geordnet = sorted(sammlung["arten"].items(), key=lambda x: -x[1])
        _sagen(" ", "     Dateiarten: " + ", ".join(
            f"{art} {anzahl}" for art, anzahl in geordnet))
        lesbar = {"pdf", "docx", "docm", "dotx", "txt", "md", "csv", "log",
                  "json", "xml", "eml", "msg", "htm", "html", "xhtml", "rtf",
                  "xlsx", "xlsm", "pptx", "pptm",
                  "png", "jpg", "jpeg", "tif", "tiff", "bmp", "gif"}
        fremd = {a: n for a, n in sammlung["arten"].items() if a not in lesbar}
        if fremd:
            _sagen("!", "     Davon nicht lesbar: " + ", ".join(
                f"{a} {n}" for a, n in sorted(fremd.items(), key=lambda x: -x[1])))
            _sagen(" ", "     Diese Arten kann das Programm nicht öffnen.")
        bildhaft = sum(n for a, n in sammlung["arten"].items()
                       if a in ("tif", "tiff", "jpg", "jpeg", "png", "bmp", "gif"))
        if bildhaft:
            _sagen("!", f"     {bildhaft} Bilddateien. Darin steht kein Text,")
            _sagen(" ", "     solange die Texterkennung aus ist.")
    if sammlung["unlesbar"]:
        _sagen("!", f"     {sammlung['unlesbar']} Ordner ließen sich nicht lesen.")
    return sammlung


def _herunterladen_proben(client: Any, endpunkte: Any,
                          woher: str, probe: tuple[str, str] | None) -> None:
    """Laesst sich aus diesem Ordner ueberhaupt eine Datei holen?

    Aus der Kanzlei am 25.09.2026: Im Betrieb wurden 38 von 55 Dokumenten
    gelesen - genau die Zahl des Dateiordners. Die 17 der Korrespondenz
    fehlten vollstaendig, obwohl alle 17 in lesbaren Formaten vorliegen
    (pdf 14, docx 3). Der Verdacht aus der Kanzlei: ein fehlendes Recht.

    Auflisten und Herunterladen sind bei jur|nodes zwei verschiedene Rechte.
    Diese Probe sah bisher nur das Auflisten - und das klappt fuer beide
    Ordner. Damit konnte sie den Unterschied gar nicht zeigen.

    Hier wird je Ordner **eine** Datei geholt. Angezeigt werden Status,
    Byteanzahl und der Wortlaut des Servers - kein Name, kein Inhalt. Die
    Bytes werden nicht gespeichert und nicht ausgegeben.

    **Nicht mehr im Korrespondenzbaum** (07.10.2026). Dort wird seitdem nur
    noch gezaehlt, nie gelesen. Der Grund steht im Lauf vom 07.10.2026:
    Die Akte war am 30.07.2026 angelegt, die Ordner hinter
    ``correspondenceFolderId`` tragen Ablagen von Dezember 2022. Eine Datei
    kann nicht in eine Akte gelegt worden sein, die es noch nicht gab - das
    sind fremde Dateien, und es ist die dritte geprueft Akte mit demselben
    Befund.

    Damit beantwortet diese Leseprobe dort keine Frage mehr: Der Betrieb
    liest den Baum seit dem 05.10.2026 ohnehin nicht, und die Vermutung von
    der Kanzlei (ein fehlendes Recht auf die 17 Dateien) hat sich in etwas
    anderes aufgeloest - es waren nie 17 Dateien dieser Akte. Was bleibt,
    ist der Preis: eine geholte Datei aus einer fremden Handakte. Den zahlt
    diese Probe nicht.
    """
    if probe is None:
        _sagen(" ", f"     {woher}: keine Datei zum Pruefen vorhanden.")
        return
    schluessel, art = probe
    try:
        antwort = client.get(endpunkte.datei_download,
                             params={endpunkte.kennungparameter: schluessel})
    except Exception as e:  # noqa: BLE001 - der Wortlaut zaehlt
        _sagen("✗", f"     {woher}: Herunterladen ({art}) nicht moeglich - {e}")
        return
    if antwort.status_code < 400:
        groesse = len(antwort.content or b"")
        _sagen("✓", f"     {woher}: Herunterladen ({art}) geht - "
                    f"Status {antwort.status_code}, {groesse} Bytes.")
        return
    _sagen("✗", f"     {woher}: Herunterladen ({art}) abgewiesen - "
                f"Status {antwort.status_code}.")
    _wortlaut(antwort)
    if antwort.status_code in (401, 403):
        _sagen(" ", "     Das ist kein Formatproblem und kein Fehler im")
        _sagen(" ", "     Programm: Der Schluessel darf diese Datei nicht")
        _sagen(" ", "     holen. Das Recht wird in jur|nodes vergeben.")


def _kennung_aus_suche(client: Any, endpunkte: Any, aktenzeichen: str) -> str:
    """Von einem Aktenzeichen zur Kennung der Akte.

    jur|nodes fuehrt beides getrennt: ``recordSign`` ist das Aktenzeichen,
    ``identifier`` die Kennung, mit der alle uebrigen Pfade arbeiten. Wer das
    Aktenzeichen einsetzt, wo die Kennung erwartet wird, bekommt 404 - und
    haelt einen Pfad fuer falsch, der richtig ist.
    """
    try:
        antwort = client.get(endpunkte.akten_suche,
                             params={endpunkte.suchparameter: aktenzeichen})
        if antwort.status_code >= 400:
            return ""
        daten = antwort.json()
    except Exception:
        return ""
    eintraege = daten.get("elements") if isinstance(daten, Mapping) else daten
    if isinstance(eintraege, list) and eintraege and isinstance(eintraege[0], Mapping):
        return str(eintraege[0].get("identifier") or "")
    return ""


def _ordner_der_akte(client: Any, endpunkte: Any, kennung: str,
                     feld: str = "fileFolderId") -> str:
    """Eine Ordnernummer der Akte.

    Die Akte nennt zwei: ``fileFolderId`` fuer die Dokumente und
    ``correspondenceFolderId`` fuer die Korrespondenz - dort liegt, was die
    Kanzlei selbst geschrieben hat.
    """
    try:
        antwort = client.get(endpunkte.akte,
                             params={endpunkte.kennungparameter: kennung})
        if antwort.status_code >= 400:
            return ""
        daten = antwort.json()
    except Exception:
        return ""
    if isinstance(daten, Mapping) and daten.get(feld):
        return str(daten[feld])
    return ""


#: Der Befund zum Nachlesen und Weitergeben.
BERICHT = "jurnodestest.txt"


def main(argv: list[str] | None = None) -> int:
    """Fragt die Schnittstelle ab und schreibt den Befund - Schirm und Datei
    zugleich, aus denselben Gruenden wie bei der Laufwerksprobe."""
    from jusperfect.bericht import mitschreiben

    with mitschreiben(BERICHT) as geschrieben:
        ende = _ablauf(argv)
    if geschrieben:
        print(f"  Der Befund steht auch in {BERICHT}.")
        print()
    return ende


def _ablauf(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(
        description="Fragt die jur|nodes-Schnittstelle ab. Liest nur.")
    zerleger.add_argument("--akte", metavar="AKTENZEICHEN", default=None,
                          help="Eine Akte, an der die übrigen Pfade geprüft werden")
    zerleger.add_argument("--kennung", metavar="IDENTIFIER", default=None,
                          help="Die Kennung der Akte, falls sie schon bekannt ist")
    zerleger.add_argument("--beschreibung", metavar="DATEI", default=None,
                          help="Die OpenAPI-Beschreibung des Servers als Datei. "
                               "Ohne Angabe wird die mitgelieferte genommen "
                               f"({BEILIEGENDE_BESCHREIBUNG.name}).")
    argumente = zerleger.parse_args(argv)
    # Leerraum abschneiden. Aus der Kanzlei am 05.10.2026 kam ein Lauf, der
    # nach " X-100-2026" suchte - mit einem Leerzeichen davor, wie es beim
    # Kopieren aus jur|nodes entsteht. Der Server antwortete sauber mit null
    # Treffern, und die halbe Probe lief danach ins Leere: ohne Kennung keine
    # Akte, kein Ordnerbaum, keine Dokumente.
    #
    # Dieselbe Lehre wie am 25.09. beim Benutzernamen: Ein Wert, der wie der
    # Wert aussieht, aber ein Zeichen zu viel hat, kostet einen ganzen Lauf.
    # Abschneiden ist hier gefahrlos - ein Aktenzeichen traegt keinen Leerraum
    # an den Raendern.
    for feld in ("akte", "kennung"):
        wert = getattr(argumente, feld, None)
        if isinstance(wert, str):
            setattr(argumente, feld, wert.strip() or None)

    print(TRENNER)
    print("  jusperfect – antwortet die jur|nodes-Schnittstelle?")
    print(TRENNER)
    print()
    for zeile in _umbrechen(
            "Dieses Programm liest nur. Es schreibt nichts, legt nichts an und "
            "löscht nichts. In der Ausgabe stehen Feldnamen und Anzahl, kein "
            "Akteninhalt. Weist der Server etwas ab, steht sein Wortlaut dabei - "
            "der kommt von ihm, nicht von hier. Ein Blick darauf vor dem "
            "Weitergeben genügt."):
        _sagen(" ", zeile)

    try:
        from jusperfect.config import Einstellungen, KonfigurationsFehler
        from jusperfect.jurnodes.http_adapter import Endpunkte
    except ImportError as fehler:  # pragma: no cover - fehlende Bausteine
        _sagen("✗", f"Das Programm liess sich nicht laden ({fehler}).")
        return 2

    try:
        e = Einstellungen.aus_umgebung()
        endpunkte = Endpunkte.aus_datei(e.jurnodes_endpunkte_datei)
    except KonfigurationsFehler as fehler:
        _sagen("✗", f"Die Einstellungen sind widersprüchlich: {fehler}")
        return 2

    print()
    _sagen(" ", f"Adresse: {e.jurnodes_url or '(nicht gesetzt)'}")
    _sagen(" ", f"Pfade aus: {e.jurnodes_endpunkte_datei or 'der Vorgabe im Programm'}")

    # Die Beschreibung zuerst, und ohne Netz: Sie braucht weder Adresse noch
    # Zugang. Wer nur wissen will, was die Schnittstelle kann, bekommt es hier
    # - auch auf einem Rechner, der gar keinen jur|nodes-Zugang hat.
    # Ohne Angabe die mitgelieferte nehmen. Sie liegt seit dem 05.10.2026 im
    # Programmordner; danach noch zu fragen hiesse, nach etwas zu fragen, das
    # schon dasteht.
    if not argumente.beschreibung and BEILIEGENDE_BESCHREIBUNG.is_file():
        argumente.beschreibung = str(BEILIEGENDE_BESCHREIBUNG)
    if argumente.beschreibung:
        print()
        print(TRENNER)
        print("  Die Beschreibung der Schnittstelle")
        print(TRENNER)
        print()
        gelesen = _beschreibung_aus_datei(argumente.beschreibung, endpunkte)
        if not e.jurnodes_url:
            return 0 if gelesen else 2

    if not e.jurnodes_url:
        print()
        # Die Meldung nennt die Abhilfe, nicht nur den Mangel.
        #
        # Am 01.10.2026 stand hier dreimal dasselbe: "ist nicht gesetzt",
        # dazu der Satz, woher die Adresse kommt. Beides half nicht weiter -
        # wer sie gerade eingetragen hat, liest hier, dass sie fehlt, und
        # sucht beim Eintragen, obwohl das Fenster die Ursache ist.
        _sagen("✗", "JUSPERFECT_JURNODES_URL ist nicht gesetzt.")
        _sagen(" ", "Ohne Adresse gibt es nichts zu fragen. Sie kommt vom")
        _sagen(" ", "jur|nodes-Server der Kanzlei.")
        _sagen(" ", "")
        _sagen(" ", "Eintragen: JURNODES-ZUGANG.bat im Programmordner.")
        _sagen(" ", "Schon eingetragen? Dann ALLE Fenster schliessen und diese")
        _sagen(" ", "Probe neu starten. Windows gibt neu hinterlegte Werte nur")
        _sagen(" ", "an NEU geoeffnete Fenster weiter - ein Fenster, das vorher")
        _sagen(" ", "offen war, kennt sie nicht, auch nach dem Eintragen nicht.")
        return 2

    token = os.environ.get(e.jurnodes_token_var, "").strip()
    benutzer = os.environ.get(e.jurnodes_benutzer_var, "").strip()
    if not token or not benutzer:
        print()
        _sagen("✗", "Es ist kein Zugang hinterlegt.")
        _sagen(" ", f"Gebraucht werden zwei Werte: {e.jurnodes_benutzer_var}")
        _sagen(" ", f"und {e.jurnodes_token_var}. jur|nodes schickt sie als")
        _sagen(" ", "die Kopfzeilen X-Auth-User und X-Auth-Key mit.")
        _sagen(" ", "Sie gehören in die Umgebung, nicht in eine Datei im")
        _sagen(" ", "Programmordner - und nie in das Versionsverzeichnis.")
        return 2

    import httpx

    # jur|nodes vergibt je Bereich einen eigenen Schluessel. Wer erst einen
    # hat, kommt damit durch - die uebrigen Bereiche antworten dann mit einer
    # Ablehnung, und genau das soll die Probe zeigen, statt es zu verschweigen.
    schluessel = {
        bereich: os.environ.get(f"JURNODES_API_KEY_{bereich.upper()}", "").strip()
        for _, bereich in __import__("jusperfect.jurnodes.http_adapter",
                                     fromlist=["BEREICHE"]).BEREICHE
    }
    eigene = {b: s for b, s in schluessel.items() if s}
    if eigene:
        _sagen(" ", "Eigene Schlüssel für: " + ", ".join(sorted(eigene)))

    client = httpx.Client(
        base_url=e.jurnodes_url.rstrip("/"),
        headers={"X-Auth-User": benutzer, "Accept": "application/json"},
        timeout=e.jurnodes_timeout_sekunden,
    )
    _schluessel_anhaengen(client, token, eigene)

    print()
    for zeile in _umbrechen(
            "Der Hersteller laesst je IP-Adresse eine Anfrage zugleich zu. "
            "Dieses Programm fragt deshalb nacheinander - es dauert ein "
            "paar Sekunden laenger und wird dafuer nicht abgewiesen."):
        _sagen(" ", zeile)

    print()
    print(TRENNER)
    geglueckt = _pruefen(client, "Aktensuche", endpunkte.akten_suche,
                         **({endpunkte.suchparameter: argumente.akte} if argumente.akte else {}))

    # Genau die drei Formen, in denen sich die Aktenliste von der Probe
    # unterscheidet - und in denen der Unterschied am 23.09.2026 lag: Die
    # Probe fragte mit dem blanken Aktenzeichen und ohne Seitenangabe, die
    # Aktenliste mit Platzhaltern und mit page=0. Welche davon der Server
    # annimmt, soll er selbst sagen, statt dass jemand es ableitet.
    print()
    _sagen(" ", "So fragt die Aktenliste - drei Formen im Vergleich:")
    begriff = f"%{argumente.akte}%" if argumente.akte else "%"
    for was, zusatz in (("mit Platzhalter, ohne Seitenangabe", {}),
                        ("mit Platzhalter und page=0", {"page": 0}),
                        ("mit Platzhalter und page=1", {"page": 1})):
        _zaehlen(client, was, endpunkte.akten_suche,
                 **{endpunkte.suchparameter: begriff}, **zusatz)

    print()
    _statuswoerter(client, endpunkte)

    if argumente.akte:
        # Die Kennung der Akte ist NICHT ihr Aktenzeichen: jur|nodes fuehrt
        # beides getrennt (identifier und recordSign). Wer hier das
        # Aktenzeichen einsetzt, bekommt 404 und sucht an der falschen Stelle.
        kennung = argumente.kennung or _kennung_aus_suche(client, endpunkte, argumente.akte)
        if not kennung:
            print()
            _sagen("!", "Zu diesem Aktenzeichen wurde keine Kennung gefunden.")
            _sagen(" ", "Die uebrigen Pfade brauchen sie. Mit --kennung laesst")
            _sagen(" ", "sie sich unmittelbar angeben.")
        else:
            print()
            _sagen(" ", f"Kennung der Akte: {kennung}")
            _pruefen(client, "Akte", endpunkte.akte,
                     **{endpunkte.kennungparameter: kennung})
            # Welches WORT steht im Aktenstatus? Daran haengt die Aufbewahrung.
            #
            # jusperfect uebersetzt "archiviert"/"archived" in "archiviert" und
            # JEDES andere Wort stillschweigend in "laufend". Eine Akte, deren
            # Status anders heisst, wird damit nie abschlussreif - und der
            # Befund "status_unbekannt", der einen Menschen einschalten soll,
            # kann auf diesem Weg gar nicht entstehen.
            #
            # Welche Woerter der Server wirklich fuehrt, stand in keinem
            # Bericht: Die Probe zeigte den Feldnamen, nicht den Wert. Fuer
            # die Loeschfristen der DSFA ist genau das die Frage.
            try:
                _a = client.get(endpunkte.akte,
                                params={endpunkte.kennungparameter: kennung})
                _d = _a.json() if _a.status_code < 400 else None
            except Exception:
                _d = None
            if _d is not None:
                _sagen(" ", "Die Woerter, an denen die Aufbewahrung haengt:")
                _arten_zeigen(_d)
            # Die Frage des 02.10.2026: Bleibt der Durchlauf in der Akte?
            # Sie steht hier und nicht in einer eigenen Startdatei, weil sie
            # dieselbe Akte, denselben Zugang und denselben Client braucht -
            # und weil eine Probe, die niemand startet, nichts prueft.
            _ordnerbaum(client, endpunkte, kennung)
            _pruefen(client, "Beteiligte", endpunkte.beteiligte,
                     **{endpunkte.akteparameter: kennung})
            _pruefen(client, "Fristen", endpunkte.fristen,
                     **{endpunkte.akteparameter: kennung,
                        "type": endpunkte.fristenart})
            # Vermerke, darunter Telefonvermerke. Aus der Kanzlei am
            # 25.09.2026: "Vermerke, auch Telefonvermerke waeren wichtig."
            #
            # Der Hersteller fuehrt GET /record/note mit "id" ODER "record".
            # Ob ein Aufruf mit der Aktenkennung ALLE Vermerke liefert oder
            # nur einen, steht nirgends - das Antwortschema ist Einzahl. Also
            # wird gefragt, nicht geraten.
            _vermerke_suchen(client, endpunkte, kennung, argumente.akte or "")

            # Der Korrespondenzordner wird hier NICHT mehr abgefragt.
            #
            # **Aufgeloest am 08.10.2026.** Dreimal trug der Ordner hinter
            # correspondenceFolderId Dateien, die aelter waren als die Akte,
            # und dreimal wurde daraus geschlossen, das Feld zeige nicht auf
            # diese Akte. Das Feld war die ganze Zeit richtig.
            #
            # jur|nodes fuehrt ZWEI getrennte Ordnerbaeume mit je eigenen
            # Nummern. Die 2871 aus correspondenceFolderId wurde an
            # /file-system/folder/content gefragt - das ist der Pfad des
            # DATEIbaums. Er liefert den Datei-Ordner Nr. 2871, nicht den
            # Korrespondenz-Ordner Nr. 2871. Beide gibt es, beide tragen
            # dieselbe Zahl, und sie haben nichts miteinander zu tun.
            #
            # Derselbe Fehler wie am 02.10.2026, nur an einer zweiten Stelle.
            # Beim ersten Mal kostete er drei fremde Schriftstuecke in einer
            # Bausache; beim zweiten Mal eine Woche Arbeit an einer Frage an
            # den Hersteller, die keine war.
            #
            # Der Beleg steht im Lauf vom 08.10.2026: Alle 26 Eintraege der
            # E-Akte nennen als folderId genau jene 2871, und ihre
            # Poststempel liegen zwischen dem 30.07. und dem 25.09.2026 -
            # innerhalb der Lebenszeit der Akte.
            #
            # Die E-Akte wird ueber POST /correspondence/search gelesen. Der
            # Weg nennt die Akte in der Anfrage und kann sie deshalb gar
            # nicht verwechseln.
            _sagen(" ", "")
            _sagen("✓", "Der Korrespondenzordner wird nicht mehr am Dateipfad")
            _sagen(" ", "gefragt. Seine Nummer gehoert in den Korrespondenzbaum;")
            _sagen(" ", "dieselbe Zahl benennt im Dateibaum einen voellig anderen")
            _sagen(" ", "Ordner. Die E-Akte steht oben, ueber /correspondence/search.")
            ordner = _ordner_der_akte(client, endpunkte, kennung)
            if ordner:
                _pruefen(client, "Dokumente (Dateiordner)", endpunkte.ordner_inhalt,
                         **{endpunkte.ordnerparameter: ordner})
                befund = _ordner_aufteilen(client, endpunkte, ordner)
                _herunterladen_proben(client, endpunkte, "Dateiordner",
                                      befund.get("probe"))
            else:
                print()
                _sagen("!", "Die Akte nennt keinen Dateiordner (fileFolderId).")
                _sagen(" ", "Ohne ihn sind die Dokumente nicht zu erreichen.")
    else:
        print()
        _sagen(" ", "Mit --akte AKTENZEICHEN werden auch Akte, Dokumente,")
        _sagen(" ", "Beteiligte und Fristen abgefragt.")

    # Welche Methoden nimmt ein schreibender Pfad ueberhaupt an? Das sagt der
    # Server auf OPTIONS - und OPTIONS schreibt nichts, legt nichts an und
    # loescht nichts. Es ist die einzige Frage, die man einem schreibenden Pfad
    # stellen darf, ohne die Zusage dieses Programms zu brechen.
    #
    # Gebraucht wird sie, seit der Server der Kanzlei am 24.09.2026 auf
    # POST /file-system/add-file mit 405 antwortete, obwohl seine eigene
    # Beschreibung diesen Aufruf fuehrt.
    print()
    _sagen(" ", "Was die schreibenden Pfade annehmen (nur gefragt, nicht benutzt):")
    for name, pfad in (("Vermerk", endpunkte.vermerke),
                       ("Datei ablegen", endpunkte.datei_hinzufuegen)):
        _methoden(client, name, pfad)

    print()
    _sagen(" ", f"Nicht angefasst: {endpunkte.vermerke} (POST, schreibt einen Vermerk)")
    _sagen(" ", f"und {endpunkte.datei_hinzufuegen} (POST, legt eine Datei ab).")
    _sagen(" ", "Dieses Programm schreibt grundsätzlich nicht.")

    print()
    print(TRENNER)
    if geglueckt:
        _sagen("✓", "Die Schnittstelle antwortet.")
        _sagen(" ", "Schicken Sie diese Ausgabe an die Entwicklung: Aus den")
        _sagen(" ", "Feldnamen ergibt sich die Zuordnung, und die ist danach")
        _sagen(" ", "eine Sache von Stunden statt von Wochen.")
    else:
        _sagen("!", "Kein Pfad hat geantwortet.")
        _sagen(" ", "Das ist der erwartete Fall, solange die Pfade geraten sind -")
        _sagen(" ", "und kein Grund zur Sorge. Gebraucht wird vom Hersteller die")
        _sagen(" ", "OpenAPI- oder Swagger-Datei des Kanzleiservers. Steht sie")
        _sagen(" ", "zur Verfügung, werden die Pfade eingetragen und dieses")
        _sagen(" ", "Programm noch einmal gestartet.")
    print(TRENNER)
    print()
    return 0 if geglueckt else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
