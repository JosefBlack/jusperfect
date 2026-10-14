"""Aus der Modellsprache wird ein Brief – und zwar in beiden Fassungen gleich.

Aus der Kanzlei am 14.10.2026, nachdem der Briefbogen hinterlegt war:

    „Es gab keinen vernünftigen Text – Formatierungen waren drin – Fußzeile
    wurde überschrieben – keine vernünftige Formatierung."

Zum ersten Mal an einem **gedruckten Blatt** nachgesehen (LibreOffice setzt
die Word-Datei, das Ergebnis als Bild). Drei Befunde, alle eindeutig:

1. **Das Modell schreibt Markdown.** ``**Unser Zeichen:**``,
   ``## Zum Unfallhergang``, ``- Reparaturkosten``, ``---``. Im Programm setzt
   ``antworttext`` das um; die Word-Datei bekam die Zeichen roh. Auf dem
   Briefbogen der Kanzlei stand dann wörtlich ``## Zum Unfallhergang``.
2. **Der Text stand auf der Fußzeile.** Der Satzspiegel endet auf diesem
   Briefbogen bei 271,6 mm, die Fußzeile beginnt bei 272,5 mm.
3. **Der Hinweisblock schob den Brief auf eine zweite Seite**, auf der dann
   drei Zeilen interner Vermerk unter dem vollständigen Briefkopf standen.

Die wichtigste Prüfung in dieser Datei ist die letzte: Die Ansicht im
Programm und die Word-Datei müssen dieselbe Lesart haben. Eine Vorschau, die
anders gliedert als das Papier, ist schlimmer als gar keine.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from jusperfect.services import briefbogen
from jusperfect.services.briefbogen import briefzeile

from tests.test_briefbogen import RUMPF_XML, _vorlage

WURZEL = Path(__file__).resolve().parent.parent

#: Was Modelle wirklich schreiben - und wie es gelesen werden muss.
FAELLE = [
    "**Unser Zeichen:** 42/26 VU",
    "## Zum Unfallhergang",
    "### Kleiner",
    "# Gross",
    "- Reparaturkosten netto: 4.812,00 EUR",
    "* Mit Stern",
    "• Mit Punkt",
    "1. Erstens",
    "12) Zwoelftens",
    "---",
    "***",
    "___",
    "Normaler *kursiver* Satz.",
    "Mit __fett__ und _nichts_ dazwischen.",
    "Ein ** halber Stern und 3*4 = 12.",
    "",
    "   ",
    "Nur Text",
    "**Alles fett**",
    "- **Fetter Punkt** mit Rest",
]


class MarkdownWirdFormatierung(unittest.TestCase):
    def test_sternchen_werden_fett(self):
        bauplan = briefzeile("**Unser Zeichen:** 42/26 VU")
        self.assertEqual(bauplan["stuecke"][0], ("Unser Zeichen:", True, False))
        self.assertEqual(bauplan["stuecke"][1], (" 42/26 VU", False, False))

    def test_rauten_werden_ueberschriften(self):
        for roh in ("# Gross", "## Mittel", "### Klein"):
            with self.subTest(roh=roh):
                self.assertEqual(briefzeile(roh)["art"], "ueberschrift")

    def test_striche_werden_aufzaehlungspunkte(self):
        bauplan = briefzeile("- Reparaturkosten netto: 4.812,00 EUR")
        self.assertEqual(bauplan["art"], "punkt")
        self.assertTrue(bauplan["einzug"])
        self.assertIn("•", bauplan["stuecke"][0][0])

    def test_die_nummer_bleibt_stehen(self):
        """Sie kann gemeint sein - eine Position, ein Antrag, ein Absatz."""
        self.assertIn("1.", briefzeile("1. Erstens")["stuecke"][0][0])

    def test_trennlinien_entfallen(self):
        for roh in ("---", "***", "___", "- - -"):
            with self.subTest(roh=roh):
                self.assertIsNone(briefzeile(roh))

    def test_fett_vor_kursiv(self):
        """Ginge kursiv zuerst, fraesse es die inneren Sternchen von **fett**
        und liesse zwei einzelne stehen."""
        stuecke = briefzeile("**Alles fett**")["stuecke"]
        self.assertEqual(stuecke, [("Alles fett", True, False)])

    def test_ein_einzelner_stern_bleibt_text(self):
        """„3*4 = 12" ist keine Formatierung."""
        stuecke = briefzeile("Ein ** halber Stern und 3*4 = 12.")["stuecke"]
        self.assertEqual("".join(w for w, _, _ in stuecke), "Ein ** halber Stern und 3*4 = 12.")

    def test_leere_zeilen_bleiben_leer(self):
        for roh in ("", "   "):
            with self.subTest(roh=roh):
                self.assertEqual(briefzeile(roh)["art"], "leer")


