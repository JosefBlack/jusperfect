"""Nimmt AWS die Texterkennung an?

**Warum es diese Probe gibt.** Der Selbsttest sagt, dass die Texterkennung
eingeschaltet ist. Ob die Zugriffsrichtlinie das Recht
``textract:DetectDocumentText`` trägt, sagt er nicht – er kann es nicht sagen,
denn er liest nur die Einstellungen.

Ohne diese Probe fiele das Fehlen erst auf, wenn eine Akte geöffnet wird. Das
ist der teurere Zeitpunkt: Der Lauf hält zwar nicht an, aber die gescannten
Blätter bleiben ungelesen, und das sieht aus wie ein Mangel der Erkennung und
nicht wie eine fehlende Berechtigung. Zwanzig Sekunden vorher sind billiger als
eine halbe Akte hinterher.

**Sie geht denselben Weg wie der Betrieb.** Nicht ein eigener ``boto3``-Aufruf,
sondern ``TextractOcr.erkennen`` selbst, mit demselben MIME-Typ und derselben
Zerlegung in einzelne Blätter. Dieses Projekt hat im September und Oktober
fünfmal gelernt: Eine Probe, die anders fragt als der Betrieb, prüft etwas
anderes als den Betrieb.

**Sie schickt kein Akteninhalt.** Das Blatt baut sie selbst – ein PDF mit einem
einzigen Wort darauf, das sie vorher kennt und hinterher wiederfindet. Aus der
Kanzlei geht nichts hinaus.

Kosten: ein Blatt, rund 0,15 Cent.
"""

from __future__ import annotations

import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from jusperfect.ocr.base import OcrFehler  # noqa: E402
from jusperfect.ocr.textract import TextractOcr  # noqa: E402

BREITE = 78

#: Das Wort auf dem Probeblatt.
#:
#: Es muss vier Dinge zugleich sein: eindeutig genug, dass ein Treffer kein
#: Zufall ist; frei von allem, was nach einer Akte aussieht; in Grossbuchstaben
#: ohne Umlaute, damit die Probe eine Berechtigung prueft statt einer
#: Schriftart - und **kurz genug, dass es auf die Seite passt**.
#:
#: Das vierte stand hier zuerst nicht, und es hat einen zweiten Lauf gekostet.
#: "JUSPERFECT TEXTERKENNUNG PROBE" ist bei 36 Punkt rund 594 Punkt breit und
#: begann bei x=60 - auf einer Seite von 595 Punkt Breite. AWS las davon
#: 23 Zeichen: "JUSPERFECT TEXTERKENNUN". Alles arbeitete richtig; nur lief
#: der Satz rechts aus dem Blatt.
#:
#: Die Lehre ist dieselbe wie am Vormittag, eine Stufe kleiner: Eine Probe
#: prueft nur das, was auch ankommt. Deshalb misst jetzt eine Pruefung den
#: Rand des gerenderten Bildes, statt sich auf eine Schaetzung zu verlassen.
PROBEWORT = "JUSPERFECT PROBE"


def _sagen(zeichen: str, text: str) -> None:
    print(f"  {zeichen}  {text}")


