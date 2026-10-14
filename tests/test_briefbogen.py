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
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
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
        """Eine Fehlermeldung, die nur „fehlt" sagt, hilft niemandem.

        Hier stand eine Prüfung, die sich selbst übersprang, wenn auf dem
        Rechner eine Vorlage lag - und dann grün war, ohne etwas geprüft zu
        haben. Eine Prüfung, die vom Rechner abhängt, auf dem sie läuft, ist
        keine. Jetzt wird der Ort gesetzt, statt ihn vorzufinden.
        """
        with TemporaryDirectory() as ordner:
            alt = briefbogen.orte
            briefbogen.orte = lambda: (Path(ordner) / "gibtesnicht.docx",)
            self.addCleanup(lambda: setattr(briefbogen, "orte", alt))
            with self.assertRaises(BriefbogenFehler) as f:
                briefbogen.erzeugen("Text")
        self.assertIn(briefbogen.DATEINAME, str(f.exception))
        self.assertIn("BRIEFBOGEN-HINTERLEGEN.bat", str(f.exception))


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


class DieSchriftKommtAusDerFormatvorlage(unittest.TestCase):
    """Aus der Kanzlei am 14.10.2026: „Schrift ist Franklin Gothic Book."

    Gelesen wurde bis dahin ``w:docDefaults`` - und dort steht in dieser
    Vorlage Times New Roman. Die Standard-Absatzformatvorlage daneben sagt
    Franklin Gothic Book, zwölf Punkt, und danach setzt Word.

    Die Größe wiegt so schwer wie der Name: Eine Ansicht in zehn statt zwölf
    Punkt zeigt einen Brief, der auf eine Seite passt, obwohl er auf zwei
    geht - und das Abschätzen der Länge ist der Grund für die Ansicht.
    """

    def _vorlage_mit_stilen(self, ordner: str, stile: str) -> Path:
        ort = Path(ordner) / briefbogen.DATEINAME
        with zipfile.ZipFile(ort, "w") as paket:
            paket.writestr("[Content_Types].xml", "<Types/>")
            paket.writestr(briefbogen.RUMPF, RUMPF_XML)
            paket.writestr("word/styles.xml", stile)
        return ort

    def test_die_formatvorlage_gewinnt_gegen_die_docdefaults(self):
        stile = (
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:docDefaults><w:rPrDefault><w:rPr>"
            '<w:rFonts w:ascii="Times New Roman"/><w:sz w:val="20"/>'
            "</w:rPr></w:rPrDefault></w:docDefaults>"
            '<w:style w:type="paragraph" w:default="1" w:styleId="Standard"><w:rPr>'
            '<w:rFonts w:ascii="Franklin Gothic Book"/><w:sz w:val="24"/>'
            "</w:rPr></w:style></w:styles>")
        with TemporaryDirectory() as ordner:
            bild = briefbogen.seitenbild(self._vorlage_mit_stilen(ordner, stile))
        self.assertEqual(bild["grundschrift"]["name"], "Franklin Gothic Book")
        self.assertEqual(bild["grundschrift"]["groesse_pt"], 12.0)

    def test_ohne_formatvorlage_gelten_die_docdefaults(self):
        stile = (
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:docDefaults><w:rPrDefault><w:rPr>"
            '<w:rFonts w:ascii="Times New Roman"/><w:sz w:val="20"/>'
            "</w:rPr></w:rPrDefault></w:docDefaults></w:styles>")
        with TemporaryDirectory() as ordner:
            bild = briefbogen.seitenbild(self._vorlage_mit_stilen(ordner, stile))
        self.assertEqual(bild["grundschrift"]["name"], "Times New Roman")
        self.assertEqual(bild["grundschrift"]["groesse_pt"], 10.0)


