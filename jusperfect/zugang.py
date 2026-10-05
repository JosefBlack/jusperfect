"""Die AWS-Zugangsdaten hinterlegen – ohne die AWS CLI.

Die CLI schreibt nichts weiter als zwei Textdateien in ``%USERPROFILE%\\.aws``.
boto3 liest sie von dort, ganz gleich, wer sie geschrieben hat. In der Kanzlei
ließ sich das Installationspaket der CLI nicht herunterladen – und damit stand
die Einrichtung an einem Schritt still, der eigentlich keiner ist.

Dieses Modul fragt die beiden Werte ab und legt die Dateien an. Vorhandene
Profile bleiben erhalten; geschrieben wird nur der Abschnitt, um den es geht.

Der geheime Schlüssel wird verdeckt eingegeben und nirgends ausgegeben – auch
nicht zur Bestätigung. Was im schwarzen Fenster steht, liest der Nächste mit.
"""

from __future__ import annotations

import configparser
import contextlib
import getpass
import os
import stat
import sys
from pathlib import Path

TRENNER = "=" * 60

# Die Region, in der jusperfect arbeitet. Steht hier noch einmal, damit die
# Datei auch dann stimmt, wenn jemand sie ohne die Startdatei nutzt.
STANDARDREGION = "eu-central-1"


def _sagen(zeichen: str, text: str) -> None:
    print(f"  {zeichen}  {text}")


def _maskiert(kennung: str) -> str:
    """Nur so viel, dass man zwei Schlüssel unterscheiden kann."""
    return f"{kennung[:4]}…{kennung[-4:]}" if len(kennung) > 8 else "…"


#: So lang sind die beiden Werte bei AWS. Eine andere Länge heisst fast immer:
#: beim Kopieren abgeschnitten oder ein Zeichen zu viel erwischt.
LAENGE_KENNUNG = 20
LAENGE_GEHEIM = 40


def _form_pruefen(was: str, wert: str, laenge: int,
                  vorsatz: tuple[str, ...] = ()) -> list[str]:
    """Was an einem eingegebenen Wert auffällt – als Hinweis, nicht als Abbruch.

    Aus der Kanzlei: „Ich habe den Schlüssel von dem anderen Rechner genommen."
    Das ist zulässig – ein Schlüssel gehört zu einem Benutzer, nicht zu einem
    Rechner. Beim Übertragen von Hand geht aber leicht ein Zeichen verloren, und
    AWS meldet das später nur als „kennt diese Kennung nicht". Zwei Zeichen zu
    wenig fallen niemandem auf; eine Zahl daneben schon.

    Kein Abbruch: AWS darf seine Formen ändern, und wer weiss, dass sein Wert
    richtig ist, soll ihn eintragen dürfen. Der Zugangstest entscheidet.
    """
    hinweise = []
    if vorsatz and not wert.startswith(vorsatz):
        hinweise.append(f"Ungewöhnliche Form – {was} beginnt sonst mit {vorsatz[0]}.")
    if len(wert) != laenge:
        hinweise.append(
            f"{was} ist {len(wert)} Zeichen lang, bei AWS sind es {laenge}. "
            + ("Beim Kopieren abgeschnitten?" if len(wert) < laenge
               else "Ein Zeichen zu viel erwischt, etwa ein Leerzeichen?"))
    if wert != wert.strip() or any(z.isspace() for z in wert):
        hinweise.append("Es steckt ein Leerzeichen darin – das gehört nicht dazu.")
    return hinweise


def _ordner(pfad: Path) -> None:
    pfad.mkdir(parents=True, exist_ok=True)
    # Unter Windows wirkungslos, unter macOS/Linux nicht: Der Ordner geht
    # niemanden sonst etwas an.
    with contextlib.suppress(OSError):
        pfad.chmod(stat.S_IRWXU)


def _schreiben(datei: Path, abschnitt: str, werte: dict[str, str]) -> None:
    """Einen Abschnitt setzen, alle anderen unangetastet lassen."""
    konf = configparser.ConfigParser()
    if datei.is_file():
        konf.read(datei, encoding="utf-8")
    if not konf.has_section(abschnitt):
        konf.add_section(abschnitt)
    for schluessel, wert in werte.items():
        konf.set(abschnitt, schluessel, wert)
    with datei.open("w", encoding="utf-8") as offen:
        konf.write(offen)
    with contextlib.suppress(OSError):
        datei.chmod(stat.S_IRUSR | stat.S_IWUSR)


