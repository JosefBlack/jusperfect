"""Einstieg für AWS Lambda hinter API Gateway (HTTP API).

Mangum übersetzt das API-Gateway-Ereignis in einen ASGI-Aufruf und legt das
Originalereignis in ``request.scope["aws.event"]`` – von dort liest die
Anwendung die vom JWT-Authorizer bestätigten Ansprüche.
"""

from __future__ import annotations

from mangum import Mangum

from jusperfect.config import Einstellungen
from jusperfect.web import app_erstellen

_app = app_erstellen(Einstellungen.aus_umgebung())
handler = Mangum(_app, lifespan="off")
