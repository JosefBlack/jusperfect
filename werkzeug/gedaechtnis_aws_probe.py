"""Nimmt der S3-Bucket der Kanzlei das Aktengedächtnis an?

**Warum es diese Probe gibt.** Der Selbsttest sagt, dass ein Bucket und ein
Schlüssel hinterlegt sind. Ob der Bucket existiert, in Frankfurt liegt, das
Schreiben zulässt und den Kanzleischlüssel annimmt, sagt er nicht - er kann es
nicht sagen, denn er liest nur die Einstellungen.

Ohne diese Probe fiele das Fehlen erst dann auf, wenn eine Akte geschlossen
wird und das Gedächtnis sich nicht sichern lässt. Das ist der teuerste
Zeitpunkt: Die Arbeit ist getan und wäre verloren.

**Sie geht denselben Weg wie der Betrieb.** Nicht ``head_bucket``, nicht
``get_bucket_encryption`` - sondern ``AwsGedaechtnisSpeicher`` selbst, mit
demselben ``ServerSideEncryption`` und demselben Schlüssel. Fünfmal an einem Tag
hat dieses Projekt gelernt: Eine Probe, die anders fragt als der Betrieb, prüft
etwas anderes als den Betrieb.

**Sie schreibt.** Ein Aktengedächtnis zu einer erfundenen Akte mit einem Satz
darin, kein Mandantengut. Der Objektname enthält keine Aktenkennung, sondern
deren Prüfsumme - wie im Betrieb. Danach wird es zurückgelesen und verglichen,
und zuletzt wieder entfernt.

Das Aufräumen ist selbst eine Auskunft: Das Löschen eines Aktengedächtnisses
ist ein vorgesehener Weg (``DELETE /api/akten/{id}/gedaechtnis``, berechtigungs-
geprüft), und ob der Bucket es zulässt, gehört zu den Dingen, die man vor dem
Einschalten wissen will. Misslingt es, bleibt ein Objekt von wenigen hundert
Byte liegen, und die Probe sagt es - statt zu schweigen.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from jusperfect.config import Einstellungen, KonfigurationsFehler  # noqa: E402
from jusperfect.domain.models import Aktengedaechtnis  # noqa: E402
from jusperfect.gedaechtnis.aws import AwsGedaechtnisSpeicher  # noqa: E402

BREITE = 78
#: Die erfundene Akte, unter der die Probe ablegt. Ihre Pruefsumme steht im
#: Objektnamen; ein Aktenzeichen aus dem Bestand kommt dort nie vor.
PROBEAKTE = "PROBE-GEDAECHTNIS-jusperfect"


def _sagen(zeichen: str, text: str) -> None:
    print(f"  {zeichen}  {text}")


#: Die Formen, in denen S3 einen KMS-Schluessel annimmt.
#:
#: Die Kennung selbst (fuenf Gruppen, 36 Zeichen), die ARN oder ein Alias.
#: Alles andere ist ein Kopierfehler - und am 28.09.2026 war es einer: In der
#: Kanzlei wurden 64 Hexzeichen ohne Bindestriche eingegeben, offenbar eine
#: Pruefsumme des Schluesselmaterials. AWS antwortete darauf mit einem
#: ClientError, und der sah aus wie ein fehlendes Recht.
#:
#: Eine falsche Form faellt hier auf, bevor ein Aufruf hinausgeht. Das ist die
#: Lehre vom 25.09.2026, nur an einer anderen Stelle: Ein Wert, der wie ein
#: Wert aussieht, aber keiner ist, kostet mehr als eine Luecke.
_KENNUNG = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                      re.IGNORECASE)


def schluessel_geprueft(wert: str) -> str:
    """Leer, wenn die Form stimmt - sonst der Satz, der weiterhilft."""
    wert = wert.strip()
    if not wert:
        return "Es ist kein Schlüssel angegeben."
    if wert.startswith("arn:aws:kms:") or wert.startswith("alias/"):
        return ""
    if _KENNUNG.match(wert):
        return ""
    return (f"„{wert[:24]}…“ hat nicht die Form einer Schlüssel-ID.\n"
            "      Erwartet wird eines von dreien:\n"
            "        1a2b3c4d-5e6f-7890-abcd-ef1234567890   (fünf Gruppen, 36 Zeichen)\n"
            "        arn:aws:kms:eu-central-1:…:key/…       (die vollständige ARN)\n"
            "        alias/jusperfect-kanzlei                (der Alias)\n"
            "      Sie steht in KMS auf der Seite des Schlüssels am Ende der ARN,\n"
            "      hinter „key/“. 64 Zeichen ohne Bindestriche sind nicht die\n"
            "      Kennung, sondern eine Prüfsumme.")


def ursache(fehler: BaseException) -> str:
    """Den Wortlaut von AWS aus der Kette der Ausnahmen holen.

    ``AwsGedaechtnisSpeicher`` verpackt jeden Fehler in einen eigenen Satz und
    nennt nur den Typ: "konnte nicht gespeichert werden (ClientError)". Fuer
    den Betrieb ist das richtig - dort hilft der AWS-Code niemandem. Fuer eine
    Probe ist es unbrauchbar: Am 28.09.2026 stand in der Kanzlei genau dieser
    Satz, und weder der Anwender noch die Probe selbst konnten daraus
    schliessen, ob der Bucket, die Region, der Schluessel oder ein Recht fehlt.

    Die Ursache ist nicht verloren, sie steht nur eine Stufe tiefer: ``raise
    ... from e`` haengt sie als ``__cause__`` an. Hier wird die Kette
    abgelaufen und der unterste Satz genommen - dazu, wenn es ein Fehler von
    boto3 ist, der Code aus seiner Antwort.
    """
    teile: list[str] = []
    gesehen: set[int] = set()
    aktuell: BaseException | None = fehler
    while aktuell is not None and id(aktuell) not in gesehen:
        gesehen.add(id(aktuell))
        antwort = getattr(aktuell, "response", None)
        if isinstance(antwort, dict):
            angabe = antwort.get("Error", {})
            code = str(angabe.get("Code", "")).strip()
            satz = str(angabe.get("Message", "")).strip()
            if code or satz:
                teile.append(" ".join(x for x in (code + ":" if code else "", satz) if x))
        else:
            text = str(aktuell).strip()
            if text:
                teile.append(f"{type(aktuell).__name__}: {text}")
        aktuell = aktuell.__cause__ or aktuell.__context__
    return "\n      ".join(teile) if teile else f"{type(fehler).__name__} ohne Wortlaut."


def _rat(fehler: Exception) -> str:
    """Aus der Meldung von AWS einen Satz machen, der weiterhilft.

    Die Rohmeldung nennt den Code, nicht die Abhilfe. Wer "AccessDenied" liest,
    weiss nicht, ob der Bucket fehlt, die Region falsch ist oder ein Recht.
    """
    text = ursache(fehler)
    if "NoSuchBucket" in text:
        return ("Diesen Bucket gibt es nicht. Name in der Startdatei mit dem in der "
                "S3-Konsole vergleichen - schon ein Tippfehler genügt.")
    if "PermanentRedirect" in text or "IllegalLocationConstraint" in text:
        return ("Der Bucket liegt in einer anderen Region. jusperfect arbeitet in "
                "Frankfurt (eu-central-1); ein Bucket lässt sich nicht verschieben, "
                "er muss dort neu angelegt werden.")
    if ("KMS.NotFoundException" in text or "InvalidArgument" in text
            or "not found" in text.lower()):
        return ("Der Schlüssel wurde nicht gefunden. Häufigste Ursache: eine falsche "
                "Schlüssel-ID. Richtig ist die Form "
                "1a2b3c4d-5e6f-7890-abcd-ef1234567890 - fünf Gruppen mit Bindestrichen, "
                "36 Zeichen. Sie steht in KMS am Ende der ARN hinter 'key/'.")
    if "KMS" in text or "kms" in text:
        return ("Der Kanzleischlüssel wurde abgewiesen. Gebraucht werden die Rechte "
                "kms:Encrypt, kms:Decrypt und kms:GenerateDataKey auf diesen Schlüssel - "
                "und der Schlüssel muss in derselben Region liegen wie der Bucket.")
    if "AccessDenied" in text or "AccessDeniedException" in text:
        return ("Das Ablegen ist nicht erlaubt. Gebraucht werden s3:PutObject und "
                "s3:GetObject auf diesen Bucket. Steht das Recht in der "
                "Zugriffsrichtlinie? Siehe AWS-EINRICHTEN.md.")
    if "NoCredentialsError" in text or "Unable to locate credentials" in text:
        return "Es sind keine AWS-Zugangsdaten hinterlegt. Abhilfe: ZUGANG-EINTRAGEN.bat."
    return "Der Wortlaut von AWS steht darüber. Bitte so weitergeben, wie er dasteht."


def main() -> int:
    print("=" * BREITE)
    print("  jusperfect – nimmt der S3-Bucket das Aktengedächtnis an?")
    print("=" * BREITE)
    print()

    try:
        e = Einstellungen.aus_umgebung()
    except KonfigurationsFehler as fehler:
        _sagen("✗", f"Die Einstellungen sind nicht in Ordnung: {fehler}")
        return 1

    if e.gedaechtnis != "aws":
        _sagen("!", f"Das Aktengedächtnis steht auf „{e.gedaechtnis}“, nicht auf „aws“.")
        print()
        print("  Diese Probe gilt nur für die Ablage in AWS. Zum Prüfen genügt es,")
        print("  die drei Zeilen in der Startdatei zu setzen; eingeschaltet werden")
        print("  muss es dafür nicht dauerhaft.")
        print()
        print("  Anleitung: AWS-EINRICHTEN.md, Abschnitt „Das Aktengedächtnis in AWS“.")
        return 2

    beanstandung = schluessel_geprueft(e.kms_schluessel_id or "")
    if beanstandung:
        _sagen("✗", "Der Schlüssel ist nicht brauchbar – es wurde nichts versucht.")
        print()
        print(f"      {beanstandung}")
        return 1

    print(f"  Region:      {e.aws_region}")
    print(f"  Bucket:      {e.gedaechtnis_bucket}")
    print(f"  Schlüssel:   {e.kms_schluessel_id}")
    print()
    print("  Diese Probe SCHREIBT – ein Gedächtnis zu einer erfundenen Akte mit")
    print("  einem Satz darin. Kein Akteninhalt, kein Mandantenname.")
    print()

    try:
        speicher = AwsGedaechtnisSpeicher(e.gedaechtnis_bucket, e.aws_region,
                                          e.kms_schluessel_id or "")
    except Exception as fehler:
        _sagen("✗", f"Der Speicher liess sich nicht einrichten: {fehler}")
        print()
        _sagen(" ", _rat(fehler))
        return 1

    satz = (f"Probe von GEDAECHTNIS-AWS-PRUEFEN.bat, "
            f"{datetime.now(timezone.utc):%d.%m.%Y %H:%M} UTC. Kein Akteninhalt.")
    gedaechtnis = Aktengedaechtnis(akte_id=PROBEAKTE, aktenzeichen="PROBE",
                                   bezeichnung="Probe der AWS-Ablage",
                                   lebenssachverhalt=satz)

    print("  [1/3] Ablegen …")
    try:
        speicher.ablegen(gedaechtnis)
    except Exception as fehler:
        _sagen("✗", "Das Ablegen wurde abgewiesen.")
        print()
        print(f"      {ursache(fehler)}")
        print()
        _sagen(" ", _rat(fehler))
        print()
        print("  Es ist nichts geschrieben worden.")
        return 1
    _sagen("✓", "Abgelegt, verschlüsselt mit dem Kanzleischlüssel.")

    print("  [2/3] Zurücklesen …")
    try:
        zurueck = speicher.lesen(PROBEAKTE)
    except Exception as fehler:
        _sagen("✗", "Das Zurücklesen wurde abgewiesen.")
        print()
        print(f"      {ursache(fehler)}")
        print()
        _sagen(" ", _rat(fehler))
        print()
        print("  Geschrieben wurde also, gelesen nicht. Das ist die gefährlichere")
        print("  Hälfte: Ein Gedächtnis, das sich ablegen aber nicht wiederholen")
        print("  lässt, sieht im Betrieb wie Erfolg aus.")
        return 1

    if zurueck is None or zurueck.lebenssachverhalt != satz:
        _sagen("✗", "Zurückgelesen wurde etwas anderes als abgelegt.")
        return 1
    _sagen("✓", "Zurückgelesen und Zeichen für Zeichen gleich.")

    print("  [3/3] Wieder entfernen …")
    aufgeraeumt = True
    try:
        speicher.loeschen(PROBEAKTE)
    except Exception as fehler:
        aufgeraeumt = False
        _sagen("!", "Das Entfernen wurde abgewiesen.")
        print()
        print(f"      {ursache(fehler)}")
    else:
        _sagen("✓", "Entfernt. Der Bucket lässt auch das Löschen zu.")

    print()
    print("=" * BREITE)
    _sagen("✓", "Die Ablage in AWS arbeitet. Das Aktengedächtnis kann eingeschaltet werden.")
    print("=" * BREITE)
    if not aufgeraeumt:
        print()
        print("  Ablegen und Lesen gehen, Löschen nicht. Für den Betrieb genügt das")
        print("  zunächst - aber der Löschweg des Programms")
        print("  (DELETE /api/akten/<Kennung>/gedaechtnis) wird dann ebenso abgewiesen.")
        print("  Gebraucht wird dafür s3:DeleteObject auf diesen Bucket.")
        print()
        print("  Liegen geblieben ist ein Objekt von wenigen hundert Byte unter")
        print("  akten/<Prüfsumme>/gedaechtnis.json. Wer es wegräumen will, tut das")
        print("  in der S3-Konsole.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
