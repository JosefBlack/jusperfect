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
    ANHANG_TRENNER, MAIL_VORSATZ, VERMERK_VORSATZ, HttpJurNodesAdapter,
    vermerk_als_dokument,
)
from jusperfect.security.approval import Freigabestelle

AKTE = "rec-1"


def _eml(text: str, anlagen: tuple[tuple[str, bytes], ...] = (),
         betreff: str = "Ein Betreff") -> bytes:
    """Die Bytes einer .eml - so, wie POST /mail/download sie liefert."""
    from email.message import EmailMessage

    m = EmailMessage()
    m["Subject"] = betreff
    m["From"] = "gegner@example.invalid"
    m["To"] = "kanzlei@example.invalid"
    m["Date"] = "Wed, 08 Oct 2026 09:14:00 +0200"
    m.set_content(text)
    for name, inhalt in anlagen:
        m.add_attachment(inhalt, maintype="application", subtype="pdf",
                         filename=name)
    return m.as_bytes()


def _eintrag(art: str, **extra):
    d = {"identifier": f"c-{art}", "subject": f"Betreff {art}", "type": art,
         "isInbox": 1, "created": "2026-05-04T09:00:00"}
    d.update(extra)
    return d


class _Server:
    """Ein erfundener jur|nodes-Server, der die Beschreibung 1.0.2 nachspielt."""

    def __init__(self, korrespondenz=(), vermerke=None, mails=None):
        self.korrespondenz = list(korrespondenz)
        self.vermerke = vermerke or {}
        #: mailIdentifier -> die Bytes der .eml, so wie POST /mail/download
        #: sie am 08.10.2026 wirklich geliefert hat.
        self.mails = dict(mails or {})
        self.gefragt: list[str] = []
        self.koerper: list[dict] = []

    def __call__(self, anfrage: httpx.Request) -> httpx.Response:
        pfad = anfrage.url.path
        self.gefragt.append(f"{anfrage.method} {pfad}")
        if pfad.endswith("/correspondence/search"):
            koerper = json.loads(anfrage.content or b"{}")
            self.koerper.append(koerper)
            # So wie der echte Server, gemessen am 13.10.2026 am Server der
            # Kanzlei. Hier stand vorher: ohne "page" die Eintraege, mit
            # "page" nichts - also das Gegenteil. Diese Erfindung hat den
            # Fehler zugedeckt, an dem die E-Akte dort vollstaendig ausfiel:
            # Der Adapter liess die Seitenangabe bei der ersten Anfrage weg,
            # und der Server wies sie ab.
            #
            # Ein erfundener Server, der mehr durchgehen laesst als der
            # echte, ist schlimmer als keiner: Er faerbt die Pruefung gruen.
            if "page" not in koerper:
                return httpx.Response(
                    405, json={"error": "Bitte geben Sie eine Page an",
                               "validationErrors": []})
            if int(koerper["page"]) != 1:
                return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
            return httpx.Response(200, json={"elements": self.korrespondenz, "pagesTotal": 1})
        if pfad.endswith("/record/note"):
            nummer = str(anfrage.url.params.get("id"))
            akte = str(anfrage.url.params.get("record"))
            daten = self.vermerke.get(nummer)
            if daten is None:
                return httpx.Response(404, json={})
            return httpx.Response(200, json={**daten, "record": daten.get("record", akte)})
        if pfad.endswith("/mail/download"):
            kennung = json.loads(anfrage.content or b"{}").get("mailIdentifier")
            roh = self.mails.get(kennung)
            if roh is None:
                return httpx.Response(404, json={})
            return httpx.Response(
                200, content=roh,
                headers={"content-type": "application/octet-stream",
                         "content-disposition": 'inline; filename="Mail.eml"'})
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

    def test_post_und_bea_werden_gezaehlt_die_mail_wird_uebernommen(self):
        """Seit dem 08.10.2026 ist die Mail dabei - beA und Post noch nicht.

        Für beide steht die Kette in der Beschreibung vollständig. Gebaut
        wird sie erst, wenn es eine Akte gibt, an der sich das messen lässt:
        In den beiden geprüften kam kein einziger Eintrag dieser Art vor.
        """
        server = _Server([_eintrag("mail", referenceMail="m-1"),
                          _eintrag("post", referencePost=5),
                          _eintrag("bea", referenceBea="b-1"),
                          _eintrag("note", referenceNote=17)],
                         mails={"m-1": _eml("Der Brieftext.")})
        a = _adapter(server)
        ids = [d.id for d in a.dokumente(AKTE)]
        self.assertIn(f"{VERMERK_VORSATZ}17", ids)
        self.assertIn("mail:m-1", ids)
        self.assertEqual(a.letzte_korrespondenz_ohne_inhalt, 2,
                         "Post und beA - die Mail nicht mehr.")

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
                if koerper.get("page") != 1:
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
        # Berichtigt am 13.10.2026. Hier stand: "Die erste Anfrage geht ohne
        # Seitenangabe." Der Server der Kanzlei weist genau das ab -
        # {"error": "Bitte geben Sie eine Page an"} -, und die ganze E-Akte
        # fiel dort aus. Ein erfundener Server, der mehr durchgehen laesst
        # als der echte, faerbt die Pruefung gruen.
        self.assertEqual(seiten[0], 1, "Auch die erste Anfrage nennt ihre Seite.")
        self.assertEqual(seiten[1], 2, "Und die zweite ist die zweite.")


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


