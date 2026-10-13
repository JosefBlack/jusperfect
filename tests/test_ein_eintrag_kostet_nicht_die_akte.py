"""Ein kaputter Eintrag kostet nicht die ganze Akte.

Aus der Kanzlei am 13.10.2026: „Zip heruntergeladen, Akte öffnen nicht möglich
Vorgang wurde abgebrochen interner Fehler 2e2e3bd1."

Der Satz heißt: eine Ausnahme, die keinem bekannten Fehlertyp entspricht, also
ein Programmfehler. Beim **Laden** eines Dokuments war die Lehre längst
gezogen – aus der Kanzlei am 25.09.2026: „es wird auch immer nur ein Dokument
in das Aktengedaechtnis uebernommen", weil das erste durchging, beim zweiten
der Adapter warf und die Schleife abbrach. Seitdem hat jedes Dokument dort
seinen eigenen Versuch.

**Beim Aufbauen der Liste nicht.** Dort riss ein einziger Eintrag, an dem etwas
unerwartet war, das Öffnen der ganzen Akte mit: 54 von 55 Dokumenten in
Ordnung und keines davon zu sehen. Dieselbe Lehre, dieselbe Datei, andere
Schleife – und niemand hatte sie dort gesucht.

Was ein ausgefallener Eintrag hinterlässt, ist **sichtbar**: eine Zahl und die
Ausnahmekette (Typen und Codestellen, kein Wortlaut, keine Aktenkennung). Der
Bearbeiter kann sie weitergeben, ohne das schwarze Fenster zu lesen.
"""

from __future__ import annotations

import json
import unittest

import httpx

from unittest import mock

from jusperfect.jurnodes import http_adapter
from jusperfect.jurnodes.http_adapter import VERMERK_VORSATZ
from tests.test_eakte import AKTE, _Server, _adapter, _eintrag, _eml

#: Diese Bytes bringen das Zerlegen zum Platzen - siehe `_sprengsatz`.
#:
#: Erfundenes Unheil und mit Absicht: Welche echte .eml das Zerlegen zum
#: Platzen bringt, weiss hier niemand - der Fall aus der Kanzlei ist noch
#: nicht gelesen. Die Zusage lautet auch nicht "diese eine Mail haelt",
#: sondern "ein Eintrag, an dem IRGENDETWAS unerwartet ist, kostet nicht die
#: Akte". Dafuer braucht die Pruefung eine Ausnahme, die sie selbst setzt.
SPRENG = b"SPRENG"


def _sprengsatz():
    """`zerlegen`, aber es wirft bei SPRENG - sonst arbeitet es wie immer."""
    echtes = http_adapter.zerlegen

    def zerlegen(roh):
        if roh.startswith(SPRENG):
            raise RuntimeError("erfundenes Unheil beim Zerlegen")
        return echtes(roh)

    return mock.patch.object(http_adapter, "zerlegen", zerlegen)


class _ServerMitEinerKaputtenMail(_Server):
    """Eine von zwei Mails ist keine Mail, sondern Unrat."""

    def __call__(self, anfrage: httpx.Request) -> httpx.Response:
        if anfrage.url.path.endswith("/mail/download"):
            kennung = json.loads(anfrage.content or b"{}").get("mailIdentifier")
            if kennung == "kaputt":
                # Antwortet mit ERFOLG und liefert etwas, an dem das Zerlegen
                # scheitert. Der gefaehrlichere Fall: Ein Fehlerstatus waere
                # behandelt - diese Mail sieht in Ordnung aus.
                return httpx.Response(
                    200, content=SPRENG,
                    headers={"content-type": "application/octet-stream"})
        return super().__call__(anfrage)


def _zwei_mails(kaputt_zuerst: bool):
    gut = _eintrag("mail", referenceMail="gut", subject="Gute Mail")
    schlecht = _eintrag("mail", referenceMail="kaputt", subject="Kaputte Mail")
    schlecht["identifier"] = "c-mail-2"
    return [schlecht, gut] if kaputt_zuerst else [gut, schlecht]


