# Sicherheits- und Berufsgeheimnis-Modell

## Grundsätze

1. **jurnodes bleibt die führende Akte; das optionale Fallgedächtnis ist die zweite
   dauerhafte Arbeitsablage.** Bei Aktivierung hält jusperfect die für die weitere
   Mandatsbearbeitung benötigten Dokumentauszüge, den belegten
   Lebenssachverhalt, eine belegte Chronologie und geprüfte Frage-Antwort-Paare. Die
   Aufbewahrung richtet sich nach dem Aktenstatus in jurnodes, nicht nach der Zeit seit dem letzten Zugriff: offene, laufende,
   ausgesetzte und auf Wiedervorlage liegende Verfahren bleiben erhalten und lösen keine
   regelmäßigen Rückfragen aus. Erst ein bestätigtes Abschlussereignis startet den kontrollierten
   Export- und Löschworkflow. Bei unbekanntem Status oder gestörter Synchronisation wird niemals
   automatisch gelöscht.
   Die technische Arbeitssitzung ist sieben Tage fortsetzbar und kann danach vollständig aus dem
   dauerhaften Fallgedächtnis rehydriert werden.

   **Wo es liegt, entscheidet `JUSPERFECT_GEDAECHTNIS`.** Abgelegt wird in allen Fällen gepackt
   (gzip, verlustfrei); das senkt den Bedarf einer großen Bausache von rund einem Megabyte auf
   etwa ein Viertel bis ein Sechstel. Ältere, ungepackte Ablagen bleiben lesbar und werden beim
   nächsten Speichern gepackt; der ungepackte Vorgänger wird dabei entfernt.

   - `akte` – **in der Akte selbst**, als eine Datei im Aktenordner
     (`00_Aktengedaechtnis.json.gz`, siehe Grundsatz 4). Damit entsteht **kein zweiter
     Aufbewahrungsort**: Das Gedächtnis wird mit der Akte gesichert und mit ihr gelöscht, eine
     verwaiste Kopie kann nicht entstehen, und die Zugriffsrechte der Akte gelten unverändert.
     Die Datei ist nicht zusätzlich verschlüsselt – sie liegt so geschützt wie die Akte, in der
     sie steht. Ein Gedächtnis, das zu einer anderen Akte gehört, wird beim Lesen abgewiesen;
     kopierte Aktenordner sind sonst der übliche Weg zu fremdem Aktentext.
   - `aws` – eigener S3-Bucket im Kanzlei-Konto. Objektnamen enthalten nur eine
     SHA-256-Ableitung der internen Aktenkennung; die Inhalte liegen KMS-verschlüsselt in einem
     nicht öffentlichen Bucket.
   - `lokal` – Datei auf dem Rechner, für Demo und Test. Der Dateiname ist eine SHA-256-Ableitung
     der Aktenkennung, der Inhalt ist **nicht** verschlüsselt; für den Echtbetrieb ist diese
     Ablage nicht gedacht.

   Was im Gedächtnis steht, ist einsehbar, ohne eine Datei öffnen zu müssen: In der Ansicht
   „Aktengedächtnis ergänzen" lässt sich der Abschnitt „Was das Programm sich gemerkt hat"
   aufklappen – Lebenssachverhalt im Wortlaut mitsamt Fundstellen, Chronologie und die
   gespeicherten Frage-Antwort-Paare.

2. **Nur berechtigte Nutzer, nur berechtigte Akten.** Cognito mit MFA stellt die Identität fest,
   der JWT-Authorizer von API Gateway prüft sie vor der Funktion, die Berechtigungstabelle
   entscheidet je Akte. Fremde Sitzungen und Entwürfe sind unsichtbar (404), nicht verboten (403).
3. **Nur erforderliche Inhalte an das Modell.** Für Fragen eine Passagenauswahl, für Analysen
   die Passagen bis zur Zeichenobergrenze. Nie Dateien, nie Dateinamen, nie Nutzer- oder
   Sitzungskennungen, nie die ganze Kanzlei.
