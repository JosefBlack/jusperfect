"""Die Dokumentliste zeigt, in welchem Ordner ein Schriftstück liegt.

Aus der Aufgabenliste, seit längerem offen: In `X-100-2026` stehen **55
Einträge aus acht Ordnern in einer Reihe**. Ein Aktenordner, der seine
Gliederung verliert, ist schwerer zu lesen als ein Papierordner mit Registern
— und wer „alles aus dem Gerichtsordner" anhaken will, klickt fünfzehnmal.

**Der Ordner war im Programm bisher gar nicht vorhanden.** Der Baumdurchlauf
`_ordner_durchgehen` kannte ihn, warf ihn aber weg; am Dokument gab es kein
Feld dafür. Das ist seit dem 12.10.2026 anders: `Dokument.ordner`.

**Was hier bewusst geprüft wird:** dass die E-Akte einen eigenen Namen trägt.
Mails, ihre Anlagen und Vermerke kommen aus dem Korrespondenzbaum, nicht aus
dem Dateiordner. Sie dazwischenzumischen hieße, zwei Bäume zu einem zu machen
— und genau diese Verwechslung hat am 02.10.2026 drei fremde Schriftstücke in
eine Bausache gebracht.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import httpx

from jusperfect.jurnodes.http_adapter import (
    EAKTE_ORDNER, HttpJurNodesAdapter, _ordnerpfad,
)
from jusperfect.security.approval import Freigabestelle

AKTE = "rec-1"
STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"


def _datei(name: str, ordner_id: int) -> dict:
    return {"type": "file", "file": {"identifier": f"f-{name}", "fileName": name,
                                     "fileExtension": "pdf", "folderId": ordner_id}}


def _unterordner(nummer: int, name: str | None) -> dict:
    ordner: dict = {"id": nummer, "canRead": True}
    if name is not None:
        ordner["folderName"] = name
    return {"type": "folder", "folder": ordner}


class _Baum:
    """Ein erfundener jur|nodes-Server mit einem Ordnerbaum.

    ``inhalt`` bildet Ordnernummer -> Liste von Einträgen ab, so wie
    ``GET /file-system/folder/content`` sie liefert.
    """

    def __init__(self, inhalt: dict[int, list[dict]]):
        self.inhalt = inhalt

    def __call__(self, anfrage: httpx.Request) -> httpx.Response:
        pfad = anfrage.url.path
        if "folder/content" in pfad:
            nummer = int(anfrage.url.params.get("folderId"))
            return httpx.Response(200, json={"elements": self.inhalt.get(nummer, []),
                                             "pagesTotal": 1})
        if pfad.endswith("/correspondence/search"):
            return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
        if pfad.endswith("/record"):
            return httpx.Response(200, json={"identifier": AKTE, "fileFolderId": 1})
        return httpx.Response(200, json={})


def _adapter(server: _Baum, korrespondenz: bool = False) -> HttpJurNodesAdapter:
    return HttpJurNodesAdapter("https://beispiel.invalid", "k", Freigabestelle(),
                               transport=httpx.MockTransport(server), benutzer="u",
                               korrespondenz=korrespondenz)


class DerOrdnerKommtMit(unittest.TestCase):

    def test_was_im_aktenordner_liegt_hat_keinen_unterordner(self):
        a = _adapter(_Baum({1: [_datei("Klage.pdf", 1)]}))
        self.assertEqual("", a.dokumente(AKTE)[0].ordner)

    def test_ein_unterordner_steht_am_dokument(self):
        a = _adapter(_Baum({1: [_unterordner(2, "Schriftsätze")],
                            2: [_datei("Erwiderung.pdf", 2)]}))
        self.assertEqual("Schriftsätze", a.dokumente(AKTE)[0].ordner)

    def test_zwei_ebenen_werden_zu_einem_pfad(self):
        a = _adapter(_Baum({1: [_unterordner(2, "Schriftsätze")],
                            2: [_unterordner(3, "Gegenseite")],
                            3: [_datei("Klageerwiderung.pdf", 3)]}))
        self.assertEqual("Schriftsätze/Gegenseite", a.dokumente(AKTE)[0].ordner)

    def test_jedes_dokument_behaelt_seinen_eigenen_ordner(self):
        """Acht Ordner in einer Reihe waren der Anlass - also acht Namen."""
        a = _adapter(_Baum({
            1: [_datei("Deckblatt.pdf", 1), _unterordner(2, "Gericht"),
                _unterordner(3, "Mandant")],
            2: [_datei("Ladung.pdf", 2)],
            3: [_datei("Vollmacht.pdf", 3)],
        }))
        nach_titel = {d.titel: d.ordner for d in a.dokumente(AKTE)}
        self.assertEqual({"Deckblatt.pdf": "", "Ladung.pdf": "Gericht",
                          "Vollmacht.pdf": "Mandant"}, nach_titel)


class WennDerOrdnerKeinenNamenHat(unittest.TestCase):
    """Dann steht die Nummer da — und nicht nichts.

    Zwei namenlose Ordner dürfen nicht zu einem verschmelzen: Das sähe aus
    wie ein Register, wo zwei sind.
    """

    def test_ohne_namen_steht_die_nummer_da(self):
        a = _adapter(_Baum({1: [_unterordner(2, None)], 2: [_datei("x.pdf", 2)]}))
        self.assertEqual("Ordner 2", a.dokumente(AKTE)[0].ordner)

    def test_zwei_namenlose_ordner_bleiben_zwei(self):
        a = _adapter(_Baum({1: [_unterordner(2, None), _unterordner(3, "")],
                            2: [_datei("a.pdf", 2)], 3: [_datei("b.pdf", 3)]}))
        self.assertEqual({"Ordner 2", "Ordner 3"},
                         {d.ordner for d in a.dokumente(AKTE)})

    def test_ein_schraegstrich_im_namen_taeuscht_keine_ebene_vor(self):
        """„Miete / Nebenkosten" ist ein Ordner, nicht zwei."""
        self.assertEqual("Miete - Nebenkosten",
                         _ordnerpfad("", {"folderName": "Miete / Nebenkosten"}, 2))
        self.assertEqual("Akte/Miete - Nebenkosten",
                         _ordnerpfad("Akte", {"folderName": "Miete / Nebenkosten"}, 2))


