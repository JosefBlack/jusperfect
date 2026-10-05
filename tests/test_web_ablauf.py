"""Der ganze Weg über die Schnittstelle: Anmeldung, Berechtigung, Sitzung, Funktionen, Freigabe, Aufräumen."""

import json
import unittest

from jusperfect.providers.base import Nutzung, ProviderAntwort
from jusperfect.security.approval import text_pruefsumme
from tests.hilfen import TESTAKTEN, client, dienste, einstellungen


class SkriptProvider:
    """Liefert vorbereitete Antworten und schreibt mit, was er bekam."""

    modell_id = "skript"

    def __init__(self, antworten):
        self.antworten = list(antworten)
        self.aufrufe = []

    def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        self.aufrufe.append({"system": system, "material": material, "aufgabe": aufgabe, "modell": modell_id})
        text = self.antworten.pop(0)
        return ProviderAntwort(text=text, nutzung=Nutzung(1000, 200), modell=modell_id or self.modell_id)


class Anmeldung(unittest.TestCase):
    def setUp(self):
        self.d = dienste()

    def test_ohne_kopfzeile_401(self):
        self.assertEqual(client(self.d, nutzer=None).get("/api/status").status_code, 401)

    def test_unbekannt_403(self):
        self.assertEqual(client(self.d, nutzer="niemand").get("/api/status").status_code, 403)

    def test_status(self):
        s = client(self.d).get("/api/status").json()
        self.assertEqual(s["anbieter"], "demo")
        self.assertEqual(s["nutzer"]["id"], "ra-weber")
        self.assertEqual(s["kosten"]["budget_eur"], 125.0)


class Berechtigung(unittest.TestCase):
    def setUp(self):
        self.d = dienste()

    def test_mitarbeiter_sieht_nur_eigene_akten(self):
        c = client(self.d, "refa-lorenz")
        self.assertEqual([a["id"] for a in c.get("/api/akten").json()], ["VU-2026-0042"])
        self.assertEqual(c.post("/api/sitzungen", json={"akte_id": "MV-2026-0007"}).status_code, 403)

    def test_anwalt_sieht_alle(self):
        """Alle vorhandenen Testakten, nicht eine feste Anzahl.

        Eine hart eingetragene Zahl bricht, sobald eine Testakte dazukommt –
        und sagt dann nichts über Berechtigungen aus, sondern nur über den
        Umfang der Testdaten.
        """
        vorhanden = {p.name for p in TESTAKTEN.iterdir() if p.is_dir()}
        sichtbar = {a["id"] for a in client(self.d).get("/api/akten").json()}
        self.assertEqual(sichtbar, vorhanden)
        self.assertGreater(len(vorhanden), 1)          # sonst prüft der Test nichts

    def test_fremde_sitzung_unsichtbar(self):
        sid = client(self.d, "ra-weber").post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        self.assertEqual(client(self.d, "ra-kaminski").get(f"/api/sitzungen/{sid}").status_code, 404)
        self.assertEqual(client(self.d, "ra-kaminski").delete(f"/api/sitzungen/{sid}").status_code, 204)
        self.assertEqual(client(self.d, "ra-weber").get(f"/api/sitzungen/{sid}").status_code, 200, "Fremdes Schließen wirkt nicht.")


class Sitzung(unittest.TestCase):
    def setUp(self):
        self.d = dienste()
        self.c = client(self.d)
        self.sid = self.c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]

    def test_dokumente_laden_und_schliessen(self):
        r = self.c.post(f"/api/sitzungen/{self.sid}/dokumente", json={"dokument_ids": ["D-001", "D-003"]})
        self.assertEqual(r.status_code, 200)
        geladen = r.json()["sitzung"]["geladen"]
        self.assertEqual([g["dokument_id"] for g in geladen], ["D-001", "D-003"])
        self.assertGreater(geladen[0]["zeichen"], 100)
        self.assertEqual(self.d.speicher.anzahl_texte(), 2)
        self.assertEqual(self.c.delete(f"/api/sitzungen/{self.sid}").status_code, 204)
        self.assertEqual(self.d.speicher.anzahl_texte(), 0, "Schließen löscht alle Texte.")
        self.assertEqual(self.c.get(f"/api/sitzungen/{self.sid}").status_code, 404)

    def test_unbekanntes_dokument_404(self):
        r = self.c.post(f"/api/sitzungen/{self.sid}/dokumente", json={"dokument_ids": ["D-999"]})
        self.assertEqual(r.status_code, 404)

    def test_frage_ohne_dokumente_422(self):
        r = self.c.post(f"/api/sitzungen/{self.sid}/frage", json={"frage": "Was?"})
        self.assertEqual(r.status_code, 422)

    def test_demo_frage_mit_belegen(self):
        self.c.post(f"/api/sitzungen/{self.sid}/dokumente", json={"dokument_ids": ["D-001", "D-002", "D-004"]})
        r = self.c.post(f"/api/sitzungen/{self.sid}/frage", json={"frage": "Welche Geschwindigkeit fuhr der Mandant?"})
        self.assertEqual(r.status_code, 200)
        a = r.json()
        self.assertTrue(a["quellen"], "Die Demo-Antwort belegt ihre Sätze.")
        self.assertTrue(all(q["kennung"].startswith("D") for q in a["quellen"]))
        self.assertGreater(a["kosten"]["betrag_eur"], 0)


