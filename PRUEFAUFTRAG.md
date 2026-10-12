# Prüfauftrag für eine zweite Meinung

**Stand: 12.10.2026.** Diese Datei liegt dem Prüfpaket bei. Sie sagt, was das
Programm ist, worauf zu sehen ist und was bereits bekannt ist — damit die
Prüfung nicht dort anfängt, wo schon jemand war.

> **Es hat schon eine Zweitprüfung gegeben, am 05.10.2026.** Ihr Bericht liegt
> im Paket unter `zweitpruefung/PRUEFBERICHT.md`, mit 13 Befunden und 17
> Gegenproben. **Zwölf davon sind geschlossen**, der dreizehnte (F12) liegt bei
> der Kanzlei. Wer dieselben dreizehn noch einmal findet, hat die Zeit beider
> Seiten verbraucht — der Abschnitt „Was die erste Zweitprüfung schon gefunden
> hat" sagt, was dort steht.

**Zweierlei wird erbeten, und beides zählt:**

1. **Eine Prüfung** des Programms — die Abschnitte „Die Zusagen" und „Worauf
   besonders zu sehen ist".
2. **Antworten auf die offenen Fragen** — der Abschnitt „Offene Fragen". Eine
   ist eine Wissensfrage, die übrigen sind Urteilsfragen. Wer nur eines von
   beidem leisten kann, leistet gern nur das.

---

## Worum es geht

**jusperfect** ist eine KI-Schicht über der Aktenverwaltung **jur|nodes** für
eine Anwaltskanzlei mit zwei Anwälten. Sie liest Dokumente einer Mandatsakte,
legt ausgewählte Passagen einem Sprachmodell (Claude über AWS Bedrock,
Frankfurt) vor und gibt das Ergebnis dem Bearbeiter zur Prüfung.

**Der Gegenstand ist Mandatsgut.** Es gilt die anwaltliche Verschwiegenheit
(§ 43a BRAO, § 203 StGB) und die DSGVO. Das Programm läuft seit dem 23.09.2026
mit den echten Akten der Kanzlei.

| | |
|---|---|
| Programm | 76 Python-Dateien, rund 18.700 Zeilen |
| Prüfungen | 110 Dateien, rund 24.600 Zeilen, **1855 Prüfungen** |
| Oberfläche | eine Seite, `jusperfect/static/` |
| Sprache im Quelltext | Deutsch — Bezeichner, Kommentare, Fehlertexte |
| Zweig | `2.0`, Fassung `2.0.0.dev` |

**Python 3.11 oder 3.12.** Unter 3.13 bricht die Installation ab
(`requires-python = ">=3.11,<3.13"`); das ist Absicht und kein Fehler des
Pakets.

### Was seit dem 05.10.2026 dazugekommen ist

Das ist der Teil, den die erste Zweitprüfung **nicht** gesehen hat — und
damit der Teil, auf den sich eine zweite Meinung heute am ehesten lohnt.

| Seit | Was |
|---|---|
| 08.10. | **Die E-Akte wird gelesen**: Korrespondenzverzeichnis, Vermerke, E-Mails mit Brieftext, **jede Anlage als eigenes Dokument** |
| 08.10. | **Obergrenzen** je Mail (20 MB) und je Akte (100 MB), mit Warnung in der Dokumentzeile statt stiller Auslassung |
| 11.10. | **Die Richtung** eines Schreibens (`isInbox`: Eingang / Ausgang / weder noch) |
| 12.10. | **Ordner** im Dokumentfenster, mit Stapelauswahl je Register |
| 12.10. | **Kein Postfachzugriff** — bisher eine Zusage, jetzt eine Prüfung |

Dazu rund 230 neue Prüfungen.

Ausführen der Prüfungen:

```
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```

---

## Die Zusagen, die das Programm gibt

**Das ist der Maßstab.** Eine Lücke in einer dieser Zusagen ist ein Befund
erster Ordnung; alles andere ist nachrangig.

