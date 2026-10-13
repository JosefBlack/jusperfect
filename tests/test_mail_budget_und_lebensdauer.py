"""Das Byte-Konto einer Akte und die Lebensdauer des Mailpuffers.

Befunde **N06** und **N10** der dritten Zweitprüfung vom 12.10.2026. Zwei
Befunde, ein gemeinsamer Satz: **Der Mailpuffer war ein Zustand ohne
Verwaltung.**

**N06 — die 100-MB-Grenze war keine Obergrenze.** `verbraucht` war eine
örtliche Zählung in `_mail_dokumente` und begann bei jedem Aufbau der
Dokumentliste wieder bei null. Wer die Liste zweimal aufbaute, holte zweimal
100 MB. Die letzte Mail wurde außerdem **voll** übernommen, auch wenn sie den
Rest überschritt. Und `dokument_laden()` holte eine wegen des Budgets
ausgelassene Mail über `_mail_teil()` **ohne jede Prüfung** nach — die Warnung
in ihrer Zeile und die tatsächliche Verfügbarkeit widersprachen einander.

**N10 — der Puffer überlebte den Sitzungsschluss.** Der Adapter hielt
zerlegte Mailtexte und Anlagen als Python-Objekte außerhalb des
Sitzungsspeichers, auch die von Mails, die beim Aufbau der Liste geholt und
nie ausgewählt wurden. Weder der Sitzungsschluss noch `_puffer_leeren()` noch
`schliessen()` entfernten sie; geleert wurde allein beim Wechsel der Akte.

> Ein gezielter Löschvorgang kann sich nicht auf den Sitzungsspeicher
> beschränken, wenn daneben neue Inhaltskopien bestehen.

**Was hier bewusst nicht behauptet wird:** `clear()` ist logisches Entfernen,
keine garantierte Nullung von Python-Speicher. Der Prozessspeicher, die
Auslagerungsdatei und ein Absturzabbild sind davon unberührt; das gehört in
die technische Datenschutzbeschreibung und nicht in eine Zusage dieser Datei.
"""

from __future__ import annotations

import time
import unittest
from email.message import EmailMessage

import httpx

from jusperfect.jurnodes.base import DokumentNichtGefunden
from jusperfect.jurnodes.http_adapter import (
    MAIL_VORSATZ, HttpJurNodesAdapter,
)
from jusperfect.security.approval import Freigabestelle

AKTE = "rec-1"


def _eml(fuellung: int = 0, text: str = "Ein Brieftext.") -> bytes:
    """Eine ``.eml`` mit einer Anlage der gewünschten Größe."""
    m = EmailMessage()
    m["Subject"] = "Ein Betreff"
    m["From"] = "gegner@example.invalid"
    m["Date"] = "Wed, 08 Oct 2026 09:14:00 +0200"
    m.set_content(text)
    if fuellung:
        m.add_attachment(b"%PDF-1.4" + b"x" * fuellung, maintype="application",
                         subtype="pdf", filename="Anlage.pdf")
    return m.as_bytes()


class _Server:
    """Ein erfundener jur|nodes-Server mit zählbaren Maildownloads."""

    def __init__(self, mails: dict[str, bytes], laenge_nennen: bool = True):
        self.mails = dict(mails)
        self.laenge_nennen = laenge_nennen
        self.downloads: list[str] = []

    def __call__(self, anfrage: httpx.Request) -> httpx.Response:
        import json as _json

        pfad = anfrage.url.path
        if pfad.endswith("/correspondence/search"):
            if "page" in str(anfrage.content or b"") and b'"page": 2' in (anfrage.content or b""):
                return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
            return httpx.Response(200, json={
                "elements": [{"identifier": f"c-{k}", "subject": f"Mail {k}",
                              "type": "mail", "isInbox": 1, "referenceMail": k,
                              "created": "2026-05-04T09:00:00"}
                             for k in self.mails],
                "pagesTotal": 1})
        if pfad.endswith("/mail/download"):
            kennung = _json.loads(anfrage.content or b"{}").get("mailIdentifier")
            roh = self.mails.get(kennung)
            if roh is None:
                return httpx.Response(404, json={})
            self.downloads.append(kennung)
            kopf = {"content-type": "application/octet-stream"}
            if not self.laenge_nennen:
                # Ohne Content-Length muss mitgezaehlt werden - der Fall, in
                # dem die Grenze erst beim Stroemen greift.
                return httpx.Response(200, content=roh, headers=kopf)
            return httpx.Response(200, content=roh, headers=kopf)
        if pfad.endswith("/record"):
            # Die ANGEFRAGTE Akte zurueckgeben: Die Pruefung aus Befund F08
            # weist eine Antwort ab, die eine andere nennt - zu Recht.
            gefragt = anfrage.url.params.get("identifier") or AKTE
            return httpx.Response(200, json={"identifier": gefragt,
                                             "fileFolderId": 7})
        if "folder/content" in pfad:
            return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
        return httpx.Response(200, json={})


