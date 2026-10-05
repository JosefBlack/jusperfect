"""„eu-" ist eine Namenskonvention von AWS, keine Aussage über die EU.

**Aus der Kanzlei am 05.10.2026: „Zürich ist eu-central-2 und nicht
eu-central-1."**

Das stimmt — und es deckt einen Fehler auf, der bis dahin in der Prüfung
stand. Geprüft wurde auf den Vorsatz `eu-`:

    if not self.aws_region.startswith("eu-"):

`eu-central-2` fängt mit `eu-` an. Die Prüfung hätte Zürich durchgelassen, und
dasselbe gilt für `eu-west-2` — London. Beide liegen außerhalb der EU und des
EWR.

Für eine Kanzlei, deren Unterlage „Übermittlung in Drittländer: keine" sagt,
ist das der Unterschied zwischen einem Satz, der stimmt, und einem, der sich
auf eine Buchstabenfolge stützt.

**Was diese Datei nicht prüft:** wohin das EU-Inferenzprofil und das
Geländerprofil `eu.guardrail.v1:0` einen Aufruf intern verteilen. Das
entscheidet AWS, nicht diese Liste — und es ist weiterhin beim AWS-Support zu
erfragen (`DSFA-ANGABEN.md`, „Noch nicht festgestellt").
"""

from __future__ import annotations

import pytest

from jusperfect.config import EU_EWR_REGIONEN, Einstellungen, KonfigurationsFehler

GRUND = {"JUSPERFECT_ANBIETER": "demo", "JUSPERFECT_JURNODES_ADAPTER": "fixture"}

#: Regionen, die mit „eu-" anfangen und trotzdem Drittländer sind.
AUSSERHALB = {
    "eu-central-2": "Schweiz",
    "eu-west-2": "Vereinigtes Königreich",
}


def _mit(region: str) -> Einstellungen:
    return Einstellungen.aus_umgebung({**GRUND, "JUSPERFECT_AWS_REGION": region})


class TestDerVorsatzGenuegtNicht:
    @pytest.mark.parametrize("region", sorted(AUSSERHALB))
    def test_eine_scheinbare_eu_region_wird_abgewiesen(self, region: str) -> None:
        """Der eigentliche Fund. Vorher ging beides durch."""
        with pytest.raises(KonfigurationsFehler):
            _mit(region)

    @pytest.mark.parametrize("region", sorted(AUSSERHALB))
    def test_und_die_meldung_sagt_warum_nicht_nur_dass(self, region: str) -> None:
        """„nicht erlaubt" hilft weniger als „das liegt in der Schweiz"."""
        with pytest.raises(KonfigurationsFehler) as fehler:
            _mit(region)
        assert AUSSERHALB[region] in str(fehler.value)
        assert "außerhalb der EU und des EWR" in str(fehler.value)

    def test_eine_region_ausserhalb_europas_ebenfalls(self) -> None:
        with pytest.raises(KonfigurationsFehler) as fehler:
            _mit("us-east-1")
        assert "keine EU- oder EWR-Region" in str(fehler.value)

    def test_die_meldung_sagt_auch_wo_die_liste_steht(self) -> None:
        """Eröffnet AWS eine neue EU-Region, wird sie hier abgewiesen, bis sie
        eingetragen ist. Das ist die sichere Richtung — aber nur, wenn
        dasteht, wo man sie einträgt."""
        with pytest.raises(KonfigurationsFehler) as fehler:
            _mit("eu-irgendwo-9")
        assert "EU_EWR_REGIONEN" in str(fehler.value)


class TestDieListeSelbst:
    @pytest.mark.parametrize("region", EU_EWR_REGIONEN)
    def test_jede_eingetragene_region_wird_angenommen(self, region: str) -> None:
        assert _mit(region).aws_region == region

    def test_frankfurt_ist_dabei(self) -> None:
        """Die Region der Kanzlei. Fiele sie heraus, startete nichts mehr."""
        assert "eu-central-1" in EU_EWR_REGIONEN

    def test_kein_drittland_steht_darin(self) -> None:
        assert not set(EU_EWR_REGIONEN) & set(AUSSERHALB)

    def test_sie_ist_aufgeschrieben_und_nicht_abgeleitet(self) -> None:
        """Genau das Ableiten war der Fehler: Jede Region trägt den Vorsatz
        „eu-", und zwei davon liegen außerhalb der EU."""
        assert all(r.startswith("eu-") for r in EU_EWR_REGIONEN)
        assert all(r.startswith("eu-") for r in AUSSERHALB)
        # Wäre der Vorsatz der Maßstab, wären die Drittländer zulässig.
        assert set(AUSSERHALB) - set(EU_EWR_REGIONEN) == set(AUSSERHALB)


class TestDasProfilBleibtDavonUnberuehrt:
    def test_der_vorsatz_eu_wird_weiter_gesetzt(self) -> None:
        """Die Modellkennung bekommt in jeder europäischen Region den Vorsatz
        `eu.` — daran ändert die engere Liste nichts. Was das Profil intern
        tut, entscheidet AWS; dazu steht die offene Frage in
        `DSFA-ANGABEN.md`."""
        e = Einstellungen.aus_umgebung({
            **GRUND, "JUSPERFECT_AWS_REGION": "eu-central-1",
            "JUSPERFECT_MODELL_ID": "anthropic.claude-opus-4-6-v1"})
        assert e.modell_id == "eu.anthropic.claude-opus-4-6-v1"
