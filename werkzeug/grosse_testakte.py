"""Erzeugt eine grosse, erfundene Testakte - den Massstab fuer grosse Akten.

Aus der Kanzlei: "Kann man das nicht schon einmal ausprobieren anhand einer
Akte mit 50 Dokumenten a 10 Seiten mindestens?"

Die vorhandenen Testakten haben acht Dokumente mit zusammen 7.000 Zeichen und
fuellen vier Prozent dessen, was in einen Modellaufruf passt. An ihnen ist
nicht zu erkennen, was bei einer echten Akte geschieht. Diese hier hat 50
Dokumente zu mindestens zehn Seiten - rund 875.000 Zeichen, das Fuenfeinhalb-
fache der Grenze.

Gewaehlt ist eine Bausache: Dort sind zehnseitige Schriftsaetze, Gutachten,
Bautagebuecher und Leistungsverzeichnisse der Normalfall, nicht die Ausnahme.

Der eigentliche Zweck sind die eingebauten Funde. Sie liegen bewusst WEIT
auseinander - Dokument 4 gegen Dokument 41 -, damit sich beweisen laesst, ob
das abschnittsweise Lesen sie noch findet. Eine Portion umfasst etwa zehn
Dokumente; ein Widerspruch innerhalb einer Portion waere kein Beweis.

Alle Namen, Firmen, Orte und Sachverhalte sind erfunden.

Aufruf:  python3 werkzeug/grosse_testakte.py [zielordner]
"""

from __future__ import annotations

import calendar
import json
import random
import re
import sys
from datetime import date
from pathlib import Path
from typing import NamedTuple

_WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag",
               "Samstag", "Sonntag"]
_MONATSNAMEN = ["", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
                "August", "September", "Oktober", "November", "Dezember"]

SEED = 20260908          # feste Saat: dieselbe Akte bei jedem Lauf
MINDESTZEICHEN = 17_500  # zehn Seiten zu je rund 1.750 Zeichen

BAUHERRIN = "Marlies Kettenbach"
UNTERNEHMEN = "Steinacker Bau GmbH"
GESCHAEFTSFUEHRER = "Egbert Steinacker"
POLIER = "Hasso Wendtland"
ARCHITEKT = "Dipl.-Ing. Cornelia Aufderheide"
GUTACHTER = "Dipl.-Ing. Reinhart Vosskuhle"
GEGENANWALT = "Kanzlei Pflüger, Marwitz & Kollegen"
SUBUNTERNEHMER = "Dämmtechnik Oberholz e.K."
EIGENE_KANZLEI = "Rechtsanwälte Dr. Weber & Partner"
FACHFIRMA = "Sanierungstechnik Lührmann GmbH"
GERICHT = "Landgericht Göttingen"
BEHOERDE = "Stadt Göttingen, Bauordnungsamt"
BAUSTELLE = "Kettenbachweg 8, 37073 Göttingen"

# ── Die eingebauten Funde ───────────────────────────────────────────────────
# Jeder besteht aus zwei Haelften in weit auseinanderliegenden Dokumenten.
#
# "Weit" heisst hier: mehr als eine Portion. Bei zehn Seiten je Dokument passen
# neun Dokumente in einen Aufruf; zwei Haelften im Abstand von fuenf waeren
# womoeglich zusammen gelesen worden und bewiesen dann nichts.
class Fund(NamedTuple):
    """Ein eingebauter Widerspruch - und woran sich messen laesst, ob er steht.

    `merkmale` sind die harten Angaben, ohne die eine Antwort den Fund nicht
    wirklich benennt. Wer schreibt "es gibt Unstimmigkeiten beim Abnahmedatum",
    hat ihn nicht benannt; wer die beiden Daten nennt, schon.
    """
    name: str
    beschreibung: str
    erste: str            # Dokument mit der einen Haelfte
    zweite: str           # Dokument mit der anderen
    merkmale: tuple[str, ...]


FUNDE = [
    Fund("Abnahmedatum",
         "Das Abnahmeprotokoll nennt den 14.08.2025, die Schlussrechnung behauptet "
         "eine Abnahme am 02.07.2025.", "D-012", "D-039",
         ("14.08.2025", "02.07.2025")),
    Fund("Rügezeitpunkt",
         "Die Mängelanzeige datiert vom 20.06.2025; die Gegenseite behauptet, der "
         "Mangel sei erstmals 2026 gerügt worden.", "D-008", "D-044",
         ("20.06.2025", "2026")),
    Fund("Zeuge nicht vor Ort",
         "Das Bautagebuch vermerkt für den 11.06.2025 die Abwesenheit des Poliers; "
         "die Gegenseite benennt ihn für diesen Tag als Augenzeugen.", "D-017", "D-046",
         ("11.06.2025",)),
    Fund("Kenntnis der Rüge",
         "Der Geschäftsführer erklärt am 03.07.2025, von keiner Rüge zu wissen; "
         "sein Empfangsbekenntnis vom 21.06.2025 liegt vor.", "D-009", "D-027",
         ("03.07.2025", "21.06.2025")),
    Fund("Dämmstärke",
         "Das Leistungsverzeichnis verlangt 24 cm, das Gutachten misst 18 cm, "
         "abgerechnet wurden 24 cm.", "D-002", "D-031",
         ("24 cm", "18 cm")),
]

# ── Was sonst noch in der Akte steckt ───────────────────────────────────────
# Dieselbe Auflistung steht in Prosa in testdaten/grosse-akte/AUFLOESUNG.md.
# tests/test_grosse_testakte.py haelt beide aneinander, damit die Beschreibung
# fuer den Menschen und der Massstab fuer die Maschine nicht auseinanderlaufen.

