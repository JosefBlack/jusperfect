"""Die KI schlägt einen Auftrag vor – ein Mensch legt ihn an.

Aus der Kanzlei: „Ich denke auch einen Wissenstempel bauen, dass sich KI
gleiche Vorgänge merkt. Wie kann dieser Wissenstempel gefüttert werden, kann
die KI entsprechende Vorschläge machen."

Die gefährliche Fassung eines solchen Speichers ist die, die sich merkt, was in
Akte A stand, und es bei Akte B heranzieht. Sie trägt das Mandantengeheimnis
über die Mandatsgrenze, und zwar unbemerkt – niemand sieht einem Satz an, woher
er kommt.

Deshalb prüft diese Datei zuerst das, was den Unterschied ausmacht: **Bei
einem Vorschlag geht die Akte nicht mit hinaus.** Nicht als Passage, nicht als
Entwurf. Was hinausgeht, ist die Anweisung, die der Bearbeiter selbst getippt
hat – und die sieht er hinterher wieder.

Danach die zweite Hälfte: Angelegt wird nichts ohne Freigabe, und was die
Kanzlei selbst geschrieben hat, wird nie überschrieben.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.hilfen import client, dienste, einstellungen

from jusperfect.domain.models import Akte, Entwurf, EntwurfArt, Kosten, Sitzung
from jusperfect.security.identitaet import Identitaet
from jusperfect.services.auftraege import AuftragFehler, Auftragsdienst
from jusperfect.services.auftragsvorschlag import (
    Auftragsvorschlag,
    Vorschlagsdienst,
    VorschlagFehler,
    dateiname,
)

RA = Identitaet(nutzer_id="ra-weber", anzeigename="RA Dr. Weber", gruppen=("alle-akten",))

# Die Anweisung eines einzelnen Falls - mit allem, was nicht in einen
# Textbaustein gehoert.
ANWEISUNG = ("Schreibe an die Musterhaft-Versicherung wegen des Nutzungsausfalls von Frau "
             "Ilse Krämer, 14 Tage zu 45,00 EUR, Unfall vom 12.03.2026, "
             "Aktenzeichen 42/26 VU.")


class _Antwort:
    def __init__(self, text: str) -> None:
        self.text, self.modell, self.quellen = text, "probe", []


class _Durchgang:
    def __init__(self, text: str) -> None:
        self.antwort, self.kosten = _Antwort(text), Kosten()


class _Ausgang:
    """Merkt sich, was wirklich hinausgegangen wäre."""

    def __init__(self, antwort: str) -> None:
        self._antwort = antwort
        self.aufrufe: list[tuple] = []

    def fragen(self, kontext, system, material, aufgabe):
        self.aufrufe.append((kontext, system, material, aufgabe))
        return _Durchgang(self._antwort)


def _sitzung() -> Sitzung:
    return Sitzung(id="s1", akte_id="VU-2026-0042", nutzer_id="ra-weber",
                   akte=Akte(id="VU-2026-0042", aktenzeichen="42/26 VU",
                             bezeichnung="Krämer ./. Sorge", rechtsgebiet="Verkehrsrecht"))


def _entwurf() -> Entwurf:
    return Entwurf(id="e1", akte_id="VU-2026-0042", art=EntwurfArt.VERSICHERUNG,
                   betreff="Nutzungsausfall Krämer", text="Sehr geehrte Damen und Herren …",
                   erstellt_von="ra-weber")


_GUTE_ANTWORT = ('{"titel": "Nutzungsausfall gegenüber der Haftpflichtversicherung",'
                 ' "anweisung": "Entwirf ein Anspruchsschreiben an die gegnerische '
                 'Haftpflichtversicherung zum Nutzungsausfall. Nenne Ausfalldauer und '
                 'Tagessatz jeweils mit Beleg und weise auf die Schadensminderungspflicht hin.",'
                 ' "hinweis": "Tagessatztabelle der Kanzlei ergänzen."}')


class DieAkteGehtNichtMit(unittest.TestCase):
    """Der Kern der Sache."""

    def test_es_geht_kein_material_hinaus(self):
        ausgang = _Ausgang(_GUTE_ANTWORT)
        Vorschlagsdienst(ausgang).vorschlagen(RA, _sitzung(), _entwurf(), ANWEISUNG)

        _kontext, _system, material, _aufgabe = ausgang.aufrufe[0]
        self.assertEqual("", material,
                         "Es ist Material hinausgegangen – damit könnten Aktentatsachen "
                         "in eine Datei geraten, die bei jeder anderen Akte mitgeht.")

    def test_der_entwurfstext_geht_nicht_hinaus(self):
        ausgang = _Ausgang(_GUTE_ANTWORT)
        entwurf = _entwurf()
        Vorschlagsdienst(ausgang).vorschlagen(RA, _sitzung(), entwurf, ANWEISUNG)

        alles = " ".join(str(teil) for teil in ausgang.aufrufe[0])
        self.assertNotIn(entwurf.text, alles)
        self.assertNotIn(entwurf.betreff, alles)

    def test_hinaus_geht_die_anweisung_des_bearbeiters(self):
        """Sie muss mit – sonst gäbe es nichts zu verallgemeinern."""
        ausgang = _Ausgang(_GUTE_ANTWORT)
        Vorschlagsdienst(ausgang).vorschlagen(RA, _sitzung(), _entwurf(), ANWEISUNG)

        _kontext, _system, _material, aufgabe = ausgang.aufrufe[0]
        self.assertIn(ANWEISUNG, aufgabe)

    def test_die_aufgabe_verlangt_das_weglassen(self):
        ausgang = _Ausgang(_GUTE_ANTWORT)
        Vorschlagsdienst(ausgang).vorschlagen(RA, _sitzung(), _entwurf(), ANWEISUNG)

        aufgabe = ausgang.aufrufe[0][3]
        self.assertIn("STRENG WEGLASSEN", aufgabe)
        for wort in ("Namen", "Beträge", "Daten", "Aktenzeichen"):
            with self.subTest(wort=wort):
                self.assertIn(wort, aufgabe)

    def test_der_vorgang_wird_als_solcher_vermerkt(self):
        ausgang = _Ausgang(_GUTE_ANTWORT)
        Vorschlagsdienst(ausgang).vorschlagen(RA, _sitzung(), _entwurf(), ANWEISUNG)
        self.assertEqual("auftragsvorschlag", ausgang.aufrufe[0][0].funktion)


class DerVorschlag(unittest.TestCase):

    def test_titel_anweisung_und_hinweis_kommen_an(self):
        v = Vorschlagsdienst(_Ausgang(_GUTE_ANTWORT)).vorschlagen(
            RA, _sitzung(), _entwurf(), ANWEISUNG)
        self.assertIn("Nutzungsausfall", v.titel)
        self.assertIn("Anspruchsschreiben", v.anweisung)
        self.assertIn("Tagessatztabelle", v.hinweis)
        self.assertTrue(v.dateiname.endswith(".txt"))

    def test_ohne_anweisung_gibt_es_nichts_zu_verallgemeinern(self):
        with self.assertRaises(VorschlagFehler) as fehler:
            Vorschlagsdienst(_Ausgang(_GUTE_ANTWORT)).vorschlagen(
                RA, _sitzung(), _entwurf(), "   ")
        self.assertIn("Anweisung", str(fehler.exception))

    def test_unbrauchbare_antwort_wird_gesagt(self):
        with self.assertRaises(VorschlagFehler):
            Vorschlagsdienst(_Ausgang("kein JSON")).vorschlagen(
                RA, _sitzung(), _entwurf(), ANWEISUNG)

    def test_aus_dem_titel_wird_ein_tragfaehiger_dateiname(self):
        self.assertEqual("Nutzungsausfall Musterhaft.txt", dateiname("Nutzungsausfall / Musterhaft"))
        self.assertEqual("Kündigung Eigenbedarf.txt", dateiname("  Kündigung: Eigenbedarf  "))
        self.assertEqual("Eigener Auftrag.txt", dateiname(""))
        self.assertTrue(len(dateiname("x" * 200)) <= 64)

    def test_kein_titel_wird_zu_einem_pfad(self):
        """Der Titel kommt vom Modell – er darf nie in einen Ordner führen."""
        for titel in ("../../etc/passwd", "C:\\Windows\\System32", "a/b/c", ".versteckt"):
            with self.subTest(titel=titel):
                name = dateiname(titel)
                for zeichen in ("/", "\\", ":", ".."):
                    self.assertNotIn(zeichen, name.removesuffix(".txt"), name)
                self.assertFalse(name.startswith("."), name)


class AngelegtWirdNurMitFreigabe(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ordner = Path(self._tmp.name)
        self.dienst = Auftragsdienst(str(self.ordner))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_ein_neuer_auftrag_entsteht_als_datei(self):
        a = self.dienst.anlegen("Nutzungsausfall.txt",
                                "Entwirf ein Anspruchsschreiben zum Nutzungsausfall.")
        self.assertTrue((self.ordner / "Nutzungsausfall.txt").is_file())
        self.assertEqual("Nutzungsausfall.txt", a.name)
        self.assertIn("Anspruchsschreiben", a.anweisung)

    def test_ein_unterordner_fuer_das_rechtsgebiet_geht(self):
        a = self.dienst.anlegen("Verkehrsrecht/Nutzungsausfall.txt",
                                "Entwirf ein Anspruchsschreiben zum Nutzungsausfall.")
        self.assertEqual("Verkehrsrecht", a.kategorie)

    def test_vorhandenes_wird_nie_ueberschrieben(self):
        """Was die Kanzlei selbst geschrieben hat, darf ein Vorschlag nicht verdrängen."""
        eigenes = self.ordner / "Nutzungsausfall.txt"
        eigenes.write_text("Der über Jahre gefeilte Text der Kanzlei.", encoding="utf-8")

        with self.assertRaises(AuftragFehler) as fehler:
            self.dienst.anlegen("Nutzungsausfall.txt",
                                "Entwirf ein Anspruchsschreiben zum Nutzungsausfall.")

        self.assertIn("gibt es bereits", str(fehler.exception))
        self.assertEqual("Der über Jahre gefeilte Text der Kanzlei.",
                         eigenes.read_text(encoding="utf-8"))

    def test_kein_name_fuehrt_aus_dem_ordner_heraus(self):
        for name in ("../draussen.txt", "/etc/passwd.txt", "a/b/c.txt",
                     ".versteckt.txt", "keine_endung", "Muster.exe"):
            with self.subTest(name=name):
                with self.assertRaises(AuftragFehler):
                    self.dienst.anlegen(name, "Entwirf ein Schreiben mit genug Text darin.")
        self.assertEqual([], list(self.ordner.rglob("*")))

    def test_ohne_anweisung_wird_nichts_angelegt(self):
        with self.assertRaises(AuftragFehler) as fehler:
            self.dienst.anlegen("Leer.txt", "kurz")
        self.assertIn("Anweisung", str(fehler.exception))
        self.assertFalse((self.ordner / "Leer.txt").exists())

    def test_ein_auftrag_der_zu_lang_waere_wird_abgewiesen(self):
        with self.assertRaises(AuftragFehler) as fehler:
            self.dienst.anlegen("Lang.txt", "Entwirf ein Schreiben. " * 5000)
        self.assertIn("zu lang", str(fehler.exception))
        self.assertFalse((self.ordner / "Lang.txt").exists())

    def test_material_hinter_der_trennlinie_bleibt_erhalten(self):
        a = self.dienst.anlegen(
            "Mit Material.txt",
            "Entwirf ein Anspruchsschreiben zum Nutzungsausfall.\n\n"
            "--- Rechtslage ---\n\nZum Nutzungsausfall gilt …")
        self.assertIn("Anspruchsschreiben", a.anweisung)
        self.assertIn("Zum Nutzungsausfall gilt", a.material)


class DerWegDurchDasProgramm(unittest.TestCase):
    """Die beiden Schaltstellen, so wie der Browser sie aufruft.

    Die Dienste oben sind einzeln geprüft. Diese Klasse prüft das, was dazwischen
    liegt – und genau dort steckte der Fehler: Der Auftrag wurde angelegt, und
    der Bearbeiter sah trotzdem „Interner Fehler", weil die Zeile danach eine
    Funktion rief, die es nicht gab.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ordner = Path(self._tmp.name)
        d = dienste(einstellungen=einstellungen(JUSPERFECT_AUFTRAG_ORDNER=str(self.ordner)))
        self.c = client(d, "ra-weber")
        self.sid = self.c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        self.c.post(f"/api/sitzungen/{self.sid}/dokumente", json={"dokument_ids": ["D-001", "D-002"]})
        self.eid = self.c.post(f"/api/sitzungen/{self.sid}/entwuerfe",
                               json={"art": "versicherung", "anweisung": ANWEISUNG}).json()["id"]

    def _vorschlag(self) -> dict:
        r = self.c.post(f"/api/sitzungen/{self.sid}/auftragsvorschlag",
                        json={"entwurf_id": self.eid, "anweisung": ANWEISUNG})
        self.assertEqual(200, r.status_code, r.text)
        return r.json()["vorschlag"]

    def test_der_vorschlag_kommt_zurueck_und_legt_noch_nichts_an(self):
        v = self._vorschlag()
        self.assertTrue(v["anweisung"].strip())
        self.assertEqual([], list(self.ordner.rglob("*.txt")))

    def test_erst_der_zweite_aufruf_legt_die_datei_an(self):
        v = self._vorschlag()
        r = self.c.post("/api/auftraege", json={"name": v["dateiname"], "text": v["anweisung"]})
        self.assertEqual(201, r.status_code, r.text)
        datei = self.ordner / v["dateiname"]
        self.assertTrue(datei.is_file())
        self.assertEqual(v["anweisung"], datei.read_text(encoding="utf-8").strip())

    def test_der_angelegte_auftrag_steht_danach_in_der_liste(self):
        v = self._vorschlag()
        self.c.post("/api/auftraege", json={"name": v["dateiname"], "text": v["anweisung"]})
        namen = [e["name"] for e in self.c.get("/api/auftraege").json()["eintraege"]]
        self.assertIn(v["dateiname"], namen)

    def test_ein_zweites_mal_derselbe_name_wird_abgewiesen(self):
        v = self._vorschlag()
        self.c.post("/api/auftraege", json={"name": v["dateiname"], "text": v["anweisung"]})
        r = self.c.post("/api/auftraege", json={"name": v["dateiname"], "text": "Ein ganz anderer Text darin."})
        self.assertEqual(422, r.status_code)
        self.assertIn("gibt es bereits", r.json()["fehler"])

    def test_ohne_anweisung_gibt_es_keinen_vorschlag(self):
        r = self.c.post(f"/api/sitzungen/{self.sid}/auftragsvorschlag",
                        json={"entwurf_id": self.eid, "anweisung": ""})
        self.assertEqual(422, r.status_code)


