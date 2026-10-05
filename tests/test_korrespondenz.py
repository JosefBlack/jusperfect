"""Die E-Akte heißt in der Schnittstelle „Korrespondenz".

**Aus der Kanzlei am 05.10.2026, mit der Beschreibung des Herstellers im
Anhang** (jur|nodes API 1.0.2, 85 Pfade, jetzt unter
`schnittstelle/jurnodes-api-1.0.2.json`).

Vier Wochen Suche sind damit beantwortet — und ein Fehler im Programm
aufgedeckt:

| Frage | Antwort |
|---|---|
| Wo liegt die E-Akte? | `POST /correspondence/search` mit `{"recordIdentifier", "page"}` |
| Wo liegen die Vermerke? | darin, als Einträge mit `type: "note"`; die Nummer steht in `referenceNote` |
| Warum sagte `/record/note` immer 405? | Es braucht **zwei** Pflichtparameter: `id` **und** `record`. Probiert wurde stets nur einer |
| Warum führte der Korrespondenzordner fremde Schriftstücke? | Weil es **zwei getrennte Ordnerbäume** gibt. `correspondenceFolderId` gehört in den Korrespondenzbaum; das Programm hat die Nummer an `/file-system/folder/content` geschickt — den anderen Baum |

Der letzte Punkt ist der schwerwiegende: **Es war kein Fehler von jur|nodes.**
Die Schnittstelle hat beantwortet, was gefragt wurde. Gefragt war das Falsche.

Diese Datei prüft, was die Probe daraus macht — gegen eine nachgebaute Antwort,
nicht gegen den Server. Was der Server wirklich sagt, zeigt erst ein Lauf in
der Kanzlei; **bis dahin wird nichts in den Betrieb eingebaut.**
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jusperfect.jurnodes.http_adapter import Endpunkte
from jusperfect.jurnodestest import _korrespondenz_lesen, _vermerke_lesen

BESCHREIBUNG = (Path(__file__).resolve().parent.parent
                / "schnittstelle" / "jurnodes-api-1.0.2.json")
AKTE = "FL6BDPWJ940ALEY4BVP0"


def _eintrag(**felder):
    grund = {"identifier": "K1", "folderId": 2871, "subject": "Betreff",
             "isInbox": 1, "type": "file", "postmark": "2026-07-30T10:00:00.000Z",
             "status": "ok"}
    return grund | felder


class _Antwort:
    def __init__(self, daten, status=200):
        self._daten = daten
        self.status_code = status
        self.text = json.dumps(daten)

    def json(self):
        return self._daten


class _Client:
    """Ein Server, der antwortet wie die Beschreibung es sagt."""

    def __init__(self, eintraege, vermerke=None):
        self.eintraege = eintraege
        self.vermerke = vermerke or {}
        self.posts: list[tuple[str, dict]] = []
        self.gets: list[tuple[str, dict]] = []

    def post(self, pfad, json=None, **rest):
        self.posts.append((pfad, json or {}))
        return _Antwort({"amountTotal": len(self.eintraege), "pagesTotal": 1,
                         "actuallyPage": 1, "elements": self.eintraege})

    def get(self, pfad, params=None, **rest):
        self.gets.append((pfad, params or {}))
        nummer = (params or {}).get("id")
        if nummer in self.vermerke:
            return _Antwort(self.vermerke[nummer])
        return _Antwort({"message": "Bitte Daten angeben"}, status=405)


class TestDieBeschreibungLiegtImBestand:
    def test_sie_ist_da_und_lesbar(self) -> None:
        d = json.loads(BESCHREIBUNG.read_text(encoding="utf-8"))
        assert d["info"]["version"] == "1.0.2"
        assert len(d["paths"]) == 85

    def test_sie_traegt_keine_mandantendaten(self) -> None:
        """Deshalb darf sie in den Bestand."""
        roh = BESCHREIBUNG.read_text(encoding="utf-8")
        import re

        assert not re.search(r"\bD-\d{3}-\d{4}\b", roh)
        assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", roh)
        assert "dortschy" not in roh.lower()

    def test_der_weg_in_die_e_akte_steht_darin(self) -> None:
        d = json.loads(BESCHREIBUNG.read_text(encoding="utf-8"))
        assert "/correspondence/search" in d["paths"]
        arten = d["components"]["schemas"]["CorrespondenceModel"]["properties"]["type"]["enum"]
        assert "note" in arten, "Die Vermerke sind Korrespondenzen."
        assert "file" in arten

    def test_record_note_braucht_zwei_pflichtparameter(self) -> None:
        """Daran ist die Suche vier Wochen lang gescheitert."""
        d = json.loads(BESCHREIBUNG.read_text(encoding="utf-8"))
        pflicht = {p["name"] for p in d["paths"]["/record/note"]["get"]["parameters"]
                   if p.get("required")}
        assert pflicht == {"id", "record"}


class TestDieEndpunkteStimmenMitDerBeschreibung:
    def test_jeder_eingetragene_pfad_steht_in_der_beschreibung(self) -> None:
        """Die Pfade waren bis zum 05.10.2026 eine plausible Annahme. Jetzt
        lassen sie sich gegen die Quelle prüfen."""
        d = json.loads(BESCHREIBUNG.read_text(encoding="utf-8"))
        vorhanden = set(d["paths"])
        e = Endpunkte()
        for name in ("akten_suche", "akte", "ordner_inhalt", "datei_download",
                     "beteiligte", "fristen", "vermerke", "datei_hinzufuegen",
                     "korrespondenz_suche", "korrespondenz", "korrespondenz_ordner"):
            assert getattr(e, name) in vorhanden, (name, getattr(e, name))

    def test_die_beiden_vermerkparameter_sind_eingetragen(self) -> None:
        e = Endpunkte()
        assert e.vermerkparameter == "id"
        assert e.vermerkakteparameter == "record"


class TestDieProbeLiestDieKorrespondenz:
    def test_sie_fragt_mit_akte_und_seite(self, capsys) -> None:
        client = _Client([_eintrag()])
        _korrespondenz_lesen(client, Endpunkte(), AKTE)
        pfad, rumpf = client.posts[0]
        assert pfad == "/correspondence/search"
        assert rumpf == {"recordIdentifier": AKTE, "page": 1}

    def test_sie_nennt_anzahl_arten_und_ordner(self, capsys) -> None:
        client = _Client([_eintrag(), _eintrag(type="note", referenceNote=7, folderId=-1)])
        _korrespondenz_lesen(client, Endpunkte(), AKTE)
        ausgabe = capsys.readouterr().out
        assert "2 Eintrag/Einträge auf Seite 1" in ausgabe
        assert "amountTotal 2" in ausgabe
        assert "Ordnernummern (Korrespondenzbaum)" in ausgabe
        assert "Davon Vermerke (type=note): 1" in ausgabe

    def test_sie_zeigt_keinen_betreff(self, capsys) -> None:
        """Der Betreff trägt den Fall. Die Ausgabe wird weitergegeben."""
        client = _Client([_eintrag(subject="Kündigung Reinhold-Özdemir")])
        _korrespondenz_lesen(client, Endpunkte(), AKTE)
        ausgabe = capsys.readouterr().out
        assert "Reinhold-Özdemir" not in ausgabe
        assert "Kündigung" not in ausgabe
        # Der Feldname darf stehen, der Wert nicht.
        assert "subject" in ausgabe

    def test_sie_nennt_den_zeitraum(self, capsys) -> None:
        client = _Client([_eintrag(postmark="2022-12-15T08:00:00.000Z"),
                          _eintrag(postmark="2026-09-25T08:00:00.000Z")])
        _korrespondenz_lesen(client, Endpunkte(), AKTE)
        ausgabe = capsys.readouterr().out
        assert "2022-12-15" in ausgabe and "2026-09-25" in ausgabe

    def test_eine_leere_akte_wird_gesagt_statt_verschwiegen(self, capsys) -> None:
        client = _Client([])
        _korrespondenz_lesen(client, Endpunkte(), AKTE)
        assert "keine Korrespondenz" in capsys.readouterr().out

    def test_eine_abweisung_bricht_die_probe_nicht_ab(self, capsys) -> None:
        class _Abweisend(_Client):
            def post(self, pfad, json=None, **rest):
                return _Antwort({"message": "Bitte Daten angeben"}, status=405)

        _korrespondenz_lesen(_Abweisend([]), Endpunkte(), AKTE)
        assert "Status 405" in capsys.readouterr().out


class TestDieProbeLiestDieVermerke:
    def test_sie_schickt_beide_pflichtparameter(self) -> None:
        """Der eigentliche Fund. Mit einem allein kam vier Wochen lang 405."""
        client = _Client([], vermerke={7: {"id": 7, "type": "note",
                                           "contentType": "text", "content": "x" * 120}})
        _vermerke_lesen(client, Endpunkte(), AKTE,
                        [_eintrag(type="note", referenceNote=7)])
        pfad, params = client.gets[0]
        assert pfad == "/record/note"
        assert params == {"id": 7, "record": AKTE}

    def test_sie_zeigt_art_und_laenge_aber_nicht_den_inhalt(self, capsys) -> None:
        geheim = "Mandant schildert den Unfallhergang am 27.04."
        client = _Client([], vermerke={7: {"id": 7, "type": "phonecall",
                                           "contentType": "text", "content": geheim,
                                           "subject": "Telefonat"}})
        _vermerke_lesen(client, Endpunkte(), AKTE,
                        [_eintrag(type="note", referenceNote=7)])
        ausgabe = capsys.readouterr().out
        assert "type=phonecall" in ausgabe
        assert f"{len(geheim)} Zeichen Inhalt" in ausgabe
        assert geheim not in ausgabe
        assert "Unfallhergang" not in ausgabe
        assert "Telefonat" not in ausgabe

    def test_sie_ruft_hoechstens_drei_ab(self) -> None:
        """Zum Nachweis, nicht zum Auslesen."""
        client = _Client([], vermerke={n: {"id": n, "type": "note", "content": ""}
                                       for n in range(1, 9)})
        _vermerke_lesen(client, Endpunkte(), AKTE,
                        [_eintrag(type="note", referenceNote=n) for n in range(1, 9)])
        assert len(client.gets) == 3

    def test_ohne_vermerk_sagt_sie_das(self, capsys) -> None:
        _vermerke_lesen(_Client([]), Endpunkte(), AKTE, [])
        assert "ungeprueft" in capsys.readouterr().out

    def test_ein_eintrag_ohne_nummer_wird_gemeldet(self, capsys) -> None:
        client = _Client([])
        _vermerke_lesen(client, Endpunkte(), AKTE, [_eintrag(type="note")])
        assert "ohne referenceNote" in capsys.readouterr().out
        assert not client.gets
