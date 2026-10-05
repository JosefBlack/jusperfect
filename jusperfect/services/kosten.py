"""Kostenwächter.

Jeder Aufruf wird mit Größenordnungspreisen bewertet und im Sitzungsspeicher
je Monat aufsummiert. Über dem Monatsbudget stoppt die Anwendung selbst;
AWS Budgets (siehe infra/) warnt zusätzlich bei 50, 80 und 100 Prozent des
tatsächlichen Kontostands. Zwei unabhängige Bremsen, weil die zweite erst
mit Verzögerung greift.

Die Preise sind Anthropic-Listenpreise je Million Token als Größenordnung;
Bedrock-Preise in Frankfurt können abweichen und sind in Phase 0 zu prüfen.
"""

from __future__ import annotations

from datetime import datetime, timezone

from jusperfect.domain.models import Kosten, Nutzungseintrag
from jusperfect.providers.base import Nutzung, ProviderAntwort
from jusperfect.security.identitaet import Identitaet
from jusperfect.speicher.base import SitzungsSpeicher

# (Eingabe, Ausgabe) in USD je Million Token
PREISE_USD: dict[str, tuple[float, float]] = {
    "opus-5": (5.00, 25.00),
    "opus-4": (5.00, 25.00),
    "sonnet-5": (2.00, 10.00),
    "sonnet-4": (3.00, 15.00),
    "haiku-4-5": (1.00, 5.00),
    "haiku": (1.00, 5.00),
}
STANDARD_PREIS = (5.00, 25.00)


class BudgetErschoepft(RuntimeError):
    pass


def preis_fuer(modell: str) -> tuple[float, float]:
    m = modell.lower()
    for schluessel, preis in PREISE_USD.items():
        if schluessel in m:
            return preis
    return STANDARD_PREIS


#: Deutscher Fließtext braucht ungefähr so viele Zeichen je Token. Der Wert ist
#: eine Näherung – juristische Texte mit vielen Zahlen, Aktenzeichen und
#: Abkürzungen liegen darunter, also bei mehr Token. Für eine Schätzung, die vor
#: dem Absenden eine Größenordnung nennen soll, reicht das; sie wird bewusst
#: eher zu hoch als zu niedrig angesetzt.
ZEICHEN_JE_TOKEN = 3.5

#: Was eine Antwort typischerweise lang wird. Nur für die Schätzung.
ANTWORT_TOKEN_SCHAETZUNG = 700


def schaetzung(modell: str, zeichen: int, kurs: float,
               ausgabe_tokens: int = ANTWORT_TOKEN_SCHAETZUNG) -> dict[str, float | int]:
    """Was ein Aufruf mit diesem Material ungefähr kostet – vor dem Absenden.

    Der Nachweis sagt hinterher, was es gekostet hat. Das hilft beim Prüfen,
    aber nicht beim Entscheiden: Wer wissen will, ob er noch drei Dokumente
    hinüberzieht, braucht die Zahl vorher.

    Zwei Beträge, weil sie weit auseinanderliegen: Die erste Frage zu einer
    Akte zahlt das Material voll, jede weitere nur den Cache-Preis. Genau das
    ist der Grund, an einer Akte zu bleiben, statt zwischen Akten zu springen.
    """
    eingabe_preis, ausgabe_preis = preis_fuer(modell)
    eingabe_tokens = int(max(0, zeichen) / ZEICHEN_JE_TOKEN)
    ausgabe_usd = ausgabe_tokens * ausgabe_preis / 1_000_000
    voll_usd = eingabe_tokens * eingabe_preis / 1_000_000 + ausgabe_usd
    # Gelesener Cache kostet ein Zehntel der Eingabe (siehe betrag_eur).
    gecacht_usd = eingabe_tokens * eingabe_preis * 0.1 / 1_000_000 + ausgabe_usd
    return {
        "zeichen": max(0, zeichen),
        "eingabe_tokens": eingabe_tokens,
        "erste_frage_eur": round(voll_usd * kurs, 4),
        "weitere_frage_eur": round(gecacht_usd * kurs, 4),
    }


def betrag_eur(modell: str, nutzung: Nutzung, kurs: float) -> float:
    eingabe, ausgabe = preis_fuer(modell)
    usd = (
        nutzung.eingabe_tokens * eingabe
        + nutzung.cache_lese_tokens * eingabe * 0.1
        + nutzung.cache_schreib_tokens * eingabe * 1.25
        + nutzung.ausgabe_tokens * ausgabe
    ) / 1_000_000
    return round(usd * kurs, 6)


