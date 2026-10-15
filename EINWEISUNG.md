# Einweisung zur Arbeit mit jusperfect

**Kanzlei Dortschy & Thunert**

**Stand: 15. Oktober 2026** (zweite Fassung dieses Tages). Gilt für alle, die mit jusperfect arbeiten.

Dieses Blatt sammelt die Regeln, die sich **nicht** aus der Bedienung ergeben
und die das Programm auch nicht erzwingen kann. Wer sie nicht kennt, macht
nichts falsch im Sinne der Bedienung — und verletzt doch eine Pflicht aus der
Datenschutz-Folgenabschätzung.

---

## Regel 1 — Das Modell wird nicht ohne Prüfung gewechselt

**Eingestellt ist `claude-opus-4-6-v1`.** Dabei bleibt es, bis jemand die
Prüfung unten gemacht hat.

### Warum

AWS führt eine Seite, auf der Modelle **namentlich** genannt sind, bei denen
Eingaben und Ausgaben **bis zu 30 Tage aufbewahrt** werden — bei einigen der
gesamte Verkehr, mit der Möglichkeit einer **Durchsicht durch Mitarbeiter von
AWS**. Das betrifft dann den Akteninhalt, der an das Modell geht.

**Unser Modell steht nicht darauf.** Für es gilt das
Zero-Operator-Access-Modell: nichts wird aufbewahrt, nichts wird mitgelesen.
Das ist der Grund, warum die Folgenabschätzung an dieser Stelle keine
Aufbewahrung ausweisen muss.

Ein anderes Modell kann das ändern — ohne dass sich an der Bedienung etwas
ändert und ohne dass eine Meldung erscheint.

### Diese beiden Modelle nicht verwenden

**Claude Fable 5** und **Claude Fable 5.1.** Sie stehen auf der Seite:
**aller** Verkehr wird bis zu 30 Tage aufbewahrt, aufgefallener kann von
**Menschen bei AWS** durchgesehen werden. Stand 14.10.2026, Anlage 17 zum
Aktenvermerk gleichen Datums.

Das steht hier mit Namen, weil die Modellliste in der AWS-Konsole davon
**nichts** sagt. Dort wird Fable 5.1 als das stärkste Modell für
„enterprise knowledge work" beschrieben — also als genau das, was eine
Kanzlei zu brauchen glaubt. Wer nach dieser Beschreibung auswählt, wählt das
Falsche.

**Claude Mythos 5** und **Claude Mythos 5.1** sind nach dem 14.10.2026
hinzugekommen; ob sie auf der Seite stehen, ist **nicht geprüft**. Vor jeder
Verwendung nachsehen.

Von den übrigen Claude-Modellen stand am 14.10.2026 keines auf der Seite.
**Das ist kein Freibrief:** Die Seite ändert sich ohne Ankündigung, und die
Prüfung unten ersetzt diese Liste nicht — sie ist nur der Vorsprung für den,
der es eilig hat.

### Was zu tun ist, bevor ein Modell gewechselt wird

1. Die Seite **„Amazon Bedrock abuse detection"** im Amazon Bedrock User Guide
   aufrufen und nachsehen, ob das neue Modell dort genannt ist. Der Wortlaut
   vom 14.10.2026 liegt als Anlage 17 zum Aktenvermerk gleichen Datums in der
   Datenschutzakte.
2. **Steht es darauf: nicht verwenden**, jedenfalls nicht für Mandatsakten.
3. Steht es nicht darauf: nachsehen, ob es **in Frankfurt** und über das
   **EU-Inferenzprofil** läuft. Was es dort nicht gibt, gibt es für uns nicht
   — die Zusage, dass die Verarbeitung die EU nicht verlässt, steht in der
   Folgenabschätzung und in der Klausel, die die Mandantschaft unterschreibt.
4. Erst dann wechseln, den Tag der Prüfung notieren und den Ausdruck der
   Seite zur Datenschutzakte nehmen.

> **Schritt für Schritt steht das in `AWS-ZWEI-HANDGRIFFE.md`, Handgriff 4**
> — mit dem, was dabei schiefgeht, und mit den drei Gründen, die *keine*
> Gründe für einen Wechsel sind.

