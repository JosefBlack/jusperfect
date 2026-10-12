# Was als Nächstes zu tun ist

Stand: **05.10.2026.** Zweig `2.0`, Fassung `2.0.0.dev`.
1653 Prüfungen grün (`.venv/bin/python -m pytest -q`).
Jüngster Programmstand: `fb66f9e`.

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

**Berichtigt am Abend des 05.10.2026: Das Programm hat NICHT richtig
gearbeitet.** Es hat die Nummer des Korrespondenzordners am Pfad des
Dateisystems abgefragt — zwei getrennte Ordnerbäume, eine Nummer im falschen
Namensraum. Siehe den Abschnitt „Aufgeklärt am 05.10.2026, abends".

**Hinzu kommt:** In der Oberfläche von jur|nodes sind diese Schriftstücke unter
dieser Akte **nicht zu finden**. Die Schnittstelle liefert sie, die Oberfläche
zeigt sie nicht.

**Erledigt — die Anfrage an den Hersteller entfällt.** Die Ursache lag im
Programm; der falsche Weg ist abgeschaltet. Die Akte lässt sich wieder öffnen,
sobald das Aktengedächtnis für sie geleert ist, falls dort noch fremde
Auszüge liegen — einzeln über „vergessen".

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

## „eu-" ist eine Namenskonvention — der Hinweis vom 05.10.2026

**Aus der Kanzlei: „Zürich ist eu-central-2 und nicht eu-central-1. Wir können
den Punkt abhaken."**

Der erste Satz stimmt. Der zweite leider nicht — und zwar aus einem Grund, der
die Sache **schlimmer** macht, nicht besser.

### Was dabei herauskam

Als Nachweis dafür, dass keine Übermittlung in ein Drittland stattfindet, stand
in den Unterlagen der Vorsatz **`eu-`**. Das Programm prüfte ihn genauso:

```python
if not self.aws_region.startswith("eu-"):
```

`eu-central-2` fängt mit `eu-` an. **Die Prüfung hätte Zürich durchgelassen** —
und `eu-west-2`, London, ebenso. Beide liegen außerhalb der EU und des EWR.

| Region | Ort | |
|---|---|---|
| `eu-central-2` | Zürich | Schweiz |
| `eu-west-2` | London | Vereinigtes Königreich |

Für eine Kanzlei, deren Unterlage „Übermittlung in Drittländer: keine" sagt, ist
das der Unterschied zwischen einem Satz, der stimmt, und einem, der sich auf
eine Buchstabenfolge stützt.

### Behoben

`jusperfect/config.py` prüft nicht mehr den Vorsatz, sondern eine
**aufgeschriebene Liste** — `EU_EWR_REGIONEN`: Frankfurt, Irland, Paris,
Mailand, Spanien, Stockholm. Der Fehlertext nennt den Grund statt nur der
Ablehnung:

> `'eu-central-2'` liegt in Zürich, Schweiz – außerhalb der EU und des EWR.

Eine neue EU-Region von AWS wird abgewiesen, bis sie in der Liste steht. Das ist
die sichere Richtung, und die Meldung sagt, wo die Liste steht. 16 Prüfungen
halten es fest.

### Die Zugriffsrichtlinie — ~~offen~~ **erledigt am 05.10.2026**