| Zusage | Wo sie steht |
|---|---|
| **Belegpflicht, fail closed.** Eine Aussage ohne Verweis auf eine mitgeschickte Passage wird **entfernt**, nicht markiert | `jusperfect/services/belegpflicht.py` |
| **Fristensperre.** Fristen werden erkannt, nie berechnet — auch wenn die Akte dazu auffordert | `jusperfect/services/fristen.py` |
| **Ein einziger Ausgang.** Genau eine Stelle im Programm führt zum Modell, und jeder Aufruf hinterlässt einen Nachweis | `jusperfect/services/ausgang.py` |
| **Kein Akteninhalt im Protokoll.** Technisch erzwungen: Inhaltsfelder werden aktiv zurückgewiesen | `jusperfect/security/protokoll.py` |
| **Zurückschreiben nur mit Freigabe**, gebunden an Nutzer, Akte, Textprüfsumme und Vorgang (HMAC) | `jusperfect/security/approval.py` |
| **Fail closed beim Start.** Mitschrift bei AWS an, kein Schutzgeländer, kein Schlüssel, Region außerhalb der EU → das Programm startet nicht | `jusperfect/config.py` |
| **Das Modell sieht keine Kennungen.** Keine Dateinamen, Dokument-, Nutzer- oder Sitzungskennungen | `jusperfect/providers/bedrock.py` |
| **Löschung folgt dem Aktenstatus**, nie dem Zeitablauf. Eine Bearbeitungspause löscht nie etwas | `jusperfect/services/abschluss.py`, `SICHERHEIT.md` |
| **Das Programm schreibt nicht.** Keine Datei, kein Vermerk, kein Ordner in jur\|nodes — und das soll eine Eigenschaft des Schlüssels bleiben, keine Zusage des Programms | `jusperfect/jurnodes/http_adapter.py` |
| **Kein Postfachzugriff.** Weder E-Mail- noch beA-Postfach: dort liegt die Post **aller** Mandate. Alles, was zu einer Akte gehört, kommt aus ihrer E-Akte | `tests/test_kein_postfach.py` *(neu am 12.10.2026)* |
| **Was keinen Inhalt hat, verschwindet nicht**, sondern wird gezählt und angezeigt. Eine unvollständige Liste sieht sonst aus wie eine vollständige | `jusperfect/jurnodes/http_adapter.py`, `jusperfect/static/app.js` |

---

## Worauf besonders zu sehen ist

In dieser Reihenfolge — oben steht, was am meisten schadet, wenn es falsch ist.

1. **Die Sicherheitsgrenze.** Kommt auf irgendeinem Weg Akteninhalt dorthin,
   wo keiner sein darf — in ein Protokoll, in eine Fehlermeldung, in eine
   Befunddatei, in einen Dateinamen? Besonders: Fehlerpfade und Ausnahmen.
2. **Die Belegpflicht.** Lässt sie sich umgehen? Gibt es einen Weg, auf dem
   eine unbelegte Aussage doch bis zum Bearbeiter kommt?
3. **Die Freigabe.** Lässt sich etwas zurückschreiben, das der Bearbeiter so
   nicht gesehen hat? Die Bindung ist ein HMAC über Nutzer, Akte, Text und
   Vorgang.
4. **Das Aktengedächtnis** (`jusperfect/services/gedaechtnis.py`,
   `jusperfect/gedaechtnis/`). Es ist der einzige Ort, an dem dauerhaft
   Akteninhalt außerhalb von jur|nodes liegt. Besonders: das gezielte Entfernen
   einzelner Einträge — fällt wirklich alles mit, was auf einem entfernten
   Dokument beruht?
5. **Der jur|nodes-Adapter** (`jusperfect/jurnodes/http_adapter.py`). Kann eine
   Antwort des Servers dazu führen, dass Inhalt einer **fremden** Akte in die
   Arbeitsakte gelangt? Siehe „Bekannt und offen", Punkt 1.
6. **Die Einstellungen** (`jusperfect/config.py`). Gibt es eine Kombination, in
   der das Programm mit echten Akten startet, obwohl eine Zusage nicht gehalten
   ist?
