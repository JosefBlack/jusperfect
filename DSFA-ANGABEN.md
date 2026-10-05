# Technische Angaben für die Datenschutz-Folgenabschätzung

**Das ist nicht die DSFA.** Die schreibt die Kanzlei; sie ist Handgriff D in
`MORGEN.md`, und ihre Grundlage steht im Löschkonzept in `SICHERHEIT.md`.

Diese Datei ist das Sammelblatt davor: die technischen Werte, die in der DSFA
und im Verarbeitungsverzeichnis benannt werden müssen, jeder mit dem Datum
seiner Feststellung und der Stelle, an der er nachzulesen ist. Sie steht
getrennt, weil ein Wert, den man beim Einrichten sieht und nicht aufschreibt,
später nur noch zu erraten ist — und weil `SICHERHEIT.md` geschützt ist und
nicht beiläufig wachsen soll.

**Wer hier etwas einträgt:** nur, was tatsächlich eingerichtet wurde, mit
Datum. Keine Absichten, keine Vorschläge. Was noch offen ist, steht unten
unter „Noch nicht festgestellt".

---

## Verarbeitung im Modell

| | |
|---|---|
| Anbieter | AWS Bedrock, Auftragsverarbeiter |
| Region | `eu-central-1` (Frankfurt) |
| Modelltraining | findet nicht statt |
| Modellkennungen | tragen den Vorsatz `eu.`, gesetzt in `jusperfect/config.py::_modellkennung` |

Der Vorsatz `eu.` bedeutet ein **EU-Inferenzprofil**: Die Anfrage kann auf
mehrere EU-Regionen verteilt werden, nicht nur auf Frankfurt. Das ist in der
DSFA zu beschreiben und steht so auch in `SICHERHEIT.md`, Grundsatz 9.

Was das Modell zu sehen bekommt, ist auf drei Dinge begrenzt: Systemanweisung,
Material (ausgewählte Passagen) und Aufgabe. Dateien, Dateinamen und
Nutzerkennungen erreichen es nicht — `jusperfect/providers/bedrock.py`,
Kopfkommentar.

---

## Schutzgeländer (Bedrock Guardrail)

Eingerichtet am 23.09.2026 in der Bedrock-Konsole, Region Frankfurt.

| | |
|---|---|
| Name | `jusperfect-kanzlei` |
| Fassung | Arbeitsstand `DRAFT` (keine veröffentlichte Version) |
| **Regionsübergreifende Verarbeitung** | **`eu.guardrail.v1:0`** |
| Stufe der Filter | Standard |
| Filter für schädliche Kategorien | aus (Hass, Beleidigungen, Sexuelles, Gewalt, Fehlverhalten) |
| Filter für Prompt-Angriffe | an, hohe Stufe, Aktion BLOCK |
| Abgelehnte Themen | keine |
| Obszönitätsfilter und Wortlisten | aus |
| Filter für sensible Informationen (PII) | keine |
| Kontextuelle Erdungsprüfung | aus |
| Automated Reasoning | aus |

**`eu.guardrail.v1:0` ist der Wert, auf den es hier ankommt.** Der Vorsatz
`eu.` sagt, dass die Geländer-Prüfung im europäischen Raum bleibt, ebenso wie
die Modellaufrufe. AWS beschreibt das in der Konsole als „across Regions
within your geography"; eine Liste der einbezogenen Regionen nennt es dort
nicht. Wer die Angabe genauer braucht, muss sie bei AWS erfragen.

**Zwischenstand vom 01.10.2026 — ausdrücklich NICHT gesichert.** Eine Suche im
Netz nennt für die europäische Geografie der regionsübergreifenden
Verarbeitung diese Zielregionen: Irland (`eu-west-1`), Frankfurt
(`eu-central-1`), Paris (`eu-west-3`), Mailand (`eu-south-1`), Spanien
(`eu-south-2`), Stockholm (`eu-north-1`), dazu Zürich. Dieselbe Quelle sagt,
dass in den Zielregionen keine Kundendaten gespeichert werden.

**Diese Angabe ist für eine DSFA so nicht verwendbar**, und zwar aus drei
Gründen:

1. Die Seiten von AWS selbst (`docs.aws.amazon.com`, `aws.amazon.com`) waren
   aus der Entwicklungsumgebung nicht erreichbar; gelesen wurde eine
   Zusammenfassung, nicht die Quelle.
