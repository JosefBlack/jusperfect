"""Welche Berechtigung AWS vermisst – und sonst nichts.

**Das Problem, das diese Datei löst.** AWS schreibt bei einer fehlenden
Berechtigung einen Satz der Form

    User: arn:aws:iam::…:user/x is not authorized to perform:
    bedrock:ApplyGuardrail on resource: …

Darin steht die einzige Angabe, die weiterhilft: der Name der Handlung. Das
Programm reicht den Wortlaut von AWS aber bewusst **nicht** durch – in einer
Ablehnung steht mitunter ein Stück der Anfrage, und das ist hier Aktentext.

So blieb am 02.10.2026 nur „Die Zugriffsrichtlinie erlaubt diesen Aufruf
nicht", und damit beginnt dieselbe Suche wie am 01.10. beim Modell: Es kommen
ein halbes Dutzend Handlungen in Frage, und geraten wird reihum.

**Warum der Name der Handlung gefahrlos hinausgeht.** Er stammt aus einem
festen Wortschatz von AWS: ein Dienstkürzel, ein Doppelpunkt, ein Wort in
Binnenmajuskel. Er kann keinen Aktentext tragen, weil er keinen Platz dafür
hat – das Muster unten lässt nichts anderes durch, und die Dienstkürzel sind
einzeln aufgezählt. Alles übrige aus der Meldung bleibt drinnen.

Das ist der Unterschied zwischen „den Wortlaut durchreichen" und „eine
einzelne, geprüfte Angabe herauslösen". Das erste ist ein Datenleck, das
zweite ist die Auskunft, die der Anwender braucht.
"""

from __future__ import annotations

import re
from typing import Any

#: Die Dienste, deren Handlungen das Programm überhaupt aufruft.
#:
#: Eine Liste und kein ``\w+``: Ein Muster, das jedes Kürzel durchlässt, lässt
#: auch durch, was wie ein Kürzel aussieht. Was hier nicht steht, geht nicht
#: hinaus.
DIENSTE = ("bedrock", "textract", "s3", "kms", "sts")

_MUSTER = re.compile(
    r"not authorized to perform:?\s*((?:" + "|".join(DIENSTE) + r"):[A-Za-z]{2,48})",
    re.IGNORECASE,
)


def handlung(fehler: Exception) -> str:
    """Der Name der vermissten Handlung, oder „" wenn keiner dasteht.

    Zum Beispiel ``bedrock:ApplyGuardrail``. Nie mehr als das.
    """
    antwort: Any = getattr(fehler, "response", None)
    if not isinstance(antwort, dict):
        return ""
    satz = str(antwort.get("Error", {}).get("Message", ""))
    treffer = _MUSTER.search(satz)
    if not treffer:
        return ""
    gefunden = treffer.group(1)
    dienst, _, was = gefunden.partition(":")
    # Zweiter Riegel, unabhängig vom Muster: Das Kürzel muss in der Liste
    # stehen, und der Rest darf nur Buchstaben sein. Ein Muster allein ist
    # eine Behauptung; zwei voneinander unabhängige Prüfungen sind eine.
    if dienst.lower() not in DIENSTE or not was.isalpha():
        return ""
    return f"{dienst.lower()}:{was}"


def mit_handlung(satz: str, fehler: Exception) -> str:
    """Den eigenen Satz um die vermisste Handlung ergänzen, falls sie dasteht."""
    name = handlung(fehler)
    if not name:
        return satz
    return f"{satz} Es fehlt: {name}."
