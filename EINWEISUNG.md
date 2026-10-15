# Einweisung zur Arbeit mit jusperfect

**Kanzlei Dortschy & Thunert**

**Stand: 15. Oktober 2026.** Gilt für alle, die mit jusperfect arbeiten.

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
