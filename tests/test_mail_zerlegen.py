"""Eine E-Mail in Text und Anlagen zerlegen.

Vorgabe der Kanzlei vom 08.10.2026: „Text der Mail immer, Anhänge als eigene
Dokumente daneben, jedes einzeln abwählbar wie die Dateien aus dem
Aktenordner."

Geprüft wird mit erfundenen Mails. Eine echte wird dafür nie gebraucht — und
genau deshalb steht das Zerlegen in einer eigenen Datei ohne Netz und ohne
Zugang.
"""

from __future__ import annotations

import unittest
from email.message import EmailMessage

from jusperfect.jurnodes.mail import (HOECHSTENS_ANHAENGE, KEIN_TEXT, Anhang,
                                      zerlegen)


def _mail(text: str = "", html: str = "", betreff: str = "Ein Betreff",
          von: str = "kanzlei@example.invalid",
          an: str = "mandant@example.invalid") -> EmailMessage:
    m = EmailMessage()
    m["Subject"] = betreff
    m["From"] = von
    m["To"] = an
    m["Date"] = "Wed, 08 Oct 2026 09:14:00 +0200"
    if text and html:
        m.set_content(text)
        m.add_alternative(html, subtype="html")
    elif html:
        m.set_content(html, subtype="html")
    else:
        m.set_content(text or "")
    return m


class DerTextDerMail(unittest.TestCase):
    def test_reiner_text_wird_genommen(self):
        z = zerlegen(_mail(text="Sehr geehrter Herr Meier,\n\nanbei.").as_bytes())
        self.assertEqual("text/plain", z.mime_typ)
        self.assertIn("Sehr geehrter Herr Meier", z.text)
        self.assertEqual((), z.anhaenge)

    def test_bei_text_und_html_gewinnt_der_text(self):
        """HTML trägt Markierungen, die in einem Aktentext nichts zu suchen haben."""
        z = zerlegen(_mail(text="Der Brieftext.",
                           html="<p>Der <b>Brieftext</b>.</p>").as_bytes())
        self.assertEqual("text/plain", z.mime_typ)
        self.assertIn("Der Brieftext.", z.text)
        self.assertNotIn("<b>", z.text)

    def test_nur_html_kommt_als_html(self):
        z = zerlegen(_mail(html="<p>Nur als HTML.</p>").as_bytes())
        self.assertEqual("text/html", z.mime_typ)
        self.assertIn("Nur als HTML.", z.text)

    def test_die_kopfzeilen_stehen_vor_dem_text(self):
        """Ohne Absender ist eine Mail als Beleg wertlos.

        Die Analyse zitiert Dokument, Seite und Passage. Bei einem Schriftsatz
        steht der Absender im Briefkopf; bei einer Mail nur in den Kopfzeilen.
        """
        z = zerlegen(_mail(text="Kurz.", von="gegner@example.invalid",
                           betreff="Fristverlängerung").as_bytes())
        self.assertIn("Von: gegner@example.invalid", z.text)
        self.assertIn("Betreff: Fristverlängerung", z.text)
        self.assertIn("Datum:", z.text)
        self.assertLess(z.text.index("Von:"), z.text.index("Kurz."))

    def test_auch_bei_html_stehen_die_kopfzeilen_davor(self):
        z = zerlegen(_mail(html="<p>Kurz.</p>", von="gegner@example.invalid").as_bytes())
        self.assertIn("gegner@example.invalid", z.text)
        self.assertLess(z.text.index("gegner@"), z.text.index("Kurz."))

    def test_eine_mail_ohne_text_sagt_das(self):
        m = EmailMessage()
        m["Subject"] = "Leer"
        m["From"] = "a@example.invalid"
        m.set_content(b"", maintype="application", subtype="octet-stream")
        z = zerlegen(m.as_bytes())
        self.assertIn(KEIN_TEXT, z.text)


