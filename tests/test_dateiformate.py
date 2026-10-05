"""Alle Dokumenttypen einer Akte lesen.

Aus der Kanzlei am 25.09.2026: "24 von 38 Dokumenten gelesen, 14 nicht: 14 in
einem Format, das nicht gelesen werden kann." Und dann: "ja bitte, er soll
alle Dokumenttypen lesen können."

In einer Akte liegen nicht nur Schriftsätze. Es liegen E-Mails darin, alte
Word-Dateien, Tabellen, ausgedruckte Webseiten. Ein Programm, das davon die
Hälfte nicht ansieht, hat die Akte nicht gelesen - und niemand merkt es, weil
eine kurze Antwort wie eine knappe Akte aussieht.

Geprüft wird an Dateien, die hier erzeugt werden - nicht an nachgebauten
Zeichenketten. Eine Probe, die anders fragt als der Betrieb, prüft etwas
anderes als den Betrieb.
"""

from __future__ import annotations

import unittest
from unittest import mock

from jusperfect.domain.models import Dokument
from jusperfect.services.extraktion import NichtUnterstuetzt, _art, text_extrahieren


def _dokument(dateiname: str, mime: str = "application/octet-stream") -> Dokument:
    return Dokument(id="D-1", akte_id="rec-1", titel=dateiname,
                    dateiname=dateiname, mime_typ=mime)


def _lesen(dateiname: str, daten: bytes, mime: str = "application/octet-stream") -> str:
    seiten, _ = text_extrahieren(_dokument(dateiname, mime), daten,
                                 mock.MagicMock(), "s1")
    return "\n".join(s.text for s in seiten)


class EMailsWerdenGelesen(unittest.TestCase):
    """In einer Akte liegen oft mehr E-Mails als Schriftsätze."""

    def _eml(self) -> bytes:
        from email.message import EmailMessage

        m = EmailMessage()
        m["From"] = "gegenseite@example.invalid"
        m["To"] = "kanzlei@example.invalid"
        m["Subject"] = "Mängelrüge vom 14.02.2025"
        m["Date"] = "Fri, 14 Feb 2025 09:12:00 +0100"
        m.set_content("Sehr geehrte Damen und Herren,\n\n"
                      "die Mängel sind bis heute nicht beseitigt.\n")
        return m.as_bytes()

    def test_der_text_kommt_an(self):
        text = _lesen("rüge.eml", self._eml())
        self.assertIn("Mängel sind bis heute nicht beseitigt", text)

    def test_die_kopfzeilen_auch(self):
        """Von wem, an wen, wann - ohne sie ließe sich ein Satz aus der Mail
        nicht zuordnen."""
        text = _lesen("rüge.eml", self._eml())
        self.assertIn("gegenseite@example.invalid", text)
        self.assertIn("Mängelrüge vom 14.02.2025", text)
        self.assertIn("14 Feb 2025", text)

    def test_anhaenge_werden_benannt(self):
        from email.message import EmailMessage

        m = EmailMessage()
        m["Subject"] = "Anbei"
        m.set_content("Siehe Anlage.")
        m.add_attachment(b"%PDF-1.4", maintype="application", subtype="pdf",
                         filename="Rechnung.pdf")
        text = _lesen("mit-anhang.eml", m.as_bytes())
        self.assertIn("Rechnung.pdf", text)

    def test_eine_html_mail_wird_zu_text(self):
        from email.message import EmailMessage

        m = EmailMessage()
        m["Subject"] = "Html"
        m.set_content("<p>Die <b>Frist</b> läuft ab.</p>", subtype="html")
        text = _lesen("html.eml", m.as_bytes())
        self.assertIn("Frist", text)
        self.assertNotIn("<b>", text)


class WebseitenWerdenGelesen(unittest.TestCase):

    def test_auszeichnung_faellt_weg_der_text_bleibt(self):
        roh = (b"<html><head><style>p{color:red}</style></head><body>"
               b"<h1>Urteil</h1><p>Die Klage wird <b>abgewiesen</b>.</p>"
               b"<script>alert(1)</script></body></html>")
        text = _lesen("urteil.html", roh)
        self.assertIn("Urteil", text)
        self.assertIn("abgewiesen", text)
        self.assertNotIn("color:red", text)
        self.assertNotIn("alert", text)


