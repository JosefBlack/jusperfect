# Was von jur|nodes noch fehlt — Stand 08.10.2026 (zweite Fassung)

**Das Meiste ist beantwortet, und zwar aus der Beschreibung selbst.** Diese
Datei nennt nur noch, was wirklich offen ist.

> **Berichtigung vom 08.10.2026.** Die Fassungen vom 06. und 07.10.2026
> fragten nach Dingen, die in `schnittstelle/jurnodes-api-1.0.2.json` längst
> stehen. Der Grund: Die Beschreibung nennt zu **jedem** der 94 Aufrufe das
> benötigte Recht — aber im Fließtext des Feldes `description`, hinter der
> Erläuterung, nicht als eigenes Feld. Dort wurde nicht gesucht. Die Fragen
> 2 und 3 der alten Fassung waren damit überflüssig; sie stehen unten unter
> „Was sich erledigt hat", damit niemand sie wieder stellt.

---

## Das ist keine Frage an den Hersteller, sondern eine Aufgabe

### Dem Schnittstellenbenutzer fehlt ein Recht: `search:correspondence`

Die Beschreibung sagt es wörtlich:

> `POST /correspondence/search` — *„Listet alle Korrespondenzen (derzeit einer
> Akte) auf. **Benötigte Rechte: search:correspondence**"*

und zu Status 401: *„Authentifizierung ungültig"*.

Der Lauf vom 07.10.2026 passt genau darauf. Was mit demselben Zugang
**funktioniert** hat, und welches Recht dahintersteht:

| Aufruf | Benötigtes Recht | Ergebnis |
|---|---|---|
| `GET /record/search` | `search:records` | 200 |
| `GET /record` | `read:records` | 200 |
| `GET /relation/search` | `search:relation` | 200 |
| `GET /todo/search` | `search:todo` | 200 |
| `GET /file-system/folder/content` | `read:folder` | 200 |
| `GET /file-system/file/download` | `download:file` | 200 |
| **`POST /correspondence/search`** | **`search:correspondence`** | **401** |

Sechs Rechte sind gesetzt, eines fehlt — und genau dessen Aufruf wird
abgewiesen. Das ist kein Zufall und keine Vermutung mehr.

**Eine andere Anmeldung ist es nicht.** Nachgezählt am 08.10.2026: Alle 94
Aufrufe der Beschreibung tragen **denselben** Sicherheitsblock, nämlich
`X-Auth-User` und `X-Auth-Key` — ohne eine einzige Ausnahme. Es gibt in dieser
Schnittstelle kein zweites Anmeldeverfahren, auf das `/correspondence/search`
ausweichen könnte. Es bleibt das Recht.

Auch der Antwortkörper passt: Für 400 und 405 beschreibt der Hersteller
`{"message", "errorStrings"}`, für **401 keinen Körper** — und genau leer
(`{}`) kam er im Lauf zurück.

> **Frage:** Wo wird `search:correspondence` am Schnittstellenbenutzer
> gesetzt — in jur|nodes selbst, oder muss der Hersteller es freischalten?

> **Zu tun:** In jur|nodes dem Schnittstellenbenutzer `user_2` das Recht
> **`search:correspondence`** geben. Danach genügt ein weiterer Lauf von
> `JURNODES-PRUEFEN.bat`.

*Ein Hinweis zur Adresse, damit niemand danach sucht:* Die Oberfläche der
Dokumentation zeigt unter einzelnen Aufrufen eine Adresse ohne Vorsatz, etwa
`https://dortschy-thunert.jur-nodes.net/post/download`. Das ist eine Vorgabe
des Anzeigewerkzeugs — die Beschreibung selbst führt **keinen** Abschnitt
`servers`. Die benutzte Adresse mit `/api/extern/v1/<Kennung>` ist richtig:
Mit ihr haben am 07.10.2026 sechs andere Aufrufe mit 200 geantwortet.

### Die Vermerke selbst brauchen kein weiteres Recht

`GET /record/note` verlangt `read:records` — dasselbe Recht wie `GET /record`,
und das antwortet bereits mit 200. Sobald die Liste da ist, sind die Vermerke
lesbar.

### Später, für den Inhalt von Mail, beA und Post

Der Hersteller trennt die Rechte sauber nach **Postfach** und **Akte**. Für
jusperfect wird ausschließlich die Akte gebraucht, nie ein Postfach:

| Zweck | Benötigtes Recht | **Nicht** nötig |
|---|---|---|
| E-Mail aus der Akte | `download:mail:record` | ~~`download:mail:postbox`~~ |
| beA-Nachricht aus der Akte | `read:bea:record`, `download:bea:record` | ~~`:postbox`~~ |
| Post | `read:post`, `download:post` | — |

Das deckt sich mit der Vorgabe der Kanzlei vom 07.10.2026: kein Zugriff auf
E-Mail-Postfach und beA-Postfach. Die Rechte mit `:postbox` bitte **nicht**
setzen.

---

## Was wirklich offen bleibt

### 1. Welche Dateiart gibt `POST /mail/download` zurück?

**Nur noch bei der E-Mail offen** — bei beA und Post nicht mehr, siehe unten.

