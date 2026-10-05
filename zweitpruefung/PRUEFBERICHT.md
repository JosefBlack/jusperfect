# Zweitprüfung jusperfect — 05.10.2026

## Ergebnis

**Die zentralen Zusagen sind im gelieferten Stand nicht durchgehend erfüllt.** Alle **1.625 vorhandenen Tests bestehen**. Zusätzlich bestätigen **17 gezielte Gegenproben** konkrete Lücken. Besonders dringlich sind die Fehlerprotokollierung, die unvollständige Löschung einschließlich Wiederherstellung durch laufende Vorgänge, die Beleg- und Fristensperren sowie die Freigabeprüfung. Die Textract-Aussagen der Datenschutzunterlagen benötigen einen gesonderten Kontonachweis.

Der Bericht enthält **13 Befunde** und Antworten auf **alle fünf Fragen** des Prüfauftrags. Zwölf Befunde beruhen auf reproduzierbarem Programmverhalten; F12 ist ein belegter Widerspruch zwischen der technischen Begründung der Unterlagen und der öffentlichen AWS-Dokumentation, dessen tatsächliche Auswirkung von der Kontokonfiguration abhängt.

**Empfehlung:** Die betroffenen Schutzfunktionen vor weiterer vertrauensgestützter Nutzung mit Mandatsgut korrigieren und ihre Zusagen bis dahin nicht als technisch garantiert behandeln. Die Entscheidung über den laufenden Kanzleibetrieb bleibt bei der Kanzlei. Es wurde kein tatsächlicher neuer Abfluss aus dem Produktivsystem nachgewiesen.

## Gegenstand, Verfahren und Grenzen

- Ausgangspunkt war `PRUEFAUFTRAG.md` im ZIP. Geprüft wurden die dort benannten Sicherheitsgrenzen, die einschlägigen Dienste, Adapter, Oberfläche, Konfiguration, Tests und Rechtsentwürfe; ergänzend die öffentlich zugänglichen Primärquellen zu AWS und jur|nodes.
- ZIP: `jusperfect-pruefpaket-05.10.2026.zip`; SHA-256: `53f07feb396413687d9dfabe0cb7daead28410334bfee979c6c4884c92656c1f`.
- Ausführung in einer getrennten Python-3.12.14-Umgebung unter Windows. AWS- und jur|nodes-Antworten wurden mit erfundenen Daten simuliert; der S3-Versuch verwendet Moto. Die Protokollprobe ruft die originale Uvicorn-ASGI-Fehlerbehandlung ohne Netzwerktransport auf.
- Keine Produktivzugangsdaten gelesen, keine echten Akten angefragt, keine Nachrichten an Hersteller oder AWS versendet und keine Programmkorrekturen vorgenommen. Der Hashvergleich aller **269 Originaldateien** ergab keine Änderungen und keine fehlenden Dateien.
- Vorhandene Suite: **1.625 bestanden, eine Deprecation-Warnung, 61,14 Sekunden**. Gegenproben: **17 bestanden, eine Deprecation-Warnung, 1,88 Sekunden**. **Grün bei den Gegenproben bedeutet: Die Lücke wurde reproduziert.** Es sind noch keine Regressionstests für einen behobenen Sollzustand.
- Nicht geprüft: wirksame IAM-/SCP-Richtlinien des Kontos, AWS-Verträge und Opt-out-Zustand, produktive Logdateien, reale E-Akten-Schnittstelle sowie ein Browserdurchlauf aller Funktionen. UI-Aussagen zum Streaming beruhen auf API-Probe und Quelltext.
- Die bekannte Korrespondenzordner-Vermengung, fehlenden Vermerke, offene Rechtsbewertungen und absichtlich allgemeinen Aktenrechte werden nicht als neue Befunde gezählt.

Datei- und Zeilenangaben unten beziehen sich auf das unveränderte Paket im Unterordner `jusperfect-pruefpaket-05.10.2026`. Gegenproben und Protokolle liegen neben diesem Bericht. **P1** bedeutet vorrangig zu beheben; **P2** bedeutet relevante Absicherungs- oder Nachweislücke.

## Befunde

### F01 · P1 — Ursprüngliche Anbieterfehler gelangen ins Serverprotokoll

**Fundstellen:** `jusperfect/web.py:294`, `jusperfect/providers/bedrock.py:241`, `jusperfect/__main__.py:128`. **Gegenproben:** `test_12` und `test_13`.

Eine simulierte `ClientError`-Antwort von Bedrock enthält einen erfundenen vertraulichen Marker in `Error.Message`. Der Provider erzeugt daraus einen bereinigten `ProviderFehler`, behält aber die ursprüngliche Ausnahme mittels `raise … from e`. Der pauschale FastAPI-Handler für `Exception` sendet zwar eine saubere HTTP-502-Antwort; Starlettes äußerer Fehlerhandler wirft die Ausnahme anschließend erneut. Die originale Uvicorn-Fehlerbehandlung protokolliert den vollständigen Traceback einschließlich Ursache und Marker. `access_log=False` schaltet dieses Fehlerprotokoll nicht ab.

**Schaden:** Enthält eine echte Abhängigkeitsfehlermeldung Mandatsinhalt, kann dieser in Serverlogs landen. Die Feldsperren in `security/protokoll.py` werden dabei nicht durchlaufen. Die saubere HTTP-Antwort beweist somit keine sauberen Logs.

**Abhilfe:** Erwartete Fehler über spezifische Ausnahmehandler abfangen; unerwartete Fehler an einer geprüften ASGI-Grenze inhaltsfrei behandeln. Nicht nur den eigenen Ereignislogger, sondern auch Server- und Bibliothekslogger prüfen. Regression muss HTTP-Antwort **und** tatsächlich erzeugtes Fehlerlog erfassen.

**Sicherheit:** Hoch für den reproduzierten Fehlerpfad; kein Nachweis, dass AWS im Produktivbetrieb bereits Mandatsinhalt in einer Fehlermeldung zurückgegeben hat.

