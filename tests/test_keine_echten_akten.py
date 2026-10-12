"""Kein echtes Aktenzeichen im Bestand — für den ganzen Programmordner.

**Entscheidung der Kanzlei vom 12.10.2026:** Die echten Aktenzeichen kommen
heraus, auch aus `MORGEN.md`.

Bis dahin standen sie dort mit Absicht: Sie trugen den Beleg. „X-100-2026 hat
26 Einträge, 22 Mails, 4 Vermerke" ist eine Messung, „eine Akte hat 26
Einträge" eine Behauptung. Das Argument war nicht falsch — es war nur das
schwächere. Der Bestand geht an Dritte (eine Zweitprüfung hat ihn schon
zweimal bekommen), und ein Aktenzeichen mit gemessenen Angaben ist eine
Aussage über ein bestimmtes Mandat, auch ohne Namen.

**Die Regel, in einem Satz:** Ein Aktenzeichen im Bestand beginnt mit `X`.

Die Kanzlei führt `D` (Dortschy) und `T` (Thunert). Ein `X` kann es dort nicht
geben — deshalb ist jede Nummer in diesem Bestand auf einen Blick als
erfunden zu erkennen, und diese Prüfung kann einen Rückfall messen statt ihn
zu erhoffen.

**Was sie nicht kann:** Ein Aktenzeichen, das in keinem der beiden Muster
steht, fällt ihr nicht auf — etwa „42/26 VU", die zweite Schreibweise des
Hauses. Die kommt in den erfundenen Testakten vor und ist dort erfunden; eine
echte in dieser Form würde hier durchgehen. Dagegen hilft nur Nachfragen, und
am 11.10.2026 hat genau das ein echtes Rubrum zutage gefördert.
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent

#: Die Aktenzeichen der Kanzlei: D wie Dortschy, T wie Thunert, drei Ziffern,
#: Jahr. Was so aussieht, gehoert zu einer echten Akte des Hauses.
ECHT = re.compile(r"\b[DT]-\d{3}-\d{4}\b")

#: Die Datei des Herstellers wird nicht angefasst - ihre Beispiele sind seine.
UNBERUEHRT = {"schnittstelle/jurnodes-api-1.0.2.json"}


def _dateien() -> list[str]:
    roh = subprocess.run(["git", "ls-files"], cwd=WURZEL, capture_output=True,
                         text=True, check=True).stdout.split()
    return [n for n in roh if n not in UNBERUEHRT]


class KeinEchtesAktenzeichenImBestand(unittest.TestCase):

    def test_nirgends_im_ganzen_programmordner(self):
        """Jede Datei, die git kennt — Quelltext, Unterlagen, Stapeldateien."""
        treffer: dict[str, set[str]] = {}
        for name in _dateien():
            try:
                text = (WURZEL / name).read_text(encoding="utf-8")
            except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
                continue
            gefunden = set(ECHT.findall(text))
            if gefunden:
                treffer[name] = gefunden
        self.assertEqual(
            {}, treffer,
            "Echte Aktenzeichen im Bestand. Ein Aktenzeichen beginnt hier mit "
            "X — die Kanzlei führt D und T.")

    def test_die_regel_faengt_eine_echte_nummer_wirklich(self):
        """Eine Prüfung, die nichts findet, muss zeigen, dass sie suchen kann.

        Ohne das wäre sie grün, auch wenn das Muster nie passt — und genau
        diese Art Prüfung war am 08.10.2026 einer der fünf Funde im Prüfbogen.

        **Die Probestücke sind zusammengesetzt und stehen nirgends als ganze
        Zeichenkette in dieser Datei.** Sonst fände die Prüfung oben sich
        selbst: Sie liest jede Datei, die git kennt, und diese gehört dazu.
        Genau das ist am 12.10.2026 geschehen — der erste Entwurf trug die
        Probestücke ausgeschrieben, lief grün, weil die Datei noch nicht in
        git war, und wäre beim nächsten Lauf rot geworden.
        """
        wie_dortschy = "D-" + "123" + "-2026"
        wie_thunert = "T-" + "456" + "-2025"
        self.assertTrue(ECHT.search(f"Der Lauf an {wie_dortschy} ergab"))
        self.assertTrue(ECHT.search(f"Thunert/2025/{wie_thunert} Name"))
        self.assertFalse(ECHT.search("Der Lauf an X-100-2026 ergab"),
                         "Eine erfundene Nummer darf sie nicht fangen.")
        self.assertFalse(ECHT.search("X-003-2025"))

    def test_der_vorsatz_x_wird_wirklich_benutzt(self):
        """Gegenprobe: Es gibt die erfundenen Nummern, sie sind nicht nur weg."""
        gefunden = set()
        for name in _dateien():
            try:
                gefunden |= set(re.findall(r"\bX-\d{3}-\d{4}\b",
                                           (WURZEL / name).read_text(encoding="utf-8")))
            except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
                continue
        self.assertGreater(len(gefunden), 5,
                           "Die Beispiele sollen Nummern tragen, nicht keine.")
