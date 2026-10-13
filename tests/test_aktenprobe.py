"""Die Aktenprobe: Welcher Eintrag lässt sich nicht lesen?

Seit dem 13.10.2026 kostet ein einzelner Eintrag nicht mehr die ganze Akte.
Damit ist die Akte benutzbar – **welcher** Eintrag ausgefallen ist, sagt die
Anzeige nur als Ausnahmekette. Diese Probe nennt die Stelle: Eintrag für
Eintrag, mit Art, Richtung und Datum.

Geprüft wird hier beides: dass sie den kaputten Eintrag findet **und** dass
ihre Ausgabe weitergegeben werden darf – kein Betreff, kein Dateiname, kein
Aktenzeichen im Klartext.
"""

from __future__ import annotations

import io
import unittest

import httpx
from contextlib import redirect_stdout
from unittest import mock

from jusperfect import aktenprobe
from tests.test_eakte import AKTE, _Server, _adapter, _eintrag, _eml
from tests.test_ein_eintrag_kostet_nicht_die_akte import (
    _ServerMitEinerKaputtenMail, _sprengsatz, _zwei_mails)

#: Erfundener Betreff, der aussieht wie Akteninhalt. Er darf nirgends stehen.
#:
#: Erfunden heisst: nachgesehen. Der erste Entwurf dieser Zeile trug den Namen
#: eines echten Versicherers aus einer echten Akte - die zwoelfte Wiederholung
#: desselben Fehlers, und die zweite an einem Tag, die SPERRLISTE-PRUEFEN.bat
#: gefunden hat und nicht ich.
BETREFF = "Zeisig ./. Nordwacht Versicherung - Schmerzensgeld 8.400 EUR"


class _ServerVollstaendig(_Server):
    """Wie `_Server`, antwortet aber auch auf Beteiligte und Fristen.

    `_Server` liess beides offen - fuer die Pruefungen der E-Akte brauchte es
    das nicht. Die Aktenprobe geht denselben Weg wie das Oeffnen und fragt
    deshalb auch danach; ohne Antwort stuenden hier zwei Fehlschlaege, die
    nichts mit dem Programm zu tun haben.
    """

    def __call__(self, anfrage):
        pfad = anfrage.url.path
        if pfad.endswith("/relation/search") or pfad.endswith("/todo/search"):
            self.gefragt.append(f"{anfrage.method} {pfad}")
            return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
        return super().__call__(anfrage)


def _lauf(adapter, akte=AKTE) -> tuple[int, str]:
    puffer = io.StringIO()
    with redirect_stdout(puffer):
        ergebnis = aktenprobe.main(["--akte", akte], adapter=adapter)
    return ergebnis, puffer.getvalue()


class EineHeileAkte(unittest.TestCase):
    def setUp(self) -> None:
        self.server = _ServerVollstaendig(
            [_eintrag("mail", referenceMail="gut", subject=BETREFF),
             _eintrag("note", referenceNote=17, subject=BETREFF)],
            vermerke={"17": {"id": 17, "type": "memo", "content": "Ein Vermerk.",
                             "contentType": "text", "record": AKTE}},
            mails={"gut": _eml("Guter Text", betreff=BETREFF)})
        self.ergebnis, self.ausgabe = _lauf(_adapter(self.server))

    def test_sie_sagt_ja(self):
        self.assertEqual(self.ergebnis, 0, self.ausgabe)
        self.assertIn("keiner gescheitert", self.ausgabe)

    def test_sie_nennt_art_richtung_und_tag(self):
        self.assertIn("mail", self.ausgabe)
        self.assertIn("note", self.ausgabe)
        self.assertIn("Eingang", self.ausgabe)
        self.assertIn("2026-05-04", self.ausgabe)

    def test_in_der_ausgabe_steht_kein_akteninhalt(self):
        """Diese Ausgabe wird verschickt."""
        self.assertNotIn(BETREFF, self.ausgabe)
        self.assertNotIn("Zeisig", self.ausgabe)
        self.assertNotIn("Nordwacht", self.ausgabe)
        self.assertNotIn("Guter Text", self.ausgabe)
        self.assertNotIn("Ein Vermerk", self.ausgabe)

    def test_das_aktenzeichen_steht_nur_verdeckt(self):
        self.assertNotIn(AKTE, self.ausgabe)
        self.assertIn(aktenprobe.verdeckt(AKTE), self.ausgabe)


class EineAkteMitEinemKaputtenEintrag(unittest.TestCase):
    def setUp(self) -> None:
        server = _ServerMitEinerKaputtenMail(_zwei_mails(True),
                                             mails={"gut": _eml("Guter Text")})
        with _sprengsatz():
            self.ergebnis, self.ausgabe = _lauf(_adapter(server))

    def test_sie_sagt_nein(self):
        self.assertEqual(self.ergebnis, 1, self.ausgabe)

    def test_sie_nennt_die_stelle(self):
        """Die Nummer des Eintrags - danach lässt er sich in jur|nodes finden."""
        self.assertRegex(self.ausgabe, r"\[\d+\] mail")
        self.assertIn("✗", self.ausgabe)

    def test_sie_nennt_die_kette_zum_weitergeben(self):
        self.assertIn("RuntimeError", self.ausgabe)
        self.assertIn("weitergeben", self.ausgabe)

    def test_der_wortlaut_der_ausnahme_geht_nicht_hinaus(self):
        """Er kann ein Stück der Akte enthalten - wie bei AWS."""
        self.assertNotIn("erfundenes Unheil", self.ausgabe)

    def test_die_heile_mail_steht_als_gelesen_daneben(self):
        """Sonst wüsste niemand, ob nur eine oder alle betroffen sind."""
        self.assertIn("✓", self.ausgabe)
        self.assertIn("Dokument(e) daraus", self.ausgabe)


