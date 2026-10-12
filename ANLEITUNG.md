# jusperfect – Anleitung für den Anwender

> **Dieses Dokument wird nur auf ausdrückliche Anweisung geändert.**
> Es ist die Anleitung, die in der Kanzlei benutzt wird. Sie soll sich nicht
> unter der Hand verschieben, weil im Programm etwas umgebaut wurde.

> **Stand: 05.10.2026.** Das Programm arbeitet seit dem 23.09.2026 über die
> Schnittstelle mit den **echten Akten** der Kanzlei. Was vor einer Benutzung
> **über die beiden Anwälte hinaus** noch fehlt, steht am Ende unter „Was noch
> nicht freigegeben ist" — vor allem die Datenschutz-Folgenabschätzung.
>
> Zum Kennenlernen liegen vier erfundene Testakten bei. Nehmen Sie für den
> ersten Durchgang die.

---

## Teil 1 – Installation

### Was Sie brauchen

| | |
| --- | --- |
| Betriebssystem | Windows 10 oder 11 |
| Festplatte | rund 200 MB |
| Internet | einmalig für die Einrichtung |
| KI-Zugang | **für den Probelauf nicht nötig**; für den AWS-Weg (Schritt 4) ein AWS-Konto |

### Schritt 1: Python installieren

jusperfect ist ein Python-Programm. Python ist kostenlos.

**Gebraucht wird Python 3.12** (3.11 geht auch). Neuere Fassungen laufen
**nicht** – nehmen Sie deshalb nicht den großen Knopf auf der Startseite von
python.org, der bietet immer die allerneueste an.

1. <https://www.python.org/downloads/release/python-3128/> öffnen
2. Ganz unten unter „Files" auf **„Windows installer (64-bit)"** klicken und
   die Datei starten
3. **Wichtig:** im ersten Fenster unten **„Add python.exe to PATH"** ankreuzen.
   Ohne dieses Häkchen findet der nächste Schritt Python nicht.
4. Auf „Install Now" klicken und warten

Ist 3.11 oder 3.12 schon vorhanden, überspringen Sie diesen Schritt. Eine
neuere Fassung darf daneben stehen bleiben, sie stört nicht – der Starter sucht
sich die richtige. Findet er keine, sagt er es und verlinkt die richtige Seite.

### Schritt 2: Das Programm herunterladen

1. <https://github.com/JosefBlack/jusperfect> öffnen und anmelden
2. Grüner Knopf **„Code"** → **„Download ZIP"**
3. Entpacken an einen Ort, an dem es bleiben darf – etwa `C:\jusperfect`.
   **Nicht** nach „Downloads": von dort wird gern aufgeräumt.

Die Datei heisst `jusperfect-2.0.zip`, der entpackte Ordner `jusperfect-2.0`.
Sie dürfen ihn umbenennen; die Dateien darin müssen aber beieinander bleiben.

> **Zur Einordnung, falls Sie sich wundern.** Oben links steht ein Knopf mit
> **`2.0`** darauf – das ist die Arbeitsfassung und zugleich die
> Voreinstellung, Sie müssen dort nichts umstellen. Daneben liegt `main`; dort
> steht die ältere **Fassung 1.0**. Die brauchen Sie nur, wenn Sie einmal
> zurück wollen.

> **Falls Sie noch die alte Adresse gespeichert haben** (sie endete auf einen
> Bindestrich): Die gibt es seit dem 12.10.2026 nicht mehr. Das Verzeichnis
> wurde neu angelegt, weil in seiner Vorgeschichte ein Aktenzeichen und ein
> Mandantenname standen. Der Inhalt ist derselbe – nur die Adresse ist neu
> und die Vorgeschichte bereinigt.

### Schritt 3: Starten

**`START-DEMO.bat`** doppelklicken.

Beim ersten Mal richtet sich alles selbst ein – das dauert eine knappe Minute.
Danach öffnet sich der Browser. Als Nutzerkennung **`ra-weber`** eintragen.

Zum Beenden das schwarze Fenster schließen.

> **Der Probelauf arbeitet ohne KI.** Er zeigt den vollständigen Ablauf mit
> Mustern statt einem Sprachmodell. Sie sehen also, *wie* gearbeitet wird –
> nicht, wie gut das Modell antwortet.

### Auf einem neuen Rechner: was nicht mitkommt

Das ZIP enthält das Programm und die erfundenen Testakten. **Nicht** darin sind
die Dinge, die zu Ihrem Rechner und Ihrem Konto gehören – die müssen einmal neu
eingetragen werden:

| Was | Wie |
|---|---|
| AWS-Zugangsschlüssel | `ZUGANG-EINTRAGEN.bat` – fragt die beiden Werte ab |
| Eigene Einstellungen (`setx …`) | noch einmal setzen, etwa das AWS-Aktengedächtnis |
| Auftragsordner | in `START-AWS.bat` das `REM` vor `JUSPERFECT_AUFTRAG_ORDNER` wegnehmen |
| Verknüpfungen auf dem Schreibtisch | `VERKNUEPFUNG.bat` einmal doppelklicken |

Das örtliche Aktengedächtnis des alten Rechners kommt nicht mit. Darin standen
nur die erfundenen Akten; es geht nichts verloren. Ein Gedächtnis, das **in der
Akte** liegt, liegt auf dem Kanzleilaufwerk und ist auf dem neuen Rechner
sofort wieder da.

### Später: auf den neuesten Stand bringen

Dasselbe noch einmal – ZIP herunterladen, entpacken, den Inhalt über Ihren
Programmordner kopieren und vorhandene Dateien ersetzen lassen.

**Ihre eigenen Sachen überschreibt das nicht.** Ersetzt wird nur, was auch im
ZIP steht; alles andere bleibt unangetastet liegen. Die AWS-Zugangsdaten stehen
ohnehin in Ihrem Windows-Benutzerprofil, der Auftragsordner und die Akten auf
dem Kanzleilaufwerk, und das örtliche Aktengedächtnis (`.jusperfect-gedaechtnis`)
kommt im ZIP nicht vor.

