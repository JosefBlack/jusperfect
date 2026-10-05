"""Der Weg zu jur|nodes über die REST-Schnittstelle – am nachgestellten Server.

**Bis zum 23.09.2026 prüfte diese Datei etwas Erfundenes.** Die Pfade und
Feldnamen im Adapter waren eine plausible Annahme, weil der Hersteller die
Dokumentation nur auf dem Kundenserver bereitstellt; die Tests bildeten
folgerichtig diese Annahme ab und bestanden. Ein Test, der die eigene Vermutung
bestätigt, sagt nichts.

An diesem Tag hat die Kanzlei die OpenAPI-Beschreibung ihres Servers geliefert
(jur|nodes API 1.0.1) und die Schnittstelle freischalten lassen. Der
nachgestellte Server hier antwortet seither so, wie es dort beschrieben ist:
``/record/search``, ``/record``, ``/file-system/folder/content``,
``/file-system/file/download``, ``/relation/search``, ``/todo/search``,
``/record/note`` – mit den echten Feldnamen.

Vier Dinge sahen anders aus, als geraten worden war, und jedes einzelne hätte
den ersten Versuch scheitern lassen:

1. Die Anmeldung geht über **zwei** Kopfzeilen (``X-Auth-User``/``X-Auth-Key``),
   nicht über ein Bearer-Token.
2. Die Akte wird über einen Abfrageparameter ``identifier`` angesprochen, nicht
   über einen Pfadbestandteil – und der Identifier ist nicht das Aktenzeichen.
3. Die Dokumente hängen am **Dateiordner** der Akte (``fileFolderId``), nicht
   an der Akte.
4. Der Vermerk will einen Umschlag ``model`` und heißt ``subject``/``content``.
"""

import json
import unittest

import httpx

from jusperfect.config import KonfigurationsFehler
from jusperfect.jurnodes.base import AkteNichtGefunden, JurNodesFehler
from jusperfect.jurnodes.http_adapter import Endpunkte, HttpJurNodesAdapter, _status_uebersetzen
from jusperfect.security.approval import Freigabestelle

#: So antwortet der Server der Kanzlei – abgeschrieben aus seiner Beschreibung.
AKTE = {
    "identifier": "rec-4711",
    "recordSign": "d-001-2026",
    "shortRubrum": "Testmann ./. Musterhaft",
    "recordStatus": "laufend",
    "lawCategory": 1,
    "fileFolderId": 900,
}


