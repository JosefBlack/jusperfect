"""Dauerhaftes Gedächtnis laden, ergänzen und belegt fortschreiben.

Das Gedächtnis ersetzt jur|nodes nicht. Es hält genau die Arbeitskopie, die
eine spätere Wiederaufnahme verbilligt: extrahierte Texte, einen belegten
Lebenssachverhalt und bereits geprüfte Frage-Antwort-Paare. Jeder Modellaufruf
geht weiterhin durch den einzigen ``Ausgang``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from jusperfect.config import Einstellungen
from jusperfect.domain.models import (
    MAX_FRAGE,
    Aktenanalyse, Aktengedaechtnis, Antwort, ChronologieEintrag, Chronologieergebnis, DialogEintrag, Dokument,
    GedaechtnisAntwort, GedaechtnisDokument, GeladenesDokument, Kosten, Passage, Seite, Sitzung,
)
from jusperfect.gedaechtnis.base import GedaechtnisFehler, GedaechtnisSpeicher
from jusperfect.security.identitaet import Identitaet
from jusperfect.fehlergrenze import ausnahmekette
from jusperfect.security.protokoll import MAX_WERT_LAENGE, ereignis, protokoll
from jusperfect.services import prompts
from jusperfect.services.ausgang import Ausgang, Ausgangskontext
from jusperfect.services.belegpflicht import VERZICHT, aussage_fail_closed
from jusperfect.services.passagen import budget_anwenden, passagen_bilden
from jusperfect.services.quellen import index_bauen
from jusperfect.services.chronologie import gleicher_vorgang
from jusperfect.speicher.base import SitzungsSpeicher, SpeicherFehler

_log = protokoll("gedaechtnis")

# Die Wortmengen-Aehnlichkeit liegt jetzt bei den Chronologie-Regeln: Was dort
# als dieselbe Zeile gilt, muss hier dieselbe Zeile sein. Zwei Fassungen
# desselben Vergleichs waeren mit der Zeit zwei verschiedene Vergleiche.
_gleicher_vorgang = gleicher_vorgang

# Was ein Aufruf an Platz braucht, der nicht aus Passagen besteht:
# Systemanweisung, Aktenkopf, eine Ueberschrift je Passage, Auftragstext.
# Grosszuegig geschaetzt - die Zeichengrenze ist selbst nur ein grobes Mass
# fuer die Tokenzahl, und eine Portion mehr ist billiger als ein Aufruf, der
# beim Anbieter auflaeuft.
_RAHMEN_ZEICHEN = 6_000

# Unterhalb dieser Portionsgroesse lohnt kein Aufruf mehr: Der bisherige
# Lebenssachverhalt fuellt den Platz dann fast allein, und jede weitere
# Portion truege mehr Vorgeschichte als neuen Text. Das ist die Decke des
# Verfahrens. Sie wird ausgesprochen und nicht dadurch umgangen, dass der
# Lebenssachverhalt gekuerzt wird - das Kuerzen waere genau der stille
# Verlust, den dieses Gedaechtnis verhindern soll.
_MINDESTPORTION_ZEICHEN = 20_000

# Notbremse gegen einen Lauf, der aus einem Fehler heraus nicht endet. Die
# eigentliche Kostenbremse ist das Monatsbudget im Ausgang; diese Zahl faengt
# nur den Programmfehler ab. 40 Portionen sind rund 6 Mio. Zeichen Akte.
_MAX_PORTIONEN = 40


@dataclass
class Einleseergebnis:
    """Was ein Lesedurchgang bewirkt hat - fuer die Oberflaeche und den Nachweis.

    Die Zahlen stehen hier, damit der Bearbeiter sieht, was gelesen wurde und
    was noch offen ist. Ein Durchgang, der auf halber Strecke endet, darf nicht
    aussehen wie einer ueber die ganze Akte - derselbe Grundsatz, nach dem eine
    zu grosse Akte lieber abgelehnt als gekuerzt wird.
    """

    gedaechtnis: Aktengedaechtnis
    portionen: int = 0
    passagen: int = 0
    offene_passagen: int = 0
    kosten: Kosten = field(default_factory=Kosten)
    hinweise: list[str] = field(default_factory=list)

    @property
    def fertig(self) -> bool:
        return self.offene_passagen == 0

    def als_dict(self) -> dict:
        return {"portionen": self.portionen, "passagen": self.passagen,
                "offene_passagen": self.offene_passagen, "fertig": self.fertig,
                "kosten": self.kosten.model_dump(), "hinweise": self.hinweise}


class Gedaechtnisdienst:
    def __init__(self, speicher: GedaechtnisSpeicher | None, sitzungsspeicher: SitzungsSpeicher,
                 ausgang: Ausgang, einstellungen: Einstellungen) -> None:
        self._speicher = speicher
        self._sitzungsspeicher = sitzungsspeicher
        self._ausgang = ausgang
        self._e = einstellungen

    #: Was beim letzten Lesen nicht gesichert werden konnte. Leer = alles gut.
    _letzter_sicherungsfehler: str = ""

    @property
    def aktiv(self) -> bool:
        return self._speicher is not None

    def lesen(self, akte_id: str) -> Aktengedaechtnis | None:
        return self._gelesen(akte_id)

    def _nachtragen(self, g: Aktengedaechtnis, warum: str) -> str:
        """Etwas am Gedaechtnis festhalten, das beim Lesen aufgefallen ist.

        **Ein misslungenes Sichern darf das Oeffnen einer Akte nicht
        verhindern.** Am 25.09.2026 tat es genau das: jur|nodes ersetzt eine
        vorhandene Datei nicht, das Ablegen beim Oeffnen schlug fehl - und der
        Fehler riss das ganze Oeffnen mit. Die Arbeitsflaeche ging nicht auf,
        und auf dem Schirm stand eine Meldung ueber das ABLEGEN, waehrend der
        Bearbeiter eine Akte OEFFNEN wollte.

        Das Gedaechtnis ist eine Arbeitshilfe, keine Bedingung. Geht es nicht,
        wird die Akte eben neu eingelesen - das kostet Geld und keine Arbeit.

        Verschluckt wird der Fehler trotzdem nicht: Er kommt als Hinweis
        zurueck und steht in der Oberflaeche. Was nicht da ist, faellt nicht
        auf.
        """
        try:
            self._speicher.ablegen(g)
        except Exception as fehler:
            ereignis(_log, "gedaechtnis_nicht_gesichert", akte=g.akte_id, warum=warum)
            return str(fehler)
        return ""

    def _gelesen(self, akte_id: str) -> Aktengedaechtnis | None:
        """Liest das Gedaechtnis und schreibt dabei einmalig die Nummern fest.

        Beim Lesen zu schreiben ist unueblich und hier trotzdem richtig: Die
        Nummern eines Gedaechtnisses aus Fassung 3 lassen sich nur aus der
        Stellung in der Liste ableiten, und diese Stellung verschiebt sich,
        sobald ein Dokument entfaellt. Was nicht vor der ersten Aenderung
        festgeschrieben ist, ist danach nicht mehr zu rekonstruieren.
        """
        if self._speicher is None:
            return None
        try:
            g = self._speicher.lesen(akte_id)
        except (GedaechtnisFehler, SpeicherFehler):
            # Ein gemeldeter Fehler des Speichers hat seinen eigenen Satz und
            # seinen eigenen Status. Hier geht es um den anderen Fall.
            raise
        except Exception as fehler:  # noqa: BLE001 - genau das ist der Zweck
            # Ein Gedaechtnis, das sich nicht mehr einlesen laesst.
            #
            # Aus der Kanzlei am 13.10.2026: "Akte oeffnen nicht moeglich
            # Vorgang wurde abgebrochen interner Fehler 2e2e3bd1." Was hier
            # unerwartet scheitert, kam vorher als Programmfehler heraus: eine
            # Nummer ohne Satz, und die Akte blieb zu.
            #
            # Jetzt ist es ein Fehler MIT Satz - und mit dem Weg hinaus. Der
            # Weg ist nicht theoretisch: "Gedaechtnis verwerfen" liest das
            # Gedaechtnis nicht, es loescht es; danach baut "Akte einlesen" es
            # neu auf.
            #
            # Und es ist ein Fehler, nicht ein stilles Weiter: Ein Schreiben
            # auf ein Gedaechtnis, das wir nicht lesen konnten, wuerde den
            # einzigen Stand ueberschreiben, an dem sich noch feststellen
            # laesst, was ihm fehlte. Alle schreibenden Wege gehen durch diese
            # Stelle und brechen deshalb hier ab, bevor sie etwas ablegen.
            raise GedaechtnisFehler(
                "Das Gedächtnis dieser Akte lässt sich nicht mehr "
                "einlesen. Die Akte selbst ist unberührt; in jurnodes ist "
                "nichts geschehen. Der Weg hinaus: im Gedächtnisfenster "
                "„Gedächtnis verwerfen“, danach „Akte einlesen“ – das "
                "Gedächtnis entsteht dann neu. Bitte diese Angabe weitergeben: "
                f"{ausnahmekette(fehler)[:MAX_WERT_LAENGE]}"
            ) from fehler
        if g is not None and self._nummern_sichern(g):
            self._letzter_sicherungsfehler = self._nachtragen(g, "nummern")
            if not self._letzter_sicherungsfehler:
                ereignis(_log, "gedaechtnis_nummern_festgeschrieben", akte=akte_id,
                         dokumente=len(g.dokumente))
        return g

    def auflisten(self) -> list[Aktengedaechtnis]:
        return self._speicher.auflisten() if self._speicher else []

    def bei_eroeffnen(self, sitzung: Sitzung) -> Sitzung:
        """Rehydriert bekannte Texte in die neue, weiterhin flüchtige Sitzung.

        **Ein Gedächtnis, das sich nicht einlesen lässt, darf das Öffnen einer
        Akte nicht verhindern.** Dasselbe gilt seit dem 25.09.2026 für das
        misslungene *Sichern* (siehe `_nachtragen`); für das *Lesen* war es
        nicht gezogen, und am 13.10.2026 blieb eine Akte deshalb zu.

        Das Gedächtnis ist eine Arbeitshilfe, keine Bedingung: Die Dokumente
        stehen in jur|nodes, und die Akte lässt sich auch ohne jede Erinnerung
        bearbeiten. Verschluckt wird der Fehler nicht - er steht als Hinweis
        in der Oberfläche, mit dem Weg hinaus.

        Geschrieben wird dann nichts: Jeder schreibende Weg liest zuerst, und
        `_gelesen` bricht dort ab, bevor etwas abgelegt wird. Ein Gedächtnis,
        das wir nicht lesen konnten, überschreiben wir nicht.
        """
        try:
            g = self.lesen(sitzung.akte_id)
        except GedaechtnisFehler as fehler:
            sitzung.hinweise.append(str(fehler))
            ereignis(_log, "gedaechtnis_nicht_gelesen", akte=sitzung.akte_id)
            return sitzung
        if g is None:
            return sitzung
        if g.akte_id != sitzung.akte_id:
            raise GedaechtnisFehler("Das Gedächtnis gehört zu einer anderen Akte.")
        # jurnodes ist für den Lebenszyklus führend. Wir übernehmen den Status
        # bei jedem Öffnen, löschen aber niemals aufgrund eines unbekannten,
        # fehlenden oder länger unveränderten Status.
        # Seit dem 25.09.2026 legt jede Sicherung eine eigene Fassung an -
        # jur|nodes ersetzt keine Datei. Das ist gewollt; ein Stapel ist es
        # nicht. Wird es zu viel, soll es auffallen, solange Aufraeumen eine
        # Kleinigkeit ist.
        fassungen = getattr(self._speicher, "letzte_fassungen", 0)
        grenze = getattr(self._speicher, "FASSUNGEN_HINWEIS", 0)
        if grenze and fassungen > grenze:
            sitzung.hinweise.append(
                f"In dieser Akte liegen {fassungen} Fassungen des "
                "Gedächtnisses. Gelesen wird die jüngste; die älteren "
                "lassen sich in jurnodes entfernen.")
        if self._status_synchronisieren(g, sitzung):
            fehler = self._nachtragen(g, "status")
            if fehler:
                sitzung.hinweise.append(
                    "Der Stand des Gedächtnisses konnte nicht gesichert "
                    "werden. Die Arbeit geht weiter; die Akte wird beim "
                    "nächsten Öffnen neu eingelesen. " + fehler)
        vorhanden = {d.dokument_id for d in sitzung.geladen}
        for dokument in g.dokumente:
            if dokument.dokument_id in vorhanden:
                continue
            self._sitzungsspeicher.text_ablegen(
                sitzung.id, dokument.dokument_id,
                json.dumps([seite.model_dump() for seite in dokument.seiten], ensure_ascii=False),
            )
            sitzung.geladen.append(GeladenesDokument(
                dokument_id=dokument.dokument_id, titel=dokument.titel,
                seiten=len(dokument.seiten), zeichen=dokument.zeichen, ocr=dokument.ocr,
                nummer=dokument.nummer,
            ))
        # Das dauerhafte Gedächtnis darf eine neue flüchtige Sitzung mit den
        # letzten geprüften Runden fortsetzen. Ohne aktiviertes Gedächtnis
        # bleibt der Dialog ausschließlich auf die laufende Sitzung begrenzt.
        sitzung.dialog = [
            DialogEintrag(
                frage=runde.frage[:MAX_FRAGE], antwort=runde.antwort[:8000],
                quellen=[quelle.kennung for quelle in runde.quellen[:50]],
                zeitpunkt=runde.zeitpunkt,
            )
            for runde in g.fragen_antworten[-self._e.dialog_max_runden:]
        ]
        if g.dokumente:
            sitzung.hinweise.append(
                f"Gedächtnis geladen: {len(g.dokumente)} Dokument(e), "
                f"{len(g.fragen_antworten)} frühere Frage(n)."
            )
        self._sitzungsspeicher.sitzung_ablegen(sitzung)
        ereignis(_log, "gedaechtnis_geladen", akte=sitzung.akte_id,
                 dokumente=len(g.dokumente), fragen=len(g.fragen_antworten))
        return sitzung

    def sichern(self, sitzung: Sitzung) -> Aktengedaechtnis | None:
        """Schreibt das Gedächtnis der Akte beim Schließen ein letztes Mal fort.

        Aus der Kanzlei: "beim schließen sollte das bearbeitete gespeichert
        werden und anhand einer meldung kenntlich gemacht werden."

        Streng genommen ist zu diesem Zeitpunkt bereits alles abgelegt: Jede
        Ergänzung des Lebenssachverhalts, jede Chronologiezeile und jede
        geprüfte Antwort geht sofort in den Speicher, nicht erst am Ende. Das
        ist Absicht - ein Programm, das erst beim Schließen speichert, verliert
        die Arbeit eines halben Vormittags, wenn der Rechner abstürzt.

        Dieser Aufruf ist trotzdem kein Selbstzweck. Er tut zweierlei: Er legt
        das Gedächtnis noch einmal ab, sodass ein Schreibfehler beim Schließen
        auffällt und nicht erst beim nächsten Öffnen. Und er gibt zurück, was
        wirklich im Speicher liegt - nicht, was die Oberfläche zu wissen glaubt.
        Nur so kann die Meldung sagen, was tatsächlich gesichert ist.

        Der Zeitpunkt der letzten inhaltlichen Änderung bleibt unangetastet:
        "aktualisiert am" soll sagen, wann zuletzt etwas hinzugekommen ist, und
        nicht, wann zuletzt jemand das Fenster geschlossen hat.
        """
        if self._speicher is None:
            return None
        g = self._gelesen(sitzung.akte_id)
        if g is None:
            return None
        self._status_synchronisieren(g, sitzung)
        self._speicher.ablegen(g)
        ereignis(_log, "gedaechtnis_gesichert", akte=sitzung.akte_id,
                 dokumente=len(g.dokumente), chronologie=len(g.chronologie),
                 fragen=len(g.fragen_antworten))
        return g

    def dokument_merken(self, sitzung: Sitzung, dokument: Dokument,
                         seiten: list[Seite], ocr: bool) -> None:
        """Einen Auszug ins Gedächtnis nehmen.

        Aus der Kanzlei am 25.09.2026: "er übernimmt direkt nur ein Dokument,
        und das wars." Genau das war der Grund - hier wurde nach jedem
        Dokument abgelegt, und sobald das abgewiesen wurde, riss es das
        Übernehmen mit. Bei achtunddreißig Dokumenten waren es
        achtunddreißig Schreibvorgänge, wo einer genügt.

        Und dieselbe Kanzlei hat die richtige Reihenfolge benannt: "erst die
        Dokumente in die Arbeitsfläche, dann unter Aktengedächtnis die Dateien
        einlesen - so hat man immer noch die Möglichkeit zu arbeiten und
        nebenbei am Gedächtnis zu feilen." Das Gedächtnis ist eine Zugabe,
        keine Bedingung; der Aufrufer fängt einen Fehlschlag ab und arbeitet
        weiter.

        (Nach jedem Dokument zu sichern ist zugleich der Preis dafür, dass
        jedes Dokument im Gedächtnis steht, sobald es gelesen ist. Wer das
        zusammenfassen will, muss den Stand zwischen den Dokumenten im
        Dienst halten - sonst liest der nächste Aufruf die alte Fassung vom
        Speicher, und das gerade Gemerkte ist weg. Ein Versuch am 25.09.2026
        lief genau in diesen Graben.)
        """
        if self._speicher is None:
            return
        g = self._gelesen(sitzung.akte_id) or self._neu(sitzung)
        neu = GedaechtnisDokument(dokument_id=dokument.id, titel=dokument.titel,
                                  seiten=seiten, ocr=ocr, datum=dokument.datum)
        for nr, vorhanden in enumerate(g.dokumente):
            if vorhanden.dokument_id == dokument.id:
                # Eine geänderte Fassung muss erneut in den Lebenssachverhalt
                # eingehen; deshalb die Zusammenfassungsmarke zurücknehmen.
                # Die Nummer bleibt: Es ist dasselbe Dokument in neuer Fassung,
                # und alles, was es zitiert, soll weiter auf es zeigen.
                neu.nummer = vorhanden.nummer
                g.dokumente[nr] = neu
                neue_kennungen = {p.kennung for p in self._passagen(g, nur_dokumente={dokument.id})}
                g.verarbeitete_passagen = [x for x in g.verarbeitete_passagen if x not in neue_kennungen]
                break
        else:
            # Ein neuer Auszug bekommt die nächste freie Nummer. Nachrücken
            # gibt es nicht - auch nicht in eine Lücke, die ein entferntes
            # Dokument hinterlassen hat.
            g.letzte_dokumentnummer += 1
            neu.nummer = g.letzte_dokumentnummer
            g.dokumente.append(neu)
        # Ein bewusstes Wiedereinlesen nimmt die Grabmarke zurueck. Es ist
        # eine eigene Handlung des Bearbeiters - genau so soll es sein.
        g.vergessene_dokumente = [x for x in g.vergessene_dokumente if x != dokument.id]
        g.aktualisiert_am = datetime.now(timezone.utc)
        self._speicher.ablegen(g)
        ereignis(_log, "gedaechtnis_dokument", akte=sitzung.akte_id,
                 dokument=dokument.id, seiten=len(seiten), zeichen=neu.zeichen)

    def nummer_von(self, akte_id: str, dokument_id: str) -> int:
        """Die feste Nummer eines Auszugs – 0, wenn es ihn hier nicht gibt."""
        g = self._gelesen(akte_id)
        if g is None:
            return 0
        return next((d.nummer for d in g.dokumente if d.dokument_id == dokument_id), 0)

    def antwort_merken(self, sitzung: Sitzung, frage: str, antwort: Antwort) -> None:
        """Persistiert ausschließlich die bereits fail-closed geprüfte Antwort."""
        if self._speicher is None or not antwort.quellen or not antwort.text.strip():
            return
        g = self._gelesen(sitzung.akte_id) or self._neu(sitzung)
        # Ein verspaetetes Ergebnis kommt nicht zurueck.
        #
        # Befund F02.3 der Zweitpruefung vom 05.10.2026: Eine Frage, die noch
        # unterwegs war, als das Dokument entfernt wurde, legte ihre Antwort
        # hinterher neu im Gedaechtnis ab - mitsamt dem Inhalt, der gerade
        # geloescht worden war. Die Oberflaeche meldete Erfolg, und durch die
        # Hintertuer kam derselbe Text zurueck.
        #
        # Unterschieden wird an der Grabmarke und nicht daran, ob das Dokument
        # im Gedaechtnis liegt: Ein noch nicht eingelesenes Dokument ist etwas
        # anderes als ein entferntes, und eine Antwort darauf gehoert gemerkt.
        if any(q.dokument_id in g.vergessene_dokumente for q in antwort.quellen):
            ereignis(_log, "gedaechtnis_antwort_verworfen", akte=sitzung.akte_id,
                     grund="dokument_entfernt")
            return
        g.fragen_antworten.append(GedaechtnisAntwort(
            frage=frage.strip(), antwort=antwort.text, quellen=antwort.quellen, modell=antwort.modell,
        ))
        # Ein Gedächtnis ist Arbeitskontext, kein unbegrenztes Chatarchiv.
        g.fragen_antworten = g.fragen_antworten[-self._e.gedaechtnis_max_fragen:]
        g.aktualisiert_am = datetime.now(timezone.utc)
        self._speicher.ablegen(g)
        ereignis(_log, "gedaechtnis_antwort", akte=sitzung.akte_id, quellen=len(antwort.quellen))

    def lebenssachverhalt_aktualisieren(self, identitaet: Identitaet,
                                        sitzung: Sitzung) -> Einleseergebnis:
        """Liest genau eine Portion nach und schreibt den Lebenssachverhalt fort."""
        if self._speicher is None:
            raise GedaechtnisFehler("Das Gedächtnis ist nicht aktiviert.")
        g = self._gelesen(sitzung.akte_id) or self._neu(sitzung)
        ergebnis = Einleseergebnis(gedaechtnis=g, offene_passagen=len(self._offene_passagen(g)))
        if ergebnis.offene_passagen:
            self._eine_portion(identitaet, sitzung, ergebnis)
        return ergebnis

    def akte_einlesen(self, identitaet: Identitaet, sitzung: Sitzung) -> Einleseergebnis:
        """Liest die ganze Akte, Portion für Portion, in einem Zug.

        Das ist der Weg für die grosse Akte. Sie passt nicht in einen Aufruf,
        also wird sie in Portionen gelesen; jede Portion bekommt den bisherigen
        Lebenssachverhalt als Faden mit und haengt an ihn an. Angehaengt wird
        immer, umgeschrieben nie - was einmal belegt vermerkt ist, bleibt
        stehen. Das ist die Zusage, auf der dieses Gedaechtnis beruht.

        Jede Portion wird einzeln gespeichert. Bricht der Lauf in der Mitte ab -
        Budget erschoepft, Anbieter nicht erreichbar -, ist das Gelesene nicht
        verloren; ein zweiter Aufruf setzt genau dort fort.
        """
        if self._speicher is None:
            raise GedaechtnisFehler("Das Gedächtnis ist nicht aktiviert.")
        g = self._gelesen(sitzung.akte_id) or self._neu(sitzung)
        ergebnis = Einleseergebnis(gedaechtnis=g, offene_passagen=len(self._offene_passagen(g)))
        while ergebnis.offene_passagen and ergebnis.portionen < _MAX_PORTIONEN:
            self._eine_portion(identitaet, sitzung, ergebnis)
        if ergebnis.offene_passagen and ergebnis.portionen >= _MAX_PORTIONEN:
            # Hierher fuehrt kein normaler Weg; die Meldung ist fuer den Fall,
            # dass doch einmal einer entsteht.
            ergebnis.hinweise.append(
                f"Nach {_MAX_PORTIONEN} Portionen abgebrochen; {ergebnis.offene_passagen} "
                "Passagen sind ungelesen. Bitte melden – das sollte nicht vorkommen."
            )
        ereignis(_log, "gedaechtnis_akte_eingelesen", akte=sitzung.akte_id,
                 portionen=ergebnis.portionen, anzahl_passagen=ergebnis.passagen,
                 offen=ergebnis.offene_passagen)
        return ergebnis

    def _offene_passagen(self, g: Aktengedaechtnis) -> list[Passage]:
        erledigt = set(g.verarbeitete_passagen)
        return [p for p in self._passagen(g) if p.kennung not in erledigt]

    def _eine_portion(self, identitaet: Identitaet, sitzung: Sitzung,
                      ergebnis: Einleseergebnis) -> None:
        """Eine Portion lesen, anhaengen, speichern - und die Marke setzen.

        Die Portion wird um den bisherigen Lebenssachverhalt kleiner. Er geht
        bei jedem Aufruf mit, damit die neue Portion an den Faden anknuepfen
        kann statt neu anzufangen; also belegt er auch Platz. Ohne diesen Abzug
        wuechse jeder Aufruf mit dem Gedaechtnis ueber die Grenze hinaus - bei
        acht Dokumenten faellt das nicht auf, bei fuenfzig laeuft der Aufruf auf.
        """
        g = ergebnis.gedaechtnis
        offen = self._offene_passagen(g)
        platz = self._e.max_passagen_zeichen - len(g.lebenssachverhalt) - _RAHMEN_ZEICHEN
        if platz < _MINDESTPORTION_ZEICHEN:
            raise GedaechtnisFehler(_decke_erreicht(g, self._e.max_passagen_zeichen, len(offen)))
        auswahl, _ = budget_anwenden(offen, platz)
        if not auswahl:
            # Eine einzelne Passage ist groesser als der verbliebene Platz.
            raise GedaechtnisFehler(_decke_erreicht(g, self._e.max_passagen_zeichen, len(offen)))
        material = prompts.material_bauen(sitzung.akte, [], [], auswahl)
        aufgabe = prompts.aufgabe_gedaechtnis(g.lebenssachverhalt)
        kontext = Ausgangskontext(identitaet, sitzung.id, sitzung.akte_id, "gedaechtnis",
                                  passagen=len(auswahl))
        durchgang = self._ausgang.fragen(kontext, prompts.SYSTEM, material, aufgabe)
        belegt = self._belegte_fortschreibung(durchgang.antwort.text, auswahl)
        if belegt.quellen and belegt.text != VERZICHT:
            g.lebenssachverhalt = "\n".join(x for x in (g.lebenssachverhalt.strip(), belegt.text.strip()) if x)
            bekannte = {q.kennung for q in g.lebenssachverhalt_quellen}
            g.lebenssachverhalt_quellen.extend(q for q in belegt.quellen if q.kennung not in bekannte)
        else:
            # Gelesen und bezahlt ist die Portion trotzdem. Bliebe sie offen,
            # liefe sie bei jedem Knopfdruck erneut und kostete jedes Mal - und
            # ein Durchlauf ueber die ganze Akte kaeme nie an sein Ende. Dass
            # nichts hervorging, muss der Bearbeiter dafuer erfahren: Es ist
            # genau die Stelle, an der etwas verlorengehen koennte.
            ergebnis.hinweise.append(
                f"Aus {_dokumentspanne(auswahl)} ging keine belegte Aussage hervor; "
                "der Lebenssachverhalt ist dort unverändert. Der Volltext liegt "
                "weiterhin im Gedächtnis und lässt sich befragen."
            )
        erledigt = set(g.verarbeitete_passagen)
        g.verarbeitete_passagen.extend(p.kennung for p in auswahl if p.kennung not in erledigt)
        g.aktualisiert_am = datetime.now(timezone.utc)
        self._speicher.ablegen(g)
        ergebnis.portionen += 1
        ergebnis.passagen += len(auswahl)
        ergebnis.offene_passagen = len(offen) - len(auswahl)
        ergebnis.kosten = Kosten(
            eingabe_tokens=ergebnis.kosten.eingabe_tokens + durchgang.kosten.eingabe_tokens,
            ausgabe_tokens=ergebnis.kosten.ausgabe_tokens + durchgang.kosten.ausgabe_tokens,
            betrag_eur=round(ergebnis.kosten.betrag_eur + durchgang.kosten.betrag_eur, 6),
        )

    def chronologie_offen(self, akte_id: str) -> list[str]:
        """Kennungen der Passagen, die die Chronologie noch nicht gesehen hat."""
        g = self.lesen(akte_id)
        if g is None:
            return []
        erledigt = set(g.chronologie_passagen)
        return [p.kennung for p in self._passagen(g) if p.kennung not in erledigt]

    def chronologie_merken(self, akte_id: str, kennungen: list[str]) -> None:
        """Haelt fest, welche Passagen der Chronologielauf gesehen hat.

        Getrennt vom Eintragen der Ereignisse: Auch ein Lauf, der nichts findet
        - ein Schriftsatz ohne datierbares Ereignis -, ist erledigt. Ohne diese
        Marke liefe er bei jedem Knopfdruck erneut und kostete jedes Mal.
        """
        if self._speicher is None or not kennungen:
            return
        g = self._gelesen(akte_id)
        if g is None:
            return
        bekannt = set(g.chronologie_passagen)
        g.chronologie_passagen.extend(k for k in kennungen if k not in bekannt)
        g.aktualisiert_am = datetime.now(timezone.utc)
        self._speicher.ablegen(g)

    def chronologie_fortschreiben(self, sitzung: Sitzung,
                                  analyse: Aktenanalyse | Chronologieergebnis) -> list[ChronologieEintrag]:
        """Traegt die belegten Ereignisse einer Analyse in die dauerhafte Chronologie ein.

        Ein Mandat laeuft ueber Wochen: Ein Schriftsatz kommt, drei Wochen
        spaeter die Antwort. Ohne diese Fortschreibung entstuende der Zeitstrahl
        bei jedem Durchgang neu - also ein voller Modellaufruf ueber die ganze
        Akte fuer zwei neue Zeilen, und die frueheren Ereignisse waeren nur so
        lange da, wie die Sitzung lebt (fuenfzehn Minuten).

        Zusammengefuehrt wird, nicht ersetzt: Was schon steht, bleibt stehen.
        Ein Ereignis gilt als bekannt, wenn am selben Datum bereits etwas
        hinreichend Gleichlautendes vermerkt ist.

        Nur belegte Eintraege. Die Analyse hat unbelegte bereits ausgesondert;
        dass hier noch einmal geprueft wird, ist Absicht - in das Dauerhafte
        soll nichts gelangen, was sich nicht auf eine Passage zurueckfuehren
        laesst.
        """
        if self._speicher is None:
            return list(analyse.chronologie)
        g = self._gelesen(sitzung.akte_id) or self._neu(sitzung)
        vorher = len(g.chronologie)
        for eintrag in analyse.chronologie:
            if not eintrag.quellen or not eintrag.ereignis.strip() or not str(eintrag.datum).strip():
                continue
            if any(vorhanden.datum == eintrag.datum
                   and _gleicher_vorgang(vorhanden.ereignis, eintrag.ereignis)
                   for vorhanden in g.chronologie):
                continue
            g.chronologie.append(eintrag)
        if len(g.chronologie) == vorher:
            return g.chronologie
        # Sortiert ablegen, damit die Oberflaeche nichts nachholen muss und der
        # Zeitstrahl auch in einem Export in der richtigen Reihenfolge steht.
        g.chronologie.sort(key=lambda x: str(x.datum))
        g.chronologie = g.chronologie[-self._e.gedaechtnis_max_chronologie:]
        g.aktualisiert_am = datetime.now(timezone.utc)
        self._speicher.ablegen(g)
        ereignis(_log, "gedaechtnis_chronologie", akte=sitzung.akte_id,
                 neu=len(g.chronologie) - vorher, gesamt=len(g.chronologie))
        return g.chronologie

    def analyse_merken(self, sitzung: Sitzung, analyse: Aktenanalyse,
                       erfasste_dokumente: list[str], akte_dokumente: list[str]) -> None:
        """Legt die zuletzt gelaufene Aktenanalyse ab.

        Sie kostet einen Modellaufruf ueber die ganze Akte - an der echten
        Akte der Kanzlei rund 28 Cent - und war bis zum 05.10.2026 weg, sobald
        das Programm geschlossen wurde. Von allem, was ein Durchgang erzeugt,
        war sie das Teuerste und das Einzige, das niemand aufbewahrt hat.

        Zwei Listen werden mitgeschrieben, weil sie zwei verschiedene Fragen
        beantworten: welche Dokumente in die Analyse eingegangen SIND, und
        welche die Akte zu dem Zeitpunkt ueberhaupt ENTHIELT. Nur an der
        zweiten laesst sich spaeter erkennen, ob seitdem etwas neu
        dazugekommen ist.
        """
        if self._speicher is None:
            return
        g = self._gelesen(sitzung.akte_id) or self._neu(sitzung)
        g.analyse = analyse
        g.analyse_am = datetime.now(timezone.utc)
        g.analyse_dokumente = sorted(set(erfasste_dokumente))
        # Alles drei zusammen: was jurnodes jetzt fuehrt, was im Gedaechtnis
        # liegt und was gerade mitging. Die Vereinigung ist die sichere
        # Richtung - ein Dokument, das hier fehlt, meldet sich spaeter als
        # "neu", und ein Hinweis zu viel ist billiger als ein uebersehenes
        # Schriftstueck.
        g.analyse_akte_dokumente = sorted(set(akte_dokumente)
                                          | {d.dokument_id for d in g.dokumente}
                                          | set(erfasste_dokumente))
        g.aktualisiert_am = g.analyse_am
        self._nachtragen(g, "analyse")
        ereignis(_log, "gedaechtnis_analyse", akte=sitzung.akte_id,
                 erfasst=len(g.analyse_dokumente), in_der_akte=len(g.analyse_akte_dokumente))

    def analyse_stand(self, akte_id: str, dokumente_jetzt: list[Dokument] | None = None) -> dict:
        """Liegt eine Analyse vor, von wann - und was ist seitdem dazugekommen?

        Kostet nichts: Der Vergleich laeuft im Programm, ohne Modellaufruf.
        Genau deshalb darf er bei jedem Oeffnen der Akte laufen. Die Kanzlei am
        05.10.2026: "Wichtig ist, dass das Programm vielleicht selber erkennt,
        wenn neue Dokumente in der Akte sind."

        Verglichen wird gegen das, was die Akte DAMALS enthielt - nicht gegen
        das, was in die Analyse eingegangen ist. Sonst zaehlte jedes bewusst
        nicht vorgewaehlte Dokument - eine Rechnung etwa - bei jedem Oeffnen
        wieder als neu, und die Warnung waere nach einer Woche nichts mehr wert.
        """
        g = self._gelesen(akte_id)
        if g is None or g.analyse is None:
            return {"vorhanden": False, "am": None, "erfasst": 0, "neu": [], "entfallen": 0}
        damals = set(g.analyse_akte_dokumente)
        heute = {d.id: d.titel for d in (dokumente_jetzt or [])}
        neu = [{"dokument_id": kennung, "titel": titel}
               for kennung, titel in heute.items() if kennung not in damals]
        return {
            "vorhanden": True,
            "am": g.analyse_am,
            "erfasst": len(g.analyse_dokumente),
            # Nach Titel sortiert, damit zweimal dieselbe Liste auch zweimal
            # gleich aussieht - sonst sieht ein zweiter Blick nach Bewegung aus.
            "neu": sorted(neu, key=lambda x: x["titel"]),
            "entfallen": len([k for k in damals if dokumente_jetzt is not None and k not in heute]),
        }

    def dokument_vergessen(self, akte_id: str, dokument_id: str) -> Aktengedaechtnis:
        """Entfernt einen Dokumentauszug samt allem, was aus ihm abgeleitet wurde.

        Es genügt nicht, den Auszug zu streichen: Der Lebenssachverhalt ist aus
        ihm mitgeschrieben, Antworten zitieren ihn, die Chronologie stützt sich
        auf ihn. Alles das bliebe sonst als Rest des gelöschten Dokuments im
        Gedächtnis stehen.

        Entfernt wird jedoch nur, was wirklich auf diesem Dokument beruht. Das
        war früher anders: Weil die Fundstellenkennungen die Dokumente
        durchzählten, verschob ein entferntes Dokument jede Kennung dahinter,
        und deshalb musste alles Abgeleitete fallen - ein Lebenssachverhalt aus
        fünfzig Dokumenten war wegen eines einzigen dahin. Seit jeder Auszug
        eine feste Nummer trägt, verschiebt sich nichts mehr, und der Rest des
        Gedächtnisses bleibt stehen.
        """
        g = self._holen(akte_id)
        if not any(d.dokument_id == dokument_id for d in g.dokumente):
            raise GedaechtnisFehler(f"Das Dokument {dokument_id} liegt nicht im Gedächtnis.")
        entfallene = {p.kennung for p in self._passagen(g, nur_dokumente={dokument_id})}
        g.dokumente = [d for d in g.dokumente if d.dokument_id != dokument_id]
        vorher = len(g.fragen_antworten)
        g.fragen_antworten = [
            runde for runde in g.fragen_antworten
            if not any(q.dokument_id == dokument_id for q in runde.quellen)
        ]
        self._abgeleitetes_bereinigen(g, entfallene, dokument_id)
        if dokument_id not in g.vergessene_dokumente:
            g.vergessene_dokumente.append(dokument_id)
        g.aktualisiert_am = datetime.now(timezone.utc)
        self._speicher.ablegen(g)
        geschlossene = self._offene_sitzungen_bereinigen(akte_id, dokument_id)
        ereignis(_log, "gedaechtnis_dokument_vergessen", akte=akte_id, dokument=dokument_id,
                 verworfene_fragen=vorher - len(g.fragen_antworten),
                 bereinigte_sitzungen=geschlossene)
        return g

    def _offene_sitzungen_bereinigen(self, akte_id: str, dokument_id: str) -> int:
        """Das Dokument auch aus den offenen Sitzungen nehmen.

        Befund F02.3 der Zweitprüfung vom 05.10.2026. „Vergessen" räumte das
        Gedächtnis auf und ließ ein bereits geöffnetes Fenster unberührt. Dort
        lag der Auszug weiter im Sitzungsspeicher; die nächste Frage
        antwortete darauf, und ``antwort_merken`` legte diese Antwort **neu**
        im Gedächtnis ab. Die Oberfläche meldete erfolgreiches Entfernen,
        während derselbe Inhalt durch die Hintertür zurückkam.

        Ein Löschverlangen, das nur gilt, solange niemand ein zweites Fenster
        offen hat, ist keines.

        Was hier nicht geschieht: die Sitzung schließen. Der Bearbeiter
        verlöre seinen Dialog und seine Belege für alle übrigen Dokumente,
        und das wäre eine Strafe für eine Löschung, die er selbst ausgelöst
        hat. Entfernt wird genau das eine Dokument.
        """
        if self._sitzungsspeicher is None:
            return 0
        betroffen = 0
        for sitzung_id in self._sitzungsspeicher.sitzungen_der_akte(akte_id):
            sitzung = self._sitzungsspeicher.sitzung_lesen(sitzung_id)
            if sitzung is None:
                continue
            if not any(d.dokument_id == dokument_id for d in sitzung.geladen):
                continue
            sitzung.geladen = [d for d in sitzung.geladen if d.dokument_id != dokument_id]
            sitzung.hinweise = list(sitzung.hinweise) + [
                "Ein Dokument ist aus dem Gedächtnis entfernt worden und steht "
                "dieser Sitzung nicht mehr zur Verfügung."
            ]
            self._sitzungsspeicher.text_loeschen(sitzung_id, dokument_id)
            self._sitzungsspeicher.sitzung_ablegen(sitzung)
            betroffen += 1
        return betroffen

    def antwort_vergessen(self, akte_id: str, nummer: int) -> Aktengedaechtnis:
        """Entfernt genau eine gespeicherte Frage-Antwort-Runde."""
        g = self._holen(akte_id)
        if not 0 <= nummer < len(g.fragen_antworten):
            raise GedaechtnisFehler("Diese Frage liegt nicht im Gedächtnis.")
        del g.fragen_antworten[nummer]
        g.aktualisiert_am = datetime.now(timezone.utc)
        self._speicher.ablegen(g)
        ereignis(_log, "gedaechtnis_antwort_vergessen", akte=akte_id, verbleibend=len(g.fragen_antworten))
        return g

    def _holen(self, akte_id: str) -> Aktengedaechtnis:
        if self._speicher is None:
            raise GedaechtnisFehler("Das Gedächtnis ist nicht aktiviert.")
        g = self._gelesen(akte_id)
        if g is None:
            raise GedaechtnisFehler("Für diese Akte gibt es kein Gedächtnis.")
        return g

    @staticmethod
    def _abgeleitetes_bereinigen(g: Aktengedaechtnis, entfallene: set[str],
                                 dokument_id: str) -> None:
        """Nimmt aus dem Abgeleiteten heraus, was auf dem entfallenen Auszug beruht.

        Der Lebenssachverhalt geht dafuer durch dieselbe Belegpruefung wie jede
        Antwort: Was sich nur auf die entfallenen Passagen stuetzte, faellt
        heraus und hinterlaesst eine sichtbare Marke; der uebrige Text bleibt
        mit seinen Belegen stehen.

        Chronologie und Frage-Antwort-Runden werden ganz verworfen, sobald sie
        das Dokument auch nur mitzitieren. Das ist strenger als noetig und
        Absicht: Ein Eintrag, der aus zwei Quellen zusammengesetzt wurde,
        stuende sonst weiter da, obwohl die Haelfte seiner Grundlage fehlt.

        **Die gespeicherte Analyse fiel bis zum 05.10.2026 durch dieses Netz.**
        Sie ist am selben Tag dazugekommen (``analyse_merken``), und hier ist
        sie schlicht vergessen worden - obwohl die Zusage "samt allem
        Abgeleiteten" lautete und obwohl eine eigene Pruefung sie behauptete.
        Gefunden hat es die Zweitpruefung desselben Tages, Befund F02.

        Die Lehre: Ein neues Feld im Gedaechtnis ist nicht fertig, wenn es
        geschrieben und angezeigt wird. Es ist fertig, wenn auch gesagt ist,
        was beim Loeschen damit geschieht.
        """
        index = index_bauen(Gedaechtnisdienst._passagen(g))
        if g.lebenssachverhalt.strip():
            # verlangt_alle: Eine Aussage, die das entfernte Dokument auch nur
            # MITzitiert, faellt ganz (Befund F02.2 der Zweitpruefung,
            # 05.10.2026). Vorher blieb sie mit der verbliebenen Kennung
            # stehen - dass die andere Quelle den Text allein traegt, wusste
            # niemand. Chronologie und Antworten waren schon immer so streng.
            belegt = aussage_fail_closed(g.lebenssachverhalt, index, verlangt_alle=True)
            leer = not belegt.quellen or belegt.text == VERZICHT
            # VERZICHT ist die Ersatzantwort auf eine Frage. Im Lebenssachverhalt
            # waere sie eine Aussage ueber die Akte, die niemand getroffen hat.
            g.lebenssachverhalt = "" if leer else belegt.text
            g.lebenssachverhalt_quellen = [] if leer else belegt.quellen
        g.verarbeitete_passagen = [k for k in g.verarbeitete_passagen if k not in entfallene]
        g.chronologie = [
            eintrag for eintrag in g.chronologie
            if eintrag.quellen and not any(q.dokument_id == dokument_id for q in eintrag.quellen)
        ]
        g.chronologie_passagen = [k for k in g.chronologie_passagen if k not in entfallene]
        Gedaechtnisdienst._analyse_bereinigen(g, dokument_id)

    @staticmethod
    def _analyse_bereinigen(g: Aktengedaechtnis, dokument_id: str) -> None:
        """Die gespeicherte Analyse nach demselben Massstab wie die Chronologie.

        Jede ihrer sechs Listen traegt Quellen. Ein Eintrag faellt GANZ, sobald
        er das entfallene Dokument auch nur mitzitiert - dieselbe Strenge wie
        oben, aus demselben Grund.

        Bleibt danach nichts uebrig, was das entfernte Dokument nicht beruehrt
        haette, faellt die Analyse insgesamt: Eine Analyse, der ihre Grundlage
        fehlt, sieht genauso vollstaendig aus wie eine vollstaendige.
        """
        if g.analyse is None:
            return
        betroffen = False
        for name in ("chronologie", "beteiligte", "forderungen", "beweismittel",
                     "offene_punkte", "widersprueche"):
            vorher = getattr(g.analyse, name, None)
            if not isinstance(vorher, list):
                continue
            behalten = [e for e in vorher
                        if not any(q.dokument_id == dokument_id
                                   for q in getattr(e, "quellen", []) or [])]
            if len(behalten) != len(vorher):
                betroffen = True
            setattr(g.analyse, name, behalten)
        if not betroffen:
            return
        # Der Umfang stimmt nicht mehr: Das Dokument gehoerte zur Analyse und
        # gehoert jetzt nicht mehr dazu. Beides muss die Oberflaeche wissen,
        # sonst steht dort ein Stand, den es so nie gab.
        g.analyse_dokumente = [d for d in g.analyse_dokumente if d != dokument_id]
        g.analyse_hinweis = (
            "Aus dieser Analyse wurde nachträglich ein Dokument entfernt. "
            "Was darauf beruhte, ist herausgenommen; der Rest ist nicht neu "
            "gerechnet.")

    def ablegen(self, gedaechtnis: Aktengedaechtnis) -> None:
        if self._speicher is None:
            raise GedaechtnisFehler("Das Gedächtnis ist nicht aktiviert.")
        self._speicher.ablegen(gedaechtnis)

    def loeschen(self, akte_id: str) -> None:
        if self._speicher is None:
            raise GedaechtnisFehler("Das Gedächtnis ist nicht aktiviert.")
        self._speicher.loeschen(akte_id)
        ereignis(_log, "gedaechtnis_geloescht", akte=akte_id)

    @staticmethod
    def arbeitsstand(g: Aktengedaechtnis | None, wieviele: int = 3) -> dict:
        """Woran zuletzt gearbeitet wurde - ohne einen Modellaufruf.

        Aus der Kanzlei am 25.09.2026: "beim Öffnen der Akte sehen, was man
        als Letztes gemacht hat, sodass man wieder daran ansetzen kann."

        Alles dafür liegt schon im Gedächtnis; es wurde nur nie gezeigt. Das
        Gedächtnisfenster sagt, WAS darin liegt - nicht, WAS ZULETZT GETAN
        wurde. Das sind zwei verschiedene Fragen, und die zweite stellt man
        morgens.

        Gezeigt werden die eigenen Fragen **im Wortlaut**, nicht eine vom
        Modell geschriebene Zusammenfassung. Zwei Gründe: Sie kostet bei jedem
        Öffnen Geld, und sie kann danebenliegen. An der eigenen Frage erkennt
        man sich ohnehin besser wieder als an einer fremden Beschreibung.
        """
        if g is None or not g.dokumente and not g.fragen_antworten:
            return {"vorhanden": False, "fragen": [], "dokumente": 0,
                    "chronologie_bis": "", "zuletzt": None}
        # Die jüngsten zuerst: Wer gestern dreimal gefragt hat, will die letzte
        # Frage sehen und nicht die erste.
        jung = sorted(g.fragen_antworten, key=lambda x: x.zeitpunkt, reverse=True)
        daten = [e.datum for e in g.chronologie if e.datum]
        return {
            "vorhanden": True,
            "zuletzt": g.aktualisiert_am,
            "fragen": [{"frage": x.frage, "zeitpunkt": x.zeitpunkt}
                       for x in jung[:wieviele]],
            "fragen_gesamt": len(g.fragen_antworten),
            "dokumente": len(g.dokumente),
            "zeichen": sum(d.zeichen for d in g.dokumente),
            "chronologie": len(g.chronologie),
            # Bis wann der Zeitstrahl reicht - die Frage "sind die neuen
            # Schriftsätze schon drin?" beantwortet sich damit von selbst.
            "chronologie_bis": max(daten) if daten else "",
            "lebenssachverhalt": bool(g.lebenssachverhalt.strip()),
        }

    @staticmethod
    def uebersicht(g: Aktengedaechtnis | None) -> dict:
        if g is None:
            return {"vorhanden": False, "dokumente": 0, "fragen": 0, "lebenssachverhalt": "",
                    "quellen": [], "chronologie": [], "zeichen": 0, "eintraege": [],
                    "analyse": None, "analyse_am": None, "analyse_dokumente": [],
                    "arbeitsstand": Gedaechtnisdienst.arbeitsstand(None)}
        return {
            "vorhanden": True,
            "dokumente": len(g.dokumente),
            "fragen": len(g.fragen_antworten),
            "lebenssachverhalt": g.lebenssachverhalt,
            "quellen": [q.model_dump() for q in g.lebenssachverhalt_quellen],
            "fragen_antworten": [x.model_dump() for x in g.fragen_antworten],
            "chronologie": [x.model_dump() for x in g.chronologie],
            # Umfang: Was liegt drin, und wie schwer wiegt es? Ohne diese Zahlen
            # ist das Gedaechtnis eine Zusage, die niemand nachpruefen kann.
            "zeichen": sum(d.zeichen for d in g.dokumente),
            "eintraege": [
                {"dokument_id": d.dokument_id, "titel": d.titel, "seiten": len(d.seiten),
                 "zeichen": d.zeichen, "ocr": d.ocr, "hinzugefuegt_am": d.hinzugefuegt_am}
                for d in g.dokumente
            ],
            # Die zuletzt gelaufene Analyse, so wie sie gespeichert ist. Ob sie
            # noch zur Akte passt, beantwortet analyse_stand() - dafuer braucht
            # es die heutige Dokumentliste, die hier nicht vorliegt.
            "analyse": g.analyse.model_dump() if g.analyse else None,
            "analyse_am": g.analyse_am,
            "analyse_dokumente": list(g.analyse_dokumente),
            "offene_dokumente": Gedaechtnisdienst._offene_dokumente(g),
            "aktualisiert_am": g.aktualisiert_am,
            "aktenstatus": g.aktenstatus,
            "retention_reason": g.retention_reason,
            "status_geprueft_am": g.status_geprueft_am,
            "abgeschlossen_am": g.abgeschlossen_am,
            "loeschung_vorgesehen_am": g.loeschung_vorgesehen_am,
            "arbeitsstand": Gedaechtnisdienst.arbeitsstand(g),
        }

    @staticmethod
    def _neu(sitzung: Sitzung) -> Aktengedaechtnis:
        status = (sitzung.akte.status or "unbekannt").strip().lower()
        return Aktengedaechtnis(
            akte_id=sitzung.akte_id, aktenzeichen=sitzung.akte.aktenzeichen,
            bezeichnung=sitzung.akte.bezeichnung, aktenstatus=status,
            retention_reason=Gedaechtnisdienst._aufbewahrungsgrund(status),
        )

    @staticmethod
    def _aufbewahrungsgrund(status: str) -> str:
        normalisiert = status.strip().lower()
        if normalisiert in {"abgeschlossen", "archiviert", "geloescht", "gelöscht"}:
            return "abschlusspruefung_erforderlich"
        if normalisiert in {"ruhend", "ausgesetzt", "wiedervorlage"}:
            return "laufendes_verfahren_ruhend"
        if not normalisiert or normalisiert in {"unbekannt", "fehler"}:
            return "status_ungeklaert_nicht_loeschen"
        return "laufende_mandatsbearbeitung"

    @staticmethod
    def _status_synchronisieren(g: Aktengedaechtnis, sitzung: Sitzung) -> bool:
        """Übernimmt den jurnodes-Status, ohne automatisch zu löschen.

        Selbst ein Abschlussstatus ist zunächst nur ein Anlass für den
        kontrollierten Export-/Abschlussworkflow. Eine bereits vorgemerkte
        Löschung wird aufgehoben, sobald die Akte wieder laufend ist.
        """
        jetzt = datetime.now(timezone.utc)
        status = (sitzung.akte.status or "unbekannt").strip().lower()
        grund = Gedaechtnisdienst._aufbewahrungsgrund(status)
        geaendert = g.aktenstatus != status or g.retention_reason != grund
        g.aktenstatus = status
        g.retention_reason = grund
        g.status_geprueft_am = jetzt
        if grund in {"laufende_mandatsbearbeitung", "laufendes_verfahren_ruhend"}:
            if g.abgeschlossen_am is not None or g.loeschung_vorgesehen_am is not None:
                geaendert = True
            g.abgeschlossen_am = None
            g.loeschung_vorgesehen_am = None
        # status_geprueft_am wird bewusst bei jedem erfolgreichen Abgleich
        # erneuert und deshalb ebenfalls persistiert.
        return True

    @staticmethod
    def _passagen(g: Aktengedaechtnis, nur_dokumente: set[str] | None = None) -> list[Passage]:
        """Die Passagen des Gedaechtnisses - mit der festen Nummer je Dokument.

        Die Nummer kommt aus dem Auszug selbst, nicht aus seiner Stellung in
        der Liste. Das ist der ganze Unterschied: Eine Kennung, die heute
        vergeben wird, bedeutet in zwei Jahren dasselbe, auch wenn davor
        Dokumente hinzugekommen oder entfallen sind.
        """
        Gedaechtnisdienst._nummern_sichern(g)
        ergebnis: list[Passage] = []
        for gespeichert in g.dokumente:
            if nur_dokumente is not None and gespeichert.dokument_id not in nur_dokumente:
                continue
            # Das Datum muss mit: material_bauen schreibt es in die Kopfzeile
            # jeder Passage, und ohne diese Zeile stand dort nie eines - das
            # Einlesen geht ueber diese zusammengebauten Dokumente, nicht
            # ueber die der Akte.
            dokument = Dokument(id=gespeichert.dokument_id, akte_id=g.akte_id,
                                 titel=gespeichert.titel, dateiname="",
                                 datum=gespeichert.datum)
            ergebnis.extend(passagen_bilden(gespeichert.nummer, dokument, gespeichert.seiten))
        return ergebnis

    @staticmethod
    def _nummern_sichern(g: Aktengedaechtnis) -> bool:
        """Traegt fehlende Dokumentnummern nach. Meldet, ob sich etwas geaendert hat.

        Ein Gedaechtnis aus Fassung 3 kennt keine Nummern; dort ergab sie sich
        aus der Stellung in der Liste. Genau diese Stellung wird deshalb
        festgeschrieben - jede bereits gespeicherte Kennung zeigt danach
        weiterhin auf dasselbe Dokument. Hat dagegen ein Teil der Auszuege
        schon eine Nummer, waere die Stellung der falsche Massstab; dann wird
        aus dem Zaehler weitergezaehlt.
        """
        ohne = [d for d in g.dokumente if d.nummer <= 0]
        if ohne and len(ohne) == len(g.dokumente):
            for stelle, dokument in enumerate(g.dokumente, start=1):
                dokument.nummer = stelle
        else:
            zaehler = max([d.nummer for d in g.dokumente] + [g.letzte_dokumentnummer], default=0)
            for dokument in ohne:
                zaehler += 1
                dokument.nummer = zaehler
        hoechste = max((d.nummer for d in g.dokumente), default=0)
        geaendert = bool(ohne) or g.letzte_dokumentnummer < hoechste or g.schema_version < 4
        g.letzte_dokumentnummer = max(g.letzte_dokumentnummer, hoechste)
        g.schema_version = max(g.schema_version, 4)
        return geaendert

    @staticmethod
    def _belegte_fortschreibung(text: str, passagen: list[Passage]):
        """Entfernt zusätzlich freien Nachlauf hinter dem letzten Beleg."""
        import re

        belegt = aussage_fail_closed(text, index_bauen(passagen))
        treffer = list(re.finditer(r"\[Q:\s*[^\]]+\]", belegt.text))
        if treffer:
            belegt.text = belegt.text[:treffer[-1].end()].strip()
        return belegt

    @staticmethod
    def _offene_dokumente(g: Aktengedaechtnis) -> int:
        erledigt = set(g.verarbeitete_passagen)
        offen = {p.dokument_id for p in Gedaechtnisdienst._passagen(g) if p.kennung not in erledigt}
        return len(offen)


def _tausender(zahl: int) -> str:
    return f"{zahl:,}".replace(",", ".")


def _dokumentspanne(passagen: list[Passage]) -> str:
    """„Dokument 19 bis 27" – damit der Hinweis auf die Akte zeigt, nicht auf Kennungen."""
    titel = []
    for p in passagen:
        if p.dokument_titel not in titel:
            titel.append(p.dokument_titel)
    if not titel:
        return "diesem Abschnitt"
    if len(titel) == 1:
        return f"„{titel[0]}“"
    return f"„{titel[0]}“ bis „{titel[-1]}“ ({len(titel)} Dokumente)"


