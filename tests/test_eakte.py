"""Die E-Akte: Korrespondenz und Vermerke, über ihren eigenen Weg.

Aus der Kanzlei am 05.10.2026: *„Die Korrespondenz bei jurnodes und die
Vermerke finden sich in der E-Akte. Vielleicht ist das die Lösung."* Sie war
es – und sie hat zugleich den Befund vom 02.10.2026 erklärt.

**Was dort geschah.** In einer Bausache lagen drei Schriftstücke aus einer
fremden Verkehrsunfallsache. Die Vermutung war ein Fehler des Herstellers. Die
Beschreibung des Herstellers (API 1.0.2, seit 05.10.2026 im Programmordner)
hat es aufgeklärt, und die Antwort war unangenehm: **Es war unser eigener
Fehler.** `correspondenceFolderId` gehört in den Ordnerbaum der
**Korrespondenz**; abgefragt wurde sie gegen den Baum des **Dateisystems**.
Zwei Nummernkreise, dieselbe Zahl, fremde Akte.

**Der richtige Weg ist aktenbezogen:** `POST /correspondence/search` mit
`recordIdentifier`. Eine Verwechslung von Nummernkreisen kann dort nicht mehr
vorkommen – gefragt wird nach der Akte, nicht nach einer Ordnernummer.

**Was übernommen wird, und was nicht.** Ein Korrespondenzeintrag ist eine
Hülle: Betreff, Art, Richtung, Datum und ein Verweis darauf, wo der Inhalt
liegt. Von den neun Arten (mail, bea, post, fax, webnodes, sms, eda, note,
file) sagt die Beschreibung nur für den **Vermerk** zu, was als *Text*
zurückkommt: `RecordNote.content`, als html oder text.

Bei Mail, beA und Post fehlt weniger, als es zuerst aussah (nachgesehen am
06.10.2026): Den Download gibt es und er ist beschrieben – er liefert
`application/octet-stream`. Offen sind die **Dateiart** dieser Bytes und, bei
beA und Post, **woher die zweite Pflichtnummer kommt** (`attachmentId`,
`postFileUniqueKey`). Beides beantwortet ein Lauf am Server; bis dahin wird
nicht geraten. Was nicht übernommen wird, wird **gezählt**, damit nichts
lautlos fehlt.
"""

from __future__ import annotations

import json
import unittest

import httpx

from jusperfect.jurnodes.base import JurNodesFehler
from jusperfect.jurnodes.http_adapter import (
    VERMERK_VORSATZ, HttpJurNodesAdapter, vermerk_als_dokument,
)
from jusperfect.security.approval import Freigabestelle

AKTE = "rec-1"


def _eintrag(art: str, **extra):
    d = {"identifier": f"c-{art}", "subject": f"Betreff {art}", "type": art,
         "isInbox": 1, "created": "2026-05-04T09:00:00"}
    d.update(extra)
    return d


class _Server:
    """Ein erfundener jur|nodes-Server, der die Beschreibung 1.0.2 nachspielt."""

    def __init__(self, korrespondenz=(), vermerke=None):
        self.korrespondenz = list(korrespondenz)
        self.vermerke = vermerke or {}
        self.gefragt: list[str] = []
        self.koerper: list[dict] = []

    def __call__(self, anfrage: httpx.Request) -> httpx.Response:
        pfad = anfrage.url.path
        self.gefragt.append(f"{anfrage.method} {pfad}")
        if pfad.endswith("/correspondence/search"):
            self.koerper.append(json.loads(anfrage.content or b"{}"))
            if "page" in str(anfrage.content or b""):
                return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
            return httpx.Response(200, json={"elements": self.korrespondenz, "pagesTotal": 1})
        if pfad.endswith("/record/note"):
            nummer = str(anfrage.url.params.get("id"))
            akte = str(anfrage.url.params.get("record"))
            daten = self.vermerke.get(nummer)
            if daten is None:
                return httpx.Response(404, json={})
            return httpx.Response(200, json={**daten, "record": daten.get("record", akte)})
        if "folder/content" in pfad:
            return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
        if pfad.endswith("/record"):
            return httpx.Response(200, json={"identifier": AKTE, "fileFolderId": 7,
                                             "correspondenceFolderId": 9})
        return httpx.Response(200, json={})


def _adapter(server: _Server, korrespondenz: bool = True) -> HttpJurNodesAdapter:
    return HttpJurNodesAdapter("https://beispiel.invalid", "k", Freigabestelle(),
                               transport=httpx.MockTransport(server), benutzer="u",
                               korrespondenz=korrespondenz)


