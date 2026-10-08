# Der Stand am 08.10.2026

Dieses Blatt sagt in einem Durchgang, wo jusperfect steht: was gemessen
feststeht, was offen ist, und welche Regeln dabei gelten. Es ist für zwei
Leser geschrieben — für die Kanzlei, und für jede spätere Sitzung, die ohne
Vorgeschichte weitermachen muss.

Ausführlich und mit Datum steht alles in `MORGEN.md` (2196 Zeilen,
chronologisch). Dieses Blatt ist der Querschnitt.

| | |
|---|---|
| Zweig | `2.0`, Fassung `2.0.0.dev` |
| Prüfungen | **1830 grün** |
| Rechner | zwei, beide eingerichtet |
| Offene Handgriffe der Kanzlei | **4** |
| Offene Fragen an jur\|nodes | **3**, alle klein |

---

## 1. Was das Programm heute kann

Es liest eine Akte aus jur|nodes, legt sie dem Anwalt zur Auswahl vor,
beantwortet Fragen dazu mit Belegstellen, führt ein Aktengedächtnis und
erzeugt Entwürfe.

**Woher der Akteninhalt kommt — Stand heute:**

| Quelle | Zustand |
|---|---|
| Dateiordner der Akte, mit allen Unterordnern | gelesen, seit 23.09.2026 |
| Gescannte Blätter (Texterkennung über Textract) | gelesen, seit 02.10.2026 |
| **Vermerke und Telefonvermerke aus der E-Akte** | **gelesen, seit 08.10.2026** |
| **E-Mails der E-Akte: Brieftext** | **gelesen, seit 08.10.2026** |
| **E-Mails: jede Anlage als eigenes Dokument** | **gelesen, seit 08.10.2026** |
| beA, Post, Fax, SMS | nicht angebunden — siehe Ziffer 4 |

Was noch keinen Inhalt hat, **verschwindet nicht**: Es wird gezählt und über
der Dokumentliste angezeigt. Eine unvollständige Liste sieht sonst aus wie
eine vollständige.

---

## 2. Was an der Schnittstelle gemessen feststeht

Nicht vermutet, nicht abgeleitet — an zwei Akten am Server der Kanzlei
gemessen (`X-100-2026` und `X-101-2026`, 08.10.2026).

**Der Weg in die E-Akte:**

```
POST /correspondence/search   {recordIdentifier, page}   → die Einträge
GET  /record/note?id=…&record=…                          → ein Vermerk
POST /mail/download           {mailIdentifier}           → eine .eml
```

* `X-100-2026`: 26 Einträge, davon 22 Mails und 4 Vermerke. Drei Vermerke
  wurden mit Inhalt geholt, alle `type=phonecall`.
* `X-101-2026`: 9 Einträge, alle Mails, kein Vermerk.
* `referenceMail` **ist** `mailIdentifier` — unverändert eingesetzt, hat
  funktioniert.
* Die Dateiart hinter `/mail/download` ist **`.eml`**; der Server nennt den
  Namen selbst (`filename="Mail.eml"`).
* Mailgrößen: einmal 8.753.880 Bytes, einmal 5.426. Mails sind fast immer
  klein; groß wird eine durch ihre Anlage.

**Die Rechte am Schnittstellenbenutzer `user_2`** stehen vollständig. Die
Beschreibung nennt zu jedem der 94 Aufrufe das benötigte Recht — im
Fließtext des Feldes `description`, hinter der Erläuterung.

**Der Aktenstatus**, an dem die Aufbewahrung hängt: Der Bestand führt genau
zwei Wörter, `archived` (290 Akten) und `active` (10). Beide kennt das
Programm.

---

## 3. Die festen Vorgaben der Kanzlei

Sie gelten weiter und sind keine Empfehlungen.

1. **Kein Postfachzugriff.** Weder E-Mail- noch beA-Postfach. Alles liegt in
   der E-Akte, und das Programm spricht ausschließlich die
   jur|nodes-Schnittstelle an. Nachgesehen am 07.10.2026: kein `imaplib`,
   kein `smtplib`, kein beA-Zugang im Quelltext.
2. **Das Programm schreibt nicht.** Keine Datei, kein Vermerk, kein Ordner.
   Dass es eine Akte nicht verändern *kann*, soll eine Eigenschaft des
   Schlüssels bleiben und keine Zusage des Programms.
3. **Text der Mail immer, Anhänge als eigene Dokumente daneben**, jedes
   einzeln abwählbar wie die Dateien aus dem Aktenordner (08.10.2026).
4. **Obergrenze mit Warnung.** Bei Überschreitung wird der Bearbeiter
   gewarnt und aufmerksam gemacht (08.10.2026). Gebaut als 20 MB je Mail und
   100 MB je Akte; was darüber liegt, bleibt mit Betreff und Datum in der
   Liste, und die Warnung steht in der Zeile selbst.
5. **Bei Dritten warten, nicht raten.** Gilt für jur|nodes und für AWS.
6. **Keine fremden Nummern probieren.** Jede Nummer gehört zu irgendeiner
   Akte des Hauses; sie abzurufen wäre ein Blick in fremde Mandate
   (§ 203 StGB). Probiert werden nur Nummern, die der Server selbst zu
   *dieser* Akte herausgibt.