2. **Die Regionsliste hängt am Modell**, nicht an der Geografie allein. Was für
   ein Modell gilt, gilt nicht ohne Weiteres für ein anderes — und schon gar
   nicht ohne Weiteres für das *Geländer*-Profil `eu.guardrail.v1:0`.
3. Zürich liegt in der **Schweiz**, also außerhalb der EU und des EWR. Trifft
   die Angabe zu, wäre das für den Eintrag zum Drittlandbezug erheblich. Gerade
   deshalb darf sie nicht aus zweiter Hand übernommen werden.

**Zu beschaffen ist sie beim AWS-Support oder aus der Dokumentation zu den
Inferenzprofilen**, und zwar ausdrücklich für `eu.guardrail.v1:0` und für die
drei Modellkennungen, die das Programm benutzt. Bis dahin bleibt es bei dem
Satz darüber: AWS nennt die Regionen in der Konsole nicht.

**Zwei Berechtigungen, nicht eine.** Der Benutzer `jusperfect-test` brauchte
`bedrock:ApplyGuardrail` auf **zwei** Ressourcen, sonst wies AWS jeden Aufruf
mit Geländer ab:

```
arn:aws:bedrock:eu-*:<Kontonummer>:guardrail/*
arn:aws:bedrock:eu-*:<Kontonummer>:guardrail-profile/*
```

Die zweite Zeile ist die Folge der regionsübergreifenden Verarbeitung: Mit
`eu.guardrail.v1:0` prüft AWS zusätzlich den Zugriff auf das Profil. Mit nur
der ersten Zeile blieb die Ablehnung bestehen; mit beiden lief es. Festgestellt
am 23.09.2026, durch Ausprobieren in dieser Reihenfolge.

`infra/iam-nur-claude.json` führt keine der beiden. Die Datei ist geschützt.

**Die Probe ist durchgelaufen.** Am 23.09.2026 hat der Modell-Testlauf alle
fünf erfundenen Sätze durchgelassen — Bausache, Kündigungsschutz,
Körperverletzung, Beleidigung, Familien- und Sexualstrafrecht. Die Filter
halten die Sprache einer Akte also nicht an. Das war die Bedingung dafür,
mit echten Akten anzufangen.

**Warum die Inhaltsfilter aus sind:** In einer Kanzlei sind Gewalt,
Beleidigung und Sexuelles der Gegenstand der Arbeit, nicht der Missbrauch.
Eine Antwort, in der Mandantin, Gegner und Zeuge geschwärzt sind, ist
wertlos. Die Begründung im Einzelnen steht in `AWS-EINRICHTEN.md`, Schritt 9.

**Was durch das Geländer geht:** nur die Frage oder der Auftrag des Nutzers
und die Antwort des Modells. Das Aktenmaterial geht daran vorbei —
`jusperfect/providers/bedrock.py`, Zeile 165 (`guardContent` umschließt allein
die Aufgabe). Für die DSFA heißt das: Was regionsübergreifend geprüft wird,
ist weniger als das, was das Modell ohnehin sieht.

---

## Texterkennung für gescannte Dokumente — eingeschaltet am 02.10.2026

Für die DSFA ist dies der Abschnitt, der die zweite Übermittlung an AWS
beschreibt. **Ein neuer Auftragsverarbeiter entsteht nicht** — es ist derselbe
wie für die Texte (Amazon Web Services EMEA SARL, Region `eu-central-1`,
Frankfurt am Main), und derselbe Auftragsverarbeitungsvertrag trägt ihn.

| | |
|---|---|
| Dienst | Amazon Textract, `DetectDocumentText` |
| Region | `eu-central-1` (Frankfurt am Main) |
| Rechtsgrundlage der Berechtigung | `textract:DetectDocumentText` in der Richtlinie `jusperfect-nur-claude`, eingesetzt am 02.10.2026 |
| Übermittelt wird | **ein Bild je Seite**, erzeugt auf dem Rechner der Kanzlei |
| Dauerhafte Speicherung bei AWS | **keine** — weder S3 noch ein anderer Ablageort wird benutzt |
| Rückgabe | nur erkannter Text, keine Bilddatei |
| Kosten | rund 1,50 € je 1000 Seiten, getrennt vom Modell abgerechnet |
| Eingeschaltet durch | `JUSPERFECT_OCR=textract` in `START-JURNODES.bat` |
| Weg zurück | dieselbe Zeile auf `aus`; gescannte Blätter bleiben dann ungelesen |

