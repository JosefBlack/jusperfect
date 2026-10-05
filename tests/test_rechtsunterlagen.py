"""Die Rechtsunterlagen dürfen nicht hinter dem Programm zurückbleiben.

Aufgabe 3 aus `MORGEN.md`: DSFA, Datenschutzhinweise, Mandatsbedingungen. Die
Entwürfe stehen; die Bewertung macht die Kanzlei.

**Warum das geprüft gehört und nicht nur geschrieben.** Am 05.10.2026 stand in
`VERARBEITUNGSVERZEICHNIS-ENTWURF.md` noch „Aktengedächtnis abgeschaltet" und
in `DSFA-ANGABEN.md` „eingerichtet, eingeschaltet nicht" — da lief es bereits
und hatte eine echte Akte mit 55 Dokumenten dauerhaft abgelegt. Eine
Datenschutzunterlage, die einen Zustand beschreibt, den es nicht mehr gibt, ist
schlimmer als keine: Sie sieht aus wie eine Prüfung und ist eine Behauptung.

Geprüft wird deshalb genau das, was mechanisch zu prüfen ist — der Abgleich
zwischen dem, was die Startdatei einschaltet, und dem, was die Unterlagen davon
sagen. Alles Übrige ist Bewertung und steht als `[KANZLEI n]` offen; auch das
wird gezählt, damit eine Stelle nicht stillschweigend verschwindet.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
DSFA = WURZEL / "DSFA-ENTWURF.md"
HINWEISE = WURZEL / "DATENSCHUTZHINWEISE-ENTWURF.md"
VERZEICHNIS = WURZEL / "VERARBEITUNGSVERZEICHNIS-ENTWURF.md"
ANGABEN = WURZEL / "DSFA-ANGABEN.md"
START = WURZEL / "START-JURNODES.bat"

ALLE = (DSFA, HINWEISE, VERZEICHNIS, ANGABEN)


@pytest.fixture(scope="module")
def startdatei() -> str:
    return START.read_bytes().decode("cp1252")


def _offene_stellen(datei: Path) -> list[int]:
    text = datei.read_text(encoding="utf-8")
    return sorted({int(n) for n in re.findall(r"\[KANZLEI (\d+)\]", text)})


@pytest.mark.parametrize("datei", ALLE, ids=lambda p: p.name)
def test_die_unterlage_liegt_im_programmordner(datei: Path) -> None:
    assert datei.is_file(), f"{datei.name} fehlt"


@pytest.mark.parametrize("datei", ALLE, ids=lambda p: p.name)
def test_sie_sagt_dass_sie_keine_rechtsberatung_ist(datei: Path) -> None:
    """Die Entwicklung kann sagen, was das Programm tut – nicht, ob es zulässig
    ist. Das muss in jeder dieser Dateien stehen."""
    text = datei.read_text(encoding="utf-8")
    assert "keine Rechtsberatung" in text or "Das ist nicht die DSFA" in text


@pytest.mark.parametrize("datei", ALLE, ids=lambda p: p.name)
def test_jede_genannte_unterlage_gibt_es_auch(datei: Path) -> None:
    """Ein Verweis ins Leere kostet erst Zeit und dann Vertrauen."""
    genannt = sorted(set(re.findall(r"`([A-ZÄÖÜ][A-ZÄÖÜa-z0-9/._-]*\.md)`",
                                    datei.read_text(encoding="utf-8"))))
    fehlend = [name for name in genannt if not (WURZEL / name).is_file()]
    assert not fehlend, f"{datei.name} verweist auf Dateien, die es nicht gibt: {fehlend}"


class TestDieOffenenStellenSindGezaehlt:
    """Eine Stelle, die stillschweigend verschwindet, gilt als erledigt."""

    def test_die_dsfa_zaehlt_ihre_eigenen_stellen_richtig(self) -> None:
        """Die Zahl im Text und die Zahl der Marken müssen übereinstimmen.

        Geprüft wird nicht die Zahl, sondern ihre Übereinstimmung — sonst
        hätte jede neue offene Stelle diesen Test zum Fehler gemacht statt
        die fehlende Marke.

        **Gezählt werden alle Stellen, auch die entschiedenen.** Nr. 18 ist am
        05.10.2026 entschieden worden und bleibt durchgestrichen stehen: Eine
        Stelle, die verschwindet, sieht aus, als hätte es sie nie gegeben, und
        die Nummern der übrigen verschöben sich.
        """
        worte = {17: "siebzehn", 18: "achtzehn", 19: "neunzehn", 20: "zwanzig",
                 21: "einundzwanzig", 22: "zweiundzwanzig"}
        stellen = _offene_stellen(DSFA)
        assert stellen == list(range(1, len(stellen) + 1)), stellen
        text = DSFA.read_text(encoding="utf-8")
        assert f"**{worte[len(stellen)]}**" in text, len(stellen)
        assert f"Die {worte[len(stellen)]} Stellen für die Kanzlei" in text

    def test_eine_entschiedene_stelle_bleibt_stehen_und_sagt_wann(self) -> None:
        """Regel der Kanzlei: durchgestrichen, mit Datum und Grund – nie
        gelöscht."""
        text = DSFA.read_text(encoding="utf-8")
        assert "~~**[KANZLEI 18]**" in text
        assert "Entschieden am 05.10.2026" in text

    def test_die_hinweise_nennen_neun_und_haben_neun(self) -> None:
        assert _offene_stellen(HINWEISE) == list(range(1, 10))
        assert "**neun**" in HINWEISE.read_text(encoding="utf-8")

    def test_die_dsfa_fuehrt_jede_stelle_in_ihrer_schlussliste(self) -> None:
        """Eine Stelle, die nur im Text steht, wird beim Abarbeiten übersehen."""
        text = DSFA.read_text(encoding="utf-8")
        tabelle = re.split(r"## 8\. Die \w+ Stellen für die Kanzlei", text)[1]
        # Auch die durchgestrichene Nummer zaehlt: Nr. 18 ist entschieden und
        # bleibt in der Liste stehen (Regel der Kanzlei).
        gelistet = sorted({int(n) for n in re.findall(r"^\| ~?~?(\d+)~?~? \|", tabelle, re.M)})
        assert gelistet == _offene_stellen(DSFA), (gelistet, _offene_stellen(DSFA))


class TestDieUnterlagenPassenZumProgramm:
    """Der Abgleich, den am 05.10.2026 niemand gemacht hatte."""

    def test_das_aktengedaechtnis_laeuft_also_sagen_sie_das_auch(
        self, startdatei: str
    ) -> None:
        laeuft = re.search(r"^set JUSPERFECT_GEDAECHTNIS=(\w+)",
                           startdatei, re.M).group(1) != "aus"
        assert laeuft, ("Diese Prüfung geht vom eingeschalteten Gedächtnis aus. "
                        "Ist es abgeschaltet worden, gehören die Unterlagen "
                        "ebenfalls geändert – und diese Prüfung mit.")
        for datei in (VERZEICHNIS, ANGABEN):
            text = datei.read_text(encoding="utf-8")
            assert "noch nicht eingeschaltet" not in text, datei.name
            assert "noch nicht in Betrieb" not in text, datei.name

    def test_die_texterkennung_laeuft_also_steht_sie_in_der_dsfa(
        self, startdatei: str
    ) -> None:
        """Sie ist eine zweite Übermittlung an AWS und erweitert den Umfang der
        Art.-9-Verarbeitung – gescannte Arztunterlagen."""
        an = re.search(r"^set JUSPERFECT_OCR=(\w+)", startdatei, re.M).group(1) != "aus"
        assert an
        for datei in (DSFA, VERZEICHNIS, ANGABEN):
            assert "Textract" in datei.read_text(encoding="utf-8"), datei.name

    def test_der_korrespondenzordner_ist_aus_und_der_befund_steht_drin(
        self, startdatei: str
    ) -> None:
        """Der Befund vom 05.10.2026 ist ein Risiko für das Mandantengeheimnis
        und keine Programmfrage – er gehört in die Unterlage, nicht nur in
        MORGEN.md."""
        assert not re.search(r"^set JUSPERFECT_KORRESPONDENZ=", startdatei, re.M), \
            "Der Korrespondenzordner wird wieder gelesen – dann ist R1 neu zu bewerten."
        for datei in (DSFA, VERZEICHNIS, ANGABEN):
            assert "Korrespondenzordner" in datei.read_text(encoding="utf-8"), datei.name

    def test_die_gezielte_loeschung_steht_in_dsfa_und_hinweisen(self) -> None:
        """Sie ist seit dem 05.10.2026 da und bedient Art. 16 und 17 – eine
        Unterlage, die sie verschweigt, verspricht weniger als das Programm
        hält."""
        assert "Art. 16 und 17" in DSFA.read_text(encoding="utf-8")
        hinweise = HINWEISE.read_text(encoding="utf-8")
        assert "gezielt daraus entfernen" in hinweise


class TestEsStehtNichtsDarinWasNichtHineingehoert:
    @pytest.mark.parametrize("datei", ALLE, ids=lambda p: p.name)
    def test_keine_zugangsdaten(self, datei: Path) -> None:
        text = datei.read_text(encoding="utf-8")
        for muster in (r"AKIA[0-9A-Z]{16}", r"aws_secret_access_key",
                       r"X-Auth-Key\s*[:=]\s*\S"):
            assert not re.search(muster, text), (datei.name, muster)

    @pytest.mark.parametrize("datei", (DSFA, HINWEISE), ids=lambda p: p.name)
    def test_keine_echten_aktenzeichen_ausser_dem_einen_befund(self, datei: Path) -> None:
        """X-100-2026 darf vorkommen: Der Befund vom 05.10.2026 ist ohne die
        Akte nicht zu beschreiben, und sie steht bereits in MORGEN.md. Andere
        nicht."""
        gefunden = set(re.findall(r"\bD-\d{3}-\d{4}\b", datei.read_text(encoding="utf-8")))
        assert gefunden <= {"X-100-2026"}, gefunden
