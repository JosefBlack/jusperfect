# Was von jur|nodes noch fehlt — Stand 06.10.2026

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
3. Die **Fassungsnummer**, auf die sich die Fragen beziehen: **1.0.2**.
