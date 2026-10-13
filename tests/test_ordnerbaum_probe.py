"""Bleibt der Durchlauf in der Akte? Die Probe vom 02.10.2026.

Aus der Kanzlei: In der Arbeitsakte einer Bausache standen drei Schriftstücke
aus einer fremden Verkehrsunfallsache. „Es ist nicht ersichtlich, wie diese
Sachen hineingekommen sind."

Zwei Erklärungen sind möglich, und sie verlangen entgegengesetzte Handgriffe:
die Schriftstücke liegen wirklich in dieser Akte (dann ist in jurnodes falsch
abgelegt worden), oder der Durchlauf verlässt die Akte (dann ist es ein Fehler
des Programms). Die Probe muss **beide** Fälle auseinanderhalten können –
eine, die immer dasselbe sagt, entscheidet nichts.

Deshalb wird sie hier gegen einen nachgebauten Server geführt, einmal so,
einmal so.
"""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from jusperfect.jurnodes.http_adapter import Endpunkte
from jusperfect.jurnodestest import _als_tag, _ordnerbaum, _verdeckt


class _Antwort:
    def __init__(self, daten, status=200):
        self._daten, self.status_code = daten, status

    def json(self):
        return self._daten


class _Server:
    """Ein jurnodes, dessen Ordnerbaum wir selbst bestimmen."""

    def __init__(self, baum, dateien, akte=None):
        self.baum = baum          # {ordner_id: [unter_ids]}
        self.dateien = dateien    # {ordner_id: [recordIdentifier, ...]}
        self.akte = akte or {"identifier": "A-1", "recordSign": "BA-7",
                             "fileFolderId": 10}

    def get(self, pfad, params=None):
        params = params or {}
        if pfad == Endpunkte.akte:
            return _Antwort(self.akte)
        if pfad == Endpunkte.ordner_inhalt:
            ordner = params.get("folderId")
            eintraege = [{"type": "folder", "folder": {"id": u, "canRead": True}}
                         for u in self.baum.get(ordner, [])]
            eintraege += [{"type": "file", "file": {"id": f"{ordner}-{i}",
                                                    "recordIdentifier": akte}}
                          for i, akte in enumerate(self.dateien.get(ordner, []))]
            return _Antwort({"elements": eintraege})
        return _Antwort(None, 404)


def _lauf(server) -> str:
    puffer = io.StringIO()
    with redirect_stdout(puffer):
        _ordnerbaum(server, Endpunkte(), "A-1")
    return puffer.getvalue()


class DerSaubereFall(unittest.TestCase):
    """Alle Dateien gehören zur Akte."""

    def test_die_probe_sagt_es_deutlich(self):
        text = _lauf(_Server({10: [11, 12], 11: [], 12: []},
                             {10: ["A-1"], 11: ["A-1", "A-1"], 12: ["A-1"]}))
        self.assertIn("Keine Datei nennt eine andere Akte", text)
        self.assertIn("4 Datei(en)", text)

    def test_und_verweist_auf_die_andere_erklaerung(self):
        """Dann liegt es an der Ablage in jurnodes – das muss dastehen."""
        text = _lauf(_Server({10: []}, {10: ["A-1"]}))
        self.assertIn("in jurnodes in dieser Akte abgelegt", text)


class DerFallDerUntersucht_Wird(unittest.TestCase):
    """Der Durchlauf verlässt die Akte."""

    def test_fremde_dateien_werden_gezaehlt_und_benannt(self):
        text = _lauf(_Server({10: [11], 11: []},
                             {10: ["A-1", "A-1"], 11: ["041234/22", "041234/22"]}))
        self.assertIn("2 Datei(en) nennen eine ANDERE Akte", text)
        self.assertIn("Fehler des Programms", text)

    def test_die_fremde_akte_wird_nicht_beim_namen_genannt(self):
        """Diese Ausgabe wird verschickt.

        Sie soll zeigen, DASS eine fremde Akte dabei ist – nicht welche. Der
        Bearbeiter sieht das in jurnodes selbst; ich brauche es nicht.
        """
        text = _lauf(_Server({10: []}, {10: ["041234/22"]}))
        self.assertNotIn("041234/22", text)
        self.assertIn("041…(9)", text)

    def test_gleiche_fremde_akten_werden_zusammengezaehlt(self):
        text = _lauf(_Server({10: []}, {10: ["041234/22"] * 3}))
        self.assertIn("041…(9): 3×", text)


