"""Das Aktengedächtnis gepackt ablegen – ohne dass ein Zeichen verloren geht.

Aus der Kanzlei: „Problem ist, dass der Serverspeicher sehr teuer ist."

Ein Aktengedächtnis ist JSON: viel wiederkehrende Struktur, viel Fließtext aus
Schriftsätzen, viele gleiche Wendungen. Das lässt sich verlustfrei packen. Bei
der großen Testakte schrumpft die Ablage von 1.064 auf 67 Kilobyte; bei echten
Schriftsätzen ist eher mit einem Viertel bis einem Sechstel zu rechnen, weil
maschinell erzeugter Fülltext sich besser packen lässt als gewachsener.

Gepackt wird beim Ablegen, entpackt beim Lesen. Fachlich ändert sich nichts:
Dieselben Felder, dieselben Fundstellen, dieselbe Prüfung durch das Modell.

**Alte Ablagen bleiben lesbar.** `entpacken` erkennt an den ersten beiden Bytes,
ob etwas gepackt ist, und liest ungepackte Ablagen unverändert weiter. Ein
Gedächtnis, das vor dieser Änderung entstanden ist, muss deshalb nicht
umgewandelt werden – es wird beim nächsten Speichern von selbst gepackt.
"""

from __future__ import annotations

import gzip

from jusperfect.domain.models import Aktengedaechtnis
from jusperfect.gedaechtnis.base import GedaechtnisFehler

# Die Kennung, an der sich eine gepackte Datei erkennen lässt (RFC 1952).
GZIP_KENNUNG = b"\x1f\x8b"

# Höchste Stufe. Ein Aktengedaechtnis ist im schlimmsten Fall gut ein Megabyte;
# das Packen dauert dann Millisekunden, waehrend das Einlesen der Akte Minuten
# braucht. Der Speicher ist hier die knappe Groesse, nicht die Rechenzeit.
STUFE = 9


def ist_gepackt(rohdaten: bytes) -> bool:
    return rohdaten[:2] == GZIP_KENNUNG


def packen(gedaechtnis: Aktengedaechtnis) -> bytes:
    """Ein Aktengedächtnis in die Form bringen, in der es abgelegt wird."""
    roh = gedaechtnis.model_dump_json().encode("utf-8")
    # mtime=0: Zweimal dasselbe Gedaechtnis ergibt dieselben Bytes. Sonst
    # truege jede Ablage die Uhrzeit im Kopf, und zwei inhaltsgleiche Staende
    # saehen verschieden aus - laestig bei jedem Vergleich und jeder Sicherung.
    return gzip.compress(roh, STUFE, mtime=0)


def entpacken(rohdaten: bytes) -> Aktengedaechtnis:
    """Gelesene Bytes zurück in ein Aktengedächtnis – gepackt oder nicht."""
    if ist_gepackt(rohdaten):
        try:
            rohdaten = gzip.decompress(rohdaten)
        except Exception as e:
            raise GedaechtnisFehler(
                f"Das Aktengedächtnis ist gepackt, lässt sich aber nicht entpacken "
                f"({type(e).__name__})."
            ) from e
    return Aktengedaechtnis.model_validate_json(rohdaten)
