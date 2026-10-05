# Fassungen

Welche Fassung was kann, und wie man zu einer früheren zurückkehrt.

Die Nummer steht in `pyproject.toml` und in `jusperfect/__init__.py`; die
Oberfläche zeigt sie unter **Mehr → Nachweis**.

---

## 1.0 · 10. September 2026

Die erste Fassung, die in der Kanzlei an einer echten AWS-Verbindung gelaufen
ist und deren Ergebnisse an einer Testakte mit bekannter Auflösung geprüft
wurden. **Der Rückfallpunkt.**

### Was sie kann

**Belegpflicht, maschinell geprüft.** Jede Aussage trägt eine
Passagenkennung; was auf keine tatsächlich mitgeschickte Passage zeigt, wird
entfernt statt markiert. Der Klick auf eine Fundstelle markiert den Abschnitt
bernsteinfarben und schaltet dafür auf das richtige Dokument um.

**Fristen werden erkannt, nie berechnet.** Die Regel steht nicht nur im
Auftragstext, sondern im Code: Ein Datum, das in keiner Passage vorkommt und
in einem Fristsatz steht, wird durch den Verweis auf den Fristenkalender in
jur|nodes ersetzt. Erkennungsfehler aus Scans (`3O.09.2026`) gelten dabei als
belegt; Daten aus dem Fristenkalender ebenfalls.

**Aktengedächtnis** mit fortschreibbarer Chronologie, Übersicht und Explorer,
der zeigt, was fehlt. Lokal für die Testakten, verschlüsselt in AWS für den
Kanzleibetrieb.

**Chronologie, die aufgeräumt wird.** Abgeschriebener Dokumenttext,
angefangene Sätze und Doppelungen fallen heraus; Gestrichenes wird gezählt und
genannt.

**Zu große Akte: Abbruch statt Kürzung.** Passt die Akte nicht in einen
Aufruf, gibt es kein Ergebnis, sondern eine Meldung mit Zahlen und zwei
Auswegen. Eine Analyse über die halbe Akte sieht aus wie eine über die ganze.

**Rückgängig** für die beiden Handgriffe, die etwas wegnehmen, mit Strg+Z.
**Suche im Explorer** über beide Spalten; „alle →" nimmt nur die Sichtbaren.
**Textsatz** für Modellantworten statt roher Rauten und Sternchen.

### Was sie nicht kann

- **Akten über etwa 80 Seiten.** Eine normale Kanzleiakte (50 Dokumente)
  überschreitet das um das Zwei- bis Vierfache. Das ist der Gegenstand von 2.0.
- **jur|nodes anbinden.** Läuft gegen Testakten (`fixture`); der HTTP-Adapter
  ist nie gegen die echte Anlage gelaufen.
- **Scans kenntlich machen.** Erkennungsfehler wandern ungebremst in die
  Analyse und tragen dort eine Fundstelle.

### Geprüft

422 Tests. An der Testakte 115/26 AR: vier der fünf eingebauten Widersprüche
gefunden, die Klagefrist nicht gerechnet, kein erfundener Beteiligter.
Drei Prüfsteine liegen bei: 115/26 AR (klein), 44/26 BA (50 Dokumente zu zehn
Seiten), 031/26 SC (Scans mit Erkennungsfehlern und einem Gegnerschreiben, das
dem Programm Anweisungen erteilt).

---

## 2.0.dev · in Arbeit

Dies ist der Arbeitszweig. Die Oberfläche zeigt unter **Mehr → Nachweis**
`2.0.0.dev` — daran erkennen Sie, dass Sie nicht auf der geprüften Fassung
arbeiten.

Das Ziel: **große Akten.** Abschnittsweises Lesen, das ins Aktengedächtnis
verdichtet, und ein abschließender Durchgang über das Verdichtete, der
Widersprüche über die ganze Akte findet. Messlatte ist die Akte 44/26 BA: alle
fünf eingebauten Funde, obwohl sie 18 bis 36 Dokumente auseinanderliegen und
eine Portion nur neun fasst.

Danach, nach Nutzen geordnet: Scans kenntlich machen · Namensvarianten
zusammenführen · Anweisungen in Dokumenten anmerken · Aktengedächtnis in AWS ·
Zahlen in die Forderungen.

---

## Zu einer früheren Fassung zurück

**Aus dem ZIP.** Jede Fassung liegt als eigenes ZIP vor
(`jusperfect-1.0.zip`). Den Programmordner umbenennen, das ZIP auspacken,
den Inhalt an die alte Stelle legen. Zugangsschlüssel und Umgebungsvariablen
bleiben unberührt — sie liegen außerhalb des Programmordners.

**Aus dem Verzeichnis.** Jede Fassung hat einen eigenen Zweig:

```
git branch -a                 # welche Fassungen es gibt
git checkout fassung-1.0      # zu einer Fassung
git checkout 2.0              # zurück zur Arbeit
```

Auf GitHub (`JosefBlack/jusperfect-`) stehen:

| Zweig | |
|---|---|
| `fassung-1.0` | die geprüfte Fassung, unverändert |
| `main` | zurzeit derselbe Stand wie `fassung-1.0` |
| `2.0` | der Arbeitszweig |

Warum Zweige und keine Marken: Der Netzweg dieser Arbeitsumgebung lässt keine
Tags durch. Für den Zweck — ein dauerhafter Zeiger auf einen bestimmten Stand —
tut ein Zweig dasselbe.

**Aus dem Bündel.** `jusperfect-verzeichnis.bundle` enthält die vollständige
Geschichte in einer Datei. Daraus lässt sich das Verzeichnis überall neu
aufbauen:

```
git clone jusperfect-verzeichnis.bundle jusperfect
```

Das ist die Sicherung, die auch dann trägt, wenn weder Rechner noch GitHub
verfügbar sind.

### Das Aktengedächtnis wandert nicht mit

Ein Rücksprung tauscht das Programm, nicht die Daten. Das lokale Gedächtnis
liegt in `.jusperfect-gedaechtnis` im Programmordner — wer den Ordner
austauscht, sollte es mitnehmen. Das AWS-Gedächtnis liegt im eigenen Konto und
ist von einem Rücksprung nicht betroffen.