### F02 · P1 — „Dokument vergessen“ entfernt nicht alle Ableitungen und sperrt alte Sitzungen nicht

**Fundstellen:** `jusperfect/services/gedaechtnis.py:551`, `:604`, `:306`, `:709`; `jusperfect/web.py:608`. **Gegenprobe:** `test_04`.

Ein gespeichertes Dokument wird über die öffentliche DELETE-Route entfernt. Dabei bleiben drei relevante Reste:

1. Die gespeicherte `g.analyse` wird nicht bereinigt; ein Chronologieereignis aus dem entfernten Dokument erscheint weiterhin in der zurückgegebenen Analyse.
2. Ein Lebenssachverhalt mit `[Q: D1-S1-P1, D2-S1-P1]` bleibt nach Entfernen von D1 vollständig stehen; lediglich der D1-Verweis verschwindet. Es wird nicht nachgewiesen, dass D2 den verbleibenden Text alleine trägt.
3. Eine bereits geöffnete Sitzung behält die D1-Passagen. Eine anschließende Frage kann darauf antworten; `antwort_merken` speichert diese Antwort erneut im Aktengedächtnis, ohne zu prüfen, ob ihre Quellen dort noch zugelassen sind.

**Schaden:** Die Oberfläche meldet erfolgreiche Entfernung, während abgeleiteter Inhalt erhalten bleibt oder unmittelbar wieder gespeichert wird. Das betrifft ausdrücklich die Zusage „samt allem Abgeleiteten“ und die praktische Bedienbarkeit von Berichtigungs-/Löschverlangen.

**Abhilfe:** Alle abhängigen Ergebnisse erfassen, einschließlich gespeicherter Analyse; gemischte Aussagen ganz verwerfen oder aus verbleibenden Quellen neu erzeugen. Aktive Sitzungen invalidieren und eine Lösch-/Freigabeversion gegen verspätete Ergebnisse prüfen. Ein bewusstes späteres Wiedereinlesen muss eine eigene Benutzerhandlung sein.

**Sicherheit:** Hoch; API-Ablauf mit lokaler Testablage und erfundenen Dokumenten reproduziert.

### F03 · P1 — Gemeinsamer ETag-Zustand lässt alte S3-Stände neue Löschungen überschreiben

**Fundstellen:** `jusperfect/gedaechtnis/aws.py:120`, `:126`, `:145`; lang laufende Verarbeitung in `jusperfect/services/gedaechtnis.py` hält gelesene Objekte bis zum späteren Speichern. **Gegenprobe:** `test_15`.

Zwei Vorgänge lesen denselben Gedächtnisstand über dieselbe Speicherinstanz. Vorgang B entfernt das Dokument und speichert. Dadurch wird die instanzweite Tabelle `_etags` aktualisiert. Der ältere Vorgang A speichert anschließend sein altes Objekt. Sein `IfMatch` stammt nun aus der **neuen** Tabelle, obwohl sein Inhalt noch zur **alten** Version gehört. S3 akzeptiert die Schreiboperation; das gelöschte Dokument ist wieder vorhanden.

**Schaden:** Parallele Fenster oder Anfragen können Löschungen und andere Änderungen rückgängig machen. Der vorhandene bedingte S3-Schreibzugriff schützt diesen Ablauf nicht.

**Abhilfe:** Die beim Lesen erhaltene Revision mit genau diesem Objekt/Arbeitsvorgang verbinden und ausdrücklich als erwartete Revision zurückgeben. Konflikte erkennen und fachlich neu verarbeiten; für Löschungen zusätzlich eine Sperrversion vorsehen. Ein lokaler Prozess-Lock allein löst den Betrieb mit mehreren Prozessen nicht.

**Sicherheit:** Hoch für die deterministisch nachgestellte Verschachtelung mit Moto; kein Lasttest gegen reales S3.

### F04 · P1 — Die Belegpflicht gilt nicht für sämtliche angezeigten Modelltexte

**Fundstellen:** `jusperfect/services/entwuerfe.py:79`; `jusperfect/services/analyse.py:222`, `:350`, `:361`; `jusperfect/services/belegpflicht.py:63`. **Gegenproben:** `test_01`, `test_02`, `test_14`.

Ein vollständig unbelegter Entwurf kommt mit HTTP 201 und leerer Quellenliste zurück: `zitate_aufloesen` ersetzt keine Fail-closed-Prüfung. Auch die Kernaussage und empfohlenen Schritte der Triage sowie modellgenerierte Analysehinweise können unbelegte Behauptungen enthalten. Das Wort „Hinweis“ macht einen vom Modell gelieferten Sachverhalt nicht automatisch zu einem ungefährlichen Systemhinweis.

Zusätzlich betrachtet `aussage_fail_closed` den gesamten Text seit dem vorherigen Quellenmarker als einen Block. Ein unbelegter Absatz, gefolgt von einem getrennten belegten Absatz, wird vollständig angenommen, ohne eine verworfene Aussage zu zählen. Das ist eine syntaktische Reichweitenlücke, zusätzlich zur bereits bekannten fehlenden semantischen Prüfung der Quelle.

**Schaden:** Unbelegte Aussagen gelangen als reguläres Ergebnis zum Bearbeiter und können in einen freigegebenen Entwurf übernommen werden.

**Abhilfe:** Eine gemeinsame Ausgabeprüfung für alle modellgenerierten Faktenfelder; technische Systemhinweise getrennt erzeugen. Aussagen als strukturierte Einheiten mit jeweils eigenen Quellen behandeln. Quellennachweis weiterhin nicht mit inhaltlicher Wahrheit gleichsetzen.

**Sicherheit:** Hoch; drei unabhängige Wege reproduziert.

### F05 · P1 — Streaming zeigt Rohtext vor der Belegprüfung

**Fundstellen:** `jusperfect/services/analyse.py:128`, `:133`; `jusperfect/web.py:671`; `jusperfect/static/app.js:2506`. **Gegenprobe:** `test_03`.

