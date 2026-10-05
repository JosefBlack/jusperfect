# Verarbeitungsverzeichnis — Entwurf für den Eintrag „jusperfect"

**Stand: 05.10.2026.** Entwurf nach Art. 30 Abs. 1 DSGVO, zum Übernehmen in das
Verzeichnis der Verarbeitungstätigkeiten der Kanzlei.

> **Geändert am 05.10.2026.** Die Fassung vom 28.09.2026 beschrieb den Betrieb
> **mit abgeschaltetem Aktengedächtnis**. Es ist seit dem 05.10.2026
> eingeschaltet; damit entsteht eine dauerhafte Kopie von Akteninhalt außerhalb
> von jur|nodes. Abschnitt 6 ist daraufhin neu gefasst. Dazu kommen die
> Texterkennung (Abschnitt 7.1) und der Befund zum Korrespondenzordner
> (Abschnitt 8a).

---

## Wie dieser Entwurf zu lesen ist

Er ist **eine Übertragung, keine Bewertung.** Jede technische Angabe darin ist
gemessen oder im Programm nachgewiesen, mit Datum und Fundstelle — die
Grundlage steht in `DSFA-ANGABEN.md`. Was eine rechtliche Einordnung verlangt,
ist als **[KANZLEI]** gekennzeichnet und bewusst offen gelassen.

Die Entwicklung kann sagen, *was* das Programm tut. Ob es zulässig ist, unter
welcher Rechtsgrundlage, wie lange gespeichert werden darf und ob eine
Datenschutz-Folgenabschätzung nach Art. 35 DSGVO erforderlich ist, entscheidet
die Kanzlei.

**Eines gilt für jede Zeile unten:** Sie beschreibt den Stand vom 05.10.2026 —
also den Betrieb **mit eingeschaltetem Aktengedächtnis**. Was vorher galt,
steht in Abschnitt 6 zum Vergleich daneben, weil der Unterschied der eigentliche
Gegenstand der Bewertung ist.

---

## 1. Bezeichnung der Verarbeitungstätigkeit

**KI-gestützte Auswertung von Mandatsakten (jusperfect)**

Eine Schicht über der Aktenverwaltung jur|nodes, die Akteninhalt einem
Sprachmodell zur Auswertung vorlegt und das Ergebnis dem Bearbeiter zur
Prüfung vorlegt.

## 2. Verantwortlicher

| | |
|---|---|
| Verantwortlicher | **[KANZLEI]** — Name, Anschrift, Vertretung |
| Datenschutzbeauftragter | **[KANZLEI]** — sofern benannt |
| Datum der Aufnahme | **[KANZLEI]** |

## 3. Zwecke der Verarbeitung

Die Verarbeitung dient der **Bearbeitung des einzelnen Mandats**, und zwar:

- Erfassung des Lebenssachverhalts aus den Dokumenten der Akte
- Zusammenstellung einer Chronologie der Ereignisse
- Auffinden von Widersprüchen zwischen Angaben verschiedener Dokumente
- Zusammenstellung von Beteiligten, Forderungen, Beweismitteln
- Vorbereitung von Entwürfen und Vermerken zur Prüfung durch den Bearbeiter
- Beantwortung von Fragen des Bearbeiters zum Akteninhalt

**Was ausdrücklich nicht Zweck ist**, und im Programm auch nicht möglich:

