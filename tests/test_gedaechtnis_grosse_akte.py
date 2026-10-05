"""Die grosse Akte ins Gedächtnis lesen – Portion für Portion, ohne Verlust.

Eine echte Akte passt nicht in einen Modellaufruf. Sie wird deshalb in
Portionen gelesen, und jede Portion bekommt den bisherigen Lebenssachverhalt
als Faden mit: Sie knüpft an ihn an, statt neu anzufangen. **Angehängt wird
immer, umgeschrieben nie** – was einmal belegt vermerkt ist, bleibt stehen.
Das ist die Zusage, auf der dieses Gedächtnis beruht, und der Grund, warum es
gegen das Vergessen hilft und nicht bloss dagegen, dass etwas nicht gelesen
wurde.

Genau daraus folgt aber eine Grenze, und diese Datei hält beide Seiten fest:

* Der Lebenssachverhalt wächst und geht bei jeder weiteren Portion mit. Also
  muss die Portion um ihn kleiner werden – sonst wächst jeder Aufruf über die
  Zeichengrenze hinaus. Bei acht Dokumenten fällt das nicht auf, bei fünfzig
  läuft der Aufruf auf.
* Irgendwann füllt der Lebenssachverhalt den Platz allein. Dann ist Schluss,
  und das wird gesagt. Ihn an dieser Stelle zusammenfassen zu lassen wäre
  genau der stille Verlust, den dieses Gedächtnis verhindern soll.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jusperfect.gedaechtnis.base import GedaechtnisFehler
from jusperfect.providers.base import Nutzung, ProviderAntwort, ProviderFehler
from tests.hilfen import client, dienste, einstellungen

GRENZE = 40_000
AKTE = "BA-2026-9001"


class PortionsProvider:
    """Antwortet je Aufruf mit einem eigenen Satz – belegt auf die erste Passage."""

    modell_id = "skript"

    def __init__(self, *, stumm_ab: int | None = None, fehler_ab: int | None = None) -> None:
        self.aufrufe: list[dict] = []
        self.stumm_ab = stumm_ab
        self.fehler_ab = fehler_ab

    def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        nummer = len(self.aufrufe) + 1
        if self.fehler_ab is not None and nummer >= self.fehler_ab:
            raise ProviderFehler("Der Anbieter ist nicht erreichbar.")
        self.aufrufe.append({"material": material, "aufgabe": aufgabe, "modell": modell_id})
        if self.stumm_ab is not None and nummer >= self.stumm_ab:
            # Nichts Belegbares – etwa ein Abschnitt aus reinen Aufmassblättern.
            return ProviderAntwort(text="Hierzu ist nichts zu vermerken.",
                                   nutzung=Nutzung(100, 20), modell=modell_id or self.modell_id)
        erste = material.split("### Passage ")[1].split(" ")[0]
        # Bewusst ausführlich: Ein echter Lebenssachverhalt wächst je Portion um
        # einige tausend Zeichen. Nur dann ist zu sehen, dass die nächste
        # Portion um ihn kleiner wird.
        breit = "Der Vorgang ist im Bautagebuch vermerkt und dort gegengezeichnet. " * 45
        return ProviderAntwort(text=f"Feststellung {nummer}. {breit} [Q: {erste}]",
                               nutzung=Nutzung(100, 20), modell=modell_id or self.modell_id)


class _GrosseAkte(unittest.TestCase):
    DOKUMENTE = 8
    ZEICHEN = 9_000

    def _aufbau(self, provider):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        akten = Path(tmp.name) / "akten"
        ordner = akten / AKTE
        ordner.mkdir(parents=True)
        absatz = ("Die Bauleitung hat die Ausfuehrung stichprobenartig ueberwacht und das "
                  "Ergebnis im Bautagebuch vermerkt. ") * 12
        for nr in range(1, self.DOKUMENTE + 1):
            text = "\n\n".join(f"Abschnitt {teil} von Dokument {nr}. {absatz}"
                               for teil in range(1, self.ZEICHEN // len(absatz) + 2))
            (ordner / f"{nr:02d}_schriftsatz.txt").write_text(text, encoding="utf-8")
        liste = [{"id": f"D-{nr:03d}", "titel": f"Schriftsatz {nr}",
                  "dateiname": f"{nr:02d}_schriftsatz.txt", "datum": "2026-01-01",
                  "kategorie": "Gegner"} for nr in range(1, self.DOKUMENTE + 1)]
        (ordner / "akte.json").write_text(json.dumps({
            "akte": {"id": AKTE, "aktenzeichen": "9001/26 BA", "bezeichnung": "Grosse Bausache",
                     "rechtsgebiet": "Baurecht", "sachbearbeiter": "RA Dr. Weber", "status": "offen"},
            "dokumente": liste, "beteiligte": [], "fristen": [],
        }, ensure_ascii=False), encoding="utf-8")

        e = einstellungen(
            JUSPERFECT_FIXTURE_PFAD=str(akten),
            JUSPERFECT_GEDAECHTNIS="lokal",
            JUSPERFECT_GEDAECHTNIS_PFAD=str(Path(tmp.name) / "gedaechtnis"),
            JUSPERFECT_MAX_PASSAGEN_ZEICHEN=str(GRENZE),
        )
        d = dienste(einstellungen=e, provider=provider)
        c = client(d)
        sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente",
               json={"dokument_ids": [x["id"] for x in liste]})
        return d, c, sid


class DieAkteWirdGanzGelesen(_GrosseAkte):
    def test_ein_aufruf_reicht_nicht_und_das_einlesen_kommt_trotzdem_durch(self):
        p = PortionsProvider()
        d, c, sid = self._aufbau(p)
        lauf = c.post(f"/api/sitzungen/{sid}/gedaechtnis/einlesen").json()["lauf"]
        self.assertGreater(lauf["portionen"], 1, "Die Akte muss mehrere Portionen brauchen.")
        self.assertEqual(lauf["offene_passagen"], 0)
        self.assertTrue(lauf["fertig"])
        self.assertEqual(len(p.aufrufe), lauf["portionen"])

    def test_der_lebenssachverhalt_waechst_und_wird_nie_umgeschrieben(self):
        """Der Kern der Zusage: Jede Portion hängt an, keine ersetzt."""
        p = PortionsProvider()
        d, c, sid = self._aufbau(p)
        lauf = c.post(f"/api/sitzungen/{sid}/gedaechtnis/einlesen").json()
        text = lauf["lebenssachverhalt"]
        for nummer in range(1, lauf["lauf"]["portionen"] + 1):
            self.assertIn(f"Feststellung {nummer}.", text,
                          "Eine frühere Portion darf nicht verlorengehen.")

    def test_jede_portion_bekommt_den_bisherigen_stand_mit(self):
        """Sonst begänne jede Portion von vorn und wüsste nichts vom Anfang."""
        p = PortionsProvider()
        d, c, sid = self._aufbau(p)
        c.post(f"/api/sitzungen/{sid}/gedaechtnis/einlesen")
        self.assertNotIn("Feststellung 1.", p.aufrufe[0]["aufgabe"])
        self.assertIn("Feststellung 1.", p.aufrufe[1]["aufgabe"])
        self.assertIn("BISHERIGER", p.aufrufe[1]["aufgabe"])

    def test_alle_dokumente_sind_am_ende_gelesen(self):
        p = PortionsProvider()
        d, c, sid = self._aufbau(p)
        uebersicht = c.post(f"/api/sitzungen/{sid}/gedaechtnis/einlesen").json()
        self.assertEqual(uebersicht["dokumente"], self.DOKUMENTE)
        self.assertEqual(uebersicht["offene_dokumente"], 0)


class DerAufrufBleibtInnerhalbDerGrenze(_GrosseAkte):
    """Der eigentliche Fehler: Der mitgeschickte Stand belegt auch Platz."""

    def test_kein_aufruf_ueberschreitet_die_zeichengrenze(self):
        p = PortionsProvider()
        d, c, sid = self._aufbau(p)
        c.post(f"/api/sitzungen/{sid}/gedaechtnis/einlesen")
        for nummer, aufruf in enumerate(p.aufrufe, start=1):
            umfang = len(aufruf["material"]) + len(aufruf["aufgabe"])
            with self.subTest(portion=nummer):
                self.assertLessEqual(umfang, GRENZE,
                                     "Material und bisheriger Stand zusammen sprengen den Aufruf.")

    def test_die_portionen_werden_kleiner_wenn_der_stand_waechst(self):
        """Der mitgeschickte Stand nimmt der nächsten Portion Platz weg."""
        p = PortionsProvider()
        d, c, sid = self._aufbau(p)
        c.post(f"/api/sitzungen/{sid}/gedaechtnis/einlesen")
        self.assertGreater(len(p.aufrufe), 2, "Für den Vergleich braucht es drei Portionen.")
        self.assertLess(len(p.aufrufe[1]["material"]), len(p.aufrufe[0]["material"]))
        # Und der Auftrag, in dem der bisherige Stand steht, wächst gegenläufig.
        self.assertGreater(len(p.aufrufe[1]["aufgabe"]), len(p.aufrufe[0]["aufgabe"]))


class NichtsBleibtUnbemerktLiegen(_GrosseAkte):
    def test_eine_portion_ohne_belegte_aussage_haelt_den_lauf_nicht_auf(self):
        """Sonst liefe der Durchgang endlos und kostete bei jedem Anlauf neu."""
        p = PortionsProvider(stumm_ab=2)
        d, c, sid = self._aufbau(p)
        lauf = c.post(f"/api/sitzungen/{sid}/gedaechtnis/einlesen").json()["lauf"]
        self.assertTrue(lauf["fertig"])
        self.assertEqual(lauf["offene_passagen"], 0)

    def test_und_sie_wird_ausdruecklich_gemeldet(self):
        """Genau hier könnte etwas verlorengehen – also muss es dastehen."""
        p = PortionsProvider(stumm_ab=2)
        d, c, sid = self._aufbau(p)
        lauf = c.post(f"/api/sitzungen/{sid}/gedaechtnis/einlesen").json()["lauf"]
        zusammen = " ".join(lauf["hinweise"])
        self.assertIn("keine belegte Aussage", zusammen)
        self.assertIn("Schriftsatz", zusammen, "Der Hinweis muss auf Dokumente zeigen.")
        self.assertIn("befragen", zusammen, "Der Volltext bleibt der Rückweg.")


class EinAbbruchVerliertNichts(_GrosseAkte):
    def test_was_gelesen_ist_bleibt_gespeichert(self):
        p = PortionsProvider(fehler_ab=3)
        d, c, sid = self._aufbau(p)
        c.post(f"/api/sitzungen/{sid}/gedaechtnis/einlesen")
        g = d.gedaechtnis.lesen(AKTE)
        self.assertIn("Feststellung 1.", g.lebenssachverhalt)
        self.assertIn("Feststellung 2.", g.lebenssachverhalt)
        self.assertTrue(g.verarbeitete_passagen)

    def test_ein_zweiter_anlauf_setzt_fort_statt_neu_zu_beginnen(self):
        p = PortionsProvider(fehler_ab=3)
        d, c, sid = self._aufbau(p)
        c.post(f"/api/sitzungen/{sid}/gedaechtnis/einlesen")
        gelesen = len(d.gedaechtnis.lesen(AKTE).verarbeitete_passagen)
        p.fehler_ab = None
        lauf = c.post(f"/api/sitzungen/{sid}/gedaechtnis/einlesen").json()["lauf"]
        self.assertTrue(lauf["fertig"])
        self.assertLess(lauf["passagen"], gelesen + lauf["passagen"])
        self.assertIn("Feststellung 1.", d.gedaechtnis.lesen(AKTE).lebenssachverhalt)


class DieDeckeWirdAusgesprochen(_GrosseAkte):
    """Zusammenfassen wäre der stille Verlust. Also wird gesagt, dass Schluss ist."""

    def _volles_gedaechtnis(self):
        p = PortionsProvider()
        d, c, sid = self._aufbau(p)
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
        g = d.gedaechtnis.lesen(AKTE)
        g.lebenssachverhalt = "Vermerkt. [Q: D1-S1-P1]\n" * 1200      # deutlich über die Decke
        d.gedaechtnis.ablegen(g)
        return d, c, sid, len(g.lebenssachverhalt)

    def test_das_einlesen_bricht_mit_klarer_meldung_ab(self):
        d, c, sid, _ = self._volles_gedaechtnis()
        antwort = c.post(f"/api/sitzungen/{sid}/gedaechtnis/einlesen")
        self.assertEqual(antwort.status_code, 422, antwort.text)
        fehler = antwort.json()["fehler"]
        self.assertIn("Lebenssachverhalt", fehler)
        self.assertIn("Gekürzt wird der Lebenssachverhalt nicht", fehler)
        self.assertIn("Explorer", fehler)

    def test_der_lebenssachverhalt_wird_dabei_nicht_angetastet(self):
        d, c, sid, laenge = self._volles_gedaechtnis()
        c.post(f"/api/sitzungen/{sid}/gedaechtnis/einlesen")
        self.assertEqual(len(d.gedaechtnis.lesen(AKTE).lebenssachverhalt), laenge)

    def test_der_dienst_meldet_denselben_fehler_unmittelbar(self):
        d, c, sid, _ = self._volles_gedaechtnis()
        sitzung = d.sitzungen.laden(_ident(d), sid)
        with self.assertRaises(GedaechtnisFehler):
            d.gedaechtnis.akte_einlesen(_ident(d), sitzung)


def _ident(d):
    from jusperfect.security.identitaet import Identitaet
    return Identitaet(nutzer_id="ra-weber", anzeigename="RA Dr. Weber", gruppen=("alle-akten",))


if __name__ == "__main__":
    unittest.main()
