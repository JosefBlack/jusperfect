"""Lässt das Schutzgeländer die Sprache einer Akte durch?

Das ist die Probe, die vor der ersten echten Akte gefehlt hat. Der Selbsttest
sagte bisher nur, **dass** ein Guardrail hinterlegt ist – nicht, ob es brauchbar
eingestellt ist.

Die Gefahr ist einseitig. Die Voreinstellungen eines Bedrock-Guardrails sind für
Anwendungen gedacht, in denen Gewalt, Sexuelles und Beleidigungen nichts zu
suchen haben. In einer Kanzlei sind genau das die Fälle: Eine
Körperverletzungssache **ist** Gewalt, eine Beleidigungsklage muss die
Beleidigung wiedergeben dürfen. Ein zu scharf eingestellter Filter fällt nicht
dadurch auf, dass er etwas Falsches tut, sondern dadurch, dass eine gewöhnliche
Frage zu einer gewöhnlichen Akte mit einer Sperrmeldung endet – und zwar zum
ersten Mal vor einer echten Akte.

Ein Modell wird für diese Prüfungen nicht gebraucht.
"""

from __future__ import annotations

import unittest

from jusperfect.services.selbsttest import (GELAENDERPROBEN, GUT, SCHLECHT,
                                            gelaender_anprobieren)
from tests.hilfen import einstellungen


def _mit_gelaender(**zusatz):
    return einstellungen(JUSPERFECT_ANBIETER="bedrock",
                         JUSPERFECT_GUARDRAIL_ID="gr-1", **zusatz)


class WannGeprueftWird(unittest.TestCase):
    def test_ohne_gelaender_ist_die_frage_gegenstandslos(self):
        e = einstellungen(JUSPERFECT_ANBIETER="bedrock")
        self.assertEqual((), gelaender_anprobieren(e, anprobe=_nie))

    def test_ohne_modell_ebenfalls(self):
        """Der Demo-Anbieter rechnet auf dem Rechner; es gibt kein Geländer."""
        e = einstellungen(JUSPERFECT_ANBIETER="demo", JUSPERFECT_GUARDRAIL_ID="gr-1")
        self.assertEqual((), gelaender_anprobieren(e, anprobe=_nie))


class DieProbenSelbst(unittest.TestCase):
    def test_jedes_rechtsgebiet_wird_einzeln_geprueft(self):
        """Sammelt man sie in einen Satz, weiß niemand, welcher Filter zuschlug."""
        zeilen = gelaender_anprobieren(_mit_gelaender(), anprobe=_immer_durch)
        self.assertEqual(len(GELAENDERPROBEN), len(zeilen))
        for zeile in zeilen:
            self.assertEqual(GUT, zeile.zustand)
            self.assertIn("Durchgelassen", zeile.satz)

    def test_die_heiklen_gebiete_sind_dabei(self):
        gebiete = " ".join(g for g, _ in GELAENDERPROBEN)
        for gebiet in ("Körperverletzung", "Beleidigung", "Sexualstrafrecht",
                       "Kündigungsschutz"):
            with self.subTest(gebiet=gebiet):
                self.assertIn(gebiet, gebiete)

    def test_die_erste_probe_ist_die_kontrolle(self):
        """Geht schon der unverfängliche Satz nicht durch, liegt es nicht an
        den Inhaltsfiltern – dann stimmt etwas Grundlegenderes nicht."""
        gebiet, _ = GELAENDERPROBEN[0]
        self.assertIn("Kontrolle", gebiet)

    def test_die_proben_koennen_keine_akte_tragen(self):
        """Sie gehen an AWS. Erfunden müssen sie sein, und erfunden bleiben.

        Ein Test kann nicht erkennen, ob jemand später echten Aktentext
        einträgt. Er kann aber die Merkmale ausschliessen, an denen so etwas
        zuerst auffällt – und die Sätze kurz halten: Ein Satz von hundert
        Zeichen trägt keinen Fall.
        """
        for gebiet, satz in GELAENDERPROBEN:
            with self.subTest(gebiet=gebiet):
                self.assertNotIn("@", satz, "E-Mail-Adresse")
                self.assertNotRegex(satz, r"\d{1,2}\.\d{1,2}\.\d{4}", "Datum")
                self.assertNotRegex(satz, r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,}", "IBAN")
                self.assertNotRegex(satz, r"\b\d{5}\b", "Postleitzahl")
                self.assertLessEqual(len(satz), 120, "zu lang für eine Probe")

    def test_die_proben_stehen_fest_im_quelltext(self):
        """Keine Datei, keine Einstellung: Was hinausgeht, ist nachlesbar."""
        self.assertIsInstance(GELAENDERPROBEN, tuple)
        for eintrag in GELAENDERPROBEN:
            self.assertIsInstance(eintrag, tuple)
            self.assertEqual(2, len(eintrag))


