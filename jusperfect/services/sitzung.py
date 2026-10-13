"""Die Aktensitzung: Berechtigung prüfen, Dokumente holen, Text bereithalten, aufräumen.

Der Datenfluss aus dem Konzept in Code: Akte öffnen -> Berechtigung prüfen ->
benötigte Dokumente aus jur|nodes laden -> temporär Text extrahieren ->
(Analyse) -> temporäre Daten löschen. Alles hier arbeitet über den
Sitzungsspeicher, damit es in Lambda ebenso läuft wie lokal.
"""

from __future__ import annotations

import json
import uuid
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from jusperfect.domain.models import (
    Akte, Antwort, Beteiligter, DialogEintrag, Dokument, Frist, GeladenesDokument, Passage, Seite, Sitzung,
)
from jusperfect.jurnodes.base import JurNodesAdapter, JurNodesFehler
from jusperfect.ocr.base import OcrDienst, OcrFehler
from jusperfect.security.berechtigungen import Berechtigungen, ZugriffVerweigert
from jusperfect.security.identitaet import Identitaet
from jusperfect.security.protokoll import ereignis, protokoll
from jusperfect.services.extraktion import NichtUnterstuetzt, text_extrahieren
from jusperfect.services.passagen import passagen_bilden
from jusperfect.speicher.base import SitzungsSpeicher

if TYPE_CHECKING:
    from jusperfect.services.gedaechtnis import Gedaechtnisdienst

_log = protokoll("sitzung")


class SitzungNichtGefunden(LookupError):
    pass