class DieWordDateiTraegtEsAlsFormat(unittest.TestCase):
    def setUp(self):
        self._ordner = TemporaryDirectory()
        self.addCleanup(self._ordner.cleanup)
        self.vorlage = _vorlage(self._ordner.name)
        alt = briefbogen.orte
        briefbogen.orte = lambda: (self.vorlage,)
        self.addCleanup(lambda: setattr(briefbogen, "orte", alt))

    def _rumpf(self, text: str) -> str:
        with zipfile.ZipFile(BytesIO(briefbogen.erzeugen(text, self.vorlage))) as paket:
            return paket.read(briefbogen.RUMPF).decode("utf-8")

    def test_kein_markdown_mehr_im_dokument(self):
        """Auf dem Briefbogen stand woertlich „## Zum Unfallhergang"."""
        rumpf = self._rumpf("## Zum Unfallhergang\n\n**Fett** und *kursiv*.\n\n- Punkt\n\n---")
        for zeichen in ("##", "**", "---"):
            with self.subTest(zeichen=zeichen):
                self.assertNotIn(zeichen, rumpf)
        self.assertIn("Zum Unfallhergang", rumpf)

    def test_fett_wird_fett(self):
        self.assertIn("<w:b/>", self._rumpf("**Unser Zeichen:** 42/26"))

    def test_kursiv_wird_kursiv(self):
        self.assertIn("<w:i/>", self._rumpf("Ein *kursiver* Satz."))

    def test_die_ueberschrift_bekommt_luft_davor(self):
        """Damit ein Abschnitt als einer zu sehen ist."""
        self.assertIn('<w:spacing w:before="200"/>', self._rumpf("Text\n\n## Abschnitt"))

    def test_der_punkt_bekommt_einzug(self):
        self.assertIn('<w:ind w:left="340"/>', self._rumpf("- Ein Punkt"))

    def test_das_dokument_bleibt_wohlgeformt(self):
        from xml.etree import ElementTree
        ElementTree.fromstring(self._rumpf(
            "## Überschrift\n\n**Fett** & *kursiv* <spitz>\n\n- Punkt\n\n---\n\nEnde"))


