"""Baut die beiden ZIP-Dateien, die aus diesem Ordner herausgehen.

    python werkzeug/pakete_bauen.py <zielordner>

**Zwei Pakete, weil sie an zwei verschiedene Stellen gehen.**

1. ``jusperfect-2.0-TT.MM.JJJJ.zip`` — fuer die Rechner der Kanzlei. Alles,
   was im Zweig liegt.
2. ``jusperfect-pruefpaket-TT.MM.JJJJ.zip`` — fuer eine zweite Meinung. **Ohne
   die Unterlagen, die Bildschirmausdrucke der AWS-Konsole der Kanzlei
   enthalten.** Der Wortlaut dieser Unterlagen liegt als Markdown bei; die
   Bilder braucht eine Pruefung des Programms nicht, und was nicht gebraucht
   wird, geht auch nicht hinaus.

Gepackt wird, was ``git ls-files`` nennt - also nur Versioniertes. Was
nebenbei im Ordner liegt (Briefbogen der Kanzlei, Sperrliste, Arbeitskopien),
ist damit sicher nicht dabei.
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent

#: Was dem Pruefpaket nicht beigelegt wird. Es sind die gesetzten Fassungen
#: des Aktenvermerks und seiner Anlagen: Sie zeigen die AWS-Konsole der
#: Kanzlei. Der Wortlaut steht in VERMERK-AWS-*.md und EINWEISUNG.md.
NICHT_INS_PRUEFPAKET = (".docx", ".pdf")

#: Steht als erste Datei im Pruefpaket und nimmt die Frage vorweg, womit man
#: anfaengt.
ZUERST = """# Zuerst lesen

Dieses Paket ist die Bitte um eine zweite Meinung zu **jusperfect**, einem
Programm fuer die Aktenarbeit einer deutschen Rechtsanwaltskanzlei.

**Die Reihenfolge:**

1. `PRUEFPAKET-{datum}.md` — der Stand dieses Arbeitstages und die Fragen,
   auf die es ankommt. **Hier anfangen.**
2. `PRUEFAUFTRAG.md` — der Rahmen: worum es geht, welche Zusagen das Programm
   gibt, was die erste Zweitpruefung gefunden hat. Nur noetig, wenn jusperfect
   unbekannt ist.
3. `PRUEFAKTE-13.10.2026.md` — der Vortag.

Das Programm liegt in `jusperfect/`, die Pruefungen in `tests/`. Quelltext,
Kommentare und Fehlertexte sind **deutsch**; das ist Absicht und kein Fund.

**Nicht in diesem Paket:** die gesetzten Fassungen des Aktenvermerks und
seiner Anlagen. Sie zeigen die AWS-Konsole der Kanzlei und werden fuer eine
Pruefung des Programms nicht gebraucht. Ihr Wortlaut liegt als Markdown bei.
"""


def versionierte_dateien() -> list[str]:
    roh = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=WURZEL, capture_output=True, text=True, check=True,
    ).stdout
    return [n for n in roh.split("\0") if n]


def packen(ziel: Path, dateien: list[str], ordner: str, zuerst: str = "") -> Path:
    ziel.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as paket:
        if zuerst:
            paket.writestr(f"{ordner}/00-ZUERST-LESEN.md", zuerst)
        for name in dateien:
            paket.write(WURZEL / name, f"{ordner}/{name}")
    return ziel


def main() -> int:
    zielordner = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    heute = date.today().strftime("%d.%m.%Y")
    alle = versionierte_dateien()

    voll = packen(
        zielordner / f"jusperfect-2.0-{heute}.zip",
        alle,
        f"jusperfect-2.0-{heute}",
    )

    fuer_pruefung = [n for n in alle if Path(n).suffix.lower() not in NICHT_INS_PRUEFPAKET]
    pruefpaket = packen(
        zielordner / f"jusperfect-pruefpaket-{heute}.zip",
        fuer_pruefung,
        f"jusperfect-pruefpaket-{heute}",
        ZUERST.format(datum=heute),
    )

    for pfad, anzahl in ((voll, len(alle)), (pruefpaket, len(fuer_pruefung))):
        print(f"{pfad.name}: {anzahl} Dateien, {pfad.stat().st_size / 1_048_576:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
