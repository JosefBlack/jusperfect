"""Was ein Fehler auf seinem Weg nach draußen mitnimmt – und was nicht.

Befund F01 der Zweitprüfung vom 05.10.2026, Gegenproben 12 und 13. Die
HTTP-Antwort war sauber, das Serverprotokoll nicht: Der Anbieter behält die
ursprüngliche AWS-Ausnahme als `__cause__`, Starlette wirft nach der sauberen
Antwort erneut, und Uvicorn schreibt den vollständigen Traceback **samt
Ursache** in den Kanal `uvicorn.error`. In einer Ablehnung von AWS steht
mitunter ein Stück der Anfrage – also Aktentext.

**Die Lehre ist dieselbe wie bei F09:** Eine saubere HTTP-Antwort beweist kein
sauberes Protokoll. Geprüft war der gewollte Weg hinaus, nicht der Weg, den
ein Fehler nimmt.

Diese Datei prüft deshalb beides und ausdrücklich getrennt:

1. **Die Antwort** – kein Wortlaut, Status wie bisher.
2. **Das tatsächlich erzeugte Protokoll** – nicht ein eigener Kanal, sondern
   der von Uvicorn, über Uvicorns eigene Fehlerbehandlung an einer echten
   `RequestResponseCycle`.

`MARKER` steht für das, was niemals hinausgehen darf. Er ist erfunden und
sieht aus wie Akteninhalt.
"""

from __future__ import annotations

import asyncio
import json
import logging
import traceback
import unittest
from unittest.mock import Mock

from fastapi.testclient import TestClient

from jusperfect.fehlergrenze import ausnahmekette, protokolle_eindaemmen
from jusperfect.providers.base import ProviderFehler
from jusperfect.web import app_erstellen
from tests.hilfen import client, dienste

MARKER = "Mandantin Kraemer, HWS-Distorsion, 8.400,00 EUR Schmerzensgeld"
AKTE = "VU-2026-0042"


def _provider_der_abgelehnt_wird():
    """Ein Bedrock-Anbieter, dessen AWS-Antwort den Marker trägt."""
    from botocore.exceptions import ClientError

    from jusperfect.providers.bedrock import BedrockProvider

    mock = Mock()
    mock.converse.side_effect = ClientError(
        {"Error": {"Code": "ValidationException", "Message": MARKER}}, "Converse")
    return BedrockProvider("test", client=mock, prompt_cache=False)


def _sitzung(provider=None):
    d = dienste(provider=provider) if provider else dienste()
    c = client(d)
    sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
    c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
    return d, c, sid


# ── Der echte Uvicorn-Weg ──────────────────────────────────────────────────

def _durch_uvicorn(app, pfad: str, koerper: bytes, nutzer: str = "ra-weber") -> bytes:
    """Eine Anfrage durch Uvicorns eigene Fehlerbehandlung schicken.

    Nicht nachgebaut: Es ist Uvicorns `RequestResponseCycle` mit einer echten
    h11-Verbindung. Ersetzt ist allein der Netzanschluss – geschrieben wird in
    eine Liste statt in einen Socket. Nur so lässt sich prüfen, was wirklich
    protokolliert wird; der Nachbau in der Gegenprobe hat genau dort
    aufgehört.
    """
    import h11
    from uvicorn.protocols.http.flow_control import FlowControl
    from uvicorn.protocols.http.h11_impl import RequestResponseCycle

    kopfzeilen = [(b"host", b"localhost"), (b"content-type", b"application/json"),
                  (b"x-jusperfect-nutzer", nutzer.encode()),
                  (b"content-length", str(len(koerper)).encode())]
    roh = (f"POST {pfad} HTTP/1.1\r\n".encode()
           + b"".join(n + b": " + w + b"\r\n" for n, w in kopfzeilen)
           + b"\r\n" + koerper)
    verbindung = h11.Connection(h11.SERVER)
    verbindung.receive_data(roh)
    assert isinstance(verbindung.next_event(), h11.Request)

    geschrieben: list[bytes] = []
    anschluss = Mock()
    anschluss.write = geschrieben.append
    anschluss.is_closing.return_value = False

    scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
             "http_version": "1.1", "method": "POST", "scheme": "http",
             "path": pfad, "raw_path": pfad.encode(), "query_string": b"",
             "root_path": "", "headers": kopfzeilen,
             "server": ("127.0.0.1", 8765), "client": ("127.0.0.1", 12345)}

    async def lauf() -> None:
        runde = RequestResponseCycle(
            scope=scope, conn=verbindung, transport=anschluss,
            flow=FlowControl(anschluss),
            logger=logging.getLogger("uvicorn.error"),
            access_logger=logging.getLogger("uvicorn.access"), access_log=False,
            default_headers=[], message_event=asyncio.Event(),
            on_response=lambda: None)
        runde.body = bytearray(koerper)
        runde.more_body = False
        runde.message_event.set()
        await runde.run_asgi(app)

    asyncio.run(lauf())
    return b"".join(geschrieben)