class WennDieAngabeFehlt(unittest.TestCase):
    def test_die_probe_gibt_das_zu(self):
        """Eine Probe, die bei fehlender Angabe „alles gut" sagt, ist gefährlich."""
        server = _Server({10: []}, {10: []})
        server.get = lambda pfad, params=None: (
            _Antwort(server.akte) if pfad == Endpunkte.akte
            else _Antwort({"elements": [{"type": "file", "file": {"id": "x"}}]}))
        text = _lauf(server)
        self.assertIn("nennen ihre Akte gar nicht", text)
        self.assertNotIn("Keine Datei nennt eine andere Akte", text)


class DieGrenzen(unittest.TestCase):
    def test_eine_schleife_haelt_sie_nicht_auf(self):
        """Ordner, die sich gegenseitig enthalten, gibt es wirklich."""
        text = _lauf(_Server({10: [11], 11: [10]}, {10: ["A-1"], 11: ["A-1"]}))
        self.assertIn("2 Ordner", text)

    def test_ein_ordner_der_anderswo_zu_liegen_angibt_faellt_auf(self):
        server = _Server({10: [11], 11: []}, {10: [], 11: []})
        echt = server.get

        def mit_elternangabe(pfad, params=None):
            antwort = echt(pfad, params)
            if pfad == Endpunkte.ordner_inhalt and params.get("folderId") == 10:
                return _Antwort({"elements": [
                    {"type": "folder",
                     "folder": {"id": 11, "canRead": True, "parentId": 999}}]})
            return antwort

        server.get = mit_elternangabe
        self.assertIn("anderswo zu liegen angeben", _lauf(server))


class DieNummern(unittest.TestCase):
    """Welche Fundstelle stammt aus welchem Ordner?

    Am 02.10.2026 musste das von Hand nachgerechnet werden, um zu sehen, dass
    D47–D49 genau der Inhalt eines einzigen Unterordners sind. Das soll
    dastehen, nicht errechnet werden müssen.
    """

    def test_jeder_ordner_bekommt_seine_spanne(self):
        text = _lauf(_Server({10: [11], 11: []},
                             {10: ["A-1"] * 2, 11: ["A-1"] * 3}))
        self.assertIn("Ordner 10: D1–D2", text)
        self.assertIn("Ordner 11: D3–D5", text)

    def test_ein_einzelnes_dokument_steht_ohne_spanne_da(self):
        text = _lauf(_Server({10: []}, {10: ["A-1"]}))
        self.assertIn("Ordner 10: D1", text)
        self.assertNotIn("D1–D1", text)

    def test_der_vorbehalt_steht_dabei(self):
        """Ein übersprungenes Dokument verschiebt alles danach."""
        text = _lauf(_Server({10: []}, {10: ["A-1"]}))
        self.assertIn("verschiebt alles danach", text)


class DieFeldnamenEinerDatei(unittest.TestCase):
    def test_sie_werden_gezeigt(self):
        """Sonst bleibt „nennt ihre Akte nicht" eine Behauptung ohne Beleg.

        Am 02.10.2026 meldete die Probe genau das für alle 55 Dateien – und es
        war nicht zu sehen, ob die Angabe fehlt oder ob das Feld nur anders
        heißt, als die Probe erwartet. Mit ``parentFolder`` war genau das der
        Fall gewesen.
        """
        server = _Server({10: []}, {10: []})
        server.get = lambda pfad, params=None: (
            _Antwort(server.akte) if pfad == Endpunkte.akte
            else _Antwort({"elements": [{"type": "file",
                                         "file": {"id": 1, "fileName": "x",
                                                  "folderId": 10}}]}))
        text = _lauf(server)
        self.assertIn("Felder, die eine Datei fuehrt", text)
        self.assertIn("fileName", text)
        self.assertIn("folderId", text)

    def test_aber_keine_werte(self):
        server = _Server({10: []}, {10: []})
        server.get = lambda pfad, params=None: (
            _Antwort(server.akte) if pfad == Endpunkte.akte
            else _Antwort({"elements": [{"type": "file",
                                         "file": {"fileName": "Vermerk Testmann.pdf"}}]}))
        text = _lauf(server)
        self.assertNotIn("Testmann", text)