Der Stream liefert zunächst den unbelegten Marker als `text`-Ereignis. Erst das abschließende `fertig`-Ereignis enthält die bereinigte Antwort. Der Browser schreibt jedes frühe Ereignis sofort mit `strom.textContent = roh` in die Oberfläche.

**Schaden:** Der Bearbeiter kann eine Aussage sehen und kopieren, die der Abschlussfilter später ausdrücklich zurückhält. Bei langsamer Übertragung bleibt sie entsprechend lange sichtbar. Die bestehende Bereinigung bei einem Streamfehler ist vorhanden; beanstandet wird hier die reguläre vorherige Anzeige, nicht ein behaupteter dauerhafter Rest nach Abbruch.

**Abhilfe:** Erst geprüfte Aussageeinheiten oder die vollständig geprüfte Antwort senden. Bis dahin nur Fortschritt anzeigen. Eine Warnmarkierung wäre eine bewusste Abschwächung der zugesagten Regel „entfernen, nicht zeigen“.

**Sicherheit:** Hoch für API und UI-Codepfad; kein separater Browserlauf.

### F06 · P1 — Der bestätigte Prüfsummenstand umfasst den Betreff nicht

**Fundstellen:** `jusperfect/web.py:911`; `jusperfect/services/entwuerfe.py:125–130`. **Gegenprobe:** `test_05`.

Fenster A lädt Entwurf und Textprüfsumme. Fenster B ändert nur den Betreff. Fenster A bestätigt mit der alten Prüfsumme. Der Server akzeptiert die Freigabe, ergänzt den **neuen, dort ungesehenen Betreff** im Vermerktext und schreibt ihn auch in den Titel nach jur|nodes.

**Schaden:** Nicht vollständig angezeigter Inhalt wird zurückgeschrieben. Die HMAC-Kryptografie ist dabei nicht gebrochen: Sie signiert erst nach dem lückenhaften Abgleich den aktuellen Gesamttext.

**Abhilfe:** Eine kanonische, versionierte Freigabevorlage über sämtliche tatsächlich geschriebenen Felder bilden, insbesondere Betreff, Text, Zielakte und Vorgangsart. Bei jeder Änderung eine neue Ansicht/Bestätigung verlangen; Prüfung und Statuswechsel atomar gestalten.

**Sicherheit:** Hoch; Schreiben im Fixture-Adapter reproduziert, keine echte Akte verändert.

### F07 · P1 — Entwürfe bleiben nach Aktenrechteentzug lesbar und schreibbar

**Fundstellen:** `jusperfect/services/entwuerfe.py:95–99`, `:111`; `jusperfect/web.py:851–865`. **Gegenprobe:** `test_06`.

Ein zunächst berechtigter Nutzer erzeugt einen Entwurf. Anschließend verliert er die Aktenberechtigung, bleibt jedoch eingetragener Nutzer. Der Sitzungszugriff liefert korrekt 403. Das Lesen und Freigeben des bestehenden Entwurfs liefert weiterhin 200 und schreibt einen Vermerk. `lesen` prüft lediglich die Erstellerkennung.

**Schaden:** Rechteänderungen wirken nicht auf den bereits vorbereiteten Schreibpfad. Das ist nicht die ausdrücklich gewollte Kanzleiregel „alle sehen alle Akten“, sondern eine Lücke für den vorhandenen eingeschränkten Berechtigungsbetrieb.

**Abhilfe:** Aktuelle Aktenberechtigung bei jedem Entwurfszugriff und unmittelbar vor dem Zurückschreiben prüfen; offene Entwürfe bei Entzug unzugänglich machen.

**Sicherheit:** Hoch im aktivierten Berechtigungsmodell; bei dauerhaft allgemeinen Aktenrechten tritt dieser konkrete Auslöser nicht ein.

### F08 · P1 — Eine erkennbar fremde `/record`-Antwort wird als eigene Dokumentliste verwendet

**Fundstellen:** `jusperfect/jurnodes/http_adapter.py:518–534`, `:640`, `:202`, `:733–739`. **Gegenprobe:** `test_07`.

Der Client fragt `EIGENE-AKTE` ab. Die simulierte Antwort enthält ausdrücklich `identifier: FREMDE-AKTE` und deren `fileFolderId`. `_roh_akte` prüft die Identität nicht. Die Ordnerdatei wird geladen; `dokument_aus_json` trägt dabei die angefragte eigene Akte ein. Die spätere Prüfung gegen diese bereits falsch zugeordnete Liste erkennt den Fehler nicht.

**Schaden:** Eine unpassende oder fehlerhaft zugeordnete Serverantwort kann fremden Inhalt in den eigenen Kontext bringen. Hier wird der normale `fileFolderId` benutzt, nicht der bereits deaktivierte Korrespondenzordner.

**Abhilfe:** Zurückgegebene Aktenidentität strikt mit der angefragten vergleichen und bei Abweichung abbrechen. Dokumentzugehörigkeit gegen belastbare Herstellerfelder prüfen, soweit die API diese liefert. Ein Server, der eine falsche Zugehörigkeit konsistent als richtig ausgibt, lässt sich damit allein nicht entlarven.

**Sicherheit:** Hoch für die fehlende Clientprüfung; kein Beleg, dass der Produktivserver diese konkrete falsche Hauptordnerantwort bereits geliefert hat.

### F09 · P1 — Einfache Datums- und Sprachvarianten umgehen die Fristensperre

**Fundstellen:** `jusperfect/services/fristen.py:45`, `:55`, `:216`. **Gegenprobe:** `test_10`, dreifach parametrisiert.

Die einzige Quellpassage nennt einen Zugang am 05.05.2026. Alle folgenden Ausgaben bleiben unverändert, mit Zähler null:

- „Die Klagefrist endet am 26.05.26 [Q: D1-S1-P1].“
- „Die Klagefrist endet am 26. Mai [Q: D1-S1-P1].“
- „Die Klage muss bis zum 26.05.2026 eingereicht werden [Q: D1-S1-P1].“

