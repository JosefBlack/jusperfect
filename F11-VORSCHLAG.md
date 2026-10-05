# Was das Modell über die Akte erfährt, bevor es den ersten Satz liest

**Vorschlag zu Befund F11 der Zweitprüfung · 05.10.2026**

> **Entschieden und gebaut am 05.10.2026.** Die Kanzlei hat Weg B gewählt und
> das Aktenzeichen auf den Entwurf beschränkt. Umgesetzt in
> `services/prompts.py::dokumentbezeichnung` und `material_bauen`, geprüft in
> `tests/test_metadaten_im_material.py`, eingetragen in `DSFA-ENTWURF.md`
> (`[KANZLEI 18]`) und in `VERARBEITUNGSVERZEICHNIS-ENTWURF.md`. Dieser Text
> bleibt als Grundlage der Entscheidung stehen.

Dieser Text ist die Entscheidungsgrundlage für die offene Stelle `[KANZLEI 18]`
in `DSFA-ENTWURF.md`. Er beschreibt, was heute hinausgeht, was davon wirklich
etwas Neues verrät, und was drei Wege kosten würden. **Entschieden wird in der
Kanzlei; die Entwicklung kann nur sagen, was technisch der Fall ist.**

---

## 1. Was der Befund sagt — und was er nicht sagt

Die Zweitprüfung hat festgestellt: Die Zusage „das Modell sieht keine
Dateinamen und keine Aktenzeichen" war **falsch**. Beides geht als Text mit.
Das ist richtig, und die Unterlagen sind am 05.10.2026 berichtigt worden.

**Der Befund sagt nicht, dass die Übermittlung dadurch mehr verrät, als
gewollt war.** Das ist die eigentliche Frage, und sie ist eine andere.

---

## 2. Was heute hinausgeht — gemessen, nicht geschätzt

Gemessen an den vier Testakten (AR, VU, MV, SC), die der Arbeitsweise der
Kanzlei nachgebaut sind:

| Was | Umfang | Woher |
|---|---|---|
| **Dokumenttext** | 20.816 Zeichen | die angehakten Dokumente selbst |
| Passagenkopfzeilen (Kennung, **Dokumenttitel**, Seite) | 1.685 Zeichen | `services/prompts.py` |
| Beteiligte: Namen, Rollen, Organisationen | 990 Zeichen | Aktenstammdaten jur|nodes |
| Fristen aus dem Fristenkalender | 459 Zeichen | jur|nodes |
| Aktenkopf: **Aktenzeichen**, Kurzrubrum, Rechtsgebiet | 398 Zeichen | jur|nodes |

**Alles außer dem Dokumenttext macht 15,4 % aus.** Eine Passagenüberschrift
sieht so aus:

```
### Passage D2-S1-P1 (Dokument: "Kündigungsschreiben", Seite 1)
```

Und die erste Zeile des Materials so:

```
## Akte 115/26 AR: Reinhold-Özdemir ./. Nordwerk Metallbau GmbH – Kündigungsschutz
```

**Wichtig für die Bewertung:** Die Namen der Beteiligten gehen **absichtlich**
hinaus. Sie stehen in den Aktenstammdaten, und das Modell braucht sie: Ohne
sie hat es im September die gegnerische Kanzlei als Rechtsschutzversicherung
geführt. Dasselbe gilt für das Kurzrubrum. Wer über die Dateinamen spricht,
sollte wissen, dass die Namen ohnehin dastehen — und im Dokumenttext erst
recht.

---

## 3. Was der Dokumenttitel wirklich hinzufügt

Ich habe für jedes der 21 Testdokumente geprüft, ob die Wörter seines Titels
schon in seinem Text stehen.

* Bei **8** Dokumenten steht alles schon im Text. Der Titel fügt nichts hinzu.
* Bei **13** Dokumenten enthält der Titel Wörter, die im Text fehlen.

Und das ist der entscheidende Befund: **Was fehlt, ist fast immer die Art des
Schriftstücks, nicht eine Person.**

