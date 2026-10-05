"""Die genaue Stelle statt der ganzen Passage.

Aus der Kanzlei: „Da wird nur zum Beispiel eine Seite markiert und nicht genau
die Information, die man braucht. Das Überprüfen dauert bisher ja immer noch zu
lange, um effizienter zu arbeiten."

Eine Fundstelle zeigt auf eine Passage von bis zu 1.500 Zeichen. Wer sie
nachliest, suchte darin noch einmal von Hand nach dem Datum. Diese Prüfung
sucht die Stelle im Programm – ohne Modell, nur aus dem, was in der Passage
steht.

Zwei Zusagen stehen hier gegeneinander und müssen beide halten:

* Sie soll die richtige Stelle finden, sonst nützt sie nichts.
* Sie darf nie eine falsche finden. Eine falsch markierte Stelle führt den
  Blick weg von dem, was wirklich dasteht – schlimmer als gar keine Markierung.
  Deshalb gibt es im Zweifel keinen Treffer, und es bleibt bei der ganzen Passage.
"""

from __future__ import annotations

import unittest

from jusperfect.services.fundstelle import treffer_finden

PASSAGE = (
    "Aktenvermerk über das Erstgespräch\n\n"
    "Sie ist seit dem 01.09.2018 bei der Nordwerk Metallbau GmbH in Gelsenkirchen "
    "als Industriekauffrau beschäftigt. Zuletzt verdiente sie 3.940,00 EUR brutto "
    "monatlich bei einer Wochenarbeitszeit von 38 Stunden.\n\n"
    "Am 04.05.2026 sei sie gegen 16:30 Uhr in das Büro des Geschäftsführers gerufen "
    "worden. Dort habe man ihr ein Schreiben überreicht, mit dem das Arbeitsverhältnis "
    "fristlos gekündigt werde."
)


class SieFindetDieRichtigeStelle(unittest.TestCase):
    def test_ein_datum_fuehrt_zum_richtigen_satz(self):
        t = treffer_finden("Die Kündigung wurde der Mandantin am 04.05.2026 überreicht.", PASSAGE)
        self.assertIsNotNone(t)
        self.assertIn("Am 04.05.2026", t.zitat)
        self.assertNotIn("01.09.2018", t.zitat, "Das falsche Datum wäre schlimmer als keines.")

    def test_ein_betrag_fuehrt_zum_richtigen_satz(self):
        t = treffer_finden("Das Bruttomonatsgehalt beträgt 3.940,00 EUR.", PASSAGE)
        self.assertIsNotNone(t)
        self.assertIn("3.940,00 EUR", t.zitat)

    def test_die_harte_angabe_wird_einzeln_markiert(self):
        """Nicht der Satz allein – die Zahl darin ist das, was man sucht."""
        t = treffer_finden("Das Bruttomonatsgehalt beträgt 3.940,00 EUR.", PASSAGE)
        markiert = [PASSAGE[a:e] for a, e in t.marken]
        self.assertIn("3.940,00 EUR", markiert)

    def test_ein_eigenname_wird_mitmarkiert(self):
        """„Fahrtrichtung Stuttgart" – der Name trägt oft die eigentliche Auskunft."""
        t = treffer_finden("Sie arbeitet in Gelsenkirchen bei der Nordwerk Metallbau GmbH.", PASSAGE)
        self.assertIsNotNone(t)
        markiert = [PASSAGE[a:e] for a, e in t.marken]
        self.assertIn("Gelsenkirchen", markiert)

    def test_die_stellen_zeigen_wirklich_auf_die_passage(self):
        """Die Zahlen sind Zeichenpositionen – zeigen sie daneben, färbt sich Falsches."""
        t = treffer_finden("Die Kündigung wurde am 04.05.2026 überreicht.", PASSAGE)
        self.assertEqual(PASSAGE[t.start:t.ende], t.zitat)
        for anfang, ende in t.marken:
            self.assertTrue(t.start <= anfang < ende <= t.ende)

    def test_die_marken_ueberschneiden_sich_nicht(self):
        """Sonst entstünden beim Einfärben verschachtelte Markierungen."""
        t = treffer_finden("Sie verdiente in Gelsenkirchen 3.940,00 EUR brutto monatlich.", PASSAGE)
        letzte = -1
        for anfang, ende in t.marken:
            self.assertGreaterEqual(anfang, letzte)
            letzte = ende


