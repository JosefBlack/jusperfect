# Verarbeitungsverzeichnis — Entwurf für den Eintrag „jusperfect"

**Stand: 28.09.2026.** Entwurf nach Art. 30 Abs. 1 DSGVO, zum Übernehmen in das
Verzeichnis der Verarbeitungstätigkeiten der Kanzlei.

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

**Zwei Dinge gelten für jede Zeile unten:** Sie beschreibt den Stand vom
28.09.2026, und sie beschreibt den Betrieb **mit abgeschaltetem
Aktengedächtnis**. Was sich mit dem Einschalten ändert, steht in Abschnitt 6
gesondert.

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
| Keine Fristberechnung | Fristensperre, in Prüfbogenläufen am 16., 17., 22. und 28.09.2026 jeweils gehalten (`services/fristen.py`) |
| Keine Aussage ohne Fundstelle | Belegpflicht fail closed: Eine Aussage ohne Verweis auf eine mitgeschickte Passage wird **entfernt**, nicht markiert (`services/belegpflicht.py`) |
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

Technisch erzwungen: `security/protokoll.py` weist Felder wie `text`, `frage`,
`antwort`, `passagen` **aktiv zurück** (Ausnahme `ProtokollVerstoss`). Ein
Protokolleintrag mit Inhalt lässt sich nicht schreiben.

## 6. Speicherdauer und Löschung

### 6.1 Heute (Aktengedächtnis abgeschaltet)

| Ort | Dauer |
|---|---|
| Arbeitsspeicher der Sitzung | solange die Sitzung offen ist, längstens die eingestellte Lebensdauer |
| Sitzungsspeicher | mit Ablauffrist; keine dauerhafte Ablage |
| Verarbeitungsnachweis | dauerhaft, **ohne Inhalte** (siehe 5.3) |
| jur\|nodes | unverändert die führende Akte; jusperfect liest daraus |

**Es entsteht keine dauerhafte Kopie des Akteninhalts außerhalb von
jur|nodes.** Stand 28.09.2026, `JUSPERFECT_GEDAECHTNIS=aus`.

### 6.2 Mit eingeschaltetem Aktengedächtnis — **noch nicht in Betrieb**

Eingerichtet am 28.09.2026, eingeschaltet nicht. **Mit dem Einschalten ändert
sich dieser Eintrag wesentlich**, denn dann entsteht erstmals eine dauerhafte
Kopie von Akteninhalt außerhalb von jur|nodes:

| | |
|---|---|
| Inhalt | Lebenssachverhalt, Chronologie, frühere Fragen mit belegten Antworten, ausgelesene Dokumenttexte |
| Ort | S3-Bucket der Kanzlei, Region Frankfurt, im eigenen AWS-Konto |
| Verschlüsselung | serverseitig mit einem Schlüssel der Kanzlei (KMS, symmetrisch, Single-Region — kein Schlüsselmaterial verlässt Frankfurt) |
| Objektnamen | enthalten **kein Aktenzeichen**, nur dessen SHA-256-Ableitung |
| Zugriff | ein eigener, auf genau diesen Bucket und diesen Schlüssel beschränkter Programmbenutzer |
| Löschung | über den berechtigungsgeprüften Weg des Programms, oder mit dem Abschluss der Akte |

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
| Leistung | Amazon Bedrock (Sprachmodell), S3 und KMS (nur bei eingeschaltetem Aktengedächtnis) |
| Ort der Verarbeitung | Region Frankfurt, `eu-central-1` |
| AV-Vertrag | **[KANZLEI]** — Datum, Fassung, Ablage |
| Berufsgeheimnis | **[KANZLEI]** — Verpflichtung nach § 43e BRAO, § 203 StGB prüfen und dokumentieren |

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
| Region | Nur EU-Regionen sind in den Einstellungen zulässig; alles andere bricht beim Start ab (`config.py`) |
| Modellaufruf | Über das europäische Inferenzprofil (`eu.`-Vorsatz), das die Verarbeitung in europäischen Regionen hält |
| Zugriffsrichtlinie | Ein ausdrückliches **Verbot** jedes Bedrock-Aufrufs außerhalb `eu-*` — ein Verbot wiegt in AWS schwerer als jede Erlaubnis |

**Eine Angabe ist offen:** Das regionsübergreifende Geländerprofil
(`eu.guardrail.v1:0`) verteilt die Prüfung der **Frage** auf mehrere
europäische Regionen. Welche das sind, nennt AWS in seiner Dokumentation;
für die Unterlage ist die Liste nachzutragen (`DSFA-ANGABEN.md`, Abschnitt
„Noch nicht festgestellt"). Akteninhalt geht dabei nicht durch das Geländer —
nur Frage und Antwort.

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
gehalten — 1247 automatische Prüfungen, Stand 28.09.2026.

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
| Belegpflicht fail closed | Unbelegte Aussagen werden entfernt |
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
| Verschlüsselung der Fallkopie | SSE-KMS mit eigenem Schlüssel (nur bei 6.2) |
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
| Der Text der Mandantenhinweise | Eine Formulierungsfrage, keine technische |
| Die Erforderlichkeit einer DSFA | Art. 35 — Bewertung |
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

**Bei Widerspruch gilt `DSFA-ANGABEN.md`** — dort steht, was gemessen wurde,
und an welchem Tag.

Dieser Entwurf ist keine Rechtsberatung.
