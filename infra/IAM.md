# Zugriffsrichtlinie: nur Claude, nur Europa

> **Dieses Dokument wird nur auf ausdrückliche Anweisung geändert.**
> Es beschreibt eine Sicherheitsgrenze. Wer sie im Vorbeigehen lockert, weil
> gerade etwas nicht läuft, hebt sie auf. Änderungen gehören besprochen, nicht
> nebenbei erledigt.

## Wozu

jusperfect schickt **echten Aktentext** an ein Sprachmodell. Welches Modell das
ist, entscheidet nicht die Konfigurationsdatei allein – sie ist nur eine
Zeichenkette und lässt sich vertippen oder ändern. Die verbindliche Grenze zieht
AWS selbst: Was die Zugriffsrichtlinie nicht erlaubt, kommt gar nicht erst
zustande, gleich was in der Anwendung steht.

Die Richtlinie erlaubt deshalb **ausschließlich Claude-Modelle in europäischen
Regionen** und verbietet alles andere ausdrücklich.

## Die beiden Orte

**1. Die Anwendung selbst.** Die Rolle der Lambda-Funktion steht in
`infra/template.yaml` (`NurClaude` und `KeinAnderesModell`). Sie wird beim
`sam deploy` mit angelegt; hier ist nichts von Hand zu tun.

**2. Ein Mensch mit AWS-Zugang.** Wer sich in der AWS-Konsole anmeldet, um
nachzusehen oder etwas zu prüfen, braucht eine eigene Richtlinie. Dafür ist
`infra/iam-nur-claude.json` da.

## Anlegen und anhängen

1. In `infra/iam-nur-claude.json` die Zeichenfolge `AWS-KONTONUMMER` durch die
   zwölfstellige Kontonummer der Kanzlei ersetzen (zweimal).
2. AWS-Konsole → **IAM** → *Richtlinien* → *Richtlinie erstellen* → Reiter
   **JSON** → Inhalt einfügen → Name etwa `jusperfect-nur-claude`.
3. Dem Benutzer oder der Rolle anhängen, die den Zugang bekommen soll.

## Was die sieben Anweisungen tun

| Anweisung | Wirkung |
|---|---|
| `ClaudeAufrufen` | erlaubt das Aufrufen von Claude-Modellen und -Inferenzprofilen in EU-Regionen |
| `TexterkennungFuerScans` | erlaubt `textract:DetectDocumentText` – gescannte Blätter ohne Textschicht lesen (Rückscheine, Einschreiben, Vollmachten) |
| `SchutzgelaenderAnwenden` | erlaubt `bedrock:ApplyGuardrail` – ohne diese Anweisung geht **kein einziger** Modellaufruf durch, solange ein Schutzgeländer gesetzt ist |
| `ModelleAnsehen` | erlaubt, die Modellliste, die gebuchten Modellabonnements und den Zustand der Aufrufprotokollierung zu **lesen** – nötig, um zu sehen, was freigeschaltet ist und dass nichts mitgeschrieben wird |
| `KeinAnderesModell` | **verbietet** jeden Modellaufruf, der nicht Claude ist |
| `NurEuropa` | **verbietet** jeden Bedrock-Aufruf außerhalb europäischer Regionen |
| `KeineModellverwaltung` | verbietet Feinabstimmung, Stapelverarbeitung, das Ein- und Ausschalten der Aufrufprotokollierung und das Ändern oder Löschen von Guardrails |

`TexterkennungFuerScans` ist am 01.10.2026 auf ausdrückliche Anweisung der
Kanzlei dazugekommen. Sie erlaubt **genau eine** Aktion, und bewusst nicht
mehr:

* `textract:DetectDocumentText` liest **ein einzelnes Blatt**, das als Bytes
  mitgeschickt wird. Es entsteht kein Ablageort und keine Kopie bei AWS.
* `textract:StartDocumentTextDetection` für **mehrseitige** Scans ist
  **nicht** enthalten. Dieser Weg verlangt einen Ablageort in S3 – also einen
  weiteren Ort, an dem Akteninhalt liegt, mit allem, was daran hängt:
  Verschlüsselung, Lebenszyklus, Eintrag in der DSFA. Wer ihn braucht, trägt
  die Berechtigung bewusst nach, nicht nebenbei.

`SchutzgelaenderAnwenden` ist am 02.10.2026 auf ausdrückliche Anweisung der
Kanzlei dazugekommen, und der Weg dorthin gehört zur Anweisung:

Das Programm schickt bei **jedem** Modellaufruf das Schutzgeländer mit. AWS
verlangt dafür ein eigenes Recht – es genügt nicht, `bedrock:InvokeModel` zu
dürfen. Ohne dieses Recht wird jeder Aufruf abgewiesen, auch ein völlig
regulärer.

