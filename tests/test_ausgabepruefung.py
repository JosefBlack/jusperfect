"""Jeder angezeigte Modelltext geht durch dieselbe Prüfung.

Befunde F04 und F05 der Zweitprüfung vom 05.10.2026, Gegenproben 01, 02, 03
und 14. Die Belegpflicht galt für die Antwort auf eine Frage und für die
strukturierten Listen – und für vier weitere Wege nicht:

1. **Der Entwurf.** Ein vollständig erfundener Entwurf kam mit HTTP 201 und
   leerer Quellenliste heraus. Die leere Liste sagt es dem Programm; gesehen
   hat sie niemand.
2. **Die Kernaussage der Eingangsprüfung** und die **Hinweise des Modells**.
   *„Das Wort ‚Hinweis' macht einen vom Modell gelieferten Sachverhalt nicht
   automatisch zu einem ungefährlichen Systemhinweis."*
3. **Die Reichweite eines Belegs.** Er trug alles seit dem vorigen Beleg –
   auch einen Absatz, der Zeilen vorher stand und nichts mit ihm zu tun hatte.
4. **Der Strom.** Der Rohtext ging hinaus, die Prüfung kam am Ende. Der
   Bearbeiter sah also, was gleich darauf zurückgehalten wurde.

`MARKER` steht für eine Behauptung, die in keiner Passage steht.
"""

from __future__ import annotations

import json
import re
import unittest

from jusperfect.domain.models import Passage
from jusperfect.providers.base import Nutzung, ProviderAntwort
from jusperfect.services.belegpflicht import (
    ENTFERNT, aussage_fail_closed, entwurf_fail_closed, feld_fail_closed,
)
from tests.hilfen import client, dienste

MARKER = "Die Gegenseite hat den Anspruch in voller Höhe anerkannt"
AKTE = "VU-2026-0042"
ECHT = "D1-S1-P1"


def _index(text: str = "Der Vertrag ist unterschrieben.") -> dict[str, Passage]:
    p = Passage(kennung=ECHT, dokument_id="D1", dokument_titel="Test", seite=1, text=text)
    return {p.kennung: p}


