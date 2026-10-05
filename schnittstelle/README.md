# Die Beschreibung der jur|nodes-Schnittstelle

`jurnodes-api-1.0.2.json` ist die **OpenAPI-Beschreibung des Herstellers**,
geliefert von der Kanzlei am 05.10.2026. 85 Pfade, Fassung 1.0.2.

**Sie gehört hierher und nicht in den Anhang einer Nachricht.** Am 05.10.2026
hat ein halber Tag daran gehangen, dass sie nicht vorlag: sechzehn geratene
Pfade, zwanzig geratene Parameternamen, zwei Prüfbogenläufe — und am Ende ein
Fehler im Programm, den ein Blick in diese Datei in zwei Minuten gezeigt hätte.

**Sie enthält keine Mandantendaten.** Keine Aktenzeichen, keine Namen, keine
Adressen, keine Serveradresse — geprüft. Es ist die Beschreibung der
Schnittstelle, nicht ihr Inhalt.

Lesen lässt sie sich mit der Probe, ohne Netz und ohne Zugang:

```
JURNODES-PRUEFEN.bat → bei „Datei mit der Schnittstellenbeschreibung" den Pfad
```

oder

```
python -m jusperfect.jurnodestest --beschreibung schnittstelle/jurnodes-api-1.0.2.json
```

---

## Was am 05.10.2026 daraus hervorging

### 1. Die E-Akte heißt in der Schnittstelle „Korrespondenz"

| | |
|---|---|
| Liste je Akte | `POST /correspondence/search` mit `{"recordIdentifier": "<Akte>", "page": 1}` |
| Antwort | `amountTotal`, `pagesTotal`, `actuallyPage`, `elements[]` |
| Ein Eintrag | `CorrespondenceModel` |

Die **Art** eines Eintrags (`type`) ist eine von neun:

```
mail · bea · post · fax · webnodes · sms · eda · note · file
```

Je nach Art trägt der Eintrag einen Verweis auf den eigentlichen Gegenstand:
`referenceMail`, `referenceBea`, `referencePost`, `referenceFax`,
`referenceWebNodes`, `referenceSMS`, **`referenceNote`**, `referenceFile`.

### 2. Die Vermerke sind Korrespondenzen vom Typ `note`

Der Weg dorthin ist zweistufig:

1. `POST /correspondence/search` → Einträge mit `type: "note"` heraussuchen,
   deren `referenceNote` ist die Nummer des Vermerks.
2. `GET /record/note?id=<referenceNote>&record=<Akten-Identifier>` → der
   Vermerk im Wortlaut.

Ein Vermerk (`RecordNote`) trägt `type` (`note` oder **`phonecall`**),
`subject`, `effectiveDate`, `contentType` (`text` oder `html`) und `content`.

**Telefonvermerke sind damit erfasst** — `type: "phonecall"` mit
`phoneCaller`. Das war der ausdrückliche Wunsch der Kanzlei vom 28.09.2026.

### 3. Warum `/record/note` einen Monat lang mit 405 antwortete

Es braucht **zwei** Pflichtparameter, nicht einen:

```
GET /record/note?id=<Zahl>&record=<Akten-Identifier>
```

Probiert wurden zwanzig Parameterformen — jede mit **einem** Wert. „Bitte Daten
angeben" war wörtlich zu nehmen: Es fehlten Daten, nicht der richtige Name.

### 4. Der Fehler im Programm: zwei Ordnerbäume, ein Namensraum zu wenig

**Das ist der wichtigste Punkt dieser Datei.**

jur|nodes führt **zwei getrennte Ordnerbäume**, jeden mit eigenen Nummern:

| Baum | Gelesen über | In der Akte |
|---|---|---|
| **Dateiordner** | `/file-system/folder/content?folderId=…` | `fileFolderId` |
| **Korrespondenzordner** | `/correspondence/folder`, Inhalt über `/correspondence/search` | `correspondenceFolderId` |

Das Programm hat `correspondenceFolderId` an **`/file-system/folder/content`**
geschickt — eine Nummer aus dem einen Baum an den anderen. Dort gibt es diese
Nummer auch, sie gehört nur zu einem **anderen Ordner**, und zwar zu dem einer
fremden Akte.

Daraus folgt alles, was am 02. und 05.10.2026 aufgefallen ist:

* Die Nummer passte **nie** zur Akte — sie stammt aus einem anderen
  Nummernkreis.
* Sie war **niedrig** — der Korrespondenzbaum hat weniger Ordner.
* Der Inhalt war **älter als die Akte** — es war der Inhalt fremder Akten.
* Die **Oberfläche zeigte ihn unter dieser Akte nicht** — zu Recht: Er gehört
  nicht dazu.

**Es war kein Fehler von jur|nodes.** Die Schnittstelle hat beantwortet, was
gefragt wurde. Gefragt war das Falsche.
