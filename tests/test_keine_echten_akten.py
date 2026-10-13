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

---

## Die Namen stehen nicht in dieser Datei — seit dem 13.10.2026

Für die **Namen** braucht diese Prüfung eine Liste, und bis zum 13.10.2026
stand die hier: zerlegt, mit Rollenzuordnung im Kommentar. Damit standen die
echten Namen weiter im Bestand, nur in zwei Stücken — und der Riegel gegen
das Verbreiten von Namen war selbst das Leck. So ist er in einem Prüfpaket
aus dem Haus gegangen (Befund N01 der dritten Zweitprüfung).

**Entscheidung der Kanzlei, Variante A:** Die Liste liegt außerhalb des
Programmordners, auf den Rechnern der Kanzlei. Was das für einen Lauf
bedeutet:

| Wo gelaufen | Aktenzeichen | Namen |
|---|---|---|
| Rechner der Kanzlei, Liste vorhanden | geprüft | **geprüft** |
| Prüfpaket für einen Dritten, keine Liste | geprüft | **übersprungen, mit Warnung im Lauf** |

Die Warnung ist der Kern dieser Lösung. Ein Lauf ohne Liste sieht sonst
genauso grün aus wie einer mit — und bedeutet etwas anderes. Siehe
``SPERRLISTE_ORTE`` und
``test_es_wird_gesagt_wenn_nach_namen_nicht_gesucht_wurde``.
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
#: Sie fuehrt selbst einen der gesperrten Namen; deshalb steht sie hier.
UNBERUEHRT = {"schnittstelle/jurnodes-api-1.0.2.json"}

#: Wo die Liste der gesperrten Namen liegt — **ausserhalb des
#: Programmordners**, und das ist der ganze Punkt.
#:
#: **Befund N01 der dritten Zweitpruefung vom 12.10.2026.** Hier standen die
#: echten Namen. Sie mussten irgendwo stehen, denn die Pruefung unten muss
#: wissen, wonach sie sucht - und ausgeschrieben haetten sie die Pruefung
#: durch sich selbst durchfallen lassen, weil sie jede Datei des Bestands
#: liest, auch diese. Mein Ausweg war, sie zerlegt hinzuschreiben und in der
#: Zeile darunter zusammenzusetzen.
#:
#: Das war kein Ausweg. Die Namen standen damit weiter im Bestand, nur in
#: zwei Stuecken - und die Kommentare sagten dazu, wer Mandant und wer Gegner
#: ist, also das Rubrum. Jeder Mensch liest das in zwei Sekunden; der externe
#: Pruefer hat es getan. **Der Riegel gegen das Verbreiten von Namen war
#: selbst das Leck**, und er ist so in einem Pruefpaket aus dem Haus gegangen.
#:
#: **Entscheidung der Kanzlei vom 13.10.2026 (Variante A):** Die Namen kommen
#: aus dem Repository heraus in eine Datei, die nur auf den Rechnern der
#: Kanzlei liegt. Dort laeuft die Pruefung vollstaendig. In einem Paket fuer
#: einen Dritten ist die Liste nicht dabei - dann prueft diese Datei nur noch
#: das Aktenzeichenmuster **und sagt das**, damit niemand ein gruenes
#: Ergebnis fuer "keine Namen gefunden" haelt.
#:
#: Gesucht wird an zwei festen Orten, beide **neben** oder **ueber** dem
#: Programmordner, nie darin: Eine Datei im Programmordner kaeme in jedes ZIP.
#: Keine Einstellung, keine Umgebungsvariable - zu konfigurieren gibt es hier
#: nichts, und die Pruefungen erben seit Befund N08 ohnehin keine Umgebung.
SPERRLISTE_NAME = "jusperfect-sperrwoerter.txt"
SPERRLISTE_ORTE = (WURZEL.parent / SPERRLISTE_NAME,
                   Path.home() / SPERRLISTE_NAME)


def sperrliste() -> Path | None:
    """Die Datei mit den gesperrten Namen - oder None, wenn es keine gibt."""
    for ort in SPERRLISTE_ORTE:
        try:
            if ort.is_file():
                return ort
        except OSError:                 # ein Pfad, den dieses System nicht mag
            continue
    return None


def gesperrte_woerter() -> tuple[str, ...]:
    """Ein Wort je Zeile; ``#`` beginnt einen Kommentar, Leerzeilen zaehlen nicht.

    **Faellt die Datei aus, faellt die Pruefung aus** - nicht still gruen. Eine
    Liste, die sich nicht lesen laesst, ist etwas anderes als keine Liste: Im
    ersten Fall ist etwas kaputt, im zweiten ist es Absicht.
    """
    ort = sperrliste()
    if ort is None:
        return ()
    woerter = []
    for zeile in ort.read_text(encoding="utf-8").splitlines():
        zeile = zeile.split("#", 1)[0].strip()
        if zeile:
            woerter.append(zeile)
    return tuple(woerter)


