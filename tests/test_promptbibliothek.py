"""Die Promptbibliothek: Ueberschrift und Prompt, je Rechtsgebiet.

Aus der Kanzlei am 13.10.2026, in drei Schritten:

    „Koennen wir noch eine Promptbibliothek anlegen. Diese fragt aber erst
    nach dem Rechtsgebiet. Fuer jedes Rechtsgebiet gibt es dann eine eigene
    kleine Promptbibliothek. Diese kann dann ueber dem Chatfenster sein."

    „Kann ich die Promptbibliothek nicht waehrend der Arbeit fuellen?"

    „Promptbibliothek neu und dann Ueberschrift und Prompt eintragen -
    einige sind schon vorher eingetragen."

Was diese Pruefungen festhalten:

1. Niemand wird nach dem Rechtsgebiet gefragt - es steht in der Akte.
2. Ueberschrift und Text sind zweierlei: in der Leiste steht die eine, ins
   Eingabefeld kommt der andere.
3. Die eigene Datei liegt **ausserhalb** des Programmordners (wie die
   Sperrliste, Befund N01): Sonst waere die Sammlung beim naechsten ZIP weg.
4. Der mitgelieferte Vorrat liegt IM Programmordner und wird nie
   beschrieben; wer einen Vorratseintrag wegnimmt, blendet ihn aus - sonst
   waere er beim naechsten ZIP wieder da.
5. Eine unlesbare eigene Datei wird nicht durch eine leere ersetzt.
6. Geschrieben wird erst daneben, dann umbenannt.
7. Der Wortlaut geht nicht ins Protokoll: Ein Prompt aus der Arbeit kann
   einen Namen enthalten.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jusperfect.services import promptbibliothek as pb
from jusperfect.services.promptbibliothek import BibliothekFehler

from tests.hilfen import client, dienste

WURZEL = Path(__file__).resolve().parent.parent


def _vorrat(ordner: str, inhalt: dict) -> Path:
    ort = Path(ordner) / "vorrat.json"
    ort.write_text(json.dumps(inhalt, ensure_ascii=False), encoding="utf-8")
    return ort


class DieEigeneDateiLiegtAusserhalb(unittest.TestCase):
    def test_kein_ort_liegt_im_programmordner(self):
        """Sonst waere sie in jeder ZIP - der Fehler, den Befund N01 behebt."""
        for ort in pb.orte():
            self.assertFalse(
                str(ort).startswith(str(pb.PROGRAMMORDNER) + "/"),
                f"{ort} liegt im Programmordner {pb.PROGRAMMORDNER}")

    def test_der_programmordner_ist_der_richtige(self):
        self.assertTrue((pb.PROGRAMMORDNER / "jusperfect").is_dir(), pb.PROGRAMMORDNER)

    def test_der_vorrat_dagegen_liegt_im_programmordner_und_ist_lesbar(self):
        self.assertTrue(pb.VORRAT.is_file(), pb.VORRAT)
        self.assertIsInstance(pb.vorrat(), dict)

    def test_der_vorrat_wird_mit_ausgeliefert(self):
        """Sonst fehlte er in der installierten Fassung - ohne dass es auffiele."""
        toml = (WURZEL / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("promptvorrat.json", toml)


class DerAusgelieferteVorrat(unittest.TestCase):
    """Was wirklich in jusperfect/promptvorrat.json steht.

    Die Verkehrsrecht-Eintraege stammen wortgleich aus der Kanzlei
    (13.10.2026, „B. Bearbeitungsmodule"). Diese Pruefungen halten fest, dass
    sie vollstaendig ankommen und die Grenzen einhalten - ein Prompt, der
    beim Lesen abgeschnitten wird, verliert seine letzte Anweisung, und das
    faellt beim Arbeiten nicht auf.
    """

    VORRAT = pb.vorrat()

    def test_die_gebiete_der_kanzlei_sind_hinterlegt(self):
        self.assertEqual(len(self.VORRAT["Verkehrsrecht"]["eintraege"]), 17)
        self.assertEqual(len(self.VORRAT["Arbeitsrecht"]["eintraege"]), 10)
        self.assertEqual(len(self.VORRAT["Privates Baurecht"]["eintraege"]), 10)
        self.assertEqual(len(self.VORRAT["Gerichtsmuster"]["eintraege"]), 12)

    def test_der_basisprompt_des_baurechts_ist_vollstaendig_da(self):
        """„Gemeinsamer Basisprompt fuer alle Module." Er ist ueber
        dreitausend Zeichen lang; eine zu enge Grenze haette ihn
        abgeschnitten, und das waere niemandem aufgefallen."""
        basis = pb.basis("Privates Baurecht")
        self.assertGreater(len(basis), 3000)
        self.assertLessEqual(len(basis), pb.MAX_ZEICHEN)
        for stichwort in ("MANDANTENROLLE", "AKTENAUSWERTUNG", "FRISTEN",
                          "VERTRAULICHKEIT", "[BITTE ERGÄNZEN]", "Kanzleifreigabe"):
            with self.subTest(stichwort=stichwort):
                self.assertIn(stichwort, basis)

    def test_der_vorspann_findet_sich_auch_unter_kurzem_namen(self):
        """jur|nodes nennt das Gebiet vielleicht nur „Baurecht"."""
        self.assertEqual(pb.basis("Baurecht"), pb.basis("Privates Baurecht"))

    def test_die_anderen_gebiete_haben_keinen_vorspann(self):
        """Die Kanzlei hat ihn nur zum Baurecht mitgeliefert."""
        self.assertEqual(pb.basis("Verkehrsrecht"), "")
        self.assertEqual(pb.basis("Arbeitsrecht"), "")

    def test_jeder_eintrag_hat_ueberschrift_und_text(self):
        for gebiet, block in self.VORRAT.items():
            for eintrag in block["eintraege"]:
                with self.subTest(gebiet=gebiet, titel=eintrag["titel"]):
                    self.assertTrue(eintrag["titel"].strip())
                    self.assertTrue(eintrag["text"].strip())

    def test_keiner_wird_beim_lesen_abgeschnitten(self):
        """Sonst fehlte die letzte Anweisung - unbemerkt."""
        roh = json.loads(pb.VORRAT.read_text(encoding="utf-8"))
        for gebiet, block in roh["rechtsgebiete"].items():
            liste = block if isinstance(block, list) else block["eintraege"]
            for eintrag in liste:
                with self.subTest(gebiet=gebiet, titel=eintrag["titel"]):
                    self.assertLessEqual(len(eintrag["titel"]), pb.MAX_TITEL)
                    self.assertLessEqual(len(eintrag["text"]), pb.MAX_ZEICHEN)

    def test_keine_ueberschrift_doppelt(self):
        """Die Ueberschrift ist der Griff zum Herausnehmen - sie muss
        innerhalb eines Gebiets eindeutig sein."""
        for gebiet, block in self.VORRAT.items():
            titel = [e["titel"].casefold() for e in block["eintraege"]]
            with self.subTest(gebiet=gebiet):
                self.assertEqual(len(titel), len(set(titel)))

    def test_er_passt_in_die_leiste(self):
        """Mehr als MAX_EINTRAEGE waere keine Auswahl mehr."""
        for gebiet, block in self.VORRAT.items():
            with self.subTest(gebiet=gebiet):
                self.assertLessEqual(len(block["eintraege"]), pb.MAX_EINTRAEGE)


class AblegenUndHerausnehmen(unittest.TestCase):
    def setUp(self):
        self._ordner = TemporaryDirectory()
        self.ort = Path(self._ordner.name) / pb.DATEINAME
        self.leer = _vorrat(self._ordner.name, {"rechtsgebiete": {}})
        self.addCleanup(self._ordner.cleanup)

    def _liste(self, gebiet="Arbeitsrecht"):
        return pb.eintraege(gebiet, self.ort, self.leer)

    def test_ohne_datei_ist_die_bibliothek_leer_und_kein_fehler(self):
        self.assertEqual(self._liste(), ())
        self.assertFalse(self.ort.exists(), "Lesen legt nichts an.")

    def test_abgelegtes_kommt_mit_ueberschrift_wieder(self):
        pb.merken("Arbeitsrecht", "Fristen", "Welche Fristen laufen?", self.ort)
        self.assertEqual(self._liste(), (
            {"titel": "Fristen", "text": "Welche Fristen laufen?", "mitgeliefert": False},))

    def test_ohne_ueberschrift_wird_der_text_zur_ueberschrift(self):
        """Besser eine abgeschnittene als gar keine - sonst steht nichts da."""
        pb.merken("Arbeitsrecht", "", "Welche Fristen laufen?", self.ort)
        self.assertEqual(self._liste()[0]["titel"], "Welche Fristen laufen?")

    def test_jedes_gebiet_hat_seine_eigene_liste(self):
        pb.merken("Arbeitsrecht", "Fristen", "Welche Fristen laufen?", self.ort)
        pb.merken("Verkehrsrecht", "Vorfahrt", "Wer hatte Vorfahrt?", self.ort)
        self.assertEqual([e["titel"] for e in self._liste("Arbeitsrecht")], ["Fristen"])
        self.assertEqual([e["titel"] for e in self._liste("Verkehrsrecht")], ["Vorfahrt"])

    def test_ein_mehrzeiliger_prompt_bleibt_mehrzeilig(self):
        """Ein brauchbarer Prompt ist mehrere Zeilen lang."""
        pb.merken("Arbeitsrecht", "Pruefung", "Erstens: ...\n\nZweitens: ...", self.ort)
        self.assertIn("\n\n", self._liste()[0]["text"])

    def test_zuletzt_abgelegtes_steht_vorn(self):
        pb.merken("Arbeitsrecht", "Eins", "Erster Prompt", self.ort)
        pb.merken("Arbeitsrecht", "Zwei", "Zweiter Prompt", self.ort)
        self.assertEqual(self._liste()[0]["titel"], "Zwei")

    def test_derselbe_text_zweimal_steht_einmal_da(self):
        pb.merken("Arbeitsrecht", "Eins", "Welche Fristen laufen?", self.ort)
        pb.merken("Arbeitsrecht", "Zwei", "welche fristen LAUFEN?", self.ort)
        self.assertEqual(len(self._liste()), 1)

    def test_leeres_laesst_sich_nicht_ablegen(self):
        with self.assertRaises(BibliothekFehler):
            pb.merken("Arbeitsrecht", "Titel", "   \n  ", self.ort)

    def test_herausnehmen_nimmt_heraus(self):
        """Sonst waere jeder Vertipper endgueltig."""
        pb.merken("Arbeitsrecht", "Fristen", "Welche Fristen laufen?", self.ort)
        pb.merken("Arbeitsrecht", "Sonst", "Und sonst?", self.ort)
        pb.vergessen("Arbeitsrecht", "Fristen", self.ort)
        self.assertEqual([e["titel"] for e in self._liste()], ["Sonst"])

    def test_ohne_rechtsgebiet_gibt_es_einen_eigenen_platz(self):
        """Ein leerer Schluessel waere unsichtbar - man suchte den Prompt vergebens."""
        pb.merken("", "Allgemein", "Was steht in der Akte?", self.ort)
        self.assertEqual([e["titel"] for e in pb.eintraege("", self.ort, self.leer)], ["Allgemein"])
        self.assertIn(pb.OHNE_GEBIET, pb.laden(self.ort)["rechtsgebiete"])

    def test_die_zahl_ist_begrenzt(self):
        for n in range(pb.MAX_EINTRAEGE):
            pb.merken("Arbeitsrecht", f"T{n}", f"Prompt {n}", self.ort)
        with self.assertRaises(BibliothekFehler) as f:
            pb.merken("Arbeitsrecht", "Zuviel", "Einer zuviel", self.ort)
        self.assertIn("entfernen", str(f.exception))

    def test_sehr_langes_wird_gekuerzt_statt_abgelehnt(self):
        pb.merken("Arbeitsrecht", "A" * 300, "B" * (pb.MAX_ZEICHEN + 500), self.ort)
        eintrag = self._liste()[0]
        self.assertEqual(len(eintrag["titel"]), pb.MAX_TITEL)
        self.assertEqual(len(eintrag["text"]), pb.MAX_ZEICHEN)

    def test_alte_sammlungen_ohne_ueberschrift_bleiben_lesbar(self):
        """Vor dem 13.10.2026 stand in der Datei nur die Frage."""
        self.ort.write_text(json.dumps(
            {"rechtsgebiete": {"Arbeitsrecht": ["Welche Fristen laufen?"]}}), encoding="utf-8")
        self.assertEqual(self._liste()[0]["text"], "Welche Fristen laufen?")
        self.assertEqual(self._liste()[0]["titel"], "Welche Fristen laufen?")


class DerVorratIstSchonDa(unittest.TestCase):
    """„Einige sind schon vorher eingetragen."""

    def setUp(self):
        self._ordner = TemporaryDirectory()
        self.ort = Path(self._ordner.name) / pb.DATEINAME
        self.vorrat = _vorrat(self._ordner.name, {"rechtsgebiete": {"Verkehrsrecht": [
            {"titel": "Haftungsquote", "text": "Welche Haftungsquote ergibt sich?"}]}})
        self.addCleanup(self._ordner.cleanup)

    def test_der_vorrat_steht_ohne_zutun_da(self):
        liste = pb.eintraege("Verkehrsrecht", self.ort, self.vorrat)
        self.assertEqual([e["titel"] for e in liste], ["Haftungsquote"])
        self.assertTrue(liste[0]["mitgeliefert"])

    def test_eigenes_steht_vor_mitgeliefertem(self):
        """Die Kanzlei hat es selbst abgelegt; der Vorrat ist nur der Anfang."""
        pb.merken("Verkehrsrecht", "Eigenes", "Eigener Prompt", self.ort)
        liste = pb.eintraege("Verkehrsrecht", self.ort, self.vorrat)
        self.assertEqual([e["titel"] for e in liste], ["Eigenes", "Haftungsquote"])

    def test_ein_anderes_gebiet_sieht_ihn_nicht(self):
        self.assertEqual(pb.eintraege("Arbeitsrecht", self.ort, self.vorrat), ())

    def test_eine_abweichende_schreibweise_findet_ihn_trotzdem(self):
        """jur|nodes schreibt lawCategory so, wie die Kanzlei es angelegt hat."""
        for gebiet in ("Verkehr", "verkehrsrecht", "Verkehrs-Recht", "Verkehrsunfallrecht"):
            with self.subTest(gebiet=gebiet):
                self.assertEqual(len(pb.eintraege(gebiet, self.ort, self.vorrat)), 1)

    def test_ein_kurzes_wort_passt_nicht_auf_jedes(self):
        self.assertEqual(pb.eintraege("Vertragsrecht", self.ort, self.vorrat), ())

    def test_ein_kaputter_vorrat_haelt_nichts_auf(self):
        """Er ist Zugabe. Eigenes darf er nicht verschatten."""
        kaputt = Path(self._ordner.name) / "kaputt.json"
        kaputt.write_text("{kein json", encoding="utf-8")
        pb.merken("Verkehrsrecht", "Eigenes", "Eigener Prompt", self.ort)
        self.assertEqual([e["titel"] for e in pb.eintraege("Verkehrsrecht", self.ort, kaputt)],
                         ["Eigenes"])


class MitgeliefertesWirdAusgeblendetNichtGeloescht(unittest.TestCase):
    """Loeschen koennte man es nur im Programmordner - beim naechsten ZIP
    waere es wieder da."""

    def setUp(self):
        self._ordner = TemporaryDirectory()
        self.ort = Path(self._ordner.name) / pb.DATEINAME
        self.addCleanup(self._ordner.cleanup)
        self._alt = pb.vorrat
        pb.vorrat = lambda ort=None: {"Verkehrsrecht": {   # type: ignore[assignment]
            "basis": "",
            "eintraege": [{"titel": "Haftungsquote",
                           "text": "Welche Haftungsquote ergibt sich?"}]}}
        self.addCleanup(lambda: setattr(pb, "vorrat", self._alt))

    def test_ausgeblendetes_erscheint_nicht_mehr(self):
        pb.vergessen("Verkehrsrecht", "Haftungsquote", self.ort)
        self.assertEqual(pb.eintraege("Verkehrsrecht", self.ort), ())

    def test_das_ausblenden_steht_in_der_eigenen_datei(self):
        pb.vergessen("Verkehrsrecht", "Haftungsquote", self.ort)
        roh = json.loads(self.ort.read_text(encoding="utf-8"))
        self.assertIn("Haftungsquote", roh["versteckt"]["Verkehrsrecht"])

    def test_der_vorrat_selbst_bleibt_unberuehrt(self):
        pb.vergessen("Verkehrsrecht", "Haftungsquote", self.ort)
        self.assertEqual(len(pb.vorrat()["Verkehrsrecht"]["eintraege"]), 1)


class DieGerichtsmusterGeltenImmer(unittest.TestCase):
    """Aus der Kanzlei: „Eigenstaendiger Bereich ‚Gerichtsmuster'."

    Eine Klageerwiderung schreibt man im Bau- wie im Arbeitsrecht. Sie
    haengen deshalb nicht am Rechtsgebiet der Akte - stehen aber in einer
    eigenen Zeile und nicht zwischen den Modulen des Gebiets.
    """

    def setUp(self):
        self._ordner = TemporaryDirectory()
        self.ort = Path(self._ordner.name) / pb.DATEINAME
        self.addCleanup(self._ordner.cleanup)

    def test_sie_stehen_bei_jedem_rechtsgebiet(self):
        for gebiet in ("Verkehrsrecht", "Arbeitsrecht", "Privates Baurecht",
                       "Sozialrecht", ""):
            with self.subTest(gebiet=gebiet):
                namen = [g["name"] for g in pb.gruppen(gebiet, self.ort)]
                self.assertIn("Gerichtsmuster", namen)

    def test_das_rechtsgebiet_steht_vorn(self):
        """Es ist das, woran gerade gearbeitet wird."""
        gruppen = pb.gruppen("Verkehrsrecht", self.ort)
        self.assertEqual(gruppen[0]["name"], "Verkehrsrecht")
        self.assertFalse(gruppen[0]["immer"])

    def test_sie_stehen_nicht_zweimal_da(self):
        """Auch nicht, wenn eine Akte zufaellig „Gerichtsmuster" hiesse."""
        namen = [g["name"] for g in pb.gruppen("Gerichtsmuster", self.ort)]
        self.assertEqual(namen.count("Gerichtsmuster"), 1)

    def test_jede_gruppe_hat_ihren_eigenen_vorspann(self):
        """Der des Rechtsgebiets gilt nicht fuer ein Gerichtsmuster."""
        gruppen = {g["name"]: g for g in pb.gruppen("Privates Baurecht", self.ort)}
        self.assertNotEqual(gruppen["Privates Baurecht"]["basis"],
                            gruppen["Gerichtsmuster"]["basis"])
        self.assertIn("gerichtlicher Schriftsätze", gruppen["Gerichtsmuster"]["basis"])
        self.assertIn("privaten Baurecht", gruppen["Privates Baurecht"]["basis"])

    def test_ausgeblendetes_bleibt_in_jedem_gebiet_weg(self):
        """Sonst waere ein Gerichtsmuster nur in Akten eines Gebiets weg."""
        pb.vergessen("Verkehrsrecht", "Duplik", self.ort)
        for gebiet in ("Verkehrsrecht", "Arbeitsrecht", "Privates Baurecht"):
            with self.subTest(gebiet=gebiet):
                gm = [g for g in pb.gruppen(gebiet, self.ort)
                      if g["name"] == "Gerichtsmuster"][0]
                self.assertNotIn("Duplik", [e["titel"] for e in gm["eintraege"]])

    def test_sie_mischen_sich_nicht_unter_das_rechtsgebiet(self):
        eigen = pb.eintraege("Verkehrsrecht", self.ort)
        self.assertNotIn("Duplik", [e["titel"] for e in eigen])


class DerVorspannKommtSichtbarInsFeld(unittest.TestCase):
    """Ein Vorspann, den man nicht sieht, ist eine Anweisung, von der man
    nichts weiss."""

    JS = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")

    def _block(self):
        return self.JS[self.JS.index("function bibReiter"):
                       self.JS.index("async function bibliothekLaden")]

    def test_er_wird_dem_prompt_vorangestellt(self):
        self.assertIn("gruppe.basis", self._block())
        self.assertIn("feld.value = ganz", self._block())

    def test_das_feld_sagt_es(self):
        self.assertIn("Vorspann", self._block())

    def test_der_web_liefert_ihn_mit(self):
        web = (WURZEL / "jusperfect" / "web.py").read_text(encoding="utf-8")
        self.assertIn('"basis": g["basis"]', web)


class EineKaputteDateiWirdNichtUeberschrieben(unittest.TestCase):
    """In ihr steht die Sammlung von Monaten."""

    def setUp(self):
        self._ordner = TemporaryDirectory()
        self.ort = Path(self._ordner.name) / pb.DATEINAME
        self.addCleanup(self._ordner.cleanup)

    def test_unlesbares_meldet_sich_und_bleibt_liegen(self):
        self.ort.write_text("{kein json", encoding="utf-8")
        with self.assertRaises(BibliothekFehler) as f:
            pb.laden(self.ort)
        self.assertIn("nicht veraendert", str(f.exception))
        self.assertEqual(self.ort.read_text(encoding="utf-8"), "{kein json")

    def test_falscher_aufbau_meldet_sich(self):
        self.ort.write_text('{"etwas": "anderes"}', encoding="utf-8")
        with self.assertRaises(BibliothekFehler):
            pb.laden(self.ort)

    def test_ablegen_auf_kaputtes_wirft_nichts_weg(self):
        self.ort.write_text("{kein json", encoding="utf-8")
        with self.assertRaises(BibliothekFehler):
            pb.merken("Arbeitsrecht", "Titel", "Ein Prompt", self.ort)
        self.assertEqual(self.ort.read_text(encoding="utf-8"), "{kein json")


class GeschriebenWirdErstDaneben(unittest.TestCase):
    """Ein Abbruch mitten im Schreiben darf die Sammlung nicht kosten."""

    def test_es_bleibt_keine_halbe_datei_liegen(self):
        with TemporaryDirectory() as ordner:
            ort = Path(ordner) / pb.DATEINAME
            pb.merken("Arbeitsrecht", "Titel", "Ein Prompt", ort)
            self.assertEqual([p.name for p in Path(ordner).iterdir()], [pb.DATEINAME])

    def test_die_datei_hat_beide_abschnitte(self):
        with TemporaryDirectory() as ordner:
            ort = Path(ordner) / pb.DATEINAME
            pb.merken("Arbeitsrecht", "Titel", "Ein Prompt", ort)
            roh = json.loads(ort.read_text(encoding="utf-8"))
            self.assertEqual(sorted(roh), ["rechtsgebiete", "versteckt"])
            self.assertEqual(roh["rechtsgebiete"]["Arbeitsrecht"],
                             [{"titel": "Titel", "text": "Ein Prompt"}])


class UeberDenWeb(unittest.TestCase):
    """Das Rechtsgebiet kommt aus der Akte - niemand wird gefragt."""

    def setUp(self):
        self._ordner = TemporaryDirectory()
        self.addCleanup(self._ordner.cleanup)
        ort = Path(self._ordner.name) / pb.DATEINAME
        self._alt_orte = pb.orte
        pb.orte = lambda: (ort,)                      # type: ignore[assignment]
        self.addCleanup(lambda: setattr(pb, "orte", self._alt_orte))
        self._alt_vorrat = pb.vorrat
        pb.vorrat = lambda o=None: {}                 # type: ignore[assignment]
        self.addCleanup(lambda: setattr(pb, "vorrat", self._alt_vorrat))
        self.d = dienste()
        self.c = client(self.d)
        self.sid = self.c.post("/api/sitzungen", json={"akte_id": "AR-2026-0115"}).json()["sitzung"]["id"]

    def _eigene(self, daten):
        """Die Gruppe des Rechtsgebiets - die erste."""
        return daten["gruppen"][0]["eintraege"]

    def test_das_gebiet_steht_in_der_antwort_und_kam_aus_der_akte(self):
        daten = self.c.get(f"/api/sitzungen/{self.sid}/prompts").json()
        self.assertEqual(daten["rechtsgebiet"], "Arbeitsrecht")
        self.assertTrue(daten["aus_akte"])
        self.assertEqual(self._eigene(daten), [])

    def test_ablegen_und_wieder_lesen(self):
        abgelegt = self.c.post(f"/api/sitzungen/{self.sid}/prompts",
                               json={"titel": "Fristen", "text": "Welche Fristen laufen?"})
        self.assertEqual(abgelegt.status_code, 201, abgelegt.text)
        self.assertEqual(self._eigene(abgelegt.json()),
                         [{"titel": "Fristen", "text": "Welche Fristen laufen?",
                           "mitgeliefert": False}])
        self.assertEqual(
            len(self._eigene(self.c.get(f"/api/sitzungen/{self.sid}/prompts").json())), 1)

    def test_herausnehmen_ueber_den_web(self):
        self.c.post(f"/api/sitzungen/{self.sid}/prompts",
                    json={"titel": "Fristen", "text": "Welche Fristen laufen?"})
        antwort = self.c.post(f"/api/sitzungen/{self.sid}/prompts/vergessen",
                              json={"titel": "Fristen"})
        self.assertEqual(antwort.status_code, 200, antwort.text)
        self.assertEqual(self._eigene(antwort.json()), [])

    def test_leeres_wird_abgewiesen_und_nicht_mit_500(self):
        antwort = self.c.post(f"/api/sitzungen/{self.sid}/prompts",
                              json={"titel": "Leer", "text": "  "})
        self.assertEqual(antwort.status_code, 422, antwort.text)

    def test_eine_fremde_sitzung_sieht_nichts(self):
        self.assertEqual(self.c.get("/api/sitzungen/gibtesnicht/prompts").status_code, 404)

    def test_der_wortlaut_steht_nicht_im_protokoll(self):
        """Ein Prompt aus der Arbeit kann einen Namen enthalten."""
        with self.assertLogs("jusperfect", level="INFO") as aufzeichnung:
            self.c.post(f"/api/sitzungen/{self.sid}/prompts",
                        json={"titel": "Kuendigungsfrist",
                              "text": "Hat die Kuendigung die Frist gewahrt?"})
        text = "\n".join(aufzeichnung.output)
        self.assertNotIn("gewahrt", text, text)
        self.assertIn("prompt_abgelegt", text)
        self.assertIn("Arbeitsrecht", text)


class DieOberflaecheZeigtSie(unittest.TestCase):
    HTML = (WURZEL / "jusperfect" / "static" / "index.html").read_text(encoding="utf-8")
    JS = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")

    def test_die_leiste_steht_ueber_der_eingabe_nicht_ueber_dem_verlauf(self):
        """Der Chat steht im Vordergrund; eine Leiste ueber dem Verlauf
        haette ihn bei jeder Nachricht ein Stueck nach unten geschoben."""
        self.assertLess(self.HTML.index('<div class="eingabe">'), self.HTML.index('id="bibliothek"'))
        self.assertLess(self.HTML.index('id="bibliothek"'), self.HTML.index('id="frage-form"'))

    def test_der_dialog_fragt_nach_ueberschrift_und_prompt(self):
        """„Neu und dann Ueberschrift und Prompt eintragen."""
        anfang = self.HTML.index('id="prompt-dialog"')
        block = self.HTML[anfang:self.HTML.index("</dialog>", anfang)]
        self.assertIn('id="prompt-titel"', block)
        self.assertIn('id="prompt-text"', block)
        self.assertIn("Überschrift", block)

    def test_der_dialog_warnt_vor_namen(self):
        """Die Bibliothek ueberdauert die Akte."""
        anfang = self.HTML.index('id="prompt-dialog"')
        self.assertIn("keine Namen", self.HTML[anfang:self.HTML.index("</dialog>", anfang)])

    def test_abgelegte_prompts_werden_als_text_gesetzt_nie_als_html(self):
        """In einem abgelegten Prompt kann alles stehen."""
        block = self.JS[self.JS.index("function bibliothekZeichnen"):
                        self.JS.index("async function bibliothekLaden")]
        self.assertNotIn("innerHTML =", block)
        self.assertNotIn("insertAdjacentHTML", block)
        self.assertIn("nehmen.textContent = eintrag.titel", block)

    def test_jede_gruppe_bekommt_ihren_eigenen_reiter(self):
        """Neununddreissig Knoepfe auf einmal waeren eine Liste zum
        Durchsuchen. Aus der Kanzlei am 14.10.2026: „Mit ausklappbaren
        Reitern."""
        block = self.JS[self.JS.index("function bibliothekZeichnen"):
                        self.JS.index("async function bibliothekLaden")]
        self.assertIn("bib-gruppe", block)
        self.assertIn("bib-gruppenname", block)
        self.assertIn('createElement("details")', block)
        self.assertIn('createElement("summary")', block)

    def test_der_dialog_ist_vorgefuellt_aber_zu_lesen(self):
        """Waehrend der Arbeit fuellen - aber mit einem Blick darauf."""
        block = self.JS[self.JS.index("function bibNeu"):self.JS.index("async function bibAblegen")]
        self.assertIn("letzteGestellteFrage", block)
        self.assertIn("showModal", block)


class DieMitteHatEineUeberschrift(unittest.TestCase):
    """Aus der Kanzlei am 14.10.2026: „Bitte in der Mitte hätte ich gerne
    eine große Überschrift Chat ohne Auswahlfunktion - eine normale
    Überschrift für die Promptbibliothek."

    „Ohne Auswahlfunktion" ist der Kern: Sie ist eine Überschrift und kein
    Knopf. Hier wird nichts umgeschaltet.
    """

    HTML = (WURZEL / "jusperfect" / "static" / "index.html").read_text(encoding="utf-8")
    CSS = (WURZEL / "jusperfect" / "static" / "styles.css").read_text(encoding="utf-8")

    def test_die_mitte_heisst_chat(self):
        kopf = self.HTML[self.HTML.index('<section class="spalte cowork'):
                         self.HTML.index('<div id="thread"')]
        self.assertIn('<h1 class="chat-titel">Chat</h1>', kopf)

    def test_die_ueberschrift_ist_kein_knopf(self):
        kopf = self.HTML[self.HTML.index('<section class="spalte cowork'):
                         self.HTML.index('<div id="thread"')]
        block = kopf[kopf.index('class="chat-titel"'):]
        self.assertNotIn("<button", block[:block.index("</h1>")])
        regel = self.CSS[self.CSS.index(".chat-titel {"):]
        self.assertIn("pointer-events: none", regel[:regel.index("}")])

    def test_die_bibliothek_bekommt_die_kleinere_ueberschrift(self):
        """Die große gehört dem Chat."""
        self.assertIn('<h2 class="bib-titel">Promptbibliothek</h2>', self.HTML)
        gross = self.CSS[self.CSS.index(".chat-titel {"):]
        klein = self.CSS[self.CSS.index(".bib-titel {"):]
        self.assertIn("font-size: 19px", gross[:gross.index("}")])
        self.assertIn("font-size: 13px", klein[:klein.index("}")])


class DasRechtsgebietLaesstSichWechseln(unittest.TestCase):
    """Aus der Kanzlei am 14.10.2026: „und Rechtsgebiet wechseln."

    Voreingestellt bleibt das Gebiet der Akte. Aber eine Verkehrssache kann
    eine arbeitsrechtliche Frage aufwerfen, und dann will man dorthin, ohne
    die Akte zu wechseln.
    """

    def setUp(self):
        self._ordner = TemporaryDirectory()
        self.addCleanup(self._ordner.cleanup)
        ort = Path(self._ordner.name) / pb.DATEINAME
        self._alt_orte = pb.orte
        pb.orte = lambda: (ort,)                      # type: ignore[assignment]
        self.addCleanup(lambda: setattr(pb, "orte", self._alt_orte))
        self.d = dienste()
        self.c = client(self.d)
        self.sid = self.c.post("/api/sitzungen",
                               json={"akte_id": "AR-2026-0115"}).json()["sitzung"]["id"]

    def test_die_gebiete_stehen_zur_wahl(self):
        daten = self.c.get(f"/api/sitzungen/{self.sid}/prompts").json()
        self.assertIn("Arbeitsrecht", daten["gebiete"])
        self.assertIn("Verkehrsrecht", daten["gebiete"])
        self.assertEqual(daten["gebiet_der_akte"], "Arbeitsrecht")
        self.assertFalse(daten["gewaehlt"])

    def test_die_gerichtsmuster_stehen_nicht_zur_wahl(self):
        """Sie sind keine Wahl, sie sind da."""
        daten = self.c.get(f"/api/sitzungen/{self.sid}/prompts").json()
        self.assertNotIn("Gerichtsmuster", daten["gebiete"])
        self.assertIn("Gerichtsmuster", [g["name"] for g in daten["gruppen"]])

    def test_ein_gewaehltes_gebiet_zeigt_dessen_prompts(self):
        daten = self.c.get(f"/api/sitzungen/{self.sid}/prompts",
                           params={"rechtsgebiet": "Verkehrsrecht"}).json()
        self.assertEqual(daten["rechtsgebiet"], "Verkehrsrecht")
        self.assertTrue(daten["gewaehlt"])
        self.assertEqual(len(daten["gruppen"][0]["eintraege"]), 17)

    def test_die_akte_bleibt_benannt(self):
        """Sonst weiß nach dem Wechseln niemand mehr, wozu die Akte gehört."""
        daten = self.c.get(f"/api/sitzungen/{self.sid}/prompts",
                           params={"rechtsgebiet": "Verkehrsrecht"}).json()
        self.assertEqual(daten["gebiet_der_akte"], "Arbeitsrecht")

    def test_abgelegt_wird_unter_dem_gewaehlten_gebiet(self):
        """Wer zum Verkehrsrecht gewechselt hat und dort etwas merkt, meint
        das Verkehrsrecht."""
        self.c.post(f"/api/sitzungen/{self.sid}/prompts",
                    json={"titel": "Eigenes", "text": "Ein eigener Prompt",
                          "rechtsgebiet": "Verkehrsrecht"})
        self.assertIn("Eigenes", [e["titel"] for e in pb.eintraege("Verkehrsrecht")])
        self.assertNotIn("Eigenes", [e["titel"] for e in pb.eintraege("Arbeitsrecht")])

    def test_ohne_wahl_bleibt_es_bei_der_akte(self):
        self.c.post(f"/api/sitzungen/{self.sid}/prompts",
                    json={"titel": "Eigenes", "text": "Ein eigener Prompt"})
        self.assertIn("Eigenes", [e["titel"] for e in pb.eintraege("Arbeitsrecht")])

    def test_die_oberflaeche_hat_die_wahl(self):
        html = (WURZEL / "jusperfect" / "static" / "index.html").read_text(encoding="utf-8")
        js = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="bib-gebietswahl"', html)
        self.assertIn("bibGebietswahl", js)
        self.assertIn("rechtsgebiet=", js)

    def test_die_wahl_gehoert_zur_akte_und_endet_mit_ihr(self):
        js = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('bibGebietswahl = "";', js)


class DieReiterKlappenAus(unittest.TestCase):
    """Aus der Kanzlei am 14.10.2026: „Mit ausklappbaren Reitern."

    Gebaut mit <details>: Das kann der Browser selbst - mit Tastatur, mit
    Vorlesesoftware und ohne eine Zeile Javascript für das Auf und Zu.
    """

    JS = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")
    CSS = (WURZEL / "jusperfect" / "static" / "styles.css").read_text(encoding="utf-8")

    def test_die_anzahl_steht_am_reiter(self):
        """Wer sucht, soll sehen, wo etwas zu holen ist, ohne aufzuklappen."""
        block = self.JS[self.JS.index("function bibReiter"):]
        self.assertIn("gruppe.eintraege.length", block[:2000])

    def test_der_stand_der_reiter_ueberlebt_die_sitzung(self):
        """Wer eine Gruppe zuklappt, hat sie beim nächsten Mal wieder zu."""
        self.assertIn("jusperfect.bib.zu", self.JS)
        block = self.JS[self.JS.index("function bibZuMerken"):]
        self.assertIn("try", block[:600])

    def test_ein_ausgefallener_speicher_haelt_nichts_auf(self):
        """Der Stand der Reiter ist Bequemlichkeit und nicht Arbeit."""
        block = self.JS[self.JS.index("function bibZu()"):self.JS.index("function bibliothekZeichnen")]
        self.assertIn("catch", block)

    def test_das_dreieck_zeigt_den_zustand(self):
        self.assertIn(".bib-gruppe[open] > .bib-gruppenname::before", self.CSS)


class DieFensterknoepfeStehenRechts(unittest.TestCase):
    """Aus der Kanzlei am 13.10.2026: „Knoepfe Chronologie, Gedaechtnis und
    Belege nach rechts verschieben, sonst verwirrend."

    Sie standen in der Kopfzeile des Chats und schalteten Fenster, die ganz
    woanders aufgehen.
    """

    HTML = (WURZEL / "jusperfect" / "static" / "index.html").read_text(encoding="utf-8")

    def test_sie_stehen_in_der_rechten_spalte(self):
        rechts = self.HTML.index('id="spalte-rechts"')
        for name in ("chronologie", "gedaechtnis", "belege"):
            with self.subTest(name=name):
                self.assertGreater(self.HTML.index(f'data-fenster="{name}"'), rechts)

    def test_sie_stehen_in_der_leiste_die_stehen_bleibt(self):
        """Sonst waeren sie weg, sobald alle drei Fenster zu sind."""
        anfang = self.HTML.index('<div class="rechts-aktionen">')
        block = self.HTML[anfang:self.HTML.index("<section", anfang)]
        for name in ("chronologie", "gedaechtnis", "belege"):
            with self.subTest(name=name):
                self.assertIn(f'data-fenster="{name}"', block)

    def test_der_dokumentenknopf_bleibt_in_der_kopfzeile(self):
        """Die linke Spalte hat keine Leiste, die stehen bliebe - ohne ihn
        kaeme man an ein zugeklapptes Dokumentenfenster nicht mehr heran."""
        self.assertLess(self.HTML.index('data-fenster="dokument"'),
                        self.HTML.index('id="spalte-rechts"'))


if __name__ == "__main__":
    unittest.main()