class RtfWirdGelesen(unittest.TestCase):

    def test_der_text_steht_ohne_steuerworte_da(self):
        roh = (rb"{\rtf1\ansi\deff0{\fonttbl{\f0 Times;}}"
               rb"\f0\fs24 Sehr geehrte Frau Kollegin,\par "
               rb"die Frist l\'e4uft am 14.02.2025 ab.\par}")
        text = _lesen("schriftsatz.rtf", roh)
        self.assertIn("Sehr geehrte Frau Kollegin", text)
        self.assertIn("14.02.2025", text)
        self.assertNotIn("fonttbl", text)
        self.assertNotIn("rtf1", text)

    def test_umlaute_kommen_richtig_an(self):
        text = _lesen("u.rtf", rb"{\rtf1\ansi M\'e4ngel und Sch\'e4den\par}")
        self.assertIn("Mängel", text)
        self.assertIn("Schäden", text)


class TabellenWerdenGelesen(unittest.TestCase):

    def _xlsx(self) -> bytes:
        import io
        import zipfile

        blatt = ('<?xml version="1.0"?><worksheet '
                 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                 '<sheetData>'
                 '<row r="1"><c r="A1" t="s"><v>0</v></c>'
                 '<c r="B1" t="s"><v>1</v></c></row>'
                 '<row r="2"><c r="A2" t="s"><v>2</v></c>'
                 '<c r="B2"><v>12500.5</v></c></row>'
                 '</sheetData></worksheet>')
        texte = ('<?xml version="1.0"?><sst '
                 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                 '<si><t>Position</t></si><si><t>Betrag</t></si>'
                 '<si><t>Schlussrechnung</t></si></sst>')
        puffer = io.BytesIO()
        with zipfile.ZipFile(puffer, "w") as z:
            z.writestr("xl/worksheets/sheet1.xml", blatt)
            z.writestr("xl/sharedStrings.xml", texte)
        return puffer.getvalue()

    def test_zellen_und_zahlen_kommen_an(self):
        text = _lesen("aufstellung.xlsx", self._xlsx())
        self.assertIn("Position", text)
        self.assertIn("Schlussrechnung", text)
        self.assertIn("12500.5", text)

    def test_die_zeilen_bleiben_zeilen(self):
        """Eine Tabelle ohne Zeilen ist eine Wortwolke."""
        text = _lesen("aufstellung.xlsx", self._xlsx())
        self.assertIn("Position | Betrag", text)


class FolienWerdenGelesen(unittest.TestCase):

    def test_jede_folie_eine_seite(self):
        import io
        import zipfile

        def folie(inhalt: str) -> str:
            return ('<?xml version="1.0"?><p:sld '
                    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                    f'<p:cSld><a:t>{inhalt}</a:t></p:cSld></p:sld>')

        puffer = io.BytesIO()
        with zipfile.ZipFile(puffer, "w") as z:
            z.writestr("ppt/slides/slide1.xml", folie("Sachverhalt"))
            z.writestr("ppt/slides/slide2.xml", folie("Rechtslage"))
        seiten, _ = text_extrahieren(_dokument("vortrag.pptx"), puffer.getvalue(),
                                     mock.MagicMock(), "s1")
        self.assertEqual(2, len(seiten))
        self.assertIn("Sachverhalt", seiten[0].text)
        self.assertIn("Rechtslage", seiten[1].text)


class DieArtWirdRichtigErkannt(unittest.TestCase):

    def test_an_der_endung(self):
        for dateiname, erwartet in (("a.pdf", "pdf"), ("a.docx", "docx"),
                                    ("a.msg", "msg"), ("a.eml", "eml"),
                                    ("a.html", "html"), ("a.rtf", "rtf"),
                                    ("a.xlsx", "xlsx"), ("a.pptx", "pptx"),
                                    ("a.txt", "text"), ("a.tif", "bild"),
                                    ("a.doc", "alt"), ("a.zip", "unbekannt")):
            with self.subTest(dateiname=dateiname):
                self.assertEqual(erwartet, _art(_dokument(dateiname)))

    def test_auch_am_mime_typ_wenn_die_endung_fehlt(self):
        """jur|nodes gibt den MIME-Typ nicht immer mit - dann steht dort
        "application/octet-stream". Umgekehrt fehlt manchmal die Endung."""
        self.assertEqual("eml", _art(_dokument("Mail ohne Endung", "message/rfc822")))
        self.assertEqual("html", _art(_dokument("Seite", "text/html")))


class AlteFormateWerdenBenanntStattGeraten(unittest.TestCase):
    """Ein halb gelesener Schriftsatz ist schlimmer als ein fehlender: Was
    daraus zitiert würde, stünde so nicht in der Akte."""

    def test_die_meldung_sagt_was_zu_tun_ist(self):
        with self.assertRaises(NichtUnterstuetzt) as fehler:
            _lesen("alt.doc", b"\xd0\xcf\x11\xe0irgendwas")
        satz = str(fehler.exception)
        self.assertIn("Altes Microsoft-Format", satz)
        self.assertIn("PDF", satz)

    def test_ein_unbekanntes_format_nennt_den_dateinamen(self):
        with self.assertRaises(NichtUnterstuetzt) as fehler:
            _lesen("archiv.zip", b"PK\x03\x04")
        self.assertIn("archiv.zip", str(fehler.exception))


