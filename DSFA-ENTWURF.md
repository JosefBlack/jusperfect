# Datenschutz-Folgenabschätzung — Entwurf

**Stand: 05.10.2026.** Entwurf nach Art. 35 DSGVO für die Verarbeitungstätigkeit
„KI-gestützte Auswertung von Mandatsakten (jusperfect)".

---

## Wie dieser Entwurf zu lesen ist

**Er ist kein Gutachten und keine Rechtsberatung.** Er ist das, was die
Entwicklung beitragen kann: eine vollständige, belegte Beschreibung dessen,
*was* das Programm tut, *welche Risiken* daraus entstehen und *welche
Maßnahmen* dagegen im Programm stehen — jede mit Fundstelle.

**Die Bewertung bleibt bei der Kanzlei.** Ob eine DSFA erforderlich ist, ob das
verbleibende Risiko tragbar ist und ob die Aufsichtsbehörde nach Art. 36
einzuschalten ist, kann nur ein Jurist entscheiden, der das Mandatsgeschäft
kennt. Diese Stellen sind mit **[KANZLEI n]** gekennzeichnet; es sind
**siebzehn**, und sie stehen am Ende noch einmal in einer Liste.

**Die Zahlen und Befunde stehen woanders.** Jede technische Angabe hier ist aus
`DSFA-ANGABEN.md` übernommen, wo sie mit Datum und Fundstelle steht. Bei
Widerspruch gilt `DSFA-ANGABEN.md`.

| Dieses Dokument | Was es ist |
|---|---|
| `DSFA-ENTWURF.md` | diese Datei — Art. 35, Risiken und Maßnahmen |
| `VERARBEITUNGSVERZEICHNIS-ENTWURF.md` | Art. 30 — die Beschreibung der Verarbeitung |
| `DSFA-ANGABEN.md` | die gemessenen technischen Werte, mit Datum |
| `SICHERHEIT.md` | die 16 Grundsätze und das Löschkonzept |

---

## 1. Ist eine DSFA überhaupt erforderlich?

**[KANZLEI 1]** — die erste und wichtigste Bewertung. Was dafür spricht, aus
der Sicht dessen, der das Programm gebaut hat:

| Anhaltspunkt | Lage hier |
|---|---|
| **Art. 35 Abs. 3 lit. b** — umfangreiche Verarbeitung besonderer Kategorien (Art. 9) oder von Daten über Straftaten (Art. 10) | Trifft je nach Rechtsgebiet regelmäßig zu: Gesundheitsdaten in Unfall-, Arzthaftungs- und Sozialrechtsakten, Art.-10-Daten im Strafrecht. Das Programm unterscheidet **nicht** nach Rechtsgebiet |
| **Neue Technologie** (Art. 35 Abs. 1) | Ein Sprachmodell wertet Mandatsakten aus. Das ist für die Kanzlei neu |
| **Berufsgeheimnis** | Der verarbeitete Inhalt unterliegt § 203 StGB und § 43a BRAO |
| **Muster-Liste der deutschen Aufsichtsbehörden (DSK)** | Dort ist die Verarbeitung von Daten, die einem Berufsgeheimnis unterliegen, durch einen Auftragsverarbeiter aufgeführt. **[KANZLEI 16]** — die einschlägige Landesliste ist heranzuziehen; die Entwicklung kann sie nicht auswählen |
| **Umfang** | Der Bestand umfasst rund 2.950 Akten und etwa 78.000 Dateien (gemessen 02.10.2026). Ob das „umfangreich" im Sinne der Norm ist: **[KANZLEI 2]** |

**Was dagegen sprechen könnte** — und ebenfalls bewertet gehört: Es findet
keine automatisierte Entscheidung im Sinne des Art. 22 statt, keine
Profilbildung, keine systematische Überwachung, und die Verarbeitung dient
ausschließlich dem einzelnen Mandat.

> **Ein Hinweis aus der Entwicklung, keine Empfehlung.** Falls die Kanzlei zu
> dem Ergebnis kommt, dass keine DSFA erforderlich ist, gehört **diese
> Prüfung selbst** dokumentiert (Rechenschaftspflicht, Art. 5 Abs. 2). Dieser
> Entwurf taugt dann als Dokumentation der Prüfung.

---

## 2. Systematische Beschreibung der Verarbeitung

Vollständig in `VERARBEITUNGSVERZEICHNIS-ENTWURF.md`. Hier nur, was für die
Risikobewertung gebraucht wird.

