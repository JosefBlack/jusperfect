"""Entwürfe: erzeugen, bearbeiten, freigeben – und erst dann nach jur|nodes.

Ein Entwurf ist bis zur Freigabe ein temporäres Objekt im Sitzungsspeicher.
Freigeben kann nur, wer ihn erstellt hat, und nur mit ausdrücklicher
Bestätigung des exakt angezeigten Textes. Die Freigabe ist an diesen Text
gebunden; der jur|nodes-Adapter prüft sie, bevor er schreibt.
"""

from __future__ import annotations

import threading
import uuid

from jusperfect.config import Einstellungen
from jusperfect.domain.models import (
    Beteiligter, Entwurf, EntwurfArt, EntwurfStatus, ENTWURF_BEZEICHNUNG, Frist, Passage, Sitzung,
)
from jusperfect.jurnodes.base import JurNodesAdapter
from jusperfect.security.approval import Freigabestelle
from jusperfect.security.identitaet import Identitaet
from jusperfect.security.protokoll import ereignis, protokoll
from jusperfect.services import prompts
# Umbenannt: siehe analyse.py - der Parameter "fristen" wuerde das
# Modul innerhalb der Methode ueberdecken.
from jusperfect.services.belegpflicht import entwurf_fail_closed
from jusperfect.services.fristen import (
    entschaerfen as frist_entschaerfen,
    hinweis as frist_hinweis,
)
from jusperfect.services.ausgang import Ausgang, Ausgangskontext
from jusperfect.services.json_ausgabe import AusgabeUnbrauchbar, json_extrahieren
from jusperfect.services.passagen import budget_anwenden, relevante_passagen
from jusperfect.services.quellen import index_bauen
from jusperfect.speicher.base import SitzungsSpeicher

_log = protokoll("entwuerfe")

KENNZEICHNUNG = "ENTWURF – anwaltliche Prüfung erforderlich"


class EntwurfFehler(RuntimeError):
    pass


class EntwurfNichtGefunden(LookupError):
    pass


FREIGABE_FASSUNG = "1"


def freigabevorlage(entwurf) -> str:
    """Genau das, was nach jur|nodes geschrieben wird – als ein Text.

    Befund F06 der Zweitprüfung vom 05.10.2026. Bestätigt wurde bisher die
    Prüfsumme **des Textes**. Geschrieben werden aber vier Dinge: Akte, Art,
    Betreff und Text. Fenster A lud den Entwurf, Fenster B änderte nur den
    Betreff, Fenster A gab mit der alten Prüfsumme frei – und der neue, dort
    nie gesehene Betreff ging in den Vermerktext **und** in den Titel nach
    jur|nodes.

    Die Kryptografie war dabei nicht gebrochen; sie signierte nur das, was ihr
    gegeben wurde, und das war zu wenig. Deshalb steht hier eine *Vorlage*:
    eine feste, benannte Reihenfolge über alle geschriebenen Felder. Ändert
    sich eines, ändert sich die Prüfsumme, und die Freigabe wird abgewiesen.

    Die Fassungsnummer in der ersten Zeile ist kein Zierrat: Kommt ein Feld
    hinzu, bekommt sie eine neue Nummer, und alte Prüfsummen passen nicht mehr
    – was richtig ist, denn sie bezeugen eine Ansicht, die es nicht mehr gibt.
    """
    return "\n".join([
        f"jusperfect-freigabe/{FREIGABE_FASSUNG}",
        f"akte: {entwurf.akte_id}",
        f"art: {getattr(entwurf.art, 'value', entwurf.art)}",
        f"betreff: {entwurf.betreff}",
        "text:",
        entwurf.text,
    ])