class DasServerprotokollBleibtInhaltsfrei(unittest.TestCase):
    """Gegenprobe 13, in richtiger Polarität: grün heißt, die Lücke ist zu."""

    def test_uvicorn_protokolliert_den_aws_wortlaut_nicht_mehr(self):
        d, c, sid = _sitzung(_provider_der_abgelehnt_wird())
        app = app_erstellen(d.einstellungen, d)
        with self.assertLogs(level=logging.DEBUG) as aufgezeichnet:
            # Eine Zeile, damit assertLogs nicht am leeren Protokoll scheitert.
            logging.getLogger("jusperfect.pruefung").info("Lauf beginnt")
            antwort = _durch_uvicorn(app, f"/api/sitzungen/{sid}/frage",
                                     json.dumps({"frage": "Unfall?"}).encode())
        self.assertIn(b"502", antwort.split(b"\r\n")[0])
        self.assertNotIn(MARKER.encode(), antwort)
        self.assertNotIn(MARKER, "\n".join(aufgezeichnet.output))
        # Und kein Traceback: Er ist der Trager, auf dem der Wortlaut reist.
        self.assertNotIn("Traceback", "\n".join(aufgezeichnet.output))

    def test_das_protokoll_nennt_weder_pfad_noch_sitzung(self):
        """Ein Pfad trägt Sitzungs- und Aktenkennungen.

        Aus demselben Grund stehen in `__main__.py` die Zugriffsprotokolle
        aus. Eine Fehlerzeile, die den Pfad mitnimmt, hebelt das aus.
        """
        d, c, sid = _sitzung(_provider_der_abgelehnt_wird())
        app = app_erstellen(d.einstellungen, d)
        with self.assertLogs(level=logging.DEBUG) as aufgezeichnet:
            logging.getLogger("jusperfect.pruefung").info("Lauf beginnt")
            _durch_uvicorn(app, f"/api/sitzungen/{sid}/frage",
                           json.dumps({"frage": "Unfall?"}).encode())
        text = "\n".join(aufgezeichnet.output)
        self.assertNotIn(sid, text)
        self.assertNotIn(AKTE, text)

    def test_ein_programmfehler_wird_protokolliert_aber_ohne_pfad(self):
        """Der fachliche Fehler erreicht die Grenze nicht mehr – er wird vorher
        beantwortet. Der unerwartete erreicht sie, und dann steht eine Zeile da:
        Verfahren, Nummer, Kette. Kein Pfad.
        """
        from jusperfect.fehlergrenze import Fehlergrenze

        async def platzt(scope, receive, send):
            raise ValueError(MARKER)

        grenze = Fehlergrenze(platzt, status_fuer=lambda exc: (500, "Interner Fehler."))

        async def senden(nachricht):
            pass

        async def empfangen():
            return {"type": "http.request", "body": b"", "more_body": False}

        with self.assertLogs("jusperfect.fehlergrenze", level=logging.INFO) as auf:
            asyncio.run(grenze(
                {"type": "http", "method": "POST",
                 "path": f"/api/sitzungen/{AKTE}-geheim/frage"},
                empfangen, senden))
        text = "\n".join(auf.output)
        self.assertNotIn(AKTE, text)
        self.assertNotIn("/api/sitzungen", text)
        self.assertIn("POST", text, "Das Verfahren darf dastehen – es trägt nichts.")


