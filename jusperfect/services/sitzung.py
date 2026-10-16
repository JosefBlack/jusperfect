"""Die Aktensitzung: Berechtigung prüfen, Dokumente holen, Text bereithalten, aufräumen.

Der Datenfluss aus dem Konzept in Code: Akte öffnen -> Berechtigung prüfen ->
benötigte Dokumente aus jur|nodes laden -> temporär Text extrahieren ->
(Analyse) -> temporäre Daten löschen. Alles hier arbeitet über den
Sitzungsspeicher, damit es in Lambda ebenso läuft wie lokal.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from jusperfect.domain.models import (
    MAX_FRAGE,
    Akte, Antwort, Beteiligter, DialogEintrag, Dokument, Frist, GeladenesDokument, Passage, Seite, Sitzung,
)
from jusperfect.jurnodes.base import JurNodesAdapter, JurNodesFehler
from jusperfect.ocr.base import OcrDienst, OcrFehler
from jusperfect.security.berechtigungen import Berechtigungen, ZugriffVerweigert
from jusperfect.security.identitaet import Identitaet
from jusperfect.security.protokoll import ereignis, protokoll
from jusperfect.services.extraktion import NichtUnterstuetzt, seiten_nennen, text_extrahieren
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
            frage=frage.strip()[:MAX_FRAGE], antwort=antwort.text[:8000],
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

    def dokumente_laden(self, identitaet: Identitaet, sitzung_id: str,
                        dokument_ids: list[str], neu_laden: bool = False) -> Sitzung:
        """Dokumente in die Arbeitsakte holen.

        ``neu_laden`` liest auch das wieder ein, was schon dasteht, und sagt,
        ob sich etwas geaendert hat.

        Befund R01 der Zweitpruefung vom 15.10.2026: Ohne diesen Weg kam ein
        unter derselben Kennung geaendertes Original nie wieder herein - weder
        beim Oeffnen (das Gedaechtnis liefert den gespeicherten Text) noch
        beim erneuten Auswaehlen (eine bekannte Kennung wurde uebersprungen).
        Und das erneute Auswaehlen SAH aus wie ein Aktualisieren.
        """
        sitzung = self.laden(identitaet, sitzung_id)
        bereits = {g.dokument_id for g in sitzung.geladen}
        # Was vorher dastand - zum Vergleich nach dem Neulesen.
        vorher_kennung = {g.dokument_id: g.inhalt_kennung for g in sitzung.geladen}
        if not neu_laden:
            # Erneut ausgewaehlt und nicht neu gelesen: Das gehoert gesagt,
            # sonst haelt der Bearbeiter es fuer eine Aktualisierung.
            schon_da = [d for d in dokument_ids if d in bereits]
            if schon_da:
                sitzung.hinweise.append(
                    f"{len(schon_da)} Dokument(e) lagen bereits in der Arbeitsakte und "
                    "wurden NICHT neu eingelesen. Hat sich das Original seitdem "
                    "geändert, steht hier weiterhin der alte Stand. Zum Neulesen "
                    "den Weg „Neu einlesen“ benutzen.")
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
        angefordert = len(dokument_ids) if neu_laden else len([d for d in dokument_ids if d not in bereits])
        geaendert: list[str] = []
        unveraendert = 0
        for dokument_id in dokument_ids:
            if dokument_id in bereits and not neu_laden:
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
            # Einzelne Seiten ohne Text - der haeufige Fall seit dem
            # 16.10.2026: Schriftsatz digital, Anlage dahinter gescannt. Das
            # Dokument hat Text und kommt herein; dass ein Teil davon fehlt,
            # muss trotzdem dastehen. Vorher sagte das niemand, weil nur
            # gezaehlt wurde, ob das GANZE Dokument leer ist.
            ohne_seiten = [x.nummer for x in seiten if x.hinweis]
            if ohne_seiten:
                grund = next(x.hinweis for x in seiten if x.hinweis)
                sitzung.hinweise.append(
                    f"„{dokument.titel}“: Auf {'Seite' if len(ohne_seiten) == 1 else 'den Seiten'} "
                    f"{seiten_nennen(ohne_seiten)} von {len(seiten)} steht kein Text. {grund}")
                ereignis(_log, "seiten_ohne_text", sitzung=sitzung.id, dokument=dokument_id,
                         anzahl=len(ohne_seiten), von=len(seiten))
            if zeichen == 0:
                ohne_text += 1
                art = PurePosixPath(dokument.dateiname).suffix.lower() or "ohne Endung"
                arten[art] = arten.get(art, 0) + 1
                sitzung.hinweise.append(f"„{dokument.titel}“ enthält keinen erkennbaren Text.")
                continue
            roh = json.dumps([s.model_dump() for s in seiten], ensure_ascii=False)
            self._speicher.text_ablegen(sitzung.id, dokument_id, roh)
            inhalt_kennung = hashlib.sha256(roh.encode("utf-8")).hexdigest()[:32]
            if dokument_id in bereits:
                alt = vorher_kennung.get(dokument_id, "")
                if not alt:
                    # Aus dem Gedaechtnis uebernommen oder aus der Zeit vor
                    # R01: Es gab nichts zu vergleichen.
                    sitzung.hinweise.append(
                        f"„{dokument.titel}“ wurde neu aus der Akte eingelesen. "
                        "Ob sich das Original seit dem letzten Mal geändert hat, "
                        "war nicht feststellbar.")
                elif alt != inhalt_kennung:
                    geaendert.append(dokument.titel)
                else:
                    unveraendert += 1
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
            eintrag = GeladenesDokument(dokument_id=dokument_id, titel=dokument.titel,
                                        seiten=len(seiten), zeichen=zeichen, ocr=ocr,
                                        nummer=nummer, inhalt_kennung=inhalt_kennung,
                                        seiten_ohne_text=ohne_seiten)
            sitzung.geladen = [g for g in sitzung.geladen if g.dokument_id != dokument_id]
            sitzung.geladen.append(eintrag)
            ereignis(_log, "dokument_geladen", sitzung=sitzung.id, dokument=dokument_id, seiten=len(seiten), zeichen=zeichen, ocr=ocr)
        # Schlaegt ALLES fehl, ist es kein Teilfehler mehr, sondern der Fall -
        # dann gehoert er nach vorn und nicht in eine Hinweiszeile. Wer ein
        # einziges Dokument anfordert und es nicht bekommt, soll das auch so
        # erfahren.
        if nicht_geladen and not sitzung.geladen:
            raise nicht_geladen[0]
        if geaendert:
            # Nach VORN, nicht in eine Zeile unter vierzehn anderen: Hierauf
            # koennen Antworten stehen, die jetzt ueberholt sind.
            sitzung.hinweise.insert(0, (
                f"ACHTUNG: {len(geaendert)} Dokument(e) haben sich seit dem letzten "
                "Einlesen geändert und stehen jetzt im neuen Stand: "
                + ", ".join(f"„{t}“" for t in geaendert)
                + ". Frühere Antworten und Auswertungen können auf dem alten Stand "
                "beruhen und sind zu prüfen."))
            ereignis(_log, "dokumente_geaendert", sitzung=sitzung.id, anzahl=len(geaendert))
        if neu_laden and unveraendert:
            sitzung.hinweise.append(
                f"{unveraendert} Dokument(e) waren unverändert.")
        if gedaechtnis_fehler:
            sitzung.hinweise.append(
                "Die Dokumente sind in der Arbeitsakte. Das Gedächtnis "
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
                gruende.append(f"{len(nicht_geladen)} von jurnodes nicht "
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

    # ── Ein Dokument von Hand einfügen ──────────────────────────

    #: Größer nimmt das Programm nicht an. Eine eingescannte Anlage hat ein
    #: paar hundert Kilobyte; was darüber liegt, gehört über die E-Akte herein.
    MAX_EINGEFUEGT_BYTES = 20 * 1024 * 1024
    #: Und so viel Text höchstens, wenn er eingefügt statt hochgeladen wird.
    MAX_EINGEFUEGT_ZEICHEN = 500_000

    def dokument_einfuegen(self, identitaet: Identitaet, sitzung_id: str, titel: str,
                           dateiname: str = "", daten: bytes | None = None,
                           text: str = "") -> tuple[Sitzung, GeladenesDokument]:
        """Ein Dokument unmittelbar in die Arbeitsakte legen – ohne jur|nodes.

        Aus der Kanzlei am 16.10.2026: „Ich hätte auch gerne das Dokument
        direkt in den Chat eingefügt, hierfür fehlt aber eine Funktion."

        Es ist der Weg für das Blatt, das gerade nicht in der E-Akte liegt:
        das soeben eingegangene Fax, der Ausdruck, der Abschnitt, den die
        Texterkennung nicht hergab. Gelesen wird es wie jedes andere Dokument
        – Seiten, Passagen, Kennungen –, damit die Belegpflicht auch dafür
        trägt.

        **Drei Dinge, die es ausdrücklich nicht tut.** Es schreibt nichts nach
        jur|nodes; die führende Akte bleibt unberührt. Es geht nicht ins
        dauerhafte Aktengedächtnis; was dort liegt, stammt aus der E-Akte, und
        das soll man sich darauf verlassen können. Und es überdauert die
        Sitzung nicht – der Text liegt im Sitzungsspeicher und geht mit ihr.

        Die Dokumentnummer wird über alle bisherigen gesetzt. Sonst truege das
        eingefügte Blatt die Nummer eines Dokuments aus dem Gedächtnis, und
        „D7-S1-P2" meinte zwei verschiedene Stellen.
        """
        sitzung = self.laden(identitaet, sitzung_id)
        titel = (titel or "").strip() or (PurePosixPath(dateiname).name if dateiname else "Eingefügtes Dokument")
        dokument_id = f"eingefuegt-{uuid.uuid4().hex[:12]}"

        if daten is not None:
            if len(daten) > self.MAX_EINGEFUEGT_BYTES:
                raise NichtUnterstuetzt(
                    f"Die Datei ist größer als {self.MAX_EINGEFUEGT_BYTES // (1024 * 1024)} MB. "
                    "Größere Dokumente kommen über die E-Akte herein.")
            dokument = Dokument(id=dokument_id, akte_id=sitzung.akte_id, titel=titel,
                                dateiname=dateiname or titel)
            try:
                seiten, ocr = text_extrahieren(dokument, daten, self._ocr, sitzung.id)
            except OcrFehler as fehler:
                # Ein durchgehender Scan ohne eingerichtete Texterkennung. Das
                # ist eine Auskunft an den Bearbeiter und kein Serverfehler -
                # und der naechste Schritt steht gleich dabei: Der Text laesst
                # sich auch von Hand einfuegen.
                raise NichtUnterstuetzt(
                    f"{fehler} Der Text dieses Blattes lässt sich stattdessen "
                    "von Hand einfügen.") from fehler
        else:
            if len(text) > self.MAX_EINGEFUEGT_ZEICHEN:
                raise NichtUnterstuetzt(
                    f"Der Text ist länger als {self.MAX_EINGEFUEGT_ZEICHEN:,} Zeichen."
                    .replace(",", "."))
            seiten, ocr = [Seite(nummer=1, text=text)], False

        zeichen = sum(len(x.text) for x in seiten)
        if zeichen == 0:
            raise NichtUnterstuetzt(
                "In diesem Dokument wurde kein Text gefunden. Ist es ein Scan, "
                "braucht es die Texterkennung; sonst lässt sich der Text auch "
                "von Hand einfügen.")

        roh = json.dumps([x.model_dump() for x in seiten], ensure_ascii=False)
        self._speicher.text_ablegen(sitzung.id, dokument_id, roh)
        # Über alle bisherigen Nummern hinweg - die aus dem Gedächtnis
        # eingeschlossen, und mindestens so hoch wie die Zahl der Dokumente.
        nummer = max([g.nummer for g in sitzung.geladen] + [len(sitzung.geladen)], default=0) + 1
        eintrag = GeladenesDokument(
            dokument_id=dokument_id, titel=titel, seiten=len(seiten), zeichen=zeichen,
            ocr=ocr, nummer=nummer,
            inhalt_kennung=hashlib.sha256(roh.encode("utf-8")).hexdigest()[:32],
            seiten_ohne_text=[x.nummer for x in seiten if x.hinweis],
            eingefuegt=True)
        sitzung.geladen.append(eintrag)
        sitzung.hinweise = [
            f"„{titel}“ wurde eingefügt und liegt nur in dieser Sitzung. Es steht "
            "nicht in der jurnodes-Akte und nicht im Aktengedächtnis."]
        # Auch beim eingefuegten Dokument gilt: Eine Seite ohne Text wird
        # genannt. Gerade hier - wer ein Blatt von Hand einfuegt, tut es
        # meistens, weil beim Einlesen etwas gefehlt hat.
        if eintrag.seiten_ohne_text:
            sitzung.hinweise.append(
                f"Auf {'Seite' if len(eintrag.seiten_ohne_text) == 1 else 'den Seiten'} "
                f"{seiten_nennen(eintrag.seiten_ohne_text)} von {len(seiten)} steht kein Text. "
                + next(x.hinweis for x in seiten if x.hinweis))
        self._speicher.sitzung_ablegen(sitzung)
        # Kein Titel und kein Dateiname ins Protokoll: Beides kann den Namen
        # der Mandantschaft tragen.
        ereignis(_log, "dokument_eingefuegt", sitzung=sitzung.id, dokument=dokument_id,
                 seiten=len(seiten), zeichen=zeichen, ocr=ocr)
        return sitzung, eintrag

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
                    "erneut laden. Die Akte in jurnodes ist unberührt."
                ) from fehler
            dokument = Dokument(id=geladen.dokument_id, akte_id=sitzung.akte_id, titel=geladen.titel, dateiname="")
            ergebnis.extend(passagen_bilden(nr, dokument, seiten))
        return ergebnis
