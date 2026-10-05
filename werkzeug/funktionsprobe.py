"""Alle Funktionen einmal durchgehen – ohne KI, ohne AWS, ohne Kosten.

Aus der Kanzlei: „bevor wir AWS einrichten, erst alle Funktionen mit einer
Testakte ausprobieren, oder?" Ja – und das ist mit vierzig Mausklicks eine
mühsame Sache, die man nach der dritten Änderung nicht mehr macht.

Dieses Werkzeug geht denselben Weg wie die Oberfläche: dieselben Endpunkte,
dieselben Dienste, dieselben Testakten. Es sagt nach jedem Schritt, ob er hält,
was er verspricht.

**Was es prüfen kann und was nicht.** Gerechnet wird mit dem Demo-Anbieter, also
ohne KI. Damit lässt sich prüfen, ob die *Wege* stimmen: ob eine Antwort Belege
trägt, ob ein Verweis an die richtige Stelle zeigt, ob das Gedächtnis eine
geschlossene Sitzung übersteht, ob eine zu große Akte abgelehnt und nach dem
Einlesen angenommen wird. Es lässt sich damit **nicht** prüfen, ob der Inhalt
gut ist: ob die Chronologie hilft, ob der Lebenssachverhalt den Fall trifft, ob
die fünf Funde in der großen Akte gefunden werden. Das entscheidet das Modell,
und dafür braucht es Bedrock (START-AWS.bat) – nicht aber das AWS-Gedächtnis.

Aufruf:  python3 werkzeug/funktionsprobe.py
Windows: FUNKTIONSPROBE.bat
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from fastapi.testclient import TestClient  # noqa: E402

from jusperfect.config import Einstellungen  # noqa: E402
from jusperfect.providers.demo import DemoProvider  # noqa: E402
from jusperfect.web import Dienste, app_erstellen  # noqa: E402

KLEIN = "AR-2026-0115"
GROSS = "BA-2026-0044"

_ergebnisse: list[tuple[bool, str, str]] = []


def pruefe(name: str, bedingung: bool, detail: str = "") -> bool:
    _ergebnisse.append((bool(bedingung), name, detail))
    print(f"  {'✓' if bedingung else '✗'} {name}" + (f"   ({detail})" if detail else ""))
    return bool(bedingung)


def abschnitt(titel: str) -> None:
    print(f"\n{titel}\n{'─' * len(titel)}")


def _client(fixture: Path, gedaechtnis: Path | None) -> tuple[TestClient, Dienste, DemoProvider]:
    umgebung = {
        "JUSPERFECT_BETRIEBSART": "lokal", "JUSPERFECT_ANBIETER": "demo",
        "JUSPERFECT_JURNODES_ADAPTER": "fixture", "JUSPERFECT_FIXTURE_PFAD": str(fixture),
        "JUSPERFECT_NUTZER_DATEI": str(WURZEL / "testdaten" / "nutzer.json"),
    }
    if gedaechtnis is not None:
        umgebung |= {"JUSPERFECT_GEDAECHTNIS": "lokal", "JUSPERFECT_GEDAECHTNIS_PFAD": str(gedaechtnis)}
    e = Einstellungen.aus_umgebung(umgebung)
    provider = DemoProvider()
    d = Dienste(e, provider=provider)
    c = TestClient(app_erstellen(e, d), headers={"X-Jusperfect-Nutzer": "ra-weber"},
                   raise_server_exceptions=False)
    return c, d, provider


# ── Die kleine Akte: alles, was täglich gebraucht wird ──────────────────────

def kleine_akte(ordner: Path) -> None:
    c, d, provider = _client(WURZEL / "testdaten" / "akten", ordner)

    abschnitt("Anmeldung und Aktenliste")
    status = c.get("/api/status").json()
    pruefe("Der Benutzer wird erkannt", status["nutzer"]["id"] == "ra-weber", status["nutzer"]["name"])
    pruefe("Die Benutzerauswahl gibt es örtlich", c.get("/api/nutzer").status_code == 200)
    akten = c.get("/api/akten").json()
    pruefe("Akten werden gefunden", len(akten) >= 3, f"{len(akten)} Akten")

    abschnitt("Akte öffnen und Dokumente übernehmen")
    sid = c.post("/api/sitzungen", json={"akte_id": KLEIN}).json()["sitzung"]["id"]
    daten = c.post(f"/api/sitzungen/{sid}/dokumente",
                   json={"dokument_ids": [f"D-{n}" for n in range(201, 209)]}).json()
    geladen = daten["sitzung"]["geladen"]
    pruefe("Alle acht Dokumente gelesen", len(geladen) == 8, f"{len(geladen)} Dokumente")
    pruefe("Jedes Dokument hat Text", all(g["zeichen"] > 0 for g in geladen))
    passagen = c.get(f"/api/sitzungen/{sid}/passagen").json()["passagen"]
    pruefe("Passagen tragen Fundstellenkennungen", all(p["kennung"].startswith("D") for p in passagen),
           f"{len(passagen)} Passagen, erste {passagen[0]['kennung']}")

    abschnitt("Frage und Beleg")
    antwort = c.post(f"/api/sitzungen/{sid}/frage", json={"frage": "Wann wurde gekündigt?"}).json()
    pruefe("Die Antwort trägt Belege", bool(antwort["quellen"]),
           ", ".join(q["kennung"] for q in antwort["quellen"][:3]))
    pruefe("Jeder Beleg zeigt auf eine geladene Passage",
           all(q["kennung"] in {p["kennung"] for p in passagen} for q in antwort["quellen"]))
    ohne = c.post(f"/api/sitzungen/{sid}/frage",
                  json={"frage": "Wie war das Wetter auf Sylt?"}).json()
    pruefe("Ohne Fund wird nichts behauptet",
           not ohne["quellen"] or "kein belastbarer Beleg" in ohne["text"],
           ohne["text"][:60])

    abschnitt("Der Verweis führt an die genaue Stelle")
    kennung = antwort["quellen"][0]["kennung"]
    stellen = []
    for aussage in ("Das Bruttomonatsgehalt beträgt 3.940,00 EUR.",
                    "Gekündigt wurde zum 30.09.2026."):
        stellen.append(c.post(f"/api/sitzungen/{sid}/fundstelle",
                              json={"kennung": kennung, "aussage": aussage}).json())
    pruefe("Zwei Aussagen, zwei verschiedene Stellen",
           stellen[0]["treffer_start"] != stellen[1]["treffer_start"],
           f"{stellen[0]['zitat'][:32]!r} / {stellen[1]['zitat'][:32]!r}")
    pruefe("Die Angabe selbst ist markiert",
           any(stellen[1]["zitat"][a - stellen[1]["treffer_start"]:b - stellen[1]["treffer_start"]]
               for a, b in stellen[1]["marken"]) if stellen[1]["marken"] else False,
           ", ".join(str(m) for m in stellen[1]["marken"][:2]))

    abschnitt("Analyse, Chronologie, Entwurf, Eingangsprüfung")
    analyse = c.post(f"/api/sitzungen/{sid}/analyse")
    pruefe("Die Analyse läuft durch", analyse.status_code == 200, str(analyse.status_code))
    if analyse.status_code == 200:
        a = analyse.json()
        pruefe("Sie liefert eine Chronologie", len(a["chronologie"]) > 0, f"{len(a['chronologie'])} Ereignisse")
        pruefe("Jeder Eintrag ist belegt", all(e["quellen"] for e in a["chronologie"]))
    vorher = len(provider.aufrufe)
    c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren")
    zweite = c.post(f"/api/sitzungen/{sid}/chronologie/aktualisieren").json()
    pruefe("Ohne neues Dokument kostet der Zeitstrahl nichts",
           zweite["neue_passagen"] == 0, f"{len(provider.aufrufe) - vorher} Aufruf(e)")
    entwurf = c.post(f"/api/sitzungen/{sid}/entwuerfe",
                     json={"art": "gegner", "anweisung": "Kündigung zurückweisen", "empfaenger": "Gegenseite"})
    pruefe("Ein Entwurf entsteht", entwurf.status_code == 201, str(entwurf.status_code))
    if entwurf.status_code == 201:
        pruefe("Der Entwurf trägt Belege", bool(entwurf.json().get("quellen")),
               ", ".join(q["kennung"] for q in entwurf.json().get("quellen", [])[:3]))
    triage = c.post(f"/api/sitzungen/{sid}/triage", json={"dokument_id": "D-202"})
    pruefe("Die Eingangsprüfung läuft", triage.status_code == 200, str(triage.status_code))

    abschnitt("Aktengedächtnis")
    lauf = c.post(f"/api/sitzungen/{sid}/gedaechtnis/aktualisieren").json()
    pruefe("Der Lebenssachverhalt entsteht", bool(lauf["lebenssachverhalt"]),
           f"{len(lauf['lebenssachverhalt'])} Zeichen")
    pruefe("Er ist belegt", bool(lauf["quellen"]), f"{len(lauf['quellen'])} Fundstellen")
    c.delete(f"/api/sitzungen/{sid}")
    neu = c.post("/api/sitzungen", json={"akte_id": KLEIN}).json()
    pruefe("Nach dem Schließen ist alles wieder da",
           len(neu["sitzung"]["geladen"]) == 8 and bool(neu["gedaechtnis"]["lebenssachverhalt"]),
           f"{len(neu['sitzung']['geladen'])} Dokumente, {neu['gedaechtnis']['fragen']} Frage(n)")
    aufrufe_vorher = len(provider.aufrufe)
    c.post("/api/sitzungen", json={"akte_id": KLEIN})
    pruefe("Das Wiederaufnehmen kostet keinen Modellaufruf",
           len(provider.aufrufe) == aufrufe_vorher)
    uebrig = c.delete(f"/api/akten/{KLEIN}/gedaechtnis/dokumente/D-202").json()
    pruefe("Ein zurückgezogenes Dokument nimmt nur seinen Teil mit",
           uebrig["dokumente"] == 7 and bool(uebrig["lebenssachverhalt"]),
           f"{uebrig['dokumente']} Dokumente, Lebenssachverhalt {len(uebrig['lebenssachverhalt'])} Zeichen")

    abschnitt("Verwaltung")
    pruefe("Der Nachweis ist abrufbar", c.get("/api/nachweis").status_code == 200)
    nachweis = c.get("/api/nachweis").json()
    text = str(nachweis)
    pruefe("Er enthält keinen Akteninhalt",
           not any(w in text for w in ("Reinhold-Özdemir", "Kündigung wird", "3.940,00")))
    aufsicht = c.get("/api/verwaltung/arbeitsbereiche")
    pruefe("Die Aufbewahrung ist abrufbar", aufsicht.status_code == 200, str(aufsicht.status_code))


# ── Die große Akte: der Weg, für den 2.0 gebaut wurde ───────────────────────

def grosse_akte(ordner: Path) -> None:
    quelle = WURZEL / "testdaten" / "grosse-akte" / GROSS
    if not (quelle / "akte.json").is_file():
        print("\n  Die große Testakte fehlt – sie wird erzeugt …")
        sys.path.insert(0, str(WURZEL / "werkzeug"))
        import grosse_testakte

        grosse_testakte.erzeugen(quelle)

    c, d, provider = _client(WURZEL / "testdaten" / "grosse-akte", ordner)
    abschnitt("Große Akte: 50 Dokumente, rund 880.000 Zeichen")
    sid = c.post("/api/sitzungen", json={"akte_id": GROSS}).json()["sitzung"]["id"]
    ids = [f"D-{nr:03d}" for nr in range(1, 51)]
    geladen = c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ids}).json()
    pruefe("Alle 50 Dokumente gelesen", len(geladen["sitzung"]["geladen"]) == 50)

    verweigert = c.post(f"/api/sitzungen/{sid}/analyse")
    pruefe("Die Analyse verweigert statt zu kürzen", verweigert.status_code == 422)
    if verweigert.status_code == 422:
        pruefe("Die Meldung nennt den Ausweg", "Akte einlesen" in verweigert.json()["fehler"])

    lauf = c.post(f"/api/sitzungen/{sid}/gedaechtnis/einlesen").json()["lauf"]
    pruefe("Die Akte wird abschnittsweise gelesen", lauf["fertig"],
           f"{lauf['portionen']} Portionen, {lauf['passagen']} Passagen")

    g = c.get(f"/api/sitzungen/{sid}/gedaechtnis").json()
    nummern = sorted({int(q["kennung"].split("-")[0][1:]) for q in g["quellen"]})
    pruefe("Die Fundstellen überstehen die Portionierung",
           bool(nummern) and max(nummern) > 40, f"D{min(nummern)} bis D{max(nummern)}")

    danach = c.post(f"/api/sitzungen/{sid}/analyse")
    pruefe("Danach läuft die Analyse", danach.status_code == 200, str(danach.status_code))
    if danach.status_code == 200:
        a = danach.json()
        pruefe("Sie sagt, worauf sie beruht", "Aktengedächtnis" in a["hinweise"][0])
        eintraege = a["chronologie"] + a["forderungen"] + a["beweismittel"]
        weit = sorted({int(q["kennung"].split("-")[0][1:]) for e in eintraege for q in e["quellen"]})
        pruefe("Die Belege reichen über den ersten Aufruf hinaus",
               bool(weit) and max(weit) > 9, f"Dokumente {weit[:5]} … {weit[-2:] if len(weit) > 5 else ''}")


def main() -> int:
    print("=" * 72)
    print("FUNKTIONSPROBE – alle Wege einmal durch, ohne KI und ohne Kosten")
    print("=" * 72)
    with tempfile.TemporaryDirectory() as tmp:
        kleine_akte(Path(tmp) / "klein")
        grosse_akte(Path(tmp) / "gross")

    fehler = [name for gut, name, _ in _ergebnisse if not gut]
    print("\n" + "=" * 72)
    print(f"{len(_ergebnisse) - len(fehler)} von {len(_ergebnisse)} Prüfungen bestanden.")
    for name in fehler:
        print(f"  ✗ {name}")
    print("=" * 72)
    print("\nWas hiermit NICHT geprüft ist: ob der Inhalt gut ist. Ob die Chronologie")
    print("hilft, ob der Lebenssachverhalt den Fall trifft, ob die fünf eingebauten")
    print("Funde der großen Akte gefunden werden – das entscheidet das Modell.")
    print("Dafür START-AWS.bat (Bedrock mit den Testakten); das AWS-Gedächtnis")
    print("braucht es dafür noch nicht.")
    return 1 if fehler else 0


if __name__ == "__main__":
    raise SystemExit(main())