4. **Zurückschreiben nur mit Freigabe – mit genau einer Ausnahme.** Eine Freigabe ist an Nutzer,
   Akte, Textprüfsumme und Prozesslauf gebunden (HMAC). Der jur|nodes-Adapter prüft sie vor
   jedem Schreibvorgang. Ohne Freigabeobjekt gibt es keinen Code-Pfad, der einen Vermerk oder
   Entwurf schreibt. Löschen gibt es dafür nicht.

   Die Ausnahme, von der Kanzlei am 15.09.2026 entschieden und im Wortlaut freigegeben:

   > jusperfect schreibt in die Akte genau eine eigene Datei – das Aktengedächtnis. Nur diese
   > eine Datei darf es ohne Einzelfreigabe anlegen, überschreiben und löschen. Auf alle
   > übrigen Inhalte der Akte bleibt der Zugriff lesend; ein Vermerk oder Entwurf entsteht dort
   > weiterhin nur nach ausdrücklicher Freigabe.

   Die Grenze ist nicht nur beschrieben, sondern gebaut: Der Dateiname steht fest
   (`00_Aktengedaechtnis.json.gz`, in `jurnodes/base.py`) und lässt sich vom Aufrufer nicht
   wählen. Über diesen Weg kann deshalb genau diese eine Datei entstehen und keine andere.
   Ein schreibgeschützter Aktenzugang meldet das ausdrücklich, statt still nichts zu tun –
   sonst bekäme der Bearbeiter „gesichert" gemeldet, und es wäre nichts geschehen.
   Geprüft in `tests/test_gedaechtnis_in_akte.py`.

5. **Kein Inhalt im Protokoll.** Das Protokoll akzeptiert nur benannte Kurzfelder; Felder wie
   `text`, `prompt`, `frage` werden abgewiesen, lange Werte ebenfalls. Texte erscheinen als
   Prüfsumme mit Länge. API-Gateway-Zugriffsprotokolle enthalten Weg, Status, Dauer.
   Bedrock-Modellaufrufprotokollierung bleibt aus.

   Das ist nicht nur eine Einstellung, sondern eine geprüfte: Beim Start fragt jusperfect
   einmal bei AWS nach (`modellprotokoll.py`). Schreibt AWS die Modellaufrufe mit, startet
   das Programm nicht – der Prompt ist der Aktentext, und er läge sonst in einer Ablage, die
   die Löschung beim Aktenabschluss nicht erfasst. Lässt sich die Frage nicht beantworten,
   weil das Leserecht fehlt oder AWS nicht erreichbar ist, entscheidet, was auf dem Spiel
   steht: Mit echten Akten ist Ungewissheit ein Nein, mit den erfundenen Testakten ein
   Hinweis. Dem Programmbenutzer ist das Ändern der Einstellung verboten (Deny auf
   `PutModelInvocationLoggingConfiguration`), das Lesen erlaubt. Der Befund steht im
   Verarbeitungsnachweis. Geprüft in `tests/test_modellprotokoll.py`.
6. **Belegpflicht, maschinell geprüft.** Jede Aussage trägt eine Passagenkennung, die auf eine
   tatsächlich mitgeschickte Passage zeigen muss. Sonst: „ohne Beleg“ plus Hinweis.
7. **Dokumente sind Material, keine Anweisungen.** Die Systemanweisung sagt dem Modell, dass
   Aufforderungen in Passagen nicht befolgt werden. In Phase 1 und 2 gibt es keine Aktionen, die
   ein Dokument auslösen könnte; Phase 4 braucht dafür eigene Tests.
8. **Fristen werden erkannt, nie berechnet.** Die Eingangsprüfung nennt Fristauslöser mit Beleg.
   Die Fristenkontrolle bleibt in jur|nodes.
9. **Nur EU-Regionen.** Die Konfiguration verweigert andere Regionen; die Lambda-Rolle trägt eine
   Deny-Regel für alles außerhalb `eu-*`. Neue Modelle laufen in Bedrock oft über
   EU-Inferenzprofile; diese verteilen auf mehrere EU-Regionen und gehören so in DSFA und
   Dokumentation.
10. **Zwei Kostenbremsen.** Der Kostenwächter in der Anwendung sperrt KI-Aufrufe oberhalb des
    Monatsbudgets; AWS Budgets warnt bei 50, 80 und 100 Prozent des tatsächlichen Kontostands.