**Eine Ausnahme:** Was Sie in einer Startdatei von Hand geändert haben – etwa
die Zeile mit dem Auftragsordner oder eine andere Kostengrenze –, wird ersetzt.
Notieren Sie sich solche Zeilen, bevor Sie kopieren, und tragen Sie sie danach
wieder ein.

### Schritt 4 (später): Mit dem echten Modell arbeiten

Es gibt zwei Starter. Sie unterscheiden sich in **einem** Punkt: wer antwortet.

| | `START-DEMO.bat` | `START-AWS.bat` |
|---|---|---|
| Antwort von | Mustern im Programm | dem echten Sprachmodell bei AWS |
| Akten | die beiliegenden erfundenen | dieselben erfundenen |
| Kosten | keine | wenige Cent je Frage |
| Voraussetzung | nur Python | ein eingerichtetes AWS-Konto |

Der Ablauf ist in beiden Fällen derselbe – Akte öffnen, Dokumente wählen,
fragen, Belege lesen. Nur die Qualität der Antwort ist eine andere.

**Für den AWS-Weg folgen Sie einmalig
[AWS-EINRICHTEN.md](AWS-EINRICHTEN.md).** Dort steht Schritt für Schritt, wie
Sie Claude in Ihrem AWS-Konto freischalten, einen Benutzer mit eng gefassten
Rechten anlegen und zwei Kostenbremsen setzen. Rechnen Sie mit einer Stunde,
davon die Hälfte Wartezeit.

Danach genügt der Doppelklick auf `START-AWS.bat`. Es prüft den Zugang selbst
und startet **nur, wenn die Prüfung durchläuft** – ein halb eingerichteter
Zugang fällt Ihnen so vor der Arbeit auf, nicht mittendrin.

> **Auch mit AWS bleiben es die erfundenen Akten.** `START-AWS.bat` liest
> ausschließlich aus `testdaten/akten`. Wann echte Akten zulässig sind, steht
> am Ende unter „Was noch nicht freigegeben ist".

### Was der AWS-Weg im Alltag ändert

**Sie sehen Kosten.** Oben rechts steht der Verbrauch des laufenden Monats. Der
Knopf **Nachweis** zeigt je Aufruf, was gegangen ist – Umfang und Betrag, nie
Aktentext.

**Sie zahlen für das, was Sie hinüberziehen.** Ziehen Sie in die Arbeitsakte
nur die Dokumente, die zur Frage gehören. Für eine Frage zur Unfallschilderung
braucht es nicht die gesamte Korrespondenz.

**Mehrere Fragen zur selben Akte sind günstiger als eine.** Die zweite und jede
weitere nutzen einen Zwischenspeicher; das Material wird nur einmal voll
bezahlt. Es lohnt sich, an einer Akte zu bleiben, statt zwischen Akten zu
springen.

**Ist die Monatsgrenze erreicht, hört das Programm auf zu fragen.** Das ist
kein Fehler, sondern die Bremse. Die Grenze steht in `START-AWS.bat`.

---

## Teil 2 – Gebrauch

### Der Grundgedanke in drei Sätzen

**jur|nodes bleibt die führende Akte.** jusperfect liest daraus, arbeitet mit
einer Kopie und schreibt nur zurück, wenn Sie es ausdrücklich freigeben.

**Jede Aussage trägt eine Fundstelle.** Was das Programm behauptet, muss auf
eine mitgeschickte Passage zeigen – sonst fällt der Satz aus der Antwort. Lieber
eine kürzere Antwort als eine erfundene.

**Nichts läuft automatisch.** Kein Schreiben, kein Versenden, keine
Fristberechnung. Das Programm bereitet vor; entschieden wird von Ihnen.

### Der Selbsttest: Stehen die Absicherungen?

Auf der Seite „Akte öffnen" steht unten der Knopf **Selbsttest**. Er zeigt in
einer Liste, was das Programm gerade prüft:

| | |
|---|---|
| Wer antwortet | Claude bei AWS – oder der Demo-Anbieter auf diesem Rechner |
| Region | welche es ist, und dass sie in der EU liegt |
| Zugang zu AWS | unter welchem Benutzer gearbeitet wird |
| AWS schreibt nichts mit | ob die Modellaufrufprotokollierung aus ist |
| Schutzgeländer | ob ein Bedrock-Guardrail vorgeschaltet ist |
| Aktenzugang | ob der Aktenbestand erreichbar ist und wie viele Akten er hat |
| Aktengedächtnis | wo es liegt – in der Akte, bei AWS oder auf diesem Rechner |
| Kostenbremse | wie viel von der Monatsgrenze verbraucht ist |

Während die Punkte erscheinen, fährt oben ein Wagen die Strecke ab; an der
Zielflagge steht das Ergebnis in einem Satz. Das Ganze dauert unter einer
Sekunde. Wer in Windows die Bewegungseffekte abgestellt hat, bekommt alles auf
einmal – die Auskunft ist dieselbe.

Ein Haken heisst: geprüft und in Ordnung. Ein Ausrufezeichen heisst: kein
Fehler, aber eine offene Frage – und die Zahl am Knopf sagt Ihnen schon vor dem
Öffnen, wie viele es sind. Ein Strich heisst: trifft hier nicht zu, etwa alles
zu AWS im Demo-Betrieb.

**Der Selbsttest kostet nichts** und schickt keinen Aktentext hinaus. Er fragt
die eigenen Einstellungen, den Aktenzugang und zwei Verwaltungsauskünfte bei
AWS ab.

**Mehrere Modelle.** jusperfect kann je Arbeit ein eigenes Modell benutzen – ein
kleines, schnelles für die Eingangsprüfung, ein starkes für die Analyse. Der
Selbsttest zeigt deshalb unten jedes eingebundene Modell einzeln, mit der
Arbeit, die es tut, und sagt, ob die Zugriffsrichtlinie der Kanzlei es
überhaupt abdeckt. Ein Modell, das sie nicht kennt, wird beim ersten Aufruf
abgewiesen – das soll im Startbild stehen und nicht mitten in einer Akte
auffallen.