| Titel | Was im Text fehlt |
|---|---|
| `Kündigungsschreiben` | „Kündigungsschreiben" |
| `Polizeiliche Unfallmitteilung` | „polizeiliche" |
| `Mietvertrag (Scan)` | „Mietvertrag", „Scan" |
| `Schreiben der Gegenseite` | „Schreiben", „Gegenseite" |
| `Gesprächsnotiz Zeuge Salzwedel` | „Zeuge" — **der Name Salzwedel steht im Text** |
| `Mahnung Vermieter` | „Vermieter" — **der Name steht im Text** |

Die Art des Schriftstücks ist für das Modell nützlich: Ein Kündigungsschreiben
wiegt anders als ein Aktenvermerk. Eine Person verrät sie nicht.

**Ein Vorbehalt, der dazugehört.** Gemessen ist das an Testakten. Gegen den
echten jur|nodes-Server gilt zusätzlich: Die Beschreibung des Herstellers
(API 1.0.2) kennt für eine Datei **kein Titelfeld** — nur `fileName`. Der
Titel **ist** dort der Dateiname. Was in der Kanzlei in einen Dateinamen
geschrieben wird, geht also hinaus: auch ein interner Vermerk wie
„Vergleich-Entwurf-NICHT-VERSENDEN.docx" oder ein Name, der im Dokument selbst
nicht vorkommt.

---

## 4. Was eine Ersetzung **nicht** kostet

Das ist die gute Nachricht und war vorher nicht klar:

**Die Belege bleiben, wie sie sind.** Der Dokumenttitel in der rechten Spalte,
in der Belegkarte und über der Passage im Dokumentfenster kommt **nicht** vom
Modell. Er steht in der Passage, die das Programm selbst baut
(`services/quellen.py`, `static/app.js`). Er geht nie durch das Modell und
käme auch nie von dort zurück.

Verloren ginge nur eines: Das Modell kann das Dokument im Fließtext nicht mehr
beim Namen nennen. Statt *„laut Kündigungsschreiben vom 04.05.2026"* stünde da
*„laut Dokument 2 vom 04.05.2026"*. Die Fundstelle daneben führt weiterhin zum
richtigen Schriftstück mit seinem richtigen Titel.

---

## 5. Drei Wege

### Weg A — alles bleibt, der Umfang wird festgeschrieben

Nichts ändern. In der DSFA und im Verarbeitungsverzeichnis steht ausdrücklich,
welche Angaben mitgehen und warum.

* **Dafür:** Kein Qualitätsverlust. Das Modell ordnet Schriftstücke am besten
  ein, wenn es weiß, was sie sind.
* **Dagegen:** Jeder Dateiname geht hinaus, auch der, den niemand bedacht hat.
  Die Kanzlei muss dann auf ihre Dateinamen achten — eine organisatorische
  Maßnahme, die nur hält, solange alle daran denken.
* **Aufwand:** keiner.

### Weg B — nur die Art, nicht der ganze Name *(mein Vorschlag)*

Aus dem Titel geht nur noch das Wort hinaus, das die **Art** des Schriftstücks
nennt. Alles andere wird zu einer Nummer.

```
heute:   ### Passage D2-S1-P1 (Dokument: "Kündigung Reinhold-Özdemir 04.05.pdf", Seite 1)
dann:    ### Passage D2-S1-P1 (Dokument 2 – Kündigung, Seite 1)
```

Erkannt wird die Art an der Liste, die das Programm für den Zeitstrahl bereits
führt (`services/chronologie.py::SCHRIFTSTUECKARTEN`: Klageschrift,
Schriftsatz, Gutachten, Kündigung, Mahnung, Rechnung, Vertrag, Beschluss …).

**Die Richtung des Irrtums stimmt hier**, und darauf kommt es an: Erkennt die
Liste ein Wort nicht, geht es **nicht** hinaus — das Dokument heißt dann nur
„Dokument 2". Eine lückenhafte Liste führt also zu weniger Auskunft, nie zu
mehr. Das ist das Gegenteil der Fristenwortlisten, die am Vormittag des
05.10.2026 genau deshalb aufgegeben wurden.