class DieAnlagen(unittest.TestCase):
    def test_eine_anlage_wird_eine_anlage(self):
        m = _mail(text="Anbei der Schriftsatz.")
        m.add_attachment(b"%PDF-1.4 ...", maintype="application", subtype="pdf",
                         filename="Schriftsatz.pdf")
        z = zerlegen(m.as_bytes())
        self.assertEqual(1, len(z.anhaenge))
        self.assertEqual("Schriftsatz.pdf", z.anhaenge[0].name)
        self.assertEqual("application/pdf", z.anhaenge[0].mime_typ)
        self.assertTrue(z.anhaenge[0].inhalt.startswith(b"%PDF"))
        self.assertIn("Anbei der Schriftsatz.", z.text)

    def test_ein_verschluesselter_dateiname_wird_lesbar(self):
        """Sonst steht Buchstabensalat in der Aktenliste.

        Ein Dateiname mit Umlauten reist als =?utf-8?B?…?= durch die Mail.
        """
        m = _mail(text="Anbei.")
        m.add_attachment(b"x", maintype="application", subtype="pdf",
                         filename="Prüfbericht Gebäude.pdf")
        z = zerlegen(m.as_bytes())
        self.assertEqual("Prüfbericht Gebäude.pdf", z.anhaenge[0].name)
        self.assertNotIn("=?", z.anhaenge[0].name)

    def test_das_signaturbild_ist_keine_anlage(self):
        """Sonst stehen nach zwanzig Mails achtzig „image001.png" in der Liste."""
        m = _mail(text="Mit freundlichen Grüßen")
        m.add_attachment(b"\x89PNG\r\n", maintype="image", subtype="png",
                         filename="image001.png", cid="<bild1@kanzlei>",
                         disposition="inline")
        z = zerlegen(m.as_bytes())
        self.assertEqual((), z.anhaenge, "Das eingebettete Bild ist keine Anlage.")
        self.assertEqual(1, z.eingebettet, "Weglassen ja - verschweigen nein.")

    def test_ein_pdf_das_inline_heisst_bleibt_eine_anlage(self):
        """Manche Programme nennen auch einen Schriftsatz „inline“.

        Ohne Content-ID bindet ihn nichts ein — dann ist es eine Anlage, wie
        sie aussieht.
        """
        m = _mail(text="Anbei.")
        m.add_attachment(b"%PDF-1.4", maintype="application", subtype="pdf",
                         filename="Klage.pdf", disposition="inline")
        z = zerlegen(m.as_bytes())
        self.assertEqual(["Klage.pdf"], [a.name for a in z.anhaenge])

    def test_mehrere_anlagen_behalten_ihre_reihenfolge(self):
        m = _mail(text="Drei Stück.")
        for name in ("A.pdf", "B.docx", "C.pdf"):
            m.add_attachment(b"inhalt", maintype="application", subtype="pdf",
                             filename=name)
        z = zerlegen(m.as_bytes())
        self.assertEqual(["A.pdf", "B.docx", "C.pdf"], [a.name for a in z.anhaenge])

    def test_eine_leere_anlage_wird_weggelassen(self):
        m = _mail(text="Mit leerer Anlage.")
        m.add_attachment(b"", maintype="application", subtype="pdf",
                         filename="Leer.pdf")
        z = zerlegen(m.as_bytes())
        self.assertEqual((), z.anhaenge)

    def test_zu_viele_anlagen_werden_gezaehlt_nicht_verschwiegen(self):
        m = _mail(text="Sehr viele.")
        for i in range(HOECHSTENS_ANHAENGE + 7):
            m.add_attachment(b"x", maintype="application", subtype="pdf",
                             filename=f"A{i}.pdf")
        z = zerlegen(m.as_bytes())
        self.assertEqual(HOECHSTENS_ANHAENGE, len(z.anhaenge))
        self.assertEqual(7, z.uebersprungen)


class EineKaputteMailKostetNichtDieAkte(unittest.TestCase):
    """Sie wirft nicht. Was sie nicht versteht, meldet sie als leeren Text."""

    def test_wirrer_inhalt(self):
        z = zerlegen(b"\x00\x01\x02 das ist keine Mail \xff\xfe")
        self.assertIsInstance(z.text, str)
        self.assertEqual((), z.anhaenge)

    def test_gar_nichts(self):
        z = zerlegen(b"")
        self.assertIn(KEIN_TEXT, z.text)

    def test_eine_erfundene_zeichentabelle(self):
        """„utf8mb4" gibt es als Python-Kodierung nicht - die Mail trotzdem."""
        roh = (b"Subject: Test\r\nFrom: a@example.invalid\r\n"
               b"Content-Type: text/plain; charset=utf8mb4\r\n\r\n"
               b"Der Text bleibt lesbar.\r\n")
        z = zerlegen(roh)
        self.assertIn("Der Text bleibt lesbar.", z.text)

    def test_eine_mail_in_der_mail(self):
        """Weitergeleitete Mails tragen die alte als Teil - ihre Anlage zählt."""
        innen = _mail(text="Die ursprüngliche Nachricht.")
        innen.add_attachment(b"%PDF-1.4", maintype="application", subtype="pdf",
                             filename="Original.pdf")
        aussen = _mail(text="Zur Kenntnis.")
        # So hängt ein Mailprogramm eine Weiterleitung an: die Nachricht
        # selbst, nicht ihre Bytes. Wer Bytes anhängt, bekommt sie base64
        # verpackt zurück, und dann ist innen nichts mehr zu finden.
        aussen.add_attachment(innen)
        z = zerlegen(aussen.as_bytes())
        namen = [a.name for a in z.anhaenge]
        self.assertIn("Original.pdf", namen,
                      "Die Anlage der weitergeleiteten Mail gehört in die Akte.")
        self.assertIn("Zur Kenntnis.", z.text)
        self.assertNotIn("Die ursprüngliche Nachricht.", z.text,
                         "Der Text der Weiterleitung steht schon im Brieftext.")


class DerAnhangKenntSeineGroesse(unittest.TestCase):
    def test_groesse(self):
        a = Anhang(name="X.pdf", mime_typ="application/pdf", inhalt=b"12345")
        self.assertEqual(5, a.groesse)


if __name__ == "__main__":
    unittest.main()
