"""Übersicht über alle Arbeitsbereiche – für die Verwaltung der Kanzlei.

Die Aufbewahrung folgt dem Aktenstatus in jurnodes. Wo dieser Status fehlt,
nicht gelesen werden kann oder die Akte gar nicht mehr existiert, darf
jusperfect nichts löschen – solche Fälle blieben ohne diese Übersicht aber
unsichtbar liegen. Genau dafür ist sie da: Sie zeigt, was ein Mensch
entscheiden muss.

Sie verändert nichts und zeigt keine Akteninhalte, nur Kennzahlen, Zustände
und Zeitpunkte.
"""

from __future__ import annotations

from datetime import datetime, timezone

from jusperfect.domain.models import Aktengedaechtnis
from jusperfect.gedaechtnis.base import GedaechtnisFehler
from jusperfect.jurnodes.base import AkteNichtGefunden, JurNodesAdapter, JurNodesFehler
from jusperfect.security.berechtigungen import Berechtigungen, ZugriffVerweigert
from jusperfect.security.identitaet import Identitaet
from jusperfect.services.abschluss import ABSCHLUSSSTATUS
from jusperfect.services.gedaechtnis import Gedaechtnisdienst

#: Befunde, die eine Entscheidung durch einen Menschen verlangen.
BEFUND_TEXT = {
    "akte_fehlt": "Die Akte ist in jurnodes nicht mehr auffindbar; der Arbeitsbereich ist verwaist.",
    "jurnodes_nicht_erreichbar": "Der Status konnte nicht aus jurnodes gelesen werden.",
    "status_unbekannt": "jurnodes meldet keinen Status; es wird nicht gelöscht.",
    "abschluss_vorgemerkt": "Der Abschluss ist vorgemerkt; die Übergangsfrist läuft.",
    "loeschung_faellig": "Die Übergangsfrist ist abgelaufen; der Abschluss kann ausgeführt werden.",
    "abschlussreif_ohne_vormerkung": "Die Akte ist in jurnodes abgeschlossen, der Abschluss aber noch nicht vorgemerkt.",
}

#: Was der Mensch daraufhin tun kann. Ein Befund ohne naechsten Schritt ist eine
#: Beunruhigung: Er sagt, dass etwas nicht stimmt, und laesst den Leser damit
#: allein. Beide Saetze stehen hier nebeneinander, damit sie nicht auseinander
#: laufen - der Befund kommt von der Pruefung, der Schritt gehoert dazu.
SCHRITT_TEXT = {
    "akte_fehlt": "Prüfen, ob die Akte in jurnodes umbenannt, verschoben oder gelöscht wurde. "
                  "Ist sie endgültig fort, kann dieser Arbeitsbereich nach Export gelöscht werden.",
    "jurnodes_nicht_erreichbar": "Verbindung zu jurnodes prüfen (Netzlaufwerk, Zugang). "
                                 "Bis dahin wird hier nichts gelöscht.",
    "status_unbekannt": "Den Aktenstatus in jurnodes setzen. Ohne ihn bleibt der "
                        "Arbeitsbereich unbefristet erhalten.",
    "abschluss_vorgemerkt": "Nichts. Die Frist läuft; danach steht die Akte hier erneut.",
    "loeschung_faellig": "Akte öffnen und den Abschluss ausführen: erst Export nach jurnodes, "
                         "dann Löschung des Arbeitsbereichs.",
    "abschlussreif_ohne_vormerkung": "Akte öffnen und den Abschluss vormerken – oder den Status "
                                     "in jurnodes richtigstellen, falls das Mandat weiterläuft.",
}


class Aufsichtsdienst:
    def __init__(self, gedaechtnis: Gedaechtnisdienst, adapter: JurNodesAdapter,
                 berechtigungen: Berechtigungen) -> None:
        self._gedaechtnis = gedaechtnis
        self._adapter = adapter
        self._berechtigungen = berechtigungen

    def uebersicht(self, identitaet: Identitaet) -> dict:
        """Alle Arbeitsbereiche mit ihrem Aufbewahrungszustand.

        Nur wer alle Akten sehen darf, sieht die Übersicht: Sie führt
        zwangsläufig Akten zusammen, für die im Einzelfall keine
        Berechtigung bestünde.
        """
        nutzer = self._berechtigungen.nutzer(identitaet)
        if "*" not in nutzer.akten:
            raise ZugriffVerweigert("Die Übersicht der Arbeitsbereiche ist der Verwaltung vorbehalten.")
        if not self._gedaechtnis.aktiv:
            raise GedaechtnisFehler("Das Gedächtnis ist nicht aktiviert.")

        eintraege = [self._eintrag(g) for g in self._gedaechtnis.auflisten()]
        eintraege.sort(key=lambda x: (not x["handlungsbedarf"], x["aktenzeichen"]))
        return {
            "stand": datetime.now(timezone.utc),
            "arbeitsbereiche": len(eintraege),
            "handlungsbedarf": sum(1 for x in eintraege if x["handlungsbedarf"]),
            "eintraege": eintraege,
        }

    def _eintrag(self, g: Aktengedaechtnis) -> dict:
        status, befunde = self._pruefen(g)
        jetzt = datetime.now(timezone.utc)
        faellig = bool(g.loeschung_vorgesehen_am and g.loeschung_vorgesehen_am <= jetzt)
        if g.loeschung_vorgesehen_am is not None:
            befunde.append("loeschung_faellig" if faellig else "abschluss_vorgemerkt")
        elif status in ABSCHLUSSSTATUS:
            befunde.append("abschlussreif_ohne_vormerkung")
        return {
            "akte_id": g.akte_id,
            "aktenzeichen": g.aktenzeichen,
            "bezeichnung": g.bezeichnung,
            "aktenstatus": status,
            "retention_reason": g.retention_reason,
            "status_geprueft_am": g.status_geprueft_am,
            "abgeschlossen_am": g.abgeschlossen_am,
            "loeschung_vorgesehen_am": g.loeschung_vorgesehen_am,
            "faellig": faellig,
            "dokumente": len(g.dokumente),
            "fragen": len(g.fragen_antworten),
            "aktualisiert_am": g.aktualisiert_am,
            "befunde": befunde,
            "hinweise": [BEFUND_TEXT[b] for b in befunde],
            "schritte": [SCHRITT_TEXT[b] for b in befunde],
            "handlungsbedarf": bool(befunde),
        }

    def _pruefen(self, g: Aktengedaechtnis) -> tuple[str, list[str]]:
        """Der Status, wie jurnodes ihn jetzt meldet – und was daran auffällt."""
        try:
            akte = self._adapter.akte(g.akte_id)
        except AkteNichtGefunden:
            return g.aktenstatus, ["akte_fehlt"]
        except JurNodesFehler:
            return g.aktenstatus, ["jurnodes_nicht_erreichbar"]
        status = (akte.status or "unbekannt").strip().lower()
        return status, ["status_unbekannt"] if status in ("", "unbekannt") else []
