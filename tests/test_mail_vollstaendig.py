"""Was aus einer E-Mail in die Akte kommt — und was gezählt wird, wenn nicht.

Befunde **N03** und **N04** der dritten Zweitprüfung vom 12.10.2026. Drei Wege,
auf denen Akteninhalt lautlos verschwand.

**N03.** Eine Mail mit „Zur Kenntnis." und einer angehängten `message/rfc822`
verlor den ganzen Text der angehängten Nachricht — also die übermittelte
Erklärung, auf die es ankam. Die Anlagenliste war leer, der Verlustzähler
null. Begründet war das mit der Annahme, der Text stehe schon im Brieftext
zitiert. Geprüft wurde sie nie, und die Prüfung, die den Verlust verlangte,
widerlegte sie am eigenen Beispiel.

**N04.** Ein PDF mit `Content-ID` und `inline` wurde wie ein Signaturbild
aussortiert, ohne dass die Medienart geprüft wurde. Ein PDF **ohne
Dateinamen** fiel durch beide Zweige. Und die 51. Anlage wurde vom Parser
gezählt, aber der Adapter nahm diesen Zähler nicht: Angezeigt wurden allein
die angenommenen Anlagen, und die sahen vollständig aus.

**Der gemeinsame Satz:** Ein Zähler, den nur der Parser kennt, ist kein
Zähler. Deshalb wird hier bis zur Anzeige gemessen — an der Zeile der Mail und
an der Antwort der Schnittstelle, nicht an `Zerlegt.uebersprungen`.
"""

from __future__ import annotations

import unittest
from email.message import EmailMessage

from jusperfect.jurnodes.mail import (
    GRUND_ANDERER_TEIL, GRUND_DOPPELT, GRUND_LEER, GRUND_SIGNATURBILD,
    GRUND_ZU_VIELE, HOECHSTENS_ANHAENGE, HOECHSTENS_NACHRICHTEN, zerlegen,
)

#: Ein Text, der lang genug ist, dass die Doppelt-Erkennung ihn ansieht.
AUSSAGE = ("Hiermit erkläre ich die Abtretung meiner Ansprüche aus dem "
           "Unfallereignis vom 12.05.2025 in vollem Umfang.")


def _mail(text: str = "", html: str = "", betreff: str = "Ein Betreff") -> EmailMessage:
    m = EmailMessage()
    m["From"] = "kanzlei@example.invalid"
    m["To"] = "mandant@example.invalid"
    m["Subject"] = betreff
    m["Date"] = "Thu, 08 Oct 2026 09:14:00 +0200"
    if text:
        m.set_content(text)
    if html:
        if text:
            m.add_alternative(html, subtype="html")
        else:
            m.set_content(html, subtype="html")
    return m


class DerTextEinerWeitergeleitetenMail(unittest.TestCase):
    """N03 — der eigentliche Fang."""

    def test_er_kommt_mit(self):
        innen = _mail(text=AUSSAGE, betreff="Abtretung")
        aussen = _mail(text="Zur Kenntnis.")
        aussen.add_attachment(innen)
        z = zerlegen(aussen.as_bytes())
        self.assertIn(AUSSAGE, z.text)
        self.assertEqual(1, z.nachrichten)
        self.assertEqual(0, z.verloren, z.ausgelassen)

    def test_er_traegt_seine_eigenen_kopfzeilen(self):
        """Ohne Absender und Datum ist der Text als Beleg wertlos."""
        innen = _mail(text=AUSSAGE, betreff="Abtretung")
        innen.replace_header("From", "gegner@example.invalid")
        aussen = _mail(text="Zur Kenntnis.")
        aussen.add_attachment(innen)
        z = zerlegen(aussen.as_bytes())
        self.assertIn("gegner@example.invalid", z.text)
        self.assertIn("Abtretung", z.text)

    def test_er_ist_als_angehaengt_erkennbar(self):
        """Sonst liest sich der Text, als hätte der äußere Absender ihn geschrieben."""
        innen = _mail(text=AUSSAGE)
        aussen = _mail(text="Zur Kenntnis.")
        aussen.add_attachment(innen)
        self.assertIn("Angehängte Nachricht 1", zerlegen(aussen.as_bytes()).text)

    def test_eine_kette_aus_dreien_kommt_ganz(self):
        innerste = _mail(text="Die erste Nachricht ist der Anfang der Kette.")
        mitte = _mail(text="Die zweite Nachricht liegt in der Mitte davon.")
        mitte.add_attachment(innerste)
        aussen = _mail(text="Zur Kenntnis.")
        aussen.add_attachment(mitte)
        z = zerlegen(aussen.as_bytes())
        self.assertIn("der Anfang der Kette", z.text)
        self.assertIn("liegt in der Mitte", z.text)
        self.assertEqual(2, z.nachrichten)

    def test_die_anlage_der_weiterleitung_bleibt_eine_anlage(self):
        """Das hat vorher schon gestimmt und muss weiter stimmen."""
        innen = _mail(text=AUSSAGE)
        innen.add_attachment(b"%PDF-1.4", maintype="application", subtype="pdf",
                             filename="Original.pdf")
        aussen = _mail(text="Zur Kenntnis.")
        aussen.add_attachment(innen)
        z = zerlegen(aussen.as_bytes())
        self.assertIn("Original.pdf", [a.name for a in z.anhaenge])