class DerEchteFeldname(unittest.TestCase):
    def test_parentFolder_wird_geprueft(self):
        """Der Name, den der Server wirklich führt.

        In der ersten Fassung fehlte er in der Liste. Die Prüfung „liegt dieser
        Ordner wirklich dort, wo wir ihn gefunden haben?" lief damit ins Leere,
        ohne es zu sagen – und Schweigen liest sich wie Entwarnung.
        """
        server = _Server({10: [11], 11: []}, {10: [], 11: []})

        def mit_echtem_namen(pfad, params=None):
            if pfad == Endpunkte.akte:
                return _Antwort(server.akte)
            if params.get("folderId") == 10:
                return _Antwort({"elements": [
                    {"type": "folder",
                     "folder": {"id": 11, "canRead": True, "parentFolder": 999}}]})
            return _Antwort({"elements": []})

        server.get = mit_echtem_namen
        self.assertIn("anderswo zu liegen angeben", _lauf(server))

    def test_der_erwartete_fall_schlaegt_keinen_alarm(self):
        server = _Server({10: [11], 11: []}, {10: [], 11: []})

        def ordentlich(pfad, params=None):
            if pfad == Endpunkte.akte:
                return _Antwort(server.akte)
            if params.get("folderId") == 10:
                return _Antwort({"elements": [
                    {"type": "folder",
                     "folder": {"id": 11, "canRead": True, "parentFolder": 10}}]})
            return _Antwort({"elements": []})

        server.get = ordentlich
        self.assertNotIn("anderswo zu liegen angeben", _lauf(server))


class DieReihenfolge(unittest.TestCase):
    """Sie muss die des Betriebs sein – sonst nennt die Probe den falschen Ordner.

    Der Lauf vom 05.10.2026 hat den Unterschied gezeigt: Die Probe ging erst
    **beide** Wurzeln ab und dann deren Unterordner; ``dokumente()`` geht den
    Dateiordner vollständig ab und erst danach die Korrespondenz. Bei der Akte
    X-100-2026 glichen sich die Unterschiede zufällig wieder aus – ab D40 stand
    in beiden dasselbe.

    Auf diesen Zufall ist kein Verlass. Eine Probe, die anders zählt als der
    Betrieb, nennt irgendwann den falschen Ordner, und niemand merkt es.
    """

    def test_wurzel_fuer_wurzel_statt_beide_zugleich(self):
        # Dateiordner 10 mit Unterordner 11, Korrespondenz 20 mit Unterordner 21.
        server = _Server({10: [11], 11: [], 20: [21], 21: []},
                         {10: ["A-1"], 11: ["A-1"], 20: ["A-1"], 21: ["A-1"]})
        server.akte = {"identifier": "A-1", "fileFolderId": 10,
                       "correspondenceFolderId": 20}
        text = _lauf(server)
        # Richtig: 10, 11, 20, 21. Falsch waere 10, 20, 11, 21.
        for ordner, spanne in ((10, "D1"), (11, "D2"), (20, "D3"), (21, "D4")):
            self.assertIn(f"Ordner {ordner}: {spanne}", text)


