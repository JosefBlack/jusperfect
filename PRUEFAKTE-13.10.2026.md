# Prüfakte 13.10.2026 — für eine zweite Meinung

**Diese Datei beschreibt den Stand nach einem Arbeitstag, nicht das ganze
Programm.** Wer jusperfect noch nicht kennt, liest zuerst `PRUEFAUFTRAG.md`
(Stand 12.10.2026): Dort steht, worum es geht, welche Zusagen das Programm
macht und was die erste Zweitprüfung vom 05.10.2026 bereits gefunden hat.

Hier steht, **was am 13.10.2026 dazugekommen ist** — und zwar vollständig,
samt der Stellen, an denen ich mir selbst nicht sicher bin.

| | |
|---|---|
| Programm | 80 Python-Dateien, rund 21.800 Zeilen |
| Prüfungen | 138 Dateien, rund 31.000 Zeilen, **2325 Prüfungen** (+ 1391 Unterprüfungen) |
| Oberfläche | eine Seite, `jusperfect/static/` |
| Sprache im Quelltext | Deutsch — Bezeichner, Kommentare, Fehlertexte |
| Zweig | `2.0` |
| Dieser Tag | 26 Commits, 92 Dateien, rund 11.300 neue Zeilen |

**Alles, was hier steht, ist durch den Prüflauf gegangen:** 2325 grün, und
`python -m jusperfect.sperrliste --pruefen` meldet keinen echten Namen und
kein echtes Aktenzeichen im Programmordner (328 Dateien angesehen).

---

## Wie dieser Tag verlaufen ist

Der Tag hatte zwei Hälften. Die erste war eine Störung: *„Akte öffnen nicht
möglich, interner Fehler."* Die zweite waren Wünsche aus der Arbeit mit der
Oberfläche.

### Erste Hälfte — die Störung und was sie freigelegt hat

| Fund | Ursache | Commit |
|---|---|---|
| Akte ließ sich nicht öffnen | `= field(default_factory=dict)` in einer Klasse, die **keine** Dataclass ist. Das Attribut blieb ein `dataclasses.Field`, und `.get()` darauf wirft. | `2329649` |
| Die Störungszeile war unsichtbar | Zwischenfälle gingen über `ereignis()` (INFO) — und INFO erreicht die Konsole nie. Jetzt `stoerung()` (ERROR). | `aab9e91` |
| Die gesamte E-Akte fehlte | `POST /correspondence/search` verlangt `page` — auch in der **ersten** Anfrage. jur|nodes antwortet auf Validierungsfehler mit **405** und einem deutschen Rumpf, der im Programm verworfen wurde. | `4b7eab2`, `13ca941` |
| Ein einzelner Fehler kostete die ganze Akte | Jeder Eintrag ist jetzt einzeln abgesichert; was scheitert, wird gezählt und benannt. | `a62e295` |
| Fremde Dokumente in der Arbeitsakte | `fileFolderId` und `correspondenceFolderId` sind **zwei Ordnerbäume mit denselben Nummern**. | (am 12.10. geschlossen, am 13.10. von der Kanzlei bestätigt) |

**Einen Fehler habe ich dabei selbst gemacht und öffentlich berichtigt:** Ich
hatte der Kanzlei gesagt, die 405 kämen nicht von unserem Code, und eine
Tabelle aus der Herstellerspezifikation vorgelegt. Richtig war: *meine
Aktenprobe schickte das Aktenzeichen statt des Identifiers*. Der Server war in
Ordnung. Commit `89ac3e2` trägt die Berichtigung im Text.

### Zweite Hälfte — die Oberfläche

Alles aus der Kanzlei, nichts von mir ausgedacht:

| Wunsch | Was gebaut wurde | Commit |
|---|---|---|
| „Gedächtnis verwerfen scheint nicht abzuschließen" | Ein Aufruf statt einer je Dokument | `888c05d` |
| „Aktengedächtnis ist leer — Akte einlesen sagt: schon eingelesen" | Leerer Bestand wird vor dem Offen-Zustand geprüft | `2cab744` |
| „Bei Auswahl dauert es lange … es wäre gut, wenn angezeigt wird, dass das Programm arbeitet" | Balken und leeres Suchfeld | `e6877ab` |
| „Überall Gedächtnis" / „den Strich in jurnodes wegnehmen" | Durchgehend eine Bezeichnung | `1b5ffc3` |
| „5 Fragen im Chat sind zu wenig … der Chat steht im Vordergrund" | Der ganze Verlauf, scrollbar | `c14f205` |
| „Chat immer in der Mitte … Dokumente auf einen Extrabildschirm" | Feste Lesebreite, Nebenfenster, Funktionen nach rechts | `afbd163` |
| „Fragen mit Returntaste auslösen" | Eingabetaste fragt, Umschalt+Eingabe bricht um | `3d82b8b` |
| Hinweiskasten ließ sich nicht schließen | Zwei ✕, die in der lokalen Betriebsart nie etwas taten | `871f162` |
| „Suchfunktion in den Dokumenten … schnell Anträge finden" | Volltextsuche über den schon geladenen Text — **kein Aufruf, keine Kosten** | `120948b` |

---

## Die drei Änderungen dieses Nachmittags — hier bitte genau hinsehen

### 1. Zurückgehaltene Aussagen werden gezählt (`2854742`)

**Aus der Kanzlei:** *„Aussage ohne belastbaren Beleg entfernt (genannt: —)
steht im Programm und nimmt unnötig Platz weg — vielleicht lieber zählen oder
ganz weglassen, da man die Aussage sowieso nicht anklicken kann."*

Der Satz stand einmal **je** zurückgehaltener Aussage. Eine Stelle las sich
`hinweise += [UNBELEGT_HINWEIS] * vorlauf_verworfen`.

Jetzt eine Zeile: *„4 Aussagen wurden ohne belastbaren Beleg entfernt. Dabei
waren Fundstellen genannt, die es nicht gibt: D1-…, D7-…"*

**Der zweiten Hälfte des Vorschlags bin ich bewusst nicht gefolgt.** „Ganz
weglassen" hätte bedeutet: eine Antwort wird stillschweigend kürzer. Das ist
genau der Zustand, den die Belegpflicht verhindern soll. Gezählt — nicht
verschwiegen.

> **Zu prüfen:** Ist diese Begründung tragfähig, oder habe ich einen Wunsch
> der Kanzlei mit einem Prinzip überstimmt, das hier nicht greift?
> `jusperfect/services/belegpflicht.py`, `unbelegt_satz`.

### 2. Promptbibliothek (`d592811`, `e905f87`)

**Aus der Kanzlei, in vier Nachrichten:** *„Können wir noch eine
Promptbibliothek anlegen. Diese fragt aber erst nach dem Rechtsgebiet."* —
*„Kann ich die Promptbibliothek nicht während der Arbeit füllen?"* —
*„Promptbibliothek neu und dann Überschrift und Prompt eintragen — einige sind
schon vorher eingetragen."* — und dann 39 ausformulierte Prompts.

`jusperfect/services/promptbibliothek.py`, `jusperfect/promptvorrat.json`.

* **Nach dem Rechtsgebiet fragt niemand.** Es steht in der Akte (jur|nodes:
  `lawCategory`).
* **Mitgeliefert:** Verkehrsrecht 17, Arbeitsrecht 10, privates Baurecht 10,
  Gerichtsmuster 12. Wortgleich aus der Kanzlei, nichts gekürzt.
* **Eigenes** landet in `jusperfect-promptbibliothek.json` **außerhalb** des
  Programmordners — sonst wäre die Sammlung beim nächsten ZIP weg (Befund N01
  vom 12.10.).
* **Gruppen:** erst das Rechtsgebiet, dann die Gerichtsmuster (`"immer": true`
  — sie gelten in jedem Verfahren).
