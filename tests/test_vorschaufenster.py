"""Der Entwurf entsteht im Vorschaufenster und ändert sich über den Chat.

Aus der Kanzlei am 13.10.2026:

    „Hier wäre dann ein Vorschaufenster sehr schön, in welchem der Entwurf
    nach und nach entsteht und durch den Chat geändert werden kann."

Beides steht hier, und beides hat eine Stelle, an der es gefährlich würde:

1. **Nach und nach** heißt strömen - und es strömt **nur Geprüftes**
   (Befund F05 der Zweitprüfung, 05.10.2026). Bis zur ersten abgeschlossenen,
   belegten Aussage steht nur da, DASS gearbeitet wird. Ein Text, der erst
   dasteht und dann verschwindet, ist gezeigt worden.
2. **Durch den Chat geändert** heißt: Das Modell schreibt den Entwurf neu.
   Die vorige Fassung bliebe sonst nirgends, und eine Änderung, die den
   Entwurf verschlechtert, wäre nicht zurückzunehmen.

Dazu kommt das Stille, das am teuersten wäre: Wer eine Frage tippt und damit
versehentlich seinen Entwurf umschreibt, hat den Entwurf verloren, den er
gerade richtig bekommen hatte. Der Umschalter ist deshalb sichtbar.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from jusperfect.providers.base import Nutzung, ProviderAntwort
from jusperfect.services.entwuerfe import teiltext

from tests.hilfen import client, dienste

WURZEL = Path(__file__).resolve().parent.parent
AKTE = "VU-2026-0042"

#: Zwei belegte Sätze - damit der Entwurf die Belegpflicht besteht und
#: zwischendurch überhaupt etwas Prüfbares dasteht.
ERSTE = "Der Sachstand ist festgehalten [Q: D1-S1-P1]."
ZWEITE = "Die Unterlagen liegen vor [Q: D1-S1-P1]."


class StromProvider:
    """Gibt die Antwort in Stücken heraus - wie ein echter Anbieter."""

    modell_id = "skript"

    def __init__(self, antworten: list[str], stueckgroesse: int = 24) -> None:
        self._antworten = list(antworten)
        self._stueck = stueckgroesse
        self.aufgaben: list[str] = []

    def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        self.aufgaben.append(aufgabe)
        text = self._antworten.pop(0) if self._antworten else "Leer"
        return ProviderAntwort(text=text, nutzung=Nutzung(1000, 200),
                               modell=modell_id or self.modell_id)

    def fragen_stream(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        self.aufgaben.append(aufgabe)
        text = self._antworten.pop(0) if self._antworten else "Leer"
        for stelle in range(0, len(text), self._stueck):
            yield text[stelle:stelle + self._stueck]
        yield ProviderAntwort(text=text, nutzung=Nutzung(1000, 200),
                              modell=modell_id or self.modell_id)


def _sitzung(provider):
    d = dienste(provider=provider)
    c = client(d)
    sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
    c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
    return d, c, sid


def _ereignisse(antwort) -> list[dict]:
    return [json.loads(z) for z in antwort.text.splitlines() if z.strip()]


class TeiltextAusHalbemJson(unittest.TestCase):
    """Der Entwurf steckt in einem JSON-Objekt, das erst am Ende schließt.

    ``json.loads`` kann damit nichts anfangen. Gelesen wird deshalb nur
    dieses eine Feld - und nur bis zu der Stelle, an der es sicher
    vollständig ist.
    """

    def test_der_anfang_wird_gelesen(self):
        self.assertEqual(teiltext('{"betreff": "X", "text": "Sehr geehrte'),
                         "Sehr geehrte")

    def test_vor_dem_textfeld_steht_nichts_da(self):
        self.assertEqual(teiltext('{"betreff": "Ein Betreff"'), "")

    def test_ein_halbes_fluchtzeichen_wartet_auf_den_rest(self):
        """``json.loads('"...\\\\u00e"')`` wirft - und ein Fehler mitten im
        Strom sähe aus, als sei der Entwurf gescheitert."""
        self.assertEqual(teiltext('{"text": "Gr\\u00f'), "Gr")
        self.assertEqual(teiltext('{"text": "Gr\\'), "Gr")

    def test_ein_ganzes_fluchtzeichen_kommt_mit(self):
        self.assertEqual(teiltext('{"text": "Gr\\u00fc\\u00dfe'), "Grüße")
        self.assertEqual(teiltext('{"text": "Zeile\\nZwei'), "Zeile\nZwei")

    def test_anfuehrungszeichen_im_text(self):
        self.assertEqual(teiltext('{"text": "ein \\"Zitat\\" darin'),
                         'ein "Zitat" darin')

    def test_das_ende_des_feldes_wird_erkannt(self):
        self.assertEqual(teiltext('{"text": "fertig", "betreff": "X"}'), "fertig")

    def test_unbrauchbares_gibt_leer_und_wirft_nicht(self):
        """Was hier ankommt, ist die Ausgabe eines Modells, also alles."""
        for roh in ("", "{", "kein json", '{"text": '):
            with self.subTest(roh=roh):
                self.assertEqual(teiltext(roh), "")


class DerEntwurfEntstehtStueckweise(unittest.TestCase):
    def setUp(self):
        self.p = StromProvider([json.dumps({"betreff": "Egal", "text": f"{ERSTE} {ZWEITE}"})])
        self.d, self.c, self.sid = _sitzung(self.p)

    def test_der_strom_endet_mit_dem_fertigen_entwurf(self):
        antwort = self.c.post(f"/api/sitzungen/{self.sid}/entwuerfe/stream",
                              json={"art": "rsv", "anweisung": "Deckung anfragen"})
        self.assertEqual(antwort.status_code, 200, antwort.text)
        ereignisse = _ereignisse(antwort)
        self.assertEqual(ereignisse[-1]["type"], "fertig", ereignisse[-1])
        entwurf = ereignisse[-1]["entwurf"]
        self.assertIn("Der Sachstand ist festgehalten", entwurf["text"])
        self.assertEqual(entwurf["fassung"], 1)

    def test_zwischendurch_kommt_gepruefter_text(self):
        """„Nach und nach" - sonst wäre es keine Vorschau, sondern Warten."""
        ereignisse = _ereignisse(self.c.post(f"/api/sitzungen/{self.sid}/entwuerfe/stream",
                                             json={"art": "rsv", "anweisung": "x"}))
        geprueft = [e for e in ereignisse if e["type"] == "geprueft"]
        self.assertTrue(geprueft, [e["type"] for e in ereignisse])
        self.assertIn("Der Sachstand ist festgehalten", geprueft[0]["text"])

    def test_der_fortschritt_nennt_nur_die_zeichenzahl(self):
        """Dass gearbeitet wird, nicht was dasteht (Befund F05)."""
        for e in _ereignisse(self.c.post(f"/api/sitzungen/{self.sid}/entwuerfe/stream",
                                         json={"art": "rsv", "anweisung": "x"})):
            if e["type"] == "fortschritt":
                self.assertEqual(sorted(e), ["type", "zeichen"], e)
                self.assertIsInstance(e["zeichen"], int)

    def test_ungepruefter_rohtext_geht_nie_hinaus(self):
        """Die Zusage lautet „entfernen, nicht zeigen"."""
        p = StromProvider([json.dumps(
            {"betreff": "Egal",
             "text": f"{ERSTE} Die Gegenseite hat alles anerkannt [Q: D9-S9-P9]."})])
        d, c, sid = _sitzung(p)
        antwort = c.post(f"/api/sitzungen/{sid}/entwuerfe/stream",
                         json={"art": "rsv", "anweisung": "x"})
        self.assertNotIn("alles anerkannt", antwort.text)


