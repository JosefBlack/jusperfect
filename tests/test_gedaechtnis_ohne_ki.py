"""Ohne AWS war das Aktengedächtnis nicht zu erleben.

Der Demo-Anbieter kennt Analyse, Chronologie, Triage, Entwurf und die Frage –
aber nicht die Aufgabe „Aktengedächtnis". Sie fiel deshalb auf die
Frage-Antwort zurück. Dort wird nach „FRAGE:" gesucht, die es in dieser
Aufgabe nicht gibt; heraus kam „keine belastbaren Angaben" ohne einen einzigen
Beleg. Die Belegpflicht warf das richtigerweise weg, und im Gedächtnis landete
nie etwas.

Das Ergebnis war ein Knopf, der jedes Mal nichts tat – im Demobetrieb, also
genau dort, wo die Kanzlei das Programm kennenlernt. Diese Datei hält fest,
dass der Weg jetzt durchgeht, und dass er dabei nicht unehrlich wird: Ohne
Fund gibt es weiterhin keine Behauptung.
"""

from __future__ import annotations

import tempfile
import unittest

from jusperfect.domain.models import Akte, Passage
from jusperfect.providers.demo import DemoProvider
from jusperfect.services import prompts
from jusperfect.services.belegpflicht import VERZICHT, aussage_fail_closed
from jusperfect.services.quellen import index_bauen
from tests.hilfen import client, dienste, einstellungen

AKTE = Akte(id="A", aktenzeichen="1/26", bezeichnung="Test", rechtsgebiet="Arbeitsrecht", status="offen")


def _passage(kennung: str, text: str) -> Passage:
    return Passage(kennung=kennung, dokument_id="D-001", dokument_titel="Vermerk", seite=1, text=text)


def _fortschreiben(passagen: list[Passage], bisher: str = "") -> str:
    material = prompts.material_bauen(AKTE, [], [], passagen)
    return DemoProvider().fragen(prompts.SYSTEM, material, prompts.aufgabe_gedaechtnis(bisher)).text


class DerDemoAnbieterKannFortschreiben(unittest.TestCase):
    def test_die_fortschreibung_traegt_belege(self):
        passagen = [_passage("D1-S1-P1", "Die Kündigung ging der Mandantin am 04.05.2026 zu.")]
        belegt = aussage_fail_closed(_fortschreiben(passagen), index_bauen(passagen))
        self.assertNotEqual(belegt.text, VERZICHT)
        self.assertEqual([q.kennung for q in belegt.quellen], ["D1-S1-P1"])

    def test_ohne_fund_wird_nichts_behauptet(self):
        """Die Ehrlichkeit bleibt: kein Fund, keine Aussage."""
        passagen = [_passage("D1-S1-P1", "Wir bestätigen den Eingang Ihres Schreibens.")]
        belegt = aussage_fail_closed(_fortschreiben(passagen), index_bauen(passagen))
        self.assertEqual(belegt.text, VERZICHT)

    def test_bereits_vermerktes_wird_nicht_wiederholt(self):
        """Sonst wüchse der Lebenssachverhalt bei jedem Lauf um dieselben Sätze."""
        passagen = [_passage("D1-S1-P1", "Die Kündigung ging der Mandantin am 04.05.2026 zu.")]
        erste = _fortschreiben(passagen)
        zweite = _fortschreiben(passagen, bisher=erste)
        self.assertIn("04.05.2026", erste)
        self.assertNotIn("04.05.2026", zweite)

    def test_die_fortschreibung_traegt_keine_ueberschrift(self):
        """Sie würde alle paar Absätze mitten im Lebenssachverhalt stehen."""
        passagen = [_passage("D1-S1-P1", "Die Kündigung ging der Mandantin am 04.05.2026 zu.")]
        self.assertNotIn("Demo-Fortschreibung", _fortschreiben(passagen))


class DerGanzeWegImDemobetrieb(unittest.TestCase):
    """Vom Knopfdruck bis in die Datei – ohne AWS, ohne Kosten."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp.name)
        self.d = dienste(einstellungen=e)
        self.c = client(self.d)
        self.sid = self.c.post("/api/sitzungen", json={"akte_id": "AR-2026-0115"}).json()["sitzung"]["id"]
        self.c.post(f"/api/sitzungen/{self.sid}/dokumente", json={"dokument_ids": ["D-201", "D-202"]})

    def test_der_knopf_schreibt_wirklich_etwas_ins_gedaechtnis(self):
        antwort = self.c.post(f"/api/sitzungen/{self.sid}/gedaechtnis/aktualisieren")
        self.assertEqual(antwort.status_code, 200, antwort.text)
        daten = antwort.json()
        self.assertNotEqual(daten["lebenssachverhalt"], "")
        self.assertTrue(daten["quellen"], "Ein Lebenssachverhalt ohne Fundstelle wäre wertlos.")

    def test_der_lauf_wird_beziffert(self):
        lauf = self.c.post(f"/api/sitzungen/{self.sid}/gedaechtnis/aktualisieren").json()["lauf"]
        self.assertEqual(lauf["portionen"], 1)
        self.assertGreater(lauf["passagen"], 0)
        self.assertTrue(lauf["fertig"])

    def test_nach_dem_wiederoeffnen_ist_alles_wieder_da(self):
        """Der eigentliche Zweck – geprüft über denselben Weg wie in der Oberfläche."""
        self.c.post(f"/api/sitzungen/{self.sid}/gedaechtnis/aktualisieren")
        self.c.post(f"/api/sitzungen/{self.sid}/frage", json={"frage": "Wann wurde gekündigt?"})
        self.c.delete(f"/api/sitzungen/{self.sid}")

        neu = self.c.post("/api/sitzungen", json={"akte_id": "AR-2026-0115"}).json()
        self.assertEqual(len(neu["sitzung"]["geladen"]), 2, "Die Dokumente müssen ohne Neueinlesen da sein.")
        self.assertEqual(len(neu["sitzung"]["dialog"]), 1, "Die geprüfte Frage gehört in den Kontext.")
        g = self.c.get(f"/api/sitzungen/{neu['sitzung']['id']}/gedaechtnis").json()
        self.assertNotEqual(g["lebenssachverhalt"], "")

    def test_ein_zweiter_lauf_ohne_neues_dokument_kostet_keinen_aufruf(self):
        self.c.post(f"/api/sitzungen/{self.sid}/gedaechtnis/aktualisieren")
        vorher = len(self.d.provider.aufrufe)
        lauf = self.c.post(f"/api/sitzungen/{self.sid}/gedaechtnis/aktualisieren").json()["lauf"]
        self.assertEqual(lauf["portionen"], 0)
        self.assertEqual(len(self.d.provider.aufrufe), vorher)

    def test_ein_neues_dokument_geht_allein_hinaus(self):
        """Das Bekannte darf nicht ein zweites Mal bezahlt werden."""
        self.c.post(f"/api/sitzungen/{self.sid}/gedaechtnis/aktualisieren")
        self.c.post(f"/api/sitzungen/{self.sid}/dokumente", json={"dokument_ids": ["D-203"]})
        self.c.post(f"/api/sitzungen/{self.sid}/gedaechtnis/aktualisieren")
        material = self.d.provider.aufrufe[-1][1]
        kennungen = {z.split()[2] for z in material.splitlines() if z.startswith("### Passage ")}
        self.assertTrue(kennungen, "Es ging gar nichts hinaus.")
        self.assertTrue(all(k.startswith("D3-") for k in kennungen),
                        f"Nur das dritte Dokument sollte mitgehen, mitgegangen sind: {sorted(kennungen)}")


if __name__ == "__main__":
    unittest.main()
