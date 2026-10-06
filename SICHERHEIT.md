# Sicherheits- und Berufsgeheimnis-Modell

> **Berichtigt am 06.10.2026 nach der Zweitprüfung vom 05.10.2026.** Eine
> zweite KI hat dieses Projekt geprüft und dreizehn Befunde erhoben
> (`zweitpruefung/`). Mehrere Zusagen dieser Datei waren **zu weit gefasst** –
> sie galten für den gewollten Weg und nicht für den zweiten. Die betroffenen
> Stellen stehen unten durchgestrichen und berichtigt daneben; gelöscht wird
> nichts, denn eine Zusage, die stillschweigend verschwindet, sah nie falsch
> aus.
>
> **Der eigentliche Befund der Prüfung steht in keiner der dreizehn Zeilen:**
> Alle 1625 damals vorhandenen Prüfungen waren grün. Eine Prüfung, die den
> gewollten Weg misst, misst nicht den Fehlerweg.

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

     **Für die Akte selbst galt das bis zum 05.10.2026 nicht (Befund F08).** Der
     Client fragte eine Akte ab, und die Antwort durfte eine **andere** nennen –
     geprüft wurde nichts. Die Dokumentliste dieser fremden Akte wurde geladen
     und unter der eigenen Aktennummer eingetragen; jede spätere Prüfung sah
     eine in sich stimmige Liste. Die zurückgegebene Kennung muss seitdem die
     angefragte sein, sonst bricht der Vorgang ab, und eine Datei muss in dem
     Ordner liegen, dessen Inhalt gefragt war. Die fremde Aktenkennung geht
     dabei **nicht** in die Fehlermeldung: Sie gehört zu einer anderen Akte.
     **Was diese Prüfung nicht kann:** Ein Server, der eine falsche
     Zugehörigkeit durchweg stimmig ausgibt, lässt sich damit nicht entlarven.
     Sie fängt die Antwort, die sich selbst widerspricht.
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

   **Berichtigt am 06.10.2026 (Befund F07).** Geprüft wurde beim Entwurf allein,
   *wer* ihn angelegt hat. Wem die Akte entzogen worden war, der bekam auf die
   Sitzung richtig 403 – und konnte denselben Entwurf weiter lesen **und
   freigeben**, also in genau diese Akte schreiben. Die Aktenberechtigung wird
   seitdem bei **jedem** Entwurfszugriff neu geprüft, nicht beim Anlegen; ein
   Entzug wirkt damit sofort auch auf den vorbereiteten Schreibweg (403 statt
   404, weil die Akte bekannt ist und nur der Zugriff fehlt). Dass in dieser
   Kanzlei alle alle Akten sehen, ändert daran nichts – dann geht die Prüfung
   eben immer durch.
3. **Nur erforderliche Inhalte an das Modell.** Für Fragen eine Passagenauswahl, für Analysen
   die Passagen bis zur Zeichenobergrenze. Nie Dateien, nie Nutzer- oder
   Sitzungskennungen, nie die ganze Kanzlei.

   ~~Nie Dateinamen.~~ **Das war falsch (Befund F11), berichtigt am
   06.10.2026.** Der Dateiname ging als **Dokumenttitel** in jeder
   Passagenüberschrift mit, das **Aktenzeichen** in der ersten Materialzeile.
   Gegen den echten jur|nodes-Server ist der Titel sogar immer der Dateiname:
   Die Beschreibung des Herstellers (API 1.0.2) kennt für eine Datei kein
   Titelfeld, nur `fileName`.

   Seit dem 05.10.2026 gilt, von der Kanzlei entschieden (`F11-VORSCHLAG.md`,
   `DSFA-ENTWURF.md` `[KANZLEI 18]`):

   | Geht mit | Geht **nicht** mit |
   |---|---|
   | der Text der angehakten Passagen | der Dateiname |
   | die **Art** des Schriftstücks, als Wort aus einer Liste im Programm (`Dokument 2 – Kündigung`) | der Dokumenttitel im Wortlaut |
   | Kurzrubrum, Rechtsgebiet, Beteiligte mit Rolle | das Aktenzeichen – außer beim **Entwurf**, der „Unser Zeichen" trägt |

   Erkennt die Liste nichts, heißt es nur `Dokument 2`: Die Richtung des
   Irrtums stimmt, weniger Auskunft und nie mehr. **Anonym ist die
   Übermittlung dadurch nicht** – im Text der Passagen stehen weiterhin Namen,
   Beträge und Daten. Das ist der Gegenstand der Auswertung und in
   `DSFA-ENTWURF.md`, Abschnitt 3.2, bewertet.