class DerEchteServer(unittest.TestCase):
    def setUp(self):
        self.anfragen: list[httpx.Request] = []
        self.gleichzeitig = 0
        self.hoechststand = 0
        self.stelle = Freigabestelle()

        def antwort(request: httpx.Request) -> httpx.Response:
            self.anfragen.append(request)
            self.gleichzeitig += 1
            self.hoechststand = max(self.hoechststand, self.gleichzeitig)
            try:
                return self._antworten(request)
            finally:
                self.gleichzeitig -= 1

        self.a = HttpJurNodesAdapter(
            "https://dortschy-thunert.jur-nodes.example/api/extern/v1/kennung",
            "schluessel", self.stelle, benutzer="kanzlei",
            transport=httpx.MockTransport(antwort))

    def _antworten(self, request: httpx.Request) -> httpx.Response:
        pfad = request.url.path
        p = request.url.params
        if pfad.endswith("/record/search"):
            # Die Suche geht je Feld, und "%" ist der Platzhalter - so
            # beschreibt es der Hersteller, und so verhaelt sich der Server
            # der Kanzlei.
            def passt(wert: str, feld: str) -> bool:
                kern = wert.strip("%")
                return not kern or kern.lower() in AKTE[feld].lower()

            treffer = []
            if p.get("sign") and passt(p["sign"], "recordSign"):
                treffer = [AKTE]
            if p.get("shortRubrum") and passt(p["shortRubrum"], "shortRubrum"):
                treffer = [AKTE]
            return httpx.Response(200, json={"amountTotal": str(len(treffer)),
                                             "pagesTotal": "1", "elements": treffer})
        if pfad.endswith("/record"):
            if p.get("identifier") == AKTE["identifier"]:
                return httpx.Response(200, json=AKTE)
            if p.get("identifier") == "rec-weg":
                return httpx.Response(404)
            if p.get("identifier") == "rec-kaputt":
                return httpx.Response(500, text="Interner Fehler, Akte Testmann ./. Musterhaft")
            return httpx.Response(404)
        if pfad.endswith("/file-system/folder/content"):
            if p.get("folderId") != "900":
                return httpx.Response(404)
            return httpx.Response(200, json={"amountTotal": "2", "pagesTotal": "1", "elements": [
                {"type": "folder", "folder": {"id": 901, "folderName": "Anlagen"}},
                {"type": "file", "file": {"identifier": "file-1", "fileName": "Klageschrift",
                                          "fileExtension": "pdf", "addedDate": "2026-03-01T10:00:00Z",
                                          "size": 12345}},
            ]})
        if pfad.endswith("/file-system/file/download"):
            if p.get("identifier") != "file-1":
                return httpx.Response(404)
            return httpx.Response(200, content=b"%PDF-1.4 test")
        if pfad.endswith("/relation/search"):
            if p.get("recordIdentifier") != AKTE["identifier"]:
                return httpx.Response(200, json={"elements": []})
            return httpx.Response(200, json={"elements": [
                {"id": "B1", "name": "T. Testmann", "rolle": "Mandant"}]})
        if pfad.endswith("/todo/search"):
            if p.get("recordIdentifier") != AKTE["identifier"]:
                return httpx.Response(200, json={"elements": []})
            return httpx.Response(200, json={"elements": [
                {"id": "F1", "bezeichnung": "Berufungsfrist", "datum": "2026-04-30"}]})
        if pfad.endswith("/record/note") and request.method == "POST":
            return httpx.Response(201, json={"id": 77})
        return httpx.Response(403)

    # ── Anmeldung ──────────────────────────────────────────────────────────

    def test_die_anmeldung_geht_ueber_zwei_kopfzeilen(self):
        """Hier stand „Authorization: Bearer" – die naheliegende Annahme, und
        die falsche. Ein abgelehnter Zugang sieht aus wie ein falscher
        Schlüssel; gesucht hätte man beim Hersteller statt im Quelltext."""
        self.a.akten_suchen("")
        k = self.anfragen[0].headers
        self.assertEqual(k["X-Auth-User"], "kanzlei")
        self.assertEqual(k["X-Auth-Key"], "schluessel")
        self.assertNotIn("authorization", {n.lower() for n in k})

    # ── Suchen und Lesen ───────────────────────────────────────────────────

    def test_die_akte_traegt_kurzrubrum_und_status(self):
        """Der sichtbarste Gewinn gegenüber dem Laufwerk: Dort steht im
        Ordnernamen nur das Aktenzeichen, das Kurzrubrum gibt es nicht."""
        akte = self.a.akte("rec-4711")
        self.assertEqual(akte.id, "rec-4711")
        self.assertEqual(akte.aktenzeichen, "d-001-2026")
        self.assertEqual(akte.bezeichnung, "Testmann ./. Musterhaft")
        self.assertEqual(akte.status, "laufend")

    def test_gesucht_wird_nach_aktenzeichen_und_nach_namen(self):
        """Über das Laufwerk findet „Testmann" nichts – der Name steht dort
        nirgends. Deshalb fragt der Adapter beide Felder."""
        nach_zeichen = self.a.akten_suchen("d-001")
        nach_namen = self.a.akten_suchen("Testmann")
        self.assertEqual([a.id for a in nach_zeichen], ["rec-4711"])
        self.assertEqual([a.id for a in nach_namen], ["rec-4711"])
        felder = {n for r in self.anfragen for n in r.url.params}
        self.assertIn("sign", felder)
        self.assertIn("shortRubrum", felder)

    def test_dieselbe_akte_kommt_nur_einmal(self):
        """Zwei Anfragen, ein Treffer – sonst stünde sie doppelt in der Liste."""
        self.assertEqual(1, len(self.a.akten_suchen("Testmann")))

    def test_ein_archivierter_status_wird_uebersetzt(self):
        """Am Laufwerk war der Status nicht zu haben; hier steht er am Satz."""
        from jusperfect.jurnodes.http_adapter import akte_aus_json
        self.assertEqual("archiviert", akte_aus_json({"recordStatus": "archiviert"}).status)
        self.assertEqual("laufend", akte_aus_json({"recordStatus": "active"}).status)
        # Kein Status heisst "unbekannt", nicht "laufend": Dann entscheidet ein
        # Mensch, und es wird nichts geloescht.
        self.assertEqual("unbekannt", akte_aus_json({"recordStatus": ""}).status)

    def test_die_dokumente_haengen_am_dateiordner(self):
        """Nicht an der Akte – die nennt nur eine fileFolderId."""
        dokumente = self.a.dokumente("rec-4711")
        self.assertEqual(1, len(dokumente), "Der Unterordner darf nicht als Dokument zählen.")
        d = dokumente[0]
        self.assertEqual((d.id, d.dateiname, str(d.datum)),
                         ("file-1", "Klageschrift.pdf", "2026-03-01"))
        self.assertEqual(d.groesse_bytes, 12345)

    def test_name_und_endung_werden_zusammengesetzt(self):
        """jur|nodes führt sie getrennt. Am Dateinamen hängt die Erkennung,
        was sich auslesen lässt und was nicht."""
        from jusperfect.jurnodes.http_adapter import dokument_aus_json
        d = dokument_aus_json("A", {"identifier": "x", "fileName": "Brief", "fileExtension": "docx"})
        self.assertEqual("Brief.docx", d.dateiname)

    def test_eine_datei_wird_ueber_ihre_eigene_kennung_geladen(self):
        _, daten = self.a.dokument_laden("rec-4711", "file-1")
        self.assertEqual(b"%PDF", daten[:4])

    def test_beteiligte_und_fristen_werden_auf_die_akte_beschraenkt(self):
        """Ohne recordIdentifier lieferte die Suche ALLE Beziehungen der
        Kanzlei statt der einen Akte."""
        self.assertEqual("Mandant", self.a.beteiligte("rec-4711")[0].rolle)
        self.assertEqual("2026-04-30", str(self.a.fristen("rec-4711")[0].datum))
        for anfrage in self.anfragen:
            if anfrage.url.path.endswith(("/relation/search", "/todo/search")):
                self.assertEqual("rec-4711", anfrage.url.params["recordIdentifier"])

    def test_fristen_werden_von_aufgaben_getrennt(self):
        self.a.fristen("rec-4711")
        letzte = [r for r in self.anfragen if r.url.path.endswith("/todo/search")][-1]
        self.assertEqual("frist", letzte.url.params["type"])

    # ── Schreiben ──────────────────────────────────────────────────────────

    def test_der_vermerk_hat_den_aufbau_des_herstellers(self):
        f = self.stelle.erteilen("e1", "rec-4711", "ra", "Text")
        self.assertEqual("77", self.a.vermerk_schreiben("rec-4711", "Betreff", "Text", f))
        koerper = json.loads(self.anfragen[-1].content)
        self.assertIn("model", koerper, "Ohne den Umschlag weist jur|nodes ab.")
        m = koerper["model"]
        self.assertEqual((m["record"], m["subject"], m["content"]), ("rec-4711", "Betreff", "Text"))
        self.assertIsNone(m["id"], "NULL heisst neu anlegen.")
        self.assertEqual("text", m["contentType"])
        self.assertFalse(koerper["onlyValidate"])

    def test_ohne_freigabe_wird_nicht_geschrieben(self):
        with self.assertRaises(Exception):
            self.a.vermerk_schreiben("rec-4711", "T", "Text", None)
        self.assertFalse([r for r in self.anfragen if r.method == "POST"])

    # ── Die Vorgabe des Herstellers: eine Anfrage zugleich ─────────────────

    def test_es_laeuft_immer_nur_eine_anfrage(self):
        """Auskunft des Herstellers vom 23.09.2026: „pro IP-Adresse nur ein
        Request zeitgleich zulässig." Ein Einlesen von fünfzig Dokumenten sind
        fünfzig Anfragen; ohne diese Sperre fiele die Anbindung unter Last
        auseinander, und zwar nicht beim Ausprobieren, sondern im Betrieb.
        """
        import threading

        fehler: list[BaseException] = []

        def arbeiten():
            try:
                for _ in range(5):
                    self.a.akten_suchen("d-001")
            except BaseException as e:  # pragma: no cover - nur im Fehlerfall
                fehler.append(e)

        faeden = [threading.Thread(target=arbeiten) for _ in range(4)]
        for f in faeden:
            f.start()
        for f in faeden:
            f.join()
        self.assertEqual([], fehler)
        self.assertEqual(1, self.hoechststand,
                         "Es liefen mehrere Anfragen zugleich – das lehnt jur|nodes ab.")

    # ── Fehler ─────────────────────────────────────────────────────────────

    def test_eine_fehlende_akte_ist_kein_serverfehler(self):
        with self.assertRaises(AkteNichtGefunden):
            self.a.akte("rec-weg")

    def test_kein_akteninhalt_in_der_fehlermeldung(self):
        """Der Antworttext eines Servers kann Mandantendaten enthalten. Er
        darf weder ins Protokoll noch an die Oberfläche."""
        with self.assertRaises(JurNodesFehler) as cm:
            self.a.akte("rec-kaputt")
        self.assertNotIn("Testmann", str(cm.exception))

    def test_nur_https(self):
        with self.assertRaises(KonfigurationsFehler):
            HttpJurNodesAdapter("http://jurnodes.example", "s", self.stelle)
        with self.assertRaises(KonfigurationsFehler):
            HttpJurNodesAdapter("https://jurnodes.example", "", self.stelle)