class Sitzungsdienst:
    def __init__(self, adapter: JurNodesAdapter, speicher: SitzungsSpeicher,
                 berechtigungen: Berechtigungen, ocr: OcrDienst,
                 gedaechtnis: Gedaechtnisdienst | None = None,
                 dialog_max_runden: int = 6) -> None:
        self._adapter = adapter
        self._speicher = speicher
        self._berechtigungen = berechtigungen
        self._ocr = ocr
        self._gedaechtnis = gedaechtnis
        self._dialog_max_runden = dialog_max_runden

    # ── Akten ──────────────────────────────────────────────────────────────

    def akten_suchen(self, identitaet: Identitaet, suchbegriff: str = "") -> list[Akte]:
        return self._berechtigungen.filtern(identitaet, self._adapter.akten_suchen(suchbegriff))

    # ── Sitzung ────────────────────────────────────────────────────────────

    def eroeffnen(self, identitaet: Identitaet, akte_id: str) -> Sitzung:
        self._berechtigungen.pruefen(identitaet, akte_id)
        akte = self._adapter.akte(akte_id)
        sitzung = Sitzung(id=uuid.uuid4().hex, nutzer_id=identitaet.nutzer_id, akte_id=akte_id, akte=akte)
        self._speicher.sitzung_ablegen(sitzung)
        if self._gedaechtnis is not None:
            sitzung = self._gedaechtnis.bei_eroeffnen(sitzung)
        ereignis(_log, "sitzung_eroeffnet", sitzung=sitzung.id, nutzer=identitaet.nutzer_id, akte=akte_id)
        return sitzung

    def laden(self, identitaet: Identitaet, sitzung_id: str) -> Sitzung:
        sitzung = self._speicher.sitzung_lesen(sitzung_id)
        if sitzung is None:
            raise SitzungNichtGefunden("Die Sitzung ist abgelaufen oder unbekannt. Bitte Akte erneut öffnen.")
        if sitzung.nutzer_id != identitaet.nutzer_id:
            # Fremde Sitzungen sind unsichtbar, nicht "verboten" – kein Hinweis auf ihre Existenz.
            raise SitzungNichtGefunden("Die Sitzung ist abgelaufen oder unbekannt. Bitte Akte erneut öffnen.")
        # Die Berechtigung kann zwischenzeitlich entzogen worden sein.
        self._berechtigungen.pruefen(identitaet, sitzung.akte_id)
        return sitzung

    def schliessen(self, identitaet: Identitaet, sitzung_id: str) -> None:
        sitzung = self._speicher.sitzung_lesen(sitzung_id)
        if sitzung is not None and sitzung.nutzer_id == identitaet.nutzer_id:
            self._speicher.sitzung_loeschen(sitzung_id)
            # Befund N10 der dritten Zweitpruefung vom 12.10.2026: Hier stand
            # nur das Loeschen der Sitzung. Der Adapter hielt daneben den
            # Klartext der Mails und ihrer Anlagen - auch den von Mails, die
            # beim Aufbau der Liste geholt und nie ausgewaehlt wurden. Nach dem
            # Schliessen war die Sitzung weg und der Mailtext noch da.
            #
            # Ein Loeschen, das eine Kopie stehen laesst, ist keines.
            self._adapter.inhalte_vergessen(sitzung.akte_id)
            ereignis(_log, "sitzung_geschlossen", sitzung=sitzung_id, dokumente=len(sitzung.geladen))

    def dialog_merken(self, identitaet: Identitaet, sitzung_id: str,
                      frage: str, antwort: Antwort) -> Sitzung:
        """Merkt nur eine belegte Endfassung; Rohtext aus dem Stream nie."""
        sitzung = self.laden(identitaet, sitzung_id)
        if not antwort.quellen or not antwort.text.strip():
            return sitzung
        sitzung.dialog.append(DialogEintrag(
            frage=frage.strip()[:4000], antwort=antwort.text[:8000],
            quellen=[quelle.kennung for quelle in antwort.quellen[:50]],
        ))
        sitzung.dialog = sitzung.dialog[-self._dialog_max_runden:]
        self._speicher.sitzung_ablegen(sitzung)
        ereignis(_log, "dialog_ergaenzt", sitzung=sitzung.id,
                 runden=len(sitzung.dialog), quellen=len(antwort.quellen))
        return sitzung

    # ── Aktenkontext aus jur|nodes ─────────────────────────────────────────

    def dokumente(self, sitzung: Sitzung) -> list[Dokument]:
        return self._adapter.dokumente(sitzung.akte_id)

    def beteiligte(self, sitzung: Sitzung) -> list[Beteiligter]:
        try:
            return self._adapter.beteiligte(sitzung.akte_id)
        except JurNodesFehler:
            return []

    def fristen(self, sitzung: Sitzung) -> list[Frist]:
        try:
            return self._adapter.fristen(sitzung.akte_id)
        except JurNodesFehler:
            return []

    # ── Dokumente laden ────────────────────────────────────────────────────

    def dokumente_laden(self, identitaet: Identitaet, sitzung_id: str, dokument_ids: list[str]) -> Sitzung:
        sitzung = self.laden(identitaet, sitzung_id)
        bereits = {g.dokument_id for g in sitzung.geladen}
        nicht_geladen: list[JurNodesFehler] = []
        # Getrennt gezaehlt, weil die Abhilfe eine andere ist: Ein Scan
        # braucht Texterkennung, ein nicht ladbares Dokument den Hersteller.
        ohne_text = 0
        nicht_lesbar = 0
        gedaechtnis_fehler = ""
        # Welche Dateiarten fielen heraus? Ohne diese Zahl bleibt die Bilanz
        # eine Feststellung ohne Folge: "14 in einem Format, das nicht gelesen
        # werden kann" sagt nicht, WELCHES - und ohne das laesst sich nichts
        # daran aendern. Am 25.09.2026 ging deshalb eine Frage dreimal hin und
        # her, die das Programm selbst haette beantworten koennen.
        arten: dict[str, int] = {}
        angefordert = len([d for d in dokument_ids if d not in bereits])
        for dokument_id in dokument_ids:
            if dokument_id in bereits:
                continue
            # Ein Dokument, das sich nicht laden laesst, darf die uebrigen
            # nicht kosten.
            #
            # Aus der Kanzlei am 25.09.2026: "es wird auch immer nur ein
            # Dokument in das Aktengedaechtnis uebernommen." Genau das war
            # der Grund: Das erste ging durch, beim zweiten warf der Adapter -
            # und die Schleife brach ab. Auf dem Schirm stand eine Meldung,
            # die nach einem einzelnen Fehler aussah, waehrend in Wahrheit
            # achtundzwanzig Dokumente fehlten.
            #
            # Dasselbe Muster wie an diesem Tag schon zweimal: Ein Teilfehler
            # riss das Ganze mit. Was nicht da ist, faellt nicht auf.
            try:
                dokument, daten = self._adapter.dokument_laden(sitzung.akte_id, dokument_id)
            except JurNodesFehler as e:
                nicht_geladen.append(e)
                sitzung.hinweise.append(f"Ein Dokument ließ sich nicht laden: {e}")
                ereignis(_log, "dokument_nicht_geladen", sitzung=sitzung.id,
                         dokument=dokument_id, grund=type(e).__name__)
                continue
            try:
                seiten, ocr = text_extrahieren(dokument, daten, self._ocr, sitzung.id)
            except (NichtUnterstuetzt, OcrFehler) as e:
                nicht_lesbar += 1
                art = PurePosixPath(dokument.dateiname).suffix.lower() or "ohne Endung"
                arten[art] = arten.get(art, 0) + 1
                sitzung.hinweise.append(f"„{dokument.titel}“ nicht geladen: {e}")
                ereignis(_log, "dokument_uebersprungen", sitzung=sitzung.id, dokument=dokument_id, grund=type(e).__name__)
                continue
            finally:
                del daten  # Originaldatei nicht länger halten als nötig
            zeichen = sum(len(s.text) for s in seiten)
            if zeichen == 0:
                ohne_text += 1
                art = PurePosixPath(dokument.dateiname).suffix.lower() or "ohne Endung"
                arten[art] = arten.get(art, 0) + 1
                sitzung.hinweise.append(f"„{dokument.titel}“ enthält keinen erkennbaren Text.")
                continue
            self._speicher.text_ablegen(sitzung.id, dokument_id, json.dumps([s.model_dump() for s in seiten], ensure_ascii=False))
            nummer = 0
            if self._gedaechtnis is not None:
                # Das Aktengedaechtnis ist eine Zugabe, keine Bedingung.
                #
                # Aus der Kanzlei am 25.09.2026: "er uebernimmt direkt nur ein
                # Dokument, und das wars. Warum ist es nicht moeglich, erst
                # einmal alle Dokumente in der Arbeitsflaeche zu oeffnen und
                # dann unter Aktengedaechtnis die Dateien einzulesen? So hat
                # man immer noch die Moeglichkeit zu arbeiten und nebenbei am
                # Gedaechtnis zu feilen."
                #
                # Genau so. Das Merken wurde hier nach JEDEM Dokument
                # abgelegt; wies jur|nodes das ab, riss es das Uebernehmen
                # mit - und in der Arbeitsakte lag ein einziges Dokument.
                # Jetzt wird im Stapel gemerkt und am Ende einmal gesichert,
                # und ein Fehlschlag kostet die Dokumente nicht.
                try:
                    self._gedaechtnis.dokument_merken(sitzung, dokument, seiten, ocr)
                    # Dieselbe Nummer wie im Gedaechtnis - sonst meinte D12
                    # hier und dort ein anderes Dokument.
                    nummer = self._gedaechtnis.nummer_von(sitzung.akte_id, dokument_id)
                except Exception as e:      # noqa: BLE001 - jeder Speicher
                    gedaechtnis_fehler = gedaechtnis_fehler or str(e)
            sitzung.geladen.append(GeladenesDokument(dokument_id=dokument_id, titel=dokument.titel,
                                                     seiten=len(seiten), zeichen=zeichen, ocr=ocr,
                                                     nummer=nummer))
            ereignis(_log, "dokument_geladen", sitzung=sitzung.id, dokument=dokument_id, seiten=len(seiten), zeichen=zeichen, ocr=ocr)
        # Schlaegt ALLES fehl, ist es kein Teilfehler mehr, sondern der Fall -
        # dann gehoert er nach vorn und nicht in eine Hinweiszeile. Wer ein
        # einziges Dokument anfordert und es nicht bekommt, soll das auch so
        # erfahren.
        if nicht_geladen and not sitzung.geladen:
            raise nicht_geladen[0]
        if gedaechtnis_fehler:
            sitzung.hinweise.append(
                "Die Dokumente sind in der Arbeitsakte. Das Aktengedächtnis "
                "konnte nicht gesichert werden – gearbeitet werden kann "
                f"trotzdem. {gedaechtnis_fehler}")
        # Die Bilanz nach VORN. Aus der Kanzlei am 25.09.2026: "er uebernimmt
        # beim Lesen der Dokumente nicht alle, nur 24 von 38."
        #
        # Das Programm sagte es auch vorher - in vierzehn einzelnen Saetzen,
        # von denen die Oberflaeche den ersten zeigte. Wer eine Meldung ueber
        # EIN Dokument liest, haelt es fuer einen Einzelfall und zaehlt nicht
        # nach. Was nicht da ist, faellt nicht auf.
        uebersprungen = ohne_text + nicht_lesbar + len(nicht_geladen)
        if uebersprungen:
            gruende = []
            if ohne_text:
                gruende.append(
                    f"{ohne_text} ohne erkennbaren Text (meist eingescannte "
                    "Seiten – dafür ist die Texterkennung nötig)")
            if nicht_lesbar:
                gruende.append(f"{nicht_lesbar} in einem Format, das nicht "
                               "gelesen werden kann")
            if nicht_geladen:
                gruende.append(f"{len(nicht_geladen)} von jur|nodes nicht "
                               "geliefert")
            if arten:
                # Die Dateiarten mit Anzahl - das ist die Auskunft, mit der
                # sich etwas anfangen laesst.
                geordnet = sorted(arten.items(), key=lambda x: -x[1])
                gruende.append("Dateiarten: " + ", ".join(
                    f"{art} {anzahl}" for art, anzahl in geordnet))
            sitzung.hinweise.insert(
                0, f"{angefordert - uebersprungen} von {angefordert} Dokumenten "
                   f"gelesen, {uebersprungen} nicht: " + ", ".join(gruende) +
                   ". Die Einzelheiten stehen darunter.")
        self._speicher.sitzung_ablegen(sitzung)
        return sitzung

    def dokumente_entfernen(self, identitaet: Identitaet, sitzung_id: str,
                            dokument_ids: list[str]) -> Sitzung:
        """Mehrere Dokumente in EINEM Zug aus der Arbeitsakte nehmen.

        **Warum das sein muss, und nicht fuenfzigmal das einzelne.** Aus der
        Kanzlei am 13.10.2026: "Gedaechtnis verwerfen scheint nicht
        abzuschliessen - komme ich auf das Feld, erscheint eine Sanduhr."

        Die Oberflaeche schickte einen Aufruf je Dokument. Jede Antwort ist
        eine vollstaendige Sitzungsantwort, und die liest die Dokumentliste
        **neu bei jur|nodes** - Ordnerbaum und Korrespondenzverzeichnis, je
        Aufruf. Der Hersteller laesst eine Anfrage je IP-Adresse zugleich zu,
        also laufen sie hintereinander. Bei fuenfzig Dokumenten sind das
        fuenfzig Lesevorgaenge der ganzen Akte fuer einen einzigen Klick.

        > Eine Schleife in der Oberflaeche ist nicht dasselbe wie eine
        > Schleife im Programm: Jeder Durchgang kostet hier einen Weg zum
        > Server und zurueck.

        Hier wird einmal geladen, einmal abgelegt und einmal geantwortet.
        """
        sitzung = self.laden(identitaet, sitzung_id)
        weg = {x for x in dokument_ids}
        bleibt = [g for g in sitzung.geladen if g.dokument_id not in weg]
        entfernt = [g.dokument_id for g in sitzung.geladen if g.dokument_id in weg]
        if not entfernt:
            return sitzung
        sitzung.geladen = bleibt
        for dokument_id in entfernt:
            self._speicher.text_loeschen(sitzung.id, dokument_id)
            # Und die Kopie im Adapter (Befund N10) - je Dokument, aber ohne
            # einen Weg nach aussen: Der Puffer liegt in diesem Prozess.
            self._adapter.inhalte_vergessen(sitzung.akte_id, dokument_id)
        self._speicher.sitzung_ablegen(sitzung)
        ereignis(_log, "dokumente_entfernt", sitzung=sitzung.id, anzahl=len(entfernt))
        return sitzung

    def dokument_entfernen(self, identitaet: Identitaet, sitzung_id: str, dokument_id: str) -> Sitzung:
        """Nimmt ein Dokument aus der Arbeitsakte – der Text wird gelöscht."""
        sitzung = self.laden(identitaet, sitzung_id)
        vorher = len(sitzung.geladen)
        sitzung.geladen = [g for g in sitzung.geladen if g.dokument_id != dokument_id]
        if len(sitzung.geladen) != vorher:
            self._speicher.text_loeschen(sitzung.id, dokument_id)
            self._speicher.sitzung_ablegen(sitzung)
            # Und die Kopie im Adapter (Befund N10). Bei einer Mail liegt dort
            # ihr Klartext samt Anlagen; ein "der Text wird geloescht", das
            # eine zweite Kopie stehen laesst, waere nicht wahr.
            self._adapter.inhalte_vergessen(sitzung.akte_id, dokument_id)
            ereignis(_log, "dokument_entfernt", sitzung=sitzung.id, dokument=dokument_id)
        return sitzung

    # ── Passagen für die KI ────────────────────────────────────────────────

    def passagen(self, sitzung: Sitzung, nur_dokument: str | None = None) -> list[Passage]:
        """Die Passagen der Arbeitsakte, mit denselben Kennungen wie im Gedächtnis.

        Die Nummer kommt aus dem geladenen Dokument, wenn dort eine steht –
        sonst aus der Reihenfolge. Ohne das zählte die Sitzung eigenständig
        durch und wiche vom Gedächtnis ab, sobald dort eine Nummer entfallen
        ist; die Fundstellen des Lebenssachverhalts zeigten dann hier auf das
        falsche Dokument.
        """
        ergebnis: list[Passage] = []
        for stelle, geladen in enumerate(sitzung.geladen, start=1):
            nr = geladen.nummer or stelle
            if nur_dokument and geladen.dokument_id != nur_dokument:
                continue
            roh = self._speicher.text_lesen(sitzung.id, geladen.dokument_id)
            if roh is None:
                raise SitzungNichtGefunden("Die Dokumenttexte sind abgelaufen. Bitte Dokumente erneut laden.")
            # Ein abgelegter Text, der sich nicht mehr lesen laesst.
            #
            # Der abgelaufene Text hatte seinen Satz, dieser nicht: Er kam als
            # "Interner Fehler" heraus, und zwar bei JEDEM Fenster, denn die
            # Passagen holt die Oberflaeche beim Oeffnen. Ein Dokument machte
            # damit die ganze Arbeitsflaeche unbenutzbar.
            #
            # Still ausgelassen wird es NICHT. Die Belegpflicht beruht darauf,
            # dass jede Aussage auf eine Passage zeigt; ein Dokument, das aus
            # dem Material verschwindet und in der Liste bleibt, waere genau
            # die Luecke, die dieses Programm verhindern soll. Also derselbe
            # Weg wie beim abgelaufenen Text: erneut laden.
            try:
                seiten = [Seite.model_validate(s) for s in json.loads(roh)]
            except Exception as fehler:  # noqa: BLE001 - genau das ist der Zweck
                ereignis(_log, "dokumenttext_unlesbar", sitzung=sitzung.id,
                         dokument=geladen.dokument_id)
                raise SitzungNichtGefunden(
                    f"Der abgelegte Text von „{geladen.titel}“ lässt sich nicht "
                    "mehr lesen. Bitte das Dokument im Explorer abwählen und "
                    "erneut laden. Die Akte in jur|nodes ist unberührt."
                ) from fehler
            dokument = Dokument(id=geladen.dokument_id, akte_id=sitzung.akte_id, titel=geladen.titel, dateiname="")
            ergebnis.extend(passagen_bilden(nr, dokument, seiten))
        return ergebnis