### 2.1 Was wohin geht

| Schritt | Was verlässt die Kanzlei | Wohin |
|---|---|---|
| Dokumente lesen | nichts | — |
| Gescannte Seite erkennen | **ein Bild je Seite** | AWS Textract, Frankfurt. Verarbeitet, **nicht gespeichert** |
| Frage, Analyse, Entwurf | **die ausgewählten Passagen** als Text | AWS Bedrock, Frankfurt, über das EU-Inferenzprofil |
| Schutzgeländer | **Frage und Antwort**, nicht der Akteninhalt | `eu.guardrail.v1:0`, verteilt auf europäische Regionen |
| Aktengedächtnis sichern | **Dokumenttexte und Abgeleitetes** | S3-Bucket der Kanzlei, Frankfurt, SSE-KMS |
| Vermerk zurückschreiben | **nur der freigegebene Text** | jur\|nodes |

**Was das Modell nie zu sehen bekommt:** Dateinamen, Dokumentkennungen,
Nutzerkennungen, Sitzungskennungen, Aktenzeichen. Es sieht Systemanweisung,
Passagen und Aufgabe (`providers/bedrock.py`).

### 2.2 Wo dauerhaft gespeichert wird

Seit dem **05.10.2026** besteht eine dauerhafte Kopie von Akteninhalt außerhalb
von jur|nodes: das Aktengedächtnis im S3-Bucket der Kanzlei, Frankfurt,
verschlüsselt mit einem eigenen KMS-Schlüssel, Objektnamen ohne Aktenzeichen.

**Das ist der Umstand, der diese Unterlage auslöst.** Vorher war jede
Verarbeitung flüchtig.

### 2.3 Die Rolle des Menschen

Keine Ausgabe des Programms wirkt nach außen, bevor ein Mensch sie freigegeben
hat. Das ist nicht nur vorgesehen, sondern technisch gebunden: Die Freigabe ist
an Nutzer, Akte, Textprüfsumme und Vorgang gekoppelt (HMAC,
`security/approval.py`); ein geänderter Text, eine fremde Akte oder eine
nachgebaute Signatur werden abgewiesen (`tests/test_freigabe.py`).

---

## 3. Notwendigkeit und Verhältnismäßigkeit

**[KANZLEI 3]** — die Abwägung selbst. Was die Entwicklung dazu beitragen kann:

### 3.1 Was die Verarbeitung erreicht

Gemessen an einer echten Akte am 25.09. und 05.10.2026: 55 Dokumente, aus denen
ein belegter Lebenssachverhalt, ein Zeitstrahl und eine Analyse entstehen, für
rund 28 Cent. Was ein Bearbeiter daran gewinnt, ist Zeit beim Erfassen eines
Sachverhalts und das Auffinden von Widersprüchen zwischen Dokument 8 und
Dokument 44 — Stellen, die beim Lesen übersehen werden.

### 3.2 Warum nicht weniger eingriffsintensiv

| Mildere Mittel, geprüft | Warum sie nicht reichen |
|---|---|
| **Anonymisierung vor der Übermittlung** | Der Gegenstand der Auswertung sind gerade die Personen, Daten und Beträge. Eine Akte, aus der Namen und Daten entfernt sind, beantwortet die Fragen nicht mehr, die gestellt werden |
| **Pseudonymisierung** | Dasselbe für Namen; für Beträge, Daten und Sachverhaltsschilderungen nicht durchführbar. Die Kanzlei betreibt mit *Perfect Shield* ein getrenntes Programm für Schwärzungen; es löst eine andere Aufgabe |
| **Nur ein Teil der Akte** | Ist umgesetzt: Es geht nur hinaus, was der Bearbeiter anhakt — nicht die Akte je Frage. Seit dem 05.10.2026 kommen Rechnungen und RSV-Korrespondenz schon ohne Haken ins Fenster |
| **Modell auf eigener Hardware** | Wäre das mildere Mittel hinsichtlich der Übermittlung. **[KANZLEI 4]** — zu bewerten, ob der Aufwand verhältnismäßig ist. Die Entwicklung kann sagen: technisch möglich, aber mit erheblichem Qualitätsverlust bei den Modellgrößen, die auf Kanzleihardware laufen |

### 3.3 Datenminimierung, die umgesetzt ist

