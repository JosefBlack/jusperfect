# Prüfauftrag für eine zweite Meinung

**Stand: 05.10.2026.** Diese Datei liegt dem Prüfpaket bei. Sie sagt, was das
Programm ist, worauf zu sehen ist und was bereits bekannt ist — damit die
Prüfung nicht dort anfängt, wo schon jemand war.

**Zweierlei wird erbeten, und beides zählt:**

1. **Eine Prüfung** des Programms — die Abschnitte „Die Zusagen" und „Worauf
   besonders zu sehen ist".
2. **Antworten auf fünf offene Fragen** — der Abschnitt „Offene Fragen". Zwei
   davon sind Wissensfragen (jur|nodes, AWS), drei sind Urteilsfragen. Wer nur
   eines von beidem leisten kann, leistet gern nur das.

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

## Bekannt und offen — nicht als Fund melden, aber gern als Antwort

Diese fünf Punkte sind bekannt. Sie noch einmal zu melden hilft nicht.
**Etwas dazu zu sagen schon** — die Fragen stehen weiter unten unter
„Offene Fragen".

1. **Der Korrespondenzordner — aufgeklärt am 05.10.2026.** Es war ein Fehler
   im Programm: zwei getrennte Ordnerbäume in jur|nodes, und die Nummer des
   einen wurde am Pfad des anderen abgefragt. Der falsche Weg ist abgeschaltet,
   der richtige belegt und in der Probe gemessen, aber **noch nicht im
   Betrieb**. Einzelheiten in `schnittstelle/README.md`.
2. **Die Regionen des Schutzgeländers.** Wohin das EU-Inferenzprofil und
   `eu.guardrail.v1:0` **intern** verteilen, ist bei AWS erfragt und noch nicht
   beantwortet.
3. **Die Rechtsdokumentation.** `DSFA-ENTWURF.md` und
   `DATENSCHUTZHINWEISE-ENTWURF.md` sind Entwürfe; 26 Stellen sind als
   `[KANZLEI n]` offen gelassen und von der Kanzlei zu bewerten, nicht von der
   Entwicklung.
4. **Die Vermerke** aus jur|nodes werden noch nicht gelesen. Der Weg steht
   seit dem 05.10.2026 fest — siehe Punkt 1.
5. **Zugriff je Bearbeiter.** Technisch vorhanden, in der Kanzlei nicht
   eingeschaltet: Alle eingetragenen Nutzer sehen alle Akten. Bewusst so, und
   offen.

---

## Offene Fragen, zu denen eine zweite Meinung willkommen ist

**Zur Behandlung der Antworten, vorab.** Was hier zurückkommt, ist eine zweite
Meinung und keine Auskunft aus der Quelle. Für die Fragen 1 und 2 gilt
ausdrücklich: Eine Antwort von Ihnen ersetzt **nicht** die Antwort des
Herstellers bzw. von AWS. Sie wird als Hinweis behandelt, nicht als Beleg —
dieselbe Regel, nach der eine Zusammenfassung aus dem Netz am 01.10.2026 schon
einmal als „ausdrücklich nicht gesichert" in die Unterlage gegangen ist.

**Und: Bitte nicht raten.** „Weiß ich nicht" ist hier eine nützliche Antwort.
Ein erfundener Schnittstellenpfad kostet einen Prüflauf an echten Mandatsakten.

---

### ~~Frage 1 — Wie liest man die E-Akte von jur|nodes?~~ — **beantwortet**

Am Abend des 05.10.2026 hat die Kanzlei die OpenAPI-Beschreibung des
Herstellers geliefert (Fassung 1.0.2, 85 Pfade). Sie liegt im Paket unter
`schnittstelle/jurnodes-api-1.0.2.json`, die Auswertung in
`schnittstelle/README.md`. Kurz:

* Die E-Akte heißt **Korrespondenz**: `POST /correspondence/search`.
* Die **Vermerke** sind Korrespondenzen vom Typ `note`, mit der Nummer in
  `referenceNote`; **Telefonvermerke** tragen `type: "phonecall"`.
