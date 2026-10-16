"""Ganze Blöcke, die beim Einlesen fehlten – und das Dokument von Hand dazu.

Aus der Kanzlei am 16.10.2026:

    „Das Programm hat leider beim Einlesen ganze Blöcke nicht mitgenommen und
    zwar an Stellen, die sehr wichtig waren. Ich hätte auch gerne das Dokument
    direkt in den Chat eingefügt, hierfür fehlt aber eine Funktion."

**Der Befund.** Ob ein PDF ein Scan ist, entschied bis dahin der *Mittelwert
über alle Seiten*. Das geht genau bei dem Dokument schief, das in einer Akte
am häufigsten vorkommt: der digital geschriebene Schriftsatz mit der
**eingescannten Anlage dahinter**. Zweiundzwanzig Seiten Text und acht Seiten
Scan ergeben einen hohen Mittelwert – das Dokument galt als lesbar, pypdf gab
für die acht Seiten nichts zurück, und niemand erfuhr davon. Gezählt wurde
nur, ob das **ganze** Dokument null Zeichen hat.

Dass es die wichtigen Stellen traf, ist kein Zufall: Gescannt wird, was von
außen kommt und unterschrieben ist – das Attest, das Urteil, die
Zustellungsurkunde, der handschriftliche Vermerk.

**Die Abhilfe, zweiteilig.** Entschieden wird je Seite; die leeren Seiten
gehen einzeln durch die Texterkennung. Und was danach noch leer ist, trägt
einen Hinweis, statt stillschweigend zu fehlen.
"""

from __future__ import annotations

import base64
import io
import json
import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jusperfect.domain.models import Dokument, Seite
from jusperfect.ocr.base import KeinOcr, OcrFehler
from jusperfect.services.extraktion import (
    NichtUnterstuetzt, _leere_seiten, seiten_nennen, text_extrahieren,
)
from tests.hilfen import client, dienste
from tests.test_extraktion import _pdf_leer, _pdf_mit_text

WURZEL = Path(__file__).resolve().parents[1]
JS = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")
HTML = (WURZEL / "jusperfect" / "static" / "index.html").read_text(encoding="utf-8")
CSS = (WURZEL / "jusperfect" / "static" / "styles.css").read_text(encoding="utf-8")

AKTE = "VU-2026-0042"


def _dok(name="schriftsatz.pdf", mime="application/pdf"):
    return Dokument(id="D-009", akte_id="X-2026-0001", titel=name, dateiname=name, mime_typ=mime)


def _gemischt(text_seiten: int = 2, leer_seiten: int = 1) -> bytes:
    """Ein PDF wie in der Akte: vorn der Schriftsatz, hinten die Anlage."""
    from pypdf import PdfReader, PdfWriter

    w = PdfWriter()
    for _ in range(text_seiten):
        for s in PdfReader(io.BytesIO(_pdf_mit_text())).pages:
            w.add_page(s)
    for _ in range(leer_seiten):
        for s in PdfReader(io.BytesIO(_pdf_leer())).pages:
            w.add_page(s)
    puffer = io.BytesIO()
    w.write(puffer)
    return puffer.getvalue()


class MitzaehlendesOcr:
    """Merkt sich, wie viele Seiten ihm vorgelegt wurden."""

    def __init__(self, text="ANLAGE K 5 - Aerztliches Attest, Dr. Meier, 14.03.2026"):
        self.vorgelegt: list[int] = []
        self._text = text

    def erkennen(self, daten, mime, sitzung_id, dokument_id):
        from pypdf import PdfReader

        n = len(PdfReader(io.BytesIO(daten)).pages)
        self.vorgelegt.append(n)
        return [Seite(nummer=i, text=f"{self._text} (Blatt {i})") for i in range(1, n + 1)]


