"""Der Weg zurück zur Aktenliste.

Aus der Kanzlei: „ich habe irgendeine akte ausgewählt und es gibt anscheinend
keinen button wo man die akte auf der website ändern kann oder?"

Stimmte. Der einzige Rückweg hieß „Sitzung schließen" und steckte im Menü
„Mehr ▾" – ein Name, der nach Aufräumen klingt, nicht nach Zurück. Wer eine
Akte geöffnet hatte, saß darin fest.

Gewechselt wird über dasselbe Schließen, nicht daran vorbei: Die Texte der
einen Akte dürfen nicht in der nächsten stehenbleiben.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
STATIC = WURZEL / "jusperfect" / "static"
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
CSS = (STATIC / "styles.css").read_text(encoding="utf-8")
JS = (STATIC / "app.js").read_text(encoding="utf-8")


class DerKnopf(unittest.TestCase):
    def test_er_steht_im_kopf_neben_dem_aktenzeichen(self):
        """Dort, wo man liest, in welcher Akte man ist – nicht in einem Menü."""
        leiste = re.search(r'<div class="kopf-mitte" id="akte-leiste" hidden>(.*?)</div>',
                           HTML, re.S)
        self.assertIsNotNone(leiste, "Die Aktenleiste im Kopf fehlt.")
        self.assertIn('id="akte-wechseln"', leiste.group(1))
        self.assertIn('id="akte-name"', leiste.group(1))

    def test_er_sagt_wohin(self):
        self.assertRegex(HTML, r'id="akte-wechseln"[^>]*>.*?Akte wechseln')

    def test_er_haengt_an_der_handlung(self):
        self.assertIn('$("akte-wechseln").addEventListener("click"', JS)
        self.assertIn("akteWechseln", JS)


class WasErTut(unittest.TestCase):
    def test_er_schliesst_die_sitzung_statt_sie_zu_umgehen(self):
        """Sonst blieben Texte der einen Akte in der nächsten stehen."""
        block = re.search(r"async function akteWechseln\(\) \{(.*?)\n\}", JS, re.S)
        self.assertIsNotNone(block)
        self.assertIn("await sitzungSchliessen()", block.group(1))

    def test_er_fragt_vorher_wenn_ein_gespraech_da_ist(self):
        """Der Wechsel kostet das begonnene Gespräch – das darf nicht überraschen."""
        block = re.search(r"async function akteWechseln\(\) \{(.*?)\n\}", JS, re.S)
        inhalt = block.group(1)
        self.assertIn('querySelector(".karte-c")', inhalt)
        self.assertIn("confirm(", inhalt)
        # Und die Frage muss sagen, was bleibt, nicht nur was weg ist. Der Text
        # steht seit dem Speichern beim Schliessen in schlussfrage() - mit den
        # Zahlen des Gedaechtnisses statt einer blossen Zusage.
        self.assertIn("schlussfrage()", inhalt)
        frage = re.search(r"function schlussfrage\(\) \{(.*?)\n\}", JS, re.S).group(1)
        self.assertIn("Aktengedächtnis", frage)
        self.assertIn("Entwürfe", frage)


class DasSchliessen(unittest.TestCase):
    """Aus der Kanzlei: „das mit der sitzung schließen muss deutlicher
    erkennbar sein für den nutzer"."""

    def test_es_steht_nicht_mehr_im_menue(self):
        menue = re.search(r'<div id="mehr-menue".*?</div>', HTML, re.S).group(0)
        self.assertNotIn("sitzung-schliessen", menue)

    def test_es_steht_im_kopf_neben_dem_anderen_weg_hinaus(self):
        """Sichtbar bleibt sichtbar – die Stelle ist nur die richtigere geworden.

        Zuerst kam es aus dem Menü „Mehr" in die Reihe der Arbeitsknöpfe: Analyse,
        Entwurf, Dokumente, Sitzung schließen. Damit war es erkennbar, stand aber
        zwischen Handlungen, während es die Arbeit beendet – ein Knopf, der etwas
        löscht, neben einem, der etwas erstellt. Jetzt steht es oben neben
        „Akte wechseln", wo der Weg hinaus ohnehin ist.
        """
        leiste = re.search(r'<div class="kopf-mitte" id="akte-leiste" hidden>(.*?)\n  </div>',
                           HTML, re.S)
        self.assertIsNotNone(leiste, "Die Aktenleiste im Kopf fehlt.")
        self.assertIn('id="sitzung-schliessen"', leiste.group(1))

    def test_es_steht_nicht_zwischen_den_arbeitsknoepfen(self):
        aktionen = re.search(r'<div class="aktionen">(.*?)<div class="mehr">', HTML, re.S)
        self.assertIsNotNone(aktionen)
        self.assertNotIn('id="sitzung-schliessen"', aktionen.group(1))

    def test_der_titel_sagt_was_geloescht_wird_und_was_bleibt(self):
        knopf = re.search(r'<button id="sitzung-schliessen".*?>', HTML, re.S).group(0)
        self.assertIn("löscht die temporären Texte", knopf)
        self.assertIn("Aktengedächtnis bleibt", knopf)

    def test_es_geht_ueber_dieselbe_rueckfrage_wie_der_wechsel(self):
        """Ein prominenter Knopf wird auch versehentlich getroffen."""
        self.assertIn('$("sitzung-schliessen").addEventListener("click", (ev) => mitKnopf(ev.target, akteWechseln))', JS)


