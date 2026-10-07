# Was von jur|nodes noch fehlt — Stand 07.10.2026

Diese Datei ist zum **Weiterleiten** gedacht: an jur|nodes, oder als Suchliste
für eine neuere Fassung der Schnittstellenbeschreibung. Sie nennt nur, was
wirklich offen ist — alles andere steht in
`schnittstelle/jurnodes-api-1.0.2.json` und ist eingebaut.

> **Was die Beschreibung 1.0.2 bereits beantwortet hat**, und zwar vollständig:
> die E-Akte heißt dort *Korrespondenz* (`POST /correspondence/search` mit
> `recordIdentifier`), die Vermerke sind Einträge vom Typ `note` und werden mit
> `GET /record/note?id=…&record=…` gelesen — mit **beiden** Pflichtparametern.
> Daran war die Suche vier Wochen gescheitert. **Dafür ist nichts mehr zu
> fragen.**

---

## Vorrangig: Status 401 auf `POST /correspondence/search`

**Gemessen am 07.10.2026** am Server der Kanzlei, mit dem Benutzer `user_2`.
Im selben Lauf, mit demselben Zugang, antworteten `GET /record/search`,
`GET /record`, `GET /relation/search`, `GET /todo/search`,
`GET /file-system/folder/content` und `GET /file-system/file/download`
jeweils mit **Status 200**. Allein das Korrespondenzverzeichnis wurde
abgewiesen:

```
POST /correspondence/search   {"recordIdentifier": "…", "page": 1}
→ Status 401, Antwortkörper: {}
```

Der Zugang als solcher steht also. Abgewiesen wird dieser eine Pfad, und der
Antwortkörper nennt keinen Grund.

> **Frage:** Verlangt `POST /correspondence/search` ein eigenes Recht am
> Schnittstellenbenutzer — und wenn ja, wie heißt es und wo wird es gesetzt?
> Oder verlangt der Pfad eine andere Anmeldung als die übrigen?

*Warum das zählt:* Das Korrespondenzverzeichnis ist der **einzige**
beschriebene Weg zu den Vermerken einer Akte. Es liefert zu jedem Eintrag die
Nummer in `referenceNote`, und erst mit ihr ist `GET /record/note` zu rufen.
Solange der Pfad 401 antwortet, bleibt die E-Akte abgeschaltet — nicht weil
etwas fehlt, sondern weil der Server nicht antwortet.

*Was wir selbst tun:* Nichts weiter. Es ist am Programm nichts zu ändern;
sobald der Pfad antwortet, genügt ein weiterer Lauf von
`JURNODES-PRUEFEN.bat`.

---

## Offen: wofür steht `correspondenceFolderId`?

**Dreimal geprüft, dreimal derselbe Befund.** Zuletzt am 07.10.2026: Die
geprüfte Akte wurde am **30.07.2026** angelegt. Die Ordner hinter ihrem
`correspondenceFolderId` tragen Ablagen ab dem **15.12.2022** — fünf Ordner,
siebzehn Dateien, alle älter als die Akte.

Eine Datei kann nicht in eine Akte gelegt worden sein, die es noch nicht gab.
Der Ordner hinter diesem Feld gehört also nicht dieser Akte.

> **Frage:** Was benennt `Record.correspondenceFolderId`? Einen Ordner der
> Akte — dann wäre der zurückgegebene Wert falsch — oder etwas anderes, etwa
> einen gemeinsamen Ablagebereich oder eine Vorlage?

*Warum das zählt:* Eine Kanzlei darf Unterlagen eines Mandats nicht in einem
anderen zeigen. Das Programm liest diesen Ordner seit dem 05.10.2026 **nicht
mehr**; die Prüfung listet ihn nur noch und holt seit dem 07.10.2026 auch
keine Datei mehr daraus. Die Frage bleibt, weil eine Antwort darauf eine
Vermutung durch eine Auskunft ersetzt.

---

## Ein Schreibfehler in der Beschreibung selbst

In `jurnodes-api-1.0.2.json` fehlt bei **einem** der 85 Pfade der führende
Schrägstrich:

```
correspondence/get-by-reference      POST
```

Alle übrigen 84 beginnen mit `/`.

> **Frage:** Lautet der Pfad `/correspondence/get-by-reference`? Und liefert
> er zu einem `referenceMail`, `referenceBea` oder `referencePost` den
> zugehörigen Eintrag? Dann beantwortet er womöglich die Fragen 2 und 3 unten
> von selbst.

