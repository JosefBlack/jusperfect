"""Der Passagen-Endpunkt der Cowork-Arbeitsfläche.

Die Dokumentspalte zeigt den echten Text mit Fundstellen-Kennungen. Damit ein
Beleg aus der Antwort im Dokument hervorgehoben werden kann, muss jede Kennung,
die eine Frage zurückgibt, auch unter den Passagen stehen.
"""

import json
import re
import unittest

from tests.hilfen import WURZEL, client, dienste

from jusperfect.providers.base import Nutzung, ProviderAntwort


def _stromzeilen(antwort) -> list[dict]:
    """Die NDJSON-Ereignisse eines Streaming-Aufrufs als Liste von dicts."""
    return [json.loads(z) for z in antwort.text.splitlines() if z.strip()]


class Passagen(unittest.TestCase):
    def setUp(self):
        self.d = dienste()
        self.c = client(self.d, "ra-weber")
        self.sid = self.c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        self.c.post(f"/api/sitzungen/{self.sid}/dokumente", json={"dokument_ids": ["D-001", "D-002", "D-004"]})

    def test_passagen_tragen_echten_text_und_kennung(self):
        r = self.c.get(f"/api/sitzungen/{self.sid}/passagen")
        self.assertEqual(r.status_code, 200)
        passagen = r.json()["passagen"]
        self.assertTrue(passagen)
        for p in passagen:
            self.assertTrue(p["kennung"] and p["text"] and p["dokument_titel"])
        # Echter Text, kein Platzhalter-Umweg.
        volltext = " ".join(p["text"] for p in passagen)
        self.assertIn("Testmann", volltext)

    def test_belege_der_frage_sind_im_dokument_auffindbar(self):
        passagen = self.c.get(f"/api/sitzungen/{self.sid}/passagen").json()["passagen"]
        sichtbar = {p["kennung"] for p in passagen}
        antwort = self.c.post(f"/api/sitzungen/{self.sid}/frage",
                              json={"frage": "Welche Geschwindigkeit fuhr der Mandant?"}).json()
        self.assertTrue(antwort["quellen"])
        for q in antwort["quellen"]:
            self.assertIn(q["kennung"], sichtbar)
        dialog = self.c.get(f"/api/sitzungen/{self.sid}").json()["sitzung"]["dialog"]
        self.assertEqual(len(dialog), 1)
        self.assertEqual(dialog[0]["frage"], "Welche Geschwindigkeit fuhr der Mandant?")

    def test_passagen_nur_mit_berechtigung(self):
        fremd = client(self.d, "refa-lorenz")  # darf nur VU-2026-0042; hier ok, aber fremde Sitzung unsichtbar
        r = client(self.d, "ra-kaminski").get(f"/api/sitzungen/{self.sid}/passagen")
        self.assertEqual(r.status_code, 404)

    def test_dokument_aus_arbeitsakte_entfernen(self):
        # Zwei-Fenster-Explorer: ein geladenes Dokument wieder herausnehmen.
        geladen = self.c.get(f"/api/sitzungen/{self.sid}").json()["sitzung"]["geladen"]
        self.assertTrue(geladen)
        weg = geladen[0]["dokument_id"]
        r = self.c.delete(f"/api/sitzungen/{self.sid}/dokumente/{weg}")
        self.assertEqual(r.status_code, 200)
        uebrig = {g["dokument_id"] for g in r.json()["sitzung"]["geladen"]}
        self.assertNotIn(weg, uebrig)
        # Seine Passagen sind weg.
        kennungen = {p["dokument_id"] for p in self.c.get(f"/api/sitzungen/{self.sid}/passagen").json()["passagen"]}
        self.assertNotIn(weg, kennungen)


if __name__ == "__main__":
    unittest.main()