* `GET /record/note` braucht **zwei** Pflichtparameter — `id` **und**
  `record`. Daran ist die Suche vier Wochen gescheitert.
* **Der Befund zum Korrespondenzordner war ein Fehler im Programm**, kein
  Verhalten des Herstellers: zwei getrennte Ordnerbäume, eine Nummer aus dem
  einen am Pfad des anderen abgefragt.

**Was hier trotzdem willkommen ist:** ein Blick auf
`schnittstelle/README.md` und auf `jusperfect/jurnodestest.py::_korrespondenz_lesen`
— ist die Auswertung richtig gelesen? Besonders: Reicht
`POST /correspondence/search` wirklich für **alle** Korrespondenz, oder braucht
es zusätzlich den Ordnerbaum über `/correspondence/folder`?

---

### Frage 2 — In welche Regionen verteilt das EU-Inferenzprofil von AWS Bedrock?

Das Programm ruft Claude über **AWS Bedrock** in Frankfurt (`eu-central-1`)
auf, und zwar über das **europäische Inferenzprofil**: Die Modellkennung trägt
den Vorsatz `eu.`, etwa `eu.anthropic.claude-opus-4-6-v1`. Dazu kommt ein
Schutzgeländer über das regionsübergreifende Profil **`eu.guardrail.v1:0`**.

AWS beschreibt das in der Konsole nur als „across Regions within your
geography" und nennt die Regionen nicht.

**Gefragt ist — namentlich, nicht „bleibt in Europa":**

1. In welche Regionen verteilt das `eu.`-Inferenzprofil für die
   Claude-Modelle?
2. Dasselbe für das Geländerprofil `eu.guardrail.v1:0`.
3. Ist in einer der beiden Mengen **`eu-central-2` (Zürich, Schweiz)** oder
   **`eu-west-2` (London, Vereinigtes Königreich)** enthalten?

**Warum Punkt 3 entscheidend ist:** Beide tragen den Vorsatz `eu-` und liegen
außerhalb der EU und des EWR. Für eine Kanzlei, deren Datenschutzunterlage
„Übermittlung in Drittländer: keine" sagt, ist das der Unterschied zwischen
einem Satz, der stimmt, und einem, der sich auf eine Buchstabenfolge stützt.
Genau daran ist am 05.10.2026 ein Fehler im Programm aufgefallen: Es prüfte auf
den Vorsatz statt auf die Regionen.

**Mit Quellenangabe, bitte** — und wenn die Angabe aus dem Gedächtnis stammt,
sagen Sie das dazu.

---

### Frage 3 — Tragen die vier Entwurfsentscheidungen?

Hier geht es nicht um Wissen, sondern um ein Urteil. Vier Entscheidungen, bei
denen eine Gegenrede nützlich wäre:

**3a · Belegpflicht: entfernen statt markieren.** Eine Aussage des Modells ohne
Verweis auf eine mitgeschickte Passage wird aus der Antwort **entfernt**. Die
Alternative wäre, sie zu markieren und stehen zu lassen. Entfernen heißt:
Der Bearbeiter sieht nicht, was das Modell gesagt hätte. Ist das die richtige
Seite des Irrtums? (`jusperfect/services/belegpflicht.py`)

**3b · Beim Entfernen eines Dokuments fällt zu viel.** Wird ein Dokument aus
dem Aktengedächtnis genommen, fallen gespeicherte Antworten und
Zeitstrahleinträge **ganz**, sobald sie es auch nur mitzitieren — auch wenn sie
sich zur Hälfte auf ein anderes Dokument stützen. Begründung: Ein Eintrag aus
zwei Quellen stünde sonst weiter da, obwohl die Hälfte seiner Grundlage fehlt.
Zu streng? (`jusperfect/services/gedaechtnis.py::dokument_vergessen`)