class WennDerTextWirklichSchonObenSteht(unittest.TestCase):
    """Weggelassen wird nur, was nachweislich doppelt ist."""

    def test_dann_wird_er_weggelassen_und_gezaehlt(self):
        innen = _mail(text=AUSSAGE)
        aussen = _mail(text=f"Wie gestern besprochen:\n\n> {AUSSAGE}\n\nMit Gruß")
        aussen.add_attachment(innen)
        z = zerlegen(aussen.as_bytes())
        self.assertEqual(0, z.nachrichten)
        self.assertEqual(1, z.ausgelassen.get(GRUND_DOPPELT))
        # Gezaehlt heisst: der Bearbeiter kann es sehen.
        self.assertTrue(any(GRUND_DOPPELT in g for g in z.gruende()), z.gruende())

    def test_ein_kurzes_ok_wird_nicht_weggerechnet(self):
        """„ok" steht in jedem zweiten Brieftext. Es doppelt mitzunehmen kostet
        nichts, es falsch wegzuwerfen eine Aussage."""
        innen = _mail(text="ok")
        aussen = _mail(text="Ist das ok so? Bitte kurz bestätigen.")
        aussen.add_attachment(innen)
        self.assertEqual(1, zerlegen(aussen.as_bytes()).nachrichten)

    def test_ein_anderer_umbruch_taeuscht_keine_abweichung_vor(self):
        innen = _mail(text=AUSSAGE)
        zitiert = AUSSAGE.replace(" ", "\n> ")
        aussen = _mail(text=f"Siehe unten:\n\n> {zitiert}\n")
        aussen.add_attachment(innen)
        self.assertEqual(1, zerlegen(aussen.as_bytes()).ausgelassen.get(GRUND_DOPPELT))


class EineAnlageDieKeinBildIst(unittest.TestCase):
    """N04, erster Fall: Die Medienart entscheidet mit."""

    def test_ein_pdf_mit_content_id_und_inline_bleibt_eine_anlage(self):
        """Manche Programme bezeichnen JEDE Anlage als „inline"."""
        m = _mail(text="Anbei.")
        m.add_attachment(b"%PDF-1.4 Schriftsatz", maintype="application",
                         subtype="pdf", filename="Schriftsatz.pdf",
                         disposition="inline", cid="<teil1@absender>")
        z = zerlegen(m.as_bytes())
        self.assertIn("Schriftsatz.pdf", [a.name for a in z.anhaenge])
        self.assertEqual(0, z.eingebettet)

    def test_ein_bild_mit_content_id_und_inline_bleibt_eine_signatur(self):
        """Sonst stünden nach zwanzig Mails achtzig „image001.png" in der Liste."""
        m = _mail(text="Mit Gruß", html="<p>Mit Gruß</p>")
        m.add_attachment(b"\x89PNG\r\n\x1a\n", maintype="image", subtype="png",
                         filename="image001.png", disposition="inline",
                         cid="<bild1@absender>")
        z = zerlegen(m.as_bytes())
        self.assertEqual((), tuple(a.name for a in z.anhaenge))
        self.assertEqual(1, z.eingebettet)
        self.assertEqual(0, z.verloren, "Ein Signaturbild ist kein Verlust.")


class EineAnlageOhneDateinamen(unittest.TestCase):
    """N04, zweiter Fall: Sie galt als Brieftext und war keiner."""

    def test_ein_pdf_ohne_namen_kommt_mit(self):
        m = _mail(text="Anbei.")
        m.add_attachment(b"%PDF-1.4 ohne Namen", maintype="application",
                         subtype="pdf")
        for teil in m.walk():
            if teil.get_content_type() == "application/pdf":
                del teil["Content-Disposition"]
        z = zerlegen(m.as_bytes())
        self.assertEqual(1, len(z.anhaenge), z.ausgelassen)
        self.assertEqual("application/pdf", z.anhaenge[0].mime_typ)

    def test_es_bekommt_einen_namen_mit_endung(self):
        """`_art` in der Extraktion sieht zuerst auf den MIME-Typ — aber ein
        Name ohne Endung sieht in der Aktenliste aus wie ein Fehler."""
        m = _mail(text="Anbei.")
        m.add_attachment(b"%PDF-1.4", maintype="application", subtype="pdf")
        for teil in m.walk():
            if teil.get_content_type() == "application/pdf":
                del teil["Content-Disposition"]
        self.assertTrue(zerlegen(m.as_bytes()).anhaenge[0].name.endswith(".pdf"))

    def test_der_brieftext_bleibt_brieftext(self):
        """Die Gegenrichtung: Nicht jeder Teil ohne Namen ist jetzt eine Anlage."""
        m = _mail(text="Nur Text.", html="<p>Nur Text.</p>")
        z = zerlegen(m.as_bytes())
        self.assertEqual((), z.anhaenge)
        self.assertIn("Nur Text.", z.text)


