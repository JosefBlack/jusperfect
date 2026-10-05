# jusperfect – Konzept, Fassung 2 (AWS-Baukasten)

Planungsstand: 03.09.2026. Fassung 1 vom 02.09.2026 wurde geprüft; die Änderungen sind in
Abschnitt 10 zusammengefasst. Kanzlei mit 2 Anwälten und etwa 3 Mitarbeitern, jur|nodes als
Kanzleisoftware, AWS in Frankfurt.

**Empfehlung:** jur|nodes bleibt die führende Akte. jusperfect wird als kontrollierte KI-Schicht
aus AWS-Bausteinen ergänzt. Das optionale Aktengedächtnis hält im eigenen AWS-Konto eine
zweckgebundene Fallkopie zur kostengünstigen Wiederaufnahme; es wird erst nach Anpassung der
DSFA und Datenschutzunterlagen aktiviert. Start mit einem klar begrenzten,
lesenden MVP plus Entwurfsassistent mit Freigabe. Keine autonome Außenkommunikation.

## 1. Zielbild

jusperfect liest Akten aus jur|nodes bedarfsbezogen, analysiert Dokumente, erstellt
Chronologien und offene Punkte, prüft den Posteingang, erkennt Fristauslöser, bereitet Entwürfe
vor. Er ersetzt weder jur|nodes noch die anwaltliche Prüfung. Das optionale Aktengedächtnis
speichert ausschließlich die für jusperfect extrahierten Dokumenttexte und geprüften
Arbeitsprodukte, nicht die vollständige jur|nodes-Akte mit Fristen- und Verwaltungsdaten.

Kernfunktionen des MVP, in Reihenfolge des Alltagsnutzens:

1. Eingangsprüfung eines neuen Dokuments: Art, Absender, Kernaussage, Fristauslöser, nächste Schritte.
2. Akte öffnen und Dokumente laden, Frage an die Akte mit Belegen.
3. Aktenanalyse: Chronologie, Beteiligte, Forderungen, Beweismittel, offene Punkte, Widersprüche.
4. Entwürfe: RSV-Deckungsanfrage, Mandanten-, Gegner-, Versicherungsschreiben, Mahnung, Aktenvermerk.
5. Freigabe und Ablage als Vermerk in jur|nodes, nur durch den Bearbeiter, nur der angezeigte Text.

Bewusst nicht enthalten: E-Mail- oder beA-Versand, Fristenberechnung oder -änderung, Zahlungen,
autonomer Zugriff auf alle Kanzleiakten oder ein aktenübergreifendes Gedächtnis.

## 2. Zielarchitektur

| Schicht | Rolle | Grundsatz |
|---|---|---|
| jur|nodes | Akten, Dokumente, Beteiligte, Fristen, Vermerke | Single Source of Truth |
| Oberfläche (S3, CloudFront) | Statische Anwendung, Anmeldung über Cognito Hosted UI (PKCE) | keine Daten im Browser über die Sitzung hinaus |
| Cognito | Identität, MFA, Gruppe „alle-akten“ für Anwälte | nur vom Administrator angelegte Nutzer |
| API Gateway (HTTP API) | JWT-Prüfung vor der Funktion, CORS, Zugriffsprotokoll ohne Inhalte | kein Aufruf ohne gültiges Token |
| Lambda (Python) | Berechtigung, jur|nodes-Adapter, Extraktion, Passagen, Belege, Kostenwächter | zustandslos, 5 parallel |
| Bedrock Converse | Modell mit Guardrail auf Frage und Antwort, Prompt-Cache auf das Material | nur erforderliche Passagen |
| DynamoDB, S3 (KMS) | Sitzungen, Texte, Entwürfe, Nutzung; alles mit Ablauf | flüchtige Arbeitskopie |
| S3-Aktengedächtnis (KMS, optional) | extrahierte Texte, belegter Lebenssachverhalt, belegte Q&A | dauerhafte Fallkopie im Kanzleikonto, löschbar |
| Textract | OCR für Scans, Zwischendatei sofort gelöscht | Scans sind Kernfall im Posteingang |
| Secrets Manager, KMS | jur|nodes-Token, Schlüssel für alle Ablagen | keine Zugangsdaten im Code |
| Budgets, CloudWatch, SNS | Kostenalarme 50/80/100 %, Prognose, Fehleralarm | zweite Bremse neben dem Kostenwächter |
| Knowledge Base (Phase 2) | Kanzleiwissen: Muster, Checklisten, veröffentlichte Entscheidungen | getrennt von Mandatsakten, lizenzrechtlich geprüft |

