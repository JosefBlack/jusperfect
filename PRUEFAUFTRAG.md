# Prüfauftrag für eine zweite Meinung

**Stand: 05.10.2026.** Diese Datei liegt dem Prüfpaket bei. Sie sagt, was das
Programm ist, worauf zu sehen ist und was bereits bekannt ist — damit die
Prüfung nicht dort anfängt, wo schon jemand war.

---

## Worum es geht

**jusperfect** ist eine KI-Schicht über der Aktenverwaltung **jur|nodes** für
eine Anwaltskanzlei mit zwei Anwälten. Sie liest Dokumente einer Mandatsakte,
legt ausgewählte Passagen einem Sprachmodell (Claude über AWS Bedrock,
Frankfurt) vor und gibt das Ergebnis dem Bearbeiter zur Prüfung.

**Der Gegenstand ist Mandatsgut.** Es gilt die anwaltliche Verschwiegenheit
(§ 43a BRAO, § 203 StGB) und die DSGVO. Das Programm läuft seit dem 23.09.2026
mit den echten Akten der Kanzlei.

| | |
|---|---|
| Programm | 74 Python-Dateien, rund 15.900 Zeilen |
| Prüfungen | 99 Dateien, rund 20.700 Zeilen, **1625 Prüfungen** |
| Oberfläche | eine Seite, `jusperfect/static/` |
| Sprache im Quelltext | Deutsch — Bezeichner, Kommentare, Fehlertexte |

Ausführen der Prüfungen:

```
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```

---

## Die Zusagen, die das Programm gibt

**Das ist der Maßstab.** Eine Lücke in einer dieser Zusagen ist ein Befund
erster Ordnung; alles andere ist nachrangig.

| Zusage | Wo sie steht |
|---|---|
| **Belegpflicht, fail closed.** Eine Aussage ohne Verweis auf eine mitgeschickte Passage wird **entfernt**, nicht markiert | `jusperfect/services/belegpflicht.py` |
| **Fristensperre.** Fristen werden erkannt, nie berechnet — auch wenn die Akte dazu auffordert | `jusperfect/services/fristen.py` |
| **Ein einziger Ausgang.** Genau eine Stelle im Programm führt zum Modell, und jeder Aufruf hinterlässt einen Nachweis | `jusperfect/services/ausgang.py` |
| **Kein Akteninhalt im Protokoll.** Technisch erzwungen: Inhaltsfelder werden aktiv zurückgewiesen | `jusperfect/security/protokoll.py` |
| **Zurückschreiben nur mit Freigabe**, gebunden an Nutzer, Akte, Textprüfsumme und Vorgang (HMAC) | `jusperfect/security/approval.py` |
| **Fail closed beim Start.** Mitschrift bei AWS an, kein Schutzgeländer, kein Schlüssel, Region außerhalb der EU → das Programm startet nicht | `jusperfect/config.py` |
| **Das Modell sieht keine Kennungen.** Keine Dateinamen, Dokument-, Nutzer- oder Sitzungskennungen | `jusperfect/providers/bedrock.py` |
| **Löschung folgt dem Aktenstatus**, nie dem Zeitablauf. Eine Bearbeitungspause löscht nie etwas | `jusperfect/services/abschluss.py`, `SICHERHEIT.md` |

---

## Worauf besonders zu sehen ist

In dieser Reihenfolge — oben steht, was am meisten schadet, wenn es falsch ist.

1. **Die Sicherheitsgrenze.** Kommt auf irgendeinem Weg Akteninhalt dorthin,
   wo keiner sein darf — in ein Protokoll, in eine Fehlermeldung, in eine
   Befunddatei, in einen Dateinamen? Besonders: Fehlerpfade und Ausnahmen.
2. **Die Belegpflicht.** Lässt sie sich umgehen? Gibt es einen Weg, auf dem
   eine unbelegte Aussage doch bis zum Bearbeiter kommt?
3. **Die Freigabe.** Lässt sich etwas zurückschreiben, das der Bearbeiter so
   nicht gesehen hat? Die Bindung ist ein HMAC über Nutzer, Akte, Text und
   Vorgang.
4. **Das Aktengedächtnis** (`jusperfect/services/gedaechtnis.py`,
   `jusperfect/gedaechtnis/`). Es ist der einzige Ort, an dem dauerhaft
   Akteninhalt außerhalb von jur|nodes liegt. Besonders: das gezielte Entfernen
   einzelner Einträge — fällt wirklich alles mit, was auf einem entfernten
   Dokument beruht?
5. **Der jur|nodes-Adapter** (`jusperfect/jurnodes/http_adapter.py`). Kann eine
   Antwort des Servers dazu führen, dass Inhalt einer **fremden** Akte in die
   Arbeitsakte gelangt? Siehe „Bekannt und offen", Punkt 1.
6. **Die Einstellungen** (`jusperfect/config.py`). Gibt es eine Kombination, in
   der das Programm mit echten Akten startet, obwohl eine Zusage nicht gehalten
   ist?
7. **Die Prüfungen selbst.** Prüft eine Prüfung den Wortlaut statt der Zusage?
   Davon sind an einem einzigen Tag fünf gefunden worden — eine Prüfung, die
   anders misst als der Betrieb, misst etwas anderes als den Betrieb.

