"""Das Werkzeug, das die jur|nodes-Schnittstelle abfragt statt sie zu raten.

Der Hersteller bestätigt eine offene REST-Schnittstelle, stellt die
Dokumentation aber auf dem jeweiligen Kundenserver bereit; uns liegt sie nicht
vor. Die Pfade in `http_adapter.py::Endpunkte` sind deshalb eine plausible
Annahme und ausdrücklich keine Zusage.

`python -m jusperfect.jurnodestest` macht aus der Wartezeit eine Messung: Es
ruft jeden Pfad einmal auf und schreibt hin, was geantwortet hat und wie die
Felder heissen. Ob jur|nodes ein Aktenzeichen „aktenzeichen", „az" oder
„fileNumber" nennt, entscheidet über die ganze Zuordnung – und steht in keiner
Vermutung, sondern nur in einer echten Antwort.

Zwei Zusagen hält diese Datei fest, weil sie in einer Kanzlei zählen: Es liest
nur, und in der Ausgabe steht kein Akteninhalt.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from jusperfect.config import KonfigurationsFehler
from jusperfect.jurnodes.http_adapter import Endpunkte


class DiePfadeLassenSichRichtigstellen(unittest.TestCase):
    """Ohne neuen Programmstand – sonst ist jeder Tippfehler eine Auslieferung."""

    def setUp(self) -> None:
        import tempfile
        self._ordner = tempfile.TemporaryDirectory()
        self.ordner = Path(self._ordner.name)
        self.addCleanup(self._ordner.cleanup)

    def _datei(self, inhalt) -> Path:
        pfad = self.ordner / "pfade.json"
        pfad.write_text(json.dumps(inhalt) if not isinstance(inhalt, str) else inhalt,
                        encoding="utf-8")
        return pfad

    def test_ohne_datei_gilt_die_vorgabe(self):
        self.assertEqual(Endpunkte(), Endpunkte.aus_datei(None))
        self.assertEqual(Endpunkte(), Endpunkte.aus_datei(""))

    def test_ein_einzelner_pfad_genuegt(self):
        """Man soll nicht alle sieben abschreiben müssen, um einen zu ändern."""
        e = Endpunkte.aus_datei(self._datei({"akten_suche": "/api/v2/files"}))
        self.assertEqual("/api/v2/files", e.akten_suche)
        self.assertEqual(Endpunkte().ordner_inhalt, e.ordner_inhalt)

    def test_auch_der_suchparameter_laesst_sich_aendern(self):
        """„suche" ist ebenso geraten wie die Pfade."""
        e = Endpunkte.aus_datei(self._datei({"suchparameter": "q"}))
        self.assertEqual("q", e.suchparameter)

    def test_eine_fehlende_datei_wird_benannt(self):
        with self.assertRaises(KonfigurationsFehler) as fehler:
            Endpunkte.aus_datei(self.ordner / "gibtsnicht.json")
        self.assertIn("fehlt", str(fehler.exception))

    def test_ein_tippfehler_im_namen_faellt_auf(self):
        """Sonst bleibt die Vorgabe stehen und niemand merkt es."""
        with self.assertRaises(KonfigurationsFehler) as fehler:
            Endpunkte.aus_datei(self._datei({"aktensuche": "/x"}))
        self.assertIn("aktensuche", str(fehler.exception))
        self.assertIn("akten_suche", str(fehler.exception), "Das Erlaubte gehört dazu.")

    def test_unbrauchbare_werte_fallen_auf(self):
        for wert in ({"akte": ""}, {"akte": 7}, {"akte": None}):
            with self.subTest(wert=wert):
                with self.assertRaises(KonfigurationsFehler):
                    Endpunkte.aus_datei(self._datei(wert))

    def test_kaputtes_json_wird_benannt(self):
        with self.assertRaises(KonfigurationsFehler) as fehler:
            Endpunkte.aus_datei(self._datei("{kein json"))
        self.assertIn("unlesbar", str(fehler.exception))


class DieAusgabeTraegtKeinenAkteninhalt(unittest.TestCase):
    """Sie wird weitergegeben - an die Entwicklung, vielleicht an den Hersteller."""

    def test_nur_feldnamen_und_arten_keine_werte(self):
        from jusperfect.jurnodestest import felder
        zeilen = felder({"aktenzeichen": "115/26 AR",
                         "bezeichnung": "Reinhold-Özdemir ./. Nordwerk",
                         "mandant": {"name": "Tanja Reinhold-Özdemir"},
                         "dokumente": [1, 2, 3]})
        text = " ".join(zeilen)
        for name in ("aktenzeichen", "bezeichnung", "mandant", "dokumente"):
            self.assertIn(name, text, name)
        for wert in ("115/26", "Reinhold", "Özdemir", "Nordwerk", "Tanja"):
            self.assertNotIn(wert, text, f"Akteninhalt in der Ausgabe: {wert}")

    def test_die_art_steht_dabei(self):
        from jusperfect.jurnodestest import felder
        text = " ".join(felder({"az": "x", "anzahl": 3, "offen": True,
                                "beteiligte": [{}, {}], "mandant": {}}))
        self.assertIn("(str)", text)
        self.assertIn("(int)", text)
        self.assertIn("(bool)", text)
        self.assertIn("Liste[2]", text)
        self.assertIn("Objekt", text)

    def test_eine_liste_wird_am_ersten_eintrag_gezeigt(self):
        from jusperfect.jurnodestest import felder
        self.assertIn("az (str)", " ".join(felder([{"az": "115/26"}, {"az": "7/26"}])))

    def test_eine_leere_liste_sagt_das(self):
        from jusperfect.jurnodestest import felder
        self.assertEqual(["(leere Liste)"], felder([]))


class EsLiestNur(unittest.TestCase):
    """Die Zusage ist: Es wird nichts geschrieben, angelegt oder gelöscht.

    **Bis zum 05.10.2026 wurde das als „kein POST" geprüft**, und das war
    dasselbe — der Vermerk war der einzige POST, den die Probe kannte. Seit die
    Beschreibung des Herstellers vorliegt, ist es nicht mehr dasselbe: Er hat
    die **Suche** in der E-Akte als POST gebaut (`/correspondence/search`).

    Geprüft wird deshalb jetzt die Zusage selbst: POST **nur** auf Pfade, die
    suchen. Jeder andere bleibt aus. Ein Test, der weiter „kein POST" verlangt
    hätte, hätte die Probe davon abgehalten, die E-Akte überhaupt zu lesen.
    """

    #: Pfade, die POST verlangen und trotzdem nur lesen - so gebaut vom
    #: Hersteller, nachzulesen in schnittstelle/jurnodes-api-1.0.2.json.
    #:
    #: Das Verfahren macht einen Aufruf nicht schreibend. Entscheidend ist,
    #: was er bewirkt: Die Korrespondenzsuche holt ein Verzeichnis, der
    #: Mail-Download holt eine Datei. Beide legen nichts an und aendern nichts.
    LESENDE_POSTS = ("/correspondence/search", "/mail/download")

    #: Pfade, die etwas ANLEGEN. Auf sie darf die Probe nie zeigen - weder mit
    #: POST noch sonstwie. Sie stehen hier beim Namen, weil eine Liste des
    #: Erlaubten allein nicht sagt, was verboten ist.
    SCHREIBENDE_PFADE = ("/record/note", "/correspondence/add", "/correspondence",
                         "/file-system/add-file", "/lead-notes")

    def _quelle(self) -> str:
        return (Path(__file__).resolve().parent.parent
                / "jusperfect" / "jurnodestest.py").read_text(encoding="utf-8")

    def test_es_wird_nichts_geschrieben_angelegt_oder_geloescht(self):
        quelle = self._quelle()
        self.assertNotIn(".put(", quelle)
        self.assertNotIn(".delete(", quelle)
        self.assertNotIn(".patch(", quelle)

    def test_post_nur_auf_pfade_die_nichts_anlegen(self):
        """Jeder POST in der Probe muss auf einen Pfad zeigen, der nur liest."""
        quelle = self._quelle()
        for stelle in re.finditer(r"\.post\(\s*([^,\n]+)", quelle):
            ziel = stelle.group(1).strip()
            self.assertTrue(
                any(p.rsplit("/", 1)[-1] in ziel or "korrespondenz_suche" in ziel
                    for p in self.LESENDE_POSTS),
                f"POST auf {ziel} - dieser Pfad legt etwas an oder ist unbekannt.")

    def test_kein_aufruf_zeigt_auf_einen_anlegenden_pfad(self):
        """Die Gegenprobe zur Liste des Erlaubten.

        Eine Liste dessen, was gehen darf, sagt nicht, was nicht gehen darf.
        `/record/note` steht in der Probe - aber nur mit GET, zum Lesen.
        """
        quelle = self._quelle()
        for stelle in re.finditer(r"\.post\(\s*([^,\n]+)", quelle):
            ziel = stelle.group(1).strip()
            for pfad in ("add-file", "correspondence/add", "lead-notes"):
                self.assertNotIn(pfad, ziel, f"POST auf {ziel} legt etwas an.")
            # /record/note legt einen Vermerk an - nur GET ist erlaubt.
            self.assertNotIn("endpunkte.vermerke", ziel,
                             "POST /record/note wuerde einen Vermerk anlegen.")

    def test_der_schreibende_vermerkpfad_wird_nicht_beschrieben(self):
        """`POST /record/note` legt einen Vermerk an. Die Probe liest ihn nur —
        mit GET und beiden Pflichtparametern."""
        quelle = self._quelle()
        self.assertIn("Nicht angefasst", quelle,
                      "Dass er nicht angefasst wird, gehört in die Ausgabe.")
        # Der Vermerk wird gelesen, nicht geschrieben.
        self.assertIn("client.get(endpunkte.vermerke", quelle)