class DiePfadeBleibenEinstellbar(unittest.TestCase):
    """Eine Beschreibung ist kein laufender Server.

    Die Vorgaben stammen jetzt aus der Dokumentation des Herstellers und sind
    keine Vermutung mehr. Gehen Beschreibung und Server trotzdem auseinander,
    gilt der Server – und dann soll das eine Zeile in einer Textdatei sein und
    kein neuer Programmstand.
    """

    def test_ein_abweichender_pfad_laesst_sich_eintragen(self):
        gesehen: list[str] = []

        def antwort(request: httpx.Request) -> httpx.Response:
            gesehen.append(request.url.path)
            return httpx.Response(200, json={"elements": []})

        a = HttpJurNodesAdapter("https://jurnodes.example/api", "s", Freigabestelle(),
                                endpunkte=Endpunkte(akten_suche="/v2/akten/suche"),
                                transport=httpx.MockTransport(antwort))
        a.akten_suchen("")
        self.assertEqual(["/api/v2/akten/suche"], gesehen)


if __name__ == "__main__":
    unittest.main()


class EinSchluesselJeBereich(unittest.TestCase):
    """Aus der Kanzlei, 23.09.2026: „Es ist für jeden Zugang ein Schlüssel mit
    Unterteilung z.B. bei Akten mit read search write."

    jur|nodes vergibt die Zugänge also nicht als **einen** Schlüssel mit
    mehreren Haken, sondern je Bereich einen eigenen. Für jusperfect heißt das:
    Der Schlüssel hängt an der Frage, nicht an der Verbindung. Eine Anfrage
    nach den Dokumenten braucht den Schlüssel des Dateisystems, eine nach der
    Akte den der Akten.

    Ohne diese Zuordnung bekäme man bei allen Bereichen außer einem eine
    Ablehnung — und die sieht aus wie ein falscher Schlüssel, nicht wie ein
    fehlender. Gesucht hätte man beim Hersteller.
    """

    def setUp(self):
        self.gesehen: list[tuple[str, str]] = []

        def antwort(request: httpx.Request) -> httpx.Response:
            self.gesehen.append((request.url.path, request.headers.get("X-Auth-Key", "")))
            if request.url.path.endswith("/record"):
                return httpx.Response(200, json=AKTE)
            return httpx.Response(200, json={"elements": []})

        self.transport = httpx.MockTransport(antwort)

    def _adapter(self, **kw):
        return HttpJurNodesAdapter("https://jurnodes.example/api", "allgemein",
                                   Freigabestelle(), transport=self.transport, **kw)

    def test_jede_frage_bekommt_den_schluessel_ihres_bereichs(self):
        a = self._adapter(schluessel={"akten": "k-akten", "dateisystem": "k-dateien",
                                      "beziehungen": "k-bez", "todo": "k-todo"})
        a.akten_suchen("")
        a.dokumente("rec-4711")
        a.beteiligte("rec-4711")
        a.fristen("rec-4711")
        nach_pfad = dict(self.gesehen)
        self.assertEqual("k-akten", nach_pfad["/api/record/search"])
        self.assertEqual("k-akten", nach_pfad["/api/record"])
        self.assertEqual("k-dateien", nach_pfad["/api/file-system/folder/content"])
        self.assertEqual("k-bez", nach_pfad["/api/relation/search"])
        self.assertEqual("k-todo", nach_pfad["/api/todo/search"])

    def test_wer_nur_einen_schluessel_hat_kommt_damit_aus(self):
        """Der erste Schritt der Kanzlei ist genau das: ein Zugang für die
        Akten, sonst nichts."""
        a = self._adapter()
        a.akten_suchen("")
        self.assertEqual([("/api/record/search", "allgemein")], self.gesehen)

    def test_ein_fehlender_bereich_faellt_auf_den_allgemeinen_zurueck(self):
        a = self._adapter(schluessel={"akten": "k-akten"})
        a.dokumente("rec-4711")
        self.assertEqual("allgemein", dict(self.gesehen)["/api/file-system/folder/content"])

    def test_der_vermerk_geht_mit_dem_aktenschluessel(self):
        """Er ist ein Vermerk AN der Akte, kein eigener Bereich."""
        from jusperfect.jurnodes.http_adapter import bereich_von
        self.assertEqual("akten", bereich_von("/record/note"))

    def test_die_zuordnung_kennt_jeden_pfad_den_der_adapter_benutzt(self):
        """Ein Pfad ohne Bereich bekäme still den allgemeinen Schlüssel."""
        from jusperfect.jurnodes.http_adapter import bereich_von
        e = Endpunkte()
        for pfad in (e.akten_suche, e.akte, e.ordner_inhalt, e.datei_download,
                     e.beteiligte, e.fristen, e.vermerke, e.datei_hinzufuegen):
            with self.subTest(pfad=pfad):
                self.assertTrue(bereich_von(pfad), f"{pfad} gehört zu keinem Bereich.")