| | Nachweis |
|---|---|
| Keine automatisierte Entscheidung im Sinne des Art. 22 DSGVO | Jede Ausgabe ist ein Vorschlag; geschrieben wird nur, was ein Mensch ausdrücklich freigibt (`security/approval.py`, HMAC an Nutzer, Akte, Textprüfsumme gebunden) |
| Keine Fristberechnung | Fristensperre (`services/fristen.py`), in Prüfbogenläufen am 16., 17., 22. und 28.09.2026 jeweils gehalten. Die Zweitprüfung vom 05.10.2026 fand drei Schreibweisen, die sie umgingen (zweistelliges Jahr, Monatsname ohne Jahr, Fristende ohne Fristwort); **am selben Tag geschlossen** — jedes angezeigte Datum muss sich seitdem auf eine mitgeschickte Passage, deren Kopfzeile oder den Fristenkalender zurückführen lassen |
| Keine Aussage ohne Fundstelle | Belegpflicht fail closed: Eine Aussage ohne Verweis auf eine mitgeschickte Passage wird **entfernt**, nicht markiert (`services/belegpflicht.py`). Bis zum 05.10.2026 galt das für die Antwort und die strukturierten Listen, nicht für Entwürfe, die Kernaussage der Eingangsprüfung und die Hinweise des Modells; und der laufende Text zeigte Ungeprüftes, bis die Prüfung am Ende kam. Beides ist geschlossen (Befunde F04/F05 der Zweitprüfung) |
| Kein Training des Modells | Amazon Bedrock verwendet Eingaben nicht zum Training; zugesichert im AWS-Vertragswerk |
| Keine Profilbildung, kein Abgleich über Akten hinweg | Jede Sitzung arbeitet an genau einer Akte |

## 4. Kategorien betroffener Personen

- **Mandanten** der Kanzlei
- **Gegner** und deren Bevollmächtigte
- **Zeugen**, Sachverständige, Beteiligte des jeweiligen Verfahrens
- **Dritte**, die in Dokumenten der Akte erwähnt werden (Angehörige,
  Sachbearbeiter von Versicherungen und Behörden, Gerichtspersonen)
- **Beschäftigte der Kanzlei** als Nutzer des Programms (Protokolldaten)

**[KANZLEI]** — zu ergänzen, falls weitere Gruppen in Betracht kommen.

## 5. Kategorien personenbezogener Daten

### 5.1 Aus der Mandatsakte

Verarbeitet wird **der Inhalt der Akte, wie er dort vorliegt** — die Auswahl
trifft der Bearbeiter, indem er eine Akte öffnet. Damit sind alle
Datenkategorien betroffen, die in Schriftsätzen, Urkunden, Korrespondenz und
Vermerken einer Mandatsakte vorkommen: Namen, Anschriften, Geburtsdaten,
Aktenzeichen, Vertrags- und Zahlungsdaten, Schilderungen des Sachverhalts.

### 5.2 Besondere Kategorien (Art. 9 DSGVO) und Art. 10 DSGVO

**Nach Rechtsgebiet regelmäßig betroffen** — deshalb hier ausdrücklich genannt
und nicht als Ausnahme behandelt:

| Rechtsgebiet | Kategorie |
|---|---|
| Personenschaden, Arzthaftung, Sozialrecht | Gesundheitsdaten (Art. 9) |
| Familien- und Erbrecht | Daten zum Familienleben, ggf. religiöse Zugehörigkeit |
| Arbeitsrecht | ggf. Gewerkschaftszugehörigkeit, Gesundheitsdaten |
| Strafrecht, Ordnungswidrigkeiten | Daten über Straftaten und Verurteilungen (Art. 10) |

**[KANZLEI]** — welche dieser Rechtsgebiete bearbeitet werden und ob die
Verarbeitung dort zugelassen wird. Das Programm unterscheidet **nicht** nach
Rechtsgebiet; eine Beschränkung wäre organisatorisch zu treffen.

> **Wichtig für die Bewertung:** Das Schutzgeländer filtert diese Inhalte
> bewusst **nicht**. Die Voreinstellungen von AWS hätten Gewalt, Sexuelles und
> Beleidigungen gesperrt — in einer Kanzlei ist genau das der Gegenstand der
> Arbeit. Eingeschaltet ist allein die Erkennung von Angriffen über den
> Fragetext (Stand 24.09.2026, geprüft mit fünf Rechtsgebietsproben).

### 5.3 Protokolldaten

| Was | Was **nicht** |
|---|---|
| Zeitpunkt, Nutzerkennung, Funktion, Modell, Aktenkennung, Tokenzahl, Kosten | **Kein Akteninhalt.** Das Material erscheint nur als Kurzkennung (Prüfsumme und Länge) |

Technisch erzwungen, an zwei Stellen:

