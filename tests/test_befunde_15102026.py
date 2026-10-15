"""Die vier Befunde der Zweitprüfung vom 15.10.2026, je als Gegenprobe.

Die prüfende Stelle hat zu jedem Fund eine Gegenprobe mitgeliefert. Hier
stehen sie als Prüfung — nicht umformuliert, sondern so, dass sie dasselbe
belegen: dass der Fehler da war und dass er weg ist.

Die Nummern sind die des Prüfberichts:

* **R01** — ein geändertes Original bleibt im Gedächtnis veraltet.
* **R02** — zwölf mitgelieferte Prompts werden vom Frage-Endpunkt abgewiesen.
* **R03** — „Zurück zu Fassung …" verliert die Quellen der alten Fassung.
* **R04** — der Streaming-Parser kann das falsche JSON-Textfeld anzeigen.

**Warum eine eigene Datei und nicht je eine Zeile im passenden Prüfstück:**
Ein Befund, der verstreut nachgetragen wird, ist in einem halben Jahr nicht
mehr als Befund erkennbar. Wer hier liest, sieht, was eine fremde Prüfung
gefunden hat — und kann die Gegenprobe gegen den Bericht halten.
"""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from jusperfect.domain.models import (
    Entwurf, EntwurfArt, Entwurfsfassung, EntwurfStatus, Quelle,
)
from jusperfect.services.entwuerfe import teiltext
from jusperfect.services.promptbibliothek import vorrat

from tests.hilfen import client, dienste

AKTE = "VU-2026-0042"


# ── R04 ──────────────────────────────────────────────────────────────────
class R04DerStromZeigtNurDasObersteTextfeld(unittest.TestCase):
    """Gegenprobe aus dem Bericht, wörtlich übernommen.

        {"extra":{"text":"FALSCHER VORSCHAUINHALT [Q: D1-S1-P1]"},
         "text":"RICHTIGER ENTWURF [Q: D1-S1-P1]"}

    Vorher nahm ein regulärer Ausdruck das erste ``"text":``, das er fand —
    gleich in welcher Verschachtelung. Im Vorschaufenster stand dann für
    Augenblicke ein anderer Text als in der Endfassung, und die Belegprüfung
    fing das nicht: Die falsche Vorschau trug eine gültige Quellenkennung.
    """

    def test_das_verschachtelte_feld_gewinnt_nicht(self):
        roh = ('{"extra":{"text":"FALSCHER VORSCHAUINHALT [Q: D1-S1-P1]"},'
               '"text":"RICHTIGER ENTWURF [Q: D1-S1-P1]"}')
        self.assertEqual(teiltext(roh), "RICHTIGER ENTWURF [Q: D1-S1-P1]")

    def test_die_endauswertung_und_die_vorschau_sagen_dasselbe(self):
        """Der eigentliche Schaden war nicht der falsche Text, sondern der
        Unterschied zwischen beiden."""
        roh = ('{"extra":{"text":"FALSCH"},"betreff":"B","text":"RICHTIG"}')
        self.assertEqual(teiltext(roh), json.loads(roh)["text"])

    def test_tiefer_verschachtelt_zaehlt_auch_nicht(self):
        self.assertEqual(
            teiltext('{"a":{"b":{"text":"tief"}},"text":"oben"}'), "oben")
        self.assertEqual(
            teiltext('{"liste":[{"text":"im Feld"}],"text":"oben"}'), "oben")

    def test_ohne_oberstes_textfeld_steht_nichts_da(self):
        """Lieber nichts als das Falsche."""
        self.assertEqual(teiltext('{"extra":{"text":"nur tief"}}'), "")

    def test_bei_zwei_obersten_textfeldern_steht_nichts_da(self):
        """Welches gilt, entscheidet erst ``json.loads`` am Ende. Raten wäre
        dasselbe Übel in neuer Form."""
        self.assertEqual(teiltext('{"text":"A","text":"B"}'), "")

    def test_klammern_im_text_verschieben_die_ebene_nicht(self):
        self.assertEqual(teiltext('{"text":"mit } und { darin"}'),
                         "mit } und { darin")

    def test_ein_schluessel_der_nur_so_heisst_zaehlt_nicht(self):
        self.assertEqual(teiltext('{"betreff":"hier steht text: drin",'
                                  '"text":"echt"}'), "echt")

    def test_das_halbe_fluchtzeichen_wartet_weiterhin(self):
        """Die alte Eigenschaft bleibt: ``json.loads('"…\\\\u00e"')`` wirft."""
        self.assertEqual(teiltext('{"text":"Gr\\u00f'), "Gr")
        self.assertEqual(teiltext('{"text":"Gr\\'), "Gr")


