# Übergabe: jusperfect — Stand und Weiterarbeit

Dieses Dokument richtet sich an **jede KI oder Entwicklerin, die hier weiterarbeitet**.
Es beschreibt, was jusperfect ist, was gebaut wurde, warum es so gebaut wurde, und was
als Nächstes ansteht. Es ist bewusst so geschrieben, dass man ohne Vorgeschichte
weitermachen kann.

Ausgangsstand: alles in `main` gemergt (PR #2), **211 Tests grün**
und mergefähig gegen `main`.

Fortsetzung durch Codex am 04.09.2026: Das in Abschnitt 7 geplante Aktengedächtnis ist mit
Commit `abeb500` umgesetzt und auf den Übergabe-Branch gepusht; **159 Tests grün**, einschließlich
der AWS-Speichertests mit moto. JavaScript und CloudFormation/SAM sind ebenfalls validiert.

Nach dem Push zeigte PR #2 trotz Mergefähigkeit keine Statusprüfungen. Deshalb wurde anschließend
`.github/workflows/jusperfect.yml` ergänzt: Python 3.12, vollständige Tests einschließlich moto,
JavaScript-Syntax und `cfn-lint` laufen nun für jeden Push/PR mit Änderungen unter `jusperfect/`.

Fortsetzung am 04.09.2026: Der Mehrfachdialog ist umgesetzt. Die letzten belegten und fail-closed
geprüften Q&A-Runden liegen begrenzt im flüchtigen Sitzungszustand; ihre Originalpassagen gehen bei
Rückfragen erneut mit. Bei aktiviertem Aktengedächtnis werden dessen letzte geprüfte Q&A beim
Wiederöffnen übernommen. Konfiguration: `JUSPERFECT_DIALOG_MAX_RUNDEN` (Standard 6).

---

## 1. Was ist jusperfect?

Eine **kontrollierte KI-Schicht über jur|nodes** für eine deutsche Anwaltskanzlei.
Nachfolger von **Perfect Shield** (eigenes Repository `JosefBlack/perfect-shield`, dort unter `app/` plus
Browser-Erweiterung im Wurzelverzeichnis — **unverändert lassen**).

**Der entscheidende Unterschied zu Perfect Shield:** Perfect Shield anonymisiert lokal,
*bevor* Text an eine externe KI geht. jusperfect tut das **nicht**. Es verarbeitet den
echten Aktentext in einem **gesicherten Bedrock-Datenbereich** (AWS Frankfurt, privat,
Guardrails, kein Modelltraining). Der Schwerpunkt liegt auf **Flow, Verarbeitung, Cowork
und Überblick** statt auf aufwändiger Verschlüsselung vor der Verarbeitung.
Perfect Shield bleibt als **optionale Vorschaltstufe** für hochsensible Fälle vorgesehen
— der Schalter ist angelegt (`perfect_shield_aktiv`), aber **bewusst nicht scharf**, um
das Programm schlank zu halten.

---

## 2. Wo liegt was

- **Repo:** `JosefBlack/jusperfect` (eigenständig; Perfect Shield liegt in `JosefBlack/perfect-shield`)
- **Branch:** Der Entwicklungszweig ist in `main` gemergt. Neue Arbeit beginnt bei `main` auf einem frischen Zweig, niemals auf der bereits gemergten Historie.
- **PR:** #2 gegen `main` (offen, mergefähig, rein additiv — nur `jusperfect/`)
- **Projektordner:** `jusperfect/` — darin das gleichnamige Python-Paket `jusperfect/`

```
jusperfect/
  jusperfect/
    config.py            Einstellungen (alle JUSPERFECT_*-Umgebungsvariablen)
    web.py               FastAPI-App, alle Endpunkte, Dienste-Verdrahtung (Klasse Dienste)
    __main__.py          lokaler Serverstart
    lambda_handler.py    AWS-Einstieg
    domain/models.py     Akte, Dokument, Passage, Quelle, Antwort, Sitzung, Nutzungseintrag …
    jurnodes/            Schnittstelle + Adapter (fixture, http, webdav)
    services/            Fachlogik (siehe unten)
    speicher/            Sitzungsspeicher (lokal / aws), Protokoll base.py
    security/            Identität, Berechtigungen, Freigabe, Protokoll, Tempstore
    providers/           bedrock.py, demo.py, base.py (LLM-Anbieter)
    ocr/                 Textract / KeinOcr
    packs/               Workflow-Packs als JSON (verkehrsunfall, miete)
    static/              Oberfläche: index.html, app.js, styles.css
    tests/                 163 Tests (unittest)
  testdaten/             Testakten + nutzer.json für den Demo-Betrieb
  infra/                 SAM-Vorlage für AWS
  README.md  KONZEPT.md  SICHERHEIT.md  .env.example  START-DEMO.bat
```

---

## 3. Starten und Prüfen

**Demo (ohne AWS, ohne KI, kostenlos):**
```bash
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e .
JUSPERFECT_BETRIEBSART=lokal JUSPERFECT_ANBIETER=demo \
JUSPERFECT_JURNODES_ADAPTER=fixture JUSPERFECT_FIXTURE_PFAD=testdaten/akten \
JUSPERFECT_NUTZER_DATEI=testdaten/nutzer.json python -m jusperfect
```
Browser: `http://127.0.0.1:8765`, Nutzerkennung `ra-weber`.
Windows-Ein-Klick: **`START-DEMO.bat`** doppelklicken.

**Tests (immer vor dem Commit laufen lassen):**
```bash
.venv/bin/python -m unittest discover -s tests -p "test_*.py"
```
**Oberfläche syntaktisch prüfen:** `node --check jusperfect/static/app.js`

**Echte Akten (WebDAV-Ordnerexport):**
`JUSPERFECT_JURNODES_ADAPTER=webdav` + `JUSPERFECT_JURNODES_WEBDAV=J:\Akten`

---

## 4. Architektur — die tragenden Entscheidungen

Diese fünf Punkte sind der Kern. Wer sie aushebelt, bricht das Produkt.

### 4.1 Belegpflicht, fail-closed
Jede Aussage der KI muss eine Fundstellenkennung tragen (`[Q: D2-S1-P3]`), die auf eine
**tatsächlich mitgeschickte** Passage zeigt. Tut sie das nicht, wird die Aussage
**entfernt** — nicht nur markiert. Siehe `services/belegpflicht.py`
(`aussage_fail_closed`, `eintraege_fail_closed`) und `services/quellen.py`.
Beim Streaming strömt der Rohtext live, aber die Prüfung greift am Ende über den
**vollständigen** Text — die Garantie bleibt erhalten.

### 4.2 Der eine geprüfte Ausgang (`services/ausgang.py`)
**Die einzige Stelle, die zum Modell führt.** Sie prüft die Eingabe (nur Text darf
hinaus), bremst am Monatsbudget, ruft den Anbieter und schreibt den Verarbeitungsnachweis.
Analyse- und Entwurfsdienst gehen ausschließlich über ihn.
**Wer einen neuen KI-Aufruf baut, baut ihn über den Ausgang — niemals direkt am Provider.**

### 4.3 Verarbeitungsnachweis ohne Inhalte
Jeder Aufruf hinterlässt eine Zeile: wann, welche Funktion, welches Modell, welche Akte,
Tokens, Kosten — und das Material nur als **Kurzkennung** (Prüfsumme·Länge), **nie als
Aktentext**. Grund: Der Aktentext liegt dauerhaft in jur|nodes und optional genau einmal im
AWS-Fallgedächtnis; eine weitere Inhaltskopie im Nachweis widerspräche dem Datenminimierungsprinzip.
Siehe `domain/models.py::Nutzungseintrag`
und `GET /api/nachweis`.

### 4.4 Kein Inhalt im Protokoll
`security/protokoll.py` weist Felder wie `text`, `frage`, `antwort`, `passagen` **aktiv
zurück** (`ProtokollVerstoss`) und begrenzt Wertlängen. **Falle:** Ein Protokollfeld
`passagen=…` wirft eine Ausnahme — nutze `anzahl_passagen`.

### 4.5 Zurückschreiben nur mit Freigabe
Nach jur|nodes wird genau eine Sache geschrieben: ein Vermerk/Entwurf, den ein Mensch
ausdrücklich freigegeben hat. Die Freigabe ist an Nutzer, Akte, **Textprüfsumme** und
Prozesslauf gebunden (HMAC, `security/approval.py`). Ohne Freigabeobjekt gibt es keinen
Code-Pfad, der schreibt. Löschen gibt es nicht.

> Das vollständige Sicherheitsmodell steht in **`SICHERHEIT.md`** (16 Grundsätze).
> **Vor größeren Änderungen dort nachlesen** — es ist die Richtschnur, nicht Beiwerk.

---

## 5. Was gebaut ist

| Baustein | Dateien | Kurz |
|---|---|---|
| Cowork-Arbeitsfläche | `static/*` | Split-View Dokument \| Cowork \| Belege |
| Antwort-Streaming | `providers/*`, `services/analyse.py::frage_stream`, `web.py` | NDJSON; live, am Ende belegt gesetzt |
| Belegpflicht fail-closed | `services/belegpflicht.py` | unbelegte Aussagen fallen raus |
| Geprüfter Ausgang + Nachweis | `services/ausgang.py`, `services/kosten.py` | einziger Weg zum Modell |
| Workflow-Packs | `services/workflow.py`, `packs/*.json` | deterministische Beweisprüfung, **kein** KI-Aufruf |
| Posteingang (Watchfolder) | `services/watchfolder.py`, `services/posteingang.py` | Ordner bereitet vor, **Mensch entscheidet** |
| Eigene Aufträge | `services/auftraege.py` | `.txt`/`.md`; Anweisung + Material an Trennlinie |
| Referenzen | `services/referenzen.py` | Urteile/Gesetze als Kontext, Kennung `R…` |
| jur\|nodes-WebDAV-Adapter | `jurnodes/webdav_adapter.py` | `<Wurzel>/<Anwalt>/<Jahr>/<Aktenzeichen Bezeichnung>/` |
| Zwei-Fenster-Explorer | `static/*`, `web.py` | jur\|nodes ⇄ Arbeitsakte, Drag&Drop + Pfeile |
| Modelle je Aufgabe | `config.py::modell_fuer`, `services/ausgang.py` | Frage/Analyse/Triage/Entwurf getrennt wählbar |
| Haufe-Recherche | `static/app.js::haufeRecherche` | Direktlink, Browser-Sitzung des Nutzers |
| Aktenstatus aus dem Ordner | `jurnodes/webdav_adapter.py`, `ordnerpruefung.py` | Kennung „archiviert" im Ordnernamen; Prüfprogramm für den echten Bestand |
| Abschlussworkflow | `services/abschluss.py`, `static/*` | erst Export nach jurnodes, **dann** Löschung; acht Abnahmetests; Dialog mit Vorschau, Freigabehaken und Löschnachweis |
| Gezielte Berichtigung | `services/gedaechtnis.py::dokument_vergessen` | Abgeleitetes fällt mit (Kennungen sind positionsabhängig!) |
| Aufsicht | `services/aufsicht.py`, `static/*` | Ausnahmefälle sichtbar machen, ohne Akteninhalte; Knopf „Arbeitsbereiche“ |
| Anmeldung mit PKCE | `static/app.js` | Cognito Hosted UI, S256, Token nur im Arbeitsspeicher |

---

## 6. Konventionen (bitte beibehalten)

- **Sprache:** Code, Bezeichner, Kommentare, Doku und Oberfläche sind **Deutsch**.
  Fachbegriffe wie „Passage", „Beleg", „Freigabe", „Ausgang" konsistent verwenden.
- **Kommentare erklären das *Warum*,** nicht das Was — im Ton der vorhandenen Dateien
  (ganze Sätze, sachlich, oft mit der Abwägung dahinter).
- **Tests:** `unittest`, deutsche Testnamen, je Baustein eine Datei `tests/test_*.py`.
  Neue Fachlogik **immer** mit Test. Vor jedem Commit die volle Sammlung laufen lassen.
- **Optionale Bausteine sind standardmäßig aus** (leerer Ordnerpfad = Knopf unsichtbar).
  Muster: `aktiv`-Property am Dienst + Flag in `GET /api/status` + `hidden` im HTML.
- **Ordnergrenzen sind hart:** Jeder Dienst, der Dateien liest (Aufträge, Referenzen,
  Posteingang, WebDAV-Adapter), lehnt `..`, absolute Pfade und mehr als eine
  Unterordner-Ebene ab. Diese Prüfung beim Kopieren **nicht weglassen**.
- **Zwei Dokumente stehen still:** `ANLEITUNG.md` (für den Anwender) und
  `infra/IAM.md` samt `infra/iam-nur-claude.json` (Zugriffsrichtlinie) werden
  **nur auf ausdrückliche Anweisung** geändert — auch dann nicht beiläufig,
  wenn eine Umbenennung oder ein neuer Knopf sie eigentlich berühren würde.
  Die Anleitung ist das, was in der Kanzlei benutzt wird; die Richtlinie ist
  eine Sicherheitsgrenze. Beides soll sich nicht unter der Hand verschieben.
  Fällt dir auf, dass eines veraltet ist: **sagen, nicht ändern.**
- **Commits:** deutscher Betreff `jusperfect: …`, Fließtext mit Begründung.
- **Branch:** Für neue Arbeit einen frischen Zweig von `main` anlegen; nicht direkt auf `main` pushen.

---

## 7. Aktengedächtnis (gebaut, standardmäßig ausgeschaltet)

**Das Problem der Kanzlei:** Wird die Arbeit unterbrochen und am nächsten Tag oder bei
Eingang eines neuen Schriftsatzes fortgesetzt, beginnt heute alles von vorn. Der
Lebenssachverhalt muss neu gebildet werden, Dokumente neu eingelesen. Das ist lästig und
kostet unnötig Modell-Geld.

**Warum es heute so ist:** Der Prompt-Cache macht Wiederholungen *innerhalb* einer Sitzung
billig (~1/10), lebt aber nur Minuten. Am nächsten Tag: voller Preis, und die Aktenanalyse
wird neu gerechnet.

**Kostenbild (Größenordnung, Opus $5/$25 je Mio. Token; Bedrock Frankfurt weicht ab):**

| Vorgang | Eingabe | ca. |
|---|---|---|
| Frage mit voller Akte, ungecacht | ~25.000 Token | ~0,14 € |
| Frage in derselben Sitzung (gecacht) | ~25.000 Token | ~0,04 € |
| Aktenanalyse (Lebenssachverhalt neu bilden) | ~40.000 Token | ~0,28 € |
| **Wiederaufnahme mit Aktengedächtnis** | ~5.000 Token | **~0,05 €** |

**Umgesetzte Bauweise:**

- **Inhalt:** (1) **Lebenssachverhalt**, fortlaufend fortgeschrieben — gebaut vom
  *günstigen* Modell (dafür ist „Modelle je Aufgabe" schon da);
  (2) **Q&A-Verlauf** (Fragen samt belegter Antworten);
  (3) **extrahierte Dokumenttexte**, damit ein Vertrag später ohne Neu-Einlesen/OCR
  wieder verfügbar ist.
- **Speicherort:** **AWS im eigenen Konto der Kanzlei** (S3, Frankfurt, KMS-verschlüsselt).
  Begründung: jur|nodes-Speicher ist der Kanzlei **zu teuer**; AWS kostet für wenige KB
  je Akte praktisch nichts (Cent/Monat) und liegt in derselben gesicherten Umgebung wie
  die Verarbeitung — nicht bei einem fremden Anbieter.
- **Bauweise:** ein `Gedaechtnisdienst` hinter einer Speicher-Schnittstelle mit **zwei**
  Implementierungen — `lokal` (Datei, für Demo/Test) und `aws` (S3, für den Echtbetrieb),
  analog zum vorhandenen `speicher/`-Muster (lokal/aws). Beim Öffnen einer Akte wird das
  Gedächtnis automatisch geladen; ein neuer Schriftsatz wird **angehängt**, nicht alles neu
  gerechnet.

Technische Einzelheiten:

- `jusperfect/gedaechtnis/`: Datei- und S3-Speicher; S3 erzwingt SSE-KMS, Objektpfade
  enthalten nur SHA-256-Ableitungen der Aktenkennung.
- `services/gedaechtnis.py`: Wiederherstellung beim Öffnen, inkrementelles Anhängen,
  Speicherung ausschließlich fail-closed belegter Q&A und Fortschreibung des
  Lebenssachverhalts über den geprüften `Ausgang`.
- Das Gedächtnismodell ist `JUSPERFECT_MODELL_GEDAECHTNIS`, sonst das kleine Modell.
- Die Oberfläche zeigt den Lebenssachverhalt und bis zu fünf frühere Q&A; der Knopf
  **Gedächtnis** verarbeitet nur neue Dokumente.
- `DELETE /api/akten/{akte_id}/gedaechtnis` ist der berechtigungsgeprüfte Löschweg.
- SAM legt einen eigenen dauerhaften Bucket an, aktiviert die Funktion aber nicht:
  `JUSPERFECT_GEDAECHTNIS=aus` bleibt Vorgabe bis zur organisatorischen Freigabe.

> **Wichtig — Sicherheitsmodell:** Damit legt jusperfect erstmals etwas **dauerhaft** ab
> (bisher nur flüchtig, mit Ablauf). Das ändert Grundsatz 1 in `SICHERHEIT.md` von
> „jur|nodes ist die einzige dauerhafte Ablage" zu „jur|nodes **+ das AWS-Fallgedächtnis
> der Kanzlei**". **Diese Änderung muss in `SICHERHEIT.md` dokumentiert werden** und
> gehört in AVV/DSFA/Verarbeitungsverzeichnis (derselbe Rahmen wie für Bedrock).
> Das ist eine bewusste, von der Kanzlei getragene Entscheidung — nicht stillschweigend
> aktivieren. `SICHERHEIT.md`, `KONZEPT.md`, `.env.example` und die Infrastruktur-Dokumentation
> sind angepasst; AVV/DSFA/Verarbeitungsverzeichnis, Hinweise, Mandatsbedingungen und
> Speicherdauer bleiben vor dem Echtbetrieb organisatorisch zu bearbeiten.

---

## 8. Externe Abhängigkeiten und erledigte Restpunkte

- **Haufe:** Am 04.09.2026 war öffentlich kein dokumentierter Such-URL-Parameter auffindbar.
  Der vorhandene Knopf bleibt deshalb sicher beim Direktlink plus Zwischenablage. Haufe bietet
  inzwischen eine offizielle CoPilot-Schnittstelle an; für eine echte Integration werden deren
  technische Dokumentation, Vertrag und Zugangsdaten der Kanzlei benötigt. **Nicht raten.**
- **jur|nodes-API:** Der Hersteller bestätigt eine offene REST-API, stellt die umfangreiche
  Dokumentation aber auf dem jeweiligen Kundenserver bereit. Für den Abnahmetest des vorhandenen
  `http_adapter.py` braucht die Entwicklung daher die dortige OpenAPI-/Swagger-Datei oder
  Dokumentations-URL, eine Basis-URL und einen dafür beschränkten Testschlüssel. Beteiligte und
  Fristen bleiben bis dahin über den WebDAV-Adapter unstrukturiert.
- **Perfect Shield als Vorschaltstufe** ist nur ein Schalter, keine Anbindung. Die vorhandene
  Browser-Erweiterung stellt keine Anonymisierungs-API für jusperfect bereit; vor einer Anbindung
  ist ein expliziter lokaler Schnittstellenvertrag einschließlich Rückübersetzung nötig. Da das
  Konzept die Klartextverarbeitung im gesicherten Bedrock-Bereich bewusst festlegt, wird eine
  vorzeitige Aktivierung nun fail-closed abgewiesen statt in der Oberfläche Schutz vorzutäuschen.
- **Mehrfach-Dialog:** umgesetzt; begrenzter, serverseitiger Verlauf ausschließlich geprüfter
  Antworten, mit erneuter Beistellung der Originalbelege.

---

## 9. Fallen, die schon Zeit gekostet haben

- **Protokollfeld `passagen`** ist verboten → `anzahl_passagen` benutzen (siehe 4.4).
- **Aktionsleiste** braucht `flex-wrap`, sonst überlappt sie bei vielen Knöpfen die
  Belege-Spalte.
- **Der Entwurfs-Endpunkt antwortet mit 201**, nicht 200.
- **`.bat`-Dateien** brauchen CRLF — dafür gibt es `.gitattributes`.
- **Dateinamen mit `/`** (etwa „Testmann ./. Musterhaft") sind auf Windows ohnehin unzulässig; beim
  Anlegen von Testordnern in der Shell erzeugt `./` versehentlich Unterordner.
- **Der Demo-Anbieter** rechnet nur mit Stichwortabgleich und beachtet Umlaute genau;
  eine Frage ohne wörtliche Treffer führt korrekt zu „kein belastbarer Beleg".
- **Fundstellenkennungen tragen eine feste Dokumentnummer** (`D2-…` ist das Dokument mit
  der Nummer 2 im Gedächtnis). Die Nummer wird beim Aufnehmen einmal vergeben
  (`GedaechtnisDokument.nummer`, Zähler `Aktengedaechtnis.letzte_dokumentnummer`) und
  danach nie geändert; eine Lücke wird nicht wieder besetzt. Deshalb entfernt
  `dokument_vergessen` nur noch das, was dieses eine Dokument zitiert, statt den ganzen
  abgeleiteten Teil zu verwerfen. Gedächtnisse aus Fassung 3 kannten keine Nummern; beim
  ersten Lesen wird die damalige Listenstellung festgeschrieben, damit keine gespeicherte
  Kennung verrutscht (`Gedaechtnisdienst._nummern_sichern`, `schema_version` 4).
  Geprüft in `tests/test_gedaechtnis_nummern.py`.
- **Gelöscht wird nie ohne vorherigen Export.** Wer am Abschlussworkflow arbeitet: Die
  Reihenfolge in `services/abschluss.py::ausfuehren` ist die eigentliche Zusage, nicht
  eine Formalie. Jede Abkürzung dort ist ein Datenschutzfehler.
- **Der Echtbetrieb ist fail closed:** Ohne Guardrail, mit Testakten oder ohne
  KMS-Schlüssel startet die Anwendung nicht. Beim lokalen Testen mit
  `JUSPERFECT_BETRIEBSART=aws` deshalb alle vier Werte setzen (siehe
  `tests/test_config.py::ECHTBETRIEB`).

---

## 10. Wenn du hier weitermachst

1. Repo klonen; `main` trägt den vollständigen Stand.
2. `SICHERHEIT.md` und `KONZEPT.md` lesen — sie erklären das *Warum*.
3. Demo starten (Abschnitt 3), einmal durchklicken: Akte öffnen → Explorer → Frage
   stellen → Belege ansehen.
4. Tests laufen lassen (211 grün) — das ist die Ausgangslage.
5. Als Nächstes stehen an:
   - **Die Ordnerprüfung einmal auf dem echten Laufwerk laufen lassen**
     (`python -m jusperfect.ordnerpruefung "J:\Akten"`). Sie sagt, ob die
     Archiv-Kennung im Bestand einheitlich geschrieben wird. Ohne dieses Ergebnis
     steht der Abschlussworkflow auf einer ungeprüften Annahme.
   - **Die restliche Rechtsdokumentation** (DSFA, Datenschutzhinweise,
     Mandatsbedingungen) — die Grundlage dafür steht im Löschkonzept in
     `SICHERHEIT.md`.

Kleine, geprüfte Schritte mit Tests sind hier ausdrücklich erwünscht — jeder der bisher
gebauten Bausteine ist genau so entstanden.

---

## Fortsetzung am 11.09.2026: Stand bei Sitzungswechsel

Dieser Abschnitt ist der **Informationsstand beim Wechsel in eine neue Sitzung**.
Wer hier weiterarbeitet, liest ihn zuerst, dann `MORGEN.md` (die Arbeitsliste).

### Verbindliche Regeln der Kanzlei (gelten weiter, ohne Ausnahme)

1. **Deutsch.** Der Nutzer ist Rechtsanwalt, kein Programmierer. Ganze Sätze,
   kein Fachjargon, Dateipfade immer vollständig nennen.
2. **Zweig `2.0`, Fassung `2.0.0.dev`.** `fassung-1.0` bleibt unangetastet als
   Rückfallebene. **Niemals auf einen anderen Zweig pushen.**
3. **Niemals einen Pull Request eröffnen**, ohne dass der Nutzer darum bittet.
4. **`ANLEITUNG.md`, `infra/IAM.md` und `infra/iam-nur-claude.json` werden nur
   auf ausdrückliche Anweisung geändert.** Sind sie veraltet: sagen, nicht ändern.
   Dasselbe gilt für `SICHERHEIT.md`, sobald eine neue Art dauerhaften Inhalts
   entstünde (zum Beispiel dauerhaft gespeicherte Entwürfe).
5. **Kein Modellbezeichner** in Commit-Nachrichten, PR-Texten, Quelltext­kommentaren
   oder sonstigen Dateien des Repositoriums. Nur in der Unterhaltung.
6. **Kleine, geprüfte Schritte.** Jeder Baustein ist so entstanden.
7. **Nach jeder Änderung an der Oberfläche einmal in einem echten Browser
   nachsehen**, nicht nur Tests laufen lassen. Chromium liegt unter
   `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`, Playwright ist da.
8. `.bat`-Dateien brauchen CRLF (über `.gitattributes` geregelt); `cmd` kann
   keine geklammerten Blöcke — mit Sprungmarken arbeiten.
9. **Belegpflicht, fail closed.** Jede Aussage trägt eine stellenabhängige
   Kennung `D<n>-S<n>-P<n>`. Ohne Beleg keine Aussage. Das ist kein Beiwerk,
   sondern der Kern des Programms.
10. **Bei Dritten warten, nicht raten** (jur|nodes-REST-Schnittstelle,
    Haufe CoPilot).
11. **Eine erledigte Aufgabe wird sofort abgehakt, ohne Nachfrage.** Aus der
    Kanzlei am 28.09.2026: „hake 7 ab wenn sie erledigt, mache das immer
    automatisch." Also: in `MORGEN.md` durchstreichen mit Datum und Begründung,
    und dieselbe Stelle in der Übersichtsseite nachziehen, falls eine offen
    ist. **Nicht löschen** — wer später nachsieht, will erkennen, was schon
    getan wurde und warum.

    Der Grund für die Regel steckt in ihrer Vorgeschichte: Am 22.09.2026
    standen drei längst gelöste Punkte noch auf der Liste, und Aufgabe 7 stand
    siebzehn Tage darauf, obwohl sie erfüllt war. Eine Arbeitsliste, die nicht
    mitgeführt wird, kostet Zeit an der falschen Stelle — und zwar zuerst bei
    dem, der ihr glaubt.

### Offene Frage an den Nutzer — **beantwortet am 28.09.2026**

Die Frage lautete: Darf `ModellAbonnement` in `infra/iam-nur-claude.json`
aufgenommen werden? Ohne diese Berechtigung lässt sich nicht anzeigen, welche
Modelle das Konto in Frankfurt buchen kann.

**Aus der Kanzlei am 28.09.2026: „zugriffsrichtlinie erlaubt".**

**Zu ändern war trotzdem nichts.** Die Berechtigung steht bereits in der Datei,
im Abschnitt `ModelleAnsehen` als `aws-marketplace:ViewSubscriptions`, und
`infra/IAM.md` beschreibt sie dort auch so. Die Frage stand seit dem 11.09.2026
hier und war offenbar längst erledigt — nur der Vermerk blieb stehen.

**Lehre, dieselbe wie am 22.09.2026:** Eine Liste offener Punkte, die nicht
mitgeführt wird, kostet Zeit an der falschen Stelle. Wer hier weiterarbeitet,
prüfe vor dem Anfassen eines Punktes erst, ob er nicht schon gelöst ist.

Was bleibt, ist eine Bestätigung, nicht eine Änderung: Die Datei im
Programmordner ist die **Vorlage**; wirksam ist die Richtlinie im AWS-Konto.
Ob sie dort dieselbe Zeile trägt, sagt ein Lauf von `MODELLE-ANZEIGEN.bat` —
erscheint die Modellliste, ist alles in Ordnung.

### Wo das Programm steht

- 615 Tests grün (`.venv/bin/python -m pytest -q`).
- `FUNKTIONSPROBE.bat` geht alle Wege mit dem Demo-Anbieter durch: 34 von 34
  Prüfungen bestehen. Sie misst ausdrücklich **nicht** die inhaltliche Güte.
- Örtlicher Start: `START-DEMO.bat` (ohne KI), `START-AWS.bat` (Bedrock,
  Betriebsart lokal). Das Aktengedächtnis liegt dabei als Datei auf dem Rechner;
  S3 mit KMS ist noch nicht eingerichtet (siehe `AWS-EINRICHTEN.md`).

Fertig und geprüft seit der letzten Übergabe:

- **Aktengedächtnis** mit wachsendem Lebenssachverhalt und Chronologie, feste
  Dokumentnummern (`GedaechtnisDokument.nummer`), Schema 4, Portionsweises
  Einlesen großer Akten (`services/gedaechtnis.py`, `akte_einlesen`).
- **Analyse über das Gedächtnis** (`services/analyse.py`,
  `analysieren_ueber_gedaechtnis`) — geprüft wird gegen **alle** Passagen, nicht
  nur gegen die mitgeschickten.
- **Genaue Querverweismarkierung** ohne Modellaufruf (`services/fundstelle.py`),
  je Beleg eine eigene Fundstelle über `POST /api/sitzungen/{id}/fundstelle`.
- **Oberfläche:** Anmeldeseite mit Benutzerauswahl, Verlauf, Fensterknöpfe mit
  Schließpfeilen, Explorer mit Häkchen statt Drag & Drop, Fortschrittsbalken
  beim Einlesen, Ausgrauen dessen, was schon im Gedächtnis liegt.
- **Neu am 10.09.2026:** der Wartekreis an den Arbeitsknöpfen (`wartekreis()` in
  `jusperfect/static/app.js`), alle vier Schließpfeile nach links, und das
  Sichern beim Schließen (`POST /api/sitzungen/{id}/gedaechtnis/sichern`,
  `Gedaechtnisdienst.sichern`) mit einer Meldung, die mit Zahlen sagt, was im
  Gedächtnis liegt und was ausdrücklich **nicht** gespeichert wird.

### Was der erste echte Bedrock-Lauf ergeben hat (10.09.2026)

Große Testakte 44/26 BA, 50 Dokumente, rund 882.000 Zeichen, abschnittsweise
eingelesen, danach Analyse über das Gedächtnis. Kosten: 0,28 €, 27.050 Token.

**Vier von fünf eingebauten Funden gefunden**, alle mit richtigen Fundstellen
und über Portionsgrenzen hinweg: doppeltes Abnahmedatum (D39/D44 gegen D12),
Rügezeitpunkt (D44 gegen D8/D9), abwesender Polier (D46 gegen D17), Kenntnis
der Rüge (D27 gegen D9). Keine berechnete Verjährungsfrist — die Fristensperre
hält. Alle fünf Zahlen der Auflösung stehen unter „Forderungen".

**Nicht gefunden:** Fund 5, die Dämmstärke (24 cm geschuldet, 18 cm gemessen,
24 cm abgerechnet). Alle drei Bausteine liegen belegt im Gedächtnis, werden
aber nicht zusammengezogen. Ursache erkannt: Die `WIDERSPRUCHS_REGEL` in
`jusperfect/services/prompts.py` (ab Zeile 240) nennt vier Arten von
Widersprüchen — genau die vier wurden gefunden. Die Art **„Maß und Menge"**
fehlt.

Zwei weitere Befunde desselben Laufs, sauber nach Ursache getrennt:

- **Rauschen:** Die Chronologie hat 68 Zeilen, rund vierzig davon
  Kolonnenstärken aus Bautagebüchern. Der Lebenssachverhalt hat Positionslisten
  von Aufmaßblättern seitenweise mitgeschrieben. Beides ist belegt und richtig
  und verdrängt trotzdem das Wesentliche.
- **Die Testdaten selbst sind teils unsinnig** — und das ist nicht dem Modell
  anzulasten: In den 45 Fülldokumenten der großen Akte sind Absender, Datum und
  Inhalt unabhängig voneinander gewürfelt (Beispiel:
  `testdaten/grosse-akte/BA-2026-0044/19_bautagebuch_august_2025.txt`, Absender
  Marlies Kettenbach, datiert 27.07.2025, mit Einträgen ab 03.03.2025).
  Solange das so ist, lässt sich Inhaltsgüte nicht messen.

### Die Arbeitsliste

Steht vollständig in **`MORGEN.md`** mit Begründung und vorgeschlagener
Reihenfolge. Kurz: Testdaten in Ordnung bringen; die fünfte Widerspruchsart
einbauen; das Rauschen begrenzen; Scanfehler kenntlich machen
(`l5.03.2026` wird still zu `15.03.2026` korrigiert — das bricht auch die neue
Markierung); Grundmieten in die Forderungen; Geburtsdaten zu den Beteiligten;
Ordnerprüfung auf `J:\Akten` und das AWS-Gedächtnis sind Handgriffe des Nutzers.

---

## Fortsetzung am 17.09.2026: Stand bei Sitzungswechsel

Dieser Abschnitt ersetzt den vorangehenden als **jüngster Informationsstand**.
Wer hier weiterarbeitet, liest ihn zuerst, dann `MORGEN.md`.

### Verbindliche Regeln der Kanzlei

Die zehn Regeln des Abschnitts vom 11.09.2026 gelten unverändert weiter. Zwei
Ergänzungen aus der Arbeit seither:

- **Geschützt sind vier Dateien**, nicht drei: `ANLEITUNG.md`, `infra/IAM.md`,
  `infra/iam-nur-claude.json` und **`SICHERHEIT.md`**. Alle vier nur auf
  ausdrückliche Anweisung ändern. Sind sie veraltet: **sagen, nicht ändern.**
  Beide Male, als der Nutzer die Änderung ausdrücklich verlangt hat, wurde sie
  gemacht und im Commit als solche kenntlich gemacht.
- **Tests laufen mit pytest**, nicht mit unittest:
  `.venv/bin/python -m pytest -q`. Stand 17.09.2026: **826 grün.**

### Wo das Programm steht

- Zweig `2.0`, Fassung `2.0.0.dev`, jüngste Änderung `9c9c189`.
- **`2.0` ist seit dem 15.09.2026 der Standardzweig auf GitHub.** Vorher war es
  `main` mit der Fassung 1.0. Wichtig für jeden, der einen Zusammenführungslauf
  erwägt: `main` und `2.0` haben **keinen gemeinsamen Vorfahren**; ein Merge
  würde in rund 89 Dateien Konflikte erzeugen. Der Umweg über den Standardzweig
  war die Lösung, nicht ein Merge.
- Eine ZIP für die Kanzlei erzeugt man mit
  `git archive --format=zip --prefix=jusperfect-<TT.MM.JJJJ>/ HEAD -o <Ziel>.zip`.
  Ohne `--prefix` liegen alle Dateien lose in der ZIP; beim Auspacken landen
  dann rund 200 Dateien mitten im Downloadordner. Am 25.09.2026 ist genau das
  dreimal hintereinander passiert, bis die Kanzlei fragte: „warum gibt es
  keinen überordner der jusperfect heißt". Der Befehl stand da schon hier —
  er wurde nur nicht gelesen.
- **Das Datum gehört in den Ordnernamen, nicht nur in den Dateinamen.** Wer
  drei Fassungen an einem Tag bekommt, sieht sonst am offenen Ordner nicht
  mehr, welche davon läuft. Die Startdateien zeigen den Stand zwar an, aber
  erst nach dem Starten.
- `git archive` ersetzt dabei `$Format:%H %cs$` in `FASSUNG.txt` durch Nummer
  und Datum. **Diese Datei niemals im Arbeitsbaum ausfüllen** — damit nimmt man
  ihr genau die Automatik, derentwegen sie da ist. Der Prüfbogen meldet es.

### Die Modellkennungen — das Wichtigste zum Merken

Am 16.09.2026 ist ein Prüfbogenlauf daran gescheitert, dass eine Modellkennung
aus dem **Anzeigenamen** im AWS-Katalog abgeleitet wurde („Opus 4.6" →
`anthropic.claude-opus-4-6`). Das ist falsch, und es kostete drei Anläufe.

Das Konto der Kanzlei führt am 16.09.2026 genau diese fünf:

| Modell | Kennung | Bauart |
|---|---|---|
| Opus 4.6 | `anthropic.claude-opus-4-6-v1` | „-v1", kein Datum |
| Opus 4.5 | `anthropic.claude-opus-4-5-20251101-v1:0` | Datum und Fassung |
| Sonnet 4.6 | `anthropic.claude-sonnet-4-6` | weder noch |
| Sonnet 4.5 | `anthropic.claude-sonnet-4-5-20250929-v1:0` | Datum und Fassung |
| Haiku 4.5 | `anthropic.claude-haiku-4-5-20251001-v1:0` | Datum und Fassung |

**Drei Bauarten bei fünf Modellen. Es gibt kein Muster.** Eine Kennung wird
**abgefragt, nicht hergeleitet** — `MODELLE-ANZEIGEN.bat` fragt das Konto und
probiert jedes Modell mit einem Wort an. Nicht zugeteilt sind Opus 4.7, 4.8,
Opus 5 und Sonnet 5; Sonnet 4 ist abgemeldet (LEGACY).

Den europäischen Vorsatz `eu.` setzt `config.py::_modellkennung` selbst, und
zwar für **alle sechs** Modellfelder — vorher nur für `modell_id`, was jedem,
der ein Modell je Aufgabe eintrug, eine Abweisung einbrachte.

Eingetragen sind die Kennungen in `START-AWS.bat`, `PRUEFBOGEN.bat`, der
Voreinstellung in `jusperfect/config.py` sowie den Tabellen in
`AWS-EINRICHTEN.md` und `ANLEITUNG.md`.

### Was seit dem 11.09.2026 dazugekommen ist

**Der Prüfbogen** (`werkzeug/pruefbogen.py`, `PRUEFBOGEN.bat`) misst einen
echten Lauf über die große Testakte gegen `testdaten/grosse-akte/AUFLOESUNG.md`
und sagt, welcher der fünf eingebauten Funde benannt wurde, mit welchen
Fundstellen. Er prüft zusätzlich Zeitstrahl, Zahlen und Fristensperre.

**Das Startbild / der Selbsttest** (`jusperfect/services/selbsttest.py`) prüft
acht Punkte — Anbieter, Region, Zugang, Mitschrift, Guardrail, Akten,
Gedächtnis, Kosten — und zeigt darunter jedes eingebundene Modell mit der
Arbeit, die es tut. Der **Modell-Testlauf** ruft jedes einmal auf (ein Wort,
Bruchteile eines Cents). Dazu eine Animation: ein Wagen fährt die Strecke ab,
an der Zielflagge steht das Ergebnis.

**Die Startprüfung der Modellaufrufprotokollierung** (`jusperfect/modellprotokoll.py`):
Ist bei Bedrock die Mitschrift der Modellaufrufe **eingeschaltet**, startet das
Programm nicht. Ist sie **unbekannt**, startet es nur mit den Testakten. Das ist
fail closed und war die Bedingung dafür, mit echten Akten anzufangen.

**Der Vorschlagsweg**, **eigene Aufträge**, **ZUGANG-PRUEFEN.bat** und
**MODELLE-ANZEIGEN.bat** sind dazugekommen; die Guardrail-Lücke im örtlichen
Betrieb ist geschlossen (`config.py`: Bedrock + echte Akten ohne Guardrail
startet nicht mehr, auch nicht in der Betriebsart `lokal`).

### Der Prüfbericht einer dritten KI (PRUEFBERICHT-2026-09-16.md)

Drei Befunde hoher Priorität. **Alle drei sind reproduziert und behoben:**

1. **Belegpflicht** (`services/belegpflicht.py`): Alles nach dem letzten
   `[Q: …]` ging ungeprüft durch. Jetzt darf dort nur noch Satzzeichen und
   Leerraum stehen; ein Nachsatz wird entfernt und gezählt. — `df76bdb`
2. **Fristensperre** (`services/fristen.py`): Ein Datum galt als Fristbeleg,
   sobald es irgendwo in der Akte vorkam. Ein **Fristende** muss jetzt dort als
   Endpunkt belegt sein; ein **Fristbeginn** muss nur vorkommen. — `0a3ffb1`
3. **Abgebrochener Antwortstrom** (`static/app.js`): Rohtext blieb stehen.
   Jetzt wacht `gepruefteAntwort` darüber. — `070fdc4`

**Offen aus demselben Bericht:** die Testeinrichtung. `pyproject.toml` führt
pytest nicht als Abhängigkeit, und `.github/workflows/tests.yml` läuft mit
`python -m unittest discover`. Damit sammelt die automatische Prüfung die
freien pytest-Testfunktionen nicht ein — sie misst weniger als der örtliche
Lauf. Siehe `MORGEN.md`, Punkt 1.

### Der erste Prüfbogenlauf (16.09.2026, 21:50)

Gelaufen mit **Sonnet 4.5**, nicht mit dem eingestellten Opus 4.6 — die
Startdatei setzte damals noch gar kein Modell und übernahm eine dauerhafte
Windows-Einstellung. Das ist behoben; beide Startdateien setzen ihr Modell
jetzt **unbedingt** und schreiben es vor dem Lauf auf den Schirm.

Ergebnis (7 Portionen, 676 Passagen aus 50 Dokumenten, 0,14 €, 17.348 Token):

- **Alle fünf Widersprüche wurden benannt.** Der Bogen zählte vier, weil er bei
  Fund 5 den Beleg aus D-002 (Leistungsverzeichnis) verlangt; das Programm
  hatte die geschuldeten 24 cm am Bautagebuch D-017 festgemacht. Sachlich wahr,
  juristisch die schwächere Fundstelle. **Das ist der einzige echte Mangel.**
- **Zeitstrahl: 41 Einträge, 0 % Bautagebuch-Routine.** Der Rauschfilter
  arbeitet einwandfrei. Fünf von dreizehn tragenden Tagen fehlen, und zwar nach
  einem Muster: Das Programm trägt **das Ereignis ein, von dem ein Schriftstück
  handelt, nicht das Datum des Schriftstücks selbst**. Für eine Kanzlei ist das
  zu wenig — Schriftsatzdaten tragen Fristen. Siehe `MORGEN.md`, Punkt 3.
- **Zahlen: 5 von 5.** Der Bogen meldete zunächst 4 von 5 — ein Fehler des
  Messgeräts, nicht des Programms (siehe unten).
- **Fristensperre hält**, obwohl die Gegenseite in der Akte ausdrücklich eine
  Verjährung ab dem 02.07.2025 behauptet.

### Das Messgerät hat selbst falsch gemessen

`werkzeug/pruefbogen.py` durchsuchte die Forderungen im Feld `bezeichnung`; das
Feld heißt `gegenstand`. Bei den Beteiligten: gesucht in `name`, benannt ist
`bezeichnung`. Beide Abschnitte waren stumm, und aus einem richtigen Ergebnis
wurde ein falsches. — `63fa248`

Dass die 786 vorhandenen Prüfungen das nicht gemerkt haben, hatte einen Grund:
**keine einzige hatte je eine Forderung oder einen Beteiligten gebaut.** Zwei
neue Prüfungen halten die Feldnamen jetzt unmittelbar an
`jusperfect/domain/models.py::Aktenanalyse`, statt sie abzuschreiben.

**Merksatz für jede Weiterarbeit am Prüfbogen:** Ein Messgerät, das falsch
misst, ist schlimmer als keines — es gibt Sicherheit, wo keine ist.

### Der Fehler, der drei Anläufe gekostet hat

Am Abend des 16.09.2026 lief in der Kanzlei ein Ordner, in dem der Programmteil
`jusperfect\` neu und die Startdateien daneben alt waren. Von außen sah das aus
wie ein Fehler im Programm; gesucht wurde zweimal an der falschen Stelle.

Zwei Gegenmittel sind eingebaut:

- **`FASSUNG.txt`** trägt Nummer und Datum der Änderung. Git setzt sie beim
  Erzeugen einer ZIP ein (`export-subst` in `.gitattributes`); im
  Arbeitsverzeichnis steht die unersetzte Vorlage, und die Auskunft lautet dann
  „Arbeitsverzeichnis". Angezeigt wird der Stand vor dem Start in beiden
  Startdateien, in der Kopfzeile jedes Bogens und im Abbruchtext.
- **Beim Abbruch eines Prüfbogenlaufs** steht jetzt, mit welchen Kennungen
  gearbeitet wurde, je Funktion, **und aus welcher Einstellung jede stammt**
  (`Einstellungen.modell_herkunft`). Sechs Einstellungen kommen in Frage; wer
  die falsche aufmacht, sucht umsonst.

Beides fängt den Mischzustand nicht — dafür müsste jede Datei ihre eigene
Nummer tragen. Es beantwortet aber die erste Frage, die man dann stellt.

### Was in der Kanzlei noch offen ist (Handgriffe des Nutzers)

1. **Das Guardrail einrichten.** Ohne es startet das Programm mit echten Akten
   nicht — das ist so gewollt. Anleitung: `AWS-EINRICHTEN.md`, Schritt 9.
   **Die PII-Filter bleiben dabei aus**, sonst schwärzt das Geländer die
   Mandantennamen aus dem eigenen Aktentext.
2. **Ordnerprüfung** auf dem echten Laufwerk:
   `python -m jusperfect.ordnerpruefung "J:\Akten"`.
3. **DSFA, Datenschutzhinweise, Mandatsbedingungen.**
4. Der zweite Prüfbogenlauf mit Opus 4.6 stand am Abend des 16.09.2026 noch
   aus; der erste war zu diesem Zeitpunkt nicht durchgelaufen.

### Angebote, die der Nutzer noch nicht angenommen hat

- Ein Satz für **`SICHERHEIT.md`, Grundsatz 15**, der den Haufe-Zugang als
  datenschutzkonform mit AVV und Löschfunktion festhält. Die Datei ist
  geschützt — vorschlagen, nicht eintragen.
- Entwürfe dauerhaft aufheben (neue Art dauerhaften Inhalts → `SICHERHEIT.md`).
- Ein Knopf „alle Verweise prüfen".
- „Was hat sich seit gestern geändert" für neu eingegangene Schriftsätze.

### Kleinigkeiten, die notiert, aber nicht behoben sind

- Die Kopfzeile läuft bei 1024 px mit langen Modellkennungen über.
- `bedrock:ApplyGuardrail` fehlt möglicherweise in
  `infra/iam-nur-claude.json`, sobald ein Guardrail eingerichtet ist. Die Datei
  ist geschützt — **sagen, nicht ändern.**
- Neuere Modelle (Opus 5, Sonnet 5) weisen `temperature` zurück;
  `providers/bedrock.py` schickt es immer mit. Beim Konto der Kanzlei fällt das
  heute nicht auf, weil diese Modelle nicht zugeteilt sind.

---

## Die Messung vom 17.09.2026: welches Modell die Akte einliest

Das ist das Ergebnis, auf das die Arbeit der beiden Vortage hinauslief. Es ist
**die** Festlegung, die man kennen muss, bevor man an den Prompts arbeitet.

### Der Versuchsaufbau

Zwei Prüfbogenläufe über die große Testakte 44/26 BA, am selben Tag, auf
demselben Rechner, mit demselben Programmstand. Ein einziger Unterschied:
`JUSPERFECT_MODELL_GEDAECHTNIS` – **welches Modell die fünfzig Dokumente
einliest.** Die Analyse danach lief in beiden Fällen auf Opus.

| | Haiku 4.5 liest ein | **Opus 4.6 liest ein** |
|---|---|---|
| Funde benannt und belegt | 3 von 5 | **5 von 5** |
| Zahlen der Auflösung | 4 von 5 | **5 von 5** |
| Bautagebuch-Routine | 2 % | **0 %** |
| Einlesen | 0,51 € · 416.088 Token | 2,56 € |
| Analyse | 0,27 € | 0,27 € |
| **Zusammen** | **0,78 €** | **2,83 €** |

**Der Lauf mit dem schlechteren Ergebnis hatte das bessere Analysemodell** –
Opus 4.6 gegen Opus 4.5. Die Ursache liegt damit nachweislich nicht in der
Auswertung, sondern im Einlesen. Ein starkes Analysemodell kann nicht
ausgleichen, was beim Lesen weggelassen wurde.

### Was genau verlorenging – der eigentliche Befund

Im Haiku-Lauf kommen **zwei Dokumente im gesamten Ergebnis nicht vor**:

- **D-002, das Leistungsverzeichnis** – die Vertragsurkunde
- **D-008, die Mängelanzeige** – die Rüge

Die Folgen sind juristisch lehrreich und lassen sich verallgemeinern:

- Ohne das Leistungsverzeichnis lässt sich nicht sagen „geschuldet 24 cm,
  ausgeführt 18 cm". Der Widerspruch **zerfällt in zwei halbe** – einmal
  Abrechnung gegen Gutachten (D-017, D-031, D-050), einmal Zeuge gegen
  Gutachten (D-017, D-031, D-046). Beide für sich richtig, beide schwach, die
  Anspruchsgrundlage fehlt.
- Ohne die Mängelanzeige verschwindet der Rügezeitpunkt als eigener Punkt und
  geht in der Kenntnisfrage auf. Aus fünf Widersprüchen werden fünf Einträge
  über **vier** Sachen.
- Die 402,00 m² Dämmfläche stehen in D-002 und fehlen deshalb ganz.

**Das schwache Modell hat die Akte nicht falsch gelesen. Es hat beim
Zusammenfassen die Urkunden weggelassen und das Geschehen behalten.** Für eine
Kanzlei ist das die falsche Auswahl – und sie fällt nicht auf: Das schwächere
Ergebnis wirkt fleißiger (8 offene Punkte statt 6, 10 Hinweise statt 7, 19
Beweismittel statt 16) und hat nur weniger Forderungen und die falschen
Urkunden.

### Die Festlegung

`START-AWS.bat` setzt seit dem 17.09.2026:

```
set JUSPERFECT_MODELL_GEDAECHTNIS=anthropic.claude-opus-4-6-v1
```

Haiku 4.5 bleibt für die Eingangsprüfung – Fließbandarbeit, dort ist nichts zu
verlieren.

**Wer das rückgängig machen will, soll die Zahlen oben kennen.** Die Mehrkosten
von 2,05 € fallen **einmal je Akte** an, nicht je Frage: Das Aktengedächtnis ist
dauerhaft, ein neuer Schriftsatz wird angehängt. Die Testakte hat fünfzig
Dokumente und 882.000 Zeichen; die meisten echten Akten sind kleiner.

### Ein Befund, der NICHT am Modell hängt

Die fünf fehlenden Tage im Zeitstrahl sind in **allen drei Läufen dieselben** –
bei Sonnet 4.5, bei Haiku 4.5 und bei Opus 4.6:

> 14.02.2025 Leistungsverzeichnis · 02.09.2025 Schlussrechnung ·
> 18.02.2026 Gutachten · 11.03.2026 Schriftsatz der Gegenseite ·
> 08.04.2026 Zeugenbenennung

Drei Modelle, dasselbe Loch. Die Ursache liegt in der `CHRONOLOGIE_REGEL` in
`jusperfect/services/prompts.py`: Der Zeitstrahl trägt das **Ereignis** ein, von
dem ein Schriftstück handelt, nicht das **Datum des Schriftstücks**. Für eine
Kanzlei ist das zu wenig – daran hängen Fristen. Das ist Punkt 1 in `MORGEN.md`.

### Was auf dem Weg dorthin schiefging – zum Lernen

Drei Läufe waren nötig, weil das Messgerät dreimal etwas anderes maß, als es
sagte. Alle drei Fehler haben dieselbe Form:

1. **Die Datei setzte gar kein Modell** und übernahm eine dauerhafte
   Windows-Einstellung. Der Bogen lief mit Sonnet 4.5 statt Opus.
2. **Sie setzte dann zwei von sechs** Modelleinstellungen. Ein dauerhaftes
   `JUSPERFECT_MODELL_ANALYSE` schob die Analyse auf Opus 4.5.
3. **Die Längengrenze** stand auf 8.000 Ausgabetoken, die Analyse brauchte
   6.753 und 7.777 – beim dritten Lauf riss sie, und das bezahlte Einlesen war
   verloren.

**Die Lehre:** Ein Messgerät muss jede Einstellung, die sein Ergebnis
beeinflusst, selbst setzen und sie im Ergebnis ausweisen. Der Bogen nennt
deshalb jetzt jede Arbeit mit ihrem Modell, seinen Programmstand aus
`FASSUNG.txt` und beide Kostenposten getrennt.

---

## Fortsetzung am 22.09.2026: die Programmarbeit ist abgeschlossen

857 Prüfungen grün. Am Programm ist nichts offen, was eine Akte betrifft; was
bleibt, sind Handgriffe der Kanzlei (siehe `MORGEN.md`).

### Der Zeitstrahl kennt jetzt das Datum des Schriftstücks

Der letzte substanzielle Befund der Messreihe. Die Ursache stand in der
`CHRONOLOGIE_REGEL` in `jusperfect/services/prompts.py` selbst, und zwar in
einem gut gemeinten Satz: **„Keine Briefkopf- und Kopfzeilen."**

Das Datum eines Schriftstücks **steht** im Briefkopf. Gemeint war, dass ein
Eintrag mehr sagen muss als „Göttingen, den 04.05.2026". Gewirkt hat es als
Verbot, das Schriftstück überhaupt zu vermerken – in drei Läufen mit drei
Modellen fehlten dieselben fünf Tage.

Die Regel sagt nun beides:

- **Ein Schriftstück, das den Fall vorantreibt, ist selbst ein Ereignis** – an
  seinem eigenen Datum, nicht an dem des Vorgangs, von dem es berichtet. Mit
  dem Beispiel, das es entscheidet: Eine Schlussrechnung vom 02.09.2025, die
  eine Abnahme am 02.07.2025 behauptet, gehört **zweimal** hinein.
- **Nicht selbst ein Ereignis** sind Bautagebücher, Aufmaßblätter,
  Stundenzettel, Lichtbildmappen und Empfangsbekenntnisse. Diese Gegenliste ist
  der Preis: Der Rauschwert stand in zwei Läufen bei 0 %, und die neue Regel
  darf ihn nicht zurückholen.

**Nicht am echten Modell gemessen.** Der nächste Prüfbogenlauf muss beides
zugleich zeigen: die fünf Tage kommen dazu, und der Rauschwert bleibt bei 0 %.
Steigt er, gehört die Gegenliste nachgeschärft – nicht die Regel zurückgenommen.

### Die Geländer-Probe: die Lücke vor der ersten echten Akte

Der Selbsttest sagte, **dass** ein Guardrail hinterlegt ist. Ob es brauchbar
eingestellt ist, sagte niemand.

Die Gefahr ist einseitig und leicht zu unterschätzen: Die Voreinstellungen eines
Bedrock-Guardrails sind für Anwendungen gedacht, in denen Gewalt, Sexuelles und
Beleidigungen nichts zu suchen haben. **In einer Kanzlei sind genau das die
Fälle.** Eine Körperverletzungssache *ist* Gewalt; eine Beleidigungsklage muss
die Beleidigung wiedergeben dürfen. Ein zu scharfer Filter fällt nicht dadurch
auf, dass er etwas Falsches tut, sondern dadurch, dass eine gewöhnliche Frage zu
einer gewöhnlichen Akte mit einer Sperrmeldung endet.

Der **Modell-Testlauf** im Selbsttest schickt deshalb, wenn ein Geländer
hinterlegt ist, fünf erfundene Sätze hindurch (`GELAENDERPROBEN` in
`jusperfect/services/selbsttest.py`): Bausache als Kontrolle,
Kündigungsschutz, Körperverletzung, Beleidigung, Familien- und
Sexualstrafrecht. Je Rechtsgebiet eine eigene Zeile – sammelte man sie in einen
Satz, wüsste niemand, welcher Filter zuschlug.

Zwei Befunde werden dabei streng getrennt, weil sie Verschiedenes verlangen:

- **„Vom Geländer angehalten"** – das Geländer arbeitet, ist aber zu scharf.
  Ein Handgriff in der AWS-Konsole.
- **„Nicht geprüft – …"** – es liess sich gar nicht fragen. Ein fehlendes Recht
  (`bedrock:ApplyGuardrail`), eine falsche Kennung, kein Netz.

Die Probe geht über `modelle.py::_gelaender_anprobieren` und benutzt
`guardContent` an derselben Stelle wie der Betrieb (`providers/bedrock.py`) –
sonst prüfte sie etwas anderes als das, was später läuft.

### Die Kopfzeile

Notiert war „läuft bei 1024 px über". In echtem Chromium war es etwas anderes
und Schlimmeres: Sie lief nicht über – das Flexbox-Layout hielt sie zusammen –,
sie **quetschte die Aktenbezeichnung** von 187 auf 34 Pixel, also auf „44…".

Im Kopf steht jetzt „Bedrock Opus 4.6"; die vollständige Kennung im Tooltip, die
genauen Kennungen im Selbsttest. Die Verkürzung in `app.js::kurzeKennung` ist
vorsichtig gebaut: Greift das Muster nicht – eine ARN, ein fremder Anbieter –,
bleibt die Kennung unverändert. Eine falsch verkürzte Kennung wäre schlimmer als
eine lange.

### Drei Punkte der Arbeitsliste waren längst erledigt

Sie standen nur noch da: Scanfehler kenntlich machen (`SYSTEM`, Punkt 8, und
`services/fundstelle.py`), Grundmieten nebeneinander in die Forderungen
(`FORDERUNGS_REGEL`) und Geburtsdaten zu den Beteiligten (`ROLLEN_REGEL`).

**Lehre daraus:** Eine Arbeitsliste, die nicht mitgeführt wird, kostet Zeit an
der falschen Stelle. Wer hier weiterarbeitet, prüfe vor dem Anfassen eines
Punktes erst, ob er nicht schon gelöst ist.

### Die jur|nodes-Anbindung: gefragt statt geraten

**Der Stand der Sache ist unverändert:** Der Hersteller bestätigt eine offene
REST-Schnittstelle, stellt die Dokumentation aber auf dem jeweiligen
Kundenserver bereit. Uns liegt sie nicht vor, und die Regel gilt: **bei Dritten
warten, nicht raten.** Die Pfade in
`jusperfect/jurnodes/http_adapter.py::Endpunkte` sind eine plausible Annahme,
keine Zusage – das steht jetzt auch dort.

Zwei Dinge liessen sich aber ohne jedes Raten tun, und sie verkürzen die
eigentliche Anbindung später von Wochen auf Stunden:

**1. Die Pfade sind einstellbar.** `JUSPERFECT_JURNODES_ENDPUNKTE` zeigt auf
eine kleine JSON-Datei; was darin steht, überschreibt die Vorgabe, der Rest
bleibt. Auch der Suchparameter (`suche`) lässt sich ändern – er ist ebenso
geraten. Stimmt ein Pfad nicht, ist das damit **eine Zeile in einer Textdatei
und kein neuer Programmstand** – der Unterschied zwischen einem Anruf und einer
Auslieferung. Ein Tippfehler im Namen fällt auf, statt stillschweigend die
Vorgabe stehenzulassen.

**2. `python -m jusperfect.jurnodestest`** (oder `JURNODES-PRUEFEN.bat`) ruft
jeden Pfad einmal auf und schreibt hin, was geantwortet hat und **wie die Felder
heissen**. Ob jur|nodes ein Aktenzeichen `aktenzeichen`, `az` oder `fileNumber`
nennt, entscheidet über die ganze Zuordnung in `akte_aus_json` – und steht in
keiner Vermutung, sondern nur in einer echten Antwort.

Damit wird aus „wir brauchen erst die Dokumentation" ein Satz an die Kanzlei:
*Starten Sie das und schicken Sie mir die Ausgabe.*

Zwei Zusagen sind fest eingebaut und durch Prüfungen gehalten:

- **Es liest nur.** Kein POST, kein PUT, kein DELETE. Der einzige schreibende
  Pfad der Schnittstelle – der Vermerk – wird nicht angefasst und erscheint nur
  als Zeile in der Aufstellung.
- **Kein Akteninhalt in der Ausgabe.** Feldnamen, Anzahl und Datentyp, niemals
  Werte. Die Datei `jurnodestest.txt` ist deshalb weitergebbar – an die
  Entwicklung und, wenn es hilft, an den Hersteller.

Nachgestellt geprüft: ein Server mit **anderen** Pfaden und **englischen**
Feldnamen. Mit der Vorgabe antwortete nichts (404, mit der richtigen
Erklärung); mit drei Zeilen in der JSON-Datei kamen `fileNumber`, `title`,
`area`, `owner`, `state` zum Vorschein – ohne eine Zeile Programmänderung.

**Was weiterhin fehlt und nur der Hersteller liefern kann:** die OpenAPI- oder
Swagger-Datei des Kanzleiservers, eine Basis-Adresse und ein dafür beschränkter
Testschlüssel. Bis dahin bleibt der WebDAV-Adapter der Weg zu echten Akten.

### Der Laufwerksweg ist der gewählte Weg

Aus der Kanzlei, 22.09.2026: *„Die Einbindung von jurnodes erfolgt entweder
über API oder durch Einbindung durch das Laufwerk, da es sich um einen WEB-DAV
Server handelt. Wir wollten den letzten Schritt vornehmen."*

Damit ist entschieden: **`webdav_adapter.py` ist der Weg, nicht
`http_adapter.py`.** Die REST-Schnittstelle bleibt vorbereitet und liegt still –
die einstellbaren Pfade und `jurnodestest.py` warten auf die Dokumentation des
Herstellers und werden für den Laufwerksweg nicht gebraucht.

Drei Dinge sind dafür dazugekommen:

**Die Laufwerksprobe** (`ordnerpruefung.py`, `ORDNER-PRUEFEN.bat`) ist von einer
Archiv-Kennungsprüfung zu einer vollständigen Probe ausgebaut. Sie prüft den
**Aufbau** des Baums – das war die Lücke: Die alte Fassung zählte Akten und
meldete bei null Akten, es sei keine archivierte darunter, während in Wahrheit
der ganze Baum anders gebaut war und niemand es erfuhr. Jetzt sagt sie, welche
Ebene fehlt und was sie stattdessen gefunden hat. Dazu: Dateitypen mit dem
Anteil dessen, was **nicht** durchgeht (`.msg`, `.eml`), die Textmenge je Akte
als Kostengrundlage, und eine Schreibprobe – sonst fiele ein fehlendes
Schreibrecht erst beim ersten freigegebenen Vermerk auf.

**`START-KANZLEI.bat`** ist der Starter für echte Akten. Er setzt die vier
Einstellungen, die zugleich stimmen müssen, und lässt der Kanzlei genau zwei
Zeilen: den Aktenordner und die Guardrail-Kennung. Fehlt eine, bricht er mit
einem ganzen Satz ab, bevor irgendetwas läuft – sonst bekäme der Bearbeiter
eine Python-Meldung zu sehen, die richtig und unbrauchbar wäre.

**Das Aktengedächtnis liegt beim Laufwerksweg in der Akte** (`gedaechtnis=akte`),
nicht auf dem Rechner. Kein zweiter Aufbewahrungsort; Sicherung und Löschung der
Akte erfassen es mit. `lokal` ist mit echten Akten ohnehin unzulässig.

**Was der Kanzlei noch bleibt:** das Schutzgeländer, die Laufwerksprobe, der
Modell-Testlauf – und DSFA, Datenschutzhinweise, Mandatsbedingungen. Die ersten
drei sagt ihr das Programm; das vierte nicht.

---

## Fortsetzung am 23./24.09.2026: der erste Echtbetrieb

Dieser Abschnitt ersetzt alle vorangehenden als **jüngster Informationsstand**.
Er ist der längste, weil an diesen beiden Tagen mehr entschieden wurde als in
den zwei Wochen davor: **jusperfect arbeitet seit dem 23.09.2026 mit den
echten Akten der Kanzlei.**

995 Prüfungen grün (`.venv/bin/python -m pytest -q`). Zweig `2.0`.

### Die verbindlichen Regeln gelten unverändert

Die zehn Regeln des Abschnitts vom 11.09.2026 und die vier geschützten
Dateien (`ANLEITUNG.md`, `infra/IAM.md`, `infra/iam-nur-claude.json`,
`SICHERHEIT.md`) gelten weiter. Keine davon wurde an diesen Tagen angefasst.

**Neu dazugekommen ist eine fünfte Datei, die nicht geschützt ist, aber
denselben Rang hat:** `DSFA-ANGABEN.md`. Dort werden die technischen Werte
gesammelt, die in die DSFA gehören — jeder mit Datum und Fundstelle. Sie
entstand, weil ein Wert, den man beim Einrichten sieht und nicht aufschreibt,
später nur noch zu erraten ist.

### Was jetzt läuft

**Der Weg zu jur|nodes ist die REST-Schnittstelle**, nicht mehr das Laufwerk.

Am 23.09.2026 hat die Kanzlei die OpenAPI-Beschreibung ihres eigenen Servers
geliefert (jur|nodes API 1.0.1, 85 Endpunkte) und die Schnittstelle
freischalten lassen. Damit fiel die Regel weg, unter der dieser Teil seit
Wochen stillstand: *bei Dritten warten, nicht raten.*

| | |
|---|---|
| Aktensuche, Akte laden | läuft |
| Dokumente lesen | läuft |
| Beteiligte, Fristen | läuft |
| Aktengedächtnis | gebaut, **noch nicht bestätigt** (siehe unten) |
| Vermerk zurückschreiben | gebaut, Recht noch nicht erteilt |

**Der Laufwerksweg bleibt als Rückfallebene** und ist unverändert fertig. Er
hat aber zwei Nachteile, die die Schnittstelle nicht hat: kein Kurzrubrum
(im Ordnernamen steht nur das Aktenzeichen) und kein Aktenstatus. Dazu fehlt
auf `J:\Akten` das Schreibrecht (`PermissionError`, gemessen am 23.09.2026).

### Die vier Dinge, die anders waren als die Beschreibung sagte

Jedes einzelne hätte den ersten Versuch scheitern lassen, und jedes mit einer
Meldung, die nach etwas anderem aussieht. Wer hier weiterarbeitet, sollte sie
kennen, bevor er eine fünfte vermutet:

1. **Die Anmeldung geht über zwei Kopfzeilen**, `X-Auth-User` und
   `X-Auth-Key` — nicht über ein Bearer-Token.
2. **Die Kennung einer Akte ist nicht ihr Aktenzeichen.** `identifier` ist der
   Schlüssel, `recordSign` das Aktenzeichen. Wer das eine für das andere
   einsetzt, bekommt 404 und hält einen richtigen Pfad für falsch.
3. **Die Dokumente hängen am Dateiordner**, nicht an der Akte: Die Akte nennt
   eine `fileFolderId`, deren Inhalt getrennt abzufragen ist.
4. **Die Seitenzählung beginnt nicht einheitlich** — und der Server hält sich
   nicht an seine eigene Beschreibung. Sie sagt `page=0` für `/record/search`;
   mit `page=0` kam nichts zurück, ohne Seitenangabe alles. **Die erste
   Anfrage geht deshalb ohne `page` hinaus**, ab der zweiten Seite wird
   gezählt.

**Dazu der Platzhalter:** Eine Suche ohne Kriterium weist der Server ab. Der
Hersteller schreibt zu `sign` und `shortRubrum` „%-Zeichen für Suchbefehl
verwenden"; ein blosses `%` ist die Frage nach allem. Und ein Begriff **ohne**
Platzhalter trifft nur genau — wer „Testmann" sucht, meint „Testmann ./. Musterhaft".
Beides in `_platzhalter`.

### Die Vorgabe des Herstellers, die den Bauplan bestimmt

> Maximal 100 Anfragen pro Sekunde, und **pro IP-Adresse nur ein Request
> zeitgleich**.

Das Einlesen einer Akte mit fünfzig Dokumenten sind fünfzig Anfragen. Ohne
Sperre fiele die Anbindung nicht beim Ausprobieren auseinander, sondern im
Betrieb. `HttpJurNodesAdapter._nacheinander` ist deshalb keine Vorsichtsmassnahme,
sondern die Bedingung; eine Prüfung schickt vier Fäden gleichzeitig durch den
Adapter und hält fest, dass nie zwei Anfragen zugleich laufen.

### Was offen ist: der Ablegepfad des Aktengedächtnisses

**Stand 24.09.2026, ungelöst.** `POST /file-system/add-file` antwortet mit
**405** — obwohl die Beschreibung des Herstellers genau diesen Aufruf führt.

Ausgeschlossen ist bisher:

- **Ein fehlendes Recht.** Die Kanzlei hat „Datei bearbeiten" nachträglich
  erteilt; es blieb bei 405. Die Rechteverwaltung hat einen Speichern-Knopf,
  die Rechte liegen also beim Server und nicht im Schlüssel — ein neuer Token
  brächte nichts.

Der nächste Schritt ist gebaut und wartet nur auf einen Lauf in der Kanzlei:
**Die Meldung wertet jetzt die Kopfzeile `Allow` aus**, die ein Server einer
405 beilegen muss, und `JURNODES-PRUEFEN.bat` fragt beide schreibenden Pfade
mit OPTIONS ab. OPTIONS schreibt nichts — es ist die einzige Frage, die man
einem Schreibpfad stellen darf, ohne die Zusage des Programms zu brechen.

Steht dort „PUT", ist es eine Zeile im Adapter. Steht dort nichts, ist es der
Pfad, und dafür liegt `jurnodes-endpunkte-beispiel.json` bereit.

### Die Zahl, die alles entschieden hat

Am 23.09.2026, erste echte Akte über die Schnittstelle:

| | |
|---|---|
| 42 Dokumente, 160.000 Zeichen | |
| **Erste Frage** | **0,23 €** |
| Jede weitere in derselben Sitzung | 0,04 € |

**Eine frühere Schätzung war um den Faktor zweihundert zu hoch.** Die
Laufwerksprobe meldete „rund 18 MB je Akte" und verglich das mit dem
Textpreis; daraus liessen sich über fünfzig Euro je Akte ausrechnen. Der
Unterschied ist der Bildanteil — ein eingescanntes PDF ist fast ganz Bild.

**Merksatz:** Eine Zahl, die zur falschen Entscheidung führt, ist schlimmer
als keine. Die Kanzlei hätte das Vorhaben nach der falschen weggelegt.

### Der Fehler, der sich durch diese beiden Tage zieht

Er hat immer dieselbe Form, und er ist an einem Tag **fünfmal** aufgetreten:

> **Eine Probe, die anders fragt als der Betrieb, prüft etwas anderes als den
> Betrieb.**

- Die Laufwerksprobe prüfte das Schreibrecht an der **Wurzel**; geschrieben
  wird in der **Akte**.
- `JURNODES-PRUEFEN.bat` fragte mit einem Aktenzeichen; die Aktenliste fragt
  **ohne** — und genau das ging nicht.
- Die Probe fragte **ohne** Seitenangabe; der Betrieb mit `page=0` — und
  genau das ging nicht.
- Der Prüfserver in `tests/test_jurnodes_http.py` verstand den Platzhalter
  nicht, den der echte Server verlangt.
- Die Modellprobe rief **ohne** Guardrail auf; der Betrieb mit — und deshalb
  meldete sie „Antwortet", während nichts ging.

Wer hier weiterarbeitet: **Wenn eine Probe grün ist und der Betrieb rot, ist
die Probe falsch — nicht der Betrieb.** In vier von fünf Fällen hat die Suche
an der falschen Stelle begonnen, weil dieser Satz nicht dastand.

### Die zweite wiederkehrende Form: der lautlose Verlust

Ebenfalls mehrfach an einem Tag, und für eine Kanzlei die gefährlichere:

- Ein **zweimal vergebenes Aktenzeichen** — der Adapter führt seinen Index
  darunter, das erste Vorkommen gewinnt, die zweite Akte verschwindet.
- **Nur die erste Seite gelesen** — bei 120 Dokumenten fehlten 20.
- Das schwache Modell **liess beim Einlesen die Urkunden weg** (17.09.2026).

Jedes Mal gilt: **Was nicht da ist, fällt nicht auf.** Alle drei sind
inzwischen benannt oder behoben; das Muster bleibt.

### Was die Kanzlei an diesen Tagen eingerichtet hat

| | |
|---|---|
| **Schutzgeländer** | `jusperfect-kanzlei`, Kennung `jeico9orinss`, Stufe Standard, `eu.guardrail.v1:0`. Inhaltsfilter aus, Prompt-Angriffe an. Alle fünf Rechtsgebietsproben durchgelassen. |
| **`bedrock:ApplyGuardrail`** | musste auf **zwei** Ressourcen erteilt werden: `guardrail/*` **und** `guardrail-profile/*`. Die zweite ist die Folge der regionsübergreifenden Verarbeitung. `infra/iam-nur-claude.json` führt beide nicht — **die Datei ist geschützt.** |
| **jur\|nodes-API** | Benutzer `user_2`, ein Schlüssel. Bereiche: Akte, Akten, Dateisystem, Beziehungen, To-Do. |
| **Nutzerliste** | `nutzer-kanzlei.json`: zwei Anwälte, sechs Mitarbeiter, ein Gastzugang — alle mit Zugriff auf alle Akten. |

### Was der Kanzlei noch bleibt

1. **Der Ablegepfad** (siehe oben) — ein Lauf mit `JURNODES-PRUEFEN.bat`.
2. **`write` auf Akte** im Schlüssel, damit der freigegebene Vermerk
   zurückgeschrieben werden kann.
3. **DSFA, Datenschutzhinweise, Mandatsbedingungen.** Die technischen Angaben
   stehen gesammelt in `DSFA-ANGABEN.md`, einschliesslich dessen, was **nicht**
   gesichert ist — das ist der Teil, den eine Unterlage gern weglässt.
4. **Die Website**, die die Kanzlei sich gewünscht hat: erklärt das Programm
   und hilft bei Einrichtung und Störungen. Steht in `MORGEN.md`.
