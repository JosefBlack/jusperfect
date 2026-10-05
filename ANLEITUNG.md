# jusperfect – Anleitung für den Anwender

> **Dieses Dokument wird nur auf ausdrückliche Anweisung geändert.**
> Es ist die Anleitung, die in der Kanzlei benutzt wird. Sie soll sich nicht
> unter der Hand verschieben, weil im Programm etwas umgebaut wurde.

> **Diese Fassung ist zum Ausprobieren, nicht für echte Mandantenakten.**
> Was dafür noch fehlt, steht am Ende unter „Was noch nicht freigegeben ist".
> Zum Ausprobieren liegen erfundene Testakten bei – nehmen Sie für den ersten
> Durchgang die.

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

1. <https://github.com/JosefBlack/jusperfect-> öffnen und anmelden
2. Grüner Knopf **„Code"** → **„Download ZIP"**
3. Entpacken an einen Ort, an dem es bleiben darf – etwa `C:\jusperfect`.
   **Nicht** nach „Downloads": von dort wird gern aufgeräumt.

Die Datei heisst `jusperfect--2.0.zip`, der entpackte Ordner `jusperfect--2.0`.
Sie dürfen ihn umbenennen; die Dateien darin müssen aber beieinander bleiben.

> **Zur Einordnung, falls Sie sich wundern.** Oben links steht ein Knopf mit
> **`2.0`** darauf – das ist die Arbeitsfassung und zugleich die
> Voreinstellung, Sie müssen dort nichts umstellen. Daneben liegen `main` und
> `fassung-1.0`; in beiden steht die ältere **Fassung 1.0**. Die brauchen Sie
> nur, wenn Sie einmal zurück wollen.

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

Es liegen drei erfundene Akten bei. Für den ersten Durchgang empfehle ich
**115/26 AR** (Kündigungsschutz): Sie hat acht Dokumente und ist absichtlich so
gebaut, dass es etwas zu finden gibt — widersprüchliche Daten, ein Zeuge, der
sich nicht festlegt, eine Betriebsratsanhörung nach der Kündigung.

Was darin steckt, steht in `testdaten/AUFLOESUNG.md`. **Lesen Sie die erst
danach** — sonst prüfen Sie nicht mehr das Programm, sondern Ihre Erinnerung.

Gute erste Fragen an diese Akte:

- *Widersprechen sich die Angaben zum Tatzeitpunkt?*
- *Wann wurde der Betriebsrat angehört?*
- *Welche Beweismittel liegen vor?*

### Eine Akte öffnen

Aktenzeichen oder Bezeichnung eingeben, **Suchen**, Akte anklicken.

Es öffnet sich der **Zwei-Fenster-Explorer**: links die Akte aus jur|nodes,
rechts Ihre Arbeitsakte. Ziehen Sie die Dokumente hinüber, die zur Frage
gehören – oder nehmen Sie „alle →". Dann **Übernehmen**.

> **Weniger ist oft besser.** Was Sie hinüberziehen, geht an das Modell und
> wird bezahlt. Für eine Frage zur Unfallschilderung braucht es nicht die
> gesamte Korrespondenz.

Die Auswahl lässt sich jederzeit ändern – auch mitten in der Arbeit, über
**Dokumente**.

### Eine Frage stellen

Frage eintippen, Eingabetaste. Die Antwort erscheint **während sie entsteht**.

Danach steht rechts die Spalte **Belege**. Jede Kennung wie `D2-S1-P3` heißt:
zweites Dokument, erste Seite, dritter Abschnitt. Ein Klick zeigt die
Originalstelle.

> **Lesen Sie die Belege, nicht nur die Antwort.** Das ist der eigentliche
> Nutzen: Sie sehen sofort, worauf sich eine Aussage stützt – und ob die Stelle
> das wirklich hergibt.

Steht „kein belastbarer Beleg", hat das Programm zu Ihrer Frage nichts
Belegbares gefunden. Das ist eine ehrliche Antwort, kein Fehler.

### Die weiteren Knöpfe

| Knopf | Wofür |
|---|---|
| **Analyse** | Chronologie, Beteiligte, Forderungen, Beweismittel, offene Punkte, Widersprüche – jede Zeile mit Beleg |
| **Eingangsprüfung** | Ein neues Schreiben einordnen: Art, Absender, Kernaussage, mögliche Fristauslöser. **Berechnet keine Fristen.** |
| **Entwurf** | Schreiben an Mandant, Gegner, Versicherung, RSV, Mahnung, Aktenvermerk – auch nach eigenen Kanzleimustern |
| **Prüfliste** | Beweisprüfung nach Rechtsgebiet, ohne KI-Aufruf |
| **Referenzen** | Urteile und Gesetze neben die Akte stellen; sie werden mitzitiert (Kennung `R…`) |
| **Recherche bei Haufe** | Öffnet den Haufe-Copilot im Browser mit Ihrer Anmeldung. jusperfect fasst keine Haufe-Zugangsdaten an. |
| **Nachweis** | Was ist wann an welches Modell gegangen – Umfang und Prüfsumme, **kein Aktentext** |
| **Abschluss** | Akte in jur|nodes archiviert? Arbeitsstand sichern, dann löschen (siehe unten) |

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

## Wenn etwas klemmt

**„Python wurde nicht gefunden"** – Bei der Installation fehlte das Häkchen
„Add python.exe to PATH". Python erneut installieren, diesmal ankreuzen.

**Der Browser öffnet sich nicht** – Von Hand <http://127.0.0.1:8765> aufrufen.

**„Bitte Nutzerkennung eingeben"** – Oben rechts `ra-weber` eintragen.

**„Keine Akte gefunden oder keine Berechtigung"** – Im Probelauf gibt es nur die
beiden Testakten. Suchfeld leeren und **Suchen** drücken.

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

Für echte Mandantenakten fehlen:

- **Die Ordnerprüfung auf dem Kanzleilaufwerk.** Solange sie nicht gelaufen ist,
  beruht das Erkennen archivierter Akten auf einer Annahme.
  Am PC: `python -m jusperfect.ordnerpruefung "J:\Akten"` – verändert nichts.
- **Datenschutz-Folgenabschätzung, Datenschutzhinweise, Mandatsbedingungen.**
  Die fachliche Grundlage steht im Löschkonzept in `SICHERHEIT.md`.
- **Die Gewissheit, dass AWS nichts mitschreibt.** Das prüft das Programm seit
  Neuestem bei jedem Start selbst: Schreibt AWS die Modellaufrufe mit, startet
  es nicht. Lässt sich die Frage nicht beantworten, läuft es mit den erfundenen
  Akten weiter und startet mit echten nicht. Wo es steht: Knopf **Nachweis**,
  erste Zeile.

Bis dahin gilt: **erfundene Testakten, keine echten Mandantendaten.**

---

## Wo Sie was nachlesen

| Datei | Inhalt |
|---|---|
| `README.md` | Überblick, Betrieb, Aufbau |
| `AWS-EINRICHTEN.md` | AWS-Konto einrichten für den Test mit echtem Modell |
| `SICHERHEIT.md` | Sicherheitsmodell und Löschkonzept |
| `KONZEPT.md` | Warum es so gebaut ist |
| `infra/IAM.md` | AWS-Zugriffsrichtlinie: nur Claude, nur Europa |