class SeiteFuerSeiteStattImMittel(unittest.TestCase):

    def test_der_alte_massstab_haette_hier_nichts_gefunden(self):
        """Die Gegenprobe zum Befund – in richtiger Polarität.

        Zwei Textseiten und eine leere ergeben im Mittel 59 Zeichen je Seite
        und liegen damit weit über der Schwelle von 30. Genau deshalb fiel
        die dritte Seite durch.
        """
        from jusperfect.services.extraktion import _SCAN_SCHWELLE_ZEICHEN_JE_SEITE

        seiten, _ = text_extrahieren(_dok(), _gemischt(), MitzaehlendesOcr(), "s")
        roh = [len(s.text.strip()) for s in seiten]
        self.assertGreater(sum(roh) / len(roh), _SCAN_SCHWELLE_ZEICHEN_JE_SEITE)

    def test_die_leeren_seiten_werden_benannt(self):
        seiten = [Seite(nummer=1, text="x" * 200), Seite(nummer=2, text=""),
                  Seite(nummer=3, text="- 3 -"), Seite(nummer=4, text="y" * 90)]
        self.assertEqual(_leere_seiten(seiten), [2, 3])

    def test_nur_die_leeren_seiten_gehen_an_die_texterkennung(self):
        """Textract rechnet je Seite ab. Ein Schriftsatz mit drei gescannten
        Anlagenseiten soll drei Seiten kosten und nicht dreißig."""
        ocr = MitzaehlendesOcr()
        seiten, benutzt = text_extrahieren(_dok(), _gemischt(5, 2), ocr, "s")
        self.assertTrue(benutzt)
        self.assertEqual(ocr.vorgelegt, [2], "Es dürfen nur die leeren Seiten hinausgehen.")
        self.assertEqual(len(seiten), 7)

    def test_die_erkannte_seite_behaelt_ihre_nummer(self):
        """Die Texterkennung zählt im Teil-PDF wieder ab 1. Zählte das
        Ergebnis hier mit, zeigte jede Fundstelle auf die falsche Seite – und
        die Belegpflicht trüge nicht."""
        seiten, _ = text_extrahieren(_dok(), _gemischt(2, 2), MitzaehlendesOcr(), "s")
        nach_nummer = {s.nummer: s.text for s in seiten}
        self.assertEqual(sorted(nach_nummer), [1, 2, 3, 4])
        self.assertIn("Blatt 1", nach_nummer[3])
        self.assertIn("Blatt 2", nach_nummer[4])
        self.assertNotIn("ANLAGE", nach_nummer[1])

    def test_ein_pdf_ohne_leere_seiten_kostet_keine_texterkennung(self):
        ocr = MitzaehlendesOcr()
        seiten, benutzt = text_extrahieren(_dok(), _gemischt(3, 0), ocr, "s")
        self.assertFalse(benutzt)
        self.assertEqual(ocr.vorgelegt, [])
        self.assertEqual([s.hinweis for s in seiten], ["", "", ""])

    def test_ein_durchgehender_scan_geht_als_ganzes(self):
        """Der Weg von früher bleibt: Dort ist nichts zu retten, was man
        behalten müsste."""
        ocr = MitzaehlendesOcr()
        seiten, benutzt = text_extrahieren(_dok(), _gemischt(0, 3), ocr, "s")
        self.assertTrue(benutzt)
        self.assertEqual(ocr.vorgelegt, [3])
        self.assertEqual(len(seiten), 3)

    def test_ohne_texterkennung_bleibt_das_gelesene_erhalten(self):
        """Zweiundzwanzig gelesene Seiten wegzuwerfen, weil die acht
        gescannten nicht gehen, wäre genau der Schaden, der behoben wird."""
        seiten, benutzt = text_extrahieren(_dok(), _gemischt(2, 1), KeinOcr(), "s")
        self.assertFalse(benutzt)
        self.assertEqual(len(seiten), 3)
        self.assertGreater(len(seiten[0].text.strip()), 30)
        self.assertIn("keine Texterkennung eingerichtet", seiten[2].hinweis)

    def test_ein_fehler_der_texterkennung_wirft_nichts_weg(self):
        class Kaputt:
            def erkennen(self, *a, **k):
                raise OcrFehler("AWS weist gerade zu viele Anfragen zugleich ab.")

        seiten, benutzt = text_extrahieren(_dok(), _gemischt(2, 1), Kaputt(), "s")
        self.assertFalse(benutzt)
        self.assertGreater(len(seiten[0].text.strip()), 30)
        self.assertIn("schlug fehl", seiten[2].hinweis)

    def test_die_luecke_steht_in_der_sitzung(self):
        """Ein Hinweis, den niemand sieht, ist keiner."""
        d = dienste()
        c = client(d, "ra-weber")
        sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
        antwort = c.post(f"/api/sitzungen/{sid}/dokumente/einfuegen", json={
            "titel": "Schriftsatz mit Anlage", "dateiname": "schriftsatz.pdf",
            "inhalt_b64": base64.b64encode(_gemischt(2, 1)).decode()})
        self.assertEqual(antwort.status_code, 201, antwort.text)
        self.assertEqual(antwort.json()["eingefuegt"]["seiten_ohne_text"], [3])
        hinweise = " ".join(antwort.json()["sitzung"]["hinweise"])
        self.assertIn("Seite 3 von 3", hinweise)

    def test_seiten_nennen(self):
        for roh, erwartet in (([], ""), ([3], "3"), ([3, 4], "3 bis 4"),
                              ([3, 7, 8, 9], "3 und 7 bis 9"),
                              ([3, 7, 8, 9, 14], "3, 7 bis 9 und 14")):
            with self.subTest(seiten=roh):
                self.assertEqual(seiten_nennen(roh), erwartet)