Ob ein Modell wirklich antwortet, steht erst nach einem **Modell-Testlauf** fest.
Das ruft jedes einmal auf – ein Wort, Bruchteile eines Cents, kein Aktentext –
und geschieht deshalb nur auf Ihren Klick, nicht bei jedem Start. Die
Einstellungen dafür – für `…` steht jeweils eine Kennung aus der Tabelle:

**Schreiben Sie eine Kennung niemals aus dem Namen ab, den die AWS-Konsole
anzeigt.** Das hat uns am 16.09.2026 einen Prüfbogenlauf gekostet. Aus „Opus
4.6" wurde `anthropic.claude-opus-4-6` – und das ist falsch. So sehen die fünf
Kennungen aus, die das Konto der Kanzlei wirklich führt:

| Modell | Kennung | Bauart |
|---|---|---|
| Opus 4.6 | `anthropic.claude-opus-4-6-v1` | „-v1", kein Datum |
| Opus 4.5 | `anthropic.claude-opus-4-5-20251101-v1:0` | Datum und Fassung |
| Sonnet 4.6 | `anthropic.claude-sonnet-4-6` | weder noch |
| Sonnet 4.5 | `anthropic.claude-sonnet-4-5-20250929-v1:0` | Datum und Fassung |
| Haiku 4.5 | `anthropic.claude-haiku-4-5-20251001-v1:0` | Datum und Fassung |

Drei Bauarten bei fünf Modellen. Es gibt kein Muster, aus dem sich eine Kennung
ableiten liesse – **fragen Sie das Konto, leiten Sie nichts her.** Das tut
`MODELLE-ANZEIGEN.bat`: Es fragt Ihr Konto, probiert jedes Modell mit einem
einzigen Wort an und schreibt die Kennungen hin, die wirklich antworten. Diese
schreiben Sie Zeichen für Zeichen ab.

Stimmt die Kennung nicht, sagt das Programm jetzt, woran es liegt – und
unterscheidet dabei zwei Fälle, die leicht zu verwechseln sind:

- **„Die Modellkennung kennt AWS nicht."** Es gibt sie so nicht. Meist eine
  abgekürzte Schreibweise. Abhilfe: `MODELLE-ANZEIGEN.bat`.
- **„Das Modell ist diesem AWS-Konto nicht zugeteilt."** Die Kennung ist
  richtig, aber Ihr Konto darf dieses Modell nicht. Daran lässt sich in der
  Startdatei nichts ändern; nehmen Sie ein anderes aus der Liste. AWS teilt mit
  der Zeit mehr zu.

**Die Kennung beginnt mit `anthropic.`** – das ist die Bedrock-Form. Ein blosses
`claude-opus-4-6-v1` ohne diesen Anfang ist die Kennung der
Anthropic-Schnittstelle und wird von AWS abgewiesen; der Selbsttest zeigt sie
rot an. Den europäischen Vorsatz `eu.` setzt das Programm selbst, wenn er fehlt.

    set JUSPERFECT_MODELL_ID=…                             das Modell für alles
    set JUSPERFECT_MODELL_ID_KLEIN=…                       das kleine, schnelle

    set JUSPERFECT_MODELL_FRAGE=…                          nur für Fragen
    set JUSPERFECT_MODELL_ANALYSE=…                        nur für die Analyse
    set JUSPERFECT_MODELL_ENTWURF=…                        nur für Entwürfe
    set JUSPERFECT_MODELL_TRIAGE=…                         nur für die Eingangsprüfung
    set JUSPERFECT_MODELL_GEDAECHTNIS=…                    nur für das Aktengedächtnis

Es genügt, `JUSPERFECT_MODELL_ID` zu setzen; alles andere ist freiwillig. Was
für eine Arbeit nicht eigens gesetzt ist, nimmt `JUSPERFECT_MODELL_ID` –
Eingangsprüfung und Aktengedächtnis nehmen davor noch
`JUSPERFECT_MODELL_ID_KLEIN`, wenn es gesetzt ist. Genau diese Auflösung zeigt
der Selbsttest: nicht, was Sie eingetragen haben, sondern was tatsächlich
benutzt wird.


### Womit anfangen

Es liegen vier erfundene Akten bei. Für den ersten Durchgang empfehle ich
**115/26 AR** (Kündigungsschutz): Sie hat acht Dokumente und ist absichtlich so
gebaut, dass es etwas zu finden gibt — widersprüchliche Daten, ein Zeuge, der
sich nicht festlegt, eine Betriebsratsanhörung nach der Kündigung.

Was darin steckt, steht in `testdaten/AUFLOESUNG.md`. **Lesen Sie die erst
danach** — sonst prüfen Sie nicht mehr das Programm, sondern Ihre Erinnerung.

Gute erste Fragen an diese Akte:

- *Widersprechen sich die Angaben zum Tatzeitpunkt?*
- *Wann wurde der Betriebsrat angehört?*
- *Welche Beweismittel liegen vor?*

---

### Der Weg durch eine Akte — die Kurzfassung

1. **Suchen**, Akte anklicken.
2. Im Fenster „Dokumente der Akte" ankreuzen, was mitgehen soll — oder **alle
   anhaken**. Dann **Arbeitsfläche öffnen**.
3. Warten, bis die Dokumente gelesen sind. Der Balken sagt, wie weit.
4. Fragen stellen. **Die Belege lesen**, nicht nur die Antwort.
5. Wenn es sich lohnt: **Akte einlesen** (Aktengedächtnis) und **Analyse**.
6. Entwurf, Freigabe — oder einfach schließen. Das Gedächtnis bleibt.

Die nächsten Abschnitte gehen diese sechs Schritte der Reihe nach durch.

---

### 1. Eine Akte öffnen

