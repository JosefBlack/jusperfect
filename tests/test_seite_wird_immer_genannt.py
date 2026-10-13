"""Auch die erste Anfrage nennt ihre Seite – sonst fällt die E-Akte ganz aus.

Aus der Kanzlei am 13.10.2026, mit `AKTE-PRUEFEN.bat` gemessen::

    POST /correspondence/search mit Status 405.
    Der Server sagt dazu: {"error":"Bitte geben Sie eine Page an",
                           "validationErrors":[]}

Der Adapter ließ die Seitenangabe bei der **ersten** Anfrage weg – eine
Entscheidung vom 28.09.2026, damals an den GET-Suchen gemessen, wo der Server
ohne sie antwortet. Für diesen POST gilt sie nicht.

**Die Folge war kein Teilverlust, sondern ein Totalausfall:** 26 Einträge, 22
davon E-Mails, und keiner davon in der Akte. Im Prüfbogen der Schnittstelle
ging derselbe Aufruf durch – der sendet „Seite 1" ausdrücklich. Zwei
Werkzeuge, zwei Ergebnisse, und der Unterschied war diese eine Angabe.

**Warum vier Prüfläufe das nicht gefunden haben:** Der erfundene Server in
`tests/test_eakte.py` tat das Gegenteil des echten – er gab die Einträge
heraus, *solange* keine Seite genannt wurde, und nichts, sobald eine dastand.

> Ein erfundener Server, der mehr durchgehen lässt als der echte, ist
> schlimmer als keiner: Er färbt die Prüfung grün. Dieselbe Form wie am
> 02.10.2026 bei Textract – ein Aufruf, der ohne Fehler zurückkam und nicht
> gearbeitet hatte.
"""

from __future__ import annotations

import json
import unittest

import httpx

from jusperfect.jurnodes.base import JurNodesFehler
from tests.test_eakte import AKTE, _Server, _adapter, _eintrag


class _ServerWieDerEchte(_Server):
    """Weist eine Suche ohne Seitenangabe ab – wörtlich wie der echte.

    Der Wortlaut steht hier, weil er das Entscheidende war: Ohne ihn stand da
    nur „Status 405", und daraus habe ich am selben Tag geschlossen, der
    Hersteller weise einen beschriebenen Aufruf ab.
    """

    ABWEISUNG = {"error": "Bitte geben Sie eine Page an", "validationErrors": []}

    def __init__(self, korrespondenz=(), **rest) -> None:
        super().__init__(korrespondenz, **rest)
        self.seiten: list[object] = []

    def __call__(self, anfrage: httpx.Request) -> httpx.Response:
        pfad = anfrage.url.path
        if pfad.endswith("/correspondence/search"):
            koerper = json.loads(anfrage.content or b"{}")
            self.seiten.append(koerper.get("page"))
            if "page" not in koerper:
                return httpx.Response(405, json=self.ABWEISUNG)
            if int(koerper["page"]) != 1:
                return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
            return httpx.Response(200, json={"elements": self.korrespondenz,
                                             "pagesTotal": 1})
        if pfad.endswith("/relation/search") or pfad.endswith("/todo/search"):
            return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
        return super().__call__(anfrage)


def _vermerk(nummer: int = 17):
    return {str(nummer): {"id": nummer, "type": "memo", "content": "Ein Vermerk.",
                          "contentType": "text", "record": AKTE}}


class DieEAkteKommtAn(unittest.TestCase):
    def setUp(self) -> None:
        self.server = _ServerWieDerEchte([_eintrag("note", referenceNote=17)],
                                         vermerke=_vermerk())
        self.adapter = _adapter(self.server)
        self.dokumente = self.adapter.dokumente(AKTE)

    def test_die_erste_anfrage_nennt_seite_eins(self):
        self.assertEqual(self.server.seiten[0], 1,
                         "Ohne sie weist dieser Server die ganze Suche ab.")

    def test_keine_einzige_anfrage_geht_ohne_seite_hinaus(self):
        self.assertNotIn(None, self.server.seiten, self.server.seiten)

    def test_der_vermerk_steht_in_der_liste(self):
        self.assertTrue([d for d in self.dokumente if d.id.startswith("vermerk:")],
                        [d.id for d in self.dokumente])

    def test_die_e_akte_gilt_nicht_als_ausgefallen(self):
        """-1 heißt „das Verzeichnis war nicht zu lesen"."""
        self.assertNotEqual(self.adapter.letzte_korrespondenz_ohne_inhalt, -1)


class DieGegenprobe(unittest.TestCase):
    """Ohne die Seitenangabe fiele die E-Akte wieder ganz aus."""

    def test_eine_suche_ohne_seite_wird_abgewiesen(self):
        server = _ServerWieDerEchte([_eintrag("note", referenceNote=17)],
                                    vermerke=_vermerk())
        adapter = _adapter(server)
        with self.assertRaises(JurNodesFehler) as gefangen:
            adapter._lesen_per_post(adapter._endpunkte.korrespondenz_suche,
                                    JurNodesFehler, recordIdentifier=AKTE)
        self.assertIn("405", str(gefangen.exception))

    def test_und_der_wortlaut_des_servers_haengt_am_fehler(self):
        """Der Satz, der die Suche beendet hat - er darf nicht wieder weg."""
        server = _ServerWieDerEchte()
        adapter = _adapter(server)
        with self.assertRaises(JurNodesFehler) as gefangen:
            adapter._lesen_per_post(adapter._endpunkte.korrespondenz_suche,
                                    JurNodesFehler, recordIdentifier=AKTE)
        self.assertIn("Page", getattr(gefangen.exception, "server_wortlaut", ""))


class DerErfundeneServerTutJetztWasDerEchteTut(unittest.TestCase):
    """Die Prüfung der Prüfung.

    Der erfundene Server aus `tests/test_eakte.py` hat vier Prüfläufe lang das
    Gegenteil getan. Dass er es jetzt richtig tut, steht hier – sonst schleicht
    sich die alte Bequemlichkeit beim nächsten Umbau zurück.
    """

    def test_er_weist_eine_suche_ohne_seite_ab(self):
        antwort = _Server()(httpx.Request(
            "POST", "https://beispiel.invalid/correspondence/search", json={}))
        self.assertEqual(antwort.status_code, 405)
        self.assertIn("Page", antwort.text)

    def test_er_gibt_die_eintraege_auf_seite_eins(self):
        server = _Server([_eintrag("note", referenceNote=17)])
        antwort = server(httpx.Request(
            "POST", "https://beispiel.invalid/correspondence/search",
            json={"page": 1}))
        self.assertEqual(antwort.status_code, 200)
        self.assertEqual(len(antwort.json()["elements"]), 1)

    def test_und_nichts_mehr_auf_seite_zwei(self):
        server = _Server([_eintrag("note", referenceNote=17)])
        antwort = server(httpx.Request(
            "POST", "https://beispiel.invalid/correspondence/search",
            json={"page": 2}))
        self.assertEqual(antwort.json()["elements"], [])


if __name__ == "__main__":
    unittest.main()
