"""Das Startbild: Stehen die Absicherungen?

Aus der Kanzlei: „ein Testlauf beim Start des Programms mit Hinweis auf den
Testablauf, was gerade gemacht wird" – und dazu: „Beachte aber, dass wir
wahrscheinlich verschiedene Modelle einbinden wollen."

Beides prüft diese Datei. Der Selbsttest muss zweierlei leisten: Er darf **nicht
kosten** (sonst zahlt die Kanzlei für jeden Programmstart, und mit mehreren
Modellen ein Vielfaches), und er muss die Modelle **einzeln** zeigen – wer ein
kleines Modell für die Eingangsprüfung und ein starkes für die Analyse
einbindet, will beide sehen und nicht eine gemittelte Zeile.

Das Heikelste steht am Ende: Ein Modell, das die Zugriffsrichtlinie der Kanzlei
nicht abdeckt, wird beim ersten Aufruf abgewiesen. Das gehört ins Startbild und
nicht mitten in die Arbeit an einer Akte.
"""

from __future__ import annotations

import re
import unittest

from jusperfect.modellprotokoll import AUS, UNBEKANNT, Befund
from jusperfect.services.selbsttest import (
    ENTFAELLT,
    GUT,
    OFFEN,
    SCHLECHT,
    UNGEPRUEFT,
    Selbsttest,
    modelle_anprobieren,
    modelle_je_kennung,
)
from tests.hilfen import WURZEL, client, dienste, einstellungen

GROSS = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
KLEIN = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"


class _Sts:
    def __init__(self, arn="arn:aws:iam::1:user/jusperfect") -> None:
        self._arn = arn

    def get_caller_identity(self):
        return {"Arn": self._arn}


def _aws_fehler(code: str) -> Exception:
    fehler = RuntimeError(code)
    fehler.response = {"Error": {"Code": code, "Message": code}}
    return fehler


def _bedrock(**extra):
    grund = {"JUSPERFECT_ANBIETER": "bedrock", "JUSPERFECT_MODELL_ID": GROSS}
    grund.update(extra)
    return einstellungen(**grund)


def _punkt(ergebnis, schluessel):
    return next(p for p in ergebnis.punkte if p.schluessel == schluessel)


