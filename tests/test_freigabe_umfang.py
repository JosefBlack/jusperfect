"""Was freigegeben wird, muss gesehen worden sein – und wem die Akte entzogen
wurde, der schreibt nicht mehr hinein.

Befunde F06 und F07 der Zweitprüfung vom 05.10.2026, Gegenproben 05 und 06.

**F06.** Bestätigt wurde die Prüfsumme des *Textes*. Geschrieben werden vier
Dinge: Akte, Art, Betreff und Text. Fenster A lud den Entwurf, Fenster B
änderte nur den Betreff, Fenster A gab mit der alten Prüfsumme frei – und der
neue, dort nie gesehene Betreff ging in den Vermerktext **und** in den Titel
nach jur|nodes. Die Kryptografie war dabei nicht gebrochen; sie signierte nur
das, was ihr gegeben wurde, und das war zu wenig.

**F07.** Geprüft wurde allein die Erstellerkennung. Ein Nutzer, dem die Akte
entzogen worden war, bekam auf die Sitzung richtig 403 – und konnte denselben
Entwurf weiter lesen und freigeben, also in genau diese Akte schreiben.

Dass in dieser Kanzlei alle alle Akten sehen, ändert daran nichts: Die Lücke
bestand für den eingeschränkten Betrieb, den das Programm ausdrücklich kann.
"""

from __future__ import annotations

import json
import unittest

from jusperfect.security.approval import text_pruefsumme
from jusperfect.services.entwuerfe import FREIGABE_FASSUNG, freigabevorlage
from tests.hilfen import client, dienste
from tests.test_web_ablauf import SkriptProvider

AKTE = "VU-2026-0042"
ECHT = "D1-S1-P1"


def _entwurf(d=None, betreff="Gesehener Betreff"):
    p = SkriptProvider([json.dumps({"betreff": betreff, "text": f"Sachstand [Q: {ECHT}]."})])
    d = d or dienste(provider=p)
    d.analyse._ausgang._provider = p
    d.entwuerfe._ausgang._provider = p
    c = client(d, "ra-weber")
    sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
    c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
    entwurf = c.post(f"/api/sitzungen/{sid}/entwuerfe", json={"art": "mandant"}).json()
    return d, c, sid, entwurf


class DieFreigabeDecktAllesAbWasGeschriebenWird(unittest.TestCase):
    """Gegenprobe 05, in richtiger Polarität."""

    def test_ein_geaenderter_betreff_macht_die_freigabe_ungueltig(self):
        d, c, sid, entwurf = _entwurf()
        # Das zweite Fenster ändert **nur** den Betreff.
        geaendert = c.put(f"/api/entwuerfe/{entwurf['id']}",
                          json={"betreff": "Heimlich geändert", "text": entwurf["text"]})
        self.assertEqual(geaendert.status_code, 200)
        # Das erste Fenster gibt mit seiner alten Prüfsumme frei.
        antwort = c.post(f"/api/entwuerfe/{entwurf['id']}/freigabe",
                         json={"bestaetigung": True,
                               "freigabe_pruefsumme": entwurf["freigabe_pruefsumme"]})
        self.assertEqual(antwort.status_code, 422, antwort.text)
        self.assertEqual(d.adapter.geschriebene_vermerke, [])
        self.assertIn("Betreff oder Text", antwort.json()["fehler"])

    def test_mit_der_neuen_pruefsumme_geht_es(self):
        """Die Sperre ist kein Hindernis, sondern ein Hinweis: neu laden."""
        d, c, sid, entwurf = _entwurf()
        neu = c.put(f"/api/entwuerfe/{entwurf['id']}",
                    json={"betreff": "Bewusst geändert", "text": entwurf["text"]}).json()
        antwort = c.post(f"/api/entwuerfe/{entwurf['id']}/freigabe",
                         json={"bestaetigung": True,
                               "freigabe_pruefsumme": neu["freigabe_pruefsumme"]})
        self.assertEqual(antwort.status_code, 200, antwort.text)
        self.assertIn("Bewusst geändert", d.adapter.geschriebene_vermerke[0]["titel"])

    def test_die_vorlage_nennt_jedes_feld_das_geschrieben_wird(self):
        """Der eigentliche Beweis: Ändert sich eines, ändert sich die Summe."""
        from jusperfect.domain.models import Entwurf, EntwurfArt

        grund = Entwurf(id="x", akte_id=AKTE, art=EntwurfArt.MANDANT, betreff="B",
                        text="T", erstellt_von="ra-weber")
        summe = text_pruefsumme(freigabevorlage(grund))
        for feld, wert in (("akte_id", "AR-2026-0115"), ("art", EntwurfArt.RSV),
                           ("betreff", "anders"), ("text", "anders")):
            with self.subTest(feld=feld):
                anders = grund.model_copy(update={feld: wert})
                self.assertNotEqual(text_pruefsumme(freigabevorlage(anders)), summe)

    def test_die_vorlage_traegt_eine_fassungsnummer(self):
        """Kommt ein Feld hinzu, passen alte Prüfsummen nicht mehr – und das
        ist richtig: Sie bezeugen eine Ansicht, die es nicht mehr gibt."""
        from jusperfect.domain.models import Entwurf, EntwurfArt

        vorlage = freigabevorlage(Entwurf(id="x", akte_id=AKTE, art=EntwurfArt.MANDANT,
                                          betreff="B", text="T", erstellt_von="u"))
        self.assertTrue(vorlage.startswith(f"jusperfect-freigabe/{FREIGABE_FASSUNG}"))
        for feld in ("akte:", "art:", "betreff:", "text:"):
            self.assertIn(feld, vorlage)

    def test_zweimal_freigeben_schreibt_nur_einen_vermerk(self):
        """Vorher wurde erst geschrieben und dann der Status gesetzt."""
        d, c, sid, entwurf = _entwurf()
        daten = {"bestaetigung": True, "freigabe_pruefsumme": entwurf["freigabe_pruefsumme"]}
        self.assertEqual(c.post(f"/api/entwuerfe/{entwurf['id']}/freigabe", json=daten).status_code, 200)
        zweite = c.post(f"/api/entwuerfe/{entwurf['id']}/freigabe", json=daten)
        self.assertEqual(zweite.status_code, 422)
        self.assertEqual(len(d.adapter.geschriebene_vermerke), 1)

    def test_ein_fehlschlag_beim_schreiben_laesst_den_entwurf_offen(self):
        """Sonst wäre er gesperrt, ohne dass etwas in der Akte steht."""
        d, c, sid, entwurf = _entwurf()

        def platzt(*args, **kwargs):
            raise RuntimeError("jur|nodes antwortet nicht")

        d.adapter.vermerk_schreiben = platzt
        daten = {"bestaetigung": True, "freigabe_pruefsumme": entwurf["freigabe_pruefsumme"]}
        self.assertEqual(c.post(f"/api/entwuerfe/{entwurf['id']}/freigabe", json=daten).status_code, 500)
        self.assertEqual(c.get(f"/api/entwuerfe/{entwurf['id']}").json()["status"], "entwurf")