11. **Ein geprüfter Ausgang, mit Nachweis.** Jeder Weg zum Modell läuft über den `Ausgang`
    (`services/ausgang.py`) – die einzige Stelle, die einen Aufruf nach draußen führt. Er prüft
    die Eingabe (nur Text darf hinaus), bremst am Budget und schreibt für jeden Aufruf einen
    Verarbeitungsnachweis: *dass* und *was* an *welches* Modell ging, als Kurzkennung
    (Prüfsumme·Länge) und Umfang – nie als Aktentext. Damit ist die Rechenschaftsfrage „was ist
    wann ungeschützt in den Bedrock-Bereich gegangen?" beantwortbar, ohne das Mandantengeheimnis
    ein zweites Mal neben der Akte abzulegen (Grundsatz 1). `GET /api/nachweis` zeigt die eigenen
    Vorgänge; ein vollständiger Export für die Datenschutzbeauftragte ist ein eigener, verwalteter
    Weg, keine offene Schnittstelle.
12. **Der Posteingang bereitet vor, der Mensch entscheidet.** Der optionale
    beobachtete Ordner (`services/watchfolder.py`, `services/posteingang.py`) liest
    eingehende Dokumente ein, sobald ihre Größe stabil ist – er verschiebt, benennt
    oder löscht im Ordner nichts, die einzige Spur ist eine inhaltsfreie Statusdatei.
    Ein vorbereiteter Eingang wird von einem Menschen geöffnet und geprüft
    (Eingangsprüfung ist ein Lesen); nichts wird automatisch beantwortet, entworfen
    oder in die Akte geschrieben. Die vorbereiteten Texte leben im Prozess und laufen
    ab wie Sitzungstexte – keine Parallelakte. Der Posteingang ist kanzleiintern und
    der Einordnung in jur|nodes vorgelagert; nur im lokalen Dauerbetrieb sinnvoll.
13. **Eigene Aufträge sind Vorlagen der Kanzlei, kein Mandantengeheimnis.** Der
    optionale Auftragsordner (`services/auftraege.py`) enthält von der Kanzlei
    verfasste `.txt`/`.md`-Dateien – eine Anweisung und, hinter einer Trennlinie,
    Material (Rechtslage, Muster). Sie gehen als Entwurfsvorlage an das Modell und
    werden deshalb bei jeder Verwendung frisch gelesen und begrenzt (Länge,
    Textform). Die Grenze des Ordners ist hart: kein übergebener Name führt aus ihm
    heraus (keine `..`, kein absoluter Pfad, höchstens ein Unterordner) – geprüft in
    `tests/test_auftraege.py`.

    **Ein Vorschlag für einen neuen Auftrag entsteht ohne die Akte.** Schlägt das
    Programm aus einer einmaligen Anweisung einen wiederverwendbaren Auftrag vor
    (`services/auftragsvorschlag.py`), bekommt das Modell weder Passagen noch den
    Entwurf, sondern nur die Art des Schreibens, das Rechtsgebiet und die Anweisung,
    die der Bearbeiter selbst getippt hat. Der Grund liegt in der Bestimmung der
    Datei: Sie geht danach bei *jeder* anderen Akte mit. Ein Vorschlag aus dem
    Entwurf trüge die Tatsachen dieses Mandats – Namen, Beträge, Daten – über die
    Mandatsgrenze, und zwar unbemerkt. Das Modell ist zusätzlich angewiesen, solche
    Angaben wegzulassen; verlassen wird sich darauf nicht. Angelegt wird durch den
    Vorschlag nichts: Der Text wird angezeigt, ist änderbar, und erst ein zweiter,
    ausdrücklicher Schritt des Bearbeiters schreibt die Datei; ein vorhandener
    Auftrag wird dabei nie überschrieben. Geprüft in
    `tests/test_auftragsvorschlag.py`.
14. **Referenzen sind veröffentlichtes Material, getrennt von der Akte.** Der
    optionale Referenzordner (`services/referenzen.py`) enthält Urteile, Gesetze,
    Tarifverträge. Der Bearbeiter zieht einzelne in den Kontext einer Sitzung; sie
    tragen eigene Fundstellen-Kennungen (`R…`), stehen im selben Belegindex wie die
    Aktenpassagen (die Belegpflicht gilt für sie genauso) und sind in Menge gedeckelt
    – was mitgeht, wird mitbezahlt. Die Ordnergrenze ist hart wie bei den Aufträgen;
    bei jeder Frage frisch gelesen. Geprüft in `tests/test_referenzen.py`.
