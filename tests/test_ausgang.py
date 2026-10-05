"""Der geprüfte Ausgang und der Verarbeitungsnachweis.

Zwei Zusagen werden hier geprüft: Nur Text geht hinaus, und über jeden Aufruf
entsteht ein Nachweis – ohne den Aktentext ein zweites Mal abzulegen.
"""

import re
import unittest

from tests.hilfen import client, dienste, einstellungen

from jusperfect.domain.models import Kosten
from jusperfect.providers.base import Nutzung, ProviderAntwort
from jusperfect.security.identitaet import Identitaet
from jusperfect.security.protokoll import kurzkennung
from jusperfect.services.ausgang import Ausgang, Ausgangskontext
from jusperfect.services.kosten import Kostenwaechter
from jusperfect.speicher.lokal import LokalerSpeicher


class _FesterProvider:
    modell_id = "test-modell"

    def __init__(self, text="Antwort [Q: D1-S1-P1]."):
        self.text = text
        self.gesehen: list[tuple] = []

    def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        self.gesehen.append((system, material, aufgabe))
        return ProviderAntwort(text=self.text, nutzung=Nutzung(eingabe_tokens=10, ausgabe_tokens=5),
                               modell=self.modell_id)

    def fragen_stream(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        for w in re.findall(r"\S+\s*", self.text):
            yield w
        yield ProviderAntwort(text=self.text, nutzung=Nutzung(eingabe_tokens=10, ausgabe_tokens=5),
                              modell=self.modell_id)


def _ausgang(provider=None):
    e = einstellungen()
    speicher = LokalerSpeicher()
    kosten = Kostenwaechter(speicher, e.monatsbudget_eur, e.usd_eur_kurs)
    return Ausgang(provider or _FesterProvider(), kosten, e), kosten, speicher


class GepruefterAusgang(unittest.TestCase):
    def _kontext(self):
        return Ausgangskontext(Identitaet(nutzer_id="ra-weber"), "S1", "VU-2026-0042", "frage", passagen=2)

    def test_nur_text_geht_hinaus(self):
        aus, _, _ = _ausgang()
        with self.assertRaises(TypeError):
            aus.fragen(self._kontext(), "System", ["nicht", "text"], "Aufgabe")  # Liste statt Text
        with self.assertRaises(TypeError):
            aus.fragen(self._kontext(), "System", "Material", object())

    def test_durchgang_traegt_antwort_und_kosten(self):
        aus, _, _ = _ausgang()
        d = aus.fragen(self._kontext(), "System", "Material", "Aufgabe")
        self.assertEqual(d.antwort.modell, "test-modell")
        self.assertIsInstance(d.kosten, Kosten)

    def test_aufruf_schreibt_nachweis_ohne_inhalte(self):
        prov = _FesterProvider()
        aus, kosten, _ = _ausgang(prov)
        material = "### Passage D1-S1-P1 (Akte)\nDer Mandant fuhr 50 km/h."
        aus.fragen(self._kontext(), "System", material, "Wie schnell?")
        eintraege = kosten.nachweis("ra-weber")
        self.assertEqual(len(eintraege), 1)
        e = eintraege[0]
        # Fingerabdruck statt Text: Kurzkennung des tatsächlich gesendeten Materials.
        self.assertEqual(e["material_kennung"], kurzkennung(material))
        self.assertEqual(e["aufgabe_kennung"], kurzkennung("Wie schnell?"))
        self.assertEqual(e["passagen"], 2)
        self.assertEqual(e["funktion"], "frage")
        self.assertGreater(e["antwort_zeichen"], 0)
        # Kein Aktentext im Nachweis.
        self.assertNotIn("Mandant", str(e))
        self.assertNotIn("km/h", str(e))

    def test_stream_schreibt_ebenfalls_nachweis(self):
        aus, kosten, _ = _ausgang()
        stuecke = list(aus.fragen_stream(self._kontext(), "System", "Material", "Aufgabe"))
        self.assertTrue(any(isinstance(s, str) for s in stuecke))
        self.assertEqual(len(kosten.nachweis("ra-weber")), 1)


class _ModellProvider:
    modell_id = "standard-modell"

    def __init__(self):
        self.gesehene_modelle: list[str | None] = []

    def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        self.gesehene_modelle.append(modell_id)
        return ProviderAntwort(text="ok", nutzung=Nutzung(), modell=modell_id or self.modell_id)

    def fragen_stream(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        yield self.fragen(system, material, aufgabe, modell_id=modell_id)


class ModellJeAufgabe(unittest.TestCase):
    """Ein eigenes Modell je Arbeit – und in Europa mit Profilvorsatz.

    Der Vorsatz „eu." bekam frueher nur JUSPERFECT_MODELL_ID. Wer ein zweites
    Modell je Aufgabe eintrug – genau der Fall, fuer den es diese Felder gibt –,
    bekam es unveraendert und lief in Europa in eine Abweisung, die nach einer
    fehlenden Freischaltung aussieht. Die Voreinstellung tat das Richtige, die
    eigene Wahl nicht; das ist die teuerste Art von Fehler.
    """

    #: So steht es in der Startdatei – so muss es bei Bedrock ankommen.
    KLEIN = "anthropic.claude-haiku-4-5"
    KLEIN_EU = "eu.anthropic.claude-haiku-4-5"

    def test_einstellungen_modell_fuer(self):
        e = einstellungen(JUSPERFECT_MODELL_TRIAGE=self.KLEIN,
                          JUSPERFECT_MODELL_FRAGE="anthropic.claude-sonnet-5")
        self.assertEqual(e.modell_fuer("triage"), self.KLEIN_EU)
        self.assertEqual(e.modell_fuer("frage"), "eu.anthropic.claude-sonnet-5")
        self.assertEqual(e.modell_fuer("entwurf"), e.modell_id)   # nicht gesetzt -> Standard
        self.assertEqual(e.modell_fuer("analyse"), e.modell_id)

    def test_jede_kennung_bekommt_denselben_vorsatz(self):
        e = einstellungen(JUSPERFECT_MODELL_ID_KLEIN=self.KLEIN,
                          JUSPERFECT_MODELL_ANALYSE="anthropic.claude-sonnet-5",
                          JUSPERFECT_MODELL_ENTWURF="anthropic.claude-sonnet-5",
                          JUSPERFECT_MODELL_GEDAECHTNIS=self.KLEIN)
        for funktion, kennung in e.modelle_uebersicht().items():
            with self.subTest(funktion=funktion):
                self.assertTrue(kennung.startswith("eu.anthropic."), kennung)

    def test_ausserhalb_europas_bleibt_die_kennung_wie_eingetragen(self):
        """Der Vorsatz ist eine europaeische Besonderheit, keine Vorschrift.

        Ueber die Einstellungen ist das nicht zu bauen - die lassen nur EU-Regionen
        zu (Grundsatz 9). Geprueft wird deshalb die Stelle selbst.
        """
        from jusperfect.config import _modellkennung

        self.assertEqual(_modellkennung(self.KLEIN, "us-east-1"), self.KLEIN)
        self.assertEqual(_modellkennung(self.KLEIN, "eu-central-1"), self.KLEIN_EU)

    def test_was_schon_einen_vorsatz_hat_bekommt_keinen_zweiten(self):
        from jusperfect.config import _modellkennung

        self.assertEqual(_modellkennung(self.KLEIN_EU, "eu-central-1"), self.KLEIN_EU)
        arn = ("arn:aws:bedrock:eu-central-1:1:inference-profile/" + self.KLEIN_EU)
        self.assertEqual(_modellkennung(arn, "eu-central-1"), arn)

    def test_triage_faellt_auf_klein_zurueck(self):
        e = einstellungen(JUSPERFECT_MODELL_ID_KLEIN=self.KLEIN)
        self.assertEqual(e.modell_fuer("triage"), self.KLEIN_EU)
        self.assertEqual(e.modell_fuer("frage"), e.modell_id)

    def test_ausgang_waehlt_modell_nach_funktion(self):
        e = einstellungen(JUSPERFECT_MODELL_TRIAGE=self.KLEIN)
        prov = _ModellProvider()
        speicher = LokalerSpeicher()
        aus = Ausgang(prov, Kostenwaechter(speicher, e.monatsbudget_eur, e.usd_eur_kurs), e)
        ident = Identitaet(nutzer_id="ra-weber")
        aus.fragen(Ausgangskontext(ident, "S1", "A", "frage"), "S", "M", "A")
        aus.fragen(Ausgangskontext(ident, "S1", "A", "triage"), "S", "M", "A")
        self.assertEqual(prov.gesehene_modelle, [e.modell_id, self.KLEIN_EU])

    def test_status_zeigt_modelluebersicht(self):
        s = client(dienste(), "ra-weber").get("/api/status").json()
        self.assertIn("modelle", s)
        self.assertEqual(set(s["modelle"]), {"frage", "analyse", "triage", "entwurf", "gedaechtnis"})


class NachweisEndpunkt(unittest.TestCase):
    def setUp(self):
        self.d = dienste()
        self.c = client(self.d, "ra-weber")
        self.sid = self.c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        self.c.post(f"/api/sitzungen/{self.sid}/dokumente", json={"dokument_ids": ["D-001", "D-002", "D-004"]})

    def test_frage_erzeugt_nachweiszeile(self):
        self.c.post(f"/api/sitzungen/{self.sid}/frage", json={"frage": "Welche Geschwindigkeit fuhr der Mandant?"})
        eintraege = self.c.get("/api/nachweis").json()["eintraege"]
        self.assertTrue(eintraege)
        e = eintraege[0]
        self.assertEqual(e["funktion"], "frage")
        self.assertEqual(e["akte_id"], "VU-2026-0042")
        self.assertTrue(re.match(r"[0-9a-f]{12}:\d+", e["material_kennung"]))
        # Keine Inhalte im Nachweis (nur Kennungen, Zahlen, Zeitpunkt).
        self.assertNotIn("Mandant", str(e))

    def test_nachweis_ist_nutzergebunden(self):
        self.c.post(f"/api/sitzungen/{self.sid}/frage", json={"frage": "Wie schnell fuhr der Mandant?"})
        # ra-kaminski darf alle Akten, sieht aber nur die eigenen Übertragungen.
        fremd = client(self.d, "ra-kaminski").get("/api/nachweis").json()["eintraege"]
        self.assertEqual(fremd, [])


if __name__ == "__main__":
    unittest.main()
