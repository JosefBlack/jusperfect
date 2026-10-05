"""Ein einzelnes Dokument aus dem Aktengedächtnis nehmen – mit Ansage.

Aus der Kanzlei am 05.10.2026, nach der Ausschlussliste: „Ja, bau das
Entfernen einzelner Dokumente aus dem Gedächtnis."

Der Dienst dahinter steht seit Längerem und ist in
``tests/test_gedaechtnis_nummern.py`` und ``tests/test_abschluss.py``
gemessen. Was fehlte, war der Weg dorthin: Bis zum 05.10.2026 gab es nur
``GEDAECHTNIS-LEEREN.bat`` — alles oder nichts. Wer ein einziges Dokument
heraushaben wollte, zahlte das Einlesen der ganzen Akte noch einmal.

Diese Datei hält zwei Dinge fest:

* **Die Rückfrage zählt, sie schätzt nicht.** Entfernen lässt sich nicht
  rückgängig machen; eine Rückfrage, die „vermutlich einiges" sagt, hilft bei
  der Entscheidung nicht.
* **Die Oberfläche zählt nach derselben Regel wie der Dienst.** Eine
  Rückfrage, die weniger ankündigt, als hinterher fehlt, ist schlimmer als
  gar keine.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from jusperfect.domain.models import (
    Aktengedaechtnis, ChronologieEintrag, GedaechtnisAntwort, GedaechtnisDokument,
    Quelle, Seite,
)
from tests.hilfen import dienste, einstellungen

AKTE = "AR-2026-0115"
STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"
APP = (STATISCH / "app.js").read_text(encoding="utf-8")
CSS = (STATISCH / "styles.css").read_text(encoding="utf-8")
HTML = (STATISCH / "index.html").read_text(encoding="utf-8")


def _quelle(kennung: str, dokument_id: str) -> Quelle:
    return Quelle(kennung=kennung, dokument_id=dokument_id, dokument_titel="Schreiben",
                  seite=1, zitat="…")


def _block(name: str) -> str:
    treffer = re.search(r"function " + name + r"\(.*?\) \{(.*?)\n\}", APP, re.S)
    assert treffer, f"Funktion {name} nicht gefunden"
    return treffer.group(1)


class EineRundeFaelltGanz(unittest.TestCase):
    """Zitiert eine gespeicherte Antwort zwei Dokumente, fällt sie bei beiden.

    Das ist strenger als nötig und Absicht: Eine Antwort, die aus zwei Quellen
    zusammengesetzt wurde, stünde sonst weiter da, obwohl die Hälfte ihrer
    Grundlage fehlt. Die Rückfrage in der Oberfläche muss deshalb nach genau
    derselben Regel zählen — sonst kündigt sie weniger an, als hinterher fehlt.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal",
                          JUSPERFECT_GEDAECHTNIS_PFAD=self._tmp.name)
        self.dienst = dienste(einstellungen=e).gedaechtnis
        g = Aktengedaechtnis(
            akte_id=AKTE, aktenzeichen="115/26 AR", bezeichnung="Test",
            dokumente=[
                GedaechtnisDokument(dokument_id=f"D-{nr:03d}", titel=f"Schreiben {nr}",
                                    nummer=nr, seiten=[Seite(nummer=1, text=f"Inhalt {nr}")])
                for nr in (1, 2)
            ],
            letzte_dokumentnummer=2,
            fragen_antworten=[
                GedaechtnisAntwort(frage="Aus zwei Quellen?",
                                   antwort="Ja. [Q: D1-S1-P1] [Q: D2-S1-P1]",
                                   quellen=[_quelle("D1-S1-P1", "D-001"),
                                            _quelle("D2-S1-P1", "D-002")]),
                GedaechtnisAntwort(frage="Nur aus dem zweiten?", antwort="Ja. [Q: D2-S1-P1]",
                                   quellen=[_quelle("D2-S1-P1", "D-002")]),
            ],
            chronologie=[
                ChronologieEintrag(datum="2026-05-04", ereignis="Aus zwei Quellen",
                                   quellen=[_quelle("D1-S1-P1", "D-001"),
                                            _quelle("D2-S1-P1", "D-002")]),
                ChronologieEintrag(datum="2026-05-06", ereignis="Nur aus dem zweiten",
                                   quellen=[_quelle("D2-S1-P1", "D-002")]),
            ],
        )
        self.dienst.ablegen(g)
        self.dienst.lesen(AKTE)

    def test_der_dienst_wirft_die_mitzitierende_runde_ganz_weg(self):
        g = self.dienst.dokument_vergessen(AKTE, "D-001")
        self.assertEqual([r.frage for r in g.fragen_antworten], ["Nur aus dem zweiten?"])

    def test_und_den_mitzitierenden_zeitstrahleintrag_auch(self):
        g = self.dienst.dokument_vergessen(AKTE, "D-001")
        self.assertEqual([x.ereignis for x in g.chronologie], ["Nur aus dem zweiten"])

    def test_die_oberflaeche_zaehlt_mit_some_nicht_mit_every(self):
        """`some` heißt „zitiert mit", `every` hieße „zitiert nur".

        Mit `every` hätte die Rückfrage hier 0 Fragen angekündigt und eine
        entfernt. Genau das soll nicht geschehen.
        """
        block = _block("gedaechtnisAbhaengiges")
        self.assertIn("(x.quellen || []).some((q) => q.dokument_id === dokumentId)", block)
        self.assertNotIn(".every(", block)

    def test_die_oberflaeche_zaehlt_dieselben_zwei_zahlen_wie_der_dienst(self):
        """Nachgerechnet, nicht nachgelesen: beide Seiten an denselben Daten."""
        vorher = self.dienst.lesen(AKTE)
        erwartet_fragen = sum(
            1 for r in vorher.fragen_antworten
            if any(q.dokument_id == "D-001" for q in r.quellen))
        erwartet_zeitstrahl = sum(
            1 for x in vorher.chronologie
            if any(q.dokument_id == "D-001" for q in x.quellen))
        nachher = self.dienst.dokument_vergessen(AKTE, "D-001")
        self.assertEqual(len(vorher.fragen_antworten) - len(nachher.fragen_antworten),
                         erwartet_fragen)
        self.assertEqual(len(vorher.chronologie) - len(nachher.chronologie),
                         erwartet_zeitstrahl)