class WasNichtUebernommenWirdWirdGezaehlt(unittest.TestCase):
    """N04, dritter Fall — und die Lehre daraus."""

    def test_eine_leere_anlage_verschwindet_nicht_lautlos(self):
        """Eine Anlage, die der Absender geschickt hat und die hier nicht
        lesbar ist, ist genau der Fall, in dem nachgefragt werden muss."""
        m = _mail(text="Anbei.")
        m.add_attachment(b"", maintype="application", subtype="pdf",
                         filename="Leer.pdf")
        z = zerlegen(m.as_bytes())
        self.assertEqual((), z.anhaenge)
        self.assertEqual(1, z.ausgelassen.get(GRUND_LEER))
        self.assertEqual(1, z.verloren)

    def test_die_einundfuenfzigste_anlage_wird_gezaehlt(self):
        m = _mail(text="Anbei.")
        for nr in range(HOECHSTENS_ANHAENGE + 3):
            m.add_attachment(b"%PDF-1.4", maintype="application", subtype="pdf",
                             filename=f"Anlage-{nr}.pdf")
        z = zerlegen(m.as_bytes())
        self.assertEqual(HOECHSTENS_ANHAENGE, len(z.anhaenge))
        self.assertEqual(3, z.ausgelassen.get(GRUND_ZU_VIELE))
        self.assertEqual(3, z.uebersprungen, "Der alte Name liest aus derselben Quelle.")
        self.assertEqual(3, z.verloren)

    def test_ein_teil_der_weder_text_noch_anlage_ist(self):
        m = _mail(text="Termin.")
        m.add_attachment("BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n",
                         subtype="calendar")
        for teil in m.walk():
            if teil.get_content_type() == "text/calendar":
                del teil["Content-Disposition"]
        z = zerlegen(m.as_bytes())
        self.assertEqual(1, z.ausgelassen.get(GRUND_ANDERER_TEIL), z.ausgelassen)

    def test_zu_viele_angehaengte_nachrichten(self):
        innerste = _mail(text="Die Kette beginnt hier mit einem langen Satz.")
        aussen = innerste
        for nr in range(HOECHSTENS_NACHRICHTEN + 2):
            naechste = _mail(text=f"Stufe {nr} dieser Kette, mit genug Text darin.")
            naechste.add_attachment(aussen)
            aussen = naechste
        z = zerlegen(aussen.as_bytes())
        self.assertLessEqual(z.nachrichten, HOECHSTENS_NACHRICHTEN)
        self.assertTrue(z.verloren, "Was nicht mitkam, muss dastehen.")

    def test_das_signaturbild_steht_nicht_in_den_gruenden(self):
        """Es ist kein Verlust, nur Rauschen in der Warnung."""
        m = _mail(text="Mit Gruß", html="<p>Mit Gruß</p>")
        m.add_attachment(b"\x89PNG", maintype="image", subtype="png",
                         filename="image001.png", disposition="inline",
                         cid="<b@a>")
        z = zerlegen(m.as_bytes())
        self.assertEqual((), z.gruende())
        self.assertIn(GRUND_SIGNATURBILD, z.ausgelassen)


class EineMailDieNurHtmlHat(unittest.TestCase):
    """Beim Umbau mitgeprüft: Die Kopfzeilen gehen nicht mehr roh in HTML."""

    def test_eine_adresse_in_den_kopfzeilen_bleibt_lesbar(self):
        """`Name <adresse@…>` verlor bei der Textgewinnung die Adresse: Die
        spitzen Klammern sahen aus wie eine Markierung."""
        m = _mail(html="<p>Nur HTML.</p>")
        m.replace_header("From", "Kanzlei Beispiel <kanzlei@example.invalid>")
        z = zerlegen(m.as_bytes())
        self.assertEqual("text/html", z.mime_typ)
        self.assertIn("&lt;kanzlei@example.invalid&gt;", z.text)

    def test_ein_betreff_mit_style_verschluckt_den_text_nicht(self):
        m = _mail(html="<p>Der eigentliche Nachrichtentext.</p>")
        m.replace_header("Subject", "<style>")
        z = zerlegen(m.as_bytes())
        self.assertIn("&lt;style&gt;", z.text)
        self.assertIn("Der eigentliche Nachrichtentext.", z.text)

    def test_text_und_html_zusammen_bleiben_lesbar(self):
        innen = _mail(html="<p>Nur als HTML in der angehängten Nachricht.</p>")
        aussen = _mail(text="Zur Kenntnis.")
        aussen.add_attachment(innen)
        z = zerlegen(aussen.as_bytes())
        self.assertEqual("text/html", z.mime_typ)
        self.assertIn("Zur Kenntnis.", z.text)
        self.assertIn("Nur als HTML", z.text)


if __name__ == "__main__":
    unittest.main()