class KeineAusnahmeVerlaesstDieAnwendung(unittest.TestCase):
    """Gegenprobe 12, in richtiger Polarität.

    Dort stand `pytest.raises(ProviderFehler)` und bestand – die Ausnahme kam
    heraus. Hier steht das Gegenteil.
    """

    def test_die_antwort_bleibt_sauber(self):
        d, c, sid = _sitzung(_provider_der_abgelehnt_wird())
        antwort = c.post(f"/api/sitzungen/{sid}/frage", json={"frage": "Unfall?"})
        self.assertEqual(antwort.status_code, 502)
        self.assertNotIn(MARKER, antwort.text)

    def test_mit_raise_server_exceptions_kommt_nichts_heraus(self):
        d, c, sid = _sitzung(_provider_der_abgelehnt_wird())
        streng = TestClient(app_erstellen(d.einstellungen, d),
                            headers={"X-Jusperfect-Nutzer": "ra-weber"},
                            raise_server_exceptions=True)
        antwort = streng.post(f"/api/sitzungen/{sid}/frage", json={"frage": "Unfall?"})
        self.assertEqual(antwort.status_code, 502)
        self.assertNotIn(MARKER, antwort.text)

    def test_ein_programmfehler_wird_inhaltsfrei_beantwortet(self):
        """Nicht nur die bekannten Fehlertypen: auch der unerwartete.

        Er ist der gefährlichere – seine Meldung ist von niemandem geprüft.
        """
        d, c, sid = _sitzung()

        async def platzt(scope, receive, send):
            raise ValueError(MARKER)

        app = app_erstellen(d.einstellungen, d)
        from jusperfect.fehlergrenze import Fehlergrenze

        grenze = Fehlergrenze(platzt, status_fuer=lambda exc: (500, "Interner Fehler."))
        gesendet: list[dict] = []

        async def senden(nachricht):
            gesendet.append(nachricht)

        async def empfangen():
            return {"type": "http.request", "body": b"", "more_body": False}

        asyncio.run(grenze({"type": "http", "method": "POST", "path": "/x"},
                           empfangen, senden))
        self.assertEqual(gesendet[0]["status"], 500)
        koerper = gesendet[1]["body"].decode("utf-8")
        self.assertNotIn(MARKER, koerper)
        # Die Vorgangsnummer macht den Fall auffindbar, ohne ihn zu nennen.
        self.assertIn("Vorgangsnummer", koerper)


class DieVorgangsnummerVerbindetAntwortUndProtokoll(unittest.TestCase):
    """Ohne sie wäre „inhaltsfrei" gleichbedeutend mit „unauffindbar"."""

    def test_dieselbe_nummer_steht_in_beiden(self):
        import re

        from jusperfect.fehlergrenze import Fehlergrenze

        async def platzt(scope, receive, send):
            raise ValueError(MARKER)

        grenze = Fehlergrenze(platzt, status_fuer=lambda exc: (500, "Interner Fehler."))
        gesendet: list[dict] = []

        async def senden(nachricht):
            gesendet.append(nachricht)

        async def empfangen():
            return {"type": "http.request", "body": b"", "more_body": False}

        with self.assertLogs("jusperfect.fehlergrenze", level=logging.INFO) as auf:
            asyncio.run(grenze({"type": "http", "method": "POST", "path": "/x"},
                               empfangen, senden))
        nummer = re.search(r"Vorgangsnummer ([0-9a-f]+)",
                           gesendet[1]["body"].decode("utf-8")).group(1)
        protokoll = "\n".join(auf.output)
        self.assertIn(nummer, protokoll)
        self.assertNotIn(MARKER, protokoll)
        # Und die Kette, damit die Suche an einer Code-Stelle beginnt.
        self.assertIn("ValueError", protokoll)


class DieAusnahmeketteTraegtKeinenWortlaut(unittest.TestCase):
    """Sie ersetzt den Traceback. Also muss sie ohne Wortlaut auskommen."""

    def _kette(self) -> str:
        try:
            try:
                raise RuntimeError(MARKER)
            except RuntimeError as urspruenglich:
                raise ProviderFehler("Bedrock hat die Anfrage abgelehnt.") from urspruenglich
        except ProviderFehler as fehler:
            return ausnahmekette(fehler)

    def test_sie_nennt_die_namen_und_die_stelle(self):
        kette = self._kette()
        self.assertIn("ProviderFehler", kette)
        self.assertIn("RuntimeError", kette)
        self.assertIn("test_fehlergrenze.py:", kette, "Ohne Stelle beginnt keine Suche.")
        self.assertIn("<-", kette, "Die Ursache gehört dazu, nur ohne ihren Text.")

    def test_sie_nennt_keinen_wortlaut(self):
        kette = self._kette()
        self.assertNotIn(MARKER, kette)
        # Auch nicht den eigenen: Eine eigene Meldung kann einen Dateinamen
        # oder einen Aktennamen enthalten.
        self.assertNotIn("abgelehnt", kette)

    def test_sie_dreht_sich_nicht_im_kreis(self):
        """Eine Ausnahme kann sich selbst als Ursache tragen."""
        fehler = RuntimeError("a")
        fehler.__cause__ = fehler
        self.assertEqual(ausnahmekette(fehler).count("RuntimeError"), 1)

    def test_sie_hoert_nach_sechs_auf(self):
        tief = RuntimeError("0")
        for i in range(12):
            neu = ValueError(str(i))
            neu.__cause__ = tief
            tief = neu
        self.assertLessEqual(ausnahmekette(tief).count("<-"), 5)


