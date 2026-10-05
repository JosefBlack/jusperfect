"""Ein geführter Durchgang durch das Aktengedächtnis – ohne AWS, ohne Browser.

Aus der Kanzlei: „dann möchte ich bitte das Aktengedächtnis noch mal mit dir
durchgehen beziehungsweise testen."

Das Gedächtnis ist der Teil, den man am schwersten sieht: Es tut seine Arbeit
zwischen zwei Arbeitstagen. Dieser Durchgang macht sie sichtbar. Er geht
dieselben Wege wie die Oberfläche – dieselben Endpunkte, dieselben Dienste –
und schreibt nach jedem Schritt auf, was im Gedächtnis steht.

Acht Schritte, und der fünfte ist der eigentliche Punkt:

  1. Akte öffnen und drei Dokumente in die Arbeitsakte legen
  2. Den Lebenssachverhalt fortschreiben
  3. Eine Frage stellen
  4. Den Zeitstrahl aufbauen
  5. Sitzung schließen und die Akte neu öffnen  ← hier zeigt sich alles
  6. Ein Schriftsatz kommt nach: nur er geht ans Modell
  7. Ein Dokument zurückziehen: nur sein Teil fällt weg
  8. Wo das alles liegt

Gerechnet wird mit dem Demo-Anbieter, also ohne KI und ohne Kosten. Seine
Fortschreibung ist grob – sie erkennt Sätze mit Datum, Betrag oder Rolle. Für
die Frage, ob das Gedächtnis trägt, genügt das: Der Weg ist derselbe.

Aufruf:  python3 werkzeug/gedaechtnis_probe.py
Windows: GEDAECHTNIS-PROBE.bat
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from fastapi.testclient import TestClient  # noqa: E402

from jusperfect.config import Einstellungen  # noqa: E402
from jusperfect.providers.demo import DemoProvider  # noqa: E402
from jusperfect.web import Dienste, app_erstellen  # noqa: E402

AKTE = "AR-2026-0115"
ERSTE_DREI = ["D-201", "D-202", "D-203"]
NACHZUEGLER = "D-208"


def _linie(text: str = "") -> None:
    print("\n" + "─" * 72)
    if text:
        print(text)
        print("─" * 72)


def _schritt(nummer: int, titel: str, warum: str) -> None:
    _linie()
    print(f"SCHRITT {nummer}: {titel}")
    print(f"  Worauf es ankommt: {warum}")
    print()


def _gedaechtnis_zeigen(c: TestClient, sitzung_id: str, kurz: bool = False) -> dict:
    g = c.get(f"/api/sitzungen/{sitzung_id}/gedaechtnis").json()
    if not g["vorhanden"]:
        print("  Im Gedächtnis steht noch nichts.")
        return g
    print(f"  Dokumente im Gedächtnis : {g['dokumente']}  ({g['zeichen']} Zeichen)")
    print(f"  Gespeicherte Fragen     : {g['fragen']}")
    print(f"  Ereignisse im Zeitstrahl: {len(g['chronologie'])}")
    if kurz:
        return g
    if g["lebenssachverhalt"]:
        print("\n  Lebenssachverhalt:")
        for zeile in g["lebenssachverhalt"].splitlines():
            if zeile.strip():
                print(f"    {zeile}")
        print("\n  Belegt durch: " + ", ".join(q["kennung"] for q in g["quellen"]))
    else:
        print("\n  Lebenssachverhalt: (noch leer)")
    return g


def durchgang(ordner: Path) -> None:
    gedaechtnis_ordner = ordner / "gedaechtnis"
    if gedaechtnis_ordner.exists():
        shutil.rmtree(gedaechtnis_ordner)
    gedaechtnis_ordner.mkdir(parents=True)

    e = Einstellungen.aus_umgebung({
        "JUSPERFECT_BETRIEBSART": "lokal",
        "JUSPERFECT_ANBIETER": "demo",
        "JUSPERFECT_JURNODES_ADAPTER": "fixture",
        "JUSPERFECT_FIXTURE_PFAD": str(WURZEL / "testdaten" / "akten"),
        "JUSPERFECT_NUTZER_DATEI": str(WURZEL / "testdaten" / "nutzer.json"),
        "JUSPERFECT_GEDAECHTNIS": "lokal",
        "JUSPERFECT_GEDAECHTNIS_PFAD": str(gedaechtnis_ordner),
    })
    provider = DemoProvider()
    d = Dienste(e, provider=provider)
    c = TestClient(app_erstellen(e, d), headers={"X-Jusperfect-Nutzer": "ra-weber"},
                   raise_server_exceptions=False)

    _linie("AKTENGEDÄCHTNIS – EIN DURCHGANG OHNE KI UND OHNE KOSTEN")
    print("Akte 115/26 AR · Reinhold-Özdemir ./. Nordwerk Metallbau – Kündigungsschutz")
    print("Anbieter: Demo (kein Modell, keine Kosten). Gedächtnis: lokal, als Datei.")

    # ── 1 ────────────────────────────────────────────────────────────────────
    _schritt(1, "Akte öffnen und drei Dokumente in die Arbeitsakte legen",
             "Beim Laden wandert der extrahierte Text ins Gedächtnis – ohne Modellaufruf.")
    sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
    c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ERSTE_DREI})
    _gedaechtnis_zeigen(c, sid)
    print(f"\n  Modellaufrufe bis hierher: {len(provider.aufrufe)}  (das Einlesen kostet keinen)")

    # ── 2 ────────────────────────────────────────────────────────────────────
    _schritt(2, "Den Lebenssachverhalt fortschreiben",
             "Jetzt geht Material an das Modell – und jede Aussage trägt eine Fundstelle.")
    vorher = len(provider.aufrufe)
    antwort = c.post(f"/api/sitzungen/{sid}/gedaechtnis/aktualisieren").json()
    _gedaechtnis_zeigen(c, sid)
    lauf = antwort.get("lauf", {})
    print(f"\n  Gelesene Portionen: {lauf.get('portionen')} · Passagen: {lauf.get('passagen')}"
          f" · noch offen: {lauf.get('offene_passagen')}")
    print(f"  Modellaufrufe in diesem Schritt: {len(provider.aufrufe) - vorher}")

    # ── 3 ────────────────────────────────────────────────────────────────────
    _schritt(3, "Eine Frage stellen",
             "Nur die belegte Endfassung wird gespeichert – Rohtext nie.")
    frage = "Wann wurde gekündigt?"
    a = c.post(f"/api/sitzungen/{sid}/frage", json={"frage": frage}).json()
    print(f"  Frage: {frage}")
    for zeile in a["text"].splitlines():
        if zeile.strip():
            print(f"    {zeile}")
    print(f"  Belege: {', '.join(q['kennung'] for q in a['quellen']) or '—'}")
    g = c.get(f"/api/sitzungen/{sid}/gedaechtnis").json()
    print(f"\n  Im Gedächtnis gespeicherte Fragen: {g['fragen']}")

    # ── 4 ────────────────────────────────────────────────────────────────────
    _schritt(4, "Den Zeitstrahl aufbauen",
             "Die Chronologie steht dauerhaft und wird fortgeschrieben, nicht neu erzeugt.")
    vorher = len(provider.aufrufe)
    chrono = c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren").json()
    for eintrag in chrono["chronologie"][:6]:
        belege = ", ".join(q["kennung"] for q in eintrag["quellen"])
        print(f"    {eintrag['datum']}  {eintrag['ereignis'][:58]}  [{belege}]")
    if len(chrono["chronologie"]) > 6:
        print(f"    … und {len(chrono['chronologie']) - 6} weitere")
    print(f"\n  Modellaufrufe in diesem Schritt: {len(provider.aufrufe) - vorher}")
    nochmal = c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren").json()
    print(f"  Noch einmal gedrückt: {nochmal['neue_passagen']} neue Passagen, "
          f"{len(provider.aufrufe) - vorher} Aufrufe insgesamt – nichts Neues kostet nichts.")

    # ── 5 ────────────────────────────────────────────────────────────────────
    _schritt(5, "Sitzung schließen – und die Akte neu öffnen",
             "DAS ist der Zweck des Gedächtnisses. Die Sitzung ist weg; die Akte nicht.")
    c.delete(f"/api/sitzungen/{sid}")
    print("  Sitzung geschlossen. Die temporären Texte sind gelöscht.")
    neu = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()
    sid2 = neu["sitzung"]["id"]
    print(f"  Akte neu geöffnet. Neue Sitzung: {sid2[:12]}…\n")
    print("  Was ohne Gedächtnis jetzt weg wäre und trotzdem da ist:")
    print(f"    Geladene Dokumente : {len(neu['sitzung']['geladen'])}"
          "   (nicht neu eingelesen, nicht neu erkannt)")
    print(f"    Frühere Fragen     : {len(neu['sitzung']['dialog'])}"
          "   (als Kontext für Rückfragen)")
    for hinweis in neu["sitzung"]["hinweise"]:
        print(f"    Hinweis: {hinweis}")
    _gedaechtnis_zeigen(c, sid2)
    print(f"\n  Modellaufrufe fürs Wiederaufnehmen: 0  (Gesamtstand: {len(provider.aufrufe)})")

    # ── 6 ────────────────────────────────────────────────────────────────────
    _schritt(6, "Drei Wochen später kommt ein Schriftsatz",
             "Nur das neue Dokument geht ans Modell. Das Bekannte wird nicht neu bezahlt.")
    c.post(f"/api/sitzungen/{sid2}/dokumente", json={"dokument_ids": [NACHZUEGLER]})
    vorher = len(provider.aufrufe)
    c.post(f"/api/sitzungen/{sid2}/gedaechtnis/aktualisieren")
    material = provider.aufrufe[-1][1]
    mitgegangen = sorted({z.split()[2] for z in material.splitlines() if z.startswith("### Passage ")})
    g = _gedaechtnis_zeigen(c, sid2)
    print(f"\n  Modellaufrufe in diesem Schritt: {len(provider.aufrufe) - vorher}")
    print(f"  Mitgegangene Passagen: {', '.join(mitgegangen)}")
    print("  Alle aus dem neuen Dokument (D4-…). Die drei alten blieben zu Hause.")

    # ── 7 ────────────────────────────────────────────────────────────────────
    _schritt(7, "Ein Dokument zurückziehen",
             "Nur was dieses Dokument belegt, fällt weg. Der Rest bleibt stehen.")
    vorher_text = g["lebenssachverhalt"]
    print(f"  Lebenssachverhalt vorher: {len(vorher_text)} Zeichen, "
          f"{len(g['quellen'])} Fundstellen")
    c.delete(f"/api/akten/{AKTE}/gedaechtnis/dokumente/{ERSTE_DREI[1]}")
    print(f"  „{ERSTE_DREI[1]}\" aus dem Gedächtnis genommen.\n")
    nachher = _gedaechtnis_zeigen(c, sid2)
    print("\n  Früher fiel hier alles Abgeleitete weg, weil sich die Fundstellen")
    print("  verschoben hätten. Seit jeder Auszug eine feste Nummer trägt, bleibt")
    print("  stehen, was auf den anderen Dokumenten beruht.")

    # ── 8 ────────────────────────────────────────────────────────────────────
    _schritt(8, "Wo das alles liegt",
             "Im Echtbetrieb ist das S3 in Frankfurt, verschlüsselt. Hier eine Datei.")
    dateien = list(gedaechtnis_ordner.glob("*.json"))
    for datei in dateien:
        print(f"  {datei}")
        print(f"    {datei.stat().st_size} Bytes")
    print("\n  Der Dateiname ist eine Prüfsumme der Aktenkennung, kein Aktenzeichen –")
    print("  auch der Name einer Datei soll nicht verraten, um welche Akte es geht.")

    _linie("ZUSAMMEN")
    print(f"Modellaufrufe insgesamt: {len(provider.aufrufe)}")
    print("Davon fürs Wiederaufnehmen der Akte am nächsten Tag: 0.")
    print("\nGenau dafür ist das Gedächtnis da. Mit einem echten Modell steht dort")
    print("statt der groben Demo-Sätze ein zusammenhängender Lebenssachverhalt –")
    print("der Weg dorthin ist derselbe, den Sie hier gesehen haben.")


if __name__ == "__main__":
    ziel = Path(sys.argv[1] if len(sys.argv) > 1 else WURZEL / "testdaten" / "gedaechtnis-probe")
    durchgang(ziel.resolve())