class DieMailWirdZerlegt(unittest.TestCase):
    """Vorgabe der Kanzlei vom 08.10.2026, wörtlich.

    „Text der Mail immer, Anhänge als eigene Dokumente daneben, jedes einzeln
    abwählbar wie die Dateien aus dem Aktenordner."

    Gebaut wurde das erst, nachdem der Lauf vom selben Tag den Weg vollständig
    gemessen hatte: `referenceMail` geht unverändert in `/mail/download`, und
    der Server nennt die Dateiart selbst — `filename="Mail.eml"`.
    """

    def _akte_mit_mail(self, text="Der Brieftext.", anlagen=(), **kw):
        server = _Server([_eintrag("mail", referenceMail="m-1")],
                         mails={"m-1": _eml(text, anlagen)})
        return server, _adapter(server, **kw)

    def test_der_text_wird_ein_dokument(self):
        server, a = self._akte_mit_mail()
        dokumente = a.dokumente(AKTE)
        self.assertEqual([f"{MAIL_VORSATZ}m-1"], [d.id for d in dokumente])
        self.assertEqual("Betreff mail", dokumente[0].titel)

    def test_jede_anlage_wird_ein_eigenes_dokument(self):
        server, a = self._akte_mit_mail(
            anlagen=(("Klage.pdf", b"%PDF-1.4 eins"),
                     ("Anlage K1.pdf", b"%PDF-1.4 zwei")))
        dokumente = a.dokumente(AKTE)
        self.assertEqual(
            [f"{MAIL_VORSATZ}m-1",
             f"{MAIL_VORSATZ}m-1{ANHANG_TRENNER}0",
             f"{MAIL_VORSATZ}m-1{ANHANG_TRENNER}1"],
            [d.id for d in dokumente])
        self.assertEqual(2, a.letzte_mail_anhaenge)

    def test_der_titel_einer_anlage_nennt_ihre_mail(self):
        """Sonst stehen drei Zeilen „Anlage K1.pdf“ nebeneinander."""
        server, a = self._akte_mit_mail(anlagen=(("Anlage K1.pdf", b"%PDF"),))
        anlage = a.dokumente(AKTE)[1]
        self.assertIn("Anlage K1.pdf", anlage.titel)
        self.assertIn("Betreff mail", anlage.titel)
        self.assertEqual("Anlage K1.pdf", anlage.dateiname)

    def test_der_text_kommt_beim_laden_mit_den_kopfzeilen(self):
        server, a = self._akte_mit_mail(text="Wir beantragen Fristverlängerung.")
        a.dokumente(AKTE)
        _, inhalt = a.dokument_laden(AKTE, f"{MAIL_VORSATZ}m-1")
        text = inhalt.decode("utf-8")
        self.assertIn("Wir beantragen Fristverlängerung.", text)
        self.assertIn("gegner@example.invalid", text,
                      "Ohne Absender ist eine Mail als Beleg wertlos.")

    def test_die_anlage_kommt_beim_laden_im_original(self):
        server, a = self._akte_mit_mail(anlagen=(("Klage.pdf", b"%PDF-1.4 echt"),))
        a.dokumente(AKTE)
        _, inhalt = a.dokument_laden(AKTE, f"{MAIL_VORSATZ}m-1{ANHANG_TRENNER}0")
        self.assertEqual(b"%PDF-1.4 echt", inhalt)

    def test_die_mail_wird_nur_einmal_geholt(self):
        """Text und Anlagen kommen aus derselben .eml - ein Aufruf genügt."""
        server, a = self._akte_mit_mail(anlagen=(("A.pdf", b"x"), ("B.pdf", b"y")))
        a.dokumente(AKTE)
        a.dokument_laden(AKTE, f"{MAIL_VORSATZ}m-1")
        a.dokument_laden(AKTE, f"{MAIL_VORSATZ}m-1{ANHANG_TRENNER}0")
        a.dokument_laden(AKTE, f"{MAIL_VORSATZ}m-1{ANHANG_TRENNER}1")
        geholt = [g for g in server.gefragt if g.endswith("/mail/download")]
        self.assertEqual(1, len(geholt), f"Mehrfach geholt: {geholt}")

    def test_ohne_die_einstellung_wird_gar_nichts_geholt(self):
        server, a = self._akte_mit_mail(korrespondenz=False)
        a.dokumente(AKTE)
        self.assertEqual([], [g for g in server.gefragt if "mail/download" in g])


