"""Die eine Probe, die schreibt - und was sie davor verspricht.

Sie soll die 405 beim Ablegen des Aktengedaechtnisses aufklaeren: 405 heisst
bei jur|nodes "ungueltige Eingabe", und welcher Wert es ist, sagt der Server
im Feld "error". Diese Probe holt den Satz ab.

Weil sie schreibt, wird hier geprueft, dass sie ohne ausdrueckliches "ja"
nichts tut - und dass sie denselben Weg geht wie der Betrieb. Eine Probe, die
anders fragt als der Betrieb, prueft etwas anderes als den Betrieb.
"""

from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkzeug"))

import ablageprobe  # noqa: E402


class DieAbgelegteDateiIstEinEchtesGedaechtnis(unittest.TestCase):
    """Am 25.09.2026 legte die Probe ein selbstgebautes JSON ab.

    Der Server nahm es an - und danach lag in einer echten Akte eine Datei,
    die den Namen des Aktengedaechtnisses trug und keines war. Beim naechsten
    Oeffnen dieser Akte bricht das Lesen ab.

    Derselbe Fehler wie immer, nur andersherum: Eine Probe, die etwas anderes
    ablegt als der Betrieb, prueft etwas anderes als den Betrieb.
    """

    def test_es_laesst_sich_wieder_lesen(self):
        from jusperfect.gedaechtnis.packen import entpacken
        g = entpacken(ablageprobe.probeninhalt("REC-4711", date(2026, 9, 25)))
        self.assertEqual("REC-4711", g.akte_id)

    def test_es_gehoert_der_richtigen_akte(self):
        """Ein Gedaechtnis in der falschen Akte weist das Programm zurueck."""
        from jusperfect.gedaechtnis.packen import entpacken
        self.assertEqual("ABC", entpacken(ablageprobe.probeninhalt("ABC")).akte_id)

    def test_es_ist_leer_bis_auf_den_vermerk(self):
        from jusperfect.gedaechtnis.packen import entpacken
        g = entpacken(ablageprobe.probeninhalt("REC-1", date(2026, 9, 25)))
        self.assertEqual([], g.dokumente)
        self.assertEqual([], g.fragen_antworten)
        self.assertEqual([], g.chronologie)
        self.assertIn("2026-09-25", g.lebenssachverhalt)
        self.assertIn("Ablageprobe", g.lebenssachverhalt)

    def test_es_wird_mit_derselben_funktion_gepackt_wie_im_betrieb(self):
        """Nicht "auch gzip" - dieselbe Funktion. Sonst weicht irgendwann
        etwas ab, und niemand merkt es."""
        quelle = (WURZEL / "werkzeug" / "ablageprobe.py").read_text(encoding="utf-8")
        self.assertIn("from jusperfect.gedaechtnis.packen import packen", quelle)
        self.assertIn("return packen(g)", quelle)

    def test_es_traegt_nichts_aus_der_akte(self):
        from jusperfect.gedaechtnis.packen import entpacken
        g = entpacken(ablageprobe.probeninhalt("REC-1"))
        self.assertEqual("", g.aktenzeichen)
        self.assertEqual("", g.bezeichnung)


class OhneJaGeschiehtNichts(unittest.TestCase):

    def _lauf(self, antwort: str) -> tuple[int, mock.MagicMock]:
        with mock.patch.object(ablageprobe, "adapter_bauen") as bauen, \
                mock.patch("builtins.input", return_value=antwort), \
                mock.patch.dict("os.environ",
                                {"JUSPERFECT_JURNODES_URL": "https://beispiel.invalid/",
                                 "JURNODES_API_USER": "u", "JURNODES_API_KEY": "k"},
                                clear=False):
            code = ablageprobe.main(["115/26"])
        return code, bauen

    def test_bei_nein_wird_kein_adapter_gebaut(self):
        """Nicht einmal die Verbindung wird aufgemacht."""
        code, bauen = self._lauf("nein")
        self.assertEqual(0, code)
        bauen.assert_not_called()

    def test_ein_blosses_enter_ist_kein_ja(self):
        code, bauen = self._lauf("")
        self.assertEqual(0, code)
        bauen.assert_not_called()

    def test_auch_jawohl_ist_kein_ja(self):
        """Nur das Wort selbst zaehlt - sonst rutscht es durch."""
        code, bauen = self._lauf("jawohl")
        self.assertEqual(0, code)
        bauen.assert_not_called()


class OhneAktenzeichenPassiertNichts(unittest.TestCase):

    def test_es_wird_danach_gefragt(self):
        self.assertEqual(2, ablageprobe.main([]))