if __name__ == "__main__":
    unittest.main()


def test_der_befund_wird_vom_programm_selbst_geschrieben(tmp_path, monkeypatch) -> None:
    """Die Startdatei leitete die Ausgabe mit ``>`` um. Am 23.09.2026 hatte das
    an einem Nachmittag drei Folgen: Der Schirm blieb minutenlang leer, ein
    offenes Notepad liess den ganzen Lauf misslingen, und die Datei war
    waehrend des Laufs leer. Alle drei verschwinden, wenn das Programm selbst
    mitschreibt."""
    from jusperfect import jurnodestest

    bat = (Path(__file__).resolve().parent.parent / "JURNODES-PRUEFEN.bat").read_text(encoding="utf-8")
    assert "> jurnodestest.txt" not in bat
    assert "Programmstand: %FASSUNG%" in bat

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("JUSPERFECT_JURNODES_URL", raising=False)
    jurnodestest.main([])
    assert (tmp_path / jurnodestest.BERICHT).is_file()


class DerZugangWirdEingetragenUndNichtAbgetippt(unittest.TestCase):
    """Aus der Kanzlei, 23.09.2026: „Wo gebe ich denn den Token ein?"

    Die richtige Antwort darf nicht „in eine Eingabeaufforderung, mit setx, und
    danach ein neues Fenster öffnen" lauten. An genau dieser Stelle ist in
    dieser Kanzlei schon die AWS-Einrichtung hängengeblieben; deshalb gibt es
    dafür ZUGANG-EINTRAGEN.bat, und deshalb gibt es das hier.

    Der Token gehört in die Umgebung des Windows-Kontos – nicht in eine Datei
    des Programmordners, denn der wird als ZIP weitergegeben.
    """

    WURZEL = Path(__file__).resolve().parent.parent

    def test_es_gibt_einen_doppelklick_dafuer(self):
        pfad = self.WURZEL / "JURNODES-ZUGANG.bat"
        self.assertTrue(pfad.is_file())
        self.assertIn(b"\r\n", pfad.read_bytes(), "Eine .bat braucht CRLF.")
        pfad.read_text(encoding="ascii")  # cmd stellt Umlaute falsch dar

    def test_er_ruft_das_programm(self):
        text = (self.WURZEL / "JURNODES-ZUGANG.bat").read_text(encoding="ascii")
        self.assertIn("-m jusperfect.jurnodeszugang", text)
        self.assertIn("pause", text, "Ohne pause ist die Meldung weg.")

    def test_die_drei_werte_heissen_wie_im_programm(self):
        """Sonst trägt der Nutzer etwas ein, das niemand liest."""
        from jusperfect.config import Einstellungen
        from jusperfect.jurnodeszugang import FELDER

        e = Einstellungen.aus_umgebung({})
        namen = [name for name, _, _ in FELDER]
        self.assertIn("JUSPERFECT_JURNODES_URL", namen)
        self.assertIn(e.jurnodes_benutzer_var, namen)
        self.assertIn(e.jurnodes_token_var, namen)

    def test_der_token_wird_verdeckt_eingegeben(self):
        """Was im schwarzen Fenster steht, liest der Nächste mit."""
        from jusperfect.jurnodeszugang import FELDER
        verdeckt = {name for name, _, v in FELDER if v}
        self.assertEqual({"JURNODES_API_KEY"}, verdeckt)

    def test_eine_adresse_ohne_https_wird_beanstandet(self):
        """Sonst erfährt man es erst beim ersten Aufruf."""
        from jusperfect.jurnodeszugang import hinweise_zur_adresse
        self.assertTrue(hinweise_zur_adresse("http://jurnodes.example/api"))
        self.assertFalse(hinweise_zur_adresse("https://jurnodes.example/api/extern/v1/x"))

    def test_ein_leerzeichen_in_der_adresse_faellt_auf(self):
        """Dieselbe Falle wie beim Aktenordner – auf schwarzem Grund unsichtbar."""
        from jusperfect.jurnodeszugang import hinweise_zur_adresse
        self.assertTrue(hinweise_zur_adresse("https://jurnodes.example /api"))

    def test_der_token_steht_in_keiner_datei_des_ordners(self):
        """Der Programmordner wird als ZIP weitergegeben."""
        quelle = (self.WURZEL / "jusperfect" / "jurnodeszugang.py").read_text(encoding="utf-8")
        self.assertIn("setx", quelle)
        self.assertNotIn("write_text", quelle)


def test_die_endpunktdatei_darf_ihre_anleitung_tragen() -> None:
    """Eine Datei, die ein Nichtprogrammierer bearbeiten soll, muss sagen
    duerfen, wie sie zu bearbeiten ist. Steht die Anleitung woanders, wird sie
    im Ernstfall nicht gefunden – und der Ernstfall ist hier ein Server, der
    einen Pfad anders fuehrt als seine eigene Beschreibung."""
    from jusperfect.jurnodes.http_adapter import Endpunkte

    e = Endpunkte.aus_datei(Path(__file__).resolve().parent.parent
                            / "jurnodes-endpunkte-beispiel.json")
    assert e.datei_hinzufuegen == "/file-system/add-file"


def test_ein_tippfehler_faellt_weiterhin_auf() -> None:
    """Die Nachsicht gilt nur fuer Unterstrich-Zeilen. Ein verschriebener
    Eintrag bliebe sonst stillschweigend wirkungslos, und die Vorgabe stuende
    weiter – das waere schlimmer als ein Abbruch."""
    import json
    import tempfile

    from jusperfect.config import KonfigurationsFehler
    from jusperfect.jurnodes.http_adapter import Endpunkte

    with tempfile.TemporaryDirectory() as ordner:
        datei = Path(ordner) / "pfade.json"
        datei.write_text(json.dumps({"datei_hinzufuegn": "/x"}), encoding="utf-8")
        try:
            Endpunkte.aus_datei(datei)
        except KonfigurationsFehler as fehler:
            assert "datei_hinzufuegn" in str(fehler)
        else:
            raise AssertionError("Der Tippfehler ist durchgegangen.")