class AlleSeiten(unittest.TestCase):
    """Die Schnittstelle gibt höchstens 50 oder 100 Einträge je Seite zurück.

    Der erste echte Lauf am 23.09.2026 traf das nicht: Die Beispielakte hatte
    8 Beteiligte und 0 Fristen. Eine Akte mit 120 Dokumenten hätte 100 davon
    geliefert, und die übrigen 20 hätten lautlos gefehlt.

    Genau diese Art von Fehler ist in diesem Programm an einem Tag schon
    zweimal aufgetreten – beim doppelt vergebenen Aktenzeichen und bei den
    Dokumenten, die das schwache Modell beim Einlesen wegließ. Beide Male galt
    dasselbe: **Was nicht da ist, fällt nicht auf.**

    Die zweite Falle steckt im Anfang der Zählung, und sie hat zugeschlagen.
    Die Beschreibung des Herstellers sagt, `/record/search` und `/todo/search`
    begännen bei 0. Sein Server sagt am 28.09.2026 das Gegenteil, in ganzen
    Worten: `page=0` wird mit 405 abgewiesen – *Bitte geben Sie eine Seitenzahl
    > 0 an*.

    Damit war die 0 ein stiller Verlust: Die erste Anfrage geht ohne
    Seitenangabe hinaus und bringt Seite 1; die Schleife zählte von 0 auf 1 und
    holte **Seite 1 noch einmal**. Seite 2 kam nie, und die Doppelung wurde als
    zweite Seite gezählt – der Adapter hielt die Akte für vollständig.

    Und dieser Prüfserver hat es mitgemacht: Er nahm `page=0` an und lieferte
    darauf die erste Seite. Solange er das tat, war der Fehler grün. Er weist
    die 0 jetzt ab, wie der echte Server.

    **Im Zweifel gilt der Server, nicht seine Beschreibung.**
    """

    def _adapter(self, seiten: dict[int, list], pfad_teil: str, erste: int = 1):
        """Ein Pruefserver, der sich verhaelt wie der Server der Kanzlei.

        Er tat es nicht: Er nahm ``page=0`` an und lieferte darauf die erste
        Seite. Der echte Server weist 0 ab - **Bitte geben Sie eine Seitenzahl
        > 0 an** (gemessen am 28.09.2026). Solange der Pruefserver das
        mitmachte, war ein stiller Verlust im Adapter gruen.

        Dieselbe Form wie am 23./24.09.2026 fuenfmal: Eine Probe, die anders
        fragt oder anders antwortet als der Betrieb, prueft etwas anderes.
        """
        self.gefragt: list[int] = []

        def antwort(request: httpx.Request) -> httpx.Response:
            if pfad_teil not in request.url.path:
                return httpx.Response(200, json=AKTE)
            angabe = request.url.params.get("page")
            if angabe == "0":
                return httpx.Response(405, json={
                    "message": "Bitte geben Sie eine Seitenzahl > 0 an"})
            # Ohne Seitenangabe liefert der Server die erste Seite.
            nummer = int(angabe) if angabe is not None else 1
            self.gefragt.append(nummer)
            return httpx.Response(200, json={
                "amountTotal": sum(len(v) for v in seiten.values()),
                "pagesTotal": len(seiten),
                "actuallyPage": nummer,
                "elements": seiten.get(nummer, []),
            })

        return HttpJurNodesAdapter("https://jurnodes.example/api", "s", Freigabestelle(),
                                   transport=httpx.MockTransport(antwort))

    def test_die_zaehlung_faengt_ueberall_bei_eins_an(self):
        """Hier stand eine 0 fuer /record/search und /todo/search.

        So sagt es die Beschreibung des Herstellers. Sein Server sagt am
        28.09.2026 etwas anderes, und zwar in ganzen Worten: ``page=0`` wird
        mit 405 abgewiesen - **Bitte geben Sie eine Seitenzahl > 0 an**. Ist 0
        keine gueltige Seite, dann ist 1 die erste.

        Die 0 war ein stiller Verlust: Die erste Anfrage geht ohne Seitenangabe
        hinaus und bringt Seite 1; die Schleife zaehlte von 0 auf 1 und holte
        Seite 1 noch einmal. Seite 2 kam nie, und die Doppelung wurde als
        zweite Seite gezaehlt - der Adapter hielt die Akte fuer vollstaendig.
        """
        from jusperfect.jurnodes.http_adapter import erste_seite
        for pfad in ("/record/search", "/todo/search", "/relation/search",
                     "/file-system/folder/content"):
            with self.subTest(pfad=pfad):
                self.assertEqual(1, erste_seite(pfad))

    def test_akten_werden_ueber_alle_seiten_gesammelt(self):
        seiten = {1: [{"identifier": f"a{i}", "recordSign": f"{i}"} for i in range(50)],
                  2: [{"identifier": "a50", "recordSign": "50"}]}
        a = self._adapter(seiten, "/record/search")
        self.assertEqual(51, len(a.akten_suchen("")))
        self.assertEqual([1, 2], self.gefragt,
                         "Die erste Anfrage ohne Seitenangabe bringt Seite 1 - "
                         "die zweite muss page=2 sein, nicht wieder 1.")

    def test_dokumente_werden_ueber_alle_seiten_gesammelt(self):
        seiten = {1: [{"type": "file", "file": {"identifier": f"f{i}", "fileName": str(i)}}
                      for i in range(100)],
                  2: [{"type": "file", "file": {"identifier": "f100", "fileName": "100"}}]}
        a = self._adapter(seiten, "/file-system/folder/content")
        self.assertEqual(101, len(a.dokumente("rec-4711")))
        self.assertEqual([1, 2], self.gefragt, "Der Dateiordner zählt ab 1.")

    def test_beteiligte_werden_ueber_alle_seiten_gesammelt(self):
        seiten = {1: [{"id": f"b{i}", "name": str(i)} for i in range(100)],
                  2: [{"id": "b100", "name": "100"}]}
        a = self._adapter(seiten, "/relation/search")
        self.assertEqual(101, len(a.beteiligte("rec-4711")))

    def test_eine_einzige_seite_erzeugt_keine_zweite_anfrage(self):
        a = self._adapter({1: [{"identifier": "a1", "recordSign": "1"}]}, "/record/search")
        a.akten_suchen("")
        self.assertEqual([1], self.gefragt, "Eine überflüssige Anfrage kostet Zeit.")

    def test_ein_server_ohne_seitenangabe_bringt_das_lesen_nicht_zum_stehen(self):
        """Ohne pagesTotal wird geholt, bis nichts mehr kommt – und die Grenze
        fängt eine Antwort, die nie endet.

        Gezählt wird ab 1: Die erste Anfrage geht ohne Seitenangabe hinaus.
        """
        gefragt: list[int] = []

        def antwort(request: httpx.Request) -> httpx.Response:
            angabe = request.url.params.get("page")
            nummer = int(angabe) if angabe is not None else 1
            gefragt.append(nummer)
            inhalt = ([{"identifier": f"a{nummer}", "recordSign": str(nummer)}]
                      if nummer <= 3 else [])
            return httpx.Response(200, json={"elements": inhalt})

        a = HttpJurNodesAdapter("https://jurnodes.example/api", "s", Freigabestelle(),
                                transport=httpx.MockTransport(antwort))
        self.assertEqual(3, len(a.akten_suchen("")))
        self.assertEqual([1, 2, 3, 4], gefragt)


