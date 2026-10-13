"""Status 405 – und was der Server selbst dazu sagt.

Aus der Kanzlei am 13.10.2026, gemessen mit `AKTE-PRUEFEN.bat` am neuen
Rechner::

    3× JurNodesFehler (http_adapter.py:841) - jur|nodes antwortete auf
       GET /record mit Status 405.
    1× JurNodesFehler (http_adapter.py:919) - jur|nodes antwortete auf
       POST /correspondence/search mit Status 405.

**405 heißt „Verfahren nicht erlaubt"** – der Pfad ist da, nur das Verfahren
passt nicht. Nachgesehen in der Beschreibung des Herstellers, die seit dem
05.10.2026 im Programmordner liegt (`schnittstelle/jurnodes-api-1.0.2.json`):

| Pfad | Verfahren laut Hersteller | Was wir senden |
|---|---|---|
| `/record` | GET, POST | GET |
| `/correspondence/search` | POST | POST |

Beides stimmt also. Und es ist auch kein Rechteproblem: Ein fehlendes Recht
(`read:records`, `search:correspondence`) gäbe 401 oder 403, und die haben hier
ihren eigenen Satz.

Welches Verfahren der Server stattdessen will, sagt er bei 405 nach RFC 9110
**selbst** – im `Allow`-Kopf. Der kostet nichts: Er liegt in der Antwort, die
wir ohnehin schon haben.

**Ausprobiert wird nichts.** `POST /record` wäre das naheliegende zweite
Verfahren und heißt in der Beschreibung „Erzeugen & Update". Ein Programm, das
nicht schreibt, probiert so etwas nicht aus – auch nicht zur Fehlersuche.
"""

from __future__ import annotations

import json
import pathlib
import unittest

import httpx

from jusperfect.jurnodes.base import JurNodesFehler
from tests.test_eakte import AKTE, _Server, _adapter

BESCHREIBUNG = (pathlib.Path(__file__).resolve().parent.parent
                / "schnittstelle" / "jurnodes-api-1.0.2.json")


class _ServerMit405(_Server):
    """Antwortet auf alles mit 405 - mit oder ohne ``Allow``."""

    def __init__(self, allow: str | None = "POST") -> None:
        super().__init__()
        self.allow = allow

    def __call__(self, anfrage: httpx.Request) -> httpx.Response:
        kopf = {"allow": self.allow} if self.allow is not None else {}
        return httpx.Response(405, json={}, headers=kopf)


class DerServerSagtEsSelbst(unittest.TestCase):
    def _fehler(self, allow: str | None) -> str:
        adapter = _adapter(_ServerMit405(allow))
        with self.assertRaises(JurNodesFehler) as gefangen:
            adapter.akte(AKTE)
        return str(gefangen.exception)

    def test_der_allow_kopf_steht_in_der_meldung(self):
        satz = self._fehler("POST, OPTIONS")
        self.assertIn("405", satz)
        self.assertIn("POST, OPTIONS", satz)

    def test_ohne_allow_kopf_bleibt_die_meldung_wie_bisher(self):
        satz = self._fehler(None)
        self.assertIn("405", satz)
        self.assertNotIn("erlaubt:", satz)

    def test_der_pfad_steht_weiterhin_darin(self):
        """Ohne ihn sagt „Status 405" nicht, WELCHER Aufruf (24.09.2026)."""
        self.assertIn("/record", self._fehler("POST"))

    def test_ein_fremder_server_schreibt_keinen_text_in_unsere_meldung(self):
        """Der Kopf kommt von aussen. Durch darf nur eine Verfahrensliste."""
        satz = self._fehler("POST <script>alert(1)</script> Mandantin Zeisig")
        self.assertNotIn("<", satz)
        self.assertNotIn("Zeisig", satz)
        self.assertNotIn("(", satz.split("erlaubt:")[-1])

    def test_ein_langer_kopf_wird_gekuerzt(self):
        satz = self._fehler("POST, " * 200)
        self.assertLess(len(satz), 300)


class WirSendenWasDerHerstellerBeschreibt(unittest.TestCase):
    """Die Gegenprobe zu „es liegt an uns"."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.pfade = json.loads(BESCHREIBUNG.read_text(encoding="utf-8"))["paths"]

    def _verfahren(self, pfad: str) -> set[str]:
        return {v.upper() for v in self.pfade[pfad]
                if v in ("get", "post", "put", "delete", "patch")}

    def test_record_wird_mit_einem_beschriebenen_verfahren_geholt(self):
        self.assertIn("GET", self._verfahren("/record"))

    def test_die_korrespondenz_wird_mit_dem_einzigen_verfahren_gesucht(self):
        self.assertEqual(self._verfahren("/correspondence/search"), {"POST"})


class NichtsWirdAusprobiert(unittest.TestCase):
    def test_post_record_heisst_erzeugen_und_wird_nirgends_gesendet(self):
        """Das naheliegende zweite Verfahren ist genau das, was nie passieren darf."""
        pfade = json.loads(BESCHREIBUNG.read_text(encoding="utf-8"))["paths"]
        self.assertIn("Erzeugt", pfade["/record"]["post"].get("description", ""))

        quelle = (pathlib.Path(__file__).resolve().parent.parent / "jusperfect"
                  / "jurnodes" / "http_adapter.py").read_text(encoding="utf-8")
        self.assertNotIn('_post(self._endpunkte.akte', quelle)
        self.assertNotIn('"POST", self._endpunkte.akte', quelle)


if __name__ == "__main__":
    unittest.main()