class Entwurfsdienst:
    def __init__(self, ausgang: Ausgang, speicher: SitzungsSpeicher,
                 adapter: JurNodesAdapter, freigabestelle: Freigabestelle,
                 einstellungen: Einstellungen, berechtigungen=None) -> None:
        self._ausgang = ausgang
        self._speicher = speicher
        self._adapter = adapter
        self._freigabestelle = freigabestelle
        self._e = einstellungen
        # Befund F07: Die Aktenberechtigung wurde beim Entwurf nie geprueft -
        # nur, ob der Nutzer ihn selbst angelegt hat. Wer die Akte verlor,
        # konnte den fertigen Entwurf weiter lesen und freigeben.
        self._berechtigungen = berechtigungen
        # Pruefen, Statuswechsel und Schreiben gehoeren zusammen. Ohne diese
        # Klammer gaben zwei gleichzeitige Freigaben beide den Statustest frei
        # und schrieben zwei Vermerke in dieselbe Akte.
        self._freigabeschloss = threading.Lock()

    def erstellen(self, identitaet: Identitaet, sitzung: Sitzung, passagen: list[Passage], art: EntwurfArt,
                  anweisung: str, empfaenger: str, beteiligte: list[Beteiligter], fristen: list[Frist],
                  muster: str = "", referenzen: list[Passage] = ()) -> Entwurf:
        if not passagen:
            raise EntwurfFehler("Es sind keine Dokumente geladen.")
        auswahl = relevante_passagen(f"{ENTWURF_BEZEICHNUNG[art]} {anweisung} {empfaenger}", passagen, self._e.max_frage_passagen * 2)
        if referenzen:
            auswahl = auswahl + list(referenzen)
        auswahl, gekuerzt = budget_anwenden(auswahl, self._e.max_passagen_zeichen)
        # Der eine Aufruf, der das Aktenzeichen braucht: Ein Anschreiben traegt
        # "Unser Zeichen". Ueberall sonst bleibt es drinnen (Befund F11).
        material = prompts.material_bauen(sitzung.akte, beteiligte, fristen, auswahl,
                                          mit_aktenzeichen=True)
        aufgabe = prompts.aufgabe_entwurf(art, anweisung, empfaenger, muster)
        kontext = Ausgangskontext(identitaet, sitzung.id, sitzung.akte_id, "entwurf",
                                  passagen=len(auswahl), detail=art.value)
        durchgang = self._ausgang.fragen(kontext, prompts.SYSTEM, material, aufgabe)
        antwort = durchgang.antwort
        try:
            roh = json_extrahieren(antwort.text)
            betreff, text = str(roh.get("betreff", "")).strip(), str(roh.get("text", "")).strip()
        except AusgabeUnbrauchbar:
            betreff, text = ENTWURF_BEZEICHNUNG[art], antwort.text.strip()
        if not text:
            raise EntwurfFehler("Das Modell hat keinen Entwurf geliefert.")
        index = index_bauen(auswahl)
        # Fail closed, auch im Entwurf (Befund F04 der Zweitpruefung,
        # 05.10.2026). Vorher stand hier nur `zitate_aufloesen`: Das setzt an
        # die Stelle eines nicht auflösbaren Belegs die Marke „[Q: ohne
        # Beleg]" und laesst die Behauptung stehen. Ein vollstaendig
        # erfundener Entwurf kam so mit HTTP 201 und leerer Quellenliste
        # heraus - die leere Liste sagt es dem Programm, gesehen hat sie
        # niemand.
        ergebnis = entwurf_fail_closed(text, index)
        text, quellen, hinweise = ergebnis.text, ergebnis.quellen, list(ergebnis.hinweise)
        if not quellen:
            raise EntwurfFehler(
                "Der Entwurf trug keinen einzigen belastbaren Beleg und wird deshalb "
                "nicht ausgegeben. Bitte die Anweisung genauer fassen oder die Auswahl "
                "der Dokumente prüfen.")
        if ergebnis.verworfen:
            hinweise.insert(0, f"{ergebnis.verworfen} Aussage(n) ohne belastbaren Beleg "
                               f"aus dem Entwurf entfernt.")
        # Ein Entwurf geht am Ende hinaus. Eine gerechnete Frist darin waere der
        # teuerste Fehler, den dieses Programm machen kann.
        text, gerechnet = frist_entschaerfen(text, index, fristen)
        if gerechnet:
            hinweise.append(frist_hinweis(gerechnet))
        if gekuerzt:
            hinweise.append("Nicht alle Passagen passten in den Aufruf; der Entwurf beruht auf einer Auswahl.")
        entwurf = Entwurf(
            id=uuid.uuid4().hex, akte_id=sitzung.akte_id, art=art, betreff=betreff or ENTWURF_BEZEICHNUNG[art],
            text=text, quellen=quellen, hinweise=hinweise, erstellt_von=identitaet.nutzer_id, modell=antwort.modell,
            kosten=durchgang.kosten,
        )
        self._speicher.entwurf_ablegen(entwurf)
        return entwurf

    def lesen(self, identitaet: Identitaet, entwurf_id: str) -> Entwurf:
        """Der Entwurf – und nur, wenn die Akte jetzt noch offensteht.

        Befund F07 der Zweitprüfung vom 05.10.2026: Geprüft wurde allein die
        Erstellerkennung. Ein Nutzer, dem die Akte entzogen worden war, bekam
        auf die Sitzung richtig 403 – und konnte denselben Entwurf weiter
        lesen und sogar freigeben, also in genau diese Akte schreiben.

        Geprüft wird bei **jedem** Zugriff neu, nicht beim Anlegen: Eine
        Rechteänderung wirkt sonst erst beim nächsten Entwurf, und der
        vorbereitete Schreibweg bleibt offen.

        Dass in dieser Kanzlei alle alle Akten sehen, ändert daran nichts –
        dann geht die Prüfung eben immer durch. Die Lücke bestand für den
        eingeschränkten Betrieb, den das Programm ausdrücklich kann.
        """
        entwurf = self._speicher.entwurf_lesen(entwurf_id)
        if entwurf is None or entwurf.erstellt_von != identitaet.nutzer_id:
            raise EntwurfNichtGefunden("Der Entwurf ist unbekannt oder abgelaufen.")
        if self._berechtigungen is not None:
            self._berechtigungen.pruefen(identitaet, entwurf.akte_id)
        return entwurf

    def bearbeiten(self, identitaet: Identitaet, entwurf_id: str, betreff: str, text: str) -> Entwurf:
        entwurf = self.lesen(identitaet, entwurf_id)
        if entwurf.status != EntwurfStatus.ENTWURF:
            raise EntwurfFehler("Ein freigegebener oder verworfener Entwurf wird nicht mehr geändert.")
        if not text.strip():
            raise EntwurfFehler("Der Text darf nicht leer sein.")
        entwurf = entwurf.model_copy(update={"betreff": betreff.strip() or entwurf.betreff, "text": text})
        self._speicher.entwurf_ablegen(entwurf)
        return entwurf

    def freigeben(self, identitaet: Identitaet, entwurf_id: str, bestaetigung: bool,
                  freigabe_pruefsumme: str) -> Entwurf:
        """Schreibt den Entwurf als Vermerk in die jur|nodes-Akte.

        ``freigabe_pruefsumme`` ist die Prüfsumme der **Freigabevorlage** –
        Akte, Art, Betreff und Text zusammen, also alles, was geschrieben
        wird. Bis zum 05.10.2026 war es die Prüfsumme des Textes allein; ein
        in einem anderen Fenster geänderter Betreff kam damit ungesehen in den
        Vermerk und in den Titel (Befund F06, siehe ``freigabevorlage``).

        Prüfen, Statuswechsel und Schreiben stehen unter einem Schloss und in
        dieser Reihenfolge. Vorher wurde erst geschrieben und dann der Status
        gesetzt: Zwei gleichzeitige Freigaben kamen beide am Statustest vorbei
        und schrieben zwei Vermerke in dieselbe Akte.
        """
        from jusperfect.security.approval import text_pruefsumme as pruefsumme

        with self._freigabeschloss:
            entwurf = self.lesen(identitaet, entwurf_id)
            if not bestaetigung:
                raise EntwurfFehler("Ohne ausdrückliche Bestätigung wird nichts nach jur|nodes geschrieben.")
            if entwurf.status != EntwurfStatus.ENTWURF:
                raise EntwurfFehler("Der Entwurf wurde bereits freigegeben oder verworfen.")
            if pruefsumme(freigabevorlage(entwurf)) != freigabe_pruefsumme:
                raise EntwurfFehler(
                    "Der angezeigte Entwurf stimmt nicht mehr mit dem gespeicherten überein – "
                    "Betreff oder Text wurden zwischenzeitlich geändert. Bitte neu laden.")
            # Erst sperren, dann schreiben: Schlaegt das Schreiben fehl, geht
            # der Entwurf zurueck in den Entwurfsstand, und der Fehler geht
            # weiter. Ein zweiter Aufruf findet bis dahin "bereits freigegeben".
            gesperrt = entwurf.model_copy(update={"status": EntwurfStatus.FREIGEGEBEN})
            self._speicher.entwurf_ablegen(gesperrt)
            text_fuer_akte = f"{KENNZEICHNUNG}\n{entwurf.betreff}\n\n{entwurf.text}"
            try:
                freigabe = self._freigabestelle.erteilen(entwurf.id, entwurf.akte_id,
                                                         identitaet.nutzer_id, text_fuer_akte)
                referenz = self._adapter.vermerk_schreiben(
                    entwurf.akte_id, f"{ENTWURF_BEZEICHNUNG[entwurf.art]}: {entwurf.betreff}",
                    text_fuer_akte, freigabe)
            except Exception:
                self._speicher.entwurf_ablegen(entwurf)
                raise
            entwurf = gesperrt.model_copy(update={"jurnodes_referenz": referenz})
            self._speicher.entwurf_ablegen(entwurf)
        ereignis(_log, "entwurf_freigegeben", entwurf_id=entwurf.id, akte=entwurf.akte_id, nutzer=identitaet.nutzer_id,
                 referenz=referenz, pruefsumme=freigabe_pruefsumme[:12])
        return entwurf

    def verwerfen(self, identitaet: Identitaet, entwurf_id: str) -> None:
        entwurf = self.lesen(identitaet, entwurf_id)
        self._speicher.entwurf_loeschen(entwurf.id)
        ereignis(_log, "entwurf_verworfen", entwurf_id=entwurf_id)
