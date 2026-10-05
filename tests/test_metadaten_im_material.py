"""Was das Modell über die Akte erfährt, bevor es den ersten Satz liest.

Befund F11 der Zweitprüfung vom 05.10.2026, Gegenprobe 09 – und die
Entscheidung der Kanzlei vom selben Tag (`F11-VORSCHLAG.md`, `[KANZLEI 18]`).

**Der Befund.** Die Zusage „das Modell sieht keine Dateinamen und keine
Aktenzeichen" war falsch. Beides ging als Text mit: das Aktenzeichen in der
ersten Materialzeile, der Dokumenttitel in jeder Passagenüberschrift. Und
gegen den echten Server ist der Titel der **Dateiname** – die Beschreibung des
Herstellers (API 1.0.2) kennt für eine Datei kein Titelfeld, nur `fileName`.

**Die Entscheidung.** Vom Titel geht nur noch die **Art** des Schriftstücks
hinaus, und auch die nur als Wort aus einer Liste im Programm – nie als Text
aus dem Dateinamen. Das Aktenzeichen geht nur noch beim **Entwurf** mit, der
„Unser Zeichen" trägt.

**Die Richtung des Irrtums stimmt**, und darauf kommt es an: Erkennt die Liste
nichts, heißt das Dokument nur „Dokument 2". Eine lückenhafte Liste führt zu
weniger Auskunft, nie zu mehr – das Gegenteil der Fristenwortlisten, die am
Vormittag desselben Tages genau deshalb aufgegeben wurden.
"""

from __future__ import annotations

import unittest

from jusperfect.domain.models import Passage
from jusperfect.services import prompts
from tests.hilfen import client, dienste
from tests.test_web_ablauf import SkriptProvider

AKTE = "VU-2026-0042"


def _passage(titel: str, kennung: str = "D2-S1-P1") -> Passage:
    return Passage(kennung=kennung, dokument_id="D-002", dokument_titel=titel,
                   seite=1, text="Inhalt")


class AusDemTitelGehtNurDieArtHinaus(unittest.TestCase):
    def test_die_art_bleibt(self):
        """Ein Kündigungsschreiben wiegt anders als eine Telefonnotiz – das
        braucht das Modell, und es verrät niemanden."""
        for titel, erwartet in (
            ("Aktenvermerk Erstgespräch", "Dokument 2 – Aktenvermerk"),
            ("Kündigungsschreiben", "Dokument 2 – Kündigung"),
            ("Schlussrechnung Nr. 4711", "Dokument 2 – Schlussrechnung"),
            ("Mietvertrag (Scan)", "Dokument 2 – Mietvertrag"),
        ):
            with self.subTest(titel=titel):
                self.assertEqual(prompts.dokumentbezeichnung(_passage(titel)), erwartet)

    def test_ein_name_im_dateinamen_geht_nicht_mit(self):
        """Der Fall, um den es geht."""
        bezeichnung = prompts.dokumentbezeichnung(
            _passage("Kündigung Reinhold-Özdemir 04.05.pdf"))
        self.assertEqual(bezeichnung, "Dokument 2 – Kündigung")
        self.assertNotIn("Reinhold", bezeichnung)

    def test_ein_unbedachter_dateiname_geht_gar_nicht_mit(self):
        """„Vergleich-Entwurf-NICHT-VERSENDEN.docx" – der Name, an den niemand
        gedacht hat. Er bleibt vollständig drinnen."""
        self.assertEqual(
            prompts.dokumentbezeichnung(_passage("Vergleich-Entwurf-NICHT-VERSENDEN.docx")),
            "Dokument 2")

    def test_was_die_liste_nicht_kennt_wird_nicht_genannt(self):
        """Die Richtung des Irrtums: weniger Auskunft, nie mehr."""
        for titel in ("scan0042.pdf", "IMG_2291", "Unterlagen Frau Özdemir", ""):
            with self.subTest(titel=titel):
                self.assertEqual(prompts.dokumentbezeichnung(_passage(titel)), "Dokument 2")

    def test_hinaus_geht_das_wort_der_liste_nicht_das_des_dateinamens(self):
        """Der Unterschied ist der ganze Punkt: Ausgegeben wird nie ein Stück
        des Titels, sondern immer ein Wort aus dem Programm."""
        bezeichnung = prompts.dokumentbezeichnung(_passage("KÜNDIGUNGSSCHREIBEN-FINAL"))
        self.assertEqual(bezeichnung, "Dokument 2 – Kündigung")
        self.assertNotIn("FINAL", bezeichnung)

    def test_die_nummer_stammt_aus_der_kennung(self):
        """Sie ist dieselbe, die in jedem Beleg steht – so lässt sich die
        Passage auch dann zuordnen, wenn das Dokument keinen Namen hat."""
        self.assertEqual(prompts.dokumentbezeichnung(_passage("x", "D17-S3-P2")),
                         "Dokument 17")

    def test_die_vordere_haelfte_eines_kompositums_gewinnt(self):
        """„Schreiben" sagt weniger als „Kündigung". Nach Länge allein stand
        hier erst das falsche Wort – beide sind neun Zeichen lang."""
        self.assertEqual(prompts.dokumentbezeichnung(_passage("Kündigungsschreiben")),
                         "Dokument 2 – Kündigung")