* **Dafür:** Das Modell behält die Einordnung, die es wirklich nutzt. Kein
  Dateiname geht mehr hinaus, auch kein unbedachter.
* **Dagegen:** Ein Schriftstück mit ungewöhnlicher Bezeichnung verliert seine
  Art, obwohl sie harmlos wäre.
* **Aufwand:** ein halber Tag mit Prüfungen und einem Blick im Browser.

### Weg C — gar kein Titel

```
dann:    ### Passage D2-S1-P1 (Dokument 2, Seite 1)
```

* **Dafür:** Die einfachste Zusage, die sich halten lässt — und die einzige,
  die ohne jede Liste auskommt.
* **Dagegen:** Das Modell weiß nicht mehr, ob es ein Urteil oder eine
  Telefonnotiz liest. Bei der Eingangsprüfung und bei Widersprüchen ist das
  genau die Angabe, auf die es ankommt.
* **Aufwand:** zwei Stunden.

---

## 6. Mein Vorschlag

**Weg B für den Dokumenttitel, und zusätzlich: das Aktenzeichen fällt weg.**

Das Aktenzeichen steht heute in der ersten Materialzeile. **Keine einzige
Regel im Auftragstext nimmt darauf Bezug**, und für Analyse, Eingangsprüfung
und Antwort wird es nicht gebraucht — das Programm weiß selbst, in welcher
Akte es arbeitet.

**Eine Stelle gibt es doch, und sie gehört genannt: der Entwurf.** Ein
Anschreiben an die Gegenseite trägt üblicherweise „Unser Zeichen: 115/26 AR".
Kennt das Modell das Aktenzeichen nicht, lässt es die Zeile weg oder erfindet
sie — und Erfundenes fiele der Belegpflicht zum Opfer, stünde also gar nicht
erst da. Die Zeile müsste dann von Hand ergänzt werden. Zwei Auswege, falls
Ihnen das zu umständlich ist:

* Das Aktenzeichen geht **nur beim Entwurf** mit, sonst nicht. Dann steht es
  in genau dem Aufruf, der es braucht.
* Es bleibt überall. Dann ändert sich an diesem Punkt nichts.

Mein Vorschlag ist der erste Ausweg: Sieben von acht Aufrufarten kommen ohne
aus, und der achte schreibt einen Brief.

**Nicht vorschlagen würde ich**, die Beteiligten oder das Kurzrubrum
herauszunehmen. Das Modell braucht die Rollen, der Dokumenttext enthält
dieselben Namen ohnehin, und ein Material ohne Rollen hat im September zu
einem Fehler geführt, der in der Akte stand.

**Was damit erreicht ist und was nicht:** Es geht dann kein Dateiname und kein
Aktenzeichen mehr hinaus. **Anonym ist die Übermittlung damit nicht** — im
Dokumenttext stehen weiterhin Namen, Beträge und Daten. Das ist der Zweck der
Auswertung und in Abschnitt 3.2 der DSFA so bewertet. Wer mehr will, landet
bei der Pseudonymisierung, und das ist eine eigene Entscheidung.

---

## 7. Was ich von Ihnen brauche

1. **Weg A, B oder C** für den Dokumenttitel.
2. Zum Aktenzeichen: **ganz heraus**, **nur beim Entwurf dabei** (mein
   Vorschlag) oder **bleibt wie bisher**.
3. Danach baue ich es, prüfe es im Browser und trage die Entscheidung in
   `DSFA-ENTWURF.md` (`[KANZLEI 18]`) und in
   `VERARBEITUNGSVERZEICHNIS-ENTWURF.md` ein — mit dem Datum und dem Grund.

`SICHERHEIT.md` trägt dieselbe zu weite Aussage („nie Dateinamen"). Die Datei
ist geschützt und wird nur auf Ihre ausdrückliche Anweisung geändert; sie
gehört nach der Entscheidung mit berichtigt.
