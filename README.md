# jusperfect

Eine kontrollierte KI-Schicht über jur|nodes für eine kleine Kanzlei, gebaut aus dem
AWS-Baukasten: Cognito, API Gateway, Lambda, Bedrock (Converse, Guardrails, Prompt-Cache),
DynamoDB, S3, Textract, Secrets Manager, KMS, Budgets. Region Frankfurt.

**jur|nodes bleibt die führende Akte.** jusperfect liest Dokumente bedarfsbezogen, verarbeitet
sie temporär, schickt nur die nötigen Passagen an das Modell, belegt jede Aussage mit einer
Fundstelle und schreibt ausschließlich nach ausdrücklicher Freigabe zurück. Er ersetzt weder
jur|nodes noch die anwaltliche Prüfung.

Konzept, Prüfung und Entscheidungen: [KONZEPT.md](KONZEPT.md). Sicherheitsmodell: [SICHERHEIT.md](SICHERHEIT.md).
Infrastruktur und Deploy: [infra/README.md](infra/README.md).

**Mit echtem Modell testen (erfundene Akten): [AWS-EINRICHTEN.md](AWS-EINRICHTEN.md).**

**Wer das Programm benutzen will, liest [ANLEITUNG.md](ANLEITUNG.md):** Installation
Schritt für Schritt und der Gebrauch im Alltag, ohne Vorkenntnisse.

**Wer hier neu weiterarbeitet – Mensch oder KI – liest zuerst [UEBERGABE.md](UEBERGABE.md):** Stand, tragende Entscheidungen, Konventionen, offene Punkte und der nächste Schritt.

## Was jusperfect kann (Phase 1 und 2)

| Funktion | Was passiert | Ausgabe |
|---|---|---|
| Akte öffnen | Berechtigung prüfen, Stammdaten, Dokumentliste, Beteiligte und Fristen aus jur|nodes | Sitzung mit Ablauf |
| Zwei-Fenster-Explorer | Links die Akte aus jur|nodes, rechts die Arbeitsakte; Dokumente per Drag&Drop oder Pfeil bewegen | Arbeitskopie, jederzeit änderbar |
| Dokumente laden | Text extrahieren (PDF, DOCX, Text), Scans über Textract, temporär verschlüsselt ablegen | Passagen mit Kennungen `D2-S1-P3` |
| Frage an die Akte | Passagenauswahl nach Stichwortnähe, Antwort mit Belegen | Text mit `[Q: …]`, Quellen, Kosten |
| Rückfragen | Letzte geprüfte Q&A-Runden als begrenzter Sitzungskontext; mit Aktengedächtnis auch nach Wiederaufnahme | Mehrfachdialog mit erneut prüfbaren Originalbelegen |
| Aktenanalyse | Chronologie, Beteiligte, Forderungen, Beweismittel, offene Punkte, Widersprüche | Tabellen, jede Zeile mit Beleg |
| Eingangsprüfung | Neues Dokument: Art, Absender, Kernaussage, Fristauslöser, nächste Schritte | Hinweise, keine Fristberechnung |
| Entwurf | Mandant, Gegner, Versicherung, RSV, Mahnung, Aktenvermerk, optional nach Kanzleimuster | bearbeitbarer Entwurf |
| Freigabe | Nur der Ersteller, nur mit Bestätigung, nur der exakt angezeigte Text | Vermerk in der jur|nodes-Akte |
| Eigene Aufträge | Kanzlei-eigene Vorlagen als `.txt`/`.md`: Anweisung + Material (Trennlinie), Dateiname = Beschriftung | Entwurfsvorlagen im Entwurfsdialog |
| Referenzen | Veröffentlichtes Material (Urteile, Gesetze) als `.txt`/`.md`/`.pdf` in den Kontext ziehen | mitzitiert, eigene Kennung `R…` |
| Haufe-Recherche | Direktlink zum Haufe-Copilot; öffnet im Browser (Login-Sitzung des Nutzers), Frage in die Zwischenablage | Recherche extern, Fund als Referenz zurück |
| Posteingang | Beobachteter Ordner (lokal): eingehende Dokumente werden vorbereitet, sobald sie vollständig sind | Überblick, Eingangsprüfung – Mensch entscheidet |
| Verarbeitungsnachweis | Was ist wann an welches Modell gegangen – Kurzkennung und Umfang, kein Aktentext | eigene Vorgänge unter `/api/nachweis` |
| Abschluss der Akte | Ist die Akte in jurnodes archiviert: Übergangsfrist, Export des belegten Arbeitsstands nach jurnodes, danach vollständige Löschung | Löschnachweis mit Zahlen und Zeitpunkten |
| Berichtigung | Einzelnen Dokumentauszug oder einzelne Frage-Antwort aus dem Gedächtnis entfernen | Abgeleitetes fällt mit, damit kein Rest bleibt |
| Aufsicht | Übersicht aller Arbeitsbereiche: verwaist, Status ungeklärt, Löschung vorgemerkt oder fällig | Knopf „Arbeitsbereiche“, nur für die Verwaltung |
| Aktengedächtnis (opt-in) | Extrahierte Texte, belegter Lebenssachverhalt und belegte Q&A im eigenen Kanzlei-AWS-Konto | Wiederaufnahme ohne erneutes Einlesen/OCR; neue Dokumente werden ergänzt |

