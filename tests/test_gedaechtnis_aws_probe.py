"""Die Probe für die AWS-Ablage - an einem nachgestellten S3 gemessen.

Der Selbsttest sagt, dass ein Bucket hinterlegt ist. Ob er das Ablegen annimmt,
sagt nur eine Probe, die denselben Weg geht wie der Betrieb - mit demselben
``ServerSideEncryption`` und demselben Schlüssel.

Diese Prüfungen messen die Probe selbst: Sagt sie das Richtige, wenn es geht,
und das Richtige, wenn es nicht geht? Ein Messgerät, das falsch misst, ist
schlimmer als keines.
"""

from __future__ import annotations

import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkzeug"))

import gedaechtnis_aws_probe as probe  # noqa: E402

REGION = "eu-central-1"
BUCKET = "kanzlei-jusperfect-gedaechtnis"


def _umgebung(monkeypatch, **zusatz: str) -> None:
    werte = {
        "JUSPERFECT_BETRIEBSART": "lokal",
        "JUSPERFECT_ANBIETER": "demo",
        "JUSPERFECT_AWS_REGION": REGION,
        "JUSPERFECT_GEDAECHTNIS": "aws",
        "JUSPERFECT_GEDAECHTNIS_BUCKET": BUCKET,
        "JUSPERFECT_KMS_SCHLUESSEL_ID": "alias/jusperfect-kanzlei",
        "JUSPERFECT_JURNODES_ADAPTER": "fixture",
        "JUSPERFECT_FIXTURE_PFAD": str(WURZEL / "testdaten" / "akten"),
        "JUSPERFECT_NUTZER_DATEI": str(WURZEL / "testdaten" / "nutzer.json"),
        "AWS_ACCESS_KEY_ID": "probe",
        "AWS_SECRET_ACCESS_KEY": "probe",
        "AWS_DEFAULT_REGION": REGION,
    }
    werte.update(zusatz)
    for name in ("JUSPERFECT_MODELL_ID", "JUSPERFECT_MODELL_GEDAECHTNIS",
                 "JUSPERFECT_GUARDRAIL_ID"):
        monkeypatch.delenv(name, raising=False)
    for name, wert in werte.items():
        monkeypatch.setenv(name, wert)


@mock_aws
def test_bei_vorhandenem_bucket_geht_ablegen_lesen_und_loeschen(monkeypatch, capsys):
    _umgebung(monkeypatch)
    boto3.client("s3", region_name=REGION).create_bucket(
        Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})

    assert probe.main() == 0
    ausgabe = capsys.readouterr().out
    assert "Abgelegt" in ausgabe
    assert "Zeichen für Zeichen gleich" in ausgabe
    assert "Die Ablage in AWS arbeitet" in ausgabe


@mock_aws
def test_ohne_bucket_sagt_sie_woran_es_liegt(monkeypatch, capsys):
    """Nicht "AccessDenied", sondern: Name vergleichen, Tippfehler genügt."""
    _umgebung(monkeypatch)
    assert probe.main() == 1
    ausgabe = capsys.readouterr().out
    assert "abgewiesen" in ausgabe
    assert "nichts geschrieben worden" in ausgabe


def test_ohne_aws_ablage_erklaert_sie_sich_statt_zu_scheitern(monkeypatch, capsys):
    """Wer sie aus Neugier startet, soll nicht auf einen Fehler stossen."""
    _umgebung(monkeypatch, JUSPERFECT_GEDAECHTNIS="aus",
              JUSPERFECT_GEDAECHTNIS_BUCKET="", JUSPERFECT_KMS_SCHLUESSEL_ID="")
    assert probe.main() == 2
    ausgabe = capsys.readouterr().out
    assert "gilt nur für die Ablage in AWS" in ausgabe
    assert "AWS-EINRICHTEN.md" in ausgabe


@pytest.mark.parametrize("meldung, erwartet", [
    ("NoSuchBucket: The specified bucket does not exist", "Tippfehler"),
    ("PermanentRedirect: The bucket is in this region", "anderen Region"),
    ("KMSAccessDeniedException", "kms:Encrypt"),
    ("AccessDenied", "s3:PutObject"),
    ("Unable to locate credentials", "ZUGANG-EINTRAGEN.bat"),
])
def test_jede_lage_bekommt_einen_eigenen_satz(meldung, erwartet):
    """„AccessDenied" allein sagt nicht, ob Bucket, Region oder Recht fehlt."""
    assert erwartet in probe._rat(Exception(meldung))


