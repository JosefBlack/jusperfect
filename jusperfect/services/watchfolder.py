"""Beobachteter Ordner: Dateien kommen herein, ohne dass jemand sie auswählt.

Aus Perfect Shield übernommen. Gedacht für einen Ordner, den die Cloud selbst
füllt – ein eingebundenes WebDAV-Laufwerk, ein OneDrive- oder Nextcloud-Ordner.
jusperfect spricht dabei mit keinem Anbieter: Es sieht nur einen Pfad im
Dateisystem, den Transport erledigt das Betriebssystem.

Zwei Eigenheiten solcher Ordner bestimmen den Aufbau:

* Eine Datei erscheint oft schon, während sie noch übertragen wird. Wer sofort
  liest, bekommt ein halbes Dokument. Deshalb gilt eine Datei erst als bereit,
  wenn ihre Größe über zwei Durchgänge hinweg gleich geblieben ist.
* Der Ordner gehört der Kanzlei, nicht diesem Programm. Es wird nichts
  verschoben, umbenannt oder gelöscht; die einzige Spur ist eine Statusdatei.

Und die wichtigste Festlegung, die von Perfect Shield bleibt: Der Ordner
bereitet einen Vorgang nur vor. Was damit geschieht, entscheidet ausschließlich
ein Mensch. Ein Ablauf, der ein eingehendes Dokument automatisch prüfte,
beantwortete oder gar zurückschriebe, überspränge genau die Kontrolle, auf der
das Werkzeug beruht.

Dieses Modul ist bewusst reine Rechnerei ohne eigene Uhr und ohne Schleife –
`scan` bekommt den Zeitpunkt und den Stand des vorigen Durchgangs übergeben und
gibt den neuen Stand zurück. Das macht die Stabilitätsprüfung prüfbar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

STATUS_DATEI = "_jusperfect-status.txt"

# So lange muss die Größe unverändert bleiben, bevor eine Datei als vollständig
# übertragen gilt.
STABIL_SEKUNDEN = 5.0


@dataclass(frozen=True, slots=True)
class GeseheneDatei:
    """Was von einer Datei zwischen zwei Durchgängen gemerkt wird."""

    groesse: int
    zuerst_gesehen: float


@dataclass(frozen=True, slots=True)
class Durchgang:
    bereit: tuple[Path, ...]
    wartend: tuple[Path, ...]
    gesehen: dict[str, GeseheneDatei]


def scan(
    ordner: Path,
    endungen: frozenset[str],
    gesehen: dict[str, GeseheneDatei],
    verarbeitet: frozenset[str],
    jetzt: float,
    stabil_sekunden: float = STABIL_SEKUNDEN,
) -> Durchgang:
    """Sucht Dateien, die vollständig übertragen und noch nicht eingelesen sind.

    ``gesehen`` trägt den Stand des vorigen Durchgangs und wird als neuer Stand
    zurückgegeben; ``verarbeitet`` sind die Dateien, die jusperfect schon kennt.
    """
    bereit: list[Path] = []
    wartend: list[Path] = []
    aktuell: dict[str, GeseheneDatei] = {}

    for eintrag in sorted(ordner.iterdir()):
        if not eintrag.is_file() or eintrag.name == STATUS_DATEI:
            continue
        if eintrag.suffix.lower() not in endungen:
            continue
        schluessel = eintrag.name
        if schluessel in verarbeitet:
            continue
        try:
            groesse = eintrag.stat().st_size
        except OSError:
            # Während der Übertragung kann eine Datei kurzzeitig unlesbar sein.
            continue
        if groesse == 0:
            wartend.append(eintrag)
            aktuell[schluessel] = GeseheneDatei(groesse=groesse, zuerst_gesehen=jetzt)
            continue

        vorher = gesehen.get(schluessel)
        if vorher is None or vorher.groesse != groesse:
            # Erstmals gesehen oder noch am Wachsen: Uhr neu starten.
            aktuell[schluessel] = GeseheneDatei(groesse=groesse, zuerst_gesehen=jetzt)
            wartend.append(eintrag)
            continue

        aktuell[schluessel] = vorher
        if jetzt - vorher.zuerst_gesehen >= stabil_sekunden:
            bereit.append(eintrag)
        else:
            wartend.append(eintrag)

    return Durchgang(bereit=tuple(bereit), wartend=tuple(wartend), gesehen=aktuell)


def status_text(ordner: Path, vorbereitet: int, wartend: int, fehler: dict[str, str],
                geprueft_am: datetime) -> str:
    """Der Text der Statusdatei im Ordner.

    Bewusst ohne Inhalte: Die Datei liegt in der Cloud und wird von jedem
    gelesen, der Zugriff auf den Ordner hat. Nur Dateinamen, die dort ohnehin
    sichtbar sind, und der Stand der Verarbeitung.
    """
    zeilen = [
        "jusperfect – Stand des Posteingangs",
        f"Ordner:   {ordner}",
        f"Geprüft:  {geprueft_am.strftime('%d.%m.%Y %H:%M:%S')}",
        "",
        f"Vorbereitet und wartet auf Prüfung: {vorbereitet}",
        f"Noch in Übertragung:                {wartend}",
    ]
    if fehler:
        zeilen.append("")
        zeilen.append("Nicht eingelesen:")
        zeilen.extend(f"  {name}: {grund}" for name, grund in sorted(fehler.items()))
    zeilen += [
        "",
        "WICHTIG: Vorbereitet heißt nicht bearbeitet. Jedes eingegangene Dokument",
        "wird in jusperfect von einem Menschen geöffnet und geprüft; nichts wird",
        "automatisch beantwortet, entworfen oder in die Akte geschrieben.",
        "",
        "Diese Datei wird von jusperfect geschrieben und bei jedem Durchgang",
        "überschrieben.",
    ]
    return "\n".join(zeilen) + "\n"


def status_schreiben(ordner: Path, text: str) -> None:
    """Schreibt die Statusdatei; ein Fehler darf den Durchgang nicht anhalten."""
    try:
        (ordner / STATUS_DATEI).write_text(text, encoding="utf-8")
    except OSError:
        pass