* **Vorspann:** Baurecht und Gerichtsmuster haben je einen „gemeinsamen
  Basisprompt". Er wird **sichtbar** ins Eingabefeld geschrieben, nicht
  heimlich vorangestellt.

> **Zu prüfen (1):** Die Zuordnung Rechtsgebiet → Gruppe ist absichtlich grob
> (`_passt`): Gleichheit, Enthaltensein ab 6 Zeichen, gemeinsamer Anfang ab 6
> Zeichen. Damit findet „Baurecht" das „private Baurecht" und
> „Verkehrsunfallrecht" das Verkehrsrecht; „Vertragsrecht" findet das
> Verkehrsrecht nicht. **Gibt es ein Paar deutscher Rechtsgebiete, bei dem
> diese Regel falsch verbindet?** „Strafrecht"/„Verkehrsstrafrecht" verbindet
> sie — ich halte das für vertretbar, bin aber nicht sicher.
>
> **Zu prüfen (2):** Ein abgelegter Prompt kann einen Mandantennamen
> enthalten, und die Datei überdauert die Akte. Dagegen stehen drei Dinge:
> der Dialog zeigt den Text vor dem Ablegen, er warnt ausdrücklich, und der
> Wortlaut geht **nie** ins Protokoll (nur Rechtsgebiet und Länge). **Reicht
> das, oder gehört hier eine Prüfung gegen die Sperrliste hinein?**
>
> **Zu prüfen (3):** Der Vorspann wird dem Prompt im Browser vorangestellt
> (`bibGruppe` in `app.js`). Damit steht er im Eingabefeld und geht als Teil
> der Frage an das Modell. Ist das der richtige Ort — oder gehörte er
> serverseitig vor den Systemprompt?

### 3. Entwurf auf dem Briefbogen (`e905f87`)

**Aus der Kanzlei:** *„Entwurf-Funktion funktioniert noch nicht, jur|nodes
lehnt ab, was ich erstmal nicht so schlimm finde. Können wir hier einen
Briefbogen hinterlegen?"* — dazu die Briefbogen-Datei selbst.

`jusperfect/services/briefbogen.py`.

**Der Briefbogen wird benutzt, nicht nachgebaut.** Die .docx der Kanzlei wird
geöffnet, in `word/document.xml` wird der leere Rumpf durch den Entwurfstext
ersetzt, **jede andere Datei des Pakets wird Byte für Byte übernommen** —
Kopfzeilen, Fußzeilen, Logo, Schriften, Formatvorlagen. Ein nachgezeichneter
Briefbogen wäre ähnlich genug, um es nicht zu merken, und irgendwo falsch.

