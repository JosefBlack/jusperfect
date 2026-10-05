"""Sitzungsspeicher: lokal im Arbeitsspeicher oder in AWS (DynamoDB und S3)."""

from jusperfect.speicher.base import SitzungsSpeicher, SpeicherFehler

__all__ = ["SitzungsSpeicher", "SpeicherFehler"]
