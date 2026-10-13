"""Was ein unerwarteter Fehler dem Bearbeiter sagt – auf jedem Weg.

Aus der Kanzlei am 13.10.2026: „Akte öffnen nicht möglich Vorgang wurde
abgebrochen interner Fehler 2e2e3bd1." Die Nummer kam an, die Zeile dazu nicht
(`tests/test_vorgangsnummer_kommt_an.py`).

Beim Nachsehen fielen zwei Wege auf, die **noch weniger** hergaben:

1. **Die Frage, mitten im Strom.** Die Fehlergrenze sieht diesen Fehler nie:
   Der Strom hat begonnen, die Antwort ist unterwegs, und was in der Schleife
   geschieht, bleibt dort. Herausging „Interner Fehler. Der Vorgang wurde
   abgebrochen." – **ohne Nummer**, ohne Zeile, ohne irgendetwas.
2. **Der abgelegte Dokumenttext.** Ein abgelaufener Text hatte seinen Satz
   („Bitte Dokumente erneut laden"), ein unlesbarer nicht. Und weil die
   Oberfläche die Passagen beim Öffnen holt, machte ein Dokument damit die
   ganze Arbeitsfläche unbenutzbar.

Was auf beiden Wegen gilt und hier geprüft wird: **kein Wortlaut der Ausnahme
geht hinaus.** Er kann ein Stück der Akte tragen – dieselbe Erwägung wie bei
einer Abweisung von AWS (Befund F01 der Zweitprüfung vom 05.10.2026).
"""

from __future__ import annotations

import json
import logging
import unittest
from unittest import mock

from tests.hilfen import client, dienste

MARKER = "Zeisig ./. Nordwacht - 8.400,00 EUR Schmerzensgeld"
AKTE = "MV-2026-0007"


def _sitzung():
    d = dienste()
    c = client(d)
    sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
    c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-101"]})
    return d, c, sid


class DieFrageMittenImStrom(unittest.TestCase):
    def setUp(self) -> None:
        self.d, self.c, self.sid = _sitzung()

    def _fehlerzeile(self) -> dict:
        with mock.patch.object(type(self.d.analyse), "frage_stream",
                               side_effect=ValueError(MARKER)):
            antwort = self.c.post(f"/api/sitzungen/{self.sid}/frage/stream",
                                  json={"frage": "Worum geht es?"})
        self.assertEqual(antwort.status_code, 200, antwort.text)
        zeilen = [json.loads(z) for z in antwort.text.splitlines() if z.strip()]
        fehler = [z for z in zeilen if z.get("type") == "fehler"]
        self.assertTrue(fehler, antwort.text)
        return fehler[-1]

    def test_eine_vorgangsnummer_steht_darin(self):
        """Vorher stand dort ein Satz und sonst nichts."""
        self.assertRegex(self._fehlerzeile()["detail"], r"Vorgangsnummer [0-9a-f]{8}")

    def test_sie_sagt_auch_wohin_damit(self):
        self.assertIn("schwarzen Fenster", self._fehlerzeile()["detail"])

    def test_der_wortlaut_geht_nicht_hinaus(self):
        self.assertNotIn(MARKER, self._fehlerzeile()["detail"])

    def test_dieselbe_nummer_steht_im_protokoll(self):
        import re

        with self.assertLogs("jusperfect.web", level=logging.ERROR) as auf:
            zeile = self._fehlerzeile()
        nummer = re.search(r"Vorgangsnummer ([0-9a-f]{8})", zeile["detail"]).group(1)
        text = "\n".join(auf.output)
        self.assertIn(nummer, text)
        self.assertIn("fehler_im_strom", text)
        self.assertIn("ValueError", text)
        self.assertNotIn(MARKER, text)

    def test_die_zeile_hat_die_stufe_die_im_fenster_ankommt(self):
        with self.assertLogs("jusperfect.web", level=logging.ERROR) as auf:
            self._fehlerzeile()
        self.assertTrue(any(e.levelno >= logging.lastResort.level for e in auf.records))

    def test_ein_bekannter_fehler_behaelt_seinen_eigenen_satz(self):
        """Nur der unerwartete bekommt eine Nummer - sonst wäre sie wertlos."""
        from jusperfect.services.analyse import AnalyseFehler

        with mock.patch.object(type(self.d.analyse), "frage_stream",
                               side_effect=AnalyseFehler("Die Akte ist zu groß.")):
            antwort = self.c.post(f"/api/sitzungen/{self.sid}/frage/stream",
                                  json={"frage": "Worum geht es?"})
        zeilen = [json.loads(z) for z in antwort.text.splitlines() if z.strip()]
        fehler = [z for z in zeilen if z.get("type") == "fehler"][-1]
        self.assertEqual(fehler["detail"], "Die Akte ist zu groß.")
        self.assertNotIn("Vorgangsnummer", fehler["detail"])


class EinUnlesbarerDokumenttext(unittest.TestCase):
    def setUp(self) -> None:
        self.d, self.c, self.sid = _sitzung()
        # Der abgelegte Text wird zu etwas, das kein JSON ist.
        self.d.speicher.text_ablegen(self.sid, "D-101", "{kein JSON")

    def test_die_passagen_antworten_mit_einem_satz_statt_einer_nummer(self):
        antwort = self.c.get(f"/api/sitzungen/{self.sid}/passagen")
        self.assertEqual(antwort.status_code, 404, antwort.text)
        self.assertNotIn("Vorgangsnummer", antwort.text)
        self.assertIn("erneut laden", antwort.json()["fehler"])

    def test_der_satz_nennt_das_dokument_und_beruhigt_wegen_jurnodes(self):
        antwort = self.c.get(f"/api/sitzungen/{self.sid}/passagen")
        satz = antwort.json()["fehler"]
        self.assertIn("Mahnung", satz, "Ohne den Titel weiß niemand, welches.")
        self.assertIn("jur|nodes ist unberührt", satz)

    def test_es_wird_nicht_still_ausgelassen(self):
        """Die Belegpflicht beruht darauf, dass jede Aussage auf eine Passage zeigt.

        Ein Dokument, das aus dem Material verschwindet und in der Liste
        bleibt, wäre genau die Lücke, die dieses Programm verhindern soll.
        """
        antwort = self.c.get(f"/api/sitzungen/{self.sid}/passagen")
        self.assertNotEqual(antwort.status_code, 200,
                            "Dann wären die Passagen stillschweigend kleiner.")

    def test_das_protokoll_haelt_es_fest_ohne_den_text(self):
        with self.assertLogs("jusperfect.sitzung", level=logging.INFO) as auf:
            self.c.get(f"/api/sitzungen/{self.sid}/passagen")
        text = "\n".join(auf.output)
        self.assertIn("dokumenttext_unlesbar", text)
        self.assertNotIn("kein JSON", text)


if __name__ == "__main__":
    unittest.main()
