"""Die Passagenauswahl bei großen Akten.

Bei zwei, drei Dokumenten geht ohnehin alles mit; erst ab einigen Dutzend
entscheidet die Auswahl, was das Modell überhaupt zu sehen bekommt. Zwei
Fälle sind dabei gefährlich, weil sie *aussehen* wie ein normales Ergebnis:

* Kein Wort der Frage kommt im Material vor – dann geht ersatzweise der
  Aktenanfang mit.
* Die Akte passt nicht in einen Aufruf – dann bleibt ein Bruchteil übrig,
  und zwar der älteste.

Der erste Fall muss im Ergebnis stehen, nicht nur im Quelltext. Der zweite
liefert seit der Entscheidung der Kanzlei gar kein Ergebnis mehr: Eine Analyse
über die halbe Akte sieht aus wie eine über die ganze – dieselbe Chronologie,
dieselben sauberen Fundstellen. Nur fehlt der Schriftsatz von letzter Woche.
Deshalb wird abgebrochen statt gekürzt.
"""

from __future__ import annotations

import unittest

from jusperfect.domain.models import Dokument, Seite
from jusperfect.services.passagen import budget_anwenden, passagen_bilden, passagen_waehlen

WOERTER = "Vertrag Kuendigung Frist Zeuge Rechnung Mahnung Termin Gutachten Schaden Anspruch".split()


def _akte(dokumente: int, absaetze: int = 6) -> list:
    alle = []
    for nr in range(1, dokumente + 1):
        text = "\n\n".join(" ".join(WOERTER) * 6 for _ in range(absaetze))
        d = Dokument(id=f"D-{nr:03d}", akte_id="A", titel=f"Schriftsatz {nr}", dateiname=f"{nr}.txt")
        alle += passagen_bilden(nr, d, [Seite(nummer=1, text=text)])
    return alle


class AuswahlBeiVielenPassagen(unittest.TestCase):
    def test_kleine_akte_geht_vollstaendig_mit(self):
        p = _akte(2)
        a = passagen_waehlen("Kuendigung", p, max_anzahl=99)
        self.assertEqual(len(a.passagen), len(p))
        self.assertTrue(a.treffer)

    def test_treffer_werden_als_treffer_gemeldet(self):
        a = passagen_waehlen("Wurde die Kuendigung zugestellt?", _akte(50), max_anzahl=14)
        self.assertTrue(a.treffer)
        self.assertEqual(len(a.passagen), 14)

    def test_ohne_treffer_wird_das_ausdruecklich_gemeldet(self):
        """Der gefährliche Fall: Es kommt etwas zurück, aber blind."""
        p = _akte(50)
        a = passagen_waehlen("Schimmelbelastung im Dachgeschoss", p, max_anzahl=14)
        self.assertFalse(a.treffer)
        self.assertEqual(len(a.passagen), 14)
        self.assertEqual(a.durchsucht, len(p))

    def test_leere_frage_gilt_nicht_als_treffer(self):
        a = passagen_waehlen("...", _akte(50), max_anzahl=14)
        self.assertFalse(a.treffer)

    def test_die_reihenfolge_der_akte_bleibt_erhalten(self):
        a = passagen_waehlen("Gutachten Schaden", _akte(50), max_anzahl=14)
        kennungen = [p.kennung for p in a.passagen]
        self.assertEqual(kennungen, sorted(kennungen, key=lambda k: (
            int(k.split("-")[0][1:]), int(k.split("-")[2][1:]))))


class KuerzungWirdBeziffert(unittest.TestCase):
    def test_budget_kuerzt_und_meldet_es(self):
        p = _akte(200)
        auswahl, gekuerzt = budget_anwenden(p, 160_000)
        self.assertTrue(gekuerzt)
        self.assertLess(len(auswahl), len(p))

    def test_die_meldung_nennt_zahlen_und_den_ausweg(self):
        from jusperfect.services.analyse import _zu_gross

        p = _akte(200)
        auswahl, _ = budget_anwenden(p, 160_000)
        text = _zu_gross("Aktenanalyse", auswahl, p, 160_000)
        # Zahlen statt "zu gross": Wer 22 von 200 liest, versteht sofort, dass
        # hier anders vorgegangen werden muss.
        self.assertIn(str(len({q.dokument_id for q in p})), text)
        self.assertIn(auswahl[-1].dokument_titel, text)
        self.assertIn("160.000", text)
        # Und was jetzt zu tun ist.
        self.assertIn("Explorer", text)
        self.assertIn("Frage stellen", text)

    def test_die_meldung_zerhackt_den_fliesstext_nicht(self):
        """Der erste Entwurf machte aus jedem Komma einen Punkt, um Tausender
        zu setzen - auch mitten im Satz."""
        from jusperfect.services.analyse import _zu_gross

        p = _akte(200)
        auswahl, _ = budget_anwenden(p, 160_000)
        text = _zu_gross("Aktenanalyse", auswahl, p, 160_000)
        self.assertIn("Zeichen; in einen Aufruf", text)
        self.assertNotIn("Dokumente. mit", text)