**Warum kein Ablageort entsteht, und warum das für die DSFA erheblich ist.**
Textract nimmt ein PDF nur über einen S3-Bucket an; ein Bild dagegen
unmittelbar. Das Programm wandelt deshalb jede Seite auf dem Rechner der
Kanzlei in ein Bild um (PDFium, dieselbe Maschine, mit der Chrome PDFs
anzeigt). Damit wird Akteninhalt bei AWS **verarbeitet**, aber nicht
**gespeichert** — es entfällt ein Ort, der sonst einzurichten, zu
verschlüsseln, mit einer Löschfrist zu versehen und hier zu nennen wäre.

Übrig bleibt ein einziger Ausnahmefall: ein PDF, das sich nicht öffnen lässt
(beschädigt oder kennwortgeschützt). Dafür ist der Weg über S3 vorgesehen,
aber **nicht eingerichtet**; das Programm sagt dann, was fehlt, und liest den
Rest der Akte weiter.

**Belegt am echten Dienst.** `TEXTERKENNUNG-PRUEFEN.bat` schickt ein selbst
gebautes Blatt mit einem bekannten Wort und prüft, ob es zurückkommt. Lauf in
der Kanzlei am 02.10.2026: *„Texterkennung arbeitet."*

**Was in der DSFA noch zu bewerten ist** (Kanzlei): ob die Erkennung
gescannter Schriftstücke besondere Kategorien nach Art. 9 DSGVO in größerem
Umfang erfasst als die Textdokumente — Rückscheine und Vollmachten regelmäßig
nicht, ärztliche Unterlagen in einer Arzthaftungssache sehr wohl.

---

## Kostenüberwachung bei AWS — eingerichtet am 02.10.2026

| | |
|---|---|
| Budget | `jusperfect-monatlich`, 100 USD im Monat |
| Meldung an | die E-Mail-Adresse des Kontoinhabers |
| Zusätzlich | AWS Cost Anomaly Detection, von AWS selbst eingerichtet, Schwelle 100 USD |

