"""Der eine geprüfte Ausgang zum Modell – und der Nachweis darüber.

Aus Perfect Shield übernommen: dort geht jeder Weg nach draußen durch einen
einzigen Übergang, der prüft, den Verlauf serverseitig hält und festhält, was
das Haus verlassen hat. jusperfect braucht dieselbe Bündelung, aus zwei
Gründen:

* **Ein Tor statt vieler Türen.** Bisher rief jeder Dienst den Anbieter selbst
  auf, prüfte selbst das Budget, protokollierte selbst und verbuchte selbst.
  Vier Schritte an vier Stellen – und die stille Gefahr, dass ein künftiger
  Aufruf einen davon vergisst. Hier laufen alle vier an einer Stelle zusammen:
  Formprüfung der Eingabe, Budgetbremse, Aufruf, Nachweis. Wer zum Modell will,
  geht durch den Ausgang; einen zweiten Weg gibt es nicht.

* **Nachweis statt Zusage.** Das Material geht unverschlüsselt in den
  gesicherten Bedrock-Bereich. Gerade deshalb hält der Ausgang für jeden
  Aufruf fest, *dass* und *was* hinausging – als Kurzkennung und Umfang, nie
  als Text (siehe ``Nutzungseintrag``). „Was ist wann an welches Modell
  gegangen?" ist danach beantwortbar, ohne dass sich jemand erinnern muss.

Die Formprüfung ist bewusst streng: Nur Text darf hinaus. Übergäbe ein späterer
Aufrufer versehentlich ein Objekt statt einer Zeichenkette, fiele es hier auf –
nicht erst beim Anbieter, und nicht als unbemerkt mitgesendete Struktur.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from jusperfect.config import Einstellungen
from jusperfect.domain.models import Kosten
from jusperfect.providers.base import LLMProvider, ProviderAntwort, ProviderFehler
from jusperfect.security.identitaet import Identitaet
from jusperfect.security.protokoll import ereignis, kurzkennung, protokoll
from jusperfect.services.kosten import Kostenwaechter

_log = protokoll("ausgang")


@dataclass(frozen=True, slots=True)
class Ausgangskontext:
    """Woher ein Aufruf stammt – für Nachweis und Protokoll, ohne Inhalte."""

    identitaet: Identitaet
    sitzung_id: str
    akte_id: str
    funktion: str
    passagen: int = 0
    detail: str = ""  # kurze Zusatzangabe, z. B. die Entwurfsart


@dataclass(frozen=True, slots=True)
class Durchgang:
    """Das Ergebnis eines Aufrufs: die Antwort und was er gekostet hat."""

    antwort: ProviderAntwort
    kosten: Kosten


class Ausgang:
    """Einziger zulässiger Übergang zu einem externen Modell."""

    def __init__(self, provider: LLMProvider, kosten: Kostenwaechter, einstellungen: Einstellungen) -> None:
        self._provider = provider
        self._kosten = kosten
        self._e = einstellungen

    def fragen(self, kontext: Ausgangskontext, system: str, material: str, aufgabe: str,
               *, modell_id: str | None = None) -> Durchgang:
        self._pruefen(system, material, aufgabe)
        self._kosten.pruefen()
        modell = modell_id or self._e.modell_fuer(kontext.funktion)
        antwort = self._provider.fragen(system, material, aufgabe,
                                        max_tokens=self._e.max_ausgabe_tokens, modell_id=modell)
        return self._abschluss(kontext, material, aufgabe, antwort)

    def fragen_stream(self, kontext: Ausgangskontext, system: str, material: str, aufgabe: str,
                      *, modell_id: str | None = None) -> Iterator[str | Durchgang]:
        """Wie ``fragen``, liefert die Antwort aber Stück für Stück.

        Die Prüfung ist dieselbe und der Nachweis derselbe; nur die Ausgabe
        kommt fortlaufend. Das letzte Stück ist der vollständige ``Durchgang``
        – erst dann stehen Kosten und Nachweis fest.
        """
        self._pruefen(system, material, aufgabe)
        self._kosten.pruefen()
        modell = modell_id or self._e.modell_fuer(kontext.funktion)
        antwort: ProviderAntwort | None = None
        for stueck in self._provider.fragen_stream(system, material, aufgabe,
                                                   max_tokens=self._e.max_ausgabe_tokens, modell_id=modell):
            if isinstance(stueck, str):
                yield stueck
            else:
                antwort = stueck
        if antwort is None:
            raise ProviderFehler("Der Anbieter lieferte keine Antwort.")
        yield self._abschluss(kontext, material, aufgabe, antwort)

    @staticmethod
    def _pruefen(system: str, material: str, aufgabe: str) -> None:
        """Nur Text darf hinaus – sonst nichts."""
        for name, wert in (("System", system), ("Material", material), ("Aufgabe", aufgabe)):
            if not isinstance(wert, str):
                raise TypeError(f"{name} muss Text sein, nicht {type(wert).__name__}.")

    def _abschluss(self, kontext: Ausgangskontext, material: str, aufgabe: str,
                   antwort: ProviderAntwort) -> Durchgang:
        kosten = self._kosten.verbuchen(
            kontext.identitaet, kontext.akte_id, kontext.funktion, antwort,
            sitzung_id=kontext.sitzung_id, material_kennung=kurzkennung(material),
            aufgabe_kennung=kurzkennung(aufgabe), passagen=kontext.passagen,
            antwort_zeichen=len(antwort.text),
        )
        ereignis(_log, "ki_aufruf", sitzung=kontext.sitzung_id, funktion=kontext.funktion,
                 detail=kontext.detail or None, modell=antwort.modell, material=kurzkennung(material),
                 anzahl_passagen=kontext.passagen, eingabe=antwort.nutzung.eingabe_tokens,
                 cache=antwort.nutzung.cache_lese_tokens, ausgabe=antwort.nutzung.ausgabe_tokens)
        return Durchgang(antwort=antwort, kosten=kosten)