class DieEAkteWirdUeberIhrenEigenenWegGelesen(unittest.TestCase):
    def test_gefragt_wird_nach_der_akte_nicht_nach_einer_ordnernummer(self):
        """Der Kern der Berichtigung vom 06.10.2026."""
        server = _Server()
        _adapter(server).dokumente(AKTE)
        self.assertIn("POST /correspondence/search", server.gefragt)
        self.assertEqual(server.koerper[0].get("recordIdentifier"), AKTE)

    def test_ohne_die_einstellung_wird_sie_gar_nicht_gefragt(self):
        server = _Server()
        _adapter(server, korrespondenz=False).dokumente(AKTE)
        self.assertNotIn("POST /correspondence/search", server.gefragt)

    def test_ein_vermerk_wird_ein_dokument_der_akte(self):
        server = _Server([_eintrag("note", referenceNote=17)])
        dokumente = _adapter(server).dokumente(AKTE)
        self.assertEqual([d.id for d in dokumente], [f"{VERMERK_VORSATZ}17"])
        self.assertEqual(dokumente[0].titel, "Betreff note")
        self.assertEqual(dokumente[0].kategorie, "Vermerk")

    def test_eine_telefonnotiz_heisst_so(self):
        server = _Server([_eintrag("note", referenceNote=4, subject="", **{"type": "note"})])
        dokument = vermerk_als_dokument(AKTE, 4, {"type": "phonecall", "subject": ""})
        self.assertEqual(dokument.titel, "Telefonnotiz 4")

    def test_der_inhalt_kommt_erst_beim_laden(self):
        """Eine Hülle trägt den Betreff, nicht den Text. Hundert Hüllen zu
        laden, um drei anzuhaken, wäre hundert Anfragen für nichts."""
        server = _Server([_eintrag("note", referenceNote=17)],
                         {"17": {"id": 17, "record": AKTE, "type": "note",
                                 "contentType": "text",
                                 "content": "Mandantin ruft an, Frist läuft."}})
        a = _adapter(server)
        a.dokumente(AKTE)
        self.assertNotIn("GET /record/note", server.gefragt)
        _, inhalt = a.dokument_laden(AKTE, f"{VERMERK_VORSATZ}17")
        self.assertIn("Mandantin ruft an", inhalt.decode("utf-8"))

    def test_beide_pflichtparameter_gehen_mit(self):
        """Daran ist die Suche nach den Vermerken vier Wochen gescheitert:
        `GET /record/note` braucht **id und record**, nicht einen von beiden."""
        gesehen = {}

        def server(anfrage: httpx.Request) -> httpx.Response:
            if anfrage.url.path.endswith("/record/note"):
                gesehen.update(dict(anfrage.url.params))
                return httpx.Response(200, json={"id": 17, "record": AKTE, "content": "x"})
            if anfrage.url.path.endswith("/correspondence/search"):
                return httpx.Response(200, json={
                    "elements": [_eintrag("note", referenceNote=17)], "pagesTotal": 1})
            if "folder/content" in anfrage.url.path:
                return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
            return httpx.Response(200, json={"identifier": AKTE, "fileFolderId": 7})

        a = HttpJurNodesAdapter("https://beispiel.invalid", "k", Freigabestelle(),
                                transport=httpx.MockTransport(server), benutzer="u",
                                korrespondenz=True)
        a.dokument_laden(AKTE, f"{VERMERK_VORSATZ}17")
        self.assertEqual(gesehen.get("id"), "17")
        self.assertEqual(gesehen.get("record"), AKTE)


class EinFremderVermerkWirdAbgewiesen(unittest.TestCase):
    """Dieselbe Prüfung wie bei der Akte (Befund F08) – und hier geht sie,
    weil `RecordNote` das Feld `record` trägt."""

    def test_eine_andere_akte_bricht_den_vorgang_ab(self):
        server = _Server([_eintrag("note", referenceNote=17)],
                         {"17": {"id": 17, "record": "rec-FREMD", "content": "Fremder Text"}})
        a = _adapter(server)
        a.dokumente(AKTE)
        with self.assertRaises(JurNodesFehler) as fehler:
            a.dokument_laden(AKTE, f"{VERMERK_VORSATZ}17")
        self.assertIn("anderen Akte", str(fehler.exception))
        self.assertNotIn("rec-FREMD", str(fehler.exception))