* `w:sectPr` bleibt stehen (Verweise auf Kopf-/Fußzeilen, Randmaße, „erste
  Seite anders"). Ohne ihn: ein weißes Blatt mit richtigem Text.
* `&`, `<`, `>` werden escaped; Steuerzeichen, die XML 1.0 nicht kennt,
  entfernt. Ein einziges rohes `&` macht die Datei für Word unlesbar.
* **Es wird nichts auf die Platte geschrieben.** Die Datei entsteht im
  Arbeitsspeicher und geht an den Browser.
* Die Vorlage liegt außerhalb des Programmordners;
  `BRIEFBOGEN-HINTERLEGEN.bat` führt dorthin.
* Auf das Blatt kommen auch die Hinweise der Belegprüfung — ein Entwurf, dem
  eine Aussage fehlt, sähe sonst aus wie ein fertiger Brief. Die Fundstellen
  (`D1-S1-P1`) bleiben weg.

> **Zu prüfen (1):** Ich habe das Ergebnis **nicht in Word geöffnet** — in
> dieser Umgebung gibt es kein Word. Geprüft sind: das ZIP ist vollständig und
> außer `document.xml` unverändert, das XML ist wohlgeformt, `sectPr` steht am
> Ende des Rumpfes. **Das ersetzt keinen Blick in Word.** Die Kanzlei muss das
> erste Blatt ansehen, bevor sie sich darauf verlässt.
>
> **Zu prüfen (2):** Der Text wird ohne eigene Formatierung eingesetzt
> (`<w:p><w:r><w:t>`), damit die Vorlage über Schrift und Abstand entscheidet.
> Hat die Vorlage eine ungewöhnliche Standardformatvorlage, sieht der Brief
> womöglich nicht aus wie gewohnt. Soll stattdessen die Formatierung des
> ersten Absatzes der Vorlage übernommen werden?
>
> **Zu prüfen (3):** `hinterlegen()` ist die **einzige** Stelle im Modul, die
> schreibt — ein Test hält das fest, indem er den übrigen Quelltext nach
> `write_text`, `write_bytes`, `open`, `mkdir` durchsucht. Ist diese Art Test
> tragfähig oder nur Theater?

---

## Was ich in eigener Sache offenlege

1. **Ich habe an diesem Tag eine falsche öffentliche Diagnose gestellt**
   (405 → „nicht unser Code") und sie erst nach einem Gegenbeweis der Kanzlei
   berichtigt. Das ist im Quelltext dokumentiert (`89ac3e2`), nicht nur hier.
2. **Ein Test war von Anfang an grün und prüfte das Falsche:**
   `assertIn("START-AWS.bat", t)` prüfte, *dass* eine Datei genannt wird, nicht
   *welche* — die Desktop-Verknüpfung zeigte auf die erfundenen Testakten.
   Gesucht werden sollte nach weiteren Tests dieser Art.
3. **Eine Attrappe war großzügiger als der echte Server.** Der fehlende
   `page`-Parameter blieb vier Prüfläufe lang unbemerkt, und ein Test hielt
   das falsche Verhalten sogar fest. Beides korrigiert — aber die Frage bleibt:
   **wo ist eine Attrappe noch großzügiger als die Wirklichkeit?**
4. **Zwölfmal an diesem Tag** hätte ich beinahe echte Aktendaten in das
   Repository geschrieben (Zitate der Kanzlei in Docstrings, ein echter Name in
   einem Test). Jedes Mal hat `SPERRLISTE-PRUEFEN.bat` es vor dem Commit
   gefunden. **Der Riegel hält — aber er ist ein Riegel, kein Vorsatz.**

---

## Was offen ist

| Punkt | Stand |
|---|---|
| **Vorschaufenster für den Entwurf** („in welchem der Entwurf nach und nach entsteht und durch den Chat geändert werden kann") | nicht gebaut |
| **jur|nodes lehnt die Entwurfsablage ab** | Wortlaut der Ablehnung liegt mir nicht vor |
| Hinweis „Die Stelle ließ sich im Absatz nicht zuordnen" erscheint sehr oft | erklärt, nicht geändert; eine Messung, welche der zwei Ursachen überwiegt, ist angeboten |
| Sperrliste auf dem zweiten Kanzleirechner | Aufgabe der Kanzlei |
| AWS AI-Services-Opt-out `[KANZLEI 19]`, Auftragsverarbeitung `[KANZLEI 20]` | Aufgabe der Kanzlei |

---

## Wie geprüft werden kann

```
python -m pytest -q                      # 2325 Prüfungen
python -m jusperfect.sperrliste --pruefen # echte Namen und Aktenzeichen
```

Die Sperrliste selbst liegt **nicht** im Paket (Befund N01). Ohne sie prüft
der Lauf nur das Aktenzeichenmuster und sagt das ausdrücklich — das ist im
Prüflauf eines Dritten der vorgesehene Zustand.

**Die Oberfläche ist nicht in einem Browser gemessen worden.** Geprüft sind
Quelltext und Struktur. Wer die vier neuen Stellen im Bild sehen will, braucht
`START-DEMO.bat` und einen Browser.