class ImZweifelKeineStelle(unittest.TestCase):
    def test_ohne_beruehrung_gibt_es_keinen_treffer(self):
        self.assertIsNone(treffer_finden("Zum Wetter am Unfalltag sagt die Akte nichts.", PASSAGE))

    def test_ein_einzelnes_allerweltswort_genuegt_nicht(self):
        """„Schreiben" allein darf nicht irgendeinen Satz auszeichnen."""
        self.assertIsNone(treffer_finden("Ein Schreiben.", PASSAGE))

    def test_leere_eingaben_ergeben_nichts(self):
        for aussage, passage in (("", PASSAGE), ("Irgendetwas", ""), ("", "")):
            with self.subTest(aussage=aussage[:10]):
                self.assertIsNone(treffer_finden(aussage, passage))

    def test_ein_datum_zerreisst_den_satz_nicht(self):
        """Die Punkte in „04.05.2026" sind keine Satzenden."""
        t = treffer_finden("Am 04.05.2026 wurde sie gerufen.", PASSAGE)
        self.assertIn("04.05.2026", t.zitat)
        self.assertGreater(len(t.zitat), 30, "Der Satz wurde am Datum zerschnitten.")


class InDerBelegpruefung(unittest.TestCase):
    """Der Weg von der Antwort bis in die Quelle."""

    def _index(self):
        from jusperfect.domain.models import Passage
        from jusperfect.services.quellen import index_bauen

        return index_bauen([Passage(kennung="D1-S1-P1", dokument_id="D-001",
                                    dokument_titel="Aktenvermerk", seite=1, text=PASSAGE)])

    def test_die_quelle_traegt_die_stelle_der_zugehoerigen_aussage(self):
        from jusperfect.services.belegpflicht import aussage_fail_closed

        belegt = aussage_fail_closed("Gekündigt wurde am 04.05.2026. [Q: D1-S1-P1]", self._index())
        quelle = belegt.quellen[0]
        self.assertIsNotNone(quelle.treffer_start)
        self.assertIn("04.05.2026", quelle.zitat)
        self.assertNotIn("Aktenvermerk über das Erstgespräch", quelle.zitat,
                         "Das Zitat soll die Stelle sein, nicht der Anfang der Passage.")

    def test_ohne_passende_stelle_bleibt_es_beim_anfang_der_passage(self):
        from jusperfect.services.belegpflicht import aussage_fail_closed

        belegt = aussage_fail_closed("Dazu sagt die Akte nichts. [Q: D1-S1-P1]", self._index())
        quelle = belegt.quellen[0]
        self.assertIsNone(quelle.treffer_start)
        self.assertTrue(quelle.zitat.startswith("Aktenvermerk"))

    def test_auch_ein_entwurf_bekommt_die_stelle(self):
        """Im Entwurf ist das Nachprüfen die eigentliche Arbeit."""
        from jusperfect.services.quellen import zitate_aufloesen

        _, quellen, _ = zitate_aufloesen(
            "Das Arbeitsverhältnis wurde am 04.05.2026 fristlos gekündigt. [Q: D1-S1-P1]",
            self._index())
        self.assertIn("04.05.2026", quellen[0].zitat)

    def test_auch_ein_chronologieeintrag_bekommt_die_stelle(self):
        """Sein Datum steht als 2026-05-04 da, im Dokument als 04.05.2026."""
        from jusperfect.domain.models import ChronologieEintrag
        from jusperfect.services.belegpflicht import eintraege_fail_closed

        eintraege = [ChronologieEintrag(datum="2026-05-04", ereignis="Kündigung überreicht")]
        roh = [{"datum": "2026-05-04", "ereignis": "Kündigung überreicht", "quellen": ["D1-S1-P1"]}]
        behalten, verworfen = eintraege_fail_closed(
            eintraege, roh, self._index(), lambda r: r.get("quellen", []))
        self.assertEqual(verworfen, 0)
        quelle = behalten[0].quellen[0]
        self.assertIn("04.05.2026", quelle.zitat)
        self.assertEqual([PASSAGE[a:e] for a, e in quelle.marken], ["04.05.2026"])


