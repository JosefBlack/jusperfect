"""Die Rückfrage: Läuft die Akte noch?

Aus der Kanzlei am 15.10.2026:

    „Du musst fragen: Läuft die Akte noch. Akten laufen manchmal jahrelang.
    Wenn die Frage mit Ja beantwortet wird, dann verlängert sich die
    Löschfrist um 12 Monate."

**Das ist der Kern, und er ist nicht technisch.** Bis heute begann in
jusperfect eine Löschfrist *nie von selbst*: Wer eine Akte nicht abschloss,
behielt die Arbeitskopie für immer. Das verstößt gegen Art. 5 Abs. 1 lit. e,
der keine Frist kennt, die vom Fleiß des Bearbeiters abhängt.

Der naheliegende Gegenentwurf — nach zwölf Monaten ohne Sitzung löschen —
wäre schlimmer gewesen. Eine Akte, in der ein Gutachten erwartet wird oder
ein Verfahren ruht, läuft weiter, auch wenn niemand sie öffnet. Sie zu
löschen, weil die Zeit vergangen ist, nimmt der Kanzlei die Arbeitskopie
eines lebenden Mandats.

**Deshalb löst die Zeit hier die FRAGE aus und nicht die Löschung.** Nach
zwölf Monaten ohne Sitzung wird gefragt. „Ja" verlängert um zwölf Monate und
wird vermerkt. „Nein" setzt die Übergangsfrist in Gang — gelöscht wird auch
dann erst über den Abschluss, mit Export und Nachweis.

Was ohne Antwort geschieht: **nichts.** Eine unbeantwortete Frage löscht
nicht. Sie bleibt stehen und steht in der Liste der offenen Rückfragen, bis
jemand sie beantwortet. Das ist die ungefährliche Richtung — und sie ist
nicht dasselbe wie der alte Zustand, weil die Frage sichtbar ist und der
alte Zustand unsichtbar war.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from jusperfect.config import Einstellungen
from jusperfect.domain.models import Aktengedaechtnis, Weiterfuehrung
from jusperfect.gedaechtnis.base import GedaechtnisFehler
from jusperfect.security.berechtigungen import Berechtigungen
from jusperfect.security.identitaet import Identitaet
from jusperfect.security.protokoll import ereignis, protokoll
from jusperfect.services.gedaechtnis import Gedaechtnisdienst

_log = protokoll("aufbewahrung")

#: Ein Monat als Tage. Kalendermonate zu rechnen brächte hier nichts: Die
#: Frist ist eine Hausfrist und kein gesetzlicher Termin, und ein Zwölftel
#: Jahr ist genau so gemeint, wie es dasteht.
TAGE_JE_MONAT = 30


class AufbewahrungFehler(RuntimeError):
    """Die Rückfrage ist in diesem Zustand nicht zu beantworten."""


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class Nachfragestand:
    """Was für eine Akte ansteht – ohne etwas zu verändern."""

    akte_id: str
    aktenzeichen: str = ""
    bezeichnung: str = ""
    zuletzt_benutzt_am: datetime | None = None
    faellig_am: datetime | None = None
    faellig: bool = False
    monate: int = 12
    weiterfuehrungen: int = 0
    nicht_mehr_laufend_seit: datetime | None = None
    loeschung_vorgesehen_am: datetime | None = None

    def als_dict(self) -> dict:
        return {
            "akte_id": self.akte_id, "aktenzeichen": self.aktenzeichen,
            "bezeichnung": self.bezeichnung,
            "zuletzt_benutzt_am": self.zuletzt_benutzt_am,
            "faellig_am": self.faellig_am, "faellig": self.faellig,
            "monate": self.monate, "weiterfuehrungen": self.weiterfuehrungen,
            "nicht_mehr_laufend_seit": self.nicht_mehr_laufend_seit,
            "loeschung_vorgesehen_am": self.loeschung_vorgesehen_am,
            "frage": FRAGE,
        }


#: Der Wortlaut steht hier und nicht in der Oberfläche: Er ist der Vorgang.
FRAGE = "Läuft die Akte noch?"


class Aufbewahrungsdienst:
    def __init__(self, gedaechtnis: Gedaechtnisdienst, berechtigungen: Berechtigungen,
                 einstellungen: Einstellungen) -> None:
        self._gedaechtnis = gedaechtnis
        self._berechtigungen = berechtigungen
        self._e = einstellungen

    @property
    def monate(self) -> int:
        return self._e.gedaechtnis_nachfrage_monate

    def _frist(self) -> timedelta:
        return timedelta(days=self.monate * TAGE_JE_MONAT)

    # ── Lesen ──────────────────────────────────────────────────────────────

    def stand(self, identitaet: Identitaet, akte_id: str) -> Nachfragestand:
        """Was ansteht – und niemals ein Grund, die Akte nicht zu öffnen.

        Ein Gedächtnis, das sich nicht lesen lässt, hält hier nichts auf.
        Dieselbe Regel wie in `Gedaechtnisdienst.bei_eroeffnen`, und aus
        demselben Anlass: Am 13.10.2026 blieb eine Akte zu, weil ein
        misslungener Lesevorgang nach oben durchschlug. Ohne lesbaren Stand
        gibt es keine fällige Frage — die ungefährliche Richtung.
        """
        self._berechtigungen.pruefen(identitaet, akte_id)
        try:
            g = self._gedaechtnis.lesen(akte_id)
        except GedaechtnisFehler:
            ereignis(_log, "stand_nicht_gelesen", akte=akte_id)
            return Nachfragestand(akte_id=akte_id, monate=self.monate)
        if g is None:
            return Nachfragestand(akte_id=akte_id, monate=self.monate)
        return self._stand(g)

    def _stand(self, g: Aktengedaechtnis) -> Nachfragestand:
        faellig_am = self._faellig_am(g)
        return Nachfragestand(
            akte_id=g.akte_id, aktenzeichen=g.aktenzeichen, bezeichnung=g.bezeichnung,
            zuletzt_benutzt_am=g.zuletzt_benutzt_am,
            faellig_am=faellig_am,
            # Eine Akte, zu der schon "Nein" gesagt wurde, wird nicht noch
            # einmal gefragt - sie wartet auf den Abschluss.
            faellig=bool(faellig_am and faellig_am <= _jetzt()
                         and g.nicht_mehr_laufend_seit is None),
            monate=self.monate,
            weiterfuehrungen=len(g.weiterfuehrungen),
            nicht_mehr_laufend_seit=g.nicht_mehr_laufend_seit,
            loeschung_vorgesehen_am=g.loeschung_vorgesehen_am,
        )

    def _faellig_am(self, g: Aktengedaechtnis) -> datetime | None:
        """Wann gefragt wird – aus dem gespeicherten Termin oder aus der Nutzung.

        Der gespeicherte Termin hat Vorrang: Er trägt die Antwort „Ja" und darf
        nicht dadurch verfallen, dass jemand die Akte danach einmal geöffnet
        hat. Fehlt er — bei allen Arbeitskopien aus der Zeit vor dem
        15.10.2026 —, wird er aus der letzten Nutzung gerechnet.
        """
        if g.nachfrage_faellig_am is not None:
            return g.nachfrage_faellig_am
        if g.zuletzt_benutzt_am is None:
            return None
        return g.zuletzt_benutzt_am + self._frist()

    def faellige(self, identitaet: Identitaet) -> list[Nachfragestand]:
        """Alle Akten, zu denen die Frage offen ist – die der Nutzer sehen darf."""
        if not self._gedaechtnis.aktiv:
            return []
        aus: list[Nachfragestand] = []
        try:
            alle = self._gedaechtnis.auflisten()
        except GedaechtnisFehler:
            ereignis(_log, "liste_nicht_gelesen")
            return []
        for g in alle:
            try:
                self._berechtigungen.pruefen(identitaet, g.akte_id)
            except PermissionError:
                continue
            stand = self._stand(g)
            if stand.faellig:
                aus.append(stand)
        aus.sort(key=lambda s: s.faellig_am or _jetzt())
        return aus

    # ── Schreiben ──────────────────────────────────────────────────────────

    def benutzt(self, akte_id: str) -> None:
        """Festhalten, dass in dieser Akte gearbeitet wurde.

        Setzt **nur** den Zeitpunkt der Nutzung, nicht den Fragetermin: Wer
        eine Akte öffnet, beantwortet damit keine Frage. Der Termin wandert
        erst mit einer ausdrücklichen Antwort.
        """
        if not self._gedaechtnis.aktiv:
            return
        try:
            g = self._gedaechtnis.lesen(akte_id)
        except GedaechtnisFehler:
            return
        if g is None:
            return
        g.zuletzt_benutzt_am = _jetzt()
        if g.nachfrage_faellig_am is None:
            g.nachfrage_faellig_am = g.zuletzt_benutzt_am + self._frist()
        try:
            self._gedaechtnis.ablegen(g)
        except GedaechtnisFehler:
            # Eine misslungene Notiz darf das Arbeiten nicht aufhalten.
            ereignis(_log, "nutzung_nicht_vermerkt", akte=akte_id)

    def beantworten(self, identitaet: Identitaet, akte_id: str,
                    laeuft_noch: bool) -> Nachfragestand:
        """Die Antwort auf die Frage – und was daraus folgt."""
        self._berechtigungen.pruefen(identitaet, akte_id)
        g = self._gedaechtnis.lesen(akte_id)
        if g is None:
            raise AufbewahrungFehler("Zu dieser Akte liegt keine Arbeitskopie vor.")
        jetzt = _jetzt()
        if laeuft_noch:
            g.nachfrage_faellig_am = jetzt + self._frist()
            g.nicht_mehr_laufend_seit = None
            g.loeschung_vorgesehen_am = None
            g.weiterfuehrungen.append(Weiterfuehrung(am=jetzt, nutzer_id=identitaet.nutzer_id))
            ereignis(_log, "akte_laeuft_weiter", akte=akte_id,
                     monate=self.monate, bisher=len(g.weiterfuehrungen))
        else:
            g.nicht_mehr_laufend_seit = jetzt
            g.nachfrage_faellig_am = None
            g.loeschung_vorgesehen_am = jetzt + timedelta(
                days=self._e.gedaechtnis_uebergangsfrist_tage)
            ereignis(_log, "akte_laeuft_nicht_mehr", akte=akte_id,
                     frist_tage=self._e.gedaechtnis_uebergangsfrist_tage)
        self._gedaechtnis.ablegen(g)
        return self._stand(g)
