"""Die Zugriffsrichtlinie nennt Regionen beim Namen, nicht nach ihrem Vorsatz.

**Aus der Kanzlei am 05.10.2026: „Zürich ist eu-central-2 und nicht
eu-central-1."** Bis dahin sperrte die Anweisung `NurEuropa` jeden
Bedrock-Aufruf außerhalb von `eu-*`.

Der Vorsatz `eu-` ist eine Namenskonvention von AWS und keine Aussage über die
Europäische Union. Zwei Regionen tragen ihn und liegen außerhalb der EU und des
EWR — `eu-central-2` (Zürich, Schweiz) und `eu-west-2` (London, Vereinigtes
Königreich). Beide hätten die Sperre passiert.

`infra/iam-nur-claude.json` ist eine geschützte Datei; sie wurde am 05.10.2026
auf ausdrückliche Anweisung der Kanzlei geändert. Diese Prüfungen halten das
Ergebnis fest — **nicht**, weil die Datei sich von selbst ändert, sondern weil
ein späterer Handgriff daran sonst unbemerkt bliebe. Eine Richtlinie ist die
letzte Grenze; was von ihr übrig ist, soll nachzählbar sein.

**Was diese Datei nicht prüft:** wohin das Inferenzprofil intern verteilt. Das
entscheidet AWS, und `aws:RequestedRegion` betrifft die Region, an die der
Aufruf geht.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from jusperfect.config import EU_EWR_REGIONEN

WURZEL = Path(__file__).resolve().parent.parent
DATEI = WURZEL / "infra" / "iam-nur-claude.json"
BESCHREIBUNG = WURZEL / "infra" / "IAM.md"

#: Was wie eine EU-Region aussieht und keine ist.
DRITTLAENDER = ("eu-central-2", "eu-west-2")


@pytest.fixture(scope="module")
def roh() -> str:
    return DATEI.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def richtlinie(roh: str) -> dict:
    return json.loads(roh)


def _anweisung(richtlinie: dict, sid: str) -> dict:
    treffer = [s for s in richtlinie["Statement"] if s.get("Sid") == sid]
    assert len(treffer) == 1, f"{sid} kommt {len(treffer)}-mal vor"
    return treffer[0]


class TestKeinVorsatzMehr:
    def test_nirgends_steht_noch_eu_stern(self, roh: str) -> None:
        """Der eigentliche Punkt. Ein einziges übriges `eu-*` wäre eine
        Stelle, auf die sich jemand verlassen könnte."""
        assert "eu-*" not in roh

    @pytest.mark.parametrize("region", DRITTLAENDER)
    def test_kein_drittland_wird_genannt(self, roh: str, region: str) -> None:
        assert region not in roh


class TestDieSperreNenntDieRegionen:
    def test_sie_prueft_auf_gleichheit_nicht_auf_aehnlichkeit(
        self, richtlinie: dict
    ) -> None:
        bedingung = _anweisung(richtlinie, "NurEuUndEwr")["Condition"]
        assert "StringNotEquals" in bedingung
        assert "StringNotLike" not in bedingung

    def test_sie_nennt_genau_die_sechs_aus_dem_programm(self, richtlinie: dict) -> None:
        """Richtlinie und Programm dürfen nicht auseinanderlaufen: Sonst
        erlaubt das eine, was das andere verbietet, und niemand merkt es."""
        erlaubt = _anweisung(richtlinie, "NurEuUndEwr")["Condition"][
            "StringNotEquals"]["aws:RequestedRegion"]
        assert sorted(erlaubt) == sorted(EU_EWR_REGIONEN)

    def test_sie_ist_ein_verbot_und_keine_erlaubnis(self, richtlinie: dict) -> None:
        """Ein Deny wiegt in AWS stärker als jedes Allow – auch stärker als
        eines aus einer Richtlinie, die jemand später anhängt."""
        anweisung = _anweisung(richtlinie, "NurEuUndEwr")
        assert anweisung["Effect"] == "Deny"
        assert anweisung["Action"] == "bedrock:*"
        assert anweisung["Resource"] == "*"


class TestDasSchutzgelaenderHatBeideRessourcenarten:
    """Gemessen am 23.09.2026: Mit `guardrail/*` allein blieb die Ablehnung
    bestehen, mit beiden lief es. Bis zum 05.10.2026 stand nur die erste in
    dieser Datei."""

    def test_guardrail_und_guardrail_profile(self, richtlinie: dict) -> None:
        ressourcen = _anweisung(richtlinie, "SchutzgelaenderAnwenden")["Resource"]
        assert any(":guardrail/*" in r for r in ressourcen)
        assert any(":guardrail-profile/*" in r for r in ressourcen)

    @pytest.mark.parametrize("region", EU_EWR_REGIONEN)
    def test_jede_erlaubte_region_fuer_beide(self, richtlinie: dict, region: str) -> None:
        ressourcen = _anweisung(richtlinie, "SchutzgelaenderAnwenden")["Resource"]
        for art in ("guardrail/*", "guardrail-profile/*"):
            assert f"arn:aws:bedrock:{region}:*:{art}" in ressourcen

    def test_keine_kontonummer_von_hand(self, richtlinie: dict) -> None:
        """Der Platzhalter hat am 02.10.2026 eine rote Zeile erzeugt. Hier wird
        er nicht gebraucht – die Richtlinie gilt ohnehin nur im eigenen Konto."""
        ressourcen = _anweisung(richtlinie, "SchutzgelaenderAnwenden")["Resource"]
        assert not any("AWS-KONTONUMMER" in r for r in ressourcen)


class TestDieModellanweisungen:
    @pytest.mark.parametrize("sid,feld", [("ClaudeAufrufen", "Resource"),
                                          ("KeinAnderesModell", "NotResource")])
    def test_jede_erlaubte_region_steht_ausgeschrieben(
        self, richtlinie: dict, sid: str, feld: str
    ) -> None:
        eintraege = _anweisung(richtlinie, sid)[feld]
        for region in EU_EWR_REGIONEN:
            assert f"arn:aws:bedrock:{region}::foundation-model/anthropic.claude-*" \
                in eintraege

    @pytest.mark.parametrize("sid,feld", [("ClaudeAufrufen", "Resource"),
                                          ("KeinAnderesModell", "NotResource")])
    def test_das_inferenzprofil_bleibt_eine_einzige_zeile(
        self, richtlinie: dict, sid: str, feld: str
    ) -> None:
        """Dort stand nie `eu-*`, und jede weitere Zeile wäre eine weitere
        Stelle, an der die Kontonummer von Hand einzutragen ist."""
        profile = [r for r in _anweisung(richtlinie, sid)[feld]
                   if "inference-profile" in r]
        assert len(profile) == 1
        assert profile[0].startswith("arn:aws:bedrock:*:AWS-KONTONUMMER:")

    def test_die_beiden_listen_sind_gleich(self, richtlinie: dict) -> None:
        """`KeinAnderesModell` verbietet alles, was `ClaudeAufrufen` nicht
        erlaubt. Laufen die Listen auseinander, sperrt die Richtlinie etwas
        aus, das sie zugleich erlaubt – und der Fehler zeigt sich erst mitten
        in einer Akte."""
        assert (sorted(_anweisung(richtlinie, "ClaudeAufrufen")["Resource"])
                == sorted(_anweisung(richtlinie, "KeinAnderesModell")["NotResource"]))


class TestSieLaesstSichInAwsEinsetzen:
    def test_sie_bleibt_unter_der_laengengrenze(self, roh: str) -> None:
        """Eine verwaltete Richtlinie darf 6144 Zeichen haben. Jede Region
        ausgeschrieben kostet Platz; die Grenze ist kein theoretischer Wert."""
        assert len(roh) <= 6144, len(roh)

    def test_sie_traegt_keine_kommentare(self, roh: str) -> None:
        """Die Grammatik der Richtlinien kennt kein Kommentarfeld. Die
        Begründungen stehen in infra/IAM.md."""
        assert "//" not in roh
        assert '"Comment"' not in roh

    def test_jede_anweisung_hat_eine_sid(self, richtlinie: dict) -> None:
        for anweisung in richtlinie["Statement"]:
            assert anweisung.get("Sid"), anweisung


class TestDieBeschreibungSagtDasselbe:
    def test_sie_nennt_die_anweisung_unter_ihrem_neuen_namen(self) -> None:
        text = BESCHREIBUNG.read_text(encoding="utf-8")
        assert "NurEuUndEwr" in text

    def test_sie_erklaert_warum_der_vorsatz_nicht_genuegt(self) -> None:
        text = BESCHREIBUNG.read_text(encoding="utf-8")
        assert "Namenskonvention" in text
        for region in DRITTLAENDER:
            assert region in text

    def test_sie_sagt_was_die_aenderung_nicht_leistet(self) -> None:
        """Wohin das Inferenzprofil intern verteilt, entscheidet AWS."""
        text = BESCHREIBUNG.read_text(encoding="utf-8")
        assert "aws:RequestedRegion" in text
        assert re.search(r"intern[^.]*AWS", text)

    def test_die_anzahl_der_anweisungen_stimmt(self, richtlinie: dict) -> None:
        """In der Überschrift steht eine Zahl. Sie ist schon einmal
        stehengeblieben, als eine Anweisung dazukam."""
        text = BESCHREIBUNG.read_text(encoding="utf-8")
        worte = {5: "fünf", 6: "sechs", 7: "sieben", 8: "acht", 9: "neun"}
        erwartet = worte[len(richtlinie["Statement"])]
        assert f"Was die {erwartet} Anweisungen tun" in text
