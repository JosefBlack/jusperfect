"""Was in der Dokumentliste einer Akte steht - und was nicht.

Aus der Kanzlei am 25.09.2026: "es wurde auch nur ein Dokument von der Akte
angezeigt" und "er hat nur eine Datei ins Aktengedächtnis abgespeichert, und
auf die anderen Dateien kann er somit nicht zugreifen."

Zwei Dinge kamen dabei heraus. Das eine ist hier behoben: Das
Aktengedächtnis ist die Arbeitsdatei des Programms und kein Dokument der
Akte - es stand trotzdem in der Liste. Vorher konnte das nicht auffallen:
Ohne Zurückschreiben gab es die Datei gar nicht.
"""

from __future__ import annotations

import unittest

import httpx

from jusperfect.jurnodes.base import GEDAECHTNIS_DATEI
from jusperfect.jurnodes.http_adapter import HttpJurNodesAdapter
from jusperfect.security.approval import Freigabestelle


def _adapter(eintraege):
    def antworten(anfrage):
        if "folder/content" in anfrage.url.path:
            if "page=" in str(anfrage.url):
                return httpx.Response(200, json={"elements": []})
            return httpx.Response(200, json={"elements": eintraege})
        if "/record" in anfrage.url.path and "search" not in anfrage.url.path:
            return httpx.Response(200, json={"identifier": "rec-1", "fileFolderId": 7})
        return httpx.Response(200, json={})

    return HttpJurNodesAdapter("https://beispiel.invalid", "k", Freigabestelle(),
                               transport=httpx.MockTransport(antworten), benutzer="u")


def _datei(name, kennung="f-1"):
    return {"file": {"identifier": kennung, "fileName": name}}


class DasAktengedaechtnisIstKeinDokument(unittest.TestCase):

    def test_die_alte_feste_datei_steht_nicht_in_der_liste(self):
        a = _adapter([_datei(GEDAECHTNIS_DATEI), _datei("Klageschrift.pdf", "f-2")])
        namen = [d.titel or d.dateiname for d in a.dokumente("rec-1")]
        self.assertEqual(1, len(namen), namen)
        self.assertNotIn(GEDAECHTNIS_DATEI, " ".join(namen))

    def test_auch_keine_der_fassungen_mit_zeitstempel(self):
        a = _adapter([
            _datei("00_Aktengedaechtnis-20260920-090000.json.gz", "g-1"),
            _datei("00_Aktengedaechtnis-20260925-113000.json.gz", "g-2"),
            _datei("Klageschrift.pdf", "f-2"),
        ])
        self.assertEqual(1, len(a.dokumente("rec-1")))

    def test_eine_akte_mit_nur_dem_gedaechtnis_hat_keine_dokumente(self):
        """Genau der Fall aus der Kanzlei: ein einziges "Dokument", und das
        war unsere eigene Arbeitsdatei."""
        a = _adapter([_datei(GEDAECHTNIS_DATEI)])
        self.assertEqual([], a.dokumente("rec-1"))

    def test_eine_aehnlich_benannte_akte_bleibt_sichtbar(self):
        """Nicht zu viel wegfiltern: Was nicht da ist, fällt nicht auf."""
        a = _adapter([_datei("00_Aktengedaechtnis_Notizen.docx"),
                      _datei("Aktengedaechtnis der Gegenseite.pdf", "f-2")])
        self.assertEqual(2, len(a.dokumente("rec-1")))