class DasDatumDerAblage(unittest.TestCase):
    """Die Angabe, die einen falsch einsortierten Ordner verrät.

    Dateien von 2022 in einer Akte von 2026 – das beantwortet die Frage, die
    ein Dateiname auch nicht besser beantworten würde. Und ein Datum nennt
    weder Mandanten noch Gegenstand.
    """

    def test_es_steht_bei_jedem_ordner(self):
        server = _Server({10: []}, {10: ["A-1", "A-1"]})
        echt = server.get

        def mit_datum(pfad, params=None):
            antwort = echt(pfad, params)
            if pfad == Endpunkte.ordner_inhalt:
                for e in antwort.json()["elements"]:
                    if e.get("type") == "file":
                        e["file"]["addedDate"] = "2022-12-15T10:00:00"
            return antwort

        server.get = mit_datum
        self.assertIn("abgelegt 2022-12-15", _lauf(server))

    def test_eine_spanne_wird_als_spanne_gezeigt(self):
        server = _Server({10: []}, {10: ["A-1", "A-1"]})
        echt = server.get

        def mit_zwei_daten(pfad, params=None):
            antwort = echt(pfad, params)
            if pfad == Endpunkte.ordner_inhalt:
                tage = ["2022-12-15", "2026-04-02"]
                for e, tag in zip([x for x in antwort.json()["elements"]
                                   if x.get("type") == "file"], tage):
                    e["file"]["addedDate"] = tag
            return antwort

        server.get = mit_zwei_daten
        self.assertIn("abgelegt 2022-12-15 bis 2026-04-02", _lauf(server))

    def test_ohne_datum_steht_nichts_dort(self):
        """Nichts hinschreiben ist besser als ein erfundenes Datum."""
        text = _lauf(_Server({10: []}, {10: ["A-1"]}))
        # Nur die Zeile des Ordners pruefen: Das Wort "abgelegt" steht auch im
        # Schlusssatz ("in dieser Akte abgelegt") und hat dort nichts mit dem
        # Datum zu tun.
        zeile = next(z for z in text.splitlines() if "Ordner 10: D" in z)
        self.assertEqual("Ordner 10: D1", zeile.strip())


