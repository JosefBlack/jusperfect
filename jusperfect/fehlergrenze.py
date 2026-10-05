"""Die Grenze, an der ein Fehler das Programm verlässt.

**Der Befund F01 der Zweitprüfung vom 05.10.2026.** Eine abgelehnte
Bedrock-Anfrage trägt den Wortlaut von AWS, und in einer Ablehnung steht
mitunter ein Stück der Anfrage – also Aktentext. Das Programm hat diesen
Wortlaut nie durchgereicht: `providers/bedrock.py` löst mit einem geprüften
Muster allenfalls den Namen der vermissten Handlung heraus, und die
HTTP-Antwort war sauber. **Das Protokoll war es nicht.**

Der Weg, den niemand gesehen hat:

1. Der Anbieter behält die ursprüngliche Ausnahme: `raise ProviderFehler(…)
   from e`. Der Wortlaut von AWS hängt damit als `__cause__` an der eigenen,
   sauberen Ausnahme.
2. Der eigene Handler für `Exception` in `web.py` sendet eine saubere 502.
3. **Starlette wirft die Ausnahme danach erneut** – so arbeitet
   `ServerErrorMiddleware`, wenn ein Handler für `Exception` eingetragen ist.
4. Uvicorn fängt sie an der ASGI-Grenze und protokolliert den vollständigen
   Traceback **samt Ursache** über den Protokollkanal `uvicorn.error`.
5. `access_log=False` schaltet diesen Kanal nicht ab. Und die Feldsperren aus
   `security/protokoll.py` kommen auf diesem Weg nie zum Einsatz.

**Die Lehre, und sie ist dieselbe wie bei F09:** Eine saubere HTTP-Antwort
beweist kein sauberes Protokoll. Geprüft war der gewollte Weg hinaus, nicht
der Weg, den ein Fehler nimmt.

---

## Was dieses Modul tut

Zwei Riegel, unabhängig voneinander. Der erste reicht; der zweite greift
auch dort, wo gar keine Anfrage läuft.

**1. `Fehlergrenze` – eine eigene ASGI-Grenze.** Sie liegt zwischen
Starlettes `ServerErrorMiddleware` und der Anwendung und lässt **keine**
Ausnahme nach außen. Was durchkommt, wird zu einer inhaltsfreien Antwort;
`ServerErrorMiddleware` kommt nie zum Zug, Uvicorn sieht nichts, es
protokolliert nichts. Fachliche Fehler erreichen sie ohnehin nicht mehr:
Für jeden eingetragenen Fehlertyp gibt es jetzt einen eigenen Handler, und
den behandelt Starlettes `ExceptionMiddleware`, ohne erneut zu werfen.

**2. `protokolle_eindaemmen()` – kein Traceback in irgendein Protokoll.**
Jeder Protokolleintrag entsteht über `logging.getLogRecordFactory()`. Dort
wird die angehängte Ausnahme abgenommen und durch die **Namen** der
Ausnahmekette samt Code-Stelle ersetzt:

    Ausnahmekette: providers.base.ProviderFehler (bedrock.py:241)
                   <- botocore.exceptions.ClientError (client.py:1057)

Das genügt zur Fehlersuche und kann keinen Inhalt tragen: Klassennamen,
Dateinamen und Zeilennummern sind Programmtext. Der Wortlaut einer Ausnahme
geht nie mit – auch nicht der eigene, denn eine eigene Meldung kann einen
Dateinamen oder einen Aktennamen enthalten.

Der Riegel wirkt für **jeden** Protokollkanal im Prozess, nicht nur für den
eigenen: Uvicorn, botocore, httpx, und was später dazukommt.

## Was dieses Modul ausdrücklich nicht tut

* **Es verschweigt den Fehler nicht.** Die Antwort nennt eine Vorgangsnummer,
  und unter derselben Nummer steht im Protokoll die Ausnahmekette. Wer
  anruft, nennt die Nummer; die Suche beginnt an der Code-Stelle.
* **Es protokolliert keinen Pfad.** Ein Pfad trägt Sitzungs- und
  Aktenkennungen; dieselbe Erwägung, aus der `__main__.py` die
  Zugriffsprotokolle abschaltet. Protokolliert werden Verfahren
  (GET/POST), Nummer und Kette.
"""

from __future__ import annotations

import logging
import secrets
from typing import Any, Callable

from jusperfect.security.protokoll import MAX_WERT_LAENGE, ereignis, protokoll

_log = protokoll("fehlergrenze")

#: Protokollkanäle, die bei feiner Einstellung Anfragekörper mitschreiben.
#: botocore schreibt auf DEBUG die vollständige Anfrage – darin steht der
#: Aktentext. Sie werden ausdrücklich auf WARNUNG gestellt, statt sich auf
#: die Vorgabe zu verlassen.
LAUTE_BIBLIOTHEKEN = (
    "botocore", "boto3", "boto3.resources", "s3transfer", "urllib3",
    "httpx", "httpcore", "requests", "requests.packages.urllib3",
)