# ---------------------------------------------------------------------------
# Was in der Startdatei als Platzhalter steht, muss das Programm abweisen
#
# Die Lehre vom 25.09.2026: Im Windows-Konto stand woertlich "IHRE-KENNUNG"
# aus unserer eigenen Anleitung. Die Pruefung "ist etwas eingetragen?" war
# zufrieden, und erst der Modellaufruf scheiterte. Ein Platzhalter ist
# schlimmer als eine Luecke - er sieht wie ein Wert aus.
# ---------------------------------------------------------------------------


def test_in_der_startdatei_steht_kein_platzhalter_mehr() -> None:
    """Seit dem 01.10.2026 ist das Aktengedächtnis eingeschaltet.

    Vorher standen hier zwei auskommentierte Zeilen mit Platzhaltern, und
    diese Prüfung hielt fest, dass jeder davon vom Programm abgewiesen wird –
    sonst hätte, wer das REM wegnimmt und das Eintragen vergisst, eine Meldung
    von S3 bekommen statt einer, die weiterhilft.

    Jetzt stehen dort die wirklichen Werte, und die Prüfung dreht sich um: Was
    dort steht, darf **kein** Platzhalter sein. Die Schutzwirkung bleibt, sie
    greift nur an der anderen Seite – dass ein Platzhalter abgewiesen WIRD,
    hält die Prüfung darunter fest.

    „Ein Platzhalter ist schlimmer als eine Lücke" – Lehre vom 25.09.2026, als
    im Windows-Konto wörtlich IHRE-KENNUNG stand.
    """
    import re

    from jusperfect.config import PLATZHALTER_ABLAGE

    text = (WURZEL / "START-JURNODES.bat").read_text(encoding="ascii")
    gefunden = 0
    for name in ("JUSPERFECT_GEDAECHTNIS_BUCKET", "JUSPERFECT_KMS_SCHLUESSEL_ID"):
        for treffer in re.finditer(rf"^set {name}=(\S+)", text, re.M):
            wert = treffer.group(1).strip()
            gefunden += 1
            assert wert.lower() not in PLATZHALTER_ABLAGE, (
                f"{wert!r} ist ein Platzhalter, steht aber als wirklicher Wert in "
                "START-JURNODES.bat. Das Programm bricht damit beim ersten Ablegen ab.")
    assert gefunden == 2, (
        f"Erwartet wurden zwei gesetzte Zeilen, gefunden {gefunden}. "
        "Ist das Aktengedächtnis wieder abgeschaltet, gehört diese Prüfung "
        "zurückgedreht – nicht gelöscht.")


def test_ein_platzhalter_bricht_den_start_mit_einem_ganzen_satz_ab(monkeypatch) -> None:
    from jusperfect.config import Einstellungen, KonfigurationsFehler

    _umgebung(monkeypatch, JUSPERFECT_GEDAECHTNIS_BUCKET="HIER-DEN-BUCKETNAMEN")
    with pytest.raises(KonfigurationsFehler) as fehler:
        Einstellungen.aus_umgebung()
    assert "Platzhalter aus der Startdatei" in str(fehler.value)
    assert "AWS-EINRICHTEN.md" in str(fehler.value)


def test_die_anleitung_zeigt_keinen_wert_den_das_programm_abweist() -> None:
    """Umgekehrte Richtung: Was in der Anleitung als Beispiel steht, muss durchgehen.

    Sonst schreibt der Naechste genau das ab, was nicht geht - und bekommt eine
    Meldung, die auf die Anleitung zeigt, aus der es stammt.
    """
    import re

    from jusperfect.config import PLATZHALTER_ABLAGE

    text = (WURZEL / "AWS-EINRICHTEN.md").read_text(encoding="utf-8")
    for name in ("JUSPERFECT_GEDAECHTNIS_BUCKET", "JUSPERFECT_KMS_SCHLUESSEL_ID"):
        for treffer in re.finditer(rf"{name}=(\S+)", text):
            wert = treffer.group(1).strip().strip('`"')
            assert wert.lower() not in PLATZHALTER_ABLAGE, (
                f"{wert!r} steht als Beispiel in AWS-EINRICHTEN.md und wird vom "
                "Programm abgewiesen. Eines von beiden ist falsch.")