class DieUebrigenBleiben(unittest.TestCase):
    def test_die_gute_mail_kommt_auch_wenn_die_kaputte_zuerst_steht(self):
        """Die Reihenfolge entschied früher über die ganze Akte."""
        for zuerst in (True, False):
            with self.subTest(kaputt_zuerst=zuerst):
                server = _ServerMitEinerKaputtenMail(
                    _zwei_mails(zuerst), mails={"gut": _eml("Guter Text")})
                adapter = _adapter(server)
                with _sprengsatz():
                    dokumente = adapter.dokumente(AKTE)
                titel = [d.titel for d in dokumente]
                self.assertTrue(any("Gute Mail" in x for x in titel), titel)
                self.assertFalse(any("Kaputte Mail" in x for x in titel), titel)

    def test_die_vermerke_bleiben_ebenso(self):
        server = _ServerMitEinerKaputtenMail(
            _zwei_mails(True) + [_eintrag("note", referenceNote=17)],
            vermerke={"17": {"id": 17, "type": "memo", "content": "Ein Vermerk.",
                             "contentType": "text", "record": AKTE}},
            mails={"gut": _eml("Guter Text")})
        with _sprengsatz():
            dokumente = _adapter(server).dokumente(AKTE)
        self.assertTrue([d for d in dokumente if d.id.startswith(VERMERK_VORSATZ)])

    def test_ohne_die_absicherung_waere_die_akte_verloren(self):
        """Die Gegenprobe: genau dieser Fall war der Abbruch vom 13.10.2026."""
        server = _ServerMitEinerKaputtenMail(_zwei_mails(True),
                                             mails={"gut": _eml("Guter Text")})
        adapter = _adapter(server)
        with _sprengsatz(), \
             mock.patch.object(type(adapter), "_eintrag_gescheitert",
                               side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                adapter.dokumente(AKTE)


class DasFehlenIstSichtbar(unittest.TestCase):
    """Ein Ausfall, den niemand sieht, ist schlimmer als ein Abbruch."""

    def _adapter_mit_ausfall(self):
        server = _ServerMitEinerKaputtenMail(
            _zwei_mails(True), mails={"gut": _eml("Guter Text")})
        adapter = _adapter(server)
        with _sprengsatz():
            adapter.dokumente(AKTE)
        return adapter

    def test_er_wird_gezaehlt(self):
        adapter = self._adapter_mit_ausfall()
        self.assertEqual(sum(adapter.letzte_eintraege_mit_fehler.values()), 1,
                         adapter.letzte_eintraege_mit_fehler)

    def test_die_kette_nennt_art_und_stelle(self):
        adapter = self._adapter_mit_ausfall()
        kette = next(iter(adapter.letzte_eintraege_mit_fehler))
        self.assertIn(".py:", kette, kette)
        self.assertRegex(kette, r"[A-Za-z]+Error|Exception|[A-Za-z]+Fehler")

    def test_in_der_kette_steht_keine_aktenkennung(self):
        adapter = self._adapter_mit_ausfall()
        for kette in adapter.letzte_eintraege_mit_fehler:
            self.assertNotIn(AKTE, kette)
            self.assertNotIn("kaputt", kette)

    def test_derselbe_fehler_an_fuenf_eintraegen_ist_ein_befund(self):
        """Sonst stünde fünfmal dasselbe in der Anzeige."""
        eintraege = []
        for nr in range(5):
            e = _eintrag("mail", referenceMail="kaputt")
            e["identifier"] = f"c-mail-{nr}"
            eintraege.append(e)
        server = _ServerMitEinerKaputtenMail(eintraege)
        adapter = _adapter(server)
        with _sprengsatz():
            adapter.dokumente(AKTE)
        self.assertEqual(len(adapter.letzte_eintraege_mit_fehler), 1)
        self.assertEqual(sum(adapter.letzte_eintraege_mit_fehler.values()), 5)

    def test_bei_einer_heilen_akte_bleibt_er_leer(self):
        """Eine Warnung an jeder Akte wäre keine Warnung."""
        server = _Server([_eintrag("mail", referenceMail="gut")],
                         mails={"gut": _eml("Guter Text")})
        adapter = _adapter(server)
        adapter.dokumente(AKTE)
        self.assertEqual(adapter.letzte_eintraege_mit_fehler, {})

    def test_der_zaehler_wird_bei_jedem_lesen_neu_gesetzt(self):
        """Sonst trüge die nächste Akte den Ausfall der vorigen."""
        adapter = self._adapter_mit_ausfall()
        self.assertTrue(adapter.letzte_eintraege_mit_fehler)
        adapter._client = httpx.Client(
            base_url="https://beispiel.invalid",
            transport=httpx.MockTransport(_Server()))
        adapter._puffer_leeren()
        adapter.dokumente(AKTE)
        self.assertEqual(adapter.letzte_eintraege_mit_fehler, {})


class DieAnzeigeSagtEs(unittest.TestCase):
    """Eine Zahl, die nur im Adapter steht, ist keine Zahl (Befund N04)."""

    @classmethod
    def setUpClass(cls) -> None:
        from pathlib import Path
        statisch = Path(__file__).resolve().parent.parent / "jusperfect" / "static"
        cls.js = (statisch / "app.js").read_text(encoding="utf-8")
        cls.web = (Path(__file__).resolve().parent.parent
                   / "jusperfect" / "web.py").read_text(encoding="utf-8")

    def test_die_schnittstelle_gibt_sie_heraus(self):
        self.assertIn('"eintraege_mit_fehler"', self.web)
        self.assertIn("letzte_eintraege_mit_fehler", self.web)

    def test_die_oberflaeche_zeigt_sie(self):
        self.assertIn("eintraege_mit_fehler", self.js)
        self.assertIn("fehlen in der Liste", self.js)


if __name__ == "__main__":
    unittest.main()
