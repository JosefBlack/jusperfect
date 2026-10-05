"""Das Aktengedächtnis liegt in der Akte – sichtbar, und sonst nichts.

Aus der Kanzlei: „Ich möchte das Gedächtnis in der Akte haben. Ich möchte nicht
lange nach dem Gedächtnis suchen müssen. Er soll oben liegen."

Und, als Regel dazu freigegeben:

    jusperfect schreibt in die Akte genau eine eigene Datei – das
    Aktengedächtnis. Nur diese eine Datei darf es ohne Einzelfreigabe anlegen,
    überschreiben und löschen. Auf alle übrigen Inhalte der Akte bleibt der
    Zugriff lesend; ein Vermerk oder Entwurf entsteht dort weiterhin nur nach
    ausdrücklicher Freigabe.

Diese Datei prüft beide Hälften: dass das Gedächtnis wirklich in der Akte
ankommt und oben steht – und dass über diesen Weg nichts anderes hineingelangt.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent

from jusperfect.domain.models import Aktengedaechtnis, GedaechtnisDokument, Seite
from jusperfect.gedaechtnis.akte import AkteGedaechtnisSpeicher
from jusperfect.gedaechtnis.base import GedaechtnisFehler
from jusperfect.gedaechtnis.packen import ist_gepackt, packen
from jusperfect.jurnodes.base import GEDAECHTNIS_DATEI
from jusperfect.jurnodes.fixture_adapter import FixtureJurNodesAdapter
from jusperfect.security.approval import Freigabestelle


def _akte_anlegen(wurzel: Path, akte_id: str, aktenzeichen: str) -> Path:
    ordner = wurzel / akte_id
    ordner.mkdir(parents=True)
    (ordner / "akte.json").write_text(json.dumps({
        "akte": {"id": akte_id, "aktenzeichen": aktenzeichen, "bezeichnung": "Probe",
                 "rechtsgebiet": "Bau", "sachbearbeiter": "RA Dr. Weber", "status": "offen"},
        "dokumente": [{"id": "D-001", "titel": "Schriftsatz", "dateiname": "01_schriftsatz.txt",
                       "datum": "2025-06-20", "kategorie": "Mandant"}],
        "beteiligte": [], "fristen": [],
    }, ensure_ascii=False), encoding="utf-8")
    (ordner / "01_schriftsatz.txt").write_text("Text der Akte.", encoding="utf-8")
    return ordner


def _gedaechtnis(akte_id: str) -> Aktengedaechtnis:
    return Aktengedaechtnis(
        akte_id=akte_id, aktenzeichen="44/26 BA", bezeichnung="Probe",
        lebenssachverhalt="Die Bauherrin rügte am 20.06.2025.",
        dokumente=[GedaechtnisDokument(dokument_id="D-001", titel="Schriftsatz", nummer=1,
                                       seiten=[Seite(nummer=1, text="Inhalt " * 200)])])


class InDerAkte(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.wurzel = Path(self._tmp.name)
        self.ordner = _akte_anlegen(self.wurzel, "BA-2026-0044", "44/26 BA")
        self.adapter = FixtureJurNodesAdapter(self.wurzel, Freigabestelle(), schreibbar=True)
        self.speicher = AkteGedaechtnisSpeicher(self.adapter)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_die_datei_landet_im_aktenordner(self):
        self.speicher.ablegen(_gedaechtnis("BA-2026-0044"))
        self.assertTrue((self.ordner / GEDAECHTNIS_DATEI).is_file())

    def test_sie_steht_im_ordner_ganz_oben(self):
        """Der eigentliche Wunsch: sehen, nicht suchen."""
        self.speicher.ablegen(_gedaechtnis("BA-2026-0044"))
        namen = sorted(p.name for p in self.ordner.iterdir())
        self.assertEqual(GEDAECHTNIS_DATEI, namen[0],
                         f"Die Gedächtnisdatei steht nicht oben, sondern hier: {namen}")

    def test_sie_liegt_gepackt_da(self):
        self.speicher.ablegen(_gedaechtnis("BA-2026-0044"))
        self.assertTrue(ist_gepackt((self.ordner / GEDAECHTNIS_DATEI).read_bytes()))

    def test_was_abgelegt_wurde_kommt_wieder(self):
        vorher = _gedaechtnis("BA-2026-0044")
        self.speicher.ablegen(vorher)
        self.assertEqual(vorher.model_dump_json(),
                         self.speicher.lesen("BA-2026-0044").model_dump_json())

    def test_ohne_gedaechtnis_kommt_nichts(self):
        self.assertIsNone(self.speicher.lesen("BA-2026-0044"))

    def test_loeschen_entfernt_nur_diese_eine_datei(self):
        self.speicher.ablegen(_gedaechtnis("BA-2026-0044"))
        vorher = {p.name for p in self.ordner.iterdir()}

        self.speicher.loeschen("BA-2026-0044")

        self.assertIsNone(self.speicher.lesen("BA-2026-0044"))
        self.assertEqual(vorher - {GEDAECHTNIS_DATEI},
                         {p.name for p in self.ordner.iterdir()},
                         "Es ist mehr verschwunden als die Gedächtnisdatei.")

    def test_die_akte_selbst_bleibt_unberuehrt(self):
        """Der Schreibweg darf nur diese eine Datei anfassen."""
        vorher = {p.name: p.read_bytes() for p in self.ordner.iterdir()}
        self.speicher.ablegen(_gedaechtnis("BA-2026-0044"))
        for name, inhalt in vorher.items():
            self.assertEqual(inhalt, (self.ordner / name).read_bytes(),
                             f"{name} wurde verändert.")

    def test_ein_fremdes_gedaechtnis_im_ordner_wird_abgewiesen(self):
        """Kopierte Aktenordner sind der übliche Weg zu fremdem Aktentext."""
        (self.ordner / GEDAECHTNIS_DATEI).write_bytes(packen(_gedaechtnis("AR-2026-0115")))
        with self.assertRaises(GedaechtnisFehler) as fehler:
            self.speicher.lesen("BA-2026-0044")
        self.assertIn("anderen Akte", str(fehler.exception))

    def test_schreibgeschuetzt_wird_gesagt_statt_verschwiegen(self):
        """Sonst meldete das Programm 'gesichert', und es wäre nichts geschehen."""
        nur_lesen = AkteGedaechtnisSpeicher(
            FixtureJurNodesAdapter(self.wurzel, Freigabestelle(), schreibbar=False))
        with self.assertRaises(GedaechtnisFehler) as fehler:
            nur_lesen.ablegen(_gedaechtnis("BA-2026-0044"))
        self.assertIn("schreibgeschützt", str(fehler.exception))
        self.assertFalse((self.ordner / GEDAECHTNIS_DATEI).exists())


class AufsichtUeberAlleAkten(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.wurzel = Path(self._tmp.name)
        for akte_id, az in (("BA-2026-0044", "44/26 BA"), ("AR-2026-0115", "115/26 AR"),
                            ("VU-2026-0042", "42/26 VU")):
            _akte_anlegen(self.wurzel, akte_id, az)
        self.speicher = AkteGedaechtnisSpeicher(
            FixtureJurNodesAdapter(self.wurzel, Freigabestelle(), schreibbar=True))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_gezaehlt_wird_nur_was_ein_gedaechtnis_hat(self):
        self.speicher.ablegen(_gedaechtnis("BA-2026-0044"))
        self.speicher.ablegen(_gedaechtnis("AR-2026-0115"))
        self.assertEqual({"AR-2026-0115", "BA-2026-0044"},
                         {g.akte_id for g in self.speicher.auflisten()})

    def test_eine_beschaedigte_datei_haelt_die_aufsicht_nicht_an(self):
        """Sonst verdeckte ein einziger kaputter Ordner alle anstehenden Fristen."""
        self.speicher.ablegen(_gedaechtnis("BA-2026-0044"))
        (self.wurzel / "AR-2026-0115" / GEDAECHTNIS_DATEI).write_bytes(b"\x1f\x8bkaputt")

        liste = self.speicher.auflisten()

        self.assertEqual(["BA-2026-0044"], [g.akte_id for g in liste])


class UeberDieSchnittstelle(unittest.TestCase):
    """Seit dem 23.09.2026 geht das Aktengedächtnis auch über die REST-Schnittstelle.

    Bis dahin stand hier „noch nicht eingerichtet" – zu Recht: Es fehlte die
    Dokumentation des Herstellers, und geraten wird bei Dritten nicht. An
    diesem Tag lag sie vor, und die Kanzlei hat den Zugang freigeschaltet.

    Ein Unterschied zum Laufwerk bleibt und ist der Grund für die Prüfungen
    unten: Dort wird die Datei überschrieben. Hier gibt es nur „hinzufügen",
    und was mit einer gleichnamigen Datei geschieht, sagt die Beschreibung des
    Herstellers nicht. Es wird deshalb **nachgesehen**, nicht angenommen.
    """

    def _adapter(self, dateien: list[dict], nach_dem_ablegen: list[dict] | None = None):
        import httpx

        from jusperfect.jurnodes.base import GEDAECHTNIS_DATEI
        from jusperfect.jurnodes.http_adapter import HttpJurNodesAdapter
        from jusperfect.security.approval import Freigabestelle

        self.abgelegt: list[bytes] = []
        self.kopfzeilen: list[dict] = []
        zustand = {"dateien": dateien}

        def antwort(request: httpx.Request) -> httpx.Response:
            pfad = request.url.path
            if pfad.endswith("/record"):
                return httpx.Response(200, json={"identifier": "rec-1", "fileFolderId": 77})
            if pfad.endswith("/file-system/folder/content"):
                return httpx.Response(200, json={"pagesTotal": 1, "elements": [
                    {"type": "file", "file": d} for d in zustand["dateien"]]})
            if pfad.endswith("/file-system/file/download"):
                return httpx.Response(200, content=b"GEDAECHTNIS")
            if pfad.endswith("/file-system/add-file"):
                self.abgelegt.append(request.content)
                self.kopfzeilen.append(dict(request.headers))
                if nach_dem_ablegen is not None:
                    zustand["dateien"] = nach_dem_ablegen
                return httpx.Response(201, json={"identifier": "neu"})
            return httpx.Response(404)

        self.GEDAECHTNIS_DATEI = GEDAECHTNIS_DATEI
        return HttpJurNodesAdapter("https://jurnodes.example/api", "s", Freigabestelle(),
                                   transport=httpx.MockTransport(antwort))

    @property
    def _eintrag(self) -> dict:
        from jusperfect.jurnodes.base import GEDAECHTNIS_DATEI
        name, _, endung = GEDAECHTNIS_DATEI.rpartition(".")
        return {"identifier": "ged-1", "fileName": name, "fileExtension": endung}

    def test_ohne_datei_gibt_es_kein_gedaechtnis(self):
        """Nicht ein Fehler, sondern „noch keines" – so faengt jede Akte an."""
        a = self._adapter([])
        self.assertIsNone(a.gedaechtnis_lesen("rec-1"))

    def test_die_vorhandene_datei_wird_gelesen(self):
        a = self._adapter([self._eintrag])
        self.assertEqual(b"GEDAECHTNIS", a.gedaechtnis_lesen("rec-1"))

    def test_es_wird_unter_dem_festen_namen_abgelegt(self):
        """Der Name steht fest. Ueber diesen Weg kann genau eine Datei
        entstehen, und keine andere."""
        a = self._adapter([], nach_dem_ablegen=[self._eintrag])
        a.gedaechtnis_ablegen("rec-1", b"inhalt")
        self.assertIn(self.GEDAECHTNIS_DATEI.encode(), self.abgelegt[0])
        self.assertIn(b"inhalt", self.abgelegt[0])

    def test_es_verlangt_ausdruecklich_das_ersetzen(self):
        """autoRenameIfExist bleibt aus - aber aus einem anderen Grund als
        frueher.

        Frueher sollte der Server abweisen, wenn er nicht ersetzen kann. Das
        tut er (gemessen am 25.09.2026), und deshalb vergeben wir den Namen
        jetzt selbst. Der Schalter bleibt trotzdem aus: Was jur|nodes beim
        Umbenennen tut, steht nirgends - ein Name, den wir nicht kennen, ist
        einer, den wir nicht wiederfinden.
        """
        a = self._adapter([], nach_dem_ablegen=[self._eintrag])
        a.gedaechtnis_ablegen("rec-1", b"inhalt")
        self.assertEqual("false", self.kopfzeilen[0]["autorenameifexist"])
        self.assertEqual("77", self.kopfzeilen[0]["folderid"])

    def test_alte_fassungen_mit_zeitstempel_bleiben_lesbar(self):
        """Am 25.09.2026 lagen kurz Fassungen mit Zeitstempel in Akten. Der
        Weg wurde zurueckgenommen - wo aber welche liegen, sollen sie nicht
        verlorengehen."""
        from jusperfect.jurnodes.base import ist_gedaechtnis_datei

        self.assertTrue(ist_gedaechtnis_datei(
            "00_Aktengedaechtnis-20260925-113000.json.gz"))

    def test_zwei_dateien_sind_der_zustand_und_kein_fehler(self):
        """Bis zum 25.09.2026 war das ein Fehler, und das war richtig gedacht:
        Legte der Server die neue Datei NEBEN die alte, verdoppelte sich das
        Gedaechtnis bei jedem Sichern.

        Inzwischen ist gemessen, dass jur|nodes GAR NICHT ersetzt, und das
        Loeschrecht hat die Kanzlei bewusst nicht erteilt. Also mehrere
        Fassungen mit Zeitstempel - und der Fehler ist keiner mehr.
        """
        zweimal = [self._eintrag, {**self._eintrag, "identifier": "ged-2"}]
        a = self._adapter([], nach_dem_ablegen=zweimal)
        a.gedaechtnis_ablegen("rec-1", b"inhalt")   # wirft nicht

    def test_beim_lesen_wird_die_juengste_genommen(self):
        a = self._adapter([self._eintrag, {**self._eintrag, "identifier": "ged-2"}])
        self.assertIsNotNone(a.gedaechtnis_lesen("rec-1"))
        self.assertEqual(2, a.letzte_fassungen)

    def test_geloescht_wird_ueber_die_schnittstelle_nichts(self):
        """Das Recht „Datei loeschen" gaelte fuer JEDE Datei der Kanzlei, nicht
        nur fuer diese eine. Dafuer ist der Preis zu hoch."""
        from jusperfect.jurnodes.base import JurNodesFehler

        a = self._adapter([self._eintrag])
        with self.assertRaises(JurNodesFehler) as fehler:
            a.gedaechtnis_loeschen("rec-1")
        self.assertIn("löscht jusperfect nichts", str(fehler.exception))