---

## Bekannt und offen — bitte nicht als Fund melden

1. **Der Korrespondenzordner von jur|nodes.** Das Feld
   `correspondenceFolderId` liefert Schriftstücke, die nicht zu der abgefragten
   Akte gehören (an drei Akten gemessen, in einer 17 von 55). Das Feld wird
   seit dem 05.10.2026 **nicht mehr gelesen**. Die Vermutung: Korrespondenz und
   Vermerke liegen in der E-Akte, die über die Schnittstelle nicht erreichbar
   ist. Anfrage an den Hersteller läuft.
2. **Die Regionen des Schutzgeländers.** Wohin das EU-Inferenzprofil und
   `eu.guardrail.v1:0` **intern** verteilen, ist bei AWS erfragt und noch nicht
   beantwortet.
3. **Die Rechtsdokumentation.** `DSFA-ENTWURF.md` und
   `DATENSCHUTZHINWEISE-ENTWURF.md` sind Entwürfe; 26 Stellen sind als
   `[KANZLEI n]` offen gelassen und von der Kanzlei zu bewerten, nicht von der
   Entwicklung.
4. **Die Vermerke** aus jur|nodes werden nicht gelesen — siehe Punkt 1.
5. **Zugriff je Bearbeiter.** Technisch vorhanden, in der Kanzlei nicht
   eingeschaltet: Alle eingetragenen Nutzer sehen alle Akten. Bewusst so, und
   offen.

---

## Vier Dinge, die bewusst so sind

Sie sehen wie Mängel aus und sind keine. Wer sie trotzdem für falsch hält,
soll das sagen — aber bitte mit Begründung, nicht als Routinehinweis.

| Scheint falsch | Ist Absicht |
|---|---|
| Der Quelltext ist auf **Deutsch** | Die Kanzlei liest mit. Fehlertexte, die ein Anwalt versteht, sind hier ein Sicherheitsmerkmal |
| Kommentare sind **lang** und erzählen Vorgeschichte | Jeder nennt einen Fehler, der einmal Geld oder einen Tag gekostet hat. Sie sind das Gedächtnis des Projekts |
| Die **Inhaltsfilter** des Schutzgeländers sind **aus** | Gewalt, Sexuelles, Beleidigung sind in einer Kanzlei der Gegenstand der Arbeit, nicht der Missbrauch |
| Das Programm **verweigert** lieber, als zu schätzen | „Kein belastbarer Beleg" ist eine zulässige Antwort. Eine kürzere Antwort ist besser als eine erfundene |

---

## Was in diesem Paket verändert wurde

Zwei Angaben sind ersetzt, weil sie zur Infrastruktur der Kanzlei gehören und
für eine Prüfung des Programms nicht gebraucht werden:

| Ersetzt durch | War |
|---|---|
| `KANZLEI-EIMER` | der Name des S3-Ablageorts |
| `KMS-SCHLUESSEL-KENNUNG` | die Kennung des Verschlüsselungsschlüssels |

**Sonst ist nichts verändert.** Die Prüfungen laufen auch im Paket grün.

**Keine Zugangsdaten im Bestand.** Die vier Zugangswerte (jur|nodes-Adresse,
Benutzer, Token; AWS-Schlüssel) liegen im Windows-Konto des jeweiligen
Rechners, nie im Programmordner. Was wie ein Schlüssel aussieht, ist ein
Prüfwert — `AKIAIOSFODNN7EXAMPLE` stammt aus der Dokumentation von AWS.

**Enthalten sind erfundene Testakten** (`testdaten/`). Sie sind erfunden, auch
wo sie echt klingen. Echte Aktenzeichen kommen in Befundbeschreibungen vor
(etwa `X-100-2026`); sie benennen einen Vorgang, nicht seinen Inhalt.

---

## Was eine nützliche Antwort enthält

- **Datei und Zeile.** „Die Fehlerbehandlung ist schwach" hilft nicht.
- **Den Weg dorthin.** Welche Eingabe, welcher Zustand, welche Reihenfolge?
- **Warum es schadet.** Und für wen — Mandant, Kanzlei, Dritter.
- **Eine Einschätzung**, wie sicher Sie sind. Eine Vermutung ist willkommen,
  wenn sie als Vermutung gekennzeichnet ist.

Und, ausdrücklich erbeten: **Wo halten Sie eine Entscheidung für falsch, die
hier als Absicht dokumentiert ist?** Die Begründungen stehen in `KONZEPT.md`,
`SICHERHEIT.md` und in den Kommentaren. Sie sind nicht unantastbar.

---

## Zum Nachlesen

| Datei | Inhalt |
|---|---|
| `UEBERGABE.md` | Stand, tragende Entscheidungen, Konventionen — **hier anfangen** |
| `SICHERHEIT.md` | die 16 Grundsätze und das Löschkonzept |
| `KONZEPT.md` | warum das Programm so gebaut ist |
| `MORGEN.md` | die Arbeitsliste mit allen Begründungen |
| `ANLEITUNG.md` | die Bedienung, für den Anwender geschrieben |
| `infra/IAM.md` | die AWS-Zugriffsrichtlinie im Wortlaut |
