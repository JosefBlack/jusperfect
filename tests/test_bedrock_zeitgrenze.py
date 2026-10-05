"""Die Aktenanalyse darf nicht an botocores Voreinstellung scheitern.

Der Fehler sah in der Kanzlei aus wie ein Netzproblem: Die Analyse lief an und
endete nach ein paar Minuten mit „Failed to fetch". Tatsaechlich hatte
botocore nach 60 Sekunden abgebrochen - so lange wartet es voreingestellt auf
das erste Byte, und die Analyse holt ihre Antwort in einem Stueck, waehrend
die Leitung stumm bleibt. Der Frage-Weg blieb verschont, weil er stroemt; das
machte den Fehler doppelt raetselhaft.

Die Grenze steht deshalb hier fest, samt der Obergrenze: Wer sie
grosszuegiger setzt, verlaengert im Fehlerfall nur das Warten, denn botocore
wiederholt auch nach einem Zeitueberlauf.
"""

from __future__ import annotations

import pytest

from jusperfect.providers import bedrock


def test_lesezeit_ueberschreitet_botocores_voreinstellung_deutlich() -> None:
    # 8000 Token entstehen in etwa drei Minuten; 60 Sekunden reichen nicht.
    assert bedrock.LESEZEIT_SEKUNDEN >= 240


def test_lesezeit_bleibt_im_ertraeglichen_rahmen() -> None:
    # Drei Versuche zu je dieser Zeit sind der schlimmste Fall, den jemand vor
    # einem haengenden Fenster aussitzt.
    assert bedrock.LESEZEIT_SEKUNDEN * 3 <= 20 * 60


def test_client_bekommt_die_zeitgrenze_mitgegeben() -> None:
    """Ohne diesen Test bliebe die Konstante Zierde."""
    boto3 = pytest.importorskip("boto3")
    gesehen: dict[str, object] = {}

    def merken(dienst: str, **kwargs: object) -> str:
        gesehen.update(kwargs, dienst=dienst)
        return "unwichtig"

    echt = boto3.client
    boto3.client = merken  # type: ignore[assignment]
    try:
        bedrock._client_bauen("eu-central-1")
    finally:
        boto3.client = echt  # type: ignore[assignment]

    assert gesehen["dienst"] == "bedrock-runtime"
    assert gesehen["region_name"] == "eu-central-1"
    config = gesehen["config"]
    assert config.read_timeout == bedrock.LESEZEIT_SEKUNDEN
    assert config.connect_timeout == bedrock.VERBINDUNGSZEIT_SEKUNDEN
    # Die Wiederholungen sind fuer ThrottlingException da, nicht fuer den
    # Zeitueberlauf - deshalb wenige.
    assert config.retries["max_attempts"] == 3