4. **Zurückschreiben nur mit Freigabe – mit genau einer Ausnahme.** Eine Freigabe ist an Nutzer,
   Akte, ~~Textprüfsumme~~ **Freigabevorlage** und Prozesslauf gebunden (HMAC).

   **Berichtigt am 06.10.2026 (Befund F06).** Bestätigt wurde die Prüfsumme des
   **Textes**. Geschrieben werden aber vier Dinge: Akte, Art, Betreff und Text.
   Fenster A lud den Entwurf, Fenster B änderte nur den Betreff, Fenster A gab
   mit der alten Prüfsumme frei – und der neue, dort nie gesehene Betreff ging
   in den Vermerktext **und** in den Titel nach jur|nodes. Die Kryptografie war
   dabei nicht gebrochen; sie signierte nur das, was ihr gegeben wurde, und das
   war zu wenig. Bestätigt wird seitdem eine **Freigabevorlage** über alle vier
   Felder mit eigener Fassungsnummer (`services/entwuerfe.py::freigabevorlage`);
   Prüfung, Statuswechsel und Schreiben stehen unter einem Schloss. Der jur|nodes-Adapter prüft sie vor
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

   **Berichtigt am 06.10.2026 (Befund F01).** Der Satz galt für den **eigenen**
   Protokollkanal und nicht für die anderen. Eine abgelehnte Bedrock-Anfrage
   trägt den Wortlaut von AWS, und darin steht mitunter ein Stück der Anfrage,
   also Aktentext. Der Anbieter behielt die Ausnahme als Ursache, Starlette warf
   sie nach der sauberen Antwort erneut, und Uvicorn schrieb den vollständigen
   Traceback **samt Ursache** ins Serverprotokoll. `access_log=False` schaltet
   diesen Kanal nicht ab, und die Feldsperren kamen auf diesem Weg nie zum
   Einsatz. **Eine saubere HTTP-Antwort beweist kein sauberes Protokoll.**

   Seitdem zwei Riegel (`jusperfect/fehlergrenze.py`): eine eigene ASGI-Grenze,
   aus der keine Ausnahme nach außen tritt, und – an der einen Stelle, durch die
   jeder Protokolleintrag geht – das Abnehmen der Ausnahme. An ihre Stelle
   treten die **Namen** der Kette samt Code-Stelle; ein Wortlaut geht nie mit,
   auch nicht der eigene. Das wirkt für jeden Kanal im Prozess. Geprüft in
   `tests/test_fehlergrenze.py`.
6. **Belegpflicht, maschinell geprüft.** Jede Aussage trägt eine Passagenkennung, die auf eine
   tatsächlich mitgeschickte Passage zeigen muss. ~~Sonst: „ohne Beleg“ plus Hinweis.~~
   **Sonst wird sie entfernt**, und an ihrer Stelle steht eine sichtbare Marke.

   **Berichtigt am 06.10.2026 (Befunde F04 und F05).** Zweierlei war zu weit:

   * **Der Umfang.** Die Prüfung galt für die Antwort auf eine Frage und für
     die strukturierten Listen – nicht für den **Entwurf**, nicht für die
     **Kernaussage** der Eingangsprüfung und nicht für die **Hinweise des
     Modells**. Ein vollständig erfundener Entwurf kam mit HTTP 201 und leerer
     Quellenliste heraus. Heute geht jeder angezeigte Modelltext durch dieselbe
     Prüfung; ein Entwurf ohne einen einzigen tragenden Beleg wird gar nicht
     erst ausgegeben. Was das Programm selbst anfügt, entsteht getrennt davon.
   * **Die Reichweite.** Ein Beleg trug alles seit dem vorigen Beleg – auch
     einen Absatz, der Zeilen vorher stand. Er reicht jetzt bis zur nächsten
     Einheitsgrenze zurück: Leerzeile, Aufzählungspunkt, Überschrift. Die
     Grenze ist bewusst der Absatz und nicht der Satz; ein Satzmaßstab
     zerschnitte fast jede richtige Antwort.

   Dazu: **Im laufenden Text wird nichts Ungeprüftes mehr gezeigt.** Vorher
   strömte der Rohtext und die Prüfung kam am Ende – der Bearbeiter sah also,
   was gleich darauf zurückgehalten wurde. Bis zur ersten abgeschlossenen
   Aussage steht jetzt nur da, *dass* gearbeitet wird. Geprüft in
   `tests/test_ausgabepruefung.py`.