# ---------------------------------------------------------------------------
# Auflisten und Herunterladen sind zwei verschiedene Rechte
#
# Aus der Kanzlei am 25.09.2026: Im Betrieb wurden 38 von 55 Dokumenten
# gelesen - genau die Zahl des Dateiordners, waehrend die 17 der Korrespondenz
# vollstaendig fehlten, obwohl alle 17 in lesbaren Formaten vorliegen. Die
# Probe sah bis dahin nur das Auflisten, und das klappt fuer beide Ordner.
# Eine Probe, die anders fragt als der Betrieb, prueft etwas anderes als den
# Betrieb: Der Betrieb laedt herunter, also muss die Probe das auch tun.
# ---------------------------------------------------------------------------


class _Antwort:
    def __init__(self, status: int, inhalt: bytes = b"", satz: str = "") -> None:
        self.status_code = status
        self.content = inhalt
        self._satz = satz
        self.headers: dict = {}

    def json(self):
        return {"error": self._satz} if self._satz else {}


class _Client:
    """Ein Server, der auf jede Frage dieselbe vorbereitete Antwort gibt."""

    def __init__(self, antwort: _Antwort) -> None:
        self.antwort = antwort
        self.gefragt: list = []

    def get(self, pfad, params=None, **kw):
        self.gefragt.append((pfad, params))
        return self.antwort


class _Endpunkte:
    datei_download = "/file-system/file/download"
    kennungparameter = "identifier"


def _ausgabe(antwort: _Antwort, probe) -> str:
    import io
    from contextlib import redirect_stdout

    from jusperfect.jurnodestest import _herunterladen_proben

    puffer = io.StringIO()
    with redirect_stdout(puffer):
        _herunterladen_proben(_Client(antwort), _Endpunkte(), "Korrespondenz", probe)
    return puffer.getvalue()


def test_ein_abgewiesener_download_nennt_das_recht_als_ursache() -> None:
    """403 heisst: Der Schluessel darf diese Datei nicht holen.

    Genau dieser Fall war monatelang als "Format wird nicht gelesen"
    fehlgedeutet. Die Probe muss ihn beim Namen nennen, sonst sucht die
    Kanzlei weiter an der falschen Stelle.
    """
    text = _ausgabe(_Antwort(403, satz="Keine Berechtigung"), ("ABC123", "pdf"))
    assert "abgewiesen" in text
    assert "403" in text
    assert "Keine Berechtigung" in text
    assert "Recht" in text, "Der Hinweis auf das Recht ist der ganze Zweck."


def test_ein_gelungener_download_zeigt_bytes_und_keinen_inhalt() -> None:
    """Gezaehlt wird, nicht angezeigt: In der Ausgabe steht kein Akteninhalt."""
    text = _ausgabe(_Antwort(200, inhalt=b"%PDF-1.7 geheim"), ("ABC123", "pdf"))
    assert "geht" in text
    assert "15 Bytes" in text
    assert "geheim" not in text, "Der Inhalt darf die Probe nicht verlassen."


def test_ohne_datei_wird_nichts_abgefragt() -> None:
    """Ein leerer Ordner ist kein Fehler - und keine Frage an den Server."""
    client = _Client(_Antwort(200))
    import io
    from contextlib import redirect_stdout

    from jusperfect.jurnodestest import _herunterladen_proben

    puffer = io.StringIO()
    with redirect_stdout(puffer):
        _herunterladen_proben(client, _Endpunkte(), "Korrespondenz", None)
    assert client.gefragt == []
    assert "keine Datei" in puffer.getvalue()


def test_die_probe_holt_hoechstens_eine_datei_je_ordner() -> None:
    """Zwei Ordner, zwei Anfragen - nicht 55. Die Probe belastet den Server
    des Herstellers, der je IP-Adresse eine Anfrage zugleich zulaesst."""
    client = _Client(_Antwort(200, inhalt=b"x"))
    import io
    from contextlib import redirect_stdout

    from jusperfect.jurnodestest import _herunterladen_proben

    with redirect_stdout(io.StringIO()):
        _herunterladen_proben(client, _Endpunkte(), "Korrespondenz", ("A", "pdf"))
        _herunterladen_proben(client, _Endpunkte(), "Dateiordner", ("B", "docx"))
    assert len(client.gefragt) == 2


class _OrdnerClient:
    """Ein Ordner mit einer Datei darin."""

    def __init__(self, eintraege) -> None:
        self.eintraege = eintraege

    def get(self, pfad, params=None, **kw):
        return _OrdnerAntwort(self.eintraege)


class _OrdnerAntwort:
    status_code = 200
    headers: dict = {}

    def __init__(self, eintraege) -> None:
        self.eintraege = eintraege

    def json(self):
        return {"elements": self.eintraege}


class _OrdnerEndpunkte:
    ordner_inhalt = "/file-system/folder/content"
    ordnerparameter = "folderId"


def test_der_ordner_liefert_eine_kennung_zum_pruefen() -> None:
    """Ohne Kennung kaeme die Download-Probe nie zum Zuge.

    Sie holt die Kennung aus derselben Liste, aus der der Betrieb sie holt -
    ``identifier``. Steht dort nichts, bleibt die Probe stumm statt zu raten.
    """
    import io
    from contextlib import redirect_stdout

    from jusperfect.jurnodestest import _ordner_aufteilen

    client = _OrdnerClient([
        {"file": {"fileName": "Schriftsatz", "fileExtension": "pdf",
                  "identifier": "XY99"}},
    ])
    with redirect_stdout(io.StringIO()):
        befund = _ordner_aufteilen(client, _OrdnerEndpunkte(), "2871")
    assert befund["dateien"] == 1
    assert befund["probe"] == ("XY99", "pdf")


def test_das_aktengedaechtnis_wird_nicht_als_probe_genommen() -> None:
    """Die eigene Datei von jusperfect sagt nichts ueber die Rechte an
    Akteninhalten - sie wurde ja von jusperfect selbst abgelegt."""
    import io
    from contextlib import redirect_stdout

    from jusperfect.jurnodes.base import GEDAECHTNIS_DATEI
    from jusperfect.jurnodestest import _ordner_aufteilen

    stamm = GEDAECHTNIS_DATEI.split(".")[0]
    client = _OrdnerClient([
        {"file": {"fileName": stamm, "fileExtension": "json.gz",
                  "identifier": "EIGEN"}},
    ])
    with redirect_stdout(io.StringIO()):
        befund = _ordner_aufteilen(client, _OrdnerEndpunkte(), "2871")
    assert befund["probe"] is None


# ---------------------------------------------------------------------------
# Die Suche nach dem Parameter der Vermerke
#
# Stand 28.09.2026: /record/note nimmt GET an (OPTIONS: GET,HEAD,POST),
# /record/note/search und /note/search antworten mit 404. Es fehlt allein der
# Name des Parameters - alle probierten Formen ergeben 405 "Bitte Daten
# angeben", und 405 heisst bei diesem Hersteller "ungueltige Eingabe".
# ---------------------------------------------------------------------------


def _probe():
    from jusperfect import jurnodestest

    return jurnodestest


def test_der_name_aus_der_herstellerbeschreibung_wird_probiert() -> None:
    """„id" stand in SEINER Beschreibung und war nie probiert worden.

    Fuenf Formen wurden am 25. und 28.09.2026 durchgegangen - "id" war nicht
    dabei, obwohl der Hersteller es an erster Stelle nennt. Ein Kandidat, den
    man uebersieht, kostet einen ganzen Tag Wartezeit auf eine Antwort.
    """
    assert "id" in _probe()._VERMERK_NAMEN
    assert _probe()._VERMERK_NAMEN[0] == "id", "Der erste Kandidat zuerst."