Beides **meldet nur und bremst nicht**; eine harte Abschaltung bietet AWS
nicht an. Gemessen liegen die Kosten bei wenigen Euro im Monat (siehe „Was
eine Akte kostet"), die Schwelle ist also ein Riegel gegen einen Ausreißer und
keine Frühwarnung. Wer früher gewarnt werden will, setzt den Betrag im Budget
herunter.

---

## Dauerhafte Ablage (Aktengedächtnis)

Wo die Fallkopie liegt, hängt von der Einstellung `JUSPERFECT_GEDAECHTNIS` ab.
Beim Laufwerksweg, den die Kanzlei am 22.09.2026 gewählt hat, gilt `akte`:

| | |
|---|---|
| Ablageort | in der Akte selbst, also bei jur\|nodes |
| Zweiter Aufbewahrungsort | keiner |
| Sicherung und Löschung | erfassen die Fallkopie mit |

Gesetzt in `START-KANZLEI.bat`. Die Einstellung `lokal` ist mit echten Akten
unzulässig und wird vom Programm abgewiesen.

### Die Ablage in AWS — eingerichtet am 28.09.2026, **eingeschaltet am 05.10.2026**

Für den Weg über die Schnittstelle, den die Kanzlei seit dem 23.09.2026 geht,
ist `akte` nicht brauchbar: jur|nodes ersetzt eine vorhandene Datei nicht,
sondern weist sie ab. Das Gedächtnis ist deshalb seit dem 25.09.2026
abgeschaltet und wandert nach AWS.

**Seit dem 05.10.2026 ist es in Betrieb.** Die Kanzlei hat an diesem Tag die
erste echte Akte vollständig eingelesen (55 Dokumente). Damit liegt erstmals
dauerhaft Akteninhalt außerhalb von jur|nodes — das ist der Umstand, der die
Rechtsdokumentation auslöst.

Die Werte, damit sie nicht erraten werden müssen:

| | |
|---|---|
| Ablageort | S3-Bucket `dortschy-thunert-jusperfect-aktengedaechtnis` |
| Region | `eu-central-1` (Frankfurt) |
| Bucket-Typ | Allzweck, globaler Namespace |
| Öffentlicher Zugriff | vollständig blockiert (alle vier Einstellungen) |
| Versionierung | aus — was gelöscht wird, soll gelöscht sein |
| Verschlüsselung | SSE-KMS mit dem Schlüssel der Kanzlei, Bucket-Schlüssel an |
| KMS-Schlüssel | Alias `jusperfect-kanzlei`, Kennung `cf389440-c627-488d-8104-4989a1393a5d` |
| Schlüsselart | symmetrisch, nur Ver- und Entschlüsseln, **Single-Region** — kein Schlüsselmaterial verlässt Frankfurt |
| Schlüsselverwalter | keine eigenen; nur der Kontoinhaber über die Standardanweisung der Schlüsselrichtlinie |
| Schlüssellöschung durch Verwalter | nicht erlaubt |
| Rechte des Programms | `jusperfect-gedaechtnis`, angefügt an den Benutzer `jusperfect-test`: `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` auf den Bucketinhalt, `s3:ListBucket` auf den Bucket, `kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey` auf genau diesen Schlüssel |
| Objektnamen | `akten/<SHA-256 der Aktenkennung>/gedaechtnis.json` — **kein Aktenzeichen** in Verwaltungsdaten |
| Inhalt | Lebenssachverhalt, Zeitstrahl, frühere Fragen mit belegten Antworten (die letzten 100), ausgelesene Dokumenttexte, seit dem 05.10.2026 zusätzlich die zuletzt gelaufene Aktenanalyse |
| Obergrenzen | 100 Frage-Antwort-Runden, 500 Zeitstrahleinträge (`config.py`) |
| Gezielte Löschung einzelner Einträge | seit dem 05.10.2026 in der Oberfläche: ein Dokument samt allem daraus Abgeleiteten, oder eine einzelne Frage-Antwort-Runde |
| Nachgewiesen am 28.09.2026 | `GEDAECHTNIS-AWS-PRUEFEN.bat`: Ablegen, Zurücklesen Zeichen für Zeichen, Entfernen — alle drei bestanden |

**Was das für die Unterlage bedeutet.** Mit dem Einschalten legt jusperfect
erstmals dauerhaft **Akteninhalt** außerhalb von jur|nodes ab — Mandatsgut,
kein Protokoll. Derselbe Auftragsverarbeiter wie für die Verarbeitung (AWS
Frankfurt), also **kein neuer AV-Vertrag**; aber Zweck, Kategorien,
Speicherdauer, Empfänger und Betroffenenrechte müssen es nennen.

Eingeschaltet ist es über `JUSPERFECT_GEDAECHTNIS=aws` samt Bucket und
Schlüssel in `START-JURNODES.bat`. **Ausgeschaltet wird es mit derselben Zeile
auf `aus`;** was bereits abgelegt ist, bleibt dann liegen und ist über den
Abschluss der Akte oder einzeln über „vergessen" zu entfernen.

Die Angaben, die das Verarbeitungsverzeichnis dazu braucht — Zweck,
Kategorien, Speicherdauer, Empfänger, Betroffenenrechte — sind in
`SICHERHEIT.md` unter „Rechtliches Paket vor der ersten echten Akte" bereits
ausformuliert und von dort zu übernehmen.

---

## Aktenstatus und Löschfristen — eine Entscheidung der Kanzlei

### Gemessen am 02.10.2026: der Bestand führt zwei Wörter

`JURNODES-PRUEFEN.bat` hat 300 Akten des echten Bestands angesehen und gezählt,
welche Wörter im Feld `recordStatus` vorkommen:

| Wort | Akten | Wie das Programm es führt |
|---|---|---|
| `archived` | 290 | **archiviert** — abschlussreif |
| `active` | 10 | **laufend** — es geschieht nichts |

**Mehr führt der Bestand nicht.** Damit ist die Frage beantwortet, die seit dem
28.09.2026 für Ziffer 6.2 offenstand: Die Zuordnung des Programms ist für den
tatsächlich benutzten Wortschatz vollständig.

**Eine Lücke war trotzdem da und ist geschlossen.** Bis zum 02.10.2026 kannte
das Programm nur die beiden Archivwörter; **jedes** andere wurde still zu
„laufend". Für `active` war das zufällig richtig. Für ein drittes Wort, das der
Hersteller morgen einführt, wäre es falsch: Eine abgeschlossene Akte sähe aus
wie eine laufende, die Aufbewahrung liefe nie an, und niemand bekäme es zu
sehen. Seit dem 02.10.2026 wird ein unbekanntes Wort zu **„unbekannt"**, und
die Aufsicht (`services/aufsicht.py`) zeigt die Akte zur Entscheidung an.
Gelöscht wird dabei nichts.

**Was das für Ziffer 6.2 heißt.** Eine Löschung, die dem Aktenstatus folgt, ist
technisch möglich und trägt: Der Status ist über die Schnittstelle verlässlich
zu lesen, er kennt genau zwei Zustände, und ein unerwarteter dritter führt zu
einer Vorlage statt zu stillem Nichtstun. **Ob** nach Archivierung gelöscht
werden soll und nach welcher Frist, bleibt die Entscheidung der Kanzlei.



**Über das Laufwerk ist eine archivierte Akte nicht zu erkennen.** Festgestellt
am 23.09.2026: Von 2932 Akten auf `J:\Akten` hat die Laufwerksprobe keine
einzige als archiviert erkannt. Archiviert wird in jur|nodes über das Programm;
am Ordnernamen ändert sich dabei nichts. Die Ordner bleiben im Explorer
sichtbar.

Die Kanzlei hat das am 23.09.2026 ausdrücklich als hinnehmbar bezeichnet:
Archivierte Akten verschwinden in jur|nodes aus der Ansicht und lassen sich
dort wieder aktivieren.

**Was daraus für die Aufbewahrung folgt, und zwar unabhängig davon, wie man es
bewertet:**

| | |
|---|---|
| Jede Akte gilt für jusperfect dauerhaft als „laufend" | |
| Eine Löschfrist beginnt damit nie | |
| Gelöscht wird nur, was ein Mensch über den Abschlussworkflow abschließt | |

Das ist die sichere Seite — es wird nichts zu früh gelöscht. Aber das
Löschkonzept in `SICHERHEIT.md` läuft über den Laufwerksweg leer: Ein
Aktengedächtnis bleibt liegen, bis jemand die Akte in jusperfect ausdrücklich
abschließt. **Für die DSFA heißt das: Die Speicherdauer der Fallkopie ist der
Abschluss durch den Bearbeiter, nicht der Aktenstatus in jur|nodes.**

Über die REST-Schnittstelle wäre der Status verfügbar: `recordStatus` am
Datensatz, dazu `archivedDate` und `archivedNumber`
(jur|nodes API 1.0.1, `GET /record`). Sobald die Anbindung steht, ist diese
Lücke geschlossen und die Angabe oben zu berichtigen.

---

## Was eine Akte kostet — die erste Messung am echten Bestand

Am 23.09.2026 wurde über die REST-Schnittstelle die erste echte Akte geöffnet
und eine Frage gestellt. Der Kostenzähler des Programms nennt:

| | |
|---|---|
| Umfang der Akte | 42 Dokumente, 160.000 Zeichen |
| **Erste Frage** | **rund 0,23 €** |
| Jede weitere Frage in derselben Sitzung | rund 0,04 € |

**Warum die zweite Frage ein Sechstel kostet:** Das Material wird beim ersten
Mal voll bezahlt und danach zum Cache-Preis. Der Cache lebt aber nur Minuten —
am nächsten Tag beginnt es wieder bei 0,23 €.

**Das ist der Grund für das Aktengedächtnis**, und die Zahl sagt, was seine
Abwesenheit kostet: Jede neue Sitzung an derselben Akte zahlt den vollen
Betrag noch einmal. Es ist derzeit ausgeschaltet (`JUSPERFECT_GEDAECHTNIS=aus`
in `START-JURNODES.bat`), weil über die Schnittstelle nicht geklärt ist, ob
eine erneut abgelegte Datei die vorherige ersetzt.

**Eine frühere Schätzung war um den Faktor zweihundert zu hoch.** Die
Laufwerksprobe hatte „rund 18 MB je Akte" gemeldet und das mit dem Textpreis
verglichen; daraus liessen sich über fünfzig Euro je Akte ausrechnen. Gemessen
sind es 23 Cent. Der Unterschied ist der Bildanteil: Ein eingescanntes PDF ist
fast ganz Bild, und der Text darin ist ein Bruchteil davon.

---

## Wer Zugang hat — und woraus der Schutz besteht

Aufgenommen am 23.09.2026 auf die Frage der Kanzlei: „Inwiefern sind die Daten
gesichert? Muss der Benutzer eingeloggt sein, um die API ansprechen zu können?"

### Die Antwort auf die zweite Frage lautet: nein

**Der jur|nodes-Zugangsschlüssel wirkt ohne Anmeldung.** Er hängt am
API-Zugang, nicht an einer Person und nicht an einem Gerät. Wer ihn hat, hat
genau die Rechte, die beim Anlegen angekreuzt wurden — auf jedem Rechner, zu
jeder Zeit, ohne dass jemand in jur|nodes angemeldet sein müsste.

Für die DSFA ist das der entscheidende Satz: **Der Schlüssel ist der Zugang.**
Nicht die Person, nicht der Arbeitsplatz.

| Was ihn begrenzt | |
|---|---|
| Die Bereiche | Nur die angekreuzten. Fremde Module (beA, E-Mail, Rechnungen, Notariat) sind nicht erteilt. |
| Das Löschen | Nicht erteilt, und jusperfect löscht über die Schnittstelle auch nichts. |
| Der Widerruf | Ein neuer Schlüssel in jur\|nodes. Es gibt keinen anderen wirksamen Weg. |

**Aufbewahrt** wird er in der Umgebung des Windows-Kontos, eingetragen über
`JURNODES-ZUGANG.bat`. Er steht in keiner Datei des Programmordners und
deshalb in keiner ZIP, die weitergegeben wird.

### Die Anmeldung in jusperfect ist kein Kennwort

Das steht so auf der Anmeldeseite, und es ist keine Floskel: Wer an diesem
Rechner sitzt, kann jeden Namen aus `nutzer-kanzlei.json` wählen, auch den
eines Anwalts. Die Auswahl leistet zweierlei — und schützt nichts davon:

- **Sie schreibt den Namen in den Verarbeitungsnachweis.** Jeder Modellaufruf
  hinterlässt eine Zeile mit Zeitpunkt, Akte, Modell, Tokens, Kosten und
  Nutzer — ohne Akteninhalt. Das ist die Grundlage für die Frage, wer wann
  was verarbeiten liess.
- **Sie entscheidet, welche Akten sichtbar sind.** Stand 23.09.2026 sehen alle
  neun Einträge alle Akten; die Kanzlei hat das so festgelegt.

**Der eigentliche Schutz liegt davor:** wer an den Rechner kommt. Windows-
Anmeldung, verschlossener Raum, Bildschirmsperre. Das ist eine organisatorische
Massnahme und gehört als solche in die DSFA.

### Was technisch gesichert ist

| | |
|---|---|
| **Übertragung** | Ausschliesslich `https`. Eine Adresse ohne `https` weist das Programm ab (`http_adapter.py`). |
| **Verarbeitung** | AWS Bedrock, EU. Kein Modelltraining. Die Mitschrift der Modellaufrufe muss aus sein — sonst startet das Programm nicht (`modellprotokoll.py`). |
| **Was hinausgeht** | Systemanweisung, ausgewählte Passagen, Frage. Keine Dateien, keine Dateinamen, keine Nutzerkennungen. |
| **Dauerhaft abgelegt** | Genau eine Datei je Akte — das Aktengedächtnis, im Dateiordner der Akte in jur\|nodes. Kein zweiter Ort. |
| **Protokoll** | Nie Akteninhalt. Felder wie `text`, `frage`, `antwort`, `passagen` werden aktiv zurückgewiesen (`security/protokoll.py`). |
| **Zurückgeschrieben** | Nur ein Vermerk nach ausdrücklicher Freigabe, gebunden an Nutzer, Akte, Textprüfsumme und Prozesslauf (HMAC). |
| **Gelöscht** | Über die Schnittstelle nie. |

### Was nicht gesichert ist, und das gehört ebenso in die Unterlage

- **Das Aktengedächtnis liegt unverschlüsselt** in der Akte — so wie die Akte
  selbst. Wer die Akte lesen darf, liest es mit.
- **Die Namensauswahl schützt nichts** (siehe oben).
- **Der Schlüssel ist ein Generalschlüssel** für die erteilten Bereiche.
- **Die AWS-Zugangsdaten** liegen je Rechner in `%USERPROFILE%\.aws`. Es gilt:
  ein eigener IAM-Benutzer je Rechner, damit sich ein einzelner zurückziehen
  lässt und im AWS-Aufrufprotokoll steht, von wo ein Aufruf kam
  (`AWS-EINRICHTEN.md`, „Ein zweiter Rechner").

---

## Fremde Schriftstücke über den Korrespondenzordner — Befund vom 05.10.2026

**Für die DSFA der wichtigste Einzelbefund des Tages.** Er betrifft nicht das
Programm, sondern die Schnittstelle von jur|nodes — und er betrifft das
Mandantengeheimnis.

In der Bausache X-100-2026 standen in der Arbeitsakte drei Schriftstücke aus
einer fremden Verkehrsunfallsache. Gemessen an der echten Schnittstelle am
05.10.2026, an **drei** Akten mit demselben Ergebnis:

| | |
|---|---|
| Der Dateiordner | passt jedesmal zur Akte; befüllt ab dem Anlagedatum |
| Der Korrespondenzordner | passt **nie**; niedrige Nummer, befüllt durchweg 2022/23, unabhängig vom Anlagedatum der Akte |
| In der Akte X-100-2026 | 17 von 55 Dokumenten stammten aus dem Korrespondenzzweig |
| In der Oberfläche von jur\|nodes | sind diese Schriftstücke unter dieser Akte **nicht zu finden** |

Das Feld `correspondenceFolderId` zeigt offenbar nicht auf die Korrespondenz
**dieser** Akte. Worauf dann, weiß nur der Hersteller; die Anfrage ist
formuliert und abzuschicken.

**Was daraus folgt — und was das Programm bereits getan hat:**

- **Der Korrespondenzordner wird seit dem 05.10.2026 nicht mehr gelesen**
  (`JUSPERFECT_KORRESPONDENZ` aus, Vorgabe). Damit fehlt die Korrespondenz;
  das ist die sichere Richtung. Fremde Schriftstücke in einer Arbeitsakte sind
  teurer als fehlende.
- **Das Programm hat richtig gearbeitet.** `GET /record` nennt für diese Akte
  selbst diesen Ordner; der Durchlauf hat die Akte an keiner Stelle verlassen.
  Das prüft die Probe seitdem ausdrücklich.
- **Für die DSFA erheblich:** Hätte das Aktengedächtnis zu diesem Zeitpunkt
  schon gearbeitet, wären die 17 fremden Dokumente dauerhaft abgelegt worden.
  Das ist das Risiko, das die Unterlage unter „Vermengung von Mandaten"
  beschreiben muss — und zugleich der Grund, warum eine gezielte Löschung
  einzelner Einträge gebraucht wird (seit dem 05.10.2026 vorhanden).

**[KANZLEI]** — zu entscheiden: ob die betroffenen Akten in jur|nodes zu
prüfen sind und ob eine Meldung nach Art. 33 DSGVO in Betracht kommt. Aus
Sicht der Entwicklung ist **kein** Datenabfluss nach außen festzustellen: Die
Schriftstücke gehören dem eigenen Aktenbestand der Kanzlei, und die
Verarbeitung lief im selben AWS-Konto. Ob eine kanzleiinterne Vermengung von
Mandaten meldepflichtig ist, bewertet die Kanzlei.

---

## Noch nicht festgestellt

- **Die Regionen, auf die `eu.guardrail.v1:0` verteilt.** AWS nennt sie in der
  Konsole nicht; dort steht nur „within your geography".
- **Das Schreibrecht auf dem Aktenlaufwerk.** Die Laufwerksprobe vom
  23.09.2026 meldet für `J:\Akten` `PermissionError`. Über das Laufwerk könnte
  jusperfect heute weder einen freigegebenen Vermerk zurückschreiben noch das
  Aktengedächtnis in der Akte ablegen. Über die REST-Schnittstelle
  (`POST /record/note`, `POST /file-system/add-file`) wäre beides ohne
  Laufwerksrecht möglich.
- **Was die Texterkennung kostet.** Der Bestand umfasst rund 78.000 Dateien,
  davon über 9.000 Bilddateien; dazu eingescannte PDF, die von außen nicht zu
  erkennen sind. Sie brauchen AWS Textract, das je Seite und getrennt vom
  Modell abgerechnet wird. Die Messung unten enthält diesen Posten **nicht**:
  Aus den 42 Dokumenten kam Text, ohne dass Textract eingeschaltet war.
