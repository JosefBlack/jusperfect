"""Was eine seltsame Antwort von jur|nodes anrichten darf – und was nicht.

Aus der Kanzlei am 13.10.2026: „Akte öffnen nicht möglich". Der Fehler trat am
echten Server auf und bei den erfundenen Akten nicht; er hängt also an echten
Daten. Welche, war nicht zu messen – also wurde die Frage umgedreht: **Was
müsste eine Antwort enthalten, damit es passiert?**

Diese Datei wirft dem Aufbauen der Liste der Reihe nach vor, was ein Server
schicken könnte, ohne die Beschreibung zu verletzen – und was sie verletzt.
Zwei Zusagen werden geprüft:

1. **Die Akte lässt sich öffnen.** Immer. Was nicht lesbar ist, fällt allein
   aus und wird gezählt.
2. **Eine Verzierung kostet kein Dokument.** Eine Größe, die keine Zahl ist,
   darf nicht dazu führen, dass das Dokument verschwindet – sie steht in der
   Zeile und entscheidet nichts.

Gefunden hat die Suche dabei genau eine Stelle: ``size`` ging unverwandelt in
ein ``int | None``. „1,5 MB" ließ das ganze Dokument aus der Liste fallen.
"""

from __future__ import annotations

import unittest

import httpx

from jusperfect.jurnodes.http_adapter import dokument_aus_json
from tests.test_eakte import AKTE, _Server, _adapter, _eintrag

#: Werte, die ein Server fuer ``size`` schicken kann. Keiner davon darf ein
#: Dokument kosten.
GROESSEN = [
    None, 0, 12345, "12345", "1,5", "1.5", 12345.0, 12345.5,
    "1,5 MB", "unbekannt", "", [1, 2], {"wert": 1}, True, False, -1,
]


class EineGroesseKostetKeinDokument(unittest.TestCase):
    def test_jeder_denkbare_wert_wird_angenommen(self):
        for wert in GROESSEN:
            with self.subTest(size=wert):
                d = dokument_aus_json(AKTE, {"identifier": "D-1", "fileName": "Brief",
                                             "fileExtension": "pdf", "size": wert})
                self.assertEqual(d.id, "D-1")
                self.assertTrue(d.dateiname.endswith(".pdf"))

    def test_eine_zahl_bleibt_eine_zahl(self):
        d = dokument_aus_json(AKTE, {"identifier": "D-1", "fileName": "x", "size": "12345"})
        self.assertEqual(d.groesse_bytes, 12345)

    def test_was_keine_zahl_ist_wird_keine_angabe(self):
        """Lieber keine Größe als eine erfundene."""
        for wert in ("1,5 MB", "unbekannt", "", [1, 2], {"wert": 1}, None, True):
            with self.subTest(size=wert):
                d = dokument_aus_json(AKTE, {"identifier": "D-1", "fileName": "x",
                                             "size": wert})
                self.assertIsNone(d.groesse_bytes)


class _ServerMitSeltsamenEintraegen(_Server):
    """Der Ordnerbaum antwortet mit allem, was mir eingefallen ist."""

    EINTRAEGE = [
        # Was die Beschreibung erlaubt, nur ungewoehnlich:
        {"type": "file", "file": {"identifier": "D-1", "fileName": "Brief",
                                  "fileExtension": "pdf", "size": "1,5 MB"}},
        {"type": "file", "file": {"identifier": "D-2", "fileName": "Ohne Endung"}},
        {"type": "file", "file": {"identifier": "D-3", "fileName": "Zahl",
                                  "addedDate": "nicht einmal ein Datum"}},
        {"type": "file", "file": {"identifier": "D-4", "fileName": "Tief",
                                  "addedDate": "2026-13-45"}},
        # Und was sie verletzt:
        {"type": "file", "file": {"fileName": "ohne Kennung"}},
        {"type": "file", "file": None},
        {"type": "file"},
        {"type": "file", "file": "eine Zeichenkette statt eines Verzeichnisses"},
        {"type": "file", "file": {"identifier": None, "fileName": "Kennung ist null"}},
    ]

    def __call__(self, anfrage: httpx.Request) -> httpx.Response:
        if "folder/content" in anfrage.url.path:
            self.gefragt.append(f"{anfrage.method} {anfrage.url.path}")
            return httpx.Response(200, json={"elements": self.EINTRAEGE,
                                             "pagesTotal": 1})
        if anfrage.url.path.endswith("/relation/search") or \
                anfrage.url.path.endswith("/todo/search"):
            return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
        return super().__call__(anfrage)


class DieAkteGehtTrotzdemAuf(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = _adapter(_ServerMitSeltsamenEintraegen())
        self.dokumente = self.adapter.dokumente(AKTE)

    def test_die_vier_ungewoehnlichen_sind_alle_dabei(self):
        """Ungewöhnlich ist nicht falsch. Keines davon darf fehlen."""
        kennungen = [d.id for d in self.dokumente]
        for erwartet in ("D-1", "D-2", "D-3", "D-4"):
            self.assertIn(erwartet, kennungen, kennungen)

    def test_ein_unmoegliches_datum_wird_keine_angabe(self):
        nach_id = {d.id: d for d in self.dokumente}
        self.assertIsNone(nach_id["D-3"].datum)
        self.assertIsNone(nach_id["D-4"].datum)

    def test_was_wirklich_kaputt_ist_faellt_allein_aus(self):
        self.assertTrue(self.adapter.letzte_eintraege_mit_fehler,
                        "Dann fiel nichts aus - der Vorrat ist zu zahm.")
        self.assertGreaterEqual(len(self.dokumente), 4)

    def test_kein_dokument_ohne_kennung_steht_in_der_liste(self):
        """Das war der zweite Fund: ein Dokument, das keines ist.

        Ein Eintrag ohne ``identifier`` wurde zu einem Dokument mit leerer
        Kennung - es stand da, ließ sich anhaken, und beim Laden war es nicht
        zu finden. Teurer als ein fehlendes: Was nicht da ist, fällt auf.
        """
        for d in self.dokumente:
            self.assertTrue(d.id.strip(), [x.id for x in self.dokumente])


class _ServerMitSeltsamerKorrespondenz(_Server):
    """Das Korrespondenzverzeichnis antwortet mit Unfug."""

    def __call__(self, anfrage: httpx.Request) -> httpx.Response:
        if anfrage.url.path.endswith("/relation/search") or \
                anfrage.url.path.endswith("/todo/search"):
            return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
        return super().__call__(anfrage)


class AuchEineSeltsameEAkteHaeltDieAkteNichtZu(unittest.TestCase):
    FAELLE = {
        "Eintrag ist eine Zeichenkette": ["kein Verzeichnis"],
        "Eintrag ist null": [None],
        "Vermerk ohne Nummer": [_eintrag("note")],
        "Vermerk mit null als Nummer": [_eintrag("note", referenceNote=None)],
        "Mail ohne Kennung": [_eintrag("mail")],
        "Art ist eine Zahl": [_eintrag("note", referenceNote=1, type=7)],
        "Richtung ist Unfug": [_eintrag("note", referenceNote=1, isInbox="vielleicht")],
        "Datum ist Unfug": [_eintrag("note", referenceNote=1, created=["2026"])],
    }

    def test_jeder_fall_laesst_die_liste_entstehen(self):
        for name, eintraege in self.FAELLE.items():
            with self.subTest(fall=name):
                adapter = _adapter(_ServerMitSeltsamerKorrespondenz(eintraege))
                dokumente = adapter.dokumente(AKTE)
                self.assertIsInstance(dokumente, list)


if __name__ == "__main__":
    unittest.main()