class DieRueckfrageSagtWasFaellt(unittest.TestCase):
    def setUp(self) -> None:
        self.block = _block("gedaechtnisDokumentVergessen")

    def test_sie_nennt_den_auszug_mit_seiten_und_umfang(self) -> None:
        self.assertIn("der Auszug selbst – ${e.seiten} Seite(n)", self.block)

    def test_sie_nennt_die_mitfallenden_fragen_und_zeitstrahleintraege(self) -> None:
        self.assertIn("${ab.fragen} gespeicherte Frage(n)", self.block)
        self.assertIn("${ab.zeitstrahl} Eintrag/Einträge im Zeitstrahl", self.block)

    def test_sie_sagt_auch_wenn_nichts_weiter_faellt(self) -> None:
        """Schweigen liest sich sonst wie „ich habe nicht nachgesehen"."""
        self.assertIn("sonst nichts", self.block)

    def test_sie_sagt_dass_die_akte_in_jurnodes_unberuehrt_bleibt(self) -> None:
        """Die Frage, die hier zuerst aufkommt — und die teuerste, wenn falsch."""
        self.assertIn("Die Akte in jur|nodes bleibt unberührt.", self.block)

    def test_sie_verspricht_kein_zurueck(self) -> None:
        """Zurücklegen geht, kostet aber — und holt das Abgeleitete nicht wieder.

        Deshalb gibt es hier auch keinen Rückgängig-Streifen: Ein „Rückgängig",
        das den vorigen Zustand nicht herstellt, ist eine Unwahrheit.
        """
        self.assertIn("kostet aber ein neues Einlesen", self.block)
        self.assertIn("kommt dadurch nicht wieder", self.block)
        self.assertNotIn("rueckgaengigAnbieten", self.block)

    def test_ohne_bestaetigung_geschieht_nichts(self) -> None:
        self.assertIn('if (!confirm(teile.join("\\n"))) return;', self.block)