# ── R03 ──────────────────────────────────────────────────────────────────
def _quelle(kennung: str) -> Quelle:
    dokument = kennung.split("-")[0]
    return Quelle(kennung=kennung, dokument_id=dokument,
                  dokument_titel=f"Testunterlage {dokument}", seite=1,
                  zitat="Die belegte Stelle.")


def _entwurf_mit_vorfassung(*, gesichert: bool) -> Entwurf:
    """Fassung 1 zitiert D1, Fassung 2 zitiert nur D2 — der Fall des Berichts."""
    vorher = Entwurfsfassung(
        nummer=1, betreff="Betreff eins", text="Alt [Q: D1-S1-P1]",
        anweisung="Kürzer fassen",
        quellen=[_quelle("D1-S1-P1")] if gesichert else [],
        hinweise=["Ein Hinweis der ersten Fassung"] if gesichert else [],
        quellen_gesichert=gesichert,
    )
    return Entwurf(
        id="probe", akte_id=AKTE, art=EntwurfArt.RSV, betreff="Betreff zwei",
        text="Neu [Q: D2-S1-P1]", quellen=[_quelle("D2-S1-P1")],
        hinweise=[], status=EntwurfStatus.ENTWURF, erstellt_von="ra-weber",
        erstellt_am=datetime.now(timezone.utc), fassung=2, vorfassungen=[vorher],
    )


class R03DieVorfassungBringtIhreQuellenMit(unittest.TestCase):
    """Gegenprobe aus dem Bericht: Fassung 1 zitiert D1, Fassung 2 nur D2.

    Vorher kam ``quellen: []`` zurück — ein Text mit einer Belegmarke, zu der
    kein Beleg mehr gehörte. Genau das, was die Belegpflicht verhindern soll,
    erzeugt vom Weg zurück.
    """

    def setUp(self):
        self.d = dienste()
        self.c = client(self.d)

    def _zuruecknehmen(self, entwurf: Entwurf) -> dict:
        self.d.speicher.entwurf_ablegen(entwurf)
        antwort = self.c.post(f"/api/entwuerfe/{entwurf.id}/zuruecknehmen")
        self.assertEqual(antwort.status_code, 200, antwort.text)
        return antwort.json()

    def test_die_quelle_der_alten_fassung_kommt_zurueck(self):
        zurueck = self._zuruecknehmen(_entwurf_mit_vorfassung(gesichert=True))
        self.assertEqual(zurueck["text"], "Alt [Q: D1-S1-P1]")
        self.assertEqual([q["kennung"] for q in zurueck["quellen"]], ["D1-S1-P1"])

    def test_jede_belegmarke_im_text_hat_ihren_beleg(self):
        """Die Richtung, die vorher nicht geprüft wurde: nicht nur, dass jede
        Quelle im Text vorkommt, sondern dass jede Marke eine Quelle hat."""
        zurueck = self._zuruecknehmen(_entwurf_mit_vorfassung(gesichert=True))
        kennungen = {q["kennung"] for q in zurueck["quellen"]}
        for marke in ("D1-S1-P1",):
            with self.subTest(marke=marke):
                self.assertIn(marke, zurueck["text"])
                self.assertIn(marke, kennungen)

    def test_die_hinweise_der_alten_fassung_kommen_mit(self):
        zurueck = self._zuruecknehmen(_entwurf_mit_vorfassung(gesichert=True))
        self.assertIn("Ein Hinweis der ersten Fassung", zurueck["hinweise"])

    def test_ein_alter_entwurf_sagt_was_ihm_fehlt(self):
        """Entwürfe aus der Zeit vor diesem Befund tragen ihre Quellen nicht.
        Mehr ist aus ihnen nicht zu holen — aber es wird benannt."""
        zurueck = self._zuruecknehmen(_entwurf_mit_vorfassung(gesichert=False))
        self.assertEqual(zurueck["quellen"], [])
        zusammen = " ".join(zurueck["hinweise"])
        self.assertIn("älteren Programmfassung", zusammen)
        self.assertIn("D1-S1-P1", zusammen)