class DieProbeMisstDieOrdner(unittest.TestCase):
    """Sie hat den Befund geliefert, auf dem die Rekursion beruht."""

    def test_ein_ordnereintrag_ohne_nummer_liefert_kein_dokument(self):
        """Ein Eintrag, der sich Ordner nennt, aber keine Nummer hat, wird
        uebersprungen statt zu einem Dokument gemacht."""
        a = _adapter([{"type": "folder", "identifier": "o-1", "name": "Schriftsätze"},
                      _datei("Klageschrift.pdf", "f-2")])
        self.assertEqual(1, len(a.dokumente("rec-1")))

    def test_die_probe_geht_die_unterordner_mit_durch(self):
        """Sonst prüft sie etwas anderes als der Betrieb.

        Am 25.09.2026 zeigte sie für eine Akte "pdf 21, docx 8" - lauter
        lesbare Formate -, während im Betrieb 14 von 38 Dokumenten
        ungelesen blieben. Die Erklärung lag in den Unterordnern, die sie
        nicht mitzählte. Schlimmer noch: Sie sagte dazu "was darin liegt,
        liest das Programm heute nicht mit", und das stimmte seit dem
        Vormittag nicht mehr.
        """
        from pathlib import Path
        quelle = (Path(__file__).resolve().parent.parent
                  / "jusperfect" / "jurnodestest.py").read_text(encoding="utf-8")
        abschnitt = quelle[quelle.index("def _ordner_aufteilen("):
                           quelle.index("def _kennung_aus_suche(")]
        # Sie steigt in die Unterordner ab - mit denselben Grenzen wie der
        # Betrieb: fuenf Stufen, jede Nummer einmal.
        self.assertIn("_ordner_aufteilen(client, endpunkte, nummer", abschnitt)
        self.assertIn("tiefe < 5", abschnitt)
        self.assertIn("gesehen", abschnitt)
        # Und der veraltete Satz wird nicht mehr AUSGEGEBEN. Im Docstring
        # steht er weiter - dort erklaert er, warum er weg ist.
        ausgaben = [z for z in abschnitt.splitlines() if "_sagen(" in z]
        self.assertFalse([z for z in ausgaben if "liest das" in z], ausgaben)
        # Keine Dateinamen im Befund - er wird weitergegeben.
        self.assertNotIn("fileName}", abschnitt)

    def test_die_probe_nennt_die_nicht_lesbaren_arten(self):
        """Die Zahl allein hilft nicht - die Endung schon."""
        from pathlib import Path
        quelle = (Path(__file__).resolve().parent.parent
                  / "jusperfect" / "jurnodestest.py").read_text(encoding="utf-8")
        abschnitt = quelle[quelle.index("def _ordner_aufteilen("):
                           quelle.index("def _kennung_aus_suche(")]
        self.assertIn("Davon nicht lesbar", abschnitt)
        # Die Liste der lesbaren Arten muss zu der im Programm passen.
        for art in ("pdf", "docx", "msg", "eml", "rtf", "xlsx", "pptx", "html"):
            self.assertIn(f'"{art}"', abschnitt, art)


if __name__ == "__main__":
    unittest.main()