class Kostenwaechter:
    def __init__(self, speicher: SitzungsSpeicher, monatsbudget_eur: float, kurs: float) -> None:
        self._speicher = speicher
        self.monatsbudget_eur = monatsbudget_eur
        self._kurs = kurs

    @staticmethod
    def _monat() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def stand(self) -> dict[str, float | str]:
        verbraucht = self._speicher.nutzung_monat(self._monat())
        return {"monat": self._monat(), "verbraucht_eur": round(verbraucht, 2),
                "budget_eur": self.monatsbudget_eur,
                "anteil": round(verbraucht / self.monatsbudget_eur, 3) if self.monatsbudget_eur else 0.0}

    def schaetzen(self, modell: str, zeichen: int) -> dict[str, float | int]:
        """Schätzung für diesen Umfang, dazu was vom Budget noch übrig ist."""
        werte = dict(schaetzung(modell, zeichen, self._kurs))
        stand = self.stand()
        werte["budget_rest_eur"] = round(
            max(0.0, self.monatsbudget_eur - float(stand["verbraucht_eur"])), 2
        )
        return werte

    def pruefen(self) -> None:
        verbraucht = self._speicher.nutzung_monat(self._monat())
        if verbraucht >= self.monatsbudget_eur:
            raise BudgetErschoepft(
                f"Das Monatsbudget von {self.monatsbudget_eur:.2f} EUR ist erreicht "
                f"({verbraucht:.2f} EUR). Weitere KI-Aufrufe sind bis zur Freigabe gesperrt."
            )

    def verbuchen(self, identitaet: Identitaet, akte_id: str, funktion: str, antwort: ProviderAntwort, *,
                  sitzung_id: str = "", material_kennung: str = "", aufgabe_kennung: str = "",
                  passagen: int = 0, antwort_zeichen: int = 0) -> Kosten:
        """Bucht die Kosten und schreibt zugleich den Verarbeitungsnachweis.

        Die Nachweis-Felder sind ohne Inhalte (Kurzkennungen und Umfänge). Sie
        werden vom Ausgang mitgegeben – der einzigen Stelle, die einen Aufruf
        nach draußen führt. Wird ``verbuchen`` ohne sie aufgerufen, bleibt der
        Eintrag ein reiner Kosteneintrag; das hält ältere Aufrufer lauffähig.
        """
        betrag = betrag_eur(antwort.modell, antwort.nutzung, self._kurs)
        eingabe = antwort.nutzung.eingabe_tokens + antwort.nutzung.cache_lese_tokens + antwort.nutzung.cache_schreib_tokens
        self._speicher.nutzung_verbuchen(Nutzungseintrag(
            zeitpunkt=datetime.now(timezone.utc), nutzer_id=identitaet.nutzer_id, akte_id=akte_id,
            funktion=funktion, modell=antwort.modell,
            eingabe_tokens=eingabe, ausgabe_tokens=antwort.nutzung.ausgabe_tokens, betrag_eur=betrag,
            sitzung_id=sitzung_id, material_kennung=material_kennung, aufgabe_kennung=aufgabe_kennung,
            passagen=passagen, antwort_zeichen=antwort_zeichen,
        ))
        return Kosten(eingabe_tokens=eingabe, ausgabe_tokens=antwort.nutzung.ausgabe_tokens, betrag_eur=betrag)

    def nachweis(self, nutzer_id: str, limit: int = 25) -> list[dict]:
        """Die jüngsten Übertragungen dieses Nutzers – neueste zuerst, ohne Inhalte.

        Der Verarbeitungsnachweis beantwortet „was ist wann an welches Modell
        gegangen?". Er ist auf die eigenen Vorgänge beschränkt; ein
        vollständiger Export für die Datenschutzbeauftragte ist ein eigener,
        verwalteter Weg und keine offene Schnittstelle.
        """
        eintraege = self._speicher.nachweis_lesen(limit * 4 if nutzer_id else limit)
        gefiltert = [e for e in eintraege if not nutzer_id or e.nutzer_id == nutzer_id][:limit]
        return [{
            "zeitpunkt": e.zeitpunkt.isoformat(timespec="seconds"),
            "funktion": e.funktion, "akte_id": e.akte_id, "sitzung_id": e.sitzung_id,
            "modell": e.modell, "material_kennung": e.material_kennung, "aufgabe_kennung": e.aufgabe_kennung,
            "passagen": e.passagen, "antwort_zeichen": e.antwort_zeichen,
            "eingabe_tokens": e.eingabe_tokens, "ausgabe_tokens": e.ausgabe_tokens,
            "betrag_eur": round(e.betrag_eur, 4),
        } for e in gefiltert]