Aktenzeichen oder Bezeichnung eingeben, **Suchen**, Akte anklicken.

Es öffnet sich das Fenster **„Dokumente der Akte"**: eine Liste mit Häkchen.
**Angehakt heißt: liegt in der Arbeitsakte und geht bei Fragen mit.**

| Knopf | Was er tut |
|---|---|
| **alle anhaken** | hakt alles an, was gerade sichtbar ist |
| **Haken entfernen** | nimmt bei allen Sichtbaren den Haken weg |
| die Felder oben (*Gegner 6*, *Mandant 2* …) | hakt eine ganze Kategorie an oder ab |
| das Suchfeld | filtert nach Titel, Datum oder Kategorie — `gegner 2026-05` findet die gegnerischen Schriftsätze aus dem Mai |

Unten steht, wie viel Sie angehakt haben und ob es für einen Aufruf reicht.

> **Weniger ist oft besser.** Was Sie anhaken, geht an das Modell und wird
> bezahlt. Für eine Frage zur Unfallschilderung braucht es nicht die gesamte
> Korrespondenz.

Die Auswahl lässt sich jederzeit ändern — auch mitten in der Arbeit, über
**‹ Dokumente**.

#### Was nicht von selbst angehakt wird

Trägt der **Titel** eines dieser Wörter, kommt das Dokument **ohne Haken** in
die Liste:

> Rechnung · Kostennote · Gebühren · Vorschuss · Honorar · RSV ·
> Rechtsschutz · Deckungszusage · Deckungsanfrage

Es steht weiter da, nur blasser, und daneben steht der Grund: *nicht
vorgewählt: Rechnung*. Wer es doch braucht, hakt es an. **alle anhaken** lässt
es aus und sagt das in einer Meldung; **ein zweiter Klick holt es dazu.**

Zwei Grenzen, die Sie kennen sollten:

- **Geprüft wird der Titel, nicht der Inhalt.** Eine Rechnung, die „Schreiben
  vom 14.03." heißt, geht durch. Eine Hilfe, keine Gewähr.
- **Es verschwindet nichts.** Das Dokument bleibt sichtbar; nur der Haken
  fehlt.

Eigene Wortliste: in `START-JURNODES.bat`, Abschnitt *„Was nicht von selbst
angehakt wird"*. Dort steht auch, warum in diese Zeile keine Umlaute gehören.

---

### 2. Das Lesen der Dokumente

Nach **Arbeitsfläche öffnen** werden die Dokumente geholt und in lesbare
Abschnitte zerlegt. Bei fünfzig Dokumenten dauert das.

Ein Balken zeigt, wie weit es ist — in Fünferschritten, mit der Zahl daneben.
Solange er läuft, sind die Wege gesperrt, die mitten in das Lesen hineinführen
würden; das Programm sagt das auch. **Anhalten** geht jederzeit, und was
gelesen ist, bleibt gelesen.

#### Gescannte Blätter

Rückscheine, Einschreiben, Vollmachten: Darin steht kein Text, sondern ein Bild
vom Text. Das Programm erkennt das und schickt die Seite an die Texterkennung
von AWS (Textract, Frankfurt — derselbe Auftragsverarbeiter wie für die Texte).

- Die Seiten werden **auf Ihrem Rechner** zu Bildern gemacht. Es wird nichts
  bei AWS abgelegt.
- Kosten: rund **1,50 € je 1000 Seiten** — für eine Akte Bruchteile eines Cents.
- Ob es überhaupt arbeitet, sagt **`TEXTERKENNUNG-PRUEFEN.bat`** in zwanzig
  Sekunden, ohne Akte und ohne Modellaufruf.

Findet die Erkennung nichts, sagt das Programm das — und sagt auch, woran es
liegt, einschließlich einer fehlenden AWS-Berechtigung.

---

### 3. Eine Frage stellen

Frage eintippen, Eingabetaste. Die Antwort erscheint **während sie entsteht**.

Danach steht rechts die Spalte **Belege**. Jede Kennung wie `D2-S1-P3` heißt:
zweites Dokument, erste Seite, dritter Abschnitt. Ein Klick zeigt die
Originalstelle; die tragende Stelle ist darin hervorgehoben.

> **Lesen Sie die Belege, nicht nur die Antwort.** Das ist der eigentliche
> Nutzen: Sie sehen sofort, worauf sich eine Aussage stützt — und ob die Stelle
> das wirklich hergibt.

Steht unter einem Beleg *„Die Stelle ließ sich im Absatz nicht zuordnen — oben
steht sein Anfang. Bitte nachlesen."*, dann zeigt die Karte den ganzen Absatz
statt des Satzes. Das ist kein Fehler, sondern der Hinweis, dass hier Ihr Auge
gebraucht wird.

Steht „kein belastbarer Beleg", hat das Programm zu Ihrer Frage nichts
Belegbares gefunden. Das ist eine ehrliche Antwort, kein Fehler.

---

### 4. Das Aktengedächtnis

Ohne Gedächtnis fängt jede Akte bei jedem Öffnen von vorn an — und wird jedes
Mal neu bezahlt. Mit Gedächtnis kostet das zweite Öffnen einer gelesenen Akte
**rund 5 Cent statt 28 Cent.**

#### Was darin liegt

| | |
|---|---|
| Dokumentauszüge | der Text, bei Scans der erkannte Text |
| Lebenssachverhalt | ein belegter Fließtext über die ganze Akte |
| Zeitstrahl | die Chronologie, fortgeschrieben statt neu gebaut |
| Frühere Fragen und Antworten | die letzten 100 |
| Die letzte Aktenanalyse | mit Datum (siehe Abschnitt 5) |

#### Wo es liegt

**In der Kanzlei: im eigenen AWS-Konto, Frankfurt, verschlüsselt** — nicht in
jur|nodes. In die jur|nodes-Akte geht nur ein **Vermerk**, und nur, wenn Sie
ihn freigeben. Wo es im Einzelfall liegt, steht unten im Gedächtnisfenster und
im Selbsttest; eingestellt wird es mit `JUSPERFECT_GEDAECHTNIS` in der
Startdatei.