#: Was in der Antwort steht, wenn der Fehler keiner der bekannten ist.
UNBEKANNT = "Interner Fehler. Der Vorgang wurde abgebrochen."


def _stelle(fehler: BaseException) -> str:
    """Datei und Zeile, an der die Ausnahme entstanden ist – sonst nichts.

    Die innerste Stelle, nicht die äußerste: Dort steht der Aufruf, der
    fehlgeschlagen ist. Der Dateiname wird auf den Namen gekürzt; ein
    vollständiger Pfad nennt auch Benutzerverzeichnisse.
    """
    spur = fehler.__traceback__
    if spur is None:
        return ""
    while spur.tb_next is not None:
        spur = spur.tb_next
    datei = spur.tb_frame.f_code.co_filename.replace("\\", "/").rsplit("/", 1)[-1]
    return f"{datei}:{spur.tb_lineno}"


def ausnahmekette(fehler: BaseException | None, max_tiefe: int = 6) -> str:
    """Die Namen der Ausnahmen und ihre Code-Stellen, ohne jeden Wortlaut.

    Kein `str(fehler)`, und das ist der ganze Punkt: Der Wortlaut ist das
    Einzige, was Inhalt tragen kann.
    """
    teile: list[str] = []
    gesehen: set[int] = set()
    aktuell: BaseException | None = fehler
    while aktuell is not None and id(aktuell) not in gesehen and len(teile) < max_tiefe:
        gesehen.add(id(aktuell))
        art = type(aktuell)
        name = f"{art.__module__}.{art.__qualname__}"
        stelle = _stelle(aktuell)
        teile.append(f"{name} ({stelle})" if stelle else name)
        aktuell = aktuell.__cause__ or aktuell.__context__
    return " <- ".join(teile)


def protokolle_eindaemmen() -> None:
    """Kein Traceback mehr in irgendein Protokoll dieses Prozesses.

    Wirkt an der einen Stelle, durch die jeder Protokolleintrag geht. Mehrfach
    aufzurufen ist gefahrlos; die Fabrik erkennt sich selbst wieder.
    """
    for name in LAUTE_BIBLIOTHEKEN:
        logging.getLogger(name).setLevel(logging.WARNING)

    alte_fabrik = logging.getLogRecordFactory()
    if getattr(alte_fabrik, "_jusperfect_ohne_traceback", False):
        return

    def fabrik(*args: Any, **kwargs: Any) -> logging.LogRecord:
        eintrag = alte_fabrik(*args, **kwargs)
        if eintrag.exc_info:
            kette = ausnahmekette(eintrag.exc_info[1])
            # exc_text statt exc_info: Der Formatierer nimmt vorhandenen
            # exc_text unveraendert und baut den Traceback dann nicht mehr.
            eintrag.exc_text = f"Ausnahmekette: {kette}" if kette else ""
            eintrag.exc_info = None
        return eintrag

    fabrik._jusperfect_ohne_traceback = True  # type: ignore[attr-defined]
    logging.setLogRecordFactory(fabrik)


class Fehlergrenze:
    """Eine ASGI-Schicht, die keine Ausnahme nach außen lässt.

    ``status_fuer`` liefert zu einer Ausnahme Status und Satz für die Antwort.
    Die Abbildung bleibt in `web.py`, wo die Fehlertypen zu Hause sind.
    """

    def __init__(self, app: Any, status_fuer: Callable[[Exception], tuple[int, str]]) -> None:
        self._app = app
        self._status_fuer = status_fuer

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return

        begonnen = False

        async def merken(nachricht: dict) -> None:
            nonlocal begonnen
            if nachricht.get("type") == "http.response.start":
                begonnen = True
            await send(nachricht)

        try:
            await self._app(scope, receive, merken)
        except Exception as fehler:  # noqa: BLE001 - genau das ist der Zweck
            nummer = secrets.token_hex(4)
            ereignis(_log, "fehler_abgefangen",
                     verfahren=str(scope.get("method", "")),
                     nummer=nummer,
                     # Gekuerzt, weil das Protokoll lange Werte abweist - und
                     # weil eine Kette von sechs Namen schon zu viel Tiefe ist.
                     kette=ausnahmekette(fehler)[:MAX_WERT_LAENGE])
            if begonnen:
                # Die Antwort ist schon unterwegs; mehr als abbrechen geht
                # nicht. Vor allem: nicht erneut werfen.
                return
            status, satz = self._status_fuer(fehler)
            if status >= 500:
                satz = f"{satz} Vorgangsnummer {nummer}."
            await self._antworten(send, status, satz)

    @staticmethod
    async def _antworten(send: Any, status: int, satz: str) -> None:
        import json

        koerper = json.dumps({"fehler": satz}, ensure_ascii=False).encode("utf-8")
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json; charset=utf-8"),
                                (b"content-length", str(len(koerper)).encode("ascii"))]})
        await send({"type": "http.response.body", "body": koerper})
