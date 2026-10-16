"""Ein Dokument, das sich nicht laden lässt, darf die übrigen nicht kosten.

Aus der Kanzlei am 25.09.2026: "es wird auch immer nur ein Dokument in das
Aktengedächtnis übernommen."

Genau das war der Grund: Die Schleife lud ein Dokument nach dem anderen und
fing dabei nur Textfehler ab, nicht das Laden selbst. Das erste ging durch,
beim zweiten warf der Adapter - und die Schleife brach ab. Auf dem Schirm
stand eine Meldung, die nach einem einzelnen Fehler aussah, während in
Wahrheit alle übrigen fehlten.

Dasselbe Muster wie an diesem Tag schon zweimal: Ein Teilfehler riss das
Ganze mit.
"""

from __future__ import annotations

import unittest
from unittest import mock

from jusperfect.domain.models import Akte, Dokument, Sitzung
from jusperfect.jurnodes.base import DokumentNichtGefunden


def _dokument(nummer: int) -> Dokument:
    return Dokument(id=f"D-{nummer}", akte_id="rec-1", titel=f"Schriftsatz {nummer}",
                    dateiname=f"s{nummer}.txt", mime_typ="text/plain")


class _AdapterMitEinemFehler:
    """Lädt alles - bis auf ein Dokument, das es nicht gibt."""

    def __init__(self, kaputt: set[str]) -> None:
        self.kaputt = kaputt
        self.versuche: list[str] = []

    def dokument_laden(self, akte_id: str, dokument_id: str):
        self.versuche.append(dokument_id)
        if dokument_id in self.kaputt:
            raise DokumentNichtGefunden(f"Dokument {dokument_id} nicht in Akte {akte_id}.")
        nummer = dokument_id.split("-")[-1]
        return _dokument(int(nummer)), b"Ein Satz mit Text."


def _dienst(adapter):
    from jusperfect.config import Einstellungen
    from jusperfect.services.sitzung import Sitzungsdienst

    d = Sitzungsdienst.__new__(Sitzungsdienst)
    d._adapter = adapter
    d._speicher = mock.MagicMock()
    d._berechtigungen = mock.MagicMock()
    d._gedaechtnis = None
    d._ocr = mock.MagicMock()
    d._e = Einstellungen.aus_umgebung({})
    return d


class EinFehlerKostetNichtDieUebrigen(unittest.TestCase):

    def setUp(self) -> None:
        self.sitzung = Sitzung(
            id="s1", nutzer_id="ra-weber", akte_id="rec-1",
            akte=Akte(id="rec-1", aktenzeichen="X-100-2026", bezeichnung="Probe"))

    def _laden(self, adapter, ids):
        d = _dienst(adapter)
        with mock.patch.object(type(d), "laden", return_value=self.sitzung):
            return d.dokumente_laden(mock.MagicMock(), "s1", ids)

    def test_das_zweite_scheitert_die_uebrigen_kommen_trotzdem(self):
        """Genau der Fall aus der Kanzlei."""
        adapter = _AdapterMitEinemFehler({"D-2"})
        sitzung = self._laden(adapter, ["D-1", "D-2", "D-3", "D-4", "D-5"])
        geladen = [g.dokument_id for g in sitzung.geladen]
        self.assertEqual(["D-1", "D-3", "D-4", "D-5"], geladen)

    def test_es_wird_bei_allen_versucht_und_nicht_abgebrochen(self):
        adapter = _AdapterMitEinemFehler({"D-2"})
        self._laden(adapter, ["D-1", "D-2", "D-3"])
        self.assertEqual(["D-1", "D-2", "D-3"], adapter.versuche)

    def test_der_fehlschlag_wird_nicht_verschwiegen(self):
        """Was nicht da ist, fällt nicht auf - also steht es als Hinweis da."""
        adapter = _AdapterMitEinemFehler({"D-2"})
        sitzung = self._laden(adapter, ["D-1", "D-2"])
        self.assertTrue([h for h in sitzung.hinweise if "nicht laden" in h])

    def test_schlaegt_alles_fehl_ist_es_ein_fehler_und_kein_hinweis(self):
        """Wer ein einziges Dokument anfordert und es nicht bekommt, soll das
        auch so erfahren - nicht in einer Hinweiszeile."""
        adapter = _AdapterMitEinemFehler({"D-1"})
        with self.assertRaises(DokumentNichtGefunden):
            self._laden(adapter, ["D-1"])

    def test_ohne_fehler_bleibt_alles_wie_es_war(self):
        adapter = _AdapterMitEinemFehler(set())
        sitzung = self._laden(adapter, ["D-1", "D-2", "D-3"])
        self.assertEqual(3, len(sitzung.geladen))
        self.assertEqual([], sitzung.hinweise)


