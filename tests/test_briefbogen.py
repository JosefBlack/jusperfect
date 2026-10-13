"""Der Entwurf auf dem Briefbogen der Kanzlei.

Aus der Kanzlei am 13.10.2026:

    „Entwurf-Funktion funktioniert noch nicht, jur|nodes lehnt ab, was ich
    erstmal nicht so schlimm finde. Koennen wir hier einen Briefbogen
    hinterlegen?"

Dazu kam die Briefbogen-Datei: ein Word-Dokument mit Kopf- und Fusszeilen,
Logo, Schriften, Raendern - und einem leeren Rumpf.

Der Briefbogen wird deshalb **benutzt und nicht nachgebaut**. Was diese
Pruefungen festhalten:

1. Jede andere Datei des Pakets bleibt Byte fuer Byte, wie sie war - Bilder,
   Kopfzeilen, Fusszeilen, Schriften.
2. ``w:sectPr`` bleibt stehen. In ihm stehen die Verweise auf Kopf- und
   Fusszeilen. Faellt er weg, kommt ein weisses Blatt mit richtigem Text
   heraus - ein Fehler, den man am Bildschirm kaum sieht und auf dem Papier
   nicht mehr heilen kann.
3. Spitze Klammern und kaufmaennische Und aus dem Entwurf werden escaped.
   Ein einziges rohes ``&`` macht die Datei fuer Word unlesbar.
4. Die Vorlage liegt ausserhalb des Programmordners (wie Sperrliste und
   Promptbibliothek, Befund N01).
5. Es wird nichts auf die Platte geschrieben.
"""

from __future__ import annotations

import re
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from jusperfect.services import briefbogen
from jusperfect.services.briefbogen import BriefbogenFehler

WURZEL = Path(__file__).resolve().parent.parent

#: Ein Briefbogen im Kleinen: ein Rumpf aus leeren Absaetzen, ein sectPr mit
#: Verweis auf eine Kopfzeile, und ein Bild, das unberuehrt bleiben muss.
RUMPF_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    "<w:body>"
    "<w:p/><w:p/><w:p/>"
    '<w:sectPr><w:headerReference w:type="default" r:id="rId7"/>'
    '<w:pgMar w:top="1417" w:left="1417"/></w:sectPr>'
    "</w:body></w:document>"
)


def _vorlage(ordner: str, name: str = briefbogen.DATEINAME) -> Path:
    ort = Path(ordner) / name
    with zipfile.ZipFile(ort, "w") as paket:
        paket.writestr("[Content_Types].xml", "<Types/>")
        paket.writestr(briefbogen.RUMPF, RUMPF_XML)
        paket.writestr("word/header1.xml", "<w:hdr>Kanzleikopf</w:hdr>")
        paket.writestr("word/media/image1.png", b"\x89PNG\r\n\x1a\n-nicht-echt-")
    return ort


class DieVorlageLiegtAusserhalb(unittest.TestCase):
    def test_kein_ort_liegt_im_programmordner(self):
        """Der Briefbogen der Kanzlei hat in keiner ZIP etwas zu suchen."""
        for ort in briefbogen.orte():
            self.assertFalse(
                str(ort).startswith(str(briefbogen.PROGRAMMORDNER) + "/"),
                f"{ort} liegt im Programmordner")

    def test_ohne_vorlage_sagt_die_meldung_wohin_sie_gehoert(self):
        """Eine Fehlermeldung, die nur „fehlt" sagt, hilft niemandem."""
        with self.assertRaises(BriefbogenFehler) as f:
            briefbogen.erzeugen("Text", None) if briefbogen.finden() is None else None
            raise BriefbogenFehler("übersprungen: auf diesem Rechner liegt eine Vorlage")
        self.assertIn(briefbogen.DATEINAME, str(f.exception))