def main(argv: list[str] | None = None) -> int:
    print(TRENNER)
    print("  jusperfect – AWS-Zugangsdaten hinterlegen")
    print(TRENNER)
    print()
    print("  Sie brauchen die beiden Werte aus der AWS-Konsole:")
    print("  IAM → Benutzer → Sicherheitsanmeldeinformationen → Zugriffsschlüssel.")
    print()
    print("  Die AWS CLI wird dafür NICHT gebraucht. Diese Datei schreibt")
    print("  dasselbe, was 'aws configure' geschrieben hätte.")
    print()

    aws = Path(os.path.expanduser("~")) / ".aws"
    zugangsdatei = aws / "credentials"
    konfigdatei = aws / "config"

    profil = (os.environ.get("AWS_PROFILE") or "default").strip() or "default"

    # Schon etwas da? Dann nicht stillschweigend überschreiben.
    vorhanden = configparser.ConfigParser()
    if zugangsdatei.is_file():
        vorhanden.read(zugangsdatei, encoding="utf-8")
    if vorhanden.has_section(profil):
        alt = vorhanden.get(profil, "aws_access_key_id", fallback="")
        _sagen("!", f"Für „{profil}“ ist bereits ein Schlüssel hinterlegt: {_maskiert(alt)}")
        antwort = input("     Überschreiben? (j/n): ").strip().lower()
        if antwort != "j":
            print("\n  Abgebrochen. Es wurde nichts geändert.\n")
            return 1
        print()

    kennung = input("  Access Key ID (beginnt mit AKIA…): ").strip()
    if not kennung:
        _sagen("✗", "Ohne Access Key ID geht es nicht.")
        return 2
    for hinweis in _form_pruefen("Die Access Key ID", kennung, LAENGE_KENNUNG,
                                 ("AKIA", "ASIA")):
        _sagen("!", hinweis)

    # Verdeckt: Was im Fenster steht, liest der Nächste mit, und die
    # Eingabeaufforderung merkt sich Zeilen über Sitzungen hinweg.
    geheim = getpass.getpass("  Secret Access Key (Eingabe bleibt unsichtbar): ").strip()
    if not geheim:
        _sagen("✗", "Ohne den geheimen Schlüssel geht es nicht.")
        _sagen(" ", "Er wird in AWS genau einmal angezeigt. Ist er weg, in IAM")
        _sagen(" ", "einen neuen erstellen – das ist der normale Weg, kein Notfall.")
        return 2
    if geheim == kennung:
        _sagen("✗", "Beide Werte sind gleich – da ist etwas verwechselt worden.")
        return 2
    if geheim.startswith(("AKIA", "ASIA")):
        _sagen("✗", "Das sieht nach einer zweiten Access Key ID aus, nicht nach dem "
                    "geheimen Schlüssel.")
        return 2
    for hinweis in _form_pruefen("Der geheime Schlüssel", geheim, LAENGE_GEHEIM):
        _sagen("!", hinweis)

    region = input(f"  Region [{STANDARDREGION}]: ").strip() or STANDARDREGION
    if not region.startswith("eu-"):
        _sagen("!", f"„{region}“ liegt nicht in Europa. jusperfect weist solche Aufrufe ab.")

    try:
        _ordner(aws)
        _schreiben(zugangsdatei, profil,
                   {"aws_access_key_id": kennung, "aws_secret_access_key": geheim})
        # Die Region gehört in config, nicht in credentials - so hält es die
        # CLI auch, und Werkzeuge, die nur eine der beiden Dateien lesen,
        # finden dann das Erwartete.
        _schreiben(konfigdatei, profil if profil == "default" else f"profile {profil}",
                   {"region": region})
    except OSError as fehler:
        _sagen("✗", f"Die Dateien ließen sich nicht schreiben ({type(fehler).__name__}).")
        _sagen(" ", f"Betroffen: {zugangsdatei}")
        return 2

    print()
    _sagen("✓", f"Hinterlegt für „{profil}“: {_maskiert(kennung)}, Region {region}")
    _sagen(" ", f"Abgelegt in {aws}")
    _sagen(" ", "Der geheime Schlüssel steht nur dort – nicht im Programmordner.")
    print()
    print(TRENNER)
    print("  Weiter mit dem Zugangstest:")
    print("    .venv\\Scripts\\python.exe -m jusperfect.awstest")
    print(TRENNER)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