class AelterAlsDieAkte(unittest.TestCase):
    """Ein Ordner, der befüllt wurde, bevor es die Akte gab.

    Der Lauf vom 05.10.2026 an der Akte X-100-2026: Der Dateiordner trägt
    Ablagedaten aus 2026, der ganze Korrespondenzzweig aus 2022 und 2023 – 17
    von 55 Dokumenten.

    Die Folgerung ist schlicht und hält: Eine Datei kann nicht in eine Akte
    gelegt worden sein, die es noch nicht gab. ``addedDate`` ist der Tag der
    Ablage in jurnodes, nicht das Datum des Schriftstücks – ein altes
    Schreiben, das heute eingescannt wird, trägt das heutige Datum.
    """

    def _server(self, angelegt, tage):
        server = _Server({10: [11], 11: []}, {10: ["A-1"], 11: ["A-1"]})
        server.akte = {"identifier": "A-1", "fileFolderId": 10,
                       "creationDate": angelegt}
        echt = server.get

        def mit_daten(pfad, params=None):
            antwort = echt(pfad, params)
            if pfad == Endpunkte.ordner_inhalt:
                for e in antwort.json()["elements"]:
                    if e.get("type") == "file":
                        e["file"]["addedDate"] = tage[params.get("folderId")]
            return antwort

        server.get = mit_daten
        return server

    def test_er_wird_benannt(self):
        """Im DATEIbaum ist er ein Mangel — dort liest der Betrieb."""
        text = _lauf(self._server("2026-07-29T08:00:00",
                                  {10: "2026-08-01", 11: "2022-12-15"}))
        self.assertIn("1 Ordner im DATEIbaum wurden befuellt, BEVOR es diese "
                      "Akte gab", text)
        self.assertIn("Ordner 11: erste Ablage 2022-12-15", text)
        self.assertIn("zu klaeren in jurnodes", text)
        self.assertIn("Das ist der Baum, den der Betrieb liest.", text)

    def test_im_korrespondenzbaum_ist_er_kein_mangel(self):
        """Berichtigt am 13.10.2026.

        Bis dahin stand über allen Ordnern ein einziges „✗ … zu klaeren in
        jur|nodes". Der Lauf am 12.10.2026 hat damit fünf Ordner als Mangel
        des Herstellers gemeldet, die **alle im Korrespondenzbaum** lagen —
        also genau das Muster, das am 08.10.2026 als **unser eigener** Fehler
        aufgeklärt worden ist: Die Nummer in `correspondenceFolderId` gehört
        nicht zur Korrespondenz dieser Akte, und der Betrieb liest diesen Baum
        seit dem 05.10.2026 nicht mehr.

        Ein Bogen, der einen aufgeklärten Befund weiter als Mangel ausgibt,
        schickt die Kanzlei zum Hersteller — mit einer Frage, die schon
        beantwortet ist.
        """
        server = _Server({10: [], 20: [21], 21: []},
                         {10: ["A-1"], 20: ["A-1"], 21: ["A-1"]})
        server.akte = {"identifier": "A-1", "fileFolderId": 10,
                       "correspondenceFolderId": 20,
                       "creationDate": "2026-07-29T08:00:00"}
        echt = server.get
        tage = {10: "2026-08-01", 20: "2023-03-22", 21: "2022-12-15"}

        def mit_daten(pfad, params=None):
            antwort = echt(pfad, params)
            if pfad == Endpunkte.ordner_inhalt:
                for e in antwort.json()["elements"]:
                    if e.get("type") == "file":
                        e["file"]["addedDate"] = tage[params.get("folderId")]
            return antwort

        server.get = mit_daten
        text = _lauf(server)
        self.assertIn("Ordner im KORRESPONDENZbaum", text)
        self.assertIn("Das ist KEIN Mangel", text)
        self.assertNotIn("im DATEIbaum wurden befuellt", text,
                         "Der Dateiordner ist hier jünger als die Akte.")
        # Und die Abhilfe steht dabei, nicht nur die Einordnung.
        self.assertIn("POST /correspondence/search", text)

    def test_beide_baeume_werden_getrennt_genannt(self):
        """Liegt in beiden etwas Älteres, darf nicht eines das andere decken."""
        server = _Server({10: [11], 11: [], 20: []},
                         {10: ["A-1"], 11: ["A-1"], 20: ["A-1"]})
        server.akte = {"identifier": "A-1", "fileFolderId": 10,
                       "correspondenceFolderId": 20,
                       "creationDate": "2026-07-29T08:00:00"}
        echt = server.get
        tage = {10: "2026-08-01", 11: "2022-12-15", 20: "2023-03-22"}

        def mit_daten(pfad, params=None):
            antwort = echt(pfad, params)
            if pfad == Endpunkte.ordner_inhalt:
                for e in antwort.json()["elements"]:
                    if e.get("type") == "file":
                        e["file"]["addedDate"] = tage[params.get("folderId")]
            return antwort

        server.get = mit_daten
        text = _lauf(server)
        self.assertIn("im DATEIbaum wurden befuellt", text)
        self.assertIn("im KORRESPONDENZbaum", text)

    def test_ein_ordner_aus_der_zeit_der_akte_nicht(self):
        text = _lauf(self._server("2026-07-29T08:00:00",
                                  {10: "2026-08-01", 11: "2026-08-05"}))
        self.assertNotIn("BEVOR es diese Akte gab", text)

    def test_ohne_anlagedatum_wird_nichts_behauptet(self):
        """Ohne Vergleichsmaßstab kein Urteil."""
        text = _lauf(self._server(None, {10: "2022-01-01", 11: "2022-01-01"}))
        self.assertNotIn("BEVOR es diese Akte gab", text)
        self.assertNotIn("Akte angelegt am", text)

    def test_das_anlagedatum_steht_oben(self):
        text = _lauf(self._server("2026-07-29T08:00:00",
                                  {10: "2026-08-01", 11: "2026-08-05"}))
        self.assertIn("Akte angelegt am: 2026-07-29", text)


