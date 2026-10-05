"""Mehrfachdialog: geprüfter, begrenzter und flüchtiger Sitzungskontext."""

import unittest

from jusperfect.providers.base import Nutzung, ProviderAntwort
from jusperfect.config import KonfigurationsFehler
from tests.hilfen import client, dienste, einstellungen


class MitschriftProvider:
    modell_id = "dialog-test"

    def __init__(self, antworten):
        self.antworten = list(antworten)
        self.aufrufe = []

    def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        self.aufrufe.append({"system": system, "material": material, "aufgabe": aufgabe})
        return ProviderAntwort(
            text=self.antworten.pop(0), nutzung=Nutzung(), modell=self.modell_id,
        )


class Mehrfachdialog(unittest.TestCase):
    def _sitzung(self, provider, **env):
        d = dienste(provider=provider, einstellungen=einstellungen(**env))
        c = client(d)
        sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
        return c, sid

    def test_rueckfrage_erhaelt_geprueften_verlauf_und_originalbeleg(self):
        p = MitschriftProvider([
            "Der Mandant schildert den Unfall. [Q: D1-S1-P1]",
            "Die frühere Angabe stammt vom Mandanten. [Q: D1-S1-P1]",
        ])
        c, sid = self._sitzung(p)
        self.assertEqual(c.post(f"/api/sitzungen/{sid}/frage", json={"frage": "Was geschah?"}).status_code, 200)
        self.assertEqual(c.post(f"/api/sitzungen/{sid}/frage", json={"frage": "Von wem stammt diese Angabe?"}).status_code, 200)

        self.assertNotIn("Früherer Dialog", p.aufrufe[0]["material"])
        self.assertIn("FRAGE: Was geschah?", p.aufrufe[1]["material"])
        self.assertIn("GEPRÜFTE ANTWORT: Der Mandant schildert", p.aufrufe[1]["material"])
        self.assertIn("### Passage D1-S1-P1", p.aufrufe[1]["material"])
        dialog = c.get(f"/api/sitzungen/{sid}").json()["sitzung"]["dialog"]
        self.assertEqual([x["frage"] for x in dialog], ["Was geschah?", "Von wem stammt diese Angabe?"])

    def test_verlauf_ist_begrenzt(self):
        p = MitschriftProvider([f"Antwort {nr}. [Q: D1-S1-P1]" for nr in range(3)])
        c, sid = self._sitzung(p, JUSPERFECT_DIALOG_MAX_RUNDEN="2")
        for nr in range(3):
            c.post(f"/api/sitzungen/{sid}/frage", json={"frage": f"Frage {nr}?"})
        dialog = c.get(f"/api/sitzungen/{sid}").json()["sitzung"]["dialog"]
        self.assertEqual([x["frage"] for x in dialog], ["Frage 1?", "Frage 2?"])

    def test_unbelegte_antwort_wird_nicht_gemerkt(self):
        p = MitschriftProvider(["Erfundene Aussage. [Q: D9-S9-P9]"])
        c, sid = self._sitzung(p)
        c.post(f"/api/sitzungen/{sid}/frage", json={"frage": "Was wurde erfunden?"})
        self.assertEqual(c.get(f"/api/sitzungen/{sid}").json()["sitzung"]["dialog"], [])

    def test_unbrauchbare_dialoggrenze_wird_abgewiesen(self):
        with self.assertRaises(KonfigurationsFehler):
            einstellungen(JUSPERFECT_DIALOG_MAX_RUNDEN="0")


if __name__ == "__main__":
    unittest.main()