1. `security/protokoll.py` weist Felder wie `text`, `frage`, `antwort`,
   `passagen` **aktiv zurück** (Ausnahme `ProtokollVerstoss`).
2. `fehlergrenze.py` nimmt **jedem** Protokolleintrag dieses Programms die
   angehängte Ausnahme ab und ersetzt sie durch die Namen der Ausnahmekette
   und die Code-Stelle. Ein Traceback, und mit ihm der Wortlaut einer fremden
   Fehlermeldung, erreicht kein Protokoll.

**Der zweite Punkt ist seit dem 05.10.2026 da, und bis dahin war die Aussage
zu weit.** Die Zweitprüfung hat gezeigt (Befund F01): Punkt 1 galt nur für den
eigenen Protokollkanal. Eine abgelehnte AWS-Anfrage wurde über Starlette
erneut geworfen und von Uvicorn samt Ursache protokolliert — und in einer
Ablehnung von AWS steht mitunter ein Stück der Anfrage.

## 6. Speicherdauer und Löschung

### 6.1 Bis zum 05.10.2026 (Aktengedächtnis abgeschaltet) — zum Vergleich

| Ort | Dauer |
|---|---|
| Arbeitsspeicher der Sitzung | solange die Sitzung offen ist, längstens die eingestellte Lebensdauer |
| Sitzungsspeicher | mit Ablauffrist; keine dauerhafte Ablage |
| Verarbeitungsnachweis | dauerhaft, **ohne Inhalte** (siehe 5.3) |
| jur\|nodes | unverändert die führende Akte; jusperfect liest daraus |

In diesem Zustand entstand **keine** dauerhafte Kopie des Akteninhalts
außerhalb von jur|nodes. Er gilt seit dem 05.10.2026 nicht mehr.

### 6.2 Seit dem 05.10.2026: das Aktengedächtnis ist in Betrieb

Eingerichtet am 28.09.2026, **eingeschaltet am 05.10.2026**. An diesem Tag hat
die Kanzlei die erste echte Akte vollständig eingelesen. Damit besteht erstmals
eine dauerhafte Kopie von Akteninhalt außerhalb von jur|nodes — **Mandatsgut,
kein Protokoll**:

| | |
|---|---|
| Inhalt | Lebenssachverhalt, Chronologie, frühere Fragen mit belegten Antworten, ausgelesene Dokumenttexte, die zuletzt gelaufene Aktenanalyse |
| Obergrenzen | 100 Frage-Antwort-Runden, 500 Chronologieeinträge |
| Ort | S3-Bucket der Kanzlei, Region Frankfurt, im eigenen AWS-Konto |
| Verschlüsselung | serverseitig mit einem Schlüssel der Kanzlei (KMS, symmetrisch, Single-Region — kein Schlüsselmaterial verlässt Frankfurt) |
| Objektnamen | enthalten **kein Aktenzeichen**, nur dessen SHA-256-Ableitung |
| Zugriff | ein eigener, auf genau diesen Bucket und diesen Schlüssel beschränkter Programmbenutzer |
| Löschung | über den berechtigungsgeprüften Weg des Programms, oder mit dem Abschluss der Akte |
| Gezielte Löschung | seit dem 05.10.2026 in der Oberfläche: ein einzelnes Dokument **samt allem daraus Abgeleiteten**, oder eine einzelne Frage-Antwort-Runde. Das bedient Berichtigungs- und Löschverlangen nach Art. 16 und 17 DSGVO, ohne die ganze Fallkopie zu verwerfen |

**[KANZLEI] — die entscheidende offene Frage: Wann wird gelöscht?**

Der heutige Stand ist die sichere, aber unbefriedigende Seite: **Eine Löschfrist
beginnt nie von selbst.** Gelöscht wird eine Fallkopie nur, wenn ein Bearbeiter
die Akte in jusperfect ausdrücklich abschließt. Die Speicherdauer ist damit der
Abschluss durch den Bearbeiter — nicht der Aktenstatus in jur|nodes.

Am 28.09.2026 ist belegt, dass die Schnittstelle den Status liefert
(`recordStatus`, `archivedDate`). Eine Löschung, die dem Aktenstatus folgt, ist
damit technisch möglich und wäre zu vereinbaren. Ob sie gewollt ist, und mit
welcher Frist nach Archivierung, ist eine Entscheidung der Kanzlei.