class SieSchreibtNichtsUndLiestKeinGedaechtnis(unittest.TestCase):
    def test_kein_schreibender_aufruf_an_den_server(self):
        server = _ServerVollstaendig(
            [_eintrag("note", referenceNote=17)],
            vermerke={"17": {"id": 17, "type": "memo", "content": "x",
                             "contentType": "text", "record": AKTE}})
        _lauf(_adapter(server))
        for aufruf in server.gefragt:
            verfahren = aufruf.split(" ")[0]
            self.assertIn(verfahren, ("GET", "POST"), aufruf)
            self.assertNotIn("PUT", aufruf)
            self.assertNotIn("DELETE", aufruf)
        # POST gibt es nur lesend - die Suche. Dieselbe Erwaegung wie im
        # Pruefbogen der Schnittstelle.
        posts = [a for a in server.gefragt if a.startswith("POST")]
        for aufruf in posts:
            self.assertTrue("search" in aufruf or "download" in aufruf, aufruf)

    def test_der_dokumentinhalt_wird_nicht_geholt(self):
        """Das Laden kostet Texterkennung. Die Probe lädt nicht."""
        server = _ServerVollstaendig(
            [_eintrag("note", referenceNote=17)],
            vermerke={"17": {"id": 17, "type": "memo", "content": "x",
                             "contentType": "text", "record": AKTE}})
        _lauf(_adapter(server))
        self.assertNotIn("GET /record/note", server.gefragt,
                         "Der Inhalt eines Vermerks gehört zum Laden, nicht zum Öffnen.")

    def test_sie_kommt_ohne_gedaechtnis_aus(self):
        """Sie muss arbeiten, wenn gerade das Gedächtnis das Problem ist."""
        quelle = (aktenprobe.__file__)
        with open(quelle, encoding="utf-8") as datei:
            text = datei.read()
        kopf = text[:text.index("from __future__")]
        self.assertIn("Aktengedächtnis wird nicht einmal gelesen", kopf)
        self.assertNotIn("gedaechtnis.lesen", text)
        self.assertNotIn("Gedaechtnisdienst", text)


class DerAufrufIstDa(unittest.TestCase):
    def test_die_startdatei_ruft_das_modul(self):
        from pathlib import Path

        roh = (Path(__file__).resolve().parent.parent / "AKTE-PRUEFEN.bat").read_bytes()
        self.assertIn(b"jusperfect.aktenprobe", roh)
        self.assertIn(b"\r\n", roh, "Windows liest eine Datei ohne CR nicht gern.")
        self.assertEqual(roh.count(b"\n"), roh.count(b"\r\n"), "Keine nackten LF.")


if __name__ == "__main__":
    unittest.main()


class DerSatzDesServersGehoertDazu(unittest.TestCase):
    """„JurNodesFehler (http_adapter.py:821)" sagt nicht, WELCHER Aufruf.

    Aus der Kanzlei am 13.10.2026, nach dem ersten Lauf dieser Probe:

        3× jusperfect.jurnodes.base.JurNodesFehler (http_adapter.py:821)
        1× jusperfect.jurnodes.base.JurNodesFehler (http_adapter.py:899)

    Zwei Zeilen, und beide beantworten die Frage nicht: An 821 steht „GET mit
    Status …", an 899 dasselbe für POST – welcher Pfad und welcher Status, das
    steht im **Satz** des Fehlers, und den hatte ich weggelassen.

    Er darf dastehen: Diese Sätze schreiben wir selbst, sie nennen einen fest
    verdrahteten Pfad und eine Zahl. Was sie doch tragen können, ist die
    Aktenkennung – die wird verdeckt.
    """

    def _lauf_mit_fehler(self, fehler):
        class _Kaputt(_ServerVollstaendig):
            def __call__(self, anfrage):
                if anfrage.url.path.endswith("/correspondence/search"):
                    return httpx.Response(405, json={})
                return super().__call__(anfrage)

        return _lauf(_adapter(_Kaputt()))

    def test_der_pfad_und_der_status_stehen_da(self):
        _, ausgabe = self._lauf_mit_fehler(None)
        self.assertIn("/correspondence/search", ausgabe)
        self.assertIn("405", ausgabe)

    def test_die_codestelle_steht_weiter_daneben(self):
        """Der Satz sagt, WAS der Server antwortete; die Kette, WO es brach."""
        _, ausgabe = self._lauf_mit_fehler(None)
        self.assertIn("JurNodesFehler", ausgabe)
        self.assertIn("http_adapter.py:", ausgabe)

    def test_eine_aktenkennung_im_satz_wird_verdeckt(self):
        from jusperfect.jurnodes.base import AkteNichtGefunden

        from jusperfect import aktenprobe as ap

        satz = ap._satz(AkteNichtGefunden(f"Akte {AKTE} nicht gefunden."), AKTE)
        self.assertNotIn(AKTE, satz)
        self.assertIn(ap.verdeckt(AKTE), satz)

    def test_ein_unerwarteter_fehler_bekommt_keinen_satz(self):
        """Sein Wortlaut ist von niemandem geprüft und kann Akteninhalt tragen."""
        from jusperfect import aktenprobe as ap

        self.assertEqual(ap._satz(ValueError("Mandantin X, 8.400 EUR"), AKTE), "")
