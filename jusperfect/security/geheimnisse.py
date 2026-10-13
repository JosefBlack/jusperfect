"""Zugangsdaten für jurnodes.

In AWS liegt das Token im Secrets Manager; die Lambda-Rolle darf genau dieses
eine Geheimnis lesen. Lokal kommt es aus einer Umgebungsvariablen, deren Name
konfigurierbar ist. In beiden Fällen: nie im Code, nie im Protokoll.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

from jusperfect.config import Einstellungen, KonfigurationsFehler


def jurnodes_token(einstellungen: Einstellungen, env: Mapping[str, str] | None = None,
                   secrets_client: Any | None = None) -> str:
    env = os.environ if env is None else env
    if einstellungen.jurnodes_secret_arn:
        if secrets_client is None:
            import boto3

            secrets_client = boto3.client("secretsmanager", region_name=einstellungen.aws_region)
        antwort = secrets_client.get_secret_value(SecretId=einstellungen.jurnodes_secret_arn)
        wert = antwort.get("SecretString", "")
        try:
            daten = json.loads(wert)
            wert = str(daten.get("token", daten.get("api_token", "")))
        except (json.JSONDecodeError, AttributeError):
            pass
        if not wert:
            raise KonfigurationsFehler("Das jurnodes-Geheimnis im Secrets Manager ist leer.")
        return wert
    token = env.get(einstellungen.jurnodes_token_var, "")
    if not token:
        raise KonfigurationsFehler(
            f"Das jurnodes-Token fehlt: Umgebungsvariable {einstellungen.jurnodes_token_var} ist leer."
        )
    return token


def jurnodes_benutzer(einstellungen: Einstellungen,
                      env: Mapping[str, str] | None = None) -> str:
    """Der Benutzername fuer die Kopfzeile ``X-Auth-User``.

    jur|nodes verlangt zwei Angaben, nicht eine: Benutzer und Token. Hier
    wurde bis zum 23.09.2026 nur das Token geholt - eine Folge der frueheren
    Annahme, die Anmeldung laufe ueber ein Bearer-Token. Der erste echte Lauf
    waere daran gescheitert, und zwar mit einer Ablehnung, die aussieht wie
    ein falscher Schluessel.
    """
    env = os.environ if env is None else env
    benutzer = env.get(einstellungen.jurnodes_benutzer_var, "").strip()
    if not benutzer:
        raise KonfigurationsFehler(
            f"Der jurnodes-Benutzer fehlt: Umgebungsvariable "
            f"{einstellungen.jurnodes_benutzer_var} ist leer. "
            "Eintragen mit JURNODES-ZUGANG.bat."
        )
    return benutzer


def jurnodes_schluessel(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Die Schluessel je Bereich, soweit eigene hinterlegt sind.

    jur|nodes vergibt je Zugang einen Schluessel. Wer fuer Akten und
    Dateisystem zwei bekommen hat, hinterlegt sie als
    ``JURNODES_API_KEY_AKTEN`` und ``JURNODES_API_KEY_DATEISYSTEM``; ohne
    einen eigenen gilt der allgemeine.
    """
    from jusperfect.jurnodes.http_adapter import BEREICHE

    env = os.environ if env is None else env
    gefunden = {}
    for _, bereich in BEREICHE:
        wert = env.get(f"JURNODES_API_KEY_{bereich.upper()}", "").strip()
        if wert:
            gefunden[bereich] = wert
    return gefunden
