"""Referenzen: veröffentlichtes Material als Zusatz zur Akte.

Aus Perfect Shield übernommen. Aus der Kanzlei: „Ich möchte Urteile, Gesetze,
Tarifverträge in den Kontext ziehen." Das ist etwas anderes als eine Akte, und
der Unterschied ist keiner der Form, sondern des Wesens: Eine Akte ist das
Geheimnis des Mandanten, ein Gesetz kann ohnehin jeder lesen.

Bei Perfect Shield lag hier die heikelste Abwägung – wonach eine Referenz
geprüft wird, damit ein Urteil durchgeht, aber keine Akte hindurchrutscht. Bei
jusperfect entfällt sie: Es wird ohnehin nicht anonymisiert, der Text geht in
den gesicherten Bedrock-Bereich. Was bleibt, ist der Zweck – veröffentlichtes
Material neben die Akte stellen – und die Sorgfalt im Umgang damit:

* **Getrennt von der Akte.** Referenzen tragen eigene Fundstellen-Kennungen
  (``R1-P2``), damit in Antwort und Beleg sichtbar bleibt, was aus der Akte
  stammt und was aus einem Urteil.
* **Mitzitierbar.** Die Referenzpassagen stehen im selben Belegindex wie die
  Aktenpassagen; die Belegpflicht gilt für sie genauso.
* **Begrenzt.** Was mitgeht, geht bei jeder Frage mit und wird mitbezahlt. Ein
  ganzer Kommentar hat hier nichts zu suchen; die Gesamtmenge ist gedeckelt.
* **Die Grenze des Ordners ist hart.** Kein übergebener Name führt aus ihm
  heraus.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jusperfect.domain.models import Dokument, Passage
from jusperfect.ocr.base import OcrDienst, OcrFehler
from jusperfect.services.extraktion import NichtUnterstuetzt, text_extrahieren
from jusperfect.services.passagen import passagen_bilden

ENDUNGEN = frozenset({".txt", ".md", ".pdf"})

# So viel veröffentlichtes Material darf höchstens mitgehen. Es geht bei jeder
# Frage mit und wird mitbezahlt; ein ganzer Kommentar gehört nicht dazu.
MAX_REFERENZ_ZEICHEN = 120_000


class ReferenzFehler(RuntimeError):
    """Ein Fehler, dessen Text der Kanzlei angezeigt werden darf."""


@dataclass(frozen=True, slots=True)
class Referenz:
    name: str        # Weg vom Referenzordner, mit Schrägstrich
    kategorie: str

    @property
    def label(self) -> str:
        return Path(self.name).stem

    def uebersicht(self) -> dict:
        return {"name": self.name, "label": self.label, "kategorie": self.kategorie}


class Referenzendienst:
    def __init__(self, ordner: str, ocr: OcrDienst) -> None:
        self._ordner = Path(ordner) if ordner else None
        self._ocr = ocr

    @property
    def aktiv(self) -> bool:
        return self._ordner is not None

    def _lesbar(self, name: str) -> bool:
        return Path(name).suffix.lower() in ENDUNGEN

    def liste(self) -> list[dict]:
        """Alle Referenzen – Wurzel und eine Ebene Unterordner (Rechtsgebiete)."""
        if self._ordner is None:
            return []
        try:
            kategorien = [""] + sorted(
                (e.name for e in self._ordner.iterdir() if e.is_dir() and not e.name.startswith(".")),
                key=str.casefold)
        except OSError as e:
            raise ReferenzFehler("Der Referenzordner ist nicht erreichbar. Ist das Laufwerk verbunden?") from e
        gefunden: list[Referenz] = []
        for kategorie in kategorien:
            ort = self._ordner / kategorie if kategorie else self._ordner
            try:
                namen = sorted((e.name for e in ort.iterdir()
                                if e.is_file() and self._lesbar(e.name) and not e.name.startswith(".")),
                               key=str.casefold)
            except OSError:
                continue
            for name in namen:
                pfad = f"{kategorie}/{name}" if kategorie else name
                gefunden.append(Referenz(name=pfad, kategorie=kategorie))
        return [r.uebersicht() for r in gefunden]

    def _sicher(self, name: str) -> Path:
        """Löst einen Namen auf – und nur innerhalb des Referenzordners."""
        if self._ordner is None:
            raise ReferenzFehler("Es ist kein Referenzordner eingerichtet (JUSPERFECT_REFERENZ_ORDNER).")
        if not self._lesbar(name):
            raise ReferenzFehler("Eine Referenz ist eine Text- oder PDF-Datei (.txt, .md, .pdf).")
        teile = [t for t in name.replace("\\", "/").split("/") if t]
        if not teile or len(teile) > 2 or any(t.startswith(".") or t in ("..", ".") for t in teile):
            raise ReferenzFehler("Diese Referenz gibt es nicht.")
        ziel = self._ordner.joinpath(*teile)
        try:
            aufgeloest, wurzel = ziel.resolve(), self._ordner.resolve()
            if wurzel not in aufgeloest.parents:
                raise ReferenzFehler("Diese Referenz liegt nicht im Referenzordner.")
            if aufgeloest.parent != wurzel and aufgeloest.parent.parent != wurzel:
                raise ReferenzFehler("Diese Referenz liegt nicht im Referenzordner.")
        except OSError as e:
            raise ReferenzFehler("Die Referenz ist nicht erreichbar.") from e
        if not ziel.is_file():
            raise ReferenzFehler(f"Die Referenz „{name}“ ist nicht vorhanden.")
        return ziel

    def passagen(self, namen: list[str]) -> list[Passage]:
        """Die gewählten Referenzen als Passagen mit ``R``-Kennungen, gedeckelt.

        Bei jeder Verwendung frisch gelesen: Eine Datei auf dem Laufwerk kann
        sich ändern, und niemand sagt es dem Programm.
        """
        if self._ordner is None or not namen:
            return []
        ergebnis: list[Passage] = []
        gesamt = 0
        for nr, name in enumerate(namen, start=1):
            ziel = self._sicher(name)
            daten = ziel.read_bytes()
            titel = Path(name).stem
            dokument = Dokument(id=f"referenz:{name}", akte_id="referenz", titel=titel, dateiname=Path(name).name)
            try:
                seiten, _ = text_extrahieren(dokument, daten, self._ocr, "referenz")
            except (NichtUnterstuetzt, OcrFehler) as e:
                raise ReferenzFehler(f"„{name}“ ließ sich nicht lesen: {e}") from e
            for p in passagen_bilden(nr, dokument, seiten):
                if gesamt + len(p.text) > MAX_REFERENZ_ZEICHEN:
                    return ergebnis  # Deckel erreicht; der Rest bleibt draußen
                gesamt += len(p.text)
                ergebnis.append(p.model_copy(update={"kennung": "R" + p.kennung[1:]}))
        return ergebnis

    def pruefen(self, namen: list[str]) -> list[str]:
        """Stellt sicher, dass jede genannte Referenz existiert; gibt sie zurück."""
        for name in namen:
            self._sicher(name)
        return list(namen)