| Maßnahme | Nachweis |
|---|---|
| Kein Akteninhalt im Protokoll | technisch erzwungen, `security/protokoll.py` weist Inhaltsfelder zurück |
| Nachweis nur mit Prüfsumme und Länge | `domain/models.py::Nutzungseintrag` |
| Objektnamen ohne Aktenzeichen | nur SHA-256-Ableitung |
| Auswahl der Passagen durch den Bearbeiter | zwei Fenster, Haken je Dokument |
| Vorauswahl schließt Rechnungen und RSV aus | seit 05.10.2026, `JUSPERFECT_NICHT_VORWAEHLEN` |
| Der Korrespondenzordner wird nicht gelesen | seit 05.10.2026, siehe Risiko R1 |

---

## 4. Die Risiken — und was ihnen entgegensteht

Acht Risiken, in der Reihenfolge, in der sie die Entwicklung für erheblich
hält. **Die Einstufung in „gering / mittel / hoch" ist bewusst leer gelassen**
([KANZLEI 5]): Sie hängt davon ab, welche Rechtsgebiete bearbeitet werden und
wie die Kanzlei das Berufsgeheimnis gewichtet.

---

### R1 · Vermengung von Mandaten

**Das größte Risiko, und es ist am 05.10.2026 eingetreten.**

Die Schnittstelle von jur|nodes lieferte über das Feld `correspondenceFolderId`
Schriftstücke, die nicht zu der abgefragten Akte gehören — in einer Akte 17 von
55, an drei Akten dasselbe Muster. Akteninhalt eines fremden Mandats wurde in
die Arbeitsakte eines anderen gelesen und ging an das Modell.

| Folge für die Betroffenen | Dass Angaben aus ihrem Mandat in der Bearbeitung eines fremden Mandats auftauchen — der Kernbereich des § 203 StGB |
|---|---|
| **Was es verhindert hat** | Das Aktengedächtnis war zu diesem Zeitpunkt **aus**. Es ist nichts dauerhaft abgelegt worden |
| **Was seitdem gilt** | Der Korrespondenzordner wird nicht mehr gelesen. Die Korrespondenz fehlt damit — die sichere Richtung |
| **Was das Programm selbst prüft** | Der Durchlauf durch die Ordner meldet seitdem ausdrücklich, wenn er die Akte verlässt |
| **Was offen ist** | Worauf das Feld tatsächlich zeigt. Die Anfrage an den Hersteller ist formuliert |

**[KANZLEI 6]** — zu bewerten: ob dies eine Verletzung nach Art. 4 Nr. 12 ist
und ob Art. 33 greift. Aus Sicht der Entwicklung **kein Abfluss nach außen**:
eigener Aktenbestand, eigenes AWS-Konto, derselbe Auftragsverarbeiter.

---

### R2 · Eine falsche Aussage wird für wahr genommen

Ein Sprachmodell erzeugt plausibel klingende Sätze. Übernimmt ein Bearbeiter
einen davon ungeprüft in einen Schriftsatz, trifft der Schaden den Mandanten.

**Was dagegen steht — und es ist die tragende Maßnahme des ganzen Programms:**

| Maßnahme | Wirkung | Nachweis |
|---|---|---|
| **Belegpflicht, fail closed** | Eine Aussage ohne Verweis auf eine mitgeschickte Passage wird **entfernt**, nicht markiert | `services/belegpflicht.py` |
| Fundstellen auf Passagenebene | `D2-S1-P3` — jede Aussage ist am Originaldokument nachprüfbar, mit einem Klick | |
| Die tragende Stelle wird hervorgehoben | und wenn sie sich nicht zuordnen lässt, steht das daneben: *„Bitte nachlesen."* | |
| Fristensperre | Fristen werden erkannt, nie berechnet — auch wenn die Akte dazu auffordert | `services/fristen.py`, in vier Prüfbogenläufen gehalten |
| Verweigerung statt Vermutung | *„kein belastbarer Beleg"* ist eine zulässige Antwort | |

**Was offen bleibt:** Die Belegpflicht sichert, dass ein Satz **auf einer
Stelle beruht**. Sie sichert nicht, dass die Stelle den Satz **trägt**. Das
bleibt die Aufgabe des Bearbeiters — und ist der Grund, warum die
Mitarbeiterschulung in Abschnitt 6 steht und nicht als Nebensache.

---

### R3 · Die dauerhafte Fallkopie