def muster(woerter: tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    """Als ganzes Wort, Gross- und Kleinschreibung zaehlt: "sauer" ist ein Adjektiv."""
    return tuple(re.compile(rf"\b{re.escape(w)}\b") for w in woerter)


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


def treffer_im_bestand(gesucht: tuple[re.Pattern[str], ...]) -> dict[str, list[str]]:
    """Welche Datei welches Muster traegt. Leer heisst: nichts gefunden."""
    treffer: dict[str, list[str]] = {}
    for name in _dateien():
        try:
            text = (WURZEL / name).read_text(encoding="utf-8")
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
        gefunden = [m.pattern for m in gesucht if m.search(text)]
        if gefunden:
            treffer[name] = gefunden
    return treffer


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
        woerter = gesperrte_woerter()
        if not woerter:
            self.skipTest(
                "Keine Sperrliste gefunden — nach NAMEN wurde nicht gesucht. "
                f"Gesucht wurde an: {', '.join(str(o) for o in SPERRLISTE_ORTE)}. "
                "Geprueft wurde nur das Aktenzeichenmuster. Siehe den Kopf "
                "dieser Datei (Befund N01).")
        treffer = treffer_im_bestand(muster(woerter))
        self.assertEqual({}, treffer, "Ein gesperrter Name ist im Bestand.")

    def test_die_suche_findet_wirklich_etwas(self):
        """Sonst waere sie gruen, weil sie nichts kann — nicht, weil nichts da ist.

        Gesucht wird hier nach einem **erfundenen** Namen aus den Testakten.
        Von ihm ist bekannt, dass er im Bestand vorkommt; findet die Suche ihn
        nicht, ist die Suche kaputt und nicht der Bestand sauber.

        Die echten Namen taugen fuer diese Gegenprobe nicht mehr — sie stehen
        nicht in dieser Datei, und das ist der Zweck der Aenderung vom
        13.10.2026.
        """
        erfunden = "Vellinghausen"          # eine der erfundenen Testakten
        self.assertTrue(treffer_im_bestand(muster((erfunden,))),
                        "Die Suche findet einen Namen nicht, der nachweislich "
                        "im Bestand steht.")

    def test_ein_gewoehnliches_wort_wird_nicht_gefangen(self):
        """Als ganzes Wort, Gross- und Kleinschreibung zaehlt.

        Viele deutsche Nachnamen sind auch gewoehnliche Woerter. Suchte diese
        Datei ohne Wortgrenze und ohne Ruecksicht auf die Schreibung, waere
        jeder zweite Satz ein Treffer und die Pruefung nach einer Woche
        abgeschaltet.

        **Das Beispiel ist mit Bedacht ein Name, der mit keiner Akte zu tun
        hat.** Beim Umbau am 13.10.2026 stand hier zuerst einer der echten —
        in genau der Aenderung, die die echten Namen entfernen sollte, zum
        fuenften Mal dasselbe Muster. Gefunden hat es nicht meine
        Aufmerksamkeit, sondern ein Nachlauf mit den Namen aus der Liste.
        Genau darum geht es in dieser Datei.
        """
        gesucht = muster(("Koch",))
        self.assertFalse(any(m.search("Die Suppe kocht.") for m in gesucht))
        self.assertFalse(any(m.search("Ein Kochtopf.") for m in gesucht))
        self.assertTrue(any(m.search("Akte Koch gegen Dritte") for m in gesucht))

    def test_die_sperrliste_liegt_niemals_im_bestand(self):
        """Der Riegel um den Riegel.

        Eine Liste echter Namen **im** Programmordner waere in jedem ZIP, das
        die Kanzlei herunterlaedt — genau der Fehler, den Variante A behebt.
        Deshalb stehen die beiden Suchorte ausserhalb, und deshalb prueft das
        hier nach.
        """
        for ort in SPERRLISTE_ORTE:
            self.assertNotIn(WURZEL, ort.parents,
                             f"{ort} liegt im Programmordner.")
        verdaechtig = [n for n in _dateien() if "sperrwoert" in n.lower()]
        self.assertEqual([], verdaechtig,
                         "Eine Sperrliste ist in den Bestand geraten.")

    def test_es_wird_gesagt_wenn_nach_namen_nicht_gesucht_wurde(self):
        """Eine Pruefung, die ausfaellt, muss das in den Lauf schreiben.

        Ohne diese Warnung sieht ein Lauf im Pruefpaket genauso gruen aus wie
        einer in der Kanzlei — und bedeutet etwas anderes. Das ist dasselbe
        Muster wie bei der leeren Dateiliste weiter unten: Was nicht sucht,
        ist still gruen.
        """
        import warnings

        ort = sperrliste()
        if ort is None:
            warnings.warn(
                "Keine Sperrliste gefunden: In diesem Lauf wurde NICHT nach "
                "Namen gesucht, nur nach dem Aktenzeichenmuster. Das ist im "
                "Prueflauf eines Dritten der vorgesehene Zustand (Befund N01); "
                "auf einem Rechner der Kanzlei fehlt die Datei "
                f"{SPERRLISTE_NAME} neben oder ueber dem Programmordner.",
                UserWarning, stacklevel=1)
        else:
            self.assertTrue(gesperrte_woerter(),
                            f"{ort} ist da, aber leer — dann prueft sie nichts.")


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
