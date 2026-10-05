"""Wer darf welche Akte sehen.

Die Anmeldung sagt, wer da ist; dieses Modul sagt, was die Person darf.
Zwei Quellen:

* ``DateiBerechtigungen`` – eine JSON-Datei, lokal und für Tests.
* ``DynamoDbBerechtigungen`` – ein Eintrag je Nutzer in jusperfect-Tabelle,
  gepflegt über ``python -m jusperfect.verwaltung``. Mitglieder der
  Cognito-Gruppe ``alle-akten`` (einstellbar) sehen alle Akten – gedacht für
  die Anwälte; Mitarbeiter bekommen eine Aktenliste.

Ohne Treffer keine Sitzung – und damit kein Dokument, kein Text, kein Aufruf.
Für Phase 2 ist vorgesehen, die Berechtigung direkt aus jur|nodes zu
beziehen, sobald die API je Nutzer auskunftsfähig ist.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from jusperfect.domain.models import Akte, Nutzer
from jusperfect.security.identitaet import Identitaet


class UnbekannterNutzer(PermissionError):
    pass


class ZugriffVerweigert(PermissionError):
    pass


class Berechtigungen(Protocol):
    def nutzer(self, identitaet: Identitaet) -> Nutzer: ...

    def pruefen(self, identitaet: Identitaet, akte_id: str) -> Nutzer: ...

    def filtern(self, identitaet: Identitaet, akten: list[Akte]) -> list[Akte]: ...


class _Basis:
    gruppe_alle_akten: str = "alle-akten"

    def _laden(self, nutzer_id: str) -> Nutzer | None:  # pragma: no cover – abstrakt
        raise NotImplementedError

    def nutzer(self, identitaet: Identitaet) -> Nutzer:
        nutzer = self._laden(identitaet.nutzer_id)
        if nutzer is None:
            if self.gruppe_alle_akten in identitaet.gruppen:
                return Nutzer(id=identitaet.nutzer_id, name=identitaet.anzeigename or identitaet.nutzer_id, akten=["*"])
            raise UnbekannterNutzer("Für diese Anmeldung ist keine Berechtigung hinterlegt.")
        if self.gruppe_alle_akten in identitaet.gruppen and "*" not in nutzer.akten:
            nutzer = nutzer.model_copy(update={"akten": ["*"]})
        return nutzer

    def pruefen(self, identitaet: Identitaet, akte_id: str) -> Nutzer:
        nutzer = self.nutzer(identitaet)
        if not nutzer.darf_akte(akte_id):
            raise ZugriffVerweigert("Für diese Akte besteht keine Berechtigung.")
        return nutzer

    def filtern(self, identitaet: Identitaet, akten: list[Akte]) -> list[Akte]:
        nutzer = self.nutzer(identitaet)
        return [a for a in akten if nutzer.darf_akte(a.id)]


class DateiBerechtigungen(_Basis):
    def __init__(self, nutzer: list[Nutzer], gruppe_alle_akten: str = "alle-akten") -> None:
        self._nutzer = {n.id: n for n in nutzer}
        self.gruppe_alle_akten = gruppe_alle_akten

    @classmethod
    def aus_datei(cls, pfad: Path, gruppe_alle_akten: str = "alle-akten") -> "DateiBerechtigungen":
        daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
        return cls([Nutzer.model_validate(n) for n in daten.get("nutzer", [])], gruppe_alle_akten)

    def _laden(self, nutzer_id: str) -> Nutzer | None:
        return self._nutzer.get(nutzer_id)

    def auflisten(self) -> list[Nutzer]:
        """Alle hinterlegten Nutzer - fuer die Auswahl im oertlichen Betrieb.

        Es gibt sie bewusst nur hier. Im AWS-Betrieb stellt Cognito die
        Identitaet fest; eine Liste der Kanzleiangehoerigen waere dort eine
        Auskunft, die vor der Anmeldung niemandem zusteht. Oertlich steht
        dieselbe Liste ohnehin als Datei auf demselben Rechner, und es gibt
        kein Kennwort, das sie schuetzen wuerde.
        """
        return sorted(self._nutzer.values(), key=lambda n: n.name.lower())


class DynamoDbBerechtigungen(_Basis):
    """Eintrag ``NUTZER#<sub>`` / ``META`` mit ``name`` und ``akten`` (Liste)."""

    def __init__(self, tabelle: str, region: str, gruppe_alle_akten: str = "alle-akten",
                 dynamodb: Any | None = None) -> None:
        if dynamodb is None:
            import boto3

            dynamodb = boto3.resource("dynamodb", region_name=region)
        self._tabelle = dynamodb.Table(tabelle)
        self.gruppe_alle_akten = gruppe_alle_akten

    def _laden(self, nutzer_id: str) -> Nutzer | None:
        eintrag = self._tabelle.get_item(Key={"pk": f"NUTZER#{nutzer_id}", "sk": "META"}).get("Item")
        if not eintrag:
            return None
        return Nutzer(id=nutzer_id, name=str(eintrag.get("name", nutzer_id)), akten=[str(a) for a in eintrag.get("akten", [])])

    def eintragen(self, nutzer: Nutzer) -> None:
        self._tabelle.put_item(Item={"pk": f"NUTZER#{nutzer.id}", "sk": "META", "name": nutzer.name, "akten": nutzer.akten})

    def entfernen(self, nutzer_id: str) -> None:
        self._tabelle.delete_item(Key={"pk": f"NUTZER#{nutzer_id}", "sk": "META"})