# ── R01 ──────────────────────────────────────────────────────────────────
class _AdapterMitGeaendertemOriginal:
    """Legt sich um den Testakten-Adapter und tauscht den Inhalt eines
    Dokuments aus - wie jur|nodes, wenn jemand die Datei ersetzt."""

    def __init__(self, echt) -> None:
        self._echt = echt
        self.neuer_inhalt: bytes | None = None
        self.gelesen = 0

    def __getattr__(self, name):
        return getattr(self._echt, name)

    def dokument_laden(self, akte_id: str, dokument_id: str):
        dokument, daten = self._echt.dokument_laden(akte_id, dokument_id)
        self.gelesen += 1
        if self.neuer_inhalt is not None:
            return dokument, self.neuer_inhalt
        return dokument, daten


class R01EinGeaendertesOriginalBleibtNichtVeraltet(unittest.TestCase):
    """Gegenprobe aus dem Bericht.

    Dort wurde ein gespeicherter Auszug wiederhergestellt, der Adapter auf
    einen neuen Inhalt gestellt und das Dokument erneut angefordert:
    **HTTP 200, null Aufrufe zum Lesen des Originals, weiterhin der alte
    Text.** Eine bekannte Kennung wurde übersprungen — und das erneute
    Auswählen sah für den Bearbeiter aus wie ein Aktualisieren.
    """

    def setUp(self):
        from jusperfect.jurnodes.fixture_adapter import FixtureJurNodesAdapter
        from jusperfect.security.approval import Freigabestelle
        from tests.hilfen import einstellungen

        e = einstellungen()
        f = Freigabestelle()
        echt = FixtureJurNodesAdapter(e.fixture_pfad, f, schreibbar=False)
        self.adapter = _AdapterMitGeaendertemOriginal(echt)
        self.d = dienste(einstellungen=e, freigabestelle=f, adapter=self.adapter)
        self.c = client(self.d)
        self.sid = self.c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
        self.c.post(f"/api/sitzungen/{self.sid}/dokumente", json={"dokument_ids": ["D-001"]})

    def _laden(self, neu_laden: bool) -> dict:
        antwort = self.c.post(f"/api/sitzungen/{self.sid}/dokumente",
                              json={"dokument_ids": ["D-001"], "neu_laden": neu_laden})
        self.assertEqual(antwort.status_code, 200, antwort.text)
        return antwort.json()

    def test_erneutes_auswaehlen_sagt_dass_es_keine_aktualisierung_war(self):
        """Der Kern des Befunds: Nicht das Überspringen war der Fehler,
        sondern dass es wie ein Aktualisieren aussah."""
        vorher = self.adapter.gelesen
        hinweise = " ".join(self._laden(neu_laden=False).get("sitzung", {}).get("hinweise", []))
        self.assertEqual(self.adapter.gelesen, vorher, "ohne neu_laden wird nicht gelesen")
        self.assertIn("NICHT neu eingelesen", hinweise)

    def test_mit_neu_laden_wird_das_original_wirklich_gelesen(self):
        vorher = self.adapter.gelesen
        self._laden(neu_laden=True)
        self.assertGreater(self.adapter.gelesen, vorher)

    def test_eine_aenderung_wird_erkannt_und_nach_vorn_gesagt(self):
        self.adapter.neuer_inhalt = b"NEUER STAND: Forderung bezahlt."
        hinweise = self._laden(neu_laden=True).get("sitzung", {}).get("hinweise", [])
        self.assertTrue(hinweise, "Eine Änderung ohne Hinweis ist der Befund selbst")
        self.assertIn("geändert", hinweise[0])
        self.assertIn("ACHTUNG", hinweise[0])

    def _passagentext(self) -> str:
        daten = self.c.get(f"/api/sitzungen/{self.sid}/passagen").json()
        return " ".join(p.get("text", "") for p in daten.get("passagen", daten))

    def test_der_neue_text_steht_danach_in_den_passagen(self):
        alt = self._passagentext()
        self.assertTrue(alt.strip(), "Vorbedingung: es stand etwas da")
        self.adapter.neuer_inhalt = b"NEUER STAND: Forderung bezahlt."
        self._laden(neu_laden=True)
        neu = self._passagentext()
        self.assertIn("NEUER STAND", neu)
        self.assertNotEqual(neu, alt, "Der alte Stand steht noch da - genau der Befund")

    def test_ein_unveraendertes_dokument_wird_nicht_als_geaendert_gemeldet(self):
        """Ein Fehlalarm bei jedem Neulesen wäre so schlimm wie das Schweigen:
        Wer ihn dreimal sieht, liest ihn beim vierten Mal nicht mehr."""
        hinweise = " ".join(self._laden(neu_laden=True).get("sitzung", {}).get("hinweise", []))
        self.assertNotIn("ACHTUNG", hinweise)
        self.assertIn("unverändert", hinweise)

    def test_das_dokument_steht_danach_genau_einmal_in_der_arbeitsakte(self):
        """Neu einlesen darf keinen zweiten Eintrag erzeugen."""
        sitzung = self._laden(neu_laden=True).get("sitzung", {})
        kennungen = [g["dokument_id"] for g in sitzung.get("geladen", [])]
        self.assertEqual(kennungen.count("D-001"), 1, kennungen)


