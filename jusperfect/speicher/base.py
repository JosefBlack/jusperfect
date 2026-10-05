"""Was jusperfect sich merken muss – und wie kurz.

Lambda ist zustandslos, also braucht eine Aktensitzung einen Speicher
außerhalb des Prozesses. Er hält vier Dinge, alle mit Ablauf:

* die Sitzung (wer, welche Akte, was ist geladen),
* die extrahierten Dokumenttexte der Sitzung,
* Entwürfe bis zur Freigabe oder zum Verwerfen,
* die Nutzung je Monat (Kosten, ohne Inhalte).

Nichts davon ist eine Parallelakte: Texte leben Minuten, Entwürfe Tage, und
beides verschwindet mit dem Schließen der Sitzung oder durch den Ablauf.
"""

from __future__ import annotations

from typing import Protocol

from jusperfect.domain.models import Entwurf, Nutzungseintrag, Sitzung


class SpeicherFehler(RuntimeError):
    pass


class SitzungsSpeicher(Protocol):
    # Sitzung
    def sitzung_ablegen(self, sitzung: Sitzung) -> None: ...
    def sitzung_lesen(self, sitzung_id: str) -> Sitzung | None: ...
    def sitzung_loeschen(self, sitzung_id: str) -> None:
        """Löscht Sitzung und alle ihre Texte."""
        ...

    # Texte je Sitzung und Dokument
    def text_ablegen(self, sitzung_id: str, dokument_id: str, text: str) -> None: ...
    def text_lesen(self, sitzung_id: str, dokument_id: str) -> str | None: ...
    def text_loeschen(self, sitzung_id: str, dokument_id: str) -> None:
        """Entfernt genau einen Dokumenttext aus der Sitzung."""
        ...

    # Entwürfe
    def entwurf_ablegen(self, entwurf: Entwurf) -> None: ...
    def entwurf_lesen(self, entwurf_id: str) -> Entwurf | None: ...
    def entwurf_loeschen(self, entwurf_id: str) -> None: ...

    # Was zu einer Akte gehört. Nur der Abschlussworkflow fragt danach: Beim
    # bestätigten Abschluss muss der Arbeitsbereich vollständig verschwinden,
    # und dafür muss er vollständig auffindbar sein.
    def sitzungen_der_akte(self, akte_id: str) -> list[str]:
        """Kennungen aller noch vorhandenen Sitzungen dieser Akte."""
        ...
    def entwuerfe_der_akte(self, akte_id: str) -> list[str]:
        """Kennungen aller noch vorhandenen Entwürfe dieser Akte."""
        ...

    # Nutzung
    def nutzung_verbuchen(self, eintrag: Nutzungseintrag) -> float:
        """Schreibt den Eintrag und gibt die Monatssumme in EUR zurück."""
        ...
    def nutzung_monat(self, monat: str) -> float:
        """Summe für ``JJJJ-MM`` in EUR."""
        ...
    def nachweis_lesen(self, limit: int = 25) -> list[Nutzungseintrag]:
        """Die jüngsten Verarbeitungsnachweise, neueste zuerst – ohne Inhalte."""
        ...