class WasNochKeinenInhaltHatWirdGezaehlt(unittest.TestCase):
    """Was fehlt, soll sichtbar fehlen – nicht lautlos."""

    def test_mail_und_post_werden_gezaehlt_nicht_uebernommen(self):
        server = _Server([_eintrag("mail", referenceMail="m-1"),
                          _eintrag("post", referencePost=5),
                          _eintrag("bea", referenceBea="b-1"),
                          _eintrag("note", referenceNote=17)])
        a = _adapter(server)
        dokumente = a.dokumente(AKTE)
        self.assertEqual([d.id for d in dokumente], [f"{VERMERK_VORSATZ}17"])
        self.assertEqual(a.letzte_korrespondenz_ohne_inhalt, 3)

    def test_eine_datei_der_korrespondenz_wird_nicht_doppelt_gezaehlt(self):
        """Sie liegt im Dateisystem und ist über den Dateiordner schon dabei."""
        server = _Server([_eintrag("file", referenceFile="f-1")])
        a = _adapter(server)
        a.dokumente(AKTE)
        self.assertEqual(a.letzte_korrespondenz_ohne_inhalt, 0)

    def test_ein_ausfall_der_korrespondenz_kostet_nicht_die_dokumente(self):
        """Sie ist eine Ergänzung, keine Bedingung."""
        def server(anfrage: httpx.Request) -> httpx.Response:
            if anfrage.url.path.endswith("/correspondence/search"):
                return httpx.Response(403, json={})
            if "folder/content" in anfrage.url.path:
                return httpx.Response(200, json={"elements": [
                    {"type": "file", "file": {"identifier": "f-1", "folderId": 7,
                                              "fileName": "Klage", "fileExtension": "pdf"}}],
                    "pagesTotal": 1})
            return httpx.Response(200, json={"identifier": AKTE, "fileFolderId": 7})

        a = HttpJurNodesAdapter("https://beispiel.invalid", "k", Freigabestelle(),
                                transport=httpx.MockTransport(server), benutzer="u",
                                korrespondenz=True)
        dokumente = a.dokumente(AKTE)
        self.assertEqual([d.id for d in dokumente], ["f-1"])
        self.assertEqual(a.letzte_korrespondenz_ohne_inhalt, -1)


class DerLesendePostAufrufBleibtDieAusnahme(unittest.TestCase):
    """Das Verfahren macht einen Aufruf nicht schreibend – aber man soll die
    lesenden POST-Aufrufe an einer Hand abzählen können."""

    def test_es_ist_genau_einer(self):
        from pathlib import Path

        quelle = (Path(__file__).resolve().parent.parent / "jusperfect" / "jurnodes"
                  / "http_adapter.py").read_text(encoding="utf-8")
        self.assertEqual(quelle.count("self._client.post("), 3,
                         "Zwei schreibende (Vermerk, Datei) und ein lesender "
                         "(Korrespondenzsuche). Kommt einer dazu, gehört er begründet.")

    def test_die_suche_blaettert(self):
        """Wer nur die erste Seite holt, verliert den Rest lautlos."""
        seiten = []

        def server(anfrage: httpx.Request) -> httpx.Response:
            if anfrage.url.path.endswith("/correspondence/search"):
                koerper = json.loads(anfrage.content or b"{}")
                seiten.append(koerper.get("page"))
                if koerper.get("page"):
                    return httpx.Response(200, json={"elements": [], "pagesTotal": 2})
                return httpx.Response(200, json={
                    "elements": [_eintrag("note", referenceNote=1)], "pagesTotal": 2})
            if "folder/content" in anfrage.url.path:
                return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
            return httpx.Response(200, json={"identifier": AKTE, "fileFolderId": 7})

        a = HttpJurNodesAdapter("https://beispiel.invalid", "k", Freigabestelle(),
                                transport=httpx.MockTransport(server), benutzer="u",
                                korrespondenz=True)
        a.dokumente(AKTE)
        self.assertGreaterEqual(len(seiten), 2)
        self.assertIsNone(seiten[0], "Die erste Anfrage geht ohne Seitenangabe.")


class DieEinstellungStehtSeitDemLaufAufEin(unittest.TestCase):
    """Seit dem 08.10.2026 ein — weil ein Lauf am Server sie bestätigt hat.

    Sie stand aus, bis die Frage „Kann die E-Akte eingeschaltet werden?"
    gemessen beantwortet war. Der Lauf vom 08.10.2026 an `X-100-2026`
    antwortet **JA**: `POST /correspondence/search` gibt 26 Einträge (22 mail,
    4 note), und drei Vermerke wurden über
    `GET /record/note?id=…&record=…` wirklich geholt — mit Inhalt,
    `type=phonecall`, `contentType=html`.

    Damit ist die Bedingung erfüllt, unter der sie eingeschaltet werden
    sollte. Nicht früher, und nicht aus Ungeduld.
    """

    def test_vorgabe(self):
        from jusperfect.config import Einstellungen

        self.assertTrue(Einstellungen.korrespondenz)

    def test_die_startdatei_erklaert_sie(self):
        from pathlib import Path

        bat = (Path(__file__).resolve().parent.parent / "START-JURNODES.bat"
               ).read_bytes().decode("cp1252")
        self.assertIn("JUSPERFECT_KORRESPONDENZ", bat)


if __name__ == "__main__":
    unittest.main()
