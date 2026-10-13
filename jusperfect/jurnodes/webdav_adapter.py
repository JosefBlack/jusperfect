"""jurnodes aus einem Ordnerbaum – der WebDAV-Export der Kanzlei.

jur|nodes legt die Akten als Ordner ab, die über ein eingebundenes Laufwerk
(WebDAV/OneDrive/Nextcloud) erreichbar sind. Der Baum ist:

    <Wurzel>/<Anwalt>/<Jahr>/<Aktenzeichen Bezeichnung>/<Dokumente>

Beispiel: ``J:/Akten/Dortschy/2026/X-001-2026 ohne Name wer gegen wen``. Der
Ordnername einer Akte trägt vorn das Aktenzeichen (bis zum ersten Leerzeichen),
dahinter die Bezeichnung. Der Anwalt ist der Sachbearbeiter, das Jahr steht im
Aktenzeichen.

Dieser Adapter liest bedarfsbezogen – die Aktenliste beim Suchen, den
Dokumenttext erst beim Laden. Geschrieben wird nur eine Sache und nur mit
Freigabe: ein Vermerk als Datei in den Unterordner ``Vermerke`` der Akte.
Gelöscht wird nichts, umbenannt nichts, verschoben nichts.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path

from jusperfect.domain.models import Akte, Beteiligter, Dokument, Frist
from jusperfect.jurnodes import gedaechtnisdatei
from jusperfect.jurnodes.base import AkteNichtGefunden, DokumentNichtGefunden, JurNodesFehler
from jusperfect.security.approval import Freigabe, Freigabestelle

MIME_NACH_ENDUNG = {
    ".txt": "text/plain", ".md": "text/markdown", ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".tif": "image/tiff", ".tiff": "image/tiff",
}
# Dateitypen, aus denen Text zu holen ist. Anderes (z. B. .msg, .zip) wird in
# der Dokumentliste nicht angeboten – es ginge ohnehin nicht durch die Analyse.
DOKUMENT_ENDUNGEN = frozenset(MIME_NACH_ENDUNG)
VERMERK_ORDNER = "Vermerke"


class WebDavJurNodesAdapter:
    def __init__(self, wurzel: Path, freigabestelle: Freigabestelle, schreibbar: bool = True,
                 archiv_kennung: str = "archiviert") -> None:
        self._wurzel = Path(wurzel)
        self._freigabestelle = freigabestelle
        self._schreibbar = schreibbar
        self._archiv_kennung = (archiv_kennung or "").strip()
        # Ganzes Wort, Groß-/Kleinschreibung egal; Klammern oder Bindestriche
        # ringsum stören nicht („D-1 (archiviert) Meier").
        self._archiv_muster = (
            re.compile(rf"(?<!\w){re.escape(self._archiv_kennung)}(?!\w)", re.IGNORECASE)
            if self._archiv_kennung else None
        )
        self._index: dict[str, Path] | None = None  # Aktenzeichen -> Aktenordner
        if not self._wurzel.is_dir():
            raise JurNodesFehler(f"Aktenordner nicht gefunden: {self._wurzel}")

    # ── Baum lesen ──────────────────────────────────────────────────────────

    @staticmethod
    def _teile(ordnername: str) -> tuple[str, str]:
        """„X-001-2026 ohne Name wer gegen wen" -> ("X-001-2026", "ohne Name …")."""
        name = ordnername.strip()
        m = re.match(r"^(\S+)\s+(.*)$", name)
        if m:
            return m.group(1), m.group(2).strip()
        return name, ""

    def _status_aus_name(self, ordnername: str) -> tuple[str, str]:
        """Liest den Aktenstatus aus dem Ordnernamen und räumt ihn heraus.

        In jurnodes wird eine Akte von Hand archiviert; im Ordnernamen steht
        dann die Kennung. Ohne Kennung ist die Akte nicht archiviert, also
        laufend. Ist keine Konvention eingestellt, bleibt der Status
        ausdrücklich unbekannt – dann wird nichts gelöscht.

        Geprüft wird der ganze Ordnername, bevor er in Aktenzeichen und
        Bezeichnung zerlegt wird: Die Kennung kann auch vorn stehen und würde
        sonst als Aktenzeichen gelesen.
        """
        if self._archiv_muster is None:
            return "unbekannt", ordnername
        if not self._archiv_muster.search(ordnername):
            return "laufend", ordnername
        rest = self._archiv_muster.sub(" ", ordnername)
        # Übrig gebliebene Klammern und Trenner der Kennung entfernen.
        rest = re.sub(r"\(\s*\)|\[\s*\]|\{\s*\}", " ", rest)
        rest = re.sub(r"\s+", " ", rest).strip(" -–_,;")
        return "archiviert", rest

    def _akte_aus_ordner(self, anwalt: str, ordner: Path) -> Akte:
        status, name = self._status_aus_name(ordner.name)
        aktenzeichen, bezeichnung = self._teile(name)
        return Akte(id=aktenzeichen, aktenzeichen=aktenzeichen,
                    bezeichnung=bezeichnung or "(ohne Bezeichnung)", sachbearbeiter=anwalt,
                    status=status)

    def _baum(self) -> dict[str, Path]:
        """Einmal durch <Anwalt>/<Jahr>/<Akte>; Aktenzeichen -> Ordner.

        Der Index wird beim Suchen aufgebaut und danach wiederverwendet; wird
        eine Akte nicht gefunden, einmal neu gelesen (der Ordner kann wachsen).
        """
        index: dict[str, Path] = {}
        try:
            anwaelte = [p for p in self._wurzel.iterdir() if p.is_dir() and not p.name.startswith(".")]
        except OSError as e:
            raise JurNodesFehler("Der Aktenordner ist nicht erreichbar. Ist das Laufwerk verbunden?") from e
        for anwalt in sorted(anwaelte, key=lambda p: p.name.casefold()):
            for jahr in sorted((p for p in anwalt.iterdir() if p.is_dir() and p.name.isdigit()),
                               key=lambda p: p.name, reverse=True):
                for akte in sorted((p for p in jahr.iterdir() if p.is_dir() and not p.name.startswith(".")),
                                   key=lambda p: p.name.casefold()):
                    _, name = self._status_aus_name(akte.name)
                    az, _ = self._teile(name)
                    index.setdefault(az, akte)  # erstes Vorkommen gewinnt
        return index

    def _ordner(self, akte_id: str) -> Path:
        if self._index is None or akte_id not in self._index:
            self._index = self._baum()
        ordner = self._index.get(akte_id)
        if ordner is None or not ordner.is_dir():
            raise AkteNichtGefunden(f"Akte {akte_id} nicht gefunden.")
        return ordner

    def _anwalt_von(self, ordner: Path) -> str:
        # <Wurzel>/<Anwalt>/<Jahr>/<Akte>
        return ordner.parent.parent.name

    def akten_suchen(self, suchbegriff: str = "") -> list[Akte]:
        self._index = self._baum()
        begriff = suchbegriff.strip().lower()
        treffer: list[Akte] = []
        for ordner in self._index.values():
            akte = self._akte_aus_ordner(self._anwalt_von(ordner), ordner)
            heu = " ".join([akte.aktenzeichen, akte.bezeichnung, akte.sachbearbeiter, akte.status]).lower()
            if not begriff or begriff in heu:
                treffer.append(akte)
        return sorted(treffer, key=lambda a: a.aktenzeichen)

    def akte(self, akte_id: str) -> Akte:
        ordner = self._ordner(akte_id)
        return self._akte_aus_ordner(self._anwalt_von(ordner), ordner)

    # ── Dokumente ────────────────────────────────────────────────────────────

    def _dateien(self, ordner: Path) -> list[Path]:
        """Alle lesbaren Dokumente der Akte, auch aus Unterordnern – ohne Vermerke."""
        gefunden: list[Path] = []
        for pfad in sorted(ordner.rglob("*"), key=lambda p: str(p).casefold()):
            if not pfad.is_file() or pfad.name.startswith("."):
                continue
            if VERMERK_ORDNER in pfad.relative_to(ordner).parts:
                continue  # eigene Vermerke sind kein Aktenmaterial für die Analyse
            if pfad.suffix.lower() in DOKUMENT_ENDUNGEN:
                gefunden.append(pfad)
        return gefunden

    def dokumente(self, akte_id: str) -> list[Dokument]:
        ordner = self._ordner(akte_id)
        ergebnis: list[Dokument] = []
        for pfad in self._dateien(ordner):
            rel = pfad.relative_to(ordner)
            # Der Unterordner stand bis zum 12.10.2026 in "kategorie". Er
            # gehoert in "ordner": Dort erwartet ihn das Dokumentfenster, und
            # "kategorie" bleibt fuer das frei, was ein Schriftstueck IST.
            unterordner = str(rel.parent).replace("\\", "/") if str(rel.parent) != "." else ""
            try:
                stat = pfad.stat()
                datum = date.fromtimestamp(stat.st_mtime)
                groesse = stat.st_size
            except OSError:
                datum, groesse = None, None
            ergebnis.append(Dokument(
                id=rel.as_posix(), akte_id=akte_id, titel=pfad.stem, dateiname=rel.as_posix(),
                mime_typ=MIME_NACH_ENDUNG.get(pfad.suffix.lower(), "application/octet-stream"),
                datum=datum, ordner=unterordner, groesse_bytes=groesse,
            ))
        return ergebnis

    def dokument_laden(self, akte_id: str, dokument_id: str) -> tuple[Dokument, bytes]:
        ordner = self._ordner(akte_id)
        ziel = self._sichere_datei(ordner, dokument_id)
        for dokument in self.dokumente(akte_id):
            if dokument.id == dokument_id:
                return dokument, ziel.read_bytes()
        raise DokumentNichtGefunden(f"Dokument {dokument_id} nicht in Akte {akte_id}.")

    @staticmethod
    def _sichere_datei(ordner: Path, dokument_id: str) -> Path:
        """Löst die Dokumentkennung auf – und nur innerhalb des Aktenordners."""
        teile = [t for t in dokument_id.replace("\\", "/").split("/") if t]
        if not teile or any(t in ("..", ".") for t in teile):
            raise DokumentNichtGefunden("Ungültige Dokumentkennung.")
        ziel = ordner.joinpath(*teile)
        try:
            if ordner.resolve() not in ziel.resolve().parents:
                raise DokumentNichtGefunden("Das Dokument liegt nicht in der Akte.")
        except OSError as e:
            raise DokumentNichtGefunden("Das Dokument ist nicht erreichbar.") from e
        if not ziel.is_file():
            raise DokumentNichtGefunden("Das Dokument ist nicht vorhanden.")
        return ziel

    # ── Beteiligte und Fristen ───────────────────────────────────────────────
    #
    # Der Ordner-Export trägt keine strukturierten Beteiligten oder Fristen; sie
    # stünden in jur|nodes selbst. Bis zur API-Anbindung bleiben sie leer – die
    # Analyse arbeitet dann allein aus dem Dokumenttext.

    def beteiligte(self, akte_id: str) -> list[Beteiligter]:
        self._ordner(akte_id)  # prüft, dass es die Akte gibt
        return []

    def fristen(self, akte_id: str) -> list[Frist]:
        self._ordner(akte_id)
        return []

    # ── Schreiben – nur mit Freigabe ─────────────────────────────────────────

    def vermerk_schreiben(self, akte_id: str, titel: str, text: str, freigabe: Freigabe) -> str:
        self._freigabestelle.pruefen(freigabe, akte_id, text)
        ordner = self._ordner(akte_id)
        zeit = datetime.now(timezone.utc)
        kennung = f"VM-{zeit.strftime('%Y%m%d-%H%M%S')}-{freigabe.entwurf_id[:8]}"
        if self._schreibbar:
            ziel = ordner / VERMERK_ORDNER
            ziel.mkdir(exist_ok=True)
            sicherer_titel = re.sub(r"[^A-Za-z0-9ÄÖÜäöüß_-]+", "_", titel)[:60]
            (ziel / f"{kennung}_{sicherer_titel}.md").write_text(
                f"# {titel}\n\nFreigegeben von {freigabe.nutzer_id} am {zeit.isoformat()}\n\n{text}\n",
                encoding="utf-8")
        return kennung

    # ── Das Aktengedächtnis in der Akte ─────────────────────────────────────

    def gedaechtnis_lesen(self, akte_id: str) -> bytes | None:
        return gedaechtnisdatei.lesen(self._ordner(akte_id))

    def gedaechtnis_ablegen(self, akte_id: str, rohdaten: bytes) -> None:
        gedaechtnisdatei.ablegen(self._ordner(akte_id), rohdaten, self._schreibbar)

    def inhalte_vergessen(self, akte_id: str | None = None,
                          dokument_id: str | None = None) -> None:
        """Nichts zu tun: Dieser Adapter puffert keinen Akteninhalt.

        Steht hier ausdruecklich und nicht als fehlende Methode - sonst waere
        beim naechsten Adapter nicht zu erkennen, ob der Puffer vergessen
        wurde oder keiner da ist (Befund N10).
        """

    def gedaechtnis_loeschen(self, akte_id: str) -> None:
        gedaechtnisdatei.loeschen(self._ordner(akte_id), self._schreibbar)