## 7. Kategorien von Empfängern

### 7.1 Auftragsverarbeiter

| | |
|---|---|
| Empfänger | **Amazon Web Services** — [KANZLEI] vertragsschließende Gesellschaft nach Ihrem AV-Vertrag |
| Leistung | Amazon Bedrock (Sprachmodell), **Amazon Textract** (Texterkennung gescannter Seiten, seit 02.10.2026), S3 und KMS (Aktengedächtnis, seit 05.10.2026) |
| Ort der Verarbeitung | Region Frankfurt, `eu-central-1` |
| AV-Vertrag | **[KANZLEI]** — Datum, Fassung, Ablage |
| Berufsgeheimnis | **[KANZLEI]** — Verpflichtung nach § 43e BRAO, § 203 StGB prüfen und dokumentieren |

**Zur Texterkennung.** Es ist **derselbe** Auftragsverarbeiter und derselbe
AV-Vertrag, kein zweiter. Übermittelt wird **ein Bild je Seite**, erzeugt auf
dem Rechner der Kanzlei; bei AWS wird es **verarbeitet, nicht gespeichert** —
kein Ablageort, keine Löschfrist, nichts hier zu nennen außer der Verarbeitung
selbst. Einzelheiten in `DSFA-ANGABEN.md`.

**Kein weiterer Anbieter.** Das Programm ruft genau einen Modellanbieter auf,
und zwar über eine einzige geprüfte Stelle im Programm (`services/ausgang.py`).
Andere Anbieter sind vorbereitet, aber nicht angebunden — jeder wäre ein neuer
Auftragsverarbeiter und verlangte eine Änderung dieses Eintrags.

### 7.2 Keine Übermittlung an Dritte

Es gibt keine Weitergabe an andere Empfänger. Die Recherche in Haufe und in
Gesetzestexten erfolgt über einen Link im Browser des Bearbeiters; dabei geht
**kein Akteninhalt** hinaus.

## 8. Übermittlung in Drittländer

**Keine.** Nachgewiesen durch drei voneinander unabhängige Grenzen:

| Grenze | Wirkung |
|---|---|
| Region | Nur die **namentlich aufgeführten** EU- und EWR-Regionen sind in den Einstellungen zulässig; alles andere bricht beim Start ab (`config.py::EU_EWR_REGIONEN`) |
| Modellaufruf | Über das europäische Inferenzprofil (`eu.`-Vorsatz), das die Verarbeitung in europäischen Regionen hält |
| Zugriffsrichtlinie | Ein ausdrückliches **Verbot** jedes Bedrock-Aufrufs außerhalb `eu-*` — ein Verbot wiegt in AWS schwerer als jede Erlaubnis |

> **Berichtigt am 05.10.2026, und es gehört in die Bewertung.** Bis zu diesem
> Tag prüfte das Programm auf den Vorsatz `eu-`, und dieser Eintrag stützte sich
> darauf. **Der Vorsatz ist eine Namenskonvention von AWS, keine Aussage über
> die EU:** `eu-central-2` ist Zürich (Schweiz), `eu-west-2` ist London
> (Vereinigtes Königreich). Beide hätten die Prüfung bestanden.
>
> Im Programm ist das behoben — geprüft wird gegen eine aufgeschriebene Liste.
> **Die Zugriffsrichtlinie prüft weiterhin `eu-*`**; sie ist eine geschützte
> Datei und wird nur auf Anweisung geändert (Vorschlag in `DSFA-ANGABEN.md`).
> Und beides trifft die eigentliche Frage nicht: Wohin das Inferenzprofil
> intern verteilt, entscheidet AWS.

