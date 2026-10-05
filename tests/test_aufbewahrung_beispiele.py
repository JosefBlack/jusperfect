"""Die Beispielfälle für die Ansicht „Aufbewahrung" landen wirklich dort.

Aus der Kanzlei: „So ganz versteh ich die Aufbewahrung noch nicht. Kannst Du
mir mal zum Beispiel Test machen, die genau dort hineinkommen würden?"

Dafür gibt es `werkzeug/aufbewahrung_beispiele.py`. Es baut sechs
Arbeitsbereiche nach, die im Alltag selten und dann unbemerkt entstehen. Ein
Werkzeug zum Kennenlernen ist aber nur so viel wert wie seine Zusage: Wenn es
sagt „dieser Fall wird als abschlussreif ohne Vormerkung erscheinen", dann muss
er genau so erscheinen. Sonst lernt man daran das Falsche.

Deshalb prüft diese Datei jeden der sechs Fälle gegen den echten
Aufsichtsdienst – denselben, den die Oberfläche befragt.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkzeug"))

from jusperfect.security.identitaet import Identitaet  # noqa: E402
from jusperfect.services.aufsicht import BEFUND_TEXT, SCHRITT_TEXT  # noqa: E402
from tests.hilfen import dienste, einstellungen  # noqa: E402

RA = Identitaet(nutzer_id="ra-weber", anzeigename="RA Dr. Weber", gruppen=("alle-akten",))


class JederBefundSagtAuchWasZuTunIst(unittest.TestCase):
    """Ein Befund ohne nächsten Schritt ist nur eine Beunruhigung."""

    def test_zu_jedem_befund_gibt_es_einen_schritt(self):
        self.assertEqual(set(BEFUND_TEXT), set(SCHRITT_TEXT))

    def test_kein_satz_ist_leer_oder_technisch(self):
        for kennung, text in {**BEFUND_TEXT, **SCHRITT_TEXT}.items():
            with self.subTest(befund=kennung):
                self.assertGreater(len(text), 30, "Ein halber Satz hilft niemandem.")
                self.assertNotIn("retention", text.lower())
                self.assertNotIn("_", text)


class DieBeispieleLandenWoSieSollen(unittest.TestCase):
    ERWARTET = {
        "MV-2026-0101": [],
        "VU-2026-0102": ["abschlussreif_ohne_vormerkung"],
        "AR-2026-0103": ["abschluss_vorgemerkt"],
        "BA-2025-0104": ["loeschung_faellig"],
        "SC-2026-0105": ["status_unbekannt"],
        "VU-2024-0106": ["akte_fehlt"],
    }

    def setUp(self) -> None:
        import aufbewahrung_beispiele

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        ziel = Path(tmp.name)
        aufbewahrung_beispiele.erzeugen(ziel)
        e = einstellungen(
            JUSPERFECT_FIXTURE_PFAD=str(ziel / "akten"),
            JUSPERFECT_GEDAECHTNIS="lokal",
            JUSPERFECT_GEDAECHTNIS_PFAD=str(ziel / "gedaechtnis"),
        )
        self.d = dienste(einstellungen=e)
        self.uebersicht = self.d.aufsicht.uebersicht(RA)
        self.nach_akte = {x["akte_id"]: x for x in self.uebersicht["eintraege"]}

    def test_alle_sechs_erscheinen(self):
        self.assertEqual(set(self.nach_akte), set(self.ERWARTET))

    def test_jeder_fall_traegt_genau_seinen_befund(self):
        for akte, befunde in self.ERWARTET.items():
            with self.subTest(akte=akte):
                self.assertEqual(self.nach_akte[akte]["befunde"], befunde)

    def test_fuenf_verlangen_eine_entscheidung_und_einer_nicht(self):
        self.assertEqual(self.uebersicht["handlungsbedarf"], 5)
        self.assertEqual(self.uebersicht["arbeitsbereiche"], 6)
        self.assertFalse(self.nach_akte["MV-2026-0101"]["handlungsbedarf"],
                         "Ein laufendes Mandat darf hier nicht als Aufgabe erscheinen.")

    def test_was_zu_entscheiden_ist_steht_oben(self):
        reihenfolge = [x["handlungsbedarf"] for x in self.uebersicht["eintraege"]]
        self.assertEqual(reihenfolge, sorted(reihenfolge, reverse=True))

    def test_jeder_eintrag_nennt_befund_und_schritt(self):
        for akte, befunde in self.ERWARTET.items():
            eintrag = self.nach_akte[akte]
            with self.subTest(akte=akte):
                self.assertEqual(len(eintrag["hinweise"]), len(befunde))
                self.assertEqual(len(eintrag["schritte"]), len(befunde))

    def test_die_uebersicht_traegt_keinen_akteninhalt(self):
        """Sie führt Akten zusammen – Inhalte hätten hier nichts zu suchen."""
        text = str(self.uebersicht)
        for inhalt in ("erfundener Beispieltext", "Aktenvermerk", "Worum geht es"):
            self.assertNotIn(inhalt, text, inhalt)

    def test_die_faellige_loeschung_ist_als_faellig_gekennzeichnet(self):
        self.assertTrue(self.nach_akte["BA-2025-0104"]["faellig"])
        self.assertFalse(self.nach_akte["AR-2026-0103"]["faellig"],
                         "Eine laufende Frist ist noch nicht fällig.")

    def test_ohne_verwaltungsrecht_gibt_es_die_uebersicht_nicht(self):
        from jusperfect.security.berechtigungen import ZugriffVerweigert

        refa = Identitaet(nutzer_id="refa-lorenz", anzeigename="ReFa Lorenz", gruppen=())
        with self.assertRaises(ZugriffVerweigert):
            self.d.aufsicht.uebersicht(refa)


if __name__ == "__main__":
    unittest.main()
