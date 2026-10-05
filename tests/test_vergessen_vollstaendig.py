"""„Vergessen" muss auch halten, wenn ein zweites Fenster offen ist.

Befunde F02.2, F02.3 und F03 der Zweitprüfung vom 05.10.2026, Gegenproben 04
und 15. F02.1 (die gespeicherte Analyse) war am selben Tag vormittags behoben
und steht in `tests/test_gedaechtnis_einzeln_vergessen.py`.

Drei Reste blieben:

* **F02.2** – ein Satz des Lebenssachverhalts mit `[Q: D1-…, D2-…]` blieb nach
  dem Entfernen von D1 stehen; nur der D1-Verweis verschwand. Dass D2 den Text
  allein trägt, wusste niemand.
* **F02.3** – eine bereits geöffnete Sitzung behielt den Auszug. Die nächste
  Frage antwortete darauf, und die Antwort wurde **neu** im Gedächtnis
  abgelegt. Die Oberfläche meldete Erfolg, und durch die Hintertür kam
  derselbe Inhalt zurück.
* **F03** – zwei Vorgänge auf einer Speicherinstanz: Der ältere überschrieb
  die Löschung des jüngeren, weil die erwartete Revision in einer gemeinsamen
  Tabelle lag statt am gelesenen Stand. Das steht in
  `tests/test_gedaechtnis_gemeinsam.py`, wo die übrigen Mehrbenutzerfälle
  stehen.

Ein Löschverlangen, das nur gilt, solange niemand ein zweites Fenster offen
hat, ist keines.
"""

from __future__ import annotations

import json
import unittest

from jusperfect.domain.models import (
    Aktenanalyse, ChronologieEintrag, GedaechtnisDokument, Seite,
)
from jusperfect.services.belegpflicht import aussage_fail_closed
from jusperfect.services.quellen import index_bauen
from tests.hilfen import client, dienste, einstellungen
from tests.test_web_ablauf import SkriptProvider

AKTE = "VU-2026-0042"
MARKER = "Die Gegenseite hat den Anspruch in voller Höhe anerkannt"


class _Umgebung:
    """Eine Akte mit Gedächtnis, einem eingelesenen Dokument und offener Sitzung."""

    def __init__(self, tmp_path, provider=None):
        self.d = dienste(einstellungen=einstellungen(
            JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=str(tmp_path)),
            provider=provider)
        self.c = client(self.d, "ra-weber")
        self.sid = self.c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
        self.c.post(f"/api/sitzungen/{self.sid}/dokumente", json={"dokument_ids": ["D-001"]})

    def gedaechtnis(self):
        return self.d.gedaechtnis.lesen(AKTE)

    def ablegen(self, g):
        self.d.gedaechtnis.ablegen(g)


def _zweites_dokument(g):
    g.dokumente.append(GedaechtnisDokument(
        dokument_id="D-ZWEI", titel="Zweite Quelle", nummer=2,
        seiten=[Seite(nummer=1, text="Ein anderer, unabhängiger Inhalt.")]))
    g.letzte_dokumentnummer = 2
    return g


