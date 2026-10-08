# Die beiden Handgriffe in AWS

**Stand 08.10.2026.** Zwei Dinge sind in der AWS-Konsole zu tun. Der erste
dauert fünf Minuten. Der zweite kann fünf Minuten dauern oder eine
Vormittagsstunde — das hängt davon ab, ob das AWS-Konto zu einer
*Organisation* gehört. Schritt 1 des zweiten Handgriffs klärt das.

Beides betrifft das Konto **579138738703**, Region **eu-central-1**
(Frankfurt).

> **Vorab, damit es nicht untergeht:** Sie brauchen für beides die
> AWS-Konsole mit einem Zugang, der Richtlinien ändern darf — also nicht den
> Benutzer `jusperfect-test`, den das Programm benutzt. Der darf nichts
> davon, und das ist Absicht.

---

## Handgriff 1 — Die Zugriffsrichtlinie `jusperfect-nur-claude` ersetzen

### Worum es geht

Die Richtlinie sagt, was das Programm bei AWS darf. Die Fassung im
Programmordner schließt zwei Lücken, die am 05.10.2026 gefunden wurden:

1. **`eu-` ist eine Namenskonvention, keine Aussage über die EU.**
   `eu-central-2` ist Zürich, `eu-west-2` ist London — beide außerhalb der EU
   und des EWR. Die alte Richtlinie prüfte auf den Vorsatz `eu-` und hätte
   beide durchgelassen. Die neue nennt die sechs erlaubten Regionen
   namentlich.
2. **`bedrock:ApplyGuardrail` braucht zwei Ressourcenarten**, `guardrail` und
   `guardrail-profile`. In der alten Datei stand nur die erste.

### Die Schritte

1. In der **AWS-Konsole** anmelden.
2. Oben rechts prüfen, dass die Region **Europa (Frankfurt) eu-central-1**
   eingestellt ist.
3. Links oben ins Suchfeld **`IAM`** eingeben und den Dienst **IAM** öffnen.
4. In der linken Spalte auf **Richtlinien** (englisch: *Policies*).
5. Ins Suchfeld **`jusperfect-nur-claude`** eingeben und die Richtlinie
   anklicken.
6. Rechts auf **Bearbeiten** (*Edit*).
7. Über dem Textfeld von **Visuell** auf **JSON** umschalten.
8. Den **gesamten** Inhalt des Feldes markieren und löschen.
9. Im Programmordner die Datei **`infra\iam-nur-claude.json`** mit dem
   Editor öffnen, alles markieren, kopieren — und in das leere Feld
   einfügen.
10. Unten auf **Weiter** (*Next*), dann auf **Änderungen speichern**
    (*Save changes*).

### Zwei Dinge, die an dieser Stelle schiefgehen können

**„Sie haben die maximale Anzahl an Versionen erreicht."** AWS hält von jeder
Richtlinie höchstens fünf Fassungen. Beim Speichern erscheint dann eine Liste;
dort die **älteste** abwählen, damit Platz für die neue ist. Die abgewählte
Fassung wird gelöscht — das ist in Ordnung, die aktuelle bleibt in der Datei.

**Ein Haken bei „Als Standardversion festlegen".** Der muss **gesetzt** sein,
sonst wird die neue Fassung zwar gespeichert, aber nicht benutzt. AWS setzt
ihn meist von selbst.

### Wie Sie merken, dass es gewirkt hat

Starten Sie am Rechner **`ZUGANG-PRUEFEN.bat`**. Es muss weiterhin sagen:
*„Der Zugang steht."* Sagt es das nicht, ist beim Einfügen etwas verloren
gegangen — dann schicken Sie mir die Datei `zugangstest.txt` aus dem
Programmordner.

---

## Handgriff 2 — Die Opt-out-Richtlinie für die KI-Dienste

### Worum es geht, und warum es wichtig ist

In unseren Unterlagen stand, Textract verarbeite die Seiten, speichere sie
aber nicht. **Dieser Satz ist so nicht belegt.** AWS behält sich für seine
KI-Dienste vor, Inhalte zu speichern und zur Verbesserung der Dienste zu
verwenden — und zwar auch in einer anderen Region —, *solange kein Opt-out
besteht*. Das steht in der Textract-FAQ unter „Data Privacy".

Die Abhilfe heißt bei AWS **AI services opt-out policy**. Sie ist keine
IAM-Richtlinie, sondern eine Richtlinie der **AWS Organizations** — deshalb
ist sie an einer anderen Stelle der Konsole und deshalb kann sie bei einem
Einzelkonto etwas Vorlauf brauchen.

> **Bis sie nachgewiesen und datiert abgelegt ist, darf keine unserer
> Unterlagen eine Nicht-Speicherung behaupten.** `SICHERHEIT.md` ist am
> 06.10.2026 entsprechend berichtigt worden; in `DSFA-ENTWURF.md` steht die
> Stelle als `[KANZLEI 19]` offen.

### Schritt 1 — Klären, ob das Konto zu einer Organisation gehört

1. In der AWS-Konsole anmelden.
2. Ins Suchfeld **`Organizations`** eingeben und **AWS Organizations**
   öffnen.
3. Eines von beiden erscheint:

   * **Eine Übersicht mit einem Baum von Konten** → Das Konto gehört zu
     einer Organisation. Weiter bei Schritt 2.
   * **Eine Einladungsseite „Organisation erstellen"** → Das Konto steht für
     sich. Weiter bei Schritt 1a.

### Schritt 1a — Nur wenn keine Organisation besteht

Eine Opt-out-Richtlinie gibt es nur innerhalb einer Organisation. Für ein
einzelnes Konto genügt eine Organisation mit genau diesem einen Konto; das
kostet nichts und ändert an der Abrechnung nichts.