Datenfluss: Anmeldung -> Akte öffnen -> Berechtigung prüfen -> Dokumentliste aus jur|nodes ->
gewählte Dokumente laden -> Text extrahieren (OCR bei Bedarf) -> verschlüsselt und mit Ablauf
ablegen -> Passagen mit Kennungen -> Auswahl an Bedrock -> Antwort mit Belegen, maschinell
geprüft -> begrenzter Dialog aus geprüften Endfassungen und ihren Originalbelegen -> Anzeige mit
Fundstellen -> Sitzung schließen löscht Texte und Dialog. Write-back nur nach
ausdrücklicher Freigabe eines Entwurfs, gebunden an Text, Nutzer und Akte.

Nicht im MVP: Bedrock Flows, AgentCore, Step Functions. Sie kommen erst, wenn jusperfect über
Lesen und freigabepflichtige Vermerke hinaus Funktionen in jur|nodes ausführen soll (Phase 4).
Fünf Kernfunktionen sind als Code testbarer und billiger zu betreiben als als visuelle Flows.

## 3. Sicherheits- und Berufsgeheimnis-Konzept

Siehe [SICHERHEIT.md](SICHERHEIT.md). Kernpunkte:

- Region eu-central-1; andere Regionen sind in Konfiguration und IAM gesperrt. EU-Inferenzprofile
  verteilen auf EU-Regionen und werden so dokumentiert.
- Identität aus Cognito, Berechtigung je Akte, fremde Sitzungen unsichtbar.
- Texte 15 Minuten, Entwürfe 7 Tage, S3-Lebenszyklus 1 Tag, keine Versionierung.
- Keine Inhalte in Protokollen; Bedrock-Aufrufprotokollierung aus; CloudTrail an.
- Belegpflicht maschinell geprüft; Dokumente sind Material, keine Anweisungen.
- Fristen nur als Auslöser mit Beleg, nie als berechnetes Datum.
- Guardrail auf Frage und Antwort, nicht auf den Dokumenttext (Kosten, deutsche Texte).
- Rechtliches Paket in Phase 0: AWS-DPA, § 43e BRAO-Dokumentation, DSFA, Art.-13-Hinweise,
  Verarbeitungsverzeichnis, KI-Kompetenz nach Art. 4 KI-VO.

Klartext oder Pseudonymisierung: Dieses Konzept arbeitet im Klartext auf Grundlage von § 43e
BRAO mit dem beschriebenen Vertrags- und Dokumentationspaket. Eine Pseudonymisierungsstufe vor
dem Modell ist bewusst nicht Teil dieser Lösung; sie würde Chronologie und Sachverhaltsabgleich
deutlich verschlechtern. Die Entscheidung ist in der DSFA zu begründen.

## 4. Projektphasen

