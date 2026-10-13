"""Das Postfach wird nicht ausgelesen — und das steht jetzt in einer Prüfung.

**Vorgabe der Kanzlei, bestätigt am 12.10.2026:**

> „Alle E-Mails und Vermerke werden in der E-Akte abgespeichert. Es macht
> daher keinen Sinn und wäre sogar kontraproduktiv, wenn das Postfach
> ausgelesen wird, in welchem sich alle Akten befinden. Das Gleiche gilt für
> die beA-Eingänge."

Im Postfach liegt die Post **aller** Mandate des Hauses. Was zu einer Akte
gehört, liegt in ihrer E-Akte und dort vollständig. Ein Postfachzugriff
brächte nichts Neues und zugleich alles Fremde — ein Blick in Mandate, die
den Vorgang nichts angehen (§ 203 StGB).

**Warum diese Datei nötig war.** Die Regel galt seit dem 07.10.2026 und ruhte
auf einer Nachschau im Quelltext — also auf einem Blick, den jemand einmal
getan hat. Genau diese Art Lücke hat am 11.10.2026 eine zweite Meinung bei
der Seitenzählung gefunden: Das Programm war richtig, geprüft war es nicht.
Hier ist es umgekehrt noch teurer, denn ein Postfachaufruf fiele niemandem
auf — er brächte ja Daten zurück, nur die falschen.

**Was diese Prüfung nicht kann.** Bei `POST /mail/download` und `GET /bea`
entscheidet nicht der Aufruf, sondern das **Recht** am Schnittstellenbenutzer:
Die Beschreibung (API 1.0.2) nennt zu jedem beide Fassungen, `…:postbox` und
`…:record`. Dieselbe Zeile Quelltext holt also je nach Schlüssel eine Nachricht
aus der Akte oder eine aus dem Postfach. Das lässt sich am Client nicht
prüfen; es hängt daran, dass `download:mail:postbox`, `read:bea:postbox` und
`download:bea:postbox` **nicht gesetzt** sind. Das steht in
`schnittstelle/ANFRAGE-HERSTELLER.md` und ist Sache der Kanzlei.

Prüfbar ist, was hier steht: die drei Aufrufe, die **ausschließlich** das
Postfach betreffen, und die Postfachprotokolle überhaupt.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
QUELLE = WURZEL / "jusperfect"

#: Aufrufe, die es nur fuer das Postfach gibt - es gibt keine Fassung "je
#: Akte". Wer sie ruft, sieht die Post aller Mandate.
NUR_POSTFACH = (
    "/bea/postbox/search",      # listet die Postfaecher
    "/bea/folder/search",       # listet die Ordner eines Postfachs
    "/bea/search",              # sucht Nachrichten im Postfach
)

#: Postfachprotokolle. Das Programm spricht ausschliesslich mit der
#: jur|nodes-Schnittstelle; ein eigener Postfachzugang waere ein zweiter Weg
#: an der E-Akte vorbei.
PROTOKOLLE = ("imaplib", "smtplib", "poplib", "aiosmtplib", "exchangelib")


#: Die eine Datei, die diese Pfade nennen **muss** - weil sie sie verbietet.
#:
#: Befund N09 der dritten Zweitpruefung vom 12.10.2026: Das Verbot stand
#: allein in dieser Pruefdatei, also im Quelltext. Die Pfade sind aber
#: einstellbar (`JUSPERFECT_JURNODES_ENDPUNKTE`) - wer dort einen reinen
#: Postfachpfad eintrug, bekam ihn gesendet, und diese Pruefung blieb gruen.
#:
#: Seit dem 13.10.2026 steht das Verbot im Programm: `Endpunkte.NUR_POSTFACH`
#: und `postfach_ausschliessen()`. Damit nennt `http_adapter.py` die drei
#: Pfade - dasselbe Muster wie bei der Datei des Herstellers, die selbst einen
#: gesperrten Namen fuehrt. Statt der Textsuche prueft `DieVorgabeIstSauber`
#: unten, was in den Pfaden tatsaechlich **eingestellt** ist.
VERBIETET_SIE = {"http_adapter.py"}


def _python_dateien() -> list[Path]:
    return [p for p in QUELLE.rglob("*.py") if "__pycache__" not in p.parts]


class DasProgrammRuftKeinenPostfachAufruf(unittest.TestCase):

    def test_die_drei_reinen_postfachaufrufe_stehen_nirgends(self):
        for pfad in _python_dateien():
            if pfad.name in VERBIETET_SIE:
                continue
            text = pfad.read_text(encoding="utf-8")
            for aufruf in NUR_POSTFACH:
                with self.subTest(datei=pfad.name, aufruf=aufruf):
                    self.assertNotIn(
                        f'"{aufruf}"', text,
                        f"{pfad.relative_to(WURZEL)} nennt {aufruf}. Dieser Aufruf "
                        "gibt es nur fuer das Postfach, in dem die Post aller "
                        "Mandate liegt.")
                    self.assertNotIn(f"'{aufruf}'", text)

    def test_kein_eigener_postfachzugang(self):
        """Kein IMAP, kein SMTP — gesprochen wird nur mit jur|nodes."""
        for pfad in _python_dateien():
            text = pfad.read_text(encoding="utf-8")
            for modul in PROTOKOLLE:
                with self.subTest(datei=pfad.name, modul=modul):
                    self.assertIsNone(
                        re.search(rf"^\s*(import|from)\s+{modul}\b", text, re.M),
                        f"{pfad.relative_to(WURZEL)} bindet {modul} ein.")


class DieBeschreibungStuetztDieseRegel(unittest.TestCase):
    """Gemessen an der Datei des Herstellers, nicht an einem Nachbau.

    Zwei Dinge sollen feststehen: dass die drei Aufrufe oben wirklich nur das
    Postfach kennen, und dass die beiden benutzten Aufrufe wirklich zweierlei
    Recht führen. Ändert der Hersteller das, soll es hier auffallen und nicht
    an einer echten Akte.
    """

    @classmethod
    def setUpClass(cls):
        datei = WURZEL / "schnittstelle" / "jurnodes-api-1.0.2.json"
        cls.pfade = json.loads(datei.read_text(encoding="utf-8"))["paths"]

    def _beschreibung(self, pfad: str, verb: str) -> str:
        return (self.pfade[pfad][verb].get("description") or "")

    def test_die_drei_aufrufe_gibt_es_und_sie_meinen_das_postfach(self):
        """Der Hersteller sagt es in jedem der drei Sätze selbst.

        „Listet alle hinterlegten beA-Postfächer auf", „alle Ordner eines
        beA-Postfachs", „alle beA-Nachrichten eines beA-Postfaches in einem
        bestimmten Ordner". Keiner der drei kennt eine Fassung je Akte — die
        beA-Nachricht einer Akte kommt über das Korrespondenzverzeichnis und
        `GET /bea?beaIdentifier=…`, nicht über eine Postfachsuche.
        """
        for aufruf in NUR_POSTFACH:
            with self.subTest(aufruf=aufruf):
                self.assertIn(aufruf, self.pfade, "Aufruf aus 1.0.2 verschwunden?")
                satz = self._beschreibung(aufruf, "get").lower()
                self.assertTrue("postbox" in satz or "postfach" in satz,
                                f"Beschreibung nennt kein Postfach mehr: {satz!r}")
                self.assertNotIn("record", satz,
                                 "Gibt es jetzt doch eine Fassung je Akte?")

    def test_bei_mail_und_bea_entscheidet_das_recht_und_nicht_der_aufruf(self):
        """Derselbe Aufruf, zwei Rechte — deshalb schützt kein Quelltext davor."""
        for pfad, verb in (("/mail/download", "post"), ("/bea", "get")):
            with self.subTest(pfad=pfad):
                b = self._beschreibung(pfad, verb)
                self.assertIn("postbox", b, "Die Postfachfassung ist weggefallen?")
                self.assertIn("record", b, "Die Aktenfassung ist weggefallen?")


class DieVorgabeStehtInDenUnterlagen(unittest.TestCase):
    """Damit sie beim nächsten Schlüssel nicht neu erfunden werden muss."""

    def test_die_anfrage_nennt_die_postfachrechte_als_nicht_zu_setzen(self):
        text = (WURZEL / "schnittstelle" / "ANFRAGE-HERSTELLER.md").read_text(
            encoding="utf-8")
        for recht in ("download:mail:postbox", "read:bea:record",
                      "download:bea:record"):
            self.assertIn(recht, text)
        self.assertIn("in welchem sich alle Akten befinden", text,
                      "Der Grund gehört dazu, nicht nur die Regel.")


class DieVorgabeIstSauber(unittest.TestCase):
    """Was eingestellt **ist**, nicht was im Quelltext steht — Befund N09."""

    def test_kein_vorgabepfad_fuehrt_in_ein_postfach(self):
        from dataclasses import fields

        from jusperfect.jurnodes.http_adapter import Endpunkte

        vorgabe = Endpunkte()
        for feld in fields(vorgabe):
            wert = getattr(vorgabe, feld.name)
            if not isinstance(wert, str):
                continue
            with self.subTest(feld=feld.name):
                self.assertNotIn("postbox", wert.lower())
                self.assertNotIn("/" + wert.strip().strip("/").lower(), NUR_POSTFACH)

    def test_das_programm_fuehrt_dieselbe_liste(self):
        """Zwei Listen, die auseinanderlaufen, sind schlimmer als eine."""
        from jusperfect.jurnodes.http_adapter import Endpunkte

        self.assertEqual(set(NUR_POSTFACH), set(Endpunkte.NUR_POSTFACH))

    def test_ein_eingestellter_postfachpfad_wird_abgewiesen(self):
        from jusperfect.config import KonfigurationsFehler
        from jusperfect.jurnodes.http_adapter import Endpunkte

        for pfad in ("/bea/postbox/search", "bea/search", "/BEA/Folder/Search",
                     "/mail/postbox/download"):
            with self.subTest(pfad=pfad):
                with self.assertRaises(KonfigurationsFehler) as fehler:
                    Endpunkte(akten_suche=pfad).postfach_ausschliessen("einer Probe")
                self.assertIn("Postfach", str(fehler.exception))

    def test_auch_der_adapter_prueft_beim_bauen(self):
        """Nicht nur die Datei: Der Satz Pfade, mit dem gesprochen wird."""
        import httpx

        from jusperfect.config import KonfigurationsFehler
        from jusperfect.jurnodes.http_adapter import Endpunkte, HttpJurNodesAdapter
        from jusperfect.security.approval import Freigabestelle

        böse = Endpunkte.__new__(Endpunkte)      # ohne die Pruefung im Konstruktor
        object.__setattr__(böse, "__dict__", dict(Endpunkte().__dict__))
        with self.assertRaises(KonfigurationsFehler):
            HttpJurNodesAdapter(
                "https://beispiel.invalid", "k", Freigabestelle(),
                transport=httpx.MockTransport(
                    lambda a: httpx.Response(200, json={})),
                benutzer="u",
                endpunkte=Endpunkte(akten_suche="/bea/postbox/search"))

    def test_eine_datei_mit_postfachpfad_wird_abgewiesen(self, ):
        """Der Weg, auf dem es tatsaechlich hereinkaeme."""
        import json as _json
        import tempfile

        from jusperfect.config import KonfigurationsFehler
        from jusperfect.jurnodes.http_adapter import Endpunkte

        with tempfile.TemporaryDirectory() as ordner:
            datei = Path(ordner) / "endpunkte.json"
            datei.write_text(_json.dumps({"akten_suche": "/bea/search"}),
                             encoding="utf-8")
            with self.assertRaises(KonfigurationsFehler) as fehler:
                Endpunkte.aus_datei(datei)
            self.assertIn("Postfach", str(fehler.exception))


class GemessenAmTatsaechlichenAufruf(unittest.TestCase):
    """Nicht am Quelltext, nicht an der Einstellung — am Transport.

    Die Empfehlung des Prüfers, wörtlich: *„Eine Zusage braucht einen Test am
    tatsächlichen Ausgang."* Hier läuft der echte Adapter gegen einen
    Ersatz-Transport, der jeden Pfad mitschreibt, den er wirklich bekommt.
    """

    def _gefragt(self) -> list[str]:
        import httpx

        from jusperfect.jurnodes.http_adapter import HttpJurNodesAdapter
        from jusperfect.security.approval import Freigabestelle

        pfade: list[str] = []

        def server(anfrage: httpx.Request) -> httpx.Response:
            pfade.append(anfrage.url.path)
            if anfrage.url.path.endswith("/record"):
                return httpx.Response(200, json={"identifier": "rec-1",
                                                 "fileFolderId": 7})
            return httpx.Response(200, json={"elements": [], "pagesTotal": 1})

        adapter = HttpJurNodesAdapter(
            "https://beispiel.invalid", "k", Freigabestelle(),
            transport=httpx.MockTransport(server), benutzer="u",
            korrespondenz=True)
        adapter.akten_suchen("")
        adapter.dokumente("rec-1")
        adapter.beteiligte("rec-1")
        adapter.fristen("rec-1")
        return pfade

    def test_kein_aufruf_geht_an_ein_postfach(self):
        pfade = self._gefragt()
        self.assertTrue(pfade, "Es wurde gar nichts gefragt — dann prüft das nichts.")
        for pfad in pfade:
            with self.subTest(pfad=pfad):
                self.assertNotIn("postbox", pfad.lower())
                self.assertNotIn(pfad.lower(), NUR_POSTFACH)

    def test_gefragt_wird_nur_was_erwartet_ist(self):
        """Eine Positivliste: Ein neuer Aufruf soll hier auffallen."""
        erlaubt = {"/record/search", "/record", "/file-system/folder/content",
                   "/relation/search", "/todo/search", "/correspondence/search"}
        unerwartet = sorted({p for p in self._gefragt()} - erlaubt)
        self.assertEqual([], unerwartet,
                         "Das Programm fragt einen Pfad, der hier nicht steht.")