def _adapter(server: _Server, grenze: int, gesamt: int) -> HttpJurNodesAdapter:
    """Mit verkleinerten Byte-Grenzen — sonst bräuchte die Prüfung 100-MB-Dateien."""
    adapter = HttpJurNodesAdapter(
        "https://beispiel.invalid", "k", Freigabestelle(),
        transport=httpx.MockTransport(server), benutzer="u", korrespondenz=True)
    adapter._mail_grenze = grenze
    adapter._mail_gesamt = gesamt
    return adapter


class DasKontoGiltUeberAlleAufrufe(unittest.TestCase):
    """N06, der Kern."""

    def test_der_zweite_listenaufbau_holt_nicht_noch_einmal(self):
        """Hier lag der Befund: Die Zählung begann jedes Mal bei null."""
        server = _Server({"m1": _eml(2000), "m2": _eml(2000), "m3": _eml(2000)})
        adapter = _adapter(server, grenze=5000, gesamt=5000)
        adapter.dokumente(AKTE)
        erster = list(server.downloads)
        adapter.dokumente(AKTE)
        self.assertEqual(erster, server.downloads,
                         "Beim zweiten Aufbau wurde erneut geholt.")

    def test_was_ueber_dem_gesamtmass_liegt_bleibt_draussen(self):
        """Gemessen am Konto, nicht an der Zahl der Anfragen: Eine Mail, die
        nicht hineinpasst, wird an der Kopfzeile abgebrochen — die Anfrage
        ging hinaus, ihre Bytes nicht."""
        server = _Server({"m1": _eml(2000), "m2": _eml(2000), "m3": _eml(2000)})
        adapter = _adapter(server, grenze=5000, gesamt=5000)
        adapter.dokumente(AKTE)
        self.assertLessEqual(adapter._mail_konto, 5000)
        self.assertTrue(adapter.letzte_mails_ueber_budget)
        self.assertLess(len(adapter._mails), 3,
                        "Alle drei liegen im Puffer, obwohl das Maß kleiner ist.")

    def test_die_letzte_mail_wird_nicht_voll_uebernommen(self):
        """Vorher galt allein die Grenze je Mail: Die Akte konnte um bis zu
        eine ganze Mail über ihr Gesamtmaß hinausgehen."""
        server = _Server({"m1": _eml(2000), "m2": _eml(4000)})
        adapter = _adapter(server, grenze=9000, gesamt=4000)
        adapter.dokumente(AKTE)
        self.assertLessEqual(adapter._mail_konto, 4000 + 2000,
                             "Das Konto ist über das Gesamtmaß hinaus gelaufen.")
        self.assertTrue(adapter.letzte_mails_ueber_budget)

    def test_was_gepuffert_ist_zaehlt_nicht_zweimal(self):
        server = _Server({"m1": _eml(100)})
        adapter = _adapter(server, grenze=5000, gesamt=5000)
        adapter.dokumente(AKTE)
        nach_dem_ersten = adapter._mail_konto
        adapter.dokumente(AKTE)
        self.assertEqual(nach_dem_ersten, adapter._mail_konto,
                         "Eine gepufferte Mail wurde ein zweites Mal verrechnet.")

    def test_das_konto_beginnt_bei_einer_anderen_akte_neu(self):
        """Das Maß gilt je Akte, nicht je Programmlauf.

        Sonst wäre die zweite Akte des Tages benachteiligt — und ein Konto,
        das nie zurückgesetzt wird, sperrt irgendwann jede Mail.
        """
        server = _Server({"m1": _eml(100)})
        adapter = _adapter(server, grenze=5000, gesamt=5000)
        adapter.dokumente(AKTE)
        eine = adapter._mail_konto
        self.assertGreater(eine, 0)
        adapter.dokumente("rec-2")
        self.assertEqual(eine, adapter._mail_konto,
                         "Das Konto hat über die Aktengrenze hinaus summiert.")
        self.assertEqual(["m1", "m1"], server.downloads,
                         "Die andere Akte holt ihre Mail selbst.")


