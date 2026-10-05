"""Ein Befund, der zugleich auf dem Schirm steht und in einer Datei liegt.

**Warum es diesen Baustein gibt.** Die Prüfprogramme der Kanzlei schrieben ihre
Ausgabe mit ``> datei.txt`` um und gaben sie danach mit ``type`` aus. Auf den
erfundenen Testakten dauert das den Bruchteil einer Sekunde und fällt nicht
auf. Am 23.09.2026, beim ersten Lauf auf dem echten Kanzleilaufwerk, hatte es
drei Folgen an einem Nachmittag:

1. **Der Schirm blieb minutenlang leer.** Wer den Pfad eingegeben hatte, sah
   nichts – keine Überschrift, keinen Haken, keine Fehlermeldung – und konnte
   nicht erkennen, ob das Programm arbeitet oder steht.
2. **Ein offenes Notepad blockierte die Datei.** Windows verweigerte die
   Umleitung („Der Prozess kann nicht auf die Datei zugreifen"), und der ganze
   Lauf war verloren, ohne dass eine Zeile davon zu sehen gewesen wäre.
3. **Die Datei blieb während des Laufs leer**, weil sie erst beim Schließen
   gefüllt wurde. Wer hineinsah, hielt den Lauf für misslungen.

Alle drei verschwinden, wenn das Programm den Befund selbst schreibt. Deshalb
steht das hier einmal und nicht in jeder Prüfdatei neu.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Iterator


class Doppelt:
    """Schreibt jede Zeile auf den Schirm und in den Bericht."""

    def __init__(self, schirm: IO[str], datei: IO[str]) -> None:
        self._schirm, self._datei = schirm, datei

    def write(self, text: str) -> int:
        self._datei.write(text)
        n = self._schirm.write(text)
        # Beides leeren, nicht nur den Schirm: sonst staut cmd die Ausgabe in
        # Blöcken, und die Datei füllt sich erst beim Schließen.
        self._schirm.flush()
        self._datei.flush()
        return n

    def flush(self) -> None:
        self._schirm.flush()
        self._datei.flush()


def nur_schirm() -> IO[str]:
    """Der Schirm allein – für Zwischenstände, die nicht in den Bericht gehören.

    Ein Lebenszeichen wie „… 5000 Dateien gesehen" gehört vor die Augen des
    Bearbeiters, nicht in eine Datei, die er weitergibt.
    """
    return getattr(sys.stdout, "_schirm", sys.stdout)


@contextmanager
def mitschreiben(bericht: str) -> Iterator[bool]:
    """Alles, was innerhalb geschrieben wird, geht auch in ``bericht``.

    Lässt sich die Datei nicht anlegen – sie ist in einem anderen Programm
    offen, der Ordner ist schreibgeschützt –, läuft die Prüfung **trotzdem**
    und nur ohne Datei. Das ist der Unterschied zur Umleitung durch Windows,
    die in diesem Fall den ganzen Lauf verwirft. Der Wert im ``with`` sagt, ob
    mitgeschrieben wird.
    """
    schirm = sys.stdout
    try:
        datei = Path(bericht).open("w", encoding="utf-8")
    except OSError as fehler:
        print(f"  !  Der Befund lässt sich nicht in {bericht} schreiben "
              f"({fehler.strerror}).")
        print("     Ist die Datei in einem anderen Programm geöffnet? Die")
        print("     Prüfung läuft trotzdem; der Text steht dann nur hier.")
        print()
        yield False
        return
    with datei:
        sys.stdout = Doppelt(schirm, datei)
        try:
            yield True
        finally:
            sys.stdout = schirm
