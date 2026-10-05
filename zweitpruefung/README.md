# Die Zweitprüfung vom 05.10.2026

Die Kanzlei hat das Projekt von einer zweiten KI prüfen lassen. Grundlage war
`PRUEFAUFTRAG.md`; geprüft wurde das Paket
`jusperfect-pruefpaket-05.10.2026.zip` (SHA-256
`53f07feb396413687d9dfabe0cb7daead28410334bfee979c6c4884c92656c1f`).

**Ergebnis: 13 Befunde, davon 10 mit Vorrang.** Die vorhandenen 1625 Prüfungen
bestanden alle — und haben die Lücken trotzdem nicht gezeigt. Das ist der
eigentliche Befund.

**Stand 05.10.2026: alle dreizehn Befunde abgearbeitet.** Elf sind in der Technik
behoben (F01 bis F10, dabei F02 vollständig, sowie F13), zwei in den Unterlagen
berichtigt (F11, F12). **Sechzehn der siebzehn Gegenproben sind rot** — bei ihnen
heißt das: geschlossen.

**Was bleibt, liegt nicht mehr an der Technik:**

* **F11** — Dateinamen und Aktenzeichen gehen über das Material zum Modell. Die
  Unterlagen sagen es jetzt richtig; ob dieser Umfang gewollt ist, entscheidet
  die Kanzlei (`[KANZLEI 18]`). Gegenprobe 9 bleibt deshalb grün.
* **F12** — der Nachweis der AI-services-Opt-out-Richtlinie für dieses Konto
  (`[KANZLEI 19]`).
* **F13** — die Anwendung weist ein globales Profil jetzt ab. Dass die
  Zugriffsrichtlinie am Programmbenutzer hängt, bleibt am Konto nachzuweisen.

| Datei | Was darin steht |
|---|---|
| `PRUEFBERICHT.md` | der Bericht im Wortlaut, unverändert |
| `gegenproben.py` | 17 Gegenproben, unverändert übernommen |
| `pruefstand.json` | Umgebung, Paket-Prüfsumme, Dateienvergleich |

---

## Die Polarität ist umgekehrt — darauf achten

**Bei den Gegenproben bedeutet GRÜN: die Lücke besteht noch.** ROT bedeutet:
sie ist geschlossen.

Deshalb liegen sie **außerhalb von `tests/`** und laufen im täglichen
`pytest -q` nicht mit (`pyproject.toml`, `testpaths`). Aufgerufen werden sie
einzeln:

```
pip install "moto[s3,dynamodb]"
AWS_EC2_METADATA_DISABLED=true AWS_ACCESS_KEY_ID=testing \
AWS_SECRET_ACCESS_KEY=testing AWS_DEFAULT_REGION=eu-central-1 \
  python -m pytest zweitpruefung/gegenproben.py -q
```

**Wird ein Befund behoben, wandert seine Gegenprobe als richtige Prüfung nach
`tests/`** — dort mit der üblichen Polarität: grün heißt, die Zusage hält. Die
Fassung hier bleibt unverändert als Beleg stehen.

---

## Stand der Abarbeitung

| | Befund | Stand |
|---|---|---|
| **F01** | Anbieterfehler gelangen über den Traceback ins Serverprotokoll | ~~offen~~ **behoben 05.10.2026** |
| **F02.1** | „Vergessen" ließ die gespeicherte **Analyse** stehen | ~~offen~~ **behoben 05.10.2026** |
| **F02.2** | ein gemischt belegter Lebenssachverhalt bleibt ganz stehen | ~~offen~~ **behoben 05.10.2026** |
| **F02.3** | eine offene Sitzung behält die Passagen und speichert Antworten darauf neu | ~~offen~~ **behoben 05.10.2026** |
| **F03** | gemeinsamer ETag-Zustand lässt alte S3-Stände Löschungen überschreiben | ~~offen~~ **behoben 05.10.2026** |
| **F04** | Belegpflicht gilt nicht für Entwürfe, Triage-Kernaussage und Analysehinweise | ~~offen~~ **behoben 05.10.2026** |
| **F05** | der Stream zeigt Rohtext vor der Belegprüfung | ~~offen~~ **behoben 05.10.2026** |
| **F06** | der bestätigte Prüfsummenstand umfasst den Betreff nicht | ~~offen~~ **behoben 05.10.2026** |
| **F07** | Entwürfe bleiben nach Aktenrechteentzug lesbar und freigebbar | ~~offen~~ **behoben 05.10.2026** |
| **F08** | eine fremde `/record`-Antwort wird nicht gegen die angefragte Akte geprüft | ~~offen~~ **behoben 05.10.2026** |
| **F09** | Datums- und Sprachvarianten umgehen die Fristensperre | ~~offen~~ **behoben 05.10.2026** |
| **F10** | ein fehlgeschlagener Modellaufruf hinterlässt keinen Nachweis | ~~offen~~ **behoben 05.10.2026** |
| **F11** | Dateinamen und Aktenzeichen gehen über das Material doch zum Modell | **Unterlagen berichtigt**, Technik offen |
| **F12** | die Nicht-Speicherung bei Textract ist nicht nachgewiesen | **Unterlagen berichtigt**, Nachweis offen |
| **F13** | eine EU-Aufrufregion verhindert kein global konfiguriertes Profil | ~~offen~~ **behoben 05.10.2026** |

Die laufende Arbeitsliste steht in `MORGEN.md`.

---

## Was der Bericht außerdem beantwortet hat

**Die Regionen der Inferenzprofile** — mit Quellenangabe aus der
AWS-Dokumentation, abgerufen am 05.10.2026: Aus Frankfurt verteilen
`eu.anthropic.claude-opus-4-6-v1`, `eu.anthropic.claude-haiku-4-5-…` und
`eu.guardrail.v1:0` auf dieselben sechs Regionen — Frankfurt, Irland, Paris,
Mailand, Spanien, Stockholm. **Zürich und London sind nicht darunter.**

Das ist der öffentliche Dokumentationsstand und **kein Nachweis für dieses
Konto**. Dafür ist `GetInferenceProfile` aus Frankfurt je Modellkennung
abzufragen und die Antwort datiert abzulegen. Die Auskunft von AWS bleibt
erbeten.

---

## Wie dieser Bericht zu lesen ist

Er ist **Fremdarbeit und steht unverändert hier**. Zwei Dinge gehören dazu:

1. **Jede Gegenprobe ist am eigenen Bestand nachgelaufen** — alle 17 waren
   grün, also reproduzierbar. Kein Befund ist auf Zuruf übernommen worden.
2. **Wo der Bericht irrt oder zu weit geht, steht das in `MORGEN.md`** und
   nicht hier. Diese Datei bleibt so, wie sie geliefert wurde.