class Analyse(unittest.TestCase):
    def _mit(self, antworten):
        p = SkriptProvider(antworten)
        d = dienste(provider=p)
        c = client(d)
        sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001", "D-004"]})
        return p, d, c, sid

    def test_analyse_prueft_belege(self):
        antwort = json.dumps({
            "chronologie": [{"datum": "2026-03-13", "ereignis": "Unfall", "quellen": ["D1-S1-P1"]},
                            {"datum": "2026-04-08", "ereignis": "Erfunden", "quellen": ["D9-S1-P1"]}],
            "beteiligte": [], "forderungen": [], "beweismittel": [], "offene_punkte": [], "widersprueche": [], "hinweise": []})
        p, d, c, sid = self._mit([antwort])
        a = c.post(f"/api/sitzungen/{sid}/analyse").json()
        # Fail closed: der belegte Eintrag bleibt, der erfundene fällt weg.
        self.assertEqual(len(a["chronologie"]), 1)
        self.assertEqual(a["chronologie"][0]["ereignis"], "Unfall")
        self.assertEqual(a["chronologie"][0]["quellen"][0]["dokument_titel"], "Unfallschilderung Mandant")
        self.assertTrue(any("entfernt" in h.lower() for h in a["hinweise"]))
        self.assertIn("AUFGABE: ANALYSE", p.aufrufe[0]["aufgabe"])
        self.assertIn("### Passage D1-S1-P1", p.aufrufe[0]["material"])

    def test_unbrauchbares_json_zweiter_versuch(self):
        gut = json.dumps({"chronologie": [], "beteiligte": [], "forderungen": [], "beweismittel": [], "offene_punkte": [], "widersprueche": [], "hinweise": []})
        p, d, c, sid = self._mit(["Ich kann leider kein JSON.", gut])
        self.assertEqual(c.post(f"/api/sitzungen/{sid}/analyse").status_code, 200)
        self.assertEqual(len(p.aufrufe), 2)
        self.assertIn("WICHTIG", p.aufrufe[1]["aufgabe"])

    def test_dauerhaft_unbrauchbar_422(self):
        p, d, c, sid = self._mit(["nix", "wieder nix"])
        self.assertEqual(c.post(f"/api/sitzungen/{sid}/analyse").status_code, 422)

    def test_triage_nutzt_kleines_modell(self):
        antwort = json.dumps({"dokumentart": "Schreiben", "absender": "Versicherung", "kernaussage": "Mithaftung [Q: D1-S1-P1]",
                              "fristausloeser": [{"text": "bis 06.05.2026", "quellen": ["D1-S1-P1"]}],
                              "empfohlene_schritte": ["Befund nachreichen"], "quellen": ["D1-S1-P1"], "hinweise": []})
        p = SkriptProvider([antwort])
        d = dienste(provider=p, einstellungen=einstellungen(JUSPERFECT_MODELL_ID_KLEIN="klein"))
        c = client(d)
        sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-004"]})
        t = c.post(f"/api/sitzungen/{sid}/triage", json={"dokument_id": "D-004"}).json()
        self.assertEqual(p.aufrufe[0]["modell"], "klein")
        self.assertEqual(t["fristausloeser"][0]["quellen"][0]["kennung"], "D1-S1-P1")
        self.assertEqual(t["modell"], "klein")

    def test_frage_antwort_belege_aufgeloest(self):
        p, d, c, sid = self._mit(["Der Mandant fuhr 90 km/h [Q: D1-S1-P1]. Behauptung ohne Grundlage [Q: D5-S5-P5]."])
        a = c.post(f"/api/sitzungen/{sid}/frage", json={"frage": "Geschwindigkeit?"}).json()
        # Fail closed: die belegte Aussage bleibt, die unbelegte wird entfernt.
        self.assertIn("Der Mandant fuhr 90 km/h", a["text"])
        self.assertNotIn("Behauptung ohne Grundlage", a["text"])
        self.assertIn("entfernt", a["text"].lower())
        self.assertEqual([q["kennung"] for q in a["quellen"]], ["D1-S1-P1"])
        self.assertTrue(any("entfernt" in h.lower() for h in a["hinweise"]))


