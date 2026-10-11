# AWS einrichten – Test mit erfundenen Akten

Diese Anleitung führt von einem AWS-Konto ohne alles bis zu jusperfect, das mit
dem **echten Sprachmodell** arbeitet – aber ausschließlich mit den beiliegenden
**erfundenen Testakten**.

> **Es gehen keine Mandantendaten hinaus.** Der Testbetrieb liest nur aus
> `testdaten/akten`. Zwei erfundene Akten liegen dort: ein Verkehrsunfall und
> eine Mietsache. Wann echte Akten zulässig sind, steht am Ende.

Rechnen Sie mit **einer Stunde**, davon die Hälfte Wartezeit auf AWS.

---

## Was Sie am Ende haben

Das Programm läuft auf Ihrem Rechner. Nur für die eigentliche Frage an das
Modell geht **ausgewählter Text** an AWS Frankfurt und kommt beantwortet zurück.
Dokumente, Dateinamen und die ganze Akte bleiben hier.

---

## Schritt 1: AWS-Konto

Falls noch keines besteht: <https://aws.amazon.com/de/> → *Konto erstellen*.
Kreditkarte nötig; abgerechnet wird nach Verbrauch.

**Melden Sie sich danach nicht mit dem Stammbenutzer zum Arbeiten an.** Dafür
legen wir in Schritt 3 einen eigenen Benutzer an.

---

## Schritt 2: Region auf Frankfurt stellen

Oben rechts in der AWS-Konsole steht die Region. Stellen Sie sie auf
**Europa (Frankfurt) eu-central-1**.

Das ist keine Kosmetik: jusperfect weist Aufrufe außerhalb europäischer Regionen
ab, und die Zugriffsrichtlinie verbietet sie zusätzlich.

---

## Schritt 3: Claude freischalten

Modelle sind in einem neuen Konto **nicht** freigeschaltet.

jusperfect benutzt **zwei** davon – ein starkes und ein schnelles:

| Modell | Wofür | Kennung in der Startdatei |
|---|---|---|
| **Claude Opus 4.6** | Fragen, Analyse, Entwürfe | `anthropic.claude-opus-4-6-v1` |
| **Claude Haiku 4.5** | Eingangsprüfung, Aktengedächtnis | `anthropic.claude-haiku-4-5-20251001-v1:0` |

> **Die Kennung lässt sich nicht aus dem Namen herleiten.** Das hat uns einen
> Lauf gekostet. So sehen die fünf aus, die das Konto der Kanzlei am 16.09.2026
> wirklich führt:
>
> | Modell | Kennung | Bauart |
> |---|---|---|
> | Opus 4.6 | `anthropic.claude-opus-4-6-v1` | „-v1", kein Datum |
> | Opus 4.5 | `anthropic.claude-opus-4-5-20251101-v1:0` | Datum und Fassung |
> | Sonnet 4.6 | `anthropic.claude-sonnet-4-6` | weder noch |
> | Sonnet 4.5 | `anthropic.claude-sonnet-4-5-20250929-v1:0` | Datum und Fassung |
> | Haiku 4.5 | `anthropic.claude-haiku-4-5-20251001-v1:0` | Datum und Fassung |
>
> Drei Bauarten bei fünf Modellen. Wer aus „Opus 4.6" die Kennung
> `anthropic.claude-opus-4-6` bildet, liegt falsch, und AWS antwortet mit einer
> Abweisung, die wie eine fehlende Freischaltung aussieht.
>
> **Deshalb: abfragen, nicht herleiten.** `MODELLE-ANZEIGEN.bat` fragt Ihr Konto
> selbst und probiert jedes Modell mit einem Wort an. Die Kennungen aus dieser
> Liste schreiben Sie Zeichen für Zeichen ab.

Opus 4.7, 4.8 und 5 sowie Sonnet 5 sind dem Konto der Kanzlei **nicht**
zugeteilt. Das ist kein Einrichtungsfehler und lässt sich in der Startdatei
nicht beheben. Prüfen Sie bei Gelegenheit nach; AWS teilt mit der Zeit mehr zu.

> **Diese Seite heisst in der AWS-Konsole immer wieder anders.** Mal
> „Model access", mal „Modellzugriff", mal steckt sie unter „Bedrock
> configurations", inzwischen führt der Weg über den **Modellkatalog**. Eine
> Klickfolge, die ich hier aufschreibe, ist in einem halben Jahr falsch.
> Deshalb steht unten, **woran Sie die richtige Stelle erkennen** – und danach
> der Weg, der von dieser Umbauerei unabhängig ist.

**In der Konsole:**

1. Oben rechts prüfen: **Europa (Frankfurt) eu-central-1**
2. Nach **Bedrock** suchen und öffnen
3. In der linken Leiste die Stelle suchen, an der die Modelle stehen – heute
   der **Modellkatalog** (*Model catalog*), früher *Model access*
4. Im Katalog **Anthropic** wählen und die beiden Modelle öffnen
5. Dort steht je Modell, ob Ihr Konto Zugriff hat. Fehlt er, gibt es an
   derselben Stelle einen Knopf, ihn anzufordern – je nach Fassung
   *Request access*, *Modify access* oder *Verfügbar machen*
6. Absenden und warten; das dauert meist Minuten

> **Bietet Ihnen die Konsole eine „neue Bedrock-Konsole" an?** Seit Kurzem
> wirbt AWS dort für eine zweite Konsole, die auf einen neueren Zugangsweg
> ausgelegt ist (*bedrock-mantle*). Die neuesten Modelle stehen dort; im alten
> Katalog fehlen sie unter Umständen. Gehen Sie ruhig hinüber und schalten Sie
> die Modelle dort frei – die Freischaltung gilt dem Konto, nicht der Konsole.
>
> **Ob jusperfect sie danach auch aufrufen kann, ist eine zweite Frage.** Das
> Programm spricht heute den herkömmlichen Weg an (`bedrock-runtime`). Ob ein
> neu freigeschaltetes Modell von dort erreichbar ist, entscheidet nicht die
> Konsole, sondern der Versuch – siehe gleich darunter. Ist es das nicht,
> sagen Sie Bescheid: Dann muss das Programm den neuen Weg lernen, und das ist
> eine Änderung im Programm, keine Einstellung.

**Und dann der Weg, der nicht veraltet:**

```
MODELLE-ANZEIGEN.bat
```

Der fragt Ihr Konto unmittelbar und **probiert die Modelle wirklich an** – je
ein Wort, Bruchteile eines Cents insgesamt. Er beantwortet damit die Frage, die
der Katalog *nicht* beantwortet.

> **Der Katalog beantwortet eine andere Frage als die gestellte.** „In
> Frankfurt vorhanden" heisst nicht „dieses Konto darf es". AWS teilt neuen
> Konten die starken Modelle nicht ohne Weiteres zu und antwortet dann mit
> `AccessDeniedException` – **derselben Meldung wie bei einer fehlenden
> Berechtigung**. Wir haben das in der Kanzlei dreimal für einen
> Einrichtungsfehler gehalten.

**Steht ein Modell gar nicht zur Verfügung**, liegt es nicht an Ihrer
Einrichtung. Nehmen Sie eines, das da ist – `anthropic.claude-sonnet-4-6` ist die
ausgewogene Wahl – und tragen Sie es in `START-AWS.bat` ein.

> **Die Kennung beginnt mit `anthropic.`** – das ist die Bedrock-Form. Ein
> blosses `claude-opus-4-6` ist die Kennung der Anthropic-Schnittstelle und wird
> abgewiesen. Den europäischen Vorsatz `eu.` setzt das Programm selbst.
>
> Das allein genügt aber nicht: Auch der Rest muss stimmen, und er folgt keinem
> Muster. Nehmen Sie die Kennung aus `MODELLE-ANZEIGEN.bat`, nicht aus dem
> Anzeigenamen im Katalog.