class DieObergrenzeWarntDenBearbeiter(unittest.TestCase):
    """Vorgabe der Kanzlei vom 08.10.2026.

    „Obergrenze sollte festgelegt werden, bei Überschreitung sollte der
    Bearbeiter gewarnt werden und aufmerksam gemacht werden."

    Eine Zahl in einer Fußzeile ist keine Warnung — sie wird übersehen.
    Deshalb steht sie in der Zeile selbst, dort, wo der Haken gesetzt wird.
    """

    def test_eine_zu_grosse_mail_bleibt_in_der_liste_und_warnt(self):
        gross = _eml("x" * 200_000)
        server = _Server([_eintrag("mail", referenceMail="m-1")],
                         mails={"m-1": gross})
        a = HttpJurNodesAdapter("https://beispiel.invalid", "k", Freigabestelle(),
                                transport=httpx.MockTransport(server), benutzer="u",
                                korrespondenz=True, mail_grenze_mb=0)
        dokumente = a.dokumente(AKTE)

        self.assertEqual(1, len(dokumente), "Sie verschwindet nicht.")
        self.assertIn("Betreff mail", dokumente[0].titel, "Der Betreff bleibt.")
        self.assertIn("zu groß", dokumente[0].titel, "Und die Warnung steht daneben.")
        self.assertIn("Inhalt fehlt", dokumente[0].kategorie)
        self.assertEqual(1, a.letzte_mails_zu_gross)

    def test_der_server_meldet_die_laenge_und_es_wird_abgebrochen(self):
        """Dann gehen die Bytes gar nicht erst über die Leitung."""
        gelesen = {"bytes": 0}

        def server(anfrage: httpx.Request) -> httpx.Response:
            pfad = anfrage.url.path
            if pfad.endswith("/correspondence/search"):
                # Seite 1 traegt die Eintraege - wie der echte Server.
                if json.loads(anfrage.content or b"{}").get("page") != 1:
                    return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
                return httpx.Response(200, json={
                    "elements": [_eintrag("mail", referenceMail="m-1")],
                    "pagesTotal": 1})
            if pfad.endswith("/mail/download"):
                roh = _eml("y" * 100_000)
                gelesen["bytes"] = len(roh)
                return httpx.Response(200, content=roh,
                                      headers={"content-length": str(len(roh))})
            if "folder/content" in pfad:
                return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
            if pfad.endswith("/record"):
                return httpx.Response(200, json={"identifier": AKTE, "fileFolderId": 7})
            return httpx.Response(200, json={})

        a = HttpJurNodesAdapter("https://beispiel.invalid", "k", Freigabestelle(),
                                transport=httpx.MockTransport(server), benutzer="u",
                                korrespondenz=True, mail_grenze_mb=0)
        dokumente = a.dokumente(AKTE)
        self.assertEqual(1, a.letzte_mails_zu_gross)
        self.assertIn("zu groß", dokumente[0].titel)

    def test_eine_mail_die_der_server_nicht_herausgibt_warnt_anders(self):
        """404 ist kein Größenproblem - und soll auch nicht so aussehen."""
        server = _Server([_eintrag("mail", referenceMail="fehlt")])
        a = _adapter(server)
        dokumente = a.dokumente(AKTE)
        self.assertEqual(1, len(dokumente))
        self.assertIn("nicht herausgegeben", dokumente[0].titel)
        self.assertEqual(1, a.letzte_mails_ohne_antwort)
        self.assertEqual(0, a.letzte_mails_zu_gross)

    def test_das_gesamtmass_der_akte_haelt_an(self):
        """Zwanzig Mails zu je acht Megabyte sind kein Aktenaufruf mehr."""
        server = _Server([_eintrag("mail", referenceMail=f"m-{i}") for i in range(4)],
                         mails={f"m-{i}": _eml("z" * 30_000) for i in range(4)})
        a = HttpJurNodesAdapter("https://beispiel.invalid", "k", Freigabestelle(),
                                transport=httpx.MockTransport(server), benutzer="u",
                                korrespondenz=True, mail_grenze_mb=1, mail_gesamt_mb=0)
        dokumente = a.dokumente(AKTE)
        self.assertEqual(4, len(dokumente), "Alle vier bleiben in der Liste.")
        self.assertEqual(4, a.letzte_mails_ueber_budget)
        for d in dokumente:
            self.assertIn("Gesamtmaß", d.titel)

    def test_eine_mail_ohne_kennung_wird_gezaehlt(self):
        server = _Server([_eintrag("mail")])
        a = _adapter(server)
        a.dokumente(AKTE)
        self.assertEqual(1, a.letzte_korrespondenz_ohne_inhalt)


