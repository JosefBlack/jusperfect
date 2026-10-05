# Was als Nächstes zu tun ist

Stand: **05.10.2026.** Zweig `2.0`, Fassung `2.0.0.dev`.
1537 Prüfungen grün (`.venv/bin/python -m pytest -q`).
Jüngster Programmstand: `632b77e`.

---

## Der Befund vom 05.10.2026: 17 fremde Dokumente in einer Akte

**Aus der Kanzlei am 02.10.2026:** In der Arbeitsakte der Bausache X-100-2026
standen drei Schriftstücke aus einer fremden Verkehrsunfallsache. „Es ist nicht
ersichtlich, wie diese Sachen hineingekommen sind."

**Gemessen am 05.10.2026, an der echten Schnittstelle:**

| Zweig | Ordner | Dokumente | abgelegt |
|---|---|---|---|
| Dateiordner | 11142 | D1–D29 | 2026-07-30 bis 2026-09-25 |
| Dateiordner | 11162 | D30–D38 | 2026-08-05 |
| Korrespondenz | 2871 | D39 | 2023-03-22 |
| Korrespondenz | 2872 | D40–D43 | 2022-12-15 |
| Korrespondenz | 2873 | D44–D46 | 2022-12-15 |
| Korrespondenz | 2883 | **D47–D49** | 2022-12-15 bis 2023-01-17 |
| Korrespondenz | 2952 | D50–D55 | 2022-12-16 bis 2022-12-30 |

Die Akte wurde am **30.07.2026** angelegt (`creationDate`). Ihr
Korrespondenzordner wurde **dreieinhalb Jahre früher** befüllt.

**Nicht drei Dokumente sind fremd, sondern der ganze Korrespondenzzweig —
17 von 55.** Die drei, die aufgefallen sind, waren der Inhalt eines einzigen
Unterordners.

**Das Programm hat richtig gearbeitet.** `GET /record` nennt für diese Akte
`correspondenceFolderId 2871`; die vier Unterordner führen `parentFolder 2871`.
Der Durchlauf hat die Akte an keiner Stelle verlassen — das prüft
`_ordnerbaum` seitdem ausdrücklich. **Der Befund gehört in die Ablage der
Kanzlei und zum Hersteller, nicht in den Quelltext.**

**Hinzu kommt:** In der Oberfläche von jur|nodes sind diese Schriftstücke unter
dieser Akte **nicht zu finden**. Die Schnittstelle liefert sie, die Oberfläche
zeigt sie nicht.

**Offen — Kanzlei:** Die Anfrage an den Hersteller ist fertig formuliert
(Ordnerzuordnung und Vermerke in einem Text) und abzuschicken. Bis zur Klärung
**diese Akte nicht in jusperfect öffnen**: Das Aktengedächtnis arbeitet seit
dem 05.10.2026, und die 17 fremden Dokumente würden dauerhaft abgelegt.

**Was der Weg dorthin gekostet hat — drei eigene Fehler, alle derselben Form:**

1. Die Probe suchte nach dem Elternordner unter einem Feldnamen, den es nicht
   gibt (`parentFolderId` statt `parentFolder`). Sie meldete nichts — und
   Schweigen liest sich wie Entwarnung.
2. Sie zählte in einer anderen Reihenfolge als der Betrieb. Bei dieser Akte
   glichen sich die Unterschiede zufällig aus.
3. Sie schnitt vom Anlagedatum zehn Zeichen ab (`Thu Jul 30`) und verglich
   Zeichen gegen Zeichen. Jede Ziffer steht vor jedem Buchstaben, also galt
   **jeder** Ordner als älter als die Akte — ein Fehlalarm, der auch den
   Dateiordner der Akte traf.

Dreimal dasselbe: **Eine Probe, die anders misst als der Betrieb, misst etwas
anderes als den Betrieb.** Der dritte Fehler hat sich selbst gefangen, weil
seit dem zweiten gilt: kein Urteil ohne verstandenen Maßstab.

---

## Der 29.09.2026 — in dieser Reihenfolge

**Stand nach dem 01.10.2026, nachts: 1290 Prüfungen grün, Programmstand
`cab1c7d` — auch der Prüflauf auf GitHub ist grün, erstmals seit dem
28.09.2026. Sieben von zehn Aufgaben erledigt (1, 4, 5, 6, 7, 8, 10);
Aufgabe 2 wartet auf den Hersteller.**

1. ~~**Prüfbogenlauf (Aufgabe 6), rund 3 €.**~~ — **erledigt 01.10.2026.**
   Gelaufen um 19:24 Uhr für 3,10 €: **13 von 13 Tagen**, 5 von 5 Funden, 5 von
   5 Zahlen, Fristensperre hält. Die fünf Tage sind am echten Modell belegt.
   Einzelheiten unter Aufgabe 6.
2. **Die Vermerke (Aufgabe 2).** `id` ist der richtige Parametername — der
   Server will eine **Zahl**. Zu bauen: Zahlen durchprobieren, und die
   Feldnamen **innerhalb** der Trefferlisten zeigen (heute zeigt die Probe nur
   die Hülle: `amountTotal`, `pagesTotal`, `elements`). Dort steckt vermutlich
   die Zahl.
3. **Eine echte Akte**, die der Nutzer gut kennt. Die einzige Probe, die zählt.

**Zwei Dinge, die zu prüfen waren — beide am 01.10.2026 bearbeitet:**

- ~~Benutzt das Programm `recordStatus` für die Löschfristen?~~ **Ja, und
  knapper als gedacht.** `_status_uebersetzen` kennt genau zwei Wörter,
  `archiviert` und `archived`; **jedes andere wird stillschweigend zu
  „laufend"**. Eine Akte, die in jur|nodes anders abgeschlossen heißt, wird nie
  abschlussreif — und der Befund `status_unbekannt`, der einen Menschen
  einschalten soll, kann auf diesem Weg gar nicht entstehen. Die
  ungefährliche Richtung immerhin: Es wird nichts gelöscht, was bleiben soll.
  **Welche Wörter der Server wirklich führt, zeigt die Probe seit dem
  01.10.2026 an** — ein Lauf, und die Übersetzung lässt sich berichtigen. Für
  Ziffer 6.2 gilt bis dahin: nicht mehr versprechen, als zwei Wörter hergeben.
- ~~Die Regionen, auf die `eu.guardrail.v1:0` verteilt.~~ **Ein Zwischenstand
  steht in `DSFA-ANGABEN.md`, ausdrücklich als ungesichert gekennzeichnet.**
  Die Seiten von AWS sind aus der Entwicklungsumgebung gesperrt; gelesen wurde
  eine Zusammenfassung. Sie nennt Irland, Frankfurt, Paris, Mailand, Spanien,
  Stockholm — und **Zürich**, also die Schweiz. Für den Drittlandbezug wäre das
  erheblich, und genau deshalb darf es nicht aus zweiter Hand übernommen
  werden. **Beim AWS-Support zu erfragen**, ausdrücklich für das
  Geländer-Profil und für die drei benutzten Modellkennungen.

**Nachtrag 28.09.2026:** Aufgabe 10 ist dazugekommen — der Zugang zur
jur|nodes-Schnittstelle auf einem neuen Rechner. Sie ist noch am selben Tag
erledigt worden.

Diese Datei ist eine Arbeitsliste, keine Anleitung zur Bedienung. Wie das
Programm bedient wird, steht in `ANLEITUNG.md` und in `HILFE.html`.

**Der Informationsstand steht in `UEBERGABE.md`.**

