"""Baut den konfigurierten Anbieter."""

from __future__ import annotations

from jusperfect.config import Einstellungen
from jusperfect.providers.base import LLMProvider


def provider_erstellen(einstellungen: Einstellungen) -> LLMProvider:
    if einstellungen.anbieter == "bedrock":
        from jusperfect.providers.bedrock import BedrockProvider

        return BedrockProvider(
            modell_id=einstellungen.modell_id,
            region=einstellungen.aws_region,
            guardrail_id=einstellungen.guardrail_id,
            guardrail_version=einstellungen.guardrail_version,
            prompt_cache=einstellungen.prompt_cache,
        )
    from jusperfect.providers.demo import DemoProvider

    return DemoProvider()