class DieRichtungStehtAmSchriftstueck(unittest.TestCase):
    """`isInbox` — seit dem 11.10.2026 benannt statt vermutet.

    Der Hersteller sagt es in `CorrespondenceModel.isInbox` selbst:
    *„1 = Eingang, 0 = Ausgang, -1 = Neutral/Unbekannt"*. Vier Wochen lang
    stand im Programm nur „E-Mail" ohne Richtung, weil die Auskunft als
    fehlend galt — sie stand die ganze Zeit in
    `schnittstelle/jurnodes-api-1.0.2.json`.

    **Der dritte Wert ist der Grund für diese Prüfklasse.** Die Vermutung
    „1 = eingegangen, 0 = ausgegangen" war richtig und unvollständig. Wer das
    Feld als Ja/Nein liest, schreibt über jedes neutrale Schreiben „Ausgang" —
    und ein falsch herum beschriftetes Schriftstück in einer Handakte ist
    teurer als ein gar nicht beschriftetes.
    """

    def test_eingang_und_ausgang_stehen_in_der_kategorie(self):
        server = _Server([_eintrag("mail", referenceMail="m-ein", isInbox=1),
                          _eintrag("mail", referenceMail="m-aus", isInbox=0)],
                         mails={"m-ein": _eml("kam herein"), "m-aus": _eml("ging hinaus")})
        nach_kennung = {d.id: d for d in _adapter(server).dokumente(AKTE)}
        self.assertEqual("E-Mail (Eingang)", nach_kennung[MAIL_VORSATZ + "m-ein"].kategorie)
        self.assertEqual("E-Mail (Ausgang)", nach_kennung[MAIL_VORSATZ + "m-aus"].kategorie)

    def test_neutral_wird_nicht_zu_ausgang(self):
        """-1 heißt *weder noch*. Das ist keine Null."""
        server = _Server([_eintrag("mail", referenceMail="m", isInbox=-1)],
                         mails={"m": _eml("weder noch")})
        dokumente = _adapter(server).dokumente(AKTE)
        self.assertEqual("E-Mail", dokumente[0].kategorie)
        self.assertNotIn("Ausgang", dokumente[0].kategorie)

    def test_ein_unbeschriebener_wert_wird_nicht_gedeutet(self):
        """Was der Hersteller nicht beschrieben hat, wird nicht erfunden."""
        for wert in (7, "ja", None, ""):
            with self.subTest(isInbox=wert):
                server = _Server([_eintrag("mail", referenceMail="m", isInbox=wert)],
                                 mails={"m": _eml("unklar")})
                self.assertEqual("E-Mail", _adapter(server).dokumente(AKTE)[0].kategorie)

    def test_fehlt_das_feld_ganz_steht_keine_richtung_da(self):
        eintrag = _eintrag("mail", referenceMail="m")
        del eintrag["isInbox"]
        server = _Server([eintrag], mails={"m": _eml("ohne Feld")})
        self.assertEqual("E-Mail", _adapter(server).dokumente(AKTE)[0].kategorie)

    def test_die_anlage_erbt_die_richtung_ihrer_mail(self):
        """Wer „alles, was eingegangen ist" anhakt, meint die Anlagen mit."""
        server = _Server([_eintrag("mail", referenceMail="m", isInbox=1)],
                         mails={"m": _eml("mit Anlage", (("Vertrag.pdf", b"%PDF-1.4 x"),))})
        anlagen = [d for d in _adapter(server).dokumente(AKTE)
                   if ANHANG_TRENNER in d.id]
        self.assertEqual(1, len(anlagen))
        self.assertEqual("Anlage zur E-Mail (Eingang)", anlagen[0].kategorie)

    def test_fehlt_der_inhalt_bleibt_die_richtung_erst_recht_stehen(self):
        """Wenn der Text fehlt, ist die Richtung das Einzige, was bleibt.

        Deshalb verdrängt die Warnung sie nicht, sondern steht hinter ihr.
        """
        server = _Server([_eintrag("mail", referenceMail="m", isInbox=1)],
                         mails={"m": _eml("x" * 40_000)})
        a = HttpJurNodesAdapter("https://beispiel.invalid", "k", Freigabestelle(),
                                transport=httpx.MockTransport(server), benutzer="u",
                                korrespondenz=True, mail_grenze_mb=0)
        dokument = a.dokumente(AKTE)[0]
        self.assertIn("Eingang", dokument.kategorie)
        self.assertIn("Inhalt fehlt", dokument.kategorie)
        self.assertIn("⚠", dokument.titel)