class DerBenutzerKommtBeimAdapterAn(unittest.TestCase):
    """jur|nodes verlangt **zwei** Angaben: Benutzer und Schlüssel.

    Die Anwendung holte bis zum 23.09.2026 nur das Token – ein Rest der
    früheren Annahme, die Anmeldung laufe über ein Bearer-Token. Der erste
    echte Lauf wäre daran gescheitert, und zwar mit einer Ablehnung, die
    aussieht wie ein falscher Schlüssel. Gesucht hätte man beim Hersteller.
    """

    def test_die_anwendung_holt_beide_werte(self):
        import inspect

        from jusperfect import web
        quelle = inspect.getsource(web._adapter_bauen)
        self.assertIn("jurnodes_benutzer", quelle)
        self.assertIn("jurnodes_token", quelle)

    def test_ein_fehlender_benutzer_sagt_wo_er_einzutragen_ist(self):
        from jusperfect.config import Einstellungen, KonfigurationsFehler
        from jusperfect.security.geheimnisse import jurnodes_benutzer

        e = Einstellungen.aus_umgebung({})
        with self.assertRaises(KonfigurationsFehler) as cm:
            jurnodes_benutzer(e, env={})
        self.assertIn("JURNODES-ZUGANG.bat", str(cm.exception))

    def test_eigene_schluessel_je_bereich_werden_gefunden(self):
        from jusperfect.security.geheimnisse import jurnodes_schluessel

        gefunden = jurnodes_schluessel(env={
            "JURNODES_API_KEY_AKTEN": "k1",
            "JURNODES_API_KEY_DATEISYSTEM": "k2",
            "JURNODES_API_KEY_UNSINN": "k3",
        })
        self.assertEqual({"akten": "k1", "dateisystem": "k2"}, gefunden)

    def test_ohne_eigene_schluessel_bleibt_es_bei_dem_einen(self):
        from jusperfect.security.geheimnisse import jurnodes_schluessel
        self.assertEqual({}, jurnodes_schluessel(env={}))


