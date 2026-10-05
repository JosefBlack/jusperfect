"""Woher eine Antwort kommt, wohin sie geht – und dass es festgehalten wird.

Befunde F08, F10 und F13 der Zweitprüfung vom 05.10.2026, Gegenproben 07, 08
und 11. Drei verschiedene Gegenstände, ein gemeinsamer Satz: **Eine Zusage,
die nur von der Gegenstelle getragen wird, hält das Programm nicht selbst.**

* **F08** – der Client fragte `EIGENE-AKTE` ab, die Antwort trug ausdrücklich
  eine fremde Kennung samt deren Ordner. Geprüft wurde nichts; fremder Inhalt
  stand damit unter der richtigen Aktennummer.
* **F10** – der Nachweis entstand erst **nach** einer erfolgreichen Antwort.
  Schlug der Aufruf fehl, nachdem das Material längst übertragen war, blieb
  das Nachweisfenster leer – und „keine Zeile" liest sich wie „nichts
  hinausgegangen".
* **F13** – Frankfurt plus `global.anthropic.…` kam durch die
  Einstellungsprüfung. Die mitgelieferte Zugriffsrichtlinie hätte den Aufruf
  abgewiesen; die Anwendung selbst nicht.
"""

from __future__ import annotations

import unittest

import httpx

from jusperfect.config import Einstellungen, KonfigurationsFehler, profil_befund
from jusperfect.domain.models import (
    AUSGANG_ABGEBROCHEN, AUSGANG_BEANTWORTET, AUSGANG_FEHLGESCHLAGEN,
    AUSGANG_UNBEKANNT,
)
from jusperfect.jurnodes.base import JurNodesFehler
from jusperfect.providers.base import Nutzung, ProviderAntwort, ProviderFehler
from tests.hilfen import einstellungen

MARKER = "Fremder Mandatsinhalt aus einer anderen Akte"


# ── F08: die zurückgegebene Aktenidentität ─────────────────────────────────

def _adapter(antworten):
    """Ein HTTP-Adapter gegen einen erfundenen Server."""
    from jusperfect.jurnodes.http_adapter import HttpJurNodesAdapter
    from jusperfect.security.approval import Freigabestelle

    def handler(anfrage: httpx.Request) -> httpx.Response:
        for pfad, antwort in antworten.items():
            if not anfrage.url.path.endswith(pfad):
                continue
            # Ab der zweiten Seite nichts mehr - sonst laeuft das Blaettern
            # endlos, weil der erfundene Server immer dasselbe antwortet.
            if "page" in anfrage.url.params:
                return httpx.Response(200, json={"elements": []})
            return antwort
        raise AssertionError(str(anfrage.url))

    return HttpJurNodesAdapter("https://jurnodes.invalid/api", "schluessel",
                               Freigabestelle(), benutzer="kanzlei",
                               transport=httpx.MockTransport(handler))