15. **Haufe-Recherche bleibt im Browser des Nutzers.** Der optionale Direktlink zum
    Haufe-Copilot öffnet dessen Seite in einem neuen Tab und nutzt die bestehende
    Login-Sitzung des Nutzers; jusperfect hält oder überträgt **keine
    Haufe-Zugangsdaten** und automatisiert die eingeloggte Sitzung nicht. Die aktuelle
    Frage geht nur mit, wenn der Nutzer sie einfügt (Zwischenablage) oder ein
    ausdrücklich eingestellter Suchparameter sie an die URL hängt – nichts wird
    geraten. Der Rückweg ist der reguläre: einen Fund als Referenz ablegen (Grundsatz 14).
16. **Der Mehrfachdialog kennt nur geprüfte Endfassungen.** Rohtext aus dem Streaming und
    Antworten ohne belastbare Quelle werden nicht in den Verlauf übernommen. Der serverseitige
    Verlauf ist auf `JUSPERFECT_DIALOG_MAX_RUNDEN` begrenzt, läuft mit der Sitzung ab und zieht
    für eine Rückfrage die Originalpassagen früherer Belege erneut heran. Nur bei bewusst
    aktiviertem Aktengedächtnis werden dessen bereits dauerhaft gespeicherte, geprüfte Q&A beim
    Wiederöffnen in den flüchtigen Dialog übernommen.

## Löschkonzept: Der Aktenstatus entscheidet, nicht die Uhr

Eine anwaltliche Akte ruht oft monatelang – ausgesetzte Verfahren, Wiedervorlagen,
Rechtsmittelfristen. Eine Löschung nach Nichtbenutzung wäre deshalb sachfremd und
gefährlich: Sie träfe genau die Verfahren, die am längsten laufen. Maßgeblich ist
allein der Status der Akte in jurnodes.

### Was welcher Status auslöst

| Status in jurnodes | Verhalten in jusperfect | Aufbewahrungsgrund |
|---|---|---|
| laufend, offen | Arbeitsbereich bleibt | `laufende_mandatsbearbeitung` |
| ruhend, ausgesetzt, Wiedervorlage | bleibt; **keine Rückfrage** wegen Zeitablaufs | `laufendes_verfahren_ruhend` |
| abgeschlossen, archiviert | Abschlussworkflow, Übergangsfrist beginnt **jetzt** | `abschlusspruefung_erforderlich` |
| unbekannt, nicht abrufbar | **nicht löschen**, in die Aufsicht | `status_ungeklaert_nicht_loeschen` |

Der Status wird bei jedem Öffnen einer Akte übernommen. Kehrt eine Akte auf „laufend"
zurück, fällt eine vorgemerkte Löschung ersatzlos weg. Aus dem Ordnerexport wird der
Status am Ordnernamen gelesen (Kennung `JUSPERFECT_ARCHIV_KENNUNG`, Vorgabe
`archiviert`); ist keine Kennung eingestellt, bleibt jeder Status ungeklärt und es
wird nichts gelöscht.

### Der Abschluss in seiner Reihenfolge

1. **Berechtigung prüfen.** Wer die Akte nicht sehen darf, schließt sie nicht ab. Ein
   Berechtigungsentzug sperrt den Zugriff sofort, löscht aber von sich aus nichts.
2. **Status frisch aus jurnodes holen.** Ist jurnodes nicht erreichbar oder die Akte
   wieder laufend, endet der Vorgang – ohne Löschung.
3. **Übergangsfrist prüfen.** Sie beginnt ausschließlich mit dem bestätigten Abschluss
   (`JUSPERFECT_GEDAECHTNIS_UEBERGANGSFRIST_TAGE`, Vorgabe 30 Tage), nie durch
   Nichtbenutzung.
4. **Exportieren.** Der belegte Arbeitsstand geht als Vermerk nach jurnodes – vom
   Bearbeiter freigegeben und an genau den angezeigten Text gebunden. Scheitert der
   Export, bleibt alles bestehen.
5. **Erst dann löschen:** Aktengedächtnis, Sitzungen, Dokumentauszüge und Entwürfe
   dieser Akte.
6. **Nachweis schreiben:** Zeitpunkt, Nutzer, jurnodes-Referenz und Stückzahlen –
   keine Akteninhalte.

Die Reihenfolge ist die eigentliche Zusage. Ein zu früh gelöschtes Mandat lässt sich
nicht wiederherstellen, ein zu lange aufbewahrtes schon.