def test_die_namen_stammen_aus_dem_wortschatz_des_herstellers() -> None:
    namen = _probe()._VERMERK_NAMEN
    for name in ("record", "recordIdentifier", "identifier", "sign", "recordSign"):
        assert name in namen, name


def test_beide_kennungen_werden_durchprobiert(monkeypatch) -> None:
    """Die Akte hat zwei, und der Hersteller haelt sie streng getrennt.

    ``identifier`` ist der Schluessel, ``recordSign`` das Aktenzeichen. Wer das
    eine fuer das andere einsetzt, bekommt 404 und haelt einen richtigen Pfad
    fuer falsch - am 23.09.2026 genau so passiert.
    """
    p = _probe()
    gefragt: list[dict] = []

    class _Client:
        def get(self, pfad, params=None, **rest):
            gefragt.append(dict(params or {}))

            class _Antwort:
                status_code = 405

                @staticmethod
                def json():
                    return {"message": "Bitte Daten angeben"}

                text = "Bitte Daten angeben"

            return _Antwort()

        options = get

    class _Endpunkte:
        vermerke = "/record/note"
        fristen = "/todo/search"
        akteparameter = "recordIdentifier"
        # Seit dem 05.10.2026 geht die Probe zuerst ueber die Korrespondenz.
        korrespondenz_suche = "/correspondence/search"
        vermerkparameter = "id"
        vermerkakteparameter = "record"

    p._vermerke_suchen(_Client(), _Endpunkte(), "FL6BDPWJ940ALEY4BVP0", "X-100-2026")

    werte = {w for params in gefragt for w in params.values()}
    assert "FL6BDPWJ940ALEY4BVP0" in werte, "Die Kennung fehlt."
    assert "X-100-2026" in werte, "Das Aktenzeichen fehlt."
    namen = {n for params in gefragt for n in params}
    assert "id" in namen
    assert "page" in namen, "Der Server verlangt anderswo eine Seitenzahl > 0."


def test_der_satz_fuer_den_hersteller_steht_am_ende(capsys) -> None:
    """Der Satz zum Abschicken - und nur das, was wirklich offen ist.

    Bis zum 07.10.2026 fragte er: „Über welchen Pfad liefert die Schnittstelle
    die Einträge der E-Akte?" Seit der Beschreibung 1.0.2 ist das beantwortet
    (`POST /correspondence/search`), und am 06.10.2026 steht es sogar als
    beantwortet in `ANFRAGE-HERSTELLER.md` — gedruckt wurde die Frage
    trotzdem weiter.

    Eine Anfrage, die Beantwortetes noch einmal fragt, kostet zweierlei: die
    Zeit des Lesers beim Hersteller und die Glaubwürdigkeit der Zeilen
    daneben, die wirklich offen sind. Dieser Test hält beides fest — dass der
    bekannte Weg genannt, aber nicht mehr erfragt wird.
    """
    p = _probe()

    class _Client:
        def get(self, pfad, params=None, **rest):
            class _Antwort:
                status_code = 405
                text = "Bitte Daten angeben"

                @staticmethod
                def json():
                    return {"message": "Bitte Daten angeben"}

            return _Antwort()

        options = get

    class _Endpunkte:
        vermerke = "/record/note"
        fristen = "/todo/search"
        akteparameter = "recordIdentifier"
        # Seit dem 05.10.2026 geht die Probe zuerst ueber die Korrespondenz.
        korrespondenz_suche = "/correspondence/search"
        vermerkparameter = "id"
        vermerkakteparameter = "record"

    p._vermerke_suchen(_Client(), _Endpunkte(), "FL6B", "X-100-2026")
    ausgabe = capsys.readouterr().out
    # Der bekannte Weg wird genannt, damit der Leser ihn vor sich hat.
    assert "POST /correspondence/search" in ausgabe
    assert "GET /record/note?id=..&record=.." in ausgabe
    assert "BEIDEN Pflicht" in ausgabe
    # Aber er wird nicht mehr erfragt.
    assert "Mit welchem Parameter" not in ausgabe, "Das ist beantwortet."
    assert "Ueber welchen Pfad" not in ausgabe, "Das ist beantwortet."
    # Und das, was offen ist, steht da - und zwar nur noch das.
    assert "ANFRAGE-HERSTELLER.md" in ausgabe
    assert "isInbox" in ausgabe
    assert "Offen sind nur noch zwei Kleinigkeiten" in ausgabe
    # Seit dem 11.10.2026 wird isInbox nicht mehr gefragt, sondern genannt.
    assert "1 = Eingang, 0 = Ausgang" in ausgabe
    assert "1 = eingegangen?" not in ausgabe, "Das ist beantwortet."
    # Was beantwortet ist, wird nicht mehr als offen ausgegeben.
    assert "Offen ist, warum der Server" not in ausgabe
    assert "Offen bleiben ausserdem: die Dateiart" not in ausgabe


# ---------------------------------------------------------------------------
# Die Zahl, die /record/note haben will
#
# Von zehn Namen antwortete am 28.09.2026 genau einer anders: "id" ergab 400
# mit "Value (FL6BDPWJ940ALEY4BVP0) cannot be parsed into number". Der Server
# kennt den Parameter und will eine Zahl - die Akte hat aber zwei Kennungen,
# und keine davon ist eine.
# ---------------------------------------------------------------------------


def test_die_felder_der_trefferliste_werden_gezeigt() -> None:
    """Die Huelle sagt ueber jede Akte dasselbe; die Namen stehen darunter.

    Eine Seitenantwort dieses Herstellers lautet {amountTotal, pagesTotal,
    elements}. Genau diese drei Zeilen standen im Bericht - und die Feldnamen,
    derentwegen die Probe laeuft, eine Ebene tiefer und ungezeigt.
    """
    from jusperfect.jurnodestest import felder

    zeilen = felder({"amountTotal": 50, "pagesTotal": 1,
                     "elements": [{"id": 4711, "recordSign": "X-100-2026"}]})
    text = " ".join(zeilen)
    assert "amountTotal" in text, "Die Hülle gehört weiter dazu."
    assert "id (int)" in text, "Der Feldname aus dem Treffer fehlt."
    assert "recordSign" in text
    assert "4711" not in text, "Werte gehören nicht in die Ausgabe."
    assert "X-100-2026" not in text


def test_nur_die_zahlen_der_eigenen_akte_werden_probiert() -> None:
    """Durchzaehlen waere in einer Kanzlei das Falsche.

    1, 2, 3 ... ist schnell geschrieben, und jede dieser Zahlen gehoert zu
    IRGENDEINER Akte des Hauses. Wer sie abruft, liest Vermerke fremder
    Mandate. Probiert wird deshalb allein, was der Server zu DIESER Akte
    selbst herausgibt.
    """
    p = _probe()
    gefragt: list[dict] = []

    class _Antwort:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"identifier": "FL6B", "recordSign": "X-100-2026",
                    "id": 4711, "fileFolderId": 88, "archiviert": False,
                    "mandant": {"nummer": 12345}}

    class _Client:
        def get(self, pfad, params=None, **rest):
            gefragt.append(dict(params or {}))
            return _Antwort()

        options = get

    class _Endpunkte:
        vermerke = "/record/note"
        fristen = "/todo/search"
        akteparameter = "recordIdentifier"
        # Seit dem 05.10.2026 geht die Probe zuerst ueber die Korrespondenz.
        korrespondenz_suche = "/correspondence/search"
        vermerkparameter = "id"
        vermerkakteparameter = "record"
        akte = "/record"
        kennungparameter = "identifier"

    p._vermerke_suchen(_Client(), _Endpunkte(), "FL6B", "X-100-2026")

    probiert = {params["id"] for params in gefragt
                if "id" in params and isinstance(params["id"], int)}
    assert probiert == {4711, 88, 12345}, probiert
    assert False not in probiert, "bool ist in Python eine Zahl – als Kennung nicht."