if __name__ == "__main__":
    unittest.main()


class SchreibweisenTreffenSich(unittest.TestCase):
    """Dasselbe Datum in zwei Notationen ist dasselbe Datum."""

    def test_iso_findet_deutsches_datum(self):
        t = treffer_finden("Ereignis am 2026-05-04.", PASSAGE)
        self.assertIsNotNone(t)
        self.assertIn("04.05.2026", t.zitat)

    def test_zweistelliges_jahr_meint_dieses_jahrhundert(self):
        t = treffer_finden("Ereignis am 04.05.26.", PASSAGE)
        self.assertIsNotNone(t)
        self.assertIn("04.05.2026", t.zitat)


class InDerOberflaeche(unittest.TestCase):
    """Was der Server ausrechnet, muss auch zu sehen sein.

    Gemessen an einem echten Chromium (scratchpad/marke.mjs): Nach dem Klick auf
    einen Beleg trägt genau eine Passage die Klasse „genau", hervorgehoben ist
    „30.09.2026", der blasse Satz ist „30.09.2026 gekündigt werde." – und der
    Klick auf dieselbe Angabe im Antworttext führt an dieselbe Stelle.
    """

    from pathlib import Path as _Path

    STATISCH = _Path(__file__).resolve().parent.parent / "jusperfect" / "static"

    def setUp(self) -> None:
        self.app = (self.STATISCH / "app.js").read_text(encoding="utf-8")
        self.css = (self.STATISCH / "styles.css").read_text(encoding="utf-8")

    def test_die_stelle_wird_gefaerbt_und_die_angabe_hervorgehoben(self):
        block = self.app[self.app.index("function satzFaerben("):self.app.index("function markierungenLoeschen(")]
        self.assertIn('stelle.className = "stelle"', block)
        self.assertIn('createElement("mark")', block)
        self.assertIn(".passage .stelle mark", self.css)

    def test_ohne_stelle_faerbt_sich_die_ganze_passage_wie_bisher(self):
        """Der Rückfall muss stehen – lieber grob als falsch."""
        block = self.app[self.app.index("function satzFaerben("):self.app.index("function markierungenLoeschen(")]
        self.assertIn("satzEl.textContent = text;", block)
        self.assertIn("return false;", block)

    def test_der_ganze_absatz_leuchtet_nicht_mehr_mit(self):
        self.assertIn(".passage.markiert.genau { background: transparent; }", self.css)

    def test_gesprungen_wird_auf_die_stelle_nicht_auf_den_absatz(self):
        """Bei einer langen Passage stünde die Zeile sonst unten aus dem Bild."""
        block = self.app[self.app.index("function passageMarkieren("):self.app.index("// ── Belege")]
        self.assertIn('satzEl.querySelector(".stelle")', block)

    def test_die_angaben_im_antworttext_sind_anklickbar(self):
        block = self.app[self.app.index("function angabenAnklickbar("):self.app.index("function textMitBelegen(")]
        self.assertIn("passageMarkieren(kennung, null, aussage)", block)
        self.assertIn(".angabe", self.css)

    def test_eine_angabe_ohne_bekannten_beleg_bleibt_gewoehnlicher_text(self):
        """Ein Klick, der nirgends hinführt, wäre schlimmer als kein Klick."""
        block = self.app[self.app.index("function angabenAnklickbar("):self.app.index("function textMitBelegen(")]
        self.assertIn("if (!kennung || !passagenIndex[kennung])", block)

    def test_die_belegkarte_zeigt_die_stelle_statt_des_passagenanfangs(self):
        block = self.app[self.app.index("function zeigeBelege("):self.app.index("// ── Cowork-Thread")]
        self.assertIn("belegQuellen[kennung]", block)
        self.assertIn("(q && q.zitat)", block)


