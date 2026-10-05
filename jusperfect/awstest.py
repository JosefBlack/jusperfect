"""Zugangstest für AWS Bedrock: ``python -m jusperfect.awstest``.

Ohne diesen Test merkt man einen falsch eingerichteten Zugang erst mitten in
der Arbeit – die Oberfläche zeigt dann nur eine Fehlermeldung, die nicht sagt,
woran es liegt. Der Test geht dieselben Schritte in der Reihenfolge durch, in
der sie scheitern können, und sagt bei jedem, was zu tun ist.

Er schickt genau eine sehr kurze Frage an das Modell (wenige Token, Bruchteil
eines Cents) und **keinen Aktentext**.
"""

from __future__ import annotations

import os
import sys

from jusperfect.config import Einstellungen, KonfigurationsFehler
from jusperfect.zugang import _maskiert
from jusperfect import modellprotokoll
from jusperfect.modellprotokoll import pruefen
from jusperfect.services.selbsttest import zugangsfehler

TRENNER = "─" * 70


def _sagen(zeichen: str, text: str) -> None:
    print(f"  {zeichen}  {text}")


def _anbietertext(fehler) -> str:
    """Der Satz, den AWS selbst geschickt hat.

    Der Fehlercode allein ist zu grob: „AccessDeniedException" steht sowohl
    fuer ein nicht freigeschaltetes Modell als auch fuer eine fehlende
    Berechtigung als auch fuer ein ausdrueckliches Verbot in der Richtlinie.
    AWS schreibt den Unterschied in die Antwort hinein - und genau der Satz
    fehlte hier, weshalb in der Kanzlei geraten statt gelesen wurde.

    Der Text beschreibt die Anfrage, nicht die Akte; er wird nur oertlich
    angezeigt.
    """
    text = ""
    antwort = getattr(fehler, "response", None)
    if isinstance(antwort, dict):
        text = str(antwort.get("Error", {}).get("Message", "")).strip()
    return text[:400]


def _umbrechen(text: str, breite: int = 66) -> list[str]:
    """Lange Hinweise in Zeilen, die in ein schwarzes Fenster passen."""
    import textwrap

    return textwrap.wrap(text, breite) or [""]


def _befehl_zeigen(name: str, wert: str) -> None:
    """Eine Zeile fuer die Eingabeaufforderung, eine fuer PowerShell.

    Wer aus dem Explorer heraus ein Fenster oeffnet, landet je nach
    Windows-Fassung im einen oder im anderen. Die "set"-Zeile ist in
    PowerShell nicht bloss wirkungslos, sondern ein Fehler - und dann steht
    man vor einer Meldung, die mit der eigentlichen Sache nichts zu tun hat.
    """
    _sagen(" ", f"   Eingabeaufforderung:  set {name}={wert}")
    _sagen(" ", f'   PowerShell:           $env:{name}="{wert}"')


