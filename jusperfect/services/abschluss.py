"""Abschluss einer Akte: erst exportieren, dann löschen – und nur dann.

jurnodes führt die Akte. Ein Arbeitsbereich in jusperfect endet deshalb
nicht durch Zeitablauf, sondern durch ein *bestätigtes* Abschlussereignis in
jurnodes. Von dort an läuft eine Übergangsfrist; danach kann der Abschluss
ausgeführt werden.

Die Reihenfolge ist die eigentliche Zusage dieses Dienstes:

1. Berechtigung prüfen – wer die Akte nicht sehen darf, schließt sie nicht ab.
2. Status frisch aus jurnodes holen. Ist jurnodes nicht erreichbar oder die
   Akte wieder laufend, wird **nichts** gelöscht.
3. Den Arbeitsstand als Vermerk nach jurnodes exportieren, freigegeben vom
   Bearbeiter und an genau den angezeigten Text gebunden.
4. Erst wenn der Export nachweislich angekommen ist: Gedächtnis, Sitzungen,
   Dokumentauszüge und Entwürfe der Akte löschen.
5. Einen Nachweis schreiben – Zeitpunkte und Stückzahlen, keine Inhalte.

Schlägt ein Schritt fehl, bricht der Vorgang ab, bevor gelöscht wird. Im
Zweifel bleibt der Arbeitsbereich bestehen: Ein zu früh gelöschtes Mandat
lässt sich nicht wiederherstellen, ein zu lange aufbewahrtes schon.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from jusperfect.config import Einstellungen
from jusperfect.domain.models import Aktengedaechtnis
from jusperfect.gedaechtnis.base import GedaechtnisFehler
from jusperfect.jurnodes.base import JurNodesAdapter, JurNodesFehler
from jusperfect.security.approval import Freigabestelle, text_pruefsumme
from jusperfect.security.berechtigungen import Berechtigungen
from jusperfect.security.identitaet import Identitaet
from jusperfect.security.protokoll import ereignis, protokoll
from jusperfect.services.gedaechtnis import Gedaechtnisdienst
from jusperfect.speicher.base import SitzungsSpeicher

_log = protokoll("abschluss")

#: Statuswerte aus jurnodes, die einen Abschluss überhaupt erst zulassen.
ABSCHLUSSSTATUS = frozenset({"abgeschlossen", "archiviert", "geloescht", "gelöscht"})

KENNZEICHNUNG = ("Arbeitsstand aus jusperfect – vor Abschluss der Akte gesichert. "
                 "Von KI erstellt, anwaltlich geprüft und freigegeben.")


class AbschlussFehler(RuntimeError):
    """Der Abschluss ist in diesem Zustand nicht zulässig."""


@dataclass(frozen=True, slots=True)
class Loeschnachweis:
    """Was gelöscht wurde – in Zahlen, nie in Inhalten."""
    akte_id: str
    aktenzeichen: str
    nutzer_id: str
    zeitpunkt: datetime
    jurnodes_referenz: str
    dokumente: int = 0
    fragen: int = 0
    sitzungen: int = 0
    entwuerfe: int = 0

    def als_dict(self) -> dict:
        return {
            "akte_id": self.akte_id, "aktenzeichen": self.aktenzeichen,
            "nutzer_id": self.nutzer_id, "zeitpunkt": self.zeitpunkt,
            "jurnodes_referenz": self.jurnodes_referenz,
            "geloescht": {
                "dokumente": self.dokumente, "fragen": self.fragen,
                "sitzungen": self.sitzungen, "entwuerfe": self.entwuerfe,
            },
        }


@dataclass(frozen=True, slots=True)
class Abschlussstand:
    akte_id: str
    aktenstatus: str
    abschlussreif: bool
    abgeschlossen_am: datetime | None = None
    loeschung_vorgesehen_am: datetime | None = None
    faellig: bool = False
    hinweise: list[str] = field(default_factory=list)

    def als_dict(self) -> dict:
        return {
            "akte_id": self.akte_id, "aktenstatus": self.aktenstatus,
            "abschlussreif": self.abschlussreif, "abgeschlossen_am": self.abgeschlossen_am,
            "loeschung_vorgesehen_am": self.loeschung_vorgesehen_am,
            "faellig": self.faellig, "hinweise": self.hinweise,
        }


class Abschlussdienst:
    def __init__(self, gedaechtnis: Gedaechtnisdienst, adapter: JurNodesAdapter,
                 berechtigungen: Berechtigungen, speicher: SitzungsSpeicher,
                 freigabestelle: Freigabestelle, einstellungen: Einstellungen) -> None:
        self._gedaechtnis = gedaechtnis
        self._adapter = adapter
        self._berechtigungen = berechtigungen
        self._speicher = speicher
        self._freigabestelle = freigabestelle
        self._e = einstellungen

    # ── Lesen ──────────────────────────────────────────────────────────────

    def stand(self, identitaet: Identitaet, akte_id: str) -> Abschlussstand:
        """Was für diese Akte ansteht – ohne etwas zu verändern."""
        g = self._gedaechtnis_holen(identitaet, akte_id)
        status, hinweise = self._status_frisch(akte_id, g)
        vorgesehen = g.loeschung_vorgesehen_am
        return Abschlussstand(
            akte_id=akte_id, aktenstatus=status,
            abschlussreif=status in ABSCHLUSSSTATUS,
            abgeschlossen_am=g.abgeschlossen_am, loeschung_vorgesehen_am=vorgesehen,
            faellig=bool(vorgesehen and vorgesehen <= _jetzt()),
            hinweise=hinweise,
        )

    def export_vorschau(self, identitaet: Identitaet, akte_id: str) -> dict:
        """Genau der Text, der nach jurnodes geschrieben würde – mit Prüfsumme.

        Die Prüfsumme bindet die spätere Freigabe an diesen Text: Freigegeben
        wird nur, was auch angezeigt wurde.
        """
        g = self._gedaechtnis_holen(identitaet, akte_id)
        titel, text = self._exporttext(g)
        return {"akte_id": akte_id, "titel": titel, "text": text,
                "text_pruefsumme": text_pruefsumme(text)}

    # ── Vormerken ──────────────────────────────────────────────────────────

    def vormerken(self, identitaet: Identitaet, akte_id: str) -> Abschlussstand:
        """Startet die Übergangsfrist – nur bei bestätigtem Abschluss in jurnodes."""
        g = self._gedaechtnis_holen(identitaet, akte_id)
        status, hinweise = self._status_frisch(akte_id, g)
        if status not in ABSCHLUSSSTATUS:
            raise AbschlussFehler(
                f"Die Akte ist in jurnodes nicht abgeschlossen (Status „{status}“). "
                "Der Arbeitsbereich bleibt unverändert erhalten."
            )
        if g.loeschung_vorgesehen_am is None:
            jetzt = _jetzt()
            g.abgeschlossen_am = jetzt
            g.loeschung_vorgesehen_am = jetzt + timedelta(days=self._e.gedaechtnis_uebergangsfrist_tage)
            self._ablegen(g)
            ereignis(_log, "abschluss_vorgemerkt", akte=akte_id, nutzer=identitaet.nutzer_id,
                     status=status, frist_tage=self._e.gedaechtnis_uebergangsfrist_tage)
        return Abschlussstand(
            akte_id=akte_id, aktenstatus=status, abschlussreif=True,
            abgeschlossen_am=g.abgeschlossen_am,
            loeschung_vorgesehen_am=g.loeschung_vorgesehen_am,
            faellig=bool(g.loeschung_vorgesehen_am and g.loeschung_vorgesehen_am <= _jetzt()),
            hinweise=hinweise,
        )

    # ── Ausführen ──────────────────────────────────────────────────────────

    def ausfuehren(self, identitaet: Identitaet, akte_id: str, bestaetigung: bool,
                   pruefsumme: str) -> Loeschnachweis:
        g = self._gedaechtnis_holen(identitaet, akte_id)
        if not bestaetigung:
            raise AbschlussFehler("Ohne ausdrückliche Bestätigung wird nichts exportiert und nichts gelöscht.")

        # jurnodes entscheidet, nicht die Uhr. Ein Ausfall bedeutet: nicht löschen.
        status = self._status_aus_jurnodes(akte_id)
        if status is None:
            raise AbschlussFehler(
                "Der Aktenstatus konnte nicht aus jurnodes gelesen werden. "
                "Es wird nichts gelöscht; bitte später erneut versuchen."
            )
        if status not in ABSCHLUSSSTATUS:
            # Die Akte ist wieder in Bearbeitung – die Vormerkung fällt weg.
            if g.abgeschlossen_am is not None or g.loeschung_vorgesehen_am is not None:
                g.abgeschlossen_am = None
                g.loeschung_vorgesehen_am = None
                self._ablegen(g)
                ereignis(_log, "abschluss_abgebrochen", akte=akte_id, status=status)
            raise AbschlussFehler(
                f"Die Akte ist in jurnodes wieder „{status}“. Eine vorgemerkte Löschung wurde aufgehoben."
            )
        if g.loeschung_vorgesehen_am is None:
            raise AbschlussFehler("Der Abschluss ist noch nicht vorgemerkt. Bitte zuerst vormerken.")
        if g.loeschung_vorgesehen_am > _jetzt():
            raise AbschlussFehler(
                f"Die Übergangsfrist läuft noch bis {g.loeschung_vorgesehen_am:%d.%m.%Y}. "
                "Vorher wird nichts gelöscht."
            )

        titel, text = self._exporttext(g)
        if text_pruefsumme(text) != pruefsumme:
            raise AbschlussFehler(
                "Der angezeigte Arbeitsstand stimmt nicht mehr mit dem gespeicherten überein. "
                "Bitte neu laden und erneut prüfen."
            )

        # Export zuerst. Schlägt er fehl, bleibt alles, wie es ist.
        freigabe = self._freigabestelle.erteilen(f"abschluss-{akte_id}", akte_id, identitaet.nutzer_id, text)
        try:
            referenz = self._adapter.vermerk_schreiben(akte_id, titel, text, freigabe)
        except JurNodesFehler as fehler:
            ereignis(_log, "abschluss_export_fehlgeschlagen", akte=akte_id, nutzer=identitaet.nutzer_id)
            raise AbschlussFehler(
                f"Der Arbeitsstand konnte nicht nach jurnodes geschrieben werden ({fehler}). "
                "Es wurde nichts gelöscht."
            ) from fehler

        nachweis = self._loeschen(identitaet, g, referenz)
        ereignis(_log, "abschluss_ausgefuehrt", akte=akte_id, nutzer=identitaet.nutzer_id,
                 referenz=referenz, dokumente=nachweis.dokumente, fragen=nachweis.fragen,
                 sitzungen=nachweis.sitzungen, entwuerfe=nachweis.entwuerfe)
        return nachweis

    # ── Innenleben ─────────────────────────────────────────────────────────

    def _loeschen(self, identitaet: Identitaet, g: Aktengedaechtnis, referenz: str) -> Loeschnachweis:
        """Entfernt alle Bestandteile des Arbeitsbereichs dieser Akte."""
        akte_id = g.akte_id
        sitzungen = self._speicher.sitzungen_der_akte(akte_id)
        entwuerfe = self._speicher.entwuerfe_der_akte(akte_id)
        # Die Sitzung nimmt ihre Dokumentauszüge mit (siehe sitzung_loeschen).
        for sitzung_id in sitzungen:
            self._speicher.sitzung_loeschen(sitzung_id)
        for entwurf_id in entwuerfe:
            self._speicher.entwurf_loeschen(entwurf_id)
        nachweis = Loeschnachweis(
            akte_id=akte_id, aktenzeichen=g.aktenzeichen, nutzer_id=identitaet.nutzer_id,
            zeitpunkt=_jetzt(), jurnodes_referenz=referenz,
            dokumente=len(g.dokumente), fragen=len(g.fragen_antworten),
            sitzungen=len(sitzungen), entwuerfe=len(entwuerfe),
        )
        self._gedaechtnis.loeschen(akte_id)
        return nachweis

    def _exporttext(self, g: Aktengedaechtnis) -> tuple[str, str]:
        """Baut den Vermerk aus dem belegten Arbeitsstand.

        Es wird nur übernommen, was ohnehin schon belegt gespeichert wurde:
        der Lebenssachverhalt und die geprüften Frage-Antwort-Runden.
        """
        zeilen = [KENNZEICHNUNG, ""]
        bezeichnung = " ".join(x for x in (g.aktenzeichen, g.bezeichnung) if x)
        if bezeichnung:
            zeilen += [f"Akte: {bezeichnung}", ""]
        inhalt = False
        if g.lebenssachverhalt.strip():
            zeilen += ["Lebenssachverhalt (mit Fundstellen)", "", g.lebenssachverhalt.strip(), ""]
            inhalt = True
        if g.fragen_antworten:
            zeilen += ["Geprüfte Fragen und Antworten", ""]
            for runde in g.fragen_antworten:
                zeilen += [f"Frage: {runde.frage}", f"Antwort: {runde.antwort}", ""]
            inhalt = True
        # Ein leerer Vermerk wäre irreführend: Er sähe aus wie ein gesicherter
        # Arbeitsstand. Der Ausdruck sagt deshalb ausdrücklich, dass keiner
        # vorlag – die Akte hatte nur Dokumentauszüge, keine belegten Ergebnisse.
        if not inhalt:
            zeilen += ["Für diese Akte lag kein belegter Arbeitsstand vor "
                       f"({len(g.dokumente)} Dokumentauszug/-auszüge, keine belegten Ergebnisse).", ""]
        return f"Arbeitsstand jusperfect – {bezeichnung or g.akte_id}", "\n".join(zeilen).strip() + "\n"

    def _gedaechtnis_holen(self, identitaet: Identitaet, akte_id: str) -> Aktengedaechtnis:
        # Berechtigung zuerst: Ein Entzug sperrt den Zugriff sofort – löscht
        # den Arbeitsbereich aber niemals von sich aus.
        self._berechtigungen.pruefen(identitaet, akte_id)
        if not self._gedaechtnis.aktiv:
            raise GedaechtnisFehler("Das Gedächtnis ist nicht aktiviert.")
        g = self._gedaechtnis.lesen(akte_id)
        if g is None:
            raise AbschlussFehler("Für diese Akte gibt es keinen Arbeitsbereich.")
        return g

    def _status_aus_jurnodes(self, akte_id: str) -> str | None:
        """Der Status, wie ihn jurnodes jetzt meldet – oder None bei Störung."""
        try:
            akte = self._adapter.akte(akte_id)
        except JurNodesFehler:
            return None
        return (akte.status or "unbekannt").strip().lower()

    def _status_frisch(self, akte_id: str, g: Aktengedaechtnis) -> tuple[str, list[str]]:
        status = self._status_aus_jurnodes(akte_id)
        if status is None:
            return g.aktenstatus, [
                "Der Status konnte nicht aus jurnodes gelesen werden; angezeigt wird der "
                "zuletzt bekannte. Es wird nichts gelöscht."
            ]
        if status == "unbekannt":
            return status, [
                "jurnodes meldet keinen Status für diese Akte. Ein Abschluss ist deshalb "
                "nicht möglich; der Arbeitsbereich bleibt erhalten."
            ]
        return status, []

    def _ablegen(self, g: Aktengedaechtnis) -> None:
        g.aktualisiert_am = _jetzt()
        self._gedaechtnis.ablegen(g)


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)