#### Die Knöpfe

Rechts **Gedächtnis ›**, dann:

| Knopf | Was er tut | Kostet |
|---|---|---|
| **Akte einlesen** | liest die ganze Akte Portion für Portion ein und bildet daraus Lebenssachverhalt und Zeitstrahl | mehrere Modellaufrufe — es wird vorher gefragt |
| **Auswahl** | öffnet das Fenster: links die Akte, rechts was im Gedächtnis liegt | nichts |
| **Anhalten** | bricht das Einlesen ab; Gelesenes bleibt | — |

Vor dem Einlesen sagt das Programm, wie viele Dokumente noch fehlen, wie viele
Zeichen das sind und mit wie vielen Aufrufen zu rechnen ist. **Erst dann wird
gerechnet.**

#### Was im Gedächtnis steht, nachlesen

Im Fenster **Auswahl** unten: **„Was das Programm sich gemerkt hat"**. Dort
stehen Lebenssachverhalt, Zeitstrahl und die früheren Fragen — **im Wortlaut,
mit den Fundstellen**, so wie sie gespeichert sind. Ein dauerhafter Speicher,
den niemand einsehen kann, wäre eine Zusage ohne Nachweis.

#### Einzelnes wieder herausnehmen

Neben jedem Eintrag steht **„vergessen"**:

- **Rechts in der Spalte „Im Gedächtnis"** — nimmt ein **Dokument** heraus.
  Die Rückfrage zählt vorher ab, was mit herausfällt: der Auszug, die
  gespeicherten Fragen und Zeitstrahleinträge, die ihn zitieren (die fallen
  **ganz**), und die Sätze des Lebenssachverhalts, die nur auf ihm beruhen.
- **In der Liste „Frühere Fragen und Antworten"** — nimmt **eine Frage samt
  Antwort** heraus. Dokumente, Lebenssachverhalt und Zeitstrahl bleiben stehen.

> **Es gibt kein Rückgängig.** Zurücklegen ist möglich, kostet aber ein neues
> Einlesen — bei einem Scan mit Texterkennung — und holt die gelöschten
> Antworten und Zeitstrahleinträge nicht wieder. Lesen Sie die Rückfrage.

Die Akte in jur|nodes bleibt dabei unberührt. Entfernt wird nur, was sich
jusperfect gemerkt hat.

Alles auf einmal wegwerfen geht nur bei den **erfundenen** Testakten, mit
`GEDAECHTNIS-LEEREN.bat`.

---

### 5. Die Aktenanalyse

**Analyse** geht einmal über die ganze Arbeitsakte und liefert sechs Listen:
Chronologie, Beteiligte, Forderungen, Beweismittel, offene Punkte,
Widersprüche. **Jede Zeile trägt ihren Beleg.**

Passt die Akte nicht in einen Aufruf, rechnet das Programm über den
**Lebenssachverhalt** aus dem Gedächtnis — der ist aus allen Dokumenten
entstanden und ein Bruchteil so lang. Erst dadurch findet sich ein Widerspruch,
der zwischen Dokument 8 und Dokument 44 liegt. Der erste Hinweis der Analyse
sagt, worauf sie beruht. Ist die Akte nur **teilweise** eingelesen, verweigert
das Programm: Eine Analyse über zwei Drittel sähe aus wie eine über die ganze
Akte.

#### Sie bleibt stehen

Die Analyse liegt im Aktengedächtnis. Beim nächsten Öffnen der Akte steht sie
wieder da, überschrieben mit **„Aktenanalyse · Stand vom 05.10.26"**. Das
kostet nichts — es wird nichts neu gerechnet.

#### Das Programm merkt, wenn sie veraltet ist

Kommen später Dokumente in die Akte, steht **über** dem Ergebnis ein gelber
Hinweis:

> Seit dieser Analyse ist ein Dokument in die Akte gekommen; es ist darin nicht
> enthalten: Schriftsatz der Gegenseite vom 02.10.  [neu rechnen]

Die Dokumente werden **beim Namen genannt**, damit Sie selbst beurteilen
können, ob es sich lohnt. Das Programm vergleicht dafür die heutige
Dokumentliste der Akte mit der von damals — das kostet keinen Modellaufruf und
geschieht bei jedem Öffnen.

Ein bewusst nicht vorgewähltes Dokument — eine Rechnung etwa, die schon damals
in der Akte lag — gilt dabei **nicht** als neu. Sonst stünde der Hinweis bei
jedem Öffnen da und wäre nach einer Woche nichts mehr wert.

#### Der Knopf fragt nach

Liegt schon eine Analyse vor, fragt **Analyse** vorher: mit dem Datum, mit dem,
was seitdem dazugekommen ist, und mit dem Hinweis, dass neu rechnen einen
Modellaufruf über die ganze Akte kostet. Beim ersten Mal fragt er nicht — da
gibt es nichts zu verlieren.

---

### 6. Der Zeitstrahl

Rechts **Chronologie ›**. Er ist **ohne Modellaufruf gefüllt**: Dokumentdaten
und Fristen stehen in den Stammdaten aus jur|nodes. Eine Analyse reichert ihn
an; was sie gefunden hat, bleibt im Gedächtnis stehen.

**aktualisieren** trägt nach, was seit dem letzten Lauf dazugekommen ist — nur
über die neuen Abschnitte und nur nach Ereignissen. **Ist nichts Neues da,
kostet der Knopfdruck nichts.**

---

### 7. Zwei Bildschirme: Fenster abtrennen

Neben **Chronologie**, **Aktengedächtnis** und **Belege** steht oben rechts das
Zeichen **⧉**. Ein Klick stellt das Fenster auf einen eigenen Browser-Tab, den
Sie auf den zweiten Bildschirm ziehen können.

- Beide Fenster bleiben im Gleichschritt. Was im Hauptfenster geschieht, steht
  sofort auch nebenan.
