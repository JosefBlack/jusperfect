# Infrastruktur (AWS SAM, eu-central-1)

Alles in `template.yaml`. Ein Stack, ein Deploy, ein Löschbefehl.

## Bausteine

| Baustein | Zweck | Grundsatz |
|---|---|---|
| Cognito User Pool | Anmeldung mit MFA, Gruppe `alle-akten` für Anwälte | nur vom Administrator angelegte Nutzer |
| API Gateway (HTTP API) | JWT-Authorizer prüft das Cognito-Token vor der Funktion | Zugriffsprotokoll ohne Inhalte |
| Lambda (Python 3.12, arm64) | die Anwendung (`jusperfect.lambda_handler`) | maximal 5 parallel, 5 Minuten |
| Bedrock Converse | Modell, Guardrail auf Frage und Antwort, Prompt-Cache | nur `eu-*` per Deny-Regel |
| DynamoDB | Sitzungen, Entwürfe, Nutzung; TTL-Attribut `ablauf` | KMS-verschlüsselt |
| S3 Sitzungsbucket | extrahierte Texte, Scans für Textract | KMS, Lebenszyklus 1 Tag, keine Versionierung |
| S3 Gedächtnisbucket | optionale dauerhafte Fallkopie | KMS erzwungen, kein Aktenzeichen im Objektpfad, keine Versionierung |
| Textract | OCR für gescannte PDFs und Bilder | nur bei fehlender Textschicht |
| Secrets Manager | jur|nodes-Token | Wert nach dem Deploy setzen |
| KMS | ein Schlüssel für Tabelle, Bucket, Protokolle, Geheimnis | jährliche Rotation |
| S3 + CloudFront | Oberfläche (statisch) | Origin Access Control, Sicherheits-Header |
| AWS Budgets, CloudWatch, SNS | Kostenalarme bei 50/80/100 % und Prognose, Fehleralarm | E-Mail |

Nicht enthalten, bewusst: Bedrock Flows, Knowledge Base, AgentCore, Step Functions. Die
Knowledge Base für Kanzleiwissen kommt in Phase 2 (`JUSPERFECT_KANZLEIWISSEN_KB_ID`), die
Berechtigung `bedrock:Retrieve` ist bereits vorgesehen.

## Voraussetzungen

1. AWS-Konto, Region Frankfurt. Modellzugang für das gewünschte Anthropic-Modell in Bedrock
   beantragen; Kontingente (Tokens pro Minute) für neue Konten früh erhöhen lassen.
2. Guardrail in Bedrock anlegen (Themenverbote, Ausgabefilter). Kennung und Version als Parameter.
3. AWS SAM CLI und Docker oder `sam build --use-container` für arm64.
4. Bedrock-Modellaufrufprotokollierung (Model invocation logging) bleibt **aus**. CloudTrail bleibt an.
5. Vor der Aktivierung des Aktengedächtnisses sind DSFA, Verarbeitungsverzeichnis,
   Löschkonzept, Datenschutzhinweise und Mandatsbedingungen anzupassen und freizugeben.

## Deploy

```bash
cp infra/samconfig.example.toml infra/samconfig.toml   # Werte eintragen
sam build -t infra/template.yaml
sam deploy --config-file infra/samconfig.toml --guided   # beim ersten Mal
infra/oberflaeche_veroeffentlichen.sh jusperfect-pilot
# Ausgabe OberflaecheUrl als Parameter OberflaecheUrl setzen und erneut deployen
```

Danach:

```bash
# jur|nodes-Token setzen (nie im Code)
aws secretsmanager put-secret-value --secret-id jusperfect/pilot/jurnodes \
  --secret-string '{"token": "…"}' --region eu-central-1
# Nutzer anlegen (E-Mail = Anmeldename), Anwälte in die Gruppe alle-akten
aws cognito-idp admin-create-user --user-pool-id <NutzerpoolId> --username anwalt@kanzlei.example
aws cognito-idp admin-add-user-to-group --user-pool-id <NutzerpoolId> --username anwalt@kanzlei.example --group-name alle-akten
# Mitarbeiter mit Aktenliste (Cognito-sub des Nutzers)
JUSPERFECT_BETRIEBSART=aws JUSPERFECT_IDENTITAET=cognito JUSPERFECT_SPEICHER=aws JUSPERFECT_ANBIETER=bedrock \
JUSPERFECT_DYNAMODB_TABELLE=jusperfect-pilot JUSPERFECT_S3_BUCKET=x \
python -m jusperfect.verwaltung eintragen <sub> "Name" VU-2026-0042
```

Das Gedächtnis bleibt nach dem Deploy zunächst mit `JUSPERFECT_GEDAECHTNIS=aus` deaktiviert.
Nach der organisatorischen Freigabe wird beim Deploy `GedaechtnisAufbewahrungTage` positiv gesetzt
und die Lambda-Variable auf `aws` geändert; der Stack liefert den Namen als Output
`GedaechtnisBucket`. Ein bloß vorhandener Bucket aktiviert keine Speicherung.

## Prüfen vor dem Deploy

```bash
cfn-lint infra/template.yaml
```

## Löschen

`sam delete --stack-name jusperfect-pilot`. Beide Buckets müssen leer sein. Der Sitzungsbucket
leert sich binnen eines Tages. Das Gedächtnis darf nur nach dem freigegebenen Löschkonzept und
bewusster Prüfung der betroffenen Akten geleert werden.
