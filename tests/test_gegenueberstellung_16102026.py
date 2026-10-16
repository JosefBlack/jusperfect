"""Die Gegenüberstellung beim Einlesen – und die Zeichengrenze, die sie blockte.

Aus der Kanzlei am 16.10.2026, vier Dinge in einer Nachricht:

    Ich kann verschiedene Funktionen nicht durchführen, da eine
    Zeichenbeschränkung gilt. Prompt Bibliothek bitte nach oben. Es gibt beim
    Einlesen Fehlermeldungen, diese sind aber nicht nachvollziehbar. Eine
    Gegenüberstellung wäre wichtig. Bitte wieder Fenster links und rechts.
    Rechts jurnodes und links jusperfect. Veranschaulichen, welche Datei
    erfolgreich eingelesen würde durch grünen Haken hinter der Datei bei
    jusperfect. Auch den Leseprozess nachvollziehbar darstellen. Datei für
    Datei abhaken.

**Warum die Meldungen nicht nachvollziehbar waren – zwei Gründe.**

*Erstens:* Gemeldet wurde eine Bilanz in Worten. „14 von 55 Dokumenten
gelesen, 41 nicht: 38 ohne erkennbaren Text …" sagt die Zahl, aber nicht,
**welche** Datei und warum. Wer die 41 sucht, sucht von Hand.

*Zweitens – und das war schlimmer:* Die Oberfläche liest in Portionen zu
fünf, und gerechnet wurde je Aufruf. Nach 55 Dokumenten stand oben die Bilanz
der **letzten Portion**: „1 von 2 gelesen, 1 nicht", während in Wahrheit 41
fehlten. Eine Zahl, die kleiner ist als der Schaden, ist schlimmer als keine.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from unittest import mock

from jusperfect.domain.models import Akte, Dokument, Seite, Sitzung
from jusperfect.services.extraktion import NichtUnterstuetzt
from jusperfect.jurnodes.base import JurNodesFehler

WURZEL = Path(__file__).resolve().parents[1]
JS = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")
HTML = (WURZEL / "jusperfect" / "static" / "index.html").read_text(encoding="utf-8")
CSS = (WURZEL / "jusperfect" / "static" / "styles.css").read_text(encoding="utf-8")


def _dienst(adapter):
    from tests.test_mehrere_dokumente import _dienst as bauen

    return bauen(adapter)


class _Adapter:
    """Liefert Text, einen Fehler oder ein leeres Blatt – je nach Kennung."""

    def __init__(self, kaputt=(), leer=(), jurnodes=()):
        self.kaputt, self.leer, self.jurnodes = set(kaputt), set(leer), set(jurnodes)

    def dokument_laden(self, akte_id, dokument_id):
        if dokument_id in self.jurnodes:
            raise JurNodesFehler("jurnodes gibt dieses Dokument nicht heraus.")
        endung = ".doc" if dokument_id in self.kaputt else ".txt"
        d = Dokument(id=dokument_id, akte_id=akte_id, titel=f"Blatt {dokument_id}",
                     dateiname=f"{dokument_id}{endung}", mime_typ="text/plain")
        return d, b"egal"

    def inhalte_vergessen(self, *a, **k):
        pass


def _extrahieren(kaputt, leer):
    def gefaelscht(dokument, daten, ocr, sitzung_id):
        if dokument.id in kaputt:
            raise NichtUnterstuetzt("Altes Microsoft-Format (.doc).")
        if dokument.id in leer:
            return [Seite(nummer=1, text="")], False
        return [Seite(nummer=1, text="Ein lesbarer Satz mit Inhalt.")], False
    return gefaelscht


class DieBilanzGiltFuerDieGanzeSitzung(unittest.TestCase):
    """Der zweite Grund – und der gefährlichere."""

    def setUp(self):
        self.sitzung = Sitzung(id="s1", nutzer_id="ra-weber", akte_id="rec-1",
                               akte=Akte(id="rec-1", aktenzeichen="X-100-2026", bezeichnung="Probe"))

    def _laden(self, ids, kaputt=(), leer=(), jurnodes=()):
        d = _dienst(_Adapter(kaputt, leer, jurnodes))
        with mock.patch.object(type(d), "laden", return_value=self.sitzung), \
                mock.patch("jusperfect.services.sitzung.text_extrahieren",
                           side_effect=_extrahieren(set(kaputt), set(leer))):
            return d.dokumente_laden(mock.MagicMock(), "s1", ids)

    def test_zwei_portionen_ergeben_eine_bilanz_ueber_beide(self):
        """Der Befund: Vorher stand hier die Bilanz der letzten Portion."""
        self._laden(["D-1", "D-2", "D-3", "D-4", "D-5"], kaputt={"D-2", "D-4"})
        sitzung = self._laden(["D-6", "D-7"], kaputt={"D-7"})
        self.assertIn("4 von 7 Dokumenten gelesen, 3 nicht", sitzung.hinweise[0])

    def test_es_steht_immer_nur_eine_bilanz_da(self):
        """Vier Portionen ergäben sonst vier Bilanzen untereinander."""
        self._laden(["D-1", "D-2"], kaputt={"D-2"})
        self._laden(["D-3", "D-4"], kaputt={"D-4"})
        sitzung = self._laden(["D-5", "D-6"], kaputt={"D-6"})
        bilanzen = [h for h in sitzung.hinweise
                    if re.match(r"^\d+ von \d+ Dokumenten gelesen, ", h)]
        self.assertEqual(len(bilanzen), 1, bilanzen)

    def test_die_gruende_stehen_weiter_getrennt(self):
        """Ein Scan braucht Texterkennung, ein Format den Hersteller, ein
        nicht geliefertes Dokument jurnodes."""
        sitzung = self._laden(["D-1", "D-2", "D-3", "D-4"],
                              kaputt={"D-2"}, leer={"D-3"}, jurnodes={"D-4"})
        bilanz = sitzung.hinweise[0]
        self.assertIn("1 ohne erkennbaren Text", bilanz)
        self.assertIn("1 in einem Format", bilanz)
        self.assertIn("1 von jurnodes nicht", bilanz)

    def test_die_dateiarten_bleiben_in_der_bilanz(self):
        """Sie stehen jetzt an der Datei und werden daraus gerechnet."""
        sitzung = self._laden(["D-1", "D-2"], kaputt={"D-1", "D-2"})
        self.assertIn("Dateiarten:", sitzung.hinweise[0])
        self.assertIn(".doc 2", sitzung.hinweise[0])


class JedeDateiTraegtIhrenAusgang(unittest.TestCase):
    """Der erste Grund: Die Bilanz sagt die Zahl, nicht die Datei."""

    def setUp(self):
        self.sitzung = Sitzung(id="s1", nutzer_id="ra-weber", akte_id="rec-1",
                               akte=Akte(id="rec-1", aktenzeichen="X-100-2026", bezeichnung="Probe"))

    def _laden(self, ids, kaputt=(), leer=(), jurnodes=()):
        d = _dienst(_Adapter(kaputt, leer, jurnodes))
        with mock.patch.object(type(d), "laden", return_value=self.sitzung), \
                mock.patch("jusperfect.services.sitzung.text_extrahieren",
                           side_effect=_extrahieren(set(kaputt), set(leer))):
            return d.dokumente_laden(mock.MagicMock(), "s1", ids)

    def test_je_datei_ein_eintrag_mit_grund_und_art(self):
        sitzung = self._laden(["D-1", "D-2", "D-3", "D-4"],
                              kaputt={"D-2"}, leer={"D-3"}, jurnodes={"D-4"})
        nach_art = {x.dokument_id: x.art for x in sitzung.nicht_gelesen}
        self.assertEqual(nach_art, {"D-2": "format", "D-3": "leer", "D-4": "jurnodes"})
        for x in sitzung.nicht_gelesen:
            with self.subTest(dokument=x.dokument_id):
                self.assertTrue(x.grund.strip(), "Ohne Grund ist der Eintrag nichts wert.")

    def test_der_grund_sagt_was_zu_tun_ist(self):
        """Eine Meldung, die den Ausweg verschweigt, kostet mehr Zeit als sie
        spart. Beim leeren Blatt ist der Ausweg die Klammer am Eingabefeld."""
        sitzung = self._laden(["D-1"], leer={"D-1"})
        self.assertIn("von Hand einfügen", sitzung.nicht_gelesen[0].grund)

    def test_ein_zweiter_versuch_loescht_den_alten_befund(self):
        """Sonst stünde die Datei grün links und rot daneben."""
        self._laden(["D-1"], kaputt={"D-1"})
        self.assertEqual(len(self.sitzung.nicht_gelesen), 1)
        sitzung = self._laden(["D-1"])          # diesmal geht es
        self.assertEqual(sitzung.nicht_gelesen, [])
        self.assertEqual([g.dokument_id for g in sitzung.geladen], ["D-1"])

    def test_was_nicht_angefordert_wurde_bleibt_stehen(self):
        """Der Befund von D-2 geht niemanden etwas an, der D-3 liest."""
        self._laden(["D-1", "D-2"], kaputt={"D-2"})
        sitzung = self._laden(["D-3"])
        self.assertEqual([x.dokument_id for x in sitzung.nicht_gelesen], ["D-2"])

    def test_gelesene_dokumente_stehen_nicht_in_der_liste(self):
        sitzung = self._laden(["D-1", "D-2"])
        self.assertEqual(sitzung.nicht_gelesen, [])


class DieOberflaecheStelltGegenueber(unittest.TestCase):
    """Rechts die Akte, links was daraus geworden ist."""

    EXPLORER = HTML[HTML.index('<dialog id="explorer-dialog"'):HTML.index('<dialog id="ged-dialog"')]

    def test_zwei_spalten_in_der_gewuenschten_richtung(self):
        self.assertIn("jusperfect · Arbeitsakte", self.EXPLORER)
        self.assertIn("jurnodes · Akte", self.EXPLORER)
        self.assertLess(self.EXPLORER.index('id="arbeit-liste"'),
                        self.EXPLORER.index('id="quelle-liste"'))

    def test_der_gruene_haken_steht_hinter_der_datei_bei_jusperfect(self):
        """Wörtlich aus der Kanzlei. Grün ist die Farbe des Gelesenen."""
        self.assertIn('marke: "\\u2713"', JS)
        self.assertIn(".explorer-eintrag.gelesen { border-color: var(--gruen)", CSS)

    def test_gelesen_aber_nicht_ganz_ist_nicht_gruen(self):
        """Eine Datei mit einer Seite ohne Text ist nicht vollständig
        gelesen. Grün wäre gelogen – sie steht in Bernstein."""
        self.assertIn(".explorer-eintrag.gelesen.teilweise", CSS)
        block = JS[JS.index("function arbeitsZeile("):JS.index("/** Die Ueberschrift eines Ordners")]
        self.assertIn("seiten_ohne_text", block)
        self.assertIn('li.classList.add("teilweise")', block)

    def test_die_vier_zustaende_einer_datei(self):
        """Wartet, wird gelesen, gelesen, nicht gelesen – mehr gibt es nicht."""
        block = JS[JS.index("const LESEZEICHEN = {"):JS.index("/** Was mit dieser Datei")]
        for zustand in ("gelesen", "liest", "wartet", "fehler"):
            self.assertIn(f"{zustand}:", block, zustand)

    def test_der_grund_steht_an_der_datei_und_nicht_in_einer_bilanz(self):
        block = JS[JS.index("function arbeitsZeile("):JS.index("/** Die Ueberschrift eines Ordners")]
        self.assertIn("e.grund", block)

    def test_der_leseprozess_haekelt_datei_fuer_datei_ab(self):
        """„Auch den Leseprozess nachvollziehbar darstellen."""
        lesen = JS[JS.index("async function dokumenteInPortionenLesen("):
                   JS.index("// ── Woran zuletzt gearbeitet wurde")]
        self.assertIn('melde(teil, "liest")', lesen)
        self.assertIn("beiPortion", lesen)
        # Und zwar auch, wenn der Aufruf platzt: Keine Zeile bleibt haengen.
        self.assertIn("finally", lesen)

    def test_der_dialog_bleibt_waehrend_des_lesens_offen(self):
        """Ein Balken hinter dem Vorhang sagt niemandem etwas."""
        self.assertIn('id="explorer-lesezeile"', self.EXPLORER)
        self.assertIn('id="explorer-anhalten"', self.EXPLORER)
        # Der Knopf schliesst den Dialog nicht mehr von selbst.
        self.assertIn('<button type="button" id="explorer-uebernehmen"', self.EXPLORER)

    def test_der_aeussere_balken_tritt_zurueck_solange_der_dialog_steht(self):
        block = JS[JS.index("function lesefortschritt("):JS.index("function wegeSperren(")]
        self.assertIn("explorerLiest", block)

    def test_ging_etwas_nicht_bleibt_das_fenster_offen(self):
        block = JS[JS.index("async function explorerUebernehmen("):
                   JS.index("async function explorerNachbereiten(")]
        self.assertIn("misslungen.length", block)
        self.assertIn("explorer.fertig = true", block)
        # Gesagt wird es IM Dialog - eine Meldung dahinter laege hinter dem
        # Vorhang und waere nicht zu sehen.
        self.assertIn("explorerLesenZeigen(misslungen.length === 1", block)

    def test_die_haken_bleiben_nach_einem_fehlschlag_stehen(self):
        """Ein zweites „Übernehmen" holt genau die noch einmal."""
        block = JS[JS.index("async function explorerUebernehmen("):
                   JS.index("async function explorerNachbereiten(")]
        self.assertNotIn("explorer.gewaehlt = new Set(explorer.geladen)", block)


