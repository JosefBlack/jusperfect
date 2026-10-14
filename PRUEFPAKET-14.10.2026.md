# Prüfpaket 14.10.2026 — für eine zweite Meinung

**Dies ist der Stand eines Arbeitstages, nicht des ganzen Programms.** Wer
jusperfect nicht kennt, liest zuerst `PRUEFAUFTRAG.md` (Stand 12.10.2026) —
dort steht, worum es geht, welche Zusagen das Programm gibt und was die erste
Zweitprüfung vom 05.10.2026 gefunden hat. Danach `PRUEFAKTE-13.10.2026.md`.

Hier steht, was am **14.10.2026** dazugekommen ist — vollständig, samt der
Stellen, an denen ich mir selbst nicht sicher bin.

| | |
|---|---|
| Programm | 80 Python-Dateien, rund 23.000 Zeilen |
| Prüfungen | 141 Dateien, rund 32.500 Zeilen, **2447 Prüfungen** (+ 1435 Unterprüfungen) |
| Oberfläche | eine Seite, `jusperfect/static/` |
| Sprache im Quelltext | Deutsch — Bezeichner, Kommentare, Fehlertexte |
| Zweig | `2.0` |
| Dieser Tag | 33 Commits |

**Alles hier ist durch den Prüflauf gegangen:** 2447 grün, und
`python -m jusperfect.sperrliste --pruefen` meldet keinen echten Namen und
kein echtes Aktenzeichen im Programmordner.

**Was die prüfende Stelle nicht hat und nicht braucht:** Zugang zu Akten, zu
AWS, zu jur|nodes. Geprüft werden Quelltext und Unterlagen aus dem Zweig
`2.0`.

---

## Der Tag hatte zwei Hälften

**Vormittag: Programm.** Vier Wünsche aus der Arbeit mit der Oberfläche.
**Nachmittag und Abend: Unterlagen.** Das AWS-Vertragswerk wurde vollständig
gelesen, und dabei fielen drei eigene Behauptungen um.

---

# Teil 1 — Was am Programm gebaut wurde

## 1.1 Die Promptbibliothek

`jusperfect/services/promptbibliothek.py` (neu), `jusperfect/promptvorrat.json`
(39 Prompts der Kanzlei), Oberfläche in `app.js`.

Prompts werden nach Rechtsgebiet gruppiert, lassen sich während der Arbeit
ablegen, als Reiter auf- und zuklappen, und das Rechtsgebiet lässt sich
wechseln, ohne die Akte zu wechseln.

**Woran ich zweifle:** `_passt()` ordnet Rechtsgebiete **tolerant** zu —
Gleichheit, dann „längeres beginnt mit kürzerem" (ab 4 Zeichen), dann
Enthaltensein (ab 6), dann gemeinsamer Anfang (ab 6). Das fängt
„Verkehrsrecht" / „Verkehr" / „verkehrsrecht" ab. Es könnte aber auch
Gebiete zusammenwerfen, die nichts miteinander zu tun haben. *Ist die
Toleranz richtig gewählt, oder sollte sie enger sein und dafür eine
ausdrückliche Zuordnung verlangen?*

## 1.2 Das Vorschaufenster

`jusperfect/services/entwuerfe.py` (umgebaut), `app.js`.

Der Entwurf wächst beim Erzeugen sichtbar im Fenster, lässt sich über den Chat
überarbeiten, und frühere Fassungen bleiben (`MAX_VORFASSUNGEN = 10`).
Umschaltbar zwischen Fließtext (mit anklickbaren Belegen) und Blattansicht.

**Woran ich zweifle:**