7. **Die E-Akte — die größte neue Fläche** (`http_adapter.py`, Abschnitt „Die
   E-Akte", und `jusperfect/jurnodes/mail.py`). Eine `.eml` ist fremde Eingabe:
   Sie kommt von außen, trägt Anlagen, MIME-Teile, Kodierungen und Dateinamen,
   die sich jemand ausgesucht hat. Besonders: Kann ein Dateiname aus einer
   Anlage irgendwo hin, wo er nicht hingehört (Pfad, Protokoll, Modell)?
   Greifen die Obergrenzen auch bei einer Mail, die ihre Größe erst beim
   Entpacken zeigt?
8. **Die Prüfungen selbst.** Prüft eine Prüfung den Wortlaut statt der Zusage?
   Davon sind an einem einzigen Tag fünf gefunden worden — eine Prüfung, die
   anders misst als der Betrieb, misst etwas anderes als den Betrieb.

**Und eine Frage, die über einzelne Funde hinausgeht:** *Wo ruht eine Zusage
auf einer Nachschau statt auf einer Prüfung?* Zweimal in der Woche vom 06. bis
12.10.2026 war das Programm richtig und ungeprüft — bei der Seitenzählung der
E-Akte und beim Postfachzugriff. Beide Male hat es ein Dritter bemerkt, nicht
die Entwicklung. **Eine solche Lücke ist hier ein Befund erster Ordnung**, auch
wenn das Verhalten heute stimmt: Was nicht gemessen wird, bleibt nur so lange
richtig, bis jemand daneben etwas ändert.

---

## Was die erste Zweitprüfung schon gefunden hat

Der Bericht vom 05.10.2026 liegt im Paket (`zweitpruefung/PRUEFBERICHT.md`),
daneben die 17 Gegenproben (`zweitpruefung/gegenproben.py`). **Zwölf der
dreizehn Befunde sind geschlossen** — unter anderem die Fehlerprotokollierung
(der ursprüngliche Anbieterfehler stand im Uvicorn-Protokoll), die
unvollständige Löschung, die Beleg- und Fristensperren und die
Freigabeprüfung.

**Offen ist allein F12**, und er liegt nicht am Programm: Die
Datenschutzunterlagen sagen, Textract verarbeite, speichere aber nicht. Das
gilt für die KI-Dienste von AWS nur mit einer wirksamen
**AI-services-Opt-out-Richtlinie** des Kontos. Die ist noch nicht eingerichtet;
bis dahin behauptet die Unterlage mehr, als belegt ist. Die Kanzlei weiß das.

Diese dreizehn bitte **nicht noch einmal melden**. Was willkommen ist: ob eine
der zwölf Behebungen die Lücke nur verschiebt.

---

## Bekannt und offen — nicht als Fund melden, aber gern als Antwort

1. **beA und Post werden nicht gelesen.** Die Ketten stehen in der
   Herstellerbeschreibung vollständig, einschließlich der Dateiart vor dem
   Herunterladen. Gebaut wird erst, wenn es eine Akte mit solchen Einträgen
   gibt — in beiden geprüften kam kein einziger vor. Lieber ungebaut als
   geraten.
2. **Die Rechtsunterlagen** (`DSFA-ENTWURF.md`,
   `DATENSCHUTZHINWEISE-ENTWURF.md`, `VERARBEITUNGSVERZEICHNIS-ENTWURF.md`)
   sind Entwürfe; **41 Stellen** sind als `[KANZLEI n]` offen gelassen und von
   der Kanzlei zu bewerten, nicht von der Entwicklung.
3. **Zugriff je Bearbeiter.** Technisch vorhanden, in der Kanzlei nicht
   eingeschaltet: Alle eingetragenen Nutzer sehen alle Akten. Bewusst so, und
   offen.
4. **Die Opt-out-Richtlinie bei AWS** — F12, siehe oben.
5. **`correspondenceFolderId`** war **nie** ein Fehler des Herstellers. Die
   Nummer gehört in den Ordnerbaum der Korrespondenz und wurde gegen den Baum
   des Dateisystems abgefragt: zwei Nummernkreise, dieselbe Zahl, fremde Akte.
   Der richtige Weg ist aktenbezogen (`POST /correspondence/search` mit
   `recordIdentifier`) und seit dem 08.10.2026 am Server der Kanzlei gemessen.
   **Dazu ist nichts zu melden.**

---

## Offene Fragen, zu denen eine zweite Meinung willkommen ist

**Zur Behandlung der Antworten, vorab.** Was hier zurückkommt, ist eine zweite
Meinung und keine Auskunft aus der Quelle. Für die Fragen 1 und 2 gilt
ausdrücklich: Eine Antwort von Ihnen ersetzt **nicht** die Antwort des
Herstellers bzw. von AWS. Sie wird als Hinweis behandelt, nicht als Beleg —
dieselbe Regel, nach der eine Zusammenfassung aus dem Netz am 01.10.2026 schon
einmal als „ausdrücklich nicht gesichert" in die Unterlage gegangen ist.

**Und: Bitte nicht raten.** „Weiß ich nicht" ist hier eine nützliche Antwort.
Ein erfundener Schnittstellenpfad kostet einen Prüflauf an echten Mandatsakten.

---

### ~~Frage 1 — Wie liest man die E-Akte von jur|nodes?~~ — **beantwortet**

Die Beschreibung des Herstellers (1.0.2) liegt im Paket unter
`schnittstelle/jurnodes-api-1.0.2.json`. Der Weg steht und ist am Server der
Kanzlei gemessen: `POST /correspondence/search` mit `recordIdentifier`,
Vermerke über `GET /record/note?id=…&record=…` (**beide** Pflichtparameter),
Mails über `POST /mail/download` (Dateiart `.eml`, gemessen).

**Eine Teilfrage der alten Fassung ist am 11.10.2026 beantwortet worden**, und
zwar von einer zweiten Meinung: Reicht `POST /correspondence/search` für
*alle* Korrespondenz, oder braucht es zusätzlich den Ordnerbaum? Antwort: Es
reicht — aber **alle Seiten** müssen gelesen werden (`page` beginnt bei 1, die
Antwort führt `pagesTotal`). Das Programm tut das; geprüft war es nur für die
GET-Aufrufe, nicht für die E-Akte. Jetzt auch dafür.

---

### ~~Frage 2 — In welche Regionen verteilt das EU-Inferenzprofil von AWS Bedrock?~~ — **beantwortet, mit Vorbehalt**

Die erste Zweitprüfung hat die AWS-Tabellen ausgewertet: **Zürich
(`eu-central-2`) und London (`eu-west-2`) stehen nicht** in den Zielmengen für
einen Aufruf aus Frankfurt. Wichtig dabei: Das ist keine Eigenschaft des
Namensvorsatzes `eu.`, sondern hängt an der **Quellregion** — deshalb nennen
die Unterlagen jetzt Modell und Quelle ausdrücklich.

**Was hier noch willkommen ist:** eine Gegenlesung dieser Auswertung, mit
Quelle und Datum. Die Angabe stammt aus einer zweiten Meinung, nicht von AWS;
sie steht in den Unterlagen entsprechend gekennzeichnet.

---

### Frage 3 — Die drei neuen Entscheidungen der letzten Woche

Alle drei betreffen die E-Akte und sind in einer Woche entstanden. Eine
Gegenrede ist willkommen.

**3a · Die Obergrenze ist 20 MB je Mail und 100 MB je Akte.** Darüber wird die
Mail **nicht** geladen, bleibt aber mit Betreff, Datum und einer Warnung in der
Dokumentzeile stehen. Grundlage: In zwei geprüften Akten lag genau **eine**
Mail darüber (8,7 MB); die zweite gemessene wog 5 kB. Ist die Grenze an der
richtigen Stelle — und ist „sichtbar fehlend" hier besser als „nachladen auf
Klick"? (`jusperfect/jurnodes/http_adapter.py`, `MAIL_OHNE_INHALT`)

**3b · Bei `isInbox = -1` steht keine Richtung am Schriftstück.** Der
Hersteller sagt: 1 = Eingang, 0 = Ausgang, **-1 = Neutral/Unbekannt**. Jeder
andere Wert wird wie -1 behandelt — also keine Angabe statt einer Vermutung.
Richtig, oder sollte „unbekannt" sichtbar sein statt abwesend?
(`http_adapter.py`, `_richtung`)

**3c · Die E-Akte steht als eigener Ordner neben dem Dateiordner.** Mails,
Anlagen und Vermerke tragen den Ordner „E-Akte" und stehen im Dokumentfenster
hinten, getrennt von den Registern des Dateiordners. Begründung: Es sind zwei
Bäume in jur|nodes, und sie zu vermischen hat am 02.10.2026 fremde
Schriftstücke in eine Akte gebracht. Zu streng getrennt, oder richtig?
(`jusperfect/static/app.js`, `explorerNachOrdnern`)

---

### Frage 4 — Tragen die vier älteren Entwurfsentscheidungen?

Hier geht es nicht um Wissen, sondern um ein Urteil. Vier Entscheidungen, bei
denen eine Gegenrede nützlich wäre:

**3a · Belegpflicht: entfernen statt markieren.** Eine Aussage des Modells ohne
Verweis auf eine mitgeschickte Passage wird aus der Antwort **entfernt**. Die
Alternative wäre, sie zu markieren und stehen zu lassen. Entfernen heißt:
Der Bearbeiter sieht nicht, was das Modell gesagt hätte. Ist das die richtige
Seite des Irrtums? (`jusperfect/services/belegpflicht.py`)

**3b · Beim Entfernen eines Dokuments fällt zu viel.** Wird ein Dokument aus
dem Aktengedächtnis genommen, fallen gespeicherte Antworten und
Zeitstrahleinträge **ganz**, sobald sie es auch nur mitzitieren — auch wenn sie
sich zur Hälfte auf ein anderes Dokument stützen. Begründung: Ein Eintrag aus
zwei Quellen stünde sonst weiter da, obwohl die Hälfte seiner Grundlage fehlt.
Zu streng? (`jusperfect/services/gedaechtnis.py::dokument_vergessen`)

**3c · Die Ausschlussliste prüft den Titel, nicht den Inhalt.** Dokumente, deren
**Titel** eines von neun Wörtern trägt (Rechnung, Kostennote, RSV …), kommen
ohne Haken in die Auswahl — sie sollen nicht ins Aktengedächtnis. Eine
Rechnung, die „Schreiben vom 14.03." heißt, geht durch. Gibt es einen Weg, der
zuverlässiger ist, **ohne** den Inhalt zu deuten? (`jusperfect/static/app.js`,
`nichtVorwaehlenGrund`)

**3d · Veraltet-Erkennung über Dokumentkennungen.** Eine gespeicherte
Aktenanalyse meldet sich als veraltet, wenn die Akte heute Dokumentkennungen
enthält, die sie beim Rechnen nicht enthielt. Geänderte oder ersetzte Dokumente
mit gleicher Kennung erkennt das **nicht**. Reicht das, oder braucht es eine
Prüfsumme je Dokument — mit allem, was daran hängt?
(`jusperfect/services/gedaechtnis.py::analyse_stand`)

---

### Frage 5 — Die Rechtsdokumentation

`DSFA-ENTWURF.md` (Art. 35 DSGVO, 19 Stellen),
`DATENSCHUTZHINWEISE-ENTWURF.md` (Art. 13, 9 Stellen) und
`VERARBEITUNGSVERZEICHNIS-ENTWURF.md` (Art. 30, 13 Stellen) sind
Entwürfe der Entwicklung. **41 Stellen sind als `[KANZLEI n]` offen gelassen**,
weil sie eine rechtliche Bewertung verlangen; sie stehen am Ende jeder Datei in
einer Liste.

**Gefragt ist nicht die Bewertung** — die trifft die Kanzlei. Gefragt ist:

1. **Fehlt ein Risiko?** Acht sind beschrieben (Abschnitt 4 des DSFA-Entwurfs).
2. **Ist eine der Maßnahmen zu optimistisch dargestellt?** Jede nennt ihren
   Nachweis im Programm — stimmt die Zuordnung?
3. **Fehlt eine Angabe, die Art. 30 oder Art. 35 verlangt?**
4. **Ist eine der offenen Stellen in Wahrheit keine** — also etwas, das die
   Entwicklung hätte beantworten können und sich zu bequem gedrückt hat?

Punkt 4 ist ernst gemeint. Eine Unterlage, die eine technische Frage als
Rechtsfrage ausgibt, schiebt Arbeit auf den Falschen.

---

### Frage 6 — Was würden Sie als Nächstes bauen?

Am Programm ist nichts offen, was das Arbeiten mit einer Akte verhindert. Auf
der Liste steht noch **beA und Post** — und das wartet bewusst auf eine Akte,
an der es sich messen lässt.

**Wenn Sie den Bestand gelesen haben: Was fehlt Ihrer Meinung nach am
meisten?** Gern auch etwas, das in der Liste nicht vorkommt. Die Liste steht
in `MORGEN.md`, der Querschnitt in `STAND-08.10.2026.md`.

---

## Vier Dinge, die bewusst so sind

Sie sehen wie Mängel aus und sind keine. Wer sie trotzdem für falsch hält,
soll das sagen — aber bitte mit Begründung, nicht als Routinehinweis.

| Scheint falsch | Ist Absicht |
|---|---|
| Der Quelltext ist auf **Deutsch** | Die Kanzlei liest mit. Fehlertexte, die ein Anwalt versteht, sind hier ein Sicherheitsmerkmal |
| Kommentare sind **lang** und erzählen Vorgeschichte | Jeder nennt einen Fehler, der einmal Geld oder einen Tag gekostet hat. Sie sind das Gedächtnis des Projekts |
| Die **Inhaltsfilter** des Schutzgeländers sind **aus** | Gewalt, Sexuelles, Beleidigung sind in einer Kanzlei der Gegenstand der Arbeit, nicht der Missbrauch |
| Das Programm **verweigert** lieber, als zu schätzen | „Kein belastbarer Beleg" ist eine zulässige Antwort. Eine kürzere Antwort ist besser als eine erfundene |

---

## Was in diesem Paket verändert wurde

**Fünf Angaben sind ersetzt**, weil sie zur Infrastruktur der Kanzlei gehören
und für eine Prüfung des Programms nicht gebraucht werden. Die Ersetzung ist
**durchgängig** — Quelltext, Unterlagen und Prüfungen tragen denselben
Platzhalter, deshalb laufen die Prüfungen auch im Paket grün:

| Ersetzt durch | War |
|---|---|
| `KANZLEI-EIMER` | der Name des S3-Ablageorts |
| `KMS-SCHLUESSEL-KENNUNG` | die Kennung des Verschlüsselungsschlüssels |
| `AWS-KONTONUMMER` | die Nummer des AWS-Kontos (auch in den ARN-Beispielen) |
| `GELAENDER-KENNUNG` | die Kennung des Bedrock-Schutzgeländers |
| `KANZLEI.jur-nodes.net` | die Adresse des jur\|nodes-Servers |

Das Paket vom 05.10.2026 ersetzte nur die ersten beiden. Die drei übrigen sind
am 12.10.2026 dazugekommen — nicht weil sie geheim wären, sondern weil sie für
die Prüfung nichts beitragen und ein Paket, das das Haus verlässt, so wenig
Infrastruktur nennen soll wie möglich.

**Wo eine dieser Angaben für die Prüfung gebraucht würde** — etwa um eine
Regionsliste oder eine Richtlinie nachzuvollziehen —, fragen Sie bitte; die
Kanzlei reicht sie dann einzeln nach.

**Sonst ist nichts verändert.**

**Keine Zugangsdaten im Bestand.** Die vier Zugangswerte (jur|nodes-Adresse,
Benutzer, Token; AWS-Schlüssel) liegen im Windows-Konto des jeweiligen
Rechners, nie im Programmordner. Was wie ein Schlüssel aussieht, ist ein
Prüfwert — `AKIAIOSFODNN7EXAMPLE` stammt aus der Dokumentation von AWS.

**Enthalten sind erfundene Testakten** (`testdaten/`). Sie sind erfunden, auch
wo sie echt klingen.

**Und ein Fund in eigener Sache, am 11.10.2026.** In diesem Bestand stand bis
dahin an siebzehn Stellen ein **echtes Rubrum** der Kanzlei — Aktenzeichen,
Mandant und Gegner einer laufenden Sache, in Beispielen und Prüfdateien, wo
Platzhalter hingehörten. Es sah aus wie ein Platzhalter; die Namen, die man
erfindet, und die, die es gibt, sehen gleich aus. Aufgefallen ist es nur, weil
**eine** Datei schon bereinigt war und die übrigen sechzehn nicht.

120 Stellen sind ersetzt; an ihrer Stelle stehen jetzt `Testmann`,
`Musterhaft`, `Beispiel` und die Aktenzeichen `X-001-2026`, `X-002-2026`,
`X-003-2025` — Nummern, die es nicht geben kann. Die Kanzlei hat bestätigt,
dass die übrigen Namen im Bestand (`Meier`, `Krämer`, `Schulz`,
`Vellinghausen`) erfunden sind.

**Auch die Aktenzeichen sind heraus — seit dem 12.10.2026.** Bis dahin standen
in `MORGEN.md` und in Befundbeschreibungen die echten Nummern der Kanzlei mit
gemessenen Angaben (wie viele Einträge, wie viele Mails, aus wie vielen
Ordnern). Kein Name, kein Betreff — aber eine Aussage über ein bestimmtes
Mandat. Die Kanzlei hat entschieden, dass auch sie nicht in ein Paket
gehören, das das Haus verlässt.

> **Die Regel, in einem Satz: Ein Aktenzeichen in diesem Bestand beginnt mit
> `X`.** Die Kanzlei führt `D` und `T`; ein `X` kann es dort nicht geben.
> `tests/test_keine_echten_akten.py` misst das über jede Datei, die git kennt
> — einschließlich einer Gegenprobe, dass das Muster eine echte Nummer
> wirklich fängt.

Die Zuordnung zwischen erfundener und echter Nummer steht nirgends im Paket.
Das heißt auch: **Ein Befund, der sich auf „X-100-2026" bezieht, ist für uns
eindeutig** — die Nummern sind durchgehend vergeben, nicht pro Datei neu.

> **Daraus eine Bitte, die zur Sache gehört.** Dieses Paket ist Mandatsgut in
> zweiter Reihe. Bitte nicht in ein Werkzeug geben, das Eingaben zum Training
> verwendet oder dauerhaft speichert, und nach der Prüfung löschen. Wenn Ihre
> Arbeitsweise das nicht zulässt, sagen Sie es bitte vorher — das ist keine
> Absage, sondern eine Angabe, die die Kanzlei braucht.

---

## Was eine nützliche Antwort enthält

**Bei einem Fund:**

- **Datei und Zeile.** „Die Fehlerbehandlung ist schwach" hilft nicht.
- **Den Weg dorthin.** Welche Eingabe, welcher Zustand, welche Reihenfolge?
- **Warum es schadet.** Und für wen — Mandant, Kanzlei, Dritter.
- **Eine Einschätzung**, wie sicher Sie sind. Eine Vermutung ist willkommen,
  wenn sie als Vermutung gekennzeichnet ist.

**Bei einer Antwort auf die offenen Fragen:**

- **Woher Sie es wissen.** Dokumentation, eigene Erfahrung, Gedächtnis? Jede
  dieser drei Herkünfte ist brauchbar — aber sie werden verschieden behandelt.
- **Was Sie nicht wissen.** „Zu Frage 1 kenne ich das Produkt nicht" ist eine
  vollständige Antwort auf Frage 1 und erspart einen Prüflauf an echten Akten.
- **Bei Frage 2 die Quelle**, möglichst mit Datum. Eine Regionsliste aus dem
  Gedächtnis geht als ungesicherter Zwischenstand in die Unterlage, nicht als
  Beleg.

Und, ausdrücklich erbeten: **Wo halten Sie eine Entscheidung für falsch, die
hier als Absicht dokumentiert ist?** Die Begründungen stehen in `KONZEPT.md`,
`SICHERHEIT.md` und in den Kommentaren. Sie sind nicht unantastbar.

---

## Zum Nachlesen

| Datei | Inhalt |
|---|---|
| `UEBERGABE.md` | Stand, tragende Entscheidungen, Konventionen — **hier anfangen** |
| `SICHERHEIT.md` | die 16 Grundsätze und das Löschkonzept |
| `KONZEPT.md` | warum das Programm so gebaut ist |
| `MORGEN.md` | die Arbeitsliste mit allen Begründungen |
| `ANLEITUNG.md` | die Bedienung, für den Anwender geschrieben |
| `infra/IAM.md` | die AWS-Zugriffsrichtlinie im Wortlaut |
| `STAND-08.10.2026.md` | der Querschnitt in einem Durchgang — **schneller als `MORGEN.md`** |
| `zweitpruefung/PRUEFBERICHT.md` | die erste Zweitprüfung, 13 Befunde |
| `schnittstelle/ANFRAGE-HERSTELLER.md` | was an jur\|nodes noch offen ist, und was ausdrücklich nicht mehr |
| `schnittstelle/jurnodes-api-1.0.2.json` | die Beschreibung des Herstellers, 94 Aufrufe |

---

## Ein Satz zum Schluss, der ernst gemeint ist

Die drei teuersten Fehler dieses Projekts sahen aus wie Fehler eines Dritten
und waren eigene: ein Status 401, der ein fehlendes Recht zu sein schien und
ein POST ohne Schlüssel war; fremde Schriftstücke in einer Akte, die eine
verwechselte Ordnernummer waren; und eine Aufgabe für die Kanzlei, die aus
einem falsch gelesenen Bildschirmfoto entstand.

> Eine Erklärung, die alle beobachteten Daten erklärt, ist noch keine richtige.

**Wo Sie den Eindruck haben, hier werde eine Erklärung zu früh für wahr
gehalten, sagen Sie es.** Das ist nützlicher als ein weiterer Befund.