---

## Der Stand in drei Sätzen

Das Programm arbeitet **mit den echten Akten der Kanzlei** über die
REST-Schnittstelle von jur|nodes. Am 25.09.2026 wurde eine echte Akte
geöffnet, 38 von 55 Dokumenten gelesen und beantwortet, zu gemessenen
**22 Cent**. Die 17 fehlenden waren gescannte PDFs ohne Textschicht; **seit
dem 02.10.2026 liest das Programm auch sie** — die Berechtigung in AWS steht,
und `TEXTERKENNUNG-PRUEFEN.bat` hat es in der Kanzlei bestätigt. Was jetzt
fehlt, ist der Lauf an einer echten Akte, die der Nutzer gut kennt.

---

## Für die neue Sitzung: das Wichtigste zuerst

**Wer hier weiterarbeitet, liest zuerst den Abschnitt „Die Lehren des
25.09.2026" weiter unten.** Der Tag hat sechs Stunden gekostet, und keine
einzige davon an dem, wonach gesucht wurde.

### Der Nutzer

Rechtsanwalt, **kein Programmierer**. Antworten kurz, klar gegliedert, auf
Deutsch, ohne Fachjargon. Was er tun soll, gehört als nummerierte Schritte
hin — nicht als Fließtext.

### Wie eine neue Fassung in die Kanzlei kommt

```
git archive --format=zip --prefix=jusperfect-<TT.MM.JJJJ>/ HEAD -o <Ziel>.zip
```

**`--prefix` ist nicht wahlfrei.** Ohne ihn liegen rund 200 Dateien lose in
der ZIP und landen beim Auspacken mitten im Downloadordner. Am 25.09. ist
das dreimal passiert, bis die Kanzlei fragte: „warum gibt es keinen
überordner der jusperfect heißt".

`FASSUNG.txt` trägt `$Format:%H %cs$` und wird von `git archive` beim
Auspacken gefüllt. **Niemals im Arbeitsbaum ausfüllen** — damit nimmt man ihr
genau die Automatik, derentwegen sie da ist. Der Prüfbogen meldet es.

---

## Offene Aufgaben

### 1. ~~Texterkennung für gescannte PDFs~~ — **erledigt 02.10.2026**

