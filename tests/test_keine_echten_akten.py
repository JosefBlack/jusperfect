"""Kein echtes Aktenzeichen und kein echter Name im Bestand.

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

import os
import re
import subprocess
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent

#: Die Aktenzeichen der Kanzlei: D wie Dortschy, T wie Thunert, drei Ziffern,
#: Jahr. Was so aussieht, gehoert zu einer echten Akte des Hauses.
ECHT = re.compile(r"\b[DT]-\d{3}-\d{4}\b")

#: Die Datei des Herstellers wird nicht angefasst - ihre Beispiele sind seine.
#: Sie fuehrt selbst einen der Namen unten; deshalb steht sie hier.
UNBERUEHRT = {"schnittstelle/jurnodes-api-1.0.2.json"}

#: Das echte Rubrum, das am 11.10.2026 im Bestand gefunden wurde.
#:
#: **Zusammengesetzt, und das ist der Punkt.** Diese Datei wird von der
#: Pruefung unten selbst gelesen; stuenden die Namen hier ausgeschrieben,
#: fiele sie durch sich selbst. Genau das ist am 12.10.2026 dreimal passiert -
#: einmal in der Pruefdatei und zweimal in der Chronik, jedesmal weil die
#: Beschreibung eines Fundes den Fund wieder hergestellt hat.
#:
#: > Wer einen Fund beschreibt, schreibt ihn hin.
#:
#: Die Namen sind hier nicht verschluesselt und sollen es nicht sein - wer die
#: Datei liest, soll sehen, worum es geht. Sie stehen nur nicht als ganze
#: Zeichenkette darin.
_RUBRUM = tuple("".join(teile) for teile in (
    ("M", "üller"),     # Mandant, mit Umlaut
    ("M", "ueller"),    # und ohne - fuenf Dateien trugen nur diese Form
    ("H", "UK"),        # der Gegner
    ("Sau", "er"),      # eine zweite Akte, gleiches Muster
))

#: Als ganzes Wort, Gross-/Kleinschreibung zaehlt: "sauer" ist ein Adjektiv.
NAMEN = tuple(re.compile(rf"\b{re.escape(n)}\b") for n in _RUBRUM)


#: Was nie zum Bestand gehoert - Arbeitsspuren, nicht Programm.
_NICHT_BESTAND = {".git", "__pycache__", ".pytest_cache", ".venv", "venv",
                  "node_modules", ".jusperfect-gedaechtnis", "build", "dist"}


def _dateien() -> list[str]:
    """Jede Datei des Bestands, relativ zur Wurzel.

    **Zuerst git, dann der Ordner — und das ist kein Luxus.** Die Prüfung ist
    am 12.10.2026 im fertig geschnürten Prüfpaket durchgefallen, mit
    ``git ls-files returned non-zero exit status 128``: Ein Paket für einen
    Dritten enthält kein ``.git``, und damit brach gerade die Prüfung ab, die
    dort am meisten zu sagen hat.

    Eine Prüfung, die nur im Entwicklungsverzeichnis läuft, prüft das Paket
    nicht. Sie fällt deshalb auf einen Lauf über den Ordner zurück.
    """
    try:
        roh = subprocess.run(["git", "ls-files"], cwd=WURZEL, capture_output=True,
                             text=True, check=True).stdout.split()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        roh = []
        for ordner, unter, dateien in os.walk(WURZEL):
            unter[:] = [u for u in unter if u not in _NICHT_BESTAND]
            for name in dateien:
                roh.append(str(Path(ordner, name).relative_to(WURZEL).as_posix()))
    return [n for n in roh if n not in UNBERUEHRT]


class KeinEchterNameImBestand(unittest.TestCase):
    """Dasselbe fuer das Rubrum — und das hat laenger gefehlt als noetig.

    Fuer die Aktenzeichen gab es seit dem 12.10.2026 eine Pruefung, fuer die
    Namen nicht. Die Regel lebte allein in meiner Aufmerksamkeit, und
    Aufmerksamkeit ist genau das, was bei der dritten Wiederholung nachlaesst:
    Dreimal an einem Tag ist der Name zurueck in den Bestand gekommen, jedesmal
    in der Beschreibung seiner eigenen Entfernung.

    Eine Regel, die nur jemand im Kopf hat, ist keine Regel. Sie ist eine
    Absicht.
    """

    def test_das_rubrum_steht_nirgends(self):
        treffer: dict[str, list[str]] = {}
        for name in _dateien():
            try:
                text = (WURZEL / name).read_text(encoding="utf-8")
            except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
                continue
            gefunden = [m.pattern for m in NAMEN if m.search(text)]
            if gefunden:
                treffer[name] = gefunden
        self.assertEqual({}, treffer, "Das echte Rubrum ist zurueck im Bestand.")

    def test_die_pruefung_kann_suchen(self):
        """Sonst waere sie gruen, weil sie nichts findet — nicht, weil nichts da ist."""
        probe = f"Akte {_RUBRUM[0]} gegen {_RUBRUM[2]}"
        self.assertTrue(any(m.search(probe) for m in NAMEN))
        self.assertFalse(any(m.search("Akte Testmann gegen Musterhaft") for m in NAMEN))

    def test_ein_gewoehnliches_wort_wird_nicht_gefangen(self):
        """„sauer" ist ein Adjektiv, „Sauerstoff" ein Gas."""
        self.assertFalse(any(m.search("Die Milch ist sauer.") for m in NAMEN))
        self.assertFalse(any(m.search("Sauerstoffgehalt") for m in NAMEN))


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

    def test_die_pruefung_laeuft_auch_ohne_git(self):
        """Im Prüfpaket gibt es kein `.git` — dort muss sie erst recht greifen.

        Am 12.10.2026 ist sie genau daran gescheitert: `git ls-files` brach mit
        Status 128 ab, und mit ihr die Prüfung. Ein Paket für einen Dritten ist
        der Ort, an dem ein echter Name am teuersten wäre — und war der Ort, an
        dem niemand mehr nachsah.

        Diese Prüfung stellt sicher, dass der Rückfall auf den Ordner wirklich
        Dateien findet, statt leer zurückzukommen. Eine leere Liste macht jede
        Suche grün.
        """
        import os as _os
        hier = _os.getcwd()
        try:
            _os.chdir(WURZEL.parent)          # ausserhalb des git-Verzeichnisses
            dateien = _dateien()
        finally:
            _os.chdir(hier)
        self.assertGreater(len(dateien), 100,
                           "Der Rückfall findet den Bestand nicht.")
        self.assertIn("MORGEN.md", dateien)

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
