"""Eigene Aufträge der Kanzlei – als Dateien, nicht in einer Oberfläche.

Aus Perfect Shield übernommen. Aus der Kanzlei: „Kann ich die Prompt-Knöpfe
bearbeiten? Ich möchte z. B. einen kleinen Aufsatz zur Rechtslage beifügen."

Die Antwort ist eine Datei. Wer einen eigenen Auftrag will, legt eine Textdatei
in den Auftragsordner; der Dateiname wird die Beschriftung, der Unterordner das
Rechtsgebiet. Bearbeitet wird sie mit dem Editor, den die Kanzlei ohnehin
benutzt – es braucht keine zweite Oberfläche dafür, und was auf dem Laufwerk
liegt, lässt sich sichern und weitergeben.

**Der Aufsatz zur Rechtslage steht in derselben Datei**, hinter einer Trennlinie:

    Entwirf ein Anspruchsschreiben an die Haftpflichtversicherung ...

    --- Rechtslage ---

    Zum Nutzungsausfall: Der Bundesgerichtshof hat entschieden ...

Vor der Trennlinie steht die **Anweisung** – sie füllt beim Aufruf das
Anweisungsfeld des Entwurfs und bleibt bearbeitbar. Dahinter steht **Material**
(Rechtslage, Aufsatz oder ein Musterschriftsatz); es wird dem Entwurf als
Hintergrund mitgegeben. Zwei Textsorten, eine Datei, ein Klick.

Bei jusperfect entfällt die Anonymisierungsprüfung von Perfect Shield (der
Aktentext geht ohnehin in den gesicherten Bedrock-Bereich). Was bleibt, ist die
strenge Grenze des Ordners: kein übergebener Name führt aus ihm heraus.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ENDUNGEN = frozenset({".txt", ".md"})

# So groß darf ein Auftrag samt Material höchstens sein. Er geht bei jeder
# Verwendung mit hinaus und wird mitbezahlt; ein ganzes Handbuch gehört nicht
# dazu.
MAX_AUFTRAG_ZEICHEN = 60_000
MIN_ANWEISUNG_ZEICHEN = 20

# Die Trennlinie zwischen Anweisung und Material. Großzügig gefasst: drei
# Striche, ein Wort, optional Striche – „--- Rechtslage ---", „--- Material ---".
TRENNLINIE = re.compile(
    r"(?m)^[ \t]*-{3,}[ \t]*(?:rechtslage|material|aufsatz|hintergrund|muster|quelle[n]?)"
    r"[ \t]*-{0,}[ \t]*$",
    re.IGNORECASE,
)


class AuftragFehler(RuntimeError):
    """Ein Fehler, dessen Text der Kanzlei angezeigt werden darf."""


@dataclass(frozen=True, slots=True)
class Auftrag:
    name: str        # Weg vom Auftragsordner, mit Schrägstrich: „Verkehrsrecht/Anspruch.txt"
    kategorie: str   # Unterordner davor (Rechtsgebiet), oder leer
    anweisung: str
    material: str

    @property
    def label(self) -> str:
        return Path(self.name).stem

    def uebersicht(self) -> dict:
        return {"name": self.name, "label": self.label, "kategorie": self.kategorie,
                "hat_material": bool(self.material), "zeichen": len(self.anweisung)}


def zerlege(text: str) -> tuple[str, str]:
    """Trennt Anweisung und Material an der Trennlinie.

    Ohne Trennlinie ist alles Anweisung – der Normalfall, der nichts über
    Trennlinien wissen muss.
    """
    treffer = TRENNLINIE.search(text)
    if treffer is None:
        return text.strip(), ""
    return text[:treffer.start()].strip(), text[treffer.end():].strip()


class Auftragsdienst:
    def __init__(self, ordner: str) -> None:
        self._ordner = Path(ordner) if ordner else None

    @property
    def aktiv(self) -> bool:
        return self._ordner is not None

    def _lesbar(self, name: str) -> bool:
        return Path(name).suffix.lower() in ENDUNGEN

    def liste(self) -> list[dict]:
        """Alle Aufträge – Wurzel und eine Ebene Unterordner (Rechtsgebiete)."""
        if self._ordner is None:
            return []
        gefunden: list[Auftrag] = []
        try:
            kategorien = [""] + sorted(
                (e.name for e in self._ordner.iterdir() if e.is_dir() and not e.name.startswith(".")),
                key=str.casefold)
        except OSError as e:
            raise AuftragFehler("Der Auftragsordner ist nicht erreichbar. Ist das Laufwerk verbunden?") from e
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
                try:
                    gefunden.append(self.laden(pfad))
                except AuftragFehler:
                    continue  # eine unbrauchbare Datei blockiert die Liste nicht
        return [a.uebersicht() for a in gefunden]

    def _ziel(self, name: str) -> tuple[Path, list[str]]:
        """Der Pfad zu einem Auftrag – oder ein Fehler.

        Dieselbe Prüfung für Lesen und Anlegen. Sie ist die eigentliche Grenze
        des Ordners: kein übergebener Name führt aus ihm heraus, höchstens ein
        Unterordner tief, keine versteckten Dateien, nur Text.
        """
        if self._ordner is None:
            raise AuftragFehler("Es ist kein Auftragsordner eingerichtet (JUSPERFECT_AUFTRAG_ORDNER).")
        if not self._lesbar(name):
            raise AuftragFehler("Ein eigener Auftrag ist eine Textdatei (.txt oder .md).")
        # Ein Name, der wie ein absoluter Pfad aussieht, ist keiner. Ohne diese
        # Zeile wurde aus "/etc/passwd.txt" der Unterordner "etc" im
        # Auftragsordner - nicht gefaehrlich, aber auch nicht gewollt: Ein
        # Auftrag traegt den Namen, den die Kanzlei ihm gibt.
        roh = name.replace("\\", "/")
        if roh.startswith("/") or (len(roh) > 1 and roh[1] == ":"):
            raise AuftragFehler("Ein Auftragsname ist ein Name, kein Pfad.")
        teile = [t for t in roh.split("/") if t]
        if not teile or len(teile) > 2:
            raise AuftragFehler("Diesen Auftrag gibt es nicht.")
        for teil in teile:
            if teil.startswith(".") or teil in ("..", "."):
                raise AuftragFehler("Diesen Auftrag gibt es nicht.")
        ziel = self._ordner.joinpath(*teile)
        try:
            aufgeloest, wurzel = ziel.resolve(), self._ordner.resolve()
            if wurzel not in aufgeloest.parents:
                raise AuftragFehler("Dieser Auftrag liegt nicht im Auftragsordner.")
            if aufgeloest.parent != wurzel and aufgeloest.parent.parent != wurzel:
                raise AuftragFehler("Dieser Auftrag liegt nicht im Auftragsordner.")
        except OSError as e:
            raise AuftragFehler("Der Auftrag ist nicht erreichbar.") from e
        return ziel, teile

    def anlegen(self, name: str, text: str) -> Auftrag:
        """Einen neuen Auftrag als Datei ablegen – nur einen neuen.

        Der Weg dahin ist ein Vorschlag, den ein Mensch gelesen und freigegeben
        hat (services/auftragsvorschlag.py). Hier steht die letzte Grenze:

        * Der Ordner bleibt hart – dieselbe Prüfung wie beim Lesen.
        * **Eine vorhandene Datei wird nie überschrieben.** Was die Kanzlei
          selbst geschrieben hat, darf ein Vorschlag nicht verdrängen; das
          fiele erst auf, wenn der alte Text gebraucht würde und fehlte.
        * Es gelten dieselben Maße wie beim Lesen: Ein Auftrag, der nicht
          geladen werden könnte, wird auch nicht angelegt.
        """
        ziel, teile = self._ziel(name)
        if ziel.exists():
            raise AuftragFehler(
                f"„{name}“ gibt es bereits. Bitte einen anderen Namen wählen – "
                "ein vorhandener Auftrag wird nicht überschrieben.")
        if len(text) > MAX_AUFTRAG_ZEICHEN:
            raise AuftragFehler(
                f"Der Auftrag ist zu lang ({len(text)} Zeichen; erlaubt sind "
                f"{MAX_AUFTRAG_ZEICHEN}). Er geht bei jeder Verwendung mit hinaus.")
        anweisung, _ = zerlege(text)
        if len(anweisung) < MIN_ANWEISUNG_ZEICHEN:
            raise AuftragFehler(
                "Vor der Trennlinie steht kaum Text. Dort gehört die Anweisung hin.")
        try:
            ziel.parent.mkdir(parents=True, exist_ok=True)
            # Ausschliessliches Anlegen: Gibt es die Datei doch schon - weil
            # jemand sie in derselben Sekunde angelegt hat -, bricht es ab,
            # statt zu ueberschreiben.
            with open(ziel, "x", encoding="utf-8", newline="\n") as datei:
                datei.write(text.strip() + "\n")
        except FileExistsError as e:
            raise AuftragFehler(f"„{name}“ gibt es bereits.") from e
        except OSError as e:
            raise AuftragFehler(
                f"Der Auftrag ließ sich nicht anlegen ({type(e).__name__}). "
                "Ist der Auftragsordner beschreibbar?") from e
        return self.laden("/".join(teile))

    def laden(self, name: str) -> Auftrag:
        """Einen Auftrag lesen – und nur aus dem Auftragsordner."""
        ziel, teile = self._ziel(name)
        if not ziel.is_file():
            raise AuftragFehler(f"Der Auftrag „{name}“ ist nicht vorhanden.")
        try:
            roh = ziel.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                roh = ziel.read_text(encoding="cp1252")
            except (OSError, UnicodeDecodeError) as e:
                raise AuftragFehler(f"„{name}“ ließ sich nicht als Text lesen.") from e
        except OSError as e:
            raise AuftragFehler("Der Auftrag ließ sich nicht lesen.") from e
        if len(roh) > MAX_AUFTRAG_ZEICHEN:
            raise AuftragFehler(
                f"„{name}“ ist zu lang ({len(roh)} Zeichen; erlaubt sind {MAX_AUFTRAG_ZEICHEN}). "
                "Der Auftrag geht bei jeder Verwendung mit hinaus.")
        anweisung, material = zerlege(roh)
        if len(anweisung) < MIN_ANWEISUNG_ZEICHEN:
            raise AuftragFehler(f"„{name}“ enthält vor der Trennlinie kaum Text. Dort steht die Anweisung.")
        return Auftrag(name="/".join(teile), kategorie=teile[0] if len(teile) == 2 else "",
                       anweisung=anweisung, material=material)
