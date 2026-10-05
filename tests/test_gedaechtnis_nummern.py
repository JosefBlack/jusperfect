"""Feste Dokumentnummern: Eine Fundstelle bedeutet in zwei Jahren dasselbe.

Die Fundstellenkennung ``D12-S1-P3`` nennt das zwölfte Dokument. Bisher war
damit die zwölfte Stelle in der Liste des Aktengedächtnisses gemeint. Das ging
gut, solange nur angehängt wurde – und ging schief, sobald etwas entfiel: Alle
Kennungen dahinter zeigten auf das nächste Dokument, und weil das niemand
bemerkt hätte, musste alles Abgeleitete verworfen werden. Bei einer Akte mit
fünfzig Dokumenten heißt das: ein zurückgezogener Auszug, und der ganze
Lebenssachverhalt ist weg.

Ein Gedächtnis, in das über Jahre nachgetragen wird, kann so nicht arbeiten.
Deshalb bekommt jeder Auszug beim Aufnehmen eine Nummer, die ihm bleibt.
Diese Datei hält fest, was daraus folgt – auch für Gedächtnisse, die noch aus
der Zeit ohne Nummern stammen.
"""

from __future__ import annotations

import tempfile
import unittest

from jusperfect.domain.models import (
    Aktengedaechtnis, ChronologieEintrag, GedaechtnisDokument, Quelle, Seite,
)
from jusperfect.services.gedaechtnis import Gedaechtnisdienst
from tests.hilfen import client, dienste, einstellungen

AKTE = "AR-2026-0115"


def _quelle(kennung: str, dokument_id: str) -> Quelle:
    return Quelle(kennung=kennung, dokument_id=dokument_id, dokument_titel="Schreiben",
                  seite=1, zitat="…")


def _alt(anzahl: int) -> Aktengedaechtnis:
    """Ein Gedächtnis, wie Fassung 3 es hinterlassen hat: ohne Nummern."""
    return Aktengedaechtnis(
        schema_version=3, akte_id=AKTE, aktenzeichen="115/26 AR", bezeichnung="Test",
        dokumente=[
            GedaechtnisDokument(dokument_id=f"D-{nr:03d}", titel=f"Schreiben {nr}",
                                seiten=[Seite(nummer=1, text=f"Inhalt {nr}")])
            for nr in range(1, anzahl + 1)
        ],
    )


class _Aufbau(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=self._tmp.name)
        self.d = dienste(einstellungen=e)
        self.dienst = self.d.gedaechtnis

    def _kennungen(self, g: Aktengedaechtnis) -> list[str]:
        return [p.kennung for p in Gedaechtnisdienst._passagen(g)]


class UebernahmeAusFassungDrei(_Aufbau):
    """Ein vorhandenes Gedächtnis darf durch die Umstellung nicht verrutschen."""

    def test_die_nummern_entsprechen_genau_der_bisherigen_stellung(self):
        self.dienst.ablegen(_alt(3))
        g = self.dienst.lesen(AKTE)
        self.assertEqual([d.nummer for d in g.dokumente], [1, 2, 3])
        self.assertEqual(self._kennungen(g), ["D1-S1-P1", "D2-S1-P1", "D3-S1-P1"])

    def test_das_nachtragen_wird_sofort_gespeichert(self):
        """Nach der ersten Änderung wäre die alte Stellung nicht mehr bekannt."""
        self.dienst.ablegen(_alt(3))
        self.dienst.lesen(AKTE)
        # Ein zweites Lesen sieht die Nummern bereits in der Ablage.
        wieder = self.dienst.lesen(AKTE)
        self.assertEqual([d.nummer for d in wieder.dokumente], [1, 2, 3])
        self.assertEqual(wieder.letzte_dokumentnummer, 3)
        self.assertEqual(wieder.schema_version, 4)

    def test_ein_leeres_gedaechtnis_stoert_sich_nicht_daran(self):
        self.dienst.ablegen(_alt(0))
        g = self.dienst.lesen(AKTE)
        self.assertEqual(g.dokumente, [])
        self.assertEqual(g.letzte_dokumentnummer, 0)


class NummernBleibenStehen(_Aufbau):
    def test_ein_entfallenes_dokument_verschiebt_die_anderen_nicht(self):
        """Der eigentliche Punkt: D3 bleibt D3, auch wenn D2 geht."""
        self.dienst.ablegen(_alt(3))
        self.dienst.lesen(AKTE)
        g = self.dienst.dokument_vergessen(AKTE, "D-002")
        self.assertEqual([(d.dokument_id, d.nummer) for d in g.dokumente],
                         [("D-001", 1), ("D-003", 3)])
        self.assertEqual(self._kennungen(g), ["D1-S1-P1", "D3-S1-P1"])

    def test_eine_luecke_wird_nicht_wieder_besetzt(self):
        """Sonst zeigte eine gespeicherte Kennung auf ein fremdes Dokument."""
        self.dienst.ablegen(_alt(3))
        self.dienst.lesen(AKTE)
        self.dienst.dokument_vergessen(AKTE, "D-002")
        c = client(self.d)
        sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-201"]})
        g = self.dienst.lesen(AKTE)
        self.assertEqual([d.nummer for d in g.dokumente if d.dokument_id == "D-201"], [4])

    def test_eine_neue_fassung_desselben_dokuments_behaelt_die_nummer(self):
        c = client(self.d)
        sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-201", "D-202"]})
        vorher = {d.dokument_id: d.nummer for d in self.dienst.lesen(AKTE).dokumente}
        # Dasselbe Dokument noch einmal laden – etwa nach erneutem Einlesen.
        zweite = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{zweite}/dokumente", json={"dokument_ids": ["D-201"]})
        nachher = {d.dokument_id: d.nummer for d in self.dienst.lesen(AKTE).dokumente}
        self.assertEqual(vorher, nachher)

    def test_das_laden_einer_akte_vergibt_die_nummern_in_reihenfolge(self):
        c = client(self.d)
        sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-201", "D-202", "D-203"]})
        g = self.dienst.lesen(AKTE)
        self.assertEqual([(d.dokument_id, d.nummer) for d in g.dokumente],
                         [("D-201", 1), ("D-202", 2), ("D-203", 3)])