Seit dem 05.10.2026 liegt Akteninhalt dauerhaft außerhalb von jur|nodes: ein
zweiter Ort, der gesichert, verschlüsselt, mit einer Löschfrist versehen und
bei einem Auskunftsverlangen mitbedacht werden muss.

| Maßnahme | Stand |
|---|---|
| Eigener Bucket, eigenes Konto, Frankfurt | 28.09.2026 eingerichtet |
| SSE-KMS, symmetrischer Single-Region-Schlüssel der Kanzlei | kein Schlüsselmaterial verlässt Frankfurt |
| Öffentlicher Zugriff vollständig blockiert, Versionierung aus | was gelöscht wird, soll gelöscht sein |
| Objektnamen ohne Aktenzeichen | nur SHA-256-Ableitung |
| Beschränkter Programmbenutzer | nur dieser Bucket, nur dieser Schlüssel |
| **Gezielte Löschung einzelner Einträge** | seit 05.10.2026: ein Dokument samt allem Abgeleiteten, oder eine einzelne Frage-Antwort-Runde. Bedient Art. 16 und 17 ohne Verwerfen der ganzen Fallkopie |
| Obergrenzen | 100 Frage-Antwort-Runden, 500 Zeitstrahleinträge |

**[KANZLEI 7] — die offene Entscheidung: Wann wird gelöscht?** Heute beginnt
eine Löschfrist **nie von selbst**. Gelöscht wird nur, wenn ein Bearbeiter die
Akte in jusperfect abschließt; danach läuft eine Übergangsfrist (Vorgabe 30
Tage), und erst dann wird gelöscht.

Das ist die sichere, aber unbefriedigende Seite: Es wird nichts gelöscht, was
bleiben soll — aber es bleibt auch, was gehen könnte. Dass der Aktenstatus aus
jur|nodes die Löschung auslösen kann, ist seit dem 28.09.2026 technisch belegt.

> **Eine Einschränkung, die dazugehört:** Das Programm erkennt im Feld
> `recordStatus` genau zwei Wörter als „abgeschlossen". Jedes andere gilt
> stillschweigend als „laufend" — die ungefährliche Richtung, aber eine Akte,
> die in jur|nodes anders abgeschlossen heißt, wird nie abschlussreif. Welche
> Wörter der Bestand wirklich führt, zeigt die Probe an.

---

### R4 · Übermittlung an einen Auftragsverarbeiter, der dem Berufsgeheimnis unterliegt

Akteninhalt geht an AWS. Das ist eine Übermittlung an einen Dritten im Sinne
des § 203 Abs. 3 StGB und des § 43e BRAO.

| Maßnahme | Stand |
|---|---|
| AV-Vertrag | **[KANZLEI 8]** — Datum, Fassung, Ablage eintragen |
| Verpflichtung zur Verschwiegenheit in Textform (§ 43e Abs. 3 BRAO) | **[KANZLEI 9]** — prüfen und dokumentieren |
| Dokumentation der Dienstleisterauswahl (§ 43e Abs. 2) | **[KANZLEI 10]** |
| Kein Modelltraining | im AWS-Vertragswerk zugesichert |
| Ein einziger Ausgang im Programm | `services/ausgang.py` — genau eine Stelle führt zum Modell |
| Kein zweiter Anbieter | andere sind vorbereitet, keiner angebunden |

---

### R5 · Drittlandbezug durch das EU-Inferenzprofil und das Schutzgeländer

Der `eu.`-Vorsatz hält die Verarbeitung in europäischen Regionen, verteilt sie
aber auf mehrere. Dasselbe gilt für das Geländerprofil `eu.guardrail.v1:0`.

| Grenze | Wirkung |
|---|---|
| Region in den Einstellungen | nur EU-Regionen zulässig; alles andere bricht beim Start ab |
| Zugriffsrichtlinie | ausdrückliches **Verbot** jedes Bedrock-Aufrufs außerhalb `eu-*` — ein Verbot wiegt in AWS schwerer als jede Erlaubnis |
| Durch das Geländer geht | nur Frage und Antwort, nicht der Akteninhalt |

**[KANZLEI 11] — eine Angabe ist ungesichert.** Welche Regionen das
Geländerprofil benutzt, nennt AWS in der Konsole nicht. Eine Zusammenfassung
aus zweiter Hand nennt Irland, Frankfurt, Paris, Mailand, Spanien, Stockholm —
**und Zürich, also die Schweiz**. Für den Drittlandbezug wäre das erheblich,
und genau deshalb darf es nicht aus zweiter Hand übernommen werden. **Beim
AWS-Support zu erfragen**, ausdrücklich für das Geländerprofil und für die drei
benutzten Modellkennungen.