class EineGemischtBelegteAussageFaelltGanz(unittest.TestCase):
    """F02.2 – der Maßstab beim Aufräumen ist ein anderer als beim Schreiben."""

    def test_beim_schreiben_genuegt_ein_tragender_beleg(self):
        """Nennt das Modell neben einer richtigen eine erfundene Kennung,
        bleibt die Aussage mit der richtigen stehen. Das ist gewollt."""
        from jusperfect.domain.models import Passage

        p = Passage(kennung="D2-S1-P1", dokument_id="D2", dokument_titel="T", seite=1, text="x")
        ergebnis = aussage_fail_closed("Gemischt [Q: D1-S1-P1, D2-S1-P1].", {p.kennung: p})
        self.assertIn("Gemischt", ergebnis.text)
        self.assertEqual(ergebnis.verworfen, 0)

    def test_beim_aufraeumen_faellt_sie(self):
        """Dort waren beim Schreiben **alle** Kennungen gültig. Löst eine
        nicht mehr auf, gehört sie zum entfernten Dokument – und die Aussage
        stand auf zwei Grundlagen, von denen eine fehlt."""
        from jusperfect.domain.models import Passage

        p = Passage(kennung="D2-S1-P1", dokument_id="D2", dokument_titel="T", seite=1, text="x")
        ergebnis = aussage_fail_closed("Gemischt [Q: D1-S1-P1, D2-S1-P1].", {p.kennung: p},
                                       verlangt_alle=True)
        self.assertNotIn("Gemischt", ergebnis.text)
        self.assertEqual(ergebnis.verworfen, 1)

    def test_der_lebenssachverhalt_wird_so_bereinigt(self, ):
        import tempfile

        with tempfile.TemporaryDirectory() as ordner:
            u = _Umgebung(ordner)
            g = _zweites_dokument(u.gedaechtnis())
            g.lebenssachverhalt = MARKER + " [Q: D1-S1-P1, D2-S1-P1]"
            u.ablegen(g)
            antwort = u.c.delete(f"/api/akten/{AKTE}/gedaechtnis/dokumente/D-001")
            self.assertEqual(antwort.status_code, 200, antwort.text)
            self.assertNotIn(MARKER, antwort.json()["lebenssachverhalt"])

    def test_ein_satz_aus_der_verbleibenden_quelle_bleibt(self):
        """Die Strenge darf nicht alles mitreißen, was sonst noch dasteht."""
        import tempfile

        with tempfile.TemporaryDirectory() as ordner:
            u = _Umgebung(ordner)
            g = _zweites_dokument(u.gedaechtnis())
            g.lebenssachverhalt = (MARKER + " [Q: D1-S1-P1, D2-S1-P1]\n\n"
                                   "Ein anderer, unabhängiger Inhalt [Q: D2-S1-P1]")
            u.ablegen(g)
            uebrig = u.c.delete(f"/api/akten/{AKTE}/gedaechtnis/dokumente/D-001").json()
            self.assertNotIn(MARKER, uebrig["lebenssachverhalt"])
            self.assertIn("unabhängiger Inhalt", uebrig["lebenssachverhalt"])


class EineOffeneSitzungBehaeltDenAuszugNichtMehr(unittest.TestCase):
    """F02.3, erster Teil."""

    def test_das_dokument_verschwindet_aus_der_offenen_sitzung(self):
        import tempfile

        with tempfile.TemporaryDirectory() as ordner:
            u = _Umgebung(ordner)
            self.assertTrue(u.d.sitzungen.passagen(u.d.speicher.sitzung_lesen(u.sid)))
            u.c.delete(f"/api/akten/{AKTE}/gedaechtnis/dokumente/D-001")
            self.assertEqual(u.d.sitzungen.passagen(u.d.speicher.sitzung_lesen(u.sid)), [])

    def test_die_sitzung_bleibt_offen_und_sagt_warum(self):
        """Sie zu schließen wäre eine Strafe für eine Löschung, die der
        Bearbeiter selbst ausgelöst hat – sein Dialog und seine Belege für
        alle übrigen Dokumente gingen mit."""
        import tempfile

        with tempfile.TemporaryDirectory() as ordner:
            u = _Umgebung(ordner)
            u.c.delete(f"/api/akten/{AKTE}/gedaechtnis/dokumente/D-001")
            sitzung = u.c.get(f"/api/sitzungen/{u.sid}")
            self.assertEqual(sitzung.status_code, 200)
            self.assertTrue(any("aus dem Aktengedächtnis entfernt" in h
                                for h in sitzung.json()["sitzung"]["hinweise"]))

    def test_der_text_ist_auch_aus_dem_sitzungsspeicher_weg(self):
        import tempfile

        with tempfile.TemporaryDirectory() as ordner:
            u = _Umgebung(ordner)
            self.assertIsNotNone(u.d.speicher.text_lesen(u.sid, "D-001"))
            u.c.delete(f"/api/akten/{AKTE}/gedaechtnis/dokumente/D-001")
            self.assertIsNone(u.d.speicher.text_lesen(u.sid, "D-001"))