7. **Dokumente sind Material, keine Anweisungen.** Die Systemanweisung sagt dem Modell, dass
   Aufforderungen in Passagen nicht befolgt werden. In Phase 1 und 2 gibt es keine Aktionen, die
   ein Dokument auslösen könnte; Phase 4 braucht dafür eigene Tests.
8. **Fristen werden erkannt, nie berechnet.** Die Eingangsprüfung nennt Fristauslöser mit Beleg.
   Die Fristenkontrolle bleibt in jur|nodes.

   **Der Nachweis ist am 05.10.2026 ein anderer geworden (Befund F09).** Die
   Zusage hing an zwei Wortlisten, und drei Schreibweisen kamen durch:
   „endet am 26.05.**26**" (zweistelliges Jahr), „endet am 26. **Mai**"
   (Monatsname ohne Jahr) und „muss **bis zum** 26.05.2026 eingereicht werden"
   (kein Wort der Fristliste). Die Zusage blieb, der Nachweis wurde ersetzt:
   **Jedes Datum muss sich auf eine Stelle zurückführen lassen, die das
   Programm selbst mitgeschickt hat** – eine Passage, deren Kopfzeile oder den
   Fristenkalender. Findet sich dort nichts, wird es ersetzt, ganz ohne
   Wortliste. Denn woher sollte es sonst kommen. Geprüft in
   `tests/test_fristen.py`.
9. **Nur EU- und EWR-Regionen.** Die Konfiguration verweigert andere Regionen; die
   Zugriffsrichtlinie trägt eine Deny-Regel für alles außerhalb der ~~`eu-*`~~
   **namentlich aufgeführten sechs Regionen**. Neue Modelle laufen in Bedrock oft über
   EU-Inferenzprofile; diese verteilen auf mehrere EU-Regionen und gehören so in DSFA und
   Dokumentation.

   **Zwei Berichtigungen, beide vom 05.10.2026:**

   * ~~`eu-*`~~ **war der falsche Maßstab.** Der Vorsatz ist eine
     Namenskonvention von AWS und keine Aussage über die EU: `eu-central-2`
     liegt in **Zürich**, `eu-west-2` in **London**. Die Richtlinie und die
     Konfiguration nennen die sechs Regionen seitdem beim Namen
     (`config.py::EU_EWR_REGIONEN`, `infra/iam-nur-claude.json`).
   * **Die Aufrufregion sagt nichts über das Inferenzprofil (Befund F13).** Ein
     Profil ist keine Modellkennung, sondern eine Verteilregel: `global.…`
     verteilt weltweit, gleich aus welcher Region es aufgerufen wird. Frankfurt
     plus `global.anthropic.…` kam durch die Einstellungsprüfung. Geprüft wird
     seitdem **jede** der sieben Modelleinstellungen, nicht nur die eine.
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

    **Berichtigt am 06.10.2026 (Befund F10).** Der Nachweis entstand erst
    **nach** einer erfolgreichen Antwort. Warf der Anbieter, nachdem er das
    Material längst empfangen hatte, blieb das Nachweisfenster leer – und
    „keine Zeile" liest sich wie „nichts hinausgegangen". Kosten und
    Übermittlung sind im Fehlerfall eben nicht beide null. Die Zeile entsteht
    seitdem **vor** der Übergabe; der Ausgang wird danach angehängt
    (beantwortet, ohne Antwort, abgebrochen) und beim Lesen mit ihr
    zusammengelegt. Angehängt und nicht überschrieben: Ein Nachweis, den man
    ändern kann, ist ein schwächerer Nachweis. Steht nur die Versuchszeile da,
    heißt das **unbekannt** und nicht **nichts**.
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
zitieren, der Lebenssachverhalt, die Chronologie und die gespeicherte Analyse –, sonst
bliebe ein Rest des gelöschten Dokuments stehen.

~~Hinzu kommt ein technischer Grund: Die Fundstellenkennungen zählen die Dokumente
durch; fällt eines weg, zeigen alle folgenden Kennungen auf das falsche Dokument. Der
abgeleitete Teil wird deshalb verworfen und neu gebildet.~~ **Das stimmt seit den festen
Dokumentnummern nicht mehr** (berichtigt am 06.10.2026): Eine einmal vergebene Nummer
gehört diesem Auszug, nachgerückt wird nicht, und deshalb bleibt der Rest des
Gedächtnisses stehen. Ein Lebenssachverhalt aus fünfzig Dokumenten war früher wegen
eines einzigen dahin.

