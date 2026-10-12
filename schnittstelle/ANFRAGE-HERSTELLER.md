# Was von jur|nodes noch fehlt — Stand 11.10.2026

**Fast alles ist beantwortet.** Der Lauf vom 08.10.2026 am Server der Kanzlei
hat die letzten Fragen gemessen statt gefragt. Offen ist **eine einzige**
Kleinigkeit; sie steht unten. Die lange Liste darunter ist Gedächtnisstütze — sie sagt,
was **nicht** mehr zu fragen ist.

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

**Das ist keine Vorsichtsmaßnahme, sondern die Sache selbst.** Vorgabe der
Kanzlei, bestätigt am 12.10.2026:

> *„Alle E-Mails und Vermerke werden in der E-Akte abgespeichert. Es macht
> daher keinen Sinn und wäre sogar kontraproduktiv, wenn das Postfach
> ausgelesen wird, in welchem sich alle Akten befinden. Das Gleiche gilt für
> die beA-Eingänge."*

Im Postfach liegt die Post **aller** Mandate des Hauses. Was zu dieser Akte
gehört, ist in der E-Akte abgelegt und dort vollständig. Ein Postfachzugriff
brächte also nichts Neues und zugleich alles Fremde — ein Blick in Mandate,
die diesen Vorgang nichts angehen (§ 203 StGB).

**Und darauf kommt es an: Der Aufruf entscheidet es nicht, das Recht tut
es.** `POST /mail/download` und `GET /bea` sind je **ein** Aufruf für beide
Fälle; die Beschreibung nennt zu jedem zwei Rechte, `…:postbox` und
`…:record`. Welche Nachrichten der Server herausgibt, hängt allein davon ab,
welches davon am Schnittstellenbenutzer gesetzt ist. Darum darf das
Postfachrecht nicht gesetzt werden — nicht „nur zum Ausprobieren".

Die drei Aufrufe, die **ausschließlich** das Postfach betreffen, ruft das
Programm nicht auf und wird es nicht: `GET /bea/postbox/search`,
`GET /bea/folder/search`, `GET /bea/search`. Seit dem 12.10.2026 hält eine
Prüfung das fest, statt es nur zu versprechen.

### Was ausdrücklich **nicht** gesetzt werden soll

Alles Schreibende: `write:records`, `write:correspondence`, `write:file`,
`write:folder`, `delete:file`, `delete:folder`, `update:…`, `create:…`,
`generate:documents`, `file_upload` und die übrigen.

**Warum das zählt.** Dass jusperfect eine Akte nicht verändern *kann*, ist
heute keine Zusage des Programms, sondern eine Eigenschaft des Schlüssels.
Ein Fehler im Programm — und es gab im Oktober mehrere — kann dann nichts
anrichten. Ein Schlüssel mit allen Rechten nähme dieses Netz weg und ließe
nur das Versprechen übrig. Dasselbe gilt für die `:postbox`-Rechte, aus dem
Grund, der eine Ebene weiter oben steht.

## Was wirklich offen bleibt

Nach dem Lauf vom 08.10.2026 am Server der Kanzlei ist es **sehr wenig**.

### 1. Ein fehlender Schrägstrich in der Beschreibung

Bei einem von 85 Pfaden fehlt der führende `/`:
`correspondence/get-by-reference`. Die übrigen 84 beginnen mit `/`.

> **Frage:** Lautet der Pfad `/correspondence/get-by-reference`?

### ~~2. Gibt es eine neuere Fassung als 1.0.2?~~ — **beantwortet: nein**

*Auskunft der Kanzlei vom 12.10.2026: nein.* **1.0.2 ist die geltende
Fassung.** Damit ist auch der Vergleich vom 11.10.2026 bestätigt: Drei Aufrufe
aus der Oberfläche der Herstellerdokumentation — `POST /correspondence/add`,
`GET /correspondence`, `POST /correspondence` — waren gegen
`jurnodes-api-1.0.2.json` Feld für Feld und Wort für Wort deckungsgleich, mit
`CorrespondenceModel` in 22 Feldern derselben Reihenfolge. Die Oberfläche
zeigte keine andere, weil es keine andere gibt.

