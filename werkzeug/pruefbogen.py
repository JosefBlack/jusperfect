"""Ein echter Lauf, gemessen an der Auflösung – der Prüfbogen.

Aus der Kanzlei: „Ich würde gerne nochmal schauen, wie akkurat das System
funktioniert anhand von Testakten."

Bisher ging das nur von Hand: einen Lauf machen, das Ergebnis ausdrucken,
`testdaten/grosse-akte/AUFLOESUNG.md` danebenlegen und Zeile für Zeile
vergleichen. Das dauert eine halbe Stunde, es ermüdet, und zwei Läufe lassen
sich hinterher nicht mehr sauber gegeneinanderhalten, weil niemand beide Male
gleich streng gelesen hat.

Dieses Werkzeug nimmt die Arbeit ab. Es geht denselben Weg wie die Oberfläche –
Akte öffnen, alle fünfzig Dokumente einlesen, über das Aktengedächtnis
analysieren – und hält das Ergebnis dann gegen die eingebauten Funde. Heraus
kommt eine Tabelle: welcher Fund benannt wurde, mit welchen Fundstellen, und
welcher nicht.

**Wie streng gemessen wird.** Ein Fund gilt erst dann als gefunden, wenn er
unter „Widersprüche" steht, die harten Angaben nennt (beide Daten, beide Maße)
**und** beide Dokumente als Fundstelle trägt. Eine richtige Aussage ohne Beleg
zählt nicht als Treffer – sie wird als „ohne Beleg" ausgewiesen. Das ist
strenger als ein Mensch beim Überfliegen, und es ist die Strenge, die das
Programm an sich selbst anlegt.

**Was der Prüfbogen nicht kann.** Er misst, ob die fünf eingebauten Funde
benannt sind, ob die dreizehn Tage im Zeitstrahl stehen, ob die Zahlen stimmen
und ob die Fristensperre hält. Er beurteilt nicht, ob ein Text gut geschrieben
ist. Und er braucht einen echten Modelllauf: Mit dem Demo-Anbieter läuft er
durch, findet aber nichts – das sagt er dann auch.

Aufruf:  python3 werkzeug/pruefbogen.py [--speichern ORDNER]
Windows: PRUEFBOGEN.bat   (vorher START-AWS.bat einrichten, sonst ohne KI)
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "werkzeug"))

from fastapi.testclient import TestClient  # noqa: E402

import grosse_testakte as vorlage  # noqa: E402
from jusperfect.config import Einstellungen  # noqa: E402
from jusperfect.domain.models import Aktengedaechtnis  # noqa: E402
from jusperfect.services.gedaechtnis import Gedaechtnisdienst  # noqa: E402
from jusperfect.web import Dienste, app_erstellen  # noqa: E402

GROSS = "BA-2026-0044"
BREITE = 78

# Woran ein Zeitstrahleintrag als Bautagebuch-Routine zu erkennen ist: an
# seiner Quelle. Nach den Worten zu suchen ("Kolonne", "Gewerk") geht fehl,
# sobald der Eintrag nur die erste Zeile des Tages mitnimmt - dann steht dort
# das Wetter und sonst nichts. Das Dokument, aus dem er stammt, luegt nicht.
ROUTINEQUELLE = "bautagebuch"


# ── Vergleichen, ohne an Schreibweisen zu scheitern ─────────────────────────

_MONATE = {"januar": "01", "februar": "02", "märz": "03", "maerz": "03",
           "april": "04", "mai": "05", "juni": "06", "juli": "07", "august": "08",
           "september": "09", "oktober": "10", "november": "11", "dezember": "12"}


def _normalisieren(text: str) -> str:
    """Alles auf eine Schreibweise bringen, bevor verglichen wird.

    „14. August 2025", „14.8.2025" und „14.08.2025" meinen denselben Tag;
    „24 cm", „24cm" und „24 Zentimeter" dasselbe Maß. Wer stur auf Zeichenketten
    vergleicht, zaehlt einen Treffer als Fehlschlag und misst damit die
    Schreibweise des Modells statt seiner Leistung.
    """
    t = unicodedata.normalize("NFKC", text).lower()
    for name, nummer in _MONATE.items():
        t = re.sub(rf"(\d{{1,2}})\.?\s+{name}\s+(\d{{4}})", rf"\1.{nummer}.\2", t)
    t = re.sub(r"\b(\d{4})-(\d{2})-(\d{2})\b", r"\3.\2.\1", t)   # 2025-06-20 → 20.06.2025
    t = t.replace("zentimeter", "cm").replace("quadratmeter", "m²").replace("€", "eur")
    t = re.sub(r"(\d)\s+(cm|m²|eur|€)", r"\1\2", t)
    t = re.sub(r"\b(\d)\.(\d{2})\.(\d{4})\b", r"0\1.\2.\3", t)   # 4.12.2025 → 04.12.2025
    t = re.sub(r"\b(\d{2})\.(\d)\.(\d{4})\b", r"\1.0\2.\3", t)   # 14.8.2025 → 14.08.2025
    return re.sub(r"\s+", " ", t)


def _varianten(merkmal: str) -> tuple[str, ...]:
    """Zu einer erwarteten Angabe die Schreibweisen, die ebenfalls gelten.

    Betraege schreibt das eine Modell „486.500,00 EUR", das andere „486500 EUR"
    oder „486.500 EUR". Gemeint ist derselbe Betrag.
    """
    grund = _normalisieren(merkmal)
    formen = {grund}
    zahl = re.match(r"^([\d.,]+)\s*(eur|€|m²|cm)?$", grund)
    if zahl:
        ziffern = zahl.group(1).replace(".", "").replace(",00", "")
        einheit = zahl.group(2) or ""
        formen |= {f"{ziffern}{einheit}", f"{ziffern},00{einheit}"}
        if len(ziffern) > 3:
            mit_punkt = f"{int(ziffern):,}".replace(",", ".")
            formen |= {f"{mit_punkt}{einheit}", f"{mit_punkt},00{einheit}"}
    return tuple(formen)


def _enthalten(text: str, merkmal: str) -> bool:
    return any(v in text for v in _varianten(merkmal))


def _dokumente(quellen: list[dict]) -> set[str]:
    """Aus Fundstellen wie „D12-S3-P1" die Dokumentnummern „D-012"."""
    gefunden = set()
    for q in quellen or []:
        treffer = re.match(r"D-?(\d+)", str(q.get("kennung", "")))
        if treffer:
            gefunden.add(f"D-{int(treffer.group(1)):03d}")
    return gefunden


# ── Die eigentliche Messung ─────────────────────────────────────────────────

# Wie die Abschnitte der Analyse heißen, steht an einer einzigen Stelle:
# jusperfect/services/prompts.py. Wer hier einen Feldnamen daneben schreibt,
# bekommt keinen Fehler, sondern ein leeres Feld – und damit ein Messgerät,
# das ein richtiges Ergebnis als falsch ausweist.
#
# Aus der Kanzlei, Lauf vom 16.09.2026: Der Bogen meldete „✗ 402,00 m²
# Dämmfläche". Die Zahl stand in der Analyse, mit Beleg aus dem
# Leistungsverzeichnis – nur im Feld „gegenstand", und gesucht wurde in
# „bezeichnung". Dasselbe bei den Beteiligten: gesucht in „name", benannt
# ist „bezeichnung".
_TEXTFELDER: dict[str, tuple[str, ...]] = {
    "chronologie": ("ereignis", "datum"),
    "beteiligte": ("bezeichnung", "rolle"),
    "forderungen": ("gegenstand", "betrag", "status"),
    "beweismittel": ("bezeichnung", "art", "beweisthema"),
    "offene_punkte": ("beschreibung", "prioritaet"),
    "widersprueche": ("beschreibung",),
}


def _alle_texte(analyse: dict) -> str:
    """Der gesamte Fließtext der Analyse, für die Suche nach Bausteinen."""
    teile: list[str] = list(analyse.get("hinweise") or [])
    for feld, schluessel in _TEXTFELDER.items():
        for eintrag in analyse.get(feld) or []:
            teile += [str(eintrag.get(s, "")) for s in schluessel]
    return _normalisieren(" ".join(t for t in teile if t))


def _fund_bewerten(fund: vorlage.Fund, analyse: dict) -> dict:
    """Ein Fund, dreifach befragt: benannt? belegt? die Bausteine überhaupt da?"""
    erwartet = {fund.erste, fund.zweite}
    bester: dict | None = None
    for w in analyse.get("widersprueche") or []:
        text = _normalisieren(str(w.get("beschreibung", "")))
        fehlende = [m for m in fund.merkmale if not _enthalten(text, m)]
        if fehlende:
            continue
        belegt = _dokumente(w.get("quellen"))
        kandidat = {"beschreibung": str(w.get("beschreibung", "")).strip(),
                    "belegt": sorted(belegt), "fehlende_belege": sorted(erwartet - belegt)}
        if not kandidat["fehlende_belege"]:
            return {"urteil": "gefunden", **kandidat}
        if bester is None or len(kandidat["fehlende_belege"]) < len(bester["fehlende_belege"]):
            bester = kandidat
    if bester is not None:
        return {"urteil": "ohne Beleg", **bester}

    # Nicht benannt - liegt es am Zusammenziehen oder fehlt der Stoff ganz?
    ueberall = _alle_texte(analyse)
    vorhanden = [m for m in fund.merkmale if _enthalten(ueberall, m)]
    return {"urteil": "nicht benannt", "beschreibung": "", "belegt": [],
            "fehlende_belege": sorted(erwartet),
            "bausteine": f"{len(vorhanden)} von {len(fund.merkmale)} Angaben stehen "
                         f"anderswo in der Analyse"}


def _gestrichen_saetze(analyse: dict) -> list[str]:
    """Die Hinweise des Aufraeumens, aus der Analyse herausgesucht.

    ``chronologie.aufraeumen`` schreibt sie in die Hinweise der Analyse. Sie
    stehen dort zwischen anderen; hier gehoeren die heraus, die vom Zeitstrahl
    handeln.
    """
    gesucht = ("Chronologie-Zeile", "chronologie-zeile")
    return [str(s).strip() for s in (analyse.get("hinweise") or [])
            if any(g in str(s) for g in gesucht)]


def _fristensperre_pruefen(analyse: dict) -> dict:
    """Darf den Auslöser benennen, aber kein Enddatum rechnen."""
    verstoesse = []
    for feld, schluessel in (("offene_punkte", "beschreibung"), ("widersprueche", "beschreibung"),
                             ("forderungen", "bezeichnung"), ("chronologie", "ereignis")):
        for eintrag in analyse.get(feld) or []:
            satz = " ".join(str(eintrag.get(s, "")) for s in (schluessel, "datum", "beschreibung"))
            klein = satz.lower()
            if "verjähr" not in klein and "verjaehr" not in klein:
                continue
            if any(jahr in satz for jahr in vorlage.FRISTENSPERRE_VERBOTENE_JAHRE):
                verstoesse.append(satz.strip())
    for satz in analyse.get("hinweise") or []:
        if ("verjähr" in satz.lower()
                and any(j in satz for j in vorlage.FRISTENSPERRE_VERBOTENE_JAHRE)):
            verstoesse.append(satz.strip())
    return {"haelt": not verstoesse, "verstoesse": verstoesse}


_BESONDERE: set[str] | None = None


def _besondere_tage() -> set[str]:
    """Die Tage, an denen das Bautagebuch selbst ein Vorkommnis vermerkt.

    Fehlt die Akte, bleibt die Menge leer, und es wird gezaehlt wie vorher.
    Das ist die ungefaehrliche Richtung: Der Bogen weist dann zu VIEL Rauschen
    aus, nie zu wenig. Ein Messgeraet, das im Zweifel zu streng ist, laesst
    niemanden ruhig schlafen, der es nicht sollte.
    """
    global _BESONDERE
    if _BESONDERE is None:
        _BESONDERE = vorlage.besondere_tage(WURZEL / "testdaten" / "grosse-akte" / GROSS)
    return _BESONDERE


def _ist_routine(eintrag: dict) -> bool:
    """Ein Tag aus einem Bautagebuch, an dem gearbeitet wurde wie am Vortag.

    Solche Einträge sind belegt und richtig. Sie sind trotzdem Rauschen: Wer den
    Zeitstrahl aufmacht, sucht die Mängelanzeige und findet Kolonnenstärken.

    **Ein Tag mit besonderem Vorkommnis ist keiner davon.** Der Auftrag
    verlangt ihn ausdrücklich – eine Abwesenheit, eine abweichende Lieferung.
    Am 01.10.2026 zählte der Bogen zwei solche Tage als Rauschen und wies
    damit 5 % aus, wo das Modell die Anweisung befolgt hatte. Wäre man dem
    Maßstab gefolgt, hätte man die Gegenliste gegen „Abwesenheit“ geschärft –
    und Fund 3 verloren, der genau daran hängt.

    Nicht das Modell und nicht die Regel lagen daneben, sondern das Meßgerät.
    Zum sechsten Mal dieselbe Form: Eine Probe, die anders mißt als der
    Auftrag verlangt, prüft etwas anderes.
    """
    tag = _normalisieren(f"{eintrag.get('datum', '')} {eintrag.get('ereignis', '')}")
    if any(_enthalten(tag, erwartet) for erwartet, _ in vorlage.CHRONOLOGIE):
        return False
    if str(eintrag.get("datum", "")) in _besondere_tage():
        return False
    quellen = eintrag.get("quellen") or []
    return any(ROUTINEQUELLE in str(q.get("dokument_titel", "")).lower() for q in quellen)


def _chronologie_pruefen(analyse: dict) -> dict:
    eintraege = analyse.get("chronologie") or []
    text = _normalisieren(" ".join(f"{e.get('datum', '')} {e.get('ereignis', '')}"
                                   for e in eintraege))
    getroffen = {tag for tag, _ in vorlage.CHRONOLOGIE if _enthalten(text, tag)}
    routine = [e for e in eintraege if _ist_routine(e)]
    return {"eintraege": len(eintraege), "erwartet": len(vorlage.CHRONOLOGIE),
            "getroffen": sorted(getroffen),
            "fehlend": [f"{t} {w}" for t, w in vorlage.CHRONOLOGIE if t not in getroffen],
            "routine": len(routine)}


def _zahlen_pruefen(analyse: dict) -> list[dict]:
    text = _alle_texte(analyse)
    return [{"wert": wert, "wofuer": wofuer, "steht_da": _enthalten(text, wert)}
            for wert, wofuer in vorlage.ZAHLEN]


def messen(analyse: dict) -> dict:
    """Das Ergebnis eines Laufs gegen die Auflösung halten."""
    funde = [{"name": f.name, **_fund_bewerten(f, analyse)} for f in vorlage.FUNDE]
    return {
        "funde": funde,
        "gefunden": sum(1 for f in funde if f["urteil"] == "gefunden"),
        "chronologie": _chronologie_pruefen(analyse),
        "gestrichen": _gestrichen_saetze(analyse),
        "zahlen": _zahlen_pruefen(analyse),
        "fristensperre": _fristensperre_pruefen(analyse),
        "kosten": analyse.get("kosten") or {},
        "modell": analyse.get("modell", ""),
    }


# ── Den Bogen ausgeben ──────────────────────────────────────────────────────

# Wie die Funktionen in der Oberflaeche heissen. Eigene Liste statt Import aus
# selbsttest.py: Der Bogen soll ohne die Oberflaeche lauffaehig bleiben.
_FUNKTIONSNAMEN = {"frage": "Fragen", "analyse": "Analyse", "triage": "Eingangsprüfung",
                   "entwurf": "Entwürfe", "gedaechtnis": "Aktengedächtnis"}


def _zeile(links: str, rechts: str = "") -> str:
    return f"{links:<44}{rechts}"


def programmstand() -> str:
    """Nummer und Datum der Änderung, aus der dieser Ordner ausgepackt wurde.

    FASSUNG.txt wird beim Erzeugen einer ZIP von Git gefüllt. Im
    Arbeitsverzeichnis steht dort noch die unersetzte Vorlage – dann ist die
    Frage gegenstandslos und die Auskunft lautet entsprechend.

    Wozu das im Bogen steht: Ein gespeicherter Bogen wird später mit einem
    anderen verglichen. Ohne diese Zeile weiß niemand mehr, welcher Stand des
    Programms ihn erzeugt hat – und vergleicht dann zwei Dinge, die nicht
    vergleichbar sind.
    """
    datei = WURZEL / "FASSUNG.txt"
    try:
        wert = datei.read_text(encoding="utf-8").strip()
    except OSError:
        return "unbekannt"
    return "Arbeitsverzeichnis" if wert.startswith("$Format") else (wert or "unbekannt")


def bogen(ergebnis: dict, lauf: dict, anbieter: str,
          modelle: dict[str, str] | None = None) -> str:
    z: list[str] = []
    z.append("=" * BREITE)
    z.append("PRÜFBOGEN – große Testakte 44/26 BA gegen AUFLOESUNG.md")
    z.append(f"{datetime.now():%d.%m.%Y, %H:%M Uhr}   ·   Anbieter: {anbieter}"
             + (f"   ·   Modell: {ergebnis['modell']}" if ergebnis["modell"] else ""))
    z.append(f"Programmstand: {programmstand()}")

    # Jede Arbeit mit ihrem Modell, nicht nur die Analyse.
    #
    # Aus der Kanzlei, 17.09.2026, 12:32 Uhr: Im Kopf der Startdatei stand
    # "Modell: anthropic.claude-opus-4-6-v1", im Bogen darunter aber
    # "eu.anthropic.claude-opus-4-5-…". Beides war richtig und meinte
    # Verschiedenes: Die Startdatei nannte, was sie gesetzt hatte, der Bogen,
    # was die Analyse benutzt hat - und dazwischen lag eine dauerhafte
    # Windows-Einstellung. Ein Bogen, der nur ein Modell nennt, verbirgt
    # genau das.
    if modelle:
        gebuendelt: dict[str, list[str]] = {}
        for funktion, kennung in modelle.items():
            gebuendelt.setdefault(kennung, []).append(
                _FUNKTIONSNAMEN.get(funktion, funktion))
        z.append("-" * BREITE)
        for kennung, funktionen in gebuendelt.items():
            z.append(f"  {', '.join(funktionen)}:")
            z.append(f"      {kennung}")
    z.append("=" * BREITE)

    if anbieter == "demo":
        z.append("")
        z.append("  ACHTUNG: Gerechnet wurde ohne KI (Demo-Anbieter). Der Weg wird")
        z.append("  geprüft, nicht die Güte. Dass nichts gefunden wird, ist hier kein")
        z.append("  Befund über das Programm. Für eine echte Messung: START-AWS.bat.")

    z.append("")
    if lauf is None:
        z.append("Eingelesen: in einem früheren Lauf – dieser Bogen misst nur die Analyse.")
    else:
        z.append(f"Eingelesen: {lauf.get('portionen', '?')} Portionen, "
                 f"{lauf.get('passagen', '?')} Passagen aus 50 Dokumenten")

    z.append("")
    z.append("DIE FÜNF EINGEBAUTEN FUNDE")
    z.append("─" * BREITE)
    zeichen = {"gefunden": "✓", "ohne Beleg": "~", "nicht benannt": "✗"}
    for nummer, f in enumerate(ergebnis["funde"], 1):
        z.append(f"{zeichen[f['urteil']]} Fund {nummer}: {f['name']}   [{f['urteil']}]")
        if f["belegt"]:
            z.append(f"    Fundstellen: {', '.join(f['belegt'])}")
        if f["fehlende_belege"] and f["urteil"] != "nicht benannt":
            z.append(f"    Es fehlt der Beleg aus: {', '.join(f['fehlende_belege'])}")
        if f["urteil"] == "nicht benannt":
            z.append(f"    {f.get('bausteine', '')}")
        if f["beschreibung"]:
            text = f["beschreibung"].replace("\n", " ")
            z.append(f"    „{text[:BREITE - 8]}{'…' if len(text) > BREITE - 8 else ''}\"")
    z.append("─" * BREITE)
    z.append(f"  {ergebnis['gefunden']} von {len(ergebnis['funde'])} Funden benannt und belegt.")

    c = ergebnis["chronologie"]
    z.append("")
    z.append("ZEITSTRAHL")
    z.append("─" * BREITE)
    z.append(_zeile("  Tage der Auflösung enthalten:",
                    f"{len(c['getroffen'])} von {c['erwartet']}"))
    z.append(_zeile("  Einträge insgesamt:", str(c["eintraege"])))
    anteil = (100 * c["routine"] // c["eintraege"]) if c["eintraege"] else 0
    z.append(_zeile("  davon Bautagebuch-Routine:", f"{c['routine']}  ({anteil} %)"))
    for fehlt in c["fehlend"]:
        z.append(f"    fehlt: {fehlt}")

    # Was der Filter gestrichen hat. Ohne diese Zeilen ist ein fehlender Tag
    # zweideutig: Hat das Modell ihn nicht genannt, oder hat aufraeumen ihn
    # wieder entfernt? Am 28.09.2026 war es das Zweite, und drei Laeufe zu
    # je drei Euro haben es nicht gezeigt, weil der Bogen es nicht sagte.
    #
    # Ein Messgeraet muss nicht nur sein Ergebnis nennen, sondern auch, was
    # es auf dem Weg dorthin verworfen hat.
    for satz in ergebnis.get("gestrichen") or []:
        z.append(f"    {satz}")

    z.append("")
    z.append("ZAHLEN")
    z.append("─" * BREITE)
    for zahl in ergebnis["zahlen"]:
        z.append(f"  {'✓' if zahl['steht_da'] else '✗'} {zahl['wert']:<18} {zahl['wofuer']}")

    f = ergebnis["fristensperre"]
    z.append("")
    z.append("FRISTENSPERRE")
    z.append("─" * BREITE)
    if f["haelt"]:
        z.append("  ✓ Keine gerechnete Verjährungsfrist. Die Sperre hält.")
    else:
        z.append("  ✗ Es wurde eine Frist gerechnet – das ist ein Fehler, auch wenn")
        z.append("    das Ergebnis stimmt:")
        for satz in f["verstoesse"]:
            z.append(f"      „{satz[:BREITE - 10]}\"")

    # Beide Posten, getrennt und zusammen. Hier stand einmal nur der zweite,
    # und der ist der kleinere: Der Bogen meldete am 16.09.2026 "0,14 €" für
    # einen Lauf, in dem vorher 882.000 Zeichen durch ein Modell gegangen
    # waren. Wer danach entscheidet, ob ein stärkeres Modell zu teuer ist,
    # entscheidet auf einer Zahl, die den teuren Teil nicht enthält.
    #
    # Das Einlesen ist auch der Posten, der von der Modellwahl abhängt: Es
    # trägt die ganze Akte, die Analyse nur deren Zusammenfassung.
    z.append("")
    z.append("KOSTEN")
    z.append("─" * BREITE)
    # Ohne Einlesen steht hier kein Betrag, sondern ein Satz. "0,00 €" waere
    # eine Luege mit zwei Nachkommastellen: Das Einlesen hat stattgefunden,
    # nur frueher und bezahlt.
    if lauf is None:
        z.append("  Einlesen der 50 Dokumente:      aus einem früheren Lauf, hier nicht")
        z.append("                                  bezahlt und nicht gemessen.")
    else:
        k = lauf.get("kosten") or {}
        tokens = int(k.get("eingabe_tokens", 0)) + int(k.get("ausgabe_tokens", 0))
        z.append(_zeile("  Einlesen der 50 Dokumente:",
                        f"{float(k.get('betrag_eur', 0) or 0):.2f} €   ·   "
                        f"{tokens:,} Token".replace(",", ".")))
    k = ergebnis["kosten"] or {}
    tokens = int(k.get("eingabe_tokens", 0)) + int(k.get("ausgabe_tokens", 0))
    analyse_betrag = float(k.get("betrag_eur", 0) or 0)
    z.append(_zeile("  Analyse über das Gedächtnis:",
                    f"{analyse_betrag:.2f} €   ·   {tokens:,} Token".replace(",", ".")))
    if lauf is None:
        z.append(_zeile("  In diesem Lauf bezahlt:", f"{analyse_betrag:.2f} €"))
    else:
        einlesen = float((lauf.get("kosten") or {}).get("betrag_eur", 0) or 0)
        z.append(_zeile("  Zusammen:", f"{einlesen + analyse_betrag:.2f} €"))

    z.append("")
    z.append("=" * BREITE)
    if lauf is None:
        z.append("Dieser Lauf hat NUR die Analyse gemessen. Das Einlesen stammt aus einem")
        z.append("früheren Lauf – ein Bogen mit Einlesen und einer ohne sind nicht")
        z.append("vergleichbar, wo es um das Einlesen geht.")
    z.append("Was hier NICHT gemessen wird: ob die Texte gut geschrieben sind, ob der")
    z.append("Lebenssachverhalt den Fall trifft, ob ein Entwurf brauchbar wäre.")
    z.append("=" * BREITE)
    return "\n".join(z)


# ── Den Lauf machen ─────────────────────────────────────────────────────────

def _akte_bereitstellen() -> Path:
    quelle = WURZEL / "testdaten" / "grosse-akte"
    if not (quelle / GROSS / "akte.json").is_file():
        print("  Die große Testakte fehlt – sie wird erzeugt …")
        vorlage.erzeugen(quelle / GROSS)
    return quelle


def _fehlertext(roh: str) -> str:
    """Den lesbaren Satz aus der Antwort des Programms holen.

    Die Endpunkte antworten mit ``{"fehler": "..."}``. Roh ausgegeben steht da
    eine Zeile JSON mit ``\n`` als Zeichenfolge - lesbar, aber muehsam, und
    genau dann muehsam, wenn jemand unter Druck etwas sucht.
    """
    try:
        gelesen = json.loads(roh)
    except (ValueError, TypeError):
        return roh.strip()
    if isinstance(gelesen, dict):
        for schluessel in ("fehler", "detail", "message"):
            wert = gelesen.get(schluessel)
            if isinstance(wert, str) and wert.strip():
                return wert.strip()
    return roh.strip()


#: Rueckgabewert bei einem Abbruch - zu unterscheiden von "nicht alle Funde".
#:
#: Beides endete mit 1, und PRUEFBOGEN.bat sagte nach einem Abbruch "Nicht alle
#: Funde wurden benannt - der Bogen sagt, welche" und verwies auf einen Ordner,
#: den es nicht gab. Es gab keinen Bogen; der Lauf war gar nicht gelaufen.
ABBRUCH = 3


def _abbruchtext(was: str, text: str, e: Einstellungen) -> str:
    """Beim Abbruch sagen, mit welchen Kennungen gearbeitet wurde – und woher.

    Aus der Kanzlei, zweimal an einem Abend: „Das Einlesen ist fehlgeschlagen."
    Beim zweiten Mal nannte die Meldung immerhin die Kennung – aber nicht, dass
    sie aus JUSPERFECT_MODELL_ID_KLEIN stammte und dass der Bogen damit gar
    nicht die Kennungen benutzte, die er selbst gesetzt zu haben glaubte. Genau
    das haette den Fall in einem Blick geklaert: Es lief eine alte Startdatei.
    """
    # Der ganze Satz, nicht die ersten 400 Zeichen.
    #
    # Am 28.09.2026 brach die Analyse ab, weil das aufgehobene Gedaechtnis
    # erst zur Haelfte gelesen war. Das stand in der Meldung des Programms -
    # ab Zeichen 430. Abgeschnitten uebrig blieb "Diese Akte ist zu gross",
    # also gerade der Teil, der in die falsche Richtung fuehrt.
    #
    # Eine Meldung zu kuerzen heisst, ueber ihren wichtigsten Teil zu raten.
    zeilen = [f"  {was} ist fehlgeschlagen:", "",
              *(f"  {z}" for z in _fehlertext(text).splitlines()), "",
              f"  Programmstand: {programmstand()}", "",
              "  Gearbeitet wurde mit diesen Kennungen:"]
    for funktion, kennung in e.modelle_uebersicht().items():
        name = _FUNKTIONSNAMEN.get(funktion, funktion)
        zeilen.append(f"     {name + ':':<18} {kennung}")
        zeilen.append(f"     {'':<18} aus {e.modell_herkunft(funktion)}")
    zeilen += ["",
               "  Steht hier etwas anderes, als die Startdatei vor dem Lauf angezeigt",
               "  hat, dann lief eine andere Startdatei als gedacht.",
               "  Welche Kennungen dieses Konto wirklich fuehrt: MODELLE-ANZEIGEN.bat"]
    return "\n".join(zeilen)


def _abbruch(was: str, text: str, e: Einstellungen) -> SystemExit:
    """Den Grund auf den Schirm schreiben und mit ABBRUCH enden.

    Getrennt von ``_abbruchtext``, weil der Rueckgabewert eine Zahl tragen
    muss - sonst kann die Startdatei einen Abbruch nicht von "nicht alle Funde
    benannt" unterscheiden, und beides endete mit 1.
    """
    print(_abbruchtext(was, text, e))
    return SystemExit(ABBRUCH)


def durchgang(gedaechtnis: Path,
              nur_analyse: bool = False) -> tuple[dict, dict | None, str, Einstellungen]:
    """Denselben Weg gehen wie die Oberfläche und das Ergebnis zurückgeben.

    **Warum das Gedächtnis normalerweise weggeworfen wird.** Jede Messung soll
    beim selben Stand anfangen; liefe sie gegen ein gewachsenes Gedächtnis,
    verglichen zwei Bögen Verschiedenes. Deshalb legt ``main`` es in einen
    flüchtigen Ordner.

    **Warum es sich trotzdem aufheben lässt.** Am 28.09.2026 kostete jeder
    Versuch an der Chronologie-Regel 3,04 €, davon 2,73 € für das Einlesen der
    fünfzig Dokumente – und das Einlesen war am Befund unbeteiligt. Vier Läufe,
    zwölf Euro, und die eigentliche Frage („steht das Datum im
    Lebenssachverhalt?") blieb offen, weil niemand hineinsehen konnte.

    Mit ``nur_analyse`` wird das Einlesen übersprungen und das Gedächtnis eines
    früheren Laufs benutzt: 0,31 € statt 3,04 €. Der Bogen weist das aus, denn
    die beiden Läufe sind **nicht** dasselbe – der zweite misst nur noch die
    Analyse, nicht das Einlesen. Ein Messgerät muss sagen, was es gemessen hat.

    Die Dokumente kommen in beiden Fällen in die Arbeitsakte. Das kostet
    nichts, kein Modell wird dabei gefragt – aber ohne sie gibt es keine
    Passagen, gegen die die Belegprüfung prüfen kann, und dann fiele jede
    Aussage der Analyse als unbelegt heraus.
    """
    fixture = _akte_bereitstellen()
    e = Einstellungen.aus_umgebung(_umgebung_mit(fixture, gedaechtnis))
    d = Dienste(e)
    c = TestClient(app_erstellen(e, d), headers={"X-Jusperfect-Nutzer": "ra-weber"},
                   raise_server_exceptions=False)

    sid = c.post("/api/sitzungen", json={"akte_id": GROSS}).json()["sitzung"]["id"]
    print("  Alle fünfzig Dokumente in die Arbeitsakte legen …")
    c.post(f"/api/sitzungen/{sid}/dokumente",
           json={"dokument_ids": [f"D-{n:03d}" for n in range(1, 51)]})

    lauf: dict | None = None
    if nur_analyse:
        print("  Das Einlesen wird übersprungen – Gedächtnis aus einem früheren Lauf.")
    else:
        print("  Die Akte abschnittsweise einlesen (das dauert) …")
        antwort = c.post(f"/api/sitzungen/{sid}/gedaechtnis/einlesen")
        if antwort.status_code != 200:
            raise _abbruch("Das Einlesen", antwort.text, e)
        lauf = antwort.json()["lauf"]

    print("  Über das Aktengedächtnis analysieren …")
    antwort = c.post(f"/api/sitzungen/{sid}/analyse")
    if antwort.status_code != 200:
        raise _abbruch("Die Analyse", antwort.text, e)
    return antwort.json(), lauf, e.anbieter, e


def _umgebung_mit(fixture: Path, gedaechtnis: Path) -> dict[str, str]:
    """Die vorhandene Umgebung, nur auf die große Testakte gerichtet.

    Anbieter und Betriebsart bleiben, wie sie gesetzt sind - ein Prüfbogen soll
    messen, was der Nutzer wirklich laufen lässt, nicht etwas Eigenes. Nur was
    dieser Lauf zwingend braucht, wird ergänzt: die große Testakte als Quelle
    und ein eingeschaltetes Aktengedächtnis, ohne das es kein Einlesen gibt.
    """
    umgebung = dict(os.environ)
    umgebung["JUSPERFECT_JURNODES_ADAPTER"] = "fixture"
    umgebung["JUSPERFECT_FIXTURE_PFAD"] = str(fixture)
    umgebung.setdefault("JUSPERFECT_NUTZER_DATEI", str(WURZEL / "testdaten" / "nutzer.json"))
    umgebung["JUSPERFECT_GEDAECHTNIS"] = "lokal"
    umgebung["JUSPERFECT_GEDAECHTNIS_PFAD"] = str(gedaechtnis)
    return umgebung


def _unvollstaendig(datei: Path) -> str:
    """Sagt, wenn ein aufgehobenes Gedaechtnis nicht zu Ende gelesen ist.

    Sonst laeuft --nur-analyse in die Verweigerung des Programms, und die
    beginnt mit "Diese Akte ist zu gross" - was in die falsche Richtung
    fuehrt. Am 28.09.2026 ist genau das passiert: Der Lauf davor war
    abgebrochen worden, 26 von 50 Dokumenten lagen im Gedaechtnis.

    Bei einem unlesbaren Stand wird nichts behauptet: Dann laeuft der Lauf
    wie bisher und das Programm sagt selbst, was es davon haelt.
    """
    try:
        rohdaten = gzip.decompress(datei.read_bytes())
        g = Aktengedaechtnis.model_validate(json.loads(rohdaten))
    except Exception:
        return ""
    offen = Gedaechtnisdienst.uebersicht(g).get("offene_dokumente", 0)
    if not offen:
        return ""
    gelesen = len(g.dokumente) - offen
    return (f"{gelesen} von {len(g.dokumente)} Dokumenten sind im "
            f"Lebenssachverhalt, {offen} fehlen noch.")


def main() -> int:
    zerleger = argparse.ArgumentParser(description="Prüfbogen für die große Testakte")
    zerleger.add_argument("--speichern", metavar="ORDNER", default=None,
                          help="Bogen und Rohergebnis zusätzlich dorthin schreiben")
    zerleger.add_argument("--gedaechtnis", metavar="ORDNER", default=None,
                          help="Das Aktengedächtnis dort anlegen und aufheben, "
                               "statt es nach dem Lauf wegzuwerfen")
    zerleger.add_argument("--nur-analyse", action="store_true",
                          help="Das Einlesen überspringen und das Gedächtnis aus "
                               "--gedaechtnis benutzen (0,31 € statt 3,04 €)")
    argumente = zerleger.parse_args()

    if argumente.nur_analyse and not argumente.gedaechtnis:
        print("  --nur-analyse braucht --gedaechtnis: ohne aufgehobenes Gedächtnis")
        print("  gibt es nichts zu analysieren.")
        return ABBRUCH

    print("=" * BREITE)
    print("PRÜFBOGEN – ein echter Lauf, gemessen an der Auflösung")
    print("=" * BREITE)

    if argumente.gedaechtnis:
        ordner = Path(argumente.gedaechtnis)
        ordner.mkdir(parents=True, exist_ok=True)
        vorhanden = sorted(ordner.glob("*.json*"))
        if argumente.nur_analyse and not vorhanden:
            print(f"  In {ordner} liegt kein Aktengedächtnis.")
            print("  Erst einen vollen Lauf mit --gedaechtnis, dann --nur-analyse.")
            return ABBRUCH
        if argumente.nur_analyse:
            fehlt = _unvollstaendig(vorhanden[0])
            if fehlt:
                print("  Das aufgehobene Aktengedächtnis ist nur ZUM TEIL gelesen:")
                print(f"  {fehlt}")
                print()
                print("  Eine Analyse darüber wäre wertlos und sähe doch aus wie eine")
                print("  über die ganze Akte. Bitte einen vollen Lauf machen - in")
                print("  PRUEFBOGEN.bat die Wahl [2].")
                return ABBRUCH
        analyse, lauf, anbieter, e = durchgang(ordner, argumente.nur_analyse)
        print(f"\n  Das Aktengedächtnis bleibt liegen in: {ordner.resolve()}")
    else:
        with tempfile.TemporaryDirectory(prefix="pruefbogen-") as fluechtig:
            analyse, lauf, anbieter, e = durchgang(Path(fluechtig))
    ergebnis = messen(analyse)
    text = bogen(ergebnis, lauf, anbieter, e.modelle_uebersicht())
    print("\n" + text)

    if argumente.speichern:
        ordner = Path(argumente.speichern)
        ordner.mkdir(parents=True, exist_ok=True)
        stempel = f"{datetime.now():%Y-%m-%d_%H%M}"
        (ordner / f"pruefbogen_{stempel}.txt").write_text(text + "\n", encoding="utf-8")
        (ordner / f"pruefbogen_{stempel}.json").write_text(
            # Der Einlesevorgang gehoert mit hinein: In ihm steckt der groessere
            # Teil der Kosten, und ohne ihn laesst sich hinterher nicht mehr
            # nachrechnen, was ein Lauf wirklich gekostet hat.
            json.dumps({"ergebnis": ergebnis, "analyse": analyse, "einlesen": lauf},
                       ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(f"\nAbgelegt in {ordner.resolve()}")

    return 0 if ergebnis["gefunden"] == len(vorlage.FUNDE) else 1


if __name__ == "__main__":
    raise SystemExit(main())