class DerChatAendertDenEntwurf(unittest.TestCase):
    def setUp(self):
        self.p = StromProvider([
            json.dumps({"betreff": "Egal", "text": ERSTE}),
            json.dumps({"betreff": "Egal", "text": f"{ERSTE} {ZWEITE}"}),
        ])
        self.d, self.c, self.sid = _sitzung(self.p)
        self.e = self.c.post(f"/api/sitzungen/{self.sid}/entwuerfe",
                             json={"art": "rsv", "anweisung": "Deckung anfragen"}).json()

    def _aendern(self, anweisung="Bitte einen Satz zu den Unterlagen ergänzen."):
        return self.c.post(
            f"/api/sitzungen/{self.sid}/entwuerfe/{self.e['id']}/aendern/stream",
            json={"anweisung": anweisung})

    def test_die_aenderung_ergibt_eine_neue_fassung(self):
        ereignisse = _ereignisse(self._aendern())
        self.assertEqual(ereignisse[-1]["type"], "fertig", ereignisse[-1])
        neu = ereignisse[-1]["entwurf"]
        self.assertEqual(neu["fassung"], 2)
        self.assertIn("Die Unterlagen liegen vor", neu["text"])

    def test_die_vorige_fassung_bleibt_erhalten(self):
        """Ohne sie wäre jede Änderung über den Chat endgültig."""
        neu = _ereignisse(self._aendern())[-1]["entwurf"]
        self.assertEqual(len(neu["vorfassungen"]), 1)
        vorher = neu["vorfassungen"][0]
        self.assertEqual(vorher["nummer"], 1)
        self.assertIn("Der Sachstand ist festgehalten", vorher["text"])

    def test_die_anweisung_steht_bei_der_abgeloesten_fassung(self):
        """Sonst steht am Ende eine Fassung da, von der niemand mehr weiß,
        warum sie so aussieht."""
        neu = _ereignisse(self._aendern("Kürzer fassen."))[-1]["entwurf"]
        self.assertEqual(neu["vorfassungen"][0]["anweisung"], "Kürzer fassen.")

    def test_der_bisherige_entwurf_geht_mit_in_den_aufruf(self):
        """Sonst schriebe das Modell ein neues Schreiben statt einer Änderung."""
        self._aendern()
        aufgabe = self.p.aufgaben[-1]
        self.assertIn("ENTWURF ÜBERARBEITEN", aufgabe)
        self.assertIn("Der Sachstand ist festgehalten", aufgabe)

    def test_der_aufruf_verlangt_die_belege_zurueck(self):
        """Ohne diesen Hinweis kommt eine glatte Fassung ohne [Q: …] zurück,
        und die Belegpflicht hält sie vollständig zurück - das sähe aus, als
        habe die Änderung das Schreiben gelöscht."""
        self._aendern()
        self.assertIn("[Q: ...]", self.p.aufgaben[-1])

    def test_eine_leere_anweisung_aendert_nichts(self):
        ereignisse = _ereignisse(self._aendern("   "))
        self.assertEqual(ereignisse[-1]["type"], "fehler", ereignisse)

    def test_ein_entwurf_aus_einer_anderen_akte_wird_abgewiesen(self):
        """Sonst würde er an den Dokumenten einer fremden Akte belegt."""
        andere = self.c.post("/api/sitzungen", json={"akte_id": "AR-2026-0115"}).json()["sitzung"]["id"]
        antwort = self.c.post(
            f"/api/sitzungen/{andere}/entwuerfe/{self.e['id']}/aendern/stream",
            json={"anweisung": "egal"})
        self.assertEqual(antwort.status_code, 404, antwort.text)

    def test_zuruecknehmen_holt_die_vorige_fassung(self):
        self._aendern()
        zurueck = self.c.post(f"/api/entwuerfe/{self.e['id']}/zuruecknehmen")
        self.assertEqual(zurueck.status_code, 200, zurueck.text)
        self.assertEqual(zurueck.json()["fassung"], 1)
        self.assertNotIn("Die Unterlagen liegen vor", zurueck.json()["text"])
        self.assertEqual(zurueck.json()["vorfassungen"], [])

    def test_ohne_vorfassung_gibt_es_nichts_zurueckzunehmen(self):
        antwort = self.c.post(f"/api/entwuerfe/{self.e['id']}/zuruecknehmen")
        self.assertEqual(antwort.status_code, 422, antwort.text)

    def test_die_quellen_passen_nach_dem_zuruecknehmen_zum_text(self):
        """Sonst stünden Belege darunter, die im Text nicht mehr vorkommen."""
        self._aendern()
        zurueck = self.c.post(f"/api/entwuerfe/{self.e['id']}/zuruecknehmen").json()
        for quelle in zurueck["quellen"]:
            with self.subTest(kennung=quelle["kennung"]):
                self.assertIn(quelle["kennung"], zurueck["text"])

    def test_die_freigabepruefsumme_passt_zur_neuen_fassung(self):
        """Die alte Prüfsumme bezeugt eine Ansicht, die es nicht mehr gibt."""
        alt = self.e["freigabe_pruefsumme"]
        neu = _ereignisse(self._aendern())[-1]["entwurf"]
        self.assertNotEqual(neu["freigabe_pruefsumme"], alt)
        abgewiesen = self.c.post(f"/api/entwuerfe/{self.e['id']}/freigabe",
                                 json={"bestaetigung": True, "freigabe_pruefsumme": alt})
        self.assertEqual(abgewiesen.status_code, 422, abgewiesen.text)
        self.assertIn("stimmt nicht mehr", abgewiesen.json()["fehler"])