**Vier Berichtigungen aus der Zweitprüfung, alle vom 05.10.2026 (Befunde F02 und F03):**

* **Die gespeicherte Analyse** fiel durch das Netz und stand nach dem Entfernen
  weiter da. Sie wird jetzt mitbereinigt; bleibt nichts Unberührtes übrig, fällt sie
  ganz – eine Analyse ohne ihre Grundlage sieht genauso vollständig aus wie eine
  vollständige.
* **Eine gemischt belegte Aussage** des Lebenssachverhalts blieb stehen, wenn nur
  einer ihrer beiden Belege wegfiel. Sie fällt jetzt ganz: Dass die verbliebene
  Quelle den Text allein trägt, weiß niemand.
* **Eine bereits geöffnete Sitzung** behielt den Auszug; die nächste Frage antwortete
  darauf, und die Antwort wurde neu gespeichert. Das Dokument verschwindet jetzt aus
  jeder offenen Sitzung, und ein Ergebnis, das beim Löschen noch unterwegs war, wird
  an einer Grabmarke erkannt und abgewiesen. Die Sitzung selbst bleibt offen – sie zu
  schließen wäre eine Strafe für eine Löschung, die der Bearbeiter selbst ausgelöst
  hat.
* **Zwei Vorgänge auf einem Speicher** konnten einander überschreiben: Die erwartete
  Revision lag in einer Tabelle je Objektname, nicht am gelesenen Stand. Der ältere
  Vorgang nahm beim Speichern die **neue** Revision und machte damit eine Löschung
  rückgängig, die er nie gesehen hatte. Die Revision hängt jetzt am gelesenen Stand;
  wer nicht gelesen hat, überschreibt nichts mehr.

**Ein Löschverlangen, das nur gilt, solange niemand ein zweites Fenster offen hat,
wäre keines.** Geprüft in `tests/test_vergessen_vollstaendig.py` und
`tests/test_gedaechtnis_gemeinsam.py`.

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
- **Texterkennung (Amazon Textract), seit dem 02.10.2026 – hier bisher nicht
  genannt, ergänzt am 06.10.2026.** Sie ist eine **zweite** Übermittlung: ein
  Bild je gescannter Seite, erzeugt auf dem Rechner der Kanzlei, an denselben
  Auftragsverarbeiter in derselben Region. Abschalten: `JUSPERFECT_OCR=keine`.

  **Offen, und das gehört hierher (Befund F12 der Zweitprüfung).** Die
  Unterlagen schlossen aus dem Versand der Bildbytes ohne eigenen
  S3-Zwischenspeicher, AWS speichere die Bilder nicht. **Dieser Schluss trägt
  nicht.** Für die KI-Dienste von AWS gilt die Nicht-Speicherung nur mit einer
  wirksamen **AI-services-Opt-out-Richtlinie** des Kontos. Solange sie nicht
  nachgewiesen und datiert abgelegt ist (`DSFA-ENTWURF.md` `[KANZLEI 19]`),
  darf keine Unterlage eine Nicht-Speicherung behaupten – diese auch nicht.

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
Dokumentkennungen, keine Dateinamen und kein Aktenzeichen (außer beim Entwurf); das
Protokoll enthält keinen Dokumenttext; ohne Freigabeobjekt schreibt der Adapter nicht;
Fehlertexte enthalten keine Stapelspuren.
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

**Aus der Zweitprüfung vom 05.10.2026 hinzugekommen** – jede dieser Dateien gehört zu
einem Befund, der vorher von keiner Prüfung gesehen wurde:
`tests/test_fehlergrenze.py` (F01, kein Traceback in irgendein Protokoll),
`tests/test_vergessen_vollstaendig.py` (F02, F03),
`tests/test_ausgabepruefung.py` (F04, F05),
`tests/test_freigabe_umfang.py` (F06, F07),
`tests/test_herkunft_und_nachweis.py` (F08, F10, F13),
`tests/test_fristen.py` (F09),
`tests/test_metadaten_im_material.py` (F11).

Die siebzehn Gegenproben der Zweitprüfung liegen unverändert in
`zweitpruefung/gegenproben.py`. **Dort ist die Polarität umgekehrt: Grün heißt, die
Lücke besteht noch.** Alle siebzehn sind rot.