class DieZeichengrenze(unittest.TestCase):
    """„Ich kann verschiedene Funktionen nicht durchführen, da eine
    Zeichenbeschränkung gilt."

    Betroffen sind Aktenanalyse und Zeitstrahl: Beide brechen ab, statt
    stillschweigend zu kürzen – was richtig ist. Die Grenze selbst war eine
    frühe, vorsichtige Zahl ohne Herleitung und ließ vom Fenster des Modells
    rund ein Viertel ungenutzt.
    """

    def test_sie_ist_hergeleitet_und_nicht_geraten(self):
        from jusperfect.config import Einstellungen

        self.assertEqual(Einstellungen.max_passagen_zeichen, 300_000)
        quelle = (WURZEL / "jusperfect" / "config.py").read_text(encoding="utf-8")
        block = quelle[quelle.index("# Verarbeitung"):quelle.index("max_passagen_zeichen: int")]
        # Die Herleitung gehört dazu: Eine Zahl ohne Begründung wird beim
        # nächsten Modellwechsel wieder geraten.
        self.assertIn("200.000 Token", block)
        self.assertIn("2,8", block)

    def test_die_meldung_nennt_die_stellschraube(self):
        """Eine Grenze, von der man nicht weiß, dass sie eine Einstellung ist,
        sieht aus wie eine Eigenschaft des Programms."""
        from jusperfect.services.analyse import _grenze_aendern

        text = _grenze_aendern(300_000)
        self.assertIn("JUSPERFECT_MAX_PASSAGEN_ZEICHEN", text)
        self.assertIn("300.000", text)
        # Und was ein höherer Wert kostet. Ein Rat, der die Rechnung
        # verschweigt, ist kein Rat.
        self.assertIn("teurer", text)

    def test_sie_steht_in_beiden_auswegen(self):
        from jusperfect.services.analyse import _ausweg

        for gedaechtnis in (True, False):
            with self.subTest(gedaechtnis=gedaechtnis):
                text = _ausweg("Aktenanalyse", 900_000, 300_000, gedaechtnis)
                self.assertIn("JUSPERFECT_MAX_PASSAGEN_ZEICHEN", text)

    def test_ein_zu_langer_aufruf_wird_erklaert_und_nicht_verwechselt(self):
        """AWS schreibt „Input is too long" – und, bei einer ganz anderen
        Sache, „Too many tokens per day". Das eine ist die Startdatei, das
        andere ist Warten."""
        from botocore.exceptions import ClientError

        from jusperfect.providers.bedrock import _abgelehnt

        zu_lang = ClientError({"Error": {
            "Code": "ValidationException",
            "Message": "Input is too long for requested model."}}, "Converse")
        self.assertIn("JUSPERFECT_MAX_PASSAGEN_ZEICHEN", _abgelehnt(zu_lang, "modell"))

        # Die Gegenprobe: dieselbe Richtung, anderer Fall. Eine Mengengrenze
        # je Tag schickte den Bearbeiter sonst in die Startdatei, wo nichts
        # zu finden ist - er muss warten.
        zu_viel = ClientError({"Error": {
            "Code": "ThrottlingException",
            "Message": "Too many tokens per day"}}, "Converse")
        self.assertNotIn("JUSPERFECT_MAX_PASSAGEN_ZEICHEN", _abgelehnt(zu_viel, "modell"))


if __name__ == "__main__":
    unittest.main()