class WennEsAngehaltenWird(unittest.TestCase):
    def test_die_meldung_sagt_was_zu_tun_ist(self):
        zeilen = gelaender_anprobieren(_mit_gelaender(), anprobe=_immer_blockiert)
        for zeile in zeilen:
            self.assertEqual(SCHLECHT, zeile.zustand)
            self.assertIn("zu scharf", zeile.satz)
            self.assertIn("AWS-EINRICHTEN.md", zeile.satz)

    def test_gesperrt_und_nicht_gefragt_sind_zwei_verschiedene_saetze(self):
        """Sie verlangen Verschiedenes: das eine eine Einstellung, das andere
        ein Recht. Wer beides in einem Satz liest, stellt falsch nach."""
        gesperrt = gelaender_anprobieren(_mit_gelaender(), anprobe=_immer_blockiert)
        self.assertIn("Vom Geländer angehalten", gesperrt[0].satz)
        self.assertIn("zu scharf", gesperrt[0].satz)

        ohne_recht = gelaender_anprobieren(_mit_gelaender(), anprobe=_kein_recht)
        self.assertEqual(SCHLECHT, ohne_recht[0].zustand)
        self.assertIn("Nicht geprüft", ohne_recht[0].satz)
        self.assertIn("bedrock:ApplyGuardrail", ohne_recht[0].satz)
        self.assertNotIn("zu scharf", ohne_recht[0].satz,
                         "Ein fehlendes Recht ist kein zu scharfer Filter.")

    def test_der_satz_selbst_steht_in_der_zeile(self):
        """Damit man sieht, WAS angehalten wurde - sonst rät man am Filter."""
        zeilen = gelaender_anprobieren(_mit_gelaender(), anprobe=_immer_blockiert)
        _, satz = GELAENDERPROBEN[0]
        self.assertIn(satz, zeilen[0].arbeit)


class WomitGepruegtWird(unittest.TestCase):
    def test_das_modell_der_frage_wird_benutzt(self):
        """Dasselbe Modell wie im Betrieb - sonst prüft die Probe etwas anderes."""
        gesehen: list[tuple] = []

        def merken(region, kennung, gr_id, gr_version, text):
            gesehen.append((region, kennung, gr_id, gr_version))
            return True, ""

        e = _mit_gelaender(JUSPERFECT_MODELL_FRAGE="anthropic.claude-opus-4-6-v1")
        gelaender_anprobieren(e, anprobe=merken)
        for region, kennung, gr_id, gr_version in gesehen:
            self.assertEqual("eu-central-1", region)
            self.assertEqual("eu.anthropic.claude-opus-4-6-v1", kennung)
            self.assertEqual("gr-1", gr_id)
            self.assertEqual("DRAFT", gr_version)


def _immer_durch(*_args):
    return True, ""


def _immer_blockiert(*_args):
    from jusperfect.modelle import GESPERRT
    return False, GESPERRT


def _kein_recht(*_args):
    return False, "der Zugriffsrichtlinie fehlt bedrock:ApplyGuardrail"


def _nie(*_args):  # pragma: no cover - darf nicht aufgerufen werden
    raise AssertionError("Ohne Geländer oder ohne Modell darf nichts gefragt werden.")


if __name__ == "__main__":
    unittest.main()