def main(argv: list[str] | None = None) -> int:
    print(TRENNER)
    print("  jusperfect – Zugangstest für AWS Bedrock")
    print(TRENNER)

    try:
        e = Einstellungen.aus_umgebung()
    except KonfigurationsFehler as fehler:
        _sagen("✗", f"Die Einstellungen sind widersprüchlich: {fehler}")
        return 2

    print(f"\nRegion:  {e.aws_region}")
    print(f"Modell:  {e.modell_id}\n")

    # 1. Ist das SDK überhaupt da?
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
    except ImportError:
        _sagen("✗", "Der AWS-Baustein boto3 fehlt.")
        _sagen(" ", "Beheben: START-AWS.bat einmal ausführen – es installiert ihn.")
        return 2

    # 2. Zugangsdaten. Der häufigste Fall, und der mit der klarsten Abhilfe.
    sitzung = boto3.Session(region_name=e.aws_region)
    zugang = sitzung.get_credentials()
    if zugang is None:
        _sagen("✗", "Es sind keine AWS-Zugangsdaten hinterlegt.")
        _sagen(" ", "Beheben: ZUGANG-EINTRAGEN.bat im Programmordner starten.")
        _sagen(" ", "Es fragt die beiden Werte ab und legt sie in")
        _sagen(" ", "%USERPROFILE%\\.aws\\credentials ab - die AWS CLI wird nicht gebraucht.")
        return 2
    # Welche Kennung wird gleich verschickt? Ohne diese Zeile las die Kanzlei
    # "AWS kennt diese Kennung nicht" und hatte nichts, womit sie in der
    # AWS-Konsole vergleichen konnte. Die Access Key ID ist kein Geheimnis -
    # AWS zeigt sie selbst an -; verkuerzt steht sie hier trotzdem, denn diese
    # Ausgabe wird weitergegeben.
    _sagen("✓", f"Zugangsdaten gefunden: {_maskiert(getattr(zugang, 'access_key', '') or '')}")
    _sagen(" ", f"   Hinterlegt in {os.path.expanduser('~')}\\.aws\\credentials"
                f" unter „{os.environ.get('AWS_PROFILE') or 'default'}“.")

    # 3. Wer sind wir? Sagt zugleich, ob die Daten überhaupt gültig sind.
    try:
        wer = sitzung.client("sts").get_caller_identity()
        _sagen("✓", f"Angemeldet als: {wer.get('Arn', '(unbekannt)')}")
    except NoCredentialsError:
        _sagen("✗", "Die Zugangsdaten sind unvollständig.")
        return 2
    except ClientError as fehler:
        # Welcher der beiden Werte klemmt, steht im Fehlercode. Vorher stand
        # hier nur "Schluessel pruefen" - und die Kanzlei prueft dann beide.
        code = fehler.response.get("Error", {}).get("Code", "")
        satz, hinweis = zugangsfehler(fehler)
        _sagen("✗", f"Die Zugangsdaten werden abgewiesen ({code}).")
        _sagen(" ", satz)
        for zeile in _umbrechen(hinweis):
            _sagen(" ", zeile)
        return 2
    except Exception as fehler:  # Netz, Proxy, DNS
        _sagen("✗", f"AWS ist nicht erreichbar ({type(fehler).__name__}).")
        _sagen(" ", "Beheben: Internetverbindung und Firewall prüfen.")
        return 2

    if not e.aws_region.startswith("eu-"):
        _sagen("✗", f"Region {e.aws_region} ist nicht in Europa.")
        return 2
    _sagen("✓", "Region liegt in Europa.")

    # 4. Der eigentliche Aufruf. Kurz, ohne Aktentext.
    print(f"\n  Ein Testaufruf an {e.modell_id} …\n")
    try:
        antwort = sitzung.client("bedrock-runtime").converse(
            modelId=e.modell_id,
            system=[{"text": "Antworte mit genau einem Wort."}],
            messages=[{"role": "user", "content": [{"text": "Sage: bereit"}]}],
            inferenceConfig={"maxTokens": 10, "temperature": 0},
        )
    except ClientError as fehler:
        code = fehler.response.get("Error", {}).get("Code", "")
        _sagen("✗", f"Der Aufruf wurde abgewiesen ({code}).")
        wortlaut = _anbietertext(fehler)
        if wortlaut:
            # Zuerst der Wortlaut, dann unsere Vermutungen. Wer "explicit
            # deny" liest, muss nicht drei Ursachen durchgehen.
            _sagen(" ", f"AWS schreibt dazu: {wortlaut}")
            _sagen(" ", "")
        if "not available for this account" in wortlaut:
            # Der eindeutige Fall - und der einzige, bei dem an der eigenen
            # Einrichtung nichts zu suchen ist. In der Kanzlei haben wir ihn
            # dreimal fuer etwas anderes gehalten, weil der Satz fehlte.
            _sagen(" ", "Das heißt: An Ihrer Einrichtung liegt es NICHT.")
            _sagen(" ", "Zugangsdaten, Richtlinie und Region stimmen; AWS hat diesem")
            _sagen(" ", "Konto nur dieses eine Modell nicht zugeteilt. Das ist bei")
            _sagen(" ", "neuen Konten üblich und betrifft vor allem die starken Modelle.")
            _sagen(" ", "")
            _sagen(" ", "Welche Modelle Ihr Konto wirklich aufrufen darf, zeigt")
            _sagen(" ", "MODELLE-ANZEIGEN.bat - es probiert sie der Reihe nach an.")
            _sagen(" ", "Eines davon eintragen:")
            _befehl_zeigen("JUSPERFECT_MODELL_ID", "eu.anthropic.claude-…")
        elif code in ("AccessDeniedException", "AccessDenied"):
            _sagen(" ", "Drei Ursachen kommen in Frage, in dieser Reihenfolge zu prüfen:")
            _sagen(" ", "a) Das Modell ist im Konto nicht freigeschaltet.")
            _sagen(" ", "   AWS-Konsole → Bedrock → Modellzugriff. Steht dort, die Seite")
            _sagen(" ", "   sei abgeschafft („has been retired\"), ist nichts mehr")
            _sagen(" ", "   freizuschalten – dann scheidet diese Ursache aus.")
            # Der Vorsatz "eu." setzt die Konfiguration in europaeischen
            # Regionen selbst; einen Hinweis darauf braucht es hier also nicht
            # mehr. Uebrig bleibt, was am Profilaufruf sonst scheitern kann.
            if e.modell_id.startswith("eu."):
                _sagen(" ", "b) Die Kontonummer in der Richtlinie: Sie kommt ZWEIMAL vor")
                _sagen(" ", "   (bei „inference-profile\"). Bleibt eine als AWS-KONTONUMMER")
                _sagen(" ", "   stehen, wird der Profilaufruf abgewiesen.")
            else:
                _sagen(" ", f"b) Die Kennung „{e.modell_id}\" ist keine gewöhnliche")
                _sagen(" ", "   Anthropic-Kennung. Deckt die Richtlinie sie ab?")
            _sagen(" ", "c) Die Richtlinie hängt nicht am Benutzer (IAM → Benutzer →")
            _sagen(" ", "   Berechtigungen). Siehe infra/IAM.md.")
            _sagen(" ", "")
            _sagen(" ", "Was Ihr Konto tatsächlich anbietet, zeigt MODELLE-ANZEIGEN.bat -")
            _sagen(" ", "es fragt AWS und kostet nichts.")
        elif code in ("ValidationException", "ResourceNotFoundException"):
            _sagen(" ", "Die Modellkennung passt nicht zu dieser Region.")
            _sagen(" ", "In Europa ist meist das Inferenzprofil nötig. Versuchen Sie:")
            _befehl_zeigen("JUSPERFECT_MODELL_ID", f"eu.{e.modell_id}")
            _sagen(" ", "und starten Sie den Test erneut.")
        elif code == "ThrottlingException":
            _sagen(" ", "Zu viele Aufrufe. Kurz warten und erneut versuchen.")
        return 1
    except Exception as fehler:
        _sagen("✗", f"Der Aufruf ist fehlgeschlagen ({type(fehler).__name__}).")
        return 1

    text = "".join(
        teil.get("text", "") for teil in antwort["output"]["message"]["content"]
    ).strip()
    nutzung = antwort.get("usage", {})
    _sagen("✓", f"Das Modell hat geantwortet: „{text}“")
    _sagen(" ", f"Verbrauch: {nutzung.get('inputTokens', 0)} + "
                f"{nutzung.get('outputTokens', 0)} Token (Bruchteil eines Cents).")

    # 5. Der Frage-Weg strömt die Antwort und braucht dafür eine *eigene*
    #    Berechtigung. Wer nur InvokeModel hat, käme bis hierher und
    #    scheiterte erst bei der ersten Frage - mit einer Meldung, die
    #    nicht sagt, dass es an der Berechtigung liegt.
    try:
        strom = sitzung.client("bedrock-runtime").converse_stream(
            modelId=e.modell_id,
            system=[{"text": "Antworte mit genau einem Wort."}],
            messages=[{"role": "user", "content": [{"text": "Sage: bereit"}]}],
            inferenceConfig={"maxTokens": 10, "temperature": 0},
        )
        for _ in strom["stream"]:
            pass
    except ClientError as fehler:
        code = fehler.response.get("Error", {}).get("Code", "")
        _sagen("✗", f"Die strömende Antwort wurde abgewiesen ({code}).")
        _sagen(" ", "Der einfache Aufruf ging durch, dieser nicht - es fehlt also")
        _sagen(" ", "die Berechtigung bedrock:InvokeModelWithResponseStream.")
        _sagen(" ", "Beheben: In der Richtlinie muss sie neben bedrock:InvokeModel")
        _sagen(" ", "stehen (siehe infra/iam-nur-claude.json).")
        return 1
    except Exception as fehler:
        _sagen("✗", f"Die strömende Antwort ist fehlgeschlagen ({type(fehler).__name__}).")
        return 1
    _sagen("✓", "Auch die strömende Antwort läuft – das ist der Weg jeder Frage.")

    # 6. Schreibt AWS die Aufrufe mit? Der Zugang kann tadellos sein und der
    #    Aktentext trotzdem in einer Protokollablage landen. Hier steht die
    #    Frage vor der Arbeit, nicht nach der ersten echten Akte.
    befund = pruefen(e.aws_region)
    if befund.zustand == modellprotokoll.AN:
        _sagen("✗", befund.satz)
        for teil in befund.einzelheiten:
            _sagen(" ", f"   {teil}")
        _sagen(" ", "")
        _sagen(" ", "Der Prompt ist der Aktentext. Damit läge das Mandantengeheimnis")
        _sagen(" ", "ein zweites Mal neben der Akte - an einer Stelle, die die Löschung")
        _sagen(" ", "beim Aktenabschluss nicht erfasst. jusperfect startet so nicht.")
        _sagen(" ", "")
        _sagen(" ", "Beheben: AWS-Konsole → Bedrock → Einstellungen →")
        _sagen(" ", "Modellaufrufprotokollierung abschalten. Dann diesen Test erneut.")
        return 1
    if befund.zustand == modellprotokoll.UNBEKANNT:
        _sagen("!", befund.satz)
        for teil in befund.einzelheiten:
            _sagen(" ", f"   {teil}")
        _sagen(" ", "Mit den erfundenen Testakten läuft das Programm trotzdem.")
        _sagen(" ", "Vor der ersten echten Akte muss diese Frage beantwortet sein.")
    else:
        _sagen("✓", befund.satz)

    print(f"\n{TRENNER}")
    print("  Der Zugang steht. Sie können START-AWS.bat benutzen.")
    print(f"{TRENNER}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