class ZweideutigesWirdNichtGeraten(unittest.TestCase):
    """Aus der Kanzlei: „wenn ein Wort häufiger in einem Text vorkommt, dann ist
    es ja, als würde man ein Wort suchen. Jetzt müsste natürlich die Information,
    die markiert wird, perfekt zu der Textstelle passen."

    Genau da trägt eine Punktzahl allein nicht: Stehen dieselben Wörter in zwei
    Sätzen gleich oft, gewänne sonst schlicht der erste – und in der Hälfte der
    Fälle wäre es der falsche, ohne dass man es der Markierung ansähe.
    """

    # Mit einem Satz dazwischen: Nachbarn werden zusammengefasst statt verworfen
    # (siehe BenachbarteSaetzeGehoerenZusammen), entfernte Stellen nicht.
    ZWEIMAL = ("Die Rechnung vom 02.09.2025 blieb offen. "
               "Dazwischen geschah nichts von Belang. "
               "Die Mahnung vom 02.09.2025 blieb offen.")

    def test_zwei_gleich_gute_stellen_ergeben_keine(self):
        self.assertIsNone(treffer_finden("Es blieb offen am 02.09.2025.", self.ZWEIMAL))

    def test_ein_unterscheidendes_wort_entscheidet(self):
        t = treffer_finden("Die Mahnung vom 02.09.2025 blieb offen.", self.ZWEIMAL)
        self.assertIsNotNone(t)
        self.assertIn("Mahnung", t.zitat)
        self.assertNotIn("Rechnung", t.zitat)

    def test_eine_woertliche_wortfolge_schlaegt_verstreute_woerter(self):
        passage = ("Der Empfang wurde bestätigt. "
                   "Der Geschäftsführer bestätigte den Empfang des Schreibens am 21.06.2025.")
        t = treffer_finden("Der Geschäftsführer bestätigte den Empfang des Schreibens.", passage)
        self.assertIsNotNone(t)
        self.assertIn("21.06.2025", t.zitat)

    def test_die_laengste_folge_zaehlt_woerter_in_der_reihenfolge(self):
        from jusperfect.services.fundstelle import _laengste_folge

        self.assertEqual(_laengste_folge(["a", "b", "c", "d"], ["x", "b", "c", "y"]), 2)
        self.assertEqual(_laengste_folge(["a", "b"], ["b", "a"]), 1)
        self.assertEqual(_laengste_folge([], ["a"]), 0)


class BenachbarteSaetzeGehoerenZusammen(unittest.TestCase):
    """Eine Aussage steht oft in zwei aufeinanderfolgenden Sätzen.

    „Am 04.05.2026 sei sie gerufen worden. Dort habe man ihr ein Schreiben
    überreicht, mit dem gekündigt werde." – Wer schreibt „am 04.05.2026 wurde
    fristlos gekündigt", meint beide. Sie zu verwerfen, weil sie gleich gut
    passen, wäre die falsche Vorsicht: Zweideutig ist das nicht.
    """

    def test_zwei_nachbarn_werden_zusammengefasst(self):
        t = treffer_finden("Das Arbeitsverhältnis wurde am 04.05.2026 fristlos gekündigt.", PASSAGE)
        self.assertIsNotNone(t)
        self.assertIn("04.05.2026", t.zitat)
        self.assertIn("fristlos", t.zitat)

    def test_der_zusammengefasste_bereich_bleibt_zusammenhaengend(self):
        t = treffer_finden("Das Arbeitsverhältnis wurde am 04.05.2026 fristlos gekündigt.", PASSAGE)
        self.assertEqual(PASSAGE[t.start:t.ende], t.zitat)

    def test_entfernte_stellen_werden_weiterhin_nicht_geraten(self):
        weit = ("Die Rechnung vom 02.09.2025 blieb offen. "
                "Dazwischen geschah nichts von Belang. "
                "Die Mahnung vom 02.09.2025 blieb offen.")
        self.assertIsNone(treffer_finden("Es blieb offen am 02.09.2025.", weit))