class DieEAkteIstEinEigenerBaum(unittest.TestCase):
    """Und steht deshalb unter eigenem Namen, nicht im Dateiordner."""

    def _mit_eakte(self) -> list:
        eintraege = [{"identifier": "c-1", "subject": "Telefonat", "type": "note",
                      "referenceNote": 7, "created": "2026-05-04T09:00:00"}]

        class _Server(_Baum):
            def __call__(self, anfrage):
                if anfrage.url.path.endswith("/correspondence/search"):
                    return httpx.Response(200, json={"elements": eintraege,
                                                     "pagesTotal": 1})
                if anfrage.url.path.endswith("/record/note"):
                    return httpx.Response(200, json={
                        "id": 7, "content": "Rückruf", "contentType": "text",
                        "record": AKTE, "type": "phonecall"})
                return super().__call__(anfrage)

        return _adapter(_Server({1: [_datei("Klage.pdf", 1)]}),
                        korrespondenz=True).dokumente(AKTE)

    def test_der_vermerk_steht_in_der_eakte_und_nicht_im_aktenordner(self):
        nach_titel = {d.titel: d.ordner for d in self._mit_eakte()}
        self.assertEqual(EAKTE_ORDNER, nach_titel["Telefonat"])
        self.assertEqual("", nach_titel["Klage.pdf"],
                         "Die Datei aus dem Dateiordner bleibt, wo sie ist.")


class DasFensterGruppiert(unittest.TestCase):
    """Was im Quelltext der Oberfläche stehen muss, damit es überhaupt greift.

    Keine Messung am laufenden Browser — die gibt es von Hand. Diese Prüfung
    hält nur fest, dass die drei Teile nicht wieder herausfallen: das Feld in
    der Karte, die Gruppierung und die Suche über den Ordner.
    """

    @classmethod
    def setUpClass(cls):
        cls.js = (STATISCH / "app.js").read_text(encoding="utf-8")
        cls.html = (STATISCH / "index.html").read_text(encoding="utf-8")

    def test_die_karte_des_explorers_traegt_den_ordner(self):
        self.assertIn("ordner: d.ordner", self.js)

    def test_es_gibt_eine_gruppierung(self):
        self.assertIn("function explorerNachOrdnern", self.js)
        self.assertIn("explorerOrdnerzeile", self.js)

    def test_die_eakte_steht_hinten(self):
        """Ein anderer Baum gehört nicht zwischen die Register des einen."""
        self.assertRegex(self.js, r'const EAKTE_ORDNER = "E-Akte"')
        self.assertIn('if (a === EAKTE_ORDNER) return 1;', self.js)

    def test_ein_einziger_ordner_ist_keine_gliederung(self):
        self.assertIn("gruppen.length > 1", self.js)

    def test_die_suche_findet_auch_den_ordner(self):
        treffer = re.search(r"function dokumentPasst\(d, begriffe\) \{.*?\n\}",
                            self.js, re.S)
        self.assertIsNotNone(treffer)
        self.assertIn("d.ordner", treffer.group(0))
        self.assertIn("Ordner", self.html, "Der Platzhalter soll es auch sagen.")