class NochNichtUeberDieSchnittstelle(unittest.TestCase):
    def test_ein_zugang_ohne_diesen_weg_wird_frueh_abgewiesen(self):
        class OhneGedaechtnis:
            def akten_suchen(self, suchbegriff: str = ""):
                return []

        with self.assertRaises(GedaechtnisFehler) as fehler:
            AkteGedaechtnisSpeicher(OhneGedaechtnis())
        self.assertIn("JUSPERFECT_GEDAECHTNIS=lokal", str(fehler.exception))




class DieOberflaecheSagtWoEsLiegt(unittest.TestCase):
    """Ein fest eingebauter Satz wäre in einem der beiden Fälle unwahr.

    In der Auswahl („links die Akte, rechts das Gedächtnis") stand bisher
    unverändert „gespeichert wird bei jusperfect, nicht in jur|nodes". Seit das
    Gedächtnis auch in der Akte liegen kann, ist das je nach Einstellung falsch
    – und zwar über die Frage, die an dieser Stelle am meisten zählt.
    """

    def _status(self, **extra):
        from tests.hilfen import client, dienste, einstellungen
        e = einstellungen(**extra)
        return client(dienste(einstellungen=e), "ra-weber").get("/api/status").json()

    def test_der_ort_wird_gemeldet(self):
        import tempfile as tf
        with tf.TemporaryDirectory() as tmp:
            self.assertEqual("lokal", self._status(JUSPERFECT_GEDAECHTNIS="lokal",
                                                   JUSPERFECT_GEDAECHTNIS_PFAD=tmp)["gedaechtnis_ort"])
        self.assertEqual("aus", self._status()["gedaechtnis_ort"])

    def test_die_oberflaeche_entscheidet_nicht_mehr_fest(self):
        quelle = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('K.gedaechtnisOrt === "akte"', quelle)
        self.assertIn("gespeichert wird in der Akte selbst", quelle)


if __name__ == "__main__":
    unittest.main()