Die Beschreibung sagt `application/octet-stream` und nicht, welches Format
diese Bytes haben. Anders als bei beA und Post gibt es zur E-Mail **keinen
zweiten Aufruf**, der Dateiname oder Endung nennen würde: `POST /mail/download`
nimmt allein `{mailIdentifier}` und gibt Bytes zurück.

> **Frage:** Ist das eine `.eml`, eine Outlook-`.msg`, ein PDF — oder je nach
> Herkunft verschieden? Setzt der Server einen `Content-Disposition`-Namen?

*Die Frage erledigt sich womöglich von selbst:* `JURNODES-PRUEFEN.bat` misst
die Signatur der ersten Bytes, sobald das Recht steht — ohne Inhalt. Die
Texterkennung liest `.eml`, `.msg` und PDF bereits.

### 2. Wofür steht `Record.correspondenceFolderId`?

Dreimal geprüft, dreimal derselbe Befund. Zuletzt am 07.10.2026: Die Akte ist
am **30.07.2026** angelegt, die Ordner hinter ihrem `correspondenceFolderId`
tragen Ablagen ab dem **15.12.2022** — fünf Ordner, siebzehn Dateien, alle
älter als die Akte.

> **Frage:** Benennt das Feld einen Ordner *dieser* Akte — dann wäre der Wert
> falsch — oder etwas anderes, etwa einen gemeinsamen Ablagebereich?

*Warum das zählt:* Eine Kanzlei darf Unterlagen eines Mandats nicht in einem
anderen zeigen. Das Programm liest diesen Ordner seit dem 05.10.2026 nicht
mehr und holt seit dem 07.10.2026 auch keine Datei mehr daraus.

### 3. Was bedeutet `isInbox`?

`CorrespondenceModel.isInbox` ist eine Zahl.

> **Frage:** Heißt `1` „eingegangen" und `0` „ausgegangen"?

Für eine Akte ist die Richtung eines Schreibens wesentlich.

### 4. Ein fehlender Schrägstrich in der Beschreibung

Bei einem von 85 Pfaden fehlt der führende `/`:
`correspondence/get-by-reference`. Die übrigen 84 beginnen mit `/`.

> **Frage:** Lautet der Pfad `/correspondence/get-by-reference`?

### 5. Gibt es eine neuere Fassung als 1.0.2?

Falls ja, bitte diese.

---

## Was sich erledigt hat — bitte nicht wieder fragen

**Woher `attachmentId` beim beA kommt — und welche Dateiart.** Aus
`GET /bea?beaIdentifier=…`: Die Antwort `BeaMessage` führt `attachments`, eine
Liste von `BeaMessageAttachment` mit `id`, **`fileName`**, `type`, `size`. Der
Dateiname sagt die Art; sie muss nicht erfragt werden.

**Woher `postFileUniqueKey` bei der Post kommt — und welche Dateiart.** Die
Kette ist vollständig und geschlossen:

| Schritt | Aufruf | Hinein | Heraus |
|---|---|---|---|
| 1 | `POST /correspondence/search` | `recordIdentifier` | Eintrag mit `identifier`, `referencePost` |
| 2 | `POST /post/get-files` | `correspondenceIdentifier`, `postId` | Liste `PostFileModel` |
| 3 | `POST /post/download` | `correspondenceIdentifier`, `postId`, `postFileUniqueKey` | die Bytes |

`PostFileModel` führt `uniqueKey` (→ `postFileUniqueKey`), `name` und
**`extension`**. Damit ist auch bei der Post die Dateiart bekannt, bevor
heruntergeladen wird. Einzeln geht es auch: `POST /post-file/get` nimmt
wahlweise `id` **oder** `uniqueKey`.

*Bestätigt am 08.10.2026* an den Beispielkörpern aus der Oberfläche der
Herstellerdokumentation — Feld für Feld deckungsgleich mit 1.0.2.

**Ob `referenceMail` dasselbe ist wie `mailIdentifier`.** Die Beschreibung
führt `POST correspondence/get-by-reference` mit je einem Feld pro
Verweisart — `mailIdentifier`, `beaIdentifier`, `postId`, `noteId` … —, und
die Typen stimmen Feld für Feld mit den `reference…`-Feldern des
Korrespondenzeintrags überein. Für `referenceNote` ist es bereits gemessen.
Nachgemessen wird es trotzdem, sobald das Recht steht; geraten wird nicht.

**Über welchen Pfad die E-Akte zu erreichen ist.**
`POST /correspondence/search` mit `recordIdentifier`. Steht seit 1.0.2 fest.

**Zum Befund vom 02.10.2026** — drei Schriftstücke einer fremden Akte in einer
Bausache — ist nichts zu fragen. Es war ein Fehler im eigenen Programm: zwei
getrennte Ordnerbäume mit je eigenen Nummern, und die Nummer des einen wurde
am Pfad des anderen abgefragt.

---

## Was beizulegen ist

1. **Nichts aus einer Akte.** Keine Aktenkennung, kein Betreff, kein
   Dateiname — die Fragen oben brauchen nichts davon.
2. Die **Ausgabe von `JURNODES-PRUEFEN.bat`** darf mit: Feldnamen, Anzahlen,
   Statuswerte, Längen, kein Akteninhalt; eine fremde Aktenkennung nur
   maskiert. Vor dem Abschicken ein Blick hinein — der Wortlaut einer
   Abweisung kommt vom Server.
3. Die **Fassungsnummer**: **1.0.2**.
