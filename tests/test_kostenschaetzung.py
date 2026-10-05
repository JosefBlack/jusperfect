"""Die Schätzung vor dem Absenden.

Sie darf nach oben abweichen, aber nicht nach unten: Eine zu niedrige Zahl
wäre schlimmer als gar keine, weil sie zu einer Entscheidung verleitet, die
teurer ausfällt als angekündigt.
"""

from __future__ import annotations

import unittest

from tests.hilfen import client, dienste, einstellungen

from jusperfect.services.kosten import ZEICHEN_JE_TOKEN, schaetzung

MODELL = "anthropic.claude-opus-5"
KURS = 0.92


class Schaetzung(unittest.TestCase):
    def test_mehr_zeichen_kosten_mehr(self):
        klein = schaetzung(MODELL, 5_000, KURS)
        gross = schaetzung(MODELL, 100_000, KURS)
        self.assertGreater(gross["erste_frage_eur"], klein["erste_frage_eur"])

    def test_weitere_frage_ist_guenstiger_als_die_erste(self):
        """Der Cache ist der Grund, an einer Akte zu bleiben."""
        s = schaetzung(MODELL, 100_000, KURS)
        self.assertLess(s["weitere_frage_eur"], s["erste_frage_eur"])

    def test_ohne_material_kostet_nur_die_antwort(self):
        s = schaetzung(MODELL, 0, KURS)
        self.assertEqual(s["zeichen"], 0)
        self.assertEqual(s["eingabe_tokens"], 0)
        self.assertGreater(s["erste_frage_eur"], 0)      # die Antwort kostet immer

    def test_negative_zeichen_werden_nicht_negativ_gerechnet(self):
        s = schaetzung(MODELL, -100, KURS)
        self.assertEqual(s["zeichen"], 0)
        self.assertEqual(s["eingabe_tokens"], 0)

    def test_guenstigeres_modell_ist_guenstiger(self):
        opus = schaetzung("anthropic.claude-opus-5", 50_000, KURS)
        haiku = schaetzung("anthropic.claude-haiku-4-5", 50_000, KURS)
        self.assertLess(haiku["erste_frage_eur"], opus["erste_frage_eur"])

    def test_schaetzung_unterschaetzt_die_tokenzahl_nicht(self):
        """Juristische Texte liegen unter der Näherung, also bei mehr Token.

        Der Wert muss so gewählt sein, dass die Schätzung eher zu hoch liegt –
        vier Zeichen je Token wären zu optimistisch.
        """
        self.assertLessEqual(ZEICHEN_JE_TOKEN, 3.5)


class UeberDieSchnittstelle(unittest.TestCase):
    def setUp(self) -> None:
        self.c = client(dienste(), "ra-weber")
        self.sid = self.c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]

    def test_ohne_dokumente_ist_die_schaetzung_leer(self):
        s = self.c.get(f"/api/sitzungen/{self.sid}").json()["kostenschaetzung"]
        self.assertEqual(s["dokumente"], 0)
        self.assertEqual(s["zeichen"], 0)

    def test_geladene_dokumente_erscheinen_in_der_schaetzung(self):
        antwort = self.c.post(f"/api/sitzungen/{self.sid}/dokumente",
                              json={"dokument_ids": ["D-001", "D-002"]}).json()
        s = antwort["kostenschaetzung"]
        self.assertEqual(s["dokumente"], 2)
        self.assertGreater(s["zeichen"], 0)
        self.assertGreater(s["erste_frage_eur"], 0)
        self.assertIn("budget_rest_eur", s)

    def test_der_umfang_bleibt_im_passagenbudget(self):
        """Mehr Text als das Budget kann gar nicht hinausgehen."""
        e = einstellungen(JUSPERFECT_MAX_PASSAGEN_ZEICHEN="500")
        c = client(dienste(einstellungen=e), "ra-weber")
        sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        antwort = c.post(f"/api/sitzungen/{sid}/dokumente",
                         json={"dokument_ids": ["D-001", "D-002", "D-004"]}).json()
        self.assertLessEqual(antwort["kostenschaetzung"]["zeichen"], 500)


if __name__ == "__main__":
    unittest.main()