---

## Offen: der Inhalt von Mail, beA und Post

Die Korrespondenz einer Akte führt neun Arten (`mail`, `bea`, `post`, `fax`,
`webnodes`, `sms`, `eda`, `note`, `file`). Übernommen werden heute die
**Vermerke**; die übrigen stehen in der Liste der Akte **nicht**, weil zwei
Angaben fehlen. Beide sind klein.

### 1. Welche Dateiart gibt der Download zurück?

`POST /mail/download` mit `{"mailIdentifier": "…"}` liefert laut Beschreibung
`application/octet-stream`. Welches **Format** diese Bytes haben, steht nicht
dabei.

> **Frage:** Ist das eine `.eml`, eine Outlook-`.msg`, ein PDF — oder je nach
> Herkunft verschieden? Setzt der Server einen `Content-Disposition`-Dateinamen?

*Warum das zählt:* Die Texterkennung des Programms liest `.eml`, `.msg` und PDF
bereits. Sie muss nur wissen, welches davon vorliegt.

*Was wir selbst tun:* `JURNODES-PRUEFEN.bat` misst es inzwischen am Server und
nennt Status, Länge und die Signatur der ersten Bytes — **ohne Inhalt**.
Bringt der Lauf eine klare Antwort, erübrigt sich diese Frage.

### 2. Woher kommt die zweite Pflichtnummer bei beA und Post?

| Aufruf | Pflichtangaben | Offen |
|---|---|---|
| `GET /bea/download` | `beaIdentifier`, **`attachmentId`** | Welcher Aufruf liefert `attachmentId`? |
| `POST /post/download` | `correspondenceIdentifier`, `postId`, **`postFileUniqueKey`** | Kommt `postFileUniqueKey` aus `POST /post/get-files`? |

Aus dem Korrespondenzverzeichnis kommen `referenceBea` und `referencePost` —
jeweils **eine** Nummer. Die zweite ist nicht erkennbar abgeleitet.

> **Frage:** Welcher Aufruf liefert zu einem Korrespondenzeintrag die Liste
> seiner Anhänge, und mit welchen Feldern?

### 3. Ist `referenceMail` dasselbe wie `mailIdentifier`?

Das Verzeichnis nennt `referenceMail`, der Download verlangt `mailIdentifier`.
Dass beides dasselbe ist, liegt nahe und steht nirgends.

> **Frage:** Ist `CorrespondenceModel.referenceMail` der Wert, der in
> `mailIdentifier` gehört?

---

## Offen: zwei kleinere Punkte

* **`isInbox`** ist eine Zahl. Heißt `1` „eingegangen" und `0` „ausgegangen"?
  Für die Akte ist die Richtung eines Schreibens wesentlich.
* **Gibt es eine neuere Fassung der Beschreibung als 1.0.2?** Falls ja, bitte
  diese — sie beantwortet die Fragen oben womöglich von selbst.

---

## Was nicht gefragt wird, und warum

**Zum Befund vom 02.10.2026** — drei Schriftstücke einer fremden Akte in einer
Bausache — ist **nichts zu fragen.** Es war ein Fehler im eigenen Programm:
jur|nodes führt zwei getrennte Ordnerbäume mit je eigenen Nummern, und die
Nummer des einen wurde am Pfad des anderen abgefragt. Eine frühere Fassung
dieser Anfrage hätte dem Hersteller einen Fehler vorgehalten, den es nicht
gibt; sie wurde zurückgezogen.

---

## Was beizulegen ist

Wenn diese Anfrage hinausgeht:

1. **Nichts aus einer Akte.** Keine Aktenkennung, kein Betreff, kein
   Dateiname — die Fragen oben brauchen nichts davon.
2. Die **Ausgabe von `JURNODES-PRUEFEN.bat`** darf mit: Sie enthält
   Feldnamen, Anzahlen, Statuswerte und Längen, aber keinen Akteninhalt. Eine
   fremde Aktenkennung erscheint darin nur maskiert.
   *Vor dem Abschicken ein Blick hinein* — der Wortlaut einer Abweisung kommt
   vom Server, nicht vom Programm, und könnte im Einzelfall ein Stück der
   Anfrage zurückgeben.
3. Die **Fassungsnummer**, auf die sich die Fragen beziehen: **1.0.2**.
