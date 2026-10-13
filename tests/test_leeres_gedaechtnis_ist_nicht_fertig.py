"""„Nichts offen" heißt zweierlei – und die beiden sind das Gegenteil voneinander.

Aus der Kanzlei am 13.10.2026, unmittelbar nach dem Verwerfen:

    Gedächtnis wurde verworfen, dauerte 10 Sekunden – Aktengedächtnis ist
    leer – Taste „Akte einlesen" führt zu dem Ergebnis: Akte ist schon
    eingelesen.

`offene_dokumente` zählt, was **im Gedächtnis liegt** und noch nicht
verarbeitet ist. Ist das Gedächtnis leer, ist nichts offen – und die
Oberfläche hatte für diese Null nur **einen** Satz:

```js
if (!offenAmAnfang) { melden("Es ist schon alles eingelesen."); return; }
```

Also „fertig", während in Wahrheit noch gar nichts angefangen hatte. Und zwar
genau nach einem Verwerfen – also genau dann, wenn der Bearbeiter weitermachen
will. Der Weg war nicht verbaut; er war nur mit einem Satz zugestellt, der das
Gegenteil sagte.

**Was wirklich gilt:** Dokumente kommen durch das **Anhaken** ins Gedächtnis,
nicht durch das Einlesen. Das Einlesen baut aus ihnen den Lebenssachverhalt.
Wer das nicht weiß, klickt auf „Akte einlesen" und wird weggeschickt.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.hilfen import client, dienste, einstellungen

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"
AKTE = "MV-2026-0007"


class DieBeidenNullenWerdenUnterschieden(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        js = (STATISCH / "app.js").read_text(encoding="utf-8")
        teil = js[js.index("async function gedaechtnisEinlesen"):]
        cls.funktion = teil[:teil.index("\n}\n")]

    def test_das_leere_gedaechtnis_hat_einen_eigenen_zweig(self):
        self.assertIn("if (!gesamt) {", self.funktion)

    def test_er_kommt_VOR_dem_satz_vom_schon_eingelesen(self):
        """Sonst greift der falsche zuerst – das war der ganze Fehler."""
        self.assertLess(self.funktion.index("if (!gesamt) {"),
                        self.funktion.index("schon alles eingelesen"))

    def test_er_sagt_was_zu_tun_ist_und_nicht_dass_es_fertig_sei(self):
        zweig = self.funktion[self.funktion.index("if (!gesamt) {"):]
        zweig = zweig[:zweig.index("if (!offenAmAnfang)")]
        self.assertIn("noch kein Dokument", zweig)
        self.assertIn("Anhaken", zweig)
        self.assertNotIn("schon alles eingelesen", zweig)

    def test_der_satz_vom_schon_eingelesen_bleibt_fuer_seinen_fall(self):
        """Er ist richtig – nur eben nicht für ein leeres Gedächtnis."""
        self.assertIn('melden("Es ist schon alles eingelesen.")', self.funktion)

    def test_das_fenster_geht_erst_nach_der_rueckfrage_auf(self):
        """Es ist ein modaler Dialog und legte sich sonst über die Erklärung."""
        zweig = self.funktion[self.funktion.index("if (!gesamt) {"):]
        zweig = zweig[:zweig.index("if (!offenAmAnfang)")]
        self.assertLess(zweig.index("confirm("), zweig.index("gedaechtnisExplorerOeffnen"))


class SoSiehtDerStandNachDemVerwerfenAus(unittest.TestCase):
    """Die Zahlen, auf die sich die Oberfläche dabei stützt."""

    def test_nach_dem_verwerfen_ist_nichts_vorhanden_und_nichts_offen(self):
        with tempfile.TemporaryDirectory() as tmp:
            e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal",
                              JUSPERFECT_GEDAECHTNIS_PFAD=tmp)
            d = dienste(einstellungen=e)
            c = client(d)
            sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
            c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-101"]})
            c.delete(f"/api/akten/{AKTE}/gedaechtnis?sitzung={sid}")

            g = c.get(f"/api/sitzungen/{sid}").json()["gedaechtnis"]
            self.assertFalse(g["vorhanden"])
            self.assertEqual(g["eintraege"], [])
            # Genau diese Null hat die Oberflaeche als "fertig" gelesen.
            self.assertEqual(g.get("offene_dokumente", 0), 0)

    def test_mit_dokumenten_im_gedaechtnis_sind_sie_offen(self):
        """Die Gegenprobe: Dann ist die Null keine Null."""
        with tempfile.TemporaryDirectory() as tmp:
            e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal",
                              JUSPERFECT_GEDAECHTNIS_PFAD=tmp)
            d = dienste(einstellungen=e)
            c = client(d)
            sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
            c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-101"]})

            g = c.get(f"/api/sitzungen/{sid}").json()["gedaechtnis"]
            self.assertTrue(g["vorhanden"])
            self.assertEqual(len(g["eintraege"]), 1)
            self.assertEqual(g["offene_dokumente"], 1)


if __name__ == "__main__":
    unittest.main()