# ── R02 ──────────────────────────────────────────────────────────────────
class R02DieMitgeliefertenPromptsPassenDurchDieFrage(unittest.TestCase):
    """Zwölf von neunundvierzig waren länger, als der Frage-Endpunkt erlaubt.

    Die Oberfläche setzt den gemeinsamen Vorspann und den Bibliothekseintrag
    zusammen; die Grenze lag bei 4.000 Zeichen, die längste Kombination bei
    4.897. Eine neue Bedienfunktion scheiterte damit an mitgeliefertem Inhalt,
    ohne dass jemand etwas falsch gemacht hätte.
    """

    def test_kein_mitgelieferter_prompt_ueberschreitet_die_grenze(self):
        from jusperfect.web import MAX_FRAGE

        zu_lang = []
        for gebiet, gruppe in vorrat().items():
            basis = gruppe.get("basis", "") if isinstance(gruppe, dict) else ""
            eintraege = gruppe.get("eintraege", []) if isinstance(gruppe, dict) else gruppe
            for eintrag in eintraege:
                text = eintrag.get("text", "")
                voll = f"{basis}\n\n{text}" if basis else text
                if len(voll) > MAX_FRAGE:
                    zu_lang.append((len(voll), gebiet, eintrag.get("titel", "?")))
        self.assertEqual(zu_lang, [], f"{len(zu_lang)} zu lang: {sorted(zu_lang)[-3:]}")

    def test_die_bibliothek_laesst_nichts_zu_was_die_frage_abweist(self):
        """Sonst speichert jemand etwas, das er danach nicht benutzen kann."""
        from jusperfect.services.promptbibliothek import MAX_ZEICHEN
        from jusperfect.web import MAX_FRAGE

        self.assertLessEqual(MAX_ZEICHEN, MAX_FRAGE)

    def test_der_laengste_mitgelieferte_prompt_geht_durch_den_endpunkt(self):
        """Die Gegenprobe des Berichts: nicht die Zahl prüfen, sondern senden.

        Zusammengesetzt wie in der Oberfläche (`app.js`, `bibReiter`):
        Vorspann, Leerzeile, Leerzeile, Modul.
        """
        d = dienste()
        c = client(d)
        sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})

        laengster = ""
        for gruppe in vorrat().values():
            basis = gruppe.get("basis", "") if isinstance(gruppe, dict) else ""
            eintraege = gruppe.get("eintraege", []) if isinstance(gruppe, dict) else gruppe
            for eintrag in eintraege:
                text = eintrag.get("text", "")
                voll = f"{basis}\n\n{text}" if basis else text
                if len(voll) > len(laengster):
                    laengster = voll
        self.assertGreater(len(laengster), 4000, "Der Fall des Berichts muss drin sein")

        antwort = c.post(f"/api/sitzungen/{sid}/frage", json={"frage": laengster})
        self.assertNotEqual(antwort.status_code, 422,
                            f"{len(laengster)} Zeichen abgewiesen: {antwort.text[:300]}")

    def test_die_gespeicherte_runde_schneidet_die_frage_nicht_ab(self):
        """Vorher wurde bei 4.000 Zeichen stillschweigend gekürzt - auch wenn
        die Schnittstelle den langen Prompt angenommen hätte."""
        from jusperfect.domain.models import MAX_FRAGE
        import inspect

        from jusperfect.services import gedaechtnis, sitzung

        for modul in (sitzung, gedaechtnis):
            with self.subTest(modul=modul.__name__):
                quelle = inspect.getsource(modul)
                self.assertNotIn("[:4000]", quelle)
                self.assertIn("[:MAX_FRAGE]", quelle)
        self.assertGreaterEqual(MAX_FRAGE, 8000)