class DerKnopfStehtInDerZeile(unittest.TestCase):
    def test_er_schliesst_den_dialog_nicht_statt_zu_loeschen(self) -> None:
        """Das Formular trägt method="dialog" — ohne type="button" wäre der
        Knopf ein Absendeknopf und der Dialog einfach zu."""
        block = _block("gedExplorerZeichnen")
        stelle = block.index("ged-vergessen")
        self.assertIn('weg.type = "button";', block[:stelle])

    def test_er_fuehrt_ueber_mitKnopf_damit_fehler_sichtbar_werden(self) -> None:
        block = _block("gedExplorerZeichnen")
        self.assertIn("mitKnopf(ev.target, () => gedaechtnisDokumentVergessen(e))", block)

    def test_der_titel_wird_vom_knopf_nicht_auf_null_gedrueckt(self) -> None:
        """Derselbe Fund wie bei der Ausschlussliste, nur eine Spalte weiter."""
        self.assertIn(".explorer-zeile .explorer-titelzeile { min-width:", CSS)

    def test_der_knopf_sieht_beim_darueberfahren_nach_wegnehmen_aus(self) -> None:
        self.assertIn(".ged-vergessen:hover", CSS)

    def test_das_fenster_sagt_dass_es_den_weg_gibt(self) -> None:
        """Ein Knopf, von dem niemand weiß, ist kein Weg."""
        self.assertIn('nimmt „vergessen" ein einzelnes', HTML)


class DanachStimmtDerSchirm(unittest.TestCase):
    """Nach dem Entfernen darf nirgends mehr stehen, was nicht mehr da ist."""

    def setUp(self) -> None:
        self.block = _block("gedaechtnisDokumentVergessen")

    def test_die_antwort_des_servers_wird_uebernommen(self) -> None:
        self.assertIn("sitzung.gedaechtnis = await api(\"DELETE\"", self.block)

    def test_der_zeitstrahl_der_oberflaeche_wird_mitgeraeumt(self) -> None:
        """Er trägt die Einträge aus der Analyse getrennt mit."""
        self.assertIn("chronoAusAnalyse = chronoAusAnalyse.filter", self.block)

    def test_beide_fenster_und_die_spalten_werden_neu_gezeichnet(self) -> None:
        for aufruf in ("gedExplorerZeichnen()", "gedaechtnisFensterZeigen()",
                       "chronologieZeigen()"):
            self.assertIn(aufruf, self.block)

    def test_die_meldung_nennt_was_mit_entfallen_ist(self) -> None:
        self.assertIn("Mit entfallen:", self.block)


if __name__ == "__main__":
    unittest.main()


class EineEinzelneFrageVergessen(unittest.TestCase):
    """Dasselbe für eine gespeicherte Frage-Antwort-Runde.

    Eine gespeicherte Antwort kann falsch oder überholt sein — etwa weil sie
    aus einem Dokument stammt, das inzwischen durch eine neue Fassung ersetzt
    wurde. Sie geht bei jeder späteren Frage als Vorwissen mit; stehen zu
    lassen, was nicht mehr stimmt, ist deshalb teurer, als es aussieht.
    """

    def setUp(self) -> None:
        self.block = _block("gedaechtnisFrageVergessen")

    def test_die_stelle_wird_frisch_bestimmt_nicht_aus_der_anzeige(self) -> None:
        """Der Server löscht nach Stelle in der Liste.

        Hat in der Zwischenzeit jemand an derselben Akte gearbeitet — zwei
        Anwälte, zwei Rechner —, zeigte die Stelle von vorhin auf eine andere
        Frage. Die wäre weg, ohne dass es jemand bemerkt.
        """
        self.assertIn('await api("GET", `/api/sitzungen/${sitzung.sitzung.id}/gedaechtnis`)',
                      self.block)
        self.assertIn("findIndex(", self.block)
        # Die Stelle kommt aus der frischen Liste, nicht aus einer Zählvariablen.
        self.assertIn("/gedaechtnis/fragen/${stelle}", self.block)

    def test_erkannt_wird_an_frage_antwort_und_zeitpunkt(self) -> None:
        for feld in ("x.frage === f.frage", "x.antwort === f.antwort",
                     "x.zeitpunkt === f.zeitpunkt"):
            self.assertIn(feld, self.block)

    def test_ist_sie_schon_weg_wird_nichts_geloescht(self) -> None:
        """Und die Ansicht sagt, warum — statt eine fremde Frage zu treffen."""
        self.assertIn("if (stelle < 0) {", self.block)
        stelle = self.block.index("if (stelle < 0) {")
        bis = self.block.index("return;", stelle)
        self.assertIn("jemand war schneller", self.block[stelle:bis])
        self.assertNotIn('api("DELETE"', self.block[:bis])

    def test_die_rueckfrage_sagt_was_stehen_bleibt(self) -> None:
        self.assertIn("Es fällt nur diese eine Runde heraus.", self.block)
        self.assertIn("Lebenssachverhalt und der Zeitstrahl bleiben stehen.", self.block)

    def test_sie_sagt_dass_die_akte_in_jurnodes_unberuehrt_bleibt(self) -> None:
        self.assertIn("Die Akte in jur|nodes bleibt unberührt.", self.block)

    def test_sie_nennt_den_preis_des_zweiten_mals(self) -> None:
        self.assertIn("kostet einen neuen Modellaufruf", self.block)

    def test_ohne_bestaetigung_geschieht_nichts(self) -> None:
        self.assertIn('if (!confirm(teile.join("\\n"))) return;', self.block)

    def test_der_knopf_steht_in_jeder_zeile_der_fragenliste(self) -> None:
        block = _block("gedInhaltZeigen")
        self.assertIn('weg.type = "button";', block)
        self.assertIn("mitKnopf(ev.target, () => gedaechtnisFrageVergessen(f))", block)

    def test_er_steht_unter_der_antwort_nicht_mitten_im_text(self) -> None:
        self.assertIn(".ged-block-frage .ged-vergessen", CSS)