class FailClosed(unittest.TestCase):
    """Was keinen belastbaren Beleg hat, fällt aus dem Ergebnis."""

    def test_freitext_haelt_unbelegte_aussage_zurueck(self):
        from jusperfect.services.belegpflicht import ENTFERNT, VERZICHT, aussage_fail_closed
        from jusperfect.domain.models import Passage
        idx = {"D1-S1-P1": Passage(kennung="D1-S1-P1", dokument_id="D-1", dokument_titel="T", seite=1, text="x")}
        r = aussage_fail_closed("Belegt [Q: D1-S1-P1]. Erfunden [Q: D9-S9-P9].", idx)
        self.assertIn("Belegt", r.text)
        self.assertNotIn("Erfunden", r.text)
        self.assertIn(ENTFERNT, r.text)
        self.assertEqual([q.kennung for q in r.quellen], ["D1-S1-P1"])
        self.assertEqual(r.verworfen, 1)

    def test_der_nachsatz_ohne_beleg_kommt_nicht_durch(self):
        """Die Lücke, durch die jede Behauptung passte, wenn sie nur zuletzt stand.

        Aus einer Gegenprobe von aussen (PRUEFBERICHT-2026-09-16.md, Befund 1):
        „Der Vertrag wurde unterschrieben [Q: D1-S1-P1]. Der Gegner hat die
        Forderung voll anerkannt." kam vollständig heraus, verworfen = 0.

        Der Grund, warum keiner unserer Tests das bemerkt hat, steht in ihnen
        selbst: Sie prüften alle, ob ein **erfundener Beleg** auffällt. Ein
        **fehlender** hatte niemand versucht – dabei ist er der einfachere Weg,
        und die Belegpflicht ist der Kernsatz dieses Programms.
        """
        from jusperfect.domain.models import Passage
        from jusperfect.services.belegpflicht import ENTFERNT, aussage_fail_closed

        idx = {"D1-S1-P1": Passage(kennung="D1-S1-P1", dokument_id="D-1", dokument_titel="T",
                                   seite=1, text="Der Vertrag wurde unterschrieben.")}
        for nachsatz in (" Der Gegner hat die Forderung voll anerkannt.",
                         "\n\nDer Gegner schuldet 999.999 EUR.",
                         "\n- Er hat zugestimmt.",
                         " und zwar vollumfänglich"):
            with self.subTest(nachsatz=nachsatz.strip()[:40]):
                r = aussage_fail_closed("Der Vertrag wurde unterschrieben [Q: D1-S1-P1]." + nachsatz, idx)
                self.assertIn("Der Vertrag wurde unterschrieben", r.text)
                self.assertNotIn("Gegner", r.text)
                self.assertNotIn("zugestimmt", r.text)
                self.assertNotIn("vollumfänglich", r.text)
                self.assertIn(ENTFERNT, r.text)
                self.assertEqual(1, r.verworfen)
                self.assertTrue(r.hinweise, "Ein stilles Entfernen wäre auch nicht recht.")

    def test_der_satzschluss_gehoert_noch_zum_belegten_satz(self):
        """Sonst stünde hinter jeder Antwort eine Marke, wo nur ein Punkt fehlt."""
        from jusperfect.domain.models import Passage
        from jusperfect.services.belegpflicht import ENTFERNT, aussage_fail_closed

        idx = {"D1-S1-P1": Passage(kennung="D1-S1-P1", dokument_id="D-1", dokument_titel="T",
                                   seite=1, text="x")}
        for schluss in (".", ".\n", "", ".  \n\n", ")", "“."):
            with self.subTest(schluss=repr(schluss)):
                r = aussage_fail_closed("Belegt [Q: D1-S1-P1]" + schluss, idx)
                self.assertNotIn(ENTFERNT, r.text)
                self.assertEqual(0, r.verworfen)

    def test_ganz_unbelegte_antwort_wird_verzicht(self):
        from jusperfect.services.belegpflicht import VERZICHT, aussage_fail_closed
        self.assertEqual(aussage_fail_closed("Alles frei erfunden.", {}).text, VERZICHT)
        r = aussage_fail_closed("Nur Erfundenes [Q: D9-S9-P9].", {})
        self.assertEqual(r.text, VERZICHT)
        self.assertEqual(r.quellen, [])

    def test_eintraege_ohne_beleg_fallen_weg(self):
        from jusperfect.services.belegpflicht import eintraege_fail_closed
        from jusperfect.domain.models import ChronologieEintrag, Passage
        idx = {"D1-S1-P1": Passage(kennung="D1-S1-P1", dokument_id="D-1", dokument_titel="T", seite=1, text="x")}
        eintraege = [ChronologieEintrag(datum="2026-01-01", ereignis="A"),
                     ChronologieEintrag(datum="2026-02-02", ereignis="B")]
        roh = [{"quellen": ["D1-S1-P1"]}, {"quellen": ["D9-S9-P9"]}]
        behalten, verworfen = eintraege_fail_closed(eintraege, roh, idx, lambda r: [str(k) for k in r.get("quellen", [])])
        self.assertEqual([e.ereignis for e in behalten], ["A"])
        self.assertEqual(verworfen, 1)