class EinEntzugDerAkteSchliesstDenEntwurf(unittest.TestCase):
    """Gegenprobe 06, in richtiger Polarität."""

    def _entziehen(self, d) -> None:
        d.berechtigungen._nutzer["ra-weber"].akten = []

    def test_lesen_ist_nach_dem_entzug_verweigert(self):
        d, c, sid, entwurf = _entwurf()
        self.assertEqual(c.get(f"/api/sitzungen/{sid}").status_code, 200)
        self._entziehen(d)
        self.assertEqual(c.get(f"/api/sitzungen/{sid}").status_code, 403)
        self.assertEqual(c.get(f"/api/entwuerfe/{entwurf['id']}").status_code, 403)

    def test_freigeben_ist_nach_dem_entzug_verweigert(self):
        """Der gefährlichere der beiden Wege: Er schreibt in die Akte."""
        d, c, sid, entwurf = _entwurf()
        self._entziehen(d)
        antwort = c.post(f"/api/entwuerfe/{entwurf['id']}/freigabe",
                         json={"bestaetigung": True,
                               "freigabe_pruefsumme": entwurf["freigabe_pruefsumme"]})
        self.assertEqual(antwort.status_code, 403, antwort.text)
        self.assertEqual(d.adapter.geschriebene_vermerke, [])

    def test_bearbeiten_und_verwerfen_ebenso(self):
        d, c, sid, entwurf = _entwurf()
        self._entziehen(d)
        self.assertEqual(c.put(f"/api/entwuerfe/{entwurf['id']}",
                               json={"betreff": "x", "text": "y"}).status_code, 403)
        self.assertEqual(c.delete(f"/api/entwuerfe/{entwurf['id']}").status_code, 403)

    def test_geprueft_wird_bei_jedem_zugriff_neu(self):
        """Nicht beim Anlegen: Eine Rechteänderung wirkte sonst erst beim
        nächsten Entwurf, und der vorbereitete Schreibweg bliebe offen."""
        d, c, sid, entwurf = _entwurf()
        self.assertEqual(c.get(f"/api/entwuerfe/{entwurf['id']}").status_code, 200)
        self._entziehen(d)
        self.assertEqual(c.get(f"/api/entwuerfe/{entwurf['id']}").status_code, 403)
        d.berechtigungen._nutzer["ra-weber"].akten = ["*"]
        self.assertEqual(c.get(f"/api/entwuerfe/{entwurf['id']}").status_code, 200)

    def test_die_kanzleiregel_alle_sehen_alles_bleibt_unberuehrt(self):
        d, c, sid, entwurf = _entwurf()
        self.assertEqual(d.berechtigungen._nutzer["ra-weber"].akten, ["*"])
        self.assertEqual(c.get(f"/api/entwuerfe/{entwurf['id']}").status_code, 200)


if __name__ == "__main__":
    unittest.main()