---

## Schritt 4: Benutzer mit eingeschränkten Rechten

Wir legen einen Benutzer an, der **nur Claude** aufrufen darf – sonst nichts.

**Zuerst die Richtlinie:**

1. Konsole → **IAM** → *Richtlinien* → **Richtlinie erstellen**
2. Reiter **JSON** wählen
3. Den Inhalt von `infra/iam-nur-claude.json` einfügen
4. Darin `AWS-KONTONUMMER` durch Ihre zwölfstellige Kontonummer ersetzen
   (**zweimal**; die Nummer steht oben rechts in der Konsole)
5. Name: `jusperfect-nur-claude` → speichern

**Dann den Benutzer:**

6. IAM → *Benutzer* → **Benutzer erstellen**, Name etwa `jusperfect-test`
7. **Keinen** Konsolenzugriff geben – der Benutzer arbeitet nur über das Programm
8. Berechtigungen → *Richtlinien direkt anfügen* → `jusperfect-nur-claude`
9. Anlegen

**Zuletzt die Schlüssel:**

10. Den Benutzer öffnen → Reiter **Sicherheitsanmeldeinformationen**
11. **Zugriffsschlüssel erstellen** → Verwendungszweck: *Lokaler Code*
12. Beide Werte notieren: **Access key ID** und **Secret access key**

> **Der geheime Schlüssel wird genau einmal angezeigt.** Danach nie wieder.
> Behandeln Sie ihn wie ein Kennwort: nicht per E-Mail, nicht in eine Datei im
> Programmordner, nicht in ein Chatfenster. Geht er verloren, löschen Sie ihn in
> IAM und erstellen einen neuen – das ist der normale Weg, kein Notfall.

Warum die Richtlinie mehr tut, als sie zu müssen scheint, steht in
[infra/IAM.md](infra/IAM.md).

---

## Schritt 5: Schlüssel auf dem Rechner hinterlegen

**`ZUGANG-EINTRAGEN.bat` doppelklicken.** Es fragt die beiden Werte aus
Schritt 4 ab und legt sie ab. Mehr ist nicht zu tun.

Was dabei auf dem Schirm passiert, Zeile für Zeile:

1. **`Access Key ID (beginnt mit AKIA…):`** – den Wert eintippen oder einfügen,
   Eingabetaste. Einfügen geht mit **Rechtsklick** ins Fenster; Strg+V kann die
   Eingabeaufforderung je nach Einstellung nicht.
2. **`Secret Access Key (Eingabe bleibt unsichtbar):`** – **Hier bleibt der
   Schirm leer.** Keine Punkte, keine Sternchen, gar nichts. Das ist Absicht:
   Was im schwarzen Fenster steht, liest der Nächste mit. Tippen oder einfügen
   Sie ruhig zu Ende und drücken Sie die Eingabetaste.
3. Fertig. Es nennt die Datei, in die es geschrieben hat, und die Kennung
   verkürzt – etwa `AKIA…7B2Q`, damit man zwei Schlüssel unterscheiden kann.

> **Steht schon ein Schlüssel da**, fragt es erst: *„Für „default" ist bereits
> ein Schlüssel hinterlegt: AKIA…7B2Q – Überschreiben? (j/n)"*. Nur ein
> kleines `j` überschreibt; alles andere bricht ab, ohne etwas zu ändern.

> **Die Form wird geprüft, aber nicht erzwungen.** Meldet es „ist 19 Zeichen
> lang, bei AWS sind es 20", haben Sie beim Kopieren ein Zeichen verloren. Das
> ist ein Hinweis, kein Abbruch – Sie dürfen eintragen, was Sie für richtig
> halten. Entschieden wird es in Schritt 7.

> **Die AWS-CLI brauchen Sie dafür nicht.** Hier stand früher der Weg über
> dieses Hilfsprogramm; er funktioniert weiter, ist aber ein
> Dreissig-Megabyte-Installationspaket für zwei Textdateien – und er verlangt
> Verwaltungsrechte, die auf einem Kanzleirechner nicht jeder hat.
> `ZUGANG-EINTRAGEN.bat` schreibt dieselben zwei Dateien, ohne beides.
>
> *(Setzt eine Arbeitsumgebung voraus. Ist `START-AWS.bat` noch nie gelaufen,
> sagt die Datei das und verweist darauf – dann zuerst starten, den
> fehlschlagenden Zugangstest abwarten, Fenster schließen, und wieder hierher.)*

Die Angaben landen in `%USERPROFILE%\.aws\credentials`, außerhalb des
Programmordners und getrennt für jedes Windows-Konto. jusperfect liest sie von
dort; es speichert selbst keine Zugangsdaten.

Geprüft wird das in Schritt 7 mit `ZUGANG-PRUEFEN.bat`.

<details>
<summary>Der alte Weg über die AWS-CLI, falls Sie sie ohnehin haben</summary>

1. <https://awscli.amazonaws.com/AWSCLIV2.msi> herunterladen und installieren
   (Verwaltungsrechte nötig)
2. Eingabeaufforderung öffnen (Windows-Taste, `cmd`, Eingabetaste)
3. Eintippen: `aws configure`
4. Vier Angaben:
   - **AWS Access Key ID** – aus Schritt 4
   - **AWS Secret Access Key** – aus Schritt 4
   - **Default region name** – `eu-central-1`
   - **Default output format** – leer lassen, Eingabetaste

Das Ergebnis ist dasselbe.

</details>

---

## Schritt 6: Kostenbremse setzen

**Vor dem ersten Aufruf**, nicht danach.

**In AWS** (fängt alles ab, auch Versehen):

1. Konsole → **Billing and Cost Management** → *Budgets* → **Budget erstellen**
2. *Monatliches Kostenbudget*, Betrag etwa **120 USD** – etwas über der
   Grenze, die jusperfect selbst zieht
3. Warnschwellen bei 50 % und 80 %, E-Mail-Adresse eintragen

**In jusperfect** (bremst das Programm selbst): `START-AWS.bat` setzt eine
Monatsgrenze von **100 EUR**. Ist sie erreicht, verweigert das Programm weitere
Modellaufrufe, statt weiterzulaufen. Ändern lässt sie sich mit
`JUSPERFECT_MONATSBUDGET_EUR`.

> Beide zusammen sind Absicht: AWS bremst zu spät (es warnt, nachdem Kosten
> entstanden sind), jusperfect bremst zu eng (es kennt nur die eigenen Aufrufe).

---

## Schritt 7: Zugang prüfen

Im Programmordner **`ZUGANG-PRUEFEN.bat`** doppelklicken. Das Fenster bleibt bis
zum Tastendruck stehen, und derselbe Befund liegt danach als `zugangstest.txt`
im Programmordner – die Datei dürfen Sie weitergeben, es steht kein Aktentext
darin.

Der Test geht die Schritte in der Reihenfolge durch, in der sie scheitern
können, und sagt bei jedem, was zu tun ist. Er schickt **eine** sehr kurze Frage
an das Modell und **keinen Aktentext**; das kostet einen Bruchteil eines Cents.

Am Ende soll stehen: *„Der Zugang steht."*

**Meldet er `ValidationException`,** braucht Ihr Konto das Inferenzprofil. Dann:

Tragen Sie in `START-AWS.bat` die Bedrock-Form der Kennung ein – sie beginnt
mit `anthropic.`, den europäischen Vorsatz `eu.` setzt das Programm selbst:

```
set JUSPERFECT_MODELL_ID=anthropic.claude-opus-4-6-v1
```

Ein blosses `claude-opus-4-6` ohne `anthropic.` ist die Kennung der
Anthropic-Schnittstelle und wird von Bedrock abgewiesen. Und ein
`anthropic.claude-opus-4-6` ohne das `-v1` ebenfalls – die genaue Schreibweise
steht in `MODELLE-ANZEIGEN.bat`.

*(Existiert der Ordner `.venv` noch nicht, führen Sie einmal `START-AWS.bat`
aus – es legt ihn an und ruft den Test von selbst auf.)*

---

## Schritt 8: Starten

**`START-AWS.bat`** doppelklicken. Es prüft den Zugang selbst und startet dann.

Im Browser als Nutzerkennung **`ra-weber`** eintragen.

Der Unterschied zu `START-DEMO.bat`: Dort antwortet ein Muster ohne KI, hier das
echte Modell. Der Ablauf ist derselbe – die Antwortqualität nicht.

---

## Schritt 9 (vor der ersten echten Akte): Das Schutzgeländer

Mit den erfundenen Testakten läuft jusperfect ohne. Sobald Sie den Aktenadapter
auf einen echten Ordner umstellen, **startet es ohne Guardrail nicht mehr** –
das ist so gewollt.

### Was ein Guardrail hier tut, und was nicht

Ein Guardrail ist ein Filter, den AWS vor und hinter das Modell schaltet.

**Er sieht bei jusperfect die Frage und die Antwort – nicht Ihre Dokumente.**
Im Programmcode steht dafür `guardContent` genau um die Aufgabe (siehe
`jusperfect/providers/bedrock.py`); das Aktenmaterial liegt daneben und geht
nicht durch den Filter. Das hat zwei Gründe: AWS rechnet je 1.000 Zeichen ab,
und eine ganze Akte durch den Filter zu schicken kostet mehr, als es bringt.

Ein Guardrail ist deshalb **Ergänzung, nicht Grundlage**. Die eigentliche
Sicherung ist die Belegpflicht, der geprüfte Ausgang und die Zugriffsrichtlinie.

### Die Filter: für eine Kanzlei gilt das Gegenteil des Üblichen

**Das ist der wichtigste Absatz dieses Schritts.** Die Voreinstellungen von AWS
sind für Anwendungen gedacht, in denen bestimmte Inhalte nichts zu suchen haben.
In einer Kanzlei sind genau diese Inhalte der Gegenstand der Arbeit.

| Filter | In einer Kanzlei |
|---|---|
| **Sensitive information / PII** | **AUS.** Eine Antwort, in der Mandantin, Gegner und Zeuge geschwärzt sind, ist wertlos. Der Guardrail sieht ohnehin nur Frage und Antwort – und die sollen die Namen tragen. |
| **Violence** (Gewalt) | **AUS oder ganz niedrig.** Eine Körperverletzungssache, eine Gewaltschutzsache, ein Strafmandat: Der Sachverhalt *ist* Gewalt. |
| **Sexual** | **AUS.** Sexualstrafrecht und Familienrecht kämen sonst nicht durch. |
| **Hate / Insults** | **AUS oder ganz niedrig.** Eine Beleidigungsklage muss die Beleidigung wiedergeben dürfen. |
| **Misconduct** | **AUS oder ganz niedrig.** Der Vorwurf ist der Fall. |
| **Prompt attacks** | **AN.** Das ist der einzige Filter, der hier wirklich passt: Er erkennt Versuche, dem Modell über den Text der Frage fremde Anweisungen unterzuschieben. |

Ein zu scharfer Filter fällt nicht dadurch auf, dass er etwas Falsches tut. Er
fällt dadurch auf, dass eine ganz gewöhnliche Frage zu einer ganz gewöhnlichen
Akte mit einer Sperrmeldung endet – und niemand weiß, warum.

### Die Schritte

Die Bedrock-Konsole wird von AWS regelmässig umgebaut; Beschriftungen und
Reihenfolge können abweichen. Deshalb steht hier, **woran Sie die Stelle
erkennen**, nicht ein starrer Klickweg.

1. AWS-Konsole, oben rechts **Frankfurt / eu-central-1** prüfen.
2. Dienst **Bedrock** öffnen. In der linken Leiste den Eintrag **Guardrails**
   suchen – je nach Fassung steht er unmittelbar dort oder unter einer
   Überschrift wie *Safeguards*, *Konfigurationen* oder *Bedrock
   configurations*. Erkennbar ist er daran, dass die Seite eine Liste mit einem
   Knopf **Create guardrail** zeigt.
3. **Create guardrail**.
4. **Name:** `jusperfect-kanzlei`. Beschreibung frei.
5. **Blocked messaging / Nachricht bei Sperrung:** Hier verlangt AWS zwei Texte
   – einen für eine gesperrte Eingabe, einen für eine gesperrte Antwort. Sie
   erscheinen später im Programm. Vorschlag für beide:

       Das Schutzgeländer der Kanzlei hat diese Anfrage angehalten.

6. **Die Filterseiten durchgehen** und dabei die Tabelle oben befolgen. Was Sie
   nicht brauchen, lassen Sie aus; AWS erlaubt es, Seiten zu überspringen.
   Mindestens **eine** Einstellung braucht ein Guardrail – nehmen Sie dafür
   *Prompt attacks*.
7. **Review and create.**
8. Auf der Seite des fertigen Guardrails steht die **Guardrail-ID** – eine
   kurze Folge aus Buchstaben und Ziffern, nicht der Name. Kopieren.
9. Eintragen mit **JURNODES-ZUGANG.bat**. Dort wird sie beim Punkt
   *Kennung des Schutzgeländers* eingefügt.

   Sie kommt **nicht** mehr in eine `.bat` des Programmordners. Am 25.09.2026
   stand sie in `START-JURNODES.bat`, die Kanzlei packte eine neue Fassung
   aus, und die Kennung war weg – mitten in der Suche nach etwas ganz
   anderem. Was eine Einrichtung überleben soll, gehört ins Windows-Konto,
   nicht in den Ordner, den wir austauschen.

Eine Version müssen Sie nicht veröffentlichen; jusperfect benutzt den
Arbeitsstand (`DRAFT`), solange Sie nichts anderes unter
`JUSPERFECT_GUARDRAIL_VERSION` eintragen.

### Ein vorhandenes Schutzgeländer nachschlagen

Wer es schon angelegt hat und nur die Kennung braucht:

1. **console.aws.amazon.com** öffnen und anmelden.
2. Oben rechts prüfen: **Frankfurt** bzw. **eu-central-1**. In einer anderen
   Region ist die Liste leer, und das sieht aus, als wäre nichts da.
3. Oben in der Suchleiste **Bedrock** eintippen und den Dienst öffnen.
4. Linke Leiste, **Guardrails** – je nach Fassung direkt sichtbar oder unter
   *Safeguards* bzw. *Bedrock configurations*.
5. In der Liste steht `jusperfect-kanzlei` (oder der Name, den Sie vergeben
   haben). **Draufklicken.**
6. Oben auf der Seite steht **Guardrail ID**: eine kurze Folge aus Buchstaben
   und Ziffern, etwa `gr7k2m9qx4vp`. **Das ist der Wert** – nicht der Name,
   nicht die ARN, nicht die Version.
7. Daneben ist ein Kopiersymbol. Damit kopieren und in `JURNODES-ZUGANG.bat`
   einfügen.

Steht die Liste leer da, wurde in dieser Region noch keines angelegt – dann
gilt die Anleitung oben ab Punkt 3.

### Danach prüfen