- **Schließen verliert nichts.** Das abgetrennte Fenster zeigt nur an; der
  Stand liegt im Hauptfenster. Jederzeit wieder aufmachbar über dasselbe
  Zeichen.
- Der Abgleich läuft **innerhalb des Browsers**, nicht über das Netz.

---

### 8. Versehentliches Schließen

Schließen Sie den Tab des **Hauptfensters**, während etwas läuft oder etwas
Ungesichertes dasteht, fragt der Browser nach. Den Wortlaut bestimmt der
Browser, nicht das Programm.

Im **abgetrennten** Fenster fragt nichts — dort geht nichts verloren.

---

### Die weiteren Knöpfe

| Knopf | Wofür |
|---|---|
| **Eingangsprüfung** | Ein neues Schreiben einordnen: Art, Absender, Kernaussage, mögliche Fristauslöser. **Berechnet keine Fristen.** |
| **Entwurf** | Schreiben an Mandant, Gegner, Versicherung, RSV, Mahnung, Aktenvermerk — auch nach eigenen Kanzleimustern |
| **Prüfliste** | Beweisprüfung nach Rechtsgebiet, ohne Modellaufruf |
| **Referenzen** | Urteile und Gesetze neben die Akte stellen; sie werden mitzitiert (Kennung `R…`) |
| **Posteingang** | Ein Schreiben prüfen, bevor es in die Akte geht |
| **Recherche bei Haufe** | Öffnet den Haufe-Copilot im Browser mit Ihrer Anmeldung. jusperfect fasst keine Haufe-Zugangsdaten an. |
| **Gesetz nachschlagen** | Normtext neben die Akte stellen |
| **Nachweis** | Was ist wann an welches Modell gegangen — Umfang und Prüfsumme, **kein Aktentext** |
| **Aufbewahrung** | Übersicht über alle Arbeitsbereiche: Zustände, keine Akteninhalte |
| **Akte abschließen** | Akte in jur|nodes archiviert? Arbeitsstand sichern, dann löschen (siehe unten) |
| **Selbsttest** | siehe oben |

### Eigene Aufträge – Ihre Muster statt fremder Formulierungen

Ein **eigener Auftrag** ist eine Textdatei. Mehr nicht. Sie legen sie in den
Auftragsordner der Kanzlei, und beim nächsten Entwurf steht sie in der Auswahl.

    J:\Kanzlei\jusperfect-auftraege\
      Verkehrsrecht\
        Nutzungsausfall.txt
        Anspruchsschreiben Haftpflicht.txt
      Mietrecht\
        Kündigung Eigenbedarf.txt

Der **Dateiname** wird die Beschriftung, der **Unterordner** das Rechtsgebiet.
Bearbeitet wird die Datei mit dem Editor, den Sie ohnehin benutzen – es braucht
keine zweite Oberfläche dafür, und was auf dem Laufwerk liegt, lässt sich
sichern und weitergeben.

In derselben Datei darf ein **Aufsatz zur Rechtslage** stehen, hinter einer
Trennlinie:

    Entwirf ein Anspruchsschreiben an die gegnerische Haftpflichtversicherung
    zum Nutzungsausfall. Nenne Ausfalldauer und Tagessatz jeweils mit Beleg.

    --- Rechtslage ---

    Zum Nutzungsausfall: Der Bundesgerichtshof hat entschieden ...

Vor der Trennlinie steht die **Anweisung**; sie füllt beim Aufruf das
Anweisungsfeld und bleibt dort änderbar. Dahinter steht **Material**; es geht
dem Entwurf als Hintergrund mit. Erlaubt sind `.txt` und `.md`, höchstens
60.000 Zeichen je Datei – der Text geht bei jeder Verwendung mit hinaus und
wird mitbezahlt, ein ganzes Handbuch gehört nicht dazu.

**Einrichten.** In `START-DEMO.bat` und `START-AWS.bat` steht die Zeile schon,
nur mit `REM` davor. Nehmen Sie das `REM` weg und tragen Sie Ihren Ordner ein:

    set JUSPERFECT_AUFTRAG_ORDNER=J:\Kanzlei\jusperfect-auftraege

Ohne eingetragenen Ordner fehlen die Auswahl beim Entwurf und der unten
beschriebene Knopf. Das ist so gewollt und kein Fehler.

### Einen Auftrag vom Programm vorschlagen lassen

Sie müssen die Datei nicht selbst tippen. Unter jedem fertigen Entwurf steht
**„Als eigenen Auftrag vormerken"**. Das Programm nimmt die Anweisung, die Sie
gerade getippt haben, und schlägt eine Fassung vor, die beim nächsten
gleichartigen Fall wieder passt. Sie sehen Dateinamen und Text in einem Fenster
und können beides ändern. **Erst Ihr Klick auf „Auftrag anlegen" schreibt die
Datei.**

> **Lesen Sie den Text, bevor Sie ihn anlegen.** Ein Auftrag geht danach bei
> *jeder* Akte mit. Streichen Sie alles, was nur zu dieser einen Sache gehört:
> Namen, Beträge, Daten, Aktenzeichen. Das Programm ist angewiesen, das
> wegzulassen – verlassen Sie sich nicht darauf, dafür ist Ihr Blick da.

Einen vorhandenen Auftrag überschreibt das Programm nie. Gibt es den Namen
schon, sagt es das und lässt das Fenster offen, damit Ihr geänderter Text nicht
verlorengeht. Was die Kanzlei über Jahre gefeilt hat, verdrängt kein Vorschlag.

**Was dabei zu AWS geht.** Nur die Art des Schreibens, das Rechtsgebiet und
Ihre eigene Anweisung. **Nicht die Akte** – weder die Passagen noch der
Entwurf. Ein Vorschlag, der aus dem Entwurf entstünde, trüge die Tatsachen
dieses Mandats in eine Datei, die danach bei jeder anderen Akte mitgeht. Das
wäre die eine Stelle, an der so ein Speicher das Mandantengeheimnis über die
Mandatsgrenze trägt, und es geschähe unbemerkt.