class KeinTracebackInIrgendeinProtokoll(unittest.TestCase):
    """Der zweite Riegel, unabhängig von der ASGI-Grenze.

    Er greift auch dort, wo gar keine Anfrage läuft – in einem Hintergrund-
    Vorgang, in einem Werkzeug, in einer Bibliothek.
    """

    def test_auch_ein_fremder_kanal_schreibt_keinen_traceback(self):
        protokolle_eindaemmen()
        try:
            raise ValueError(MARKER)
        except ValueError:
            with self.assertLogs("irgendeine.fremde.bibliothek", level=logging.ERROR) as auf:
                logging.getLogger("irgendeine.fremde.bibliothek").exception("Fehler")
        zeilen = [h for h in auf.records]
        self.assertIsNone(zeilen[0].exc_info)
        self.assertIn("Ausnahmekette", zeilen[0].exc_text or "")
        self.assertNotIn(MARKER, zeilen[0].exc_text or "")

    def test_der_formatierer_haengt_die_kette_an_statt_des_tracebacks(self):
        protokolle_eindaemmen()
        try:
            raise ValueError(MARKER)
        except ValueError:
            eintrag = logging.getLogger("jusperfect.pruefung").makeRecord(
                "jusperfect.pruefung", logging.ERROR, __file__, 1, "Fehler", (),
                __import__("sys").exc_info())
        text = logging.Formatter("%(message)s").format(eintrag)
        self.assertNotIn(MARKER, text)
        self.assertNotIn("Traceback", text)
        self.assertIn("ValueError", text)

    def test_die_lauten_bibliotheken_stehen_auf_warnung(self):
        """botocore schreibt auf DEBUG die vollständige Anfrage mit."""
        protokolle_eindaemmen()
        for name in ("botocore", "boto3", "urllib3", "httpx"):
            with self.subTest(kanal=name):
                self.assertGreaterEqual(logging.getLogger(name).level, logging.WARNING)

    def test_mehrfaches_einrichten_stapelt_nicht(self):
        vorher = logging.getLogRecordFactory()
        protokolle_eindaemmen()
        protokolle_eindaemmen()
        self.assertIs(logging.getLogRecordFactory(), vorher if getattr(
            vorher, "_jusperfect_ohne_traceback", False) else logging.getLogRecordFactory())
        # Und sie wirkt weiterhin.
        try:
            raise ValueError(MARKER)
        except ValueError:
            eintrag = logging.getLogger("x").makeRecord(
                "x", logging.ERROR, __file__, 1, "F", (), __import__("sys").exc_info())
        self.assertIsNone(eintrag.exc_info)


class DieFachlichenFehlerAntwortenWieBisher(unittest.TestCase):
    """Die Umstellung auf einzelne Handler darf nichts am Verhalten ändern.

    Hier hängt die ganze Oberfläche dran: Jede Fehlermeldung, die der Anwender
    liest, kommt über diesen Weg.
    """

    def test_eine_unbekannte_sitzung_bleibt_404(self):
        d, c, _ = _sitzung()
        self.assertEqual(c.get("/api/sitzungen/gibtsnicht").status_code, 404)

    def test_eine_unbekannte_akte_bleibt_404(self):
        d, c, _ = _sitzung()
        self.assertEqual(
            c.post("/api/sitzungen", json={"akte_id": "XX-9999-9999"}).status_code, 404)

    def test_ein_unbekannter_nutzer_bleibt_403(self):
        d = dienste()
        fremd = TestClient(app_erstellen(d.einstellungen, d),
                           headers={"X-Jusperfect-Nutzer": "niemand"},
                           raise_server_exceptions=False)
        self.assertEqual(fremd.get("/api/status").status_code, 403)

    def test_der_satz_des_fehlers_steht_weiter_in_der_antwort(self):
        """„fehler" ist das Feld, das die Oberfläche anzeigt."""
        d, c, _ = _sitzung()
        antwort = c.get("/api/sitzungen/gibtsnicht")
        self.assertIn("fehler", antwort.json())
        self.assertTrue(antwort.json()["fehler"].strip())


if __name__ == "__main__":
    unittest.main()