class DasAktenzeichenGehtNurBeimEntwurfMit(unittest.TestCase):
    def _material(self, mit_aktenzeichen: bool) -> str:
        from jusperfect.domain.models import Akte

        akte = Akte(id="A", aktenzeichen="042/26 VU", bezeichnung="Testmann ./. Musterhaft",
                    rechtsgebiet="Verkehrsrecht")
        return prompts.material_bauen(akte, [], [], [_passage("Kündigungsschreiben")],
                                      mit_aktenzeichen=mit_aktenzeichen)

    def test_ohne_schalter_steht_es_nicht_da(self):
        material = self._material(False)
        self.assertNotIn("042/26 VU", material)
        self.assertIn("## Akte: Testmann ./. Musterhaft", material)

    def test_mit_schalter_steht_es_da(self):
        self.assertIn("## Akte 042/26 VU: Testmann ./. Musterhaft", self._material(True))

    def test_das_kurzrubrum_bleibt_in_beiden_faellen(self):
        """Es geht **absichtlich** hinaus: Das Modell braucht die Rollen, und
        dieselben Namen stehen im Dokumenttext ohnehin. Anonym ist die
        Übermittlung dadurch nicht – so steht es in der DSFA, Abschnitt 3.2."""
        for schalter in (True, False):
            self.assertIn("Testmann ./. Musterhaft", self._material(schalter))

    def test_der_gedaechtnisweg_fuehrt_es_ebenfalls_nicht(self):
        from jusperfect.domain.models import Akte

        akte = Akte(id="A", aktenzeichen="042/26 VU", bezeichnung="Testmann ./. Musterhaft")
        material = prompts.material_gedaechtnis(akte, [], [], "Sachverhalt [Q: D1-S1-P1]", [])
        self.assertNotIn("042/26 VU", material)


class AmEchtenWegNachgeprueft(unittest.TestCase):
    """Nicht nur die Funktion – der Aufruf, wie er wirklich hinausgeht."""

    def _aufrufe(self, *, entwurf: bool):
        import json

        p = SkriptProvider([json.dumps({"betreff": "Test", "text": "Sachstand [Q: D1-S1-P1]."})]
                           if entwurf else ["Antwort [Q: D1-S1-P1]"])
        d = dienste(provider=p)
        c = client(d, "ra-weber")
        sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
        if entwurf:
            c.post(f"/api/sitzungen/{sid}/entwuerfe", json={"art": "mandant"})
        else:
            c.post(f"/api/sitzungen/{sid}/frage", json={"frage": "Wie schnell?"})
        return p.aufrufe[-1]["material"]

    def test_die_frage_traegt_weder_dateiname_noch_aktenzeichen(self):
        material = self._aufrufe(entwurf=False)
        self.assertNotIn("Unfallschilderung Mandant", material)
        self.assertNotIn("042/26 VU", material)
        self.assertIn("Dokument 1", material)

    def test_der_entwurf_traegt_das_aktenzeichen_aber_keinen_dateinamen(self):
        material = self._aufrufe(entwurf=True)
        self.assertIn("042/26 VU", material)
        self.assertNotIn("Unfallschilderung Mandant", material)


class DieBelegeBleibenUnberuehrt(unittest.TestCase):
    """Die gute Nachricht des Vorschlags, und sie gehört geprüft.

    Der Titel in der Belegkarte kommt aus der Passage, die das Programm selbst
    baut. Er ging nie durch das Modell – die Ersetzung im Material kostet ihn
    also nicht.
    """

    def test_die_fundstelle_nennt_weiterhin_den_richtigen_titel(self):
        d = dienste(provider=SkriptProvider(["Der Unfall war auf der B 27 [Q: D1-S1-P1]"]))
        c = client(d, "ra-weber")
        sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
        antwort = c.post(f"/api/sitzungen/{sid}/frage", json={"frage": "Wie schnell?"}).json()
        self.assertTrue(antwort["quellen"])
        self.assertEqual(antwort["quellen"][0]["dokument_titel"], "Unfallschilderung Mandant")

    def test_die_passagenliste_der_oberflaeche_ebenso(self):
        d = dienste()
        c = client(d, "ra-weber")
        sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
        passagen = c.get(f"/api/sitzungen/{sid}/passagen").json()["passagen"]
        self.assertEqual(passagen[0]["dokument_titel"], "Unfallschilderung Mandant")


class DieListeBleibtNachpruefbar(unittest.TestCase):
    def test_sie_enthaelt_keinen_namen_und_keine_zahl(self):
        """Sie steht im Programm und kann deshalb nichts aus einer Akte
        tragen. Geprüft wird es trotzdem – sie ist der einzige Weg, auf dem
        noch ein Wort nach draußen geht."""
        import re

        for art in prompts._DOKUMENTARTEN:
            with self.subTest(art=art):
                self.assertTrue(re.fullmatch(r"[A-Za-zÄÖÜäöüß]+", art), art)

    def test_sie_baut_auf_der_liste_des_zeitstrahls_auf(self):
        """Zwei Listen nebeneinander laufen mit der Zeit auseinander."""
        from jusperfect.services.chronologie import SCHRIFTSTUECKARTEN

        self.assertTrue(set(SCHRIFTSTUECKARTEN) <= set(prompts._DOKUMENTARTEN))


if __name__ == "__main__":
    unittest.main()