* `teiltext(roh)` zieht aus einer **halb angekommenen** JSON-Antwort das Feld
  `"text"` heraus, damit der Entwurf streamen kann. Das ist ein von Hand
  geschriebener Teilparser: halbe `\` und halbe `\uXXXX` werden abgeschnitten.
  *Gibt es eine Eingabe, bei der er falschen Text liefert statt gar keinen?*
* Ab der elften Fassung fällt die älteste still heraus. *Still ist hier
  richtig — oder gehört ein Hinweis hin?*

## 1.3 Der Briefbogen — und drei Funde am gedruckten Blatt

`jusperfect/services/briefbogen.py` (neu, groß). Die Kanzlei hat ihre echte
Word-Vorlage hinterlegt; das Programm liest Seitenmaß, Ränder, Kopf- und
Fußstücke und setzt den Entwurf in den leeren Rumpf.

**Das Entscheidende an diesem Teil ist die Methode:** Ich habe die erzeugte
Word-Datei mit LibreOffice gesetzt und das **Bild** angesehen. Drei Fehler,
die am Quelltext unsichtbar waren:

| Fund | Ursache |
|---|---|
| Markdown stand roh auf dem Briefbogen (`## …`, `**…**`, `- …`) | Niemand setzte es um. Jetzt `briefzeile()` |
| Der Text stand auf der Fußzeile | Satzspiegel endet bei 271,6 mm, Fußzeile beginnt bei 272,5 mm |
| Ein Hinweisblock schob den Brief auf Seite 2 | Drei Zeilen interner Vermerk unter vollem Briefkopf |

**Beim dritten habe ich eine Entscheidung vom Vortag zurückgenommen.** Sie
lautete: Ein Entwurf, dem eine Aussage fehlt, sieht ohne Hinweis wie ein
fertiger Brief aus. Am Blatt gemessen war das falsch — ein Brief, aus dem vor
dem Versand etwas zu entfernen ist, ist auch kein fertiger Brief. Die Hinweise
stehen jetzt an vier Stellen im Programm und an keiner auf dem Papier.

**Woran ich zweifle, und das ist die wichtigste Frage dieses Teils:**

* **`briefzeile` gibt es zweimal** — in `services/briefbogen.py` für die
  Word-Datei und in `static/app.js` für die Blattansicht. Zwei Fassungen
  derselben Regel laufen auseinander, sobald eine geändert wird; dann zeigt
  die Vorschau etwas anderes als das Papier.
  `tests/test_brief_statt_markdown.py` führt deshalb die JS-Fassung **wirklich
  aus** (über Node) und vergleicht an zwanzig Zeilen. *Genügt das, oder ist
  die Doppelung an sich der Fehler?*
* Der **Vorlauf** (wo der Text unter dem Briefkopf beginnt) wird aus den
  festgesetzten Stücken des Kopfes gerechnet. Geprüft ist das an **einer**
  echten Vorlage und an eigenen Prüfvorlagen. *Welche Bauweise eines
  Briefbogens bricht diese Rechnung?*

## 1.4 Platz in der Oberfläche

Bibliothek als Lade, kleinere Schrift (13,5 pt) in Chat und Dokumenten, ein
einheitlicher Balken links, ausklappbare Kopfzeile.