# Die Tage, an denen in dieser Sache etwas geschehen ist. Ein Zeitstrahl, der
# sie nicht traegt, ist unvollstaendig; einer, der in vierzig Kolonnenstaerken
# aus den Bautagebuechern ertrinkt, ist unbrauchbar.
CHRONOLOGIE = [
    ("14.02.2025", "Leistungsverzeichnis"),
    ("11.06.2025", "Einbau der Dämmung ohne Polier"),
    ("14.06.2025", "Feuchtigkeit erstmals festgestellt"),
    ("20.06.2025", "Mängelanzeige"),
    ("21.06.2025", "Empfangsbekenntnis des Geschäftsführers"),
    ("03.07.2025", "Erklärung, von keiner Rüge zu wissen"),
    ("14.08.2025", "Abnahme unter Vorbehalt"),
    ("02.09.2025", "Schlussrechnung"),
    ("04.12.2025", "Beweisbeschluss"),
    ("27.01.2026", "Ortstermin"),
    ("18.02.2026", "Gutachten"),
    ("11.03.2026", "Schriftsatz der Gegenseite"),
    ("08.04.2026", "Zeugenbenennung"),
]

# Die Zahlen, die unter "Forderungen" stehen muessen.
ZAHLEN = [
    ("486.500,00 EUR", "Werklohn brutto"),
    ("48.650,00 EUR", "Einbehalt"),
    ("61.400,00 EUR", "Kosten der Mängelbeseitigung netto"),
    ("7.140,00 EUR", "Gutachterkosten"),
    ("402,00 m²", "Dämmfläche"),
]

# Die Fristensperre: Das Programm darf den Ausloeser benennen, aber kein
# Enddatum rechnen. Die Verjaehrung einer Bausache lauefe in die Jahre 2027 ff.;
# taucht ein solches Jahr neben dem Wort "Verjaehrung" auf, ist gerechnet worden.
FRISTENSPERRE_VERBOTENE_JAHRE = ("2027", "2028", "2029", "2030", "2031")

# ── Bausteine fuer glaubwuerdigen Fliesstext ────────────────────────────────
WETTER = ["trocken, 18 °C", "bedeckt, 14 °C", "Regenschauer, 11 °C", "sonnig, 24 °C",
          "wechselnd bewölkt, 16 °C", "Dauerregen, 9 °C", "schwül, 27 °C", "windig, 13 °C"]
GEWERKE = ["Rohbau", "Dachdecker", "Zimmerer", "Elektro", "Sanitär", "Estrich",
           "Trockenbau", "Fassade", "Wärmedämmverbundsystem", "Fenster", "Maler",
           "Bodenbelag", "Außenanlagen", "Heizung", "Lüftung"]
TAETIGKEITEN = [
    "Fortsetzung der Arbeiten gemäß Bauzeitenplan",
    "Materialanlieferung, Abladen und Einlagerung im Bauzelt",
    "Aufmaß genommen und im Beisein der Bauleitung geprüft",
    "Nacharbeiten an der Vortagsleistung",
    "Abstimmung der Anschlussdetails mit der Bauleitung",
    "Einrichtung des Arbeitsbereichs, Absturzsicherung gestellt",
    "Prüfung der Vorleistung, keine Beanstandungen",
    "Unterbrechung wegen Witterung, Arbeiten eingestellt",
    "Anlieferung verzögert, Umdisposition der Kolonne",
    "Reinigung des Arbeitsbereichs, Bauschutt abgefahren",
]
POSITIONEN = [
    ("Erdarbeiten, Aushub Baugrube", "m³", 486.0, 18.40),
    ("Sauberkeitsschicht C8/10", "m²", 214.5, 12.80),
    ("Bodenplatte Stahlbeton C25/30", "m³", 62.4, 168.00),
    ("Mauerwerk Außenwand, Planziegel 36,5 cm", "m²", 388.0, 94.50),
    ("Stahlbetondecke, Ortbeton, d = 20 cm", "m²", 214.5, 132.00),
    ("Wärmedämmverbundsystem, Mineralwolle, d = 24 cm", "m²", 402.0, 88.60),
    ("Dachstuhl, Kehlbalkendach, Nadelholz C24", "m²", 236.0, 148.00),
    ("Dacheindeckung, Tonziegel, inkl. Lattung", "m²", 236.0, 76.40),
    ("Fenster, Kunststoff, dreifach verglast, Uw 0,9", "St", 24.0, 986.00),
    ("Innenputz, Gipsputz, zweilagig", "m²", 742.0, 24.90),
    ("Estrich, Zementestrich auf Dämmung, d = 60 mm", "m²", 402.0, 38.70),
    ("Sanitärinstallation, Rohleitungen", "psch", 1.0, 28400.00),
    ("Elektroinstallation, Grundausstattung", "psch", 1.0, 34200.00),
    ("Heizung, Wärmepumpe Luft/Wasser 12 kW", "St", 1.0, 21800.00),
    ("Malerarbeiten, Innenanstrich zweifach", "m²", 742.0, 14.20),
]
RECHTSSAETZE = [
    "Nach § 631 Abs. 1 BGB ist der Unternehmer zur Herstellung des versprochenen "
    "Werkes verpflichtet.",
    "Ein Werk ist gemäß § 633 Abs. 2 Satz 1 BGB frei von Sachmängeln, wenn es die "
    "vereinbarte Beschaffenheit hat.",
    "Die Abnahme ist die körperliche Entgegennahme verbunden mit der Anerkennung "
    "des Werkes als im Wesentlichen vertragsgemäß.",
    "Mit der Abnahme geht die Vergütungsgefahr auf den Besteller über und die "
    "Verjährung der Mängelansprüche beginnt.",
    "Die Beweislast für die Mangelfreiheit trägt bis zur Abnahme der Unternehmer.",
    "Der Besteller kann nach § 637 BGB den Mangel selbst beseitigen und Ersatz der "
    "erforderlichen Aufwendungen verlangen, wenn eine gesetzte Frist fruchtlos "
    "verstrichen ist.",
    "Ein Zurückbehaltungsrecht besteht nach § 641 Abs. 3 BGB in Höhe des Doppelten "
    "der für die Mängelbeseitigung erforderlichen Kosten.",
    "Die anerkannten Regeln der Technik bestimmen den geschuldeten Standard auch "
    "dann, wenn der Vertrag dazu schweigt.",
]
STANDARDABSATZ = [
    "Die vorstehenden Ausführungen beruhen auf den bei den Akten befindlichen "
    "Unterlagen sowie den Angaben der Beteiligten. Soweit Angaben streitig sind, "
    "ist dies jeweils kenntlich gemacht.",
    "Die Bauleitung hat die Ausführung stichprobenartig überwacht. Eine "
    "lückenlose Überwachung war vertraglich nicht geschuldet und ist auch nicht "
    "erfolgt.",
    "Der zeitliche Ablauf ergibt sich aus dem Bautagebuch, das täglich geführt und "
    "von der Bauleitung gegengezeichnet wurde.",
    "Auf die beigefügten Anlagen wird zur Vermeidung von Wiederholungen "
    "ausdrücklich Bezug genommen.",
    "Eine abschließende rechtliche Bewertung bleibt dem weiteren Vortrag "
    "vorbehalten.",
    "Die Kosten der Ersatzvornahme sind durch das eingeholte Angebot belegt und "
    "der Höhe nach angemessen.",
    "Sämtliche Fristsetzungen erfolgten schriftlich und sind durch "
    "Einwurf-Einschreiben nachgewiesen.",
]


