"""Posteingang: Stabilitätsprüfung, Vorbereitung, Eingangsprüfung – Mensch bleibt Tor."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from tests.hilfen import client, dienste, einstellungen

from jusperfect.services.watchfolder import (
    GeseheneDatei, STATUS_DATEI, scan, status_text,
)


class Watchfolder(unittest.TestCase):
    """Der reine Scan: erst wenn die Größe stabil ist, gilt eine Datei als bereit."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ordner = Path(self._tmp.name)
        self.endungen = frozenset({".txt"})

    def _datei(self, name, inhalt):
        (self.ordner / name).write_text(inhalt, encoding="utf-8")

    def test_neue_datei_wartet_dann_bereit(self):
        self._datei("post.txt", "Hallo")
        d1 = scan(self.ordner, self.endungen, {}, frozenset(), 0.0)
        self.assertEqual(d1.bereit, ())
        self.assertEqual([p.name for p in d1.wartend], ["post.txt"])
        # Gleiche Größe, genug Zeit vergangen -> bereit.
        d2 = scan(self.ordner, self.endungen, d1.gesehen, frozenset(), 10.0)
        self.assertEqual([p.name for p in d2.bereit], ["post.txt"])

    def test_wachsende_datei_startet_uhr_neu(self):
        self._datei("post.txt", "A")
        d1 = scan(self.ordner, self.endungen, {}, frozenset(), 0.0)
        self._datei("post.txt", "A viel mehr Text")  # gewachsen
        d2 = scan(self.ordner, self.endungen, d1.gesehen, frozenset(), 10.0)
        self.assertEqual(d2.bereit, ())  # Uhr neu gestartet, noch nicht stabil
        d3 = scan(self.ordner, self.endungen, d2.gesehen, frozenset(), 20.0)
        self.assertEqual([p.name for p in d3.bereit], ["post.txt"])

    def test_verarbeitete_und_fremde_endungen_uebergangen(self):
        self._datei("post.txt", "X" * 20)
        self._datei("bild.xyz", "Y" * 20)
        d = scan(self.ordner, self.endungen, {}, frozenset({"post.txt"}), 100.0)
        self.assertEqual(d.bereit, ())
        self.assertEqual(d.wartend, ())  # post.txt verarbeitet, .xyz falsche Endung

    def test_statusdatei_ohne_inhalte(self):
        text = status_text(self.ordner, vorbereitet=2, wartend=1, fehler={"x.txt": "kaputt"},
                           geprueft_am=datetime(2026, 9, 3, 17, 0, 0))
        self.assertIn("Vorbereitet und wartet auf Prüfung: 2", text)
        self.assertIn("Noch in Übertragung", text)
        self.assertIn("von einem Menschen geöffnet", text)
        self.assertNotIn("Hallo", text)  # nie Inhalte


