"""Welche Claude-Modelle darf dieses Konto in dieser Region aufrufen?

Die AWS-Konsole baut die Seite mit den Freischaltungen regelmässig um; mal
heisst sie „Model access", mal steckt sie unter „Bedrock configurations", mal
zeigt der Modellkatalog etwas anderes an als der Zugriff hergibt. Wer dort
sucht, sucht je nach Woche woanders.

Das Konto selbst weiss es genau. Dieser Befehl fragt es und beantwortet die
zwei Fragen, an denen die Einrichtung haengt:

  1. Ist das Modell in dieser Region ueberhaupt vorhanden?
  2. Laesst es sich unmittelbar aufrufen, oder verlangt es das
     Inferenzprofil? Anthropic gibt neuere Modelle in Europa nur ueber ein
     Profil frei - der unmittelbare Aufruf wird dann abgewiesen, und zwar mit
     derselben Meldung wie eine fehlende Freischaltung.

Und die dritte, die uns am teuersten zu stehen kam: Der Katalog beantwortet
eine andere Frage als die gestellte. "In Frankfurt vorhanden" heisst nicht
"dieses Konto darf es". AWS teilt neuen Konten die starken Modelle nicht ohne
Weiteres zu und antwortet dann mit AccessDeniedException - derselben Meldung
wie bei einer fehlenden Berechtigung. In der Kanzlei haben wir das dreimal
fuer einen Einrichtungsfehler gehalten.

Der Befehl probiert die Modelle deshalb wirklich an: je ein Wort, Bruchteile
eines Cents insgesamt. Wer das nicht will, haengt --ohne-aufruf an; dann
bleibt es beim Katalog, mit dessen bekannter Schwaeche.
"""

from __future__ import annotations

import sys

from jusperfect.config import Einstellungen, KonfigurationsFehler

TRENNER = "=" * 70


def _sagen(zeichen: str, text: str) -> None:
    print(f"  {zeichen}  {text}")


def _befehl_zeigen(name: str, wert: str) -> None:
    """Beide Fensterarten - aus dem Explorer landet man oft in PowerShell."""
    _sagen(" ", f"   Eingabeaufforderung:  set {name}={wert}")
    _sagen(" ", f'   PowerShell:           $env:{name}="{wert}"')


def _anprobieren(region: str, kennung: str) -> tuple[bool, str]:
    """Ein Wort an das Modell schicken. Gibt (geht, Grund) zurueck."""
    import boto3
    from botocore.exceptions import ClientError
    try:
        boto3.client("bedrock-runtime", region_name=region).converse(
            modelId=kennung,
            messages=[{"role": "user", "content": [{"text": "hi"}]}],
            inferenceConfig={"maxTokens": 1, "temperature": 0},
        )
        return True, ""
    except ClientError as fehler:
        text = str(fehler.response.get("Error", {}).get("Message", ""))
        if "not available for this account" in text:
            return False, "diesem Konto nicht zugeteilt"
        code = fehler.response.get("Error", {}).get("Code", "")
        return False, f"{code}: {text[:90]}"
    except Exception as fehler:  # pragma: no cover - Netz
        return False, type(fehler).__name__


#: Der Filter hat gesperrt - kein Fehler, sondern eine Einstellung.
GESPERRT = "gesperrt"