| Phase | Umfang | Abnahme |
|---|---|---|
| 0 – Grundlagen (2 Wochen) | jur|nodes-API-Test gegen die sechs Lesefunktionen und die Schreibfunktion; AWS-Konto, Modellzugang, Kontingente, Guardrail; Rechtspaket; Testakten | Akte suchen, Dokumentliste, Dokument laden, Vermerk schreiben funktionieren. Go/No-Go 1 |
| 1 – Lesender MVP (4–6 Wochen) | Eingangsprüfung, Frage, Analyse, Oberfläche, Berechtigungen, Prüfstand mit Testakten | keine dauerhafte Parallelakte; Belegquote im Prüfstand mindestens 95 % |
| 2 – Entwurfsassistent | RSV-Deckungsanfrage zuerst, dann Mandant, Versicherung, Mahnung, Aktenvermerk; Kanzleimuster als Vorbild; Knowledge Base für Kanzleiwissen | Write-back nur nach Freigabe |
| Pilot (6 Wochen) | drei Nutzer, feste Kennzahlen | Go/No-Go 2 |
| 3 – Fachmodule | Verkehrsunfall-Sachverhaltsabgleich, RSV, RVG-Hinweise, Schadenberechnung | deterministische Rechnung getrennt vom Modell; Lizenzfragen geklärt |
| 4 – Workflows | Wiedervorlagevorschläge, Aufgaben, kontrollierte Tool-Aktionen (AgentCore, Step Functions mit Freigabepunkten) | keine autonome Außenaktion; Prompt-Injection-Tests |

Plan B für Phase 0: Bietet jur|nodes keine brauchbare API, wird ein Exportordner oder eine
WebDAV-Ablage als Adapter angebunden. Der Rest der Lösung bleibt unverändert.

## 5. Kostenkalkulation

| Kostenblock | Ansatz | Bemerkung |
|---|---|---|
| Phase 0 | 1.500–2.500 EUR einmalig | API-Test, AWS-Einrichtung, Rechtspaket, Testakten |
| Phase 1 MVP | 4.000–7.000 EUR einmalig | fünf Funktionen, Oberfläche, Berechtigungen, Prüfstand |
| Phase 2 | 2.000–4.000 EUR einmalig | Entwürfe mit Freigabe, Kanzleiwissen |
| Fachmodule, Workflows | bis etwa 10.000–18.000 EUR gesamt | nur nach positivem Pilot |
| Betrieb | 50–100 EUR je Monat | Modellwechsel, Updates, Alarme; benannte verantwortliche Person oder Firma |
| AWS normal | 60–125 EUR je Monat | fünf Nutzer, mit Passagenauswahl, Prompt-Cache, kleinem Modell für Triage |
| AWS intensiv | 150–260 EUR je Monat | viele lange Akten mit dem großen Modell |

Feste AWS-Kosten (Lambda, API Gateway, DynamoDB, S3, KMS, Secrets Manager, CloudWatch,
CloudFront) etwa 10–20 EUR je Monat. Die Modellkosten sind die Hauptvariable; Überschlag für
fünf Nutzer und 20 Arbeitstage:

| Szenario | Annahme | Modellkosten je Monat |
|---|---|---|
| Moderat, Sonnet-Klasse | 5 Analysen und 10 Fragen je Nutzer und Tag, 20k Token je Aufruf | ca. 70 EUR |
| Moderat, Opus-Klasse | wie oben | ca. 175 EUR |
| Lange Akten, Opus | 3 Analysen je Nutzer und Tag mit 100k Token | 150–200 EUR zusätzlich |
| Mit Prompt-Cache | mehrere Fragen zur selben Akte | Eingabekosten grob auf ein Drittel |

Interne Grenze zum Start: 125 EUR je Monat, im Kostenwächter der Anwendung und als
AWS-Budget mit Alarmen bei 50, 80 und 100 Prozent. Die Anwendung sperrt KI-Aufrufe oberhalb
der Grenze selbst.

Guardrails werden je 1.000 Zeichen abgerechnet. Deshalb wirken sie auf Frage und Antwort,
nicht auf 200 Seiten Dokumenttext je Aufruf.

## 6. Wirtschaftlichkeit

| Ersparnis je Person und Tag | Kanzlei gesamt je Monat | Einordnung |
|---|---|---|
| 10 Minuten | ca. 16,7 Stunden | laufende Kosten gut vertretbar |
| 20 Minuten | ca. 33,3 Stunden | sehr guter Hebel |
| 30 Minuten | ca. 50 Stunden | hohe Wirtschaftlichkeit |