**3c · Die Ausschlussliste prüft den Titel, nicht den Inhalt.** Dokumente, deren
**Titel** eines von neun Wörtern trägt (Rechnung, Kostennote, RSV …), kommen
ohne Haken in die Auswahl — sie sollen nicht ins Aktengedächtnis. Eine
Rechnung, die „Schreiben vom 14.03." heißt, geht durch. Gibt es einen Weg, der
zuverlässiger ist, **ohne** den Inhalt zu deuten? (`jusperfect/static/app.js`,
`nichtVorwaehlenGrund`)

**3d · Veraltet-Erkennung über Dokumentkennungen.** Eine gespeicherte
Aktenanalyse meldet sich als veraltet, wenn die Akte heute Dokumentkennungen
enthält, die sie beim Rechnen nicht enthielt. Geänderte oder ersetzte Dokumente
mit gleicher Kennung erkennt das **nicht**. Reicht das, oder braucht es eine
Prüfsumme je Dokument — mit allem, was daran hängt?
(`jusperfect/services/gedaechtnis.py::analyse_stand`)

---

### Frage 4 — Die Rechtsdokumentation

`DSFA-ENTWURF.md` (Folgenabschätzung nach Art. 35 DSGVO) und
`DATENSCHUTZHINWEISE-ENTWURF.md` (Hinweise nach Art. 13, Mandatsklausel) sind
Entwürfe der Entwicklung. **26 Stellen sind als `[KANZLEI n]` offen gelassen**,
weil sie eine rechtliche Bewertung verlangen; sie stehen am Ende jeder Datei in
einer Liste.

**Gefragt ist nicht die Bewertung** — die trifft die Kanzlei. Gefragt ist:

1. **Fehlt ein Risiko?** Acht sind beschrieben (Abschnitt 4 des DSFA-Entwurfs).
2. **Ist eine der Maßnahmen zu optimistisch dargestellt?** Jede nennt ihren
   Nachweis im Programm — stimmt die Zuordnung?
3. **Fehlt eine Angabe, die Art. 30 oder Art. 35 verlangt?**
4. **Ist eine der offenen Stellen in Wahrheit keine** — also etwas, das die
   Entwicklung hätte beantworten können und sich zu bequem gedrückt hat?

Punkt 4 ist ernst gemeint. Eine Unterlage, die eine technische Frage als
Rechtsfrage ausgibt, schiebt Arbeit auf den Falschen.

---

### Frage 5 — Was würden Sie als Nächstes bauen?

Am Programm ist nichts offen, was das Arbeiten mit einer Akte verhindert. Die
Arbeitsliste steht in `MORGEN.md`. **Wenn Sie den Bestand gelesen haben: Was
fehlt Ihrer Meinung nach am meisten?** Gern auch etwas, das in der Liste nicht
vorkommt.

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

**Bei einem Fund:**

- **Datei und Zeile.** „Die Fehlerbehandlung ist schwach" hilft nicht.
- **Den Weg dorthin.** Welche Eingabe, welcher Zustand, welche Reihenfolge?
- **Warum es schadet.** Und für wen — Mandant, Kanzlei, Dritter.
- **Eine Einschätzung**, wie sicher Sie sind. Eine Vermutung ist willkommen,
  wenn sie als Vermutung gekennzeichnet ist.

**Bei einer Antwort auf die offenen Fragen:**

- **Woher Sie es wissen.** Dokumentation, eigene Erfahrung, Gedächtnis? Jede
  dieser drei Herkünfte ist brauchbar — aber sie werden verschieden behandelt.
- **Was Sie nicht wissen.** „Zu Frage 1 kenne ich das Produkt nicht" ist eine
  vollständige Antwort auf Frage 1 und erspart einen Prüflauf an echten Akten.
- **Bei Frage 2 die Quelle**, möglichst mit Datum. Eine Regionsliste aus dem
  Gedächtnis geht als ungesicherter Zwischenstand in die Unterlage, nicht als
  Beleg.

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