class DieBelegpflichtGiltAuchBeimAendern(unittest.TestCase):
    def test_eine_fassung_ohne_beleg_wird_nicht_ausgegeben(self):
        p = StromProvider([
            json.dumps({"betreff": "Egal", "text": ERSTE}),
            json.dumps({"betreff": "Egal", "text": "Alles bestens, ganz ohne Beleg."}),
        ])
        d, c, sid = _sitzung(p)
        e = c.post(f"/api/sitzungen/{sid}/entwuerfe",
                   json={"art": "rsv", "anweisung": "x"}).json()
        ereignisse = _ereignisse(c.post(
            f"/api/sitzungen/{sid}/entwuerfe/{e['id']}/aendern/stream",
            json={"anweisung": "Freier formulieren."}))
        self.assertEqual(ereignisse[-1]["type"], "fehler", ereignisse)
        self.assertIn("Beleg", ereignisse[-1]["detail"])

    def test_die_alte_fassung_steht_danach_unveraendert_da(self):
        """Eine gescheiterte Änderung darf den Entwurf nicht kosten."""
        p = StromProvider([
            json.dumps({"betreff": "Egal", "text": ERSTE}),
            json.dumps({"betreff": "Egal", "text": "Alles bestens, ganz ohne Beleg."}),
        ])
        d, c, sid = _sitzung(p)
        e = c.post(f"/api/sitzungen/{sid}/entwuerfe",
                   json={"art": "rsv", "anweisung": "x"}).json()
        c.post(f"/api/sitzungen/{sid}/entwuerfe/{e['id']}/aendern/stream",
               json={"anweisung": "Freier formulieren."})
        danach = c.get(f"/api/entwuerfe/{e['id']}").json()
        self.assertEqual(danach["fassung"], 1)
        self.assertEqual(danach["text"], e["text"])


