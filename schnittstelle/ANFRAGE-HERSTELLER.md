# Was von jur|nodes noch fehlt — Stand 08.10.2026 (dritte Fassung)

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

## Zurückgezogen: der Status 401 war unser eigener Fehler

**Bitte diese Frage nicht stellen.** Die Fassungen vom 07. und 08.10.2026
führten hier, als erste und dringlichste Frage, den Status 401 auf
`POST /correspondence/search` und schlossen daraus, dem Schnittstellen-
benutzer fehle das Recht `search:correspondence`.

**Das war falsch, und der Fehler lag im Prüfbogen.** Gefunden am 08.10.2026:

Der Prüfbogen hängte den Schlüssel `X-Auth-Key` nur an GET-Anfragen an; die
Grundkopfzeilen des Clients tragen `X-Auth-User`, aber nicht den Schlüssel.
**Jeder POST ging damit ohne Schlüssel hinaus.** Im Lauf vom 07.10.2026 war
genau ein POST dabei — `/correspondence/search` —, und alle sechs übrigen
Aufrufe waren GET. Deshalb sah es aus wie ein Rechteproblem an genau diesem
einen Pfad.

Der Server hatte die ganze Zeit recht: Ohne Schlüssel ist die
Authentifizierung ungültig. Genau das sagt er mit 401.

**Der Betrieb war nie betroffen.** `jusperfect/jurnodes/http_adapter.py` gibt
den Kopf bei jedem Aufruf mit, bei GET wie bei POST. Der Fehler lag allein im
Werkzeug, das Vertrauen schaffen soll.

Berichtigt und durch zwei Prüfungen abgesichert: Der Schlüssel wird jetzt über
alle benutzten Verfahren geschleift, und ein zweiter, nicht umhüllter Client
lässt die Prüfung fallen.

> **An den Hersteller ist dazu nichts zu schreiben.** Die Antwort, welche
> Rechte welcher Aufruf braucht, steht ohnehin in der Beschreibung — zu jedem
> der 94 Aufrufe, im Feld `description` hinter „Benötigte Rechte:".

---

## Welche Rechte der Schnittstellenbenutzer wirklich braucht

Aus der Beschreibung ausgelesen, nicht geraten. **Nur lesende Rechte** — das
Programm schreibt grundsätzlich nicht.

### Jetzt

| Zweck | Recht |
|---|---|
| Akte suchen | `search:records` |
| Akte und Vermerk lesen | `read:records` |
| Beteiligte | `search:relation` |
| Fristen und Aufgaben | `search:todo` |
| Ordner und Inhalt | `read:folder` |
| Datei herunterladen | `download:file` |
| **Korrespondenzliste (E-Akte)** | **`search:correspondence`** |

### Später, für den Inhalt von Mail, beA und Post

Der Hersteller trennt die Rechte nach **Postfach** und **Akte**. Gebraucht
wird ausschließlich die Akte:

| Zweck | Recht | **Nicht** setzen |
|---|---|---|
| E-Mail aus der Akte | `download:mail:record` | ~~`download:mail:postbox`~~ |
| beA aus der Akte | `read:bea:record`, `download:bea:record` | ~~`…:postbox`~~ |
| Post | `read:post`, `download:post` | — |

### Was ausdrücklich **nicht** gesetzt werden soll

Alles Schreibende: `write:records`, `write:correspondence`, `write:file`,
`write:folder`, `delete:file`, `delete:folder`, `update:…`, `create:…`,
`generate:documents`, `file_upload` und die übrigen.

**Warum das zählt.** Dass jusperfect eine Akte nicht verändern *kann*, ist
heute keine Zusage des Programms, sondern eine Eigenschaft des Schlüssels.
Ein Fehler im Programm — und es gab im Oktober mehrere — kann dann nichts
anrichten. Ein Schlüssel mit allen Rechten nähme dieses Netz weg und ließe
nur das Versprechen übrig. Dasselbe gilt für die `:postbox`-Rechte: Ein
Postfachzugriff ist nach Vorgabe der Kanzlei vom 07.10.2026 nicht
erforderlich, weil alles in der E-Akte liegt.

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