---

### R6 · Besondere Kategorien, verstärkt durch die Texterkennung

Seit dem 02.10.2026 werden auch gescannte Blätter gelesen. Rückscheine und
Vollmachten enthalten regelmäßig keine Gesundheitsdaten — ärztliche Unterlagen
in einer Arzthaftungssache sehr wohl, und genau die liegen typischerweise als
Scan vor.

**Die Texterkennung erweitert damit den Umfang der Art.-9-Verarbeitung**, ohne
dass sich an Anbieter, Region oder Vertrag etwas ändert.

| Maßnahme | Stand |
|---|---|
| Derselbe Auftragsverarbeiter, derselbe AV-Vertrag | kein neuer Vertrag |
| Verarbeitet, nicht gespeichert | kein Ablageort bei AWS; die Bilder entstehen auf dem Rechner der Kanzlei |
| Abschaltbar mit einer Zeile | `JUSPERFECT_OCR=aus`; gescannte Blätter bleiben dann ungelesen |

**[KANZLEI 12]** — Erlaubnistatbestand nach Art. 9 Abs. 2 benennen, und
bewerten, ob eine Beschränkung nach Rechtsgebiet getroffen werden soll. Das
Programm unterscheidet **nicht** nach Rechtsgebiet; eine Beschränkung wäre
organisatorisch zu treffen.

> **Was das Schutzgeländer hier ausdrücklich nicht tut:** Es filtert Gewalt,
> Sexuelles und Beleidigungen **nicht**. Die Voreinstellung von AWS hätte das
> getan — in einer Kanzlei ist genau das der Gegenstand der Arbeit.
> Eingeschaltet ist allein die Erkennung von Angriffen über den Fragetext.

---

### R7 · Zugriff innerhalb der Kanzlei

| Lage | |
|---|---|
| Heute | alle eingetragenen Nutzer haben Zugriff auf alle Akten (Stand 24.09.2026) |
| Technisch möglich | eine Beschränkung je Nutzer auf einzelne Akten; im Programm vorhanden und in den Testdaten benutzt |
| Die Anmeldung | ist im Laufwerks- und Schnittstellenbetrieb **kein Kennwort**, sondern eine Kennung. Wer am Rechner sitzt, kann eine andere eintragen |

**[KANZLEI 13]** — zu entscheiden: ob die Zugriffsbeschränkung je Bearbeiter
eingeführt wird, und ob der Schutz des Windows-Kontos als Zugangsschutz genügt.
Die Entwicklung kann dazu nur sagen, was ist, nicht was reicht.

---

### R8 · Auskunft, Berichtigung, Löschung (Art. 15 bis 17)

| Verlangen | Wie es bedient wird |
|---|---|
| Auskunft | Was im Aktengedächtnis liegt, ist in der Oberfläche **im Wortlaut** einsehbar — Lebenssachverhalt, Zeitstrahl, frühere Fragen, mit Fundstellen |
| Berichtigung | Einzelne Einträge lassen sich entfernen; die Akte in jur\|nodes bleibt die führende |
| Löschung | gezielt je Dokument oder je Frage-Antwort-Runde, oder vollständig über den Abschluss |
| Nachweis der Verarbeitung | der Nachweis nennt Zeitpunkt, Nutzer, Funktion, Modell, Umfang — **ohne Inhalt** |

**Eine Grenze, die genannt gehört:** Was einmal an das Modell übermittelt
wurde, lässt sich nicht zurückholen. AWS sichert zu, Eingaben nicht zu
speichern und nicht zum Training zu verwenden; mehr als diese Zusage gibt es
nicht. **[KANZLEI 14]** — in den Hinweisen an die Betroffenen zu beschreiben.

---

## 5. Was das Programm von sich aus verweigert

Das gehört in die Bewertung, weil es die Maßnahmen von bloßen Absichten
unterscheidet. **Das Programm startet nicht**, wenn mit echten Akten eine
dieser Bedingungen nicht erfüllt ist:

- AWS schreibt die Modellaufrufe mit, oder der Zustand ist unbekannt
- kein Schutzgeländer hinterlegt
- kein Schlüssel der Kanzlei bei dauerhafter Ablage
- eine unverschlüsselte Ablage auf dem Rechner zusammen mit echten Akten
- eine Region außerhalb der EU