class DieEAkteWirdUeberAlleSeitenGelesen(unittest.TestCase):
    """Eine E-Akte, die auf der zweiten Seite aufhört, ist unvollständig.

    Angemerkt am 11.10.2026 von einer zweiten Meinung: `POST
    /correspondence/search` führt `page` und gibt `pagesTotal` zurück; wer nur
    die erste Seite liest, bekommt eine Liste, die wie eine vollständige
    aussieht. Der Einwand war berechtigt gestellt und ist hier gemessen
    beantwortet — `_alle_seiten_post` gab es bereits, geprüft war es für die
    E-Akte noch nicht.
    """

    class _SeitenServer(_Server):
        """Gibt die Einträge seitenweise heraus, wie der Hersteller es tut."""

        def __init__(self, seiten, **rest):
            super().__init__([], **rest)
            self.seiten = seiten          # Liste von Listen
            self.gefragte_seiten: list[int] = []

        def __call__(self, anfrage):
            if anfrage.url.path.endswith("/correspondence/search"):
                koerper = json.loads(anfrage.content or b"{}")
                # Die erste Anfrage geht ohne "page" hinaus - gemessen am
                # 07.10.2026: mit page=0 kam nichts zurueck.
                nummer = int(koerper.get("page", 1))
                self.gefragte_seiten.append(nummer)
                teil = self.seiten[nummer - 1] if nummer <= len(self.seiten) else []
                return httpx.Response(200, json={"elements": teil,
                                                 "pagesTotal": len(self.seiten),
                                                 "amountTotal": sum(map(len, self.seiten))})
            return super().__call__(anfrage)

    def test_drei_seiten_vermerke_kommen_vollstaendig_an(self):
        seiten = [[_eintrag("note", referenceNote=n) for n in (1, 2)],
                  [_eintrag("note", referenceNote=n) for n in (3, 4)],
                  [_eintrag("note", referenceNote=5)]]
        vermerke = {str(n): {"id": n, "content": f"Vermerk {n}", "contentType": "text",
                             "record": AKTE} for n in range(1, 6)}
        server = self._SeitenServer(seiten, vermerke=vermerke)
        dokumente = _adapter(server).dokumente(AKTE)
        self.assertEqual([1, 2, 3], server.gefragte_seiten,
                         "Alle drei Seiten müssen abgefragt worden sein.")
        self.assertEqual(5, len([d for d in dokumente
                                 if d.id.startswith(VERMERK_VORSATZ)]),
                         "Kein Vermerk darf auf einer späteren Seite liegen bleiben.")