**`ZUGANG-PRUEFEN.bat`** und dann jusperfect starten und den **Selbsttest**
öffnen. Der Punkt **Schutzgeländer** muss von `!` auf `✓` wechseln.

Stellen Sie danach **eine Frage an eine Testakte**. Kommt eine Antwort, greift
das Geländer und stört nicht. Kommt stattdessen *„Die Guardrail hat die Anfrage
oder Antwort blockiert"*, ist ein Filter zu scharf – zurück in die Konsole und
nach der Tabelle oben abschwächen.

> **Wenn sofort `AccessDeniedException` kommt, sobald die ID eingetragen ist:**
> Dann verlangt Ihr Konto für den Aufruf mit Guardrail ein eigenes Recht,
> `bedrock:ApplyGuardrail`. Vorher lief derselbe Aufruf – daran erkennen Sie es.
> Das Recht gehört dann neben `bedrock:InvokeModel` in die Zugriffsrichtlinie.
> `infra/iam-nur-claude.json` führt es bisher **nicht**; die Datei ist geschützt
> und wird nur auf ausdrückliche Anweisung geändert. Prüfen liess sich das nie,
> weil es dafür ein angelegtes Guardrail braucht.

---

## Schritt 10 (der letzte): Der echte Aktenbestand über das Laufwerk

jur|nodes lässt sich auf zwei Wegen anbinden. Über die REST-Schnittstelle –
dafür fehlt uns die Dokumentation des Herstellers – oder über das
**eingebundene Laufwerk**, denn jur|nodes ist ein WebDAV-Server. Die Kanzlei hat
den Laufwerksweg gewählt; er ist fertig und braucht vom Hersteller nichts.

Damit hängt alles an einer Frage: **Ist der Ordnerbaum so gebaut, wie jusperfect
ihn erwartet?**

```
<Wurzel>\<Anwalt>\<Jahr>\<Aktenzeichen Bezeichnung>\<Dokumente>
```