def test_ohne_zahlen_wird_nichts_erfunden() -> None:
    """Gibt die Akte keine Zahl heraus, wird auch keine probiert."""
    p = _probe()
    gefragt: list[dict] = []

    class _Antwort:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"identifier": "FL6B", "recordSign": "X-100-2026"}

    class _Client:
        def get(self, pfad, params=None, **rest):
            gefragt.append(dict(params or {}))
            return _Antwort()

        options = get

    class _Endpunkte:
        vermerke = "/record/note"
        fristen = "/todo/search"
        akteparameter = "recordIdentifier"
        # Seit dem 05.10.2026 geht die Probe zuerst ueber die Korrespondenz.
        korrespondenz_suche = "/correspondence/search"
        vermerkparameter = "id"
        vermerkakteparameter = "record"
        akte = "/record"
        kennungparameter = "identifier"

    p._vermerke_suchen(_Client(), _Endpunkte(), "FL6B", "X-100-2026")
    zahlen = [params["id"] for params in gefragt
              if "id" in params and isinstance(params["id"], int)]
    assert zahlen == [], zahlen


def test_die_probe_laeuft_mit_den_echten_endpunkten() -> None:
    """Die Attrappe trug weniger als das echte Objekt.

    Am 01.10.2026 brach die Vermerksuche in vier Pruefungen mit
    AttributeError ab, weil ``_Endpunkte`` nur ``vermerke`` kannte - der
    Betrieb aber ``fristen`` und ``akteparameter`` mitbringt. Dieselbe Form,
    die dieses Projekt seit September verfolgt: Eine Probe, die anders
    antwortet als der Betrieb, prueft etwas anderes.

    Deshalb laeuft hier das ECHTE Endpunkte-Objekt mit. Greift die Probe
    kuenftig auf ein weiteres Feld zu, faellt es hier auf und nicht in der
    Kanzlei.
    """
    p = _probe()

    class _Antwort:
        status_code = 405
        text = "Bitte Daten angeben"
        headers: dict = {}

        @staticmethod
        def json():
            return {"message": "Bitte Daten angeben"}

    class _Client:
        def get(self, pfad, params=None, **rest):
            return _Antwort()

        options = get
        request = get

    p._vermerke_suchen(_Client(), Endpunkte(), "FL6B", "X-100-2026")


def test_der_aufgabenpfad_wird_nach_allen_drei_arten_gefragt() -> None:
    """Er kennt frist, task und resubmit - gefragt wurde nur nach Fristen.

    Die Akte X-100-2026 hat keine Frist; der Pfad kam deshalb mit null
    Eintraegen zurueck und sah geprueft aus. Geprueft war ein Drittel.
    """
    p = _probe()
    gefragt: list[dict] = []

    class _Antwort:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"amountTotal": 0, "elements": []}

    class _Client:
        def get(self, pfad, params=None, **rest):
            gefragt.append(dict(params or {}))
            return _Antwort()

        options = get

    p._vermerke_als_todo(_Client(), Endpunkte(), "FL6B")
    arten = {params.get("type") for params in gefragt}
    assert {"frist", "task", "resubmit"} <= arten, arten
    assert None in arten, "Einmal ohne type - sonst bleibt unbekannt, was es sonst gibt."


def test_die_beschreibung_des_servers_wird_ausgelesen(capsys) -> None:
    """Bei Dritten warten, nicht raten - aber fragen darf man.

    Der Hersteller stellt die OpenAPI-Beschreibung auf dem Kundenserver
    bereit. Steht sie dort, beantwortet sie die Frage nach dem Parameter
    endgueltig, statt einen elften Namen zu erfinden.
    """
    p = _probe()

    class _Antwort:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"openapi": "3.0.1", "paths": {"/record/note": {"get": {"parameters": [
                {"name": "id", "in": "query", "required": True,
                 "schema": {"type": "integer"}}]}}}}

    class _Client:
        def get(self, pfad, params=None, **rest):
            return _Antwort()

    assert p._beschreibung_suchen(_Client(), Endpunkte()) is True
    ausgabe = capsys.readouterr().out
    assert "GET /record/note" in ausgabe
    assert "id" in ausgabe
    assert "integer" in ausgabe
    assert "Pflicht" in ausgabe


def test_ohne_beschreibung_wird_das_gesagt(capsys) -> None:
    """Und nicht stillschweigend uebergangen."""
    p = _probe()

    class _Antwort:
        status_code = 404
        text = ""

        @staticmethod
        def json():
            return {}

    class _Client:
        def get(self, pfad, params=None, **rest):
            return _Antwort()

    assert p._beschreibung_suchen(_Client(), Endpunkte()) is False
    assert "Keiner der ueblichen Pfade" in capsys.readouterr().out


def test_die_arten_werden_gezeigt_der_betreff_nicht() -> None:
    """Die eng begrenzte Ausnahme von „keine Werte".

    Ob die zehn Aufgaben einer Akte Vermerke sind, steht in todoType - einem
    Schluesselwort des Herstellers. Es nicht zu zeigen hiesse, die Frage offen
    zu lassen, obwohl die Antwort vorlag.

    Der Betreff dagegen traegt den Fall. Er bleibt drinnen, und diese Pruefung
    haelt das fest: Die Ausgabe wird weitergegeben, vielleicht an den
    Hersteller.
    """
    p = _probe()
    daten = {"elements": [
        {"todoType": "task", "todoDeadlineStatus": "offen",
         "todoSubject": "Telefonat Reinhold-Özdemir wegen Kündigung"},
        {"todoType": "task", "todoDeadlineStatus": "erledigt",
         "todoSubject": "Fristablauf Berufungsbegründung"},
    ]}
    import io
    import contextlib
    fang = io.StringIO()
    with contextlib.redirect_stdout(fang):
        p._arten_zeigen(daten)
    ausgabe = fang.getvalue()
    assert "task" in ausgabe
    assert "offen" in ausgabe and "erledigt" in ausgabe
    for geheim in ("Telefonat", "Reinhold", "Özdemir", "Kündigung",
                   "Berufungsbegründung", "Fristablauf"):
        assert geheim not in ausgabe, f"Akteninhalt in der Ausgabe: {geheim}"


def test_zahlen_aus_den_aufgaben_werden_gesammelt() -> None:
    """Die Akte gab fuenf Zahlen her, und keine nahm /record/note an.

    Die Aufgaben tragen eigene - todoGroup, todoDeadlineId. Sie gehoeren zu
    DIESER Akte und sind damit so erlaubt wie die der Akte selbst; gezaehlt
    wird weiterhin nicht.
    """
    p = _probe()
    zahlen = p._zahlen_aus_eintraegen({"elements": [
        {"todoGroup": 7, "todoDeadlineId": 90210, "todoIdentifier": "XY",
         "erledigt": False},
        {"todoGroup": 7, "todoDeadlineId": 90211},
    ]})
    werte = {wert for _, wert in zahlen}
    assert werte == {7, 90210, 90211}, werte
    assert False not in werte, "bool ist in Python eine Zahl – als Kennung nicht."