class DerBriefbogenBleibtUnberuehrt(unittest.TestCase):
    def setUp(self):
        self._ordner = TemporaryDirectory()
        self.addCleanup(self._ordner.cleanup)
        self.vorlage = _vorlage(self._ordner.name)

    def _erzeugen(self, text: str) -> zipfile.ZipFile:
        return zipfile.ZipFile(BytesIO(briefbogen.erzeugen(text, self.vorlage)))

    def test_alle_dateien_sind_noch_da(self):
        with zipfile.ZipFile(self.vorlage) as alt, self._erzeugen("Hallo") as neu:
            self.assertEqual(alt.namelist(), neu.namelist())

    def test_kopfzeile_und_bild_bleiben_byte_fuer_byte(self):
        with zipfile.ZipFile(self.vorlage) as alt, self._erzeugen("Hallo") as neu:
            for name in ("word/header1.xml", "word/media/image1.png", "[Content_Types].xml"):
                with self.subTest(name=name):
                    self.assertEqual(alt.read(name), neu.read(name))

    def test_der_abschnittsblock_bleibt_stehen(self):
        """In ihm stehen Kopfzeile und Randmasse. Ohne ihn ein weisses Blatt."""
        with self._erzeugen("Hallo") as neu:
            rumpf = neu.read(briefbogen.RUMPF).decode("utf-8")
        self.assertIn("<w:sectPr>", rumpf)
        self.assertIn('w:headerReference', rumpf)
        self.assertIn('w:pgMar', rumpf)

    def test_der_abschnittsblock_steht_am_ende_des_rumpfes(self):
        """An jeder anderen Stelle gilt er nicht fuer das ganze Dokument."""
        with self._erzeugen("Hallo") as neu:
            rumpf = neu.read(briefbogen.RUMPF).decode("utf-8")
        self.assertLess(rumpf.index("Hallo"), rumpf.index("<w:sectPr>"))
        self.assertLess(rumpf.index("<w:sectPr>"), rumpf.index("</w:body>"))

    def test_die_leeren_absaetze_der_vorlage_weichen_dem_text(self):
        with self._erzeugen("Hallo") as neu:
            rumpf = neu.read(briefbogen.RUMPF).decode("utf-8")
        koerper = rumpf[rumpf.index("<w:body>"):rumpf.index("<w:sectPr>")]
        self.assertEqual(koerper.count("<w:p/>"), 0, koerper)


class DerTextKommtAnWieErIst(unittest.TestCase):
    def setUp(self):
        self._ordner = TemporaryDirectory()
        self.addCleanup(self._ordner.cleanup)
        self.vorlage = _vorlage(self._ordner.name)

    def _rumpf(self, text: str) -> str:
        with zipfile.ZipFile(BytesIO(briefbogen.erzeugen(text, self.vorlage))) as paket:
            return paket.read(briefbogen.RUMPF).decode("utf-8")

    def test_jede_zeile_wird_ein_absatz(self):
        rumpf = self._rumpf("Erste Zeile\nZweite Zeile")
        self.assertEqual(rumpf.count("<w:t"), 2)
        self.assertIn("Erste Zeile", rumpf)
        self.assertIn("Zweite Zeile", rumpf)

    def test_leerzeilen_bleiben_leerzeilen(self):
        """Ein Brief ohne Absaetze ist keiner."""
        self.assertIn("<w:p/>", self._rumpf("Oben\n\nUnten"))

    def test_kaufmaennisches_und_macht_die_datei_nicht_kaputt(self):
        """Ein rohes & genuegt, und Word meldet nur „beschaedigt"."""
        rumpf = self._rumpf("Meier & Sohn <GmbH>")
        self.assertIn("Meier &amp; Sohn &lt;GmbH&gt;", rumpf)
        self.assertNotIn("Meier & Sohn", rumpf)

    def test_das_dokument_bleibt_wohlgeformtes_xml(self):
        from xml.etree import ElementTree
        roh = self._rumpf('Ein "Zitat" & <Klammern> und ein   Leerzeichen')
        # r: ist in der kleinen Vorlage nicht deklariert; fuer die Pruefung der
        # Wohlgeformtheit genuegt es, den Namensraum nachzureichen.
        roh = roh.replace("<w:document ",
                          '<w:document xmlns:r="http://x/" ', 1)
        ElementTree.fromstring(roh)

    def test_steuerzeichen_werden_entfernt(self):
        """XML 1.0 kennt sie nicht; eines davon macht die Datei unlesbar."""
        self.assertNotIn("\x07", self._rumpf("Vor\x07Nach"))

    def test_zeilenumbrueche_aus_windows_zaehlen_einmal(self):
        self.assertEqual(self._rumpf("Eins\r\nZwei").count("<w:t"), 2)

    def test_leerraum_am_zeilenanfang_bleibt(self):
        """Eine Einrueckung im Entwurf ist Absicht."""
        self.assertIn('xml:space="preserve"', self._rumpf("    eingerückt"))