class NurDasEigeneFaelltMit(_Aufbau):
    """Was auf anderen Dokumenten beruht, bleibt stehen."""

    def _mit_abgeleitetem(self) -> Aktengedaechtnis:
        g = _alt(3)
        g.lebenssachverhalt = ("Die Kündigung ging am 04.05.2026 zu. [Q: D1-S1-P1]\n"
                               "Der Betriebsrat wurde angehört. [Q: D2-S1-P1]\n"
                               "Die Gegenseite hat geantwortet. [Q: D3-S1-P1]")
        g.lebenssachverhalt_quellen = [_quelle("D1-S1-P1", "D-001"), _quelle("D2-S1-P1", "D-002"),
                                       _quelle("D3-S1-P1", "D-003")]
        g.verarbeitete_passagen = ["D1-S1-P1", "D2-S1-P1", "D3-S1-P1"]
        g.chronologie = [
            ChronologieEintrag(datum="2026-05-04", ereignis="Kündigung zugegangen",
                               quellen=[_quelle("D1-S1-P1", "D-001")]),
            ChronologieEintrag(datum="2026-05-06", ereignis="Betriebsrat angehört",
                               quellen=[_quelle("D2-S1-P1", "D-002")]),
        ]
        g.chronologie_passagen = ["D1-S1-P1", "D2-S1-P1", "D3-S1-P1"]
        self.dienst.ablegen(g)
        self.dienst.lesen(AKTE)
        return g

    def test_der_lebenssachverhalt_verliert_nur_die_betroffenen_saetze(self):
        self._mit_abgeleitetem()
        g = self.dienst.dokument_vergessen(AKTE, "D-002")
        self.assertIn("Die Kündigung ging am 04.05.2026 zu.", g.lebenssachverhalt)
        self.assertIn("Die Gegenseite hat geantwortet.", g.lebenssachverhalt)
        self.assertNotIn("Der Betriebsrat wurde angehört.", g.lebenssachverhalt)
        self.assertEqual([q.kennung for q in g.lebenssachverhalt_quellen],
                         ["D1-S1-P1", "D3-S1-P1"])

    def test_das_entfernte_bleibt_sichtbar_und_wird_nicht_stillschweigend_geglaettet(self):
        """Wer den Lebenssachverhalt liest, soll die Lücke bemerken."""
        self._mit_abgeleitetem()
        g = self.dienst.dokument_vergessen(AKTE, "D-002")
        self.assertIn("[Aussage ohne belastbaren Beleg entfernt]", g.lebenssachverhalt)

    def test_die_chronologie_behaelt_die_uebrigen_ereignisse(self):
        self._mit_abgeleitetem()
        g = self.dienst.dokument_vergessen(AKTE, "D-002")
        self.assertEqual([x.ereignis for x in g.chronologie], ["Kündigung zugegangen"])

    def test_die_marken_der_uebrigen_passagen_bleiben_gesetzt(self):
        """Sonst würde beim nächsten Fortschreiben alles noch einmal bezahlt."""
        self._mit_abgeleitetem()
        g = self.dienst.dokument_vergessen(AKTE, "D-002")
        self.assertEqual(g.verarbeitete_passagen, ["D1-S1-P1", "D3-S1-P1"])
        self.assertEqual(g.chronologie_passagen, ["D1-S1-P1", "D3-S1-P1"])

    def test_faellt_die_letzte_grundlage_weg_bleibt_kein_ersatztext_stehen(self):
        """Der Verzichtssatz ist eine Antwort auf eine Frage, kein Sachverhalt."""
        g = _alt(1)
        g.lebenssachverhalt = "Die Kündigung ging zu. [Q: D1-S1-P1]"
        g.lebenssachverhalt_quellen = [_quelle("D1-S1-P1", "D-001")]
        self.dienst.ablegen(g)
        self.dienst.lesen(AKTE)
        uebrig = self.dienst.dokument_vergessen(AKTE, "D-001")
        self.assertEqual(uebrig.lebenssachverhalt, "")
        self.assertEqual(uebrig.lebenssachverhalt_quellen, [])


if __name__ == "__main__":
    unittest.main()