class OhneKiWirdNichtsBehauptet(unittest.TestCase):
    """Der Demo-Anbieter muss den Weg zeigen, ohne zu verallgemeinern.

    Ein Vorschlag landet in einer Datei, die danach bei jeder Akte mitgeht.
    Ein Demo-Anbieter, der so täte, als hätte er verallgemeinert, wäre dort am
    gefährlichsten.
    """

    def _vorschlag(self) -> Auftragsvorschlag:
        from jusperfect.providers.demo import DemoProvider

        class _Roh:
            def __init__(self) -> None:
                self._p = DemoProvider()

            def fragen(self, kontext, system, material, aufgabe):
                return _Durchgang(self._p.fragen(system, material, aufgabe).text)

        return Vorschlagsdienst(_Roh()).vorschlagen(RA, _sitzung(), _entwurf(), ANWEISUNG)

    def test_der_weg_laeuft_auch_ohne_ki_durch(self):
        v = self._vorschlag()
        self.assertTrue(v.anweisung.strip())
        self.assertTrue(v.dateiname.endswith(".txt"))

    def test_datum_betrag_und_aktenzeichen_sind_ersetzt(self):
        v = self._vorschlag()
        for einzelfall in ("12.03.2026", "45,00 EUR", "42/26 VU"):
            with self.subTest(einzelfall=einzelfall):
                self.assertNotIn(einzelfall, v.anweisung)

    def test_es_steht_dabei_dass_von_hand_nachzuarbeiten_ist(self):
        self.assertIn("von Hand", self._vorschlag().hinweis)


if __name__ == "__main__":
    unittest.main()
