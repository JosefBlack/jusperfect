"""Die Aufsicht über alle Arbeitsbereiche: sichtbar machen, was ein Mensch entscheiden muss."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.hilfen import NUTZER, einstellungen

from jusperfect.domain.models import Akte, Aktengedaechtnis
from jusperfect.jurnodes.base import AkteNichtGefunden, JurNodesFehler
from jusperfect.security.berechtigungen import DateiBerechtigungen, ZugriffVerweigert
from jusperfect.security.identitaet import Identitaet
from jusperfect.services.aufsicht import Aufsichtsdienst
from jusperfect.services.gedaechtnis import Gedaechtnisdienst
from jusperfect.gedaechtnis.lokal import LokalerGedaechtnisSpeicher
from jusperfect.speicher.lokal import LokalerSpeicher


class _Adapter:
    def __init__(self) -> None:
        self.status: dict[str, str] = {}
        self.fehlend: set[str] = set()
        self.stoerung = False

    def akte(self, akte_id: str) -> Akte:
        if self.stoerung:
            raise JurNodesFehler("jurnodes ist nicht erreichbar.")
        if akte_id in self.fehlend:
            raise AkteNichtGefunden(f"Akte {akte_id} nicht gefunden.")
        return Akte(id=akte_id, aktenzeichen=akte_id, bezeichnung="Test",
                    status=self.status.get(akte_id, "laufend"))


class Aufsicht(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp.name)
        self.gspeicher = LokalerGedaechtnisSpeicher(Path(tmp.name))
        self.gedaechtnis = Gedaechtnisdienst(self.gspeicher, LokalerSpeicher(), None, e)
        self.adapter = _Adapter()
        self.dienst = Aufsichtsdienst(self.gedaechtnis, self.adapter,
                                      DateiBerechtigungen.aus_datei(NUTZER))
        self.ich = Identitaet(nutzer_id="ra-weber")            # darf alle Akten

    def _anlegen(self, akte_id: str, **felder) -> None:
        self.gspeicher.ablegen(Aktengedaechtnis(akte_id=akte_id, aktenzeichen=akte_id, **felder))

    def test_uebersicht_ist_der_verwaltung_vorbehalten(self):
        self._anlegen("A-1")
        with self.assertRaises(ZugriffVerweigert):
            self.dienst.uebersicht(Identitaet(nutzer_id="refa-lorenz"))   # nur eine Akte

    def test_laufende_akte_erzeugt_keinen_handlungsbedarf(self):
        self._anlegen("A-1")
        uebersicht = self.dienst.uebersicht(self.ich)
        self.assertEqual(uebersicht["arbeitsbereiche"], 1)
        self.assertEqual(uebersicht["handlungsbedarf"], 0)
        self.assertEqual(uebersicht["eintraege"][0]["befunde"], [])

    def test_verwaister_arbeitsbereich_faellt_auf(self):
        self._anlegen("A-1")
        self.adapter.fehlend.add("A-1")
        eintrag = self.dienst.uebersicht(self.ich)["eintraege"][0]
        self.assertIn("akte_fehlt", eintrag["befunde"])
        self.assertTrue(eintrag["handlungsbedarf"])

    def test_stoerung_und_unbekannter_status_werden_gemeldet(self):
        self._anlegen("A-1")
        self.adapter.stoerung = True
        self.assertIn("jurnodes_nicht_erreichbar",
                      self.dienst.uebersicht(self.ich)["eintraege"][0]["befunde"])
        self.adapter.stoerung = False
        self.adapter.status["A-1"] = "unbekannt"
        self.assertIn("status_unbekannt",
                      self.dienst.uebersicht(self.ich)["eintraege"][0]["befunde"])

    def test_abgeschlossene_akte_ohne_vormerkung_faellt_auf(self):
        self._anlegen("A-1")
        self.adapter.status["A-1"] = "archiviert"
        self.assertIn("abschlussreif_ohne_vormerkung",
                      self.dienst.uebersicht(self.ich)["eintraege"][0]["befunde"])

    def test_vorgemerkte_und_faellige_loeschung_werden_unterschieden(self):
        jetzt = datetime.now(timezone.utc)
        self._anlegen("A-1", abgeschlossen_am=jetzt, loeschung_vorgesehen_am=jetzt + timedelta(days=10))
        self._anlegen("A-2", abgeschlossen_am=jetzt, loeschung_vorgesehen_am=jetzt - timedelta(days=1))
        self.adapter.status.update({"A-1": "archiviert", "A-2": "archiviert"})
        nach_akte = {x["akte_id"]: x for x in self.dienst.uebersicht(self.ich)["eintraege"]}
        self.assertIn("abschluss_vorgemerkt", nach_akte["A-1"]["befunde"])
        self.assertFalse(nach_akte["A-1"]["faellig"])
        self.assertIn("loeschung_faellig", nach_akte["A-2"]["befunde"])
        self.assertTrue(nach_akte["A-2"]["faellig"])

    def test_faelle_mit_handlungsbedarf_stehen_oben(self):
        self._anlegen("A-1")                                   # unauffällig
        self._anlegen("A-2")
        self.adapter.fehlend.add("A-2")
        self.assertEqual(self.dienst.uebersicht(self.ich)["eintraege"][0]["akte_id"], "A-2")

    def test_uebersicht_traegt_keine_akteninhalte(self):
        self._anlegen("A-1", bezeichnung="Testmann gegen Musterhaft",
                      lebenssachverhalt="Der Mandant fuhr 50 km/h. [Q: D1-S1-P1]")
        text = str(self.dienst.uebersicht(self.ich))
        self.assertNotIn("50 km/h", text)
        self.assertNotIn("Mandant", text)


if __name__ == "__main__":
    unittest.main()