1. Auf **Organisation erstellen** (*Create an organization*).
2. AWS schickt eine Bestätigungsmail an die Kontoadresse — den Link darin
   anklicken.
3. Danach weiter bei Schritt 2.

> **Wenn Sie das nicht selbst entscheiden wollen:** Eine Organisation
> anzulegen ist eine Entscheidung über die Kontostruktur der Kanzlei, nicht
> über jusperfect. Dann ist der andere Weg, den AWS-Support zu fragen — siehe
> „Der Weg über den Support" unten.

### Schritt 2 — Die Richtlinienart einschalten

AWS schaltet diese Richtlinienart nicht von selbst frei.

1. In **AWS Organizations** links auf **Richtlinien** (*Policies*).
2. In der Liste **Opt-out-Richtlinien für KI-Services**
   (*AI services opt-out policies*) anklicken.
3. Oben auf **Aktivieren** (*Enable*). Steht dort schon „Aktiviert", ist
   nichts zu tun.

### Schritt 3 — Die Richtlinie anlegen

1. Auf **Richtlinie erstellen** (*Create policy*).
2. **Name:** `jusperfect-keine-ki-nutzung`
3. **Beschreibung:** `Kein Opt-in zur Nutzung von Inhalten durch AWS-KI-Dienste. Kanzlei Dortschy & Thunert, 08.10.2026.`
4. Auf **JSON** umschalten und als Inhalt genau dies eintragen:

```json
{
  "services": {
    "default": {
      "opt_out_policy": {
        "@@assign": "optOut"
      }
    }
  }
}
```

5. Auf **Richtlinie erstellen** speichern.

> **Warum `default` und nicht `textract`.** `default` deckt **alle**
> KI-Dienste von AWS ab — auch Bedrock, über das die Analyse läuft, und jeden
> Dienst, der später dazukäme. Eine Richtlinie, die nur Textract nennt, müsste
> man bei jedem neuen Dienst nachziehen, und das vergisst man.

### Schritt 4 — Die Richtlinie anhängen

Erstellt ist nicht wirksam. Sie muss an das Konto gehängt werden.

1. In der Richtlinienliste die neue Richtlinie anklicken.
2. Reiter **Ziele** (*Targets*), dann **Anhängen** (*Attach*).
3. Die **Stammorganisation** (*Root*) auswählen — damit gilt sie für alle
   Konten, auch für später hinzukommende.
4. Bestätigen.

### Schritt 5 — Den Nachweis sichern

**Das ist der eigentliche Zweck des Ganzen.** Ohne Nachweis bleibt die Stelle
`[KANZLEI 19]` offen, auch wenn die Richtlinie wirkt.

1. In **AWS Organizations** links auf **AWS-Konten**, dann das Konto
   **579138738703** anklicken.
2. Reiter **Richtlinien** (*Policies*). Dort steht unter „Opt-out-Richtlinien
   für KI-Services" die **wirksame** Richtlinie — nicht die erstellte, sondern
   die, die für dieses Konto tatsächlich gilt.
3. Davon einen **Bildschirmausdruck** machen, mit sichtbarem Datum.
4. Den Ausdruck zur Datenschutzakte nehmen, mit dem Vermerk:
   *„Wirksame AI-services-Opt-out-Richtlinie für Konto 579138738703,
   festgestellt am TT.MM.JJJJ."*
5. Mir Bescheid geben — dann trage ich `[KANZLEI 19]` in `DSFA-ENTWURF.md`
   nach und nehme den Vorbehalt aus `SICHERHEIT.md` heraus.

> **Der Unterschied zwischen „erstellt" und „wirksam" ist hier der ganze
> Punkt.** Eine erstellte, aber nicht angehängte Richtlinie sieht in der
> Konsole fast genauso aus und bewirkt nichts. Deshalb wird der Nachweis am
> **Konto** abgelesen und nicht an der Richtlinie.

### Der Weg über den Support

Wenn Schritt 1a nicht in Frage kommt oder die Konsole etwas anderes zeigt als
hier beschrieben, geht es auch über ein Support-Ticket. Dieser Text ist dafür
fertig:

> Sehr geehrte Damen und Herren,
>
> für das Konto 579138738703 benötigen wir eine verbindliche Auskunft zu zwei
> Punkten:
>
> 1. Besteht für dieses Konto derzeit eine wirksame AI-services-Opt-out-
>    Richtlinie, die die Nutzung unserer Inhalte zur Verbesserung der Dienste
>    ausschließt? Falls ja: seit wann, und für welche Dienste?
> 2. Falls nein: Wie richten wir sie für ein Konto ein, das keiner
>    Organisation angehört?
>
> Hintergrund ist eine Datenschutz-Folgenabschätzung nach Art. 35 DSGVO. Wir
> verarbeiten mit Amazon Textract und Amazon Bedrock Unterlagen, die dem
> anwaltlichen Berufsgeheimnis unterliegen (§ 203 StGB), und benötigen den
> Nachweis in dokumentierter Form.
>
> Mit freundlichen Grüßen

---

## Was danach noch offen ist

Nach beiden Handgriffen bleibt in AWS nichts mehr zu tun. Offen bleiben dann
nur noch die Stellen in den drei Rechtsunterlagen — und die sind Bewertung,
keine Konsolenarbeit.

---

*Diese Anleitung gehört zu `MORGEN.md` und zur Aufgabenliste. Die Namen der
Schaltflächen stammen aus der deutschsprachigen AWS-Konsole; in der
englischen stehen sie in Klammern daneben. AWS benennt Schaltflächen
gelegentlich um — findet sich eine nicht, hilft die Suche oben in der Konsole
mit dem englischen Wort.*
