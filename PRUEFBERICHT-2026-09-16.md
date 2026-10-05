# Pruefbericht jusperfect

Stand: 16.09.2026. Repository JosefBlack/jusperfect-, Branch 2.0,
Commit 8c14a2b0c90070474f4943e8b9d15e514e0aa4c1.

## Testergebnisse

- Python 3.12.14, Windows, separate virtuelle Umgebung.
- Vollstaendige Sammlung nach lokaler Ergaenzung von pytest: 781 Tests bestanden,
  152 Untertests bestanden, keine uebersprungenen Tests gemeldet; Laufzeit 97,89 Sekunden.
- Zwei Abkuendigungswarnungen in Starlette/httpx und anyio; keine Testfehler.
- Funktionsprobe mit Demo-Anbieter: 34 von 34 bestanden, einschliesslich grosser Akte.
- JavaScript-Syntax: node --check jusperfect/static/app.js bestanden.
- AWS-Vorlage: cfn-lint infra/template.yaml bestanden.
- Die unten beschriebenen Gegenproben reproduzieren Luecken trotz gruener Bestandstests.

Die Testprotokolle liegen lokal vor und sind nicht Teil dieses Uploads:
jusperfect-pytest.log, jusperfect-funktionsprobe.log und jusperfect-tests.log
(letzteres dokumentiert den ersten Lauf mit fehlendem pytest).

## Reproduzierte Befunde

### 1. Hohe Prioritaet: Unbelegter Nachsatz passiert die Belegpflicht

Ort: jusperfect/services/belegpflicht.py:80.

Testquelle D1-S1-P1: "Der Vertrag wurde unterschrieben. Eine Besprechung fand am 26.05.2026 statt."
Antwort: "Der Vertrag wurde unterschrieben [Q: D1-S1-P1]. Der Gegner hat die Forderung voll anerkannt."
Ergebnis: Beide Saetze bleiben erhalten; verworfen = 0. Der zweite Satz hat keinen Beleg.
Ursache: Der gesamte Text nach dem letzten Quellenverweis wird unveraendert angehaengt.

Vorschlag: Aussagen einzeln an Quellen binden. Nach dem letzten Beleg nur Satzzeichen und
Leerraum zulassen; weitere Aussagen zurueckhalten. Regressionstests fuer Nachsaetze,
mehrere Absaetze und gemischte gueltige/ungueltige Belege ergaenzen.

### 2. Hohe Prioritaet: Fristensperre verwechselt Datumsvorkommen mit Fristbeleg

Ort: jusperfect/services/fristen.py:159.

Mit derselben Testquelle wird "Die Klagefrist endet am 26.05.2026 [Q: D1-S1-P1]."
unveraendert akzeptiert; Zahl entfernter Daten = 0. Die Quelle nennt nur eine Besprechung.
Ursache: Das Datum muss lediglich irgendwo im gesamten uebergebenen Aktenmaterial stehen.

Vorschlag: Fristende an einen passenden Fristenkalendereintrag oder eine konkrete,
inhaltlich passende Fristpassage binden. Ein beliebiges gleiches Datum darf nicht reichen.
Gegenproben mit Besprechungsdaten, Rechnungsdaten und mehreren verschiedenen Fristen aufnehmen.

### 3. Hohe Prioritaet: Unvollstaendiger Antwortstrom laesst Rohtext stehen

Ort: jusperfect/static/app.js:1617.

Die Originalfunktion frageStellen wurde in Node mit einer simulierten Oberflaeche und
einem Antwortstrom ausgefuehrt: ein text-Ereignis, danach Ende ohne fertig-Ereignis.
Ergebnis: "Ungepruefte Behauptung" bleibt sichtbar, entfernt = false.
Dies war ein isolierter Funktionstest, kein visueller Browsertest.

Vorschlag: Abschlussstatus verfolgen; bei Ende ohne gepruefte Antwort oder Lesefehler
Rohtext entfernen und den Abbruch melden. Auch Netzwerkausnahmen und ungueltige
Antwortzeilen pruefen. Vorlaeufigen Text deutlich als ungeprueft kennzeichnen.

## Weitere Verbesserung

### Testeinrichtung vervollstaendigen

Der dokumentierte und in GitHub Actions hinterlegte Installationsbefehl installiert
kein pytest (pyproject.toml:30, .github/workflows/tests.yml:38).
Der anschliessende unittest-Lauf meldete 678 Tests, davon neun Importfehler wegen
fehlendem pytest. Zusaetzlich sammelt unittest die freien pytest-Testfunktionen nicht
ein, etwa in tests/test_anmeldeseite.py und tests/test_bedrock_zeitgrenze.py.
Vorschlag: pytest als Testabhaengigkeit deklarieren und in der automatischen Pruefung
python -m pytest verwenden. Nur pytest zu installieren beseitigt die unvollstaendige
Testsammlung durch unittest nicht.

### Inhaltliche Belegqualitaet

Die Existenz einer Quellenkennung beweist nicht die Richtigkeit der Aussage.
Die erfundene Aussage "Der Gegner schuldet 999.999 EUR [Q: D1-S1-P1]." passiert
die Belegpruefung mit obiger Quelle ohne Hinweis. Diese Grenze ist im Code teilweise
dokumentiert, sollte aber auch bei der Bewertung der Ergebnisse beruecksichtigt werden.
Zahlen, Daten und Rollen sollten soweit moeglich gegen genau die zitierte Passage
geprueft werden; verbleibende inhaltliche Unsicherheit braucht anwaltliche Kontrolle.

## Bereits vorhanden

Einige Punkte aus MORGEN.md sind inzwischen umgesetzt: die Widerspruchsart Mass/Menge,
bereinigte grosse Testdaten mit eigenen Tests, Scanzeichenerkennung und ein Pruefbogen.
Die Arbeitsliste und Uebergabe sollten mit dem aktuellen Stand abgeglichen werden.
Fuer die fachliche Qualitaet empfiehlt sich der vorhandene Pruefbogen mit echten
Modellantworten, mehreren Laeufen und zusaetzlichen unbekannten Testakten.

## Umfang und Grenzen

Im Rahmen der Pruefung wurde der Programmcode nicht geaendert. Dieser Bericht wird
anschliessend auf Wunsch des Nutzers im Zweig 2.0 veroeffentlicht. Keine echten Mandantenakten
verarbeitet und keine kostenpflichtigen Modellaufrufe ausgefuehrt. Die Gegenproben
testen die Schutzlogik unabhaengig davon, wie oft ein Modell solche Antworten erzeugt.