class _LauterProvider:
    """Ein Anbieter, der jeden Aufruf laut mitzählt."""

    modell_id = GROSS

    def __init__(self) -> None:
        self.aufrufe: list[str] = []

    def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        self.aufrufe.append(modell_id or self.modell_id)
        raise AssertionError("Der Selbsttest darf kein Modell aufrufen.")

    def fragen_stream(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        yield self.fragen(system, material, aufgabe, max_tokens=max_tokens, modell_id=modell_id)


class DerTestKostetNichts(unittest.TestCase):
    """Der Punkt, an dem ein Startbild teuer wird, ohne dass es jemand merkt."""

    def test_kein_modell_wird_aufgerufen(self):
        spion = _LauterProvider()
        e = _bedrock(JUSPERFECT_MODELL_TRIAGE=KLEIN)
        d = dienste(einstellungen=e, provider=spion)
        Selbsttest(e, adapter=d.adapter, kosten=d.kosten, sts=_Sts()).ausfuehren()
        self.assertEqual([], spion.aufrufe,
                         "Der Selbsttest hat ein Modell aufgerufen – das kostet bei "
                         "jedem Start, und mit mehreren Modellen ein Vielfaches.")

    def test_auch_ueber_die_schaltstelle_nicht(self):
        spion = _LauterProvider()
        d = dienste(einstellungen=_bedrock(), provider=spion)
        # Die Schaltstelle fragt STS; das ist eine Verwaltungsauskunft, kein Modell.
        antwort = client(d).get("/api/selbsttest")
        self.assertEqual(200, antwort.status_code, antwort.text)
        self.assertEqual([], spion.aufrufe)


class WasDasStartbildZeigt(unittest.TestCase):

    def setUp(self):
        self.d = dienste()

    def _lauf(self, e=None, **extra):
        d = dienste(einstellungen=e) if e else self.d
        return Selbsttest(d.einstellungen, adapter=d.adapter, kosten=d.kosten, **extra).ausfuehren()

    def test_jeder_punkt_traegt_einen_ganzen_satz(self):
        for p in self._lauf().punkte:
            with self.subTest(punkt=p.schluessel):
                self.assertTrue(p.titel and p.satz, p.schluessel)
                self.assertTrue(p.satz.endswith((".", "!")), p.satz)

    def test_die_region_steht_mit_namen_da(self):
        p = _punkt(self._lauf(_bedrock(), sts=_Sts()), "region")
        self.assertIn("eu-central-1", p.satz)
        self.assertEqual(GUT, p.zustand)

    def test_der_aktenzugang_wird_wirklich_angefasst(self):
        p = _punkt(self._lauf(), "akten")
        self.assertEqual(GUT, p.zustand)
        self.assertIn("Akte(n) erreichbar", p.satz)
        self.assertIn("kein Mandantengeheimnis", p.hinweis)

    def test_ein_unerreichbarer_aktenbestand_faellt_auf(self):
        class _Kaputt:
            def akten_suchen(self, suchbegriff=""):
                raise OSError("Laufwerk J: nicht verbunden")

        d = dienste()
        p = _punkt(Selbsttest(d.einstellungen, adapter=_Kaputt(), kosten=d.kosten).ausfuehren(), "akten")
        self.assertEqual(SCHLECHT, p.zustand)
        self.assertIn("nicht erreichbar", p.satz)

    def test_eine_kaputte_pruefung_reisst_die_anderen_nicht_mit(self):
        """Ein Startbild, das selbst abstürzt, ist schlimmer als keines."""
        class _Kaputt:
            def akten_suchen(self, suchbegriff=""):
                raise OSError("weg")

        d = dienste()
        ergebnis = Selbsttest(d.einstellungen, adapter=_Kaputt(), kosten=d.kosten).ausfuehren()
        self.assertEqual(8, len(ergebnis.punkte))

    def test_der_befund_zur_mitschrift_wird_uebernommen(self):
        e = _bedrock()
        p = _punkt(self._lauf(e, sts=_Sts(),
                              modellprotokoll=Befund(AUS, "AWS schreibt die Modellaufrufe nicht mit.")),
                   "mitschrift")
        self.assertEqual(GUT, p.zustand)

    def test_eine_offene_frage_zur_mitschrift_bleibt_offen(self):
        e = _bedrock()
        p = _punkt(self._lauf(e, sts=_Sts(),
                              modellprotokoll=Befund(UNBEKANNT, "Lässt sich nicht feststellen.",
                                                     ("Das Leserecht fehlt.",))),
                   "mitschrift")
        self.assertEqual(OFFEN, p.zustand)
        self.assertIn("Leserecht", p.hinweis)

    def test_ein_abgewiesener_zugang_ist_kein_haken(self):
        class _Weg:
            def get_caller_identity(self):
                raise RuntimeError("kaputt")

        p = _punkt(self._lauf(_bedrock(), sts=_Weg()), "zugang")
        self.assertEqual(SCHLECHT, p.zustand)
        self.assertIn("awstest", p.hinweis)

    def test_der_zugang_sagt_welcher_der_beiden_schluessel_klemmt(self):
        """„ClientError" half niemandem – Kennung und geheimer Schlüssel sind
        zwei verschiedene Handgriffe."""
        faelle = {
            "InvalidClientTokenId": "Access Key ID",
            "UnrecognizedClientException": "Access Key ID",
            "SignatureDoesNotMatch": "geheime Schlüssel",
            "InvalidSignatureException": "Uhr dieses Rechners",
            "RequestTimeTooSkewed": "Uhr dieses Rechners",
            "ExpiredToken": "abgelaufen",
            "AccessDenied": "sich selbst",
        }
        for code, erwartet in faelle.items():
            with self.subTest(code=code):
                class _Weg:
                    def get_caller_identity(self, _code=code):
                        raise _aws_fehler(_code)

                p = _punkt(self._lauf(_bedrock(), sts=_Weg()), "zugang")
                self.assertEqual(SCHLECHT, p.zustand)
                self.assertIn(erwartet, p.satz + " " + p.hinweis)

    def test_eine_falsche_uhr_wird_als_ursache_genannt(self):
        """Derselbe Fehlercode, zwei Ursachen – und die Uhr übersieht man.

        Ein Schlüssel, der auf einem Rechner geht und auf dem nächsten nicht,
        ist fast nie der Schlüssel. AWS unterschreibt jede Anfrage mit der Zeit.
        """
        class _Weg:
            def get_caller_identity(self):
                raise _aws_fehler("SignatureDoesNotMatch")

        p = _punkt(self._lauf(_bedrock(), sts=_Weg()), "zugang")
        self.assertIn("Uhr dieses Rechners", p.hinweis)
        self.assertIn("geheime Schlüssel", p.hinweis)

    def test_ganz_ohne_schluessel_steht_das_auch_so_da(self):
        class _Leer:
            def get_caller_identity(self):
                raise type("NoCredentialsError", (Exception,), {})()

        p = _punkt(self._lauf(_bedrock(), sts=_Leer()), "zugang")
        self.assertIn("gar keine AWS-Zugangsdaten", p.satz)
        self.assertIn("ZUGANG-EINTRAGEN.bat", p.hinweis)

    def test_ein_gestoertes_netz_ist_kein_schluesselproblem(self):
        """Sonst sucht die Kanzlei am falschen Ende."""
        class _Weg:
            def get_caller_identity(self):
                raise type("EndpointConnectionError", (Exception,), {})()

        p = _punkt(self._lauf(_bedrock(), sts=_Weg()), "zugang")
        self.assertIn("nicht erreichbar", p.satz)
        self.assertIn("Firewall", p.hinweis)

    def test_ohne_guardrail_steht_die_frage_offen(self):
        p = _punkt(self._lauf(_bedrock(), sts=_Sts()), "guardrail")
        self.assertEqual(OFFEN, p.zustand)

    def test_betraege_stehen_deutsch_da(self):
        p = _punkt(self._lauf(_bedrock(), sts=_Sts()), "kosten")
        self.assertIn("0,00 von 125 EUR", p.satz)

    def test_die_offenen_punkte_werden_gezaehlt(self):
        ergebnis = self._lauf(_bedrock(), sts=_Sts())
        self.assertEqual(ergebnis.offen,
                         sum(1 for p in ergebnis.punkte if p.zustand in (OFFEN, SCHLECHT)))

    def test_im_demobetrieb_entfaellt_was_aws_betrifft(self):
        ergebnis = self._lauf()
        for schluessel in ("region", "zugang", "guardrail", "kosten"):
            with self.subTest(punkt=schluessel):
                self.assertEqual(ENTFAELLT, _punkt(ergebnis, schluessel).zustand)


class MehrereModelle(unittest.TestCase):
    """„Beachte aber, dass wir wahrscheinlich verschiedene Modelle einbinden wollen."""

    def test_ein_eintrag_je_modell_nicht_je_funktion(self):
        e = _bedrock(JUSPERFECT_MODELL_TRIAGE=KLEIN, JUSPERFECT_MODELL_GEDAECHTNIS=KLEIN)
        gebuendelt = modelle_je_kennung(e)
        self.assertEqual({GROSS, KLEIN}, set(gebuendelt))
        self.assertEqual({"triage", "gedaechtnis"}, set(gebuendelt[KLEIN]))

    def test_das_startbild_zeigt_beide_mit_ihrer_arbeit(self):
        e = _bedrock(JUSPERFECT_MODELL_TRIAGE=KLEIN)
        d = dienste(einstellungen=e)
        zeilen = Selbsttest(e, adapter=d.adapter, kosten=d.kosten, sts=_Sts()).ausfuehren().modelle
        self.assertEqual(2, len(zeilen))
        klein = next(z for z in zeilen if z.kennung == KLEIN)
        self.assertEqual("Eingangsprüfung", klein.arbeit)
        self.assertEqual(UNGEPRUEFT, klein.zustand,
                         "Ohne Aufruf kann niemand wissen, ob es antwortet – das muss dastehen.")

    def test_ein_modell_ausserhalb_der_richtlinie_faellt_sofort_auf(self):
        """Sonst merkt es die Kanzlei erst bei der ersten Frage an einer Akte."""
        e = _bedrock(JUSPERFECT_MODELL_ANALYSE="meta.llama3-70b-instruct-v1:0")
        d = dienste(einstellungen=e)
        zeilen = Selbsttest(e, adapter=d.adapter, kosten=d.kosten, sts=_Sts()).ausfuehren().modelle
        fremd = next(z for z in zeilen if z.kennung.startswith("meta."))
        self.assertEqual(SCHLECHT, fremd.zustand)
        self.assertIn("deckt diese Kennung nicht ab", fremd.satz)

    def test_ein_inferenzprofil_als_arn_gilt_als_gedeckt(self):
        arn = ("arn:aws:bedrock:eu-central-1:123456789012:inference-profile/"
               "eu.anthropic.claude-sonnet-4-5-20250929-v1:0")
        e = _bedrock(JUSPERFECT_MODELL_ID=arn)
        d = dienste(einstellungen=e)
        zeilen = Selbsttest(e, adapter=d.adapter, kosten=d.kosten, sts=_Sts()).ausfuehren().modelle
        self.assertEqual(UNGEPRUEFT, zeilen[0].zustand)

    def test_anprobieren_fragt_jedes_modell_genau_einmal(self):
        gefragt = []

        def anprobe(region, kennung):
            gefragt.append(kennung)
            return kennung != KLEIN, "diesem Konto nicht zugeteilt"

        e = _bedrock(JUSPERFECT_MODELL_TRIAGE=KLEIN)
        zeilen = modelle_anprobieren(e, anprobe=anprobe)
        self.assertEqual({GROSS, KLEIN}, set(gefragt))
        self.assertEqual(GUT, next(z for z in zeilen if z.kennung == GROSS).zustand)
        schlecht = next(z for z in zeilen if z.kennung == KLEIN)
        self.assertEqual(SCHLECHT, schlecht.zustand)
        self.assertIn("nicht zugeteilt", schlecht.satz)

    def test_ein_ungedecktes_modell_wird_gar_nicht_erst_gefragt(self):
        """Der Aufruf würde abgewiesen; ihn trotzdem zu machen wäre Geldausgeben."""
        gefragt = []
        e = _bedrock(JUSPERFECT_MODELL_ID="meta.llama3-70b-instruct-v1:0")
        modelle_anprobieren(e, anprobe=lambda r, k: (gefragt.append(k), (True, ""))[1])
        self.assertEqual([], gefragt)


class UeberDieSchaltstelle(unittest.TestCase):

    def test_der_selbsttest_kommt_als_liste_zurueck(self):
        antwort = client(dienste()).get("/api/selbsttest")
        self.assertEqual(200, antwort.status_code, antwort.text)
        daten = antwort.json()
        self.assertTrue(daten["punkte"])
        self.assertTrue(daten["modelle"])
        self.assertIn("offen", daten)

    def test_jede_zeile_traegt_was_die_oberflaeche_anzeigt(self):
        daten = client(dienste()).get("/api/selbsttest").json()
        for zeile in daten["punkte"]:
            with self.subTest(punkt=zeile["schluessel"]):
                self.assertEqual({"schluessel", "titel", "zustand", "satz", "hinweis"}, set(zeile))
        for zeile in daten["modelle"]:
            with self.subTest(modell=zeile["kennung"]):
                self.assertIn("arbeit", zeile)

    def test_ohne_kennung_gibt_es_kein_startbild(self):
        self.assertEqual(401, client(dienste(), None).get("/api/selbsttest").status_code)


class DerLaufDarfNichtAufhalten(unittest.TestCase):
    """Aus der Kanzlei: „Das Bild ist ein wenig trocken. Vielleicht eine kleine
    Animation … Ein wegfahrender Rennwagen mit einem anschließenden Haken."

    Eine Animation in einem Arbeitsprogramm hat zwei Pflichten: Sie darf niemanden
    aufhalten, der das Bild fünfmal am Tag aufmacht, und sie muss sich abstellen
    lassen. Beides steht in der Oberfläche und kann dort auch wieder verlorengehen.
    """

    def setUp(self):
        statisch = WURZEL / "jusperfect" / "static"
        self.js = (statisch / "app.js").read_text(encoding="utf-8")
        self.css = (statisch / "styles.css").read_text(encoding="utf-8")
        self.html = (statisch / "index.html").read_text(encoding="utf-8")

    def test_der_ganze_lauf_bleibt_unter_einer_sekunde(self):
        takt = int(re.search(r"const ST_TAKT = (\d+)", self.js).group(1))
        self.assertLessEqual(takt * 8, 1000,
                             "Acht Punkte in diesem Takt dauern über eine Sekunde – "
                             "das merkt, wer das Bild mehrmals am Tag aufmacht.")

    def test_wer_bewegung_abgestellt_hat_bekommt_alles_auf_einmal(self):
        self.assertIn("prefers-reduced-motion", self.js)
        self.assertIn("prefers-reduced-motion", self.css)

    def test_der_wagen_faehrt_vorwaerts(self):
        """Aus der Kanzlei: „Der Rennwagen fährt rückwärts."

        Der Wagen zeigt in fast jeder Schrift nach links. Faehrt er nach rechts,
        sieht es aus, als setze er zurueck – gespiegelt faehrt er vorwaerts.
        """
        self.assertIn("scaleX(-1)", self.css)
        self.assertIn("ST_BLICKRICHTUNG", self.js)

    def test_erst_schieben_dann_wenden(self):
        """Die Reihenfolge ist der ganze Punkt: `scaleX` zuerst drehte auch die
        Fahrtrichtung um, und der Wagen fuehre rueckwaerts aus dem Bild."""
        import re as _re
        for stelle in _re.findall(r"transform = `([^`]+)`", self.js):
            if "translateX" in stelle and "BLICKRICHTUNG" in stelle:
                with self.subTest(stelle=stelle):
                    self.assertLess(stelle.index("translateX"), stelle.index("${ST_BLICKRICHTUNG}"))

    def test_die_strecke_und_das_ziel_stehen_in_der_seite(self):
        for teil in ('id="st-wagen"', 'id="st-ziel"', 'id="selbsttest-ergebnis"'):
            with self.subTest(teil=teil):
                self.assertIn(teil, self.html)

    def test_die_entwarnung_haengt_an_der_zahl_der_offenen_punkte(self):
        """Ein Haken, der immer erscheint, ist schlimmer als gar keiner."""
        anfang = self.js.index("function selbsttestErgebnis(")
        koerper = self.js[anfang:self.js.index("\n}", anfang)]
        self.assertIn("Alles in Ordnung", koerper)
        self.assertIn("offen", koerper)
        self.assertIn("?", koerper, "Die Entwarnung muss an eine Bedingung geknüpft sein.")


if __name__ == "__main__":
    unittest.main()


class DerAktenzugangSagtWarumEsKlemmt(unittest.TestCase):
    """Aus der Kanzlei, 23.09.2026, beim ersten Start über die Schnittstelle:

        ✗ Aktenzugang
          Der Aktenbestand ist nicht erreichbar (JurNodesFehler).
          Liegt das Laufwerk an? Ist der Ordner in den Einstellungen richtig?

    Zwei Fehler in drei Zeilen. Der Satz nannte nur den Namen der Ausnahme —
    wahr und nutzlos. Und der Rat fragte nach einem Laufwerk, das in dieser
    Einrichtung gar nicht vorkommt: Die Kanzlei arbeitete über die
    REST-Schnittstelle. Wer dem Rat folgt, sucht an einer Stelle, die es bei
    ihm nicht gibt.
    """

    def _punkt(self, adapter: str, fehler: Exception):
        from jusperfect.services.selbsttest import Selbsttest

        class Kaputt:
            def akten_suchen(self, suchbegriff=""):
                raise fehler

        e = einstellungen(JUSPERFECT_JURNODES_ADAPTER=adapter,
                          JUSPERFECT_JURNODES_URL="https://x.jur-nodes.net/api/x",
                          JUSPERFECT_JURNODES_WEBDAV="J:/Akten")
        punkte = {p.schluessel: p for p in Selbsttest(e, adapter=Kaputt()).ausfuehren().punkte}
        return punkte["akten"]

    def test_der_grund_des_adapters_steht_im_satz(self):
        """Die Meldungen des Adapters tragen einen Statuscode und nie den
        Antworttext eines Servers – sie sind eigens so gebaut und gehören
        deshalb vor die Augen des Bearbeiters."""
        from jusperfect.jurnodes.base import JurNodesFehler

        p = self._punkt("http", JurNodesFehler("jur|nodes antwortete mit Status 400."))
        self.assertIn("Status 400", p.satz)

    def test_eine_fremde_ausnahme_wird_nicht_ungeprueft_angezeigt(self):
        """Was darin steht, ist nicht geprüft – die Oberfläche ist der falsche
        Ort für einen ungeprüften Text."""
        p = self._punkt("http", RuntimeError("Mandant Testmann, Az. X-105-2026"))
        self.assertNotIn("Testmann", p.satz)
        self.assertIn("RuntimeError", p.satz)

    def test_der_rat_passt_zur_schnittstelle(self):
        from jusperfect.jurnodes.base import JurNodesFehler

        p = self._punkt("http", JurNodesFehler("abgelehnt"))
        self.assertIn("JURNODES-PRUEFEN.bat", p.hinweis)
        self.assertNotIn("Laufwerk", p.hinweis)

    def test_der_rat_passt_zum_laufwerk(self):
        from jusperfect.jurnodes.base import JurNodesFehler

        p = self._punkt("webdav", JurNodesFehler("weg"))
        self.assertIn("Laufwerk", p.hinweis)
        self.assertIn("ORDNER-PRUEFEN.bat", p.hinweis)
