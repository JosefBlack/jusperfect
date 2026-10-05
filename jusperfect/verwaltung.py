"""Verwaltung der Berechtigungen in AWS: ``python -m jusperfect.verwaltung``.

Beispiele:
  python -m jusperfect.verwaltung eintragen <cognito-sub> "Name" VU-2026-0042 MV-2026-0007
  python -m jusperfect.verwaltung eintragen <cognito-sub> "Name" "*"
  python -m jusperfect.verwaltung entfernen <cognito-sub>
"""

from __future__ import annotations

import sys

from jusperfect.config import Einstellungen
from jusperfect.domain.models import Nutzer
from jusperfect.security.berechtigungen import DynamoDbBerechtigungen


def main(argv: list[str]) -> int:
    e = Einstellungen.aus_umgebung()
    if not e.dynamodb_tabelle:
        print("JUSPERFECT_DYNAMODB_TABELLE fehlt.", file=sys.stderr)
        return 2
    b = DynamoDbBerechtigungen(e.dynamodb_tabelle, e.aws_region, e.gruppe_alle_akten)
    if len(argv) >= 4 and argv[0] == "eintragen":
        b.eintragen(Nutzer(id=argv[1], name=argv[2], akten=argv[3:]))
        print(f"Berechtigung für {argv[1]} eingetragen: {argv[3:]}")
        return 0
    if len(argv) == 2 and argv[0] == "entfernen":
        b.entfernen(argv[1])
        print(f"Berechtigung für {argv[1]} entfernt.")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
