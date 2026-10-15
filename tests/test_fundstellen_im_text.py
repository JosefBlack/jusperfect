"""Die Fundstellen im Text: ein Schalter im Chat, und aus dem Entwurf heraus.

Aus der Kanzlei am 15.10.2026:

    „Aufgrund der ganzen Quellen und Anlagen im Text ist der Text im Chat
    kaum lesbar. Es wäre daher gut, wenn man das ein- und ausschalten
    könnte. Darüber hinaus gehören die Quellen nicht mehr in den Fließtext
    des Entwurfs, da sind diese entsprechend zu entfernen, da der Entwurf
    ansonsten nicht brauchbar ist."

Zwei verschiedene Dinge, und sie werden hier verschieden behandelt.

**Der Chat** ist der Ort, an dem geprüft wird. Dort bleiben die Marken, aber
sie stehen nicht mehr zwangsläufig mitten im Satz: Ein Schalter in der
Kopfzeile nimmt sie aus dem Text heraus und holt sie zurück. Ausgeblendet ist
die Grundstellung, weil öfter gelesen als nachgeschlagen wird.

**Der Entwurf** ist das Schriftstück, das das Haus verlässt. Dort sind sie
weg – in der Ansicht, auf dem Blatt, in der Word-Datei und in dem Vermerk,
der nach jur|nodes geschrieben wird. Auf dem Blatt und in Word standen sie
schon vorher nicht mehr; in der Ansicht und im Vermerk standen sie noch.

Was sich **nicht** ändert, ist die Belegpflicht. Es strömt nur Geprüftes,
eine Aussage ohne Beleg wird zurückgehalten, und das Fenster „Belege" führt
jede Fundstelle mit Dokument, Seite und Wortlaut. Gespeichert bleibt der
Entwurf mit Marken. Entfernt werden sie erst beim Anzeigen und beim
Schreiben – nie beim Prüfen.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jusperfect.services.entwuerfe import FREIGABE_FASSUNG, freigabevorlage
from jusperfect.services.quellen import ohne_belege
from tests.test_freigabe_umfang import ECHT, _entwurf

WURZEL = Path(__file__).resolve().parents[1]
JS = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")
HTML = (WURZEL / "jusperfect" / "static" / "index.html").read_text(encoding="utf-8")
CSS = (WURZEL / "jusperfect" / "static" / "styles.css").read_text(encoding="utf-8")


def _block(quelle: str, von: str, bis: str) -> str:
    return quelle[quelle.index(von):quelle.index(bis)]


class DerEntwurfTraegtKeineMarkenMehr(unittest.TestCase):
    """Nicht in der Ansicht, nicht in Word, nicht in der Akte."""

    def test_der_vermerk_in_der_akte_traegt_keine_belegmarken(self):
        """Der Vermerk ist das Ergebnis: Er steht danach in der Mandatsakte.

        Bis zum 15.10.2026 ging der Rohtext hinein, also „Sachstand
        [Q: D1-S1-P1]." – mitten im Satz eine Kennung, die außerhalb des
        Programms nichts bedeutet.
        """
        d, c, _sid, entwurf = _entwurf()
        antwort = c.post(f"/api/entwuerfe/{entwurf['id']}/freigabe",
                         json={"bestaetigung": True,
                               "freigabe_pruefsumme": entwurf["freigabe_pruefsumme"]})
        self.assertEqual(antwort.status_code, 200, antwort.text)
        geschrieben = d.adapter.geschriebene_vermerke[0]["text"]
        self.assertNotIn("[Q:", geschrieben)
        self.assertNotIn(ECHT, geschrieben)
        # Und der Satz liest sich, als wäre nie eine Marke darin gestanden:
        # kein Leerzeichen vor dem Punkt.
        self.assertIn("Sachstand.", geschrieben)

    def test_die_kennzeichnung_bleibt_im_vermerk_stehen(self):
        """Entfernt werden die Belege, nicht die Warnung."""
        d, c, _sid, entwurf = _entwurf()
        c.post(f"/api/entwuerfe/{entwurf['id']}/freigabe",
               json={"bestaetigung": True,
                     "freigabe_pruefsumme": entwurf["freigabe_pruefsumme"]})
        geschrieben = d.adapter.geschriebene_vermerke[0]["text"]
        self.assertIn("ENTWURF", geschrieben)
        self.assertIn("anwaltliche Prüfung erforderlich", geschrieben)

    def test_die_freigabevorlage_bezeugt_genau_den_geschriebenen_text(self):
        """Der Sinn der Vorlage (Befund F06): Sie deckt ab, was geschrieben
        wird. Wird ohne Marken geschrieben, muss sie ohne Marken bezeugen –
        sonst signierte sie wieder etwas anderes als das Ergebnis."""
        from jusperfect.domain.models import Entwurf, EntwurfArt

        e = Entwurf(id="x", akte_id="VU-2026-0042", art=EntwurfArt.MANDANT,
                    betreff="B", text=f"Sachstand [Q: {ECHT}].", erstellt_von="u")
        vorlage = freigabevorlage(e)
        self.assertNotIn("[Q:", vorlage)
        self.assertIn("Sachstand.", vorlage)

    def test_die_fassungsnummer_ist_mitgewachsen(self):
        """Eine Prüfsumme von vorher bezeugt eine Ansicht, die es nicht mehr
        gibt. Sie darf nicht mehr passen – dafür ist die Nummer da."""
        self.assertNotEqual(FREIGABE_FASSUNG, "1")

    def test_gespeichert_bleibt_der_entwurf_mit_marken(self):
        """Die Prüfung lebt von ihnen. Entfernt wird beim Anzeigen und beim
        Schreiben, nicht im Speicher – sonst wäre der Weg zum Beleg
        unwiederbringlich fort."""
        _d, c, _sid, entwurf = _entwurf()
        gelesen = c.get(f"/api/entwuerfe/{entwurf['id']}").json()
        self.assertIn(f"[Q: {ECHT}]", gelesen["text"])
        self.assertTrue(any(q["kennung"] == ECHT for q in gelesen["quellen"]))

    def test_die_ansicht_setzt_den_text_ohne_marken(self):
        """Fließtext und Blatt gehen beide über `ohneBelege`."""
        fliess = _block(JS, "function entwurfInhalt(", "function entwurfKnoepfe(")
        self.assertIn("antworttext(block, ohneBelege(text))", fliess)
        self.assertNotIn("antworttext(block, text)", fliess)


class DasChatfensterHatEinenSchalter(unittest.TestCase):
    """Ein- und ausschalten, wie aus der Kanzlei gewünscht."""

    def test_der_knopf_steht_in_der_kopfzeile_des_chats(self):
        kopf = _block(HTML, '<h1 class="chat-titel">', '<div id="chat-suche-zeile"')
        self.assertIn('id="chat-fundstellen"', kopf)
        self.assertIn("Fundstellen", kopf)

    def test_der_knopf_sagt_seinen_stand(self):
        """Ein Schalter, dessen Stand man nicht sieht, ist ein Knopf mit
        Nebenwirkung. Also beides: Beschriftung und `aria-pressed`."""
        self.assertIn('aria-pressed="false"', _block(
            HTML, 'id="chat-fundstellen"', 'id="chat-lupe"'))
        for stand in ('"Fundstellen: an"', '"Fundstellen: aus"'):
            self.assertIn(stand, JS, stand)
        zeichnen = _block(JS, "function fundstellenZeichnen(", "function fundstellenUmschalten(")
        self.assertIn('setAttribute("aria-pressed"', zeichnen)

    def test_die_grundstellung_ist_aus(self):
        """Gelesen wird öfter als nachgeschlagen – und genau das war die
        Beschwerde: „kaum lesbar"."""
        self.assertIn("let fundstellenAn = false;", JS)

    def test_die_wahl_bleibt_in_diesem_rechner_stehen(self):
        """Wer sie einmal eingeschaltet hat, soll sie nicht bei jedem Start
        wieder einschalten müssen."""
        self.assertIn('localStorage.getItem("jusperfect.fundstellen")', JS)
        self.assertIn('localStorage.setItem("jusperfect.fundstellen"', JS)

    def test_ausgeblendet_wird_mit_einer_regel_nicht_mit_einem_eingriff(self):
        """Die Marken bleiben im Text stehen; nur gezeigt werden sie nicht.

        Wer den Inhalt neu schriebe, um eine Kennung zu verstecken, nähme dem
        Bearbeiter die Belege unter der Hand weg – derselbe Grundsatz wie bei
        den Hervorhebungen der Suche.
        """
        self.assertRegex(CSS, r"\.thread\.ohne-fundstellen \.belegstelle \{ display: none; \}")
        umschalten = _block(JS, "function fundstellenUmschalten(", "/** Der Text eines Beitrags")
        for eingriff in ("replaceChildren", "innerHTML", "remove()", "api("):
            self.assertNotIn(eingriff, umschalten, eingriff)

    def test_der_schalter_greift_nur_im_verlauf(self):
        """Das Fenster „Belege" führt jede Fundstelle weiter – immer. Es ist
        der Weg zum Beleg und darf nicht abschaltbar sein."""
        zeichnen = _block(JS, "function fundstellenZeichnen(", "function fundstellenUmschalten(")
        self.assertIn('$("thread")', zeichnen)
        self.assertNotIn("belege", zeichnen)
        # Die Regel hängt am Verlauf, nicht an `.beleg` überhaupt.
        self.assertNotRegex(CSS, r"^\.belegstelle \{ display: none")

    def test_jede_fundstelle_steht_in_einer_eigenen_gruppe(self):
        """Nur so lässt sie sich als Ganzes ausblenden – samt der Trennzeichen
        zwischen zwei Kennungen."""
        block = _block(JS, "function textMitBelegen(", "function fusszeile(")
        self.assertIn('gruppe.className = "belegstelle"', block)
        self.assertIn("gruppe.appendChild(chip)", block)
        self.assertIn("ziel.appendChild(gruppe)", block)

    def test_das_leerzeichen_vor_der_fundstelle_gehoert_zur_fundstelle(self):
        """Sonst bliebe „… geschlossen ." stehen – mit einer Lücke vor dem
        Punkt. Dieselbe Regel, die `ohneBelege` von Hand anwendet."""
        block = _block(JS, "function textMitBelegen(", "function fusszeile(")
        self.assertIn("vorlauf", block)
        self.assertIn("gruppe.appendChild(document.createTextNode(vorlauf))", block)

    def test_die_suche_zaehlt_nur_was_zu_sehen_ist(self):
        """Ein Treffer in einer ausgeblendeten Kennung wäre ein Treffer, den
        man nicht findet: Der Beitrag stünde da, die Farbe nirgends."""
        umschalten = _block(JS, "function fundstellenUmschalten(", "/** Der Text eines Beitrags")
        self.assertIn("chatSuchen()", umschalten)
        marken = _block(JS, "function markenSetzen(", "/** Den Verlauf auf die Beitraege")
        self.assertIn('closest(".belegstelle")', marken)
        self.assertIn("!fundstellenAn", marken)
        suchen = _block(JS, "function chatSuchen(", "/** Die Suchzeile auf- oder zuklappen")
        self.assertIn("sichtbarerText(el)", suchen)

    def test_der_sichtbare_text_wird_an_einem_klon_gemessen(self):
        """Gemessen, nicht verändert: Der Verlauf auf dem Bildschirm bleibt,
        wie er ist."""
        block = _block(JS, "function sichtbarerText(", "/** Die Suchwoerter aus dem Chatfeld")
        self.assertIn("cloneNode(true)", block)

    def test_der_knopf_ist_verdrahtet_und_wird_beim_start_gezeichnet(self):
        self.assertIn('$("chat-fundstellen")', JS)
        self.assertIn('addEventListener("click", fundstellenUmschalten)', JS)
        self.assertIn("fundstellenZeichnen();", JS)