class _KlebeProvider:
    """Streamt eine feste Antwort Wort für Wort – für den Streaming-Weg.

    Der ``fragen``-Zweig ist der Vollständigkeit halber da; ``frage_stream``
    ruft nur ``fragen_stream``. Die erste Kennung aus dem Material wird als
    echte Fundstelle übernommen, damit der Streaming-Test nicht rät.
    """

    modell_id = "klebe-test"

    def __init__(self, vorlage: str) -> None:
        self.vorlage = vorlage

    def _text(self, material: str) -> str:
        m = re.search(r"### Passage ([A-Za-z0-9\-]+)", material)
        echt = m.group(1) if m else "D1-S1-P1"
        return self.vorlage.replace("{ECHT}", echt)

    def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        return ProviderAntwort(text=self._text(material), nutzung=Nutzung(), modell=self.modell_id)

    def fragen_stream(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        text = self._text(material)
        for stueck in re.findall(r"\S+\s*", text):
            yield stueck
        yield ProviderAntwort(text=text, nutzung=Nutzung(), modell=self.modell_id)


class Streaming(unittest.TestCase):
    """Die Frage strömt stückweise – und es strömt nur Geprüftes.

    Befund F05 der Zweitprüfung vom 05.10.2026: Vorher ging der Rohtext
    hinaus und die Prüfung kam am Ende. Der Bearbeiter sah also – und konnte
    kopieren –, was der Abschlussfilter gleich darauf zurückhielt; bei
    langsamer Übertragung lange. Die Zusage lautet „entfernen, nicht zeigen",
    und ein Text, der erst dasteht und dann verschwindet, ist gezeigt worden.

    Bis zur ersten abgeschlossenen Aussage sieht der Bearbeiter seitdem nur,
    **dass** gearbeitet wird: ein Fortschrittsereignis mit der Zeichenzahl,
    ohne Inhalt.
    """

    def _sitzung(self, d):
        c = client(d, "ra-weber")
        sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001", "D-002", "D-004"]})
        return c, sid

    def test_stream_liefert_fortschritt_und_fertig(self):
        c, sid = self._sitzung(dienste())
        r = c.post(f"/api/sitzungen/{sid}/frage/stream",
                   json={"frage": "Welche Geschwindigkeit fuhr der Mandant?"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.headers["content-type"].startswith("application/x-ndjson"))
        ereignisse = _stromzeilen(r)
        fortschritt = [e for e in ereignisse if e["type"] == "fortschritt"]
        fertig = [e for e in ereignisse if e["type"] == "fertig"]
        self.assertGreater(len(fortschritt), 1, "es sollte in mehreren Stücken strömen")
        # Der Fortschritt traegt keinen Inhalt, nur die Zeichenzahl - und die
        # waechst, sonst waere es kein Fortschritt.
        for e in fortschritt:
            self.assertEqual(set(e) - {"type"}, {"zeichen"})
        self.assertLess(fortschritt[0]["zeichen"], fortschritt[-1]["zeichen"])
        self.assertFalse([e for e in ereignisse if e["type"] == "text"],
                         "Rohtext geht seit dem 05.10.2026 nicht mehr hinaus.")
        self.assertEqual(len(fertig), 1)
        antwort = fertig[0]["antwort"]
        sichtbar = {p["kennung"] for p in c.get(f"/api/sitzungen/{sid}/passagen").json()["passagen"]}
        for q in antwort["quellen"]:
            self.assertIn(q["kennung"], sichtbar)
        dialog = c.get(f"/api/sitzungen/{sid}").json()["sitzung"]["dialog"]
        self.assertEqual(len(dialog), 1, "Auch der Streaming-Weg merkt erst die geprüfte Endfassung.")

    def test_stream_entfernt_unbelegte_aussage_am_ende(self):
        prov = _KlebeProvider("Belegtes fährt schnell [Q: {ECHT}]. Frei erfunden [Q: D9-S9-P9].")
        c, sid = self._sitzung(dienste(provider=prov))
        r = c.post(f"/api/sitzungen/{sid}/frage/stream", json={"frage": "Was steht drin?"})
        ereignisse = _stromzeilen(r)
        # **Nichts** von dem Erfundenen geht hinaus – auch nicht für einen
        # Augenblick. Geprüft wird der ganze Strom, nicht nur das Ende.
        alles = json.dumps(ereignisse, ensure_ascii=False)
        self.assertNotIn("Frei erfunden", alles)
        # Was geprüft gesendet wurde, trägt die echte Aussage und die Marke.
        gepruefte = [e for e in ereignisse if e["type"] == "geprueft"]
        self.assertTrue(gepruefte, "Belegtes soll schon während des Stroms kommen.")
        self.assertIn("Belegtes", gepruefte[-1]["text"])
        # Fertig: die unbelegte Aussage ist raus, nur die echte Kennung bleibt.
        antwort = [e for e in ereignisse if e["type"] == "fertig"][0]["antwort"]
        self.assertIn("Belegtes", antwort["text"])
        self.assertNotIn("Frei erfunden", antwort["text"])
        # Die verworfene Kennung darf nicht als Beleg gelten (der Hinweis nennt
        # sie transparent, das ist gewollt).
        self.assertNotIn("D9-S9-P9", antwort["text"])
        self.assertEqual([q["kennung"] for q in antwort["quellen"]], ["D1-S1-P1"])

    def test_stream_leere_frage_meldet_fehler(self):
        c, sid = self._sitzung(dienste())
        r = c.post(f"/api/sitzungen/{sid}/frage/stream", json={"frage": "   "})
        ereignisse = _stromzeilen(r)
        self.assertTrue(ereignisse)
        self.assertEqual(ereignisse[-1]["type"], "fehler")


class WorkflowPacks(unittest.TestCase):
    def setUp(self):
        self.d = dienste()
        self.c = client(self.d, "ra-weber")
        self.sid = self.c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        self.c.post(f"/api/sitzungen/{self.sid}/dokumente",
                    json={"dokument_ids": ["D-001", "D-002", "D-003", "D-004"]})

    def test_packs_liste(self):
        packs = {p["id"] for p in self.c.get("/api/packs").json()}
        self.assertIn("verkehrsunfall", packs)
        self.assertIn("miete", packs)

    def test_auto_wahl_nach_rechtsgebiet(self):
        r = self.c.post(f"/api/sitzungen/{self.sid}/pack", json={})
        self.assertEqual(r.status_code, 200)
        erg = r.json()
        self.assertEqual(erg["pack_id"], "verkehrsunfall")
        self.assertGreaterEqual(erg["vorhanden"], 7)
        # Jeder vorhandene Befund trägt eine echte Fundstelle.
        for b in erg["befunde"]:
            if b["status"] == "vorhanden":
                self.assertTrue(b["belege"], f"{b['titel']} ohne Beleg")

    def test_befund_belege_sind_im_dokument(self):
        passagen = {p["kennung"] for p in self.c.get(f"/api/sitzungen/{self.sid}/passagen").json()["passagen"]}
        erg = self.c.post(f"/api/sitzungen/{self.sid}/pack", json={}).json()
        for b in erg["befunde"]:
            for q in b["belege"]:
                self.assertIn(q["kennung"], passagen)

    def test_explizites_pack(self):
        erg = self.c.post(f"/api/sitzungen/{self.sid}/pack", json={"pack_id": "miete"}).json()
        self.assertEqual(erg["pack_id"], "miete")

    def test_unbekanntes_pack_404(self):
        r = self.c.post(f"/api/sitzungen/{self.sid}/pack", json={"pack_id": "gibtsnicht"})
        self.assertEqual(r.status_code, 404)

    def test_fehlender_pflichtpunkt_nennt_schritt(self):
        from jusperfect.domain.models import Passage
        from jusperfect.services.workflow import Workflowdienst
        w = Workflowdienst()
        pack = w.pack("verkehrsunfall")
        # Nur eine belanglose Passage -> viele Pflichtpunkte fehlen.
        erg = w.pruefen(pack, [Passage(kennung="D1-S1-P1", dokument_id="D-1", dokument_titel="T", seite=1,
                                       text="Ein Satz ohne einschlägige Stichworte.")])
        self.assertGreater(erg["fehlt_pflicht"] if isinstance(erg, dict) else erg.fehlt_pflicht, 0)
        self.assertTrue((erg.offene_schritte if hasattr(erg, "offene_schritte") else erg["offene_schritte"]))


class VorschaltstufeSchalter(unittest.TestCase):
    """Ohne echte Schnittstelle darf die Oberfläche keinen Schutz vortäuschen."""

    def test_standard_nicht_aktiv(self):
        d = dienste()
        s = client(d, "ra-weber").get("/api/status").json()
        self.assertIn("perfect_shield_aktiv", s)
        self.assertFalse(s["perfect_shield_aktiv"])

    def test_vorzeitige_aktivierung_wird_abgewiesen(self):
        from tests.hilfen import einstellungen
        from jusperfect.config import KonfigurationsFehler
        with self.assertRaises(KonfigurationsFehler):
            einstellungen(JUSPERFECT_PERFECT_SHIELD="1")


class HaufeRecherche(unittest.TestCase):
    """Direktlink zur Haufe-Recherche – im Status hinterlegt, ohne Zugangsdaten."""

    def test_standard_traegt_die_adresse(self):
        s = client(dienste(), "ra-weber").get("/api/status").json()
        self.assertTrue(s["haufe_aktiv"])
        self.assertTrue(s["haufe"]["url"].startswith("https://"))
        self.assertEqual(s["haufe"]["suche_param"], "")  # kein geratener Parameter

    def test_ohne_getippte_frage_geht_die_akte_nicht_mit(self):
        """Der Knopf darf nicht die Aktenbezeichnung einsetzen.

        Vorher fiel die Oberfläche bei leerem Fragefeld auf
        ``sitzung.akte.bezeichnung`` zurück – das sind die Parteinamen. Sie
        landeten damit in der Zwischenablage, und bei eingestelltem
        Suchparameter in der Adresse. Der Haufe-Zugang ist zwar mit
        Auftragsverarbeitungsvertrag und Löschfunktion abgesichert; darauf kommt
        es nicht an: Was der Bearbeiter nicht getippt hat, geht nicht hinaus –
        er sähe es sonst nicht einmal.
        """
        quelle = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")
        anfang = quelle.index("function haufeRecherche(")
        koerper = quelle[anfang:quelle.index("\n}", anfang)]
        self.assertNotIn("akte.bezeichnung", koerper)

    def test_abschaltbar_und_suchparameter_einstellbar(self):
        from tests.hilfen import einstellungen
        s = client(dienste(einstellungen=einstellungen(JUSPERFECT_HAUFE_URL="")), "ra-weber").get("/api/status").json()
        self.assertFalse(s["haufe_aktiv"])
        s2 = client(dienste(einstellungen=einstellungen(JUSPERFECT_HAUFE_SUCHE_PARAM="q")), "ra-weber").get("/api/status").json()
        self.assertEqual(s2["haufe"]["suche_param"], "q")