# ── Befund N04 der dritten Zweitprüfung vom 12.10.2026 ──────────────────────
#
# Der Parser zählte, was er nicht übernehmen konnte, und gab es zurück. Der
# Adapter nahm diesen Zähler nicht. Angezeigt wurden allein die angenommenen
# Anlagen — und die sahen vollständig aus. „Ein Zähler, den nur der Parser
# kennt, ist kein Zähler."
#
# Gemessen wird deshalb hier: am Dokument, das in der Liste steht, und am
# Zähler des Adapters, den `web.py` in die Antwort schreibt.

def _eml_mit_leerer_anlage() -> bytes:
    from email.message import EmailMessage

    m = EmailMessage()
    m["Subject"] = "Mit einer unlesbaren Anlage"
    m["From"] = "gegner@example.invalid"
    m["Date"] = "Wed, 08 Oct 2026 09:14:00 +0200"
    m.set_content("Anbei der Schriftsatz.")
    m.add_attachment(b"", maintype="application", subtype="pdf",
                     filename="Schriftsatz.pdf")
    return m.as_bytes()


class DerVerlustErreichtDieAnzeige(unittest.TestCase):
    def _dokumente(self, roh: bytes):
        server = _Server([_eintrag("mail", referenceMail="m-1")],
                         mails={"m-1": roh})
        adapter = _adapter(server)
        return adapter, adapter.dokumente(AKTE)

    def test_die_zeile_der_mail_sagt_dass_etwas_fehlt(self):
        """Dort sucht man es, wenn eine Anlage fehlt."""
        _, dokumente = self._dokumente(_eml_mit_leerer_anlage())
        mail = next(d for d in dokumente if d.id == f"{MAIL_VORSATZ}m-1")
        self.assertIn("nicht alles übernommen", mail.titel)
        self.assertIn("unvollständig", mail.kategorie)

    def test_der_adapter_fuehrt_den_grund_mit(self):
        adapter, _ = self._dokumente(_eml_mit_leerer_anlage())
        self.assertTrue(adapter.letzte_mail_ausgelassen,
                        "Der Zähler des Parsers muss im Adapter ankommen.")
        self.assertEqual(1, sum(adapter.letzte_mail_ausgelassen.values()))

    def test_eine_vollstaendige_mail_traegt_keine_warnung(self):
        """Die Gegenrichtung: Eine Warnung an jeder Mail wäre keine Warnung."""
        adapter, dokumente = self._dokumente(
            _eml("Anbei.", anlagen=(("Schriftsatz.pdf", b"%PDF-1.4"),)))
        mail = next(d for d in dokumente if d.id == f"{MAIL_VORSATZ}m-1")
        self.assertNotIn("nicht alles übernommen", mail.titel)
        self.assertEqual({}, adapter.letzte_mail_ausgelassen)

    def test_der_zaehler_wird_je_akte_zurueckgesetzt(self):
        """Sonst trüge die nächste Akte die Warnung der vorigen."""
        adapter, _ = self._dokumente(_eml_mit_leerer_anlage())
        self.assertTrue(adapter.letzte_mail_ausgelassen)
        server = _Server([_eintrag("mail", referenceMail="m-2")],
                         mails={"m-2": _eml("Ohne Anlage.")})
        adapter._client = httpx.Client(base_url="https://beispiel.invalid",
                                       transport=httpx.MockTransport(server))
        adapter.dokumente(AKTE)
        self.assertEqual({}, adapter.letzte_mail_ausgelassen)

    def test_der_text_der_weitergeleiteten_mail_steht_im_dokument(self):
        """Befund N03, am Weg durch den Adapter gemessen."""
        from email.message import EmailMessage

        innen = EmailMessage()
        innen["Subject"] = "Abtretung"
        innen["From"] = "mandant@example.invalid"
        innen.set_content("Hiermit erkläre ich die Abtretung meiner Ansprüche.")
        aussen = EmailMessage()
        aussen["Subject"] = "Zur Kenntnis"
        aussen["From"] = "gegner@example.invalid"
        aussen["Date"] = "Wed, 08 Oct 2026 09:14:00 +0200"
        aussen.set_content("Zur Kenntnis.")
        aussen.add_attachment(innen)
        adapter, dokumente = self._dokumente(aussen.as_bytes())
        self.assertEqual(1, adapter.letzte_mail_nachrichten)
        mail = next(d for d in dokumente if d.id == f"{MAIL_VORSATZ}m-1")
        self.assertNotIn("nicht alles übernommen", mail.titel)