class UnterordnerWerdenMitgelesen(unittest.TestCase):
    """Gemessen am 25.09.2026 in der Kanzlei, Akte mit 32 Einträgen:
    2 Unterordner, 29 Dateien, 1 Aktengedächtnis.

    Bis dahin las das Programm nur den Wurzelordner. Was in den Unterordnern
    lag, fehlte lautlos - und eine kurze Liste sieht aus wie eine kurze Akte.

    Die Beschreibung des Herstellers führt jeden Eintrag als "folder" oder
    "file"; ein Ordner nennt seine Nummer in folder.id und sagt mit canRead,
    ob er gelesen werden darf. Nichts davon ist geraten.
    """

    def _baum(self, baum, gefragt=None):
        """Ein Server mit Unterordnern. baum: {ordner_id: [eintraege]}."""
        def antworten(anfrage):
            if "folder/content" in anfrage.url.path:
                nummer = anfrage.url.params.get("folderId")
                if gefragt is not None:
                    gefragt.append(str(nummer))
                if "page=" in str(anfrage.url):
                    return httpx.Response(200, json={"elements": []})
                if str(nummer) not in baum:
                    return httpx.Response(404, json={})
                return httpx.Response(200, json={"elements": baum[str(nummer)]})
            if "/record" in anfrage.url.path and "search" not in anfrage.url.path:
                return httpx.Response(200, json={"identifier": "rec-1", "fileFolderId": 7})
            return httpx.Response(200, json={})

        return HttpJurNodesAdapter("https://beispiel.invalid", "k", Freigabestelle(),
                                   transport=httpx.MockTransport(antworten), benutzer="u")

    @staticmethod
    def _ordner(nummer, name="Schriftsätze", lesbar=True):
        return {"type": "folder",
                "folder": {"id": nummer, "folderName": name, "canRead": lesbar}}

    def test_was_im_unterordner_liegt_kommt_mit(self):
        a = self._baum({
            "7": [_datei("Klageschrift.pdf", "f-1"), self._ordner(11)],
            "11": [_datei("Anlage K1.pdf", "f-2"), _datei("Anlage K2.pdf", "f-3")],
        })
        self.assertEqual(3, len(a.dokumente("rec-1")))

    def test_auch_ueber_mehrere_stufen(self):
        a = self._baum({
            "7": [self._ordner(11)],
            "11": [self._ordner(12, "Korrespondenz")],
            "12": [_datei("Brief.pdf", "f-9")],
        })
        self.assertEqual(1, len(a.dokumente("rec-1")))

    def test_ein_ordner_ohne_leserecht_wird_uebersprungen(self):
        """Er gehört dann jemand anderem - kein Grund für einen Fehler."""
        gefragt = []
        a = self._baum({"7": [_datei("Klageschrift.pdf"),
                              self._ordner(11, "Fremd", lesbar=False)]},
                       gefragt)
        self.assertEqual(1, len(a.dokumente("rec-1")))
        self.assertNotIn("11", gefragt)

    def test_ein_unlesbarer_unterordner_kostet_nicht_die_ganze_liste(self):
        """Derselbe Fehler wie beim Gedächtnis: Ein Teilfehler riss das Ganze
        mit. Die übrigen Dokumente kommen trotzdem."""
        a = self._baum({"7": [_datei("Klageschrift.pdf"), self._ordner(99)]})
        self.assertEqual(1, len(a.dokumente("rec-1")))
        self.assertEqual(1, a.letzte_ordner_uebersprungen)

    def test_der_wurzelordner_dagegen_schon(self):
        """Ein still leerer Bestand wäre schlimmer als ein Fehler."""
        from jusperfect.jurnodes.base import JurNodesFehler

        a = self._baum({})          # auch die Wurzel fehlt
        with self.assertRaises(JurNodesFehler):
            a.dokumente("rec-1")

    def test_eine_schleife_bringt_das_programm_nicht_zum_stehen(self):
        """Ordner, die sich gegenseitig enthalten - jede Nummer nur einmal."""
        a = self._baum({
            "7": [self._ordner(11)],
            "11": [self._ordner(7), _datei("Brief.pdf", "f-1")],
        })
        self.assertEqual(1, len(a.dokumente("rec-1")))

    def test_die_tiefe_ist_begrenzt(self):
        """Der Hersteller lässt je IP eine Anfrage zugleich - ein versehentlich
        verschachtelter Bestand darf nicht in hunderte Anfragen laufen."""
        baum = {str(7 + i): [self._ordner(8 + i)] for i in range(20)}
        baum["27"] = [_datei("Tief.pdf", "f-1")]
        gefragt = []
        a = self._baum(baum, gefragt)
        a.dokumente("rec-1")
        self.assertLessEqual(len(set(gefragt)), a.ORDNER_TIEFE + 1)