def _gelaender_anprobieren(region: str, kennung: str, guardrail_id: str,
                           guardrail_version: str, text: str) -> tuple[bool, str]:
    """Einen Satz durch das Schutzgelaender schicken. Gibt (durch, Grund) zurueck.

    Warum das eigens geprueft werden muss: Die Voreinstellungen eines
    Bedrock-Guardrails sind fuer Anwendungen gedacht, in denen Gewalt,
    Sexuelles und Beleidigungen nichts zu suchen haben. In einer Kanzlei sind
    genau das die Faelle. Ein zu scharf eingestellter Filter faellt nicht
    dadurch auf, dass er etwas Falsches tut, sondern dadurch, dass eine
    gewoehnliche Frage zu einer gewoehnlichen Akte mit einer Sperrmeldung
    endet - und zwar zum ersten Mal vor einer echten Akte.

    Geschickt wird ein erfundener Satz in der Sprache einer Akte, ein Token
    Antwort. Kein Mandantengeheimnis, Bruchteile eines Cents.
    """
    import boto3
    from botocore.exceptions import ClientError
    try:
        antwort = boto3.client("bedrock-runtime", region_name=region).converse(
            modelId=kennung,
            # guardContent genau um den Satz - dieselbe Stelle wie im Betrieb
            # (siehe providers/bedrock.py), sonst prueft die Probe etwas anderes.
            messages=[{"role": "user",
                       "content": [{"guardContent": {"text": {"text": text}}}]}],
            guardrailConfig={"guardrailIdentifier": guardrail_id,
                             "guardrailVersion": guardrail_version},
            inferenceConfig={"maxTokens": 1, "temperature": 0},
        )
        if antwort.get("stopReason") == "guardrail_intervened":
            # Eigene Kennung, kein Satz: Der Aufrufer unterscheidet daran zwei
            # ganz verschiedene Faelle - "das Gelaender hat gesperrt" (ein
            # Filter ist zu scharf) und "es liess sich nicht fragen" (Recht,
            # Kennung, Netz). Der erste ist einzustellen, der zweite zu beheben.
            return False, GESPERRT
        return True, ""
    except ClientError as fehler:
        code = fehler.response.get("Error", {}).get("Code", "")
        satz = str(fehler.response.get("Error", {}).get("Message", ""))
        # Der Fall, auf den die Kanzlei vorbereitet ist: Manche Konten verlangen
        # fuer den Aufruf mit Geländer ein eigenes Recht. Vorher lief derselbe
        # Aufruf - daran erkennt man es, und nur daran.
        if "ApplyGuardrail" in satz or ("AccessDenied" in code and guardrail_id in satz):
            return False, ("der Zugriffsrichtlinie fehlt bedrock:ApplyGuardrail")
        if "guardrail" in satz.lower() and "not found" in satz.lower():
            return False, "diese Geländer-Kennung kennt AWS nicht"
        return False, f"{code}: {satz[:80]}"
    except Exception as fehler:  # pragma: no cover - Netz
        return False, type(fehler).__name__


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    anprobieren = "--ohne-aufruf" not in argv
    print(TRENNER)
    print("  jusperfect – welche Modelle darf dieses Konto?")
    print(TRENNER)

    try:
        e = Einstellungen.aus_umgebung()
    except KonfigurationsFehler as fehler:
        _sagen("✗", f"Die Einstellungen sind widersprüchlich: {fehler}")
        return 2

    print(f"\nRegion:     {e.aws_region}")
    print(f"Eingestellt: {e.modell_id}\n")

    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
    except ImportError:
        _sagen("✗", "Der AWS-Baustein boto3 fehlt. START-AWS.bat einmal ausführen.")
        return 2

    try:
        antwort = boto3.client("bedrock", region_name=e.aws_region).list_foundation_models(
            byProvider="anthropic"
        )
    except NoCredentialsError:
        _sagen("✗", "Es sind keine AWS-Zugangsdaten hinterlegt.")
        _sagen(" ", "Beheben: ZUGANG-EINTRAGEN.bat starten.")
        return 2
    except ClientError as fehler:
        code = fehler.response.get("Error", {}).get("Code", "")
        _sagen("✗", f"Die Abfrage wurde abgewiesen ({code}).")
        if code in ("AccessDeniedException", "AccessDenied"):
            _sagen(" ", "Der Richtlinie fehlt bedrock:ListFoundationModels.")
            _sagen(" ", "In infra/iam-nur-claude.json steht sie unter „ModelleAnsehen“.")
            _sagen(" ", "Hängt die Richtlinie wirklich am Benutzer? IAM → Benutzer →")
            _sagen(" ", "jusperfect-test → Berechtigungen.")
        return 2
    except Exception as fehler:  # pragma: no cover – Netz, DNS, Firewall
        _sagen("✗", f"AWS ist nicht erreichbar ({type(fehler).__name__}).")
        return 2

    modelle = antwort.get("modelSummaries", [])
    if not modelle:
        _sagen("✗", f"In {e.aws_region} ist kein Anthropic-Modell vorhanden.")
        _sagen(" ", "Steht die Region richtig? Für Frankfurt: eu-central-1.")
        return 1

    unmittelbar: list[str] = []
    nur_profil: list[str] = []
    for modell in modelle:
        kennung = modell.get("modelId", "")
        # Ausgemusterte Modelle nur verwirren.
        if modell.get("modelLifecycleStatus", {}).get("status") == "LEGACY":
            continue
        wege = modell.get("inferenceTypesSupported", [])
        if "ON_DEMAND" in wege:
            unmittelbar.append(kennung)
        elif "INFERENCE_PROFILE" in wege:
            nur_profil.append(kennung)

    if anprobieren:
        print("  Probiere jedes Modell mit einem Wort an "
              "(Bruchteile eines Cents insgesamt) …\n")
        brauchbar: list[str] = []
        for kennung in sorted(nur_profil) + sorted(unmittelbar):
            # Profilgebundene nur mit Vorsatz - anders sind sie nicht aufrufbar.
            versuch = f"eu.{kennung}" if kennung in nur_profil else kennung
            geht, grund = _anprobieren(e.aws_region, versuch)
            marke = "  ← eingestellt" if versuch == e.modell_id else ""
            if geht:
                brauchbar.append(versuch)
                print(f"     ✓  {versuch}{marke}")
            else:
                print(f"     ✗  {versuch}  – {grund}{marke}")
        print(f"\n{TRENNER}")
        if brauchbar:
            if e.modell_id in brauchbar:
                _sagen("✓", "Das eingestellte Modell funktioniert. Nichts zu tun.")
            else:
                _sagen("!", f"„{e.modell_id}“ ist nicht dabei. Nehmen Sie eines der Haken:")
                _befehl_zeigen("JUSPERFECT_MODELL_ID", brauchbar[0])
                _sagen(" ", "Dauerhaft: dieselbe Zeile in START-AWS.bat eintragen,")
                _sagen(" ", "unter „set JUSPERFECT_AWS_REGION=…“.")
        else:
            _sagen("✗", "Diesem Konto ist derzeit kein Claude-Modell zugeteilt.")
            _sagen(" ", "Das ist kein Einrichtungsfehler. Bei neuen Konten legt es")
            _sagen(" ", "sich oft nach der ersten Abrechnung; sonst hilft eine")
            _sagen(" ", "Anfrage bei AWS über den Link aus der Fehlermeldung.")
        print(TRENNER + "\n")
        return 0

    print("  Unmittelbar aufrufbar (Kennung so eintragen):")
    if unmittelbar:
        for kennung in sorted(unmittelbar):
            marke = "  ← eingestellt" if kennung == e.modell_id else ""
            print(f"     {kennung}{marke}")
    else:
        print("     – keines –")

    print("\n  Nur über das Inferenzprofil (Kennung mit „eu.“ davor):")
    if nur_profil:
        for kennung in sorted(nur_profil):
            profil = f"eu.{kennung}"
            marke = "  ← eingestellt" if profil == e.modell_id else ""
            print(f"     {profil}{marke}")
    else:
        print("     – keines –")

    print(f"\n{TRENNER}")
    kern = e.modell_id.removeprefix("eu.")
    mit_vorsatz = e.modell_id.startswith("eu.")
    if mit_vorsatz and (kern in nur_profil or kern in unmittelbar):
        _sagen("✓", "Die eingestellte Kennung steht in der Liste.")
        _sagen(" ", "Wird sie trotzdem abgewiesen, liegt es an der Richtlinie:")
        _sagen(" ", "IAM → Benutzer → Berechtigungen.")
    elif not mit_vorsatz and kern in unmittelbar:
        _sagen("✓", "Die eingestellte Kennung steht in der Liste.")
        _sagen(" ", "Wird sie trotzdem abgewiesen, liegt es an der Richtlinie:")
        _sagen(" ", "IAM → Benutzer → Berechtigungen.")
    else:
        _sagen("!", f"„{e.modell_id}“ steht in keiner der beiden Listen.")
        vorschlag = (sorted(unmittelbar) or [f"eu.{k}" for k in sorted(nur_profil)])
        if vorschlag:
            _sagen(" ", "Nehmen Sie eine Kennung von oben, etwa:")
            _sagen(" ", f"   Eingabeaufforderung:  set JUSPERFECT_MODELL_ID={vorschlag[0]}")
            _sagen(" ", f'   PowerShell:           $env:JUSPERFECT_MODELL_ID="{vorschlag[0]}"')
    print(TRENNER)
    print("\n  Diese Liste sagt, was es GIBT. Ob es freigeschaltet ist, zeigt erst")
    print("  der Aufruf:  .venv\\Scripts\\python.exe -m jusperfect.awstest\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