class DieLeiste(unittest.TestCase):
    def test_der_name_schrumpft_der_knopf_nicht(self):
        """Sonst frisst eine lange Bezeichnung den einzigen Weg zurück auf."""
        mitte = re.search(r"\.kopf-mitte \{([^}]*)\}", CSS)
        self.assertIsNotNone(mitte)
        self.assertIn("display: flex", mitte.group(1))

        name = re.search(r"\.akte-name \{([^}]*)\}", CSS)
        self.assertIsNotNone(name, "Regel für .akte-name fehlt.")
        self.assertIn("text-overflow: ellipsis", name.group(1))
        self.assertIn("min-width: 0", name.group(1))

        knopf = re.search(r"\.akte-wechseln \{([^}]*)\}", CSS)
        self.assertIsNotNone(knopf, "Regel für .akte-wechseln fehlt.")
        self.assertIn("flex: none", knopf.group(1))

    def test_die_alte_regel_zeigt_nicht_mehr_auf_die_leiste(self):
        """.kopf-mitte b hätte den Aktenzeichen-Fettdruck ins Leere laufen lassen."""
        self.assertNotIn(".kopf-mitte b", CSS)
        self.assertIn(".akte-name b", CSS)


if __name__ == "__main__":
    unittest.main()


class FehlerOhneKnopf(unittest.TestCase):
    """Ein Fehler, der keinen Fehler zeigt, ist der teuerste.

    Aus der Kanzlei: „bei der großen akte öffnet er nicht die arbeitsfläche".
    ``mitKnopf`` begann mit ``if (!knopf) return arbeit();`` – ohne try/catch.
    Vier Aufrufer übergeben keinen Knopf, darunter das Übernehmen im Explorer
    und das Öffnen einer Akte aus der Liste. Schlug einer davon fehl, war der
    Dialog zu, die Arbeitsfläche blieb weg, und der Grund landete als
    unbehandelte Promise-Ablehnung in der Browserkonsole.
    """

    def test_auch_ohne_knopf_wird_gemeldet(self):
        block = re.search(r"async function mitKnopf\(knopf, arbeit\) \{(.*?)\n\}", JS, re.S)
        self.assertIsNotNone(block)
        # Ohne die Kommentarzeilen - dort steht der alte Code als Erklaerung.
        inhalt = "\n".join(z for z in block.group(1).splitlines()
                           if not z.strip().startswith("//"))
        self.assertNotIn("if (!knopf) return arbeit();", inhalt)
        self.assertIn("if (knopf) knopf.disabled = true;", inhalt)
        self.assertIn("catch", inhalt)
        self.assertIn("melden(e.message, true)", inhalt)

    def test_langes_lesen_wird_angezeigt(self):
        """Fünfzig Dokumente dauern; ohne Anzeige wirkt der Klick verpufft.

        Seit dem 02.10.2026 ist es mehr als eine Meldung: Die Oberfläche liest
        in Portionen und zeigt gezählte Dokumente. Aus der Kanzlei: „55
        Dokumente werden gelesen ... Dauert sehr lange."
        """
        self.assertIn("function laeuft(", JS)
        block = re.search(r"async function explorerUebernehmen\(\) \{(.*?)\n\}", JS, re.S)
        self.assertIn("dokumenteInPortionenLesen(dazu)", block.group(1))
        lesen = re.search(r"async function dokumenteInPortionenLesen\(dazu\) \{(.*?)\n\}",
                          JS, re.S).group(1)
        # Beides: die kurze Meldung fuer ein, zwei Dokumente - und der Balken,
        # sobald es sich lohnt.
        self.assertIn("laeuft(", lesen)
        self.assertIn("lesefortschritt(", lesen)

    def test_die_laufende_meldung_laeuft_nicht_ab(self):
        """Sonst verschwände sie, während der Vorgang noch läuft – eine Lüge."""
        block = re.search(r"function laeuft\(text\) \{(.*?)\n\}", JS, re.S)
        self.assertIn("clearTimeout", block.group(1))
        self.assertNotIn("setTimeout", block.group(1))