class DerSuchbegriffBrauchtPlatzhalter(unittest.TestCase):
    """Aus der Kanzlei, 23.09.2026, beim ersten Start über die Schnittstelle:

        File "...\\jurnodes\\http_adapter.py", line 339, in _get
          raise JurNodesFehler(f"jur|nodes antwortete mit Status ...")

    Die Aktenliste fragt beim Öffnen **ohne** Suchbegriff — und genau dieser
    eine Weg war nie ausprobiert worden. Der Prüflauf davor hatte immer ein
    Aktenzeichen mitgegeben, und damit ging es.

    Der Hersteller schreibt zu `sign` und `shortRubrum` dasselbe: „%-Zeichen
    für Suchbefehl verwenden". Ein bloßes `%` ist damit die Frage nach allem.

    Das Zweite fällt erst im Gebrauch auf: Ein Begriff ohne Platzhalter trifft
    nur genau. Die Kanzlei sucht aber „Testmann" und meint „Testmann ./. Musterhaft".
    """

    def setUp(self):
        self.gesehen: list[dict] = []

        def antwort(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/record/search"):
                self.gesehen.append(dict(request.url.params))
                # Ein Server, der eine Suche ohne Kriterium abweist - so wie
                # der der Kanzlei.
                if not request.url.params.get("sign") and not request.url.params.get("shortRubrum"):
                    return httpx.Response(400, json={"message": "kein Suchkriterium"})
                return httpx.Response(200, json={"pagesTotal": 1, "elements": [AKTE]})
            return httpx.Response(200, json=AKTE)

        self.a = HttpJurNodesAdapter("https://jurnodes.example/api", "s", Freigabestelle(),
                                     transport=httpx.MockTransport(antwort))

    def test_die_leere_suche_fragt_nach_allem(self):
        """Sonst läuft die Aktenliste beim Öffnen in einen Fehler."""
        self.assertEqual(1, len(self.a.akten_suchen("")))
        self.assertEqual("%", self.gesehen[0]["sign"])

    def test_ein_name_wird_in_platzhalter_gefasst(self):
        self.a.akten_suchen("Testmann")
        self.assertEqual("%Testmann%", self.gesehen[0]["sign"])
        self.assertEqual("%Testmann%", self.gesehen[1]["shortRubrum"])

    def test_eigene_platzhalter_bleiben_unangetastet(self):
        """Wer selbst welche setzt, weiß was er tut."""
        self.a.akten_suchen("D-057-%")
        self.assertEqual("D-057-%", self.gesehen[0]["sign"])

    def test_leerzeichen_am_rand_stoeren_nicht(self):
        from jusperfect.jurnodes.http_adapter import HttpJurNodesAdapter as A
        self.assertEqual("%", A._platzhalter("   "))
        self.assertEqual("%Testmann%", A._platzhalter("  Testmann  "))


class DieErsteAnfrageGehtOhneSeitenangabe(unittest.TestCase):
    """Aus der Kanzlei, 23.09.2026: „aktenzeichen eingegeben - Keine Akte
    gefunden oder keine Berechtigung."

    Die Probe am selben Tag hatte dieselbe Akte gefunden. Der Unterschied
    zwischen beiden Aufrufen war die Seitenangabe: Die Probe fragte **ohne**,
    die Aktenliste mit `page=0`. Der Hersteller schreibt, die erste Seite sei
    0 — sein Server sieht das offenbar anders.

    Im Zweifel gilt der Server, nicht seine Beschreibung. Die erste Anfrage
    geht deshalb in der Form hinaus, die nachweislich funktioniert hat; ab der
    zweiten Seite wird gezählt, und dort kann die Angabe des Herstellers
    stimmen.
    """

    def setUp(self):
        self.gesehen: list[dict] = []

        def antwort(request: httpx.Request) -> httpx.Response:
            self.gesehen.append(dict(request.url.params))
            seite = request.url.params.get("page")
            # Der Server der Kanzlei weist 0 ab und liefert auf 1 die ERSTE
            # Seite - nicht die zweite. Genau daran ging Seite 2 verloren.
            if seite == "0":
                return httpx.Response(405, json={
                    "message": "Bitte geben Sie eine Seitenzahl > 0 an"})
            if seite is None or seite == "1":
                return httpx.Response(200, json={"pagesTotal": 2, "elements": [AKTE]})
            if seite == "2":
                return httpx.Response(200, json={"pagesTotal": 2, "elements": [
                    {"identifier": "rec-2", "recordSign": "d-002-2026"}]})
            return httpx.Response(200, json={"pagesTotal": 2, "elements": []})

        self.a = HttpJurNodesAdapter("https://jurnodes.example/api", "s", Freigabestelle(),
                                     transport=httpx.MockTransport(antwort))

    def test_die_erste_anfrage_traegt_kein_page(self):
        self.a.akten_suchen("d-001")
        self.assertNotIn("page", self.gesehen[0],
                         "Genau diese Form hat am Server der Kanzlei funktioniert.")

    def test_die_zweite_seite_ist_page_2_und_nicht_wieder_1(self):
        """Der stille Verlust vom 28.09.2026.

        Die erste Anfrage geht ohne Seitenangabe hinaus und bringt Seite 1.
        Zaehlte die Schleife dann von 0 auf 1, holte sie Seite 1 noch einmal -
        und zaehlte die Doppelung als zweite Seite. Seite 2 kam nie, und der
        Adapter hielt die Akte fuer vollstaendig.
        """
        akten = self.a.akten_suchen("d-001")
        seiten = [g.get("page") for g in self.gesehen]
        self.assertIn("2", seiten, f"Seite 2 wurde nie geholt: {seiten}")
        self.assertEqual(2, len({a.id for a in akten}),
                         "Beide Seiten muessen im Ergebnis stehen.")

    def test_page_null_geht_nie_hinaus(self):
        """Der Server weist sie ab - und die Akte waere leer zurueckgekommen."""
        self.a.akten_suchen("d-001")
        self.assertNotIn("0", [g.get("page") for g in self.gesehen])


class EineMeldungNenntDenAufruf(unittest.TestCase):
    """Aus der Kanzlei, 24.09.2026: „Leider gibt es eine Fehlermeldung 405
    Aktengedächtnis wurde nicht gefunden."

    „Status 405" allein sagt nicht, **welcher** Aufruf abgewiesen wurde — und in
    einer Sitzung laufen ein halbes Dutzend: Akte laden, Ordnerinhalt,
    Datei herunterladen, Datei ablegen. Die Suche begann deshalb wieder bei
    einer Vermutung.

    Ein Pfad ist im Programm fest verdrahtet und enthält keinen Akteninhalt. Er
    gehört in die Meldung.
    """

    def _adapter(self, status: int, nur_pfad: str = ""):
        def antwort(request: httpx.Request) -> httpx.Response:
            if nur_pfad and nur_pfad not in request.url.path:
                if request.url.path.endswith("/record"):
                    return httpx.Response(200, json={"identifier": "rec-1", "fileFolderId": 7})
                return httpx.Response(200, json={"elements": []})
            return httpx.Response(status, json={"message": "nein"})

        return HttpJurNodesAdapter("https://jurnodes.example/api", "s", Freigabestelle(),
                                   transport=httpx.MockTransport(antwort))

    def test_der_pfad_steht_in_der_meldung(self):
        from jusperfect.jurnodes.base import JurNodesFehler

        a = self._adapter(500)
        with self.assertRaises(JurNodesFehler) as fehler:
            a.akten_suchen("x")
        self.assertIn("/record/search", str(fehler.exception))
        self.assertIn("500", str(fehler.exception))

    def test_bei_405_beim_ablegen_steht_da_was_zu_tun_ist(self):
        """405 heisst bei diesem Hersteller "ungueltige Eingabe".

        Nicht "den Pfad gibt es nicht fuer diese Methode" - so stand es hier
        bis zum 25.09.2026, und so steht es in der Norm. Die Beschreibung von
        jur|nodes fuehrt den Code 94mal, jedesmal als "Ungueltige Eingabe".
        Zwei Tage Suche nach dem Pfad gingen darauf, und der Pfad war richtig.
        """
        from jusperfect.jurnodes.base import JurNodesFehler

        a = self._adapter(405, nur_pfad="/file-system/add-file")
        with self.assertRaises(JurNodesFehler) as fehler:
            a.gedaechtnis_ablegen("rec-1", b"x")
        satz = str(fehler.exception)
        self.assertIn("405", satz)
        self.assertIn("/file-system/add-file", satz)
        self.assertIn("JUSPERFECT_JURNODES_ENDPUNKTE", satz)
        # Die richtige Deutung steht vor der alten - wer nur den Anfang
        # liest, sucht sonst wieder den Pfad.
        self.assertIn("ungültige Eingabe", satz)
        self.assertLess(satz.index("ungültige Eingabe"),
                        satz.index("JUSPERFECT_JURNODES_ENDPUNKTE"))

    def test_bei_401_wird_der_fehlende_bereich_benannt(self):
        """„Abgelehnt" schickt zum Hersteller. Der Bereichsname schickt in die
        Rechteverwaltung – dorthin, wo es zu beheben ist."""
        from jusperfect.jurnodes.base import JurNodesFehler

        a = self._adapter(401, nur_pfad="/file-system/folder/content")
        with self.assertRaises(JurNodesFehler) as fehler:
            a.dokumente("rec-1")
        self.assertIn("dateisystem", str(fehler.exception))


class BeiEinemFuenfnullfuenfFragtManDenServer(unittest.TestCase):
    """Aus der Kanzlei, 24.09.2026: „Datei bearbeiten angehakt, kommt immer
    noch 405."

    Damit ist die naheliegende Erklärung — ein fehlendes Recht — ausgeschieden,
    und es wäre der Moment, an dem man anfängt, Pfade zu erfinden. Das ist der
    falsche Moment dafür.

    Ein Server, der 405 antwortet, gehört nach der Norm dazuzusagen, **welche**
    Methoden er auf diesem Pfad annimmt: in der Kopfzeile `Allow`. Die liegt
    der Ablehnung schon bei und kostet keine weitere Anfrage. Sie ist die eine
    Auskunft, die die Ratepartie beendet.
    """

    def _adapter(self, allow: str | None):
        kopf = {"allow": allow} if allow is not None else {}

        def antwort(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/record"):
                return httpx.Response(200, json={"identifier": "rec-1", "fileFolderId": 7})
            if request.url.path.endswith("/file-system/add-file"):
                return httpx.Response(405, headers=kopf, json={})
            return httpx.Response(200, json={"elements": []})

        return HttpJurNodesAdapter("https://jurnodes.example/api", "s", Freigabestelle(),
                                   transport=httpx.MockTransport(antwort))

    def test_was_der_server_dort_annimmt_steht_in_der_meldung(self):
        from jusperfect.jurnodes.base import JurNodesFehler

        a = self._adapter("GET, PUT, OPTIONS")
        with self.assertRaises(JurNodesFehler) as fehler:
            a.gedaechtnis_ablegen("rec-1", b"x")
        self.assertIn("GET, PUT, OPTIONS", str(fehler.exception))

    def test_schweigt_der_server_steht_auch_das_da(self):
        """Eine Meldung, die eine Auskunft vortäuscht, die es nicht gibt, ist
        schlimmer als eine, die die Lücke benennt."""
        from jusperfect.jurnodes.base import JurNodesFehler

        a = self._adapter(None)
        with self.assertRaises(JurNodesFehler) as fehler:
            a.gedaechtnis_ablegen("rec-1", b"x")
        self.assertIn("sagt nicht", str(fehler.exception))

class EineDateiJeAkteAberAlteFassungenBleibenLesbar(unittest.TestCase):
    """jur|nodes ersetzt eine vorhandene Datei nicht - es weist sie ab.

    Gemessen am 25.09.2026 in der Kanzlei: "Der ausgewaehlte Dateiname wird
    bereits verwendet", Status 405. Gesichert wird aber bei JEDEM
    Sitzungsende. Das Loeschrecht hat die Kanzlei bewusst nicht erteilt - es
    gaelte fuer jede Datei des Bestands.

    Also nebeneinander statt uebereinander: Jede Fassung traegt einen
    Zeitstempel im Namen, gelesen wird die juengste.

    Der Zeitstempel kommt von UNS, nicht vom Server. jur|nodes kann selbst
    umbenennen (autoRenameIfExist), aber WIE, steht nirgends - und ein Name,
    den wir nicht kennen, ist einer, den wir nicht wiederfinden.
    """

    def _adapter(self, dateien, aufgezeichnet=None):
        from jusperfect.security.approval import Freigabestelle

        def antworten(anfrage):
            if aufgezeichnet is not None:
                aufgezeichnet.append(anfrage)
            if "folder/content" in anfrage.url.path:
                # Wie der echte Server: Die zweite Seite ist leer, sonst
                # blaettert der Adapter zu Recht bis ans Ende der Welt.
                if "page=" in str(anfrage.url):
                    return httpx.Response(200, json={"elements": []})
                return httpx.Response(200, json={"elements": [
                    {"file": {"identifier": f"f-{i}", "fileName": n}}
                    for i, n in enumerate(dateien)]})
            if "/record" in anfrage.url.path and "search" not in anfrage.url.path:
                return httpx.Response(200, json={"identifier": "rec-1", "fileFolderId": 7})
            return httpx.Response(200, json={})

        return HttpJurNodesAdapter(
            "https://beispiel.invalid", "k", Freigabestelle(),
            transport=httpx.MockTransport(antworten), benutzer="u")

    def test_liegt_schon_eine_da_wird_es_gesagt_statt_abgewiesen(self):
        """Aus der Kanzlei am 25.09.2026: "Loesung B ist bloed, aendere das
        bitte wieder." In einer Mandatsakte sammelten sich Fassungen neben
        den Schriftsaetzen - der falsche Ort dafuer.

        Die Folge ist bewusst in Kauf genommen: Liegt schon eine Datei da,
        laesst sich keine neue ablegen. Das Programm sagt es in eigenen
        Worten und arbeitet weiter.
        """
        from jusperfect.jurnodes.base import GEDAECHTNIS_DATEI, JurNodesFehler

        anfragen = []
        a = self._adapter([GEDAECHTNIS_DATEI], anfragen)
        with self.assertRaises(JurNodesFehler) as fehler:
            a.gedaechtnis_ablegen("rec-1", b"x")
        self.assertIn("bereits ein Aktengedächtnis", str(fehler.exception))
        self.assertIn("nichts verloren", str(fehler.exception))
        self.assertFalse([r for r in anfragen if "add-file" in str(r.url)],
                         "Der Server wurde gefragt, obwohl die Antwort feststand.")

    def test_geschrieben_wird_unter_dem_festen_namen(self):
        from jusperfect.jurnodes.base import GEDAECHTNIS_DATEI

        anfragen = []
        a = self._adapter([], anfragen)
        a.gedaechtnis_ablegen("rec-1", b"x")
        rumpf = [r for r in anfragen if "add-file" in str(r.url)][0].content.decode(
            "utf-8", "replace")
        self.assertIn(GEDAECHTNIS_DATEI, rumpf)

    def test_gelesen_wird_die_juengste(self):
        from jusperfect.jurnodes.base import GEDAECHTNIS_DATEI

        a = self._adapter([
            "00_Aktengedaechtnis-20260920-090000.json.gz",
            GEDAECHTNIS_DATEI,                                  # die aelteste
            "00_Aktengedaechtnis-20260925-113000.json.gz",      # die juengste
            "00_Aktengedaechtnis-20260922-140000.json.gz",
        ])
        eintrag = a._gedaechtnis_eintrag("rec-1")
        self.assertEqual("00_Aktengedaechtnis-20260925-113000.json.gz",
                         eintrag["fileName"])

    def test_die_alte_feste_datei_gilt_als_aelteste(self):
        """"-" steht im Zeichensatz vor "." - nach dem Namen sortiert waere
        die alte Datei die juengste, und die Arbeit eines Tages weg."""
        from jusperfect.jurnodes.base import GEDAECHTNIS_DATEI

        a = self._adapter([GEDAECHTNIS_DATEI,
                           "00_Aktengedaechtnis-20260925-113000.json.gz"])
        self.assertEqual("00_Aktengedaechtnis-20260925-113000.json.gz",
                         a._gedaechtnis_eintrag("rec-1")["fileName"])

    def test_allein_die_alte_datei_wird_weiter_gelesen(self):
        """Wer schon eine hat, soll sie nicht verlieren."""
        from jusperfect.jurnodes.base import GEDAECHTNIS_DATEI

        a = self._adapter([GEDAECHTNIS_DATEI])
        self.assertEqual(GEDAECHTNIS_DATEI,
                         a._gedaechtnis_eintrag("rec-1")["fileName"])

    def test_fremde_dateien_werden_nicht_eingesammelt(self):
        a = self._adapter(["Schriftsatz.pdf", "00_Aktengedaechtnis_alt.json.gz",
                           "00_Aktengedaechtnis-Notizen.json.gz"])
        self.assertIsNone(a._gedaechtnis_eintrag("rec-1"))

    def test_wie_viele_fassungen_liegen_wird_gemerkt(self):
        """Ohne zweite Abfrage - die Liste liegt beim Lesen ohnehin vor."""
        a = self._adapter(["00_Aktengedaechtnis-20260920-090000.json.gz",
                           "00_Aktengedaechtnis-20260925-113000.json.gz"])
        a._gedaechtnis_eintrag("rec-1")
        self.assertEqual(2, a.letzte_fassungen)


class DerAktenstatusEntscheidetUeberDieAufbewahrung(unittest.TestCase):
    """Welches Wort jur|nodes schickt, ist noch nicht bekannt – und es zählt.

    ``_status_uebersetzen`` kennt genau zwei Wörter, „archiviert" und
    „archived". Jedes andere wird stillschweigend zu „laufend". Das hat zwei
    Folgen, und die zweite ist die schwerere:

    * Eine Akte, die in jur|nodes abgeschlossen ist und ihren Status anders
      nennt (etwa „closed" oder „erledigt"), wird nie abschlussreif. Die
      Aufbewahrung, die dem Aktenstatus folgen soll, läuft dann nie an.
    * Der Befund ``status_unbekannt`` aus ``services/aufsicht.py`` – „jur|nodes
      meldet keinen Status; es wird nicht gelöscht" – kann auf diesem Weg gar
      nicht entstehen, denn „laufend" ist weder leer noch „unbekannt". Das
      Netz, das einen Menschen einschalten soll, hängt an dieser Stelle nicht.

    **Beides ist am 02.10.2026 behoben, und zwar gemessen statt geraten:** Die
    Probe hat 300 Akten des Bestands angesehen – 290 tragen „archived", 10
    „active", mehr gibt es nicht. Beide Wörter stehen jetzt in der Tabelle,
    jedes andere wird „unbekannt", und damit schaltet die Aufsicht einen
    Menschen ein, statt zu raten.

    Für die DSFA ist das Ziffer 6.2: Was dort zur Speicherdauer steht, darf
    nicht mehr versprechen als diese zwei Wörter hergeben.
    """

    def test_archiviert_wird_erkannt(self):
        for wort in ("archiviert", "archived", "ARCHIVIERT", " archived "):
            with self.subTest(wort=wort):
                self.assertEqual("archiviert", _status_uebersetzen(wort))

    def test_die_laufenden_woerter_sind_jetzt_benannt(self):
        """Gemessen am 02.10.2026: Der Bestand führt „archived" und „active"."""
        for wort in ("active", "aktiv", "open", "offen", "laufend", "ACTIVE "):
            with self.subTest(wort=wort):
                self.assertEqual("laufend", _status_uebersetzen(wort))

    def test_jedes_andere_wort_heisst_unbekannt(self):
        """Das Netz, das einen Menschen einschalten soll, kann jetzt auslösen.

        Vorher wurde jedes unbekannte Wort still zu „laufend", und der Befund
        ``status_unbekannt`` aus ``services/aufsicht.py`` war damit auf diesem
        Weg unerreichbar – er stand auf dem Papier und hing nicht.
        """
        for wort in ("closed", "abgeschlossen", "erledigt", "geschlossen", "", None):
            with self.subTest(wort=wort):
                self.assertEqual("unbekannt", _status_uebersetzen(wort))

    def test_laufend_loest_keinen_abschluss_aus(self):
        """Immerhin die ungefährliche Richtung: Es wird nichts gelöscht."""
        from jusperfect.services.abschluss import ABSCHLUSSSTATUS

        self.assertNotIn("laufend", ABSCHLUSSSTATUS)
        self.assertIn("archiviert", ABSCHLUSSSTATUS)