**Dasselbe gilt für Modelle fremder Anbieter aus dem AWS-Marktplatz** — die
bringen eigene Vertragsbedingungen mit, die wir nicht geprüft haben.

### Wo das Modell steht

* In `START-JURNODES.bat`, Eintrag `JUSPERFECT_MODELL_ID`.
* **Zum Nachsehen genügt die Oberfläche:** Unter jeder Antwort steht, welches
  Modell sie erzeugt hat.

### Einmal im Jahr

Die Seite wird bei der jährlichen Durchsicht der Folgenabschätzung erneut
angesehen. Sie ist **Dokumentation und kein Vertrag** — AWS kann sie ohne
Ankündigung ändern und ein Modell aufnehmen, auch unseres.

---

## Regel 1a — Wird gefragt, ob die Akte noch läuft, wird geantwortet

Hat zwölf Monate lang niemand in einer Akte gearbeitet, fragt jusperfect beim
Öffnen: **„Läuft die Akte noch?"**

* **Ja** — die Arbeitskopie bleibt, und in zwölf Monaten wird erneut gefragt.
  Die Antwort wird mit Datum und Bearbeiter vermerkt.
* **Nein** — die Akte wird zum Abschluss vorgemerkt. Gelöscht wird erst beim
  Abschluss, nach dem Export des Arbeitsstands.
* **Später** — die Frage bleibt offen und kommt wieder. **Es wird nichts
  gelöscht, solange nicht geantwortet ist.**

### Warum das eine Hausregel ist

Art. 5 Abs. 1 lit. e DSGVO verlangt, dass nicht länger aufbewahrt wird als
nötig. Eine Frist, die von selbst abläuft, wäre hier falsch: **Akten laufen
manchmal jahrelang**, und eine Arbeitskopie zu löschen, weil ein Jahr
vergangen ist, nähme der Kanzlei die Vorarbeit eines lebenden Mandats.

Deshalb löst die Zeit die **Frage** aus und nicht die Löschung. Die Frage
ersetzt die Frist — aber nur, wenn sie beantwortet wird. Wer immer „Später"
klickt, hat den alten Zustand wiederhergestellt.

**Die Akte selbst ist davon nie betroffen.** Gelöscht wird allenfalls die
Arbeitskopie in jusperfect; die Handakte unterliegt § 50 Abs. 1 BRAO.

---

## Regel 1b — Der zweite Faktor, wenn er eingeschaltet ist

Die Anmeldung in jusperfect ist im Laufwerksbetrieb **kein Kennwort**,
sondern eine Kennung: Wer am Rechner sitzt, kann eine andere eintragen. Das
ist das einzige Risiko, das die Folgenabschätzung als **hoch** einstuft
(R7) — und es liegt nicht bei AWS, sondern im Flur.

Seit dem 15.10.2026 lässt sich ein **zweiter Faktor** davorsetzen: ein
Einmalkennwort aus einer Authentifizierungs-App, wie bei der Bank.

### Wenn er eingeschaltet ist

1. Beim ersten Mal **„Einrichten"** klicken. Das angezeigte Geheimnis in die
   Authentifizierungs-App übernehmen (Microsoft Authenticator, Google
   Authenticator, Aegis oder eine andere).
2. **Das Geheimnis wird nur einmal angezeigt.** Wer es verliert, braucht eine
   Neueinrichtung.
3. Danach bei jedem Programmstart das sechsstellige Einmalkennwort eingeben.

### Was er nicht ersetzt

Den Schutz des Windows-Kontos. Er sorgt nur dafür, dass ein unbeaufsichtigter
Rechner allein nicht genügt, um eine Mandatsakte zu öffnen.

**Eingeschaltet wird er in `START-JURNODES.bat`**, Eintrag
`JUSPERFECT_ZWEITER_FAKTOR=an`. Voreingestellt ist „aus".

---

## Regel 1c — Drei Dinge, die jeder einhält