class DieOberflaecheZeigtDasFenster(unittest.TestCase):
    HTML = (WURZEL / "jusperfect" / "static" / "index.html").read_text(encoding="utf-8")
    JS = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")

    def test_es_gibt_ein_vorschaufenster_in_der_rechten_spalte(self):
        self.assertIn('id="fenster-entwurf"', self.HTML)
        self.assertGreater(self.HTML.index('id="fenster-entwurf"'),
                           self.HTML.index('id="spalte-rechts"'))

    def test_es_hat_einen_knopf_in_der_leiste_die_stehen_bleibt(self):
        anfang = self.HTML.index('<div class="rechts-aktionen">')
        block = self.HTML[anfang:self.HTML.index("<section", anfang)]
        self.assertIn('data-fenster="entwurf"', block)

    def test_es_laesst_sich_auf_den_zweiten_bildschirm_holen(self):
        """Aus der Kanzlei: „so dass der Chat viel Platz hat."""
        self.assertIn('data-fenster-los="entwurf"', self.HTML)
        self.assertIn('entwurf: "fenster-entwurf"', self.JS)
        self.assertIn('nebenfenster === "entwurf"', self.JS)

    def test_es_faengt_zu_an(self):
        """Es hat erst etwas zu zeigen, wenn ein Entwurf entsteht."""
        self.assertRegex(self.JS, r"let fensterStand = \{[^}]*entwurf: false")

    def test_der_umschalter_steht_sichtbar_ueber_dem_eingabefeld(self):
        """Ein Modus, den man nicht sieht, ist der teuerste von allen."""
        self.assertIn('id="entwurf-modus"', self.HTML)
        self.assertLess(self.HTML.index('id="entwurf-modus"'),
                        self.HTML.index('id="frage-form"'))
        self.assertIn('id="entwurf-modus-aus"', self.HTML)

    def test_auch_der_knopf_sagt_was_er_tut(self):
        """Er stand auf „Fragen", während darüber stand, dass hier nicht
        gefragt wird - und der Knopf ist das Letzte, was man vor dem
        Abschicken ansieht."""
        block = self.JS[self.JS.index("function entwurfModusZeigen"):
                        self.JS.index("function entwurfFensterZeichnen")]
        self.assertIn('senden.textContent = "Ändern"', block)
        self.assertIn('senden.textContent = "Fragen"', block)

    def test_das_fenster_heisst_nicht_wie_der_knopf_daneben(self):
        """Zwei Knöpfe „Entwurf" nebeneinander - einer macht einen, einer
        zeigt ihn. Im Bild war nicht zu sehen, welcher welcher ist."""
        beschriftungen = re.findall(
            r'data-(?:aktion|fenster)="entwurf"[^>]*>([^<]+)</button>', self.HTML)
        self.assertEqual(len(beschriftungen), 2, beschriftungen)
        self.assertEqual(len(set(beschriftungen)), 2, beschriftungen)

    def test_der_chat_aendert_nur_mit_eingeschaltetem_umschalter(self):
        block = self.JS[self.JS.index("async function frageStellen"):]
        block = block[:block.index("\n}")]
        self.assertIn("if (entwurfAendernAn && entwurfStand) return entwurfAendern(frage);", block)

    def test_das_nebenfenster_hat_keine_knoepfe(self):
        """Es ist ein Spiegel, keine zweite Arbeitsfläche: In einer
        Mandatsakte muss klar sein, WO gearbeitet wird."""
        block = self.JS[self.JS.index("function entwurfFensterZeichnen"):
                        self.JS.index("function entwurfKnoepfe")]
        self.assertIn("if (!nebenfenster) ziel.appendChild(entwurfKnoepfe(e));", block)

    def test_der_entwurf_verschwindet_mit_der_akte(self):
        """Sonst stünde beim nächsten Öffnen ein Entwurf im Fenster, der zu
        einer anderen Akte gehört."""
        self.assertRegex(self.JS, r"entwurfStand = null; entwurfLaeuft = \"\";")

    def test_das_fenster_sagt_dass_es_nur_geprueftes_zeigt(self):
        block = self.JS[self.JS.index("function entwurfFensterZeichnen"):
                        self.JS.index("function entwurfKnoepfe")]
        self.assertIn("nur, was schon geprüft ist", block)

    def test_die_spalte_bleibt_offen_wenn_nur_die_vorschau_offen_ist(self):
        """Wer alles andere zuklappt und nur die Vorschau offenlässt, bekam
        eine Spalte in „nur-leiste" - und die blendet ihre Fenster aus. Der
        Entwurf war unsichtbar, obwohl sein Knopf gedrückt war."""
        block = self.JS[self.JS.index("function fensterAnwenden"):]
        treffer = re.search(r'const offen = \[([^\]]*)\]', block)
        self.assertIsNotNone(treffer, block[:400])
        namen = set(re.findall(r'"([a-z]+)"', treffer.group(1)))
        self.assertEqual(namen, {"chronologie", "gedaechtnis", "entwurf", "belege"})

    def test_es_gibt_die_wahl_zwischen_text_und_blatt(self):
        """Aus der Kanzlei: „Kann der Entwurf nicht gleich das fertige
        Schreiben mit Briefkopf angeben?" - beides hat seinen Zweck: Der
        Fließtext ist zum Lesen und Ändern da, das Blatt zum Abschätzen."""
        block = self.JS[self.JS.index("function entwurfAnsichtWahl"):
                        self.JS.index("function entwurfInhalt")]
        self.assertIn('"text", "Text"', block)
        self.assertIn('"blatt", "Blatt"', block)

    def test_im_entwurf_stehen_nirgends_belegmarken(self):
        """Weder auf dem Blatt noch im Fließtext.

        Bis zum 15.10.2026 blieben sie im Fließtext stehen, weil dort geprüft
        wird. Aus der Kanzlei an diesem Tag: „Die Quellen gehören nicht mehr
        in den Fließtext des Entwurfs, da sind diese entsprechend zu
        entfernen, da der Entwurf ansonsten nicht brauchbar ist."

        Geprüft wird seither über das Fenster „Belege": Dort steht jede
        Fundstelle mit Dokument, Seite und Wortlaut. Gespeichert bleibt der
        Entwurf mit Marken - entfernt werden sie erst beim Anzeigen.
        """
        blatt = self.JS[self.JS.index("function blattBauen"):][:9000]
        self.assertIn("ohneBelege(text)", blatt)
        fliess = self.JS[self.JS.index("function entwurfInhalt"):
                         self.JS.index("function entwurfKnoepfe")]
        self.assertIn("antworttext(block, ohneBelege(text))", fliess)
        self.assertNotIn("antworttext(block, text)", fliess)

    def test_das_blatt_bricht_die_zeilen_wie_die_word_datei(self):
        """`antworttext` setzt zwei Zeilen hintereinander zu einem Absatz
        zusammen, Word macht daraus zwei. Dann sähe die Ansicht anders aus
        als das Blatt - der eine Fehler, den eine Ansicht nicht machen darf."""
        blatt = self.JS[self.JS.index("function blattBauen"):][:9000]
        self.assertNotIn("antworttext(koerper", blatt)
        self.assertIn('.split("\\n")', blatt)

    def test_das_blatt_ist_weiss_und_bleibt_weiss(self):
        """Papier ist weiß. Wer hier die Länge eines Schreibens abschätzt,
        soll dasselbe sehen wie auf dem Papier - auch im dunklen Bild."""
        css = (WURZEL / "jusperfect" / "static" / "styles.css").read_text(encoding="utf-8")
        block = css[css.index(".blatt {"):css.index(".blatt-stueck")]
        self.assertIn("#ffffff", block)

    def test_das_blatt_sagt_dass_word_es_anders_setzen_kann(self):
        """Eine Ansicht, die sich für die Wahrheit ausgibt, ist schlimmer als
        gar keine."""
        block = self.JS[self.JS.index("function entwurfInhalt"):
                        self.JS.index("function entwurfKnoepfe")]
        self.assertIn("Das Blatt baut Word", block)

    def test_das_blatt_wird_auf_die_fensterbreite_gerechnet(self):
        """Ein Blatt, das man nicht ganz sieht, sagt über die Länge nichts
        aus - und die Länge ist der Grund, warum es dasteht."""
        block = self.JS[self.JS.index("function blattBauen"):]
        self.assertIn("ResizeObserver", block[:6000])
        self.assertIn("transform = `scale(", block[:6000])

    def test_der_strom_bleibt_nicht_in_entsteht_stehen(self):
        """Auch wenn es schiefging - sonst wartet das Fenster für immer."""
        block = self.JS[self.JS.index("async function entwurfStromLesen"):
                        self.JS.index("async function entwurfStarten")]
        self.assertIn("finally", block)
        self.assertIn('entwurfLaeuft = "";', block)


if __name__ == "__main__":
    unittest.main()