class WasSichEinstellenLaesst(unittest.TestCase):
    """Aus der Kanzlei am 14.10.2026: „ob die KI das Schreiben inklusive
    Briefbogen generieren kann, so dass die Vorschau besser anpassbar ist."

    Der Briefbogen bleibt eine Datei. Anpassbar ist, was dazwischen liegt -
    und jeder Wert gilt für die Ansicht **und** für die Word-Datei.
    """

    def setUp(self):
        self._ordner = TemporaryDirectory()
        self.addCleanup(self._ordner.cleanup)
        self.vorlage = _vorlage(self._ordner.name)
        alt = briefbogen.orte
        briefbogen.orte = lambda: (self.vorlage,)
        self.addCleanup(lambda: setattr(briefbogen, "orte", alt))

    def test_ohne_datei_ist_nichts_eingestellt(self):
        self.assertEqual(briefbogen.einstellungen(), briefbogen.EINSTELLUNGEN_LEER)

    def test_die_datei_liegt_neben_dem_briefbogen(self):
        self.assertEqual(briefbogen.einstellungen_ort().parent, self.vorlage.parent)
        self.assertFalse(str(briefbogen.einstellungen_ort()).startswith(
            str(briefbogen.PROGRAMMORDNER) + "/"))

    def test_eingestelltes_kommt_wieder(self):
        briefbogen.einstellungen_speichern(
            {"textbeginn_mm": 100, "schrift": "Arial", "groesse_pt": 11, "zeilenabstand": 1.15})
        self.assertEqual(briefbogen.einstellungen()["schrift"], "Arial")
        bild = briefbogen.seitenbild(self.vorlage)
        self.assertEqual(bild["grundschrift"]["name"], "Arial")
        self.assertEqual(bild["textbeginn_mm"], 100.0)

    def test_die_vorlage_steht_daneben_damit_niemand_raten_muss(self):
        briefbogen.einstellungen_speichern({"schrift": "Arial"})
        bild = briefbogen.seitenbild(self.vorlage)
        self.assertIn("name", bild["aus_vorlage"])
        self.assertNotEqual(bild["aus_vorlage"]["name"], "Arial")

    def test_unsinnige_werte_werden_nicht_uebernommen(self):
        """Ein Textbeginn von 400 mm ergaebe ein leeres Blatt - und eine
        Word-Datei, in der der Brief auf Seite zwei anfaengt."""
        briefbogen.einstellungen_speichern(
            {"textbeginn_mm": 400, "groesse_pt": 200, "zeilenabstand": 0.1})
        gesetzt = briefbogen.einstellungen()
        self.assertIsNone(gesetzt["textbeginn_mm"])
        self.assertIsNone(gesetzt["groesse_pt"])
        self.assertIsNone(gesetzt["zeilenabstand"])

    def test_eine_kaputte_datei_nimmt_nicht_den_briefbogen_mit(self):
        """Dann gilt die Vorlage - der Zustand, in dem alles angefangen hat."""
        briefbogen.einstellungen_ort().write_text("{kein json", encoding="utf-8")
        self.assertEqual(briefbogen.einstellungen(), briefbogen.EINSTELLUNGEN_LEER)
        self.assertTrue(briefbogen.erzeugen("Text", self.vorlage))

    def _rumpf_mit(self, einstellungen: dict) -> str:
        briefbogen.einstellungen_speichern(einstellungen)
        with zipfile.ZipFile(BytesIO(briefbogen.erzeugen("Erste\n\nZweite", self.vorlage))) as p:
            return p.read(briefbogen.RUMPF).decode("utf-8")

    def test_die_word_datei_bekommt_dieselben_werte_wie_die_ansicht(self):
        rumpf = self._rumpf_mit({"textbeginn_mm": 100, "schrift": "Arial",
                                 "groesse_pt": 11, "zeilenabstand": 1.15})
        self.assertIn('w:ascii="Arial"', rumpf)
        self.assertIn('<w:sz w:val="22"/>', rumpf)
        self.assertIn('w:line="276"', rumpf)

    def test_der_erste_absatz_hat_genau_ein_abstandselement(self):
        """Zwei davon sind kein Fehler beim Oeffnen - Word naehme einfach das
        letzte, und der Textbeginn waere lautlos weg."""
        rumpf = self._rumpf_mit({"textbeginn_mm": 100, "zeilenabstand": 1.15})
        erster = rumpf[rumpf.index("<w:body>"):rumpf.index("</w:p>")]
        self.assertEqual(erster.count("<w:spacing"), 1, erster)
        self.assertIn("w:before=", erster)
        self.assertIn("w:line=", erster)

    def test_das_dokument_bleibt_wohlgeformt(self):
        from xml.etree import ElementTree
        ElementTree.fromstring(self._rumpf_mit(
            {"textbeginn_mm": 100, "schrift": "Arial", "groesse_pt": 11, "zeilenabstand": 1.15}))

    def test_ohne_einstellung_steht_nichts_ueberfluessiges_im_dokument(self):
        """Eine Angabe, die dasselbe sagt wie die Formatvorlage, haelt sie
        fest: Aendert die Kanzlei spaeter ihre Schrift, aendert sich der
        Brief dann nicht mit."""
        rumpf = self._rumpf_mit(dict(briefbogen.EINSTELLUNGEN_LEER))
        self.assertNotIn("<w:rFonts", rumpf)
        self.assertNotIn("<w:sz ", rumpf)
        self.assertNotIn("w:line=", rumpf)

    def test_zuruecksetzen_stellt_die_vorlage_wieder_her(self):
        briefbogen.einstellungen_speichern({"schrift": "Arial", "groesse_pt": 11})
        briefbogen.einstellungen_speichern(dict(briefbogen.EINSTELLUNGEN_LEER))
        self.assertEqual(briefbogen.einstellungen(), briefbogen.EINSTELLUNGEN_LEER)


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

    #: Die beiden Stellen, an denen die Kanzlei ausdruecklich etwas ablegt.
    SCHREIBENDE = ("hinterlegen", "einstellungen_speichern")

    def test_im_quelltext_wird_nichts_geschrieben(self):
        """Ausser dort, wo die Kanzlei ausdruecklich etwas ablegt.

        Geschnitten wird nach Funktionen und nicht nach Zeilennummern:
        Kommt eine Funktion dazu, faellt sie auf, statt stillschweigend in
        einen Ausschnitt zu rutschen.
        """
        quelle = (WURZEL / "jusperfect" / "services" / "briefbogen.py").read_text(encoding="utf-8")
        teile = re.split(r"^def ", quelle, flags=re.M)
        uebrig = "".join(t for t in teile[1:]
                         if not t.startswith(self.SCHREIBENDE))
        for verboten in ("write_text(", "write_bytes(", "open(", "mkdir("):
            with self.subTest(verboten=verboten):
                self.assertNotIn(verboten, uebrig)

    def test_die_schreibenden_stellen_sind_genau_diese_zwei(self):
        """Wer eine dritte anlegt, soll es hier begruenden muessen."""
        quelle = (WURZEL / "jusperfect" / "services" / "briefbogen.py").read_text(encoding="utf-8")
        schreibend = [name for name in re.findall(r"^def ([a-z_]+)", quelle, re.M)
                      if re.search(rf"^def {name}\b.*?(?=^def |\Z)", quelle, re.M | re.S)
                      and any(w in re.search(rf"^def {name}\b.*?(?=^def |\Z)", quelle,
                                             re.M | re.S).group(0)
                              for w in ("write_text(", "write_bytes(", "copyfile(",
                                        "NamedTemporaryFile(", "os.replace("))]
        self.assertEqual(sorted(schreibend), sorted(self.SCHREIBENDE))


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
        Gegenseite haetten sie nichts zu suchen.

        **Dieser Test war von Anfang an gruen und prueffte nichts:** Sein
        Beispieltext enthielt keine einzige Belegmarke. Der Entwurf ging bis
        zum 13.10.2026 mitsamt seinen ``[Q: …]`` auf den Briefbogen. Gefunden
        durch die Frage aus der Kanzlei, ob der Entwurf „nicht gleich das
        fertige Schreiben" sein koenne.
        """
        from jusperfect.web import briefbogentext
        blatt = briefbogentext(self._entwurf(
            text="Der Vertrag wurde geschlossen [Q: D1-S1-P1]. "
                 "Mehr steht nicht fest [Q: D2-S1-P1]."))
        self.assertFalse(re.search(r"D\d+-S\d+-P\d+", blatt), blatt)
        self.assertNotIn("[Q:", blatt)
        self.assertIn("Der Vertrag wurde geschlossen.", blatt)

    def test_der_satzbau_bleibt_heil(self):
        """„geschlossen [Q: …]." darf nicht zu „geschlossen ." werden."""
        from jusperfect.web import briefbogentext
        blatt = briefbogentext(self._entwurf(
            text="Der Vertrag wurde geschlossen [Q: D1-S1-P1]."))
        self.assertIn("geschlossen.", blatt)
        self.assertNotIn(" .", blatt)


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


class DasBlattAnsehenOhneWord(unittest.TestCase):
    """Aus der Kanzlei am 13.10.2026: „Kann der Entwurf nicht gleich das
    fertige Schreiben mit Briefkopf angeben? Schließlich muss auch optisch
    zum Teil aktualisiert werden."

    Die Ansicht wird aus der Vorlage GELESEN und nicht nachgezeichnet. Diese
    Prüfungen halten fest, was gelesen wird - und dass der Entwurf im fertigen
    Dokument unter dem Briefkopf anfängt und nicht quer durch ihn.
    """

    def setUp(self):
        self._ordner = TemporaryDirectory()
        self.addCleanup(self._ordner.cleanup)
        self.vorlage = _vorlage(self._ordner.name)

    def test_seitenmass_und_raender_kommen_aus_der_datei(self):
        bild = briefbogen.seitenbild(self.vorlage)
        self.assertAlmostEqual(bild["raender_mm"]["oben"], 25.0, places=1)
        self.assertAlmostEqual(bild["raender_mm"]["links"], 25.0, places=1)

    def test_ohne_vorlage_sagt_die_ansicht_wohin_die_datei_gehoert(self):
        alt = briefbogen.orte
        briefbogen.orte = lambda: (Path(self._ordner.name) / "gibtesnicht.docx",)
        self.addCleanup(lambda: setattr(briefbogen, "orte", alt))
        with self.assertRaises(BriefbogenFehler) as f:
            briefbogen.seitenbild()
        self.assertIn(briefbogen.DATEINAME, str(f.exception))
        self.assertIn("BRIEFBOGEN-HINTERLEGEN.bat", str(f.exception))

    def test_ein_bild_kommt_nur_heraus_wenn_es_im_paket_liegt(self):
        """Sonst waere dieser Weg ein Pfad, den der Browser bestimmt."""
        inhalt, art = briefbogen.bild_lesen("word/media/image1.png", self.vorlage)
        self.assertTrue(inhalt.startswith(b"\x89PNG"))
        self.assertEqual(art, "image/png")
        for versuch in ("../../etc/passwd", "word/document.xml.bak", "/etc/passwd"):
            with self.subTest(versuch=versuch):
                with self.assertRaises(BriefbogenFehler):
                    briefbogen.bild_lesen(versuch, self.vorlage)


class DerEntwurfFaengtUnterDemBriefkopfAn(unittest.TestCase):
    """**Ein Fehler, der erst auf dem Papier aufgefallen waere.**

    ``erzeugen`` ersetzte den leeren Rumpf der Vorlage durch den Entwurf - und
    der begann damit am oberen Rand, also quer durch das Anschriftenfeld, das
    auf einem Briefbogen weit ins Blatt reicht. In Word sieht man das erst,
    wenn man es ausdruckt.

    Der Vorlauf wird jetzt aus dem Briefkopf selbst berechnet: bis unter das
    unterste Stueck, das im Textspalt steht. Eine Falzmarke am Blattrand
    schiebt nichts.
    """

    def _vorlage_mit(self, ordner: str, kopf_xml: str) -> Path:
        ort = Path(ordner) / briefbogen.DATEINAME
        with zipfile.ZipFile(ort, "w") as paket:
            paket.writestr("[Content_Types].xml", "<Types/>")
            paket.writestr(briefbogen.RUMPF, RUMPF_XML)
            paket.writestr("word/_rels/document.xml.rels",
                           '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                           '<Relationship Id="rId7" Type="header" Target="header1.xml"/>'
                           "</Relationships>")
            paket.writestr("word/header1.xml", kopf_xml)
        return ort

    def _kopf(self, x_mm: float, y_mm: float, breite_mm: float, hoehe_mm: float) -> str:
        e = briefbogen.EMU_JE_MM
        return (
            '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:p><w:r><w:drawing><wp:anchor>"
            f'<wp:positionH relativeFrom="page"><wp:posOffset>{int(x_mm * e)}</wp:posOffset></wp:positionH>'
            f'<wp:positionV relativeFrom="page"><wp:posOffset>{int(y_mm * e)}</wp:posOffset></wp:positionV>'
            f'<wp:extent cx="{int(breite_mm * e)}" cy="{int(hoehe_mm * e)}"/>'
            "<w:txbxContent><w:p><w:r><w:t>Anschrift</w:t></w:r></w:p></w:txbxContent>"
            "</wp:anchor></w:drawing></w:r></w:p></w:hdr>")

    def test_ein_anschriftenfeld_im_textspalt_schiebt_den_text_herunter(self):
        with TemporaryDirectory() as ordner:
            # Satzspiegel 25..185 mm; der Kasten reicht bis 110 mm hinunter.
            vorlage = self._vorlage_mit(ordner, self._kopf(120.0, 20.0, 60.0, 90.0))
            bild = briefbogen.seitenbild(vorlage)
        erwartet = 110.0 + briefbogen.ABSTAND_NACH_KOPF_MM - 25.0
        self.assertAlmostEqual(bild["vorlauf_mm"], erwartet, places=0)

    def test_eine_falzmarke_am_blattrand_schiebt_nichts(self):
        with TemporaryDirectory() as ordner:
            vorlage = self._vorlage_mit(ordner, self._kopf(5.0, 99.0, 6.0, 0.0))
            bild = briefbogen.seitenbild(vorlage)
        self.assertEqual(bild["vorlauf_mm"], 0.0)

    def test_der_abstand_steht_als_ein_wert_im_dokument(self):
        """Keine geschaetzten Leerzeilen: Zwei zuviel schieben den Brief auf
        die zweite Seite."""
        with TemporaryDirectory() as ordner:
            vorlage = self._vorlage_mit(ordner, self._kopf(120.0, 20.0, 60.0, 90.0))
            roh = briefbogen.erzeugen("Sehr geehrte Damen und Herren", vorlage)
        with zipfile.ZipFile(BytesIO(roh)) as paket:
            rumpf = paket.read(briefbogen.RUMPF).decode("utf-8")
        treffer = re.search(r'<w:spacing w:before="(\d+)"/>', rumpf)
        self.assertIsNotNone(treffer, rumpf[:600])
        erwartet = round((110.0 + briefbogen.ABSTAND_NACH_KOPF_MM - 25.0) * briefbogen.TWIPS_JE_MM)
        self.assertAlmostEqual(int(treffer.group(1)), erwartet, delta=30)
        self.assertEqual(rumpf.count("<w:spacing"), 1, "Nur der erste Absatz bekommt ihn.")

    def test_ohne_briefkopf_im_textspalt_bleibt_alles_wie_bisher(self):
        with TemporaryDirectory() as ordner:
            vorlage = _vorlage(ordner)
            roh = briefbogen.erzeugen("Sehr geehrte Damen und Herren", vorlage)
        with zipfile.ZipFile(BytesIO(roh)) as paket:
            rumpf = paket.read(briefbogen.RUMPF).decode("utf-8")
        self.assertNotIn("<w:spacing", rumpf)


class UeberDenWeb(unittest.TestCase):
    """Der ganze Weg, so wie die Kanzlei ihn geht.

    Hier stand zuerst nur eine Prüfung auf 404. Das genügte nicht: Der
    erfolgreiche Weg schrieb eine Protokollzeile mit dem Feldnamen
    ``entwurf`` - und der ist verboten (``security/protokoll.py``). Der
    Download hätte in der Kanzlei mit „interner Fehler" geendet, und keine
    Prüfung hätte es gesagt. Seitdem wird der Weg gegangen, nicht nur
    abgewiesen.
    """

    #: Ein belegter Satz - sonst gibt die Belegpflicht den Entwurf nicht aus.
    BELEGT = "Der Sachstand ist festgehalten [Q: D1-S1-P1]."

    def setUp(self):
        import json as _json

        from jusperfect.providers.base import Nutzung, ProviderAntwort
        from tests.hilfen import client, dienste

        self._ordner = TemporaryDirectory()
        self.addCleanup(self._ordner.cleanup)
        self.vorlage = _vorlage(self._ordner.name)
        self._alt = briefbogen.orte
        briefbogen.orte = lambda: (self.vorlage,)     # type: ignore[assignment]
        self.addCleanup(lambda: setattr(briefbogen, "orte", self._alt))

        class _Provider:
            modell_id = "skript"

            def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
                return ProviderAntwort(
                    text=_json.dumps({"betreff": "Egal", "text": UeberDenWeb.BELEGT}),
                    nutzung=Nutzung(1000, 200), modell=self.modell_id)

            def fragen_stream(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
                yield self.fragen(system, material, aufgabe)

        self.c = client(dienste(provider=_Provider()))

    def _entwurf(self):
        sid = self.c.post("/api/sitzungen",
                          json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        self.c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
        antwort = self.c.post(f"/api/sitzungen/{sid}/entwuerfe",
                              json={"art": "rsv", "anweisung": "Deckung anfragen"})
        self.assertEqual(antwort.status_code, 201, antwort.text)
        return antwort.json()

    def test_der_stand_sagt_ob_und_wohin(self):
        daten = self.c.get("/api/briefbogen").json()
        self.assertTrue(daten["vorhanden"])
        self.assertEqual(daten["dateiname"], briefbogen.DATEINAME)

    def test_ein_unbekannter_entwurf_gibt_404(self):
        self.assertEqual(self.c.get("/api/entwuerfe/gibtesnicht/briefbogen").status_code, 404)

    def test_der_entwurf_kommt_als_word_datei_heraus(self):
        e = self._entwurf()
        antwort = self.c.get(f"/api/entwuerfe/{e['id']}/briefbogen")
        self.assertEqual(antwort.status_code, 200, antwort.text[:400])
        self.assertIn("wordprocessingml", antwort.headers["content-type"])
        self.assertIn(".docx", antwort.headers["content-disposition"])
        with zipfile.ZipFile(BytesIO(antwort.content)) as paket:
            self.assertIn("word/header1.xml", paket.namelist())
            rumpf = paket.read(briefbogen.RUMPF).decode("utf-8")
        self.assertIn("Der Sachstand ist festgehalten", rumpf)
        self.assertIn("<w:sectPr>", rumpf)

    def test_ohne_hinterlegten_briefbogen_kommt_kein_serverfehler(self):
        """Sondern der Satz, der sagt, wohin die Datei gehört."""
        briefbogen.orte = lambda: (Path(self._ordner.name) / "gibtesnicht.docx",)  # type: ignore[assignment]
        e = self._entwurf()
        antwort = self.c.get(f"/api/entwuerfe/{e['id']}/briefbogen")
        self.assertEqual(antwort.status_code, 422, antwort.text[:400])
        self.assertIn(briefbogen.DATEINAME, antwort.json()["fehler"])


if __name__ == "__main__":
    unittest.main()
