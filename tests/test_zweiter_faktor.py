"""Der zweite Faktor beim Öffnen von jusperfect.

Aus der Kanzlei am 15.10.2026: „Ich möchte für die Programmöffnung jusperfect
und die Möglichkeit der Einrichtung einer 2-Faktor-Authentifizierung."

Der Anlass steht in der Folgenabschätzung, Risiko **R7** — dem einzigen, das
dort auf „hoch" steht: Die Anmeldung ist im Laufwerksbetrieb kein Kennwort,
sondern eine Kennung. Wer am Rechner sitzt, kann eine andere eintragen.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.hilfen import client, dienste, einstellungen

from jusperfect.security.zweiter_faktor import (
    Bestaetigungen, Geheimnisablage, code_jetzt, code_pruefen, einrichtungslink,
    geheimnis_erzeugen,
)

NUTZER_KOPF = {"X-Jusperfect-Nutzer": "ra-weber"}


class DasEinmalkennwort(unittest.TestCase):
    """TOTP nach RFC 6238 — dieselbe Technik wie bei der Bank."""

    def test_der_eigene_code_stimmt(self):
        g = geheimnis_erzeugen()
        self.assertTrue(code_pruefen(g, code_jetzt(g)))

    def test_ein_fremder_code_stimmt_nicht(self):
        self.assertFalse(code_pruefen(geheimnis_erzeugen(), code_jetzt(geheimnis_erzeugen())))

    def test_eine_uhr_die_etwas_abweicht_stoert_nicht(self):
        """In einer Kanzlei ist eine um Sekunden abweichende Uhr der Normalfall."""
        g = geheimnis_erzeugen()
        self.assertTrue(code_pruefen(g, code_jetzt(g, 1_000_000), 1_000_000 + 25))
        self.assertTrue(code_pruefen(g, code_jetzt(g, 1_000_000), 1_000_000 - 25))

    def test_eine_uhr_die_weit_abweicht_stoert_sehr_wohl(self):
        g = geheimnis_erzeugen()
        self.assertFalse(code_pruefen(g, code_jetzt(g, 1_000_000), 1_000_000 + 600))

    def test_nur_sechsstellige_zahlen(self):
        g = geheimnis_erzeugen()
        for unfug in ("", "12345", "1234567", "abcdef", None):
            self.assertFalse(code_pruefen(g, unfug))

    def test_der_link_traegt_das_geheimnis_und_den_namen(self):
        g = geheimnis_erzeugen()
        link = einrichtungslink("ra-weber", g)
        self.assertTrue(link.startswith("otpauth://totp/"))
        self.assertIn(g, link)
        self.assertIn("ra-weber", link)


class DieGeheimnisseLiegenNichtInDerNutzerdatei(unittest.TestCase):
    """Die Nutzerdatei wird von Hand gepflegt und liegt in der Sicherung."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.ablage = Geheimnisablage(Path(tmp.name) / "zweiter-faktor.json")

    def test_merken_und_lesen(self):
        g = geheimnis_erzeugen()
        self.ablage.merken("ra-weber", g)
        self.assertEqual(self.ablage.geheimnis("ra-weber"), g)

    def test_vergessen(self):
        self.ablage.merken("ra-weber", geheimnis_erzeugen())
        self.ablage.vergessen("ra-weber")
        self.assertFalse(self.ablage.eingerichtet("ra-weber"))

    def test_eine_kaputte_datei_sperrt_niemanden_aus_dem_programm(self):
        self.ablage.pfad.write_text("{kein json", encoding="utf-8")
        self.assertFalse(self.ablage.eingerichtet("ra-weber"))


class EinCodeGiltEinmal(unittest.TestCase):
    def test_ein_benutzter_code_ist_verbraucht(self):
        b = Bestaetigungen()
        b.bestaetigen("ra-weber", "123456", 1000.0)
        self.assertTrue(b.schon_benutzt("ra-weber", "123456", 1000.0))

    def test_ein_anderer_nutzer_ist_nicht_betroffen(self):
        b = Bestaetigungen()
        b.bestaetigen("ra-weber", "123456", 1000.0)
        self.assertFalse(b.schon_benutzt("refa-lorenz", "123456", 1000.0))

    def test_die_bestaetigung_laeuft_ab(self):
        b = Bestaetigungen(gueltig_sekunden=60)
        b.bestaetigen("ra-weber", "123456", 1000.0)
        self.assertTrue(b.gilt("ra-weber", 1030.0))
        self.assertFalse(b.gilt("ra-weber", 1100.0))