class DieSchnittstelleGibtZurueckWasDieAnsichtBraucht(unittest.TestCase):
    """Die Oberfläche setzt die Antwort unmittelbar als neuen Stand ein.

    ``sitzung.gedaechtnis = await api("DELETE", …)`` — kommt dort etwas
    anderes zurück als die gewohnte Übersicht, steht danach ein halb leeres
    Fenster da, ohne dass irgendwo ein Fehler erschiene.
    """

    def setUp(self) -> None:
        from tests.hilfen import client, dienste, einstellungen

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal",
                          JUSPERFECT_GEDAECHTNIS_PFAD=self._tmp.name)
        self.d = dienste(einstellungen=e)
        self.c = client(self.d)
        g = Aktengedaechtnis(
            akte_id=AKTE, aktenzeichen="115/26 AR", bezeichnung="Test",
            dokumente=[GedaechtnisDokument(dokument_id="D-202", titel="Kündigung", nummer=1,
                                           seiten=[Seite(nummer=1, text="Text")])],
            letzte_dokumentnummer=1,
            fragen_antworten=[
                GedaechtnisAntwort(frage="Erste?", antwort="Ja. [Q: D1-S1-P1]",
                                   quellen=[_quelle("D1-S1-P1", "D-202")]),
                GedaechtnisAntwort(frage="Zweite?", antwort="Auch. [Q: D1-S1-P1]",
                                   quellen=[_quelle("D1-S1-P1", "D-202")]),
            ],
        )
        self.d.gedaechtnis.ablegen(g)
        self.d.gedaechtnis.lesen(AKTE)

    def test_sie_antwortet_mit_der_vollstaendigen_uebersicht(self) -> None:
        antwort = self.c.delete(f"/api/akten/{AKTE}/gedaechtnis/fragen/0")
        self.assertEqual(antwort.status_code, 200)
        daten = antwort.json()
        for feld in ("eintraege", "fragen_antworten", "chronologie", "zeichen",
                     "lebenssachverhalt", "quellen"):
            self.assertIn(feld, daten)
        self.assertEqual([f["frage"] for f in daten["fragen_antworten"]], ["Zweite?"])

    def test_die_dokumentauszuege_bleiben_stehen(self) -> None:
        """Genau das verspricht die Rückfrage."""
        daten = self.c.delete(f"/api/akten/{AKTE}/gedaechtnis/fragen/0").json()
        self.assertEqual([e["dokument_id"] for e in daten["eintraege"]], ["D-202"])

    def test_eine_stelle_die_es_nicht_gibt_loescht_nichts(self) -> None:
        self.assertGreaterEqual(self.c.delete(f"/api/akten/{AKTE}/gedaechtnis/fragen/7").status_code,
                                400)
        self.assertEqual(len(self.d.gedaechtnis.lesen(AKTE).fragen_antworten), 2)


