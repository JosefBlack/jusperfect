"""Beim Schließen sichern – und sagen, was gesichert ist.

Aus der Kanzlei: „beim schließen sollte das bearbeitete gespeichert werden und
anhand einer meldung kenntlich gemacht werden."

Gespeichert wurde auch vorher schon, und zwar sofort: Jede Ergänzung des
Lebenssachverhalts, jede Chronologiezeile und jede geprüfte Antwort geht in dem
Augenblick in den Speicher, in dem sie entsteht. Das ist die richtige
Reihenfolge - wer erst beim Schließen speichert, verliert bei einem Absturz den
halben Vormittag.

Nur wusste der Bearbeiter davon nichts. Die Meldung sagte „Sitzung geschlossen,
temporäre Texte gelöscht" - drei Wörter über das Löschen, keines über das
Bleiben. Jetzt wird beim Schließen noch einmal abgelegt (damit ein
Schreibfehler hier auffällt und nicht erst am nächsten Morgen), und die Meldung
nennt, was im Aktengedächtnis liegt: mit Zahlen, nicht als Zusage.

Was ausdrücklich nicht gespeichert wird - Entwürfe und Eingangsprüfungen -,
steht ebenfalls in der Meldung. Ein Programm, das verschweigt, was es nicht
aufhebt, ist gefährlicher als eines, das nichts aufhebt.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import tempfile

from tests.hilfen import client, dienste, einstellungen

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"
JS = (STATISCH / "app.js").read_text(encoding="utf-8")
HTML = (STATISCH / "index.html").read_text(encoding="utf-8")


class DerWeg(unittest.TestCase):
    def test_erst_sichern_dann_schliessen(self):
        """Andersherum wäre die Sitzung weg, bevor der Speicher geantwortet hat."""
        block = re.search(r"async function sitzungSchliessen\(\) \{(.*?)\n\}", JS, re.S).group(1)
        sichern = block.index("gedaechtnis/sichern")
        loeschen = block.index('api("DELETE", `/api/sitzungen/')
        self.assertLess(sichern, loeschen)

    def test_ein_schreibfehler_wird_nicht_verschluckt(self):
        block = re.search(r"async function sitzungSchliessen\(\) \{(.*?)\n\}", JS, re.S).group(1)
        self.assertIn("fehler = e.message", block)
        self.assertIn("schlussHinweisZeigen(schlussmeldung(bericht, fehler), !!fehler)", block)

    def test_die_meldung_bleibt_auf_der_startseite_stehen(self):
        """Die Einblendung unten rechts ist nach drei Sekunden weg."""
        self.assertIn('id="schluss-hinweis"', HTML)
        self.assertIn("schlussHinweisZeigen(schlussmeldung(", JS)
        # Und sie verschwindet, sobald die nächste Akte geöffnet wird.
        auf = re.search(r"async function akteOeffnen\(akteId\) \{(.*?)\n\}", JS, re.S).group(1)
        self.assertIn('schlussHinweisZeigen("")', auf)


class WasDieMeldungSagt(unittest.TestCase):
    def setUp(self):
        self.block = re.search(r"function schlussmeldung\(bericht, fehler\) \{(.*?)\n\}",
                               JS, re.S).group(1)

    def test_sie_nennt_zahlen_statt_zusagen(self):
        for stueck in ("Lebenssachverhalt", "Dokument(e)", "Zeile(n) Chronologie",
                       "geprüfte Antwort(en)"):
            self.assertIn(stueck, self.block, stueck)

    def test_sie_nennt_auch_das_nicht_gespeicherte(self):
        self.assertIn("Entwürfe und Eingangsprüfungen werden nicht gespeichert.", self.block)

    def test_ohne_gedaechtnis_behauptet_sie_nichts(self):
        self.assertIn("das Gedächtnis ist nicht aktiviert", self.block)

    def test_die_zahlen_kommen_aus_dem_speicher_nicht_aus_der_oberflaeche(self):
        """`bericht` ist die Antwort des Servers, nicht der Stand im Browser."""
        self.assertNotIn("sitzung.gedaechtnis", self.block)
        self.assertIn("bericht.eintraege", self.block)


class DerAufruf(unittest.TestCase):
    """Der Endpunkt selbst, an einer laufenden Demo-Sitzung gemessen."""

    def setUp(self):
        self._ged = tempfile.TemporaryDirectory()
        e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=self._ged.name)
        self.c = client(dienste(einstellungen=e))

    def tearDown(self):
        self._ged.cleanup()

    def _sitzung(self, akte="VU-2026-0042"):
        return self.c.post("/api/sitzungen", json={"akte_id": akte}).json()

    def test_ohne_gedaechtnisinhalt_meldet_er_ehrlich_nichts(self):
        s = self._sitzung()
        antwort = self.c.post(f"/api/sitzungen/{s['sitzung']['id']}/gedaechtnis/sichern")
        self.assertEqual(antwort.status_code, 200)
        self.assertFalse(antwort.json()["gesichert"])
        self.assertTrue(antwort.json()["aktiv"])

    def test_mit_inhalt_meldet_er_was_liegt(self):
        s = self._sitzung()
        ids = [d["id"] for d in s["dokumente"][:2]]
        self.c.post(f"/api/sitzungen/{s['sitzung']['id']}/dokumente", json={"dokument_ids": ids})
        antwort = self.c.post(f"/api/sitzungen/{s['sitzung']['id']}/gedaechtnis/sichern").json()
        self.assertTrue(antwort["gesichert"])
        self.assertEqual(len(antwort["eintraege"]), 2)
        self.assertEqual(antwort["aktenzeichen"], "042/26 VU")

    def test_sichern_verschiebt_den_zeitpunkt_der_letzten_aenderung_nicht(self):
        """„aktualisiert am" soll sagen, wann zuletzt etwas hinzukam –
        nicht, wann zuletzt jemand das Fenster zugemacht hat."""
        s = self._sitzung()
        self.c.post(f"/api/sitzungen/{s['sitzung']['id']}/dokumente", json={"dokument_ids": [s["dokumente"][0]["id"]]})
        vorher = self.c.get(f"/api/sitzungen/{s['sitzung']['id']}/gedaechtnis").json()["aktualisiert_am"]
        nachher = self.c.post(f"/api/sitzungen/{s['sitzung']['id']}/gedaechtnis/sichern").json()["aktualisiert_am"]
        self.assertEqual(vorher, nachher)
