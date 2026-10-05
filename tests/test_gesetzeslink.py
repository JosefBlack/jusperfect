"""Der Sprung zum Gesetzeswortlaut - derselbe Weg wie bei Haufe.

Aus der Kanzlei am 25.09.2026, zuerst als Frage: "wenn die KI argumentiert,
kann man dann bei Belegen schnell den Gesetzestext nachlesen und schauen, ob
man das Gesetz so auslegen kann?" Und dann als Weg: "wie hast du Recherche
Haufe eingebunden, genauso wollte ich das auch mit den Gesetzestexten machen."

Also ein Sprung in den Browser, nichts im Programmordner: nichts zu
aktualisieren, nichts, was veraltet, keine Urheberrechtsfrage - und der Stand
ist immer der von heute.

Das Adressmuster wurde am 25.09.2026 von der Kanzlei am lebenden Server
geprueft ("geht auf"), nicht geraten. Es bleibt trotzdem einstellbar.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from jusperfect.config import Einstellungen

WURZEL = Path(__file__).resolve().parent.parent
APP_JS = (WURZEL / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")


def _muster_aus_app_js() -> re.Pattern[str]:
    """Das ECHTE Muster aus app.js, nicht eine Nachbildung.

    Eine Probe, die ein zweites Muster prueft, prueft etwas anderes als den
    Betrieb - dieser Satz hat in diesem Programm an einem Tag fuenfmal
    zugeschlagen. Deshalb wird hier der Quelltext gelesen.

    Grenze: Python und JavaScript schreiben regulaere Ausdruecke nicht
    voellig gleich. Fuer dieses Muster stimmen sie ueberein; kaeme ein
    JavaScript-eigenes Stueck hinein, faellt dieser Test auf die Nase - und
    das ist dann der richtige Zeitpunkt, es zu merken.
    """
    zeile = APP_JS[APP_JS.index("const GESETZESVERWEIS ="):]
    roh = zeile[zeile.index("/") + 1:zeile.index("/g;")]
    return re.compile(roh)


class DasMusterFindetEchteVerweise(unittest.TestCase):

    def setUp(self) -> None:
        self.muster = _muster_aus_app_js()

    def test_paragraf_mit_zusatz_und_kuerzel(self):
        for satz, gesetz, paragraf in (
                ("Der Anspruch folgt aus § 634 Nr. 4 BGB.", "BGB", "634"),
                ("in Verbindung mit § 280 Abs. 1 BGB", "BGB", "280"),
                ("§ 204 Abs. 1 Nr. 1 ZPO", "ZPO", "204"),
                ("Die Frist des § 195 BGB", "BGB", "195"),
                ("Nach § 13b UStG schuldet", "UStG", "13b"),
                ("§§ 823 BGB", "BGB", "823"),
        ):
            with self.subTest(satz=satz):
                treffer = self.muster.search(satz)
                self.assertIsNotNone(treffer, satz)
                self.assertEqual(paragraf, treffer.group(1))
                self.assertEqual(gesetz, treffer.group(3))

    def test_ein_gewoehnliches_wort_ist_kein_gesetz(self):
        """"§ 634 Die Frist" darf nicht als Gesetz gelesen werden.

        Das Muster trifft hier zwar - deshalb verlangt die Oberflaeche
        zusaetzlich zwei Grossbuchstaben im Kuerzel. Lieber ein Verweis
        weniger als einer, der ins Leere fuehrt.
        """
        treffer = self.muster.search("Die Klage ist nach § 634 Die Frist unzulässig.")
        self.assertIsNotNone(treffer)
        self.assertEqual("Die", treffer.group(3))
        self.assertLess(len(re.findall(r"[A-ZÄÖÜ]", treffer.group(3))), 2)

    def test_die_kuerzel_echter_gesetze_haben_zwei_grossbuchstaben(self):
        for kuerzel in ("BGB", "ZPO", "StGB", "UStG", "BauGB", "InsO", "GG", "VVG"):
            with self.subTest(kuerzel=kuerzel):
                self.assertGreaterEqual(len(re.findall(r"[A-ZÄÖÜ]", kuerzel)), 2)


class DieOberflaecheBautDieAdresse(unittest.TestCase):

    def test_die_zwei_grossbuchstaben_werden_wirklich_verlangt(self):
        js = APP_JS[APP_JS.index("function sichtbaresKuerzel("):]
        self.assertIn(">= 2", js[:300])

    def test_ohne_muster_gibt_es_keinen_sprung(self):
        """Dann nur die Startseite - wie bei Haufe ohne Suchparameter.

        Geraten wird nicht. Das ist derselbe Grundsatz, unter dem der
        Haufe-Knopf am 04.09.2026 beim Direktlink geblieben ist.
        """
        js = APP_JS[APP_JS.index("function gesetzesAdresse("):
                    APP_JS.index("function sichtbaresKuerzel(")]
        self.assertIn('if (!cfg.url) return ""', js)
        self.assertIn("if (!cfg.muster) return cfg.url", js)

    def test_der_verweis_kommt_in_die_zwischenablage(self):
        """Fuehrt die Adresse ins Leere, ist die Suche ein Einfuegen entfernt."""
        js = APP_JS[APP_JS.index("function gesetzesKnopf("):]
        self.assertIn("clipboard.writeText", js[:900])

    def test_der_klick_auf_die_nummer_bleibt_der_weg_ins_dokument(self):
        """Ein Klick kann nicht zweierlei tun. Der Sprung steht DANEBEN."""
        js = APP_JS[APP_JS.index("function angabenAnklickbar("):
                    APP_JS.index("function gesetzeAnklickbar(")]
        self.assertIn("passageMarkieren(kennung", js)
        self.assertIn("gesetzesKnopf(", js)

    def test_auch_ohne_fundstelle_gibt_es_den_sprung(self):
        """Der Wortlaut eines Paragrafen steht nicht in der Akte."""
        js = APP_JS[APP_JS.index("function angabenAnklickbar("):]
        self.assertIn("gesetzeAnklickbar(ziel, teil); return;", js[:900])


class DieAdresseIstEinstellbar(unittest.TestCase):

    def test_die_voreinstellung_ist_die_amtliche_seite(self):
        e = Einstellungen.aus_umgebung({})
        self.assertEqual("https://www.gesetze-im-internet.de/", e.gesetze_url)
        self.assertEqual("{gesetz}/__{paragraf}.html", e.gesetze_muster)

    def test_beides_laesst_sich_umstellen(self):
        e = Einstellungen.aus_umgebung({
            "JUSPERFECT_GESETZE_URL": "https://beispiel.invalid/",
            "JUSPERFECT_GESETZE_MUSTER": "recht/{gesetz}-{paragraf}",
        })
        self.assertEqual("https://beispiel.invalid/", e.gesetze_url)
        self.assertEqual("recht/{gesetz}-{paragraf}", e.gesetze_muster)

    def test_leer_heisst_aus(self):
        e = Einstellungen.aus_umgebung({"JUSPERFECT_GESETZE_URL": ""})
        self.assertEqual("", e.gesetze_url)


class DerKnopfStehtNebenHaufe(unittest.TestCase):
    """Aus der Kanzlei am 25.09.2026: "ich finde unter mehr gar nicht die
    Gesetzestexte."

    Der Sprung stand bis dahin nur IN einer Antwort, neben einem genannten
    Paragrafen. Nachschlagen will man aber auch ohne Antwort - und wer nach
    dem Haufe-Vorbild sucht, sucht einen Knopf.
    """

    @property
    def html(self) -> str:
        return (WURZEL / "jusperfect" / "static" / "index.html").read_text(encoding="utf-8")

    def test_es_gibt_ihn_im_mehr_menue(self):
        html = self.html
        self.assertIn('data-aktion="gesetze"', html)
        # Im selben Menue wie Haufe, nicht irgendwo sonst.
        menue = html[html.index('data-aktion="triage"'):html.index('data-aktion="abschluss"')]
        self.assertIn('data-aktion="gesetze"', menue)

    def test_er_steht_fest_da_wie_eingangspruefung_und_pruefliste(self):
        """Zweimal aus der Kanzlei am 25.09.2026: "ich sehe ihn immer noch
        nicht."

        Er stand zuerst auf "hidden" und wurde aus dem Status eingeblendet -
        wie der Haufe-Knopf, der eine hinterlegte Adresse braucht. Die
        Adresse der amtlichen Seite steht aber fest im Programm; es gibt
        nichts einzublenden. Fehlt sie doch, sagt es der Klick. Ein Knopf,
        den niemand findet, ist schlimmer als einer, der einmal meldet.
        """
        html = self.html
        menue = html[html.index('data-aktion="triage"'):html.index('data-aktion="abschluss"')]
        zeile = [z for z in menue.splitlines() if 'data-aktion="gesetze"' in z][0]
        self.assertNotIn("hidden", zeile)
        # Und niemand blendet ihn nachtraeglich aus.
        self.assertNotIn('gs.hidden', APP_JS)

    def test_auch_der_gedaechtnisknopf_verschwindet_nicht_spurlos(self):
        """Aus der Kanzlei am 25.09.2026: "der Button Aktengedaechtnis ist
        jetzt komplett weg, sodass man gar nicht nachtraeglich das
        Aktengedaechtnis erstellen koennte."

        Etwas, das spurlos verschwindet, sieht aus wie ein Fehler - und
        niemand erfaehrt, dass es die Sache ueberhaupt gibt.
        """
        html = self.html
        # Er steht nicht mehr im Mehr-Menue, sondern als eigener Knopf neben
        # Analyse und Entwurf. Aus der Kanzlei am 25.09.2026:
        # "Aktengedaechtnis soll eigener Button sein."
        leiste = html[html.index('class="arbeitsknoepfe"'):html.index('class="mehr"')]
        zeile = [z for z in leiste.splitlines() if 'data-aktion="gedaechtnis"' in z][0]
        self.assertNotIn("hidden", zeile)
        self.assertIn('class="mini"', zeile)
        # Ist es aus, sagt der Klick, wie es wieder angeht.
        stelle = APP_JS[APP_JS.index("async function gedaechtnisAktualisieren("):]
        self.assertIn("K.gedaechtnisAktiv", stelle[:900])
        self.assertIn("JUSPERFECT_GEDAECHTNIS", stelle[:900])

    def test_ein_paragraf_im_fragefeld_fuehrt_direkt_hin(self):
        js = APP_JS[APP_JS.index("function gesetzNachschlagen("):]
        self.assertIn("GESETZESVERWEIS.exec(frage)", js[:1200])
        self.assertIn("gesetzesAdresse(m[3], m[1])", js[:1200])

    def test_sonst_zwischenablage_wie_bei_haufe(self):
        js = APP_JS[APP_JS.index("function gesetzNachschlagen("):]
        self.assertIn("clipboard.writeText(frage)", js[:1500])

    def test_der_status_traegt_die_adresse_zur_oberflaeche(self):
        """Wie beim Haufe-Knopf: Die Oberflaeche erfaehrt es aus dem Status."""
        import sys
        sys.path.insert(0, str(WURZEL / "tests"))
        from test_cowork import client, dienste

        s = client(dienste(), "ra-weber").get("/api/status").json()
        self.assertTrue(s["gesetze_aktiv"])
        self.assertTrue(s["gesetze"]["url"].startswith("https://"))
        self.assertIn("{gesetz}", s["gesetze"]["muster"])
        self.assertIn("{paragraf}", s["gesetze"]["muster"])

    def test_ohne_adresse_meldet_der_status_es_auch(self):
        import sys
        sys.path.insert(0, str(WURZEL / "tests"))
        from test_cowork import client, dienste
        from tests.hilfen import einstellungen

        s = client(dienste(einstellungen=einstellungen(JUSPERFECT_GESETZE_URL="")),
                   "ra-weber").get("/api/status").json()
        self.assertFalse(s["gesetze_aktiv"])


if __name__ == "__main__":
    unittest.main()