Die ersten beiden Varianten entgehen dem Datumsmuster; die dritte dem Fristwortmuster. Die Quellenkennung ist gültig, das behauptete Enddatum steht aber nicht in der Quelle.

**Schaden:** Ein vom Modell abgeleiteter oder erfundener Endtermin kann als reguläre Antwort erscheinen. Die Absolutaussage „nie berechnet“ ist durch die Musterprüfung nicht gedeckt.

**Abhilfe:** Fristenauslöser, wörtlich vorgegebene Termine und Berechnungen strukturell unterscheiden. Angezeigte Endtermine müssen aus einer expliziten Kalender- oder Dokumentstelle stammen. Größere Wortlisten verbessern einzelne Fälle, können die Garantie über beliebige natürliche Sprache aber nicht herstellen.

**Sicherheit:** Hoch für die drei Filterumgehungen; keine Aussage über Häufigkeiten realer Modellantworten.

### F10 · P2 — Fehlgeschlagene Modellaufrufe hinterlassen keinen Verarbeitungsnachweis

**Fundstellen:** `jusperfect/services/ausgang.py:74–76`, `:90–98`, `:107`. **Gegenprobe:** `test_08`.

Der simulierte Anbieter empfängt Material und wirft anschließend einen Fehler. Die API liefert 502; der Nutzungsnachweis bleibt leer. Er wird erst in `_abschluss` nach erfolgreicher Antwort erzeugt. Auch ein vor Abschluss abgebrochener Stream hat diesen strukturellen Schwachpunkt.

**Schaden:** Übermittlungen können stattgefunden haben, obwohl das Nachweisfenster keine Zeile enthält. Kosten und Übermittlung sind im Fehlerfall nicht gleichbedeutend mit null.

**Abhilfe:** Vor Übergabe an den Anbieter einen inhaltsfreien Versuchsnachweis dauerhaft anlegen. Danach Erfolg, Ablehnung, Abbruch oder unbekannten Abschluss ergänzen. Eine fehlende Anbieterabrechnung als unbekannt ausweisen.

**Sicherheit:** Hoch für den simulierten Fehler nach Materialübergabe. Direkte Diagnoseaufrufe mit synthetischem Material sind zusätzlich als bewusste Ausnahme von „ein einziger Ausgang“ zu dokumentieren.

### F11 · P2 — Dateinamen und Aktenzeichen gelangen über das Material zum Modell

**Fundstellen:** `jusperfect/services/prompts.py:46`, `:67`; `jusperfect/jurnodes/http_adapter.py:198–206`. **Gegenprobe:** `test_09`.

Der HTTP-Adapter übernimmt `fileName` als Dokumenttitel, wenn kein anderer Titel vorliegt. `material_bauen` schreibt diesen Titel in die Passagenüberschrift. Ein Testdateiname erscheint dadurch unverändert im Modellmaterial. Das Aktenzeichen wird bereits in der ersten Materialzeile ausdrücklich eingefügt.

**Schaden:** Die Zusage „keine Dateinamen“ und die weitergehende DSFA-Aussage „keine Aktenzeichen“ sind falsch. Dass dem Provider keine gesonderten Metadatenobjekte übergeben werden, verhindert ihre Einbettung als Text nicht.

**Abhilfe:** Externe Titel durch neutrale lokale Dokumentbezeichnungen ersetzen oder den tatsächlich gewollten Metadatenumfang ausdrücklich freigeben und korrekt dokumentieren. Eine solche Änderung anonymisiert nicht den eigentlichen Dokumenttext; darin können weiterhin Namen und Kennungen stehen.

**Sicherheit:** Hoch; reale Adapterkonvertierung und Materialfunktion mit erfundenen Daten geprüft. Die Aussage betrifft diese nachgewiesenen Kennungsarten, nicht pauschal jede Nutzer-/Sitzungskennung.

### F12 · P1 — Textracts zugesicherte Nicht-Speicherung ist technisch nicht nachgewiesen

**Fundstellen:** `DSFA-ENTWURF.md`, Abschnitt 2.1 und R6; `VERARBEITUNGSVERZEICHNIS-ENTWURF.md`, Abschnitt 7.1; `jusperfect/ocr/textract.py:120`. **Nachweisart:** Quelltext-/Dokumentationsabgleich, kein Kontotest.