Das ist keine Warnung, sondern ein Abbruch — geprüft in `tests/test_config.py`.

**1562 automatische Prüfungen** halten diese und die übrigen Zusagen
(Stand 05.10.2026).

---

## 6. Organisatorische Maßnahmen — offen

| | |
|---|---|
| **[KANZLEI 15] · Schulung** | Wer das Programm bedient, muss wissen, dass jede Ausgabe zu prüfen ist und dass eine Fundstelle nur sagt, *worauf* ein Satz beruht — nicht, dass sie ihn trägt. Zugleich die KI-Kompetenz nach Art. 4 KI-VO: eine Stunde, dokumentiert |
| Nutzerverwaltung | siehe R7 |
| Kostengrenze | 100 USD im Monat, meldet und bremst nicht |
| Weitergabe von Befunddateien | Die Prüfprogramme schreiben Dateien ohne Akteninhalt; ein Blick vor dem Weitergeben bleibt vorgesehen |

---

## 7. Verbleibendes Risiko und Konsultation

**[KANZLEI 17]** — vollständig offen, weil es die Bewertung selbst ist:

1. Wie hoch ist das verbleibende Risiko nach den Maßnahmen?
2. Ist es tragbar, oder ist die Aufsichtsbehörde nach Art. 36 zu konsultieren?
3. Ist der Datenschutzbeauftragte beteiligt worden (Art. 35 Abs. 2)?
4. Wann wird die DSFA überprüft (Art. 35 Abs. 11)?

> **Ein Vorschlag zur vierten Frage, keine Vorgabe:** Die Unterlage ist zu
> überprüfen, sobald sich eines dieser vier Dinge ändert — ein neuer
> Auftragsverarbeiter, ein neuer Speicherort, eine neue Übermittlung
> (die Texterkennung war eine), oder eine Antwort des Herstellers zu R1.

---

## 8. Die siebzehn offenen Stellen auf einen Blick

| Nr. | Was zu entscheiden ist | Abschnitt |
|---|---|---|
| 1 | Ist eine DSFA erforderlich? | 1 |
| 2 | Ist der Umfang „umfangreich" im Sinne der Norm? | 1 |
| 16 | Welche Muster-Liste der Aufsichtsbehörden gilt? | 1 |
| 3 | Verhältnismäßigkeit insgesamt | 3 |
| 4 | Modell auf eigener Hardware als milderes Mittel? | 3.2 |
| 5 | Einstufung der acht Risiken | 4 |
| 6 | R1: Verletzung nach Art. 4 Nr. 12? Meldung nach Art. 33? | R1 |
| 7 | Wann wird die Fallkopie gelöscht? | R3 |
| 8 | AV-Vertrag: Datum, Fassung, Ablage | R4 |
| 9 | Verschwiegenheitsverpflichtung § 43e Abs. 3 BRAO | R4 |
| 10 | Dokumentation der Dienstleisterauswahl § 43e Abs. 2 | R4 |
| 11 | Regionen des Geländerprofils — bei AWS erfragen | R5 |
| 12 | Erlaubnistatbestand Art. 9 Abs. 2; Beschränkung nach Rechtsgebiet? | R6 |
| 13 | Zugriffsbeschränkung je Bearbeiter? Zugangsschutz? | R7 |
| 14 | Was den Betroffenen über die Übermittlung gesagt wird | R8 |
| 15 | Schulung und KI-Kompetenz nach Art. 4 KI-VO | 6 |
| 17 | Verbleibendes Risiko, Art. 36, Beteiligung des DSB, Überprüfungsfrist | 7 |

---

## Woher die Angaben stammen

| Quelle | Inhalt |
|---|---|
| `DSFA-ANGABEN.md` | alle technischen Werte, mit Datum und Fundstelle |
| `VERARBEITUNGSVERZEICHNIS-ENTWURF.md` | die Beschreibung nach Art. 30 |
| `SICHERHEIT.md` | die 16 Grundsätze und das Löschkonzept |
| `MORGEN.md` | der Befund zum Korrespondenzordner vom 05.10.2026 |
| `infra/IAM.md` | die Zugriffsrichtlinie im Wortlaut |

**Bei Widerspruch gilt `DSFA-ANGABEN.md`** — dort steht, was gemessen wurde,
und an welchem Tag.

Dieser Entwurf ist keine Rechtsberatung.