def test_die_beschreibung_wird_auch_oberhalb_der_kennung_gesucht() -> None:
    """Sie gehoert zum Server, nicht zur Kennung der Kanzlei.

    Am 01.10.2026 antworteten alle sechs Pfade unter
    .../api/extern/v1/<Kennung>/ mit 404. Das heisst nicht, dass es keine
    Beschreibung gibt - nur, dass sie dort nicht liegt.
    """
    p = _probe()
    gefragt: list[str] = []

    class _Antwort:
        def __init__(self, treffer: bool) -> None:
            self.status_code = 200 if treffer else 404
            self._treffer = treffer

        text = ""

        def json(self):
            if self._treffer:
                return {"openapi": "3.0.1", "paths": {}}
            return {}

    class _Client:
        base_url = "https://x.jur-nodes.net/api/extern/v1/ad8b"

        def get(self, pfad, params=None, **rest):
            gefragt.append(pfad)
            return _Antwort(pfad == "https://x.jur-nodes.net/api/openapi.json")

    assert p._beschreibung_suchen(_Client(), Endpunkte()) is True
    assert "https://x.jur-nodes.net/api/extern/v1/openapi.json" in gefragt
    assert "https://x.jur-nodes.net/api/openapi.json" in gefragt


def test_eine_liste_sagt_wovon_sie_eine_ist() -> None:
    """„todoFolder (Liste[1])" - und die Probe ging nicht hinein.

    Sie steigt nur in Listen von Objekten ab. Steht in der Liste eine
    Ordnernummer, fuehrt sie zum Vermerk; das war am 01.10.2026 nicht zu
    sehen. Eine Liste ohne Angabe ihres Inhalts ist eine Auskunft, die keine
    ist.
    """
    from jusperfect.jurnodestest import felder

    text = " ".join(felder({"todoFolder": [4711], "namen": ["Meier"],
                            "leer": [], "objekte": [{"a": 1}]}))
    assert "Liste[1] von int" in text
    assert "Liste[1] von str" in text
    assert "4711" not in text, "Werte gehören nicht in die Ausgabe."
    assert "Meier" not in text


def test_der_ordner_einer_aufgabe_wird_gefunden() -> None:
    p = _probe()
    daten = {"elements": [
        {"todoFolder": [2871], "todoSubject": "egal"},
        {"todoFolder": [{"id": 11142, "folderName": "egal"}]},
        {"todoFolder": [2871]},
        {"todoFolder": []},
    ]}
    assert p._ordner_der_aufgaben(daten) == [2871, 11142]


def test_die_eakte_wird_gesucht_und_nur_gelesen() -> None:
    """Die Vermerke stehen in der E-Akte, nicht in der To-Do-Liste.

    Am 01.10.2026 hat ein Blick in jur|nodes geklaert, woran zwanzig
    Parameternamen vorbeigelaufen sind: Die zehn „task"-Eintraege sind die
    To-Do-Liste („Aufgabe Sonstiges"); die Vermerke liegen in der E-Akte,
    zusammen mit den Mails.

    Gefragt wird mit OPTIONS - der Server unterscheidet sauber zwischen „gibt
    es nicht" (404) und einer Allow-Zeile. Geschrieben wird nichts.
    """
    p = _probe()
    verfahren: list[str] = []
    gefragt: list[str] = []

    class _Antwort:
        def __init__(self, pfad: str) -> None:
            self.status_code = 200 if pfad == "/record/process" else 404
            self.headers = {"allow": "GET,HEAD"} if self.status_code == 200 else {}
            self.text = ""

        @staticmethod
        def json():
            return {"amountTotal": 3, "elements": [{"entryType": "note"}]}

    class _Client:
        def request(self, art, pfad, **rest):
            verfahren.append(art)
            return _Antwort(pfad)

        def get(self, pfad, params=None, **rest):
            gefragt.append(pfad)
            return _Antwort(pfad)

    p._eakte_suchen(_Client(), Endpunkte(), "FL6B")
    assert set(verfahren) == {"OPTIONS"}, verfahren
    assert gefragt and all(pfad == "/record/process" for pfad in gefragt), gefragt


def test_die_frage_an_den_hersteller_nennt_die_eakte(capsys) -> None:
    p = _probe()

    class _Antwort:
        status_code = 404
        text = ""
        headers: dict = {}

        @staticmethod
        def json():
            return {}

    class _Client:
        def get(self, pfad, params=None, **rest):
            return _Antwort()

        options = get
        request = lambda self, art, pfad, **rest: _Antwort()

    p._vermerke_suchen(_Client(), Endpunkte(), "FL6B", "X-100-2026")
    ausgabe = capsys.readouterr().out
    # Die E-Akte heisst in der Schnittstelle Korrespondenz - und der Pfad
    # dorthin ist bekannt. Was dasteht, ist der Pfad, nicht die Frage danach.
    assert "POST /correspondence/search" in ausgabe
    # Und die drei Dinge, die der Lauf vom 08.10.2026 geklaert hat, stehen
    # ausdruecklich als BEANTWORTET da - damit sie niemand wieder fragt.
    assert "mail/download" in ausgabe and ".eml" in ausgabe
    assert "attachmentId" in ausgabe and "postFileUniqueKey" in ausgabe
    assert "nicht mehr zu fragen" in ausgabe


def test_der_probelauf_fuer_ziffer_6_2(capsys) -> None:
    """Welche Wörter führt der Aktenstatus im Bestand?

    Daran hängt die Aufbewahrung. Welche Wörter das Programm kennt, steht an
    **einer** Stelle: ``_STATUS`` im Adapter. Die Probe fragt jene Tabelle,
    statt eine zweite zu führen.

    **Warum das geprüft wird.** Bis zum 07.10.2026 hatte die Probe eine
    eigene Liste, und zwar eine veraltete: Sie kannte nur „archiviert" und
    „archived". Der Lauf vom 07.10.2026 meldete deshalb bei zehn Akten
    ``active <- kennt das Programm NICHT``, obwohl ``_STATUS`` „active"
    führt. Dieser Test hielt den Fehler fest, weil er die veraltete Liste
    nachbaute: Er verlangte, dass „open" als unbekannt gilt - und „open"
    steht in ``_STATUS``. Eine Kopie veraltet, und ein Test, der die Kopie
    nachbaut, veraltet mit ihr.

    Hier liegt jetzt beides richtig: „open" und „archiviert" sind bekannt und
    werden mit ihrer Übersetzung gezeigt, „closed" ist es nicht.

    Gefragt wird die Aktenliste, nicht eine einzelne Akte - hundert Akten je
    Seite statt einer Stichprobe von eins. Gezählt wird Wort und Anzahl; kein
    Aktenzeichen, kein Rubrum, kein Inhalt.
    """
    p = _probe()
    gefragt: list[dict] = []

    class _Antwort:
        status_code = 200
        text = ""

        def __init__(self, seite):
            self._seite = seite

        def json(self):
            if self._seite > 2:
                return {"elements": []}
            return {"amountTotal": 150, "elements": [
                {"identifier": "A", "sign": "D-1", "shortRubrum": "Meier ./. Schulz",
                 "status": "open"},
                {"identifier": "B", "sign": "D-2", "shortRubrum": "geheim", "status": "archiviert"},
                {"identifier": "C", "sign": "D-3", "shortRubrum": "geheim", "status": "closed"},
            ]}

    class _Client:
        def get(self, pfad, params=None, **rest):
            gefragt.append(dict(params or {}))
            return _Antwort((params or {}).get("page", 1))

    p._statuswoerter(_Client(), Endpunkte())
    ausgabe = capsys.readouterr().out

    assert "open: 2" in ausgabe and "closed: 2" in ausgabe and "archiviert: 2" in ausgabe
    assert ausgabe.count("kennt das Programm NICHT") == 1, "allein closed ist unbekannt"
    assert "closed: 2   <- kennt das Programm NICHT" in ausgabe
    assert "archiviert: 2   <-" not in ausgabe, "archiviert kennt es sehr wohl"
    # Die Uebersetzung muss dastehen, sonst ist nicht nachzulesen, was das
    # Programm aus dem Wort macht - und genau daran haengt die Aufbewahrung.
    assert "open: 2   -> laufend" in ausgabe
    assert "archiviert: 2   -> archiviert" in ausgabe
    # Ein unbekanntes Wort wird "unbekannt", NICHT "laufend". Stand hier das
    # Falsche, haette der Leser einen gefaehrlichen Satz geglaubt.
    assert "laufend\"" not in ausgabe, "unbekannt heisst nicht laufend"
    assert "Ziffer 6.2" in ausgabe

    for geheim in ("Meier", "Schulz", "D-1", "D-2"):
        assert geheim not in ausgabe, f"Akteninhalt in der Ausgabe: {geheim}"

    assert all(params.get("page") for params in gefragt), "Seite 0 weist der Server ab."