Ehrliche Vollkostenrechnung: 7.000 EUR Entwicklung über 24 Monate sind rund 290 EUR je
Monat, plus 100 EUR AWS und 75 EUR Betrieb, zusammen etwa 465 EUR. Bei 33 gesparten Stunden
sind das rund 14 EUR je Stunde. Die Zeitersparnis ist eine Annahme und wird im Pilot gemessen.

## 7. Messung im Pilot

- Zeit je Vorgang an zehn typischen Vorgängen vorher und nachher (Stoppuhr).
- Belegquote: Anteil der Belege, die bei Prüfung tatsächlich die Aussage stützen; Ziel mindestens 95 %.
- Korrekturquote je Entwurf: Anteil geänderter Sätze vor der Freigabe.
- Nutzung je Person und Woche; Bewertungen „brauchbar / korrigiert / unbrauchbar“ je Ergebnis.
- Kosten je Vorgang, angezeigt in der Oberfläche.

Prüfstand: zehn anonymisierte Testakten mit Soll-Chronologie und Soll-Beteiligten, Lauf bei
jeder Änderung an Prompt oder Modell.

## 8. Go/No-Go-Entscheidung

| Kriterium | Bewertung | Begründung |
|---|---|---|
| Technische Machbarkeit | GELB bis Phase 0 | AWS-Baukasten passt; die jur|nodes-API ist die einzige ungeprüfte Annahme |
| Laufende Kosten | GRÜN | überschaubar mit Kostenwächter, Budgetalarmen, Cache und Modellstaffelung |
| Entwicklungsrisiko | GELB-GRÜN | Managed Services; jur|nodes-Integration ist der Prüfpunkt, Plan B benannt |
| Datenschutz und Berufsgeheimnis | GELB-GRÜN | mit DPA, § 43e-Dokumentation, DSFA und den technischen Leitplanken gestaltbar |
| Kanzleinutzen | GRÜN | Posteingang, Aktenanalyse, RSV und Entwürfe treffen den Alltag |

Empfehlung: GO für Phase 0 mit Abbruchkriterium. Nach Phase 0 Entscheidung über Phase 1,
nach dem Pilot über den Ausbau.

## 9. Organisation

- Ein Produktverantwortlicher aus der Anwaltschaft; wöchentlich 30 Minuten Durchsicht.
- Ein Fehlerkasten für falsche oder unbelegte Ergebnisse; Auswertung im Wochentermin.
- Betrieb durch eine benannte Person oder Firma: Alarme, Updates, Modellwechsel, Kontingente.
- Der eigene Produktname „jusperfect“ (statt „Copilot“) vermeidet die Verwechslung mit Microsoft Copilot.

## 10. Änderungen gegenüber Fassung 1

1. Technische Machbarkeit auf GELB bis Phase 0; Abbruchkriterium und Plan B ohne API.
2. Rechtlicher Rahmen ergänzt: § 43e BRAO, DPA, DSFA, Art. 13, Verarbeitungsverzeichnis, KI-VO, Lizenzen für Kanzleiwissen.
3. Klartext-Entscheidung ausdrücklich getroffen und begründet.
4. Berechtigungen konstruiert: Cognito-Identität, Aktenliste je Nutzer, Gruppe für Anwälte, fremde Sitzungen unsichtbar.
5. Guardrail auf Frage und Antwort statt auf den Dokumenttext; Kosten aufgenommen.
6. OCR als Kernfunktion (Textract), nicht „nur bei Bedarf“.
7. Flows, AgentCore, Step Functions aus dem MVP gestrichen; Knowledge Base nach Phase 2.
8. Eingangsprüfung als erste Funktion, Sachverhaltsabgleich statt freier Widerspruchssuche in Phase 3.
9. Budget: Phase 0 getrennt ausgewiesen, Betrieb ergänzt, Alarme 50/80/100 %, Kostenwächter in der Anwendung, Cache und Modellstaffelung.
10. Messung und Prüfstand definiert, Zeitplan ergänzt, Organisation benannt.
