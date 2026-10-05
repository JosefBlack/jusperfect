"""Der Abschluss einer Akte – die Abnahmetests aus Issue #3.

Die tragende Zusage: Gelöscht wird nur nach einem bestätigten Abschluss in
jurnodes, erst nach abgelaufener Übergangsfrist und erst nachdem der
Arbeitsstand nachweislich zurückgeschrieben wurde. In jedem Zweifelsfall
bleibt der Arbeitsbereich bestehen.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.hilfen import NUTZER, einstellungen

from jusperfect.domain.models import (
    Akte, Aktengedaechtnis, Entwurf, EntwurfArt, GedaechtnisAntwort, GedaechtnisDokument, Quelle,
    Seite, Sitzung,
)
from jusperfect.gedaechtnis.lokal import LokalerGedaechtnisSpeicher
from jusperfect.jurnodes.base import JurNodesFehler
from jusperfect.security.approval import Freigabestelle
from jusperfect.security.berechtigungen import DateiBerechtigungen, ZugriffVerweigert
from jusperfect.security.identitaet import Identitaet
from jusperfect.services.abschluss import AbschlussFehler, Abschlussdienst
from jusperfect.services.gedaechtnis import Gedaechtnisdienst
from jusperfect.speicher.lokal import LokalerSpeicher

AKTE = "VU-2026-0042"


class _Adapter:
    """jurnodes im Test: Status einstellbar, Störungen provozierbar."""

    def __init__(self, status: str = "laufend") -> None:
        self.status = status
        self.lesestoerung = False
        self.schreibstoerung = False
        self.vermerke: list[tuple[str, str, str]] = []

    def akte(self, akte_id: str) -> Akte:
        if self.lesestoerung:
            raise JurNodesFehler("jurnodes ist nicht erreichbar.")
        return Akte(id=akte_id, aktenzeichen="42/26", bezeichnung="Testmann gegen Musterhaft", status=self.status)

    def vermerk_schreiben(self, akte_id: str, titel: str, text: str, freigabe) -> str:
        if self.schreibstoerung:
            raise JurNodesFehler("Der Vermerk wurde abgelehnt.")
        self.vermerke.append((akte_id, titel, text))
        return "VM-2026-0001"


class _Aufbau(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp.name)
        self.speicher = LokalerSpeicher()
        self.gspeicher = LokalerGedaechtnisSpeicher(Path(tmp.name))
        self.gedaechtnis = Gedaechtnisdienst(self.gspeicher, self.speicher, None, self.e)
        self.adapter = _Adapter()
        self.dienst = Abschlussdienst(
            self.gedaechtnis, self.adapter, DateiBerechtigungen.aus_datei(NUTZER),
            self.speicher, Freigabestelle(), self.e,
        )
        self.ich = Identitaet(nutzer_id="ra-weber")
        self.gspeicher.ablegen(self._gedaechtnis())

    @staticmethod
    def _gedaechtnis() -> Aktengedaechtnis:
        quelle = Quelle(kennung="D1-S1-P1", dokument_id="D-001", dokument_titel="Klage", seite=1)
        return Aktengedaechtnis(
            akte_id=AKTE, aktenzeichen="42/26", bezeichnung="Testmann gegen Musterhaft",
            dokumente=[GedaechtnisDokument(dokument_id="D-001", titel="Klage",
                                           seiten=[Seite(nummer=1, text="Der Mandant fuhr 50 km/h.")])],
            lebenssachverhalt="Unfall am 3. Januar 2026. [Q: D1-S1-P1]",
            lebenssachverhalt_quellen=[quelle],
            fragen_antworten=[GedaechtnisAntwort(frage="Wie schnell?", antwort="50 km/h. [Q: D1-S1-P1]",
                                                 quellen=[quelle])],
        )

    def _vormerken_und_faellig(self) -> Aktengedaechtnis:
        """Abschluss vormerken und die Übergangsfrist als abgelaufen setzen."""
        self.adapter.status = "archiviert"
        self.dienst.vormerken(self.ich, AKTE)
        g = self.gspeicher.lesen(AKTE)
        g.loeschung_vorgesehen_am = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.gspeicher.ablegen(g)
        return g

    def _ausfuehren(self):
        vorschau = self.dienst.export_vorschau(self.ich, AKTE)
        return self.dienst.ausfuehren(self.ich, AKTE, True, vorschau["text_pruefsumme"])


class LaufendeAkteBleibt(_Aufbau):
    def test_1_neun_monate_unveraendert_aber_laufend_wird_nicht_geloescht(self):
        g = self.gspeicher.lesen(AKTE)
        g.aktualisiert_am = datetime.now(timezone.utc) - timedelta(days=270)
        self.gspeicher.ablegen(g)
        stand = self.dienst.stand(self.ich, AKTE)
        self.assertFalse(stand.abschlussreif)
        self.assertIsNone(stand.loeschung_vorgesehen_am)
        with self.assertRaises(AbschlussFehler):
            self.dienst.vormerken(self.ich, AKTE)
        self.assertIsNotNone(self.gspeicher.lesen(AKTE))

    def test_2_aussetzung_und_wiedervorlage_loesen_nichts_aus(self):
        for status in ("ruhend", "ausgesetzt", "wiedervorlage"):
            with self.subTest(status=status):
                self.adapter.status = status
                stand = self.dienst.stand(self.ich, AKTE)
                self.assertFalse(stand.abschlussreif)
                self.assertEqual(stand.hinweise, [])          # keine Rückfrage
                self.assertIsNotNone(self.gspeicher.lesen(AKTE))


class AbschlussStartetDieFrist(_Aufbau):
    def test_3_erst_der_abschluss_startet_die_uebergangsfrist(self):
        self.adapter.status = "archiviert"
        stand = self.dienst.vormerken(self.ich, AKTE)
        self.assertTrue(stand.abschlussreif)
        self.assertIsNotNone(stand.abgeschlossen_am)
        erwartet = stand.abgeschlossen_am + timedelta(days=self.e.gedaechtnis_uebergangsfrist_tage)
        self.assertEqual(stand.loeschung_vorgesehen_am, erwartet)
        self.assertFalse(stand.faellig)

    def test_vor_ablauf_der_frist_wird_nicht_geloescht(self):
        self.adapter.status = "archiviert"
        self.dienst.vormerken(self.ich, AKTE)
        with self.assertRaises(AbschlussFehler) as f:
            self._ausfuehren()
        self.assertIn("Übergangsfrist", str(f.exception))
        self.assertIsNotNone(self.gspeicher.lesen(AKTE))

    def test_ohne_vormerkung_kein_abschluss(self):
        self.adapter.status = "archiviert"
        with self.assertRaises(AbschlussFehler) as f:
            self._ausfuehren()
        self.assertIn("vorgemerkt", str(f.exception))

    def test_wiederholtes_vormerken_verschiebt_die_frist_nicht(self):
        self.adapter.status = "archiviert"
        erste = self.dienst.vormerken(self.ich, AKTE).loeschung_vorgesehen_am
        self.assertEqual(self.dienst.vormerken(self.ich, AKTE).loeschung_vorgesehen_am, erste)


class RueckkehrStopptDieLoeschung(_Aufbau):
    def test_4_rueckkehr_zu_laufend_stoppt_die_vorgemerkte_loeschung(self):
        self._vormerken_und_faellig()
        self.adapter.status = "laufend"                       # Akte wird wieder bearbeitet
        with self.assertRaises(AbschlussFehler) as f:
            self._ausfuehren()
        self.assertIn("wieder", str(f.exception))
        g = self.gspeicher.lesen(AKTE)
        self.assertIsNotNone(g)
        self.assertIsNone(g.loeschung_vorgesehen_am)          # Vormerkung aufgehoben
        self.assertIsNone(g.abgeschlossen_am)


class StoerungLoeschtNicht(_Aufbau):
    def test_5_bei_ausfall_von_jurnodes_wird_nicht_geloescht(self):
        self._vormerken_und_faellig()
        vorschau = self.dienst.export_vorschau(self.ich, AKTE)
        self.adapter.lesestoerung = True
        with self.assertRaises(AbschlussFehler) as f:
            self.dienst.ausfuehren(self.ich, AKTE, True, vorschau["text_pruefsumme"])
        self.assertIn("nichts gelöscht", str(f.exception))
        self.assertIsNotNone(self.gspeicher.lesen(AKTE))

    def test_stand_meldet_stoerung_ohne_zu_loeschen(self):
        self.adapter.lesestoerung = True
        stand = self.dienst.stand(self.ich, AKTE)
        self.assertTrue(any("nichts gelöscht" in h for h in stand.hinweise))
        self.assertIsNotNone(self.gspeicher.lesen(AKTE))

    def test_gescheiterter_export_loescht_nichts(self):
        self._vormerken_und_faellig()
        self.adapter.schreibstoerung = True
        with self.assertRaises(AbschlussFehler) as f:
            self._ausfuehren()
        self.assertIn("nichts gelöscht", str(f.exception))
        self.assertIsNotNone(self.gspeicher.lesen(AKTE))
        self.assertEqual(self.adapter.vermerke, [])

    def test_unbekannter_status_erlaubt_keinen_abschluss(self):
        self.adapter.status = "unbekannt"
        with self.assertRaises(AbschlussFehler):
            self.dienst.vormerken(self.ich, AKTE)
        self.assertIsNotNone(self.gspeicher.lesen(AKTE))


class BerechtigungSperrtOhneZuLoeschen(_Aufbau):
    def test_6_entzogene_berechtigung_sperrt_den_zugriff_loescht_aber_nicht(self):
        fremd = Identitaet(nutzer_id="refa-lorenz")           # nur VU-2026-0042
        with self.assertRaises(ZugriffVerweigert):
            self.dienst.stand(fremd, "MV-2026-0007")
        self.assertIsNotNone(self.gspeicher.lesen(AKTE))


class AbschlussExportiertUndLoescht(_Aufbau):
    def test_7_export_nach_jurnodes_dann_vollstaendige_loeschung(self):
        self._vormerken_und_faellig()
        sitzung = Sitzung(id="S1", akte_id=AKTE, nutzer_id="ra-weber",
                          akte=Akte(id=AKTE, aktenzeichen="42/26", bezeichnung="Testmann gegen Musterhaft"))
        self.speicher.sitzung_ablegen(sitzung)
        self.speicher.text_ablegen("S1", "D-001", "Der Mandant fuhr 50 km/h.")
        self.speicher.entwurf_ablegen(Entwurf(id="E1", akte_id=AKTE, erstellt_von="ra-weber",
                                              art=EntwurfArt.MAHNUNG, betreff="Mahnung", text="Text"))

        nachweis = self._ausfuehren()

        # Erst exportiert …
        self.assertEqual(len(self.adapter.vermerke), 1)
        akte_id, titel, text = self.adapter.vermerke[0]
        self.assertEqual(akte_id, AKTE)
        self.assertIn("Arbeitsstand", titel)
        self.assertIn("Unfall am 3. Januar 2026", text)
        self.assertIn("Wie schnell?", text)
        # … dann restlos gelöscht.
        self.assertIsNone(self.gspeicher.lesen(AKTE))
        self.assertIsNone(self.speicher.sitzung_lesen("S1"))
        self.assertIsNone(self.speicher.text_lesen("S1", "D-001"))
        self.assertIsNone(self.speicher.entwurf_lesen("E1"))
        self.assertEqual(nachweis.jurnodes_referenz, "VM-2026-0001")

    def test_veraenderter_arbeitsstand_wird_nicht_blind_freigegeben(self):
        self._vormerken_und_faellig()
        vorschau = self.dienst.export_vorschau(self.ich, AKTE)
        g = self.gspeicher.lesen(AKTE)
        g.lebenssachverhalt += "\nNachtrag. [Q: D1-S1-P1]"
        self.gspeicher.ablegen(g)
        with self.assertRaises(AbschlussFehler) as f:
            self.dienst.ausfuehren(self.ich, AKTE, True, vorschau["text_pruefsumme"])
        self.assertIn("neu laden", str(f.exception))
        self.assertIsNotNone(self.gspeicher.lesen(AKTE))

    def test_ohne_bestaetigung_geschieht_nichts(self):
        self._vormerken_und_faellig()
        vorschau = self.dienst.export_vorschau(self.ich, AKTE)
        with self.assertRaises(AbschlussFehler):
            self.dienst.ausfuehren(self.ich, AKTE, False, vorschau["text_pruefsumme"])
        self.assertEqual(self.adapter.vermerke, [])
        self.assertIsNotNone(self.gspeicher.lesen(AKTE))


class NachweisOhneInhalte(_Aufbau):
    def test_8_nachweis_traegt_zahlen_und_zeitpunkte_aber_keine_akteninhalte(self):
        self._vormerken_und_faellig()
        nachweis = self._ausfuehren().als_dict()
        self.assertEqual(nachweis["geloescht"]["dokumente"], 1)
        self.assertEqual(nachweis["geloescht"]["fragen"], 1)
        self.assertIsInstance(nachweis["zeitpunkt"], datetime)
        self.assertEqual(nachweis["nutzer_id"], "ra-weber")
        text = str(nachweis)
        for inhalt in ("50 km/h", "Mandant", "Unfall", "Wie schnell"):
            self.assertNotIn(inhalt, text)


if __name__ == "__main__":
    unittest.main()


class GezielteLoeschung(_Aufbau):
    """Einzelne Auszüge und Einträge entfernen – ohne Rest im Gedächtnis."""

    def test_dokument_vergessen_nimmt_abgeleitetes_mit(self):
        """Hier ist es das einzige Dokument – es bleibt also nichts übrig.

        Dass bei mehreren Dokumenten nur das Betroffene fällt, steht in
        tests/test_gedaechtnis_nummern.py.
        """
        self.gedaechtnis.dokument_vergessen(AKTE, "D-001")
        g = self.gspeicher.lesen(AKTE)
        self.assertEqual(g.dokumente, [])
        # Der Lebenssachverhalt war aus diesem Dokument geschrieben …
        self.assertEqual(g.lebenssachverhalt, "")
        self.assertEqual(g.lebenssachverhalt_quellen, [])
        self.assertEqual(g.verarbeitete_passagen, [])
        # … und die Antwort zitierte es.
        self.assertEqual(g.fragen_antworten, [])

    def test_unbekanntes_dokument_wird_abgewiesen(self):
        from jusperfect.gedaechtnis.base import GedaechtnisFehler

        with self.assertRaises(GedaechtnisFehler):
            self.gedaechtnis.dokument_vergessen(AKTE, "D-999")

    def test_einzelne_frage_vergessen_laesst_den_rest_stehen(self):
        g = self.gspeicher.lesen(AKTE)
        g.fragen_antworten.append(GedaechtnisAntwort(frage="Und sonst?", antwort="Nichts. [Q: D1-S1-P1]",
                                                     quellen=list(g.fragen_antworten[0].quellen)))
        self.gspeicher.ablegen(g)
        self.gedaechtnis.antwort_vergessen(AKTE, 0)
        uebrig = self.gspeicher.lesen(AKTE)
        self.assertEqual([r.frage for r in uebrig.fragen_antworten], ["Und sonst?"])
        self.assertNotEqual(uebrig.lebenssachverhalt, "")      # bleibt unberührt

    def test_ungueltige_nummer_wird_abgewiesen(self):
        from jusperfect.gedaechtnis.base import GedaechtnisFehler

        for nummer in (-1, 5):
            with self.subTest(nummer=nummer), self.assertRaises(GedaechtnisFehler):
                self.gedaechtnis.antwort_vergessen(AKTE, nummer)


class ExporttextIstEhrlich(_Aufbau):
    def test_ohne_belegten_arbeitsstand_sagt_der_vermerk_das(self):
        """Ein leerer Vermerk sähe aus wie ein gesicherter Arbeitsstand."""
        g = self.gspeicher.lesen(AKTE)
        g.lebenssachverhalt = ""
        g.lebenssachverhalt_quellen = []
        g.fragen_antworten = []
        self.gspeicher.ablegen(g)
        text = self.dienst.export_vorschau(self.ich, AKTE)["text"]
        self.assertIn("kein belegter Arbeitsstand", text)
        self.assertIn("1 Dokumentauszug", text)

    def test_mit_arbeitsstand_steht_er_im_vermerk(self):
        text = self.dienst.export_vorschau(self.ich, AKTE)["text"]
        self.assertIn("Lebenssachverhalt", text)
        self.assertIn("Unfall am 3. Januar 2026", text)
        self.assertNotIn("kein belegter Arbeitsstand", text)


class UeberDieSchnittstelle(unittest.TestCase):
    """Die Endpunkte, wie die Oberfläche sie benutzt."""

    def setUp(self) -> None:
        import tempfile as _tempfile

        from tests.hilfen import client, dienste

        tmp = _tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp.name,
                               JUSPERFECT_GEDAECHTNIS_UEBERGANGSFRIST_TAGE="0")
        self.d = dienste(einstellungen=self.e)
        self.c = client(self.d, "ra-weber")
        # Arbeitsbereich anlegen: Sitzung öffnen und ein Dokument laden.
        sid = self.c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
        self.c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})

    def test_status_meldet_verwaltungsrecht(self):
        from tests.hilfen import client

        self.assertTrue(self.c.get("/api/status").json()["verwaltung"])
        self.assertFalse(client(self.d, "refa-lorenz").get("/api/status").json()["verwaltung"])

    def test_laufende_akte_ist_nicht_abschlussreif(self):
        stand = self.c.get(f"/api/akten/{AKTE}/abschluss").json()
        self.assertFalse(stand["abschlussreif"])
        self.assertEqual(self.c.post(f"/api/akten/{AKTE}/abschluss/vormerken").status_code, 409)

    def test_aufsicht_nur_fuer_die_verwaltung(self):
        from tests.hilfen import client

        self.assertEqual(self.c.get("/api/verwaltung/arbeitsbereiche").status_code, 200)
        self.assertEqual(client(self.d, "refa-lorenz").get("/api/verwaltung/arbeitsbereiche").status_code, 403)

    def test_aufsicht_listet_den_arbeitsbereich(self):
        daten = self.c.get("/api/verwaltung/arbeitsbereiche").json()
        self.assertEqual(daten["arbeitsbereiche"], 1)
        self.assertEqual(daten["eintraege"][0]["akte_id"], AKTE)
        self.assertEqual(daten["eintraege"][0]["dokumente"], 1)

    def test_ausfuehren_ohne_vormerkung_wird_abgewiesen(self):
        vorschau = self.c.get(f"/api/akten/{AKTE}/abschluss/vorschau").json()
        antwort = self.c.post(f"/api/akten/{AKTE}/abschluss/ausfuehren",
                              json={"bestaetigung": True, "text_pruefsumme": vorschau["text_pruefsumme"]})
        self.assertEqual(antwort.status_code, 409)

    def test_dokument_gezielt_vergessen_ueber_die_schnittstelle(self):
        antwort = self.c.delete(f"/api/akten/{AKTE}/gedaechtnis/dokumente/D-001")
        self.assertEqual(antwort.status_code, 200)
        self.assertEqual(antwort.json()["dokumente"], 0)
