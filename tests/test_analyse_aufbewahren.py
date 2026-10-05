"""Die Aktenanalyse bleibt – und das Programm merkt, wenn sie veraltet ist.

Aus der Kanzlei am 05.10.2026: „Ja, bau das — Wichtig ist, dass das Programm
vielleicht selber erkennt, wenn neue Dokumente in der Akte sind."

Die Aktenanalyse kostet einen Modellaufruf über die ganze Akte — an der echten
Akte der Kanzlei rund 28 Cent. Von allem, was ein Durchgang erzeugt, war sie
das Teuerste und bis zum 05.10.2026 das Einzige, das niemand aufbewahrt hat:
Sie stand im Fenster und war weg, sobald das Programm geschlossen wurde.

Zwei Dinge hält diese Datei fest:

* **Sie bleibt.** Und zwar mitsamt der Angabe, *wofür* sie gilt — über welche
  Dokumente sie gerechnet wurde.
* **Sie sagt, wenn sie veraltet ist.** Verglichen wird gegen das, was die Akte
  **damals** enthielt, nicht gegen das, was in die Analyse eingegangen ist.
  Sonst zählte jedes bewusst nicht vorgewählte Dokument — eine Rechnung etwa —
  bei jedem Öffnen wieder als „neu", und die Warnung wäre nach einer Woche
  nichts mehr wert.

Der Vergleich kostet nichts: Er läuft im Programm, ohne Modellaufruf. Genau
deshalb darf er bei jedem Öffnen der Akte laufen.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from jusperfect.domain.models import (
    Aktenanalyse, Aktengedaechtnis, ChronologieEintrag, Dokument, GedaechtnisDokument,
    Quelle, Seite,
)
from tests.hilfen import dienste, einstellungen

AKTE = "AR-2026-0115"
STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"
APP = (STATISCH / "app.js").read_text(encoding="utf-8")
CSS = (STATISCH / "styles.css").read_text(encoding="utf-8")


def _block(name: str) -> str:
    treffer = re.search(r"(?:async )?function " + name + r"\(.*?\) \{(.*?)\n\}", APP, re.S)
    assert treffer, f"Funktion {name} nicht gefunden"
    return treffer.group(1)


def _dok(kennung: str, titel: str) -> Dokument:
    return Dokument(id=kennung, akte_id=AKTE, titel=titel, dateiname=f"{kennung}.txt",
                    mime="text/plain")


def _analyse() -> Aktenanalyse:
    return Aktenanalyse(
        chronologie=[ChronologieEintrag(
            datum="2026-05-04", ereignis="Kündigung zugegangen",
            quellen=[Quelle(kennung="D1-S1-P1", dokument_id="D-202",
                            dokument_titel="Kündigung", seite=1, zitat="…")])],
        modell="probe",
    )


class _Aufbau(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal",
                          JUSPERFECT_GEDAECHTNIS_PFAD=self._tmp.name)
        self.d = dienste(einstellungen=e)
        self.dienst = self.d.gedaechtnis
        self.dienst.ablegen(Aktengedaechtnis(
            akte_id=AKTE, aktenzeichen="115/26 AR", bezeichnung="Test",
            dokumente=[GedaechtnisDokument(dokument_id="D-202", titel="Kündigung", nummer=1,
                                           seiten=[Seite(nummer=1, text="Text")])],
            letzte_dokumentnummer=1))
        self.sitzung = _Sitzungshuelle(AKTE)


class _Sitzungshuelle:
    """Nur so viel Sitzung, wie ``analyse_merken`` wirklich anfasst."""

    def __init__(self, akte_id: str) -> None:
        from jusperfect.domain.models import Akte

        self.akte_id = akte_id
        self.akte = Akte(id=akte_id, aktenzeichen="115/26 AR", bezeichnung="Test",
                         rechtsgebiet="Arbeitsrecht")
        self.id = "s-1"


class SieBleibt(_Aufbau):
    def test_sie_liegt_nach_dem_rechnen_im_gedaechtnis(self) -> None:
        self.dienst.analyse_merken(self.sitzung, _analyse(),
                                   erfasste_dokumente=["D-202"], akte_dokumente=["D-202"])
        g = self.dienst.lesen(AKTE)
        self.assertIsNotNone(g.analyse)
        self.assertEqual([x.ereignis for x in g.analyse.chronologie], ["Kündigung zugegangen"])
        self.assertIsNotNone(g.analyse_am)

    def test_sie_haelt_fest_wofuer_sie_gilt(self) -> None:
        """Ohne diese Liste wäre später nicht mehr zu sagen, was darin steckt."""
        self.dienst.analyse_merken(self.sitzung, _analyse(),
                                   erfasste_dokumente=["D-202"],
                                   akte_dokumente=["D-202", "D-203"])
        g = self.dienst.lesen(AKTE)
        self.assertEqual(g.analyse_dokumente, ["D-202"])
        self.assertEqual(g.analyse_akte_dokumente, ["D-202", "D-203"])

    def test_sie_geht_mit_der_uebersicht_an_die_oberflaeche(self) -> None:
        from jusperfect.services.gedaechtnis import Gedaechtnisdienst

        self.dienst.analyse_merken(self.sitzung, _analyse(),
                                   erfasste_dokumente=["D-202"], akte_dokumente=["D-202"])
        u = Gedaechtnisdienst.uebersicht(self.dienst.lesen(AKTE))
        self.assertIsNotNone(u["analyse"])
        self.assertIsNotNone(u["analyse_am"])
        self.assertEqual(u["analyse_dokumente"], ["D-202"])

    def test_ohne_analyse_steht_das_feld_trotzdem_da(self) -> None:
        """Sonst müsste die Oberfläche raten, ob „fehlt" oder „nicht geladen"."""
        from jusperfect.services.gedaechtnis import Gedaechtnisdienst

        for u in (Gedaechtnisdienst.uebersicht(self.dienst.lesen(AKTE)),
                  Gedaechtnisdienst.uebersicht(None)):
            self.assertIn("analyse", u)
            self.assertIsNone(u["analyse"])

    def test_ein_aelteres_gedaechtnis_laesst_sich_weiter_lesen(self) -> None:
        """Dateien aus der Zeit vor dem 05.10.2026 kennen die Felder nicht."""
        g = self.dienst.lesen(AKTE)
        roh = g.model_dump()
        for feld in ("analyse", "analyse_am", "analyse_dokumente", "analyse_akte_dokumente"):
            roh.pop(feld)
        wieder = Aktengedaechtnis.model_validate(roh)
        self.assertIsNone(wieder.analyse)
        self.assertEqual(wieder.analyse_akte_dokumente, [])


class SieSagtWennSieVeraltetIst(_Aufbau):
    def test_ohne_analyse_sagt_der_stand_genau_das(self) -> None:
        stand = self.dienst.analyse_stand(AKTE, [_dok("D-202", "Kündigung")])
        self.assertFalse(stand["vorhanden"])
        self.assertEqual(stand["neu"], [])

    def test_ein_neues_dokument_wird_erkannt_und_benannt(self) -> None:
        self.dienst.analyse_merken(self.sitzung, _analyse(),
                                   erfasste_dokumente=["D-202"], akte_dokumente=["D-202"])
        stand = self.dienst.analyse_stand(AKTE, [_dok("D-202", "Kündigung"),
                                                 _dok("D-301", "Schriftsatz der Gegenseite")])
        self.assertTrue(stand["vorhanden"])
        self.assertEqual([x["dokument_id"] for x in stand["neu"]], ["D-301"])
        # Mit Titel: „1 Dokument" sagt nicht, ob man hinsehen muss.
        self.assertEqual(stand["neu"][0]["titel"], "Schriftsatz der Gegenseite")

    def test_ein_bewusst_nicht_vorgewaehltes_dokument_gilt_nicht_als_neu(self) -> None:
        """Der Punkt der zweiten Liste.

        Die Rechnung lag beim Rechnen in der Akte und ging bewusst nicht mit.
        Zählte sie weiter als „neu", stünde die Warnung bei jedem Öffnen da —
        und wäre nach einer Woche nichts mehr wert.
        """
        self.dienst.analyse_merken(self.sitzung, _analyse(),
                                   erfasste_dokumente=["D-202"],
                                   akte_dokumente=["D-202", "D-190"])
        stand = self.dienst.analyse_stand(AKTE, [_dok("D-202", "Kündigung"),
                                                 _dok("D-190", "Rechnung Nr. 2026-114")])
        self.assertEqual(stand["neu"], [])

    def test_der_umfang_der_analyse_steht_daneben(self) -> None:
        self.dienst.analyse_merken(self.sitzung, _analyse(),
                                   erfasste_dokumente=["D-202", "D-203"],
                                   akte_dokumente=["D-202", "D-203"])
        stand = self.dienst.analyse_stand(AKTE, [_dok("D-202", "Kündigung")])
        self.assertEqual(stand["erfasst"], 2)

    def test_die_liste_kommt_zweimal_gleich_zurueck(self) -> None:
        """Sonst sähe ein zweiter Blick nach Bewegung aus, wo keine ist."""
        self.dienst.analyse_merken(self.sitzung, _analyse(),
                                   erfasste_dokumente=["D-202"], akte_dokumente=["D-202"])
        jetzt = [_dok("D-202", "Kündigung"), _dok("D-303", "Zweites"), _dok("D-302", "Erstes")]
        erste = self.dienst.analyse_stand(AKTE, jetzt)["neu"]
        zweite = self.dienst.analyse_stand(AKTE, list(reversed(jetzt)))["neu"]
        self.assertEqual(erste, zweite)
        self.assertEqual([x["titel"] for x in erste], ["Erstes", "Zweites"])

    def test_er_kostet_keinen_modellaufruf(self) -> None:
        """Nur deshalb darf er bei jedem Öffnen laufen."""
        self.dienst.analyse_merken(self.sitzung, _analyse(),
                                   erfasste_dokumente=["D-202"], akte_dokumente=["D-202"])
        vorher = len(self.d.speicher.eintraege)
        self.dienst.analyse_stand(AKTE, [_dok("D-202", "K"), _dok("D-9", "Neu")])
        self.assertEqual(len(self.d.speicher.eintraege), vorher)


class UeberDieSchnittstelle(unittest.TestCase):
    """Der Weg, den die Oberfläche wirklich geht."""

    def setUp(self) -> None:
        from tests.hilfen import client

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal",
                          JUSPERFECT_GEDAECHTNIS_PFAD=self._tmp.name)
        self.d = dienste(einstellungen=e)
        self.c = client(self.d)
        self.sid = self.c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]

    def test_ohne_analyse_antwortet_sie_mit_nichts_statt_mit_einem_fehler(self) -> None:
        antwort = self.c.get(f"/api/sitzungen/{self.sid}/analyse")
        self.assertEqual(antwort.status_code, 200)
        self.assertIsNone(antwort.json()["analyse"])
        self.assertFalse(antwort.json()["stand"]["vorhanden"])

    def test_nach_dem_rechnen_liefert_sie_die_gespeicherte_analyse(self) -> None:
        self.c.post(f"/api/sitzungen/{self.sid}/dokumente",
                    json={"dokument_ids": ["D-201", "D-202"]})
        gerechnet = self.c.post(f"/api/sitzungen/{self.sid}/analyse")
        self.assertEqual(gerechnet.status_code, 200)
        self.assertIn("stand", gerechnet.json())
        spaeter = self.c.get(f"/api/sitzungen/{self.sid}/analyse").json()
        self.assertIsNotNone(spaeter["analyse"])
        self.assertTrue(spaeter["stand"]["vorhanden"])

    def test_die_analyse_erfasst_was_geladen_war_nicht_die_ganze_akte(self) -> None:
        """Und die Akte wird trotzdem vollständig vermerkt.

        Sonst meldete jedes nicht geladene Dokument sich später als „neu".
        """
        self.c.post(f"/api/sitzungen/{self.sid}/dokumente", json={"dokument_ids": ["D-201"]})
        self.c.post(f"/api/sitzungen/{self.sid}/analyse")
        g = self.d.gedaechtnis.lesen(AKTE)
        self.assertEqual(g.analyse_dokumente, ["D-201"])
        self.assertGreater(len(g.analyse_akte_dokumente), 1)
        self.assertEqual(self.c.get(f"/api/sitzungen/{self.sid}/analyse").json()["stand"]["neu"], [])


class DieOberflaecheZeigtEsBeimOeffnen(unittest.TestCase):
    def test_die_gespeicherte_analyse_wird_ohne_knopfdruck_geholt(self) -> None:
        block = _block("arbeitsflaecheOeffnen")
        self.assertIn("await gespeicherteAnalyseZeigen()", block)

    def test_der_abruf_haelt_das_oeffnen_nicht_auf(self) -> None:
        """Sie ist eine Arbeitshilfe, keine Bedingung."""
        block = _block("gespeicherteAnalyseZeigen")
        self.assertIn("catch (e) { return; }", block)

    def test_beim_aktenwechsel_wird_der_stand_zurueckgesetzt(self) -> None:
        """Sonst fragte der Knopf nach einer Analyse, die es hier nie gab."""
        block = _block("gespeicherteAnalyseZeigen")
        zuruecksetzen = block.index("analyseStand = { vorhanden: false")
        self.assertLess(zuruecksetzen, block.index("await api("))

    def test_die_karte_traegt_das_datum_des_standes(self) -> None:
        block = _block("analyseKarte")
        self.assertIn("Aktenanalyse · Stand vom ${datumKurz(stand.am)}", block)

    def test_was_fehlt_steht_ueber_dem_ergebnis_nicht_darunter(self) -> None:
        """Eine Analyse, der drei Schriftstücke fehlen, sieht genauso
        vollständig aus wie eine vollständige."""
        block = _block("analyseKarte")
        self.assertLess(block.index("analyse-veraltet"), block.index("hinweiseBlock"))

    def test_der_hinweis_nennt_die_dokumente_beim_namen(self) -> None:
        block = _block("analyseNachzuglerText")
        self.assertIn("d.titel", block)
        self.assertIn("es ist darin ", block)
        self.assertIn("sie sind darin nicht enthalten:", block)

    def test_der_titel_steht_am_schluss_ohne_punkt_dahinter(self) -> None:
        """Ein Dokumenttitel endet oft selbst auf einen Punkt.

        Im Browserlauf vom 05.10.2026 stand da „Schriftsatz vom 02.10.."
        """
        block = _block("analyseNachzuglerText")
        for zeile in block.splitlines():
            if "${namen}" in zeile:
                self.assertNotIn("${namen}.", zeile)
            if "${rest}" in zeile:
                self.assertNotIn("${rest}.", zeile)

    def test_bei_vielen_wird_gekuerzt_aber_die_zahl_bleibt_genannt(self) -> None:
        block = _block("analyseNachzuglerText")
        self.assertIn("neu.slice(0, 5)", block)
        self.assertIn("${neu.length - 5} weitere", block)
        self.assertIn("${neu.length} Dokumente", block)

    def test_neben_dem_hinweis_steht_der_knopf_zum_neu_rechnen(self) -> None:
        block = _block("analyseKarte")
        self.assertIn('knopf.textContent = "neu rechnen"', block)
        self.assertIn("mitKnopf(ev.target, analyseStarten)", block)

    def test_es_gibt_nur_eine_darstellung_fuer_beide_wege(self) -> None:
        """Zwei wären mit der Zeit zwei verschiedene."""
        self.assertEqual(APP.count("function analyseKarte("), 1)
        for aufruf in ("analyseKarte(daten.analyse, analyseStand)", "analyseKarte(a, null)"):
            self.assertIn(aufruf, APP)

    def test_der_hinweis_faellt_ins_auge(self) -> None:
        self.assertIn(".analyse-veraltet", CSS)
        self.assertIn("var(--amber)", CSS.split(".analyse-veraltet")[1][:400])


class DerKnopfGibtNichtUngefragtGeldAus(unittest.TestCase):
    def setUp(self) -> None:
        self.block = _block("analyseStarten")

    def test_liegt_schon_eine_vor_wird_erst_gefragt(self) -> None:
        self.assertIn("if (analyseStand.vorhanden) {", self.block)
        frage = self.block.index("if (analyseStand.vorhanden) {")
        self.assertLess(frage, self.block.index('api("POST"'))

    def test_die_frage_nennt_das_datum_und_den_preis(self) -> None:
        self.assertIn("Es liegt eine Analyse vom ${datumKurz(analyseStand.am)} vor.", self.block)
        self.assertIn("kostet einen Modellaufruf über die ganze Akte", self.block)

    def test_sie_sagt_auch_wenn_sich_nichts_geaendert_hat(self) -> None:
        """Gerade dann ist der Knopf eine Geldausgabe ohne Auskunft."""
        self.assertIn("Seitdem ist kein Dokument in die Akte gekommen.", self.block)

    def test_ohne_bestaetigung_geschieht_nichts(self) -> None:
        self.assertIn('if (!confirm(teile.join("\\n"))) return;', self.block)

    def test_ohne_gespeicherte_analyse_wird_nicht_gefragt(self) -> None:
        """Der erste Lauf braucht keine Rückfrage – es gibt nichts zu verlieren."""
        vor_dem_post = self.block[:self.block.index('api("POST"')]
        self.assertEqual(vor_dem_post.count("confirm("), 1)
        self.assertIn("if (analyseStand.vorhanden) {", vor_dem_post)


if __name__ == "__main__":
    unittest.main()
