"""Die Probe zeigt, was der Server zu einer Abweisung sagt.

Bis zum 25.09.2026 druckte sie nur "Status 405" und warf den Satz weg, den
jur|nodes jeder Abweisung beilegt. Das hat zwei Tage gekostet: 405 heisst bei
diesem Hersteller nicht "diesen Weg gibt es nicht", sondern "ungueltige
Eingabe" - 94mal so in seiner eigenen Beschreibung und keinmal anders.

Nur die Probe zeigt den Satz, nicht das Programm im Alltag: Er kommt von einem
fremden Server, niemand liest ihn vorher, und im Alltag stehen echte Akten
daneben. So entschieden mit der Kanzlei am 25.09.2026.
"""

from __future__ import annotations

import unittest

from jusperfect.jurnodestest import HINWEIS_405, _serverwort


class _Antwort:
    """So viel von einer Antwort, wie die Auswertung anfasst."""

    def __init__(self, daten=None, text="", status=405):
        self._daten = daten
        self.text = text
        self.status_code = status

    def json(self):
        if self._daten is None:
            raise ValueError("kein JSON")
        return self._daten


class DerSatzDesServersWirdAusgelesen(unittest.TestCase):

    def test_das_feld_error_ist_der_regelfall(self):
        """So beschreibt der Hersteller seine 405 (Schema InvalidInput)."""
        self.assertEqual("Ungültiger Wert in folderId",
                         _serverwort(_Antwort({"error": "Ungültiger Wert in folderId"})))

    def test_eine_400_bringt_message_und_einzelheiten(self):
        """Schema InvalidData: message und errorStrings."""
        satz = _serverwort(_Antwort(
            {"message": "Anfrage unvollständig",
             "errorStrings": ["folderId fehlt", "autoRenameIfExist fehlt"]},
            status=400))
        self.assertIn("Anfrage unvollständig", satz)
        self.assertIn("folderId fehlt", satz)
        self.assertIn("autoRenameIfExist fehlt", satz)

    def test_ohne_jeden_satz_bleibt_es_still(self):
        """Nichts zu sagen ist besser als eine leere Zeile im Befund."""
        self.assertEqual("", _serverwort(_Antwort({})))
        self.assertEqual("", _serverwort(_Antwort(None, text="")))

    def test_eine_html_seite_ist_kein_satz(self):
        """Ein Anmeldeformular im Befund hilft niemandem."""
        self.assertEqual("", _serverwort(_Antwort(None, text="<html><body>Fehler")))

    def test_nackter_text_wird_genommen_wenn_es_kein_json_gibt(self):
        self.assertEqual("Method Not Allowed",
                         _serverwort(_Antwort(None, text="Method Not Allowed")))

    def test_zeilenumbrueche_zerreissen_den_befund_nicht(self):
        self.assertEqual("a b c", _serverwort(_Antwort({"error": "a\n  b\r\nc"})))

    def test_ein_langer_satz_wird_gekuerzt(self):
        satz = _serverwort(_Antwort({"error": "x" * 500}), grenze=50)
        self.assertEqual(50, len(satz))
        self.assertTrue(satz.endswith("…"))

    def test_der_hinweis_nennt_beide_bedeutungen(self):
        """Wer nur die eine liest, sucht wieder den Pfad."""
        self.assertIn("ungueltige Eingabe", HINWEIS_405)
        self.assertIn("diesen Weg gibt es nicht", HINWEIS_405)


class DerBefundSagtWoherDerSatzKommt(unittest.TestCase):

    def test_die_zusage_verspricht_nicht_mehr_als_sie_haelt(self):
        """Der Wortlaut kommt vom Server - das gehoert dazugesagt."""
        from pathlib import Path
        quelle = (Path(__file__).resolve().parent.parent
                  / "jusperfect" / "jurnodestest.py").read_text(encoding="utf-8")
        self.assertIn("der kommt von ihm, nicht von hier", quelle)
        self.assertNotIn("kein Akteninhalt - sie lässt sich weitergeben", quelle)


if __name__ == "__main__":
    unittest.main()