**Was daraus folgt, und das ist mehr als eine erledigte Frage:** Die
Beschreibung im Programmordner ist nicht nur *eine* Fassung, sondern **die**
Fassung. Was dort nicht steht, gibt es nicht — und was dort steht, ist zu
lesen, bevor gefragt wird. Viermal in dieser Woche lag die Antwort in dieser
Datei: die benötigten Rechte, die Herkunft von `attachmentId` und
`postFileUniqueKey`, die Bedeutung von `isInbox`, und die Seitenzählung.

---


## Durch den Lauf vom 08.10.2026 beantwortet

`POST /correspondence/search` an einer Akte der Kanzlei: **Status 200, 26
Einträge** (22 `mail`, 4 `note`), eine Seite.

**Die Vermerke sind lesbar.** Drei wurden über
`GET /record/note?id=…&record=…` geholt — mit beiden Pflichtparametern, mit
Inhalt, `type=phonecall`, `contentType=html`.

**Die Dateiart hinter `POST /mail/download` ist `.eml`.** Gemessen: Status
200, 8 753 880 Bytes, `Content-Type: application/octet-stream`, und
`Content-Disposition: inline; filename="Mail.eml"`. Die Texterkennung des
Programms liest `.eml` bereits.

**`referenceMail` ist `mailIdentifier`.** Der Wert aus dem
Korrespondenzverzeichnis wurde unverändert in `/mail/download` eingesetzt und
hat funktioniert. Keine Ableitung mehr, sondern eine Messung.

**Wofür `correspondenceFolderId` steht — und es war unser Fehler.** Die
Nummer gehört in den Ordnerbaum der **Korrespondenz** und wurde gegen den Baum
des **Dateisystems** abgefragt. Beide Bäume führen eine Nummer 2871, und sie
haben nichts miteinander zu tun. Der Lauf zeigt es: Alle 26 Einträge der
E-Akte nennen als `folderId` genau jene 2871, und ihre Poststempel liegen
innerhalb der Lebenszeit der Akte. Die „Dateien älter als die Akte" lagen im
falschen Baum. **Dazu ist nichts zu fragen.**

---

## Was sich erledigt hat — bitte nicht wieder fragen

**Was `isInbox` bedeutet — es stand in der Beschreibung.** Nicht im
Beispielkörper, sondern in der Eigenschaft selbst:

> `isInbox` · number · *„1 = Eingang, 0 = Ausgang, **-1 = Neutral/Unbekannt**"*

So steht es in `schnittstelle/jurnodes-api-1.0.2.json`, gleichlautend in
beiden Schemata — `Correspondence` (schreibend) und `CorrespondenceModel`
(lesend). `POST /correspondence/search` gibt `CorrespondenceSearchResponse`
zurück, dessen `elements` genau dieses `CorrespondenceModel` sind. Die
Richtung ist also bei jedem Eintrag der E-Akte mitgeliefert, ohne einen
zweiten Aufruf.

**Der dritte Wert ist der Grund, warum Raten falsch gewesen wäre.** Die
Vermutung lautete „1 heißt eingegangen, 0 ausgegangen". Sie ist richtig — aber
unvollständig: `-1` heißt *weder noch*. Wer das Feld als Ja/Nein liest, schreibt
über jedes neutrale Schreiben „Ausgang". Ein falsch herum beschriftetes
Schriftstück in einer Handakte ist teurer als ein gar nicht beschriftetes.

*Gefunden am 11.10.2026* an den Beispielkörpern aus der Oberfläche der
Herstellerdokumentation. Die Beispiele selbst zeigen nur den Platzhalter
`"isInbox": 0`; die Bedeutung steht im Schema dahinter, das die Oberfläche
erst auf Aufklappen zeigt.


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
