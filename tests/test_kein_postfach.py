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


def _python_dateien() -> list[Path]:
    return [p for p in QUELLE.rglob("*.py") if "__pycache__" not in p.parts]


class DasProgrammRuftKeinenPostfachAufruf(unittest.TestCase):

    def test_die_drei_reinen_postfachaufrufe_stehen_nirgends(self):
        for pfad in _python_dateien():
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
