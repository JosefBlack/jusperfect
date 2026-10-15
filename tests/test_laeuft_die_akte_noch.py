"""„Läuft die Akte noch?" — die Rückfrage statt einer ablaufenden Frist.

Aus der Kanzlei am 15.10.2026:

    „Du musst fragen: Läuft die Akte noch. Akten laufen manchmal jahrelang.
    Wenn die Frage mit Ja beantwortet wird, dann verlängert sich die
    Löschfrist um 12 Monate."

Der Entwurf der Folgenabschätzung hatte eine Frist vorgesehen, die nach zwölf
Monaten ohne Sitzung **löscht**. Das war falsch gedacht: Eine Akte, in der ein
Gutachten erwartet wird oder ein Verfahren ruht, läuft weiter, auch wenn
niemand sie öffnet.

Jetzt löst die Zeit die **Frage** aus und nicht die Löschung. Diese Prüfungen
halten den Unterschied fest.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.hilfen import NUTZER, einstellungen

from jusperfect.domain.models import Aktengedaechtnis
from jusperfect.gedaechtnis.lokal import LokalerGedaechtnisSpeicher
from jusperfect.security.berechtigungen import DateiBerechtigungen
from jusperfect.security.identitaet import Identitaet
from jusperfect.services.aufbewahrung import AufbewahrungFehler, Aufbewahrungsdienst
from jusperfect.services.gedaechtnis import Gedaechtnisdienst
from jusperfect.speicher.lokal import LokalerSpeicher

AKTE = "VU-2026-0042"


def _vor(tage: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=tage)


class _Aufbau(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp.name)
        self.speicher = LokalerSpeicher()
        self.gspeicher = LokalerGedaechtnisSpeicher(Path(tmp.name))
        self.gedaechtnis = Gedaechtnisdienst(self.gspeicher, self.speicher, None, self.e)
        self.dienst = Aufbewahrungsdienst(
            self.gedaechtnis, DateiBerechtigungen.aus_datei(NUTZER), self.e)
        self.ich = Identitaet(nutzer_id="ra-weber")

    def _ablegen(self, **felder) -> Aktengedaechtnis:
        g = Aktengedaechtnis(akte_id=AKTE, aktenzeichen="042/26 VU",
                             bezeichnung="Testmann ./. Versicherung", **felder)
        self.gspeicher.ablegen(g)
        return g


class DieZeitLoestDieFrageAusUndNichtDieLoeschung(_Aufbau):
    def test_eine_frische_akte_wird_nicht_gefragt(self):
        self._ablegen(zuletzt_benutzt_am=_vor(10))
        self.assertFalse(self.dienst.stand(self.ich, AKTE).faellig)

    def test_nach_zwoelf_monaten_ohne_sitzung_wird_gefragt(self):
        self._ablegen(zuletzt_benutzt_am=_vor(13 * 30))
        self.assertTrue(self.dienst.stand(self.ich, AKTE).faellig)

    def test_die_frage_loescht_nichts(self):
        """Der Kern: Faellig heisst gefragt, nicht geloescht."""
        self._ablegen(zuletzt_benutzt_am=_vor(13 * 30))
        stand = self.dienst.stand(self.ich, AKTE)
        self.assertTrue(stand.faellig)
        self.assertIsNone(stand.loeschung_vorgesehen_am)
        self.assertIsNotNone(self.gspeicher.lesen(AKTE))

    def test_eine_unbeantwortete_frage_bleibt_stehen(self):
        """Wer nicht antwortet, verliert nichts — die Frage kommt wieder."""
        self._ablegen(zuletzt_benutzt_am=_vor(13 * 30))
        for _ in range(3):
            self.assertTrue(self.dienst.stand(self.ich, AKTE).faellig)


class JaVerlaengertUmZwoelfMonate(_Aufbau):
    def test_ja_schiebt_den_termin_um_zwoelf_monate(self):
        self._ablegen(zuletzt_benutzt_am=_vor(13 * 30))
        stand = self.dienst.beantworten(self.ich, AKTE, True)
        self.assertFalse(stand.faellig)
        tage = (stand.faellig_am - datetime.now(timezone.utc)).days
        self.assertGreater(tage, 11 * 30)

    def test_ja_wird_vermerkt_mit_datum_und_nutzer(self):
        self._ablegen(zuletzt_benutzt_am=_vor(13 * 30))
        self.dienst.beantworten(self.ich, AKTE, True)
        g = self.gspeicher.lesen(AKTE)
        self.assertEqual(len(g.weiterfuehrungen), 1)
        self.assertEqual(g.weiterfuehrungen[0].nutzer_id, "ra-weber")

    def test_eine_akte_darf_jahrelang_weiterlaufen(self):
        """Aus der Kanzlei: „Akten laufen manchmal jahrelang."""
        self._ablegen(zuletzt_benutzt_am=_vor(13 * 30))
        for _ in range(5):
            self.dienst.beantworten(self.ich, AKTE, True)
            g = self.gspeicher.lesen(AKTE)
            g.nachfrage_faellig_am = _vor(1)      # ein weiteres Jahr vergeht
            self.gspeicher.ablegen(g)
            self.assertTrue(self.dienst.stand(self.ich, AKTE).faellig)
        self.assertEqual(len(self.gspeicher.lesen(AKTE).weiterfuehrungen), 5)
        self.assertIsNotNone(self.gspeicher.lesen(AKTE))

    def test_der_vermerk_traegt_keinen_grund(self):
        """Warum die Akte noch laeuft, steht in der Akte und nicht hier."""
        self._ablegen(zuletzt_benutzt_am=_vor(13 * 30))
        self.dienst.beantworten(self.ich, AKTE, True)
        felder = set(self.gspeicher.lesen(AKTE).weiterfuehrungen[0].model_dump())
        self.assertEqual(felder, {"am", "nutzer_id"})


class NeinSetztDieUebergangsfristInGang(_Aufbau):
    def test_nein_merkt_vor_statt_zu_loeschen(self):
        self._ablegen(zuletzt_benutzt_am=_vor(13 * 30))
        stand = self.dienst.beantworten(self.ich, AKTE, False)
        self.assertIsNotNone(stand.nicht_mehr_laufend_seit)
        self.assertIsNotNone(stand.loeschung_vorgesehen_am)
        self.assertIsNotNone(self.gspeicher.lesen(AKTE), "Nein loescht nicht selbst.")

    def test_die_uebergangsfrist_ist_die_eingestellte(self):
        self._ablegen(zuletzt_benutzt_am=_vor(13 * 30))
        stand = self.dienst.beantworten(self.ich, AKTE, False)
        tage = (stand.loeschung_vorgesehen_am - datetime.now(timezone.utc)).days
        self.assertEqual(tage, self.e.gedaechtnis_uebergangsfrist_tage - 1)

    def test_nach_nein_wird_nicht_weiter_gefragt(self):
        self._ablegen(zuletzt_benutzt_am=_vor(13 * 30))
        self.dienst.beantworten(self.ich, AKTE, False)
        self.assertFalse(self.dienst.stand(self.ich, AKTE).faellig)

    def test_ja_nach_nein_nimmt_die_vormerkung_zurueck(self):
        """Ein Irrtum muss sich zuruecknehmen lassen, solange nichts geloescht ist."""
        self._ablegen(zuletzt_benutzt_am=_vor(13 * 30))
        self.dienst.beantworten(self.ich, AKTE, False)
        stand = self.dienst.beantworten(self.ich, AKTE, True)
        self.assertIsNone(stand.nicht_mehr_laufend_seit)
        self.assertIsNone(stand.loeschung_vorgesehen_am)


class DasOeffnenBeantwortetNichts(_Aufbau):
    def test_benutzen_verschiebt_den_termin_nicht(self):
        """Sonst waere die Frage nie faellig, solange jemand hineinschaut."""
        self._ablegen(zuletzt_benutzt_am=_vor(13 * 30),
                      nachfrage_faellig_am=_vor(30))
        self.dienst.benutzt(AKTE)
        self.assertTrue(self.dienst.stand(self.ich, AKTE).faellig)

    def test_benutzen_haelt_die_nutzung_fest(self):
        self._ablegen(zuletzt_benutzt_am=_vor(200))
        self.dienst.benutzt(AKTE)
        g = self.gspeicher.lesen(AKTE)
        self.assertLess((datetime.now(timezone.utc) - g.zuletzt_benutzt_am).days, 1)


class AlteArbeitskopienOhneTermin(_Aufbau):
    def test_der_termin_wird_aus_der_nutzung_gerechnet(self):
        """Arbeitskopien von vor dem 15.10.2026 tragen keinen Termin."""
        self._ablegen(zuletzt_benutzt_am=_vor(13 * 30), nachfrage_faellig_am=None)
        self.assertTrue(self.dienst.stand(self.ich, AKTE).faellig)


class DieListeDerOffenenFragen(_Aufbau):
    def test_sie_nennt_die_faelligen(self):
        self._ablegen(zuletzt_benutzt_am=_vor(13 * 30))
        self.assertEqual([s.akte_id for s in self.dienst.faellige(self.ich)], [AKTE])

    def test_sie_nennt_keine_fremden_akten(self):
        """Eine Akte, die der Nutzer nicht sehen darf, steht nicht darin."""
        self._ablegen(zuletzt_benutzt_am=_vor(13 * 30))
        fremd = Identitaet(nutzer_id="gibt-es-nicht")
        self.assertEqual(self.dienst.faellige(fremd), [])


class WerNichtDarfFragtNicht(_Aufbau):
    def test_fremder_zugriff_wird_abgewiesen(self):
        self._ablegen(zuletzt_benutzt_am=_vor(13 * 30))
        with self.assertRaises(PermissionError):
            self.dienst.beantworten(Identitaet(nutzer_id="gibt-es-nicht"), AKTE, True)

    def test_ohne_arbeitskopie_gibt_es_nichts_zu_beantworten(self):
        with self.assertRaises(AufbewahrungFehler):
            self.dienst.beantworten(self.ich, AKTE, True)


if __name__ == "__main__":
    unittest.main()