class EineUnbrauchbareVorlage(unittest.TestCase):
    def setUp(self):
        self._ordner = TemporaryDirectory()
        self.addCleanup(self._ordner.cleanup)

    def test_keine_zip_datei(self):
        ort = Path(self._ordner.name) / briefbogen.DATEINAME
        ort.write_text("Das ist ein Word-Dokument von 1997.", encoding="utf-8")
        with self.assertRaises(BriefbogenFehler) as f:
            briefbogen.erzeugen("Text", ort)
        self.assertIn("als .docx speichern", str(f.exception))

    def test_zip_ohne_dokumentrumpf(self):
        ort = Path(self._ordner.name) / briefbogen.DATEINAME
        with zipfile.ZipFile(ort, "w") as paket:
            paket.writestr("irgendwas.txt", "nichts")
        with self.assertRaises(BriefbogenFehler):
            briefbogen.erzeugen("Text", ort)

    def test_rumpf_ohne_body(self):
        ort = Path(self._ordner.name) / briefbogen.DATEINAME
        with zipfile.ZipFile(ort, "w") as paket:
            paket.writestr(briefbogen.RUMPF, "<w:document/>")
        with self.assertRaises(BriefbogenFehler) as f:
            briefbogen.erzeugen("Text", ort)
        self.assertIn("w:body", str(f.exception))

    def test_hinterlegen_prueft_vorher(self):
        """Eine Vorlage, die erst beim ersten Entwurf auffaellt, faellt zur
        unguenstigsten Zeit auf."""
        quelle = Path(self._ordner.name) / "unbrauchbar.docx"
        quelle.write_text("kein docx", encoding="utf-8")
        ziel = Path(self._ordner.name) / briefbogen.DATEINAME
        with self.assertRaises(BriefbogenFehler):
            briefbogen.hinterlegen(quelle, ziel)
        self.assertFalse(ziel.exists(), "Unbrauchbares wird nicht abgelegt.")

    def test_hinterlegen_legt_eine_brauchbare_ab(self):
        quelle = _vorlage(self._ordner.name, "original.docx")
        ziel = Path(self._ordner.name) / briefbogen.DATEINAME
        self.assertEqual(briefbogen.hinterlegen(quelle, ziel), ziel)
        self.assertEqual(ziel.read_bytes(), quelle.read_bytes())


class DasProgrammSchreibtNichts(unittest.TestCase):
    """„Das Programm schreibt nicht. Keine Datei, kein Vermerk, kein Ordner."""

    def test_erzeugen_legt_nichts_an(self):
        with TemporaryDirectory() as ordner:
            vorlage = _vorlage(ordner)
            vorher = sorted(p.name for p in Path(ordner).iterdir())
            briefbogen.erzeugen("Ein langer Entwurf\n\nmit Absätzen", vorlage)
            self.assertEqual(sorted(p.name for p in Path(ordner).iterdir()), vorher)

    def test_die_vorlage_bleibt_unveraendert(self):
        with TemporaryDirectory() as ordner:
            vorlage = _vorlage(ordner)
            vorher = vorlage.read_bytes()
            briefbogen.erzeugen("Text", vorlage)
            self.assertEqual(vorlage.read_bytes(), vorher)

    def test_im_quelltext_wird_nichts_geschrieben(self):
        """Ausser in hinterlegen, wo die Kanzlei es ausdruecklich will."""
        quelle = (WURZEL / "jusperfect" / "services" / "briefbogen.py").read_text(encoding="utf-8")
        ohne_hinterlegen = quelle[:quelle.index("def hinterlegen")] + \
            quelle[quelle.index("def _rumpf_lesen"):]
        for verboten in ("write_text(", "write_bytes(", "open(", "mkdir("):
            with self.subTest(verboten=verboten):
                self.assertNotIn(verboten, ohne_hinterlegen)


