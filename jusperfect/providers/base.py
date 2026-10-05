from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol


class ProviderFehler(RuntimeError):
    """Ein Fehler, dessen Text der Kanzlei angezeigt werden darf."""


class GuardrailEingriff(ProviderFehler):
    """Die Bedrock-Guardrail hat Frage oder Antwort blockiert."""


@dataclass(frozen=True)
class Nutzung:
    eingabe_tokens: int = 0
    ausgabe_tokens: int = 0
    cache_lese_tokens: int = 0
    cache_schreib_tokens: int = 0


@dataclass(frozen=True)
class ProviderAntwort:
    text: str
    nutzung: Nutzung
    modell: str
    stop_grund: str = "end_turn"


class LLMProvider(Protocol):
    """Genau zwei Textteile gehen hinaus: das Material (Passagen) und die Aufgabe.

    Die Trennung ist Absicht: Das Material wird zwischengespeichert (mehrere
    Fragen zur selben Akte), die Aufgabe wird von der Guardrail geprüft.
    """

    modell_id: str

    def fragen(self, system: str, material: str, aufgabe: str, *, max_tokens: int = 8000,
               modell_id: str | None = None) -> ProviderAntwort: ...

    def fragen_stream(self, system: str, material: str, aufgabe: str, *, max_tokens: int = 8000,
                      modell_id: str | None = None) -> Iterator[str | ProviderAntwort]:
        """Wie ``fragen``, aber stückweise: erst Textstücke, zuletzt die
        vollständige ``ProviderAntwort`` mit der Nutzung."""
        ...