def _decke_erreicht(g: Aktengedaechtnis, grenze: int, offen: int) -> str:
    """Sagt, dass der Lebenssachverhalt den Platz aufgebraucht hat – und was jetzt hilft.

    Diese Meldung ist der ehrliche Boden des Verfahrens. Der Lebenssachverhalt
    wächst mit jeder Portion, und er geht bei jeder weiteren mit; irgendwann
    füllt er den Aufruf allein. Man könnte ihn an dieser Stelle zusammenfassen
    lassen – und genau dabei ginge unbemerkt verloren, wofür dieses Gedächtnis
    gebaut ist. Deshalb wird nicht gekürzt, sondern gesagt, dass Schluss ist.
    """
    return (
        f"Der Lebenssachverhalt dieser Akte ist auf {_tausender(len(g.lebenssachverhalt))} "
        f"Zeichen gewachsen. Zusammen mit einer weiteren Portion passt er nicht mehr in "
        f"einen Aufruf (Grenze: {_tausender(grenze)} Zeichen). {_tausender(offen)} Passagen "
        f"aus {len(g.dokumente)} Dokumenten sind noch ungelesen.\n\n"
        f"Gekürzt wird der Lebenssachverhalt nicht. Er ist das Gedächtnis dieser Akte; "
        f"was beim Zusammenfassen herausfiele, merkte niemand – und genau davor soll "
        f"dieses Programm schützen.\n\n"
        f"Was jetzt hilft: im Explorer Dokumente aus der Arbeitsakte nehmen, die für die "
        f"weitere Bearbeitung nichts mehr hergeben (der Volltext bleibt im Gedächtnis und "
        f"bleibt befragbar) – oder die Akte in zwei Arbeitsakten teilen, etwa nach "
        f"Verfahrensabschnitten. Fragen an die Akte sind von dieser Grenze nicht betroffen: "
        f"Sie suchen sich ihre Stellen aus allen Dokumenten."
    )