# ── Bausteine zu Dokumenten fuegen ──────────────────────────────────────────

def _arbeitstage(monat: date) -> list[date]:
    """Die Werktage des Monats, in dem dieser Tag liegt."""
    letzter = calendar.monthrange(monat.year, monat.month)[1]
    tage = [date(monat.year, monat.month, t) for t in range(1, letzter + 1)]
    return [t for t in tage if t.weekday() < 5]


def _genannte_tage(text: str) -> set[date]:
    """Die Tage, die im vorgegebenen Text schon vorkommen.

    Ein Bautagebuch, das den 11.06.2025 bereits traegt, darf fuer denselben Tag
    keinen zweiten, womoeglich widersprechenden Eintrag erhalten. Der
    eingebaute Fund 3 haengt genau an diesem Tag.
    """
    gefunden = set()
    for tt, mm, jjjj in re.findall(r"(\d{2})\.(\d{2})\.(\d{4})", text):
        try:
            gefunden.add(date(int(jjjj), int(mm), int(tt)))
        except ValueError:
            continue
    return gefunden


def _tagebucheintrag(zufall: random.Random, tag: date) -> str:
    """Ein Tag im Bautagebuch - mehrere Gewerke, wie es auf einer Baustelle ist."""
    zeilen = [f"\n{tag.strftime('%d.%m.%Y')} ({_WOCHENTAGE[tag.weekday()]}) – "
              f"{zufall.choice(WETTER)}\n"
              f"Arbeitszeit 07:00 bis 16:30 Uhr. "
              f"Bauleitung anwesend {'ja' if zufall.random() > 0.3 else 'nein'}.\n"]
    for gewerk in zufall.sample(GEWERKE, zufall.randint(3, 4)):
        erste, zweite = zufall.sample(TAETIGKEITEN, 2)
        zeilen.append(f"Gewerk {gewerk}: Kolonne {zufall.randint(2, 9)} Personen. "
                      f"{erste}. {zweite}.\n")
    bez = zufall.choice(POSITIONEN)[0]
    zeilen.append(f"Anlieferung: {bez}, Lieferschein Nr. "
                  f"{zufall.randint(10000, 99999)}, Menge geprüft und übernommen.\n")
    zeilen.append(f"Besondere Vorkommnisse: "
                  f"{zufall.choice(['keine', 'keine', 'keine', 'Anlieferung verspätet', 'Kran ausgefallen'])}.\n")
    return "".join(zeilen)