class WasAufDemBlattSteht(unittest.TestCase):
    """Die Hinweise der Belegpruefung gehoeren mit aufs Papier."""

    def _entwurf(self, **extra):
        from types import SimpleNamespace
        daten = {"id": "E-1", "betreff": "Ihr Schreiben", "text": "Sehr geehrte Damen und Herren,",
                 "hinweise": [], "quellen": []}
        daten.update(extra)
        return SimpleNamespace(**daten)

    def test_betreff_und_text_stehen_drauf(self):
        from jusperfect.web import briefbogentext
        blatt = briefbogentext(self._entwurf())
        self.assertIn("Ihr Schreiben", blatt)
        self.assertIn("Sehr geehrte Damen und Herren,", blatt)

    def test_zurueckgehaltenes_steht_drauf(self):
        """Ein Entwurf, dem eine Aussage fehlt, sieht sonst aus wie ein
        fertiger Brief - und genau so wuerde er unterschrieben."""
        from jusperfect.web import briefbogentext
        blatt = briefbogentext(self._entwurf(
            hinweise=["2 Aussagen wurden ohne belastbaren Beleg entfernt."]))
        self.assertIn("ohne belastbaren Beleg entfernt", blatt)
        self.assertIn("nicht Teil des Schreibens", blatt)

    def test_ohne_hinweise_steht_kein_leerer_block_drauf(self):
        from jusperfect.web import briefbogentext
        self.assertNotIn("---", briefbogentext(self._entwurf()))

    def test_die_fundstellen_kommen_nicht_mit(self):
        """Sie sind der Weg zum Beleg im Programm. In einem Schreiben an die
        Gegenseite haetten sie nichts zu suchen."""
        from jusperfect.web import briefbogentext
        blatt = briefbogentext(self._entwurf(text="Der Vertrag wurde geschlossen."))
        self.assertFalse(re.search(r"D\d+-S\d+-P\d+", blatt), blatt)


class DerGefuehrteWeg(unittest.TestCase):
    """Ein Nichtprogrammierer soll keine Datei an einen abgezaehlten Pfad
    kopieren muessen."""

    def test_es_gibt_eine_bat_die_dorthin_fuehrt(self):
        bat = WURZEL / "BRIEFBOGEN-HINTERLEGEN.bat"
        self.assertTrue(bat.is_file())
        inhalt = bat.read_text(encoding="utf-8")
        self.assertIn("jusperfect.services.briefbogen", inhalt)

    def test_die_bat_sagt_warum_die_datei_nicht_in_den_ordner_gehoert(self):
        inhalt = (WURZEL / "BRIEFBOGEN-HINTERLEGEN.bat").read_text(encoding="utf-8")
        self.assertIn("NEBEN dem Programmordner", inhalt)

    def test_der_knopf_steht_am_entwurf(self):
        js = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("Auf Briefbogen (Word)", js)
        self.assertIn("briefbogenHolen", js)

    def test_die_datei_wird_nicht_vom_programm_gespeichert(self):
        """Der Browser fragt, wohin. Das Programm schreibt nichts."""
        js = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")
        block = js[js.index("async function briefbogenHolen"):]
        block = block[:block.index("// ── Aus einer Anweisung")]
        self.assertIn("a.download", block)
        self.assertIn("revokeObjectURL", block)


class UeberDenWeb(unittest.TestCase):
    def setUp(self):
        from tests.hilfen import client, dienste

        self._ordner = TemporaryDirectory()
        self.addCleanup(self._ordner.cleanup)
        self.vorlage = _vorlage(self._ordner.name)
        self._alt = briefbogen.orte
        briefbogen.orte = lambda: (self.vorlage,)     # type: ignore[assignment]
        self.addCleanup(lambda: setattr(briefbogen, "orte", self._alt))
        self.c = client(dienste())

    def test_der_stand_sagt_ob_und_wohin(self):
        daten = self.c.get("/api/briefbogen").json()
        self.assertTrue(daten["vorhanden"])
        self.assertEqual(daten["dateiname"], briefbogen.DATEINAME)

    def test_ein_unbekannter_entwurf_gibt_404(self):
        self.assertEqual(self.c.get("/api/entwuerfe/gibtesnicht/briefbogen").status_code, 404)


if __name__ == "__main__":
    unittest.main()