class DasDatumLesen(unittest.TestCase):
    """Zwei Schreibweisen in derselben Antwort – und ein Fehlalarm dazwischen.

    ``addedDate`` kommt als ISO (``2022-12-15T09:14:00``), ``creationDate``
    dagegen als ``Thu Jul 30 00:00:00 CEST 2026``.

    Am 05.10.2026 nahm die Probe davon die ersten zehn Zeichen – ``Thu Jul 30``
    – und verglich **Zeichen gegen Zeichen**. Jede Ziffer steht vor jedem
    Buchstaben, also galt jeder Ordner als älter als die Akte: sieben statt
    fünf, darunter der Dateiordner der Akte selbst. Der Befund stimmte in der
    Sache und war in der Begründung falsch, und das ist der schlechteste
    Zustand von beidem.
    """

    def test_die_wortform_mit_dem_jahr_vorn(self):
        """So schickt es dieser Server – die Schreibweise von JavaScript.

        Der erste Versuch nahm nur die Java-Form an, bei der das Jahr am Ende
        steht. Welche ein Server schickt, ist seine Sache; beide zu lesen ist
        billiger als eine Annahme darüber.
        """
        self.assertEqual("2026-07-30", _als_tag(
            "Thu Jul 30 2026 17:42:18 GMT+0000 (Coordinated Universal Time)"))
        self.assertEqual("2022-12-15", _als_tag("Mon Dec 15 2022 11:02:33 GMT+0100"))

    def test_die_wortform_mit_dem_jahr_hinten(self):
        self.assertEqual("2026-07-30", _als_tag("Thu Jul 30 00:00:00 CEST 2026"))
        self.assertEqual("2022-12-15", _als_tag("Mon Dec 15 11:02:33 CET 2022"))

    def test_iso_mit_und_ohne_uhrzeit(self):
        self.assertEqual("2022-12-15", _als_tag("2022-12-15T09:14:00"))
        self.assertEqual("2026-08-05", _als_tag("2026-08-05"))

    def test_was_nicht_zu_lesen_ist_bleibt_leer(self):
        """Leer heißt: damit wird nicht gerechnet."""
        for wert in ("irgendwas", "", None, "30.07.2026", "Thu Jul 30"):
            self.assertEqual("", _als_tag(wert), repr(wert))

    def test_ohne_lesbares_datum_wird_nichts_verglichen(self):
        server = _Server({10: []}, {10: ["A-1"]})
        server.akte = {"identifier": "A-1", "fileFolderId": 10,
                       "creationDate": "Thu Jul 30"}
        echt = server.get

        def mit_datum(pfad, params=None):
            antwort = echt(pfad, params)
            if pfad == Endpunkte.ordner_inhalt:
                for e in antwort.json()["elements"]:
                    if e.get("type") == "file":
                        e["file"]["addedDate"] = "2022-12-15"
            return antwort

        server.get = mit_datum
        text = _lauf(server)
        self.assertIn("nicht zu lesen", text)
        self.assertNotIn("BEVOR es diese Akte gab", text)

    def test_die_wortform_wird_auch_oben_richtig_gezeigt(self):
        server = _Server({10: []}, {10: ["A-1"]})
        server.akte = {"identifier": "A-1", "fileFolderId": 10,
                       "creationDate": "Thu Jul 30 2026 17:42:18 GMT+0000 "
                                       "(Coordinated Universal Time)"}
        self.assertIn("Akte angelegt am: 2026-07-30", _lauf(server))


class DasVerdecken(unittest.TestCase):
    def test_es_laesst_wiedererkennen_aber_nicht_lesen(self):
        self.assertEqual("041…(9)", _verdeckt("041234/22"))
        self.assertEqual("abc…(5)", _verdeckt("abcde"))

    def test_kurze_werte_verraten_gar_nichts(self):
        self.assertEqual("…(2)", _verdeckt("ab"))


if __name__ == "__main__":
    unittest.main()