class DerWegIstDerDesBetriebs(unittest.TestCase):

    def test_der_adapter_kommt_aus_den_einstellungen(self):
        """aus_einstellungen zieht auch die abweichenden Pfade aus der Datei.

        Von Hand zusammengesetzt pruefte die Probe einen anderen Weg als den,
        den die Oberflaeche geht.
        """
        quelle = (WURZEL / "werkzeug" / "ablageprobe.py").read_text(encoding="utf-8")
        self.assertIn("HttpJurNodesAdapter.aus_einstellungen", quelle)

    def test_die_kennung_wird_gesucht_nicht_geraten(self):
        """recordSign ist das Aktenzeichen, identifier die Kennung."""
        adapter = mock.MagicMock()
        adapter.akten_suchen.return_value = [mock.Mock(id="REC-4711")]
        self.assertEqual("REC-4711", ablageprobe.kennung_suchen(adapter, "115/26"))
        adapter.akten_suchen.assert_called_once_with("115/26")

    def test_ohne_treffer_bleibt_die_kennung_leer(self):
        adapter = mock.MagicMock()
        adapter.akten_suchen.return_value = []
        self.assertEqual("", ablageprobe.kennung_suchen(adapter, "gibt-es-nicht"))


class DerWortlautWirdAbgeholt(unittest.TestCase):

    def test_bei_einer_abweisung_steht_der_satz_des_servers_da(self):
        from jusperfect.jurnodes.base import JurNodesFehler

        adapter = mock.MagicMock()
        adapter.akten_suchen.return_value = [mock.Mock(id="REC-1")]
        adapter.gedaechtnis_ablegen.side_effect = JurNodesFehler(
            "abgelehnt", serverwort='header folderId must be a number')
        gedruckt: list[str] = []
        with mock.patch.object(ablageprobe, "adapter_bauen", return_value=adapter), \
                mock.patch("builtins.input", return_value="ja"), \
                mock.patch("builtins.print", side_effect=lambda *a, **k: gedruckt.append(" ".join(map(str, a)))), \
                mock.patch.dict("os.environ",
                                {"JUSPERFECT_JURNODES_URL": "https://beispiel.invalid/",
                                 "JURNODES_API_USER": "u", "JURNODES_API_KEY": "k"},
                                clear=False):
            code = ablageprobe.main(["115/26"])
        self.assertEqual(1, code)
        self.assertIn("header folderId must be a number", "\n".join(gedruckt))

    def test_schweigt_der_server_wird_das_gesagt(self):
        """Eine Auskunft vorzutaeuschen, die es nicht gibt, ist schlimmer."""
        from jusperfect.jurnodes.base import JurNodesFehler

        adapter = mock.MagicMock()
        adapter.akten_suchen.return_value = [mock.Mock(id="REC-1")]
        adapter.gedaechtnis_ablegen.side_effect = JurNodesFehler("abgelehnt")
        gedruckt: list[str] = []
        with mock.patch.object(ablageprobe, "adapter_bauen", return_value=adapter), \
                mock.patch("builtins.input", return_value="ja"), \
                mock.patch("builtins.print", side_effect=lambda *a, **k: gedruckt.append(" ".join(map(str, a)))), \
                mock.patch.dict("os.environ",
                                {"JUSPERFECT_JURNODES_URL": "https://beispiel.invalid/",
                                 "JURNODES_API_USER": "u", "JURNODES_API_KEY": "k"},
                                clear=False):
            ablageprobe.main(["115/26"])
        self.assertIn("keinen Wortlaut", "\n".join(gedruckt))


class DieStartdateiWarntBevorSieSchreibt(unittest.TestCase):
    """Sie ist die einzige Probe, die schreibt. Das muss dastehen, bevor
    jemand doppelklickt - nicht erst danach."""

    @property
    def text(self) -> str:
        return (WURZEL / "ABLAGE-PRUEFEN.bat").read_text(encoding="ascii")

    def test_sie_gibt_es_und_sie_ist_windowstauglich(self):
        roh = (WURZEL / "ABLAGE-PRUEFEN.bat").read_bytes()
        self.assertIn(b"\r\n", roh, "cmd.exe stolpert ohne CRLF")
        self.assertEqual(0, roh.replace(b"\r\n", b"").count(b"\n"),
                         "gemischte Zeilenenden")
        roh.decode("ascii")   # wirft, wenn ein Umlaut hineingeraten ist

    def test_dass_sie_schreibt_steht_ganz_oben(self):
        text = self.text
        self.assertIn("SCHREIBT", text)
        # Vor der Frage nach dem Aktenzeichen, nicht danach.
        self.assertLess(text.index("SCHREIBT"), text.index("set /p AKTE"))

    def test_sie_sagt_auch_dass_nichts_ohne_ja_geschieht(self):
        self.assertIn("ja", self.text.lower())

    def test_sie_ruft_das_werkzeug(self):
        self.assertIn("werkzeug\\ablageprobe.py", self.text)

    def test_ohne_aktenzeichen_wird_nichts_aufgerufen(self):
        """Ein leeres Aktenzeichen darf nicht in das Werkzeug durchrutschen."""
        text = self.text
        self.assertIn("if not defined AKTE goto", text)
        self.assertLess(text.index("if not defined AKTE goto"),
                        text.index("werkzeug\\ablageprobe.py"))

    def test_ohne_klammernbloecke(self):
        """cmd wertet in Klammern frueher aus, als man denkt."""
        for zeile in self.text.splitlines():
            nackt = zeile.strip()
            if nackt.startswith("echo") or nackt.startswith("rem") or nackt.startswith("REM"):
                continue
            self.assertNotIn(") else", nackt)
            self.assertFalse(nackt.endswith("("), nackt)


if __name__ == "__main__":
    unittest.main()