Die Unterlagen schließen aus dem synchronen Versand von Bildbytes ohne eigenen S3-Zwischenspeicher, dass AWS die Bilder nicht speichere. Dieser Schluss trägt nicht. AWS beschreibt für Textract mögliche Speicherung und Nutzung zur Verbesserung des Dienstes und weiterer KI-Technologien, einschließlich möglicher Speicherung von Teilen der Inhalte in einer anderen Region, sofern kein entsprechendes Opt-out besteht. Die FAQ nennt auch einen Löschweg über AWS Support. [AWS Textract FAQ, Abschnitt Data Privacy](https://aws.amazon.com/textract/faqs/).

**Schaden:** Die Datenspeicher-, Trainings- und Regionsbewertung kann für gescannte Mandatsunterlagen falsch sein. Das Bedrock-Versprechen darf nicht ungeprüft auf Textract übertragen werden.

**Abhilfe:** Wirksame AI-Services-Opt-out-Richtlinie für das konkrete AWS-Konto und die anwendbaren Vertragsbedingungen dokumentieren; einen bloß erstellten Organisationsentwurf nicht mit der effektiven Richtlinie verwechseln. Ohne diesen Nachweis ist „nicht gespeichert“ nicht abgesichert. Bei einer vorläufigen Abschaltung lautet der unterstützte Wert **`JUSPERFECT_OCR=keine`**, nicht das in R6 genannte `aus` (`config.py:438`). [AWS Organizations: AI services opt-out policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_ai-opt-out.html).

**Sicherheit:** Hoch für den unzulässigen technischen Schluss. **Unbekannt**, ob das reale Konto bereits wirksam ausgenommen ist; aus dem fehlenden Paketnachweis folgt nicht, dass dort tatsächlich kein Opt-out besteht.

### F13 · P2 — Eine EU-Aufrufregion verhindert kein ausdrücklich konfiguriertes globales Modellprofil

**Fundstellen:** `jusperfect/config.py:147–160`, `:472`; `infra/iam-nur-claude.json`. **Gegenprobe:** `test_11`.

Eine Konfiguration mit HTTP-Aktenadapter, Bedrock, Schutzgeländer, Frankfurt und `global.anthropic.claude-opus-4-6-v1` passiert die Einstellungsprüfung. `_modellkennung` lässt explizite Profile/ARNs unverändert; die EU-Prüfung kontrolliert die Clientregion, nicht die Profilziele.

**Schaden:** Die Anwendungsprüfung alleine erzwingt die beschriebene EU-Grenze nicht. Bei einem weiter berechtigten AWS-Prinzipal wäre die Regionszusage damit nicht abgesichert.

**Wichtige Begrenzung:** Die **mitgelieferte** IAM-Datei enthält bereits ausdrücklich die sechs EU-Regionen und ein Verbot anderer Modellressourcen. Wenn sie tatsächlich wirksam am Programmbenutzer hängt, sollte sie diesen Modellaufruf verhindern. Kein globaler Aufruf wurde ausgeführt; der Befund behauptet keinen nachgewiesenen globalen Abfluss und keinen vollständig erfolgreichen produktiven Start mit diesem Profil.

**Abhilfe:** Auch die Anwendung auf freigegebene konkrete Modell-/Profilkennungen beschränken, einschließlich Klein- und Gedächtnismodell. Profilziele und wirksame Kontorichtlinien als eigene Nachweise führen.

**Sicherheit:** Hoch für die akzeptierte Einstellung, kontobedingt hinsichtlich weiterer Wirkung.

## Antworten auf die fünf offenen Fragen

### 1 · E-Akte und `/record/note`

Ich habe **keine verifizierte eigene Produkterfahrung**, die einen E-Akten-Pfad oder die Bedeutung dieser numerischen `id` belegt. Die öffentliche Herstellerseite bestätigt eine API und verweist für deren Beschreibung auf den jeweiligen Server. Sie dokumentiert an dieser Stelle weder den gesuchten E-Akten-Leseweg noch den Parametervertrag von `/record/note`. [jur|nodes: Schnittstellen](https://www.jur-nodes.de/funktionen/schnittstellen), abgerufen am 05.10.2026.

Aus „cannot be parsed into number“ lässt sich lediglich ableiten, dass eine Zahl erwartet wird; nicht, ob es die interne Akten-, Vermerk- oder eine andere ID ist. Ebenso belegen die beobachteten 404/405 allein nicht, dass die E-Akte grundsätzlich unerreichbar ist. Ich schlage **keinen geratenen Pfad** vor.

Die Herstelleranfrage sollte ein vollständiges, anonymisiertes Beispiel für **Lesen**, HTTP-Methode, Query-/Body-Schema, ID-Herkunft, Pagination und verlässliche Aktenzuordnung verlangen. Bis dahin den bereits deaktivierten Korrespondenzordner nicht auf Verdacht wieder einbeziehen.

### 2 · Regionen von Modell- und Guardrail-Profilen

**Quelle: am 05.10.2026 abgerufene AWS-Primärdokumentation, keine Regionsliste aus dem Gedächtnis.** Maßgeblich ist jeweils die Zeile für die **Quellregion Frankfurt (`eu-central-1`)**.

| Profil | In AWS dokumentierte Zielregionen aus Frankfurt |
|---|---|
| `eu.anthropic.claude-opus-4-6-v1` | Frankfurt `eu-central-1`; Irland `eu-west-1`; Paris `eu-west-3`; Mailand `eu-south-1`; Spanien `eu-south-2`; Stockholm `eu-north-1` |
| `eu.anthropic.claude-haiku-4-5-20251001-v1:0` | dieselben sechs Regionen |
| `eu.guardrail.v1:0` | dieselben sechs Regionen |

Die Modellangaben folgen den jeweiligen AWS-Modellkarten: [Claude Opus 4.6](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-opus-4-6.html), [Claude Haiku 4.5](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html). Die Schutzgeländerangabe folgt der eigenständigen [AWS-Tabelle für regionsübergreifende Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-cross-region-support.html).

**Zürich (`eu-central-2`) und London (`eu-west-2`) stehen in diesen drei Frankfurt-Zielmengen nicht.** Das ist keine allgemeine Eigenschaft des Namensvorsatzes `eu.`: In den AWS-Tabellen unterscheiden sich die Mengen nach Quellregion. Die Opus-Tabelle nennt beispielsweise für einen Aufruf aus Zürich beziehungsweise London auch diese Quellregion als Ziel. Deshalb Modell und Quelle ausdrücklich in der Unterlage nennen.

`START-JURNODES.bat:182–184` enthält drei Modellkonfigurationen, aber nur **zwei unterschiedliche Kennungen**: Opus für Haupt- und Gedächtnismodell, Haiku für das kleine Modell. Falls die produktive Umgebung davon abweicht, müssen deren konkrete Kennungen separat geprüft werden. Eine pauschale Bescheinigung für alle Claude-Modelle wäre nicht belastbar.

Für den Kontonachweis sollte zusätzlich `GetInferenceProfile` aus Frankfurt je tatsächlicher Modellkennung abgefragt und die zurückgegebene Liste `models[].modelArn` datiert abgelegt werden. AWS dokumentiert dieses Verfahren in [Supported Regions and models for inference profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html). Ich habe diese Abfrage nicht mit Kanzleizugangsdaten ausgeführt.

Die Unterlagen sind auch beim IAM-Stand auseinandergefallen: Die Paketdatei verwendet bereits konkrete Regionen; DSFA und VVT sprechen noch von einer unveränderten `eu-*`-Richtlinie. Außerdem erfordert Cross-Region-Inferenz Berechtigungen für die Zielressourcen; die pauschale Aussage, Richtlinien beträfen nur den ursprünglichen Endpunkt, ist zu weitgehend. Eine Sperre kann den ganzen Aufruf scheitern lassen, statt die Route auf eine beliebige gewünschte Teilmenge zu reduzieren. [AWS: Geographic cross-Region inference](https://docs.aws.amazon.com/bedrock/latest/userguide/geographic-cross-region-inference.html).

Dies ist der dokumentierte öffentliche Stand, kein Nachweis der konkreten Kontoausführung und kein Ersatz für die erbetene AWS-Auskunft. Er deckt auch die eigenständige Textract-Frage F12 nicht ab.

### 3 · Die vier Entwurfsentscheidungen

**3a — Entfernen statt markieren:** Für modellgenerierte Tatsachenbehauptungen im Mandatskontext halte ich Entfernen für die richtige Voreinstellung. Der Bearbeiter sollte sehen, **dass und wie viel** zurückgehalten wurde, ohne dass unbelegter Rohtext über Streaming wieder in die Arbeitsoberfläche gelangt. Verweigerungen und vom Programm erzeugte Bedienhinweise brauchen keine Aktenfundstelle. Allgemeine rechtliche Erwägungen benötigen einen ausdrücklich getrennten Quellen- und Prüfmaßstab. Eine gültige Quellenkennung beweist weiterhin nicht die inhaltliche Tragfähigkeit.

**3b — Gemischte Einträge vollständig verwerfen:** Richtig, solange keine feinere Abhängigkeitsstruktur vorliegt. Eine halb erhaltene Quellenliste legitimiert keine ganze Aussage. Die Umsetzung muss aber auch Lebenssachverhalt und gespeicherte Analyse erfassen; genau dort scheitert der aktuelle Stand, siehe F02. Neuaufbau aus den verbliebenen Quellen ist eine vertretbare Alternative zum ersatzlosen Entfernen.

**3c — Vorauswahl ohne Inhaltsdeutung:** Zuverlässiger wird sie durch bestätigte strukturierte Herstellermerkmale: Dokumentart, Vorgangskategorie, explizite Kennzeichnung durch den Bearbeiter oder einen nachweislich aktenrichtigen Ablagebereich. Fehlen diese Merkmale, gibt es keine zuverlässige inhaltsfreie Erkennung einer beliebig benannten Rechnung. Dann ist die Titelregel lediglich eine Hilfe. Unbekannte Kategorien unmarkiert lassen, Auswahlgrund anzeigen und die endgültige Aufnahme bestätigen lassen. Den als unzuverlässig bekannten Korrespondenzordner nicht als Ersatzklassifikation verwenden.

**3d — Kennungen oder Prüfsummen:** Bei wiederverwendeten Analysen reicht die Kennung alleine nicht. Beim Einlesen Rohdatei-Hash, Extraktionsversion und möglichst verlässliche Herstellerrevision/Änderungszeit speichern. Die Analyse an die genaue Menge der Dokumentrevisionen und an relevante Verarbeitungs-/Modellkonfiguration binden. Metadaten können Nachladen vermeiden, falls ihre Änderungssemantik zugesichert ist; sonst erkennt nur ein erneuter Inhaltsvergleich eine Änderung bei gleicher ID. Ohne erneute Prüfung sollte die Oberfläche „Stand vom …; Änderungen nicht geprüft“ statt Aktualität behaupten. Hashwerte bei Mandatsdaten weiterhin geschützt behandeln.

### 4 · Rechtsdokumentation

Die offene rechtliche Bewertung ist als solche kein Befund. Problematisch sind technische Tatsachen, die bereits als gesichert dargestellt werden.

#### Fehlende oder zu wenig ausgearbeitete Risikoszenarien

- **Löschungsreste und Wiederherstellung:** gespeicherte Analyse, aktive Sitzungen, konkurrierende Schreibvorgänge, gegebenenfalls Backups. R3/R8 nennen Löschung, decken ihre tatsächliche Durchsetzung aber nicht ab.
- **Inhalt in Fehlerlogs und lokalen Nebenablagen:** R4/R8 betrachten hauptsächlich den vorgesehenen Nachweis; Server-/Bibliotheksfehler brauchen ein eigenes Szenario. Für temporäre Dateien, Betriebssystem-Sicherungen und Absturzabbilder fehlen belastbare Betriebsangaben; hier wurde keine konkrete Exfiltration nachgewiesen.
- **Manipulierte Dokumente und dauerhafte Fehlannahmen:** Nicht nur Benutzereingaben können Anweisungen enthalten. In Dokumenten eingeschleuste Anweisungen und fehlerhafte OCR können über den Lebenssachverhalt wiederholt in spätere Antworten eingehen. Quellenverweise schließen diesen Mechanismus nicht aus.
- **Veraltete Ergebnisse und parallele Bearbeitung:** geänderte Dateien mit gleicher ID, Freigabe nach einer Änderung, überschriebenes Gedächtnis.
- **Ausfall und Wiederherstellbarkeit:** verlorener KMS-Zugang, beschädigte zweite Fallkopie, nicht erkennbare Teilfehler; maßgeblich ist auch ein möglicher Nachteil für die rechtzeitige Mandatsbearbeitung.
- **Unvollständiger Widerrufsprozess:** Freiwilliges Nichtbenutzen ist keine technische Aktensperre. Alte Sitzungen, laufende Anfragen und Wiedereinlesen müssen zur gewählten organisatorischen Regel passen.
- **Textract-Serviceverbesserung und weitere Speicherung:** F12 gehört eigenständig in R6 und die Datenflussbeschreibung.

Das sind Erweiterungen beziehungsweise Konkretisierungen der vorhandenen acht Risiken, keine Behauptung, sämtliche Szenarien seien bereits eingetreten.

#### Zu optimistisch dargestellte Maßnahmen

| Dokumentbehauptung | Bewertung anhand des Pakets |
|---|---|
| „Kein Akteninhalt im Protokoll“, technisch erzwungen | Nur für den eigenen kontrollierten Logger; F01 widerlegt die umfassende Aussage. |
| Jede unbelegte Aussage wird entfernt | F04/F05 zeigen ausgenommene Felder und vorherige Rohtextanzeige. |
| Fristen werden nie berechnet | F09 zeigt nicht zurückgehaltene Endtermine. |
| Gezielte Löschung entfernt alles Abgeleitete | F02/F03 widerlegen Vollständigkeit und Beständigkeit. |
| Freigabe entspricht genau der gesehenen Fassung | Betreff fehlt im bestätigten Stand, F06; Rechteentzug wird nicht erneut geprüft, F07. |
| Jeder Modellaufruf hinterlässt eine Zeile | Erst bei erfolgreichem Abschluss, F10. |
| Keine Dateinamen/Aktenzeichen beim Modell | Über Textmaterial doch vorhanden, F11. |
| Nur Frage und Antwort im Guardrail, also kein Akteninhalt | Die Folgerung ist falsch: Fragen/Antworten können Mandatsinhalt enthalten. Zudem umfasst der Aufgabenkanal bei Gedächtnisverarbeitung bisherigen Fallkontext; `bedrock.py:203` markiert diesen Kanal als `guardContent`. |
| Textract verarbeitet, speichert aber nicht | Durch Verwendung von Bytes nicht belegbar, F12. |
| EU-Clientregion und Präfix garantieren die Region | Konkrete Profile, Ausgangsregion und wirksame Richtlinien erforderlich, F13 und Antwort 2. |

Auch „kein Abfluss nach außen“, begründet allein mit eigenem AWS-Konto und demselben Auftragsverarbeiter, sollte entfallen: Technisch wurde Inhalt an AWS übertragen und für eine andere Mandatsbearbeitung verwendet. Die bereits ausdrücklich offengelassene Bewertung nach Art. 4 Nr. 12 und Art. 33 darf dieser Satz nicht vorwegnehmen. Daraus folgt hier keine eigenständige rechtliche Feststellung eines meldepflichtigen Vorfalls.

Die Dokumente widersprechen sich außerdem beim IAM-Stand, bei der Kostenbegrenzung und bei der Testzahl. Eine einheitliche Fassung sollte tatsächliche Konfiguration, gemessenen Nachweis und offene Bewertung getrennt nennen. „Nur Frankfurt“ ist auch bei den dokumentierten EU-Modellprofilen zu eng.

#### Angaben nach Art. 30 und 35

**Art. 30:** Die wesentlichen Rubriken sind angelegt. Ergänzungsbedürftig sind die konkreten Verantwortlichen-/DSB-Kontaktdaten und gegebenenfalls weitere Verantwortlichkeitsangaben, die tatsächlichen Empfänger-/Regionsangaben sowie Löschfristen nach Datenkategorie. Insbesondere enthält der Verarbeitungsnachweis Nutzer- und Aktenbezug; „inhaltsfrei“ ersetzt keine Entscheidung über dessen Aufbewahrung. Speicherfristen sollten Fallkopie, Sitzungen, Entwürfe und Nachweise auseinanderhalten. [DSGVO, Art. 30, EUR-Lex](https://eur-lex.europa.eu/legal-content/DE/ALL/?tid=111387962&uri=celex%3A32016R0679).

**Art. 35:** Notwendigkeit/Verhältnismäßigkeit, Risiken und Abhilfen sind strukturell vorhanden, die bewertete DSFA aber noch nicht abgeschlossen. Erforderlich sind belastbare Datenflüsse, bewertete Auswirkungen und Eintrittswahrscheinlichkeiten, Wirksamkeit der Maßnahmen und verbleibende Risiken. Die DSB-Beteiligung ist bereits als offen benannt. Zusätzlich sollte die gegebenenfalls erforderliche Einholung des Standpunkts Betroffener nach Abs. 9 behandelt werden. Auslöser und Verantwortung der erneuten Prüfung konkretisieren. [Sächsische Datenschutzaufsicht: Zeitpunkt und Durchführung einer DSFA](https://www.datenschutz.sachsen.de/zeitpunkt-und-durchfuehrung.html).

Die Mandantenhinweise sind ausdrücklich nur ein Ergänzungsbaustein; fehlende allgemeine Art.-13-Pflichtangaben im Baustein allein belegen daher keinen Mangel der gesamten Kanzleihinweise. Ob und wie Nichtmandanten informiert werden müssen, ist gesondert durch die Kanzlei einzuordnen.

#### Welche Platzhalter sind technische beziehungsweise tatsächliche Fragen?

| Stelle | Sinnvolle Aufteilung |
|---|---|
| DSFA **KANZLEI 11** — Profilregionen | Technische Tatsachenermittlung durch Entwicklung/Administration mit AWS-Belegen; rechtliche Bewertung etwaiger Drittlandbezüge anschließend durch die Kanzlei. |
| DSFA **KANZLEI 4** — lokales Modell | Entwicklung liefert Hardwarebedarf, Laufzeit und gemessene Qualität an repräsentativen erfundenen/zulässig verwendeten Fällen. „Erheblicher Qualitätsverlust“ ohne Vergleichsmessung ist kein ausreichender Nachweis. Die Verhältnismäßigkeit bleibt rechtlich/organisatorisch. |
| DSFA **KANZLEI 7** — Löschung | Zulässige Fristen entscheidet die Kanzlei. Tatsächliche Auslöser, Statusmapping, erfasste Speicherorte und erfolgreiche Durchführung muss die Entwicklung nachweisen. |
| DSFA **KANZLEI 8** — Vertragsdatum/-fassung/-ablage | Tatsachenbeschaffung durch Vertragsinhaber/Administration, nicht an sich eine Rechtsfrage. Die Entwicklung kann unbekannte Kanzleiverträge aber nicht erfinden. |
| Datenschutzhinweise **KANZLEI 2** — Drittlandangaben | Zuerst dokumentierte technische Empfänger-/Regionstatsachen einschließlich Textract, danach rechtliche Einordnung. |
| Datenschutzhinweise **KANZLEI 6** — Widerruf | Die Entwicklung muss Löschung, Sperrung und laufende Verarbeitung tatsächlich beschreiben und testen; die rechtliche Angemessenheit bleibt offen. |

Die übrigen zentralen Entscheidungen — Rechtsgrundlagen, Geheimnisschutz, Risikobewertung, Umfang, Dienstleisterauswahl und Konsultation — sind zu Recht bei der Kanzlei. Die Entwicklung kann Tatsachen und Messungen liefern, diese Entscheidungen aber nicht allein treffen.

### 5 · Was als Nächstes bauen?

**Zuerst die nachgewiesenen Schutzlücken schließen.** Die offenen E-Akten-Funktionen und weitere Anbieter sind nachrangig, solange vorhandene Zusagen auf Fehlerpfaden nicht halten. `MORGEN.md` sollte insbesondere die als erledigt bezeichnete gezielte Löschung wieder aufnehmen und die überholte Reihenfolge am Dateiende ersetzen.

Als nächste zusammenhängende Erweiterung würde ich eine **versionierte Quellen- und Ergebnisverwaltung** bauen: Jede Dokumentfassung erhält eine Revision; jede Aussage/Analyse kennt ihre zugrunde liegenden Fassungen; jede Freigabe bestätigt genau einen vollständigen Stand. Löschung oder Änderung macht davon abhängige Ergebnisse und laufende Sitzungen ungültig. Damit werden die Probleme aus F02, F03, F06 und Frage 3d gemeinsam adressierbar.

Eine sinnvolle Arbeitsfolge ist:

1. Fehlerlogs abdichten; Textract-Opt-out und Aussagen zur Speicherung belegen; bis zur Klärung keine gesicherte Nicht-Speicherung behaupten.
2. Vollständige und beständige Löschung, revisionsgebundene S3-Schreibvorgänge, vollständige Freigabeprüfung und erneute Aktenrechteprüfung.
3. Einheitliche Ausgabeprüfung einschließlich Triage, Hinweise, Entwürfe und Stream; Fristentermine strukturell absichern.
4. Vorabnachweis jeder Übermittlung, Metadatenminimierung, strikte Prüfung zurückgegebener Aktenidentitäten und erlaubter Profile.
5. Die korrigierten Gegenproben als Regressionen behalten; Rechtsunterlagen aus dem nachgewiesenen Stand aktualisieren. Danach den vom Hersteller bestätigten E-Akten-Leseweg implementieren.

## Einordnung bewusster Entscheidungen

Deutsch im Quelltext, ausführliche historische Kommentare, deaktivierte pauschale Gewalt-/Sexualinhaltsfilter und eine bewusste Verweigerung bei fehlenden Belegen halte ich für diesen Anwendungsfall für nachvollziehbar. Die allgemeinen Aktenrechte sind als bewusste Betriebsregel zu bewerten, nicht als hier neu entdeckter Fehler.

Widersprechen würde ich dagegen der vorzeitigen Rohtextanzeige zugunsten des Schreibgefühls, der Gleichsetzung „gültige Fundstellenkennung = jeder vorangehende Satz belegt“, und der Behauptung, nur die Aufrufregion oder der Transport ohne S3 bewiesen die weitere Datenverarbeitung. Ebenso braucht die pauschale Verwerfung von Pseudonymisierung in DSFA 3.2 eine differenziertere technische Untersuchung: Manche Identifikatoren lassen sich für bestimmte Aufgaben ersetzen, ohne den ganzen Sachverhalt unbrauchbar zu machen. Eine universelle Lösung ist damit nicht behauptet.

## Reproduktion und Anlagen

Anlagen in diesem Verzeichnis:

- `test_gegenproben.py` — 17 offline ausführbare Gegenproben; im Dateikopf steht ausdrücklich, dass sie das Fehlverhalten bestätigen.
- `bestand-tests.log` — Ergebnis der vorhandenen Suite.
- `gegenproben.log` — Ergebnis der Gegenproben.
- `abhaengigkeiten.txt` — tatsächlich installierte Python-Abhängigkeiten einschließlich Prüfwerkzeugen.
- `pruefstand.json` — Umgebung, ZIP-Hash und Ergebnis des Originaldateivergleichs.
- `pruefstand.py` — wiederholbarer Hashvergleich und Export der Abhängigkeiten.

Ausführung in der hier bereits angelegten Umgebung, PowerShell aus dem Verzeichnis dieses Berichts:

```powershell
$env:AWS_EC2_METADATA_DISABLED = 'true'
$env:AWS_ACCESS_KEY_ID = 'testing'
$env:AWS_SECRET_ACCESS_KEY = 'testing'
$env:AWS_DEFAULT_REGION = 'eu-central-1'
Set-Location '.\jusperfect-pruefpaket-05.10.2026'
& '..\pruef-venv\Scripts\python.exe' -m pytest -q
& '..\pruef-venv\Scripts\python.exe' -m pytest -q '..\test_gegenproben.py'
```

Für einen anderen Rechner ist eine frische virtuelle Umgebung mit dem Paket `.[dev]` und zusätzlich `moto[s3,dynamodb]` erforderlich. Die Bibliotheksversionen der tatsächlich geprüften Umgebung stehen in der Anlage. Keine Produktivzugangsdaten für diese Tests einsetzen.

**Gesamturteil:** Die vorhandene Testbasis ist umfangreich und funktionsfähig. Sie belegt jedoch die umfassenden Sicherheitszusagen nicht. Die wichtigste nächste Verbesserung ist die prüfbare Durchsetzung dieser Zusagen über Fehlerpfade, Ableitungen und gleichzeitige Vorgänge hinweg.