class DieDokumentlisteWirdNichtJedesMalNeuGeholt(unittest.TestCase):
    """Seit die Unterordner mitgelesen werden, ist die Liste nicht mehr eine
    Anfrage, sondern eine je Ordner. Bei dreißig Dokumenten wären es über
    hundert - alle nacheinander, weil der Hersteller je IP eine zugleich
    zulässt."""

    def test_ein_puffer_haelt_sie_fuer_die_dauer_eines_uebernehmens(self):
        from pathlib import Path
        quelle = (Path(__file__).resolve().parent.parent / "jusperfect"
                  / "jurnodes" / "http_adapter.py").read_text(encoding="utf-8")
        self.assertIn("def _dokumente_gepuffert(", quelle)
        self.assertIn("LISTE_GILT_SEKUNDEN", quelle)
        # dokument_laden benutzt den Puffer, nicht die ungepufferte Liste.
        stelle = quelle[quelle.index("def dokument_laden("):]
        self.assertIn("_dokumente_gepuffert(akte_id)", stelle[:400])

    def test_der_puffer_gilt_nur_fuer_dieselbe_akte(self):
        import time
        from unittest import mock as m

        from jusperfect.jurnodes.http_adapter import HttpJurNodesAdapter as A

        a = A.__new__(A)
        a._liste_puffer = ("rec-1", time.monotonic(), ["gepuffert"])
        with m.patch.object(A, "dokumente", return_value=["frisch"]) as holen:
            self.assertEqual(["gepuffert"], a._dokumente_gepuffert("rec-1"))
            holen.assert_not_called()
            self.assertEqual(["frisch"], a._dokumente_gepuffert("rec-2"))
            holen.assert_called_once()

    def test_ein_alter_puffer_wird_nicht_benutzt(self):
        import time
        from unittest import mock as m

        from jusperfect.jurnodes.http_adapter import HttpJurNodesAdapter as A

        a = A.__new__(A)
        a._liste_puffer = ("rec-1", time.monotonic() - A.LISTE_GILT_SEKUNDEN - 1,
                           ["alt"])
        with m.patch.object(A, "dokumente", return_value=["frisch"]):
            self.assertEqual(["frisch"], a._dokumente_gepuffert("rec-1"))


if __name__ == "__main__":
    unittest.main()


class DieBilanzStehtVorn(unittest.TestCase):
    """Aus der Kanzlei am 25.09.2026: "er übernimmt beim Lesen der Dokumente
    nicht alle, nur 24 von 38."

    Das Programm sagte es auch vorher - in vierzehn einzelnen Sätzen, von
    denen die Oberfläche einen drei Sekunden lang zeigte. Wer eine Meldung
    über EIN Dokument liest, hält es für einen Einzelfall und zählt nicht
    nach. Was nicht da ist, fällt nicht auf.
    """

    def setUp(self) -> None:
        self.sitzung = Sitzung(
            id="s1", nutzer_id="ra-weber", akte_id="rec-1",
            akte=Akte(id="rec-1", aktenzeichen="X-100-2026", bezeichnung="Probe"))

    def _laden(self, adapter, ids):
        d = _dienst(adapter)
        with mock.patch.object(type(d), "laden", return_value=self.sitzung):
            return d.dokumente_laden(mock.MagicMock(), "s1", ids)

    def test_sie_nennt_beide_zahlen(self):
        adapter = _AdapterMitEinemFehler({"D-2", "D-5"})
        sitzung = self._laden(adapter, [f"D-{i}" for i in range(1, 6)])
        self.assertIn("3 von 5 Dokumenten gelesen", sitzung.hinweise[0])
        self.assertIn("2 nicht", sitzung.hinweise[0])

    def test_sie_steht_an_erster_stelle(self):
        """Die Oberfläche hebt die erste Zeile hervor."""
        adapter = _AdapterMitEinemFehler({"D-2"})
        sitzung = self._laden(adapter, ["D-1", "D-2", "D-3"])
        self.assertIn("von 3 Dokumenten gelesen", sitzung.hinweise[0])
        self.assertTrue(len(sitzung.hinweise) > 1, "Einzelheiten fehlen")

    def test_ohne_uebersprungene_gibt_es_keine_bilanz(self):
        """Eine Bilanz, die immer dasteht, liest niemand mehr."""
        adapter = _AdapterMitEinemFehler(set())
        sitzung = self._laden(adapter, ["D-1", "D-2"])
        self.assertEqual([], sitzung.hinweise)

    def test_die_gruende_stehen_getrennt_weil_die_abhilfe_verschieden_ist(self):
        """Ein Scan braucht Texterkennung, ein nicht geliefertes Dokument den
        Hersteller. Beides in einer Zahl wäre keine Hilfe."""
        adapter = _AdapterMitEinemFehler({"D-2"})
        sitzung = self._laden(adapter, ["D-1", "D-2"])
        self.assertIn("nicht geliefert", sitzung.hinweise[0])


