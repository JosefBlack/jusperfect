"""Die Analyse über eine Akte, die nicht in einen Aufruf passt.

Aus der Kanzlei, nachdem die große Akte eingelesen war und die Analyse trotzdem
abbrach: Sie las weiterhin die Rohdokumente. Damit war das abschnittsweise
Einlesen eine halbe Sache – die Akte lag im Gedächtnis, und niemand kam an sie
heran.

Jetzt entscheidet die Analyse selbst: Passt die Akte in einen Aufruf, geht es
wie immer über die Dokumente. Passt sie nicht und ist sie vollständig gelesen,
geht es über den Lebenssachverhalt. Er ist abschnittsweise aus allen Dokumenten
entstanden, ein Bruchteil so lang – und deckt die Akte doch ganz ab. Erst
dadurch lässt sich ein Widerspruch finden, der zwischen Dokument 8 und
Dokument 44 liegt.

Der heikle Punkt steht in `test_geprueft_wird_gegen_die_ganze_akte`: Die
Kennungen im Lebenssachverhalt zeigen auf Passagen, die im Aufruf gar nicht
vorkamen. Gegen die mitgeschickten geprüft, fiele jede einzelne Aussage als
unbelegt heraus.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jusperfect.domain.models import Aktengedaechtnis, ChronologieEintrag, GedaechtnisDokument, Quelle, Seite
from tests.hilfen import client, dienste, einstellungen

AKTE = "GR-2026-0009"


def _grosse_akte(ordner: Path, dokumente: int = 30) -> None:
    ziel = ordner / AKTE
    ziel.mkdir(parents=True)
    fueller = " ".join("Vertrag Kuendigung Frist Zeuge Rechnung Mahnung Termin Gutachten".split()) * 40
    liste = []
    for nr in range(1, dokumente + 1):
        name = f"{nr:03d}_schriftsatz.txt"
        # Jedes Dokument mit eigener Angabe: Waeren alle gleich, schriebe das
        # Gedaechtnis nur einen einzigen Satz fort - es wiederholt nichts, was
        # schon dasteht. Der Test pruefte dann sich selbst, nicht das Programm.
        eigen = (f"Schriftsatz {nr} vom {min(nr, 28):02d}.03.2026. "
                 f"Der Mandant fordert {nr}.500,00 EUR von der Gegnerin.")
        (ziel / name).write_text("\n\n".join([eigen] + [fueller for _ in range(8)]), encoding="utf-8")
        liste.append({"id": f"D-{nr:03d}", "titel": f"Schriftsatz {nr}", "dateiname": name,
                      "datum": "2026-01-01", "kategorie": "Gegner"})
    (ziel / "akte.json").write_text(json.dumps({
        "akte": {"id": AKTE, "aktenzeichen": "9/26 GR", "bezeichnung": "Grosse Akte",
                 "rechtsgebiet": "Zivilrecht", "sachbearbeiter": "RA Dr. Weber", "status": "offen"},
        "dokumente": liste, "beteiligte": [], "fristen": [],
    }, ensure_ascii=False), encoding="utf-8")


class _Aufbau(unittest.TestCase):
    def setUp(self) -> None:
        self._akten = tempfile.TemporaryDirectory()
        self._ged = tempfile.TemporaryDirectory()
        self.addCleanup(self._akten.cleanup)
        self.addCleanup(self._ged.cleanup)
        _grosse_akte(Path(self._akten.name))
        e = einstellungen(JUSPERFECT_FIXTURE_PFAD=self._akten.name,
                          JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=self._ged.name)
        self.d = dienste(einstellungen=e)
        self.c = client(self.d)
        self.sid = self.c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
        self.c.post(f"/api/sitzungen/{self.sid}/dokumente",
                    json={"dokument_ids": [f"D-{nr:03d}" for nr in range(1, 31)]})


class OhneGelesenesGedaechtnis(_Aufbau):
    def test_die_analyse_verweigert_wie_bisher(self):
        antwort = self.c.post(f"/api/sitzungen/{self.sid}/analyse")
        self.assertEqual(antwort.status_code, 422)
        self.assertIn("zu groß", antwort.json()["fehler"])

    def test_die_meldung_nennt_den_knopf(self):
        fehler = self.c.post(f"/api/sitzungen/{self.sid}/analyse").json()["fehler"]
        self.assertIn("Akte einlesen", fehler)


class MitGelesenemGedaechtnis(_Aufbau):
    def setUp(self) -> None:
        super().setUp()
        self.c.post(f"/api/sitzungen/{self.sid}/gedaechtnis/einlesen")

    def test_die_analyse_geht_jetzt_durch(self):
        antwort = self.c.post(f"/api/sitzungen/{self.sid}/analyse")
        self.assertEqual(antwort.status_code, 200, antwort.text[:400])

    def test_der_erste_hinweis_sagt_worauf_sie_beruht(self):
        """Ein stiller Wechsel der Grundlage wäre genau das, was dieses Programm
        sonst verweigert."""
        hinweise = self.c.post(f"/api/sitzungen/{self.sid}/analyse").json()["hinweise"]
        self.assertIn("Gedächtnis", hinweise[0])
        self.assertIn("nicht unmittelbar auf den Dokumenten", hinweise[0])

    def test_geprueft_wird_gegen_die_ganze_akte(self):
        """Der heikle Punkt: Die Kennungen zeigen auf Passagen, die im Aufruf
        gar nicht vorkamen. Gegen die mitgeschickten geprüft, fiele alles."""
        a = self.c.post(f"/api/sitzungen/{self.sid}/analyse").json()
        eintraege = a["chronologie"] + a["forderungen"] + a["beweismittel"]
        self.assertTrue(eintraege, "Es kam gar nichts durch die Belegprüfung.")
        dokumente = {q["kennung"].split("-")[0] for e in eintraege for q in e["quellen"]}
        self.assertGreater(len(dokumente), 1,
                           "Belege aus nur einem Dokument – die Prüfung greift zu eng.")

    def test_die_belege_reichen_ueber_den_ersten_aufruf_hinaus(self):
        """Genau dafür ist der ganze Umweg da: Was in einen Aufruf gepasst
        hätte, sind die ersten neun Dokumente."""
        a = self.c.post(f"/api/sitzungen/{self.sid}/analyse").json()
        eintraege = a["chronologie"] + a["forderungen"] + a["beweismittel"]
        nummern = {int(q["kennung"].split("-")[0][1:]) for e in eintraege for q in e["quellen"]}
        self.assertTrue(any(n > 9 for n in nummern),
                        f"Nur Dokumente {sorted(nummern)} belegt – das ist der erste Aufruf.")


class NurTeilweiseGelesen(_Aufbau):
    """Eine Analyse über zwei Drittel sähe aus wie eine über die ganze Akte."""

    def test_sie_wird_verweigert_und_sagt_wie_viel_fehlt(self):
        # Genau eine Portion lesen, dann ist ein Teil offen.
        self.c.post(f"/api/sitzungen/{self.sid}/gedaechtnis/aktualisieren")
        g = self.d.gedaechtnis.lesen(AKTE)
        self.assertTrue(g.lebenssachverhalt.strip(), "Vorbedingung: etwas ist gelesen.")
        antwort = self.c.post(f"/api/sitzungen/{self.sid}/analyse")
        self.assertEqual(antwort.status_code, 422)
        fehler = antwort.json()["fehler"]
        self.assertIn("erst zum Teil gelesen", fehler)
        self.assertIn("zu Ende laufen lassen", fehler)


class DasGedaechtnisUndDieSitzungZaehlenGleich(unittest.TestCase):
    """Die Sitzung zählte Dokumente nach ihrer Reihenfolge, das Gedächtnis nach
    seiner festen Nummer. Fällt im Gedächtnis eine Nummer weg, zeigt derselbe
    Beleg in beiden auf ein anderes Dokument – und die Analyse über den
    Lebenssachverhalt liefe gegen die falschen Passagen.
    """

    def test_eine_luecke_im_gedaechtnis_verschiebt_die_sitzung_nicht(self):
        with tempfile.TemporaryDirectory() as ged:
            e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=ged)
            d = dienste(einstellungen=e)
            c = client(d)
            sid = c.post("/api/sitzungen", json={"akte_id": "AR-2026-0115"}).json()["sitzung"]["id"]
            c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-201", "D-202", "D-203"]})
            d.gedaechtnis.dokument_vergessen("AR-2026-0115", "D-202")
            # Neue Sitzung: Sie wird aus dem Gedaechtnis wiederhergestellt.
            neu = c.post("/api/sitzungen", json={"akte_id": "AR-2026-0115"}).json()["sitzung"]["id"]
            sitzung = d.sitzungen.laden(
                __import__("jusperfect.security.identitaet", fromlist=["Identitaet"]).Identitaet(
                    nutzer_id="ra-weber", anzeigename="RA", gruppen=()), neu)
            nummern = sorted({int(p.kennung.split("-")[0][1:]) for p in d.sitzungen.passagen(sitzung)})
            self.assertEqual(nummern, [1, 3], f"Die Sitzung hat neu durchgezählt: {nummern}")


if __name__ == "__main__":
    unittest.main()