class DieGespeicherteAnalyseFaelltMit(unittest.TestCase):
    """Befund F02 der Zweitprüfung vom 05.10.2026 — und es war mein Fehler.

    Die gespeicherte Aktenanalyse ist am Vormittag des 05.10.2026 dazugekommen.
    Beim Entfernen eines Dokuments wurde sie **nicht** mitbereinigt: Ein
    Chronologieereignis aus dem entfernten Dokument stand anschließend
    weiterhin in der zurückgegebenen Analyse.

    Die Zusage lautete „samt allem Abgeleiteten". Eine Prüfung in dieser Datei
    behauptete sie. Keine prüfte sie für die Analyse — weil es die Analyse beim
    Schreiben der Prüfung noch nicht gab.

    **Die Lehre:** Ein neues Feld im Gedächtnis ist nicht fertig, wenn es
    geschrieben und angezeigt wird. Es ist fertig, wenn auch gesagt ist, was
    beim Löschen damit geschieht.
    """

    def setUp(self) -> None:
        from jusperfect.domain.models import Aktenanalyse, BeteiligtenEintrag

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal",
                          JUSPERFECT_GEDAECHTNIS_PFAD=self._tmp.name)
        self.dienst = dienste(einstellungen=e).gedaechtnis
        g = Aktengedaechtnis(
            akte_id=AKTE, aktenzeichen="115/26 AR", bezeichnung="Test",
            dokumente=[
                GedaechtnisDokument(dokument_id=f"D-{nr:03d}", titel=f"Schreiben {nr}",
                                    nummer=nr, seiten=[Seite(nummer=1, text="Text")])
                for nr in (1, 2)
            ],
            letzte_dokumentnummer=2,
            analyse=Aktenanalyse(
                chronologie=[
                    ChronologieEintrag(datum="2026-05-04", ereignis="Aus D-001",
                                       quellen=[_quelle("D1-S1-P1", "D-001")]),
                    ChronologieEintrag(datum="2026-05-06", ereignis="Aus D-002",
                                       quellen=[_quelle("D2-S1-P1", "D-002")]),
                    ChronologieEintrag(datum="2026-05-07", ereignis="Aus beiden",
                                       quellen=[_quelle("D1-S1-P1", "D-001"),
                                                _quelle("D2-S1-P1", "D-002")]),
                ],
                beteiligte=[BeteiligtenEintrag(rolle="Zeuge", bezeichnung="X",
                                               quellen=[_quelle("D1-S1-P1", "D-001")])],
            ),
            analyse_dokumente=["D-001", "D-002"],
            analyse_akte_dokumente=["D-001", "D-002"],
        )
        self.dienst.ablegen(g)
        self.dienst.lesen(AKTE)

    def test_was_das_dokument_zitiert_faellt_aus_der_analyse(self) -> None:
        g = self.dienst.dokument_vergessen(AKTE, "D-001")
        assert [x.ereignis for x in g.analyse.chronologie] == ["Aus D-002"]
        assert g.analyse.beteiligte == []

    def test_ein_eintrag_aus_zwei_quellen_faellt_ganz(self) -> None:
        """Derselbe Maßstab wie bei der dauerhaften Chronologie: Ein Eintrag,
        dem die halbe Grundlage fehlt, stünde sonst weiter da."""
        g = self.dienst.dokument_vergessen(AKTE, "D-001")
        assert "Aus beiden" not in [x.ereignis for x in g.analyse.chronologie]

    def test_der_umfang_der_analyse_wird_nachgezogen(self) -> None:
        g = self.dienst.dokument_vergessen(AKTE, "D-001")
        assert g.analyse_dokumente == ["D-002"]

    def test_und_es_steht_dabei_dass_nicht_neu_gerechnet_wurde(self) -> None:
        """Eine Analyse, der ihre Grundlage fehlt, sieht genauso vollständig
        aus wie eine vollständige."""
        g = self.dienst.dokument_vergessen(AKTE, "D-001")
        assert "nachträglich ein Dokument entfernt" in g.analyse_hinweis
        assert "nicht neu" in g.analyse_hinweis

    def test_ein_unbeteiligtes_dokument_laesst_die_analyse_in_ruhe(self) -> None:
        """Sonst trüge jede Löschung einen Hinweis, der nichts bedeutet."""
        g = self.dienst.lesen(AKTE)
        g.dokumente.append(GedaechtnisDokument(dokument_id="D-003", titel="Drittes",
                                               nummer=3, seiten=[Seite(nummer=1, text="T")]))
        g.letzte_dokumentnummer = 3
        self.dienst.ablegen(g)
        nach = self.dienst.dokument_vergessen(AKTE, "D-003")
        assert len(nach.analyse.chronologie) == 3
        assert nach.analyse_hinweis == ""

    def test_ohne_analyse_geschieht_nichts(self) -> None:
        g = self.dienst.lesen(AKTE)
        g.analyse = None
        self.dienst.ablegen(g)
        nach = self.dienst.dokument_vergessen(AKTE, "D-001")
        assert nach.analyse is None