Beispiel: `J:\Akten\Dortschy\2026\X-001-2026 Testmann ./. Musterhaft\`

Stimmt das nicht, findet jusperfect **null Akten** – und eine leere Liste sagt
nicht, woran es liegt.

### 10.1 Die Laufwerksprobe

**`ORDNER-PRUEFEN.bat` doppelklicken.** Sie sieht nur nach; geändert wird
nichts. Nur für das Schreibrecht legt sie eine einzelne Probedatei an und
entfernt sie sofort wieder.

Sie beantwortet fünf Fragen auf einmal:

| | |
|---|---|
| **Aufbau** | Stimmen die Ebenen Anwalt / Jahr / Akte? Wenn nicht, sagt sie, was sie stattdessen gefunden hat. |
| **Akten** | Wie viele werden erkannt, wie viele gelten als archiviert? |
| **Archiv-Kennung** | Wird „archiviert" im Bestand einheitlich geschrieben? An ihr hängt die Aufbewahrung. |
| **Dokumente** | Welche Dateitypen kommen vor – und wie viele gehen **nicht** durch (`.msg`, `.eml`, `.zip`)? Dazu die Textmenge je Akte, aus der sich die Kosten ergeben. |
| **Schreibrecht** | Darf jusperfect einen freigegebenen Vermerk zurückschreiben? Sonst fällt das erst beim ersten Versuch auf. |

Der Befund liegt zusätzlich in `ordnerpruefung.txt`. **Bevor Sie die Datei
weitergeben:** Darin stehen Aktenzeichen und Bezeichnungen als Beispiele.

> **Sagt sie „Der Aufbau passt nicht"**, hören Sie hier auf und schicken die
> Ausgabe an die Entwicklung. Der Adapter lässt sich an einen anderen Aufbau
> anpassen – aber nicht raten. Alles Weitere wäre vergeblich.

### 10.2 Der Starter für den Echtbetrieb

**`START-KANZLEI.bat`** ist die Datei für die echten Akten; `START-AWS.bat`
bleibt für die Testakten. Öffnen Sie sie einmal mit dem Editor (Rechtsklick →
Öffnen mit) und tragen Sie **zwei** Dinge ein:

```
set JUSPERFECT_JURNODES_WEBDAV=J:\Akten
set JUSPERFECT_GUARDRAIL_ID=gr7k2m9qx4vp
```

Mehr ist nicht einzutragen. Fehlt eines von beiden, sagt die Datei das in
ganzen Sätzen und startet nicht – statt einer Python-Meldung, die richtig und
unbrauchbar wäre.

**Was sie sonst noch tut, und warum:**

- **Das Aktengedächtnis liegt in der Akte**, als Datei im Aktenordner. Beim
  Laufwerksweg ist das die saubere Wahl: kein zweiter Aufbewahrungsort, und
  Sicherung wie Löschung der Akte erfassen es mit. Ein Gedächtnis auf dem
  Rechner (`lokal`) ist mit echten Akten **nicht zulässig** – das Programm weist
  es ab, und das ist gewollt.
- **Dieselben Modelle wie im Testbetrieb.** Sonst misst der Prüfbogen etwas
  anderes, als Sie benutzen.
- **Vor dem Start eine ausdrückliche Warnung** und ein Tastendruck: Ab dort geht
  echter Aktentext an AWS Frankfurt.

### 10.3 Was vorher fertig sein muss

1. **Das Schutzgeländer** (Schritt 9) – ohne es startet nichts.
2. **Der Modell-Testlauf** im Selbsttest: Lassen Ihre Filter die Sprache einer
   Akte durch?
3. **Die Laufwerksprobe** (10.1) ohne „✗".
4. **DSFA, Datenschutzhinweise, Mandatsbedingungen** – die Grundlage steht im
   Löschkonzept in `SICHERHEIT.md`.

Die ersten drei sagt Ihnen das Programm. Das vierte nicht.

---

## Schritt 11 (wenn das Aktengedächtnis nach AWS soll): Der Ablageort in S3

Dieser Schritt ist **nicht nötig, um zu arbeiten.** Ohne ihn liest jusperfect
jede Akte bei jeder Sitzung neu ein. Er spart Geld und Zeit, und er ist eine
Entscheidung, die Sie bewusst treffen sollten – deshalb steht er am Ende.

### Was er bringt

Gemessen am 23.09.2026 an einer echten Akte: Die erste Frage kostet 23 Cent,
jede weitere in derselben Sitzung 4 Cent. Der günstige Preis hält aber nur
Minuten – am nächsten Tag beginnt es wieder bei 23 Cent, weil die Akte neu
gelesen wird.

Mit dem Aktengedächtnis kostet die Wiederaufnahme rund **5 Cent**, und der
Lebenssachverhalt ist noch da: Wer am Dienstag weiterarbeitet, fängt nicht von
vorn an. Bei einer Akte, an der über Wochen gearbeitet wird, ist das der
Unterschied zwischen ein paar Euro und ein paar Cent.

### Was er bedeutet – der Absatz, der Ihre Entscheidung ist

**Damit legt jusperfect erstmals dauerhaft Akteninhalt außerhalb von jur|nodes
ab.** Im Gedächtnis stehen der Lebenssachverhalt, der Zeitstrahl, frühere Fragen
mit ihren Antworten und die ausgelesenen Dokumenttexte. Das ist Mandatsgut, kein
Protokoll.

Es liegt im **eigenen AWS-Konto der Kanzlei**, in Frankfurt, verschlüsselt mit
einem Schlüssel, der der Kanzlei gehört – nicht bei einem weiteren Anbieter.
Derselbe Auftragsverarbeiter wie schon für die Verarbeitung, also **kein neuer
AV-Vertrag**. Aber: DSFA, Verarbeitungsverzeichnis, Datenschutzhinweise und
Speicherdauer müssen es nennen. `SICHERHEIT.md` und `DSFA-ANGABEN.md` sind
darauf vorbereitet; ausformuliert ist es nicht.

**Warum nicht in der Akte selbst?** Das war der erste Weg, und er wurde am
25.09.2026 verworfen: jur|nodes ersetzt eine vorhandene Datei nicht, sondern
weist sie ab. Ein Zeitstempel je Fassung wurde versucht – dann sammelten sich
Fassungen neben den Schriftsätzen in der Mandatsakte. Das Recht „Datei löschen"
hätte für **jede** Datei des Bestands gegolten; dafür ist der Preis zu hoch.

### A. Den Schlüssel anlegen (KMS)

Zuerst der Schlüssel, denn der Ablageort braucht ihn schon beim Anlegen.

1. AWS-Konsole, oben rechts **Frankfurt / eu-central-1** prüfen. Der Schlüssel
   muss in **derselben** Region liegen wie der Ablageort.
2. Oben suchen: **KMS** (Key Management Service), Dienst öffnen.
3. Linke Leiste: **Customer managed keys** → **Create key**.
4. **Key type: Symmetric.** **Key usage: Encrypt and decrypt.** Beides ist die
   Voreinstellung; weiterklicken.
5. **Alias:** `jusperfect-kanzlei`. Beschreibung frei.
6. Die beiden Seiten zu den Benutzern (*Key administrators*, *Key users*):
   Tragen Sie dort Ihren AWS-Benutzer ein, damit Sie den Schlüssel später
   verwalten können. Den eingeschränkten Benutzer aus Schritt 4 brauchen Sie
   hier **nicht** einzutragen – er bekommt sein Recht über die
   Zugriffsrichtlinie (Abschnitt C).
7. **Finish.**
8. Auf der Seite des fertigen Schlüssels steht die **Key ID** – eine lange
   Folge mit Bindestrichen, etwa `1a2b3c4d-5e6f-7890-abcd-ef1234567890`.
   **Diese kopieren**, nicht den Alias und nicht den ARN.

### B. Den Ablageort anlegen (S3)

1. Oben suchen: **S3**, Dienst öffnen. **Create bucket.**
2. **AWS Region:** Europe (Frankfurt) eu-central-1. **Ein Bucket lässt sich
   später nicht verschieben** – liegt er falsch, muss er neu angelegt werden.
3. **Bucket name:** Der Name muss weltweit einmalig sein, also nehmen Sie etwas
   Eigenes hinein, zum Beispiel
   `dortschy-thunert-jusperfect-gedaechtnis`. Kleinbuchstaben, Ziffern und
   Bindestriche, keine Punkte.
4. **Block all public access:** eingeschaltet lassen. Das ist die
   Voreinstellung.
5. **Bucket Versioning: Disable** (Voreinstellung). Das Gedächtnis wird bei
   jeder Sitzung überschrieben; mit Versionierung sammelten sich Kopien, die
   niemand liest und die jede Löschung unvollständig machen.
6. **Default encryption:** **Server-side encryption with AWS Key Management
   Service keys (SSE-KMS)** wählen, dann **Choose from your AWS KMS keys** und
   den Schlüssel `jusperfect-kanzlei` aus Abschnitt A nehmen.

   Das Programm verlangt die Verschlüsselung bei jedem Ablegen ohnehin selbst.
   Die Voreinstellung am Bucket ist der zweite Riegel: Sie gilt auch für alles,
   was auf anderem Weg hineinkäme.
7. **Create bucket.** Den **Namen** notieren.

### C. Die vier Rechte für die Zugriffsrichtlinie

Der eingeschränkte Benutzer aus Schritt 4 darf heute Claude aufrufen – nicht in
S3 schreiben. Ohne diese vier Rechte weist AWS das Ablegen ab.

| Recht | Wofür | Auf welche Ressource |
|---|---|---|
| `s3:PutObject` | das Gedächtnis ablegen | `arn:aws:s3:::IHR-BUCKETNAME/*` |
| `s3:GetObject` | es wieder lesen | `arn:aws:s3:::IHR-BUCKETNAME/*` |
| `s3:DeleteObject` | es löschen, wenn eine Akte abgeschlossen wird | `arn:aws:s3:::IHR-BUCKETNAME/*` |
| `s3:ListBucket` | die Übersicht „Arbeitsbereiche" | `arn:aws:s3:::IHR-BUCKETNAME` |
| `kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey` | verschlüsseln und entschlüsseln | der ARN des Schlüssels aus A |

**Zweimal hinsehen:** Die ersten vier Zeilen stehen auf **zwei verschiedenen**
Ressourcen – `ListBucket` auf den Bucket selbst, die anderen auf dessen Inhalt
mit `/*` dahinter. Wer überall dasselbe einträgt, bekommt eine Abweisung, die
nach einem Programmfehler aussieht.

> **`infra/iam-nur-claude.json` im Programmordner ist eine Vorlage und wird
> nicht von uns geändert.** Sie ist eine Sicherheitsgrenze, und sie wird nur auf
> ausdrückliche Anweisung angefasst. Wirksam ist ohnehin die Richtlinie in Ihrem
> AWS-Konto: Dort tragen Sie die Rechte ein (IAM → Benutzer → Berechtigungen).
> Wenn Sie wollen, dass die Vorlage im Ordner es künftig auch enthält, sagen Sie
> es – dann wird sie ergänzt und im Commit als solche gekennzeichnet.

### D. Eintragen und einmal prüfen

1. `START-JURNODES.bat` mit Rechtsklick → **Bearbeiten** öffnen.
2. Den Abschnitt **„So wird daraus aws"** suchen. Bei den drei Zeilen darunter
   das `REM` am Anfang wegnehmen und die zwei Werte eintragen:

       set JUSPERFECT_GEDAECHTNIS=aws
       set JUSPERFECT_GEDAECHTNIS_BUCKET=dortschy-thunert-jusperfect-gedaechtnis
       set JUSPERFECT_KMS_SCHLUESSEL_ID=1a2b3c4d-5e6f-7890-abcd-ef1234567890

3. Speichern, Editor schließen.
4. **`GEDAECHTNIS-AWS-PRUEFEN.bat`** doppelklicken – **einmal, vor der ersten
   echten Akte.**

   Die Probe legt ein Gedächtnis zu einer **erfundenen** Akte ab, liest es
   zurück, vergleicht es Zeichen für Zeichen und entfernt es wieder. Kein
   Akteninhalt, kein Mandantenname, kein Modellaufruf. Geht etwas nicht, sagt
   sie, was zu tun ist – fehlender Bucket, falsche Region, abgewiesener
   Schlüssel, fehlendes Recht.

   **Warum eine eigene Probe?** Der Selbsttest im Startbild sagt nur, dass ein
   Bucket *hinterlegt* ist. Ob er das Ablegen *annimmt*, sagt nur ein echter
   Versuch. Ohne ihn fiele das Fehlen erst auf, wenn eine Akte geschlossen wird
   und das Gedächtnis sich nicht sichern lässt – also dann, wenn die Arbeit
   getan ist und verloren wäre.

5. Erst wenn die Probe grün ist, arbeiten Sie mit einer echten Akte.

### Was es kostet

Ein Aktengedächtnis ist gepackt wenige Kilobyte groß. Hundert Akten sind
weniger als ein Megabyte. S3 rechnet nach Speicherplatz und Anfragen ab;
realistisch sind **Cent-Beträge im Monat**. Der Schlüssel kostet rund einen
Dollar im Monat, unabhängig von der Nutzung.

Dagegen stehen die 23 Cent, die jede Akte an jedem Tag kostet, an dem ohne
Gedächtnis gearbeitet wird.

### Was Sie danach aufschreiben

In `DSFA-ANGABEN.md` gehören: der Bucketname, die Region, die Key ID, das Datum
der Einrichtung und die Speicherdauer. Ein Wert, den man beim Einrichten sieht
und nicht aufschreibt, ist später nur noch zu erraten – die Datei gibt es aus
genau diesem Grund.

---

## Die Texterkennung für gescannte Blätter

Eingeschaltet am 02.10.2026. Sie liest Rückscheine, Einschreiben und
Vollmachten — alles, was als Bild in der Akte liegt und keinen Text enthält.

**Es braucht genau ein Recht und keinen Ablageort.** Ein PDF wird auf dem
Rechner der Kanzlei Seite für Seite zu einem Bild gemacht; jedes Bild geht für
sich unmittelbar an Textract. Dadurch entfällt der Bucket, den Textract sonst
für PDFs verlangt — und mit ihm ein weiterer Ort, an dem Akteninhalt läge.

| | |
|---|---|
| Recht | `textract:DetectDocumentText` |
| Steht in | `infra/iam-nur-claude.json`, Abschnitt `TexterkennungFuerScans` |
| Eingeschaltet durch | `JUSPERFECT_OCR=textract` in `START-JURNODES.bat` |
| Ablageort | **keiner** |
| Auftragsverarbeiter | derselbe wie für die Texte (AWS Frankfurt), kein neuer Vertrag |
| Kosten | rund 1,50 € je 1000 Seiten — für eine Akte Bruchteile eines Cents |

### Prüfen, bevor eine Akte offen ist

**`TEXTERKENNUNG-PRUEFEN.bat`** doppelklicken. Die Probe baut sich ein eigenes
Blatt mit einem Wort darauf, schickt es an AWS und sieht nach, ob das Wort
zurückkommt. Aus der Kanzlei geht dabei nichts hinaus.

Warum es sie gibt: Der Selbsttest sagt, dass die Texterkennung eingeschaltet
ist. Ob die Zugriffsrichtlinie das Recht dazu trägt, sagt er nicht — das sagt
nur ein echter Versuch. Ohne die Probe fiele das Fehlen erst auf, wenn eine
Akte offen ist; dann bleiben die gescannten Blätter ungelesen, und das sieht
aus wie ein Mangel der Erkennung statt einer fehlenden Berechtigung.

Die Probe kostet rund 0,15 Cent und ruft kein Modell auf.

**Sie hat sich am ersten Tag bezahlt gemacht.** Der erste Lauf in der Kanzlei
am 02.10.2026 meldete: *„AWS hat geantwortet, aber das Probewort kam nicht
zurück."* Die Berechtigung stand also — gelesen wurde trotzdem nichts. Grund
war ein Fehler im Programm: Es schickte die Seiten als PDF, und Textract nimmt
über dieses Feld nur PNG und JPEG an (so steht es in der API-Beschreibung, die
mit `boto3` ausgeliefert wird). Der Aufruf lief **ohne Fehlermeldung** durch
und lieferte nichts.

Ohne die Probe wäre das in einer echten Akte als „kein Text gefunden"
durchgegangen — und das sieht aus wie ein schlechter Scan, nicht wie ein
Programmfehler. Seitdem werden die Seiten örtlich zu Bildern gemacht.

**Der zweite Lauf fand einen zweiten Fehler, diesmal in der Probe.** Sie meldete
*„1 Seite mit zusammen 23 Zeichen"*: Das Probewort war breiter als die Seite und
lief rechts heraus. Gelesen wurden genau die 23 Zeichen, die noch aufs Blatt
passten. Berechtigung, Umwandlung und Erkennung arbeiteten dabei alle richtig.
Das Wort ist seitdem kürzer, und zwei Prüfungen messen den Rand am gerenderten
Bild.

### Wenn das Recht fehlt

Der Lauf hält nicht an. Die übrigen Dokumente der Akte werden gelesen wie
bisher; beim ersten Scan sagt das Programm in einem Satz, welches Recht fehlt
und in welcher Datei es steht. Abhilfe: IAM → *Richtlinien* →
`jusperfect-nur-claude` → **Bearbeiten** → **JSON**, und den Abschnitt
`TexterkennungFuerScans` aus `infra/iam-nur-claude.json` ergänzen.

**Der Wortlaut von AWS wird nicht durchgereicht.** In einer Abweisung steht
mitunter ein Stück der Anfrage — und das ist hier ein gescanntes Blatt aus
einer Mandatsakte.

---

## Ein zweiter Rechner: eigener Benutzer, eigene Schlüssel

Wer jusperfect auf einem zweiten Rechner benutzt, braucht dort Zugangsdaten.
**Technisch könnten Sie denselben Schlüssel nehmen** – ein AWS-Zugriffsschlüssel
hängt am Benutzer, nicht am Gerät. Er funktioniert auf jedem Rechner.

**Tun Sie es trotzdem nicht.** Drei Gründe, und der erste allein genügt:

1. **Ein Benutzer hat höchstens zwei Zugriffsschlüssel.** Zwei Rechner an einem
   Benutzer belegen beide Plätze. Dann ist kein Platz mehr, um einen Schlüssel
   zu erneuern, ohne vorher den alten zu löschen – und in dem Moment steht der
   andere Rechner still.
2. **Zurückziehen wird sauber.** Geht ein Rechner verloren oder wird er
   ausgetauscht, löschen Sie genau dessen Schlüssel. Der andere Rechner arbeitet
   weiter, ohne dass jemand etwas neu eintragen muss.
3. **AWS führt Buch, wer aufruft.** Im Aufrufprotokoll von AWS (CloudTrail)
   steht der Benutzername. Mit einem Benutzer je Rechner lässt sich später
   sagen, von wo ein Aufruf kam; mit einem gemeinsamen Benutzer nicht.

### So legen Sie ihn an

Sie brauchen dafür **keine** neue Richtlinie. Die aus Schritt 4
(`jusperfect-nur-claude`) gilt für beliebig viele Benutzer und ist bereits da.

1. In der Konsole oben rechts prüfen, dass **Frankfurt (eu-central-1)** steht.
2. **IAM** → *Benutzer* → **Benutzer erstellen**.
3. Name: einer, an dem Sie den Rechner erkennen. Zum Beispiel
   `jusperfect-kanzlei-pc` und `jusperfect-notebook`. Nicht `jusperfect-test-2`
   – in einem halben Jahr wissen Sie nicht mehr, welcher das war.
4. **Keinen Konsolenzugriff** geben. Das Häkchen bei *AWS Management
   Console-Zugriff bereitstellen* bleibt leer. Der Benutzer arbeitet nur über
   das Programm; ein Kennwort für die Konsole wäre eine Tür, die niemand
   braucht.
5. Berechtigungen → **Richtlinien direkt anfügen** → `jusperfect-nur-claude`
   ankreuzen. *(Steht sie nicht in der Liste, ist sie noch nicht angelegt –
   dann zuerst Schritt 4, erster Teil.)*
6. **Benutzer erstellen**.
7. Den neuen Benutzer öffnen → Reiter **Sicherheitsanmeldeinformationen** →
   **Zugriffsschlüssel erstellen** → Verwendungszweck **Lokaler Code** →
   die Warnung bestätigen → **Zugriffsschlüssel erstellen**.
8. Jetzt stehen **Access key ID** und **Secret access key** auf dem Schirm.

> **Der geheime Schlüssel wird genau einmal angezeigt.** Lassen Sie das Fenster
> offen, bis Sie ihn auf dem anderen Rechner eingetragen haben. Schicken Sie ihn
> nicht per E-Mail, nicht in ein Chatfenster, nicht in eine Datei im
> Programmordner. Er ist wie ein Kennwort.
>
> Haben Sie ihn doch verloren: kein Notfall. In IAM den Schlüssel löschen und
> einen neuen erstellen. Das ist der vorgesehene Weg.

### Auf dem zweiten Rechner

9. Dort `ZUGANG-EINTRAGEN.bat` doppelklicken und die beiden Werte eingeben. Die
   AWS-CLI wird dafür nicht gebraucht.
10. `ZUGANG-PRUEFEN.bat` doppelklicken. Am Ende muss stehen: *„Der Zugang
    steht."* Das Ergebnis liegt zusätzlich in `zugangstest.txt`.
11. `MODELLE-ANZEIGEN.bat` doppelklicken. Es sagt, welche Modelle dieses Konto
    aufrufen darf – dieselben wie auf dem ersten Rechner, denn die Zuteilung
    hängt am Konto, nicht am Benutzer.

### Wenn der zweite Rechner abgewiesen wird

Die Meldung sagt, woran es liegt. Drei Fälle, die leicht zu verwechseln sind:

| Meldung | Was sie heisst |
|---|---|
| `InvalidClientTokenId` – *Die Access Key ID kennt AWS nicht* | Tippfehler, oder der Schlüssel wurde in IAM gelöscht |
| `SignatureDoesNotMatch` | Der geheime Schlüssel stimmt nicht – **oder die Uhr des Rechners geht falsch.** Windows-Einstellungen → Zeit → *Jetzt synchronisieren* |
| `AccessDeniedException` … *is not authorized* | Die Richtlinie `jusperfect-nur-claude` hängt nicht am Benutzer (Schritt 5 oben) |

### Wenn ein Rechner ausscheidet

IAM → *Benutzer* → den Benutzer öffnen → **Sicherheitsanmeldeinformationen** →
beim Schlüssel **Deaktivieren** wählen. Erst wenn ein paar Tage nichts fehlt,
**Löschen**. Deaktivieren ist umkehrbar, Löschen nicht.

---

## Ein neues Windows-Konto auf demselben Rechner

Etwas anderes als ein zweiter Rechner, und die Verwechslung liegt nahe. Hier
bleibt die Maschine dieselbe, es wechselt nur, wer angemeldet ist.

### Zuerst: das Konto anlegen, ohne eine E-Mail-Adresse zu vergeben

Windows drängt an dieser Stelle zu einem Microsoft-Konto und fragt nach einer
E-Mail-Adresse. Für einen Arbeitsplatz in der Kanzlei braucht es das **nicht**.
Ein **lokales Konto** genügt; es bleibt auf diesem Rechner und meldet sich
nirgends an.

Der Weg dorthin ist versteckt, aber er ist da:

1. **Einstellungen** öffnen (Windows-Taste + `i`).
2. **Konten** → **Andere Benutzer** → bei *Anderen Benutzer hinzufügen* auf
   **Konto hinzufügen**.
3. Es fragt: *„Wie wird sich diese Person anmelden?"* und will eine E-Mail-
   Adresse. **Nicht ausfüllen.** Stattdessen unten auf den kleinen Verweis
   klicken: **„Ich habe die Anmeldeinformationen für diese Person nicht."**
4. Im nächsten Bild wieder unten: **„Benutzer ohne Microsoft-Konto
   hinzufügen."**
5. Jetzt erst kommt die Maske, die man von früher kennt: Benutzername,
   Kennwort, Kennwort wiederholen. Windows 11 verlangt zusätzlich **drei
   Sicherheitsfragen** – sie ersetzen die E-Mail-Adresse beim Zurücksetzen des
   Kennworts. Die Antworten gehören ins Kennwortverzeichnis der Kanzlei, nicht
   auf einen Zettel am Bildschirm.
6. **Fertig.** Das Konto steht in der Liste.

> **Wenn die Verweise in Schritt 3 oder 4 fehlen** – das kommt bei manchen
> Windows-Fassungen vor –, geht es auch über die Eingabeaufforderung. Windows-
> Taste, `cmd` tippen, **Rechtsklick auf „Eingabeaufforderung" → Als
> Administrator ausführen**. Dann:
>
> ```
> net user Kanzlei2 /add
> ```
>
> Windows fragt danach zweimal nach dem Kennwort. Der Name darf keine Leer-
> zeichen enthalten. Das Konto ist ein Standardkonto – genau richtig.

### Standardkonto oder Administrator?

**Standardkonto.** Für die tägliche Arbeit mit jusperfect reicht es vollständig,
und zwar ohne jede Einschränkung: Das Programm läuft im eigenen Benutzerordner,
schreibt nur dorthin und braucht nichts, was Windows einem Standardkonto
verwehrt.

Soll es doch Administrator werden: **Einstellungen → Konten → Andere Benutzer →
das Konto anklicken → Kontotyp ändern → Administrator.**

> **Zum Anlegen selbst braucht es aber Verwaltungsrechte.** Ein neues Konto
> hinzuzufügen ist ein Eingriff in den Rechner, und Windows lässt ihn nur mit
> Administratorrechten zu – über die Einstellungen ebenso wie über `net user`.
> Wer selbst nur als Standardbenutzer angemeldet ist, kommt hier nicht weiter
> und braucht das Kennwort des Administratorkontos dieses Rechners.
>
> Das betrifft **nur diesen einen Schritt**. Alles Weitere – jusperfect
> einrichten, Zugangsdaten hinterlegen, arbeiten – geht danach ohne
> Verwaltungsrechte.

### Und dann: einmal anmelden

Nach dem Anlegen ist das Konto nur ein Eintrag in einer Liste. Der eigentliche
Benutzerordner unter `C:\Users\…` entsteht erst bei der **ersten Anmeldung**,
und die dauert einige Minuten – Windows richtet dabei den Schreibtisch, das
Startmenü und die Ordner ein. Warten Sie das ab, bevor Sie mit jusperfect
anfangen.

**Die Regel dahinter:** Fast alles, was jusperfect braucht, hängt am
**Windows-Benutzerprofil**, nicht am Rechner. Ein neues Konto ist deshalb fast
so leer wie ein neuer Rechner.

### Was nicht mitkommt

| Was | Wo es liegt | Wie es wiederkommt |
|---|---|---|
| Die AWS-Zugangsdaten | `%USERPROFILE%\.aws` | `ZUGANG-EINTRAGEN.bat` |
| Dauerhafte Einstellungen (`setx …`) | Registrierung des Benutzers | noch einmal setzen |
| Verknüpfungen auf dem Schreibtisch | Schreibtisch des Benutzers | `VERKNUEPFUNG.bat` |
| Die angemeldete Haufe-Sitzung | Browserprofil des Benutzers | einmal neu anmelden |

**Ein Vorteil, der leicht übersehen wird:** Ein frisches Konto hat auch keine
**alten** `setx`-Einstellungen. Genau daran ist am 16.09.2026 ein Prüfbogenlauf
gescheitert – eine vergessene Modellkennung aus einer früheren Einrichtung lief
noch mit. Im neuen Konto ist das ausgeschlossen.

### Zwei Stolpersteine, bevor Sie anfangen

**1. Wo der Programmordner liegt.** Liegt er unter
`C:\Users\<alter Name>\…`, kommt das neue Konto dort **nicht** hinein –
Windows sperrt fremde Benutzerprofile ab. Das ist keine Fehlfunktion, sondern
Absicht.

**2. Wie Python installiert wurde.** Wurde es seinerzeit *nur für mich*
installiert, liegt es ebenfalls im alten Profil. Das neue Konto findet dann kein
Python, und auch ein vorhandener `.venv`-Ordner hilft nicht: Er verweist auf die
Python-Installation, die er nicht erreichen kann.

Beides prüfen Sie im neuen Konto in einer Minute: Eingabeaufforderung öffnen
(Windows-Taste, `cmd`, Eingabetaste) und eintippen:

```
py -3.12 --version
```

Kommt eine Versionsnummer, ist Python für alle Konten da, und Sie sind fertig.

Kommt eine Fehlermeldung, muss Python nachinstalliert werden. Dafür gibt es zwei
Wege, und **der zweite braucht keine Verwaltungsrechte**:

**Mit Verwaltungsrechten – einmal für alle Konten.** Python 3.12 noch einmal
starten und im Setup **„Install for all users"** ankreuzen, zusätzlich zu „Add
python.exe to PATH". Danach findet es jedes Konto auf diesem Rechner.

**Ohne Verwaltungsrechte – nur für dieses Konto.** Im neuen Konto anmelden,
Python 3.12 von python.org herunterladen und mit der Voreinstellung **„Install
Now"** installieren. Diese legt Python in den eigenen Benutzerordner und
verlangt kein Administratorkennwort. Wichtig: unten im ersten Fenster
**„Add python.exe to PATH" ankreuzen**, bevor Sie auf „Install Now" klicken.

Der zweite Weg genügt vollständig, wenn jedes Konto ohnehin seine eigene Kopie
des Programms bekommt – und genau das empfehle ich unten. `py -3.12` kann dabei
weiterhin fehlschlagen, weil der Starter „py" Verwaltungsrechte verlangt. Das
macht nichts: `START-AWS.bat` fragt zuerst nach `py`, greift aber auf ein
schlichtes `python` zurück, und das steht nach „Add python.exe to PATH" bereit.
Zum Nachsehen:

```
python --version
```

### Der Weg, den ich empfehle: eine eigene Kopie

Für zwei Konten auf einem Rechner ist das der einfachste Weg. Er kostet ein paar
hundert Megabyte und eine Einrichtung, dafür gibt es keine Rechteprobleme.

1. Im **neuen** Konto anmelden.
2. Die ZIP herunterladen und in den **eigenen** Ordner auspacken, etwa
   `C:\Users\<neuer Name>\jusperfect--2.0`. Den äußeren Ordner nehmen, den,
   in dem die Startdateien liegen.
3. `START-AWS.bat` doppelklicken. Beim ersten Mal legt es die Arbeitsumgebung
   an; das dauert ein paar Minuten und ist einmalig.
4. Der Zugangstest wird fehlschlagen – die Zugangsdaten fehlen ja noch. Das ist
   an dieser Stelle richtig. Fenster schließen.
5. `ZUGANG-EINTRAGEN.bat` doppelklicken, die beiden Werte aus IAM eingeben.
6. `ZUGANG-PRUEFEN.bat`. Am Ende muss stehen: *„Der Zugang steht."*
7. `VERKNUEPFUNG.bat`, wenn Sie das Symbol auf dem Schreibtisch wollen.

**Zu den Zugangsdaten in Schritt 5:** Ob Sie dieselben nehmen wie im alten Konto
oder einen eigenen IAM-Benutzer anlegen, ist eine Frage der Ordnung, nicht der
Technik. Arbeitet in beiden Konten dieselbe Person, genügen dieselben Werte.
Sind es zwei Personen, legen Sie einen zweiten IAM-Benutzer an – der Abschnitt
darüber sagt, wie, und warum sich das lohnt.

### Der andere Weg: ein gemeinsamer Ordner

Möglich, aber mit einer Bedingung, die Sie kennen müssen. Der Ordner kommt dann
an eine Stelle außerhalb beider Profile, etwa `C:\jusperfect`. Dort darf ein
gewöhnliches Konto standardmäßig nur **lesen**. jusperfect muss aber schreiben –
in `.venv` und in das örtliche Aktengedächtnis. Sie müssten dem Ordner also erst
Schreibrechte für beide Konten geben (Rechtsklick → Eigenschaften → Sicherheit).

Dafür gibt es das Programm nur **einmal**, und eine neue ZIP wird nur **einmal**
ausgepackt. Bei zwei Konten wiegt das den Aufwand meist nicht auf; bei vieren
schon.

> **Wenn Sie den gemeinsamen Ordner nehmen:** Das örtliche Aktengedächtnis
> liegt dann im gemeinsamen Ordner und ist für beide Konten dasselbe. Für die
> erfundenen Testakten ist das gleichgültig. Vor dem ersten Versuch mit einer
> echten Akte gehört das Gedächtnis ohnehin nach S3 – dort stellt sich die
> Frage nicht mehr.

---

## Was der Test kostet

Größenordnung, keine Zusage – maßgeblich ist die Preisliste von AWS:

| | ungefähr |
|---|---|
| eine Frage an eine kleine Akte | wenige Cent |
| eine vollständige Aktenanalyse | ein niedriger zweistelliger Cent-Betrag |
| ein Nachmittag Ausprobieren | ein niedriger einstelliger Euro-Betrag |

Zwei Dinge senken das spürbar: **wenige Dokumente** in die Arbeitsakte ziehen
(nur was zur Frage gehört), und **mehrere Fragen zur selben Akte
hintereinander** – die zweite und jede weitere nutzen den Zwischenspeicher.

Was tatsächlich gelaufen ist, zeigt der Knopf **Nachweis**: Umfang und Kosten je
Aufruf, ohne Aktentext.

---

## Wenn etwas klemmt

**`AccessDeniedException`** – Schritt 3 fehlt (Modell nicht freigeschaltet) oder
die Richtlinie greift. Beides prüft `AWS-EINRICHTEN.md` Schritt 3 und
`infra/IAM.md`.

**`ValidationException` / `ResourceNotFoundException`** – falsche Modellkennung
für diese Region. Siehe Schritt 7, Inferenzprofil.

**„Es sind keine AWS-Zugangsdaten hinterlegt"** – Schritt 5 fehlt oder
`aws configure` lief in einem anderen Windows-Benutzerkonto.

**`ThrottlingException`** – zu viele Aufrufe kurz hintereinander. Warten.

**Budget erschöpft** – die Bremse aus Schritt 6 hat gegriffen. Das ist kein
Fehler. Grenze anheben oder bis zum Monatswechsel warten.

---

## Wann echte Akten zulässig sind

**Jetzt noch nicht.** Für den Betrieb mit Mandantendaten fehlen:

- **Die Ordnerprüfung auf dem Kanzleilaufwerk** – solange sie nicht gelaufen
  ist, beruht das Erkennen archivierter Akten auf einer Annahme.
  `python -m jusperfect.ordnerpruefung "J:\Akten"` – verändert nichts.
- **Ein Bedrock-Guardrail**, eingetragen unter `JUSPERFECT_GUARDRAIL_ID`.
- **Die vollständige AWS-Umgebung** statt des lokalen Betriebs: Anmeldung über
  Cognito, verschlüsselter Sitzungsspeicher, Protokolle. Dafür ist die
  SAM-Vorlage in [infra/](infra/) da – ein eigener Schritt, nicht dieser.
- **Datenschutz-Folgenabschätzung, Datenschutzhinweise, Mandatsbedingungen.**
  Die fachliche Grundlage steht im Löschkonzept in
  [SICHERHEIT.md](SICHERHEIT.md).

Bis dahin gilt: **erfundene Testakten.** Genau dafür ist diese Anleitung.
