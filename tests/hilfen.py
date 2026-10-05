"""Gemeinsames für die Tests: Einstellungen, Dienste, Testclient."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from jusperfect.config import Einstellungen
from jusperfect.web import Dienste, app_erstellen

WURZEL = Path(__file__).resolve().parent.parent
TESTAKTEN = WURZEL / "testdaten" / "akten"
NUTZER = WURZEL / "testdaten" / "nutzer.json"


def einstellungen(**extra: str) -> Einstellungen:
    env = {
        "JUSPERFECT_BETRIEBSART": "lokal", "JUSPERFECT_ANBIETER": "demo", "JUSPERFECT_JURNODES_ADAPTER": "fixture",
        "JUSPERFECT_FIXTURE_PFAD": str(TESTAKTEN), "JUSPERFECT_NUTZER_DATEI": str(NUTZER),
    }
    env.update(extra)
    return Einstellungen.aus_umgebung(env)


def dienste(**extra) -> Dienste:
    """Testakten-Adapter ohne Schreiben auf die Platte."""
    from jusperfect.jurnodes.fixture_adapter import FixtureJurNodesAdapter
    from jusperfect.security.approval import Freigabestelle

    e = extra.pop("einstellungen", None) or einstellungen()
    freigabestelle = extra.pop("freigabestelle", None) or Freigabestelle()
    adapter = extra.pop("adapter", None) or FixtureJurNodesAdapter(e.fixture_pfad, freigabestelle, schreibbar=False)
    return Dienste(e, adapter=adapter, freigabestelle=freigabestelle, **extra)


def client(d: Dienste, nutzer: str | None = "ra-weber") -> TestClient:
    kopf = {"X-Jusperfect-Nutzer": nutzer} if nutzer else {}
    return TestClient(app_erstellen(d.einstellungen, d), headers=kopf, raise_server_exceptions=False)
