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
**zweiundzwanzig** — Nr. 21 und Nr. 22 sind am 14.10.2026 dazugekommen, beim
Lesen des AWS-Vertragswerks —, und sie stehen am Ende noch einmal in einer
Liste. Vier davon sind erledigt: **Nr. 18** am 05.10.2026, **Nr. 19**,
**Nr. 20** und **Nr. 21** am 14.10.2026; bei **Nr. 10** liegt seit dem
14.10.2026 das Material vor und fehlt nur noch die Bewertung. Sie bleiben stehen und durchgestrichen — eine
Stelle, die verschwindet, sieht aus, als hätte es sie nie gegeben.

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
| Gescannte Seite erkennen | **ein Bild je Seite** | AWS Textract, Frankfurt. Verarbeitet; **weder gespeichert noch zur Verbesserung der AWS-KI-Dienste verwendet** — wirksame Abmelderichtlinie seit 14.10.2026, siehe `[KANZLEI 19]` |
| Frage, Analyse, Entwurf | **die ausgewählten Passagen** als Text | AWS Bedrock, Frankfurt, über das EU-Inferenzprofil. **Nicht zum Training verwendet** (Service Terms 50.12, Stand 15.09.2026) und für das genutzte Modell **auch nicht zur Missbrauchserkennung aufbewahrt** — anders als bei den namentlich gelisteten Modellen, siehe `[KANZLEI 22]` |
| Schutzgeländer | **Frage und Antwort**, nicht der Akteninhalt | `eu.guardrail.v1:0`, verteilt auf europäische Regionen |
| Aktengedächtnis sichern | **Dokumenttexte und Abgeleitetes** | S3-Bucket der Kanzlei, Frankfurt, SSE-KMS |
| Vermerk zurückschreiben | **nur der freigegebene Text** | jur\|nodes |

**Was das Modell nicht zu sehen bekommt:** Dokumentkennungen,
Nutzerkennungen, Sitzungskennungen. Es sieht Systemanweisung, Passagen und
Aufgabe (`providers/bedrock.py`).