FAELLE = [[], [3], [3, 4], [3, 7, 8, 9], [3, 7, 8, 9, 14], [1, 2, 3], [2, 4, 6]]


class BeideFassungenNennenGleich(unittest.TestCase):
    """`seiten_nennen` gibt es zweimal: im Programm und in der Oberfläche.

    Zwei Fassungen derselben Regel laufen auseinander, sobald eine geändert
    wird – und dann sagt der Hinweis in der Sitzung etwas anderes als das Band
    über dem Dokument.
    """

    def test_wortgleich(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node ist auf diesem Rechner nicht vorhanden.")
        anfang = JS.index("function seitenNennen(")
        ende = JS.index("/** Der Eintrag der Arbeitsakte")
        programm = JS[anfang:ende] + (
            "\nconst faelle = " + json.dumps(FAELLE) + ";\n"
            "console.log(JSON.stringify(faelle.map(seitenNennen)));\n")
        with TemporaryDirectory() as ordner:
            datei = Path(ordner) / "probe.js"
            datei.write_text(programm, encoding="utf-8")
            lauf = subprocess.run([node, str(datei)], capture_output=True, text=True, timeout=60)
        self.assertEqual(lauf.returncode, 0, lauf.stderr)
        for roh, dort in zip(FAELLE, json.loads(lauf.stdout)):
            with self.subTest(seiten=roh):
                self.assertEqual(seiten_nennen(roh), dort)


class DasDokumentDirektInDenChat(unittest.TestCase):
    """Der Weg für das Blatt, das gerade nicht in der E-Akte liegt."""

    def _sitzung(self):
        d = dienste()
        c = client(d, "ra-weber")
        sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
        return d, c, sid

    def test_text_wird_zu_einem_dokument_mit_fundstellen(self):
        """Es wird gelesen wie jedes andere Dokument – sonst trüge die
        Belegpflicht dafür nicht."""
        d, c, sid = self._sitzung()
        antwort = c.post(f"/api/sitzungen/{sid}/dokumente/einfuegen", json={
            "titel": "Attest Dr. Meier",
            "text": "ANLAGE K 5\n\nHWS-Distorsion festgestellt.\n"
                    "Arbeitsunfaehigkeit fuer eine Woche bescheinigt."})
        self.assertEqual(antwort.status_code, 201, antwort.text)
        eintrag = antwort.json()["eingefuegt"]
        self.assertTrue(eintrag["eingefuegt"])
        passagen = c.get(f"/api/sitzungen/{sid}/passagen").json()["passagen"]
        meine = [p for p in passagen if p["dokument_id"] == eintrag["dokument_id"]]
        self.assertTrue(meine)
        self.assertTrue(meine[0]["kennung"].startswith(f"D{eintrag['nummer']}-"))
        self.assertIn("HWS-Distorsion", meine[0]["text"])

    def test_eine_datei_geht_denselben_weg(self):
        d, c, sid = self._sitzung()
        antwort = c.post(f"/api/sitzungen/{sid}/dokumente/einfuegen", json={
            "dateiname": "anlage.pdf",
            "inhalt_b64": base64.b64encode(_pdf_mit_text()).decode()})
        self.assertEqual(antwort.status_code, 201, antwort.text)
        self.assertEqual(antwort.json()["eingefuegt"]["titel"], "anlage.pdf")
        self.assertGreater(antwort.json()["eingefuegt"]["zeichen"], 0)

    def test_die_nummer_stoesst_nicht_mit_der_akte_zusammen(self):
        """Sonst meinte „D7-S1-P2" zwei verschiedene Stellen."""
        d, c, sid = self._sitzung()
        vorher = c.get(f"/api/sitzungen/{sid}").json()["sitzung"]["geladen"]
        hoechste = max([g["nummer"] for g in vorher] + [len(vorher)])
        antwort = c.post(f"/api/sitzungen/{sid}/dokumente/einfuegen",
                         json={"text": "Ein eingefuegtes Blatt."})
        self.assertGreater(antwort.json()["eingefuegt"]["nummer"], hoechste)
        kennungen = [p["kennung"].split("-")[0]
                     for p in c.get(f"/api/sitzungen/{sid}/passagen").json()["passagen"]]
        nach_dokument = {}
        for p in c.get(f"/api/sitzungen/{sid}/passagen").json()["passagen"]:
            nach_dokument.setdefault(p["kennung"].split("-")[0], set()).add(p["dokument_id"])
        for marke, dokumente in nach_dokument.items():
            self.assertEqual(len(dokumente), 1, f"{marke} meint mehrere Dokumente")
        self.assertTrue(kennungen)

    def test_es_geht_nicht_ins_gedaechtnis_und_nicht_nach_jurnodes(self):
        """Was im Aktengedächtnis liegt, stammt aus der E-Akte – darauf soll
        man sich verlassen können. Und geschrieben wird ohnehin nichts."""
        d, c, sid = self._sitzung()
        antwort = c.post(f"/api/sitzungen/{sid}/dokumente/einfuegen",
                         json={"titel": "Fax von heute", "text": "Zugestellt am 16.10.2026."})
        eingefuegt = antwort.json()["eingefuegt"]["dokument_id"]
        g = d.gedaechtnis.lesen(AKTE)
        if g is not None:
            self.assertNotIn(eingefuegt, [x.dokument_id for x in g.dokumente])
        self.assertEqual(d.adapter.geschriebene_vermerke, [])

    def test_es_sagt_dass_es_nur_in_dieser_sitzung_liegt(self):
        d, c, sid = self._sitzung()
        antwort = c.post(f"/api/sitzungen/{sid}/dokumente/einfuegen",
                         json={"titel": "Fax", "text": "Zugestellt am 16.10.2026."})
        hinweise = " ".join(antwort.json()["sitzung"]["hinweise"])
        self.assertIn("nur in dieser Sitzung", hinweise)
        self.assertIn("nicht im Aktengedächtnis", hinweise)

    def test_ohne_inhalt_eine_auskunft_und_kein_serverfehler(self):
        d, c, sid = self._sitzung()
        for daten in ({"text": "   "}, {}):
            with self.subTest(daten=daten):
                antwort = c.post(f"/api/sitzungen/{sid}/dokumente/einfuegen", json=daten)
                self.assertEqual(antwort.status_code, 422, antwort.text)
                self.assertIn("weder eine Datei noch Text", antwort.json()["fehler"])

    def test_eine_beschaedigte_datei_wird_benannt(self):
        d, c, sid = self._sitzung()
        antwort = c.post(f"/api/sitzungen/{sid}/dokumente/einfuegen",
                         json={"inhalt_b64": "keine gueltige Kodierung!!"})
        self.assertEqual(antwort.status_code, 422)
        self.assertIn("beschädigt", antwort.json()["fehler"])

    def test_ein_dokument_ohne_text_wird_nicht_still_aufgenommen(self):
        d, c, sid = self._sitzung()
        antwort = c.post(f"/api/sitzungen/{sid}/dokumente/einfuegen", json={
            "dateiname": "scan.pdf",
            "inhalt_b64": base64.b64encode(_pdf_leer()).decode()})
        self.assertEqual(antwort.status_code, 422, antwort.text)
        fehler = antwort.json()["fehler"]
        self.assertIn("Texterkennung", fehler)
        # Und der nächste Schritt steht gleich dabei.
        self.assertIn("von Hand einfügen", fehler)

    def test_zu_gross_wird_abgewiesen(self):
        from jusperfect.services.sitzung import Sitzungsdienst

        d, c, sid = self._sitzung()
        zu_viel = b"x" * (Sitzungsdienst.MAX_EINGEFUEGT_BYTES + 1)
        antwort = c.post(f"/api/sitzungen/{sid}/dokumente/einfuegen", json={
            "dateiname": "gross.txt", "inhalt_b64": base64.b64encode(zu_viel).decode()})
        self.assertEqual(antwort.status_code, 422)
        self.assertIn("größer als", antwort.json()["fehler"])

    def test_es_laesst_sich_wieder_herausnehmen(self):
        d, c, sid = self._sitzung()
        eintrag = c.post(f"/api/sitzungen/{sid}/dokumente/einfuegen",
                         json={"titel": "Fax", "text": "Zugestellt."}).json()["eingefuegt"]
        weg = c.delete(f"/api/sitzungen/{sid}/dokumente/{eintrag['dokument_id']}")
        self.assertEqual(weg.status_code, 200)
        self.assertNotIn(eintrag["dokument_id"],
                         [g["dokument_id"] for g in weg.json()["sitzung"]["geladen"]])
        self.assertIsNone(d.speicher.text_lesen(sid, eintrag["dokument_id"]))

    def test_weder_titel_noch_dateiname_gehen_ins_protokoll(self):
        """Beides kann den Namen der Mandantschaft tragen."""
        quelle = (WURZEL / "jusperfect" / "services" / "sitzung.py").read_text(encoding="utf-8")
        block = quelle[quelle.index("def dokument_einfuegen("):quelle.index("def dokument_entfernen(")]
        protokollzeile = block[block.index('ereignis(_log, "dokument_eingefuegt"'):]
        for verboten in ("titel=", "dateiname="):
            self.assertNotIn(verboten, protokollzeile.split(")")[0], verboten)


class DieOberflaecheNimmtEsEntgegen(unittest.TestCase):

    def test_die_klammer_steht_am_eingabefeld(self):
        block = HTML[HTML.index('<form id="frage-form"'):HTML.index('id="schaetzung"')]
        self.assertIn('id="dok-einfuegen"', block)

    def test_der_dialog_bietet_datei_und_text(self):
        block = HTML[HTML.index('<dialog id="einfuegen-dialog"'):HTML.index('<dialog id="entwurf-dialog"')]
        self.assertIn('id="einfuegen-datei"', block)
        self.assertIn('id="einfuegen-text"', block)
        self.assertIn('id="einfuegen-titel"', block)

    def test_der_dialog_sagt_wohin_es_nicht_geht(self):
        """In einer Mandatsakte ist das die wichtigere Hälfte der Auskunft."""
        block = HTML[HTML.index('<dialog id="einfuegen-dialog"'):HTML.index('<dialog id="entwurf-dialog"')]
        self.assertIn("nicht nach jurnodes", block)
        self.assertIn("Aktengedächtnis", block)

    def test_das_band_ueber_dem_dokument_nennt_luecke_und_herkunft(self):
        block = JS[JS.index("function dokumentBand("):JS.index("/** Die Dokumentspalte zeichnen")]
        self.assertIn("seiten_ohne_text", block)
        self.assertIn("eingefuegt", block)
        self.assertIn("kein Text gefunden", block)
        for klasse in (".dok-band-luecke", ".dok-band-herkunft"):
            self.assertIn(klasse, CSS, klasse)

    def test_das_band_haengt_am_dokumenttitel(self):
        """Dort, wo man zu lesen anfängt – nicht in einer Meldung, die nach
        dem nächsten Klick weg ist."""
        block = JS[JS.index("function zeigeDokument("):JS.index("// Die Passage ist bis zu 1.500")]
        self.assertIn("dokumentBand(p.dokument_id)", block)


if __name__ == "__main__":
    unittest.main()