**Im Demo-Betrieb** läuft der Weg durch, aber ohne KI wird nichts
verallgemeinert. Das Programm ersetzt nur, was es sicher als Einzelfall
erkennt – Daten, Beträge, Aktenzeichen – und schreibt dazu, dass der Rest von
Hand zu schreiben ist. Wie ein brauchbarer Auftrag aussieht, sehen Sie erst mit
`START-AWS.bat`.

### Etwas in die Akte zurückschreiben

Nur über **Entwurf → Freigabe**. Sie sehen vorher genau den Text, der geschrieben
wird, und bestätigen ihn. Es geht nichts anderes hinaus als das, was dort steht.

### Eine Akte abschließen

Ist die Akte in jur|nodes archiviert, bietet **Abschluss** an:

1. **Vormerken** – erst jetzt beginnt die Übergangsfrist (Vorgabe 30 Tage).
2. Nach Ablauf: Der Arbeitsstand wird **im Wortlaut angezeigt**. Lesen Sie ihn.
3. Nach Ihrem Häkchen: Er geht als Vermerk nach jur|nodes, und **erst danach**
   werden Gedächtnis, Dokumentauszüge und Entwürfe gelöscht.
4. Sie erhalten einen Nachweis: wann, durch wen, was gelöscht wurde.

> **Eine Bearbeitungspause löscht nie etwas.** Auch nach neun Monaten nicht.
> Maßgeblich ist allein der Aktenstatus in jur|nodes.

---

## Was wie lange gespeichert bleibt

Die Frage, die bei einem KI-Programm zuerst zu stellen ist. Hier die Antwort in
einer Tabelle.

| Was | Wo | Wie lange |
|---|---|---|
| **Dokumentauszüge** (bei Scans der erkannte Text) | Aktengedächtnis — AWS-Konto der Kanzlei, Frankfurt, verschlüsselt | dauerhaft, bis zum Abschluss der Akte |
| **Lebenssachverhalt** | ebenda | dauerhaft |
| **Zeitstrahl** | ebenda | dauerhaft, höchstens 500 Einträge |
| **Fragen und Antworten** | ebenda | die letzten 100 |
| **Die letzte Aktenanalyse** | ebenda | dauerhaft, bis sie neu gerechnet wird |
| **Der Gesprächsverlauf im Fenster** | Arbeitsspeicher des Programms | **weg, sobald das schwarze Serverfenster zugeht** |
| **Entwürfe** | ebenda | ebenso |
| **Der Nachweis** (wer, wann, welches Modell, wie viel) | Arbeitsspeicher, beim AWS-Betrieb im AWS-Konto | — ohne Aktentext |
| **In jur|nodes** | die Akte selbst | **nur ein Vermerk, und nur nach Ihrer Freigabe** |

Drei Sätze dazu, die sich zu merken lohnen:

1. **Was dauerhaft bleibt, ist das Aktengedächtnis — sonst nichts.** Darauf
   baut das zweite Öffnen auf.
2. **Was nur in der Sitzung lebt, ist weg, wenn das Programm zugeht.** Ein
   Entwurf, den Sie brauchen, gehört vorher herauskopiert oder freigegeben.
3. **In die Akte in jur|nodes schreibt das Programm nur, wenn Sie es sagen.**

Gelöscht wird das Gedächtnis **nur** über den Abschluss der Akte (siehe dort) —
oder von Hand, einzeln, über **vergessen**. Eine Bearbeitungspause löscht nie
etwas, auch nach neun Monaten nicht.

---

## Wenn etwas klemmt

**„Python wurde nicht gefunden"** – Bei der Installation fehlte das Häkchen
„Add python.exe to PATH". Python erneut installieren, diesmal ankreuzen.

**Der Browser öffnet sich nicht** – Von Hand <http://127.0.0.1:8765> aufrufen.

**„Bitte Nutzerkennung eingeben"** – Oben rechts `ra-weber` eintragen.

**„Keine Akte gefunden oder keine Berechtigung"** – Im Probelauf gibt es nur die
vier erfundenen Testakten. Suchfeld leeren und **Suchen** drücken.

**„jusperfect läuft schon" / „Errno 10048"** – Das Programm läuft bereits, nur
ohne sichtbares Fenster. Es startet kein zweites Mal, weil sonst zwei
Programme auf dieselbe Ablage schrieben. Abhilfe: Im Browser
<http://127.0.0.1:8765> aufrufen — oder, wenn kein Fenster mehr zu sehen ist,
den Task-Manager öffnen (Strg+Umschalt+Esc), unter „Details" den Eintrag
`python.exe` beenden und neu starten.

**„Das AWS-Aktengedächtnis ist nicht erreichbar"** – Der Satz dahinter sagt,
woran es liegt: kein Netz, der Eimer fehlt, die Berechtigung fehlt oder er
liegt in einer anderen Region. Das Programm arbeitet dann **ohne** Gedächtnis
weiter; die Akte wird beim nächsten Mal eben neu eingelesen. Es wartet dabei
nicht mehr minutenlang: nach fünf Sekunden ohne Verbindung gibt es auf.

**„Es fehlt: bedrock:…"** – In der AWS-Zugriffsrichtlinie fehlt genau diese
Berechtigung. Der Name steht in der Meldung; einzutragen ist er in
`infra/iam-nur-claude.json` (siehe `infra/IAM.md`). Der Wortlaut von AWS selbst
geht dabei nie hinaus — eine Abweisung von AWS kann ein Stück der Anfrage
enthalten, und die Anfrage ist Aktentext.

**Die Antwort ist kürzer als erwartet** – Das ist Absicht: Unbelegte Sätze
fallen heraus. Ziehen Sie mehr Dokumente in die Arbeitsakte oder fragen Sie
enger.

### Nur beim AWS-Weg