Belege werden maschinell geprüft: Eine Kennung, die das Modell nennt, muss auf eine tatsächlich
mitgeschickte Passage zeigen, sonst wird die Stelle als „ohne Beleg“ markiert.

**Gelöscht wird nach dem Aktenstatus, nicht nach der Uhr.** Eine Bearbeitungspause löst nie eine
Löschung aus; erst ein bestätigter Abschluss in jurnodes startet die Übergangsfrist, und erst nach
erfolgreichem Export wird gelöscht. Das vollständige Löschkonzept steht in
[SICHERHEIT.md](SICHERHEIT.md).

## Schnellstart Windows (ein Klick)

Für die Vorführung ohne Vorwissen: im entpackten Ordner die Datei **`START-DEMO.bat`**
doppelklicken. Sie legt beim ersten Mal alles selbst an (virtuelle Umgebung, Bausteine) und
öffnet jusperfect im Browser. Einzige Voraussetzung: einmalig
[Python 3.12](https://www.python.org/downloads/release/python-3128/) installiert (beim Setup
„Add Python to PATH" ankreuzen) – **nicht** die neueste Fassung von der Startseite, 3.13 und
neuer laufen nicht. Nutzerkennung im Browser: `ra-weber`. Zum Beenden das schwarze Fenster
schließen.

Der ZIP von der Startseite bringt die Arbeitsfassung **`2.0`**; `main` trägt die
ältere Fassung 1.0. Eine ausführliche Anleitung steht in
[ANLEITUNG.md](ANLEITUNG.md).

## Lokal starten (ohne AWS, ohne KI)

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env                              # Standard: Demo-Anbieter, Testakten
set -a; . ./.env; set +a                          # Windows: Variablen in der Sitzung setzen
python -m jusperfect
```

Dann `http://127.0.0.1:8765` öffnen, als Nutzerkennung `ra-weber` oder `refa-lorenz` eintragen
(siehe `testdaten/nutzer.json`). Der Demo-Anbieter arbeitet mit Mustern statt KI; er zeigt den
vollständigen Ablauf, nicht die Qualität des Modells.

Mit echtem Modell lokal: `JUSPERFECT_ANBIETER=bedrock` und AWS-Zugangsdaten mit Bedrock-Rechten
in der Umgebung (Profil oder `AWS_*`-Variablen). Die Anwendung erzwingt EU-Regionen.

## In AWS betreiben

Siehe [infra/README.md](infra/README.md). Kurz: `sam build`, `sam deploy`, Oberfläche
veröffentlichen, jur|nodes-Token im Secrets Manager setzen, Nutzer in Cognito anlegen,
Berechtigungen mit `python -m jusperfect.verwaltung` eintragen.

### Aktengedächtnis bewusst aktivieren

Für die **erfundenen Testakten ist es eingeschaltet**: `START-DEMO.bat` und `START-AWS.bat`
setzen `JUSPERFECT_GEDAECHTNIS=lokal`. Ohne das lebt eine Sitzung 15 Minuten, und ein Mandat, das
sich über Tage zieht, ließe sich gar nicht durchspielen. `GEDAECHTNIS-LEEREN.bat` setzt diesen
Testspeicher zurück.

Für echte Mandantenakten ist es standardmäßig **ausgeschaltet**. Es ändert das
Datenschutzmodell, weil neben jur|nodes eine dauerhafte Fallkopie im eigenen AWS-Konto entsteht.
Vor `JUSPERFECT_GEDAECHTNIS=aws` müssen DSFA, Verarbeitungsverzeichnis, Löschkonzept,
Datenschutzhinweise und Mandatsbedingungen angepasst und organisatorisch freigegeben sein. Die
Anwendung verlangt zusätzlich eine positive `JUSPERFECT_GEDAECHTNIS_AUFBEWAHRUNG_TAGE`; die
SAM-Vorlage setzt daraus die automatische S3-Löschung nach der letzten Änderung.

Die SAM-Vorlage legt dafür einen eigenen, nicht öffentlichen S3-Bucket ohne Versionierung an.
Uploads müssen SSE-KMS verwenden; die Objektpfade enthalten nur SHA-256-Ableitungen, keine
Aktenzeichen. Nach der Aktivierung gilt:

- Öffnen einer Akte stellt gespeicherte Dokumenttexte automatisch in der flüchtigen Sitzung her.
- Neu geladene Dokumente werden angehängt und müssen nicht erneut per OCR eingelesen werden.
- Nur die fail-closed geprüfte Antwortfassung wird als Q&A gespeichert.
- **Gedächtnis** ergänzt den Lebenssachverhalt nur um noch nicht verarbeitete Dokumente und nutzt
  `JUSPERFECT_MODELL_GEDAECHTNIS`, sonst das kleine Modell.
- `DELETE /api/akten/{akte_id}/gedaechtnis` löscht die dauerhafte Fallkopie nach erneuter
  Berechtigungsprüfung.

Für Demo und Tests dient `JUSPERFECT_GEDAECHTNIS=lokal` mit
`JUSPERFECT_GEDAECHTNIS_PFAD=.jusperfect-gedaechtnis`. Dieser Dateispeicher schreibt
**unverschlüsselten Klartext** in den Programmordner. Die Anwendung lässt ihn deshalb nur
zusammen mit den Testakten zu (`JUSPERFECT_JURNODES_ADAPTER=fixture`) und startet sonst nicht –
sonst genügte es, in einer Startdatei den Adapter auf das Kanzleilaufwerk zu stellen und das
Gedächtnis abzuschalten zu vergessen.

### Mehrfachdialog

jusperfect hält standardmäßig die letzten sechs **belegten und fail-closed geprüften**
Frage-Antwort-Runden im flüchtigen Sitzungszustand. Rückfragen erhalten diesen Verlauf und die
zugehörigen Originalpassagen; neue Antworten werden deshalb weiterhin gegen echte Fundstellen
geprüft. `JUSPERFECT_DIALOG_MAX_RUNDEN` begrenzt den Verlauf. Ohne Aktengedächtnis wird er beim
Schließen oder Ablauf der Sitzung gelöscht. Mit aktiviertem Aktengedächtnis werden dessen letzte
geprüfte Q&A-Runden beim Wiederöffnen als neuer Sitzungskontext übernommen.

## jur|nodes-Anbindung (Phase 0)

Die Schnittstelle ist in `jusperfect/jurnodes/base.py` festgelegt: sechs Lesefunktionen,
eine freigabepflichtige Schreibfunktion. Der HTTP-Adapter (`http_adapter.py`) hat Pfade und
Feldnamen an einer Stelle gesammelt, weil beides erst gegen die echte API geprüft werden muss.
Bis dahin liefert `fixture_adapter.py` Testakten aus `testdaten/akten/`.

Der im Konzept vorgesehene Plan B ist gebaut: `webdav_adapter.py` liest den Ordnerexport der
Kanzlei (eingebundenes WebDAV/OneDrive/Nextcloud) im Aufbau
`<Wurzel>/<Anwalt>/<Jahr>/<Aktenzeichen Bezeichnung>/`. Der Ordnername einer Akte trägt vorn das
Aktenzeichen, dahinter die Bezeichnung; der Anwalt ist der Sachbearbeiter. Aktivierung:
`JUSPERFECT_JURNODES_ADAPTER=webdav` und `JUSPERFECT_JURNODES_WEBDAV=J:\Akten`. Geschrieben wird
nur ein freigegebener Vermerk in den Unterordner `Vermerke` der Akte; gelesen wird
bedarfsbezogen. Beteiligte und Fristen liefert erst die API – aus dem Ordner arbeitet die
Analyse allein aus dem Dokumenttext.

Den **Aktenstatus** liest der Adapter aus dem Ordnernamen: In jurnodes wird eine Akte von Hand
archiviert, danach steht die Kennung (`JUSPERFECT_ARCHIV_KENNUNG`, Vorgabe `archiviert`) im
Namen – vorn oder hinten, auch in Klammern. Solche Akten melden `archiviert` und lösen die
Abschlussprüfung aus; ohne Kennung gilt die Akte als `laufend`. Ist keine Kennung eingestellt,
bleibt der Status `unbekannt`, und es wird nichts gelöscht. Ob die Konvention im Bestand
durchgehalten wird, beantwortet nur der Bestand:

```bash
python -m jusperfect.ordnerpruefung "J:\Akten"
```

Das zählt erkannte und laufende Akten und meldet Ordnernamen, die nach Archiv aussehen, ohne
erkannt zu werden (etwa „Archiv 2024"). Es verändert nichts.

## Prüfen

```bash
pip install -e ".[dev]" moto[s3,dynamodb] cfn-lint
python -m unittest discover -s tests -v
cfn-lint infra/template.yaml
node --check jusperfect/static/app.js
```

Dieselben Prüfungen laufen über `.github/workflows/jusperfect.yml` bei jedem Push und jedem
Pull Request, der `jusperfect/` betrifft. So kann ein Stand ohne vollständige Tests und gültige
AWS-Vorlage nicht unbemerkt als geprüft gelten.

## Aufbau

```
jusperfect/
  config.py          Einstellungen aus der Umgebung, Betriebsarten lokal/aws
  domain/models.py   Akte, Dokument, Passage, Quelle, Antwort, Analyse, Triage, Entwurf, Sitzung
  jurnodes/          Schnittstelle, HTTP-Adapter, Testakten-Adapter
  security/          Identität (Cognito/Kopfzeile), Berechtigungen, Freigaben, Temporärspeicher,
                     inhaltsfreies Protokoll, Geheimnisse
  speicher/          Sitzungsspeicher lokal (Arbeitsspeicher) und AWS (DynamoDB + S3)
  ocr/               Textract, oder keine OCR
  providers/         Bedrock Converse (Guardrail, Cache), Demo ohne KI
  services/          Extraktion, Passagen, Belege, Prompts, Frage/Analyse/Triage, Entwürfe,
                     Kostenwächter, Kanzleiwissen (Knowledge Base, Phase 2)
  web.py             FastAPI-Schnittstelle; lambda_handler.py für AWS; verwaltung.py für Berechtigungen
  static/            Oberfläche ohne Abhängigkeiten, PKCE-Anmeldung gegen Cognito
infra/               SAM-Vorlage, Deploy-Skripte
testdaten/           zwei erfundene Testakten, Testnutzer
tests/               unittest-Suite mit Fake-Anbieter, moto für DynamoDB/S3
```