def test_die_startdatei_setzt_die_werte_selbst() -> None:
    """Sonst liest die Probe das Windows-Konto - und dort steht "aus".

    Der Fehler war gebaut und ausgeliefert: GEDAECHTNIS-AWS-PRUEFEN.bat rief
    nur das Python auf. Die Einstellungen kommen aber aus der Umgebung, und in
    der Kanzlei steht JUSPERFECT_GEDAECHTNIS nicht auf "aws" - die Probe waere
    mit "gilt nur fuer die Ablage in AWS" abgebrochen, nach vier Klicks in der
    AWS-Konsole.

    Dieselbe Form wie fuenfmal am 23./24.09.2026: Eine Probe, die anders fragt
    als der Betrieb - hier sogar anders als sie selbst verlangt.
    """
    text = (WURZEL / "GEDAECHTNIS-AWS-PRUEFEN.bat").read_text(encoding="ascii")
    assert "set JUSPERFECT_GEDAECHTNIS=aws" in text
    assert "set /p BUCKET=" in text
    assert "set /p KMSID=" in text
    assert 'set "JUSPERFECT_GEDAECHTNIS_BUCKET=%BUCKET%"' in text
    assert 'set "JUSPERFECT_KMS_SCHLUESSEL_ID=%KMSID%"' in text


def test_ohne_angabe_wird_nichts_geprueft_und_das_steht_da() -> None:
    """Eine leere Eingabe darf nicht in einen AWS-Fehler laufen."""
    text = (WURZEL / "GEDAECHTNIS-AWS-PRUEFEN.bat").read_text(encoding="ascii")
    assert "if not defined BUCKET goto keineangabe" in text
    assert "if not defined KMSID goto keineangabe" in text
    assert "es wurde nichts geprueft" in text


def test_die_probe_hinterlegt_nichts_dauerhaft() -> None:
    """Sie soll pruefen, nicht einrichten - kein setx, keine Datei."""
    text = (WURZEL / "GEDAECHTNIS-AWS-PRUEFEN.bat").read_text(encoding="ascii")
    assert "setx" not in text.lower()
    assert "setlocal" in text, "Ohne setlocal ueberdauern die Werte das Fenster."


# ---------------------------------------------------------------------------
# Die Form der Schluessel-ID
#
# Am 28.09.2026 wurden in der Kanzlei 64 Hexzeichen ohne Bindestriche
# eingegeben - offenbar eine Pruefsumme des Schluesselmaterials. AWS antwortete
# mit einem ClientError, und der sah aus wie ein fehlendes Recht.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("wert", [
    "1a2b3c4d-5e6f-7890-abcd-ef1234567890",
    "arn:aws:kms:eu-central-1:579138738703:key/1a2b3c4d-5e6f-7890-abcd-ef1234567890",
    "alias/jusperfect-kanzlei",
])
def test_die_drei_brauchbaren_formen_gehen_durch(wert):
    assert probe.schluessel_geprueft(wert) == ""


@pytest.mark.parametrize("wert", [
    "c907e6e7ece6796748dd6a0bfbe293b94cde376c4bab5bbb9f7c92ef5b63ae4f",
    "jusperfect-kanzlei",
    "",
])
def test_eine_falsche_form_faellt_vorher_auf(wert):
    """Bevor ein Aufruf hinausgeht - und mit der richtigen Form im Satz."""
    satz = probe.schluessel_geprueft(wert)
    assert satz
    if wert:
        assert "Form" in satz or "kein Schlüssel" in satz


@mock_aws
def test_bei_falscher_form_wird_nichts_versucht(monkeypatch, capsys):
    _umgebung(monkeypatch, JUSPERFECT_KMS_SCHLUESSEL_ID="c907e6e7ece6796748dd6a0bf")
    assert probe.main() == 1
    ausgabe = capsys.readouterr().out
    assert "es wurde nichts versucht" in ausgabe
    assert "Ablegen" not in ausgabe


def test_der_wortlaut_von_aws_geht_nicht_verloren():
    """Der Speicher nennt nur den Typ - die Probe muss tiefer sehen."""
    from jusperfect.gedaechtnis.base import GedaechtnisFehler

    class _Client(Exception):
        def __init__(self) -> None:
            super().__init__("An error occurred (KMS.NotFoundException)")
            self.response = {"Error": {"Code": "KMS.NotFoundException",
                                       "Message": "Invalid keyId"}}

    try:
        try:
            raise _Client()
        except Exception as innen:
            raise GedaechtnisFehler("konnte nicht gespeichert werden (ClientError).") from innen
    except Exception as aussen:
        assert "KMS.NotFoundException" in probe.ursache(aussen)
        assert "Schlüssel wurde nicht gefunden" in probe._rat(aussen)