class JederVerweisHatSeineEigeneStelle(unittest.TestCase):
    """Aus der Kanzlei: „wenn man dann schon auf den zweiten Verweis
    draufdrückt, dann springt er leider nicht genau wie bei der ersten
    Markierung zur Quelle, woher die Info stammt."

    Der Grund lag tiefer, als er aussah: Eine Quelle gehört zu einer *Passage*,
    eine Fundstelle aber zu einer *Aussage*. Zitieren zwei Sätze dieselbe
    Passage, entsteht nur eine Quelle – und die kann nur eine der beiden
    Stellen tragen. Der zweite Verweis sprang deshalb an die Stelle des ersten.
    """

    ZWEIMAL = ("Sie ist seit dem 01.09.2018 beschäftigt. "
               "Zuletzt verdiente sie 3.940,00 EUR brutto monatlich. "
               "Dazwischen lag nichts von Belang. "
               "Am 04.05.2026 wurde ihr fristlos gekündigt.")

    def test_die_quelle_allein_kann_es_nicht_leisten(self):
        """Festgehalten, damit niemand die Umgehung wieder ausbaut."""
        from jusperfect.domain.models import Passage
        from jusperfect.services.belegpflicht import aussage_fail_closed
        from jusperfect.services.quellen import index_bauen

        index = index_bauen([Passage(kennung="D1-S1-P1", dokument_id="D-001",
                                     dokument_titel="Vermerk", seite=1, text=self.ZWEIMAL)])
        belegt = aussage_fail_closed(
            "Das Gehalt betrug 3.940,00 EUR. [Q: D1-S1-P1]\\n"
            "Gekündigt wurde am 04.05.2026. [Q: D1-S1-P1]", index)
        self.assertEqual(len(belegt.quellen), 1, "Eine Passage, eine Quelle – so ist es gedacht.")

    def test_je_aussage_kommt_die_richtige_stelle_heraus(self):
        erste = treffer_finden("Das Gehalt betrug 3.940,00 EUR.", self.ZWEIMAL)
        zweite = treffer_finden("Gekündigt wurde am 04.05.2026.", self.ZWEIMAL)
        self.assertIn("3.940,00 EUR", erste.zitat)
        self.assertIn("04.05.2026", zweite.zitat)
        self.assertNotEqual(erste.start, zweite.start)