def test_eine_abweisung_beantwortet_die_frage_trotzdem(capsys) -> None:
    """Status 401 auf die E-Akte ist eine Antwort, kein Abbruch.

    **Der Lauf vom 07.10.2026.** `/correspondence/search` kam mit Status 401
    zurück, während jeder andere Pfad desselben Laufs mit 200 antwortete.
    Der Abschnitt endete danach still: Der Satz „Kann die E-Akte eingeschaltet
    werden?" wurde nie gedruckt, weil er erst nach dem gelungenen Lesen stand.

    Damit ließ der Prüfbogen den Leser mit zwanzig Zeilen Befund allein und
    beantwortete genau die Frage nicht, für die er gebaut ist. Ein Status 401
    sagt etwas Klares: Der Zugang steht, dieser eine Pfad wird abgewiesen -
    das ist ein Recht, kein Programmfehler. Genau das muss dastehen.
    """
    p = _probe()

    class _Antwort:
        status_code = 401
        text = "{}"

        def json(self):
            return {}

    class _Client:
        def post(self, pfad, json=None, **rest):
            return _Antwort()

    p._korrespondenz_lesen(_Client(), Endpunkte(), "FL6BDPWJ940ALEY4BVP0")
    ausgabe = capsys.readouterr().out

    assert "Kann die E-Akte eingeschaltet werden?" in ausgabe, \
        "Die Frage muss auch bei einer Abweisung beantwortet werden."
    assert "NEIN" in ausgabe
    assert "401" in ausgabe
    assert "Recht" in ausgabe, "Der Leser muss erfahren, woran es liegt."
    assert "ANFRAGE-HERSTELLER.md" in ausgabe, "Und wo die Frage steht."
    assert "Am Programm ist dafuer nichts zu tun" in ausgabe


def test_vermerke_werden_mit_id_UND_record_probiert(capsys) -> None:
    """Die Beschreibung verlangt zwei Pflichtparameter - also beide zusammen.

    GET /record/note führt `id` (Zahl) **und** `record` (Zeichenkette), beide
    Pflicht. Bis zum 07.10.2026 probierte diese Suche jeden Namen EINZELN;
    zwanzig Formen, jede mit einem Wert. Der Server antwortete jedes Mal mit
    405 und „Bitte Daten angeben" - und das war keine Klage über den Namen,
    sondern die zutreffende Auskunft, dass der zweite Wert fehlt.

    Geprüft wird hier zweierlei: dass die Form überhaupt vorkommt, und dass
    dabei **nur** Zahlen verwendet werden, die der Server selbst zu dieser
    Akte herausgibt. Jede andere Nummer gehört einer fremden Akte.
    """
    p = _probe()
    gefragt: list[dict] = []

    class _Antwort:
        status_code = 405
        text = "Bitte Daten angeben"

        def json(self):
            return {}

    class _Client:
        def get(self, pfad, params=None, **rest):
            gefragt.append({"pfad": pfad, **(params or {})})
            if pfad == Endpunkte().akte:
                class _Akte:
                    status_code = 200
                    text = ""

                    def json(self):
                        # Flach, so wie GET /record wirklich antwortet -
                        # gemessen im Lauf vom 07.10.2026.
                        return {"identifier": "FL6B",
                                "fileFolderId": 11142,
                                "correspondenceFolderId": 2871}
                return _Akte()
            return _Antwort()

        def options(self, pfad, **rest):
            return _Antwort()

    p._vermerke_suchen(_Client(), Endpunkte(), "FL6BDPWJ940ALEY4BVP0", "X-100-2026")
    ausgabe = capsys.readouterr().out

    assert "id UND record" in ausgabe, "Die Form muss angekündigt werden."
    zusammen = [g for g in gefragt
                if g.get("pfad") == Endpunkte().vermerke
                and "id" in g and "record" in g]
    assert zusammen, "Keine einzige Anfrage trug beide Pflichtparameter."
    erlaubt = {11142, 2871}
    for g in zusammen:
        assert g["record"] == "FL6BDPWJ940ALEY4BVP0"
        assert g["id"] in erlaubt, \
            f"id={g['id']} gibt die Akte nicht selbst heraus - fremde Nummer."


def test_aus_dem_korrespondenzbaum_wird_nichts_geholt() -> None:
    """Dort liegen fremde Dateien - gemessen, nicht vermutet.

    Dreimal geprüft, dreimal derselbe Befund: Die Ordner hinter
    `correspondenceFolderId` tragen Ablagen, die älter sind als die Akte
    selbst. Im Lauf vom 07.10.2026 war die Akte am 30.07.2026 angelegt und
    fünf Ordner ab Dezember 2022 befüllt. Eine Datei kann nicht in eine Akte
    gelegt worden sein, die es noch nicht gab.

    Die Leseprobe holte aus diesem Baum eine Datei - 44763 Bytes, Status 200.
    Kein Inhalt stand im Bericht, aber geholt war sie. Das ist der Blick in
    eine fremde Handakte, und er beantwortet seit dem 05.10.2026 keine Frage
    mehr: Der Betrieb liest diesen Baum nicht.
    """
    quelle = Path("jusperfect/jurnodestest.py").read_text(encoding="utf-8")

    # Der Korrespondenzordner darf gar nicht mehr geholt werden - weder
    # gelistet noch heruntergeladen. Seine Nummer gehört in den anderen Baum.
    assert 'feld="correspondenceFolderId"' not in quelle, \
        "Die Nummer wurde wieder am Dateipfad gefragt - das ist der falsche Baum."

    # Im Dateibaum bleibt die Leseprobe - dort gehören die Dateien zur Akte.
    stelle = quelle.index("ordner = _ordner_der_akte")
    assert "_herunterladen_proben(" in quelle[stelle:stelle + 1200], \
        "Im Dateiordner ist die Leseprobe richtig und muss bleiben."


def test_das_fehlende_recht_steht_in_der_beschreibung(capsys) -> None:
    """Ein 401 ist kein Rätsel — die Beschreibung nennt das Recht beim Namen.

    **Vier Wochen lang übersehen.** Der Hersteller nennt zu jedem der 94
    Aufrufe das benötigte Recht, aber im Fließtext des Feldes `description`,
    hinter der Erläuterung:

        "Listet alle Korrespondenzen (derzeit einer Akte) auf.
         Benötigte Rechte: search:correspondence"

    Der Lauf vom 07.10.2026 bekam auf genau diesen Aufruf ein 401, und die
    Beschreibung sagt zu 401: „Authentifizierung ungültig". Die Antwort lag
    die ganze Zeit in der Datei im Programmordner — gesucht wurde an den
    Feldnamen, nicht in den Sätzen.

    Deshalb wird sie jetzt ausgelesen. Geprüft wird gegen die **echte** Datei,
    nicht gegen einen Nachbau: Ein Nachbau könnte die Form bestätigen, die ich
    erwarte, statt der, die der Hersteller liefert.
    """
    p = _probe()
    daten = json.loads(
        Path("schnittstelle/jurnodes-api-1.0.2.json").read_text(encoding="utf-8"))
    p._rechte_sammeln(daten["paths"])

    # Der Aufruf, an dem alles hängt.
    assert p.recht_fuer("/correspondence/search", "post") == "search:correspondence"
    # Die Vermerke brauchen kein weiteres Recht - dasselbe wie GET /record,
    # und das antwortet bereits.
    assert p.recht_fuer("/record/note", "get") == "read:records"
    assert p.recht_fuer("/record", "get") == "read:records"
    # Und die Aufrufe, die am 07.10.2026 mit 200 geantwortet haben.
    assert p.recht_fuer("/record/search", "get") == "search:records"
    assert p.recht_fuer("/file-system/file/download", "get") == "download:file"
    # Auch der Pfad ohne führenden Schrägstrich - der Schreibfehler des
    # Herstellers darf die Auskunft nicht kosten.
    assert p.recht_fuer("/correspondence/get-by-reference", "post") == \
        "search:correspondence"

    # Und das Urteil nennt es, statt den Leser raten zu lassen.
    p._eakte_urteil(0, 0, 0, abweisung=401, pfad="/correspondence/search")
    ausgabe = capsys.readouterr().out
    assert "search:correspondence" in ausgabe, "Das Recht muss dastehen."
    assert "NEIN" in ausgabe
    assert "Am Programm ist dafuer nichts zu tun" in ausgabe


