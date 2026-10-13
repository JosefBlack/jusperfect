"""Ein Kreuz, das dasteht und nichts tut, ist schlimmer als keines.

Aus der Kanzlei am 13.10.2026, zu einem Hinweis über nicht lesbare Dokumente:

    Fehlermeldung nimmt viel Platz weg und läßt sich nicht schließen. Auch
    nicht mit dem Kreuz.

Beide Schließkreuze — der über dem Arbeitsstand und der über der Bilanz des
Einlesens — bekamen ihren Anschluss **innerhalb von `if (AWS_MODUS)`**. Die
Kanzlei läuft mit `JUSPERFECT_BETRIEBSART=lokal`; dort ist `AWS_MODUS` falsch,
und die Kreuze waren tot.

Wie sie dort hineingerieten: Der Block begann mit der Anmeldung, und was
später dazukam, wurde darunter geschrieben.

> Eine Einrückung ist kein Zusammenhang.

Man klickt so ein Kreuz, nichts geschieht, und man zweifelt an sich statt am
Programm. Deshalb prüft diese Datei nicht nur, **dass** die Kreuze
angeschlossen sind, sondern dass **kein** Anschluss für etwas, das jeder
Betriebsart gehört, in diesem Block steht.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"


class _Quelle(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.js = (STATISCH / "app.js").read_text(encoding="utf-8")
        cls.html = (STATISCH / "index.html").read_text(encoding="utf-8")
        anfang = cls.js.index("  if (AWS_MODUS) {\n    $(\"anmelden-aws\")")
        cls.vor = cls.js[:anfang]
        cls.block = cls.js[anfang:]


class DieKreuzeSindAngeschlossen(_Quelle):
    def test_beide_stehen_im_bild(self):
        for kennung in ("arbeitsstand-zu", "uebernahme-zu"):
            with self.subTest(knopf=kennung):
                self.assertIn(f'id="{kennung}"', self.html)

    def test_beide_bekommen_ihren_anschluss(self):
        for kennung in ("arbeitsstand-zu", "uebernahme-zu"):
            with self.subTest(knopf=kennung):
                self.assertRegex(
                    self.js, rf'\$\("{kennung}"\)[\s\S]{{0,160}}addEventListener')

    def test_und_zwar_ausserhalb_der_anmeldung(self):
        """Das war der ganze Fehler."""
        for kennung in ("arbeitsstand-zu", "uebernahme-zu"):
            with self.subTest(knopf=kennung):
                self.assertIn(kennung, self.vor,
                              "Steht noch im AWS-Block und ist damit in der "
                              "Betriebsart der Kanzlei tot.")


class KeinSchliessknopfHaengtAnDerAnmeldung(_Quelle):
    """Die enge Regel, die den Fehler verhindert - und sonst nichts.

    Der AWS-Block darf Anmeldesachen enthalten; das ist sein Zweck. Was er
    nicht enthalten darf, sind Knöpfe, die in JEDER Betriebsart gebraucht
    werden. Die Schließkreuze tragen alle die Endung "-zu" - daran lässt sich
    das prüfen, ohne den ganzen Block zu bewerten.
    """

    def test_kein_knopf_mit_endung_zu_steht_darin(self):
        bis = self.block.index("\n  }\n")
        innen = self.block[:bis]
        gefunden = re.findall(r'\$\("([a-z0-9-]+-zu)"\)', innen)
        self.assertEqual(gefunden, [], gefunden)

    def test_und_die_bekannten_zwei_stehen_davor(self):
        for kennung in ("arbeitsstand-zu", "uebernahme-zu"):
            with self.subTest(knopf=kennung):
                self.assertIn(f'$("{kennung}")', self.vor)


if __name__ == "__main__":
    unittest.main()
