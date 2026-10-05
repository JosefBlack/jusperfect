"""Entwürfe: erzeugen, bearbeiten, freigeben – und erst dann nach jur|nodes.

Ein Entwurf ist bis zur Freigabe ein temporäres Objekt im Sitzungsspeicher.
Freigeben kann nur, wer ihn erstellt hat, und nur mit ausdrücklicher
Bestätigung des exakt angezeigten Textes. Die Freigabe ist an diesen Text
gebunden; der jur|nodes-Adapter prüft sie, bevor er schreibt.
"""

from __future__ import annotations

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


class Entwurfsdienst:
    def __init__(self, ausgang: Ausgang, speicher: SitzungsSpeicher,
                 adapter: JurNodesAdapter, freigabestelle: Freigabestelle, einstellungen: Einstellungen) -> None:
        self._ausgang = ausgang
        self._speicher = speicher
        self._adapter = adapter
        self._freigabestelle = freigabestelle
        self._e = einstellungen

    def erstellen(self, identitaet: Identitaet, sitzung: Sitzung, passagen: list[Passage], art: EntwurfArt,
                  anweisung: str, empfaenger: str, beteiligte: list[Beteiligter], fristen: list[Frist],
                  muster: str = "", referenzen: list[Passage] = ()) -> Entwurf:
        if not passagen:
            raise EntwurfFehler("Es sind keine Dokumente geladen.")
        auswahl = relevante_passagen(f"{ENTWURF_BEZEICHNUNG[art]} {anweisung} {empfaenger}", passagen, self._e.max_frage_passagen * 2)
        if referenzen:
            auswahl = auswahl + list(referenzen)
        auswahl, gekuerzt = budget_anwenden(auswahl, self._e.max_passagen_zeichen)
        material = prompts.material_bauen(sitzung.akte, beteiligte, fristen, auswahl)
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
        entwurf = self._speicher.entwurf_lesen(entwurf_id)
        if entwurf is None or entwurf.erstellt_von != identitaet.nutzer_id:
            raise EntwurfNichtGefunden("Der Entwurf ist unbekannt oder abgelaufen.")
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

    def freigeben(self, identitaet: Identitaet, entwurf_id: str, bestaetigung: bool, text_pruefsumme: str) -> Entwurf:
        """Schreibt den Entwurf als Vermerk in die jur|nodes-Akte.

        ``text_pruefsumme`` ist die Prüfsumme des Textes, den die Oberfläche
        angezeigt hat. So kann niemand einen Text freigeben, den er nicht
        gesehen hat – auch nicht durch einen zwischenzeitlichen Bearbeitungsschritt.
        """
        from jusperfect.security.approval import text_pruefsumme as pruefsumme

        entwurf = self.lesen(identitaet, entwurf_id)
        if not bestaetigung:
            raise EntwurfFehler("Ohne ausdrückliche Bestätigung wird nichts nach jur|nodes geschrieben.")
        if entwurf.status != EntwurfStatus.ENTWURF:
            raise EntwurfFehler("Der Entwurf wurde bereits freigegeben oder verworfen.")
        if pruefsumme(entwurf.text) != text_pruefsumme:
            raise EntwurfFehler("Der angezeigte Text stimmt nicht mit dem gespeicherten Entwurf überein. Bitte neu laden.")
        text_fuer_akte = f"{KENNZEICHNUNG}\n{entwurf.betreff}\n\n{entwurf.text}"
        freigabe = self._freigabestelle.erteilen(entwurf.id, entwurf.akte_id, identitaet.nutzer_id, text_fuer_akte)
        referenz = self._adapter.vermerk_schreiben(entwurf.akte_id, f"{ENTWURF_BEZEICHNUNG[entwurf.art]}: {entwurf.betreff}",
                                                   text_fuer_akte, freigabe)
        entwurf = entwurf.model_copy(update={"status": EntwurfStatus.FREIGEGEBEN, "jurnodes_referenz": referenz})
        self._speicher.entwurf_ablegen(entwurf)
        ereignis(_log, "entwurf_freigegeben", entwurf_id=entwurf.id, akte=entwurf.akte_id, nutzer=identitaet.nutzer_id,
                 referenz=referenz, pruefsumme=text_pruefsumme[:12])
        return entwurf

    def verwerfen(self, identitaet: Identitaet, entwurf_id: str) -> None:
        entwurf = self.lesen(identitaet, entwurf_id)
        self._speicher.entwurf_loeschen(entwurf.id)
        ereignis(_log, "entwurf_verworfen", entwurf_id=entwurf_id)