class Entwuerfe(unittest.TestCase):
    def setUp(self):
        self.p = SkriptProvider([json.dumps({"betreff": "Deckungsanfrage", "text": "Sehr geehrte Damen und Herren, [Q: D1-S1-P1] ..."})])
        self.d = dienste(provider=self.p)
        self.c = client(self.d)
        self.sid = self.c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        self.c.post(f"/api/sitzungen/{self.sid}/dokumente", json={"dokument_ids": ["D-001"]})
        self.e = self.c.post(f"/api/sitzungen/{self.sid}/entwuerfe", json={"art": "rsv", "anweisung": "Deckung"}).json()

    def test_entwurf_angelegt(self):
        self.assertEqual(self.e["status"], "entwurf")
        self.assertEqual(self.e["betreff"], "Deckungsanfrage")
        # Die Pruefsumme deckt die ganze Freigabevorlage ab, nicht nur den
        # Text - Akte, Art und Betreff werden mitgeschrieben (Befund F06).
        from jusperfect.services.entwuerfe import freigabevorlage
        from jusperfect.domain.models import Entwurf
        self.assertEqual(self.e["freigabe_pruefsumme"],
                         text_pruefsumme(freigabevorlage(Entwurf.model_validate(
                             {k: v for k, v in self.e.items()
                              if k != "freigabe_pruefsumme"}))))
        self.assertEqual(self.d.adapter.geschriebene_vermerke, [])

    def test_freigabe_schreibt_nach_jurnodes(self):
        r = self.c.post(f"/api/entwuerfe/{self.e['id']}/freigabe", json={"bestaetigung": True, "freigabe_pruefsumme": self.e["freigabe_pruefsumme"]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "freigegeben")
        vermerk = self.d.adapter.geschriebene_vermerke[0]
        self.assertEqual(vermerk["nutzer_id"], "ra-weber")
        self.assertTrue(vermerk["text"].startswith("ENTWURF – anwaltliche Prüfung erforderlich"))

    def test_ohne_bestaetigung_nichts(self):
        r = self.c.post(f"/api/entwuerfe/{self.e['id']}/freigabe", json={"bestaetigung": False, "freigabe_pruefsumme": self.e["freigabe_pruefsumme"]})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(self.d.adapter.geschriebene_vermerke, [])

    def test_bearbeitet_dann_alte_pruefsumme_abgewiesen(self):
        neu = self.c.put(f"/api/entwuerfe/{self.e['id']}", json={"betreff": "", "text": self.e["text"] + " Zusatz"}).json()
        r = self.c.post(f"/api/entwuerfe/{self.e['id']}/freigabe", json={"bestaetigung": True, "freigabe_pruefsumme": self.e["freigabe_pruefsumme"]})
        self.assertEqual(r.status_code, 422)
        r = self.c.post(f"/api/entwuerfe/{self.e['id']}/freigabe", json={"bestaetigung": True, "freigabe_pruefsumme": neu["freigabe_pruefsumme"]})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Zusatz", self.d.adapter.geschriebene_vermerke[0]["text"])

    def test_fremder_nutzer_sieht_entwurf_nicht(self):
        c2 = client(self.d, "ra-kaminski")
        self.assertEqual(c2.get(f"/api/entwuerfe/{self.e['id']}").status_code, 404)
        r = c2.post(f"/api/entwuerfe/{self.e['id']}/freigabe", json={"bestaetigung": True, "freigabe_pruefsumme": self.e["freigabe_pruefsumme"]})
        self.assertEqual(r.status_code, 404)

    def test_verwerfen(self):
        self.assertEqual(self.c.delete(f"/api/entwuerfe/{self.e['id']}").status_code, 204)
        self.assertEqual(self.c.get(f"/api/entwuerfe/{self.e['id']}").status_code, 404)


class Budget(unittest.TestCase):
    def test_budget_sperrt(self):
        d = dienste(einstellungen=einstellungen(JUSPERFECT_MONATSBUDGET_EUR="0.001"))
        c = client(d)
        sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001", "D-002", "D-003", "D-004"]})
        self.assertEqual(c.post(f"/api/sitzungen/{sid}/analyse").status_code, 200)
        r = c.post(f"/api/sitzungen/{sid}/frage", json={"frage": "Noch eine Frage?"})
        self.assertEqual(r.status_code, 429)
        self.assertIn("Monatsbudget", r.json()["fehler"])
        self.assertGreaterEqual(c.get("/api/status").json()["kosten"]["anteil"], 1.0)