**Eine Angabe ist offen:** Das regionsübergreifende Geländerprofil
(`eu.guardrail.v1:0`) verteilt die Prüfung der **Frage** auf mehrere
europäische Regionen. Welche das sind, nennt AWS in seiner Dokumentation;
für die Unterlage ist die Liste nachzutragen (`DSFA-ANGABEN.md`, Abschnitt
„Noch nicht festgestellt"). Akteninhalt geht dabei nicht durch das Geländer —
nur Frage und Antwort.

## 8a. Ein Befund, der in die Bewertung gehört: fremde Schriftstücke

Am 05.10.2026 hat sich an drei echten Akten gezeigt, dass über das Feld
`correspondenceFolderId` Schriftstücke in die Arbeitsakte gelangten, die
**nicht zu ihr gehören** — in einer Akte 17 von 55.

**Die Ursache liegt im Programm.** jur|nodes führt zwei getrennte Ordnerbäume
mit je eigenen Nummern; das Programm hat die Nummer des Korrespondenzordners am
Pfad des Dateisystems abgefragt. Eine frühere Fassung dieses Entwurfs führte
den Vorgang auf ein Verhalten der Schnittstelle zurück — **das war falsch und
ist berichtigt.**

| | |
|---|---|
| Was geschehen ist | Akteninhalt eines fremden Mandats wurde in die Arbeitsakte eines anderen Mandats gelesen |
| Wohin | in den Arbeitsspeicher der Sitzung und an das Modell; **nicht** in das Aktengedächtnis (das war damals aus) |
| Was seitdem gilt | Der Korrespondenzordner wird **nicht mehr gelesen**. Damit fehlt die Korrespondenz — die sichere Richtung |
| Der richtige Weg | `POST /correspondence/search` — seit dem 05.10.2026 belegt, in der Probe gemessen, noch nicht im Betrieb |

**[KANZLEI]** — zu bewerten: ob eine kanzleiinterne Vermengung von Mandaten
eine Verletzung im Sinne des Art. 4 Nr. 12 DSGVO ist und ob Art. 33 greift. Aus
Sicht der Entwicklung ist **kein Abfluss nach außen** festzustellen: Die
Schriftstücke stammen aus dem eigenen Aktenbestand der Kanzlei, die
Verarbeitung lief im selben AWS-Konto desselben Auftragsverarbeiters. Die
Ursache liegt jedoch **beim Verantwortlichen** — im Programm —, nicht beim
Auftragsverarbeiter und nicht beim Hersteller der Aktenverwaltung.

## 9. Rechtsgrundlage

**[KANZLEI]** — vollständig offen, weil es eine Bewertung ist.

Zu entscheiden sind mindestens:

1. Rechtsgrundlage für Mandantendaten (Art. 6 Abs. 1 DSGVO)
2. Rechtsgrundlage für Daten von Gegnern, Zeugen und Dritten
3. Erlaubnistatbestand für besondere Kategorien (Art. 9 Abs. 2)
4. Verhältnis zur Verschwiegenheitspflicht und § 43e BRAO
5. Ob eine Datenschutz-Folgenabschätzung nach Art. 35 erforderlich ist

## 10. Technische und organisatorische Maßnahmen (Art. 32 DSGVO)

Die folgenden Maßnahmen sind im Programm umgesetzt und durch Prüfungen
gehalten — 1562 automatische Prüfungen, Stand 05.10.2026.

### 10.1 Datenminimierung

| Maßnahme | Wirkung |
|---|---|
| Kein Inhalt im Protokoll | Technisch erzwungen, nicht nur vorgesehen (5.3) |
| Nachweis nur mit Kurzkennung | Prüfsumme und Länge statt Text |
| Objektnamen ohne Aktenzeichen | Nur SHA-256-Ableitung, auch in Verwaltungsdaten |
| Auswahl der Passagen | Es geht nur hinaus, was zur Frage gehört — nicht die ganze Akte je Frage |

### 10.2 Richtigkeit und Nachvollziehbarkeit

| Maßnahme | Wirkung |
|---|---|
| Belegpflicht fail closed | Unbelegte Aussagen werden entfernt – in jedem angezeigten Modelltext und schon im laufenden Text |
| Fundstellen auf Passagenebene | Jede Aussage ist am Originaldokument nachprüfbar |
| Fristensperre | Keine berechneten Fristen, auch wenn die Akte dazu auffordert |
| Verarbeitungsnachweis | Jeder Modellaufruf hinterlässt eine Zeile |

### 10.3 Zugriff und Integrität

| Maßnahme | Wirkung |
|---|---|
| Ein geprüfter Ausgang | Genau eine Stelle im Programm führt zum Modell |
| Zurückschreiben nur mit Freigabe | An Nutzer, Akte, Textprüfsumme und Vorgang gebunden (HMAC) |
| Kein Löschrecht in jur\|nodes | Das Programm kann im Aktenbestand nichts löschen |
| Nur lesende Schnittstellenzugriffe | Bis auf den einen freigegebenen Vermerk |
| Beschränkter AWS-Benutzer | Darf Claude aufrufen und sonst nichts; Verbote ausdrücklich gesetzt |
| Verschlüsselung der Fallkopie | SSE-KMS mit eigenem Schlüssel der Kanzlei |
| Gezielte Löschung | Einzelne Dokumente und einzelne Frage-Antwort-Runden lassen sich aus der Fallkopie entfernen, samt allem daraus Abgeleiteten |
| Anbieterbegrenzung | Ein Verbot jedes Modells, das nicht Claude in EU ist |

### 10.4 Fail-closed-Sicherungen beim Start

Das Programm **startet nicht**, wenn eine dieser Bedingungen mit echten Akten
nicht erfüllt ist:

- Die Mitschrift der Modellaufrufe bei AWS ist eingeschaltet oder ihr Zustand
  unbekannt
- Kein Schutzgeländer hinterlegt
- Kein Schlüssel der Kanzlei bei dauerhafter Ablage
- Eine unverschlüsselte Ablage auf dem Rechner zusammen mit echten Akten

Das ist keine Warnung, sondern ein Abbruch. Geprüft in `tests/test_config.py`.

### 10.5 Organisatorisch — **[KANZLEI]**

| Offen | |
|---|---|
| Nutzerverwaltung | Derzeit haben alle neun eingetragenen Nutzer Zugriff auf alle Akten (Stand 24.09.2026, `nutzer-kanzlei.json`). Ob das so bleiben soll, ist zu entscheiden |
| Schulung | Wer das Programm bedient, muss wissen, dass jede Ausgabe zu prüfen ist |
| Kostengrenze | Eine Monatsgrenze ist gesetzt und bremst weitere Aufrufe |
| Weitergabe von Befunddateien | Die Prüfprogramme schreiben Dateien ohne Akteninhalt; ein Blick vor dem Weitergeben ist trotzdem vorgesehen |

## 11. Was in diesem Entwurf bewusst fehlt

| Fehlt | Warum |
|---|---|
| Die rechtliche Bewertung | Sache der Kanzlei |
| Der Text der Mandantenhinweise | Entwurf seit 05.10.2026 in `DATENSCHUTZHINWEISE-ENTWURF.md` |
| Die Erforderlichkeit einer DSFA | Art. 35 — Bewertung. Entwurf seit 05.10.2026 in `DSFA-ENTWURF.md` |
| Die Liste der Regionen des Geländerprofils | Bei AWS nachzulesen, noch nicht festgestellt |
| Ein Löschkonzept mit Fristen | Hängt an der Entscheidung in 6.2 |

---

## Woher die Angaben stammen

| Quelle | Inhalt |
|---|---|
| `DSFA-ANGABEN.md` | Alle technischen Werte mit Datum und Fundstelle |
| `SICHERHEIT.md` | Die 16 Grundsätze und das Löschkonzept |
| `KONZEPT.md` | Warum das Programm so gebaut ist |
| `infra/IAM.md` | Die Zugriffsrichtlinie im Wortlaut |
| `DSFA-ENTWURF.md` | Der Entwurf der Folgenabschätzung nach Art. 35 |
| `DATENSCHUTZHINWEISE-ENTWURF.md` | Entwurf der Hinweise nach Art. 13 und der Mandatsklausel |

**Bei Widerspruch gilt `DSFA-ANGABEN.md`** — dort steht, was gemessen wurde,
und an welchem Tag.

Dieser Entwurf ist keine Rechtsberatung.