class Posteingangsdienst(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ordner = Path(self._tmp.name)
        self.uhr = [0.0]
        self.d = dienste(einstellungen=einstellungen(JUSPERFECT_POSTEINGANG_ORDNER=str(self.ordner)))
        self.d.posteingang._uhr = lambda: self.uhr[0]
        self.c = client(self.d, "ra-weber")

    def _eingang(self, name, inhalt):
        (self.ordner / name).write_text(inhalt, encoding="utf-8")

    def _vorbereiten(self):
        """Zwei Durchgänge, dazwischen vergeht Zeit – Datei wird stabil und bereit."""
        self.d.posteingang.pruefen()
        self.uhr[0] = 10.0
        return self.d.posteingang.pruefen()

    def test_aktiv_nur_mit_ordner(self):
        ohne = dienste()  # kein Ordner
        self.assertFalse(ohne.posteingang.aktiv)
        self.assertTrue(self.d.posteingang.aktiv)

    def test_vorbereiten_listet_ohne_inhalt_und_schont_datei(self):
        self._eingang("schreiben.txt", "Sehr geehrte Damen und Herren, Frist bis zum 30.09.2026.")
        erg = self._vorbereiten()
        self.assertEqual(len(erg["eintraege"]), 1)
        e = erg["eintraege"][0]
        self.assertEqual(e["dateiname"], "schreiben.txt")
        self.assertGreater(e["zeichen"], 0)
        self.assertNotIn("Frist", str(e))  # Überblick trägt keinen Inhalt
        # Originaldatei unangetastet, nur die Statusdatei kam hinzu.
        self.assertTrue((self.ordner / "schreiben.txt").exists())
        self.assertTrue((self.ordner / STATUS_DATEI).exists())

    def test_datei_wird_nur_einmal_vorbereitet(self):
        self._eingang("a.txt", "Inhalt eins zwei drei")
        self._vorbereiten()
        self.uhr[0] = 20.0
        erg = self.d.posteingang.pruefen()  # kein neuer Vorgang
        self.assertEqual(len(erg["eintraege"]), 1)

    def test_endpunkt_zeigt_und_prueft_eingang(self):
        self._eingang("unfall.txt",
                      "Unfallschilderung. Der Gegner fuhr mit mindestens 120 km/h. Frist bis zum 30.09.2026.")
        self._vorbereiten()
        liste = self.c.get("/api/posteingang").json()
        self.assertTrue(liste["aktiv"])
        self.assertEqual(len(liste["eintraege"]), 1)
        eid = liste["eintraege"][0]["id"]
        # Passagen lesbar
        passagen = self.c.get(f"/api/posteingang/{eid}/passagen").json()["passagen"]
        self.assertTrue(passagen)
        # Eingangsprüfung (Triage) über die vorhandene Analyse
        triage = self.c.post(f"/api/posteingang/{eid}/triage")
        self.assertEqual(triage.status_code, 200)
        self.assertIn("dokumentart", triage.json())

    def test_verwerfen_nimmt_aus_dem_blick_ohne_datei_zu_loeschen(self):
        self._eingang("weg.txt", "Etwas Text hier drin")
        self._vorbereiten()
        eid = self.c.get("/api/posteingang").json()["eintraege"][0]["id"]
        self.assertEqual(self.c.delete(f"/api/posteingang/{eid}").status_code, 204)
        self.assertEqual(self.c.get("/api/posteingang").json()["eintraege"], [])
        self.assertTrue((self.ordner / "weg.txt").exists())

    def test_verworfenes_laesst_sich_zurueckholen(self):
        """Ein Fehlgriff im Posteingang darf nicht die Texterkennung neu kosten."""
        self._eingang("versehen.txt", "Ein Schreiben, das nicht weg soll")
        self._vorbereiten()
        eid = self.c.get("/api/posteingang").json()["eintraege"][0]["id"]
        self.c.delete(f"/api/posteingang/{eid}")
        self.assertEqual(self.c.get("/api/posteingang").json()["eintraege"], [])

        antwort = self.c.post(f"/api/posteingang/{eid}/zurueckholen")
        self.assertEqual(antwort.status_code, 200)
        self.assertEqual(antwort.json()["dateiname"], "versehen.txt")

        eintraege = self.c.get("/api/posteingang").json()["eintraege"]
        self.assertEqual([e["id"] for e in eintraege], [eid])
        # Und der Vorgang ist vollständig da, nicht nur dem Namen nach.
        self.assertTrue(self.c.get(f"/api/posteingang/{eid}/passagen").json()["passagen"])

    def test_zweimal_zurueckholen_geht_nicht(self):
        """Sonst legte ein Doppelklick denselben Vorgang zweimal hin."""
        self._eingang("einmal.txt", "Ein Schreiben")
        self._vorbereiten()
        eid = self.c.get("/api/posteingang").json()["eintraege"][0]["id"]
        self.c.delete(f"/api/posteingang/{eid}")
        self.assertEqual(self.c.post(f"/api/posteingang/{eid}/zurueckholen").status_code, 200)
        zweite = self.c.post(f"/api/posteingang/{eid}/zurueckholen")
        self.assertEqual(zweite.status_code, 422)
        self.assertIn("zurückholen", zweite.json()["fehler"])

    def test_unbekanntes_zurueckholen_sagt_das(self):
        antwort = self.c.post("/api/posteingang/gibtesnicht/zurueckholen")
        self.assertEqual(antwort.status_code, 422)

    def test_ruecklage_bleibt_klein(self):
        """Die Rücklage hält Aktentext. Sie ist ein Rückgängig, kein Papierkorb."""
        from jusperfect.services.posteingang import RUECKLAGE

        eids = []
        for nummer in range(RUECKLAGE + 2):
            self._eingang(f"post{nummer}.txt", f"Schreiben Nummer {nummer} mit Text")
            self.uhr[0] += 20.0
            self.d.posteingang.pruefen()
        # Der Scan sieht eine Datei erst beim zweiten Blick als stabil an - der
        # zuletzt gelegte Vorgang braucht also noch einen Durchgang.
        self.uhr[0] += 20.0
        self.d.posteingang.pruefen()
        eids = [e["id"] for e in self.c.get("/api/posteingang").json()["eintraege"]]
        self.assertEqual(len(eids), RUECKLAGE + 2)
        # Alle verwerfen - die ältesten fallen aus der Rücklage heraus.
        for eid in reversed(eids):   # Liste ist neueste zuerst
            self.c.delete(f"/api/posteingang/{eid}")
        zurueck = [eid for eid in eids
                   if self.c.post(f"/api/posteingang/{eid}/zurueckholen").status_code == 200]
        self.assertEqual(len(zurueck), RUECKLAGE)

    def test_ruecklage_laeuft_mit_derselben_frist_ab(self):
        """Verworfenes darf Aktentext nicht länger halten als der Posteingang selbst."""
        from jusperfect.services.posteingang import VORGANG_TTL_SEKUNDEN

        self._eingang("alt.txt", "Ein Schreiben, das verfallen soll")
        self._vorbereiten()
        eid = self.c.get("/api/posteingang").json()["eintraege"][0]["id"]
        self.c.delete(f"/api/posteingang/{eid}")
        self.uhr[0] += VORGANG_TTL_SEKUNDEN + 1
        self.assertEqual(self.c.post(f"/api/posteingang/{eid}/zurueckholen").status_code, 422)

    def test_status_kennt_posteingang(self):
        s = self.c.get("/api/status").json()
        self.assertTrue(s["posteingang_aktiv"])


if __name__ == "__main__":
    unittest.main()