def test_die_rechte_der_benutzten_aufrufe_stehen_im_bericht(capsys) -> None:
    """Welches Recht jeder benutzte Aufruf braucht — als Liste zum Nachsehen.

    Damit der Verwalter in jur|nodes nicht sieben Beschreibungstexte
    durchsuchen muss, sondern eine Spalte vor sich hat.
    """
    p = _probe()
    daten = json.loads(
        Path("schnittstelle/jurnodes-api-1.0.2.json").read_text(encoding="utf-8"))
    p._rechte_sammeln(daten["paths"])
    p._rechte_zeigen(Endpunkte())
    ausgabe = capsys.readouterr().out

    for recht in ("search:records", "read:records", "search:correspondence",
                  "read:folder", "download:file", "search:todo"):
        assert recht in ausgabe, f"{recht} fehlt in der Übersicht."
    assert "401" in ausgabe, "Der Leser muss den Bezug zum Status sehen."


def test_jede_anfrage_traegt_den_schluessel_auch_POST() -> None:
    """GET **und** POST — sonst antwortet der Server zu Recht mit 401.

    **Der Fehler vom 07.10.2026, und was er gekostet hat.** Die Probe hing den
    Schlüssel `X-Auth-Key` nur an `client.get` an; die Grundkopfzeilen des
    Clients tragen ihn nicht. Jeder `client.post` ging damit ohne Schlüssel
    hinaus.

    Im Lauf vom 07.10.2026 war genau ein POST dabei:
    `/correspondence/search`. Er bekam 401 „Authentifizierung ungültig", die
    sechs übrigen Aufrufe waren GET und antworteten mit 200. Daraus wurde
    geschlossen, dem Schlüssel fehle das Recht `search:correspondence` — und
    die Kanzlei bekam eine Aufgabe, die keine war. Der Server hatte die ganze
    Zeit recht: Ohne Schlüssel ist die Authentifizierung ungültig.

    Der Betrieb war nie betroffen: `http_adapter.py` gibt den Kopf bei GET und
    POST mit. Der Fehler lag allein im Prüfbogen — in dem Werkzeug, das
    Vertrauen schaffen soll.

    Geprüft wird über `VERFAHREN`, nicht über eine Liste in diesem Test: Kommt
    ein drittes Verfahren hinzu, fällt dieser Test, statt es durchzulassen.
    """
    p = _probe()
    gesehen: list[tuple[str, dict]] = []

    class _Client:
        def get(self, pfad, **kw):
            gesehen.append(("get", kw.get("headers") or {}))

        def post(self, pfad, **kw):
            gesehen.append(("post", kw.get("headers") or {}))

    client = _Client()
    p._schluessel_anhaengen(client, "DER-SCHLUESSEL")

    for verfahren in p.VERFAHREN:
        getattr(client, verfahren)("/correspondence/search", json={"a": 1})

    assert len(gesehen) == len(p.VERFAHREN), "Jedes Verfahren muss durchlaufen."
    for verfahren, kopf in gesehen:
        assert kopf.get("X-Auth-Key") == "DER-SCHLUESSEL", \
            f"{verfahren.upper()} ging ohne Schlüssel hinaus — das gibt 401."


def test_kein_post_umgeht_den_schluessel() -> None:
    """Jeder POST im Prüfbogen muss über den umhüllten Client laufen.

    Ein zweiter Client, direkt gebaut, oder ein `httpx.post(...)` am Modul
    vorbei hätte denselben stillen 401 zur Folge. Deshalb wird hier die
    Quelle gelesen, nicht nur das Verhalten.
    """
    quelle = Path("jusperfect/jurnodestest.py").read_text(encoding="utf-8")
    # Erlaubt ist allein client.post(...) - der Client, der umhüllt wurde.
    assert "httpx.post(" not in quelle, "Am umhüllten Client vorbei."
    assert "httpx.request(" not in quelle, "Am umhüllten Client vorbei."
    # Und es darf nur EINEN Client geben, der gebaut wird.
    assert quelle.count("httpx.Client(") == 1, \
        "Ein zweiter Client bekäme die Umhüllung nicht."


def test_ein_aktenzeichen_in_der_dateizeile_entwertet_den_lauf_nicht(capsys) -> None:
    """Eine Tippfehlerzeile darf keinen Lauf kosten.

    **Der Lauf vom 08.10.2026.** `JURNODES-PRUEFEN.bat` fragt zweimal
    hintereinander: erst nach dem Aktenzeichen, dann nach einer anderen
    Beschreibung. In die zweite Zeile wurde ein Aktenzeichen getippt — was
    naheliegt, wenn zwei Eingabezeilen untereinander stehen.

    Die Folge war still und teuer: Die Probe lief ohne Beschreibung weiter. Es
    fehlten die 85 Pfade, die Rechteübersicht und die Namen der
    Pflichtparameter — also gerade das, wofür der Lauf gemacht wird. Im
    Bericht stand davon eine einzige Zeile, drei Seiten weiter oben.

    Jetzt wird auf die beiliegende Datei zurückgefallen, und es steht dabei,
    warum.
    """
    p = _probe()
    p._beschreibung_aus_datei("X-102-2026", Endpunkte())
    ausgabe = capsys.readouterr().out

    assert "Die Datei gibt es nicht" in ausgabe
    assert "sieht nach einem Aktenzeichen aus" in ausgabe, \
        "Der Leser muss erfahren, WARUM die Datei fehlt."
    assert "Zeile DAVOR" in ausgabe, "Und wo das Aktenzeichen hingehört."
    # Und der Lauf hat die Beschreibung trotzdem.
    assert "85 Pfade stehen darin" in ausgabe, \
        "Ohne Rückfall verliert der Lauf seinen Zweck."
    assert "search:correspondence" in ausgabe, "Auch die Rechteübersicht."


def test_die_startdatei_trennt_die_beiden_fragen() -> None:
    """Zwei Eingabezeilen untereinander sind eine Falle — also nicht so.

    Die Startdatei nummeriert die Fragen und sagt bei der zweiten ausdrücklich,
    dass dort kein Aktenzeichen hingehört.
    """
    bat = (Path(__file__).resolve().parent.parent / "JURNODES-PRUEFEN.bat"
           ).read_bytes().decode("cp1252")

    assert "FRAGE 1 von 2" in bat and "FRAGE 2 von 2" in bat
    assert "HIER GEHOERT KEIN AKTENZEICHEN HIN" in bat
    # Und die Zeilenenden bleiben, wie cmd sie braucht: JEDES \n mit \r davor.
    # Ein nacktes \n laesst cmd ueber die Sprungmarken stolpern.
    assert "\n" in bat
    assert all(bat[i - 1] == "\r"
               for i, zeichen in enumerate(bat) if zeichen == "\n" and i), \
        "Eine Zeile endet ohne CRLF."