FAELLE = [
    "Sachstand [Q: D1-S1-P1].",
    "Die Frist läuft [Q: D1-S1-P1] und endet am 30.10.2026 [Q: D2-S1-P1].",
    "Mehrere Belege [Q: D1-S1-P1, D2-S2-P3]!",
    "Ohne Marken bleibt alles, wie es ist.",
    "In der Klammer (so steht es dort [Q: D1-S1-P1]) weiter.",
    "Zeile eins [Q: D1-S1-P1]\nZeile zwei [Q: D2-S1-P1]",
    "Ohne Beleg [Q: ohne Beleg] mitten im Satz.",
    "",
]


class BeideFassungenEntfernenGleich(unittest.TestCase):
    """`ohne_belege` gibt es zweimal: in ``services/quellen.py`` für Word und
    den Vermerk, in ``static/app.js`` für Ansicht und Blatt.

    Zwei Fassungen derselben Regel laufen auseinander, sobald eine geändert
    wird – und dann zeigt die Vorschau etwas anderes, als auf dem Papier
    steht. Genau das soll eine Vorschau nicht.
    """

    def test_wortgleich(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node ist auf diesem Rechner nicht vorhanden; "
                          "die Fassung aus der Oberflaeche laesst sich nicht ausfuehren.")
        anfang = JS.index("function ohneBelege(")
        ende = JS.index("// ── Aus der Modellsprache wird ein Brief")
        programm = JS[anfang:ende] + (
            "\nconst faelle = " + json.dumps(FAELLE, ensure_ascii=False) + ";\n"
            "console.log(JSON.stringify(faelle.map(ohneBelege)));\n")
        with TemporaryDirectory() as ordner:
            datei = Path(ordner) / "probe.js"
            datei.write_text(programm, encoding="utf-8")
            lauf = subprocess.run([node, str(datei)], capture_output=True, text=True, timeout=60)
        self.assertEqual(lauf.returncode, 0, lauf.stderr)
        aus_der_oberflaeche = json.loads(lauf.stdout)
        for roh, dort in zip(FAELLE, aus_der_oberflaeche):
            with self.subTest(text=roh):
                self.assertEqual(ohne_belege(roh), dort)

    def test_und_es_bleibt_keine_marke_stehen(self):
        for roh in FAELLE:
            with self.subTest(text=roh):
                sauber = ohne_belege(roh)
                self.assertNotIn("[Q:", sauber)
                self.assertNotRegex(sauber, r"\s[.,;:!?)]")


if __name__ == "__main__":
    unittest.main()
