"""Erzeugt Beispielfaelle fuer die Ansicht „Aufbewahrung".

Aus der Kanzlei: "So ganz versteh ich die Aufbewahrung noch nicht. Kannst Du
mir mal zum Beispiel Test machen, die genau dort hineinkommen wuerden?"

Die Ansicht zeigt Arbeitsbereiche, in denen jusperfect **nicht selbst
entscheiden darf**. Solche Faelle entstehen im Alltag selten und dann meist
unbemerkt - genau deshalb gibt es die Liste. Zum Kennenlernen taugt sie so
allerdings nicht: Man muesste warten, bis von allein etwas schiefgeht.

Dieses Werkzeug baut den Zustand nach. Es legt eine eigene, kleine Welt an -
eigene Akten, eigenes Aktengedaechtnis - und ruehrt die vorhandenen Testakten
nicht an. Danach laesst sich die Ansicht oeffnen und Zeile fuer Zeile
nachvollziehen.

Alle Namen und Sachverhalte sind erfunden.

Aufruf:  python3 werkzeug/aufbewahrung_beispiele.py [zielordner]
Windows: AUFBEWAHRUNG-BEISPIELE.bat
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jusperfect.domain.models import (  # noqa: E402
    Aktengedaechtnis, GedaechtnisAntwort, GedaechtnisDokument, Quelle, Seite,
)
from jusperfect.gedaechtnis.lokal import LokalerGedaechtnisSpeicher  # noqa: E402

JETZT = datetime.now(timezone.utc)

# Jeder Fall: (Kennung, Aktenzeichen, Bezeichnung, Status in jurnodes,
#              Vormerkung, was dabei herauskommen soll)
#
# Der Status in jurnodes steht im Ordner der Akte; die Vormerkung steht im
# Aktengedaechtnis. Aus dem Zusammenspiel beider ergibt sich der Befund - und
# genau das ist der Punkt, den die Ansicht sichtbar macht.
FAELLE = [
    ("MV-2026-0101", "101/26 MV", "Rossmann ./. Delfs – Mietrückstand",
     "offen", None,
     "Nichts zu tun. Das Mandat läuft; der Arbeitsbereich bleibt."),

    ("VU-2026-0102", "102/26 VU", "Brammer ./. Ostsee-Versicherung – Auffahrunfall",
     "abgeschlossen", None,
     "Abschlussreif ohne Vormerkung: In jur|nodes ist die Akte abgeschlossen, "
     "in jusperfect liegt der Arbeitsbereich noch offen da."),

    ("AR-2026-0103", "103/26 AR", "Nowotny ./. Hafenlogistik Bremerhaven – Kündigungsschutz",
     "archiviert", JETZT + timedelta(days=12),
     "Abschluss vorgemerkt: Die Übergangsfrist läuft noch zwölf Tage."),

    ("BA-2025-0104", "104/25 BA", "Kettler ./. Dachbau Sievers – Werkmängel",
     "abgeschlossen", JETZT - timedelta(days=3),
     "Löschung fällig: Die Übergangsfrist ist abgelaufen, der Abschluss kann ausgeführt werden."),

    ("SC-2026-0105", "105/26 SC", "Lührs ./. Wohnbau Nord – Eigenbedarf",
     "", None,
     "Status unbekannt: jur|nodes meldet keinen Status – es wird nichts gelöscht."),

    # Kein Aktenordner: Die Akte ist in jurnodes nicht mehr auffindbar.
    ("VU-2024-0106", "106/24 VU", "Peschke ./. Fahrschule Kranz – Vorfahrtsverletzung",
     None, None,
     "Akte verwaist: Zu diesem Arbeitsbereich gibt es in jur|nodes keine Akte mehr."),
]

BEISPIELTEXT = (
    "Aktenvermerk\n\n"
    "Dies ist ein erfundener Beispieltext. Er steht hier nur, damit der\n"
    "Arbeitsbereich einen Umfang hat und die Ansicht Zahlen zeigen kann.\n"
)


def erzeugen(ziel: Path) -> list[tuple[str, str]]:
    akten = ziel / "akten"
    gedaechtnis = ziel / "gedaechtnis"
    for ordner in (akten, gedaechtnis):
        if ordner.exists():
            shutil.rmtree(ordner)
        ordner.mkdir(parents=True)

    speicher = LokalerGedaechtnisSpeicher(gedaechtnis)
    erklaerungen: list[tuple[str, str]] = []

    for kennung, aktenzeichen, bezeichnung, status, vormerkung, erklaerung in FAELLE:
        if status is not None:
            ordner = akten / kennung
            ordner.mkdir()
            (ordner / "01_aktenvermerk.txt").write_text(BEISPIELTEXT, encoding="utf-8")
            (ordner / "akte.json").write_text(json.dumps({
                "akte": {"id": kennung, "aktenzeichen": aktenzeichen, "bezeichnung": bezeichnung,
                         "rechtsgebiet": "Beispiel", "sachbearbeiter": "RA Dr. Weber",
                         "status": status},
                "dokumente": [{"id": "D-001", "titel": "Aktenvermerk",
                               "dateiname": "01_aktenvermerk.txt",
                               "datum": "2026-01-15", "kategorie": "Mandant"}],
                "beteiligte": [], "fristen": [],
            }, ensure_ascii=False, indent=2), encoding="utf-8")

        g = Aktengedaechtnis(
            akte_id=kennung, aktenzeichen=aktenzeichen, bezeichnung=bezeichnung,
            aktenstatus=(status or "unbekannt"),
            dokumente=[GedaechtnisDokument(
                dokument_id="D-001", titel="Aktenvermerk", nummer=1,
                seiten=[Seite(nummer=1, text=BEISPIELTEXT)])],
            letzte_dokumentnummer=1,
            lebenssachverhalt="Beispielhafter Arbeitsstand. [Q: D1-S1-P1]",
            lebenssachverhalt_quellen=[Quelle(kennung="D1-S1-P1", dokument_id="D-001",
                                              dokument_titel="Aktenvermerk", seite=1,
                                              zitat="Dies ist ein erfundener Beispieltext.")],
            verarbeitete_passagen=["D1-S1-P1"],
            fragen_antworten=[GedaechtnisAntwort(
                frage="Worum geht es?", antwort="Um ein Beispiel. [Q: D1-S1-P1]",
                quellen=[Quelle(kennung="D1-S1-P1", dokument_id="D-001",
                                dokument_titel="Aktenvermerk", seite=1, zitat="Beispiel")])],
            aktualisiert_am=JETZT - timedelta(days=5),
        )
        if vormerkung is not None:
            g.abgeschlossen_am = vormerkung - timedelta(days=30)
            g.loeschung_vorgesehen_am = vormerkung
            g.retention_reason = "abschlusspruefung_erforderlich"
        speicher.ablegen(g)
        erklaerungen.append((f"{aktenzeichen} · {bezeichnung}", erklaerung))

    return erklaerungen


if __name__ == "__main__":
    ziel = Path(sys.argv[1] if len(sys.argv) > 1 else "testdaten/aufbewahrung").resolve()
    erklaerungen = erzeugen(ziel)

    print(f"\n{len(erklaerungen)} Beispielfälle angelegt in {ziel}\n")
    for name, erklaerung in erklaerungen:
        print(f"  {name}\n    → {erklaerung}\n")
    print("Ein Befund lässt sich so nicht nachstellen: „Der Status konnte nicht aus")
    print("jur|nodes gelesen werden.\" Er entsteht, wenn das Netzlaufwerk gerade nicht")
    print("erreichbar ist – dafür müsste man J: trennen.\n")
    print("So ansehen (in diesem Ordner, mit aktivem Aktengedächtnis):\n")
    print(f'  JUSPERFECT_BETRIEBSART=lokal JUSPERFECT_ANBIETER=demo \\\n'
          f'  JUSPERFECT_JURNODES_ADAPTER=fixture JUSPERFECT_FIXTURE_PFAD="{ziel / "akten"}" \\\n'
          f'  JUSPERFECT_NUTZER_DATEI=testdaten/nutzer.json \\\n'
          f'  JUSPERFECT_GEDAECHTNIS=lokal JUSPERFECT_GEDAECHTNIS_PFAD="{ziel / "gedaechtnis"}" \\\n'
          f'  python -m jusperfect\n')
    print("Dann als ra-weber anmelden und unten auf „Aufbewahrung\" klicken.")