class AusgeschaltetAendertSichNichts(unittest.TestCase):
    """Voreingestellt ist aus: Ein geschuetzter Einzelplatz soll nicht zu
    einem zweiten Geraet gezwungen werden."""

    def test_ohne_faktor_geht_alles_wie_bisher(self):
        c = client(dienste(einstellungen=einstellungen()))
        self.assertEqual(c.get("/api/akten", headers=NUTZER_KOPF).status_code, 200)

    def test_der_stand_sagt_dass_keiner_noetig_ist(self):
        c = client(dienste(einstellungen=einstellungen()))
        stand = c.get("/api/anmeldung/zweiter-faktor", headers=NUTZER_KOPF).json()
        self.assertFalse(stand["noetig"])


class EingeschaltetSperrtErDasProgramm(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.datei = Path(tmp.name) / "zweiter-faktor.json"
        self.e = einstellungen(JUSPERFECT_ZWEITER_FAKTOR="an",
                               JUSPERFECT_ZWEITER_FAKTOR_DATEI=str(self.datei))
        self.d = dienste(einstellungen=self.e)
        self.c = client(self.d)

    def test_ohne_bestaetigung_kommt_428(self):
        """428 und nicht 401: Nicht „wer bist du", sondern „da fehlt noch was"."""
        self.assertEqual(self.c.get("/api/akten", headers=NUTZER_KOPF).status_code, 428)

    def test_auch_jeder_andere_weg_ist_zu(self):
        """Ein halb geschuetztes Programm ist keines."""
        for weg in ("/api/akten", "/api/status", "/api/aufbewahrung/faellig"):
            with self.subTest(weg=weg):
                self.assertEqual(self.c.get(weg, headers=NUTZER_KOPF).status_code, 428)

    def test_der_weg_zur_einrichtung_bleibt_offen(self):
        """Sonst kaeme man nie dahin, den Faktor zu zeigen."""
        self.assertEqual(
            self.c.get("/api/anmeldung/zweiter-faktor", headers=NUTZER_KOPF).status_code, 200)

    def test_einrichten_bestaetigen_und_dann_geht_es(self):
        auf = self.c.post("/api/anmeldung/zweiter-faktor/einrichten", headers=NUTZER_KOPF).json()
        self.assertIn("geheimnis", auf)
        code = code_jetzt(auf["geheimnis"])
        ok = self.c.post("/api/anmeldung/zweiter-faktor/bestaetigen",
                         json={"code": code}, headers=NUTZER_KOPF)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(self.c.get("/api/akten", headers=NUTZER_KOPF).status_code, 200)

    def test_ein_falscher_code_richtet_nichts_ein(self):
        """Sonst sperrte ein misslungener Scan den Zugang aus."""
        self.c.post("/api/anmeldung/zweiter-faktor/einrichten", headers=NUTZER_KOPF)
        ab = self.c.post("/api/anmeldung/zweiter-faktor/bestaetigen",
                         json={"code": "000000"}, headers=NUTZER_KOPF)
        self.assertEqual(ab.status_code, 401)
        self.assertFalse(Geheimnisablage(self.datei).eingerichtet("ra-weber"))

    def test_ein_code_oeffnet_nur_einmal(self):
        """Ohne das waere ein abgelesener Code dreissig Sekunden ein Nachschluessel."""
        auf = self.c.post("/api/anmeldung/zweiter-faktor/einrichten", headers=NUTZER_KOPF).json()
        code = code_jetzt(auf["geheimnis"])
        self.c.post("/api/anmeldung/zweiter-faktor/bestaetigen",
                    json={"code": code}, headers=NUTZER_KOPF)
        zweite = self.c.post("/api/anmeldung/zweiter-faktor/pruefen",
                             json={"code": code}, headers=NUTZER_KOPF)
        self.assertEqual(zweite.status_code, 401)
        self.assertIn("schon verwendet", str(zweite.json()))

    def test_zweimal_einrichten_geht_nicht(self):
        auf = self.c.post("/api/anmeldung/zweiter-faktor/einrichten", headers=NUTZER_KOPF).json()
        self.c.post("/api/anmeldung/zweiter-faktor/bestaetigen",
                    json={"code": code_jetzt(auf["geheimnis"])}, headers=NUTZER_KOPF)
        noch = self.c.post("/api/anmeldung/zweiter-faktor/einrichten", headers=NUTZER_KOPF)
        self.assertEqual(noch.status_code, 409)


if __name__ == "__main__":
    unittest.main()
