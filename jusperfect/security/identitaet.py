"""Wer ruft an?

In AWS beantwortet das der JWT-Authorizer von API Gateway: Er prüft das
Cognito-Token, bevor die Lambda überhaupt läuft, und legt die Ansprüche
(``sub``, ``cognito:groups`` …) in das Ereignis. Die Anwendung liest sie von
dort – sie prüft keine Token selbst und vertraut keiner Kopfzeile.

Lokal gibt es keinen Authorizer; dort nennt die Kopfzeile ``X-Jusperfect-Nutzer``
die Kennung, und die Nutzerdatei sagt, ob es sie gibt. Diese Betriebsart ist
in AWS gesperrt (siehe ``Einstellungen.pruefen``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class NichtAngemeldet(PermissionError):
    pass


@dataclass(frozen=True)
class Identitaet:
    nutzer_id: str
    anzeigename: str = ""
    gruppen: tuple[str, ...] = field(default_factory=tuple)


def aus_cognito_ereignis(ereignis: dict[str, Any] | None) -> Identitaet:
    """Liest die vom API-Gateway-Authorizer bestätigten Ansprüche."""
    try:
        anspruch = ereignis["requestContext"]["authorizer"]["jwt"]["claims"]  # type: ignore[index]
    except (KeyError, TypeError):
        raise NichtAngemeldet("Keine bestätigte Anmeldung im Aufruf.") from None
    sub = str(anspruch.get("sub", "")).strip()
    if not sub:
        raise NichtAngemeldet("Anmeldung ohne Nutzerkennung.")
    gruppen_roh = anspruch.get("cognito:groups", "")
    if isinstance(gruppen_roh, str):
        gruppen = tuple(g.strip() for g in gruppen_roh.strip("[]").split(",") if g.strip())
    else:
        gruppen = tuple(str(g) for g in gruppen_roh or ())
    return Identitaet(
        nutzer_id=sub,
        anzeigename=str(anspruch.get("email") or anspruch.get("cognito:username") or sub),
        gruppen=gruppen,
    )


def aus_kopfzeile(wert: str | None) -> Identitaet:
    kennung = (wert or "").strip()
    if not kennung:
        raise NichtAngemeldet("Kopfzeile X-Jusperfect-Nutzer fehlt.")
    return Identitaet(nutzer_id=kennung, anzeigename=kennung)