class EinVerspaetetesErgebnisKommtNichtZurueck(unittest.TestCase):
    """F02.3, zweiter Teil – der Fall, den das Aufräumen allein nicht deckt.

    Die Frage war schon unterwegs, als gelöscht wurde. Ihre Antwort trifft
    danach ein und würde den gerade entfernten Inhalt neu ablegen.
    """

    def test_eine_antwort_auf_ein_entferntes_dokument_wird_nicht_gemerkt(self):
        import tempfile

        from jusperfect.domain.models import Antwort, Quelle

        with tempfile.TemporaryDirectory() as ordner:
            u = _Umgebung(ordner)
            sitzung = u.d.speicher.sitzung_lesen(u.sid)
            quelle = Quelle(kennung="D1-S1-P1", dokument_id="D-001",
                            dokument_titel="Unfallschilderung", seite=1, auszug="x")
            u.c.delete(f"/api/akten/{AKTE}/gedaechtnis/dokumente/D-001")
            u.d.gedaechtnis.antwort_merken(
                sitzung, "Unfall?", Antwort(text=MARKER + " [Q: D1-S1-P1]", quellen=[quelle]))
            self.assertEqual(u.gedaechtnis().fragen_antworten, [])

    def test_eine_antwort_auf_ein_vorhandenes_dokument_wird_gemerkt(self):
        """Die Sperre darf nicht jede Antwort verschlucken."""
        import tempfile

        from jusperfect.domain.models import Antwort, Quelle

        with tempfile.TemporaryDirectory() as ordner:
            u = _Umgebung(ordner)
            sitzung = u.d.speicher.sitzung_lesen(u.sid)
            quelle = Quelle(kennung="D1-S1-P1", dokument_id="D-001",
                            dokument_titel="Unfallschilderung", seite=1, auszug="x")
            u.d.gedaechtnis.antwort_merken(
                sitzung, "Unfall?", Antwort(text="Belegt [Q: D1-S1-P1]", quellen=[quelle]))
            self.assertEqual(len(u.gedaechtnis().fragen_antworten), 1)

    def test_ein_noch_nicht_eingelesenes_dokument_ist_etwas_anderes(self):
        """Unterschieden wird an der Grabmarke, nicht daran, ob der Auszug im
        Gedächtnis liegt – sonst fiele jede Antwort auf eine Akte, die noch
        nicht eingelesen ist."""
        import tempfile

        from jusperfect.domain.models import Antwort, Quelle

        with tempfile.TemporaryDirectory() as ordner:
            u = _Umgebung(ordner)
            sitzung = u.d.speicher.sitzung_lesen(u.sid)
            fremd = Quelle(kennung="D9-S1-P1", dokument_id="D-NEU",
                           dokument_titel="Noch nicht gelesen", seite=1, auszug="x")
            u.d.gedaechtnis.antwort_merken(
                sitzung, "Was?", Antwort(text="Belegt [Q: D9-S1-P1]", quellen=[fremd]))
            self.assertEqual(len(u.gedaechtnis().fragen_antworten), 1)

    def test_ein_bewusstes_wiedereinlesen_nimmt_die_grabmarke_zurueck(self):
        """Der Bericht verlangt genau das: ein späteres Wiedereinlesen muss
        eine eigene Benutzerhandlung sein – und dann auch wirken."""
        import tempfile

        with tempfile.TemporaryDirectory() as ordner:
            u = _Umgebung(ordner)
            u.c.delete(f"/api/akten/{AKTE}/gedaechtnis/dokumente/D-001")
            self.assertIn("D-001", u.gedaechtnis().vergessene_dokumente)
            # Dasselbe Dokument erneut in die Sitzung holen.
            u.c.post(f"/api/sitzungen/{u.sid}/dokumente", json={"dokument_ids": ["D-001"]})
            self.assertNotIn("D-001", u.gedaechtnis().vergessene_dokumente)

    def test_die_grabmarke_traegt_nur_die_kennung(self):
        """Kein Inhalt: nur die Nummer, die in jur|nodes ohnehin steht."""
        import tempfile

        with tempfile.TemporaryDirectory() as ordner:
            u = _Umgebung(ordner)
            u.c.delete(f"/api/akten/{AKTE}/gedaechtnis/dokumente/D-001")
            self.assertEqual(u.gedaechtnis().vergessene_dokumente, ["D-001"])


class DasFensterZeigtNichtMehrWasEsNichtMehrHat(unittest.TestCase):
    """Im Browser gesehen, am 05.10.2026.

    Der Server nahm das Dokument aus der Sitzung – und die linke Spalte zeigte
    seinen Text weiter, weil die Oberfläche nur die Gedächtnisansicht neu
    zeichnete. Ein Fenster, das zeigt, was es nicht mehr hat, ist schlimmer
    als eines, das gar nichts zeigt: Es lädt zum Zitieren ein.
    """

    def _app_js(self) -> str:
        from pathlib import Path

        return (Path(__file__).resolve().parent.parent
                / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")

    def test_nach_dem_vergessen_wird_die_sitzung_neu_geladen(self):
        quelle = self._app_js()
        block = quelle.split("gedaechtnis/dokumente/${dok}")[1][:900]
        self.assertIn('api("GET", `/api/sitzungen/', block)
        self.assertIn("passagenLaden()", block)


if __name__ == "__main__":
    unittest.main()