**Eingeschaltet auf ausdrückliche Anweisung der Kanzlei** („Jetzt die
Texterkennung einschalten"). `START-JURNODES.bat` trägt `JUSPERFECT_OCR=textract`;
die Zugriffsrichtlinie in AWS trägt `TexterkennungFuerScans` — von der Kanzlei
am 02.10.2026 eingesetzt und gespeichert.

**Offen bleibt nur die Probe an einer echten Akte.** Dafür gibt es seit dem
02.10.2026 `TEXTERKENNUNG-PRUEFEN.bat`: Sie baut sich ein eigenes Blatt mit
einem Wort darauf, schickt es an AWS und sieht nach, ob das Wort zurückkommt.
Kosten rund 0,15 Cent, kein Modellaufruf, kein Akteninhalt. **Dieselbe Lehre
wie beim Aktengedächtnis:** Eine Berechtigung, die erst mitten in einer offenen
Akte fehlt, kostet mehr als zwanzig Sekunden vorher — und sieht dort aus wie
ein Mangel der Erkennung statt einer fehlenden Berechtigung.

**Und sie hat beim ersten Lauf sofort einen Fehler gefunden — im Betrieb, nicht
in sich selbst.** Meldung aus der Kanzlei: *„AWS hat geantwortet, aber das
Probewort kam nicht zurück."* Die Berechtigung stand, gelesen wurde nichts.

Ursache: Das Programm zerlegte ein PDF in einseitige PDFs und schickte jedes
als `Bytes`. Über dieses Feld nimmt Textract aber **nur PNG und JPEG** an —
PDF ausschließlich über einen Ablageort in S3. So steht es in der
API-Beschreibung, die mit `boto3` selbst ausgeliefert wird
(`botocore/data/textract/2018-06-27/service-2.json`, Shape `Document`,
Member `Bytes`). **Der Aufruf lief ohne Fehlermeldung durch und lieferte
nichts.**

Behoben: Die Seiten werden auf dem Rechner der Kanzlei zu Bildern gemacht
(PDFium, dieselbe Maschine, mit der Chrome PDFs anzeigt), und das Bild geht an
Textract. Der Ablageort bleibt damit entbehrlich — das war die ganze Zeit das
Ziel, nur der Weg dorthin war falsch. Zwei Pakete kommen dazu, beide fertige
Wheels ohne Systembibliothek.

**Die Lehre, und es ist die dritte an derselben Datei:** Ein Aufruf, der ohne
Fehler zurückkommt, hat nicht gearbeitet — er hat nur nicht widersprochen. In
einer echten Akte wäre das als „kein Text gefunden" durchgegangen und hätte
nach einem schlechten Scan ausgesehen. Eine Probe, deren Antwort man vorher
kennt, ist der einzige Weg, „nichts gefunden" von „nichts gelesen" zu
unterscheiden.

**Der dritte Lauf war grün.** Aus der Kanzlei am 02.10.2026: *„Texterkennung
arbeitet."* Damit ist die Kette vollständig belegt — Berechtigung, Umwandlung
zum Bild, Erkennung, und das Wort kam zurück.

**Der zweite Lauf fand den zweiten Fehler — diesmal in der Probe selbst.**
Meldung: *„Zurückgekommen sind 1 Seite(n) mit zusammen 23 Zeichen."* AWS hatte
gelesen, nur nicht das ganze Wort. Das Probewort
`JUSPERFECT TEXTERKENNUNG PROBE` ist bei 36 Punkt rund **594 Punkt** breit und
begann bei x=60 — auf einer Seite von **595 Punkt** Breite. Gelesen wurden
genau die 23 Zeichen, die noch aufs Blatt passten: `JUSPERFECT TEXTERKENNUN`.

Berechtigung, Umwandlung und Erkennung arbeiteten dabei **alle richtig**. Das
Wort ist jetzt kürzer, die Schrift kleiner — und zwei Prüfungen messen den Rand
am **gerenderten Bild**, statt die Zeichenbreite zu schätzen. Die Schätzung war
der Fehler.

Ebenfalls am 02.10.2026: `AWS-EINRICHTEN.md` hat einen eigenen Abschnitt zur
Texterkennung — Recht, Probe, und was geschieht, wenn das Recht fehlt.

#### Der Stand vor dem 02.10.2026

**Es fehlte genau eine Berechtigung in AWS, kein Ablageort.**

Am 01.10.2026 kam heraus, dass die Aufgabe kleiner ist, als sie hier stand.
Der Dateikopf von `jusperfect/ocr/textract.py` sagte seit jeher „mehrseitige
PDFs verlangt Textract aus S3" — der Quelltext schickte **alle** PDFs dorthin,
auch einen einseitigen Rückschein. Die Folge war keine falsche Erkennung,
sondern eine falsche Voraussetzung: Für siebzehn Rückscheine hätte die Kanzlei
einen Bucket einrichten, sichern und in der DSFA als Ablageort führen müssen.

Behoben: `seitenzahl()` zählt mit pypdf, ein Blatt geht unmittelbar über
`detect_document_text`, erst ab zwei Seiten der Weg über S3. Ein unlesbares
PDF zählt als 0 und nimmt den vorsichtigen Weg. Fehlt der Ablageort bei einem
mehrseitigen Scan, sagt das Programm, was fehlt.

**Damit entscheidet die Frage „wie viele der 17 sind einseitig" gar nichts
mehr.** Die einseitigen gehen sofort; bei einem mehrseitigen sagt das Programm
genau, was dann noch fehlt.

| Was noch fehlt | Wer |
|---|---|
| ~~`textract:DetectDocumentText` in der Zugriffsrichtlinie~~ | **erledigt 02.10.2026** — von der Kanzlei in AWS eingesetzt und gespeichert. |
| ~~`JUSPERFECT_OCR=textract` einschalten~~ | **erledigt 02.10.2026** auf ausdrückliche Anweisung („Jetzt die Texterkennung einschalten"). `START-JURNODES.bat` Zeile 141, mit Grund und Rückweg im Kommentar. |
| DSFA um die Texterkennung ergänzen | Kanzlei (Aufgabe 3) — kein neuer Auftragsverarbeiter, derselbe wie für die Texte |

**Fehlt die Berechtigung, sagt das Programm jetzt, was fehlt.** Vorher stand
dort `Textract nicht verfügbar (ClientError)` — ein Satz, der nichts verrät.
Jetzt nennt er das fehlende Recht und die Datei, in der es steht. Der Wortlaut
von AWS selbst geht dabei **nicht** hinaus: Eine Abweisung kann ein Stück der
Anfrage enthalten, und die Anfrage ist eine Seite der Akte. Vier Prüfungen
halten das fest, darunter `test_der_wortlaut_von_aws_geht_nie_hinaus`.

**Der Rest der Akte wird auch ohne die Berechtigung gelesen.** Ein gescannter
Rückschein, der nicht erkannt werden kann, hält den Lauf nicht an.

Die ursprüngliche Beschreibung steht unverändert darunter.

#### Der Stand vor dem 01.10.2026

17 von 55 Dokumenten der echten Akte sind gescannte Blätter: Rückscheine,
Einschreiben, die Vollmacht. Darin steht kein Text, nur ein Bild vom Text.

Der Einbau ist vorhanden (`jusperfect/ocr/textract.py`, Amazon Textract,
Frankfurt). Es fehlt:

- Das AWS-Recht `textract:DetectDocumentText` in der Zugriffsrichtlinie
- Für **mehrseitige** Scans ein S3-Ablageort — Textract verlangt das so.
  **Einseitige** gehen direkt über `detect_document_text` mit Bytes, ohne
  S3. Rückscheine und Vollmachten sind meist einseitig; es lohnt zu prüfen,
  wie viele der 17 einseitig sind, bevor ein Bucket eingerichtet wird.
- `JUSPERFECT_OCR=textract` in `START-JURNODES.bat`
- Kosten: rund 1,50 € je 1000 Seiten. Für diese Akte unter einem Cent.
- **Datenschutz:** derselbe Auftragsverarbeiter wie schon für die Texte
  (AWS Frankfurt), also kein neuer Vertrag — aber die DSFA muss es nennen
  (siehe Aufgabe 3).

### 2. Vermerke und Telefonvermerke einbeziehen — **wartet auf den Hersteller**

Aus der Kanzlei: „vermerke auch telefonvermerke wären wichtig."

**Stand 01.10.2026, abends: Die Schnittstelle gibt die Vermerke nicht her.**
Alles, was der Server selbst beantworten kann, ist gefragt worden:

| Gefragt | Ergebnis |
|---|---|
| 20 Parameterformen auf `/record/note` | 405 „Bitte Daten angeben" |
| 16 Zahlen aus Akte und Aufgaben als `id` | 405 „Bitte Daten angeben" |
| 16 Pfade für die E-Akte (OPTIONS) | **alle 404** |
| 30 Pfade für eine OpenAPI-Beschreibung | alle 404 |

**Der entscheidende Befund kam nicht aus der Schnittstelle, sondern aus einem
Bildschirmfoto der Kanzlei.** Die Akte X-100-2026 führt in jur|nodes drei
Bereiche: eine **To-Do-Liste** („Aufgabe Sonstiges", drei offene und sieben
erledigte), das **Dateisystem** und die **E-Akte**. Die zehn Einträge, die
`/todo/search?type=task` liefert, sind die To-Do-Liste — Zahl und Status
(`open`, `done`) passen genau. **Die Vermerke stehen in der E-Akte**, zusammen
mit den Mails; der oberste Eintrag dort lautet wörtlich „Vermerk".

Für die E-Akte gibt es keinen auffindbaren Pfad. Damit gilt Regel 10: **bei
Dritten warten, nicht raten.** Die Frage an den Hersteller steht fertig
formuliert am Ende jedes `jurnodestest.txt`.

**Die Lehre des Abends:** Zwanzig Parameternamen, sechzehn Zahlen und
sechsundvierzig Pfade gegen zehn Sekunden Hinsehen in der Oberfläche des
Herstellers. Wer eine Schnittstelle absucht, muss vorher wissen, wonach — und
die billigste Quelle dafür ist das Programm, das die Kanzlei ohnehin offen hat.

**Was unabhängig davon dabei herauskam** (alles am 01.10. am echten Server
belegt): Die Seitenzählung ist berichtigt (`page=0` wird abgewiesen, der
Server sagt es wörtlich), die Trefferlisten zeigen jetzt ihre Feldnamen zwei
Ebenen tief, und das Herunterladen geht aus beiden Ordnern — Korrespondenz
17 Dateien, Dateiordner 38.

#### Der Stand vom 28.09.2026 (überholt, zur Nachvollziehbarkeit)

Stand der Untersuchung: `GET /record/note` antwortet auf **fünf** verschiedene
Parameterformen mit demselben Satz — *„Bitte Daten angeben"*, Status 405
(bei diesem Hersteller heißt 405 **„ungültige Eingabe"**, nicht „Weg gibt es
nicht"). Fünf verschiedene Eingaben, eine Antwort: Dann liegt es nicht an der
Eingabe, sondern am Pfad.

**Der Lauf liegt seit dem 28.09.2026 vor, und er engt es deutlich ein:**

| Gefragt | Antwort |
|---|---|
| `/record/note` mit OPTIONS | **`GET,HEAD,POST`** — der Pfad existiert und nimmt GET an |
| `/record/note` mit `record`, `recordIdentifier`, `identifier`, `record`+`page`, `recordIdentifier`+`type` | fünfmal 405 „Bitte Daten angeben" |
| `/record/note/search` | **404** — gibt es nicht |
| `/note/search` | **404** — gibt es nicht |

Damit ist die Vermutung „es heißt `<ding>/search`" **widerlegt**. Der Pfad ist
`/record/note`, und GET ist erlaubt — es fehlt allein **der Name des
Parameters**. „Bitte Daten angeben" heißt: Der Server hat keine bekannte
Angabe gefunden.

Zwei Wege, und der erste ist billiger:

1. **Weitere Namen durchprobieren.** Die Probe kostet nichts. Kandidaten aus
   dem Muster der übrigen Pfade: `noteIdentifier`, `recordId`, `id`, `note`,
   `sign`, `recordSign`, `folderId`, dazu Kombinationen mit `page=1`.
2. **Den Hersteller fragen.** Ein Satz: *Mit welchem Parameter liest
   `GET /record/note` die Vermerke einer Akte?* Das ist die sichere Auskunft;
   bei Dritten warten, nicht raten.

**Ebenfalls beantwortet:** Das Herunterladen geht aus **beiden** Ordnern —
Korrespondenz (17 Dateien, 44 KB geladen) und Dateiordner (38 Dateien, 5,6 MB
geladen). Damit ist die zweite offene Frage des Tages erledigt.

### 3. DSFA, Datenschutzhinweise, Mandatsbedingungen — *Kanzlei*

Die Rechtsdokumentation, bevor das Programm in die Breite geht. Die technischen
Angaben stehen in `DSFA-ANGABEN.md`, seit dem 28.09.2026 einschließlich der
vollständigen AWS-Ablage.

**Vorarbeit erledigt am 28.09.2026:** `VERARBEITUNGSVERZEICHNIS-ENTWURF.md`
trägt den Eintrag nach Art. 30 Abs. 1 DSGVO vorformuliert — Zwecke, betroffene
Personen, Datenkategorien einschließlich Art. 9 und 10 nach Rechtsgebiet,
Empfänger, Drittlandbezug, Speicherdauer mit und ohne Aktengedächtnis, und die
technischen Maßnahmen nach Art. 32 mit ihrem Nachweis im Programm.

**Zwölf Stellen sind mit `[KANZLEI]` gekennzeichnet** — dort hört die
Übertragung auf und die Bewertung fängt an: Rechtsgrundlage, Erlaubnistatbestand
für besondere Kategorien, § 43e BRAO und § 203 StGB, die Erforderlichkeit einer
DSFA nach Art. 35, und die Löschfristen.

**Eine Angabe in `DSFA-ANGABEN.md` war überholt und ist berichtigt:** Dort
stand, über das Laufwerk sei ein archivierter Aktenstatus nicht zu erkennen und
die Lücke schließe sich mit der Schnittstelle. Die Schnittstelle steht seit dem
23.09., und der Lauf vom 28.09. belegt die Felder (`recordStatus`,
`archivedDate`). Eine Löschung, die dem Aktenstatus folgt, ist damit technisch
möglich — ob sie gewollt ist, ist Punkt 6.2 des Entwurfs.

Muss um die Texterkennung ergänzt werden, falls Aufgabe 1 kommt.

### 4. ~~Aktengedächtnis ins AWS-Konto~~ — **erledigt 01.10.2026**

**Eingeschaltet auf ausdrückliche Anweisung der Kanzlei** („Schalte das
Aktengedächtnis nun ein"). `START-JURNODES.bat` trägt `JUSPERFECT_GEDAECHTNIS=aws`
samt Ablageort und Schlüsselkennung — keine Platzhalter mehr; eine Prüfung hält
fest, dass dort keine stehen.

| | |
|---|---|
| Ablageort | `dortschy-thunert-jusperfect-aktengedaechtnis`, Frankfurt |
| Schlüssel | `jusperfect-kanzlei`, SSE-KMS |
| In die jur\|nodes-Akte | wird weiterhin **nichts** geschrieben |
| Weg zurück | aus `aws` wieder `aus`; `GEDAECHTNIS-LEEREN.bat` räumt weg |

**Offen bleibt die Rechtsdokumentation, nicht die Technik.** jusperfect legt
damit erstmals dauerhaft Akteninhalt außerhalb von jur|nodes ab — Mandatsgut,
kein Protokoll. Derselbe Auftragsverarbeiter, also kein neuer AV-Vertrag; aber
**Ziffer 6.2 des Verarbeitungsverzeichnisses muss es nennen, und die ist noch
offen.** Die Unterlage läuft dem Betrieb damit hinterher, nicht umgekehrt. Das
ist gesagt und entschieden, nicht übersehen.

**Vor der ersten Akte:** einmal `GEDAECHTNIS-AWS-PRUEFEN.bat` — erst wenn die
grün ist, arbeitet das Gedächtnis wirklich.

Der ursprüngliche Stand steht unverändert darunter.

#### Der Stand vom 28.09.2026

Heute ist das Aktengedächtnis **abgeschaltet**
(`set JUSPERFECT_GEDAECHTNIS=aus` in `START-JURNODES.bat`, mit Begründung
in der Datei). Grund: Es lag als Datei in der jur|nodes-Akte und hat den
Aktenbestand vollgeschrieben. Die Entscheidung der Kanzlei: erst in Ruhe die
AWS-Lösung bauen, dann wieder einschalten.

**Am Programm ist nichts mehr offen** (`a6066db`, Anleitung folgt im nächsten
Commit):

- Der Speicher war schon fertig (`jusperfect/gedaechtnis/aws.py`, S3 mit
  SSE-KMS).
- **Der Selbsttest behauptete etwas.** Für `aws` zeigte er einen grünen Haken —
  abgeleitet allein daraus, dass in der Startdatei ein Name steht. Jetzt sagt er
  „eingestellt, aber nicht geprüft". Dieselbe Trennung wie beim Schutzgeländer.
- **`GEDAECHTNIS-AWS-PRUEFEN.bat`** legt ab, liest zurück, vergleicht und
  entfernt wieder — über `AwsGedaechtnisSpeicher` selbst, nicht über
  `head_bucket`. Bei einem Fehlschlag nennt sie die Abhilfe je Lage. Gemessen an
  einem nachgestellten S3 (moto).
- **Die drei Zeilen in `START-JURNODES.bat`** sind vorbereitet, auskommentiert.
  Ihre Platzhalter weist das Programm jetzt ab (`PLATZHALTER_ABLAGE`) — sonst
  käme eine Meldung von S3, die nach einem Programmfehler aussieht.
- **`AWS-EINRICHTEN.md`, Schritt 11** führt durch Schlüssel, Ablageort, die
  nötigen Rechte und die Probe.

**Die Einrichtung in AWS ist am 28.09.2026 erfolgt und nachgewiesen.** Bucket
`dortschy-thunert-jusperfect-aktengedaechtnis`, Schlüssel `jusperfect-kanzlei`,
Richtlinie `jusperfect-gedaechtnis` am Benutzer `jusperfect-test`. Alle Werte
stehen in `DSFA-ANGABEN.md`. `GEDAECHTNIS-AWS-PRUEFEN.bat` hat Ablegen,
Zurücklesen und Entfernen bestanden.

**Offen ist allein das Einschalten** — drei Zeilen in `START-JURNODES.bat`. Das
ist eine Entscheidung der Kanzlei, keine technische: Damit legt jusperfect
erstmals dauerhaft Akteninhalt außerhalb von jur|nodes ab. **Solange die
Rechtsdokumentation nicht steht (Aufgabe 3), bleibt es aus.** Deshalb ist
dieser Punkt nicht abgehakt: gebaut ist alles, in Benutzung ist nichts.

### 5. ~~Gedächtnisdateien aus den Akten entfernen~~ — **erledigt 28.09.2026**

Aus der Kanzlei am 28.09.2026: „habe beide aktengedächtnisse aus 018-2025 und
140-2026 gelöscht." Von Hand in jur|nodes, wie vorgesehen — das Programm hat
kein Löschrecht und soll keines bekommen.

Der Lauf von `JURNODES-PRUEFEN.bat` vom selben Tag hatte in X-100-2026 noch
eine gezählt (Dateiordner: „Aktengedächtnis: 1"), im Korrespondenzordner keine.
Die Probe zählt sie mit — ein zweiter Lauf zeigt jederzeit, ob wieder eine
entsteht. Solange `JUSPERFECT_GEDAECHTNIS=aus` steht, entsteht keine.

### 6. ~~Prüfbogenlauf für die Chronologie-Regel~~ — **erledigt 01.10.2026**

**Der Lauf vom 01.10.2026, 19:24 Uhr, mit Opus 4.6 (3,10 €):**

| Gemessen | Ergebnis |
|---|---|
| Tage im Zeitstrahl | **13 von 13** |
| Funde | 5 von 5, belegt |
| Zahlen | 5 von 5, auch die 402,00 m² |
| Fristensperre | hält |
| Rauschwert | 5 % — **und das war ein Fehler des Messgeräts** |

Die fünf Tage, die in fünf Läufen bei drei Modellen gefehlt haben, sind da. Die
Ursache war richtig erkannt: Das Modell sah das Datum eines Schriftstücks nie.

**Der Rauschwert maß die Befolgung der Anweisung als Fehler.** Von drei
gezählten Einträgen verlangt der Auftrag zwei ausdrücklich — sie stehen im
Bautagebuch unter „Besondere Vorkommnisse", und die Akte würfelt 60 solcher
Tage. Wer daraufhin die Gegenliste gegen „Abwesenheit" geschärft hätte, hätte
Fund 3 verloren. Der dritte Eintrag war ein echter Fehler und wird jetzt
gefiltert. Nachgerechnet am Lauf selbst: 51 Einträge werden 46, die Tage
bleiben 13 von 13, der Rauschwert fällt auf **0 %** — ohne weiteren Lauf.

**Beinahe-Unfall, zum Mitschreiben:** Der erste Entwurf des Filters strich
sieben Einträge und damit einen der dreizehn Tage — „21.06.2025
Empfangsbekenntnis des Geschäftsführers", den Zugang der Mängelrüge. Ursache
war die Gegenliste selbst: Ein Empfangsbekenntnis stand bei den laufenden
Aufzeichnungen, deren eigenes Datum nichts trägt. Für eine Kanzlei ist das
falsch herum — an diesem Datum beginnen Fristen. Aufgefallen ist es beim
Nachrechnen am echten Lauf, nicht in einer Prüfung.

Die ursprüngliche Aufgabenstellung steht unverändert darunter.

---

Die Regel vom 22.09.2026 ist nach wie vor **nicht am echten Modell gemessen**.
Der Lauf muss zwei Dinge zugleich zeigen:

1. Die fünf fehlenden Tage kommen dazu — 14.02.2025 Leistungsverzeichnis,
   02.09.2025 Schlussrechnung, 18.02.2026 Gutachten, 11.03.2026 Schriftsatz,
   08.04.2026 Zeugenbenennung.
2. **Der Rauschwert bleibt bei 0 %.** Das ist die eigentliche Schwierigkeit.
   Steigt er, gehört die Gegenliste nachgeschärft — nicht die Regel
   zurückgenommen.

Läuft auf der erfundenen Testakte, braucht keine echte Akte.

**Stand 28.09.2026: gemessen, Ursache gefunden, behoben — der Nachweis fehlt.**

Der Lauf (0,79 €) hat beides verfehlt: alle fünf Tage fehlten weiter, der
Rauschwert stieg auf 5 %. Dafür 5 von 5 Funden, Fund 5 endlich mit D-002.

Zwei Ursachen, beide behoben:

1. **Die Regel stand an der falschen Stelle.** Der Zeitstrahl entsteht in der
   Analyse, und die sieht die Dokumente nicht mehr — `material_gedaechtnis`
   schickt ihr den Lebenssachverhalt, nicht die Passagen. Ein Datum, das beim
   **Einlesen** nicht aufgeschrieben wurde, kann sie nicht nachtragen. Deshalb
   fehlten dieselben fünf Tage bei drei Modellen: Ein Fehler, den jedes Modell
   gleich macht, liegt nicht am Modell. `aufgabe_gedaechtnis` verlangt das
   eigene Datum jetzt ausdrücklich; die beiden Listen stehen einmal da und
   werden von beiden Aufträgen benutzt.
2. **Der Bogen misst jetzt den Betrieb.** Er löschte
   `JUSPERFECT_MODELL_GEDAECHTNIS` und las mit Haiku ein, während alle drei
   Startdateien Opus setzen — daher die fehlenden 402,00 m². Gleiche Form wie
   fünfmal am 23./24.09.: eine Probe, die anders fragt als der Betrieb.
   `tests/test_starter.py::DasMessgeraetMisstDenBetrieb` hält die Dateien
   gegeneinander.

**Lauf 13:04 Uhr mit Opus (2,97 €): Rauschwert 0 %, Zahlen 5 von 5 — aber
dieselben fünf Tage fehlen.** Damit war die dritte Ursache zu sehen:

3. **Der Filter strich, was der Auftrag verlangte.** `chronologie.aufraeumen`
   hielt „Leistungsverzeichnis vom 14.02.2025" für abgeschriebenen
   Dokumenttext — und das ist es wörtlich, denn die Kopfzeile des Dokuments
   lautet genau so. Ein Eintrag, der ein Schriftstück benennt, kann dem
   Dokumenttext nicht ausweichen, ohne ungenau zu werden.
   `benennt_ein_schriftstueck` nimmt ihn jetzt aus; die Dokumentarten stehen
   in `chronologie.SCHRIFTSTUECKARTEN` und der Auftrag baut seine Liste
   daraus. Zwei Regeln, die einander widersprechen, sind schlimmer als eine
   falsche — und keine von beiden meldete es.
4. **Der Bogen sagt jetzt, was der Filter gestrichen hat.** Ohne diese Zeile
   ist ein fehlender Tag zweideutig: nicht genannt oder wieder entfernt? Drei
   Läufe zu je drei Euro haben es nicht gezeigt, weil der Bogen es nicht
   sagte.

**Was fehlt: ein Lauf mit `ef2c9ad`+. Er muss zeigen, dass die fünf Tage
kommen und der Rauschwert bei 0 % bleibt.**

**Zur Methode:** Zwei Läufe mit gleicher Fassung und gleichem Modell ergaben
5 von 5 gegen 3 von 5 Funde und 5 % gegen 11 % Rauschen. Das Messgerät
schwankt stärker als mancher Unterschied, den es messen soll — ein einzelner
Lauf ist bei diesen beiden Zahlen kein Beweis. Stabil über alle Läufe sind
allein die fünf fehlenden Tage und die Fristensperre.

### 7. ~~Darf `ModellAbonnement` in `infra/iam-nur-claude.json`?~~ — **erledigt 28.09.2026**

Aus der Kanzlei: „zugriffsrichtlinie erlaubt".

**Zu ändern war nichts.** Die Berechtigung steht bereits in der Datei, im
Abschnitt `ModelleAnsehen` als `aws-marketplace:ViewSubscriptions`, und
`infra/IAM.md` beschreibt sie dort auch so. Die Frage stand seit dem
11.09.2026 in der Übergabe und war offenbar längst erledigt — nur der Vermerk
blieb stehen. Dieselbe Lehre wie am 22.09.2026: Eine Arbeitsliste, die nicht
mitgeführt wird, kostet Zeit an der falschen Stelle.

Offen bleibt eine **Bestätigung**, keine Änderung: Die Datei im Programmordner
ist die Vorlage, wirksam ist die Richtlinie im AWS-Konto.
`MODELLE-ANZEIGEN.bat` zeigt, ob sie dort wirkt — erscheint die Modellliste,
ist alles in Ordnung.

### 8. ~~`START-DEMO.bat` auf `_UMGEBUNG.bat` umstellen~~ — **erledigt 28.09.2026**

`START-DEMO.bat` hatte eine eigene Kopie des Python- und `.venv`-Blocks und
wich schon ab (`VPY` statt `PY`, kein boto3, eine eigene Fehlermarke). Sie ist
weg; die Datei ist von 217 auf 95 Zeilen geschrumpft (`4c8132b`).

Dabei kam mehr heraus als erwartet:

- Die **Aufbauprüfung** stand in **drei** Startdateien, und eine Fassung war
  schon schwächer: `START-JURNODES.bat` unterschied nicht, ob `web.py` neben
  der Startdatei liegt — der einzige Fall, in dem man dem Anwender genau sagen
  kann, was er falsch gemacht hat.
- Die neue Prüfung fand eine **vierte**: `START-KANZLEI.bat`. Sie hatte dazu
  die Hürde, die am 25.09. bei `START-JURNODES.bat` entfernt wurde — „bitte
  zuerst START-AWS.bat ausführen". Dort behoben, hier stehengeblieben, und
  niemandem aufgefallen, weil niemand danach gesucht hat.
- `_UMGEBUNG.bat` schrieb `[1/4]` in jede aufrufende Datei. `START-DEMO.bat`
  hat drei Schritte, die Prüfdateien zwei. Die Schrittzahl wird jetzt
  übergeben.

`tests/test_starter.py::Aufbaupruefung` prüft jetzt nicht mehr, **ob** die
Logik in jeder Startdatei steht, sondern dass sie in **keiner** steht — eine
neue Kopie fällt beim Einbauen auf, nicht Wochen später.

### 9. Andere KI-Anbieter (Gemini u. a.) — *zurückgestellt*

Technisch ein Tag Arbeit (`jusperfect/providers/` hat die Stelle dafür).
Dagegen spricht: Jeder neue Anbieter ist ein neuer Auftragsverarbeiter — neuer
AV-Vertrag, DSFA erweitern, Mandantenhinweise anpassen. Und zwei Modelle sind
schwerer zu verantworten als eines. Erst entscheiden, dann bauen.

---

### 10. Der jur|nodes-Zugang fehlt auf diesem Rechner — *Nutzer, blockiert alles*

Gemeldet am 28.09.2026. Das ist **kein Fehler des Programms und zu erwarten:**
Die vier Zugangswerte liegen im **Windows-Konto** des jeweiligen Rechners und
nicht im Programmordner — genau deshalb überleben sie das Auspacken einer neuen
Fassung (siehe „Die Lehren des 25.09.2026", Punkt 5). Ein anderer Rechner, ein
anderes Windows-Konto oder ein neu aufgesetztes Windows hat sie folglich nicht.

Gebraucht werden vier Werte (`jusperfect/jurnodeszugang.py::FELDER`):

| Wert | Woher |
|---|---|
| `JUSPERFECT_JURNODES_URL` | Adresse der Schnittstelle, aus jur\|nodes |
| `JURNODES_API_USER` | Benutzername, am 24.09.2026 `user_2` |
| `JURNODES_API_KEY` | der Token, aus jur\|nodes |
| `JUSPERFECT_GUARDRAIL_ID` | Kennung des Schutzgeländers, am 24.09.2026 `jeico9orinss` |

Eingetragen werden sie mit **`JURNODES-ZUGANG.bat`** — die braucht seit dem
25.09.2026 weder die Arbeitsumgebung noch einen vorherigen Start und sucht die
Geländerkennung in älteren Programmordnern selbst. Geprüft wird mit
**`JURNODES-PRUEFEN.bat`**.

**Berichtigt am 01.10.2026:** Hier stand `ZUGANG-PRUEFEN.bat`. Die prüft
**nur AWS** — in `jusperfect/awstest.py` kommt jur|nodes kein einziges Mal
vor. Wer dem Satz folgte, bekam einen grünen AWS-Befund und hielt damit den
jur|nodes-Zugang für geprüft, der gar nicht angefasst worden war. Zwei
Zugänge, zwei Proben; sie heißen nur ähnlich.

**Zwei Fallen, die diesen Sommer je eine Stunde gekostet haben** (Lehren 3 und 4):

- Nichts eintragen, was wie ein Platzhalter aussieht — `IHRE-KENNUNG` und zwölf
  weitere Wörter weist das Programm ab.
- Nur den **Wert** eintragen, nicht die ganze Zeile aus der Startübersicht.
  `Benutzer:        user_2` ist nicht der Benutzername; `user_2` ist er.

**Der AWS-Zugang ist davon getrennt.** War dieser Rechner noch nie am Modell,
fehlt er ebenfalls und wird mit **`ZUGANG-EINTRAGEN.bat`** hinterlegt. Ob er
steht, sagt der Selbsttest im Startbild.

---

### 11. ~~Rechnung und RSV nicht ins Aktengedächtnis~~ — **erledigt 05.10.2026**

**Aus der Kanzlei am 05.10.2026:** „Grundsätzlich gehört die Rechnung nicht ins
Aktengedächtnis und Korrespondenz mit der RSV."

Trägt der **Titel** eines der Wörter aus `JUSPERFECT_NICHT_VORWAEHLEN`, kommt
das Dokument **ohne Haken** ins Fenster „Dokumente der Akte". Vorgabe:
Rechnung, Kostennote, Gebühren, Vorschuss, Honorar, RSV, Rechtsschutz,
Deckungszusage, Deckungsanfrage. Eigene Liste: in `START-JURNODES.bat`, dort
steht auch, warum in diese Zeile keine Umlaute gehören.

Zwei Dinge geschehen bewusst **nicht**:

* **Nichts verschwindet stillschweigend.** Das Dokument steht weiter in der
  Liste, nur blasser, mit dem Grund daneben („nicht vorgewählt: Rechnung").
  Ein Programm, das Akteninhalt heimlich auslässt, ist schlimmer als eines,
  das zu viel mitnimmt — was fehlt, fällt niemandem auf.
* **Es wird nicht gedeutet.** Geprüft wird der Titel, nicht der Inhalt. Eine
  Rechnung, die „Schreiben vom 14.03." heißt, geht durch. Eine Hilfe, keine
  Gewähr.

„alle anhaken" lässt die Ausgeschlossenen aus und sagt es; ein zweiter Klick
holt sie dazu — sonst wäre die Liste eine Sperre statt einer Vorauswahl.

**Im Browser gefunden, nicht in den Prüfungen:** Bei 430 Pixel Breite war
„nicht vorgewählt: Rechnung" länger als die übrige Beschriftung, nahm die ganze
Zeile ein und drückte den Dokumenttitel auf **null Breite** — das Dokument
stand ohne Namen da, also genau das stillschweigende Verschwinden, das diese
Liste nicht tun soll. Der Titel hat jetzt eine Untergrenze, und unter 560 Pixel
rutscht die Beschriftung darunter statt daneben. Zwei Prüfungen halten das fest.

**Noch nicht gebaut, falls es gewünscht wird:** nach Ordnern gruppieren — braucht
ein Ordnerfeld am Dokument.

---

### 12. ~~Einzelnes aus dem Aktengedächtnis nehmen — Dokument und Frage~~ — **erledigt 05.10.2026**

Bisher gab es nur alles oder nichts: `GEDAECHTNIS-LEEREN.bat` warf das ganze
Gedächtnis weg. Wer ein einziges Dokument heraushaben wollte, zahlte das
Einlesen der ganzen Akte noch einmal.

**Der Dienst dahinter stand längst** und ist in `tests/test_gedaechtnis_nummern.py`
und `tests/test_abschluss.py` gemessen. Was fehlte, war der Weg dorthin: In der
rechten Spalte des Gedächtnisfensters steht jetzt je Zeile ein Knopf
**„vergessen"**.

**Die Rückfrage zählt, sie schätzt nicht.** Sie nennt den Auszug mit Seiten und
Umfang, die Zahl der gespeicherten Fragen und Zeitstrahleinträge, die ihn
zitieren und deshalb **ganz** fallen, und ob der Lebenssachverhalt betroffen
ist. Sie sagt auch, wenn sonst nichts fällt — Schweigen läse sich wie „nicht
nachgesehen". Gezählt wird nach **derselben Regel wie im Dienst** (`some`, nicht
`every`); eine Prüfung rechnet beide Seiten an denselben Daten nach. Eine
Rückfrage, die weniger ankündigt, als hinterher fehlt, wäre schlimmer als gar
keine.

**Kein Rückgängig-Streifen.** Zurücklegen ist möglich, kostet aber ein neues
Einlesen — bei einem Scan mit Texterkennung — und holt das Abgeleitete nicht
wieder. Ein „Rückgängig", das den vorigen Zustand nicht herstellt, wäre eine
Unwahrheit.

**Am 05.10.2026 im Browser nachgesehen:** Die Rückfrage kündigte 1 Frage und 1
Zeitstrahleintrag an, und genau die fehlten danach; im Lebenssachverhalt stand
an der Stelle sichtbar `[Aussage ohne belastbaren Beleg entfernt]`, nichts wurde
stillschweigend geglättet. Dabei fiel auf, dass der Knopf vom Titel
„Kündigungss…" übrig ließ — in dieser Spalte steht der Titel seitdem auf einer
eigenen Zeile.

**Was der Weg nicht ist:** Die Akte in jur|nodes bleibt unberührt. Entfernt wird
nur, was sich jusperfect gemerkt hat; das steht auch so in der Rückfrage, weil
es die erste Frage ist, die dabei aufkommt.

**Nachtrag am selben Tag: auch eine einzelne gespeicherte Frage.** In der Liste
„Frühere Fragen und Antworten" steht je Runde derselbe Knopf. Eine gespeicherte
Antwort kann falsch oder überholt sein — etwa weil sie aus einem Dokument
stammt, das inzwischen durch eine neue Fassung ersetzt wurde; sie geht bei jeder
späteren Frage als Vorwissen mit.

**Dabei eine Falle, die nicht in der Anzeige steckt:** Der Server löscht eine
Frage nach **Stelle** in der Liste. Hätte die Oberfläche die Stelle von vorhin
geschickt und in der Zwischenzeit jemand an derselben Akte gearbeitet — zwei
Anwälte, zwei Rechner —, wäre eine **andere** Frage weg, ohne dass es jemand
bemerkt. Die Stelle wird deshalb erst beim Klick frisch bestimmt, anhand von
Frage, Antwort und Zeitpunkt. **Am 05.10.2026 im Browser nachgestellt:** Während
das Fenster offen stand, löschte ein zweiter Zugang dieselbe Frage. Es kam keine
Rückfrage, es wurde nichts gelöscht, die Liste ging von zwei auf eins, und der
Grund stand auf dem Schirm.

---

### 13. ~~Die Aktenanalyse aufbewahren~~ — **erledigt 05.10.2026**

Die Analyse kostet einen Modellaufruf über die ganze Akte — an der echten Akte
rund 28 Cent. Von allem, was ein Durchgang erzeugt, war sie das **Teuerste und
das Einzige, das niemand aufbewahrt hat**: Sie stand im Fenster und war weg,
sobald das Programm geschlossen wurde. Nur ihr Zeitstrahl wurde fortgeschrieben.

Sie liegt jetzt im Aktengedächtnis und steht beim Öffnen der Akte wieder da,
überschrieben mit **„Stand vom …"**. Der Abruf kostet nichts.

**Aus der Kanzlei:** „Wichtig ist, dass das Programm vielleicht selber erkennt,
wenn neue Dokumente in der Akte sind." Mitgeschrieben wird deshalb auch, **was
die Akte damals enthielt**. Kommen später Dokumente dazu, steht über dem
Ergebnis, welche fehlen — **beim Namen genannt** —, und daneben ein Knopf
„neu rechnen".

**Der Punkt, an dem die Warnung sonst wertlos geworden wäre:** Verglichen wird
gegen das, was die Akte **damals enthielt**, nicht gegen das, was in die
Analyse eingegangen ist. Sonst zählte jedes bewusst nicht vorgewählte
Dokument — eine Rechnung etwa — bei jedem Öffnen wieder als „neu".

Der Knopf **Analyse** fragt jetzt nach, wenn schon eine vorliegt: mit Datum,
mit dem, was seitdem dazugekommen ist, und mit dem Preis. Beim ersten Mal
fragt er nicht.

**Im Browser nachgestellt:** rechnen, Programm neu starten, Analyse ist wieder
da; dann ein neues Dokument in die Akte legen — die Warnung erscheint und nennt
es. Dabei fiel auf, dass ein Titel, der selbst auf einen Punkt endet, zu
„02.10.." führte; die Titel stehen jetzt am Schluss ohne Satzzeichen dahinter.

**Und ein eigener Fehler, den der Browserlauf gefangen hat:** Zweimal hat die
Probe gegen einen Server gemessen, der noch den Stand von vor der Änderung
trug — `pkill -f jusperfect` traf die eigene Kommandozeile und nicht den
Server, und weil das Programm bei belegtem Anschluss nicht zweimal startet,
antwortete weiter der alte. Dieselbe Lehre wie am 05.10. zuvor: **Eine Probe,
die etwas anderes misst als den Betrieb, misst etwas anderes als den Betrieb.**
Erkennbar war es nur daran, dass eine neue Schnittstelle mit 405 antwortete,
während dieselbe Prüfung im Testlauf grün war.

---

### 14. ~~Eine ausführliche Anleitung~~ — **erledigt 05.10.2026**

Auf ausdrückliche Anweisung der Kanzlei geändert (Regel 4).

`ANLEITUNG.md`, Teil 2, beschrieb noch den **Zwei-Fenster-Explorer mit Ziehen**
und „alle →". Den gibt es seit Wochen nicht mehr; es ist eine Liste mit Haken.

Neu beschrieben: das Lesen in Portionen mit Balken und Anhalten, die
Texterkennung für Scans, die Ausschlussliste, das Aktengedächtnis im Alltag
samt „vergessen", die gespeicherte Aktenanalyse mit Stand und Veraltungshinweis,
der Zeitstrahl, die abtrennbaren Fenster, die Rückfrage beim Schließen.

**Neu dazu: „Was wie lange gespeichert bleibt"** — eine Tabelle über
Aktengedächtnis, Sitzung und jur|nodes. Das ist die Frage, die bei einem
KI-Programm zuerst zu stellen ist, und sie stand nirgends zusammen.

**Berichtigt:** Der Kopf sagte, die Fassung sei „zum Ausprobieren, nicht für
echte Mandantenakten", während die Kanzlei seit dem 23.09.2026 damit arbeitet.
Jetzt steht dort, was wirklich noch fehlt (vor allem die DSFA), was inzwischen
steht (Modellaufrufprotokollierung, Schutzgeländer) und die offene Frage zum
Korrespondenzordner.

**Nachtrag am selben Tag: dasselbe als Seite zum Durchklicken.** `HILFE.html`
liegt neben dem Programm, öffnet sich mit einem Doppelklick und **braucht kein
Internet** — genau dafür ist sie da, wenn etwas klemmt.

Abschnitt 4 ist neu geschrieben; drei Abschnitte kommen dazu (5 Aktengedächtnis,
6 Aktenanalyse, 9 Was wie lange bleibt), alles Spätere ist umnummeriert. Fünf
neue Störungen, darunter zwei, die **wie ein Fehler aussehen und keiner sind**:
der gelbe Hinweis über der Analyse und das blasse Dokument ohne Haken.

Gemessen in echtem Chromium bei 1280 und 390 Pixel: kein waagerechter Überlauf,
kein Konsolenfehler, kein Verweis ins Leere, die Suche findet die neuen
Einträge, hell und dunkel. Sieben neue Prüfungen — eine zählt die
Abschnittsnummern lückenlos nach, eine besteht darauf, dass der
**Zwei-Fenster-Explorer nicht mehr vorkommt**: Eine Anleitung, die eine
Bedienung beschreibt, die es nicht gibt, kostet erst Zeit und dann Vertrauen.

---

## Die Lehren des 25.09.2026

Der Tag ging fast vollständig für Dinge drauf, die **nicht** das Problem
waren. Wer morgen weitermacht, spart sich das mit diesen sechs Sätzen.

### 1. Eine Probe, die anders fragt als der Betrieb, prüft etwas anderes

`JURNODES-PRUEFEN.bat` **listete** die Ordner auf — beide, tadellos. Der
Betrieb **lädt herunter**. Das ist bei jur|nodes ein anderes Recht, und die
Probe konnte den Unterschied gar nicht zeigen. Seit `a865d0e` lädt sie je
Ordner eine Datei testweise herunter.

Derselbe Satz steht seit Wochen in der Übergabe. Er wurde trotzdem gebrochen.

### 2. 1176 grüne Prüfungen sagen nichts über eine Datei, die niemand parst

Ein fehlendes `+` zwischen zwei Zeichenketten im JavaScript:

```javascript
laeuft("Erster Teil. "
       "Zweiter Teil.");
```

In Python eine Verkettung, in JavaScript ein Syntaxfehler — und der legt die
**ganze Datei** lahm, nicht die eine Zeile. Die Seite lud, das Gerüst stand,
es blieb bei „verbinde …", kein Knopf tat etwas. Die Kanzlei suchte
stundenlang bei AWS, beim Zugang, beim Schutzgeländer.

Geprüft wurde, *was* das JavaScript sagt — nie, *ob* es sich lesen lässt.
`tests/test_oberflaeche_syntax.py` holt das nach.

**Konsequenz für morgen:** Bei „die Seite ist grau/leer/tot" **zuerst**
`node --check jusperfect/static/*.js` und die Seite im Browser öffnen, bevor
irgendetwas an Zugangsdaten gesucht wird.

### 3. Ein Platzhalter ist schlimmer als eine Lücke

Im Windows-Konto stand `IHRE-KENNUNG` — wörtlich der Platzhalter aus meiner
eigenen Anleitung. Die Prüfung „ist etwas eingetragen?" war zufrieden, das
Programm startete, der AWS-Zugangstest lief durch, und erst der Modellaufruf
scheiterte. Dreizehn solcher Wörter werden jetzt abgewiesen, und eine Prüfung
verhindert, dass je wieder ein Beispiel in `AWS-EINRICHTEN.md` steht, das das
Programm selbst zurückweist.

**Wer eine Anleitung schreibt, muss damit rechnen, dass sie befolgt wird.**

### 4. Wer eine Übersicht auf den Schirm schreibt, muss damit rechnen, dass
sie kopiert wird

Im Windows-Konto stand als Benutzername wörtlich `Benutzer:        user_2` —
die ganze Zeile aus der Startübersicht, mit Beschriftung und acht Leerzeichen.
jur|nodes lehnte mit 401 ab, meine Meldung sprach von fehlenden Rechten, und
die Suche ging eine Stunde in die Rechteverwaltung des Herstellers.

Das ist kein Bedienfehler. Dort steht der Wert, den das Programm haben will.
`ohne_beschriftung()` schneidet eine bekannte Beschriftung jetzt ab; eine
Adresse behält ihr `https:`.

### 5. Was eine Einrichtung überleben soll, gehört nicht in den Ordner, den
wir austauschen

Die Kennung des Schutzgeländers stand in `START-JURNODES.bat`. Beim Auspacken
der neuen Fassung war sie weg. Sie liegt jetzt im Windows-Konto, eingetragen
mit `JURNODES-ZUGANG.bat` — die sie zusätzlich in älteren Ordnern selbst
sucht, statt den Anwender in eine Programmdatei schauen zu lassen.

### 6. Eine Hürde, die nichts schützt, ist keine Sperre, sondern ein Fehler

`JURNODES-ZUGANG.bat` verlangte die `.venv`, obwohl sie vier Werte ins
Windows-Konto schreibt und dafür blankes Python genügt. `START-JURNODES.bat`
schickte den Anwender zu `START-AWS.bat` — also erst die erfundenen Testakten
starten, um an die echten zu kommen, und das bei jeder neuen ZIP. Beides ist
weg.

---

## Was am 25.09.2026 fertig geworden ist

44 Änderungen. Die tragenden:

- **Alle Dokumentarten lesen** — dazugekommen: `.eml`, `.msg`, `.html`,
  `.rtf`, `.xlsx`, `.pptx`. `.doc`/`.xls`/`.ppt` werden bewusst abgelehnt.
- **Unterordner und Korrespondenzordner** gehören zur Akte. Eine Akte nennt
  **zwei** Ordner: `fileFolderId` und `correspondenceFolderId`.
- **Ein Dokument, das sich nicht laden lässt, kostet nicht die übrigen.** Fünf
  Fälle von „Teilfehler reißt das Ganze mit" behoben.
- **Die Bilanzleiste** nennt gelesen/nicht gelesen mit Grund und Dateiarten;
  die Einzelheiten stehen zugeklappt darunter.
- **Das Öffnen einer Akte** fragt nicht mehr dreimal dasselbe (8 s → 1 s) und
  zeigt einen Kreis mit Wartehinweis.
- **Arbeitsstand beim Öffnen**, **Archivmarke**, **Gesetzesverweise als Link**,
  **Knopf „Gesetz nachschlagen"**, **Aktengedächtnis als eigener Knopf**.
- **Der Browser geht erst auf, wenn der Server antwortet** — vorher kam
  jedes Mal zuerst eine Fehlerseite.
- **405 heißt bei jur|nodes „ungültige Eingabe"**, nicht „Methode nicht
  erlaubt". Steht 94-mal so in der Herstellerbeschreibung. Das hat das
  Aktengedächtnis-Rätsel gelöst.

---

## Die Reihenfolge, die ich vorschlage

1. **Den Zugang auf diesem Rechner hinterlegen** (Aufgabe 10). Ohne ihn
   erreicht keine der folgenden Proben eine echte Akte.
2. **`JURNODES-PRUEFEN.bat` einmal laufen lassen** (Akte `X-100-2026`). Sie
   beantwortet in einem Lauf zwei offene Fragen: den Weg zu den Vermerken
   (Aufgabe 2) und ob das Herunterladen aus beiden Ordnern geht.
3. **Texterkennung** (Aufgabe 1) — das Einzige, was noch Akteninhalt kostet.
4. **Prüfbogenlauf Chronologie** (Aufgabe 6) — der zweite Lauf, jetzt mit
   Opus, zum Nachweis der Änderungen vom 28.09.
5. ~~**`START-DEMO.bat` zusammenführen** (Aufgabe 8)~~ — erledigt.

Am Programm ist nichts offen, was das Arbeiten mit einer echten Akte
verhindert.