def probeblatt(text: str = PROBEWORT) -> bytes:
    """Ein einseitiges PDF mit genau diesem Text – von Hand gebaut.

    Von Hand, weil die Alternative eine weitere Abhängigkeit wäre
    (``reportlab``) und weil ein Probeblatt nichts können muss ausser lesbar
    sein. Die Form ist die eines PDF 1.4 mit einer Seite, einer Schrift und
    einem Textobjekt; die Verweistabelle wird aus den tatsächlichen Abständen
    berechnet, nicht hingeschrieben.
    """
    # 28 Punkt statt 36 und links 60: Bei A4 (595 Punkt breit) bleibt damit
    # auch fuer ein laengeres Wort Rand. Wie viel wirklich uebrig bleibt,
    # misst tests/test_texterkennung_probe.py am gerenderten Bild - geschaetzt
    # wurde es schon einmal, und die Schaetzung war um 60 Punkt daneben.
    inhalt = f"BT /F1 28 Tf 60 700 Td ({text}) Tj ET\n".encode("ascii")
    objekte = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]"
        b"/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        b"<</Length " + str(len(inhalt)).encode("ascii") + b">>stream\n"
        + inhalt + b"endstream",
    ]

    teile = [b"%PDF-1.4\n"]
    stellen: list[int] = []
    stand = len(teile[0])
    for nummer, objekt in enumerate(objekte, 1):
        stellen.append(stand)
        stueck = str(nummer).encode("ascii") + b" 0 obj\n" + objekt + b"\nendobj\n"
        teile.append(stueck)
        stand += len(stueck)

    tabelle = [b"xref\n0 " + str(len(objekte) + 1).encode("ascii") + b"\n",
               b"0000000000 65535 f \n"]
    for stelle in stellen:
        tabelle.append(f"{stelle:010d} 00000 n \n".encode("ascii"))
    teile.extend(tabelle)
    teile.append(
        b"trailer\n<</Size " + str(len(objekte) + 1).encode("ascii")
        + b"/Root 1 0 R>>\nstartxref\n" + str(stand).encode("ascii") + b"\n%%EOF\n"
    )
    return b"".join(teile)


def _gefunden(seiten: list, gesucht: str) -> bool:
    """Steht das Probewort im Ergebnis? Leerzeichen zählen dabei nicht mit.

    Textract gibt jede Zeile für sich zurück und darf das Wort anders umbrechen
    als es dasteht. Verglichen wird deshalb die Folge der Buchstaben, nicht die
    Folge der Zeilen.
    """
    text = "".join(s.text for s in seiten)
    ohne = "".join(text.split()).upper()
    return "".join(gesucht.split()).upper() in ohne


def main() -> int:
    region = "eu-central-1"
    print("=" * BREITE)
    print("  jusperfect – nimmt AWS die Texterkennung an?")
    print("=" * BREITE)
    print()
    print(f"  Region:      {region}")
    print(f"  Aufruf:      textract:DetectDocumentText")
    print(f"  Geschickt:   ein selbst gebautes Blatt mit einem Wort darauf")
    print()
    print("  Aus der Kanzlei geht nichts hinaus. Das Blatt baut die Probe selbst;")
    print("  es enthält kein Akteninhalt und keinen Mandantennamen.")
    print()

    blatt = probeblatt()

    try:
        erkennung = TextractOcr(region=region, bucket="")
    except Exception as fehler:
        _sagen("✗", f"Die Verbindung liess sich nicht einrichten: {fehler}")
        print()
        _sagen(" ", "Hinterlegt ZUGANG-EINTRAGEN.bat die AWS-Schlüssel? "
                    "ZUGANG-PRUEFEN.bat sagt, ob sie angenommen werden.")
        return 1

    try:
        seiten = erkennung.erkennen(blatt, "application/pdf", "probe", "probeblatt")
    except OcrFehler as fehler:
        # Der Satz kommt aus _warum() und nennt das fehlende Recht beim Namen.
        # Der Wortlaut von AWS steht absichtlich nicht darin.
        _sagen("✗", "Die Texterkennung hat abgelehnt.")
        print()
        for zeile in str(fehler).split(". "):
            if zeile.strip():
                print(f"      {zeile.strip().rstrip('.')}.")
        return 1
    except Exception as fehler:
        _sagen("✗", f"Unerwartet gescheitert ({type(fehler).__name__}).")
        return 1

    if not _gefunden(seiten, PROBEWORT):
        _sagen("!", "AWS hat geantwortet, aber das Probewort kam nicht zurück.")
        print()
        print(f"      Zurückgekommen sind {len(seiten)} Seite(n) mit zusammen "
              f"{sum(len(s.text) for s in seiten)} Zeichen.")
        print()
        print("      Die Berechtigung steht also – abgewiesen wurde nichts. Das")
        print("      ist ein Mangel der Erkennung, nicht des Zugangs. Bitte diese")
        print("      Meldung weitergeben; die Zahlen darüber sagen, woran es liegt.")
        return 1

    _sagen("✓", "Die Texterkennung arbeitet.")
    print()
    print("      Das Probewort ist hin- und zurückgegangen. Gescannte Blätter")
    print("      in einer echten Akte werden jetzt gelesen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