1. **Bildschirm sperren beim Verlassen des Platzes.** Windows-Taste + L.
   Zusätzlich die automatische Sperre nach wenigen Minuten einstellen.
2. **Keine geteilten Windows-Konten.** Jede Person hat ihr eigenes.
3. **Jeder trägt seine eigene Kennung ein** — auch wer nur kurz nachsieht.

### Warum das keine Nebensache ist

**In jusperfect sieht jede Berufsträgerin und jeder Mitarbeitende jede
Akte.** Das ist eine Entscheidung der Kanzlei vom 15.10.2026 und richtig so:
In einer Kanzlei dieser Größe vertritt jeder jeden, und eine Berechtigung,
die im Vertretungsfall regelmäßig aufgehoben werden müsste, schützt
niemanden.

**Diese Entscheidung verlagert den Schutz aber von der Technik auf die
Organisation.** Wenn nicht die Berechtigung begrenzt, *wer* eine Akte öffnen
kann, dann trägt die Last der Umstand, dass jeder Zugriff **einer Person
zuzuordnen** ist — und dass jede Person zur **Verschwiegenheit verpflichtet**
ist.

Bei einem geteilten Konto fällt die Zuordnung aus. Dann sagt der
Nutzungsnachweis nicht mehr, wer gefragt hat, und die Rechenschaftspflicht
nach Art. 5 Abs. 2 DSGVO geht an dieser Stelle verloren. **Deshalb sind diese
drei Punkte seit dem 15.10.2026 die tragende Maßnahme und nicht mehr die
Ergänzung.**

> **Für die Kanzleileitung, nicht für die Einweisung:** Für jede Person mit
> Zugang — auch Referendare, Aushilfen und externe IT — muss eine
> Verpflichtung auf die Verschwiegenheit in Textform vorliegen (§ 203 Abs. 4
> StGB). Das ist zu bestätigen, nicht anzunehmen.

---

## Regel 2 — Die E-Mail-Adresse des AWS-Kontos wird gelesen

**Benannt ist:** ........................................ *(Adresse eintragen)*

**Dafür verantwortlich ist:** ........................................

**Vertretung:** ........................................

### Warum

Erkennt AWS einen möglichen Verstoß gegen seine Nutzungsbedingungen, fragt es
**per E-Mail an die Kontoadresse** nach. Erfolgt keine Antwort, **kann AWS den
Zugang zu Amazon Bedrock oder zu einzelnen Modellen sperren**.

Eine Sperre bedeutet: **jusperfect steht still.** Keine Analyse, kein Entwurf,
keine Texterkennung — mitten in der Arbeit und ohne Vorwarnung, weil die
Vorwarnung in einem Postfach lag, das niemand liest.

An dieselbe Adresse gehen auch die übrigen Nachrichten von AWS: Rechnungen,
Hinweise auf Änderungen an Diensten, Fristen.

### Was zu tun ist

1. Eine Adresse benennen, die **tatsächlich gelesen wird** — kein Sammelkorb,
   der einmal im Quartal geöffnet wird.
2. Eine Person benennen, die dafür zuständig ist, und eine Vertretung für
   Urlaub und Krankheit.
3. **Feststellen, welche Adresse AWS heute wirklich verwendet — nicht
   annehmen.** Dafür genügt ein Blick in die Postfächer: Nachrichten mit dem
   Absender **Amazon Web Services** liegen in genau dieser Adresse. Verlässlich
   kommt die **monatliche Rechnung**; dazu Hinweise auf Änderungen an Diensten.

   > Beim Anlegen der Organisation am 14.10.2026 kam **keine** Mail — darauf
   > ist also kein Verlass.

   > **Die Anmeldung beweist es nur in einem Fall.** Wer sich mit einer
   > **E-Mail-Adresse** anmeldet, ist als Root-Benutzer unterwegs — dann ist
   > das die Kontoadresse. Wer sich mit **Kontonummer oder Kontoalias und
   > einem Benutzernamen** anmeldet, benutzt einen IAM-Benutzer; dann sagt die
   > Anmeldung über die Kontoadresse **nichts**.