class DerWegDafuerInDerOberflaeche(unittest.TestCase):
    """Deshalb fragt jeder Klick für seinen eigenen Satz nach."""

    def setUp(self) -> None:
        from tests.hilfen import client, dienste

        self.c = client(dienste())
        self.sid = self.c.post("/api/sitzungen", json={"akte_id": "AR-2026-0115"}).json()["sitzung"]["id"]
        self.c.post(f"/api/sitzungen/{self.sid}/dokumente", json={"dokument_ids": ["D-201"]})

    def test_derselbe_beleg_liefert_je_aussage_eine_andere_stelle(self):
        stellen = []
        for aussage in ("Das Bruttomonatsgehalt beträgt 3.940,00 EUR.",
                        "Gekündigt wurde zum 30.09.2026."):
            antwort = self.c.post(f"/api/sitzungen/{self.sid}/fundstelle",
                                  json={"kennung": "D1-S1-P1", "aussage": aussage})
            self.assertEqual(antwort.status_code, 200, antwort.text)
            stellen.append(antwort.json())
        self.assertIn("3.940,00", stellen[0]["zitat"])
        self.assertIn("30.09.2026", stellen[1]["zitat"])
        self.assertNotEqual(stellen[0]["treffer_start"], stellen[1]["treffer_start"])

    def test_ohne_passende_stelle_kommt_ein_leerer_treffer(self):
        antwort = self.c.post(f"/api/sitzungen/{self.sid}/fundstelle",
                              json={"kennung": "D1-S1-P1", "aussage": "Zum Wetter sagt die Akte nichts."})
        self.assertIsNone(antwort.json()["treffer_start"])

    def test_eine_fremde_kennung_wird_abgewiesen(self):
        antwort = self.c.post(f"/api/sitzungen/{self.sid}/fundstelle",
                              json={"kennung": "D9-S9-P9", "aussage": "irgendetwas"})
        self.assertEqual(antwort.status_code, 404)

    def test_eine_fremde_sitzung_bleibt_unsichtbar(self):
        from tests.hilfen import client, dienste

        fremd = client(dienste(), nutzer="refa-lorenz")
        antwort = fremd.post(f"/api/sitzungen/{self.sid}/fundstelle",
                             json={"kennung": "D1-S1-P1", "aussage": "irgendetwas"})
        self.assertEqual(antwort.status_code, 404)


# ── Scanfehler: der Beleg muss auch dann hinspringen ────────────────────────
# Aus der Kanzlei, zur Scanakte 31/26 SC: Das Programm berichtigte „l5.03.2026"
# stillschweigend zu „15.03.2026". Zweierlei war daran falsch. Der Leser sah
# nicht, was auf dem Papier steht – und die Markierung fand den berichtigten
# Wert im Originaltext nicht wieder, sprang also nicht hin. Ausgerechnet bei
# einer Scanakte, wo das Nachsehen am nötigsten ist.

_SCAN = (
    "Goettingen, den l5.03.2026\n\n"
    "Sehr geehrte Frau Ostwald,\n\n"
    "hiermit kuendige ich das Mietverhaeltnis ueber die Wohnung 2. OG links, "
    "ordentlich und fristgerecht zum 3O.09.2026."
)


def test_ein_datum_mit_kleinem_L_wird_gefunden():
    treffer = treffer_finden("Die Kündigung datiert vom 15.03.2026.", _SCAN)
    assert treffer is not None, "Der Beleg springt bei einem Scanfehler nicht hin."
    assert "l5.03.2026" in treffer.zitat


def test_ein_datum_mit_grossem_O_wird_gefunden():
    treffer = treffer_finden("Das Mietverhältnis soll zum 30.09.2026 enden.", _SCAN)
    assert treffer is not None
    assert "3O.09.2026" in treffer.zitat


def test_ein_betrag_mit_grossem_O_wird_gefunden():
    passage = ("§ 3  Miete und Nebenkosten\n"
               "Die monatliche Grundmiete betraegt 85O,00 EUR.\n"
               "Die Nebenkostenvorauszahlung betraegt 180,00 EUR.")
    treffer = treffer_finden("Die monatliche Grundmiete beträgt 850,00 EUR.", passage)
    assert treffer is not None
    assert "85O,00" in treffer.zitat


def test_aus_buchstaben_wird_keine_zahl():
    """Die Übersetzung darf nur greifen, wo wirklich eine Zahl gemeint ist."""
    from jusperfect.services.fundstelle import _entziffern

    for wort in ("Bauvorhaben", "OOO", "Ostwald", "SOS", "lIlI"):
        assert _entziffern(wort) is None, f"{wort} wurde zur Zahl gemacht."


def test_ein_sauberes_dokument_verhaelt_sich_wie_bisher():
    passage = ("Goettingen, den 15.03.2026\n\n"
               "hiermit kuendige ich das Mietverhaeltnis fristgerecht zum 30.09.2026.")
    treffer = treffer_finden("Die Kündigung datiert vom 15.03.2026.", passage)
    assert treffer is not None
    assert "15.03.2026" in treffer.zitat