> **Berichtigt am 05.10.2026 nach der Zweitprüfung (Befund F11).** Hier stand
> zusätzlich „Dateinamen" und „Aktenzeichen" — **das war falsch.** Das
> **Aktenzeichen** steht in der ersten Zeile des Materials, und der
> **Dokumenttitel** in jeder Passagenüberschrift; liefert jur|nodes keinen
> Titel, ist das der **Dateiname** (`services/prompts.py`,
> `jurnodes/http_adapter.py`). Dass dem Anbieter keine gesonderten
> Metadatenobjekte übergeben werden, verhindert nicht, dass dieselben Angaben
> als Text mitgehen.
>
> ~~**[KANZLEI 18]** — zu entscheiden: ob dieser Umfang gewollt ist oder ob
> beides durch neutrale Bezeichnungen zu ersetzen ist.~~
>
> **Entschieden am 05.10.2026** (Grundlage: `F11-VORSCHLAG.md`, dort die
> Messung an vier Testakten). Seitdem gilt:
>
> * **Der Dateiname geht nicht mehr hinaus.** Aus dem Titel wird nur noch die
>   **Art** des Schriftstücks genannt — und auch die als Wort aus einer Liste
>   im Programm, nie als Text aus dem Dateinamen: `Dokument 2 – Kündigung`.
>   Erkennt die Liste nichts, heißt es nur `Dokument 2`. Die Richtung des
>   Irrtums stimmt damit: weniger Auskunft, nie mehr.
> * **Das Aktenzeichen geht nur noch beim Entwurf mit.** Ein Anschreiben trägt
>   „Unser Zeichen"; Frage, Analyse und Eingangsprüfung brauchen es nicht.
> * **Beteiligte und Kurzrubrum bleiben.** Sie gehen absichtlich hinaus: Das
>   Modell braucht die Rollen — ohne sie hat es im September die gegnerische
>   Kanzlei als Rechtsschutzversicherung geführt —, und dieselben Namen stehen
>   im Dokumenttext ohnehin.
>
> **Anonym ist die Übermittlung dadurch nicht.** Im Dokumenttext stehen
> weiterhin Namen, Beträge und Daten; das ist der Zweck der Auswertung und in
> Abschnitt 3.2 bewertet.
>
> Die Oberfläche ist unberührt: Der Dokumenttitel in der Belegkarte und über
> der Passage kommt aus dem Programm und ging nie durch das Modell.
>
> `SICHERHEIT.md` enthält dieselbe zu weite Aussage („nie Dateinamen"). Die
> Datei ist geschützt und wird nur auf ausdrückliche Anweisung geändert.

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

### 2.4 Verschlüsselung gegenüber dem Auftragsverarbeiter

*Ergänzt am 13.10.2026 auf Frage der Kanzlei. Die technische Darstellung steht
in `SICHERHEIT.md`, Abschnitt „Verschlüsselung gegenüber AWS"; hier steht, was
für die Risikobewertung daraus folgt.*

**Es ist eine sichere Umgebung mit verschlüsselter Ablage, nicht eine
Verschlüsselung, die den Auftragsverarbeiter aussperrt.** Diese Unterscheidung
trägt mehrere Risiken dieses Abschnitts, und sie wird häufig verwechselt:

| | Zustand bei AWS |
|---|---|
| Übertragung | verschlüsselt (TLS) |
| Dauerhafte Ablage (S3) | verschlüsselt mit dem KMS-Schlüssel der Kanzlei |
| **Verarbeitung im Modell (Bedrock)** | **Klartext** |
| **Verarbeitung in der Texterkennung (Textract)** | **Klartext** |

**Warum die beiden letzten Zeilen nicht anders sein können.** Ein Modell muss
den Text lesen, um ihn zu beantworten; eine Texterkennung muss das Bild sehen.
Verschlüsselter Inhalt ist für beide ohne Nutzen. Es gibt an dieser Stelle
keine Bauweise, die es anders macht — auch keine andere Software.

**Was der KMS-Schlüssel deshalb bedeutet, und was nicht.** Er schützt die
Ablage wirksam: Ohne `kms:Decrypt` auf diesen Schlüssel ist kein Objekt
lesbar, die Kanzlei verfügt allein über die Schlüsselrichtlinie, kann ihn
sperren oder löschen, und jede Entschlüsselung steht in CloudTrail. Er liegt
aber **im Dienst KMS bei AWS** — es ist der Schlüssel der Kanzlei, nicht
einer, den AWS nie gesehen hat.

> **Daraus folgt für diese Unterlage:** Die Verarbeitung ist
> **Auftragsverarbeitung** nach Art. 28 DSGVO und **nicht** ein Vorgang, dem
> durch Verschlüsselung der Personenbezug genommen wäre. Keine Maßnahme dieses
> Abschnitts darf als „AWS kann den Inhalt nicht lesen" gelesen werden. Wo in
> dieser Unterlage „verschlüsselt" steht, ist die **Ablage** gemeint.

**Die Maßnahme an der offenen Stelle ist Mengenbegrenzung, nicht
Verschlüsselung.** Zum Modell gehen die Systemanweisung, die **vom Bearbeiter
ausgewählten Passagen** und die Aufgabe — nicht die Akte (Abschnitt 2.1,
`providers/bedrock.py`). Damit ist die Auswahl im Dokumentfenster die
wirksamste Maßnahme in der Hand des Bearbeiters: Was nicht angehakt ist, sieht
das Modell nie. Sie ist in Abschnitt 3.3 als Datenminimierung geführt und
gehört in die Einweisung.

**Was von hier aus nicht belegbar ist.** Was AWS vertraglich zusagt, steht
nicht im Programm. Belegbar ist nur, *was das Programm sendet und wie es
ablegt*. Die Aufbewahrung beim Auftragsverarbeiter hängt am
Auftragsverarbeitungsvertrag und — für die KI-Dienste, die sie erfasst — an
der **AI-services-Opt-out-Richtlinie**. Sie ist seit dem 14.10.2026 für das
Konto wirksam und nachgewiesen (`[KANZLEI 19]`); deshalb sagt die
Textract-Zeile in Abschnitt 2.1 wieder „nicht gespeichert". **Für Bedrock
gilt das nicht** — die Richtlinienart erfasst es nicht, und dort trägt allein
der Auftragsverarbeitungsvertrag.

### [KANZLEI 20] — die Entscheidung über die Bauweise

**Entschieden am 14.10.2026: Es bleibt bei dieser Bauweise.** Die Kanzlei
verarbeitet weiterhin mit AWS als Auftragsverarbeiter nach Art. 28 DSGVO und
richtet ihre Maßnahmen darauf aus, statt die Verarbeitung auf eigene Hardware
zu verlegen.

**Worauf sich die Entscheidung stützt.** Belegbar ist nur, was das Programm
tut; was AWS vertraglich zusagt, steht nicht im Programm (siehe oben).

| Umstand | belegt an |
|---|---|
| Verarbeitung und Ablage in Frankfurt (`eu-central-1`); eine Region außerhalb von EU und EWR lässt das Programm nicht zu, sondern bricht ab | `jusperfect/config.py:118`, `:286`, `:629` |
| Zum Modell gehen die Systemanweisung, die vom Bearbeiter ausgewählten Passagen und die Aufgabe — **nicht die Akte** | Abschnitt 2.1, `jusperfect/providers/bedrock.py` |
| Die dauerhafte Ablage ist mit dem KMS-Schlüssel der Kanzlei verschlüsselt; über die Schlüsselrichtlinie verfügt die Kanzlei allein, jede Entschlüsselung steht in CloudTrail | Abschnitt 2.4, `SICHERHEIT.md` |
| In den Protokollen steht kein Akteninhalt; das ist nicht Vorsatz des Bearbeiters, sondern im Programm erzwungen | `jusperfect/security/protokoll.py` |
| Der Auftragsverarbeitungsvertrag mit AWS liegt vor und ist Abschnitt für Abschnitt gegen Art. 28 Abs. 3 DSGVO gelesen | Abschnitt 4, R4, „Der Auftragsverarbeitungsvertrag, Abschnitt für Abschnitt" |

**Was daran Bewertung der Kanzlei ist und kein Beleg:** dass diese
Mengenbegrenzung, diese Verschlüsselung der Ablage und diese
Nachvollziehbarkeit für Unterlagen, die dem Berufsgeheimnis unterliegen
(§ 203 StGB), angemessen sind. Das ist eine Abwägung und keine Messung;
sie steht der Kanzlei zu und ist hier als ihre Abwägung ausgewiesen.

**Was mit dieser Entscheidung ausdrücklich NICHT behauptet wird.** Drei Sätze,
die aus ihr nicht folgen und an keiner Stelle aus ihr abgeleitet werden
dürfen:

1. **Nicht**, dass AWS den Inhalt nicht lesen könne. Bedrock und Textract
   verarbeiten im Klartext; das lässt sich nicht anders bauen (Abschnitt 2.4).
2. **Nicht**, dass die Alternative geprüft und schlechter befunden worden
   wäre. Der Preis eigener Hardware an Qualität, Kosten und Betriebsaufwand
   ist **nicht gemessen** (`[KANZLEI 4]`, Gegenlesung zu Abschnitt 3.2 vom
   12.10.2026). Die Entscheidung fällt ohne diese Messung — bewusst, weil die
   Kanzlei den Aufwand der Messung nicht für verhältnismäßig hält, und nicht,
   weil das Ergebnis feststünde.
3. **Nicht**, dass die Frage der Speicherung beim Auftragsverarbeiter geklärt
   wäre. Sie steht als `[KANZLEI 19]` offen.

**Unter welcher Bedingung sie gilt.** Die Entscheidung setzte voraus, dass
`[KANZLEI 19]` eingelöst wird — die wirksame AI-services-Opt-out-Richtlinie
für das Konto, nachgewiesen und datiert. **Das ist am selben Tag geschehen**
(Abschnitt 4, `[KANZLEI 19]`): die Richtlinie ist am 14.10.2026 um 17:11 MESZ
am Konto als wirksam festgestellt und abgelegt. Die Bedingung ist damit
erfüllt — für die Dienste, die diese Richtlinienart erfasst. **Für Bedrock
ist sie es nicht**, und diese Frage trägt die Entscheidung mit: Sie steht
beim AWS-Support und ist bei Antwort hier nachzutragen.

**Wann sie neu zu treffen ist.** Wenn eines davon eintritt, ist dieser
Abschnitt neu zu schreiben und nicht fortzuschreiben:

* `[KANZLEI 19]` lässt sich nicht einlösen — AWS gibt den Nachweis nicht oder
  nur eingeschränkt;
* AWS ändert die Bedingungen für Bedrock oder Textract in der Region
  Frankfurt, insbesondere zur Verwendung von Inhalten;
* die Kanzlei verarbeitet mit dem Programm Unterlagen einer Art, die hier
  nicht bewertet ist;
* es wird eine Bauweise verfügbar, die in der Qualität trägt und ohne
  Auftragsverarbeiter auskommt — dann ist die Messung nachzuholen, die hier
  unterblieben ist.

Im Übrigen mit der Unterlage im Ganzen, jährlich.

Festgehalten für die Kanzlei Dortschy & Thunert am 14.10.2026.

Ort, Datum ........................  Unterschrift ........................

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
| Kein Akteninhalt im Protokoll | technisch erzwungen an zwei Stellen: `security/protokoll.py` weist Inhaltsfelder zurück, `fehlergrenze.py` nimmt jedem Protokolleintrag den Traceback ab. Der zweite Riegel ist seit dem 05.10.2026 da; bis dahin galt der erste nur für den eigenen Protokollkanal (Befund F01 der Zweitprüfung) |
| Nachweis nur mit Prüfsumme und Länge | `domain/models.py::Nutzungseintrag` |
| Objektnamen ohne Aktenzeichen | nur SHA-256-Ableitung |
| Auswahl der Passagen durch den Bearbeiter | zwei Fenster, Haken je Dokument |
| Vorauswahl schließt Rechnungen und RSV aus | seit 05.10.2026, `JUSPERFECT_NICHT_VORWAEHLEN` |
| Der Korrespondenzordner wird nicht gelesen | seit 05.10.2026, seit dem 06.10.2026 ganz ausgebaut; an seiner Stelle der aktenbezogene Weg des Herstellers, noch nicht eingeschaltet. Siehe Risiko R1 |

---

## 4. Die Risiken — und was ihnen entgegensteht

Acht Risiken, in der Reihenfolge, in der sie die Entwicklung für erheblich
hält. **Die Einstufung in „gering / mittel / hoch" ist bewusst leer gelassen**
([KANZLEI 5]): Sie hängt davon ab, welche Rechtsgebiete bearbeitet werden und
wie die Kanzlei das Berufsgeheimnis gewichtet.

---

### R1 · Vermengung von Mandaten

**Das größte Risiko, und es ist am 05.10.2026 eingetreten.**

Akteninhalt eines fremden Mandats wurde in die Arbeitsakte eines anderen
gelesen und ging an das Modell — in einer Akte 17 von 55 Dokumenten, an drei
Akten dasselbe Muster.

**Die Ursache liegt im Programm.** Am Abend des 05.10.2026 hat die Beschreibung
des Herstellers sie gezeigt: jur|nodes führt **zwei getrennte Ordnerbäume** mit
je eigenen Nummern — das Dateisystem und die Korrespondenz. Das Programm hat
die Nummer des **Korrespondenz**ordners an den Pfad des **Dateisystems**
geschickt. Dort gibt es diese Nummer auch; sie gehört zu einem anderen Ordner,
und zwar zu dem einer fremden Akte.

Die Fassung dieses Entwurfs von heute früh führte den Vorgang auf ein Verhalten
der Schnittstelle zurück und hielt fest, das Programm habe richtig gearbeitet.
**Das war falsch und ist hiermit berichtigt.**

| Folge für die Betroffenen | Dass Angaben aus ihrem Mandat in der Bearbeitung eines fremden Mandats auftauchen — der Kernbereich des § 203 StGB |
|---|---|
| **Was es verhindert hat** | Das Aktengedächtnis war zu diesem Zeitpunkt **aus**. Es ist nichts dauerhaft abgelegt worden |
| **Was seitdem gilt** | Der falsche Weg wird nicht mehr gegangen. Die Korrespondenz fehlt damit — die sichere Richtung |
| **Was das Programm selbst prüft** | Der Durchlauf durch die Ordner meldet ausdrücklich, wenn er die Akte verlässt |
| **Der richtige Weg** | ist seit dem 05.10.2026 belegt (`POST /correspondence/search`) und in der Probe gemessen, aber **noch nicht im Betrieb**. Erst ein Lauf an einer echten Akte zeigt, was der Server liefert |

**[KANZLEI 6]** — zu bewerten: ob dies eine Verletzung nach Art. 4 Nr. 12 ist
und ob Art. 33 greift. Aus Sicht der Entwicklung **kein Abfluss nach außen**:
eigener Aktenbestand, eigenes AWS-Konto, derselbe Auftragsverarbeiter.

**Für diese Bewertung erheblich:** Die Ursache liegt im Programm und damit beim
Verantwortlichen, nicht beim Auftragsverarbeiter und nicht beim Hersteller der
Aktenverwaltung. Umfang und Richtung des Vorgangs ändert das nicht, die
Zurechnung schon.

---

### R2 · Eine falsche Aussage wird für wahr genommen

Ein Sprachmodell erzeugt plausibel klingende Sätze. Übernimmt ein Bearbeiter
einen davon ungeprüft in einen Schriftsatz, trifft der Schaden den Mandanten.

**Was dagegen steht — und es ist die tragende Maßnahme des ganzen Programms:**

| Maßnahme | Wirkung | Nachweis |
|---|---|---|
| **Belegpflicht, fail closed** | Eine Aussage ohne Verweis auf eine mitgeschickte Passage wird **entfernt**, nicht markiert. Seit dem 05.10.2026 für **jeden** angezeigten Modelltext: Antwort, Entwurf, Kernaussage der Eingangsprüfung, Hinweise des Modells – und schon im laufenden Text, nicht erst am Ende (Befunde F04/F05 der Zweitprüfung) | `services/belegpflicht.py` |
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
| **Gezielte Löschung einzelner Einträge** | seit 05.10.2026: ein Dokument samt allem Abgeleiteten, oder eine einzelne Frage-Antwort-Runde. Bedient Art. 16 und 17 ohne Verwerfen der ganzen Fallkopie. Erfasst sind auch offene Sitzungen und verspätete Ergebnisse — ein Löschverlangen, das nur gilt, solange niemand ein zweites Fenster offen hat, wäre keines |
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
| AV-Vertrag und Hauptvertrag | liegen vor: **AWS Data Processing Addendum**, **AWS-Kundenvereinbarung** (01.06.2026), **AWS-Datenschutzhinweis** (18.05.2026) — alle drei unten gelesen; `[KANZLEI 8]` nur noch für Ablage |
| Verpflichtung zur Verschwiegenheit in Textform (§ 43e Abs. 3 BRAO) | **[KANZLEI 9]** — prüfen und dokumentieren |
| Dokumentation der Dienstleisterauswahl (§ 43e Abs. 2) | **Material beschafft am 14.10.2026** — sechs Nachweise aus AWS Artifact, siehe unten; `[KANZLEI 10]` nur noch für die Bewertung |
| Kein Modelltraining | **Kundenvereinbarung Ziffer 1.4 und 6.1** (Fassung 01.06.2026) — nicht im AV-Vertrag, siehe unten |
| Ein einziger Ausgang im Programm | `services/ausgang.py` — genau eine Stelle führt zum Modell |
| Kein zweiter Anbieter | andere sind vorbereitet, keiner angebunden |

#### Der Auftragsverarbeitungsvertrag, Abschnitt für Abschnitt

*Gelesen am 14.10.2026 am vorgelegten Stück „AWS Data Processing Addendum"
(englisch, zehn Seiten, Anlage 1 „Security Standards"). Die Abschnittsnummern
unten sind die des Vertrages.*

**Was Art. 28 Abs. 3 DSGVO verlangt, und wo es steht:**

| Verlangt | Im Vertrag |
|---|---|
| Verarbeitung nur auf dokumentierte Weisung (lit. a) | Abschn. 2; Weisung sind der Vertrag und die Einstellungen in Konsole und Schnittstelle |
| Vertraulichkeit des eingesetzten Personals (lit. b) | Abschn. 4 |
| Technische und organisatorische Maßnahmen (lit. c) | Abschn. 5 und Anlage 1 |
| Unterauftragsverarbeiter (lit. d) | Abschn. 6 — **allgemeine** Genehmigung, 30 Tage Vorankündigung |
| Unterstützung bei Betroffenenrechten (lit. e) | Abschn. 7 |
| Unterstützung bei Meldungen und Folgenabschätzung (lit. f) | Abschn. 9 und 10.4 |
| Löschung oder Rückgabe am Ende (lit. g) | Abschn. 14 — bis 90 Tage nach Vertragsende |
| Nachweise und Überprüfungen (lit. h) | Abschn. 10 und 11 |
| Drittlandübermittlung | Abschn. 12 — Standardvertragsklauseln, einbezogen durch Verweis |

**Vier Stellen, die in die Bewertung gehören und keine Formalien sind:**

1. **Abschnitt 3 ist die Stelle, auf die es bei § 203 StGB ankommt.** AWS darf
   auf Kundendaten nicht zugreifen, sie nicht verwenden und sie nicht an
   Dritte geben — außer soweit zur Erbringung des Dienstes nötig oder aufgrund
   eines rechtswirksamen behördlichen Verlangens. Beim behördlichen Verlangen
   sagt AWS zu, die Behörde an die Kanzlei zu verweisen und die Kanzlei zu
   unterrichten, **soweit nicht rechtlich untersagt**. Dieser letzte Halbsatz
   ist das verbleibende Risiko und lässt sich vertraglich nicht wegnehmen.
2. **Beim Unterauftragsverarbeiter gibt es kein Vetorecht**, nur einen
   Ausgang: kündigen, den Dienst nicht mehr nutzen, oder in eine Region
   ausweichen, in der dieser Unterauftragsverarbeiter nicht eingesetzt ist
   (Abschn. 6.1). Wer widersprechen will, muss also gehen. Das ist bei
   Hyperscalern üblich und gehört trotzdem in die Abwägung.
3. **Die Prüfung erfolgt über Berichte, nicht vor Ort.** Die Kanzlei übt ihr
   Prüfrecht aus, indem sie AWS anweist, die Prüfung nach Abschn. 10
   durchzuführen — ISO-Zertifikate und SOC-Berichte gegen eine
   Vertraulichkeitsvereinbarung (Abschn. 11). Eine eigene Besichtigung des
   Rechenzentrums gibt es nicht.
4. **Abschnitt 12.1 trägt unsere Regionswahl.** AWS verbringt Kundendaten
   nicht aus der gewählten Region — *außer soweit zur Erbringung des Dienstes
   nötig*. Genau unter diesen Vorbehalt fallen das EU-Inferenzprofil und das
   Geländerprofil, die auf mehrere europäische Regionen verteilen (R5). Die
   Regionswahl `eu-central-1` des Programms ist damit vertraglich gedeckt,
   die Verteilung innerhalb Europas ebenfalls — eine Festlegung auf **ein**
   Rechenzentrum ist der Vertrag nicht.

**[KANZLEI 21] — was in diesem Vertrag NICHT steht, und wo es stehen müsste.**
Das vorgelegte Stück enthält **kein Wort** zu Modelltraining oder zur
Verwendung von Inhalten zur Verbesserung der Dienste. Der einzige Satz in
diese Richtung ist Abschnitt 3 („nur soweit zur Erbringung des Dienstes
nötig") — allgemein gehalten, und ausdrücklich nachrangig: **Abschnitt 16
bestimmt, dass die AWS Service Terms diesem Vertrag vorgehen.** Die Zusage zu
Bedrock steht dort und nicht hier.

> **Daraus folgt für diese Unterlage:** Die Zeile „Kein Modelltraining — im
> AWS-Vertragswerk zugesichert" stand bis zum 14.10.2026 ohne Fundstelle da.
> Die Fundstelle ist noch am selben Tag beigebracht worden, aber sie steht
> **nicht hier**, sondern in der Kundenvereinbarung — siehe den nächsten
> Abschnitt. Wer nur den AV-Vertrag liest, findet sie nicht; deshalb bleibt
> dieser Hinweis stehen.

#### Die Nachweise der Prüfer

*Am 14.10.2026 aus **AWS Artifact** abgerufen und in der Datenschutzakte
abgelegt. Sie liegen bewusst **nicht** im Programmordner: Der SOC-2-Bericht
ist vertrauliche Information von AWS, und der Ordner wird weitergegeben.*

| Nachweis | Was er sagt |
|---|---|
| ISO 27001:2022 | Informationssicherheit, das Grundzertifikat |
| ISO 27017:2015 | Sicherheit in der Cloud |
| ISO 27018:2019 | Schutz personenbezogener Daten in der Cloud |
| ISO/IEC 27701:2019 | Datenschutz-Managementsystem |
| **SOC 2 Typ 2**, Berichtszeitraum **01.04.2025 – 31.03.2026** | Prüfurteil über die **Wirksamkeit** der Kontrollen, nicht nur über ihr Vorhandensein — geprüfte Kriterien: Security, Availability, **Confidentiality**, **Privacy** |
| SOC 3 | dasselbe Prüfurteil in einer Fassung, die weitergegeben werden darf |

**Wozu das trägt.** § 43e Abs. 2 BRAO verlangt, dass die Auswahl des
Dienstleisters dokumentiert ist — dass die Kanzlei ihn sich *angesehen* hat
und nicht nur beauftragt. Das ist hiermit belegbar. Der Vertrag verspricht
diese Unterlagen in seinem Abschnitt 10; Artifact ist der Weg dorthin.

**Zwei Einschränkungen, die zum Nachweis gehören:**

1. **Der SOC-2-Bericht darf nicht zitiert werden.** Die
   Vertraulichkeitsvereinbarung beim Abruf untersagt Auszüge. Deshalb steht
   aus ihm in dieser Unterlage nichts — nur, dass er vorliegt, für welchen
   Zeitraum und mit welchen Kriterien. An eine **Aufsichtsbehörde** darf er
   vollständig gehen, mit dem Antrag auf vertrauliche Behandlung; jede
   Weitergabe ist zu notieren. An Mandanten geht **SOC 3**.
2. **Der Berichtszeitraum endete am 31.03.2026.** Für die Zeit danach trägt
   der Bericht nichts. Die Lücke schließt das **SOC Continued Operations
   Letter** aus derselben Quelle. Zur jährlichen Durchsicht dieser Unterlage
   gehört, die Nachweise neu abzurufen.

**[KANZLEI 10]** — die Bewertung bleibt bei der Kanzlei: ob diese Nachweise
die Auswahl nach § 43e Abs. 2 BRAO tragen und was darüber hinaus in die Akte
soll. Das Material liegt vor; der Satz dazu fehlt.

#### Die Kundenvereinbarung und der Datenschutzhinweis

*Am 14.10.2026 nachgereicht und gelesen: die **AWS-Kundenvereinbarung**
(deutsche Fassung, Stand 01.06.2026) und der **AWS-Datenschutzhinweis**
(Stand 18.05.2026). Beide frisch von AWS abgerufen.*

**Hier steht, was im AV-Vertrag fehlte.** Ziffer 1.4 der Kundenvereinbarung
ist die tragende Stelle, und sie ist weiter als Abschnitt 3 des AV-Vertrages:
Sie gilt für **„Ihre Inhalte"** und nicht nur für personenbezogene Daten.

> „Wir werden nicht auf Ihre Inhalte zugreifen oder diese nutzen, es sei denn,
> dass dies notwendig ist, um die Services zu warten oder anzubieten oder
> erforderlich, um die Gesetze einzuhalten oder einer verbindlichen Anordnung
> einer staatlichen Stelle nachzukommen."

Dazu Ziffer 6.1: AWS erhält keine Rechte an den Inhalten; die Kanzlei stimmt
ihrer Nutzung nur zu, „um Ihnen und allen Endnutzern die Services zur
Verfügung zu stellen". Ein Modell mit Akteninhalt zu trainieren ist keines von
beidem. **Damit hat die Zeile „kein Modelltraining" eine Fundstelle** — sie
steht in der Kundenvereinbarung und nicht im AV-Vertrag, und sie ist eine
allgemeine Nutzungsschranke und keine Zusage zu einem bestimmten Dienst.

**Drei weitere Sätze derselben Ziffer, die hierhergehören:**

1. AWS gibt Inhalte **nicht an staatliche Stellen oder Dritte** weiter und
   verlagert sie nicht aus den gewählten Regionen — außer soweit im Einzelfall
   gesetzlich oder durch verbindliche Anordnung gefordert. Über eine solche
   Anordnung wird die Kanzlei unterrichtet, **„es sei denn, dass dies uns
   gesetzlich oder durch die Anordnung einer staatlichen Stelle untersagt
   ist"**. Das ist dasselbe verbleibende Risiko wie im AV-Vertrag, nur in
   anderen Worten; es ist nicht wegzuverhandeln und steht hier als bekannt.
2. **„Die Datenschutzerklärung ist auf Ihre Inhalte nicht anwendbar."** Das
   ist ein Satz, der eine Fehllesung verhindert: Wer den Datenschutzhinweis
   allein liest, findet dort als Zweck „die AWS-Angebote zu verbessern und zu
   entwickeln" und schließt daraus auf die Akte. Falsch — der
   Datenschutzhinweis sagt es selbst, gleich auf seiner ersten Seite: Er
   „gilt nicht für ‚Inhalte', die von unseren Kunden unter Nutzung von
   AWS-Angeboten in Verbindung mit einem AWS-Account verarbeitet, gespeichert
   oder gehostet werden." Er betrifft die **Account-Informationen** —
   Anschrift, Abrechnung, Nutzungsmessung —, nicht den Akteninhalt.
3. **Vertragspartei ist für Kunden mit Sitz in der EU die Amazon Web Services
   EMEA SARL in Luxemburg** (Ziffer 12 (e)). Für sie gilt zusätzlich, dass
   Haftung für grobe Fahrlässigkeit und Vorsatz nicht beschränkt ist.

> **Eine Falle in Ziffer 6.5, die den Umgang mit AWS betrifft und nicht die
> Technik.** Wer AWS einen **Vorschlag** macht — eine Anregung, eine
> Fehlermeldung mit Beispiel, einen Verbesserungswunsch —, überträgt AWS
> daran unwiderruflich sämtliche Rechte, „ohne jegliche Beschränkung".
> Daraus folgt eine Hausregel: **In eine Support-Anfrage oder einen
> Verbesserungswunsch an AWS gehört niemals Akteninhalt**, auch kein
> anonymisierter Ausschnitt und kein Bildschirmfoto mit Text. Der Support-Text
> in `AWS-ZWEI-HANDGRIFFE.md` ist danach gebaut.

> **Und ein Vorbehalt, der für beide Stücke gilt:** Sie liegen in deutscher
> Übersetzung vor, und beide tragen oben den Satz, dass die Übersetzung nur
> der Information dient und bei Abweichungen **die englische Fassung
> maßgeblich** ist. Für die Datenschutzakte gehört deshalb zu jedem deutschen
> Ausdruck der englische dazu.

**[KANZLEI 21] — am 14.10.2026 beantwortet.** Die Service Terms lagen nicht
vor; sie gehen dem AV-Vertrag (Abschnitt 16) und der Kundenvereinbarung
(Ziffer 11.2) **beiden vor**, und solange niemand sie gelesen hatte, stand die
Schranke aus Ziffer 1.4 unter Vorbehalt. Der Abschnitt liegt jetzt vor — siehe
den nächsten Abschnitt. Der Vorbehalt ist ausgeräumt; **dafür ist eine neue
Stelle entstanden** (`[KANZLEI 22]`).

#### Die Service Terms, Abschnitt 50.12 — Amazon Bedrock

*AWS Service Terms, Stand 15.09.2026, deutsche Fassung. Am 14.10.2026 gelesen.
Auch hier gilt: Bei Abweichungen ist die englische Fassung maßgeblich.*

**Das Wichtigste zuerst: Eine Erlaubnis, Inhalte zum Training oder zur
Verbesserung der Dienste zu verwenden, enthält der Abschnitt nicht.** Die
Schranke aus Ziffer 1.4 der Kundenvereinbarung bleibt damit unangetastet; die
Aussage „kein Modelltraining" trägt.

**Dass dieses Schweigen Absicht ist und keine Lücke, zeigt der unmittelbar
folgende Abschnitt.** In 50.13 (*Amazon Q*) schreibt AWS das Gegenteil
ausdrücklich hin: Inhalte dürfen genutzt werden, „um Amazon Q und die zugrunde
liegenden Technologien zu entwickeln und zu verbessern", einschließlich des
„Trainieren[s] von Machine-Learning-Modellen", und dürfen dafür in einer
anderen AWS-Region gespeichert werden; 50.13.3 verweist für den Widerspruch
auf die **Opt-out-Richtlinie für KI-Services**. Wo AWS solche Rechte will,
nennt es sie — und für Bedrock nennt es sie nicht. Das bestätigt zugleich den
Befund vom Vormittag, dass die Abmelderichtlinie (`[KANZLEI 19]`) für Bedrock
kein Werkzeug ist: Sie hat dort nichts, woran sie greifen könnte.

**Was der Abschnitt sonst regelt, geordnet nach Bedeutung für diese Akte:**

| Stelle | Inhalt |
|---|---|
| **50.12.2 Erkennung von Missbrauch** | **Für bestimmte Modelle** — genannt auf der Bedrock-Missbrauchserkennungsseite — speichert Bedrock **Ein- und Ausgaben bis zu 30 Tage**, zum alleinigen Zweck, Verstöße gegen die Nutzungsbedingungen zu erkennen. Bei erkanntem Verdacht **überprüft AWS** die Ein- und Ausgaben; der Kunde „stimmt zu und weist an". Siehe `[KANZLEI 22]` |
| 50.12.2.1 | Bei Verdacht auf Darstellungen von Kindesmissbrauch Prüfung und Meldung an das NCMEC oder eine andere Stelle |
| 50.12.4 | Ein durch Feinabstimmung angepasstes Modell steht allein der Kanzlei zu; Drittanbieter haben keinen Zugriff. AWS greift darauf nur zu, soweit zur Wartung oder Bereitstellung nötig oder gesetzlich gefordert. **Betrifft uns heute nicht** — jusperfect stimmt kein Modell ab |
| 50.12.5 | AWS darf dem Anbieter eines Drittanbieter-Modells Angaben zur Nutzung weitergeben, **die die Inhalte nicht umfassen** |
| 50.12.5.1 | Bestimmte Anthropic-Produkte (genannt werden Claude Code und die Computernutzung) betten **Metadaten** in Anfragen ein. **Betrifft uns nicht** — jusperfect ruft die Schnittstelle unmittelbar auf |
| 50.12.1 | Modelle von Drittanbietern sind „Inhalte von Drittanbietern"; ihre Nutzung heißt Zustimmung zu deren eigenen Bedingungen, über AWS Marketplace (Abschnitt 20) |
| 50.12.6 | Ausgaben können Herkunftsdaten tragen (Metadaten, Signaturen, Wasserzeichen); sie dürfen nicht entfernt werden |

> **Eine Folgerung für den Betrieb, die nicht datenschutzrechtlich aussieht und
> es doch ist:** Nach 50.12.1 hängt die Rechtslage **am gewählten Modell**. Ein
> Wechsel auf ein Modell eines Drittanbieters aus dem Marktplatz unterstellt
> die Verarbeitung dessen Bedingungen — nicht mehr allein denen, die hier
> geprüft sind. Die Modellwahl ist deshalb keine rein technische Einstellung.
> `JUSPERFECT_MODELL` zu ändern ist eine Entscheidung mit Rechtsfolgen.

**[KANZLEI 22] — die Missbrauchserkennung nach 50.12.2.** Die beiden offenen
Fragen dazu sind am 14.10.2026 beantwortet worden; siehe den nächsten
Abschnitt. Übrig bleibt eine Bestätigung und eine Hausregel.

#### Die Missbrauchserkennungsseite und Abschnitt 1.24

*Amazon Bedrock User Guide, Abschnitt „Abuse detection", und AWS Service
Terms Abschnitt 1.24; beide am 14.10.2026 gelesen. Der User Guide ist
**Dokumentation und kein Vertrag** — AWS kann ihn ohne Ankündigung ändern.
Gerade deshalb gehört er mit Abrufdatum in die Akte.*

**Erstens: Abschnitt 1.24 betrifft die Kanzlei nicht.** Er regelt *andere*
AWS-Dienste, die eine von Bedrock betriebene KI-Funktion eingebaut haben —
genannt werden unter anderem CloudWatch, CodeCatalyst, Connect, Q, SageMaker,
WorkSpaces, Kiro, GuardDuty. jusperfect ruft die Bedrock-Schnittstelle
**unmittelbar** auf und nutzt keinen dieser Dienste. Die Frage ist damit
erledigt.

**Zweitens, und das ist der Befund dieses Tages:** Die Seite nennt die Modelle
namentlich, für die gespeichert wird.

| Modell | Was gespeichert wird |
|---|---|
| OpenAI-Modelle (bis auf vier genannte) | vom Klassifikator aufgefallener Verkehr, bis zu 30 Tage |
| **Anthropic Claude Fable 5 und Claude Fable 5.1** | **der gesamte Verkehr**, bis zu 30 Tage; aufgefallener Verkehr zusätzlich mit **möglicher menschlicher Überprüfung durch AWS** |
| alle übrigen | nichts — es gilt das **Zero-Operator-Access-Modell** (ZOA) |

**Das voreingestellte Modell von jusperfect ist
`anthropic.claude-opus-4-6-v1`** (`jusperfect/config.py:299`), als
EU-Inferenzprofil `eu.anthropic.claude-opus-4-6-v1`. **Es steht nicht auf der
Liste.** Für die Kanzlei gilt damit nach heutigem Stand der Seite: **keine
Aufbewahrung, kein Mitlesen** — es greift das Zero-Operator-Access-Modell.

> **Zwei Vorbehalte, ohne die dieser Satz zu viel sagt.**
>
> 1. Maßgeblich ist das Modell, das in `START-JURNODES.bat` wirklich
>    eingetragen ist (`JUSPERFECT_MODELL_ID`), nicht die Voreinstellung. Die
>    Oberfläche nennt es unter jeder Antwort. **Die Kanzlei bestätigt es
>    einmal**; dann ist dieser Punkt geschlossen.
> 2. **Die Liste ist Dokumentation und ändert sich.** Ein Modell kann
>    hinzukommen, auch das heute genutzte. Sie gehört deshalb in die
>    jährliche Durchsicht dieser Unterlage.

**Daraus folgt eine Hausregel, die in die Einweisung gehört:** Für
Mandatsakten wird **kein Modell verwendet, das auf dieser Seite steht** — und
vor jedem Modellwechsel wird sie angesehen. Ein Wechsel auf Claude Fable 5
oder 5.1 hieße nach heutigem Stand: *aller* Verkehr dreißig Tage bei AWS,
aufgefallener mit menschlicher Durchsicht. Das ist keine Einstellung, die man
nebenbei ändert (dazu schon oben zu 50.12.1).

**Drei weitere Angaben der Seite, die hierhergehören:**

1. **Regionsübergreifende Inferenz:** Würde ein gelistetes Modell genutzt,
   lägen die aufbewahrten Ein- und Ausgaben „in den Zielregionen" — also dort,
   wo die Anfrage verarbeitet wurde. Das `eu.`-Profil verteilt auf mehrere
   europäische Regionen (R5). Für das heute genutzte Modell ist das
   gegenstandslos, weil nichts aufbewahrt wird.
2. **CSAM-Erkennung:** Sie arbeitet auf **Bild**-Ein- und -Ausgaben. jusperfect
   sendet an Bedrock ausschließlich Text; gescannte Seiten gehen an Textract
   und nicht an Bedrock. Sie greift hier also nicht.
3. **Aufbewahrtes wird nicht an die Modellanbieter weitergegeben**, sondern
   allein von AWS gespeichert und verarbeitet.

> **Eine Pflicht, die nicht nach Datenschutz aussieht und den Betrieb trifft:**
> Erkennt AWS einen möglichen Verstoß, fragt es per E-Mail an die
> **Kontoadresse** nach — und kann den Zugang sperren, wenn niemand antwortet.
> Diese Adresse muss also gepflegt und gelesen werden. Eine unbeantwortete
> Rückfrage könnte jusperfect zum Stillstand bringen.

**[KANZLEI 22] — was noch bleibt:** die Bestätigung des wirklich eingetragenen
Modells, die Aufnahme der Hausregel in die Einweisung, und die Entscheidung,
ob der Umstand in die Hinweise nach Art. 13 DSGVO gehört. Nach heutigem Stand
ist dort **nichts über eine Aufbewahrung bei Bedrock zu sagen** — das kann
sich mit der Liste ändern.

> **Was das für Abschnitt 2.1 und für `[KANZLEI 20]` heißt.** Die
> Mengenbegrenzung bleibt die wirksamste Maßnahme in der Hand des Bearbeiters
> und wird durch diesen Befund **wichtiger**, nicht unwichtiger: Was nicht
> angehakt ist, kann auch nicht dreißig Tage liegen. Die Entscheidung vom
> 14.10.2026 steht; sie behauptet an keiner Stelle, es werde nichts
> aufbewahrt. Ihr dritter „nicht behauptet"-Satz — die Speicherfrage sei
> geklärt — ist durch diesen Befund bestätigt und nicht widerlegt.

**[KANZLEI 8] — was zur Ablage noch fehlt.** Der Weg dorthin steht in
`AWS-ZWEI-HANDGRIFFE.md`, Handgriff 3: In **AWS Artifact** liegen die
Zertifikate und Prüfberichte bereit, die der Vertrag in seinem Abschnitt 10
verspricht, und dort steht auch, ob das Data Processing Addendum für dieses
Konto **angenommen** ist — ein Nachweis, den das vorgelegte PDF nicht
erbringt. Das Stück trägt keine
Fassungsnummer, und der Vertrag gilt „in der jeweils geänderten Fassung"
(Einleitungssatz). Für die Akte sind deshalb **drei** Dinge festzuhalten: der
Tag des Abrufs, von welcher AWS-Seite abgerufen wurde, und ein Ausdruck des
Stücks. Dazu gehören drei Unterlagen, auf die der Vertrag nur verweist und die
er nicht enthält: die **Standardvertragsklauseln** (Abschn. 17, zwei
verlinkte Stücke), die **Liste der Unterauftragsverarbeiter** (Abschn. 6.1)
und die **AWS Service Terms** (Abschn. 16).

---

### R5 · Drittlandbezug durch das EU-Inferenzprofil und das Schutzgeländer

Der `eu.`-Vorsatz hält die Verarbeitung in europäischen Regionen, verteilt sie
aber auf mehrere. Dasselbe gilt für das Geländerprofil `eu.guardrail.v1:0`.

| Grenze | Wirkung |
|---|---|
| Region in den Einstellungen | nur die **namentlich aufgeführten** EU- und EWR-Regionen zulässig; alles andere bricht beim Start ab Seit dem 05.10.2026 gilt dasselbe für die **Modellkennung**: Ein Inferenzprofil mit dem Vorsatz `global.` oder `us.` verteilt außerhalb der EU, gleich aus welcher Region es aufgerufen wird, und wird abgewiesen (Befund F13 der Zweitprüfung). |
| Zugriffsrichtlinie | ausdrückliches **Verbot** jedes Bedrock-Aufrufs außerhalb `eu-*` — ein Verbot wiegt in AWS schwerer als jede Erlaubnis |
| Durch das Geländer geht | nur Frage und Antwort, nicht der Akteninhalt |

**Am 05.10.2026 berichtigt, auf einen Hinweis aus der Kanzlei hin.** Bis dahin
prüften Programm und Richtlinie auf den Vorsatz `eu-`. Der ist eine
Namenskonvention von AWS und **kein Nachweis**: `eu-central-2` ist Zürich
(Schweiz), `eu-west-2` ist London (Vereinigtes Königreich). Beide hätten die
Prüfung bestanden. Das Programm prüft seitdem gegen eine aufgeschriebene Liste;
die Richtlinie noch nicht (geschützte Datei, Vorschlag in `DSFA-ANGABEN.md`).

**Was auch die engere Liste nicht leistet:** `aws:RequestedRegion` und die
Einstellung betreffen die Region, an die der **Aufruf** geht — Frankfurt. Wohin
das Inferenzprofil und das Geländerprofil intern verteilen, entscheidet AWS und
steht in keiner Richtlinie. Deshalb bleibt die Auskunft von AWS erforderlich;
und eine Antwort, die nur `eu-`-Regionen nennt, genügt dafür nicht.

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
| Nicht gespeichert, nicht zur Verbesserung der Dienste verwendet | **belegt am 14.10.2026** — siehe unten |
| Abschaltbar mit einer Zeile | `JUSPERFECT_OCR=keine`; gescannte Blätter bleiben dann ungelesen |

> **Berichtigt am 05.10.2026 nach der Zweitprüfung (Befund F12).** Die
> Unterlagen schlossen aus dem Versand als Bytes **ohne** eigenen S3-Zwischen&shy;speicher,
> AWS speichere die Bilder nicht. **Dieser Schluss trägt nicht.** Für die
> KI-Dienste von AWS — anders als für Bedrock — gilt die Nicht-Speicherung nur
> bei einer wirksamen **AI-services-Opt-out-Richtlinie** des Kontos. Ohne
> diesen Nachweis ist „nicht gespeichert" eine Vermutung.
>
> **[KANZLEI 19] — eingelöst am 14.10.2026.** Für das AWS-Konto
> 579138738703 ist eine **wirksame** Abmelderichtlinie für KI-Services
> (*AI services opt-out policy*) festgestellt worden. Die Konsole gibt als
> effektive Richtlinie des Kontos aus:
>
> ```json
> { "services": { "default": { "opt_out_policy": "optOut" } } }
> ```
>
> Festgestellt am **14.10.2026, 17:11 MESZ**; die Richtlinie
> `jusperfect-keine-ki-nutzung` ist an der Stammorganisation verknüpft, AWS
> meldet keine Validierungsprobleme. Die Bildschirmausdrucke liegen in der
> Datenschutzakte. **Damit ist belegt:** Inhalte der erfassten KI-Dienste —
> Textract gehört dazu — werden nicht gespeichert und nicht zur Entwicklung
> und Verbesserung der AWS-KI-Dienste verwendet.
>
> **Was damit nicht belegt ist, und was deshalb eine eigene Frage bleibt.**
>
> 1. **Bedrock ist von dieser Richtlinienart nicht erfasst.** Die Abmeldung
>    sagt über die Verarbeitung im Modell nichts. AWS führt dafür an, Bedrock
>    verwende Inhalte ohnehin nicht zur Verbesserung der Dienste; eine
>    Auskunft dazu ist beim AWS-Support angefragt
>    (`AWS-ZWEI-HANDGRIFFE.md`, Support-Text, Punkt 3). Bis sie vorliegt,
>    gilt für Bedrock die vertragliche Grundlage und nicht diese Richtlinie.
> 2. **Die Abmeldung betrifft Speicherung und Verwendung zur Entwicklung und
>    Verbesserung der Dienste** — den Wortlaut der Konsole. Aufbewahrung zu
>    anderen Zwecken, etwa zum Betrieb, hängt am Auftragsverarbeitungsvertrag
>    und nicht hieran.
>
> Abschalten der Texterkennung, falls sie je zu klären ist:
> `JUSPERFECT_OCR=keine` in `START-JURNODES.bat` — **nicht** `aus`, wie es
> hier zuvor stand.

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
wurde, lässt sich nicht zurückholen. Mehr als eine vertragliche Schranke gibt
es dagegen nicht: AWS darf die Inhalte nur nutzen, soweit zur Erbringung der
Services nötig (Kundenvereinbarung Ziffer 1.4 und 6.1). Diese Schranke steht
**nicht** im Auftragsverarbeitungsvertrag; die Service Terms gehen ihr vor,
weichen für Bedrock aber nicht von ihr ab (R4, Abschnitt 50.12). **Zum Löschen
kommt hinzu, was 50.12.2 zulässt:** Je nach Modell liegen Ein- und Ausgaben
bis zu dreißig Tage bei AWS, und eine Löschung durch die Kanzlei erreicht sie
nicht (`[KANZLEI 22]`). **[KANZLEI 14]** — in den Hinweisen an die Betroffenen
zu beschreiben.

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

## 8. Die zweiundzwanzig Stellen für die Kanzlei auf einen Blick

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
| 8 | Ablage: Tag des Abrufs, Quelle, Ausdruck — je deutsch **und** englisch; dazu SCC, Unterauftragsverarbeiterliste, Service Terms | R4 |
| 9 | Verschwiegenheitsverpflichtung § 43e Abs. 3 BRAO | R4 |
| 10 | Dokumentation der Dienstleisterauswahl § 43e Abs. 2 — **Nachweise liegen seit 14.10.2026 vor**, es fehlt die Bewertung | R4 |
| 11 | Regionen des Geländerprofils — bei AWS erfragen | R5 |
| 12 | Erlaubnistatbestand Art. 9 Abs. 2; Beschränkung nach Rechtsgebiet? | R6 |
| 13 | Zugriffsbeschränkung je Bearbeiter? Zugangsschutz? | R7 |
| 14 | Was den Betroffenen über die Übermittlung gesagt wird | R8 |
| 15 | Schulung und KI-Kompetenz nach Art. 4 KI-VO | 6 |
| 17 | Verbleibendes Risiko, Art. 36, Beteiligung des DSB, Überprüfungsfrist | 7 |
| ~~18~~ | ~~Sollen Aktenzeichen und Dokumenttitel an das Modell gehen?~~ **Entschieden am 05.10.2026: Dateiname nein, Art des Schriftstücks ja, Aktenzeichen nur beim Entwurf** | 2.1 |
| ~~19~~ | ~~Wirksame AI-services-Opt-out-Richtlinie für Textract nachweisen~~ **Eingelöst am 14.10.2026, 17:11 MESZ — Nachweis in der Datenschutzakte** | R6 |
| ~~20~~ | ~~Bleibt es bei der Verarbeitung durch einen Auftragsverarbeiter, obwohl der Inhalt dort im Klartext vorliegt?~~ **Entschieden am 14.10.2026: ja, es bleibt dabei** | 2.4 |
| ~~21~~ | ~~Einschlägigen Abschnitt der AWS Service Terms zu Amazon Bedrock beschaffen~~ **Beschafft und gelesen am 14.10.2026: keine Abweichung von Ziffer 1.4, kein Training** | R4 |
| 22 | Missbrauchserkennung nach 50.12.2: **Modellliste und Abschnitt 1.24 am 14.10.2026 geklärt — das genutzte Modell ist nicht gelistet.** Bleibt: das eingetragene Modell bestätigen, Hausregel in die Einweisung, Art.-13-Hinweise | R4 |

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