class EineFremdeAktenantwortWirdAbgewiesen(unittest.TestCase):
    """Gegenprobe 07, in richtiger Polarität."""

    def test_eine_andere_kennung_bricht_den_vorgang_ab(self):
        adapter = _adapter({"/record": httpx.Response(200, json={
            "identifier": "FREMDE-AKTE", "recordSign": "FREMD",
            "shortRubrum": "Fremd", "fileFolderId": 42})})
        with self.assertRaises(JurNodesFehler) as fehler:
            adapter.dokumente("EIGENE-AKTE")
        self.assertIn("eine andere Akte", str(fehler.exception))

    def test_die_fremde_kennung_steht_nicht_in_der_meldung(self):
        """Sie gehört zu einer anderen Akte – und ist Mandantengeheimnis."""
        adapter = _adapter({"/record": httpx.Response(200, json={
            "identifier": "FREMDE-AKTE", "recordSign": "FREMD-AZ",
            "shortRubrum": "Testmann ./. Musterfrau", "fileFolderId": 42})})
        with self.assertRaises(JurNodesFehler) as fehler:
            adapter.dokumente("EIGENE-AKTE")
        for geheim in ("FREMDE-AKTE", "FREMD-AZ", "Testmann"):
            self.assertNotIn(geheim, str(fehler.exception), geheim)

    def test_eine_antwort_ganz_ohne_kennung_bricht_ebenfalls_ab(self):
        """Eine Aktenantwort ohne Kennung ist nach der Beschreibung des
        Herstellers (API 1.0.2) keine. Ihr stillschweigend zu glauben hieße,
        die Prüfung auf Zuruf abzuschalten."""
        adapter = _adapter({"/record": httpx.Response(200, json={
            "recordSign": "X", "shortRubrum": "Y", "fileFolderId": 7})})
        with self.assertRaises(JurNodesFehler) as fehler:
            adapter.dokumente("EIGENE-AKTE")
        self.assertIn("keine Aktenkennung", str(fehler.exception))

    def test_die_eigene_akte_geht_durch(self):
        adapter = _adapter({
            "/record": httpx.Response(200, json={
                "identifier": "EIGENE-AKTE", "recordSign": "1/26",
                "shortRubrum": "Eigen", "fileFolderId": 7}),
            "/file-system/folder/content": httpx.Response(200, json={"elements": [
                {"type": "file", "file": {"identifier": "D1", "folderId": 7,
                                          "fileName": "schreiben", "fileExtension": "txt"}}]}),
        })
        self.assertEqual(len(adapter.dokumente("EIGENE-AKTE")), 1)

    def test_gross_und_kleinschreibung_macht_keinen_unterschied(self):
        """Sonst scheiterte eine richtige Antwort an einer Schreibweise."""
        adapter = _adapter({
            "/record": httpx.Response(200, json={
                "identifier": "eigene-akte", "recordSign": "1/26",
                "shortRubrum": "Eigen", "fileFolderId": 7}),
            "/file-system/folder/content": httpx.Response(200, json={"elements": []}),
        })
        self.assertEqual(adapter.dokumente("EIGENE-AKTE"), [])

    def test_eine_datei_aus_einem_anderen_ordner_wird_ausgesondert(self):
        """Die zweite Hälfte: Wer den Inhalt von Ordner 7 abfragt, bekommt
        Dateien aus Ordner 7. Mehr liefert die Beschreibung des Herstellers
        zur Zugehörigkeit einer einzelnen Datei nicht."""
        adapter = _adapter({
            "/record": httpx.Response(200, json={
                "identifier": "EIGENE-AKTE", "recordSign": "1/26",
                "shortRubrum": "Eigen", "fileFolderId": 7}),
            "/file-system/folder/content": httpx.Response(200, json={"elements": [
                {"type": "file", "file": {"identifier": "EIGEN", "folderId": 7,
                                          "fileName": "eigen", "fileExtension": "txt"}},
                {"type": "file", "file": {"identifier": "FREMD", "folderId": 99,
                                          "fileName": MARKER, "fileExtension": "txt"}}]}),
        })
        dokumente = adapter.dokumente("EIGENE-AKTE")
        self.assertEqual([d.id for d in dokumente], ["EIGEN"])
        self.assertEqual(adapter.letzte_dateien_aussortiert, 1)


# ── F10: der Nachweis vor der Übermittlung ─────────────────────────────────