7. **Vier Dateien nur auf ausdrückliche Anweisung**: `ANLEITUNG.md`,
   `infra/IAM.md`, `infra/iam-nur-claude.json`, `SICHERHEIT.md`.
8. **Sollte es Probleme mit jur|nodes geben, nach den Herstellerangaben
   fragen** — die Kanzlei hat sie und kann sie liefern (06.10.2026).

---

## 4. Was offen ist

### Bei der Kanzlei — vier Handgriffe

| Was | Wo | Anmerkung |
|---|---|---|
| **Opt-out-Richtlinie für die KI-Dienste** | AWS Organizations | Befund F12. Schritt für Schritt in `AWS-ZWEI-HANDGRIFFE.md`. Das Konto gehört zu keiner Organisation; eine anzulegen ist der erste Schritt. |
| 19 Stellen bewerten | `DSFA-ENTWURF.md` | Art. 35 DSGVO. Dringendste: die Löschfrist, die heute nie von selbst beginnt. |
| 9 Stellen bewerten | `DATENSCHUTZHINWEISE-ENTWURF.md` | Art. 13. Hängt an einer Frage: Einwilligung oder nicht. |
| 13 Stellen bewerten | `VERARBEITUNGSVERZEICHNIS-ENTWURF.md` | Art. 30. Ziffer 6.2 steht jetzt gemessen fest. |

### Am Programm — zwei Dinge

* **beA und Post anbinden.** Beide Ketten stehen in der Beschreibung
  vollständig, einschließlich der Dateiart vor dem Herunterladen
  (beA: `GET /bea` → `attachments[].fileName`; Post: `POST /post/get-files`
  → `PostFileModel.extension`). Gebaut wird erst, wenn es eine Akte gibt, an
  der sich das messen lässt — in beiden geprüften kam kein einziger Eintrag
  dieser Art vor.
* **Ordner im Dokumentfenster gruppieren.** 55 Einträge aus acht Ordnern
  stehen heute in einer Reihe.

### An jur|nodes — drei Kleinigkeiten

Fertig formuliert in `schnittstelle/ANFRAGE-HERSTELLER.md`. Keine hält etwas
auf.

1. Was bedeutet `isInbox`? Heißt `1` „eingegangen"?
2. Fehlt bei `correspondence/get-by-reference` der führende Schrägstrich?
3. Gibt es eine neuere Fassung der Beschreibung als 1.0.2?

---

## 5. Die Woche in einem Absatz — und was daraus folgt

Vier Befunde haben sich aufgelöst, **drei davon zu meinen Lasten**:

* Der **Status 401** auf die E-Akte war kein fehlendes Recht, sondern ein
  POST ohne Schlüssel — der Prüfbogen hängte ihn nur an GET-Anfragen.
* **`correspondenceFolderId`** war immer richtig; gelesen wurde im falschen
  Ordnerbaum. Zwei Nummernkreise, dieselbe Zahl, fremde Akte. Derselbe
  Fehler wie am 02.10.2026, nur an zweiter Stelle.
* **Zwei schreibende Rechte**, die ich auf einem Bildschirmfoto zu erkennen
  glaubte, waren gar nicht vergeben. Die grünen Felder zeigten die
  verfügbaren, nicht die gesetzten.
* Die **AWS-Zugriffsrichtlinie** war längst eingesetzt und stand trotzdem
  als offen in der Liste.

**Was daraus folgt**, über die einzelnen Fehler hinaus:

> Eine Erklärung, die alle beobachteten Daten erklärt, ist noch keine
> richtige. Beim 401 waren alle sechs gelungenen Aufrufe GET und der eine
> gescheiterte POST — der Unterschied stand in meiner eigenen Tabelle und
> wurde nicht gesehen, weil die Rechte-Erklärung schon passte.

Und:

> Ein Bildschirmfoto zeigt, was auf dem Schirm steht, nicht, was es
> bedeutet. Wo es um eine Aufgabe für die Kanzlei geht, ist nachzufragen
> statt zu schließen.

Der Prüfbogen ist entsprechend umgebaut: Er geht zuerst den Weg, der steht,
und sucht nur noch im Rückfall. Er liest die benötigten Rechte selbst aus der
Beschreibung und nennt bei einem 401 das Recht beim Namen. Und er fragt nicht
mehr nach Dingen, die beantwortet sind.

---

## 6. Wie es weitergeht, wenn nichts dazwischenkommt

1. **Die Opt-out-Richtlinie** — der einzige Punkt, an dem eine Unterlage
   derzeit mehr behauptet, als belegt ist.
2. **Eine echte Akte mit den neuen E-Mails öffnen.** `X-100-2026` hat 22
   davon. Das ist die Probe, die kein Prüfbogen ersetzt.
3. **Die Rechtsunterlagen.** 41 Stellen, und sie sind Bewertung, nicht
   Programmierung.
4. beA und Post, sobald eine Akte mit solchen Einträgen da ist.

---

*Geschrieben am 08.10.2026. Was hier steht, steht ausführlich und mit
Messwert in `MORGEN.md`; was offen ist, auch in der Aufgabenliste im
Browser.*
