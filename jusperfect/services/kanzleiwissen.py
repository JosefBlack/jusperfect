"""Kanzleiwissen aus einer Bedrock Knowledge Base – getrennt von Mandatsakten.

Phase 2 des Konzepts. Die Knowledge Base enthält ausschließlich freigegebene,
lizenzrechtlich unbedenkliche Inhalte: eigene Muster, Checklisten,
veröffentlichte Gerichtsentscheidungen. Keine Mandatsakten. Treffer werden
als Passagen mit dem Präfix ``KW`` mitgegeben, damit das Modell sie belegen
kann wie Aktenpassagen – und die Kanzlei sieht, was aus dem Wissen und was
aus der Akte stammt.
"""

from __future__ import annotations

from typing import Any

from jusperfect.domain.models import Passage


class Kanzleiwissen:
    def __init__(self, kb_id: str, region: str, anzahl: int = 4, client: Any | None = None) -> None:
        if client is None:
            import boto3

            client = boto3.client("bedrock-agent-runtime", region_name=region)
        self._client = client
        self._kb_id = kb_id
        self._anzahl = anzahl

    def suchen(self, frage: str) -> list[Passage]:
        try:
            antwort = self._client.retrieve(
                knowledgeBaseId=self._kb_id,
                retrievalQuery={"text": frage},
                retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": self._anzahl}},
            )
        except Exception:
            # Kanzleiwissen ist Zugabe: Ohne es geht die Frage trotzdem an die Akte.
            return []
        passagen: list[Passage] = []
        for nr, treffer in enumerate(antwort.get("retrievalResults", []), start=1):
            text = (treffer.get("content") or {}).get("text", "")
            if not text:
                continue
            ort = (treffer.get("location") or {})
            uri = (ort.get("s3Location") or {}).get("uri") or ort.get("type", "Kanzleiwissen")
            passagen.append(Passage(kennung=f"KW-{nr}", dokument_id="kanzleiwissen",
                                    dokument_titel=f"Kanzleiwissen: {uri.rsplit('/', 1)[-1]}", seite=0, text=text))
        return passagen