class VerweigerungStattKuerzung(unittest.TestCase):
    """Die Entscheidung der Kanzlei: lieber kein Ergebnis als ein halbes."""

    def _grosse_akte(self, dokumente: int):
        import json
        import tempfile
        from pathlib import Path

        from tests.hilfen import client, dienste, einstellungen

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        ordner = Path(self._tmp.name) / "GR-2026-0002"
        ordner.mkdir()
        absatz = " ".join(WOERTER) * 40
        for nr in range(1, dokumente + 1):
            (ordner / f"{nr:03d}_schriftsatz.txt").write_text(
                "\n\n".join(absatz for _ in range(8)), encoding="utf-8")
        liste = [{"id": f"D-{nr:03d}", "titel": f"Schriftsatz {nr}",
                  "dateiname": f"{nr:03d}_schriftsatz.txt", "datum": "2026-01-01",
                  "kategorie": "Gegner"} for nr in range(1, dokumente + 1)]
        (ordner / "akte.json").write_text(json.dumps({
            "akte": {"id": "GR-2026-0002", "aktenzeichen": "2/26 GR", "bezeichnung": "Sehr grosse Akte",
                     "rechtsgebiet": "Zivilrecht", "sachbearbeiter": "RA Dr. Weber", "status": "offen"},
            "dokumente": liste, "beteiligte": [], "fristen": [],
        }, ensure_ascii=False), encoding="utf-8")
        e = einstellungen(JUSPERFECT_FIXTURE_PFAD=self._tmp.name)
        c = client(dienste(einstellungen=e), "ra-weber")
        sid = c.post("/api/sitzungen", json={"akte_id": "GR-2026-0002"}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": [d["id"] for d in liste]})
        return c, sid

    def test_die_analyse_bricht_ab_statt_zu_kuerzen(self):
        c, sid = self._grosse_akte(60)
        antwort = c.post(f"/api/sitzungen/{sid}/analyse")
        self.assertEqual(antwort.status_code, 422, antwort.text)
        fehler = antwort.json()["fehler"]
        self.assertIn("zu groß", fehler)
        self.assertIn("abgebrochen", fehler)

    def test_kein_serverfehler(self):
        """Die Akte ist in Ordnung - sie passt nur nicht in einen Aufruf."""
        c, sid = self._grosse_akte(60)
        self.assertNotEqual(c.post(f"/api/sitzungen/{sid}/analyse").status_code, 500)

    def test_fragen_gehen_weiter(self):
        """Der Frage-Weg sucht sich die passenden Stellen und ist kaum betroffen.

        Das ist der Ausweg, den die Meldung nennt - er muss also auch offen sein.
        """
        c, sid = self._grosse_akte(60)
        antwort = c.post(f"/api/sitzungen/{sid}/frage", json={"frage": "Wurde gekuendigt?"})
        self.assertEqual(antwort.status_code, 200, antwort.text)

    def test_eine_kleine_akte_wird_nicht_verweigert(self):
        c, sid = self._grosse_akte(2)
        self.assertEqual(c.post(f"/api/sitzungen/{sid}/analyse").status_code, 200)


class ImProgramm(unittest.TestCase):
    def test_frage_ohne_treffer_traegt_den_hinweis(self):
        import tempfile
        from pathlib import Path

        from tests.hilfen import client, dienste, einstellungen

        # Eine Akte mit mehr Passagen als das Fragebudget, damit ausgewählt wird.
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp) / "GR-2026-0001"
            ordner.mkdir()
            for nr in range(1, 21):
                (ordner / f"{nr:02d}_schriftsatz.txt").write_text(
                    "\n\n".join("Vertrag Kuendigung Frist Zeuge Mahnung Termin" for _ in range(4)),
                    encoding="utf-8")
            dokumente = [{"id": f"D-{nr:03d}", "titel": f"Schriftsatz {nr}",
                          "dateiname": f"{nr:02d}_schriftsatz.txt", "datum": "2026-01-01",
                          "kategorie": "Gegner"} for nr in range(1, 21)]
            import json
            (ordner / "akte.json").write_text(json.dumps({
                "akte": {"id": "GR-2026-0001", "aktenzeichen": "1/26 GR", "bezeichnung": "Grosse Akte",
                         "rechtsgebiet": "Zivilrecht", "sachbearbeiter": "RA Dr. Weber", "status": "offen"},
                "dokumente": dokumente, "beteiligte": [], "fristen": [],
            }, ensure_ascii=False), encoding="utf-8")

            e = einstellungen(JUSPERFECT_FIXTURE_PFAD=tmp)
            c = client(dienste(einstellungen=e), "ra-weber")
            sid = c.post("/api/sitzungen", json={"akte_id": "GR-2026-0001"}).json()["sitzung"]["id"]
            c.post(f"/api/sitzungen/{sid}/dokumente",
                   json={"dokument_ids": [d["id"] for d in dokumente]})
            antwort = c.post(f"/api/sitzungen/{sid}/frage",
                             json={"frage": "Schimmelbelastung im Dachgeschoss?"}).json()
            hinweise = " ".join(antwort["hinweise"])
            self.assertIn("Kein Wort der Frage", hinweise)
            self.assertIn("Anfang der Akte", hinweise)


if __name__ == "__main__":
    unittest.main()