**Ein Fund, der zweimal passiert ist:** Zwei Knöpfe hießen gleich („Entwurf",
dann „Gedächtnis"). Jetzt sieht eine Prüfung **alle** Knöpfe durch und fällt
rot aus, sobald zwei gleich heißen. *Zweimal von Hand berichtigt, beim dritten
Mal soll es der Prüflauf sagen — ist das die richtige Lehre, oder behandelt
sie nur das Symptom?*

---

# Teil 2 — Die Unterlagen, und drei eigene Behauptungen, die umfielen

Am Nachmittag wurde das AWS-Vertragswerk vollständig gelesen: Data Processing
Addendum, Kundenvereinbarung (01.06.2026), Datenschutzhinweis (18.05.2026),
Service Terms Abschnitt 50.12 und 1.24 (15.09.2026), und die Seite „Amazon
Bedrock abuse detection" aus dem User Guide.

## 2.1 Was dabei umfiel

| Behauptung in unseren Unterlagen | Befund |
|---|---|
| „`default` deckt alle KI-Dienste ab — **auch Bedrock**" (`AWS-ZWEI-HANDGRIFFE.md`) | **Falsch.** Bedrock gehört nicht zu dieser Richtlinienart. Der Satz widersprach unserer eigenen Berichtigung vom 05.10.2026 |
| „Kein Modelltraining — **im AWS-Vertragswerk zugesichert**" (`DSFA-ENTWURF.md`) | **Ohne Fundstelle.** Im AV-Vertrag steht dazu kein Wort. Die Fundstelle gibt es, sie steht in Ziffer 1.4 und 6.1 der **Kundenvereinbarung** |
| „Der Auftragsverarbeiter sichert zu, Eingaben **weder zu speichern** noch zum Training zu verwenden" (`DATENSCHUTZHINWEISE-ENTWURF.md`) | **Zu stark.** Eine vertragliche Zusage der Nicht-Speicherung gibt es nicht; sie folgt aus der Modellwahl |

## 2.2 Was positiv festgestellt wurde

* **Die Opt-out-Richtlinie ist wirksam** (14.10.2026, 17:11 MESZ); dabei hat
  sich gezeigt, dass eine Richtlinie an der Stammorganisation auch das
  **Verwaltungskonto** erfasst — anders als Service-Kontrollrichtlinien.
* **Für Bedrock gibt es keine Trainings- oder Verbesserungserlaubnis.** Dass
  dieses Schweigen Absicht ist, zeigt der Nachbarabschnitt 50.13 zu Amazon Q,
  wo AWS sich das Gegenteil ausdrücklich herausnimmt.
* **Abschnitt 50.12.2 erlaubt eine Aufbewahrung von bis zu 30 Tagen** zur
  Missbrauchserkennung — aber nur für namentlich genannte Modelle. Das
  eingesetzte `anthropic.claude-opus-4-6-v1` steht nicht darauf.

## 2.3 Die Konstruktion, über die ich eine zweite Meinung will

Daraus ist etwas entstanden, das ich für richtig halte und das trotzdem
ungewöhnlich ist:

> **Die Datenschutzhinweise nach Art. 13 DSGVO hängen an einer
> Betriebsregel.** Der Satz „beim Auftragsverarbeiter wird nichts darüber
> hinaus aufbewahrt" ist heute wahr, weil das eingesetzte Modell nicht auf
> einer Liste von AWS steht. Wird ein gelistetes Modell eingesetzt, wird der
> Satz falsch. Abgesichert ist das durch **Regel 1 in `EINWEISUNG.md`** (kein
> gelistetes Modell für Mandatsakten) und durch Anmerkungen an beiden Stellen
> der Hinweise.

**Fragen dazu:**

1. *Ist es vertretbar, eine Rechtsunterlage von einer Betriebsregel abhängen
   zu lassen — oder gehört die Prüfung ins Programm?* Technisch wäre ein
   Startabbruch bei gelistetem Modell möglich. Ich habe ihn **nicht** gebaut,
   weil die Liste außerhalb des Programms liegt und sich ändert: eine fest
   eingebaute Liste wäre nach wenigen Monaten falsch und gäbe eine Sicherheit
   vor, die sie nicht hat. *Ist das die richtige Abwägung?*
2. *War es richtig, die dreißig Tage in den Art.-13-Hinweisen nicht zu
   nennen?* Mein Grund: Art. 13 Abs. 2 lit. a verlangt die Dauer der
   **tatsächlichen** Verarbeitung; eine Frist zu nennen, die nicht läuft, wäre
   unrichtig. Gegenargument wäre Transparenz über das, was passieren *könnte*.

## 2.4 Die Rechtsgrundlage und die Einwilligung

`[KANZLEI 1]` ist am 14.10.2026 ausformuliert worden: Art. 6 Abs. 1 lit. b für
Mandantendaten, lit. f für Daten Dritter in der Akte, Art. 9 Abs. 2 lit. f für
besondere Kategorien; dazu § 203 Abs. 3 StGB und § 43e BRAO für die
Offenbarung.

**Offen und ausdrücklich zur zweiten Meinung gestellt:** Die Kanzlei neigt
dazu, **zusätzlich eine Einwilligung** einzuholen („sicher ist sicher").
Meine Bedenken, die ich noch nicht in die Unterlage geschrieben habe:

* **Widerruf** (Art. 7 Abs. 3) mitten im Mandat;
* **Freiwilligkeit** (Art. 7 Abs. 4): Wer das Mandat nur mit Einwilligung
  bekommt, willigt nicht freiwillig ein — dann ist sie unwirksam;
* Nach verbreiteter Auffassung darf die Rechtsgrundlage **nicht
  nachrücken**, wenn die Einwilligung wegfällt;
* Sie deckt **Dritte** (Gegner, Zeugen) ohnehin nicht;
* Art. 9 Abs. 2 **lit. f** ist belastbarer als lit. a, weil nicht widerruflich.

*Trägt diese Einschätzung? Und gibt es eine Fassung, die dem Wunsch der
Kanzlei entspricht, ohne die Rechtsgrundlage zu schwächen — etwa eine
vertragliche Vereinbarung im Mandatsvertrag statt einer Einwilligung?*

---

# Teil 3 — Was bewusst so ist, nicht als Fund melden

* **Deutsch im Quelltext** — Bezeichner, Kommentare, Fehlertexte. Absicht.
* **Belegpflicht und „fail closed"** — jede Aussage trägt `D<n>-S<n>-P<n>`;
  ohne Beleg wird verworfen, nicht abgeschwächt.
* **Das Programm schreibt nichts** von sich aus in die E-Akte.
* **Zwei schreibende Stellen im Briefbogenteil** (`hinterlegen`,
  `einstellungen_speichern`) — eine Prüfung hält fest, dass es dabei bleibt.
* **Markdown für Arbeitsunterlagen, Word/PDF für alles, was unterschrieben
  oder abgelegt wird.** Seit dem 14.10.2026 bewusst getrennt.

---

# Teil 4 — Was eine nützliche Antwort enthält

1. **Zu jedem Fund:** Datei und Zeile, ein Weg vom echten Aufruf zum Schaden,
   und was er kostet. Vermutungen gern — aber als solche gekennzeichnet.
2. **Zu den vier Fragen** in 1.1, 1.2, 1.3 und 2.3.
3. **Zu 2.4** die juristische Einschätzung, wenn die prüfende Stelle sie geben
   kann.
4. **Widerspruch ist willkommen.** Drei eigene Behauptungen sind heute
   umgefallen, und zwei davon hat die Kanzlei durch Bildschirmfotos umgeworfen,
   nicht ich durch Nachdenken. Das ist der Normalfall und kein Unfall.

---

## Zum Nachlesen im Zweig `2.0`

| Datei | Inhalt |
|---|---|
| `PRUEFAUFTRAG.md` | der Rahmen, Stand 12.10.2026 |
| `PRUEFAKTE-13.10.2026.md` | der Vortag |
| `MORGEN.md` | der laufende Arbeitsstand, oben die Kanzleiliste |
| `DSFA-ENTWURF.md` | Folgenabschätzung, 22 Stellen für die Kanzlei |
| `DATENSCHUTZHINWEISE-ENTWURF.md` | Art. 13, 9 offene Entscheidungen |
| `SICHERHEIT.md` | die technische Darstellung |
| `EINWEISUNG.md` | die beiden Hausregeln, neu am 14.10.2026 |
| `VERMERK-AWS-14.10.2026.md` | der Aktenvermerk zum AWS-Vorgang |
| `AWS-ZWEI-HANDGRIFFE.md` | die Anleitung, heute fünfmal berichtigt |

---

*Dieses Paket ist von dem Entwickler geschrieben, dessen Arbeit es prüfen
lässt. Die Stellen, an denen ich mir unsicher bin, stehen deshalb nicht am
Ende, sondern jeweils dort, wo die Arbeit beschrieben ist.*
