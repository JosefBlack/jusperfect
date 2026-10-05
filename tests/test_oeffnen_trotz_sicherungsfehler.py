"""Ein misslungenes Sichern darf das Öffnen einer Akte nicht verhindern.

Am 25.09.2026 tat es genau das. jur|nodes ersetzt eine vorhandene Datei
nicht; beim Öffnen legt das Programm das Gedächtnis aber neu ab, um den
Aktenstatus nachzuziehen. Das schlug fehl - und der Fehler riss das ganze
Öffnen mit.

Aus der Kanzlei: "die Arbeitsfläche öffnet sich nicht, sondern die
Fehlermeldung wird wieder angezeigt." Und die Meldung handelte vom ABLEGEN,
während der Bearbeiter eine Akte ÖFFNEN wollte.

Das Aktengedächtnis ist eine Arbeitshilfe, keine Bedingung. Geht es nicht,
wird die Akte neu eingelesen - das kostet Geld und keine Arbeit.
"""

from __future__ import annotations

import unittest
from unittest import mock

from jusperfect.domain.models import Aktengedaechtnis, Sitzung, Akte
from jusperfect.gedaechtnis.base import GedaechtnisFehler
from jusperfect.services.gedaechtnis import Gedaechtnisdienst


class _SpeicherDerNichtAblegenKann:
    """Verhält sich wie jur|nodes mit einer bereits vorhandenen Datei."""

    def __init__(self, gedaechtnis: Aktengedaechtnis) -> None:
        self._g = gedaechtnis
        self.versuche = 0

    def lesen(self, akte_id: str) -> Aktengedaechtnis:
        return self._g

    def ablegen(self, g: Aktengedaechtnis) -> None:
        self.versuche += 1
        raise GedaechtnisFehler(
            "In dieser Akte liegt bereits ein Aktengedächtnis, und jur|nodes "
            "ersetzt eine vorhandene Datei nicht.")

    def auflisten(self):
        return [self._g]

    def loeschen(self, akte_id: str) -> None:
        raise GedaechtnisFehler("löscht nichts")


def _dienst(speicher):
    """Der echte Dienst mit einem Speicher, der nicht ablegen kann.

    Zusammengesetzt wie im Betrieb - dieselben Feldnamen, sonst prueft die
    Probe etwas anderes als den Betrieb.
    """
    from jusperfect.config import Einstellungen

    return Gedaechtnisdienst(speicher, mock.MagicMock(), mock.MagicMock(),
                             Einstellungen.aus_umgebung({}))


class DasOeffnenGehtWeiter(unittest.TestCase):

    def setUp(self) -> None:
        self.g = Aktengedaechtnis(akte_id="rec-1", aktenstatus="laufend")
        self.speicher = _SpeicherDerNichtAblegenKann(self.g)
        self.dienst = _dienst(self.speicher)
        self.sitzung = Sitzung(
            id="s1", nutzer_id="ra-weber", akte_id="rec-1",
            akte=Akte(id="rec-1", aktenzeichen="X-106-2025",
                      bezeichnung="Probe", status="archiviert"))

    def test_die_akte_geht_auf_obwohl_das_sichern_scheitert(self):
        """Der eigentliche Fehler: Die Ausnahme riss das Öffnen mit."""
        with mock.patch.object(Gedaechtnisdienst, "_status_synchronisieren",
                               return_value=True):
            sitzung = self.dienst.bei_eroeffnen(self.sitzung)
        self.assertIsNotNone(sitzung)
        self.assertEqual("rec-1", sitzung.akte_id)
        self.assertEqual(1, self.speicher.versuche, "Es wurde nicht versucht.")

    def test_der_fehlschlag_wird_nicht_verschwiegen(self):
        """Was nicht da ist, fällt nicht auf - also steht er als Hinweis da."""
        with mock.patch.object(Gedaechtnisdienst, "_status_synchronisieren",
                               return_value=True):
            sitzung = self.dienst.bei_eroeffnen(self.sitzung)
        self.assertTrue(sitzung.hinweise, "Kein Hinweis auf den Fehlschlag.")
        hinweis = " ".join(sitzung.hinweise)
        self.assertIn("nicht gesichert", hinweis)

    def test_der_hinweis_sagt_dass_nichts_verloren_geht(self):
        """Das ist die Frage, die der Bearbeiter in dem Moment hat."""
        with mock.patch.object(Gedaechtnisdienst, "_status_synchronisieren",
                               return_value=True):
            sitzung = self.dienst.bei_eroeffnen(self.sitzung)
        hinweis = " ".join(sitzung.hinweise)
        self.assertIn("Die Arbeit geht weiter", hinweis)
        self.assertIn("neu eingelesen", hinweis)

    def test_ohne_aenderung_wird_gar_nicht_erst_abgelegt(self):
        """Der Regelfall: Nichts hat sich geändert, also nichts zu sichern."""
        with mock.patch.object(Gedaechtnisdienst, "_status_synchronisieren",
                               return_value=False):
            sitzung = self.dienst.bei_eroeffnen(self.sitzung)
        self.assertEqual(0, self.speicher.versuche)
        self.assertEqual([], sitzung.hinweise)


class AuchDasLesenBrichtNichtAb(unittest.TestCase):

    def test_ein_altes_gedaechtnis_laesst_sich_lesen_ohne_sichern(self):
        """Die Nummern werden beim Lesen festgeschrieben - auch das darf
        nicht das Lesen selbst zum Scheitern bringen."""
        g = Aktengedaechtnis(akte_id="rec-1")
        speicher = _SpeicherDerNichtAblegenKann(g)
        dienst = _dienst(speicher)
        with mock.patch.object(Gedaechtnisdienst, "_nummern_sichern",
                               return_value=True):
            gelesen = dienst.lesen("rec-1")
        self.assertIsNotNone(gelesen)
        self.assertEqual("rec-1", gelesen.akte_id)
        self.assertIn("ersetzt eine vorhandene Datei nicht",
                      dienst._letzter_sicherungsfehler)


if __name__ == "__main__":
    unittest.main()