class _PlatzenderProvider:
    modell_id = "skript"

    def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        raise ProviderFehler("Bedrock hat die Anfrage abgelehnt.")

    def fragen_stream(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        yield "Ein Stück kam noch"
        raise ProviderFehler("Die Verbindung brach ab.")


class _StummerProvider:
    """Liefert Stücke, aber nie den abschließenden Durchgang."""

    modell_id = "skript"

    def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        return ProviderAntwort(text="x", nutzung=Nutzung(), modell=self.modell_id)

    def fragen_stream(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        yield "nur Text"


def _ausgang(provider):
    from jusperfect.security.identitaet import Identitaet
    from jusperfect.services.ausgang import Ausgang, Ausgangskontext
    from jusperfect.services.kosten import Kostenwaechter
    from jusperfect.speicher.lokal import LokalerSpeicher

    e = einstellungen()
    speicher = LokalerSpeicher()
    kosten = Kostenwaechter(speicher, e.monatsbudget_eur, e.usd_eur_kurs)
    kontext = Ausgangskontext(Identitaet(nutzer_id="ra-weber"), "s-1", "VU-2026-0042", "frage",
                              passagen=2)
    return Ausgang(provider, kosten, e), kosten, kontext


class EinFehlgeschlagenerAufrufHinterlaesstEineSpur(unittest.TestCase):
    """Gegenprobe 08, in richtiger Polarität.

    Kosten und Übermittlung sind im Fehlerfall nicht beide null.
    """

    def test_der_versuch_steht_im_nachweis(self):
        aus, kosten, kontext = _ausgang(_PlatzenderProvider())
        with self.assertRaises(ProviderFehler):
            aus.fragen(kontext, "System", "Material", "Aufgabe")
        eintraege = kosten.nachweis("ra-weber")
        self.assertEqual(len(eintraege), 1)
        self.assertEqual(eintraege[0]["ausgang"], AUSGANG_FEHLGESCHLAGEN)

    def test_der_versuch_traegt_die_kurzkennung_des_materials(self):
        """Sonst stünde da nur, **dass** etwas hinausging, nicht **was**."""
        from jusperfect.security.protokoll import kurzkennung

        aus, kosten, kontext = _ausgang(_PlatzenderProvider())
        with self.assertRaises(ProviderFehler):
            aus.fragen(kontext, "System", "Material", "Aufgabe")
        eintrag = kosten.nachweis("ra-weber")[0]
        self.assertEqual(eintrag["material_kennung"], kurzkennung("Material"))
        self.assertEqual(eintrag["passagen"], 2)

    def test_der_fehlversuch_kostet_nichts_in_der_monatssumme(self):
        """Eine geratene Zahl wäre schlechter als gar keine."""
        aus, kosten, kontext = _ausgang(_PlatzenderProvider())
        with self.assertRaises(ProviderFehler):
            aus.fragen(kontext, "System", "Material", "Aufgabe")
        self.assertEqual(kosten.nachweis("ra-weber")[0]["betrag_eur"], 0)

    def test_ein_abgebrochener_strom_ebenso(self):
        aus, kosten, kontext = _ausgang(_PlatzenderProvider())
        with self.assertRaises(ProviderFehler):
            list(aus.fragen_stream(kontext, "System", "Material", "Aufgabe"))
        self.assertEqual(kosten.nachweis("ra-weber")[0]["ausgang"], AUSGANG_FEHLGESCHLAGEN)

    def test_ein_strom_ohne_abschluss_heisst_abgebrochen(self):
        aus, kosten, kontext = _ausgang(_StummerProvider())
        with self.assertRaises(ProviderFehler):
            list(aus.fragen_stream(kontext, "System", "Material", "Aufgabe"))
        self.assertEqual(kosten.nachweis("ra-weber")[0]["ausgang"], AUSGANG_ABGEBROCHEN)

    def test_ein_gelungener_aufruf_steht_weiterhin_als_eine_zeile_da(self):
        """In der Ablage stehen zwei; gelesen wird eine. Ein Nachweis, den man
        ändern kann, wäre ein schwächerer – deshalb wird angehängt und beim
        Lesen zusammengelegt."""
        from tests.test_ausgang import _FesterProvider

        aus, kosten, kontext = _ausgang(_FesterProvider())
        aus.fragen(kontext, "System", "Material", "Aufgabe")
        eintraege = kosten.nachweis("ra-weber")
        self.assertEqual(len(eintraege), 1)
        self.assertEqual(eintraege[0]["ausgang"], AUSGANG_BEANTWORTET)
        self.assertGreater(eintraege[0]["eingabe_tokens"], 0)

    def test_eine_zeile_ohne_ausgang_heisst_unbekannt_und_nicht_nichts(self):
        """Wenn das Programm mitten im Aufruf endet, steht nur der Versuch da."""
        from jusperfect.security.identitaet import Identitaet

        aus, kosten, kontext = _ausgang(_StummerProvider())
        kosten.versuch_vermerken(Identitaet(nutzer_id="ra-weber"), "A", "frage", "m",
                                 versuch_id="abc", sitzung_id="s-1")
        self.assertEqual(kosten.nachweis("ra-weber")[0]["ausgang"], AUSGANG_UNBEKANNT)

    def test_der_nachweis_traegt_keinen_inhalt(self):
        aus, kosten, kontext = _ausgang(_PlatzenderProvider())
        with self.assertRaises(ProviderFehler):
            aus.fragen(kontext, "System", "Der Mandant fuhr 90 km/h", "Wie schnell?")
        text = str(kosten.nachweis("ra-weber"))
        self.assertNotIn("Mandant", text)
        self.assertNotIn("km/h", text)


# ── F13: das Modellprofil bleibt in der EU ─────────────────────────────────

class EinGlobalesProfilWirdAbgewiesen(unittest.TestCase):
    """Gegenprobe 11, in richtiger Polarität.

    Ein Inferenzprofil ist kein Modellname, sondern eine Verteilregel. Die
    Aufrufregion sagt darüber nichts – sie ist der Ort, an dem die Anfrage
    ankommt, nicht der, an dem gerechnet wird.
    """

    def _bedrock(self, **extra) -> Einstellungen:
        werte = {"JUSPERFECT_ANBIETER": "bedrock", "JUSPERFECT_JURNODES_ADAPTER": "http",
                 "JUSPERFECT_JURNODES_URL": "https://jurnodes.invalid",
                 "JUSPERFECT_GUARDRAIL_ID": "realguard123"}
        werte.update(extra)
        return einstellungen(**werte)

    def test_global_in_frankfurt_wird_abgewiesen(self):
        with self.assertRaises(KonfigurationsFehler) as fehler:
            self._bedrock(JUSPERFECT_MODELL_ID="global.anthropic.claude-opus-4-6-v1")
        self.assertIn("JUSPERFECT_MODELL_ID", str(fehler.exception))
        self.assertIn("außerhalb der EU", str(fehler.exception))

    def test_auch_das_zweite_modell_je_aufgabe_wird_geprueft(self):
        """Wer ein eigenes Modell je Aufgabe einträgt – genau der Fall, für den
        es die Felder gibt –, käme sonst an der Prüfung vorbei."""
        with self.assertRaises(KonfigurationsFehler) as fehler:
            self._bedrock(JUSPERFECT_MODELL_TRIAGE="us.anthropic.claude-haiku-4-5")
        self.assertIn("JUSPERFECT_MODELL_TRIAGE", str(fehler.exception))

    def test_eine_arn_ausserhalb_der_eu_ebenfalls(self):
        with self.assertRaises(KonfigurationsFehler) as fehler:
            self._bedrock(JUSPERFECT_MODELL_ID=
                          "arn:aws:bedrock:us-east-1:123456789012:inference-profile/x")
        self.assertIn("us-east-1", str(fehler.exception))

    def test_zuerich_in_einer_arn_wird_beim_namen_genannt(self):
        """„eu-" ist eine Namenskonvention von AWS, keine Aussage über die EU."""
        self.assertIn("Zürich", profil_befund(
            "arn:aws:bedrock:eu-central-2:123456789012:inference-profile/x"))

    def test_das_eu_profil_geht_durch(self):
        e = self._bedrock(JUSPERFECT_MODELL_ID="eu.anthropic.claude-opus-4-6-v1")
        self.assertEqual(e.modell_fuer("frage"), "eu.anthropic.claude-opus-4-6-v1")

    def test_eine_arn_in_frankfurt_geht_durch(self):
        arn = "arn:aws:bedrock:eu-central-1:123456789012:inference-profile/eu.anthropic.x"
        self.assertEqual(profil_befund(arn), "")
        self.assertEqual(self._bedrock(JUSPERFECT_MODELL_ID=arn).modell_id, arn)

    def test_der_demo_anbieter_bleibt_unberuehrt(self):
        """Er ruft kein Modell auf; eine Kennung ist dort ein Name ohne Folge."""
        e = einstellungen(JUSPERFECT_MODELL_ID="global.anthropic.claude-opus-4-6-v1")
        self.assertEqual(e.anbieter, "demo")

    def test_die_zugriffsrichtlinie_bleibt_der_zweite_riegel(self):
        """Der Bericht hat recht: Die mitgelieferte Richtlinie nennt die sechs
        Regionen bereits. Beides zusammen trägt – die Anwendung allein trug
        nicht, und die Kontoeinstellung allein ist nicht geprüft."""
        import json
        from pathlib import Path

        richtlinie = json.loads((Path(__file__).resolve().parent.parent
                                 / "infra" / "iam-nur-claude.json").read_text(encoding="utf-8"))
        text = json.dumps(richtlinie)
        self.assertIn("eu-central-1", text)
        self.assertIn("StringNotEquals", text)


if __name__ == "__main__":
    unittest.main()