Der Zugangstest sagt bei jedem dieser Fälle, was zu tun ist. Sie rufen ihn
jederzeit einzeln auf: **`ZUGANG-PRUEFEN.bat`** doppelklicken. Das Fenster
bleibt bis zum Tastendruck stehen, und derselbe Befund steht danach in
`zugangstest.txt` im Programmordner – die Datei dürfen Sie weitergeben, es
steht kein Aktentext darin.

**„AccessDeniedException"** – Meist ist das Modell im AWS-Konto nicht
freigeschaltet (Bedrock → *Model access*). Seltener greift die
Zugriffsrichtlinie. Beides in [AWS-EINRICHTEN.md](AWS-EINRICHTEN.md), Schritt 3
und 4.

**„ValidationException"** – Die Modellkennung passt nicht zu dieser Region. In
Europa ist meist ein Inferenzprofil nötig, das mit `eu.` beginnt.
AWS-EINRICHTEN.md, Schritt 7.

**„Es sind keine AWS-Zugangsdaten hinterlegt"** – `aws configure` fehlt, oder es
lief in einem anderen Windows-Benutzerkonto.

**„Budget erschöpft"** – Die Kostenbremse hat gegriffen. Kein Fehler. Grenze
anheben oder bis zum Monatswechsel warten.

**„AWS schreibt die Modellaufrufe mit"** – Kein Fehler, sondern eine Sperre. Ist
in Bedrock die *Modellaufrufprotokollierung* eingeschaltet, schreibt AWS den
vollständigen Prompt mit – und der Prompt ist der Aktentext. Er läge damit ein
zweites Mal neben der Akte, an einer Stelle, die beim Aktenabschluss nicht
mitgelöscht wird. jusperfect startet deshalb nicht.
Abhilfe: AWS-Konsole → Bedrock → Einstellungen → Modellaufrufprotokollierung
abschalten, dann neu starten.

**„Mit echten Akten ist ein Bedrock-Guardrail zwingend"** – Kein Fehler,
sondern eine Sperre. Das Guardrail ist der Filter, den AWS vor und hinter das
Modell schaltet; es ist die letzte Stelle, an der eine entgleiste Frage oder
Antwort noch aufgehalten wird. Solange Sie mit den erfundenen Testakten
arbeiten, läuft das Programm ohne. Sobald Sie den Adapter auf einen echten
Aktenordner stellen, nicht mehr. Einrichten: `AWS-EINRICHTEN.md`, danach
`set JUSPERFECT_GUARDRAIL_ID=…` in der Startdatei.

**„Lässt sich nicht feststellen: Das Leserecht dafür fehlt"** – Dieselbe Frage,
nur unbeantwortet. In der Zugriffsrichtlinie fehlt
`bedrock:GetModelInvocationLoggingConfiguration` (siehe `infra/IAM.md`). Mit den
erfundenen Testakten läuft das Programm trotzdem und schreibt den offenen Punkt
in den **Nachweis**. Mit echten Akten startet es nicht – dort ist Ungewissheit
ein Nein.

---

## Was noch nicht freigegeben ist

Bevor das Programm **über die beiden Anwälte hinaus** benutzt wird, fehlen:

- **Datenschutz-Folgenabschätzung, Datenschutzhinweise, Mandatsbedingungen.**
  Die fachliche Grundlage steht im Löschkonzept in `SICHERHEIT.md`, die
  technischen Angaben gesammelt in `DSFA-ANGABEN.md` — jeder Wert mit Datum und
  Fundstelle, einschließlich dessen, was **nicht** gesichert ist.
- **Die Auskunft von AWS, in welche Regionen das Schutzgeländer verteilt.** Ein
  Zwischenstand steht in `DSFA-ANGABEN.md`, ausdrücklich als ungesichert
  gekennzeichnet; er nennt auch Zürich, also außerhalb von EU und EWR. Das ist
  beim AWS-Support zu erfragen.
- **Die Ordnerprüfung auf dem Kanzleilaufwerk.** Nur für den Ordnerweg nötig.
  Solange sie nicht gelaufen ist, beruht das Erkennen archivierter Akten auf
  einer Annahme. Am PC: `python -m jusperfect.ordnerpruefung "J:\Akten"` –
  verändert nichts.

**Zwei Dinge, die inzwischen stehen** und hier früher als offen standen:

- **AWS schreibt nichts mit.** Das prüft das Programm bei jedem Start selbst:
  Ist in Bedrock die Modellaufrufprotokollierung an, startet es nicht. Lässt
  sich die Frage nicht beantworten, startet es mit echten Akten ebenfalls
  nicht. Wo es steht: Knopf **Nachweis**, erste Zeile.
- **Das Schutzgeländer.** Mit echten Akten ist ein Bedrock-Guardrail zwingend;
  es ist eingerichtet und wird bei jedem Aufruf vorgeschaltet.

> **Eine offene Frage beim Hersteller von jur|nodes.** Am 05.10.2026 hat sich
> gezeigt, dass das Feld, mit dem die Schnittstelle den Korrespondenzordner
> einer Akte benennt, offenbar nicht auf die Korrespondenz **dieser** Akte
> zeigt: In drei geprüften Akten enthielt dieser Zweig durchweg fremde
> Schriftstücke. **Das Programm liest den Korrespondenzordner seitdem nicht
> mehr mit.** Bis zur Antwort des Herstellers fehlt damit die Korrespondenz;
> das ist die sichere Richtung. Einzelheiten in `MORGEN.md`.

---

## Wo Sie was nachlesen

| Datei | Inhalt |
|---|---|
| `README.md` | Überblick, Betrieb, Aufbau |
| `AWS-EINRICHTEN.md` | AWS-Konto einrichten für den Test mit echtem Modell |
| `SICHERHEIT.md` | Sicherheitsmodell und Löschkonzept |
| `KONZEPT.md` | Warum es so gebaut ist |
| `infra/IAM.md` | AWS-Zugriffsrichtlinie: nur Claude, nur Europa |