4. In der AWS-Konsole nachsehen, dass **diese** Adresse hinterlegt ist, und
   nicht eine aus der Einrichtungszeit. Zwei Wege führen hin:

   * oben rechts auf den **Kontonamen**, dann **Konto** (*Account*) — dort
     stehen die Adresse des Root-Benutzers und weiter unten die
     **alternativen Kontakte** für **Abrechnung**, **Betrieb** und
     **Sicherheit**;
   * oder in **AWS Organizations** unter **AWS-Konten** das Konto anklicken —
     die **Kontodetails** nennen die Adresse ebenfalls. Das ist dieselbe
     Seite, auf der am 14.10.2026 die wirksame Opt-out-Richtlinie abgelesen
     wurde.

   > **Dieselbe Adresse setzt auch das Passwort zurück.** Wer Zugriff auf
   > dieses Postfach hat, kann sich damit das Kennwort des **Root-Benutzers**
   > von AWS neu setzen lassen — und der Root-Benutzer darf im Konto alles.
   > Je mehr Menschen das Postfach lesen, desto wichtiger werden deshalb zwei
   > Dinge: Für den Root-Benutzer muss die **Zwei-Faktor-Anmeldung
   > eingeschaltet** sein, und **gearbeitet wird nie als Root-Benutzer**
   > (`AWS-EINRICHTEN.md`, Schritt 1).
   >
   > Wird das Postfach umgekehrt kaum geöffnet, läge dort die Rückfrage von
   > AWS und niemand sähe sie. Dann gehört unter **„Betrieb"** und
   > **„Sicherheit"** eine Adresse, die wirklich gelesen wird.
5. Bei einer Nachfrage von AWS **nicht abwarten**. Wer nicht weiß, was zu
   antworten ist, fragt zurück — aber antwortet.

> **Was in eine solche Antwort nicht gehört:** Akteninhalt. Kein Ausschnitt,
> kein anonymisiertes Beispiel, kein Bildschirmfoto mit Text. Nach Ziffer 6.5
> der AWS-Kundenvereinbarung überträgt ein Vorschlag an AWS diesem
> unwiderruflich sämtliche Rechte daran.

---

## Woher diese Regeln kommen

| Regel | Fundstelle |
|---|---|
| 1 | `DSFA-ENTWURF.md`, Abschnitt 4, R4, `[KANZLEI 22]`; AWS Service Terms 50.12.1 und 50.12.2 (Stand 15.09.2026); Amazon Bedrock User Guide, „Abuse detection" (Anlage 17); `AWS-ZWEI-HANDGRIFFE.md`, Handgriff 4 |
| 1a | `DSFA-ENTWURF.md`, Risiko R3, `[KANZLEI 7]`; Art. 5 Abs. 1 lit. e DSGVO |
| 1b | ebenda, Risiko R7, `[KANZLEI 13]`; Art. 32 DSGVO |
| 1c | ebenda; Art. 5 Abs. 2 und Art. 32 DSGVO, § 203 Abs. 4 StGB |
| 2 | ebenda, letzter Absatz zu `[KANZLEI 22]`; Amazon Bedrock User Guide, „General information" |

---

## Was hier noch hinzukommt

Dieses Blatt ist **nicht vollständig**. Die Folgenabschätzung nennt noch
mindestens einen weiteren Punkt, der in die Einweisung gehört und hier noch
nicht steht:

* **Die Auswahl im Dokumentfenster ist die wirksamste Maßnahme in der Hand des
  Bearbeiters** (`DSFA-ENTWURF.md`, Abschnitt 2.4). Zum Modell gehen nur die
  angehakten Passagen — was nicht angehakt ist, sieht das Modell nie. Das ist
  keine Bequemlichkeitsfrage, sondern Datenminimierung nach Art. 5 Abs. 1
  lit. c DSGVO.

Weitere Punkte ergeben sich aus den noch offenen Stellen der
Folgenabschätzung. Dieses Blatt wächst mit ihnen.

---

Zur Kenntnis genommen:

Name ........................  Ort, Datum ........................  Unterschrift ........................

Name ........................  Ort, Datum ........................  Unterschrift ........................