class SkriptProvider:
    """Liefert vorgegebene Antworten der Reihe nach."""

    modell_id = "skript"

    def __init__(self, antworten: list[str]) -> None:
        self._antworten = list(antworten)

    def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        text = self._antworten.pop(0) if self._antworten else "Leer"
        return ProviderAntwort(text=text, nutzung=Nutzung(), modell=self.modell_id)

    def fragen_stream(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        yield self.fragen(system, material, aufgabe)


def _sitzung(provider=None, dokumente=("D-001",)):
    d = dienste(provider=provider) if provider else dienste()
    c = client(d, "ra-weber")
    sid = c.post("/api/sitzungen", json={"akte_id": AKTE}).json()["sitzung"]["id"]
    c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": list(dokumente)})
    return d, c, sid


# ── F04, Teil 1: Wie weit ein Beleg zurückreicht ───────────────────────────

class EinBelegTraegtNurSeineEigeneEinheit(unittest.TestCase):
    """Gegenprobe 14, in richtiger Polarität.

    Die Prüfung war **nach** dem letzten Beleg streng und **vor** jedem Beleg
    großzügig. Niemandem fiel das auf, weil alle Prüfungen nach erfundenen
    Belegen suchten und keine nach fehlenden.
    """

    def test_ein_absatz_davor_braucht_einen_eigenen_beleg(self):
        text = MARKER + f".\n\nDer Vertrag ist unterschrieben [Q: {ECHT}]."
        ergebnis = aussage_fail_closed(text, _index())
        self.assertNotIn(MARKER, ergebnis.text)
        self.assertIn(ENTFERNT, ergebnis.text)
        self.assertEqual(ergebnis.verworfen, 1)
        self.assertIn("Der Vertrag ist unterschrieben", ergebnis.text)

    def test_ein_aufzaehlungspunkt_davor_ebenso(self):
        text = f"- {MARKER}.\n- Der Vertrag ist unterschrieben [Q: {ECHT}]."
        ergebnis = aussage_fail_closed(text, _index())
        self.assertNotIn(MARKER, ergebnis.text)
        self.assertEqual(ergebnis.verworfen, 1)

    def test_eine_ueberschrift_davor_ebenso(self):
        text = f"## {MARKER}\nDer Vertrag ist unterschrieben [Q: {ECHT}]."
        ergebnis = aussage_fail_closed(text, _index())
        self.assertNotIn(MARKER, ergebnis.text)

    def test_zwei_saetze_in_einem_absatz_bleiben_zusammen(self):
        """Die Grenze ist bewusst der Absatz und nicht der Satz.

        Die Anweisung lautet, jede Tatsachenaussage mit einem Beleg zu
        schließen; schreibt das Modell zwei Sätze und setzt den Beleg ans
        Ende, ist das die vorgesehene Form. Ein Satzmaßstab zerschnitte fast
        jede richtige Antwort – diese Grenze steht so auch im Modulkopf.
        """
        text = f"Der Vertrag liegt vor. Er ist unterschrieben [Q: {ECHT}]."
        ergebnis = aussage_fail_closed(text, _index())
        self.assertEqual(ergebnis.verworfen, 0)
        self.assertIn("Der Vertrag liegt vor", ergebnis.text)

    def test_die_liste_bleibt_eine_liste(self):
        """Ohne die Trenner klebte sie nach der Prüfung zusammen."""
        text = f"- {MARKER}.\n- Der Vertrag ist unterschrieben [Q: {ECHT}]."
        ergebnis = aussage_fail_closed(text, _index())
        self.assertIn("\n- ", ergebnis.text)


# ── F04, Teil 2: Der Entwurf ───────────────────────────────────────────────

class EinEntwurfOhneBelegGehtNichtHinaus(unittest.TestCase):
    """Gegenprobe 01, in richtiger Polarität."""

    def test_der_erfundene_entwurf_wird_abgelehnt(self):
        p = SkriptProvider([json.dumps({"betreff": "Test", "text": MARKER + "."})])
        d, c, sid = _sitzung(p)
        antwort = c.post(f"/api/sitzungen/{sid}/entwuerfe", json={"art": "mandant"})
        self.assertEqual(antwort.status_code, 422, antwort.text)
        self.assertIn("keinen einzigen belastbaren Beleg", antwort.json()["fehler"])

    def test_ein_entwurf_mit_beleg_kommt_durch(self):
        p = SkriptProvider([json.dumps(
            {"betreff": "Test", "text": f"Der Unfall ereignete sich auf der B 27 [Q: {ECHT}]."})])
        d, c, sid = _sitzung(p)
        antwort = c.post(f"/api/sitzungen/{sid}/entwuerfe", json={"art": "mandant"})
        self.assertEqual(antwort.status_code, 201, antwort.text)
        self.assertTrue(antwort.json()["quellen"])

    def test_anrede_und_gruss_bleiben_stehen(self):
        """Der Maßstab ist hier bewusst ein anderer als bei der Antwort.

        Ein Entwurf ist ein Brief. „Sehr geehrte Damen und Herren" trägt
        keinen Beleg und beansprucht auch keinen; die strenge Prüfung machte
        daraus eine Entfernungsmarke.
        """
        text = ("Sehr geehrte Damen und Herren,\n\n"
                f"der Unfall ereignete sich auf der B 27 [Q: {ECHT}].\n\n"
                "Mit freundlichen Grüßen")
        ergebnis = entwurf_fail_closed(text, _index())
        self.assertIn("Sehr geehrte Damen und Herren", ergebnis.text)
        self.assertIn("Mit freundlichen Grüßen", ergebnis.text)
        self.assertEqual(ergebnis.verworfen, 0)

    def test_ein_nicht_auflösbarer_beleg_nimmt_seine_aussage_mit(self):
        """Vorher blieb sie stehen und bekam die Marke „[Q: ohne Beleg]"."""
        text = f"Der Vertrag liegt vor [Q: {ECHT}]. {MARKER} [Q: D9-S9-P9]."
        ergebnis = entwurf_fail_closed(text, _index())
        self.assertNotIn(MARKER, ergebnis.text)
        self.assertNotIn("ohne Beleg", ergebnis.text)
        self.assertEqual(ergebnis.verworfen, 1)
        self.assertEqual([q.kennung for q in ergebnis.quellen], [ECHT])


# ── F04, Teil 3: Kernaussage, Schritte, Hinweise ───────────────────────────

class DieEingangspruefungPruefIhreEigenenFelder(unittest.TestCase):
    """Gegenprobe 02, erste Hälfte."""

    def _triage(self, roh: dict):
        d, c, sid = _sitzung(SkriptProvider([json.dumps(roh)]))
        antwort = c.post(f"/api/sitzungen/{sid}/triage", json={"dokument_id": "D-001"})
        self.assertEqual(antwort.status_code, 200, antwort.text)
        return antwort.json()

    def test_eine_unbelegte_kernaussage_wird_zurueckgehalten(self):
        ergebnis = self._triage({"kernaussage": MARKER + ".", "empfohlene_schritte": []})
        self.assertNotIn(MARKER, ergebnis["kernaussage"])
        self.assertIn("keine belegte Kernaussage", ergebnis["kernaussage"])
        self.assertTrue(any("Kernaussage" in h for h in ergebnis["hinweise"]))

    def test_eine_belegte_kernaussage_bleibt(self):
        ergebnis = self._triage(
            {"kernaussage": f"Der Unfall ereignete sich auf der B 27 [Q: {ECHT}].",
             "empfohlene_schritte": []})
        self.assertIn("B 27", ergebnis["kernaussage"])

    def test_ein_schritt_mit_unauflösbarem_beleg_faellt(self):
        ergebnis = self._triage({"kernaussage": f"Sachstand [Q: {ECHT}].",
                                 "empfohlene_schritte": [f"{MARKER} [Q: D9-S9-P9]",
                                                         "Mandantin anrufen"]})
        self.assertEqual(ergebnis["empfohlene_schritte"], ["Mandantin anrufen"])

    def test_ein_schritt_ohne_beleg_bleibt_und_warum(self):
        """Ein Schritt ist ein Vorschlag, keine Aussage über die Akte.

        Einen Beleg dafür zu verlangen hieße, jeden Vorschlag zu streichen.
        Dass ein Schritt ganz ohne Beleg eine Tatsache einschmuggeln kann,
        bleibt – deshalb sagt der Auftragstext jetzt ausdrücklich, dass
        Sachverhaltsangaben in die Kernaussage gehören.
        """
        from jusperfect.services import prompts

        ergebnis = self._triage({"kernaussage": f"Sachstand [Q: {ECHT}].",
                                 "empfohlene_schritte": ["Klage prüfen"]})
        self.assertEqual(ergebnis["empfohlene_schritte"], ["Klage prüfen"])
        self.assertIn("keine Sachverhaltsangaben", prompts.aufgabe_triage())


class DieHinweiseDesModellsSindKeineSystemmeldungen(unittest.TestCase):
    """Gegenprobe 02, zweite Hälfte."""

    def test_ein_unbelegter_modellhinweis_faellt(self):
        d, c, sid = _sitzung(SkriptProvider([json.dumps({"hinweise": [MARKER + "."]})]))
        ergebnis = c.post(f"/api/sitzungen/{sid}/analyse").json()
        self.assertNotIn(MARKER, json.dumps(ergebnis, ensure_ascii=False))
        self.assertTrue(any("Hinweis(e) des Modells" in h for h in ergebnis["hinweise"]))

    def test_ein_belegter_modellhinweis_bleibt(self):
        d, c, sid = _sitzung(SkriptProvider([json.dumps(
            {"hinweise": [f"Das Zugangsdatum ist im Scan unleserlich [Q: {ECHT}]."]})]))
        ergebnis = c.post(f"/api/sitzungen/{sid}/analyse").json()
        self.assertTrue(any("unleserlich" in h for h in ergebnis["hinweise"]))

    def test_die_eigenen_hinweise_gehen_nicht_durch_die_pruefung(self):
        """Sonst löschte die Belegpflicht die Meldungen des Programms über
        sich selbst – und am lautesten die über zurückgehaltene Aussagen."""
        d, c, sid = _sitzung(SkriptProvider([json.dumps({"hinweise": [MARKER + "."]})]))
        ergebnis = c.post(f"/api/sitzungen/{sid}/analyse").json()
        eigene = [h for h in ergebnis["hinweise"] if "Hinweis(e) des Modells" in h]
        self.assertEqual(len(eigene), 1)

    def test_ein_kurzes_feld_faellt_ganz_statt_eine_marke_zu_lassen(self):
        self.assertIsNone(feld_fail_closed(MARKER + ".", _index()))
        self.assertIsNotNone(feld_fail_closed(f"Steht da [Q: {ECHT}].", _index()))


# ── F05: Der Strom ─────────────────────────────────────────────────────────

class _StueckweiseProvider:
    """Gibt den Text wortweise heraus – wie ein echter Anbieter."""

    modell_id = "skript"

    def __init__(self, text: str) -> None:
        self._text = text

    def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        return ProviderAntwort(text=self._text, nutzung=Nutzung(), modell=self.modell_id)

    def fragen_stream(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        for stueck in re.findall(r"\S+\s*", self._text):
            yield stueck
        yield ProviderAntwort(text=self._text, nutzung=Nutzung(), modell=self.modell_id)


class DerStromZeigtNurGepruefes(unittest.TestCase):
    """Gegenprobe 03, in richtiger Polarität."""

    def _strom(self, text: str) -> list[dict]:
        d, c, sid = _sitzung(_StueckweiseProvider(text))
        antwort = c.post(f"/api/sitzungen/{sid}/frage/stream", json={"frage": "Was steht drin?"})
        return [json.loads(z) for z in antwort.text.splitlines() if z.strip()]

    def test_unbelegtes_geht_zu_keinem_zeitpunkt_hinaus(self):
        ereignisse = self._strom(f"Der Unfall war auf der B 27 [Q: {ECHT}]. {MARKER} [Q: D9-S9-P9].")
        self.assertNotIn(MARKER, json.dumps(ereignisse, ensure_ascii=False))

    def test_vor_der_ersten_aussage_steht_nur_die_zeichenzahl(self):
        ereignisse = self._strom(f"Der Unfall war auf der B 27 [Q: {ECHT}].")
        vor_dem_ersten_text = []
        for e in ereignisse:
            if e["type"] in ("geprueft", "fertig"):
                break
            vor_dem_ersten_text.append(e)
        self.assertTrue(vor_dem_ersten_text)
        for e in vor_dem_ersten_text:
            self.assertEqual(e["type"], "fortschritt")
            self.assertEqual(set(e) - {"type"}, {"zeichen"})

    def test_belegtes_kommt_schon_waehrend_des_stroms(self):
        """Das Schreibgefühl bleibt – nur eine Aussage später."""
        ereignisse = self._strom(
            f"Der Unfall war auf der B 27 [Q: {ECHT}]. Der Wagen war beschädigt [Q: {ECHT}].")
        gepruefte = [e for e in ereignisse if e["type"] == "geprueft"]
        self.assertTrue(gepruefte)
        self.assertIn("B 27", gepruefte[0]["text"])
        # Und er wächst, statt sich zu wiederholen.
        self.assertGreater(len(gepruefte[-1]["text"]), len(gepruefte[0]["text"]))

    def test_die_fristensperre_gilt_auch_im_strom(self):
        """Sonst stünde ein gerechneter Fristablauf da, bis das Ende kommt."""
        ereignisse = self._strom(
            f"Die Klagefrist endet am 26.05.2026 [Q: {ECHT}]. Weiteres folgt [Q: {ECHT}].")
        alles = json.dumps(ereignisse, ensure_ascii=False)
        self.assertNotIn("26.05.2026", alles)

    def test_die_endfassung_bleibt_massgeblich(self):
        ereignisse = self._strom(f"Der Unfall war auf der B 27 [Q: {ECHT}].")
        fertig = [e for e in ereignisse if e["type"] == "fertig"]
        self.assertEqual(len(fertig), 1)
        self.assertTrue(fertig[0]["antwort"]["quellen"])


class DieOberflaecheZeigtKeinenRohtext(unittest.TestCase):
    """Die Prüfung oben misst den Server. Der Rohtext stand im Browser."""

    def _app_js(self) -> str:
        from pathlib import Path

        return (Path(__file__).resolve().parent.parent
                / "jusperfect" / "static" / "app.js").read_text(encoding="utf-8")

    def test_sie_kennt_das_alte_textereignis_nicht_mehr(self):
        quelle = self._app_js()
        self.assertNotIn('ev.type === "text"', quelle)
        self.assertIn('ev.type === "fortschritt"', quelle)
        self.assertIn('ev.type === "geprueft"', quelle)

    def test_der_fortschritt_schreibt_keinen_inhalt_in_die_seite(self):
        """Er trägt nur eine Zahl – es darf gar kein Textfeld geben, das er
        anzeigen könnte."""
        quelle = self._app_js()
        block = quelle.split('ev.type === "fortschritt"')[1].split('ev.type === "geprueft"')[0]
        self.assertNotIn("ev.text", block)


if __name__ == "__main__":
    unittest.main()