Aufgefallen ist es erst an diesem Tag, und das hat einen Grund, der hier
festgehalten gehört: **Der Prüfbogen läuft ohne Schutzgeländer.** Er hat am
01.10.2026 für 3,10 € gemessen und alles für gut befunden – über einen Weg,
den der Betrieb so nicht geht. Eine Probe, die anders fragt als der Betrieb,
prüft etwas anderes als den Betrieb; dieser Satz steht in diesem Projekt an
mehreren Stellen, und hier hat er wieder zugeschlagen.

Die Ressource lautet `arn:aws:bedrock:eu-*:*:guardrail/*` und bewusst nicht
`*`:

* Nur **Schutzgeländer**, nichts anderes.
* Nur in **europäischen** Regionen, unabhängig von der Sperre `NurEuropa`.
* Der Stern an der Stelle der Kontonummer ist Absicht. Dort stand in den
  beiden anderen Anweisungen `AWS-KONTONUMMER`, und dieser Platzhalter hat am
  02.10.2026 in der Kanzlei eine rote Zeile erzeugt. Eine Angabe, die
  eingetragen werden **muss**, ist eine Fehlerquelle; hier wird keine
  gebraucht, weil die Richtlinie ohnehin nur im eigenen Konto gilt.

Datenschutzrechtlich ist Textract **derselbe Auftragsverarbeiter** wie für die
Texte (AWS, Frankfurt) – also kein neuer Vertrag. Genannt werden muss es in
der DSFA trotzdem.

**Warum zusätzlich verbieten, was ohnehin nicht erlaubt ist?** Ein `Deny` in AWS
wiegt stärker als jedes `Allow` – auch stärker als eines aus einer anderen
Richtlinie, die jemand später anhängt. Erlauben allein wäre eine Absicht;
verbieten ist eine Grenze.

`KeineModellverwaltung` verdient eine eigene Begründung: Wer die
Aufrufprotokollierung einschalten darf, kann veranlassen, dass **Aktentext in
ein Protokoll geschrieben** wird. Wer Guardrails ändern darf, kann die
Inhaltsprüfung abschalten. Beides sind Wege, die Sicherheitszusagen von außen
auszuhebeln, ohne eine Zeile Code anzufassen.

## Was diese Richtlinie **nicht** leistet

- **Sie ersetzt nicht die Freischaltung.** Ein Modell muss im AWS-Konto
  zusätzlich freigeschaltet sein (Bedrock → *Model access*). Die Richtlinie
  erlaubt nur; sie schaltet nichts frei.
- **Sie sagt nichts über den Inhalt.** Sie regelt, *welches Modell* Text sehen
  darf, nicht *welcher Text* hingeht. Das leisten die Belegpflicht und der
  geprüfte Ausgang in der Anwendung (siehe `SICHERHEIT.md`).
- **Sie schützt nicht vor einem zu weit berechtigten Konto.** Wer in AWS
  Administrator ist, kann sie jederzeit abnehmen. Sie gehört deshalb an
  Benutzer *ohne* Administratorrechte.
- **Sie deckt Bedrock ab, dazu ein Leserecht im AWS Marketplace** (die
  Modellabonnements – dort läuft die Freischaltung der Modelle). S3, DynamoDB,
  Textract und KMS sind über die Rolle der Anwendung geregelt, nicht hier.

## Wenn ein Aufruf abgewiesen wird

Meldet AWS `AccessDeniedException`, ist das im Regelfall **kein Fehler, sondern
die Richtlinie bei der Arbeit**. Zu prüfen ist der Reihe nach:

1. Ist die Modellkennung wirklich ein Claude-Modell? Sie muss mit
   `anthropic.claude-` beginnen, ein Inferenzprofil mit `eu.anthropic.claude-`.
2. Läuft der Aufruf in einer EU-Region? `JUSPERFECT_AWS_REGION` prüfen.
3. Ist das Modell im Konto freigeschaltet?

Erst wenn alle drei stimmen und der Aufruf weiter scheitert, liegt es an der
Richtlinie. **Sie dann nicht aufweiten, ohne den Grund verstanden zu haben.**

**Welches Recht fehlt, sagt das Programm selbst.** Seit dem 02.10.2026 endet
die Meldung mit einem Satz wie *„Es fehlt: bedrock:ApplyGuardrail."* Der Name
der Handlung ist die einzige Angabe, die aus der Meldung von AWS hinausgeht –
der übrige Wortlaut bleibt drinnen, weil darin ein Stück der Anfrage stehen
kann, und das ist Aktentext. Wie das abgesichert ist, steht in
`jusperfect/aws_handlung.py`.