#: Woran im Bautagebuch ein Tageseintrag beginnt: "06.03.2025 (Donnerstag) - ...".
_TAGESKOPF = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4}) \(", re.M)


def besondere_tage(ordner: Path) -> set[str]:
    """Die Tage, an denen das Bautagebuch SELBST ein Vorkommnis vermerkt.

    Gebraucht vom Pruefbogen, und zwar als Gegenstueck zum Rauschwert. Der
    Auftrag sagt dem Modell: Ein Tag aus einem laufenden Tagesbericht gehoert
    hinein, WENN er ein besonderes Vorkommnis traegt - eine Abwesenheit, eine
    abweichende Lieferung. Diese Akte stellt genau solche Vorkommnisse her,
    gewuerfelt: 60 der 126 Tage tragen eines, 45 eine abwesende Bauleitung.

    Am 01.10.2026 zaehlte der Bogen zwei solche Tage als Rauschen. Damit mass
    er die Befolgung der Anweisung als Fehler - und haette, waere man ihm
    gefolgt, zum Nachschaerfen genau der Worte gefuehrt, an denen Fund 3
    haengt. Ein Massstab, der das Richtige bestraft, ist schlimmer als keiner.
    """
    tage: set[str] = set()
    for datei in sorted(ordner.glob("*.txt")):
        text = datei.read_text(encoding="utf-8", errors="ignore")
        if "Besondere Vorkommnisse:" not in text:
            continue
        koepfe = list(_TAGESKOPF.finditer(text))
        for nummer, kopf in enumerate(koepfe):
            ende = koepfe[nummer + 1].start() if nummer + 1 < len(koepfe) else len(text)
            block = text[kopf.start():ende]
            vorkommnis = re.search(r"Besondere Vorkommnisse: (.+?)\.", block)
            if ("Bauleitung anwesend nein" in block
                    or (vorkommnis and vorkommnis.group(1).strip() != "keine")):
                tag, monat, jahr = kopf.groups()
                tage.add(f"{jahr}-{monat}-{tag}")
    return tage


def _wochenbericht(zufall: random.Random, monat: date, woche: int) -> str:
    """Anlage zum Bautagebuch, falls die Werktage des Monats nicht ausreichen."""
    return (f"\nAnlage zum Bautagebuch {_MONATSNAMEN[monat.month]} {monat.year} – "
            f"Wochenbericht {woche}\n"
            f"Personalstand im Wochenmittel: {zufall.randint(9, 24)} Personen. "
            f"{'. '.join(zufall.sample(TAETIGKEITEN, 2))}.\n"
            f"Geprüfte Vorleistungen: {', '.join(zufall.sample(GEWERKE, 2))}. "
            f"{zufall.choice(STANDARDABSATZ)}\n")


def _fuellen(zufall: random.Random, text: str, mindestens: int, thema: str,
             monat: date | None = None) -> str:
    """Bis zur Mindestlaenge mit sachlich passendem Text auffuellen.

    Nicht mit Wiederholungen: Ein Bautagebuch fuellt sich mit Tagen, ein
    Schriftsatz mit Rechtssaetzen und Wuerdigung, ein Aufmass mit Positionen.
    Sonst waere die Akte zwar gross, aber als Pruefstein wertlos - ein Modell
    erkennt Wiederholung und ueberspringt sie.

    Ein Bautagebuch fuellt sich mit den Werktagen SEINES Monats. Frueher lief
    es stur ab dem 01.03.2025 - dann stand im Tagebuch fuer August ein Eintrag
    vom Maerz, und wer die Akte pruefte, konnte nicht mehr unterscheiden, ob
    das Programm irrt oder die Testdaten.
    """
    teile = [text]
    laenge = len(text)
    nummer = 1
    if thema == "tagebuch":
        if monat is None:
            raise ValueError("Ein Bautagebuch braucht den Monat, den es abbildet.")
        offene_tage = [t for t in _arbeitstage(monat) if t not in _genannte_tage(text)]
    while laenge < mindestens:
        if thema == "tagebuch":
            if offene_tage:
                block = _tagebucheintrag(zufall, offene_tage.pop(0))
            else:
                block = _wochenbericht(zufall, monat, nummer)
        elif thema == "positionen":
            bez, einheit, menge, preis = zufall.choice(POSITIONEN)
            menge = round(menge * zufall.uniform(0.8, 1.2), 2)
            block = (f"\nPos. {nummer:03d}  {bez}\n"
                     f"    Menge {menge:,.2f} {einheit}   Einheitspreis {preis:,.2f} EUR   "
                     f"Gesamt {menge * preis:,.2f} EUR\n"
                     f"    Ausführung nach DIN 18299 ff. und den anerkannten Regeln der Technik.\n"
                     .replace(",", "#").replace(".", ",").replace("#", "."))
        elif thema == "recht":
            erster, zweiter = zufall.sample(RECHTSSAETZE, 2)
            block = (f"\n{nummer + 1}. {erster} "
                     f"{zufall.choice(STANDARDABSATZ)} {zweiter}\n")
        else:
            erster, zweiter = zufall.sample(STANDARDABSATZ, 2)
            block = (f"\n{erster} {zufall.choice(TAETIGKEITEN)}. {zweiter}\n")
        teile.append(block)
        laenge += len(block)
        nummer += 1
    return "".join(teile)


# ── Die tragenden Dokumente ─────────────────────────────────────────────────
# Sie enthalten die Funde. Ihre Nummern sind mit Bedacht gewaehlt: Die beiden
# Haelften eines Widerspruchs liegen mindestens zwoelf Dokumente auseinander,
# damit sie bei abschnittsweisem Lesen nicht zufaellig zusammen gelesen werden.

TRAGEND: dict[int, tuple[str, str, str, str, str]] = {
    2: ("Leistungsverzeichnis, Auszug", "2025-02-14", "Mandant", "positionen",
        f"""LEISTUNGSVERZEICHNIS – Auszug
Bauvorhaben: Einfamilienhaus {BAUSTELLE}
Bauherrin: {BAUHERRIN}   ·   Planung: {ARCHITEKT}

Pos. 6.40  Wärmedämmverbundsystem
    Mineralwolle-Dämmplatten, Wärmeleitfähigkeitsgruppe 035,
    Dämmstärke 24 cm, verklebt und verdübelt, einschließlich
    Armierungsschicht und Oberputz.
    Menge 402,00 m²   Einheitspreis 88,60 EUR
    Die Dämmstärke von 24 cm ist verbindlich vereinbart und darf nicht
    unterschritten werden; sie ist Grundlage des Nachweises nach GEG.
"""),
    8: ("Mängelanzeige der Bauherrin", "2025-06-20", "Mandant", "text",
        f"""{BAUHERRIN}
{BAUSTELLE}

{UNTERNEHMEN}
z. Hd. Herrn {GESCHAEFTSFUEHRER}

Göttingen, den 20.06.2025

Mängelanzeige – Feuchtigkeit im Kellergeschoss

Sehr geehrter Herr {GESCHAEFTSFUEHRER},

hiermit zeige ich Ihnen folgende Mängel an und fordere Sie zur Beseitigung auf:

1. An der Nordwand des Kellergeschosses zeigen sich seit dem 14.06.2025 auf
   einer Länge von etwa 4,20 m dunkle Verfärbungen und feuchte Stellen.
2. Der Sockelbereich der Außendämmung weist an mehreren Stellen Hohlstellen auf,
   die beim Abklopfen deutlich hörbar sind.
3. Die Abdichtung im Übergang Bodenplatte/Aufgehendes Mauerwerk ist an der
   Nordostecke sichtbar unvollständig.

Zur Beseitigung setze ich Ihnen eine Frist bis zum 11.07.2025.

Dieses Schreiben ging Ihnen per Einwurf-Einschreiben zu.
"""),
    9: ("Empfangsbekenntnis und E-Mail-Verkehr", "2025-06-21", "Gegner", "text",
        f"""AUSDRUCK E-MAIL-VERKEHR

Von: {GESCHAEFTSFUEHRER} <steinacker@steinacker-bau.example>
An: {BAUHERRIN} <m.kettenbach@example.org>
Datum: 21.06.2025, 08:14 Uhr
Betreff: AW: Mängelanzeige – Feuchtigkeit im Kellergeschoss

Sehr geehrte Frau {BAUHERRIN},

Ihr Schreiben vom 20.06.2025 habe ich erhalten und zur Kenntnis genommen.
Ich werde die von Ihnen bezeichneten Stellen im Kellergeschoss in der
kommenden Woche gemeinsam mit unserem Polier in Augenschein nehmen.

Mit freundlichen Grüßen
{GESCHAEFTSFUEHRER}
"""),
    12: ("Abnahmeprotokoll", "2025-08-14", "Gegner", "text",
         f"""ABNAHMEPROTOKOLL

Bauvorhaben: {BAUSTELLE}
Datum der Abnahme: 14.08.2025, 10:00 bis 11:45 Uhr

Anwesend:
  {BAUHERRIN} (Bauherrin)
  {GESCHAEFTSFUEHRER} ({UNTERNEHMEN})
  {ARCHITEKT} (Bauleitung)

Die Abnahme fand am heutigen Tage, dem 14.08.2025, statt. Das Werk wird unter
Vorbehalt der nachstehenden Mängel als im Wesentlichen vertragsgemäß
entgegengenommen.

Vorbehalte:
  1. Feuchtigkeit Kellergeschoss Nordwand – nicht beseitigt (siehe Anzeige
     vom 20.06.2025)
  2. Hohlstellen im Sockelbereich der Außendämmung
  3. Zwei Fensterbänke ohne Gefälle

Ein Einbehalt in Höhe von 48.650,00 EUR wird vereinbart.
"""),
    27: ("Schreiben der Gegenseite an die Bauleitung", "2025-07-03", "Gegner", "text",
         f"""{UNTERNEHMEN}

An die Bauleitung
{ARCHITEKT}

Göttingen, den 03.07.2025

Betreff: Sachstand Bauvorhaben {BAUSTELLE}

Sehr geehrte Frau Kollegin,

zu Ihrer Anfrage vom Vortag teile ich mit, dass mir eine Mängelrüge der
Bauherrin nicht bekannt ist. Weder liegt mir ein entsprechendes Schreiben vor
noch ist eine Rüge mündlich an mich herangetragen worden.

Sollte die Bauherrin Beanstandungen haben, bitte ich um deren Mitteilung in
Textform; bis dahin sehe ich keinen Anlass für Nacharbeiten.

Mit freundlichen Grüßen
{GESCHAEFTSFUEHRER}
"""),
    17: ("Bautagebuch, Juni 2025", "2025-06-30", "Mandant", "tagebuch",
         f"""BAUTAGEBUCH – Juni 2025
Bauvorhaben: {BAUSTELLE}
Geführt von: {ARCHITEKT}

11.06.2025 – bedeckt, 15 °C
Gewerk: Wärmedämmverbundsystem, ausgeführt durch {SUBUNTERNEHMER}.
Kolonne: 4 Personen. Bauleitung anwesend ja.
Polier {POLIER} ist an diesem Tag NICHT auf der Baustelle erschienen; er ist
ausweislich der Mitteilung des Unternehmens erkrankt. Die Kolonne arbeitete
ohne Aufsicht des Poliers.
Besondere Vorkommnisse: Dämmplatten angeliefert, Stärke nach Aufdruck 18 cm.
Hinweis der Bauleitung an die Kolonne, dass 24 cm geschuldet sind.

14.06.2025 – Dauerregen, 12 °C
Gewerk: keine Arbeiten. An der Nordwand des Kellers erstmals dunkle
Verfärbungen festgestellt und fotografisch dokumentiert.
"""),
    31: ("Selbständiges Beweisverfahren – Gutachten", "2026-02-18", "Sachverständige", "recht",
         f"""SACHVERSTÄNDIGENGUTACHTEN

Sachverständiger: {GUTACHTER}, öffentlich bestellt und vereidigt
Beweisbeschluss des Landgerichts Göttingen vom 04.12.2025
Ortstermin: 27.01.2026

BEFUND

Zu Beweisfrage 1 (Dämmstärke):
An sechs Messpunkten wurde die Dämmschicht durch Bohrkernentnahme geöffnet.
Die gemessene Dämmstärke beträgt an allen sechs Messpunkten 18 cm
(Einzelwerte: 18,0 / 18,0 / 17,5 / 18,0 / 18,5 / 18,0 cm).
Die vertraglich geschuldete Dämmstärke von 24 cm ist damit um 6 cm
unterschritten.

Zu Beweisfrage 2 (Feuchtigkeit):
Die Feuchtigkeit an der Nordwand beruht auf einer unvollständigen Abdichtung
im Übergang Bodenplatte/aufgehendes Mauerwerk. Die Ausführung entspricht nicht
den anerkannten Regeln der Technik.

Kosten der Mängelbeseitigung: 61.400,00 EUR netto.
Kosten dieses Gutachtens: 7.140,00 EUR.
"""),
    39: ("Schlussrechnung", "2025-09-02", "Gegner", "positionen",
         f"""{UNTERNEHMEN}
SCHLUSSRECHNUNG Nr. 2025-1184

Bauvorhaben: {BAUSTELLE}
Bauherrin: {BAUHERRIN}

Die Abnahme des Werkes erfolgte am 02.07.2025. Die Schlussrechnung wird
hiermit gemäß § 650g BGB gestellt.

Pos. 6.40  Wärmedämmverbundsystem, Dämmstärke 24 cm
    Menge 402,00 m²   Einheitspreis 88,60 EUR   Gesamt 35.617,20 EUR

Gesamtsumme netto        408.823,53 EUR
Umsatzsteuer 19 %         77.676,47 EUR
Gesamtsumme brutto       486.500,00 EUR

Ein Einbehalt ist nicht gerechtfertigt und wird zurückgewiesen.
"""),
    44: ("Schriftsatz der Gegenseite", "2026-03-11", "Gegner", "recht",
         f"""{GEGENANWALT}

An das Landgericht Göttingen

In dem Rechtsstreit
{BAUHERRIN} ./. {UNTERNEHMEN}

nehmen wir wie folgt Stellung:

I.
Mängelansprüche bestehen nicht. Die Bauherrin hat die behauptete Feuchtigkeit
im Kellergeschoss erstmals im Jahr 2026 gerügt, nämlich mit Schriftsatz vom
15.01.2026. Eine frühere Rüge ist nicht erfolgt und wird ausdrücklich
bestritten.

II.
Die Abnahme ist am 02.07.2025 erfolgt. Die Verjährungsfrist für
Mängelansprüche läuft daher ab diesem Tage.

III.
Der Werklohn ist in voller Höhe von 486.500,00 EUR zur Zahlung fällig.
"""),
    46: ("Zeugenbenennung der Gegenseite", "2026-04-08", "Gegner", "text",
         f"""{GEGENANWALT}

An das Landgericht Göttingen

Beweisangebot

Zum Beweis der Tatsache, dass die Dämmplatten am 11.06.2025 in der
geschuldeten Stärke von 24 cm eingebaut wurden, benennen wir:

  Zeuge {POLIER}, Polier, zu laden über die Beklagte.

Der Zeuge war am 11.06.2025 den ganzen Tag auf der Baustelle anwesend und hat
den Einbau persönlich überwacht. Er wird bekunden, dass die Platten der
Stärke 24 cm verwendet und ordnungsgemäß verklebt und verdübelt wurden.
"""),
}


# ── Die Routine dazwischen ──────────────────────────────────────────────────
# Eine echte Akte besteht zu vier Fuenfteln aus Vorgaengen ohne eigenen
# Erkenntniswert: Fristverlaengerungen, Empfangsbekenntnisse, Aufmasse,
# Sachstandsanfragen. Genau das macht sie unuebersichtlich - und genau deshalb
# gehoert es in einen Pruefstein hinein. Eine Akte aus fuenfzig tragenden
# Schriftsaetzen waere keine Akte, sondern eine Sammlung.

# Absender und Datum stehen hier ausdruecklich, nicht mehr aus der Stellung in
# der Liste gewuerfelt. Frueher trug das Bautagebuch fuer August den Absender
# der Bauherrin und ein Datum aus dem Juli; ein Ergaenzungsgutachten kam vom
# Gericht statt vom Sachverstaendigen. Beides ist erfunden, aber es war
# widerspruechlich erfunden - und damit war an dieser Akte nicht mehr zu
# messen, ob eine falsche Angabe vom Programm stammt oder aus den Testdaten.
#
# Die Daten bilden den Gang der Sache ab: Bau von Februar bis September 2025,
# Maengelruege im Juni 2025, selbstaendiges Beweisverfahren ab Oktober 2025,
# Hauptsache ab Februar 2026, Ergaenzungsgutachten im August 2026 (die Frist
# zur Stellungnahme laeuft am 30.09.2026 ab).
ROUTINE = [
    ("Bauvertrag, Auszug", "2025-02-20", f"{UNTERNEHMEN} / {BAUHERRIN}", "Mandant", "recht"),
    ("Baugenehmigung, Auszug", "2025-01-15", BEHOERDE, "Behörde", "text"),
    ("Bautagebuch, März 2025", "2025-03-31", ARCHITEKT, "Mandant", "tagebuch"),
    ("Bautagebuch, April 2025", "2025-04-30", ARCHITEKT, "Mandant", "tagebuch"),
    ("Bautagebuch, Mai 2025", "2025-05-31", ARCHITEKT, "Mandant", "tagebuch"),
    ("Bautagebuch, Juli 2025", "2025-07-31", ARCHITEKT, "Mandant", "tagebuch"),
    ("Bautagebuch, August 2025", "2025-08-29", ARCHITEKT, "Mandant", "tagebuch"),
    ("Aufmaßblatt Rohbau", "2025-05-12", UNTERNEHMEN, "Gegner", "positionen"),
    ("Aufmaßblatt Dachdecker", "2025-06-16", UNTERNEHMEN, "Gegner", "positionen"),
    ("Aufmaßblatt Fassade", "2025-07-21", UNTERNEHMEN, "Gegner", "positionen"),
    ("Abschlagsrechnung Nr. 1", "2025-04-07", UNTERNEHMEN, "Gegner", "positionen"),
    ("Abschlagsrechnung Nr. 2", "2025-06-05", UNTERNEHMEN, "Gegner", "positionen"),
    ("Abschlagsrechnung Nr. 3", "2025-07-28", UNTERNEHMEN, "Gegner", "positionen"),
    ("Zahlungsnachweis Abschläge", "2025-08-05", BAUHERRIN, "Mandant", "positionen"),
    ("Nachtragsangebot Nr. 1", "2025-05-20", UNTERNEHMEN, "Gegner", "positionen"),
    ("Nachtragsangebot Nr. 2", "2025-07-15", UNTERNEHMEN, "Gegner", "positionen"),
    ("Protokoll Baubesprechung 12.03.2025", "2025-03-12", ARCHITEKT, "Mandant", "text"),
    ("Protokoll Baubesprechung 09.04.2025", "2025-04-09", ARCHITEKT, "Mandant", "text"),
    ("Protokoll Baubesprechung 07.05.2025", "2025-05-07", ARCHITEKT, "Mandant", "text"),
    ("Protokoll Baubesprechung 04.06.2025", "2025-06-04", ARCHITEKT, "Mandant", "text"),
    ("Lichtbildmappe Kellergeschoss, Beschreibung", "2025-06-23", ARCHITEKT, "Mandant", "text"),
    ("Fristsetzung zur Mängelbeseitigung", "2025-07-14", BAUHERRIN, "Mandant", "text"),
    ("Antwortschreiben der Gegenseite", "2025-07-24", UNTERNEHMEN, "Gegner", "text"),
    ("Angebot Ersatzvornahme, Fachfirma", "2025-08-20", FACHFIRMA, "Mandant", "positionen"),
    ("Anwaltliches Aufforderungsschreiben", "2025-09-15", EIGENE_KANZLEI, "Mandant", "recht"),
    ("Antrag auf selbständiges Beweisverfahren", "2025-11-10", EIGENE_KANZLEI, "Mandant", "recht"),
    ("Beweisbeschluss des Landgerichts", "2025-12-04", GERICHT, "Gericht", "recht"),
    ("Ladung zum Ortstermin", "2026-01-08", GERICHT, "Gericht", "text"),
    ("Protokoll des Ortstermins", "2026-01-27", GUTACHTER, "Sachverständige", "text"),
    ("Kostenrechnung des Sachverständigen", "2026-02-25", GUTACHTER, "Sachverständige", "positionen"),
    ("Klageschrift", "2026-01-15", EIGENE_KANZLEI, "Mandant", "recht"),
    ("Empfangsbekenntnis Klageschrift", "2026-01-22", GEGENANWALT, "Gegner", "text"),
    ("Stellungnahme zum Gutachten, Bauherrin", "2026-03-05", EIGENE_KANZLEI, "Mandant", "recht"),
    ("Fristverlängerungsantrag der Gegenseite", "2026-02-05", GEGENANWALT, "Gegner", "text"),
    ("Verfügung des Vorsitzenden", "2026-02-10", GERICHT, "Gericht", "text"),
    ("Stellungnahme zum Gutachten, Gegenseite", "2026-03-16", GEGENANWALT, "Gegner", "recht"),
    ("Replik der Bauherrin", "2026-04-22", EIGENE_KANZLEI, "Mandant", "recht"),
    ("Duplik der Gegenseite", "2026-05-13", GEGENANWALT, "Gegner", "recht"),
    ("Terminsverlegungsantrag", "2026-06-10", GEGENANWALT, "Gegner", "text"),
    ("Ergänzungsgutachten", "2026-08-24", GUTACHTER, "Sachverständige", "recht"),
]

# Die Rechnung muss aufgehen: 50 Dokumente, davon die tragenden.
assert len(ROUTINE) == 50 - len(TRAGEND), (len(ROUTINE), len(TRAGEND))


def _monat_aus_titel(titel: str, tag: date) -> date:
    """Der Monat, den ein Dokument abbildet - aus dem Titel, nicht aus dem Datum.

    "Bautagebuch, August 2025" bildet den August ab, gleich an welchem Tag es
    abgeschlossen wurde. Steht im Titel kein Monat, gilt der Monat des Datums.
    """
    treffer = re.search(r"(" + "|".join(_MONATSNAMEN[1:]) + r")\s+(\d{4})", titel)
    if treffer:
        return date(int(treffer.group(2)), _MONATSNAMEN.index(treffer.group(1)), 1)
    return date(tag.year, tag.month, 1)


def _empfaenger(absender: str) -> str:
    """An wen ein Schreiben geht, ergibt sich aus dem, von wem es kommt."""
    if absender == GERICHT:
        return f"{EIGENE_KANZLEI} und {GEGENANWALT}"
    if absender in (GEGENANWALT, UNTERNEHMEN):
        return EIGENE_KANZLEI
    if absender in (EIGENE_KANZLEI, GUTACHTER):
        return GERICHT
    if absender in (BEHOERDE, FACHFIRMA):
        return BAUHERRIN
    return BAUHERRIN


def _routinetext(zufall: random.Random, titel: str, tag: date, absender: str,
                 thema: str, monat: date | None) -> str:
    """Der Kopf eines Routinedokuments - Absender, Empfaenger, Ort und Datum.

    Der Absender wird uebergeben, nicht aus der Herkunftsgruppe erraten: Ein
    Bautagebuch fuehrt die Bauleitung, ein Ergaenzungsgutachten schreibt der
    Sachverstaendige, ein Empfangsbekenntnis zeichnet der Anwalt.
    """
    if thema == "tagebuch" and monat is not None:
        return (f"BAUTAGEBUCH – {_MONATSNAMEN[monat.month]} {monat.year}\n"
                f"Bauvorhaben: {BAUSTELLE}\n"
                f"Geführt von: {absender}\n"
                f"Abgeschlossen und der Bauherrin übergeben am "
                f"{tag.strftime('%d.%m.%Y')}\n")
    return (f"{absender}\n\n{_empfaenger(absender)}\n\n"
            f"Bauvorhaben: {BAUSTELLE}\n"
            f"Göttingen, den {tag.strftime('%d.%m.%Y')}\n\n{titel.upper()}\n\n"
            f"{zufall.choice(STANDARDABSATZ)}\n")


def erzeugen(ziel: Path) -> dict:
    zufall = random.Random(SEED)
    ziel.mkdir(parents=True, exist_ok=True)
    for alt in ziel.glob("*.txt"):
        alt.unlink()

    routine = list(ROUTINE)
    zufall.shuffle(routine)
    dokumente = []

    for nummer in range(1, 51):
        if nummer in TRAGEND:
            titel, datum, kategorie, thema, rumpf = TRAGEND[nummer]
            tag = date.fromisoformat(datum)
            monat = _monat_aus_titel(titel, tag)
        else:
            titel, datum, absender, kategorie, thema = routine.pop()
            tag = date.fromisoformat(datum)
            monat = _monat_aus_titel(titel, tag)
            rumpf = _routinetext(zufall, titel, tag, absender, thema, monat)

        text = _fuellen(zufall, rumpf, MINDESTZEICHEN, thema, monat)
        name = f"{nummer:02d}_{titel.lower().replace(' ', '_').replace(',', '').replace('.', '')[:40]}.txt"
        (ziel / name).write_text(text, encoding="utf-8")
        dokumente.append({"id": f"D-{nummer:03d}", "titel": titel, "dateiname": name,
                          "datum": tag.isoformat(), "kategorie": kategorie})

    akte = {
        "akte": {
            "id": "BA-2026-0044",
            "aktenzeichen": "44/26 BA",
            "bezeichnung": f"{BAUHERRIN} ./. {UNTERNEHMEN} – Werkmängel",
            "rechtsgebiet": "Bau- und Architektenrecht",
            "sachbearbeiter": "RA Dr. Weber",
            "status": "offen",
        },
        "dokumente": dokumente,
        "beteiligte": [
            {"id": "B-41", "name": BAUHERRIN, "rolle": "Mandantin, Bauherrin"},
            {"id": "B-42", "name": UNTERNEHMEN, "rolle": "Gegnerin, Werkunternehmerin"},
            {"id": "B-43", "name": GESCHAEFTSFUEHRER, "rolle": "Geschäftsführer der Gegnerin"},
            {"id": "B-44", "name": POLIER, "rolle": "Zeuge der Gegenseite"},
            {"id": "B-45", "name": ARCHITEKT, "rolle": "Bauleitung"},
            {"id": "B-46", "name": GUTACHTER, "rolle": "Sachverständiger"},
            {"id": "B-47", "name": GEGENANWALT, "rolle": "Gegenanwälte"},
            {"id": "B-48", "name": SUBUNTERNEHMER, "rolle": "Subunternehmer der Gegnerin"},
            {"id": "B-49", "name": EIGENE_KANZLEI, "rolle": "Prozessbevollmächtigte der Mandantin"},
            {"id": "B-50", "name": FACHFIRMA, "rolle": "Fachfirma, Angebot Ersatzvornahme"},
        ],
        "fristen": [
            {"id": "F-41", "bezeichnung": "Stellungnahme zum Ergänzungsgutachten",
             "datum": "2026-09-30", "erledigt": False},
        ],
    }
    (ziel / "akte.json").write_text(json.dumps(akte, ensure_ascii=False, indent=2), encoding="utf-8")
    return akte


if __name__ == "__main__":
    ordner = Path(sys.argv[1] if len(sys.argv) > 1 else "testdaten/grosse-akte/BA-2026-0044")
    akte = erzeugen(ordner)
    zeichen = sum(len((ordner / d["dateiname"]).read_text(encoding="utf-8"))
                  for d in akte["dokumente"])
    kuerzeste = min(len((ordner / d["dateiname"]).read_text(encoding="utf-8"))
                    for d in akte["dokumente"])
    print(f"{len(akte['dokumente'])} Dokumente, {zeichen:,} Zeichen".replace(",", "."))
    print(f"kürzestes Dokument: {kuerzeste:,} Zeichen (~{kuerzeste // 1750} Seiten)".replace(",", "."))
    print(f"Grenze je Aufruf: 160.000 Zeichen – das ist das {zeichen / 160_000:.1f}-fache")