### Berichtigung einzelner Einträge

Ein einzelner Dokumentauszug und eine einzelne Frage-Antwort-Runde lassen sich gezielt
entfernen. Beim Dokument fällt mit, was aus ihm abgeleitet wurde – Antworten, die es
zitieren, der Lebenssachverhalt und die Chronologie –, sonst bliebe ein Rest des
gelöschten Dokuments stehen. Hinzu kommt ein technischer Grund: Die Fundstellenkennungen zählen die
Dokumente durch; fällt eines weg, zeigen alle folgenden Kennungen auf das falsche
Dokument. Der abgeleitete Teil wird deshalb verworfen und neu gebildet.

### Aufsicht über die Ausnahmefälle

Wo nicht gelöscht werden darf, muss jemand hinsehen. Die Übersicht
(`/api/verwaltung/arbeitsbereiche`, nur für Berechtigte mit Zugriff auf alle Akten)
zeigt verwaiste Arbeitsbereiche, Synchronisationsfehler, ungeklärte Status sowie
vorgemerkte und fällige Löschungen. Sie zeigt Zustände und Zahlen, keine Akteninhalte,
und verändert nichts.

### Was das Löschkonzept nicht leistet

- Es ersetzt keine Löschung in jurnodes. jurnodes bleibt die führende Akte mit eigenen
  Aufbewahrungspflichten (§ 50 BRAO).
- Es läuft nicht von selbst. Der Abschluss wird von einem Menschen ausgelöst; die
  Aufsicht macht sichtbar, was ansteht.

## Technische Leitplanken in AWS

- KMS-Schlüssel mit Rotation für DynamoDB, S3, Protokolle und Geheimnis.
- S3-Sitzungsbucket: kein öffentlicher Zugriff, nur TLS, keine Versionierung, sieben Tage
  fortsetzbare Sitzung und ein Tag technische Löschkarenz.
- S3-Gedächtnisbucket: eigener Bucket, kein öffentlicher Zugriff, nur TLS, erzwungenes SSE-KMS
  und keine Versionierung. Keine pauschale Lifecycle-Löschung nach letzter Änderung: Sie könnte
  ein jahrelang laufendes oder ausgesetztes Verfahren irrtümlich treffen. Der Aktenstatus in
  jurnodes steuert einen kontrollierten Export-/Löschworkflow. Zugriff nur für die
  jusperfect-Funktion. Die Freigabe zur Aktivierung ist eine organisatorische Voraussetzung.
- Lambda: maximal 5 parallele Ausführungen, 5 Minuten, Rechte nur auf die eigenen Ressourcen.
- Guardrail wirkt auf Frage und Antwort (`guardContent`), nicht auf den Dokumenttext, der sonst
  je Aufruf so viel kostet wie das Modell. Für deutsche personenbezogene Daten sind die
  Guardrail-Filter begrenzt; sie sind Ergänzung, nicht Grundlage.
- Cognito: nur vom Administrator angelegte Nutzer, MFA verpflichtend, erweiterter Schutz.
  Die Oberfläche meldet sich über die Hosted UI mit dem Autorisierungscode-Verfahren und
  PKCE (S256) an; die Antwort wird gegen den selbst erzeugten Zustandswert geprüft. Das
  Token bleibt im Arbeitsspeicher der Seite und wird in keinen Browserspeicher
  geschrieben – ein erneutes Laden meldet über die Cognito-Sitzung neu an.
- Fail closed im Echtbetrieb: Ohne Guardrail, mit Testakten oder ohne Kanzleischlüssel
  für die Sitzungsdaten startet die Anwendung nicht. Eine halb eingerichtete Umgebung
  soll ausfallen, nicht unbemerkt ungeschützt laufen.
- CloudTrail bleibt an; Zugriffs- und Funktionsprotokolle 30 Tage.

## Rechtliches Paket vor der ersten echten Akte (Phase 0)

- AWS-Auftragsverarbeitungsvertrag (DPA; bereits geprüft) und Dokumentation der Dienstleisterauswahl nach § 43e BRAO
  mit Verschwiegenheitsverpflichtung in Textform.
- Datenschutz-Folgenabschätzung nach Art. 35 DSGVO (Gesundheitsdaten in Unfall- und RSV-Akten,
  neue Technologie).
