"""Die Promptbibliothek: Ueberschrift und Frage, je Rechtsgebiet.

Aus der Kanzlei am 13.10.2026, in drei Schritten gewachsen:

    „Koennen wir noch eine Promptbibliothek anlegen. Diese fragt aber erst
    nach dem Rechtsgebiet. Fuer jedes Rechtsgebiet gibt es dann eine eigene
    kleine Promptbibliothek. Diese kann dann ueber dem Chatfenster sein."

    „Kann ich die Promptbibliothek nicht waehrend der Arbeit fuellen?"

    „Promptbibliothek neu und dann Ueberschrift und Prompt eintragen -
    einige sind schon vorher eingetragen."

Daraus folgen die drei Dinge, die dieses Modul ausmachen:

1. **Ueberschrift und Text sind zweierlei.** Ein brauchbarer Prompt ist
   mehrere Zeilen lang; als Knopfbeschriftung taugt er nicht. In der Leiste
   steht die Ueberschrift, ins Eingabefeld kommt der Text.
2. **Sie waechst waehrend der Arbeit.** Eine Bibliothek, die vorab am
   Schreibtisch entsteht, enthaelt die Fragen, die man fuer wichtig HAELT;
   eine, die beim Arbeiten waechst, die, die sich bewaehrt haben.
3. **Einiges ist schon da.** Ein mitgelieferter Vorrat je Rechtsgebiet, damit
   die Leiste am ersten Tag nicht leer ist.

**Das Rechtsgebiet steht schon in der Akte.** jur|nodes liefert es als
``lawCategory``; es kommt als ``akte.rechtsgebiet`` an. Es muss also niemand
gefragt werden - die Bibliothek ueber dem Chat ist von selbst die zum
laufenden Mandat.

**Wo die eigene Datei liegt: ausserhalb des Programmordners.** Denselben Weg
geht die Sperrliste, aus demselben Grund (Befund N01 vom 12.10.2026): Eine
Datei im Programmordner waere in jedem ZIP, das die Kanzlei herunterlaedt -
die gesammelten Prompts waeren beim naechsten Herunterladen weg.

**Der Vorrat dagegen liegt IM Programmordner** und wird nie beschrieben. Er
gehoert zum Programm wie die Packs. Wer einen Vorratseintrag wegnimmt,
loescht deshalb nichts, sondern blendet ihn aus - sonst waere er beim
naechsten ZIP wieder da.

**Was hier NICHT passiert:** Der Wortlaut eines Prompts wird nirgends
protokolliert. Ein Prompt aus der Arbeit kann einen Namen enthalten; ins
Protokoll gehen Anzahl und Rechtsgebiet, nie der Text.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

#: Der Name der eigenen Datei. Immer derselbe, an beiden Orten.
DATEINAME = "jusperfect-promptbibliothek.json"

#: Der Programmordner - zwei Ebenen ueber dieser Datei.
PROGRAMMORDNER = Path(__file__).resolve().parent.parent.parent

#: Der mitgelieferte Vorrat. Liegt IM Programmordner und wird nur gelesen.
VORRAT = Path(__file__).resolve().parent.parent / "promptvorrat.json"

#: Ohne Angabe aus der Akte landen Prompts hier. Ein eigener Schluessel und
#: kein leerer: Sonst waere nicht zu sehen, WARUM ein Eintrag nirgends
#: auftaucht.
OHNE_GEBIET = "Ohne Rechtsgebiet"

#: Laenger als das ist kein Prompt mehr, sondern ein Schriftsatz.
MAX_ZEICHEN = 4000

#: Eine Ueberschrift muss in eine Leiste passen.
MAX_TITEL = 80

#: Mehr als das je Rechtsgebiet ist keine Auswahl mehr, sondern eine Liste,
#: die man durchsuchen muesste - dann waere nichts gewonnen.
MAX_EINTRAEGE = 60


class BibliothekFehler(Exception):
    """Die Datei ist da, laesst sich aber nicht lesen oder nicht schreiben."""


# ── Orte ───────────────────────────────────────────────────────────────────

def orte() -> tuple[Path, ...]:
    """Wo gesucht wird - erst neben dem Programmordner, dann im Benutzerordner."""
    gefunden: list[Path] = []
    for ort in (PROGRAMMORDNER.parent / DATEINAME, Path.home() / DATEINAME):
        if ort not in gefunden:
            gefunden.append(ort)
    return tuple(gefunden)


def finden() -> Path | None:
    """Die vorhandene eigene Datei - oder ``None``, wenn es noch keine gibt."""
    for ort in orte():
        try:
            if ort.is_file():
                return ort
        except OSError:              # ein Pfad, den dieses System nicht mag
            continue
    return None


def _ziel() -> Path:
    """Wohin geschrieben wird: an den vorhandenen Ort, sonst an den ersten."""
    return finden() or orte()[0]


# ── Glaetten und Vergleichen ───────────────────────────────────────────────

def _schluessel(rechtsgebiet: str) -> str:
    return " ".join((rechtsgebiet or "").split()) or OHNE_GEBIET


def _kern(gebiet: str) -> str:
    """Nur Buchstaben, klein - "Verkehrs-Recht" und "verkehrsrecht" sind eins."""
    return re.sub(r"[^0-9a-zäöüß]+", "", (gebiet or "").casefold())


#: So viele gleiche Anfangsbuchstaben muessen zwei Gebietsbezeichnungen
#: teilen, damit sie als dasselbe Gebiet gelten. Sechs ist mit Bedacht
#: gewaehlt: „verkehrs" (8) verbindet Verkehrsrecht und
#: Verkehrsunfallrecht, „ver" (3) trennt Verkehrsrecht und Vertragsrecht.
GLEICHER_ANFANG = 6


def _passt(eines: str, anderes: str) -> bool:
    """Zwei Gebietsbezeichnungen meinen dasselbe.

    jur|nodes schreibt ``lawCategory`` so, wie es die Kanzlei angelegt hat -
    einmal „Verkehrsrecht", einmal „Verkehr", einmal „Verkehrsunfallrecht".
    Ein Vorrat, der nur beim Wort-fuer-Wort-Treffer erscheint, erschiene
    nirgends.

    Deshalb zaehlt auch ein gemeinsamer Anfang. Das ist mit Absicht grob: Der
    Preis eines Fehlgriffs ist ein Prompt zuviel in der Leiste, den man nicht
    anklickt - der Preis einer zu engen Regel waere eine Leiste, die bei jeder
    zweiten Akte leer bleibt, ohne dass jemand den Grund saehe.
    """
    a, b = _kern(eines), _kern(anderes)
    if not a or not b:
        return a == b
    if a == b:
        return True
    if a.startswith(b) or b.startswith(a):
        return len(min(a, b, key=len)) >= 4
    gemeinsam = 0
    for links, rechts in zip(a, b):
        if links != rechts:
            break
        gemeinsam += 1
    return gemeinsam >= GLEICHER_ANFANG


def _titel_glaetten(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()[:MAX_TITEL]


def _text_glaetten(text: str) -> str:
    """Zeilen bleiben - ein Prompt darf mehrzeilig sein; Raender fallen weg."""
    sauber = "\n".join(zeile.rstrip() for zeile in (text or "").splitlines())
    return re.sub(r"\n{3,}", "\n\n", sauber).strip()[:MAX_ZEICHEN]


def _eintrag(roh: object) -> dict[str, str] | None:
    """Ein Eintrag aus der Datei - oder ``None``, wenn nichts Brauchbares.

    Ein blosser Text wird als Eintrag ohne eigene Ueberschrift gelesen: So
    bleiben Sammlungen lesbar, die vor dem 13.10.2026 entstanden sind, als es
    nur die Frage und keine Ueberschrift gab.
    """
    if isinstance(roh, str):
        text = _text_glaetten(roh)
        return {"titel": _titel_glaetten(text), "text": text} if text else None
    if isinstance(roh, dict):
        text = _text_glaetten(str(roh.get("text", "")))
        if not text:
            return None
        titel = _titel_glaetten(str(roh.get("titel", ""))) or _titel_glaetten(text)
        return {"titel": titel, "text": text}
    return None


# ── Der mitgelieferte Vorrat ───────────────────────────────────────────────

def vorrat(ort: Path | None = None) -> dict[str, list[dict[str, str]]]:
    """Was mitgeliefert wird. Faellt er aus, faellt nur er aus.

    Anders als bei der eigenen Datei wird hier abgefangen: Der Vorrat ist
    Zugabe. Ein beschaedigter Vorrat darf die eigene Sammlung nicht
    verschatten und die Akte nicht aufhalten.
    """
    ort = ort or VORRAT
    try:
        roh = json.loads(ort.read_text(encoding="utf-8"))
        gebiete = roh["rechtsgebiete"]
        if not isinstance(gebiete, dict):
            return {}
    except (OSError, UnicodeDecodeError, ValueError, KeyError, TypeError):
        return {}
    fertig: dict[str, list[dict[str, str]]] = {}
    for gebiet, liste in gebiete.items():
        if not isinstance(liste, list):
            continue
        eintraege = [e for e in (_eintrag(x) for x in liste) if e]
        if eintraege:
            fertig[_schluessel(str(gebiet))] = eintraege
    return fertig


# ── Die eigene Datei ───────────────────────────────────────────────────────

def laden(ort: Path | None = None) -> dict[str, object]:
    """Die eigene Sammlung: ``{"rechtsgebiete": …, "versteckt": …}``.

    **Eine unlesbare Datei wird nicht durch eine leere ersetzt.** Das waere
    der bequeme Weg und der falsche: In der Datei steht die Sammlung von
    Monaten. Laesst sie sich nicht lesen, sagt das Programm das und ruehrt
    sie nicht an.
    """
    ort = ort or finden()
    if ort is None or not ort.is_file():
        return {"rechtsgebiete": {}, "versteckt": {}}
    try:
        roh = json.loads(ort.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as fehler:
        raise BibliothekFehler(
            f"Die Promptbibliothek liegt in {ort}, laesst sich aber nicht lesen: "
            f"{fehler}. Die Datei wurde nicht veraendert."
        ) from fehler
    gebiete = roh.get("rechtsgebiete") if isinstance(roh, dict) else None
    if not isinstance(gebiete, dict):
        raise BibliothekFehler(
            f"Die Promptbibliothek in {ort} hat nicht den erwarteten Aufbau "
            "(es fehlt der Abschnitt „rechtsgebiete“). Die Datei wurde "
            "nicht veraendert."
        )
    eigene: dict[str, list[dict[str, str]]] = {}
    for gebiet, liste in gebiete.items():
        if not isinstance(liste, list):
            continue
        hier: list[dict[str, str]] = []
        for roh_eintrag in liste:
            eintrag = _eintrag(roh_eintrag)
            if eintrag and eintrag["text"].casefold() not in {e["text"].casefold() for e in hier}:
                hier.append(eintrag)
        eigene[_schluessel(str(gebiet))] = hier[:MAX_EINTRAEGE]
    verborgen: dict[str, list[str]] = {}
    for gebiet, liste in (roh.get("versteckt") or {}).items():
        if isinstance(liste, list):
            verborgen[_schluessel(str(gebiet))] = [str(x) for x in liste if isinstance(x, str)]
    return {"rechtsgebiete": eigene, "versteckt": verborgen}


def _ablegen(bestand: dict[str, object], ort: Path) -> None:
    """Erst daneben schreiben, dann umbenennen - ein Abbruch kostet nichts.

    Ohne das koennte ein Stromausfall mitten im Schreiben eine halbe Datei
    hinterlassen, und die waere nach ``laden`` unlesbar: die Sammlung weg,
    obwohl nur ein Eintrag dazukommen sollte.
    """
    inhalt = json.dumps(bestand, ensure_ascii=False, indent=2)
    try:
        ort.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False,
                                         dir=str(ort.parent),
                                         prefix=ort.name + ".", suffix=".neu") as datei:
            datei.write(inhalt + "\n")
            vorlaeufig = Path(datei.name)
        os.replace(vorlaeufig, ort)
    except OSError as fehler:
        raise BibliothekFehler(
            f"Die Promptbibliothek liess sich nicht nach {ort} schreiben: {fehler}"
        ) from fehler


# ── Was in der Leiste steht ────────────────────────────────────────────────

def eintraege(rechtsgebiet: str, ort: Path | None = None,
              vorrat_ort: Path | None = None) -> tuple[dict[str, object], ...]:
    """Was zu diesem Rechtsgebiet bereitsteht - Eigenes zuerst, Vorrat danach.

    Eigenes zuerst, weil es die Kanzlei selbst abgelegt hat; der Vorrat ist
    nur der Anfang. Jeder Eintrag sagt, woher er kommt (``mitgeliefert``) -
    die Oberflaeche zeigt es, damit niemand raetselt, warum etwas dasteht,
    das er nie eingetippt hat.
    """
    bestand = laden(ort)
    eigene_alle: dict[str, list[dict[str, str]]] = bestand["rechtsgebiete"]   # type: ignore[assignment]
    verborgen_alle: dict[str, list[str]] = bestand["versteckt"]               # type: ignore[assignment]

    # Ueber den Schluessel, nicht ueber den Rohwert: Eine Akte ohne
    # Rechtsgebiet soll finden, was unter OHNE_GEBIET abgelegt wurde.
    gesucht = _schluessel(rechtsgebiet)

    eigene: list[dict[str, str]] = []
    for gebiet, liste in eigene_alle.items():
        if _passt(gebiet, gesucht):
            eigene.extend(liste)
    verborgen = {t.casefold() for gebiet, titel in verborgen_alle.items()
                 if _passt(gebiet, gesucht) for t in titel}

    fertig: list[dict[str, object]] = [
        {"titel": e["titel"], "text": e["text"], "mitgeliefert": False}
        for e in reversed(eigene)          # zuletzt Abgelegtes zuerst
    ]
    schon = {e["text"].casefold() for e in eigene}
    for gebiet, liste in vorrat(vorrat_ort).items():
        if not _passt(gebiet, gesucht):
            continue
        for e in liste:
            if e["titel"].casefold() in verborgen or e["text"].casefold() in schon:
                continue
            fertig.append({"titel": e["titel"], "text": e["text"], "mitgeliefert": True})
    return tuple(fertig)


def merken(rechtsgebiet: str, titel: str, text: str,
           ort: Path | None = None) -> None:
    """Einen Prompt hinterlegen.

    Ohne Ueberschrift wird der Anfang des Textes eine - besser eine
    abgeschnittene als gar keine: In der Leiste steht sonst nichts.

    Doppelter Text wird nicht zweimal abgelegt, auch nicht mit anderer Gross-
    und Kleinschreibung.
    """
    sauber = _text_glaetten(text)
    if not sauber:
        raise BibliothekFehler("Ein leerer Prompt laesst sich nicht ablegen.")
    ueberschrift = _titel_glaetten(titel) or _titel_glaetten(sauber)
    ort = ort or _ziel()
    bestand = laden(ort)
    gebiete: dict[str, list[dict[str, str]]] = bestand["rechtsgebiete"]   # type: ignore[assignment]
    gebiet = _schluessel(rechtsgebiet)
    liste = gebiete.setdefault(gebiet, [])
    if sauber.casefold() in {e["text"].casefold() for e in liste}:
        return
    if len(liste) >= MAX_EINTRAEGE:
        raise BibliothekFehler(
            f"Zu „{gebiet}“ sind schon {MAX_EINTRAEGE} Prompts hinterlegt. "
            "Bitte zuerst einen entfernen, der nicht mehr gebraucht wird."
        )
    liste.append({"titel": ueberschrift, "text": sauber})
    _ablegen(bestand, ort)


def vergessen(rechtsgebiet: str, titel: str, ort: Path | None = None) -> None:
    """Einen Eintrag herausnehmen - sonst waere jeder Vertipper endgueltig.

    Ein eigener Eintrag wird geloescht. Ein mitgelieferter wird ausgeblendet:
    Loeschen koennte man ihn nur im Programmordner, und beim naechsten ZIP
    waere er wieder da.
    """
    gesucht = _titel_glaetten(titel)
    gebiet_gesucht = _schluessel(rechtsgebiet)
    ort = ort or _ziel()
    bestand = laden(ort)
    gebiete: dict[str, list[dict[str, str]]] = bestand["rechtsgebiete"]   # type: ignore[assignment]
    verborgen: dict[str, list[str]] = bestand["versteckt"]                # type: ignore[assignment]
    geaendert = False
    for gebiet, liste in gebiete.items():
        if not _passt(gebiet, gebiet_gesucht):
            continue
        uebrig = [e for e in liste if e["titel"].casefold() != gesucht.casefold()]
        if len(uebrig) != len(liste):
            gebiete[gebiet] = uebrig
            geaendert = True
    for gebiet, liste in vorrat().items():
        if not _passt(gebiet, gebiet_gesucht):
            continue
        if any(e["titel"].casefold() == gesucht.casefold() for e in liste):
            weg = verborgen.setdefault(gebiet_gesucht, [])
            if gesucht not in weg:
                weg.append(gesucht)
                geaendert = True
    if geaendert:
        _ablegen(bestand, ort)