class EinKaputtesDokumentNenntSeineArt(unittest.TestCase):
    """"Nicht lesbar" allein hilft niemandem weiter."""

    def test_die_meldung_sagt_um_was_fuer_eine_datei_es_ging(self):
        with self.assertRaises(NichtUnterstuetzt) as fehler:
            _lesen("kaputt.xlsx", b"das ist kein ZIP")
        self.assertIn("Tabelle", str(fehler.exception))


if __name__ == "__main__":
    unittest.main()


class OutlookNachrichtenWerdenGelesen(unittest.TestCase):
    """Das einzige Format mit eigenem Paket - .msg ist ein Dateibaum, kein Text.

    GRENZE DIESER PRÜFUNG: Hier wird kein echtes .msg gelesen, sondern das
    Paket vorgetäuscht. Eine .msg-Datei lässt sich nicht in ein paar Zeilen
    erzeugen, und eine aus einer Akte gehört nicht in dieses Verzeichnis.

    Geprüft wird deshalb, was hier tatsächlich gebaut wurde: dass die
    Kopfzeilen mit dem Text zusammenkommen, dass Anhänge benannt werden - und
    dass die Datei, die dafür kurz auf der Platte liegt, danach wieder weg
    ist. Aktentext gehört nicht länger dorthin als nötig.
    """

    def _nachricht(self, **felder):
        n = mock.MagicMock()
        n.sender = felder.get("sender", "gegenseite@example.invalid")
        n.to = felder.get("to", "kanzlei@example.invalid")
        n.cc = None
        n.date = felder.get("date", "2025-02-14 09:12:00")
        n.subject = felder.get("subject", "Mängelrüge")
        n.body = felder.get("body", "Die Mängel sind nicht beseitigt.")
        n.htmlBody = felder.get("htmlBody", None)
        n.attachments = felder.get("attachments", [])
        return n

    def _lesen(self, nachricht):
        modul = mock.MagicMock()
        modul.Message.return_value = nachricht
        with mock.patch.dict("sys.modules", {"extract_msg": modul}):
            return _lesen("mail.msg", b"\xd0\xcf\x11\xe0 OLE")

    def test_kopfzeilen_und_text_kommen_zusammen(self):
        text = self._lesen(self._nachricht())
        self.assertIn("gegenseite@example.invalid", text)
        self.assertIn("Mängelrüge", text)
        self.assertIn("Die Mängel sind nicht beseitigt", text)

    def test_ohne_textteil_wird_der_html_teil_genommen(self):
        n = self._nachricht(body="", htmlBody=b"<p>Die <b>Frist</b> l\xc3\xa4uft.</p>")
        text = self._lesen(n)
        self.assertIn("Frist", text)
        self.assertNotIn("<b>", text)

    def test_anhaenge_werden_benannt(self):
        anhang = mock.MagicMock()
        anhang.longFilename = "Mängelliste.pdf"
        text = self._lesen(self._nachricht(attachments=[anhang]))
        self.assertIn("Mängelliste.pdf", text)

    def test_die_zwischendatei_wird_wieder_geloescht(self):
        """Aktentext gehört nicht länger auf die Platte als nötig."""
        import os

        gemerkt = []
        echtes_unlink = os.unlink

        def merken(pfad):
            gemerkt.append(pfad)
            return echtes_unlink(pfad)

        with mock.patch("os.unlink", side_effect=merken):
            self._lesen(self._nachricht())
        self.assertEqual(1, len(gemerkt), "Die Zwischendatei blieb liegen.")
        self.assertFalse(os.path.exists(gemerkt[0]))

    def test_auch_wenn_das_lesen_scheitert(self):
        import os

        gemerkt = []
        modul = mock.MagicMock()
        modul.Message.side_effect = ValueError("kaputt")
        echtes_unlink = os.unlink
        with mock.patch.dict("sys.modules", {"extract_msg": modul}), \
                mock.patch("os.unlink", side_effect=lambda p: (gemerkt.append(p),
                                                               echtes_unlink(p))[1]):
            with self.assertRaises(NichtUnterstuetzt):
                _lesen("mail.msg", b"\xd0\xcf\x11\xe0")
        self.assertEqual(1, len(gemerkt), "Die Zwischendatei blieb nach dem Fehler liegen.")