class DerNachladewegPrueftAuch(unittest.TestCase):
    """N06, der Teil, der die Warnung zur Lüge machte."""

    def test_eine_wegen_budget_ausgelassene_mail_kommt_nicht_doch_herein(self):
        server = _Server({"m1": _eml(3000), "m2": _eml(3000)})
        adapter = _adapter(server, grenze=5000, gesamt=3200)
        dokumente = adapter.dokumente(AKTE)
        ausgelassen = [d for d in dokumente
                       if d.id.startswith(MAIL_VORSATZ) and "Gesamtmaß" in d.kategorie]
        self.assertTrue(ausgelassen, "Keine Mail wurde wegen des Budgets ausgelassen.")
        with self.assertRaises(DokumentNichtGefunden) as fehler:
            adapter.dokument_laden(AKTE, ausgelassen[0].id)
        self.assertIn("Gesamtmaß", str(fehler.exception))

    def test_eine_gepufferte_mail_laedt_weiter_ohne_zweiten_abruf(self):
        """Die Gegenrichtung: Das Konto darf das Laden nicht blockieren."""
        server = _Server({"m1": _eml(100)})
        adapter = _adapter(server, grenze=5000, gesamt=5000)
        dokumente = adapter.dokumente(AKTE)
        mail = next(d for d in dokumente if d.id == f"{MAIL_VORSATZ}m1")
        vorher = len(server.downloads)
        _, bytes_ = adapter.dokument_laden(AKTE, mail.id)
        self.assertIn(b"Ein Brieftext", bytes_)
        self.assertEqual(vorher, len(server.downloads), "Es wurde erneut geholt.")


class DerPufferHatDreiEnden(unittest.TestCase):
    """N10."""

    def _mit_mail(self):
        server = _Server({"m1": _eml(100, text="Der Klartext dieser Mail.")})
        adapter = _adapter(server, grenze=5000, gesamt=5000)
        adapter.dokumente(AKTE)
        self.assertTrue(adapter._mails, "Nichts gepuffert — dann prüft das nichts.")
        return server, adapter

    def test_inhalte_vergessen_leert_ihn(self):
        _, adapter = self._mit_mail()
        adapter.inhalte_vergessen(AKTE)
        self.assertEqual({}, adapter._mails)
        self.assertEqual(0, adapter._mail_konto)

    def test_ein_einzelnes_dokument_laesst_sich_vergessen(self):
        """„Der Text wird gelöscht" wäre nicht wahr, wenn die Kopie bliebe."""
        _, adapter = self._mit_mail()
        adapter.inhalte_vergessen(AKTE, f"{MAIL_VORSATZ}m1")
        self.assertEqual({}, adapter._mails)

    def test_eine_fremde_akte_leert_ihn_nicht(self):
        """Sonst räumte das Schließen einer Sitzung die einer anderen mit aus."""
        _, adapter = self._mit_mail()
        adapter.inhalte_vergessen("rec-2")
        self.assertTrue(adapter._mails)

    def test_schliessen_nimmt_ihn_mit(self):
        """Hier stand nur `self._client.close()`."""
        _, adapter = self._mit_mail()
        adapter.schliessen()
        self.assertEqual({}, adapter._mails)

    def test_die_frist_laeuft_auch_ohne_zugriff_ab(self):
        _, adapter = self._mit_mail()
        adapter.MAIL_PUFFER_SEKUNDEN = 0.0
        self.assertIsNone(adapter._mail_aus_puffer(AKTE, "m1"))
        adapter.MAIL_PUFFER_SEKUNDEN = 3600
        adapter.dokumente(AKTE)
        adapter.MAIL_PUFFER_SEKUNDEN = 0.0
        adapter._mails_abgelaufene_entfernen()
        self.assertEqual({}, adapter._mails,
                         "Abgelaufenes bleibt liegen, solange niemand darauf zugreift.")

    def test_die_frist_ist_kuerzer_als_die_sitzung(self):
        """Sieben Tage Klartext im Arbeitsspeicher wären keine Frist."""
        self.assertLessEqual(HttpJurNodesAdapter.MAIL_PUFFER_SEKUNDEN, 24 * 3600)


class DerSitzungsschlussRaeumtMitAus(unittest.TestCase):
    """Der Weg, der zählt — über den Dienst, nicht über den Adapter."""

    def test_der_dienst_sagt_dem_adapter_bescheid(self):
        gerufen: list[tuple] = []

        class Adapter:
            def inhalte_vergessen(self, akte_id=None, dokument_id=None):
                gerufen.append((akte_id, dokument_id))

        from jusperfect.domain.models import Akte, Sitzung
        from jusperfect.security.identitaet import Identitaet
        from jusperfect.services.sitzung import Sitzungsdienst
        from jusperfect.speicher.lokal import LokalerSpeicher

        speicher = LokalerSpeicher()
        sitzung = Sitzung(id="s1", nutzer_id="ra-weber", akte_id=AKTE,
                          akte=Akte(id=AKTE, aktenzeichen="X-100-2026",
                                    bezeichnung="Sache"))
        speicher.sitzung_ablegen(sitzung)

        class Rechte:
            def pruefen(self, identitaet, akte_id):
                return None

        dienst = Sitzungsdienst(Adapter(), speicher, Rechte(), ocr=None)
        dienst.schliessen(Identitaet(nutzer_id="ra-weber", anzeigename="RA"), "s1")
        self.assertEqual([(AKTE, None)], gerufen,
                         "Der Sitzungsschluss hat den Puffer nicht geleert.")


if __name__ == "__main__":
    unittest.main()