# ── Befund N07 der dritten Zweitprüfung vom 12.10.2026 ─────────────────────
#
# Fehlt der Akte die `fileFolderId`, stand in `dokumente()` ein `return []` —
# und damit war auch die **E-Akte** weg, obwohl sie an einem völlig anderen
# Weg hängt: `POST /correspondence/search` mit `recordIdentifier`, kein
# Ordner. Statt einer erkennbaren Lücke erschien eine leere Akte.
#
# Zwei unabhängige Lesewege dürfen nicht aneinander hängen. Und eine leere
# Liste ist die schlechteste aller Antworten: Sie sieht aus wie „die Akte ist
# leer" und heißt „ich habe nicht nachgesehen".
#
# Die Herstellerbeschreibung kennzeichnet das Feld als nicht erforderlich,
# sagt aber zugleich, es werde bei Aktenanlage automatisch vergeben; ein
# Echtfall ist nicht belegt. Das ändert am Kontrollfluss nichts.

class _ServerOhneDateiordner(_Server):
    """Wie `_Server`, nur nennt die Akte keinen Dateiordner."""

    def __call__(self, anfrage: httpx.Request) -> httpx.Response:
        if anfrage.url.path.endswith("/record"):
            self.gefragt.append(f"{anfrage.method} {anfrage.url.path}")
            return httpx.Response(200, json={"identifier": AKTE,
                                             "correspondenceFolderId": 9})
        return super().__call__(anfrage)


class OhneDateiordnerBleibtDieEAkteLesbar(unittest.TestCase):
    def test_die_vermerke_kommen_trotzdem(self):
        server = _ServerOhneDateiordner([_eintrag("note", referenceNote=17)],
                                        vermerke={"17": {"id": 17, "type": "memo",
                                                         "content": "Ein Vermerk.",
                                                         "contentType": "text",
                                                         "record": AKTE}})
        dokumente = _adapter(server).dokumente(AKTE)
        self.assertTrue([d for d in dokumente if d.id.startswith(VERMERK_VORSATZ)],
                        "Ohne Dateiordner fehlt auch die E-Akte.")

    def test_die_korrespondenz_wird_ueberhaupt_gefragt(self):
        """Vorher kam der Aufruf nicht einmal zustande."""
        server = _ServerOhneDateiordner()
        _adapter(server).dokumente(AKTE)
        self.assertIn("POST /correspondence/search", server.gefragt)

    def test_das_fehlen_wird_gemeldet(self):
        """Sonst sieht die Liste aus wie eine Akte, in der nur Mails liegen."""
        server = _ServerOhneDateiordner()
        adapter = _adapter(server)
        adapter.dokumente(AKTE)
        self.assertTrue(adapter.letzte_akte_ohne_dateiordner)

    def test_mit_dateiordner_bleibt_die_meldung_aus(self):
        """Eine Warnung an jeder Akte wäre keine Warnung."""
        server = _Server()
        adapter = _adapter(server)
        adapter.dokumente(AKTE)
        self.assertFalse(adapter.letzte_akte_ohne_dateiordner)

    def test_der_zaehler_wird_bei_jedem_lesen_neu_gesetzt(self):
        """Sonst trüge die nächste Akte die Warnung der vorigen.

        Der Kurzpuffer wird dazwischen geleert — sonst käme die Antwort der
        Akte aus ihm, und dann prüft das hier den Puffer und nicht den
        Zähler.
        """
        server = _ServerOhneDateiordner()
        adapter = _adapter(server)
        adapter.dokumente(AKTE)
        self.assertTrue(adapter.letzte_akte_ohne_dateiordner)
        adapter._client = httpx.Client(base_url="https://beispiel.invalid",
                                       transport=httpx.MockTransport(_Server()))
        adapter._puffer_leeren()
        adapter.dokumente(AKTE)
        self.assertFalse(adapter.letzte_akte_ohne_dateiordner)