Auf ausdrückliche Anweisung der Kanzlei („Ja, bau es in die Zugriffsrichtlinie
ein"). `infra/iam-nur-claude.json` und `infra/IAM.md` sind geschützte Dateien.

* Die Anweisung heißt jetzt **`NurEuUndEwr`** und prüft mit `StringNotEquals`
  gegen die sechs namentlich genannten Regionen. **In der ganzen Datei steht
  kein `eu-*` mehr** — auch nicht in den Ressourcen von `ClaudeAufrufen`,
  `SchutzgelaenderAnwenden` und `KeinAnderesModell`.
* Beim **Inferenzprofil** bleibt der Stern an der Stelle der Region. Dort stand
  nie `eu-*`, und jede weitere Zeile wäre eine weitere Stelle, an der die
  Kontonummer von Hand einzutragen ist — die Fehlerquelle vom 02.10.2026.
* **Eine zweite Lücke mitgeschlossen:** Am 23.09.2026 war gemessen worden, dass
  `bedrock:ApplyGuardrail` **zwei** Ressourcenarten braucht — `guardrail` und
  `guardrail-profile` —, sobald das regionsübergreifende Profil benutzt wird.
  In der Datei stand nur die erste. Jetzt stehen beide. Wer die Datei einsetzt,
  ohne die zweite Zeile, kann dieselbe Ablehnung wieder bekommen wie am
  02.10.2026.
* 26 Prüfungen halten das Ergebnis fest, darunter eine, die **Richtlinie und
  Programm gegeneinander** prüft: Laufen die beiden Regionslisten auseinander,
  erlaubt das eine, was das andere verbietet, und niemand merkt es.

**Einzusetzen in der Kanzlei:** AWS-Konsole → IAM → Richtlinien →
`jusperfect-nur-claude` → Bearbeiten → JSON → Inhalt durch
`infra\iam-nur-claude.json` aus dem neuen Programmordner ersetzen → speichern.
AWS hält höchstens fünf Fassungen; beim Speichern die älteste abwählen, wenn er
danach fragt.

### Was weiterhin offen bleibt

1. **Die Auskunft von AWS.** **Beides trifft die eigentliche Frage ohnehin nicht.** `aws:RequestedRegion`
   und die Einstellung betreffen die Region, an die der **Aufruf** geht —
   Frankfurt. Wohin das Inferenzprofil und `eu.guardrail.v1:0` **intern**
   verteilen, entscheidet AWS und steht in keiner Richtlinie.
3. **Neu dazugelernt:** Auch eine Antwort von AWS, die ausschließlich
   `eu-`-Regionen nennt, beantwortet die Frage **nicht**. Es kommt auf die
   Regionen selbst an. Die Frage an den AWS-Support ist entsprechend zu
   stellen: *welche Regionen, namentlich.*
4. **Eine neue EU-Region von AWS** wird jetzt an zwei Stellen abgewiesen, bis
   sie eingetragen ist: in `jusperfect/config.py::EU_EWR_REGIONEN` und in der
   Richtlinie. Das ist die sichere Richtung — und beide Stellen müssen
   zusammen geändert werden. Eine Prüfung achtet darauf.

**Zum fünften Mal an diesem Tag dieselbe Form:** Eine Prüfung, die den Namen
misst statt der Sache, misst etwas anderes als die Sache.

---

## Die Zweitprüfung vom 05.10.2026 — 13 Befunde

Die Kanzlei hat das Projekt von einer zweiten KI prüfen lassen. **Der Bericht
ist ernst zu nehmen.** Er liegt unverändert in `zweitpruefung/`, zusammen mit
17 Gegenproben.

**Ich habe alle 17 am eigenen Bestand nachlaufen lassen: alle grün.** Bei
diesen Gegenproben heißt grün *die Lücke besteht*. Kein Befund ist auf Zuruf
übernommen, keiner ließ sich entkräften.

> **Der eigentliche Befund steht nicht in der Liste:** Alle 1625 vorhandenen
> Prüfungen waren grün — und haben nichts davon gezeigt. Eine Prüfung, die den
> gewollten Weg misst, misst nicht den Fehlerweg.

### Was sofort behoben ist

**F02.1 — und es war mein Fehler von heute Vormittag.** Die gespeicherte
Aktenanalyse wurde beim Entfernen eines Dokuments **nicht** mitbereinigt: Ein
Chronologieereignis aus dem gelöschten Dokument stand anschließend weiter in
der Analyse. Die Zusage lautete „samt allem Abgeleiteten", eine eigene Prüfung
behauptete sie — und keine prüfte sie für die Analyse, weil es die Analyse beim
Schreiben jener Prüfung noch nicht gab.

Behoben, mit sechs Prüfungen. Fällt aus der Analyse etwas heraus, trägt sie
jetzt den Satz *„Aus dieser Analyse wurde nachträglich ein Dokument entfernt …
der Rest ist nicht neu gerechnet."* — eine Analyse, der ihre Grundlage fehlt,
sieht sonst genauso vollständig aus wie eine vollständige.

**Die Lehre:** Ein neues Feld im Gedächtnis ist nicht fertig, wenn es
geschrieben und angezeigt wird. Es ist fertig, wenn auch gesagt ist, **was beim
Löschen damit geschieht.**

**F09 — die Fristensperre, behoben am 05.10.2026.** Drei Sätze kamen durch,
obwohl keiner ein Datum aus der Akte nannte:

| Satz | Warum er durchkam |
|---|---|
| „Die Klagefrist endet am **26.05.26**." | zweistelliges Jahr — das Datumsmuster kannte es nicht |
| „Die Klagefrist endet am **26. Mai**." | Monatsname ohne Jahr — dasselbe |
| „Die Klage muss **bis zum 26.05.2026** eingereicht werden." | kein Wort der Fristliste |

Gebaut ist **keine größere Wortliste.** Der Bericht hat recht: Über beliebige
natürliche Sprache beweist eine Wortliste nichts. **Die Beweisrichtung ist
umgekehrt.**

Vorher: *Ein Datum fällt, wenn ein Fristwort danebensteht.*
Jetzt: *Jedes Datum muss sich auf eine Stelle zurückführen lassen, die das
Programm selbst mitgeschickt hat* — eine Passage, deren Kopfzeile (Titel und
Dokumentdatum) oder den Fristenkalender aus jur|nodes. Findet sich dort nichts,
wird es ersetzt, ganz ohne Wortliste. Denn woher sollte es sonst kommen.

Die Wortlisten sind nicht verschwunden, sie entscheiden nur nicht mehr über die
Zusage: Eine behauptet weiter ein *Ende* und verschärft dann die Prüfung — die
Akte muss das Datum selbst als Endpunkt führen —, die andere wählt nur noch den
**Wortlaut des Ersatzes**. Fällt eine von beiden aus, wird weniger streng oder
unschöner geprüft, nie gar nicht.

**Was dadurch strenger wird, und das gehört gesagt:** Ein erfundenes Datum
fällt jetzt auch dann, wenn es nach keiner Frist klingt. „Die Besprechung
findet am 12.09.2026 statt" ohne jede Stelle in der Akte ist ebenfalls
erfunden. Eine Prüfung, die bisher ausdrücklich das Gegenteil verlangte, ist
umgeschrieben — sie war die Lücke.

**Damit kein richtiges Datum mitgerissen wird**, zählt als Stelle nun auch die
Kopfzeile der Passage: Das Dokumentdatum steht in den Stammdaten und fast nie
im Text, und der Auftrag verlangt, dass das Modell es nennt. Als *Endpunkt*
taugt die Kopfzeile dagegen nicht — „Kündigung, datiert 04.05.2026" würde sonst
jede behauptete Kündigungsfrist zum Briefdatum belegen.

**Nachgemessen, nicht behauptet:** Über alle fünf Testakten (903.720 Zeichen)
stehen 248 Daten im Text. **Keines davon** wird in einem neutralen Satz
gestrichen. Die Form ohne Jahr („26.05.") kommt darin genau einmal vor; sie
gilt nur hinter einem Anlass („am", „bis zum", „Frist …"), damit aus einer
Vertragsziffer „2.1." kein Datum wird.

Behoben mit 12 neuen Prüfungen in `tests/test_fristen.py`; Gegenprobe 10 ist
dreifach rot, also geschlossen. **1666 Prüfungen grün.**

**F01 — das Serverprotokoll, behoben am 05.10.2026.** Die HTTP-Antwort war
sauber, das Protokoll nicht. Der Weg, den niemand gesehen hatte:

1. Der Anbieter behält die AWS-Ausnahme: `raise ProviderFehler(…) from e`.
2. Der eigene Handler für `Exception` sendet eine saubere 502.
3. **Starlette wirft danach erneut** — so arbeitet `ServerErrorMiddleware`,
   wenn ein Handler für `Exception` eingetragen ist.
4. Uvicorn protokolliert den vollständigen Traceback **samt Ursache**.
5. `access_log=False` schaltet diesen Kanal nicht ab, und die Feldsperren aus
   `security/protokoll.py` kommen auf diesem Weg nie zum Einsatz.

Gebaut sind zwei Riegel, unabhängig voneinander, in
`jusperfect/fehlergrenze.py`:

* **Eine eigene ASGI-Grenze.** Sie liegt zwischen `ServerErrorMiddleware` und
  der Anwendung und lässt **keine** Ausnahme nach außen. Uvicorn sieht nichts,
  also protokolliert es nichts. Dazu hat jetzt **jeder Fehlertyp seinen
  eigenen Handler** statt eines gemeinsamen für `Exception` — die behandelt
  Starlettes `ExceptionMiddleware`, ohne erneut zu werfen.
* **Kein Traceback in irgendein Protokoll.** An der einen Stelle, durch die
  jeder Protokolleintrag geht, wird die Ausnahme abgenommen und durch die
  **Namen** der Kette samt Code-Stelle ersetzt:
  `ProviderFehler (bedrock.py:241) <- ClientError (client.py:1057)`.
  Klassennamen, Dateinamen und Zeilennummern sind Programmtext; ein Wortlaut
  geht nie mit, auch nicht der eigene. Das wirkt für **jeden** Kanal im
  Prozess — Uvicorn, botocore, httpx, und was später dazukommt. botocore und
  die übrigen lauten Bibliotheken stehen zusätzlich auf WARNUNG, weil sie auf
  DEBUG die vollständige Anfrage mitschreiben.

**Kein Pfad im Protokoll.** Eine Fehlerzeile nennt Verfahren, Vorgangsnummer
und Kette — nicht den Pfad. Ein Pfad trägt Sitzungs- und Aktenkennungen;
genau deshalb stehen die Zugriffsprotokolle aus. Dieselbe Vorgangsnummer steht
in der Antwort, damit „inhaltsfrei" nicht „unauffindbar" heißt.

**Geprüft am echten Weg, nicht am nachgebauten.** Die neue Prüfung schickt die
Anfrage durch Uvicorns eigene `RequestResponseCycle` mit einer echten
h11-Verbindung; ersetzt ist allein der Netzanschluss. Die Gegenprobe hatte
genau dort aufgehört. 19 Prüfungen in `tests/test_fehlergrenze.py`,
Gegenproben 12 und 13 rot.

**Was ausdrücklich offen bleibt und kein Versehen ist:** Ein Traceback auf der
Konsole beim *Start* — eine falsch gesetzte Umgebungsvariable etwa — bleibt
stehen. Dort ist er die einzige Auskunft, die die Kanzlei hat, und er trägt
keinen Akteninhalt: Zu diesem Zeitpunkt ist keine Akte geladen.

**F04 und F05 — jeder angezeigte Modelltext, behoben am 05.10.2026.** Die
Belegpflicht galt für die Antwort auf eine Frage und für die strukturierten
Listen. Für vier Wege galt sie nicht:

| Weg | Was durchkam |
|---|---|
| **Entwurf** | ein vollständig erfundener Entwurf, HTTP 201, leere Quellenliste. Die leere Liste sagt es dem Programm; gesehen hat sie niemand |
| **Kernaussage der Eingangsprüfung** | eine erfundene Kernaussage ohne jeden Beleg |
| **Hinweise des Modells** | *„Das Wort ‚Hinweis' macht einen vom Modell gelieferten Sachverhalt nicht automatisch zu einem ungefährlichen Systemhinweis."* Richtig |
| **Reichweite eines Belegs** | er trug alles seit dem vorigen Beleg — auch einen Absatz, der Zeilen vorher stand |
| **Der Strom** | der Rohtext ging hinaus, die Prüfung kam am Ende |

**Die Reichweite war die stillste davon.** Die Prüfung war *nach* dem letzten
Beleg streng und *vor* jedem Beleg großzügig. Niemandem fiel das auf, weil
alle Prüfungen nach erfundenen Belegen suchten und keine nach fehlenden. Ein
Beleg reicht jetzt bis zur nächsten Einheitsgrenze zurück: bis zur Leerzeile,
bis zum Beginn des Aufzählungspunktes, bis zur Überschrift.

Die Grenze ist bewusst der **Absatz** und nicht der Satz. Die Anweisung
lautet, jede Tatsachenaussage mit einem Beleg zu schließen; schreibt das
Modell zwei Sätze und setzt den Beleg ans Ende, ist das die vorgesehene Form.
Ein Satzmaßstab zerschnitte fast jede richtige Antwort. Das bleibt eine Grenze
dieser Prüfung, und sie steht im Modulkopf, statt verschwiegen zu werden.

**Der Entwurf bekommt einen eigenen Maßstab, und das ist kein Nachlassen.**
Ein Entwurf ist ein Brief, keine Auskunft über die Akte. Die strenge Prüfung
machte daraus einen Brief, in dem „Sehr geehrte Damen und Herren" durch eine
Entfernungsmarke ersetzt ist. Geprüft wird deshalb: jeder genannte Beleg muss
tragen — sonst fällt die Aussage, nicht nur der Beleg —, und ein Entwurf ohne
einen einzigen tragenden Beleg wird **gar nicht ausgegeben**. Das ist eine
neue Fehlermeldung, die die Kanzlei sehen kann; sie nennt den Grund.

**Der Strom zeigt nur noch Geprüftes.** Bis zur ersten abgeschlossenen Aussage
steht da, *dass* gearbeitet wird — kursiv, mit der Zeichenzahl, ohne Inhalt.
Danach kommt der geprüfte Stand, Aussage für Aussage; die Fristensperre läuft
dabei mit. Das Schreibgefühl bleibt, nur eine Aussage später.

**Getrennt erzeugt, wie der Bericht verlangt:** Was das Programm selbst anfügt
(gekürzt, verworfen, Fristensperre), entsteht **nach** dem Modellaufruf und
kommt an der Belegpflicht gar nicht vorbei. Sonst hätte sie am Ende die
eigenen Meldungen gelöscht — und am lautesten die über zurückgehaltene
Aussagen. Eine Prüfung ohne diese Trennung ging im ersten Anlauf genau so
daneben.

Dazu geschärft: Der Auftragstext sagt dem Modell jetzt ausdrücklich, dass ein
Beleg nur seinen eigenen Absatz trägt, dass Sachverhaltsangaben in die
Kernaussage gehören und nicht in die Schritte, und dass ein Entwurf ohne
tragenden Beleg nicht ausgegeben wird.

24 neue Prüfungen in `tests/test_ausgabepruefung.py`, Gegenproben 1, 2, 3 und
14 rot. **1709 Prüfungen grün.** Im Browser nachgesehen: Der Strom zeigt
zuerst „jusperfect schreibt … (412 Zeichen)", dann die geprüften Aussagen.

**F02.2, F02.3, F03, F06 und F07 — behoben am 05.10.2026.** Fünf Befunde in
einem Zug, weil sie dieselbe Form haben: Eine Zusage galt für den gewollten
Weg und nicht für den zweiten.

| Befund | Was durchkam | Was jetzt gilt |
|---|---|---|
| **F02.2** | ein Satz mit `[Q: D1-…, D2-…]` blieb nach dem Entfernen von D1 stehen; nur der Verweis verschwand | eine Aussage, die das entfernte Dokument auch nur **mitzitiert**, fällt ganz — wie Chronologie und Antworten es schon immer taten |
| **F02.3** | eine offene Sitzung behielt den Auszug; die nächste Frage antwortete darauf, und die Antwort wurde **neu** gespeichert | das Dokument verschwindet aus jeder offenen Sitzung, und ein verspätetes Ergebnis wird an einer Grabmarke erkannt und abgewiesen |
| **F03** | zwei Vorgänge, ein Speicher: Der ältere überschrieb die Löschung des jüngeren | die erwartete Revision hängt am **gelesenen Stand**, nicht in einer Tabelle des Speichers |
| **F06** | ein in einem anderen Fenster geänderter **Betreff** ging ungesehen in den Vermerk und in den Titel | die Prüfsumme deckt die ganze Freigabevorlage: Akte, Art, Betreff, Text |
| **F07** | wem die Akte entzogen war, der konnte den fertigen Entwurf weiter lesen **und freigeben** | die Aktenberechtigung wird bei jedem Entwurfszugriff neu geprüft |

**Die Form dahinter, und sie wiederholt sich:** *„Vergessen" räumt das
Gedächtnis auf* galt — aber nicht für das zweite Fenster. *Die Freigabe ist an
den gesehenen Text gebunden* galt — aber der Betreff war kein Text. *Der
bedingte Schreibzugriff schützt vor Überschreiben* galt — aber die Bedingung
gehörte nicht mehr zu dem Inhalt, den sie schützen sollte.

**Zwei Entscheidungen, die bedacht sind und nicht beiläufig:**

* **Die Sitzung wird nicht geschlossen**, nur das eine Dokument entfernt. Sie
  zu schließen wäre eine Strafe für eine Löschung, die der Bearbeiter selbst
  ausgelöst hat; sein Dialog und seine Belege für alle übrigen Dokumente
  gingen mit.
* **Die Grabmarke** (`vergessene_dokumente`) trägt nur die Kennung, die in
  jur|nodes ohnehin steht — keinen Inhalt. Sie beantwortet die eine Frage, die
  sich sonst nicht beantworten lässt: ob ein Dokument nie hier war oder
  bewusst entfernt wurde. Ein bewusstes Wiedereinlesen nimmt sie zurück, und
  das ist eine eigene Handlung des Bearbeiters — so verlangt es der Bericht.

**Eine strengere Regel kam dabei heraus, die der Bericht nicht genannt hat:**
Ein frisch gebautes Gedächtnis, das nie gelesen wurde, überschreibt nichts
mehr. Wer nicht gelesen hat, weiß nicht, was er überschreibt.

**Im Browser nachgesehen, und dort einen Rest gefunden:** Der Server nahm das
Dokument aus der Sitzung — und die linke Spalte zeigte seinen Text weiter,
weil die Oberfläche nur die Gedächtnisansicht neu zeichnete. Ein Fenster, das
zeigt, was es nicht mehr hat, lädt zum Zitieren ein. Die Oberfläche lädt die
Sitzung jetzt mit nach; nachgesehen und bestätigt.

23 neue Prüfungen in `tests/test_freigabe_umfang.py` und
`tests/test_vergessen_vollstaendig.py`, Gegenproben 4, 5, 6 und 15 rot.
**1736 Prüfungen grün.**

**F08, F10 und F13 — behoben am 05.10.2026. Damit sind alle dreizehn Befunde
abgearbeitet.** Ein gemeinsamer Satz verbindet auch diese drei: *Eine Zusage,
die nur von der Gegenstelle getragen wird, hält das Programm nicht selbst.*

| Befund | Was durchkam | Was jetzt gilt |
|---|---|---|
| **F08** | die Antwort auf `EIGENE-AKTE` trug ausdrücklich eine fremde Kennung samt deren Ordner; geprüft wurde nichts | die zurückgegebene Kennung muss die angefragte sein, sonst bricht der Vorgang ab — und eine Datei muss in dem Ordner liegen, dessen Inhalt gefragt war |
| **F10** | der Nachweis entstand erst **nach** einer erfolgreichen Antwort; schlug der Aufruf fehl, blieb das Fenster leer | die Zeile entsteht, **bevor** das Material hinausgeht; der Ausgang wird danach angehängt |
| **F13** | Frankfurt plus `global.anthropic.…` kam durch die Einstellungsprüfung | jede Modellkennung wird geprüft: ein Profil, das außerhalb der EU verteilt, wird abgewiesen |

**Zu F08, und das gehört gesagt:** Ein Server, der eine falsche Zugehörigkeit
durchweg stimmig ausgibt, lässt sich damit nicht entlarven. Gefangen wird die
Antwort, die sich **selbst widerspricht** — und das ist der Fall, der sich am
Client überhaupt erkennen lässt. Die fremde Aktenkennung geht dabei nicht in
die Fehlermeldung: Sie gehört zu einer anderen Akte.

**Zu F10, zwei Entscheidungen:**

* **Zwei Zeilen in der Ablage, eine beim Lesen.** Angehängt, nicht
  überschrieben — ein Nachweis, den man ändern kann, ist ein schwächerer
  Nachweis. Steht nur die Versuchszeile da, heißt das `unbekannt` und nicht
  `nichts`.
* **Scheitert das Schreiben des Nachweises selbst, geht der Aufruf trotzdem
  hinaus.** Ein Aktenvorgang soll nicht an der Buchführung scheitern. Das ist
  eine Abwägung und keine Nachlässigkeit; sie steht im Code und wird
  protokolliert.
* **Die Wortwahl in der Oberfläche ist zurückhaltend:** „ohne Antwort", nicht
  „übertragen, abgelehnt". Die Zeile entsteht vor der Übergabe; scheitert der
  Aufruf, lässt sich nicht mehr sagen, ob er die Leitung noch erreicht hat.
  „Übertragen" wäre zu viel behauptet, „nichts passiert" zu wenig. Was der
  Eintrag bedeutet, steht jetzt im Kopf des Fensters.

**Zu F13:** Ein Inferenzprofil ist kein Modellname, sondern eine Verteilregel.
Die Aufrufregion ist der Ort, an dem die Anfrage **ankommt**, nicht der, an dem
gerechnet wird. Geprüft wird jede der sieben Modelleinstellungen, nicht nur die
eine — wer ein eigenes Modell je Aufgabe einträgt, kam sonst daran vorbei.

22 neue Prüfungen in `tests/test_herkunft_und_nachweis.py`, Gegenproben 7, 8
und 11 rot. **1758 Prüfungen grün.** Im Browser nachgesehen: Der
Verarbeitungsnachweis zeigt den Regelfall wie bisher und den Fehlerfall mit
einer bernsteinfarbenen Marke daneben.

### F11 — der Vorschlag liegt der Kanzlei vor

`F11-VORSCHLAG.md`, geschrieben am 05.10.2026. Gebaut ist nichts; die
Entscheidung gehört der Kanzlei (`[KANZLEI 18]`).

**Was die Messung ergeben hat und vorher niemand wusste:**

* Alles außer dem Dokumenttext macht **15,4 %** des Materials aus (gemessen an
  vier Testakten): Passagenkopfzeilen 1.685, Beteiligte 990, Fristen 459,
  Aktenkopf 398 Zeichen.
* Bei **13 von 21** Dokumenten trägt der Titel Wörter, die im Text fehlen —
  und das ist fast immer die **Art des Schriftstücks**, nicht eine Person.
  „Kündigungsschreiben", „Polizeiliche Unfallmitteilung", „Mietvertrag". Wo ein
  Name im Titel stand, stand er auch im Text.
* **Die Belege kosten eine Ersetzung nichts.** Der Dokumenttitel in der
  rechten Spalte kommt aus der Passage, die das Programm selbst baut — er geht
  nie durch das Modell. Verloren ginge nur, dass das Modell das Schriftstück
  im Fließtext benennen kann.
* **Gegen den echten Server gibt es kein Titelfeld.** Die Beschreibung des
  Herstellers (API 1.0.2) führt an einer Datei nur `fileName`. Der Titel *ist*
  dort der Dateiname — also geht hinaus, was jemand hineinschreibt.

**Vorgeschlagen:** nur die Art des Schriftstücks statt des ganzen Titels, über
die Liste, die der Zeitstrahl ohnehin führt (`SCHRIFTSTUECKARTEN`). **Die
Richtung des Irrtums stimmt dort**: Was die Liste nicht kennt, geht nicht
hinaus. Das ist das Gegenteil der Fristenwortlisten, die am Vormittag desselben
Tages genau deshalb aufgegeben wurden.

Dazu: Das Aktenzeichen fällt weg — außer beim Entwurf, der „Unser Zeichen"
braucht. Nicht vorgeschlagen ist, Beteiligte und Kurzrubrum herauszunehmen:
Das Modell braucht die Rollen, der Dokumenttext enthält dieselben Namen
ohnehin, und ein Material ohne Rollen hat im September die gegnerische Kanzlei
zur Rechtsschutzversicherung gemacht.

### F11 — entschieden und gebaut, 05.10.2026

Die Kanzlei hat den Vorschlag angenommen. Gebaut ist er noch am selben Tag.

| Vorher | Jetzt |
|---|---|
| `### Passage D2-S1-P1 (Dokument: "Kündigung Reinhold-Özdemir 04.05.pdf", Seite 1)` | `### Passage D2-S1-P1 (Dokument 2 – Kündigung, Seite 1)` |
| `## Akte 115/26 AR: Reinhold-Özdemir ./. Nordwerk …` | `## Akte: Reinhold-Özdemir ./. Nordwerk …` — das Aktenzeichen nur noch beim Entwurf |

**Drei Fälle, an denen sich der Bau messen lässt:**

| Dateiname | Was hinausgeht |
|---|---|
| `Kündigung Reinhold-Özdemir 04.05.pdf` | `Dokument 9 – Kündigung` — der Name bleibt drinnen |
| `Vergleich-Entwurf-NICHT-VERSENDEN.docx` | `Dokument 7` — nichts davon geht hinaus |
| `scan0042.pdf` | `Dokument 8` |

**Ein Fehler beim ersten Anlauf, und er war lehrreich.** „Kündigungsschreiben"
wurde zu „Dokument 2 – **Schreiben**". Beide Wörter stehen in der Liste und
sind neun Zeichen lang; nach Länge sortiert gewann das falsche. Die hintere
Hälfte eines deutschen Kompositums ist die allgemeinere — „Schreiben" sagt
weniger als „Kündigung". Gewählt wird jetzt das Wort, das am weitesten **vorne**
steht, und bei gleichem Anfang das längste.

**Was dabei herauskam und vorher niemand wusste:** Die Belege kosten die
Ersetzung nichts. Im Browser nachgesehen — die Belegkarte nennt weiter
„D1-S1-P1 · Aktenvermerk Erstgespräch, Seite 1", die linke Spalte den vollen
Titel, der Zeitstrahl die Dokumentnamen. Sie kommen alle aus dem Programm und
gingen nie durch das Modell.

17 neue Prüfungen in `tests/test_metadaten_im_material.py`. **Gegenprobe 9 ist
rot — damit sind alle siebzehn Gegenproben rot.** 1779 Prüfungen grün.

`SICHERHEIT.md` trägt weiterhin die zu weite Aussage „nie Dateinamen". Sie ist
jetzt *fast* richtig und bleibt trotzdem falsch: Die Art des Schriftstücks geht
mit. **Die Datei ist geschützt und wartet auf eine ausdrückliche Anweisung.**

### SICHERHEIT.md berichtigt, 06.10.2026

Auf ausdrückliche Anweisung. Zehn Zusagen waren zu weit gefasst — Grundsatz 1
(fremde `/record`-Antwort), 2 (Rechteentzug), 3 (Dateinamen), 4 (Freigabe
ohne Betreff), 5 (Protokoll nur im eigenen Kanal), 6 (Belegpflicht, Umfang und
Reichweite), 8 (Fristensperre), 9 (`eu-*` und das Modellprofil), 11 (Nachweis
erst nach Erfolg) und der technische Grund im Löschkonzept, der seit den festen
Dokumentnummern nicht mehr stimmt. Alles durchgestrichen und berichtigt
daneben; gelöscht ist nichts.

Dazu **Textract ergänzt** — es stand in dieser Datei überhaupt nicht, obwohl es
seit dem 02.10.2026 läuft und eine zweite Übermittlung ist. Mit dem offenen
Nachweis F12.

---

## Die E-Akte, 06.10.2026 — gebaut, aber noch nicht eingeschaltet

**Was die Beschreibung des Herstellers geklärt hat, und es war unangenehm.**
Der Befund vom 02.10.2026 — drei fremde Schriftstücke in einer Bausache — war
**unser eigener Fehler**. jur|nodes führt zwei getrennte Ordnerbäume mit je
eigenen Nummern: das Dateisystem und die Korrespondenz. Das Programm hat die
Nummer aus `correspondenceFolderId` am Pfad des **Dateisystems** abgefragt.
Dort gibt es die Nummer auch — sie gehört nur zu einem anderen Ordner, dem
einer fremden Akte.

**Der richtige Weg ist aktenbezogen:** `POST /correspondence/search` mit
`recordIdentifier`. Eine Verwechslung der Nummernkreise kann dort nicht mehr
vorkommen; gefragt wird nach der Akte, nicht nach einer Ordnernummer. Der alte
Weg ist **ausgebaut** und kommt auch mit der Einstellung nicht zurück.

**Was übernommen wird — und was nicht.** Ein Korrespondenzeintrag ist eine
Hülle: Betreff, Art, Richtung, Datum und ein Verweis darauf, wo der Inhalt
liegt. Von den neun Arten sagt die Beschreibung nur für den **Vermerk** zu, was
als *Text* zurückkommt (`RecordNote.content`, html oder text).

> **Berichtigt am 06.10.2026, noch am selben Tag.** Hier stand: „die
> Beschreibung schweigt über die Antwort". **Das war ungenau.** Sie nennt den
> Download sehr wohl — `POST /mail/download` mit `{mailIdentifier}` gibt
> `application/octet-stream`. Offen sind zwei kleinere Dinge: **welche
> Dateiart** diese Bytes sind (.eml, .msg, PDF — die Texterkennung kann alle
> drei, sie muss nur wissen, welche) und **woher die zweite Pflichtnummer
> kommt**, die beA und Post brauchen (`attachmentId`, `postFileUniqueKey`).
> Beides misst der Prüfbogen jetzt am Server, ohne Inhalt auszugeben.

| | |
|---|---|
| **Vermerke** (Aktenvermerke, Telefonnotizen) | werden Dokumente der Akte |
| **Dateien** der Korrespondenz | liegen im Dateisystem und sind längst dabei |
| **Mail, beA, Post, Fax, SMS, eDA** | werden **gezählt und angezeigt**, nicht übernommen |

**Was fehlt, fehlt sichtbar:** Im Dokumentfenster steht jetzt eine Zeile
„2 Eintrag/Einträge der E-Akte (Mail, beA, Post) stehen hier nicht". Eine
unvollständige Liste sieht sonst aus wie eine vollständige.

**Zwei Dinge aus der Zweitprüfung sind hier eingebaut:**

* **Die Prüfung aus Befund F08, und hier geht sie wirklich.** `RecordNote`
  trägt das Feld `record` — anders als eine Datei lässt sich also nachsehen, ob
  die Antwort zur angefragten Akte gehört. Sie tut es, im Programm und im
  Prüfbogen. Die fremde Aktenkennung geht nicht in die Fehlermeldung.
* **Ein eigener Nummernkreis bekommt einen eigenen Vorsatz.** Eine
  Vermerkkennung heißt `vermerk:17`. Vermerk 17 und Datei 17 haben nichts
  miteinander zu tun; ohne den Vorsatz wäre das Laden eine Verwechslung, die
  niemandem auffiele — genau die Art Fehler, die am 02.10. passiert ist.

**Ein lesender POST-Aufruf ist dazugekommen**, und das gehört begründet: Das
Korrespondenzverzeichnis holt nichts als Daten, der Hersteller verlangt dafür
trotzdem POST. Das Verfahren macht einen Aufruf nicht schreibend. Er steht
getrennt von `vermerk_schreiben` in `_lesen_per_post`, und eine Prüfung zählt
nach: **drei** `self._client.post(` im Adapter — zwei schreibende, ein
lesender. Kommt einer dazu, fällt es auf.

**Eingeschaltet ist nichts.** `JUSPERFECT_KORRESPONDENZ` steht auf aus, bis ein
Lauf am Server der Kanzlei es bestätigt. Der Prüfbogen beantwortet die Frage
jetzt ausdrücklich — ganz unten steht „Kann die E-Akte eingeschaltet werden?"
mit JA, NEIN oder unentschieden und dem Grund. Die Startdatei erklärt die drei
Schritte.

14 Prüfungen in `tests/test_eakte.py`. **1790 Prüfungen grün.** Im Browser
gegen einen nachgebauten Server nachgesehen: Die beiden Vermerke stehen mit
Betreff und Datum in der Liste, der Hinweis nennt die zwei übrigen, und nach
dem Übernehmen steht der Vermerktext wirklich in der linken Spalte.

### Stehende Anweisung der Kanzlei, 06.10.2026

> *„Sollte es Probleme mit jurnodes geben, frage erneut nach den
> Herstellerangaben, die ich vielleicht direkt liefern kann."*

**Das gilt ab jetzt immer und ist keine einmalige Bitte.** Die Lehre vom
05.10.2026 steht dahinter: Vier Wochen lang wurde nach den Vermerken geraten —
zwanzig Parameternamen, jeder mit einem Wert —, und die Beschreibung des
Herstellers hat es in einem Lauf beantwortet. *Die Kanzlei hatte sie die ganze
Zeit.*

Fest eingerichtet, damit es nicht am Gedächtnis hängt:

* `schnittstelle/ANFRAGE-HERSTELLER.md` — die offenen Fragen zum Weiterleiten,
  jederzeit aktuell zu halten. Nur was wirklich fehlt; alles andere steht in
  der Beschreibung.
* Der Prüfbogen verweist bei der E-Akte auf diese Datei und bittet darum, seine
  Ausgabe mitzuschicken.
* **Vor jeder Frage an den Hersteller: erst messen.** Was der Prüfbogen selbst
  beantworten kann, wird nicht gefragt — die Anfrage vom 05.10. hätte dem
  Hersteller einen Fehler vorgehalten, den es nicht gab.

**Offen und beim Hersteller erfragt** (oder durch einen Prüfbogenlauf zu
klären): die Dateiart hinter `/mail/download`, die Herkunft von `attachmentId`
und `postFileUniqueKey`, ob `referenceMail` gleich `mailIdentifier` ist, die
Bedeutung von `isInbox` — und ob es eine Fassung neuer als 1.0.2 gibt.

### Was in den Unterlagen berichtigt ist

| Befund | Was falsch war |
|---|---|
| **F11** | „Das Modell sieht nie Dateinamen und Aktenzeichen." **Falsch.** Das Aktenzeichen steht in der ersten Materialzeile, der Dokumenttitel in jeder Passagenüberschrift — und ohne Titel aus jur|nodes ist das der Dateiname. Neue offene Stelle `[KANZLEI 18]`: Ist dieser Umfang gewollt? |
| **F12** | „Textract verarbeitet, speichert aber nicht." **Nicht belegt.** Für die KI-Dienste von AWS gilt das nur mit einer wirksamen **AI-services-Opt-out-Richtlinie** des Kontos. Neue offene Stelle `[KANZLEI 19]`: diese Richtlinie beschaffen und datiert ablegen. Bis dahin darf die Unterlage keine Nicht-Speicherung behaupten. |
| | Dazu berichtigt: Abschalten heißt `JUSPERFECT_OCR=keine`, nicht `aus`. |

`SICHERHEIT.md` trägt dieselbe zu weite Aussage zu den Dateinamen. **Die Datei
ist geschützt** — sie wird nur auf ausdrückliche Anweisung geändert.

### Die Reihenfolge, die ich vorschlage

Der Bericht schlägt eine vor; ich folge ihr im Wesentlichen, mit einer
Abweichung: **F09 (Fristensperre) gehört nach vorn.** Ein erfundener
Fristablauf ist der einzige Befund, der unmittelbar einen Mandanten schädigen
kann.

1. ~~**F09** — Fristensperre. `26.05.26` und `26. Mai` entgehen dem
   Datumsmuster, „muss bis zum … eingereicht werden" dem Fristwortmuster.~~
   **Erledigt am 05.10.2026** — umgekehrte Beweisrichtung statt größerer
   Wortliste; Gegenprobe 10 dreifach rot. Siehe oben.
   **Als nächstes ist damit F01 der erste Punkt.**
2. ~~**F01** — Fehlerprotokolle abdichten. Der bereinigte Fehler geht sauber
   hinaus, der ursprüngliche steht über `raise … from e` im Traceback des
   Servers.~~ **Erledigt am 05.10.2026** — eigene ASGI-Grenze und kein
   Traceback in irgendein Protokoll; Gegenproben 12 und 13 rot. Siehe oben.
   **Als nächstes sind damit F04/F05 an der Reihe.**
3. ~~**F04, F05** — eine gemeinsame Ausgabeprüfung für **alle** Modelltexte
   (Entwurf, Triage-Kernaussage, Analysehinweise) und kein Rohtext im Stream vor
   der Prüfung.~~ **Erledigt am 05.10.2026** — Gegenproben 1, 2, 3 und 14 rot.
   Siehe oben. **Als nächstes ist damit F02.2/2.3, F03, F06, F07 an der Reihe.**
4. ~~**F02.2/2.3, F03, F06, F07** — Löschung vollständig und beständig,
   S3-Schreiben an die gelesene Revision gebunden, Freigabe über **alle**
   geschriebenen Felder, Aktenrechte bei jedem Entwurfszugriff neu prüfen.~~
   **Erledigt am 05.10.2026** — Gegenproben 4, 5, 6 und 15 rot. Siehe oben.
   **Als nächstes sind damit F08, F10 und F13 an der Reihe.**
5. ~~**F08, F10, F11, F13** — zurückgegebene Aktenidentität prüfen, Nachweis
   **vor** der Übermittlung anlegen, erlaubte Profilkennungen auch in der
   Anwendung begrenzen.~~ **Erledigt am 05.10.2026** — Gegenproben 7, 8 und 11
   rot. **F11 bleibt**: Die Unterlagen sind berichtigt, ob der Metadatenumfang
   gewollt ist, entscheidet die Kanzlei (`[KANZLEI 18]`).
6. **F12** — der Opt-out-Nachweis. Kanzlei, nicht Entwicklung.

Erst danach die E-Akte in den Betrieb. Sie ist eine Erweiterung; die obigen
Punkte sind Zusagen, die nicht halten.

### Wo ich dem Bericht nicht folge

* **„Keine Fristberechnung" ganz aufgeben** — nein. Die Zusage bleibt, der
  Nachweis muss besser werden. Was nicht hält, ist die *Musterprüfung*, nicht
  das Ziel. ~~Offen.~~ **Am 05.10.2026 eingelöst:** Der Nachweis hängt nicht
  mehr an einer Wortliste, sondern an der Stelle, aus der das Datum stammt.
* **Pseudonymisierung erneut untersuchen** (DSFA 3.2) — der Bericht hat recht,
  dass die pauschale Verwerfung zu kurz greift. Aufgenommen, aber nachrangig.
* **F13** — richtig, aber die mitgelieferte Zugriffsrichtlinie nennt bereits
  die sechs Regionen namentlich. Der Befund betrifft die Anwendung, nicht das
  Konto.

### Was der Bericht beantwortet hat

**Die Regionen der Inferenzprofile**, mit Quellenangabe aus der
AWS-Dokumentation vom 05.10.2026: Aus Frankfurt verteilen beide benutzten
Modellprofile **und** `eu.guardrail.v1:0` auf dieselben sechs Regionen.
**Zürich und London sind nicht darunter.**

Das ist der öffentliche Dokumentationsstand und **kein Nachweis für dieses
Konto** — dafür ist `GetInferenceProfile` aus Frankfurt je Modellkennung
abzufragen und datiert abzulegen. Die Auskunft von AWS bleibt erbeten.

---

## Aufgeklärt am 05.10.2026, abends: es war unser Fehler

**Die Kanzlei hat die OpenAPI-Beschreibung des Herstellers geliefert** — jur|nodes
API 1.0.2, 85 Pfade. Sie liegt jetzt im Bestand unter
`schnittstelle/jurnodes-api-1.0.2.json`, die Auswertung in
`schnittstelle/README.md`.

### Der Fehler

jur|nodes führt **zwei getrennte Ordnerbäume**, jeden mit eigenen Nummern:

| Baum | Gelesen über | In der Akte |
|---|---|---|
| Dateiordner | `/file-system/folder/content?folderId=…` | `fileFolderId` |
| **Korrespondenzordner** | `/correspondence/search` | `correspondenceFolderId` |

Das Programm hat `correspondenceFolderId` an **`/file-system/folder/content`**
geschickt. Dort gibt es diese Nummer auch — sie gehört nur zu einem **anderen
Ordner**, und zwar zu dem einer fremden Akte.

Daraus folgt **jede einzelne** Beobachtung vom 02. und 05.10.2026: die niedrige
Nummer (eigener, kleinerer Nummernkreis), der Inhalt von 2022/23 (fremde
Akten), dass die Oberfläche ihn unter dieser Akte nicht zeigt (er gehört nicht
dazu), und dass es bei drei Akten gleich aussah.

> **Der Satz „Das Programm hat richtig gearbeitet" war falsch.** Er stand heute
> früh in `MORGEN.md`, in `DSFA-ANGABEN.md`, im Verarbeitungsverzeichnis, im
> DSFA-Entwurf und in der Anfrage an den Hersteller. Überall berichtigt.
>
> **Die Lehre, und sie ist dieselbe wie fünfmal zuvor an diesem Tag:** Eine
> Nummer ohne ihren Namensraum ist keine Nummer. Dass `2871` eine Antwort
> ergab, hat niemanden misstrauisch gemacht — der Pfad hat sie ja
> angenommen.

### Was die Beschreibung sonst beantwortet

| Frage | Antwort |
|---|---|
| Wo liegt die E-Akte? | `POST /correspondence/search` mit `{"recordIdentifier", "page"}` |
| Wo liegen die **Vermerke**? | darin, als Einträge mit `type: "note"`; die Nummer steht in `referenceNote`. **Telefonvermerke** tragen `type: "phonecall"` — der Wunsch vom 28.09.2026 |
| Warum sagte `/record/note` immer 405? | Es braucht **zwei** Pflichtparameter: `id` **und** `record`. Zwanzig Namen wurden probiert, jeder mit **einem** Wert. „Bitte Daten angeben" war wörtlich zu nehmen |
| Welche Arten gibt es? | `mail · bea · post · fax · webnodes · sms · eda · note · file` |

### Was gebaut ist, und was nicht

**Gebaut:** Die Probe geht den richtigen Weg — `_korrespondenz_lesen` fragt
`/correspondence/search`, zählt Arten, Ordnernummern und Zeitraum, sucht die
Einträge vom Typ `note` heraus und ruft bis zu drei Vermerke mit **beiden**
Pflichtparametern ab. Gezeigt werden Art und **Länge** des Inhalts, nie der
Inhalt und nie ein Betreff; 17 Prüfungen halten das fest.

**Nicht gebaut:** Im Betrieb ist noch nichts geändert. `correspondenceFolderId`
bleibt abgeschaltet.

> **Warum nicht gleich?** Weil wir die Antwort des Servers noch nicht gesehen
> haben. Genau dieser Schritt — aus einer Beschreibung unmittelbar in den
> Betrieb — hat heute früh die 17 fremden Dokumente erzeugt.

### Zu tun

1. **Kanzlei:** `JURNODES-PRUEFEN.bat` an `X-100-2026` laufen lassen und
   `jurnodestest.txt` schicken. Die Probe geht jetzt zuerst über die
   Korrespondenz.
2. Mit dem Lauf: die Korrespondenz in den Betrieb einbauen — Dateien über
   `referenceFile`, Vermerke über `/record/note`.
3. **Die Anfrage an den Hersteller ist nicht mehr nötig** und darf nicht so
   hinausgehen: Sie behauptet einen Fehler, den es nicht gibt.

---

## Die E-Akte — der Hinweis aus der Kanzlei vom 05.10.2026

**„Die Korrespondenz bei jurnodes und die Vermerke finden sich in der E-Akte.
Vielleicht ist das die Lösung."**

Das ist sie vermutlich — und zwar für **beides**. Bisher standen zwei Dinge
getrennt offen:

| Offen seit | Was |
|---|---|
| 28.09.2026 | Wo liegen die **Vermerke**? (Aufgabe 2) |
| 05.10.2026 | Warum führt der **Korrespondenzordner** fremde Schriftstücke? |

**Liegen beide in der E-Akte, ist es eine Frage.** Und der zweite Punkt erklärt
sich mit: Liegt die Korrespondenz gar nicht im Dateisystem, dann zeigt
`correspondenceFolderId` auf etwas anderes — einen Ordner an einer Adresse,
einen Altbestand oder ein nicht mehr benutztes Feld. Das passt zu dem, was
gemessen wurde: niedrige Nummer, befüllt 2022/23, unabhängig vom Anlagedatum
der Akte, und in der Oberfläche unter dieser Akte nicht zu finden.

**Geraten wird trotzdem nicht.** 16 Pfadnamen für die E-Akte sind geprüft, alle
404; die Pfade für eine Beschreibung ebenso — sechs unterhalb der Zugangskennung
und vierundzwanzig darüber. Regel 10 gilt: bei Dritten warten,
nicht raten.

### Der Weg, der ohne den Hersteller auskommt

**Die Kanzlei hat die Beschreibung.** Am 23.09.2026 hat sie die
OpenAPI-Beschreibung ihres Servers geliefert; daraus sind die Pfade
abgeschrieben, mit denen das Programm heute arbeitet. Der Server selbst gibt
sie nicht heraus — die Datei gibt es aber.

Die Probe liest sie jetzt **von der Festplatte**, ohne Netz und ohne Zugang:

```
JURNODES-PRUEFEN.bat → bei „Datei mit der Schnittstellenbeschreibung"
                        den Pfad eintragen
```

Sie druckt **jeden** Pfad, der darin steht, und hebt die hervor, die nach
E-Akte, Korrespondenz oder Vermerk klingen. Ein Lauf, und die Frage ist
beantwortet — falls die Datei noch da ist.

**Dabei gleich ein eigener Fehler gefangen:** Der Hersteller schreibt
`electronic-file`, die Wortliste hieß `electronicfile` — und damit ging beim
ersten Versuch genau der Pfad durch, auf den es ankommt. Verglichen wird
seitdem ohne Trennzeichen. **Zum vierten Mal an einem Tag dieselbe Form:** Eine
Prüfung, die anders schreibt als der Gegenstand, prüft etwas anderes als den
Gegenstand.

### Zu tun

1. **Kanzlei:** Die OpenAPI-Datei vom 23.09.2026 suchen und der Probe geben.
   Sie beantwortet die Frage womöglich sofort.
2. **Kanzlei:** Die Anfrage an den Hersteller abschicken — sie ist neu
   geschrieben und führt jetzt mit der E-Akte; der Korrespondenzordner steht
   darin als Beleg, nicht als zweite Frage.
3. Mit der Antwort: den Weg in die E-Akte einbauen. Dann kommen Korrespondenz
   **und** Vermerke dazu, und `correspondenceFolderId` bleibt aus.

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

---

**Am 05.10.2026 ist der Rest dazugekommen — die Entwürfe stehen vollständig,
die Bewertung ist die Arbeit der Kanzlei.**

| Datei | Was darin steht | Offen |
|---|---|---|
| `DSFA-ENTWURF.md` | **neu** — Art. 35: acht Risiken, jedes mit dem, was im Programm dagegen steht und wo es nachzulesen ist | **17** Stellen `[KANZLEI n]`, am Ende in einer Liste |
| `DATENSCHUTZHINWEISE-ENTWURF.md` | **neu** — Text nach Art. 13, zwei Fassungen für die Mandatsbedingungen (mit und ohne Einwilligung), drei Sätze fürs Erstgespräch, die vier Fragen Betroffener | **9** Stellen |
| `VERARBEITUNGSVERZEICHNIS-ENTWURF.md` | nachgezogen auf den 05.10.2026 | 12 Stellen wie bisher |
| `DSFA-ANGABEN.md` | nachgezogen; der Befund zum Korrespondenzordner trägt jetzt einen eigenen Abschnitt | — |

**Die acht Risiken im DSFA-Entwurf:** Vermengung von Mandaten (R1, am
05.10.2026 eingetreten) · eine falsche Aussage wird für wahr genommen (R2) ·
die dauerhafte Fallkopie (R3) · Übermittlung an einen Auftragsverarbeiter unter
Berufsgeheimnis (R4) · Drittlandbezug durch EU-Profil und Schutzgeländer (R5) ·
besondere Kategorien, verstärkt durch die Texterkennung (R6) · Zugriff
innerhalb der Kanzlei (R7) · Auskunft, Berichtigung, Löschung (R8).

**Ein Fehler in den vorhandenen Unterlagen, dabei gefunden und behoben.**
`VERARBEITUNGSVERZEICHNIS-ENTWURF.md` sagte „Aktengedächtnis abgeschaltet" und
`DSFA-ANGABEN.md` „eingerichtet, eingeschaltet nicht" — **da lief es bereits**
und hatte eine echte Akte mit 55 Dokumenten dauerhaft abgelegt. Eine
Datenschutzunterlage, die einen Zustand beschreibt, den es nicht mehr gibt,
ist schlimmer als keine: Sie sieht aus wie eine Prüfung und ist eine Behauptung.

**25 Prüfungen halten das künftig fest.** Sie gleichen ab, was
`START-JURNODES.bat` einschaltet, mit dem, was die Unterlagen davon sagen —
Aktengedächtnis, Texterkennung, Korrespondenzordner — und zählen die offenen
Stellen, damit keine stillschweigend verschwindet.

**Was die Kanzlei jetzt tut:** die 17 und die 9 Stellen durchgehen. Die
dringendsten drei: die Löschfrist (R3), die Auskunft von AWS zu den Regionen
des Schutzgeländers (R5) und die Vorfrage Einwilligung oder nicht.

**Eine Angabe in `DSFA-ANGABEN.md` war überholt und ist berichtigt:** Dort
stand, über das Laufwerk sei ein archivierter Aktenstatus nicht zu erkennen und
die Lücke schließe sich mit der Schnittstelle. Die Schnittstelle steht seit dem
23.09., und der Lauf vom 28.09. belegt die Felder (`recordStatus`,
`archivedDate`). Eine Löschung, die dem Aktenstatus folgt, ist damit technisch
möglich — ob sie gewollt ist, ist Punkt 6.2 des Entwurfs.

Die Texterkennung ist in allen vier Unterlagen nachgetragen (eingeschaltet am 02.10.2026).

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

1. ~~**Den Zugang auf diesem Rechner hinterlegen** (Aufgabe 10)~~ —
   erledigt am 07.10.2026 auf dem neuen Rechner. `ZUGANG-PRUEFEN.bat` sagt
   „Der Zugang steht."; einzutragen war nichts, der Schlüssel lag schon im
   Windows-Konto.
2. ~~**`JURNODES-PRUEFEN.bat` einmal laufen lassen** (Akte `X-100-2026`)~~ —
   gelaufen am 07.10.2026. Ergebnis unten im Nachtrag: Der Weg zu den
   Vermerken steht, das Herunterladen aus dem Dateiordner geht — aber
   `POST /correspondence/search` antwortet **401**. Der Rest hängt daran.
3. **Texterkennung** (Aufgabe 1) — das Einzige, was noch Akteninhalt kostet.
4. **Prüfbogenlauf Chronologie** (Aufgabe 6) — der zweite Lauf, jetzt mit
   Opus, zum Nachweis der Änderungen vom 28.09.
5. ~~**`START-DEMO.bat` zusammenführen** (Aufgabe 8)~~ — erledigt.

Am Programm ist nichts offen, was das Arbeiten mit einer echten Akte
verhindert.

---

## Nachtrag 06.10.2026 — anderer Rechner

Herr Dortschy arbeitet seit dem 06.10.2026 an einem **anderen Rechner**. Das
ändert nichts am Programm und nichts am Aktengedächtnis: `START-JURNODES.bat`
setzt `JUSPERFECT_GEDAECHTNIS=aws`, die Erinnerungen liegen also im
AWS-Ablageort `dortschy-thunert-jusperfect-aktengedaechtnis` und nicht auf dem
alten Rechner. Seit der Berichtigung F03 kann auch kein zweiter Rechner mehr
überschreiben, was ein erster zur selben Akte geschrieben hat — der zweite
Schreibversuch wird abgewiesen.

Was der neue Rechner braucht, steht in `EINRICHTUNGSBOGEN.md`, Teil 4: die
neun Schritte vom Auspacken der ZIP bis `START-JURNODES.bat`. Die
Zugangswerte liegen im Windows-Konto, nicht im Programmordner
(`EINRICHTUNGSBOGEN.md`, Teil 5) — der neue Rechner hat sie deshalb nicht und
bekommt sie über `JURNODES-ZUGANG.bat` und `ZUGANG-EINTRAGEN.bat`.

**Folge für Schritt 1 der Reihenfolge oben:** „Den Zugang auf diesem Rechner
hinterlegen" meint jetzt den neuen Rechner. Der offene Lauf von
`JURNODES-PRUEFEN.bat` an `X-100-2026` ist davon nicht aufgehoben, sondern
nur verschoben: Er kann vom neuen Rechner aus laufen, sobald dort die
Zugangswerte eingetragen sind.

---

## Feste Vorgabe 07.10.2026 — kein Postfachzugriff

Aus der Kanzlei: **„Zugriff auf E-Mail-Postfach und beA-Postfach ist nicht
erforderlich, da alles in der E-Akte abgespeichert wird."**

Das ist keine Einschränkung, die etwas kostet, sondern die Bestätigung des
gebauten Weges. Nachgesehen am 07.10.2026:

- Im Programm gibt es keinen Postfachzugriff. Weder `imaplib`, `smtplib`,
  `poplib`, `exchangelib` noch ein beA-Zugang kommen vor.
- Alle Aufrufe gehen gegen `JUSPERFECT_JURNODES_URL`, also gegen die
  jur|nodes-Schnittstelle. Auch `POST /mail/download` ist ein Aufruf an
  jur|nodes und holt die **dort** abgelegte Fassung.
- `jusperfect/services/extraktion.py` erkennt `.msg` und `.eml` bereits als
  Dateiart. Gibt die E-Akte eine E-Mail als solche Datei heraus, lässt sie
  sich lesen, ohne Outlook und ohne Postfach.

**Folge:** Die beiden offenen Fragen in
`schnittstelle/ANFRAGE-HERSTELLER.md` bleiben unverändert — sie betreffen
nur, *wie die E-Akte* die abgelegte Fassung herausgibt (Dateiart hinter
`/mail/download`, Herkunft von `attachmentId` und `postFileUniqueKey`), nicht
den Zugang zu einem Postfach. Ein Postfachzugriff wird auch künftig nicht
gebaut.


---

## Nachtrag 07.10.2026 — der Lauf am neuen Rechner

Zwei Berichte aus der Kanzlei: `zugangstest.txt` und `jurnodestest.txt`,
beide vom neuen Rechner (`C:\Users\elmar\jusperfect-06.10.2026`).

### Der Zugang zu AWS steht

`AKIA…27UA`, angemeldet als `arn:aws:iam::579138738703:user/jusperfect-test`,
Region `eu-central-1`, Modell antwortet, Strom läuft, und: *„AWS schreibt die
Modellaufrufe nicht mit."* Eingetragen werden musste nichts — der Schlüssel
lag schon im Windows-Konto des Rechners.

### Der Befund, auf den es ankommt: Status 401

`POST /correspondence/search` wird mit **401** und leerem Antwortkörper
abgewiesen. Im **selben Lauf**, mit **demselben** Zugang, antworteten
`/record/search`, `/record`, `/relation/search`, `/todo/search`,
`/file-system/folder/content` und `/file-system/file/download` jeweils mit
200. Der Zugang steht also; abgewiesen wird dieser eine Pfad.

Das ist **keine Frage an das Programm**. Der Pfad ist der richtige, die
Parameter sind die beschriebenen. Es fehlt ein Recht am Schnittstellen-
benutzer `user_2` — oder dieser Pfad verlangt eine andere Anmeldung. Die
Frage dazu steht jetzt als **erste** in `schnittstelle/ANFRAGE-HERSTELLER.md`.

Weil die Korrespondenz der einzige beschriebene Weg zu den Vermerken ist
(`referenceNote`), bleibt die E-Akte abgeschaltet. Sobald der Pfad antwortet,
genügt ein weiterer Lauf.

### `correspondenceFolderId` — zum dritten Mal derselbe Befund

Die Akte ist am 30.07.2026 angelegt. Die Ordner hinter ihrem
`correspondenceFolderId` tragen Ablagen ab dem 15.12.2022: fünf Ordner,
siebzehn Dateien, alle älter als die Akte. Eine Datei kann nicht in eine
Akte gelegt worden sein, die es noch nicht gab.

Damit ist die Entscheidung vom 05.10.2026, diesen Baum im Betrieb **nicht**
mehr zu lesen, bestätigt. Sie bleibt.

### Vier Fehler in der eigenen Probe — berichtigt am 07.10.2026

Alle vier waren Fehler im Prüfbogen, nicht im Betrieb.

1. **Falscher Alarm beim Aktenstatus.** Der Bericht meldete
   `active: 10  <- kennt das Programm NICHT`. Falsch: `_STATUS` im Adapter
   führt „active" seit dem 02.10.2026. Die Probe hatte eine **zweite,
   veraltete** Liste. Sie fragt jetzt die Tabelle des Programms und zeigt zu
   jedem Wort die Übersetzung. Der erklärende Satz war ebenfalls falsch — ein
   unbekanntes Wort wird „unbekannt", nicht „laufend", und die Aufsicht legt
   die Akte einem Menschen vor.
2. **Die Frage blieb unbeantwortet.** Bei Status 401 brach der Abschnitt ab,
   ohne den Satz „Kann die E-Akte eingeschaltet werden?" zu drucken — also
   genau dort, wo er gebraucht wurde. Jetzt antwortet jeder Ausweg: bei 401
   oder 403 mit **NEIN — noch nicht**, samt Grund und dem Hinweis, dass am
   Programm nichts zu tun ist.
3. **Eine fremde Datei wurde geholt.** Die Leseprobe zog aus dem
   Korrespondenzbaum eine PDF (44 763 Bytes). Kein Inhalt stand im Bericht,
   aber geholt war sie — aus einem Baum, der nachweislich fremde Dateien
   trägt. Dort wird jetzt nur noch gezählt. Im Dateiordner bleibt die
   Leseprobe, dort gehören die Dateien zur Akte.
4. **Die naheliegende Form war nie probiert.** `GET /record/note` führt
   `id` **und** `record` als Pflicht. Probiert wurde jeder Name einzeln —
   zwanzig Formen, jede mit einem Wert. „Bitte Daten angeben" war deshalb
   kein Rätsel, sondern die zutreffende Auskunft: Es fehlte jedes Mal der
   zweite Wert. Jetzt wird die Form `id` + `record` mitprobiert, und zwar
   nur mit Zahlen, die der Server selbst zu dieser Akte herausgibt.

Dazu kommt: Der gedruckte „Satz zum Abschicken" fragte noch nach dem **Pfad**
zur E-Akte — seit 1.0.2 beantwortet. Er nennt den bekannten Weg jetzt und
fragt nur noch das Offene.

### Nebenbei: ein Schreibfehler in der Beschreibung

In `jurnodes-api-1.0.2.json` fehlt bei einem von 85 Pfaden der führende
Schrägstrich: `correspondence/get-by-reference`. Die übrigen 84 beginnen mit
`/`. Als Frage in `ANFRAGE-HERSTELLER.md` aufgenommen — der Pfad könnte
zugleich die Fragen zu `referenceMail` beantworten.

---

## Nachtrag 08.10.2026 — der Punkt lag in der Datei, die wir hatten

Herr Dortschy hat die vollständige Herstellerdokumentation vor sich und
gefragt, wo der Punkt liegen könnte. Er liegt in
`schnittstelle/jurnodes-api-1.0.2.json` — seit dem 05.10.2026 im
Programmordner.

**Der Hersteller nennt zu jedem der 94 Aufrufe das benötigte Recht.** Aber im
Fließtext des Feldes `description`, hinter der Erläuterung:

> `POST /correspondence/search` — *„Listet alle Korrespondenzen (derzeit einer
> Akte) auf. **Benötigte Rechte: search:correspondence**"*

Gesucht wurde an den Feldnamen, am Antwortschema, an den Parametern. Nicht in
den Sätzen. Vier Wochen lang.

### Was damit feststeht

| Aufruf | Recht | Lauf 07.10. |
|---|---|---|
| `GET /record/search` | `search:records` | 200 |
| `GET /record` | `read:records` | 200 |
| `GET /relation/search` | `search:relation` | 200 |
| `GET /todo/search` | `search:todo` | 200 |
| `GET /file-system/folder/content` | `read:folder` | 200 |
| `GET /file-system/file/download` | `download:file` | 200 |
| **`POST /correspondence/search`** | **`search:correspondence`** | **401** |

Sechs Rechte gesetzt, eines fehlt — und genau dessen Aufruf wird abgewiesen.
Die Beschreibung sagt zu 401 ausdrücklich: *„Authentifizierung ungültig."*

**`GET /record/note` verlangt nur `read:records`** — dasselbe Recht wie
`GET /record`, das bereits antwortet. Die Vermerke sind also lesbar, sobald
die Liste da ist. Es fehlt ein einziges Recht.

### Zwei offene Fragen haben sich erledigt

* **`attachmentId` beim beA** kommt aus `GET /bea?beaIdentifier=…`: Die
  Antwort `BeaMessage` führt `attachments`, eine Liste von
  `BeaMessageAttachment` mit `id`.
* **`postFileUniqueKey` bei der Post** kommt aus `POST /post/get-files` mit
  `{correspondenceIdentifier, postId}`: eine Liste von `PostFileModel` mit
  `uniqueKey`, `postId`, `name`, `extension`, `size`.

Beides stand ebenfalls in der Datei.

### Die Rechte für später — und welche ausdrücklich nicht

Der Hersteller trennt die Rechte nach **Postfach** und **Akte**. Das deckt
sich genau mit der Vorgabe vom 07.10.2026:

| Zweck | Recht | Nicht setzen |
|---|---|---|
| E-Mail aus der Akte | `download:mail:record` | `download:mail:postbox` |
| beA aus der Akte | `read:bea:record`, `download:bea:record` | `…:postbox` |
| Post | `read:post`, `download:post` | — |

### Gebaut

Die Probe liest die Rechte jetzt selbst aus der Beschreibung aus
(`_rechte_sammeln`, `recht_fuer`). Sie druckt zu jedem benutzten Aufruf das
Recht, und bei einem 401 nennt das Urteil es beim Namen statt „das liest sich
wie ein fehlendes Recht". Zwei Prüfungen messen das gegen die **echte**
Beschreibungsdatei, nicht gegen einen Nachbau.

### Nachtrag 08.10.2026, zweite Fassung — die Dateiart ist bei beA und Post geklärt

Herr Dortschy hat die Beispielkörper aus der Oberfläche der
Herstellerdokumentation geschickt (Post-Abschnitt). Sie sind Feld für Feld
deckungsgleich mit `jurnodes-api-1.0.2.json` — neu war daran nichts. Aber sie
haben ein Feld vor Augen geführt, das ich zwar gelesen, aber nicht verbunden
hatte: **`PostFileModel.extension`**.

Damit ist die Frage „welche Dateiart kommt zurück?" **bei beA und bei der
Post beantwortet**, bevor überhaupt heruntergeladen wird:

* **beA:** `BeaMessageAttachment` führt `fileName` und `type`.
* **Post:** `PostFileModel` führt `name` und `extension`.

Die Kette bei der Post ist vollständig und geschlossen:

1. `POST /correspondence/search` → Eintrag mit `identifier` und `referencePost`
2. `POST /post/get-files` mit `{correspondenceIdentifier, postId}` → Liste
   `PostFileModel`
3. `POST /post/download` mit `{correspondenceIdentifier, postId,
   postFileUniqueKey}` → die Bytes

**Offen bleibt die Dateiart allein bei der E-Mail.** Dort gibt es keinen
zweiten Aufruf: `POST /mail/download` nimmt nur `{mailIdentifier}` und gibt
Bytes zurück. Das misst der Prüfbogen an der Signatur der ersten Bytes,
sobald das Recht `search:correspondence` steht.

Nichts davon ist zu bauen, bevor das Recht steht — und dann zuerst gemessen,
nicht angenommen.

### Nachtrag 08.10.2026, dritter — die Anmeldung ist ausgeschlossen

Aus der Oberfläche der Herstellerdokumentation (Post-Abschnitt, geschickt am
08.10.2026) ergeben sich zwei Dinge, die über den Dateiinhalt hinausgehen:

**Alle 94 Aufrufe tragen denselben Sicherheitsblock** — `X-Auth-User` und
`X-Auth-Key`, ohne eine einzige Ausnahme. Nachgezählt in
`jurnodes-api-1.0.2.json`. Damit ist die zweite Erklärung für den 401
erledigt: Es gibt in dieser Schnittstelle kein anderes Anmeldeverfahren, auf
das `/correspondence/search` ausweichen könnte. Bleibt das Recht
`search:correspondence`. Die Frage in `ANFRAGE-HERSTELLER.md` ist entsprechend
verengt: nicht mehr „welches Recht oder welche Anmeldung", sondern nur noch
„wo wird dieses Recht gesetzt".

**Die Adresse in der Oberfläche ist keine.** Die Dokumentation zeigt unter den
Aufrufen `https://dortschy-thunert.jur-nodes.net/post/download`, also ohne den
Vorsatz `/api/extern/v1/<Kennung>`. Das ist eine Vorgabe des Anzeigewerkzeugs;
die Beschreibung führt keinen Abschnitt `servers`. Die benutzte Adresse ist
richtig — mit ihr haben am 07.10.2026 sechs andere Aufrufe mit 200
geantwortet. In `ANFRAGE-HERSTELLER.md` steht der Hinweis, damit niemand dort
sucht.

Auch der Antwortkörper passt: Für 400 und 405 ist
`{"message", "errorStrings"}` beschrieben, für **401 kein Körper** — und genau
leer (`{}`) kam er im Lauf zurück.

### Nachtrag 08.10.2026, vierter — der 401 war unser eigener Fehler

Herr Dortschy: *„search:correspondence war von mir freigegeben."* Damit war
die Erklärung von gestern hinfällig, und die Nachschau fand den wahren Grund
innerhalb einer Minute — in unserem eigenen Prüfbogen.

**`jusperfect/jurnodestest.py` hängte den Schlüssel `X-Auth-Key` nur an
`client.get` an.** Die Grundkopfzeilen des Clients tragen `X-Auth-User`, aber
nicht den Schlüssel; den setzte allein dieser eine Wrapper. **Jeder POST ging
ohne Schlüssel hinaus.**

Im Lauf vom 07.10.2026 war genau **ein** POST dabei:
`/correspondence/search`. Alle sechs Aufrufe, die mit 200 antworteten, waren
GET. Deshalb sah es nach einem Rechteproblem an genau diesem einen Pfad aus —
und die Erklärung war in sich stimmig, sogar mit Tabelle. Sie war trotzdem
falsch. Der Server hatte recht: Ohne Schlüssel ist die Authentifizierung
ungültig, und genau das heißt 401.

**Der Betrieb war nie betroffen.** `http_adapter.py` gibt `self._kopf(pfad)`
bei GET wie bei POST mit (Zeile 483 und 566). Der Fehler lag allein im
Werkzeug, das Vertrauen schaffen soll — und er hat der Kanzlei eine Aufgabe
gemacht, die keine war.

**Was daraus folgt, über diesen Fehler hinaus:** Eine Erklärung, die alle
beobachteten Daten erklärt, ist noch keine richtige. Alle sechs gelungenen
Aufrufe waren GET, der eine gescheiterte war POST — dieser Unterschied stand
in meiner eigenen Tabelle und wurde nicht gesehen, weil die Rechte-Erklärung
schon passte. Die Spalte „Verfahren" fehlte in der Tabelle; sie hätte es
gezeigt.

**Berichtigt.** `_schluessel_anhaengen()` schleift den Schlüssel über
`VERFAHREN = ("get", "post")`. Zwei Prüfungen sichern es: eine misst, dass
jedes Verfahren den Schlüssel trägt, die andere liest die Quelle und lässt
keinen zweiten, nicht umhüllten Client zu.

**`ANFRAGE-HERSTELLER.md`** führt die 401-Frage jetzt unter „Zurückgezogen"
und an ihrer Stelle die Liste der wirklich benötigten Rechte — nur lesende.

### Zur Frage, ob man für einen Test alles freischalten soll: nein

Dass jusperfect eine Akte nicht verändern *kann*, ist heute keine Zusage des
Programms, sondern eine Eigenschaft des Schlüssels. Ein Schlüssel mit allen
Rechten nähme dieses Netz weg und ließe nur das Versprechen übrig — und der
Oktober hat gezeigt, was Versprechen wert sind: drei Fehler, die als
Herstellerproblem aussahen und keines waren. Die lesenden Rechte oben
genügen; die schreibenden und die `:postbox`-Rechte bitte zurücknehmen.

### Nachtrag 08.10.2026, fünfter — die tatsächlich gesetzten Rechte, geprüft

Die Kanzlei hat die Liste gezeigt. Geprüft gegen
`schnittstelle/jurnodes-api-1.0.2.json`, Aufruf für Aufruf.

**Alle sieben Rechte, die das Programm heute braucht, sind gesetzt:**
`search:records`, `read:records`, `search:relation`, `search:todo`,
`read:folder`, `download:file`, `search:correspondence`.

Dazu `download:post`, `read:post` und `download:mail:record` — die werden für
den Inhalt von Post und E-Mail gebraucht, sobald er gebaut ist. Richtig ist
dabei besonders `download:mail:record`: die Variante für die **Akte**, nicht
die für das Postfach.

**Zwei Rechte sind schreibend und gehören zurückgenommen:**

| Recht | Was es öffnet |
|---|---|
| `generate:documents` | `POST /documents/generate` — „Erzeugt ein Dokument (Beta)" |
| `update:correspondence:folder` | `POST /correspondence/folder` — „Unterordner Erzeugen oder Bearbeiten" |

Beide schreiben in die Akte. Das Programm ruft keinen von beiden auf und wird
es nicht tun. Solange sie gesetzt sind, ist „jusperfect kann nichts
verändern" wieder nur eine Zusage statt einer Eigenschaft des Schlüssels.

**Ohne Wirkung, weil ungenutzt:** `read:file`, `read:relation`, `read:todo`,
`read:correspondence`, `read:correspondence:folder`, `read:object`. Alle
lesend; sie schaden nicht, werden aber auch nicht gebraucht. `search:object`
kommt in 1.0.2 an keinem einzigen Aufruf vor.

`/file-system/add-file` steht zwar in der Endpunktliste des Programms, wird
aber nie gerufen — und das zugehörige Recht `write:file` ist nicht gesetzt.
Richtig so.

---

## 08.10.2026 — der Lauf ist durch: **JA**

`JURNODES-PRUEFEN.bat` an `X-100-2026`, mit dem berichtigten Prüfbogen und
den freigegebenen Rechten. Alles antwortet.

### Die E-Akte ist lesbar

`POST /correspondence/search` → **Status 200, 26 Einträge**, eine Seite.
Davon **22 `mail`** und **4 `note`**. Poststempel vom 30.07. bis 25.09.2026 —
also innerhalb der Lebenszeit der Akte.

**Drei Vermerke wurden wirklich geholt**, über
`GET /record/note?id=…&record=…` mit beiden Pflichtparametern: 1589, 1590,
1600, je `type=phonecall`, `contentType=html`, 31 / 71 / 388 Zeichen. Die
Probe holt höchstens drei — zum Nachweis, nicht zum Auslesen.

Beim Versuch mit einer Nummer, die kein Vermerk ist, sagt der Server
**„Notiz nicht gefunden"** statt „Bitte Daten angeben". Auch das passt: Die
Form war richtig, nur die Zahl nicht.

### Die Dateiart hinter dem E-Mail-Download ist `.eml`

Gemessen: Status 200, **8 753 880 Bytes**, `Content-Type:
application/octet-stream`, `Content-Disposition: inline; filename="Mail.eml"`.
Die Texterkennung liest `.eml` bereits (`services/extraktion.py`).

Und: **`referenceMail` ist `mailIdentifier`.** Der Wert aus dem Verzeichnis
wurde unverändert eingesetzt und hat funktioniert. Keine Ableitung mehr.

### `correspondenceFolderId` — der Befund löst sich auf, und zwar zu unseren Lasten

Die Nummer gehört in den Ordnerbaum der **Korrespondenz**. Abgefragt wurde sie
gegen den Baum des **Dateisystems**. Beide führen eine Nummer 2871, und sie
haben nichts miteinander zu tun.

Der Beleg steht in diesem Lauf: Alle 26 Einträge der E-Akte nennen als
`folderId` genau jene 2871, und ihre Poststempel liegen zwischen dem 30.07.
und dem 25.09.2026. Die „Dateien aus 2022/23, älter als die Akte" lagen im
falschen Baum.

**Das ist derselbe Fehler wie am 02.10.2026, nur an einer zweiten Stelle.**
Beim ersten Mal kostete er drei fremde Schriftstücke in einer Bausache; beim
zweiten Mal eine Woche Arbeit an einer Frage an den Hersteller, die keine war.
`tests/test_dokumentliste.py` hatte die Erklärung seit dem 05.10.2026 im
Klartext stehen — in `config.py` stand sie nicht, und der Prüfbogen fragte
weiter am falschen Pfad.

### Gebaut

* **Die E-Akte ist eingeschaltet.** `Einstellungen.korrespondenz = True` in
  `jusperfect/config.py`, Vorgabe auch aus der Umgebung. `START-JURNODES.bat`
  erklärt jetzt das Ausschalten statt das Einschalten. Damit stehen die
  Vermerke als Dokumente in der Aktenliste.
* **Der Prüfbogen fragt `correspondenceFolderId` nicht mehr am Dateipfad.**
  Eine Prüfung hält fest, dass die Zeichenkette `feld="correspondenceFolderId"`
  in der Quelle nicht wieder auftaucht.
* `schnittstelle/ANFRAGE-HERSTELLER.md` ist auf **drei Kleinigkeiten**
  geschrumpft: `isInbox`, der fehlende Schrägstrich, und ob es eine neuere
  Fassung als 1.0.2 gibt.

### Was als Nächstes ansteht

**Der Inhalt der 22 E-Mails.** Alles dafür ist jetzt belegt: der Weg, die
Nummer, die Dateiart. Zwei Dinge sind vorher zu entscheiden, und beide sind
keine Programmierfragen:

1. **Die Größe.** Eine einzige Mail wog 8,7 MB. 22 davon wären rund 190 MB je
   Akte, dazu Texterkennung. Vorschlag: eine Obergrenze je Mail, darüber wird
   der Eintrag mit Betreff und Datum gezeigt und der Inhalt erst auf Klick
   geholt.
2. **Was hineingehört.** Eine `.eml` trägt Anhänge, Signaturbilder und oft den
   ganzen Verlauf doppelt. Ob der Anhang mit hineinsoll, ist eine Frage an die
   Kanzlei, keine ans Programm.

### Nachtrag 08.10.2026, später — zwei Eingabezeilen untereinander sind eine Falle

Der Lauf an `X-101-2026` zeigt es in der ersten Zeile des Berichts:

```
Beschreibung aus der Datei: X-102-2026
✗  Die Datei gibt es nicht.
```

In **beide** Eingabezeilen von `JURNODES-PRUEFEN.bat` wurde ein Aktenzeichen
getippt — in die erste `X-101-2026`, in die zweite `X-102-2026`. Die zweite
will einen **Dateipfad**.

**Die Folge war still und teuer.** Die Probe lief ohne die
Schnittstellenbeschreibung weiter. Es fehlten die 85 Pfade, die
Rechteübersicht und die Namen der Pflichtparameter — also gerade das, wofür
der Lauf gemacht wird. Im Bericht stand davon eine einzige Zeile, drei Seiten
weiter oben, mit einem Haken daneben, der kein Haken war.

Und vermutlich ist das auch die Antwort auf *„X-100-2026 nimmt er nicht mehr
an"*: Wer das Aktenzeichen in die zweite Zeile tippt, bekommt „Die Datei gibt
es nicht." zu lesen. Das sieht aus wie eine Abweisung der Akte und ist eine
Abweisung eines Dateinamens.

**Berichtigt:**

* `_beschreibung_aus_datei()` fällt auf die beiliegende Datei zurück, statt
  ohne weiterzulaufen, und sagt dabei, wenn die Eingabe nach einem
  Aktenzeichen aussieht und in welche Zeile es gehört.
* `JURNODES-PRUEFEN.bat` nummeriert die beiden Fragen („FRAGE 1 von 2"),
  erklärt jede und schreibt bei der zweiten ausdrücklich: *HIER GEHOERT KEIN
  AKTENZEICHEN HIN.*

### Was der Lauf trotzdem gezeigt hat

* **`X-101-2026`: 9 Einträge, alle `mail`, kein Vermerk.** Das Urteil lautet
  richtig *unentschieden* — nicht JA und nicht NEIN. Der Weg steht, aber diese
  Akte kann über `/record/note` nichts aussagen.
* **`/mail/download` ein zweites Mal: `.eml`**, Status 200 — diesmal aber nur
  **5 426 Bytes** statt 8 753 880. Die 8,7 MB vom ersten Lauf waren also ein
  Ausreißer, vermutlich eine Mail mit großem Anhang. Für die Frage nach der
  Obergrenze heißt das: Die meisten Mails sind klein; eine Grenze träfe
  wenige.
* Die Aktensuche arbeitet einwandfrei (`X-101-2026` → 1 Eintrag, Status 200).
  An der Schnittstelle liegt es nicht.

### Berichtigung 08.10.2026 — die beiden schreibenden Rechte sind nicht gesetzt

Aus der Kanzlei: *„Rechte gar nicht bei jurnodes ausgewählt — generate
documents und update correspondence folder — und somit gar nicht
eingeschaltet."*

Damit ist meine Lesart des Bildschirmfotos falsch gewesen. Ich hatte die
grünen Felder für die **vergebenen** Rechte gehalten; offenbar zeigen sie die
**verfügbaren**. Die Aufgabe „zwei schreibende Rechte zurücknehmen" ist
hinfällig und aus der Aufgabenliste entfernt.

**Was davon bleibt, ist die Regel, nicht die Aufgabe:** Dass jusperfect eine
Akte nicht verändern kann, soll eine Eigenschaft des Schlüssels bleiben und
keine Zusage des Programms. Die Rechte mit `write:`, `delete:`, `update:`,
`create:`, dazu `generate:documents` und `file_upload`, gehören weiterhin
nicht an den Schnittstellenbenutzer. Nach dem heutigen Stand sind sie es auch
nicht.

**Und eine Lehre über den Fall hinaus:** Ein Bildschirmfoto zeigt, was auf dem
Schirm steht, nicht, was es bedeutet. Eine Liste grüner Felder kann „gesetzt"
heißen oder „zur Auswahl". Ich habe das eine gelesen und das andere gemeint,
und daraus eine Aufgabe für die Kanzlei gemacht, die keine war — zum zweiten
Mal in dieser Woche nach dem 401.

### Nachtrag 08.10.2026 — Handgriff 1 in AWS war längst erledigt

Die Kanzlei hat die eingesetzte Zugriffsrichtlinie gezeigt. Verglichen mit
`infra/iam-nur-claude.json`, Anweisung für Anweisung: **alle sieben
identisch.** `NurEuUndEwr` nennt die sechs Regionen namentlich,
`SchutzgelaenderAnwenden` führt `guardrail-profile` neben `guardrail`. Die
neue Fassung ist also drin.

Der einzige Unterschied: Die Datei im Programmordner trägt den Platzhalter
`AWS-KONTONUMMER`, die eingesetzte Fassung die richtige Nummer. So soll es
sein — die Datei ist eine Vorlage.

**Damit ist F13 vollständig geschlossen**, nicht nur zur Hälfte. In der
Aufgabenliste stand der Handgriff bis heute als offen; er war es nicht.

**Und ein Mangel in meiner eigenen Anleitung vom selben Tag:** Sie sagte
nicht, dass `AWS-KONTONUMMER` zu ersetzen ist. Wer die Datei unverändert
eingesetzt hätte, hätte das Inferenzprofil ausgesperrt — den Weg, über den
jede Analyse läuft —, und der Fehler wäre erst beim nächsten Aufruf
aufgefallen, aussehend wie ein Modellproblem. Nachgetragen als Schritt 10,
mit dem Hinweis, dass die Zeichenfolge zweimal vorkommt.

---

## 11.10.2026 — `isInbox` ist beantwortet, und zwar aus unserer eigenen Datei

Herr Dortschy hat drei Beispielkörper aus der Oberfläche der
Herstellerdokumentation geschickt und in jedem `isInbox` markiert:
`POST /correspondence/add` („Request samples"), `GET /correspondence`
(„Korrespondenzen Laden") und `POST /correspondence` („Korrespondenzen
Update").

**Die Beispiele selbst sagen nichts.** In allen dreien steht nur der
Platzhalter `"isInbox": 0` — so, wie die Oberfläche jede Zahl zeigt. Die
Antwort steht eine Ebene darunter, im Schema, das die Oberfläche erst auf
Aufklappen zeigt:

> `isInbox` · number · *„1 = Eingang, 0 = Ausgang, -1 = Neutral/Unbekannt"*

Das steht in `schnittstelle/jurnodes-api-1.0.2.json` — **seit dem 05.10.2026
im Programmordner**, gleichlautend in `Correspondence` und
`CorrespondenceModel`.

### Der dritte Wert ist der Punkt

Die Vermutung in `ANFRAGE-HERSTELLER.md` lautete: „Heißt 1 eingegangen und 0
ausgegangen?" Sie war richtig — und unvollständig. `-1` heißt *weder noch*.
Wer das Feld als Ja/Nein liest, schreibt über jedes neutrale Schreiben
„Ausgang".

Dass `_richtung()` in `jusperfect/jurnodes/http_adapter.py` bisher nur
„E-Mail" zurückgibt und die Richtung weglässt, war deshalb richtig. Der
Kommentar dort nennt es „die letzte offene Frage in ANFRAGE-HERSTELLER.md" —
das stimmt seit heute nicht mehr und ist mit dem Einbau zu berichtigen.

### Der Weg ist vollständig

`POST /correspondence/search` gibt `CorrespondenceSearchResponse` zurück;
deren `elements` sind `CorrespondenceModel`, und das führt `isInbox`. Die
Richtung liegt also bei jedem Eintrag der E-Akte schon vor — ohne zweiten
Aufruf, ohne in ein Schreiben hineinzusehen.

### Nebenbei dreierlei

* **Die Oberfläche zeigt 1.0.2.** Alle drei Aufrufe sind Feld für Feld und
  Wort für Wort deckungsgleich mit unserer Datei: dieselbe Überschrift,
  derselbe Beschreibungssatz, dasselbe benötigte Recht, und
  `CorrespondenceModel` mit 22 Feldern in derselben Reihenfolge. Das beweist
  nicht, dass es keine neuere Fassung gibt; es heißt, dass die Oberfläche
  keine andere zeigt.
* **`referencePost` ist zweierlei, und das ist kein Widerspruch.** Im
  Schreibschema `Correspondence` ein Objekt (`CorrespondencePost` mit
  `identifier` und `type`), im Lesemodell `CorrespondenceModel` eine Zahl.
  Zwei Schemata, zwei Richtungen.
* **Ein Warnhinweis, der die Rechtevorgabe bestätigt.** Die Beschreibung von
  `POST /correspondence/add` sagt: *„beim Erzeugen einer Korrespondenz wird
  die ursprüngliche beA-Nachricht aus dem eigentlichen beA-Ordner entfernt.
  Bitte prüfen Sie sorgfältig, dass keine beA-Nachricht in Vergessenheit
  gerät."* Ein schreibender Aufruf, der nebenbei etwas aus dem beA-Ordner
  nimmt — genau dafür gehört `write:correspondence` nicht an den
  Schnittstellenbenutzer.

### Was daraus folgt — zum vierten Mal dieselbe Lehre

Der 401 stand in unserer Tabelle. `correspondenceFolderId` stand in
`tests/test_dokumentliste.py`. Die benötigten Rechte standen im Feld
`description`. Und jetzt `isInbox`, in derselben Datei, eine Zeile neben dem
Feldnamen, den wir vier Wochen lang gelesen haben.

> Gesucht wurde immer dort, wo die Antwort stehen *sollte*. Nicht dort, wo
> sie stand.

Die Frage ist aus `ANFRAGE-HERSTELLER.md` heraus; offen sind dort noch
**zwei** Kleinigkeiten statt drei.

### Noch nicht gebaut

Die Richtung anzuzeigen ist ein Eingriff in die Oberfläche und in das, was in
einer echten Akte an einem Schriftstück steht. Er wartet auf das Wort der
Kanzlei — zusammen mit der Berichtigung des Kommentars in `http_adapter.py`
und des Satzes „drei Kleinigkeiten" in `jusperfect/jurnodestest.py`.

### Nachtrag 11.10.2026 — die Richtung ist eingebaut

`_richtung()` in `jusperfect/jurnodes/http_adapter.py` liest `isInbox` jetzt
über eine Tabelle, nicht über ein `if`:

| `isInbox` | Kategorie |
|---|---|
| 1 | `E-Mail (Eingang)` |
| 0 | `E-Mail (Ausgang)` |
| -1, fehlend, unbekannter Wert | `E-Mail` — ohne Zusatz |

Eine Tabelle, weil der dritte Wert sonst durchfällt. Jeder Wert außer 1, 0
und -1 geht denselben Weg wie -1: keine Angabe. Was der Hersteller nicht
beschrieben hat, wird nicht gedeutet.

**Zwei Entscheidungen dabei:**

* **Die Anlage erbt die Richtung ihrer Mail** — `Anlage zur E-Mail
  (Eingang)`. Wer „alles, was eingegangen ist" anhakt, meint die Anlagen mit.
* **Bei fehlendem Inhalt bleibt die Richtung stehen**, die Warnung tritt
  dahinter: `E-Mail (Eingang) – Inhalt fehlt (zu groß)`. Gerade dann ist die
  Richtung das Einzige, woran sich das Schreiben noch einordnen lässt.

**An der Oberfläche war nichts zu ändern.** Das Dokumentfenster zeigt die
Kategorie ohnehin in jeder Zeile und macht aus jeder einen Knopf zur
Stapelauswahl. Im echten Browser nachgesehen (Chromium, 1320 × 980, Demo mit
umetikettierten Testdokumenten): Die Knopfreihe bricht sauber um, die Zeilen
tragen die Richtung rechts neben dem Datum.

Berichtigt sind außerdem der Satz „drei Kleinigkeiten" im Prüfbogen
(`jusperfect/jurnodestest.py`) und der Kommentar in `_richtung`, der
`isInbox` noch „die letzte offene Frage" nannte.

**1837 Prüfungen grün** — sieben neue: fünf zur Richtung, eine dazu, dass
eine Anlage sie erbt, und eine zur Seitenzählung (siehe unten).

### Nachtrag 11.10.2026 — die zweite Meinung, und was davon zutraf

Die Kanzlei hat die Schnittstellenfragen einer zweiten KI vorgelegt. Vier
Punkte kamen zurück.

**1. `isInbox`** — dasselbe Ergebnis, unabhängig gefunden, mit Verweis auf die
Zeile in der Beschreibungsdatei. Bestätigt.

**2. Der fehlende Schrägstrich** ist ein Verstoß gegen die OpenAPI-Regel, dass
jeder Pfad mit `/` beginnt. Dazu kommt ein Beleg aus der Oberfläche selbst:
Das Bildschirmfoto vom 11.10.2026 zeigt in der Adresszeile
`https://dortschy-thunert.jur-nodes.net` **`correspondence`**`/get-by-reference`
— ohne Trennzeichen. Die Dokumentation baut aus dem Pfad eine unbrauchbare
Adresse. Dass `/correspondence/get-by-reference` richtig ist, bleibt
trotzdem eine Vermutung; beweisen kann es nur ein Aufruf.

**3. Die Seitenzählung — der Einwand war berechtigt gestellt und geprüft.**
Die Warnung lautete: `POST /correspondence/search` führt `page` und gibt
`pagesTotal` zurück; wer nur die erste Seite liest, bekommt eine Liste, die
wie eine vollständige aussieht. **Nachgesehen: Das Programm liest alle
Seiten** — `_alle_seiten_post` in `http_adapter.py` zählt hoch, bis
`pagesTotal` erreicht ist, mit der gemessenen Eigenart, dass die erste
Anfrage ohne `page` hinausgeht. Geprüft war das bisher nur für die
GET-Aufrufe; für die E-Akte gab es keine Prüfung. **Jetzt gibt es eine:**
drei Seiten Vermerke, fünf Einträge, und die Prüfung misst, dass alle drei
Seiten abgefragt wurden.

Das ist der Nutzen einer zweiten Meinung, auch wenn der Befund sich nicht
bestätigt: Die Lücke war keine im Programm, sondern eine im Prüfnetz.

**4. Der Ordnerbaum für die Gruppierung** — trifft die offene Aufgabe
„Ordner im Dokumentfenster gruppieren". Festgehalten für den Einbau.

**Was die zweite Meinung noch braucht:** Sie arbeitet mit dem Prüfbestand vom
**16.09.2026**. Alles seither — die E-Akte, die Mails, die 1830 Prüfungen —
hat sie nicht gesehen und sagt das auch deutlich: Die Zahl der grünen
Prüfungen sei „eine Angabe aus dem Standbericht, kein von mir bestätigtes
Ergebnis." Richtig. Ohne aktuellen Quelltext ist keine Sicherheitsprüfung
möglich, und `PRUEFAUFTRAG.md` ist vom 05.10.2026 und nennt noch 1625
Prüfungen.

---

## 11.10.2026 — ein echtes Rubrum lag im Programmbestand

Auf Nachfrage aus der Kanzlei: Eines der Aktenzeichen, die in Beispielen und
Prüfdateien standen, gehört zu einer **echten Akte**. Damit war der Name
daneben kein Platzhalter, sondern Mandant und Gegner einer laufenden Sache —
in einem Bestand, der an Dritte geht.

> **Dieser Eintrag nennt weder den Namen noch die Nummer.** Am 12.10.2026 ist
> aufgefallen, dass er es in seiner ersten Fassung tat: Die Beschreibung des
> Fundes hat den Fund wieder hergestellt. Siehe dort.

### Was gefunden wurde

**120 Stellen in 16 Dateien** — in `AWS-EINRICHTEN.md` ein Laufwerkspfad mit
vollem Rubrum, in `UEBERGABE.md` zweimal das Rubrum als Beispiel für einen
Dateinamen, dazu dreizehn Prüfdateien mit Ordnernamen, Kurzrubren und
Suchbegriffen, und ein Kommentar in `jusperfect/jurnodes/http_adapter.py`.

Fünf der dreizehn trugen den Namen **ohne Umlaut** und waren in der ersten
Suche durchgerutscht — gefunden hat sie erst der Austausch selbst, weil er
beide Schreibweisen führte.

Alle ersetzt durch die erfundenen Namen, die der Bestand ohnehin führt:
`Testmann`, `Musterhaft`, `Musterfrau`, `Beispiel`.

`schnittstelle/jurnodes-api-1.0.2.json` blieb unberührt — die Beispiele darin
sind die des Herstellers.

**1837 Prüfungen grün** — der Austausch war durchgängig, keine Prüfung hat
ihn bemerkt.

### Dass es überhaupt auffiel, war ein Zufall

`jusperfect/jurnodes/webdav_adapter.py` trug den Namen schon nicht mehr; dort
steht seit längerem `ohne Name wer gegen wen`. Jemand hat an **einer** Stelle
hingesehen und an den übrigen sechzehn nicht. Dieser Unterschied — eine Datei
bereinigt, der Rest nicht — war das Einzige, was den Verdacht getragen hat.

Die Namen selbst sahen aus wie Platzhalter. Es waren genau die Namen, die man
erfindet, wenn man einen erfinden will.

> Ein erfundener Name und ein echter sehen gleich aus. Was sie unterscheidet,
> weiß nur die Kanzlei — also ist zu fragen, nicht zu schließen.

### Zwei Dinge, die damit **nicht** erledigt sind

**1. Die Vorgeschichte.** Das Repository beginnt mit dem Commit `d145e3e` vom
05.10.2026, 10:58 Uhr — 261 Dateien auf einmal, und die Namen waren von der
ersten Zeile an dabei. Sie stehen damit in **allen 52 Commits**. Der heutige
Austausch ändert den Arbeitsstand, nicht die Vorgeschichte. Wer `git log -p`
liest, findet sie weiter.

Das Repository ist **privat** (nachgesehen am 11.10.2026: `visibility:
private`, keine Forks, keine Beobachter) — es liegt also bei einem Anbieter,
nicht offen. Die Vorgeschichte zu bereinigen hieße, alle 52 Commits neu zu
schreiben und überschreibend zu pushen. Das ist eine Entscheidung der
Kanzlei, keine der Entwicklung.

**2. Was bereits hinausgegangen ist.** Die Namen lagen seit dem ersten Commit
im Bestand. Das **Prüfpaket vom 05.10.2026**, aus dem die Zweitprüfung
gearbeitet hat, ist am selben Tag entstanden; der Bericht kam um 15:54 Uhr
zurück, die Namen waren um 10:58 Uhr da. **Ob sie im Paket lagen, lässt sich
hier nicht feststellen** — die ZIP liegt auf dem Rechner der Kanzlei. Ein
Suchlauf nach „Musterhaft" in
`jusperfect-pruefpaket-05.10.2026.zip` beantwortet es in einer Minute.
Dasselbe gilt für den Bestand vom 16.09.2026, mit dem die jetzige zweite
Meinung arbeitet.

Gesagt, nicht vermutet: Wenn die Namen im Paket lagen, ist das eine
Offenlegung, die bereits stattgefunden hat.

### Nachtrag 11.10.2026 — die übrigen Namen sind erfunden

Aus der Kanzlei, auf Nachfrage: *„Krämer, Schulz und Vellinghausen sind
erfunden, Meier auch."*

Damit ist der Bestand geprüft und nicht nur bereinigt. Was heute noch an
Namen darin steht — `Meier`, `Krämer`, `Schulz`, `Schulze`, `Vellinghausen`,
dazu die Namen der erfundenen Testakten in `testdaten/` — ist bestätigt
erfunden. Einzig `Testmann ./. Musterhaft` war echt, und das ist heraus.

**Für spätere Sitzungen:** Diese Liste ist eine Auskunft der Kanzlei vom
11.10.2026, kein Befund aus dem Quelltext. Kommt ein neuer Name hinzu, ist
erneut zu fragen. Ein erfundener Name und ein echter sehen gleich aus.

---

## 12.10.2026 — die Ordner stehen im Dokumentfenster

Die letzte der drei offenen Programmaufgaben. In `X-100-2026` standen 55
Einträge aus acht Ordnern in einer Reihe.

### Es war mehr als eine Anzeigeänderung

**Der Ordner war im Programm gar nicht vorhanden.** `_ordner_durchgehen` in
`jusperfect/jurnodes/http_adapter.py` läuft den Baum ab, kennt dabei jeden
Ordnernamen — und warf ihn weg. Am `Dokument` gab es kein Feld dafür.

Neu: `Dokument.ordner`. Der Baumdurchlauf gibt zu jedem Eintrag seinen Pfad
zurück (`Schriftsätze/Gegenseite`); der Wurzelordner ist die leere
Zeichenkette.

### Drei Entscheidungen

**Die E-Akte steht unter eigenem Namen und hinten.** Mails, ihre Anlagen und
Vermerke tragen `ordner = "E-Akte"`. Sie kommen aus dem Korrespondenzbaum,
nicht aus dem Dateiordner. Sie dazwischenzumischen hieße, zwei Bäume zu einem
zu machen — und genau diese Verwechslung hat am 02.10.2026 drei fremde
Schriftstücke in eine Bausache gebracht.

**Ein Ordner ohne Namen bekommt seine Nummer.** `Ordner 2`, `Ordner 3`. Zwei
namenlose Ordner dürfen nicht zu einem verschmelzen; das sähe aus wie ein
Register, wo zwei sind.

**Ein `/` im Ordnernamen wird zu `-`.** „Miete / Nebenkosten" ist ein Ordner,
nicht zwei. Sonst täuschte der Pfad eine Ebene vor, die es nicht gibt.

### Beim WebDAV-Adapter stand es schon da — an der falschen Stelle

`jusperfect/jurnodes/webdav_adapter.py` legte den Unterordner seit jeher in
`kategorie` ab. Das ist umgezogen nach `ordner`. `kategorie` bleibt für das
frei, was ein Schriftstück **ist** (Mandant, Gegner, E-Mail (Eingang)); der
Ordner sagt, **wo es liegt**. Beides in einem Feld hieß, dass die
Stapelauswahl nach Art bei einer Laufwerksakte die Ordner anbot und bei einer
jur|nodes-Akte die Arten.

### Im Fenster

Eine Überschrift je Ordner, mit Anzahl und einem Griff für den Stapel („alle
anhaken" / „Haken entfernen") — wer ein Register ganz will, klickt einmal
statt fünfzehnmal. Reihenfolge: zuerst, was unmittelbar im Aktenordner liegt,
dann die Ordner nach dem Alphabet, die E-Akte zuletzt. **Bei einem einzigen
Ordner bleibt die Liste glatt** — eine Gliederung aus einem Teil ist keine.

Der Filter sucht jetzt auch im Ordnernamen; der Platzhalter sagt es.

**Im echten Browser nachgesehen** (Chromium, 1320 × 1000, Demo mit
Testdokumenten in sechs Ordnern): Die Überschriften stehen, der Stapelgriff
hakt an und wieder ab und beschriftet sich um, die Suche nach „gericht"
findet das Dokument im Gerichtsordner und zeigt es ohne Überschrift — weil
dann nur noch ein Ordner übrig ist. Keine Meldung in der Browserkonsole.

**1850 Prüfungen grün**, dreizehn neue in `tests/test_ordner_gruppieren.py`.

### Nachtrag 12.10.2026 — das Aktenzeichen ist aus dem Schreiben heraus

`schnittstelle/ANFRAGE-HERSTELLER.md` nannte in der Zeile über die gemessene
E-Akte das Aktenzeichen `X-100-2026` und die Poststempel vom 30.07. bis
25.09.2026 — und verlangte zwei Absätze weiter unten vom Leser ausdrücklich
*„Nichts aus einer Akte. Keine Aktenkennung."* Beides ist heraus; es steht
jetzt „an einer Akte der Kanzlei". Die Zahlen, auf die es ankommt — 26
Einträge, 22 Mails, 4 Vermerke —, sagen nichts über ein Mandat.

### Nachtrag 12.10.2026 — kein Postfachzugriff, und zwar geprüft

Vorgabe der Kanzlei, heute bestätigt und begründet:

> *„Alle E-Mails und Vermerke werden in der E-Akte abgespeichert. Es macht
> daher keinen Sinn und wäre sogar kontraproduktiv, wenn das Postfach
> ausgelesen wird, in welchem sich alle Akten befinden. Das Gleiche gilt für
> die beA-Eingänge."*

Das ist eine bessere Begründung als die bisher aufgeschriebene. Bisher stand
da, ein Postfachzugriff sei „nicht erforderlich". Der eigentliche Punkt ist
schärfer: Im Postfach liegt die Post **aller** Mandate. Ein Zugriff brächte
also nichts Neues und zugleich alles Fremde.

**Nachgesehen: Das Programm ruft keinen Postfachaufruf.** Kein `imaplib`,
kein `smtplib`, keiner der drei beA-Postfachaufrufe.

**Aber geprüft war das nicht.** Die Regel galt seit dem 07.10.2026 und ruhte
auf einer Nachschau — auf einem Blick, den jemand einmal getan hat. Dieselbe
Art Lücke hat die zweite Meinung am 11.10.2026 bei der Seitenzählung
gefunden. Hier wäre sie teurer: Ein Postfachaufruf fiele niemandem auf, denn
er brächte Daten zurück, nur die falschen.

Seit heute steht es in `tests/test_kein_postfach.py`, fünf Prüfungen.

### Und ein Punkt, der dabei erst klar wurde

**Der Aufruf entscheidet es nicht, das Recht tut es.**

`POST /mail/download` und `GET /bea` sind je **ein** Aufruf für beide Fälle.
Die Beschreibung nennt zu jedem zwei Rechte: `download:mail:postbox` *(Für
E-Mail im Postfach)* und `download:mail:record`, ebenso `read:bea:postbox`
und `read:bea:record`. **Dieselbe Zeile Quelltext holt je nach Schlüssel eine
Nachricht aus der Akte oder eine aus dem Postfach.**

Am Client lässt sich das nicht prüfen, und die neue Prüfdatei sagt das auch
ausdrücklich. Es hängt allein daran, dass die `:postbox`-Rechte nicht gesetzt
sind. Nach der Liste vom 08.10.2026 sind sie es nicht — gesetzt ist
`download:mail:record`, die Fassung für die Akte. Richtig so.

Nur drei Aufrufe betreffen **ausschließlich** das Postfach, und keiner hat
eine Fassung je Akte — sie sagen es in ihrer eigenen Beschreibung:

| Aufruf | Beschreibung des Herstellers |
|---|---|
| `GET /bea/postbox/search` | „Listet alle hinterlegten beA-Postfächer auf" |
| `GET /bea/folder/search` | „Listet alle Ordner eines beA-Postfachs auf" |
| `GET /bea/search` | „Listet alle beA-Nachrichten eines beA-Postfaches in einem bestimmten Ordner auf" |

Diese drei ruft das Programm nicht und wird es nicht. **Für den späteren
Einbau von beA heißt das zugleich, welcher Weg der richtige ist:** über das
Korrespondenzverzeichnis der Akte (`referenceBea`) und dann
`GET /bea?beaIdentifier=…` — nie über eine Postfachsuche.

**1855 Prüfungen grün.**

---

## 12.10.2026 — die Aktenzeichen sind heraus, und die letzte Frage ist beantwortet

### Entscheidung der Kanzlei: auch aus `MORGEN.md`

Gestern hatte ich dafür gehalten, die echten Aktenzeichen behalten zu dürfen,
und es im Prüfauftrag auch so aufgeschrieben: Sie trügen den Beleg, ohne sie
wäre die Chronik eine Behauptung. „X-100-2026 hat 26 Einträge, 22 Mails, 4
Vermerke" ist eine Messung — „eine Akte hat 26 Einträge" ist keine.

**Das Argument war nicht falsch, aber das schwächere.** Der Bestand geht an
Dritte; eine Zweitprüfung hat ihn schon zweimal bekommen. Ein Aktenzeichen mit
gemessenen Angaben ist eine Aussage über ein bestimmtes Mandat, auch ohne
Namen. Und die Chronik verliert nichts: Die Zahlen bleiben, nur der Zeiger auf
die Akte fällt weg.

### Die Regel, in einem Satz

> **Ein Aktenzeichen im Bestand beginnt mit `X`.**

Die Kanzlei führt `D` (Dortschy) und `T` (Thunert). Ein `X` kann es dort nicht
geben. Damit ist jede Nummer im Bestand auf einen Blick als erfunden zu
erkennen — und eine Prüfung kann einen Rückfall **messen**, statt ihn zu
erhoffen.

**141 Stellen in 26 Dateien.** Die Zuordnung ist durchgehend, damit die
Chronik lesbar bleibt: Jede echte Nummer hat **überall** dieselbe erfundene
bekommen — die am 08.10. gemessene Akte heißt von der ersten bis zur letzten
Erwähnung `X-100-2026`, die zweite `X-101-2026`. Mit umgezogen sind auch die
Platzhalter von gestern, damit es genau **eine** Regel gibt statt zwei.

Die Zuordnung selbst steht nirgends im Bestand, und das ist Absicht: Sie wäre
sonst der Schlüssel, der alles rückgängig macht. Die Kanzlei weiß, welche Akte
22 Mails hatte.

Die Stapeldateien sind binär ersetzt worden; ihre CRLF-Zeilenenden stehen
noch — nachgesehen mit `file`.

### Eine Ausnahme, die ich selbst eingebaut hatte, ist gestrichen

`tests/test_rechtsunterlagen.py` ließ **ein** Aktenzeichen in der DSFA zu, mit
der Begründung, der Befund sei „ohne die Akte nicht zu beschreiben". Das war
bequem und falsch. Die Prüfung verlangt jetzt gar keines mehr.

Neu ist `tests/test_keine_echten_akten.py`: drei Prüfungen über den **ganzen**
Bestand, jede Datei, die git kennt. Dazu eine Gegenprobe, die misst, dass das
Muster eine echte Nummer wirklich fängt — eine Prüfung, die nichts findet, muss
zeigen, dass sie suchen kann. Genau diese Art Prüfung war am 08.10.2026 einer
der fünf Funde im Prüfbogen.

**Was sie nicht kann, und das steht auch dort:** Die zweite Schreibweise des
Hauses („42/26 VU") fällt ihr nicht auf. Dagegen hilft nur Nachfragen — und
genau das hat am 11.10.2026 ein echtes Rubrum zutage gefördert.

### Die letzte Frage an jur|nodes ist beantwortet

Aus der Kanzlei: *„Gibt es eine neuere Fassung als 1.0.2? Nein."*

Damit steht fest, dass `schnittstelle/jurnodes-api-1.0.2.json` nicht *eine*
Fassung ist, sondern **die**. Der Vergleich vom 11.10.2026 — drei Aufrufe,
Feld für Feld und Wort für Wort deckungsgleich — hatte recht.

**Offen ist an der Schnittstelle nur noch der fehlende Schrägstrich bei
`correspondence/get-by-reference`**, und der hält nichts auf.

Was daraus folgt, ist mehr als eine erledigte Frage: **Was in dieser Datei
nicht steht, gibt es nicht — und was dort steht, ist zu lesen, bevor gefragt
wird.** Viermal in dieser Woche lag die Antwort darin: die benötigten Rechte,
die Herkunft von `attachmentId` und `postFileUniqueKey`, die Bedeutung von
`isInbox`, und die Seitenzählung.

**1858 Prüfungen grün.**

---

## 12.10.2026, später — die Vorgeschichte ist umgeschrieben, und dabei fiel zweierlei auf

Auf Anweisung der Kanzlei. Alle **58 Commits** des Zweigs `2.0` sind neu
geschrieben: Dateien **und** Commit-Texte, sechs der Texte waren betroffen.
Die Beschreibungsdatei des Herstellers blieb ausgenommen — ihre Beispiele sind
seine, und das Programm vergleicht sich gegen sie.

Vorher gesichert als `git bundle` außerhalb des Programmordners, und der alte
Stand des Zweigs steht notiert, falls etwas zurückzuholen wäre.

### Zwei Funde, die erst die Umschreibung zutage gefördert hat

Die Gegenprobe war: **Der heutige Arbeitsstand muss unverändert bleiben.**
Wenn das Umschreiben der Vorgeschichte den heutigen Stand ändert, dann war der
heutige Stand nicht sauber. Er war es nicht — in zwei Dateien.

**1. `MORGEN.md` trug den echten Namen noch.** Und zwar in dem Eintrag, der
seine Entfernung *beschreibt*: Die Fundtabelle vom 11.10.2026 zitierte das
Rubrum zehnmal, um zu zeigen, wo es überall gestanden hatte.

Der Grund ist unangenehm einfach: Der Austausch lief, **dann** schrieb ich die
Chronik. Die Gegenprobe danach — `grep` über den Bestand — lief vor dem
Schreiben. Der Bericht über den Fund hat den Fund wieder hergestellt, und das
blieb einen Tag so stehen.

> Wer einen Fund beschreibt, schreibt ihn hin. Die Gegenprobe gehört deshalb
> **ans Ende** der Arbeit, nicht in ihre Mitte.

**2. `tests/test_keine_echten_akten.py` fiel durch die eigene Prüfung.** Die
Gegenprobe darin — „fängt das Muster eine echte Nummer wirklich?" — trug zwei
echt aussehende Aktenzeichen ausgeschrieben. Die Prüfung daneben liest jede
Datei, die git kennt, und diese gehört dazu.

Dass sie trotzdem grün lief, lag an einem Zufall der Reihenfolge: Beim Lauf
war die Datei **noch nicht in git**, also stand sie nicht in `git ls-files`.
Beim nächsten Lauf wäre sie rot geworden. Die Probestücke sind jetzt aus
Teilen zusammengesetzt und stehen nirgends als ganze Zeichenkette.

**Beide Male hat die Prüfung getan, was sie soll** — nur eben einen Tag zu
spät und einmal an sich selbst. Das ist kein Argument gegen sie.

### Was damit **nicht** erledigt ist

~~**Der Zweig `main`.**~~ **Erledigt am 12.10.2026** auf ausdrückliche
Anweisung der Kanzlei — siehe den Nachtrag unten.

**Und das Entscheidende, das keine Umschreibung leistet — am 12.10.2026
gemessen, nicht vermutet:** Ein überschreibender Push nimmt die alten Commits
**nicht** vom Server.

Die Probe: ein frisch angelegtes, leeres Repository, als einzige Angabe die
Adresse und die Prüfsumme des alten Stands, dann
`git fetch --depth=1 origin <pruefsumme>`. **Der Server hat ihn herausgegeben**
— nach dem überschreibenden Push, aus einem Verzeichnis, das nichts von dem
Zweig wusste.

Wer die Prüfsumme kennt, kommt also weiter heran. Der offene Pull Request
Nr. 1 hält sie zusätzlich fest; er zeigt die alten Commits in seinem Verlauf.

Sicher weg sind sie erst, wenn das Repository gelöscht und neu angelegt wird —
oder GitHub die unerreichbaren Objekte auf Anfrage entfernt. Das ist eine
Entscheidung der Kanzlei.

**Entlastend bleibt:** Das Repository ist privat, ohne Forks und ohne
Beobachter (nachgesehen am 11.10.2026).


### Nachtrag 12.10.2026 — `main` ist ebenfalls umgeschrieben

Auf Anweisung der Kanzlei. Das ist die **eine** Abweichung von der festen
Vorgabe „nur auf `2.0` schreiben"; danach gilt sie wieder.

`main` trägt eine eigene Geschichte: **79 Commits**, kein gemeinsamer Vorfahr
mit `2.0`, Stand „Fassung 1.0" vom 15.09.2026. Dort standen die Namen nicht
nur in der Vorgeschichte, sondern in den heutigen Dateien — 30-mal die
Aktennummer, 13-mal der Gegner.

**Alle 79 Commits sind neu geschrieben**, Dateien und Texte, mit denselben
Ersetzungen wie bei `2.0`, damit beide Zweige dieselbe Sprache sprechen. Die
Herstellerdatei war auf `main` noch gar nicht vorhanden; sie kam erst am
05.10.2026 dazu.

### Eine Regel hat gefehlt, und die Prüfungen haben es gesagt

Der erste Durchgang ließ `tests/test_webdav_adapter.py` fallen: In einer Zeile
stand zwischen dem Namen und dem Gegner ein Wort in Klammern, und mein Muster
führte beide **unmittelbar nebeneinander**. Es griff deshalb nicht. Dieselbe
Stelle war mir am
11.10.2026 schon einmal entwischt; damals habe ich sie von Hand nachgezogen.

**Diesmal nicht von Hand.** `main` wurde auf den Ausgangsstand zurückgesetzt,
die fehlende Regel eingefügt und neu geschrieben — ein Flickcommit obendrauf
hätte den Fehler verdeckt statt behoben. Danach **426 Prüfungen grün**.

> Eine Ersetzung von Hand repariert eine Stelle. Eine Regel repariert alle,
> die so aussehen — auch die, die man noch nicht gesehen hat.

### Zwei Gegenproben, nicht eine

1. **Kein Treffer** in einem der 79 Commits, weder in Dateien noch in Texten.
2. **Nur ersetzt, nichts zerstört:** Alle 92 geänderten Zeilen (46 raus, 46
   rein) tragen einen der ersetzten Begriffe. Eine Umschreibung, die eine
   Datei beschädigt, fiele in Gegenprobe 1 nicht auf — dort wäre sie sogar
   besonders sauber.

**Stand jetzt:** `main` auf `1e538cd`, `2.0` auf `dd1074c`, beide entfernten
Zweige geprüft und sauber.

**Unverändert bleibt, was keine Umschreibung leistet:** Die alten Commits sind
über ihre Prüfsumme weiter vom Server zu holen — am 12.10.2026 gemessen. Sicher
weg sind sie erst, wenn das Repository gelöscht und neu angelegt wird.

### Nachtrag 12.10.2026 — Pull Request Nr. 1: er war schon zu, und es ändert nichts

Die Kanzlei hat angewiesen, ihn zu schließen. **Er war es bereits** — geschlossen
am 12.10.2026 um 13:04:53 UTC, **nicht zusammengeführt**, und nicht von mir.

Das ist genau die Minute des überschreibenden Pushes auf `main`. Die Erklärung
liegt nahe: Der Pull Request lief von `2.0` nach `main`; nachdem `main` eine
neu geschriebene Geschichte ohne gemeinsamen Vorfahr bekam, war er nicht mehr
zusammenführbar, und GitHub hat ihn selbst geschlossen. Ich habe ihn also nicht
geschlossen, sondern vorgefunden.

### Und die Probe sagt: Es ändert nichts

Dreimal gefragt, aus einem frisch angelegten, leeren Verzeichnis, nur mit
Adresse und Prüfsumme:

| Alter Stand | Noch zu holen? | Was darin steht |
|---|---|---|
| alter Kopf von `2.0` | **ja** | 13 Fundstellen des Namens, 9 des Gegners |
| alter Kopf von `main` | **ja** | 3 und 13 Fundstellen, dazu 30-mal die Aktennummer |
| Zwischenstand aus dem Pull Request | **ja** | — |

**Der geschlossene Pull Request gibt die alten Commits nicht frei.** Das ist
keine Eigenheit dieses Falles: Ein Commit bleibt auf dem Server erreichbar,
solange der Anbieter ihn nicht aufräumt, und wann das geschieht, bestimmt nicht
die Kanzlei.

> Drei Maßnahmen, drei Messungen, dasselbe Ergebnis: Umschreiben, überschreibend
> pushen, Pull Request schließen — die alten Stände bleiben abrufbar.

**Damit ist belegt, was vorher eine Vermutung war:** Es bleibt genau ein Mittel,
das sicher wirkt — **das Repository löschen und neu anlegen.** Alles andere
verringert die Auffindbarkeit, nicht die Verfügbarkeit.

Wer die Prüfsumme nicht kennt, kommt allerdings auch nicht heran: Sie steht in
keinem Verzeichnis mehr, der Zweig zeigt woanders hin, und das Repository ist
privat, ohne Forks und ohne Beobachter. Das ist kein Schutz, auf den man sich
verlässt — aber es ist der Unterschied zwischen „offen zugänglich" und „für
den auffindbar, der die Nummer schon hat".

### Nachtrag 12.10.2026 — zum dritten Mal derselbe Fehler, und jetzt eine Prüfung dagegen

Beim Bündeln des bereinigten Standes zur Gegenprobe fiel auf: **Der Name des
Gegners stand wieder in `MORGEN.md`.** In dem Absatz, der beschreibt, warum
beim Umschreiben von `main` eine Ersetzungsregel gefehlt hat — ich hatte die
Regel zitiert, und die Regel enthält den Namen.

Das ist derselbe Vorgang wie zweimal vorher an diesem Tag:

| Wo | Was |
|---|---|
| Chronik, 11.10. | Die Fundtabelle zitierte das Rubrum, um zu zeigen, wo es stand |
| Prüfdatei, 12.10. | Die Gegenprobe trug echt aussehende Aktenzeichen ausgeschrieben |
| Chronik, 12.10. | Der Bericht über die fehlende Regel zitierte die Regel |

Dreimal dieselbe Bewegung: **Die Beschreibung eines Fundes stellt den Fund
wieder her.**

### Warum es dreimal passieren konnte

Für die **Aktenzeichen** gab es seit heute Vormittag eine Prüfung. Für die
**Namen** nicht — dort lebte die Regel allein in meiner Aufmerksamkeit. Und
Aufmerksamkeit ist genau das, was bei der dritten Wiederholung nachlässt.

> Eine Regel, die nur jemand im Kopf hat, ist keine Regel. Sie ist eine
> Absicht.

`tests/test_keine_echten_akten.py` prüft jetzt beides. Die Namen stehen darin
**zusammengesetzt**, nicht ausgeschrieben — sonst fiele die Datei durch sich
selbst, wie es der ersten Fassung heute Vormittag ergangen ist. Dazu zwei
Gegenproben: dass das Muster überhaupt sucht, und dass es „sauer" und
„Sauerstoff" in Ruhe lässt.

**Gefunden hat es die Gegenprobe am Bündel**, nicht die Prüfungen — die
suchten die Namen ja nicht. Das war Glück. Jetzt ist es keines mehr.

---

## 12.10.2026 — das neue Repository steht

Auf Anweisung der Kanzlei. **Das Anlegen konnte ich nicht selbst** — die
GitHub-Zugangsdaten dieser Sitzung gelten nur für das eine Repository, das
Anlegen eines neuen wird mit Status 403 abgewiesen. Die Kanzlei hat es
angelegt, dann war es anzuhängen und zu füllen.

| | |
|---|---|
| Neu | `JosefBlack/jusperfect`, privat, leer angelegt |
| Zweig `2.0` | 63 Commits, 1861 Prüfungen grün |
| Zweig `main` | 79 Commits, 426 Prüfungen grün |

### Die Gegenprobe lief am Server, nicht am Arbeitsstand

Das ist der Unterschied, auf den es ankommt: Der Arbeitsstand war längst
geprüft. Geprüft werden musste, was wirklich **oben** liegt. Also frisch
geklont und darin gesucht:

* **142 Commits**, beide Zweige, Dateien **und** Commit-Texte, mit
  Wortgrenzen: kein Treffer.
* **Die Prüfungen laufen aus dem frischen Klon** — 1861 auf `2.0`, 426 auf
  `main`. Damit steht, dass der Push nichts verloren hat; eine Suche allein
  hätte auch ein halbes Repository für sauber erklärt.

### Was noch zu tun bleibt, und zwar von der Kanzlei

1. **Den Vorgabezweig auf `2.0` stellen.** Das neue Repository zeigt auf
   `main` — die Kanzlei arbeitet aber auf `2.0`, und spätere Sitzungen holen
   sich den Vorgabezweig. Einstellungen → *Default branch* → `2.0`.
2. **Das alte Repository löschen.** Das ist der Schritt, der wirkt; alles
   davor hat die Lage nur vorbereitet. Solange es steht, sind die alten
   Commits über ihre Prüfsumme erreichbar — dreimal gemessen am 12.10.2026.
3. **Die örtlichen Kopien auf beiden Kanzleirechnern** zeigen noch auf das
   alte Repository und tragen dessen Vorgeschichte. Sie gehören neu geklont,
   nicht umgehängt: Ein `git remote set-url` tauscht die Adresse, nicht die
   Geschichte.

### Was dieser Sitzung nicht gelingt

Der **Prüfbericht der Zweitprüfung** nennt eine ZIP mit einer Prüfsumme. Ob
die Namen darin lagen, ist hier nicht festzustellen — die Datei liegt auf dem
Rechner der Kanzlei. Diese Frage bleibt offen, und sie ist die einzige, bei
der es um etwas geht, das das Haus schon verlassen hat.

---

## 12.10.2026 — das alte Repository ist gelöscht, und die Probe fällt zum ersten Mal anders aus

Die Kanzlei hat den Vorgabezweig auf `2.0` gestellt und das alte Repository
gelöscht.

### Die vierte Messung

Dieselbe Probe wie dreimal zuvor — frisch angelegtes, leeres Verzeichnis, nur
Adresse und Prüfsumme:

| Alter Stand | 12.10., vorher | 12.10., nach dem Löschen |
|---|---|---|
| alter Kopf von `2.0` | zu holen | **nicht mehr erreichbar** |
| alter Kopf von `main` | zu holen | **nicht mehr erreichbar** |
| Zwischenstand des Pull Requests | zu holen | **nicht mehr erreichbar** |

Und das Repository selbst: *„repository not found"*.

> Umschreiben, überschreibend pushen, Pull Request schließen — dreimal keine
> Wirkung. Löschen — Wirkung. Was dazwischen lag, war Vorbereitung.

### Ein Verlust, und er geht auf mein Konto

`ANLEITUNG.md` nennt drei Zweige: *„Daneben liegen `main` und `fassung-1.0`;
in beiden steht die ältere Fassung 1.0."*

**Den Zweig `fassung-1.0` habe ich nicht mitgenommen.** Er steht in keiner
Sicherung, nicht im neuen Repository, und das alte gibt es nicht mehr.

Der Fehler ist einfach zu benennen: Ich habe die Zweige mit `git branch -a`
aufgezählt — das zeigt, was **geholt** ist, nicht, was auf dem Server liegt.
`git ls-remote --heads` hätte alle drei gezeigt. Vor einem unumkehrbaren
Schritt ist die Frage „was ist alles da?" am Server zu stellen, nicht am
eigenen Verzeichnis.

**Was vermutlich nicht verloren ist:** Die Anleitung sagt, in `fassung-1.0`
und `main` stehe **dasselbe** — die ältere Fassung 1.0 —, und der Kopf von
`main` heißt wörtlich „Fassung 1.0". Dass der Inhalt erhalten ist, ist damit
wahrscheinlich; **dass die beiden auf denselben Commit zeigten, ist es nicht
mehr zu prüfen.** Ich sage das so, weil ich es nicht besser weiß.

Wenn der Zweig gebraucht wird, lässt sich bei GitHub nachfragen, ob ein
kürzlich gelöschtes Repository wiederhergestellt werden kann. Ob und wie lange
das geht, weiß ich nicht und rate es nicht.

### Dazu ein zweiter Fehler, von der Kanzlei bemerkt

Ich hatte geraten, die örtlichen Kopien auf beiden Rechnern **neu zu klonen**.
Die Rückfrage lautete sinngemäß: Was ist mit der Eingabeaufforderung gemeint?

**Die Kanzlei benutzt gar kein git.** `ANLEITUNG.md`, Schritt 2: „Grüner Knopf
*Code* → *Download ZIP*". Ein Klon hat dort nie gestanden; meine Anweisung war
für einen Arbeitsablauf gedacht, den es im Haus nicht gibt.

**Was dadurch richtig bleibt und was nicht:**

* **Falsch:** „die Kopien neu klonen". Es gibt keine Klone, also auch keine
  alte Vorgeschichte auf den Rechnern.
* **Richtig, und wichtiger:** Auf beiden Rechnern liegt ein **entpackter
  ZIP-Ordner** mit dem Stand von vor der Bereinigung. Darin stehen Name,
  Gegner und Aktenzeichen — in `MORGEN.md`, in `UEBERGABE.md`, in den
  Prüfdateien. Das ist der örtliche Rückstand, und er wird durch eine neue ZIP
  **überschrieben**, nicht gelöscht: Die Anleitung sagt ausdrücklich, dass nur
  ersetzt wird, was auch im ZIP steht.

### `ANLEITUNG.md` stimmt an drei Stellen nicht mehr

Sie gehört zu den vier Dateien, die nur auf ausdrückliche Anweisung geändert
werden. Deshalb hier benannt, nicht geändert:

| Zeile | Was dort steht | Was gilt |
|---|---|---|
| 49 | die Adresse des alten Repositorys | es ist gelöscht — der Verweis geht ins Leere |
| 54 | `jusperfect--2.0.zip`, Ordner `jusperfect--2.0` | jetzt `jusperfect-2.0.zip` und `jusperfect-2.0` |
| ~57 | „daneben liegen `main` und `fassung-1.0`" | es gibt nur noch `main` |

### Nachtrag 12.10.2026 — die Sicherungen sind gelöscht, und der Container ist durchgesehen

Auf Anweisung der Kanzlei. Drei `git`-Bündel: zwei mit dem Stand **vor** der
Bereinigung, eines mit dem bereinigten. Alle drei weg, der Ordner dazu auch.

Damit ist auch das letzte Mittel fort, die Umschreibung rückgängig zu machen.
Das ist der Zweck, nicht ein Nebeneffekt.

### Dabei fiel zweierlei auf, das ich sonst übersehen hätte

**1. Im Arbeitsverzeichnis lagen noch unerreichbare git-Objekte.** Neun Stück,
darunter zwei Blobs und zwei Commit-Texte, die die Namen trugen — Reste der
Umschreibungen und des überschreibenden Pushes. Nicht auf dem Server; der war
am frischen Klon geprüft. Aber hier.

`git reflog expire --expire-unreachable=now --all` und `git gc --prune=now`
haben sie entfernt. Danach lassen sich die alten Prüfsummen nicht einmal mehr
auflösen: `git cat-file -t` sagt zu jeder „weg".

> Ein Repository, das sauber **aussieht**, hat die alten Stände oft noch —
> nur nicht mehr in einem Zweig. Erreichbarkeit ist nicht Abwesenheit.

**2. Meine eigenen Werkzeuge trugen die Namen.** Die Ersetzungslisten, mit
denen umgeschrieben wurde, führen notwendigerweise beide Seiten: links den
echten Namen, rechts den erfundenen. Sie lagen im Arbeitsordner und sind jetzt
ebenfalls gelöscht.

Das ist dieselbe Bewegung wie dreimal vorher an diesem Tag, nur eine Ebene
tiefer: **Das Werkzeug gegen den Fund enthält den Fund.**

### Die abschließende Probe

Der ganze Container, Datei für Datei, dazu jedes gepackte git-Objekt einzeln:

* **Ein einziger Treffer** — `schnittstelle/jurnodes-api-1.0.2.json`. Der
  Hersteller führt in seinen eigenen Beispielen zufällig denselben Nachnamen
  (es ist der häufigste in Deutschland; er steht dort an drei Stellen, in einer
  Briefanrede und in zwei erfundenen Firmen). Die Datei gehört ihm, das
  Programm vergleicht sich gegen sie, und sie bleibt unberührt.

  **Der Satz oben ist in seiner ersten Fassung durch die eigene Prüfung
  gefallen** — ich hatte die Beispiele des Herstellers *zitiert*. Die Regel
  kennt keine Ausnahme für Zitate, und das ist richtig so: Ein Zitat sieht in
  einer Suche aus wie ein Vorkommen, weil es eines ist.
* Sonst nichts. Nicht im Arbeitsverzeichnis, nicht in den git-Objekten, nicht
  im Arbeitsordner dieser Sitzung.

### Nachtrag 12.10.2026 — `ANLEITUNG.md` ist nachgezogen, auf ausdrückliche Anweisung

Die Datei gehört zu den vier, die nur auf Anweisung geändert werden. Die
Anweisung lag vor; geändert sind genau die drei benannten Stellen:

| Was | Vorher | Jetzt |
|---|---|---|
| Adresse | das gelöschte Verzeichnis | das neue |
| Dateiname | doppelter Bindestrich | einfacher |
| Zweige | „`main` und `fassung-1.0`" | nur noch `main` |

Dazu **ein Absatz, der nicht verlangt war** und den ich nenne, damit er nicht
unbemerkt bleibt: ein Hinweis für den Fall, dass die alte Adresse als
Lesezeichen gespeichert ist. Ohne ihn stünde der Leser vor einer Seite, die es
nicht gibt, und wüsste nicht, warum. Er sagt, dass bereinigt wurde und warum —
ohne Namen, ohne Aktenzeichen.

### Und der verlorene Zweig ist doch belegt erhalten

Bei der Durchsicht ist aufgefallen, was gestern noch eine Vermutung war.
`FASSUNGEN.md` führt eine Tabelle der Zweige, und dort steht:

> `main` | zurzeit derselbe Stand wie `fassung-1.0`

Das ist keine Erinnerung und keine Ableitung, sondern eine Angabe, die
geschrieben wurde, **als es beide noch gab**. Damit steht fest: Mit
`fassung-1.0` ist eine Zweigbezeichnung verloren, **kein Inhalt**. Der Stand
liegt in `main`.

Der Fehler bleibt einer — die Zweige am Server abzufragen hätte ihn vermieden.
Aber sein Schaden ist kleiner, als er aussah.

### Was noch nicht stimmt, und wo ich nichts geändert habe

Dieselbe Angabe steht in weiteren Dateien, die **nicht** zu den vier gehören.
Sie sind dadurch heute falsch:

| Datei | Was dort steht |
|---|---|
| `README.md` | „`main` und `fassung-1.0`" |
| `FASSUNGEN.md` | eine Zeile je Zweig, dazu `git checkout fassung-1.0` als Anleitung |
| `UEBERGABE.md` | „`fassung-1.0` bleibt unangetastet" |
| `AWS-EINRICHTEN.md` | der alte Ordnername mit doppeltem Bindestrich |

Die Anweisung lautete auf `ANLEITUNG.md`, und dabei bleibt es, bis die Kanzlei
etwas anderes sagt. **Besonders `FASSUNGEN.md` sticht hervor:** Dort steht ein
Befehl, der heute ins Leere greift.
