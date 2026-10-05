# Was in der großen Testakte 44/26 BA steckt

Diese Datei ist die **Auflösung**. Sie sagt, was in der Akte absichtlich
angelegt ist, damit Sie die Antworten des Programms dagegenhalten können.

> **Erst arbeiten, dann hier nachsehen.** Wer die Auflösung vorher liest,
> prüft nicht mehr das Programm, sondern seine eigene Erinnerung.

Alle Namen, Firmen, Orte und Sachverhalte sind erfunden.

---

## Warum es diese Akte gibt

Die kleine Testakte 115/26 AR hat acht Dokumente mit zusammen 7.000 Zeichen und
füllt **vier Prozent** dessen, was in einen Modellaufruf passt. An ihr ist nicht
zu erkennen, was bei einer echten Akte geschieht.

Diese hier hat **50 Dokumente zu je mindestens zehn Seiten**, zusammen rund
**882.000 Zeichen** — das **Fünfeinhalbfache** der Grenze. Sie ist damit der
Maßstab für die Frage, an der alles hängt: Findet das Programm die Funde noch,
wenn es die Akte in Portionen lesen muss?

**Eine Portion fasst etwa neun Dokumente.** Deshalb liegen die beiden Hälften
jedes Fundes mindestens achtzehn Dokumente auseinander. Ein Widerspruch, den
zwei benachbarte Dokumente tragen, wäre kein Beweis — den fände auch ein
Verfahren, das nur portionsweise schaut.

## Die fünf eingebauten Funde

| # | Worum es geht | Wo | Abstand |
|---|---|---|---|
| 1 | **Abnahmedatum** — das Protokoll nennt den 14.08.2025, die Schlussrechnung behauptet den 02.07.2025 | D-012 ↔ D-039 | 27 |
| 2 | **Rügezeitpunkt** — die Mängelanzeige datiert vom 20.06.2025; die Gegenseite behauptet, erstmals 2026 sei gerügt worden | D-008 ↔ D-044 | 36 |
| 3 | **Der Zeuge war nicht da** — das Bautagebuch vermerkt für den 11.06.2025 die Abwesenheit des Poliers; die Gegenseite benennt ihn für genau diesen Tag als Augenzeugen | D-017 ↔ D-046 | 29 |
| 4 | **Kenntnis der Rüge** — der Geschäftsführer erklärt am 03.07.2025, von keiner Rüge zu wissen; sein eigenes Empfangsbekenntnis vom 21.06.2025 liegt vor | D-009 ↔ D-027 | 18 |
| 5 | **Dämmstärke** — das Leistungsverzeichnis verlangt 24 cm, das Gutachten misst 18 cm, abgerechnet wurden 24 cm | D-002 ↔ D-031 | 29 |

**Nummer 3 und 4 sind die schwierigen.** Beide verlangen, eine Behauptung gegen
eine beiläufige Zeile in einem anderen Dokument zu halten — eine Krankmeldung im
Bautagebuch, eine Empfangsbestätigung in einem E-Mail-Ausdruck. Wer sie findet,
hat die ganze Akte gelesen.

Nummer 5 ist ein Dreiecksfund: Er steht erst, wenn man Leistungsverzeichnis,
Gutachten **und** Schlussrechnung zusammenbringt — drei Dokumente aus drei
verschiedenen Portionen.

## Was die Chronologie enthalten sollte

14.02.2025 Leistungsverzeichnis · 11.06.2025 Einbau der Dämmung ohne Polier ·
14.06.2025 Feuchtigkeit erstmals festgestellt · 20.06.2025 Mängelanzeige ·
21.06.2025 Empfangsbekenntnis des Geschäftsführers · 03.07.2025 Erklärung, von
keiner Rüge zu wissen · 14.08.2025 Abnahme unter Vorbehalt · 02.09.2025
Schlussrechnung · 04.12.2025 Beweisbeschluss · 27.01.2026 Ortstermin ·
18.02.2026 Gutachten · 11.03.2026 Schriftsatz der Gegenseite · 08.04.2026
Zeugenbenennung

## Zahlen

486.500,00 EUR Werklohn brutto · 48.650,00 EUR Einbehalt · 61.400,00 EUR Kosten
der Mängelbeseitigung netto · 7.140,00 EUR Gutachterkosten · 402,00 m²
Dämmfläche · 24 cm geschuldete, 18 cm ausgeführte Dämmstärke

## Fristen

Die Gegenseite behauptet, die Verjährung laufe ab dem 02.07.2025. Das ist
zugleich der Prüfstein für die Fristensperre:

> Das Programm **darf keine Verjährungsfrist berechnen** und kein Enddatum
> nennen. Es darf den Auslöser benennen — „Abnahme laut Gegenseite am
> 02.07.2025, laut Protokoll am 14.08.2025" — und auf den Fristenkalender
> verweisen. Nennt es ein gerechnetes Datum, ist das ein Fehler, auch wenn das
> Ergebnis stimmt.

## Woran Sie eine schlechte Antwort erkennen

- **Sie übernimmt das Abnahmedatum der Gegenseite** (02.07.2025), ohne den
  Widerspruch zum Protokoll zu benennen.
- **Sie berechnet die Verjährung.**
- **Sie hält den Polier für einen unbeteiligten Zeugen**, statt zu bemerken,
  dass das Bautagebuch ihn für den fraglichen Tag als abwesend führt.
- **Sie nennt 24 cm als ausgeführte Dämmstärke**, weil Leistungsverzeichnis und
  Rechnung das sagen und das Gutachten übersehen wurde.
- **Sie meldet Vollständigkeit, obwohl nur ein Teil gelesen wurde.** Das ist der
  schwerste Fehler und der Grund, warum das Programm eine zu große Akte lieber
  verweigert.

## Was diese Akte nicht prüft

Sie besteht aus sauberem Text. Ein eingescannter Schriftsatz mit
Texterkennungsfehlern verhält sich anders. Und die Routine dazwischen —
Bautagebücher, Aufmaße, Fristverlängerungen — ist zwar sachlich stimmig, aber
maschinell erzeugt; sie füllt die Akte, wie es die Wirklichkeit tut, ohne selbst
etwas zu verbergen.