- Aktualisierte Datenschutzhinweise nach Art. 13 DSGVO, Eintrag im Verarbeitungsverzeichnis, ein Satz
  in den Mandatsbedingungen.
- Vor Aktivierung des Fallgedächtnisses: DSFA, Verarbeitungsverzeichnis, Löschkonzept,
  Datenschutzhinweise und Mandatsbedingungen ausdrücklich um die dauerhafte Fallkopie,
  Speicherdauer, Zweck, Empfängerkreis und Betroffenenrechte ergänzen. **Wo die Fallkopie
  liegt, hängt vom Ablageort ab** (Grundsatz 1) und ist entsprechend zu beschreiben: bei
  `akte` in der Akte selbst und damit bei jurnodes, bei `aws` in einem eigenen Bucket des
  Kanzlei-Kontos in Frankfurt. Für das
  Verarbeitungsverzeichnis gilt: **Zweck** ist die Bearbeitung des konkreten Mandats;
  **Kategorien** sind Dokumentauszüge, ein belegter Lebenssachverhalt, eine belegte
  Chronologie der Akte und geprüfte Frage-Antwort-Runden; **Speicherdauer** ist der Mandats- und Verfahrensstatus in
  jurnodes zuzüglich der Übergangsfrist nach bestätigtem Abschluss (siehe Löschkonzept);
  **Empfänger** sind zwei zu trennende: für die **Aufbewahrung** der Fallkopie der Betreiber
  des gewählten Ablageorts – jurnodes beim Ablegen in der Akte, sonst AWS in Frankfurt –, für
  die **Verarbeitung** in jedem Fall AWS als Auftragsverarbeiter in Frankfurt (Bedrock ohne
  Modelltraining), weil die Passagen zur Analyse dorthin gehen;
  **Betroffenenrechte** werden über die gezielte Berichtigung und Löschung einzelner
  Einträge sowie den Abschlussworkflow bedient.
- KI-Kompetenz der Mitarbeiter nach Art. 4 KI-Verordnung (eine Stunde Schulung, dokumentiert).
- Kanzleiwissen (Phase 2): nur lizenzrechtlich unbedenkliche Inhalte, keine Datenbankinhalte
  von juris, beck-online oder lizenzierte Tabellen.

## Nachweise in den Tests

`tests/test_sicherheitsgrenze.py`: Der Anbieter sieht keine Nutzer-, Sitzungs- oder
Dokumentkennungen und keine Dateinamen; das Protokoll enthält keinen Dokumenttext; ohne
Freigabeobjekt schreibt der Adapter nicht; Fehlertexte enthalten keine Stapelspuren.
`tests/test_freigabe.py`: geänderter Text, fremde Akte, nachgebaute Signatur und fremder
Prozesslauf werden abgewiesen. `tests/test_web_ablauf.py`: Berechtigungen, Unsichtbarkeit
fremder Sitzungen, Budgetsperre, Prüfsummenbindung der Freigabe.
`tests/test_ausgang.py`: Nur Text geht durch den Ausgang; jeder Aufruf erzeugt einen
Verarbeitungsnachweis ohne Inhalte, der Nachweis ist nutzergebunden.
`tests/test_posteingang.py`: Stabilitätsprüfung vor dem Einlesen, Vorbereitung ohne
Inhalte im Überblick, die Originaldatei bleibt unangetastet, Verwerfen löscht sie nicht.
`tests/test_abschluss.py`: die acht Abnahmetests des Löschkonzepts – eine neun Monate
unveränderte laufende Akte wird nicht gelöscht; Aussetzung und Wiedervorlage lösen
nichts aus; erst der Abschluss startet die Frist; die Rückkehr auf „laufend" hebt eine
Vormerkung auf; ein Ausfall von jurnodes und ein gescheiterter Export löschen nichts;
Berechtigungsentzug sperrt, ohne zu löschen; der Abschluss exportiert und löscht dann
vollständig; der Nachweis trägt Zahlen und Zeitpunkte, keine Inhalte.
`tests/test_aufsicht.py`: verwaiste Bereiche, Synchronisationsfehler und ungeklärte
Status werden gemeldet; die Übersicht ist der Verwaltung vorbehalten und enthält keine
Akteninhalte.
`tests/test_config.py`: Die Produktivkonfiguration ist fail closed.