class DieOberflaecheZeigtAlleHinweise(unittest.TestCase):

    @property
    def app_js(self) -> str:
        from pathlib import Path
        return (Path(__file__).resolve().parent.parent / "jusperfect" / "static"
                / "app.js").read_text(encoding="utf-8")

    def test_nicht_mehr_nur_der_erste(self):
        js = self.app_js
        self.assertNotIn("melden(hinweise[0], true)", js.replace(
            "if (hinweise.length) melden(hinweise[0], true); return; }", ""))
        self.assertIn("function hinweiseZeigen(", js)

    def test_die_leiste_bleibt_bis_man_sie_wegklickt(self):
        """Vierzehn übersprungene Dokumente gehen in sechs Sekunden unter."""
        from pathlib import Path
        html = (Path(__file__).resolve().parent.parent / "jusperfect" / "static"
                / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="uebernahme"', html)
        self.assertIn('id="uebernahme-zu"', html)

    def test_auch_nach_dem_aktualisieren_der_arbeitsakte(self):
        """Die Nachbereitung steht seit dem 16.10.2026 in einer eigenen
        Funktion: Sie wird zweimal gebraucht – beim glatten Durchlauf und
        beim Schließen, nachdem die Gegenüberstellung stehen geblieben ist.
        """
        js = self.app_js
        stelle = js[js.index("async function explorerNachbereiten("):]
        self.assertIn("hinweiseZeigen(", stelle[:3000])
        # Und sie wird aus dem Übernehmen heraus wirklich gerufen.
        uebernehmen = js[js.index("async function explorerUebernehmen("):
                         js.index("async function explorerNachbereiten(")]
        self.assertIn("explorerNachbereiten(", uebernehmen)


class DasOeffnenFragtNichtDreimalDasselbe(unittest.TestCase):
    """Aus der Kanzlei am 25.09.2026: "es dauert 8 Sekunden, damit sich das
    Fenster öffnet, um die Dateien anzukreuzen - das ist zu lang."

    Beim Öffnen wurde die Akte dreimal geholt (für die Akte selbst, für den
    Dateiordner der Dokumentliste und für den des Aktengedächtnisses) und der
    Wurzelordner zweimal. Jede Anfrage einzeln über die Leitung, weil der
    Hersteller je IP nur eine zugleich zulässt.
    """

    def _adapter(self, gefragt):
        import httpx

        from jusperfect.jurnodes.http_adapter import HttpJurNodesAdapter
        from jusperfect.security.approval import Freigabestelle

        def antworten(anfrage):
            gefragt.append(anfrage.url.path)
            if "folder/content" in anfrage.url.path:
                if "page=" in str(anfrage.url):
                    return httpx.Response(200, json={"elements": []})
                return httpx.Response(200, json={"elements": [
                    {"file": {"identifier": "f-1", "fileName": "Klage",
                              "fileExtension": "pdf"}}]})
            if "/record" in anfrage.url.path:
                return httpx.Response(200, json={"identifier": "rec-1",
                                                 "recordSign": "D-1",
                                                 "fileFolderId": 7})
            return httpx.Response(200, json={})

        return HttpJurNodesAdapter("https://beispiel.invalid", "k", Freigabestelle(),
                                   transport=httpx.MockTransport(antworten),
                                   benutzer="u")

    def test_die_akte_wird_nur_einmal_geholt(self):
        gefragt = []
        a = self._adapter(gefragt)
        a.akte("rec-1")
        a.dokumente("rec-1")
        a.gedaechtnis_lesen("rec-1")
        self.assertEqual(1, len([p for p in gefragt if p.endswith("/record")]),
                         gefragt)

    def test_der_wurzelordner_wird_nur_einmal_gelesen(self):
        gefragt = []
        a = self._adapter(gefragt)
        a.dokumente("rec-1")
        a.gedaechtnis_lesen("rec-1")
        erste_seiten = [p for p in gefragt if "folder/content" in p]
        # Eine Anfrage fuer den Inhalt, eine fuer die zweite (leere) Seite.
        self.assertLessEqual(len(erste_seiten), 2, gefragt)

    def test_nach_dem_schreiben_ist_der_puffer_leer(self):
        """Eine falsche Antwort ist schlimmer als eine langsame."""
        gefragt = []
        a = self._adapter(gefragt)
        a.dokumente("rec-1")
        vorher = len([p for p in gefragt if "folder/content" in p])
        a.gedaechtnis_ablegen("rec-1", b"x")
        a.dokumente("rec-1")
        self.assertGreater(len([p for p in gefragt if "folder/content" in p]),
                           vorher, "Der Puffer wurde nach dem Schreiben nicht geleert")


class DasGedaechtnisIstEineZugabeKeineBedingung(unittest.TestCase):
    """Aus der Kanzlei am 25.09.2026:

    "Er übernimmt direkt nur ein Dokument, und das wars. Dann ist es mir auch
    nicht möglich, die Arbeitsfläche zu öffnen, um ohne das Aktengedächtnis
    zu arbeiten. Warum ist es nicht möglich, erst einmal alle Dokumente in
    der Arbeitsfläche zu öffnen und dann unter Aktengedächtnis die Dateien
    einzulesen? So hat man immer noch die Möglichkeit zu arbeiten und
    nebenbei am Gedächtnis zu feilen."

    Und: "Wäre es möglich, die Dokumente zwar alle zu übernehmen, dann aber
    eine Meldung zu bekommen, dass es nicht im Aktengedächtnis liegt?"

    Genau so. Das Merken legt nach jedem Dokument ab; wies jur|nodes das ab,
    riss es das Übernehmen mit, und in der Arbeitsakte lag ein einziges
    Dokument. Das Programm war damit unbenutzbar - wegen einer Zugabe.
    """

    def setUp(self) -> None:
        self.sitzung = Sitzung(
            id="s1", nutzer_id="ra-weber", akte_id="rec-1",
            akte=Akte(id="rec-1", aktenzeichen="X-100-2026", bezeichnung="Probe"))

    def _laden(self, ids, gedaechtnis):
        adapter = _AdapterMitEinemFehler(set())
        d = _dienst(adapter)
        d._gedaechtnis = gedaechtnis
        with mock.patch.object(type(d), "laden", return_value=self.sitzung):
            return d.dokumente_laden(mock.MagicMock(), "s1", ids)

    def test_alle_dokumente_kommen_an_auch_wenn_das_gedaechtnis_klemmt(self):
        from jusperfect.gedaechtnis.base import GedaechtnisFehler

        ged = mock.MagicMock()
        ged.dokument_merken.side_effect = GedaechtnisFehler(
            "In dieser Akte liegt bereits ein Aktengedächtnis.")
        sitzung = self._laden(["D-1", "D-2", "D-3", "D-4"], ged)
        self.assertEqual(4, len(sitzung.geladen))

    def test_und_es_steht_da_dass_das_gedaechtnis_nicht_gesichert_wurde(self):
        from jusperfect.gedaechtnis.base import GedaechtnisFehler

        ged = mock.MagicMock()
        ged.dokument_merken.side_effect = GedaechtnisFehler(
            "In dieser Akte liegt bereits ein Aktengedächtnis.")
        sitzung = self._laden(["D-1", "D-2"], ged)
        hinweis = " ".join(sitzung.hinweise)
        self.assertIn("Dokumente sind in der Arbeitsakte", hinweis)
        self.assertIn("gearbeitet werden kann", hinweis)
        # Der Grund des Speichers steht dabei - sonst raet man.
        self.assertIn("bereits ein Aktengedächtnis", hinweis)

    def test_der_hinweis_steht_nur_einmal_da_nicht_je_dokument(self):
        """Achtunddreißig gleiche Sätze sind keine Meldung mehr."""
        from jusperfect.gedaechtnis.base import GedaechtnisFehler

        ged = mock.MagicMock()
        ged.dokument_merken.side_effect = GedaechtnisFehler("klemmt")
        sitzung = self._laden([f"D-{i}" for i in range(1, 11)], ged)
        self.assertEqual(1, len([h for h in sitzung.hinweise
                                 if "Arbeitsakte" in h]))

    def test_ohne_fehler_bleibt_alles_still(self):
        ged = mock.MagicMock()
        ged.nummer_von.return_value = 3
        sitzung = self._laden(["D-1"], ged)
        self.assertEqual([], sitzung.hinweise)
        self.assertEqual(3, sitzung.geladen[0].nummer)


class DieBilanzNenntDieDateiarten(unittest.TestCase):
    """Aus der Kanzlei am 25.09.2026, dreimal in Folge: "es werden nur 24 von
    38 Dokumenten übernommen."

    Die Bilanz sagte "14 in einem Format, das nicht gelesen werden kann" -
    aber nicht, WELCHES. Ohne das lässt sich nichts daran ändern, und die
    Frage ging dreimal hin und her, die das Programm selbst hätte beantworten
    können.
    """

    def setUp(self) -> None:
        self.sitzung = Sitzung(
            id="s1", nutzer_id="ra-weber", akte_id="rec-1",
            akte=Akte(id="rec-1", aktenzeichen="X-100-2026", bezeichnung="Probe"))

    def _laden_mit_formaten(self, dateinamen):
        """Ein Adapter, dessen Dokumente die genannten Dateinamen tragen."""
        from jusperfect.services.extraktion import NichtUnterstuetzt

        class _Adapter:
            def dokument_laden(self, akte_id, dokument_id):
                nr = int(dokument_id.split("-")[-1])
                d = Dokument(id=dokument_id, akte_id=akte_id,
                             titel=dateinamen[nr - 1], dateiname=dateinamen[nr - 1],
                             mime_typ="application/octet-stream")
                return d, b"egal"

        d = _dienst(_Adapter())
        with mock.patch.object(type(d), "laden", return_value=self.sitzung), \
                mock.patch("jusperfect.services.sitzung.text_extrahieren",
                           side_effect=NichtUnterstuetzt("Dateityp nicht unterstützt")):
            return d.dokumente_laden(mock.MagicMock(),
                                     "s1", [f"D-{i}" for i in range(1, len(dateinamen) + 1)])

    def test_die_endungen_stehen_mit_anzahl_in_der_bilanz(self):
        sitzung = self._laden_mit_formaten(
            ["a.msg", "b.msg", "c.msg", "d.zip", "e.doc"])
        bilanz = sitzung.hinweise[0]
        self.assertIn("Dateiarten:", bilanz)
        self.assertIn(".msg 3", bilanz)
        self.assertIn(".zip 1", bilanz)
        self.assertIn(".doc 1", bilanz)

    def test_die_haeufigste_art_steht_vorn(self):
        """Wer eine Zeile liest, liest den Anfang."""
        sitzung = self._laden_mit_formaten(["a.zip", "b.msg", "c.msg"])
        bilanz = sitzung.hinweise[0]
        self.assertLess(bilanz.index(".msg"), bilanz.index(".zip"))

    def test_eine_datei_ohne_endung_wird_benannt(self):
        sitzung = self._laden_mit_formaten(["Schriftsatz ohne Endung"])
        self.assertIn("ohne Endung", sitzung.hinweise[0])