class DerTextStehtNichtAufDerFusszeile(unittest.TestCase):
    """„Fußzeile wurde überschrieben."

    Der Unterrand wird aus der Fußzeile gerechnet, wie der Vorlauf aus dem
    Kopf: bis über ihr oberstes Stück, plus Luft.
    """

    def _vorlage_mit_fuss(self, ordner: str, y_mm: float) -> Path:
        e = briefbogen.EMU_JE_MM
        fuss = (
            '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:p><w:r><w:drawing><wp:anchor>"
            f'<wp:positionH relativeFrom="page"><wp:posOffset>{int(20 * e)}</wp:posOffset></wp:positionH>'
            f'<wp:positionV relativeFrom="page"><wp:posOffset>{int(y_mm * e)}</wp:posOffset></wp:positionV>'
            f'<wp:extent cx="{int(30 * e)}" cy="{int(12 * e)}"/>'
            '<a:blip r:embed="rId1"/>'
            "</wp:anchor></w:drawing></w:r></w:p></w:ftr>")
        ort = Path(ordner) / briefbogen.DATEINAME
        with zipfile.ZipFile(ort, "w") as paket:
            paket.writestr("[Content_Types].xml", "<Types/>")
            paket.writestr(briefbogen.RUMPF,
                           RUMPF_XML.replace("<w:sectPr>",
                                             '<w:sectPr><w:footerReference w:type="default" r:id="rId8"/>'))
            paket.writestr("word/_rels/document.xml.rels",
                           '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                           '<Relationship Id="rId8" Type="footer" Target="footer1.xml"/></Relationships>')
            paket.writestr("word/footer1.xml", fuss)
            paket.writestr("word/_rels/footer1.xml.rels",
                           '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                           '<Relationship Id="rId1" Type="image" Target="media/image1.png"/></Relationships>')
            paket.writestr("word/media/image1.png", b"\x89PNG\r\n\x1a\n")
        return ort

    def test_eine_hohe_fusszeile_hebt_den_unterrand(self):
        with TemporaryDirectory() as ordner:
            vorlage = self._vorlage_mit_fuss(ordner, 260.0)
            bild = briefbogen.seitenbild(vorlage)
        # Seite 297, Fusszeile beginnt bei 260 -> 37 + 6 Luft.
        self.assertAlmostEqual(bild["raender_mm"]["unten_noetig"], 43.0, places=0)

    def test_eine_niedrige_fusszeile_laesst_den_rand_wie_er_ist(self):
        """Nur vergroessert, nie verkleinert."""
        with TemporaryDirectory() as ordner:
            vorlage = self._vorlage_mit_fuss(ordner, 290.0)
            bild = briefbogen.seitenbild(vorlage)
        self.assertEqual(bild["raender_mm"]["unten_noetig"], bild["raender_mm"]["unten"])

    def test_der_wert_steht_in_der_word_datei(self):
        with TemporaryDirectory() as ordner:
            vorlage = self._vorlage_mit_fuss(ordner, 260.0)
            roh = briefbogen.erzeugen("Text", vorlage)
        with zipfile.ZipFile(BytesIO(roh)) as paket:
            rumpf = paket.read(briefbogen.RUMPF).decode("utf-8")
        treffer = re.search(r'<w:pgMar[^>]*w:bottom="(\d+)"', rumpf)
        self.assertIsNotNone(treffer, rumpf[-400:])
        self.assertAlmostEqual(int(treffer.group(1)) / briefbogen.TWIPS_JE_MM, 43.0, places=0)

    def test_sonst_bleibt_der_abschnittsblock_zeichen_fuer_zeichen(self):
        """Das ist der einzige Eingriff - Kopf- und Fusszeilenverweise,
        Seitenmass und die erste Seite bleiben."""
        with TemporaryDirectory() as ordner:
            vorlage = self._vorlage_mit_fuss(ordner, 260.0)
            alt = zipfile.ZipFile(vorlage).read(briefbogen.RUMPF).decode("utf-8")
            roh = briefbogen.erzeugen("Text", vorlage)
        with zipfile.ZipFile(BytesIO(roh)) as paket:
            neu = paket.read(briefbogen.RUMPF).decode("utf-8")
        alt_sect = alt[alt.rfind("<w:sectPr"):alt.index("</w:body>")]
        neu_sect = neu[neu.rfind("<w:sectPr"):neu.index("</w:body>")]
        ohne = lambda roh: re.sub(r"\s{2,}", " ", re.sub(r'\s*w:bottom="\d+"', "", roh))
        self.assertEqual(ohne(alt_sect), ohne(neu_sect))


class DieHinweiseGehenNichtVerloren(unittest.TestCase):
    """Sie stehen nicht mehr im Brief - also müssen sie woanders stehen."""

    JS = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")

    def test_das_vorschaufenster_zeigt_sie_ueber_dem_entwurf(self):
        block = self.JS[self.JS.index("function entwurfFensterZeichnen"):
                        self.JS.index("function entwurfAnsichtWahl")]
        self.assertIn("hinweiseBlock(", block)

    def test_die_meldung_beim_herunterladen_nennt_sie(self):
        block = self.JS[self.JS.index("async function briefbogenHolen"):]
        block = block[:block.index("\n}")]
        self.assertIn("Belegprüfung", block)
        self.assertIn("nicht im Schreiben", block)


class DieAnsichtLiestWieDasBlatt(unittest.TestCase):
    """Die wichtigste Prüfung hier.

    ``briefzeile`` gibt es zweimal: in ``services/briefbogen.py`` für die
    Word-Datei und in ``static/app.js`` für die Blattansicht. Zwei Fassungen
    derselben Regel laufen auseinander, sobald eine davon geändert wird - und
    dann zeigt die Vorschau etwas anderes, als auf dem Papier steht.

    Hier wird die Fassung aus der Oberfläche wirklich ausgeführt und mit der
    aus dem Programm verglichen. Ohne Node lässt sich das nicht messen; dann
    sagt die Prüfung das, statt grün zu sein.
    """

    def test_beide_fassungen_lesen_dieselben_zeilen_gleich(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node ist auf diesem Rechner nicht vorhanden; "
                          "die Fassung aus der Oberflaeche laesst sich nicht ausfuehren.")
        js = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")
        anfang = js.index("const BRIEF_UEBERSCHRIFT")
        ende = js.index("/** Eine Briefzeile als Element")
        programm = js[anfang:ende] + (
            "\nconst faelle = " + json.dumps(FAELLE, ensure_ascii=False) + ";\n"
            "console.log(JSON.stringify(faelle.map(briefzeile)));\n")
        with TemporaryDirectory() as ordner:
            datei = Path(ordner) / "probe.js"
            datei.write_text(programm, encoding="utf-8")
            lauf = subprocess.run([node, str(datei)], capture_output=True, text=True, timeout=60)
        self.assertEqual(lauf.returncode, 0, lauf.stderr)
        aus_der_oberflaeche = json.loads(lauf.stdout)

        for roh, dort in zip(FAELLE, aus_der_oberflaeche):
            hier = briefzeile(roh)
            with self.subTest(zeile=roh):
                if hier is None:
                    self.assertIsNone(dort)
                    continue
                self.assertIsNotNone(dort, f"Die Oberflaeche laesst {roh!r} entfallen.")
                self.assertEqual(hier["art"], dort["art"])
                self.assertEqual(hier["einzug"], dort["einzug"])
                self.assertEqual([list(s) for s in hier["stuecke"]], dort["stuecke"])


if __name__ == "__main__":
    unittest.main()
