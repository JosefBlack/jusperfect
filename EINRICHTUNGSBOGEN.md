# Einrichtungsbogen jusperfect

**Vertraulich. Ausdrucken, von Hand ausfüllen, verschlossen aufbewahren.**

Dieser Bogen beantwortet eine einzige Frage: *Was muss ich eintragen, wenn ein
weiterer Rechner jusperfect benutzen soll?* Er ist dafür gedacht, ausgedruckt
und wie ein Kennwortblatt behandelt zu werden — im Tresor oder in der
verschlossenen Handakte.

> **Die beiden Geheimnisse stehen hier nicht vorgedruckt, und das ist Absicht.**
> Der jur|nodes-Token und der geheime AWS-Schlüssel gehören **handschriftlich**
> auf das ausgedruckte Blatt und in keine Datei. Wer dieses Blatt am Rechner
> ausfüllt und speichert, hat beide Geheimnisse wieder dort, wo sie nicht sein
> sollen.
>
> Die ausgefüllte Fassung **nicht** per E-Mail versenden, nicht in den
> Programmordner legen, nicht in eine Cloud.

---

## Teil 1 — Was feststeht (bereits eingetragen)

Diese Werte sind keine Geheimnisse. Sie stehen so auch in `DSFA-ANGABEN.md`
im Programmordner.

### jur|nodes

| Wert | Eintrag |
|---|---|
| Adresse der Schnittstelle | `https://dortschy-thunert.jur-nodes.net/api/extern/v1/ad8b9d99-b70b-4c87-8e12-b3e38c31f337` |
| Benutzername | `user_2` (Stand 24.09.2026) |
| Token | **nicht vorgedruckt — von Hand eintragen** |

### AWS

| Wert | Eintrag |
|---|---|
| Region | `eu-central-1` (Frankfurt) |
| IAM-Benutzer | `jusperfect-test` |
| Zugriffsschlüssel-ID | **von Hand eintragen** (beginnt mit `AKIA`) |
| Geheimer Zugriffsschlüssel | **von Hand eintragen** |
| Ablageort Aktengedächtnis | `dortschy-thunert-jusperfect-aktengedaechtnis` |
| KMS-Schlüssel (Alias) | `jusperfect-kanzlei` |
| KMS-Schlüssel-ID | `cf389440-c627-488d-8104-4989a1393a5d` |
| Zugriffsrichtlinien am Benutzer | `jusperfect-nur-claude`, `jusperfect-gedaechtnis` |

### Schutzgeländer und Modelle

| Wert | Eintrag |
|---|---|
| Kennung des Schutzgeländers | |
| Geländerprofil | `eu.guardrail.v1:0` |
| Modell (Fragen, Analyse, Gedächtnis) | `anthropic.claude-opus-4-6-v1` |
| Modell (Eingangsprüfung) | `anthropic.claude-haiku-4-5-20251001-v1:0` |

> Die Kennung des Schutzgeländers steht in der Bedrock-Konsole. Sie ist kein
> Geheimnis, wechselt aber je Einrichtung — deshalb hier eine leere Zeile.

---

## Teil 2 — Von Hand einzutragen

**Die beiden Geheimnisse.** Hier mit Kugelschreiber, sonst nirgends.

| | |
|---|---|
| **jur\|nodes-Token** | |
| | |
| **AWS Zugriffsschlüssel-ID** | |
| **AWS Geheimer Schlüssel** | |
| | |
| Kennung des Schutzgeländers | |

---

## Teil 3 — Welcher Rechner benutzt welchen Schlüssel

Ein AWS-Benutzer hat **höchstens zwei** Zugriffsschlüssel. Wer drei Rechner
ausstatten will, legt für den dritten einen eigenen Benutzer an — die
Zugriffsrichtlinie gilt für beliebig viele.

| Rechner | letzte 4 Zeichen des Schlüssels | eingerichtet am | von |
|---|---|---|---|
| | | | |
| | | | |
| | | | |
| | | | |

---

## Teil 4 — Ein neuer Rechner, Schritt für Schritt

1. Die aktuelle ZIP auspacken. Es entsteht **ein** Ordner, z. B.
   `jusperfect-02.10.2026`.
2. **`JURNODES-ZUGANG.bat`** — fragt Adresse, Benutzername, Token und die
   Kennung des Schutzgeländers. Die Geländerkennung sucht sie in älteren
   Programmordnern selbst; steht sie schon da, genügt die Eingabetaste.
3. **`ZUGANG-EINTRAGEN.bat`** — fragt die beiden AWS-Schlüsselwerte.
4. **Das Fenster schließen und neu öffnen.** Windows gibt neu hinterlegte
   Werte nur an **neu geöffnete** Fenster weiter.
5. **`ZUGANG-PRUEFEN.bat`** — muss sagen: *„Der Zugang steht."*
6. **`JURNODES-PRUEFEN.bat`**, ein Aktenzeichen eingeben — prüft die
   Schnittstelle. Beim ersten Mal dauert „Bausteine prüfen" einige Minuten;
   das Fenster hängt nicht, es lädt.
7. **`GEDAECHTNIS-AWS-PRUEFEN.bat`** — fragt Bucketname und Schlüssel-ID aus
   Teil 1 ab. Muss sagen: *„Die Ablage arbeitet."*
8. **`TEXTERKENNUNG-PRUEFEN.bat`** — muss sagen: *„Die Texterkennung
   arbeitet."* Kostet rund 0,15 Cent; schickt ein selbst gebautes Blatt, kein
   Akteninhalt.
9. **`START-JURNODES.bat`** — der Betrieb.

---

## Teil 5 — Zwei Dinge, die Zeit kosten, wenn man sie nicht weiß

**Die Zugangswerte liegen im Windows-Konto, nicht im Programmordner.** Genau
deshalb überleben sie das Auspacken jeder neuen Fassung. Der Preis: Ein
anderer Rechner — oder ein anderes Windows-Konto auf demselben Rechner — hat
sie nicht. Das ist kein Fehler, sondern die gewollte Bauweise.

**Nur den Wert eintragen, nicht die ganze Zeile.** Das Startbild zeigt
`Benutzer:        user_2`. Der Benutzername ist `user_2`, nicht die Zeile.
Ebenso: Nichts eintragen, was wie ein Platzhalter aussieht — `IHRE-KENNUNG`
und zwölf weitere Wörter weist das Programm ab.

---

## Teil 6 — Wo dieses Blatt liegt

| | |
|---|---|
| Aufbewahrungsort | |
| Ausgefüllt am | |
| Zuletzt geprüft am | |
| Wer hat Zugriff | |

---

*Vorlage aus `EINRICHTUNGSBOGEN.md` im Programmordner. Die vorgedruckten Werte
stammen aus `DSFA-ANGABEN.md`; ändert sich dort etwas, ist dieser Bogen neu zu
drucken.*