class DerKorrespondenzordnerBleibtDraussen(unittest.TestCase):
    """Er war nie der richtige Weg – und das wussten wir am 05.10.2026 noch nicht.

    Am 02.10. fielen in einer Bausache drei Schriftstücke aus einer fremden
    Verkehrsunfallsache auf. Drei Läufe an drei Akten zeigten am 05.10.
    dasselbe Muster:

        X-100-2026  angelegt 30.07.2026  Ordner 2871, befüllt 2022/23
        X-103-2026  angelegt 23.02.2026  Ordner 2616, befüllt 2022/23
        X-104-2023  angelegt 28.12.2023  Ordner 1478, befüllt 2022/23

    Damals stand die Frage an den Hersteller offen, und der Ordner wurde
    abgeschaltet. **Die Beschreibung des Herstellers (API 1.0.2) hat sie dann
    beantwortet, und die Antwort war unangenehm: Es war unser eigener Fehler.**
    `correspondenceFolderId` gehört in den Ordnerbaum der **Korrespondenz** und
    wurde gegen den Baum des **Dateisystems** abgefragt. Zwei Nummernkreise,
    dieselbe Zahl, fremde Akte.

    Deshalb kommt dieser Weg nicht zurück – auch nicht mit der Einstellung.
    Die Korrespondenz hat einen eigenen, aktenbezogenen Weg; er steht in
    `DieEAkteWirdUeberIhrenEigenenWegGelesen`.

    **Fremde Schriftstücke in einer Arbeitsakte sind teurer als fehlende.**
    Was fehlt, fällt auf; was zu viel ist, wird mitanalysiert, zitiert und ins
    Aktengedächtnis geschrieben.
    """

    def _adapter(self, gefragt, korrespondenz=False):
        def antworten(anfrage):
            if "folder/content" in anfrage.url.path:
                nummer = str(anfrage.url.params.get("folderId"))
                gefragt.append(nummer)
                if "page=" in str(anfrage.url):
                    return httpx.Response(200, json={"elements": []})
                if nummer == "7":
                    return httpx.Response(200, json={
                        "elements": [_datei("Klageschrift.pdf", "f-1")]})
                return httpx.Response(200, json={
                    "elements": [_datei("Fremdes Schreiben.pdf", "k-1")]})
            if "correspondence/search" in anfrage.url.path:
                return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
            if "/record" in anfrage.url.path and "search" not in anfrage.url.path:
                return httpx.Response(200, json={
                    "identifier": "rec-1", "fileFolderId": 7,
                    "correspondenceFolderId": 9})
            return httpx.Response(200, json={})

        return HttpJurNodesAdapter("https://beispiel.invalid", "k", Freigabestelle(),
                                   transport=httpx.MockTransport(antworten), benutzer="u",
                                   korrespondenz=korrespondenz)

    def test_er_wird_von_sich_aus_nicht_gefragt(self):
        gefragt = []
        a = self._adapter(gefragt)
        a.dokumente("rec-1")
        self.assertIn("7", gefragt)
        self.assertNotIn("9", gefragt, "Der Korrespondenzordner wurde gelesen.")

    def test_und_sein_inhalt_steht_in_keiner_arbeitsakte(self):
        a = self._adapter([])
        namen = [d.dateiname for d in a.dokumente("rec-1")]
        self.assertEqual(["Klageschrift.pdf"], namen)

    def test_auch_mit_der_einstellung_bleibt_er_draussen(self):
        """Die Einstellung schaltet die **E-Akte** ein, nicht den Ordner.

        Hier stand bis zum 06.10.2026 das Gegenteil: „Der Weg zurück, falls
        der Hersteller Entwarnung gibt." Es gab keine Entwarnung zu geben –
        der Weg war von Anfang an der falsche.
        """
        gefragt = []
        a = self._adapter(gefragt, korrespondenz=True)
        namen = [d.dateiname for d in a.dokumente("rec-1")]
        self.assertNotIn("9", gefragt, "Der Korrespondenzordner wurde gelesen.")
        self.assertNotIn("Fremdes Schreiben.pdf", namen)

    def test_die_einstellung_steht_von_haus_aus_auf_aus(self):
        from jusperfect.config import Einstellungen

        self.assertFalse(Einstellungen.korrespondenz)

    def test_und_wird_aus_der_umgebung_gelesen(self):
        from jusperfect.config import Einstellungen

        for wert, erwartet in (("ein", True), ("an", True), ("ja", True),
                               ("aus", False), ("", False), ("nein", False)):
            with self.subTest(wert=wert):
                e = Einstellungen.aus_umgebung({
                    "JUSPERFECT_ANBIETER": "demo",
                    "JUSPERFECT_BETRIEBSART": "lokal",
                    "JUSPERFECT_JURNODES_ADAPTER": "fixture",
                    "JUSPERFECT_KORRESPONDENZ": wert,
                })
                self.assertEqual(erwartet, e.korrespondenz)

    def test_derselbe_ordner_wird_nicht_zweimal_gelesen(self):
        """Manche Akten nennen für beides dieselbe Nummer."""
        gefragt = []

        def antworten(anfrage):
            if "folder/content" in anfrage.url.path:
                gefragt.append(str(anfrage.url.params.get("folderId")))
                if "page=" in str(anfrage.url):
                    return httpx.Response(200, json={"elements": []})
                return httpx.Response(200, json={
                    "elements": [_datei("Klageschrift.pdf", "f-1")]})
            if "/record" in anfrage.url.path:
                return httpx.Response(200, json={
                    "identifier": "rec-1", "fileFolderId": 7,
                    "correspondenceFolderId": 7})
            return httpx.Response(200, json={})

        a = HttpJurNodesAdapter("https://beispiel.invalid", "k", Freigabestelle(),
                                transport=httpx.MockTransport(antworten), benutzer="u")
        self.assertEqual(1, len(a.dokumente("rec-1")))
