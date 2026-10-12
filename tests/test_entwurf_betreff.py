"""Der Betreff eines Entwurfs — Befund N12.

Dritte Zweitprüfung vom 12.10.2026. Das Modell liefert zwei Felder,
``betreff`` und ``text``. Durch die Belegprüfung ging nur ``text``.

Ein Betreff wie **„Anerkenntnis der Haftung vom 14.03.2026"** blieb damit
unverändert stehen, sobald der Brieftext irgendeinen tragenden Beleg hatte —
und kam mit HTTP 201 heraus. Die Belegpflicht war vorhanden, sie deckte nur
nicht alle Felder der Antwort.

**Warum das mehr ist als eine Kopfzeile:** Bei der Freigabe geht der Betreff
in den Vermerktext *und* in den Titel des Vermerks nach jur|nodes
(``entwuerfe.py``, ``freigeben``). Eine erfundene Behauptung landete also an
der sichtbarsten Stelle der Akte, dort, wo später jemand die Akte überfliegt.

**Die Abhilfe ist nicht eine weitere Prüfung, sondern eine andere Quelle.**
Ein Betreff ist kein Satz; ein ``[Q: …]`` darin wäre unbrauchbar, und eine
Belegprüfung über drei Wörter würde entweder alles verwerfen oder nichts
fangen. Art des Schreibens, Aktenzeichen und Bezeichnung stehen alle in
jur|nodes — keine dieser drei Angaben kann ein Modell erfinden.

Der Vorschlag des Modells wird dabei nicht weggeworfen: Er steht als
ungeprüft gekennzeichneter **Hinweis** da. Hinweise gehen nicht nach
jur|nodes und nicht in die Freigabevorlage. Wer den Vorschlag will, trägt ihn
ein — dann steht dort, was ein Mensch geschrieben hat, und die
Freigabeprüfsumme bindet ihn (Befund F06).

F04 am 05.10.2026 war der Brieftext. Dies ist ein zweiter Ausgang, nicht
derselbe noch einmal.
"""

from __future__ import annotations

import json

import pytest

from jusperfect.domain.models import Akte, EntwurfArt
from jusperfect.providers.base import Nutzung, ProviderAntwort
from jusperfect.services.entwuerfe import betreff_aus_der_akte
from tests.hilfen import client, dienste

#: Was ein Modell erfunden hat und was niemals in einer Akte stehen darf.
ERFUNDEN = "Anerkenntnis der Haftung vom 14.03.2026"

#: Eine Passage, die es wirklich gibt — damit der Brieftext belegt ist und der
#: Entwurf überhaupt ausgegeben wird. Sonst prüft die Sache hier nichts.
BELEGT = "Sehr geehrte Damen und Herren, der Sachstand ist festgehalten [Q: D1-S1-P1]."


class SkriptProvider:
    modell_id = "skript"

    def __init__(self, antworten):
        self.antworten = list(antworten)

    def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        return ProviderAntwort(text=self.antworten.pop(0), nutzung=Nutzung(1000, 200),
                               modell=modell_id or self.modell_id)


@pytest.fixture
def entwurf():
    """Ein Entwurf über die öffentliche Schnittstelle — mit erfundenem Betreff."""
    p = SkriptProvider([json.dumps({"betreff": ERFUNDEN, "text": BELEGT})])
    d = dienste(provider=p)
    c = client(d)
    sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
    c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
    antwort = c.post(f"/api/sitzungen/{sid}/entwuerfe",
                     json={"art": "rsv", "anweisung": "Deckung anfragen"})
    assert antwort.status_code == 201, antwort.text
    return d, c, antwort.json()


class TestDerErfundeneBetreffKommtNichtHeraus:
    """Der Nachweis, am öffentlichen Ausgang gemessen."""

    def test_er_steht_nicht_im_betreff(self, entwurf):
        _, _, e = entwurf
        assert ERFUNDEN not in e["betreff"]

    def test_er_steht_auch_nicht_im_text(self, entwurf):
        """Nicht heimlich nach unten verschoben."""
        _, _, e = entwurf
        assert ERFUNDEN not in e["text"]

    def test_er_erreicht_jurnodes_nicht(self, entwurf):
        """Der Weg, der zählt: Vermerktitel und Vermerktext in der Akte."""
        d, c, e = entwurf
        antwort = c.post(f"/api/entwuerfe/{e['id']}/freigabe",
                         json={"bestaetigung": True,
                               "freigabe_pruefsumme": e["freigabe_pruefsumme"]})
        assert antwort.status_code == 200, antwort.text
        vermerk = d.adapter.geschriebene_vermerke[0]
        geschrieben = json.dumps(vermerk, ensure_ascii=False, default=str)
        assert ERFUNDEN not in geschrieben, geschrieben

    def test_der_vorschlag_bleibt_als_vorschlag_sichtbar(self, entwurf):
        """Verschwiegen wird nichts — nur nicht übernommen.

        „Entfernen statt markieren" gilt für die Hauptausgabe. Zahl und Art
        des Entfernten gehören trotzdem auf den Tisch, und hier ist es der
        Wortlaut: Vielleicht ist der Vorschlag ja gut.
        """
        _, _, e = entwurf
        hinweise = " ".join(e["hinweise"])
        assert ERFUNDEN in hinweise
        assert "nicht übernommen" in hinweise
        assert "nicht belegt" in hinweise

    def test_die_hinweise_gehen_nicht_mit_nach_jurnodes(self, entwurf):
        """Sonst wäre der Hinweis der neue Weg hinaus."""
        d, c, e = entwurf
        c.post(f"/api/entwuerfe/{e['id']}/freigabe",
               json={"bestaetigung": True,
                     "freigabe_pruefsumme": e["freigabe_pruefsumme"]})
        geschrieben = json.dumps(d.adapter.geschriebene_vermerke[0],
                                 ensure_ascii=False, default=str)
        assert "nicht übernommen" not in geschrieben


class TestWoherDerBetreffStattdessenKommt:
    def test_aus_der_akte(self, entwurf):
        d, _, e = entwurf
        akte = d.adapter.akte("VU-2026-0042")
        assert e["betreff"] == betreff_aus_der_akte(EntwurfArt.RSV, akte)
        assert akte.aktenzeichen in e["betreff"]

    def test_er_nennt_die_art_des_schreibens(self):
        akte = Akte(id="a", aktenzeichen="X-100-2026", bezeichnung="Sache gegen Dritte")
        betreff = betreff_aus_der_akte(EntwurfArt.MAHNUNG, akte)
        assert betreff.startswith("Mahnung")
        assert "X-100-2026" in betreff
        assert "Sache gegen Dritte" in betreff

    def test_eine_akte_ohne_bezeichnung_gibt_keinen_leeren_teil(self):
        """Sonst stünde dort „Mahnung · X-100-2026 · " mit nichts dahinter."""
        akte = Akte(id="a", aktenzeichen="X-100-2026", bezeichnung="")
        assert betreff_aus_der_akte(EntwurfArt.MAHNUNG, akte) == "Mahnung · X-100-2026"

    def test_auch_ohne_jede_angabe_bleibt_die_art_stehen(self):
        akte = Akte(id="a", aktenzeichen="", bezeichnung="")
        assert betreff_aus_der_akte(EntwurfArt.MANDANT, akte) == "Schreiben an den Mandanten"

    def test_jede_entwurfsart_hat_einen_betreff(self):
        akte = Akte(id="a", aktenzeichen="X-100-2026", bezeichnung="Sache")
        for art in EntwurfArt:
            assert betreff_aus_der_akte(art, akte).strip()


class TestDerMenschDarfWeiterSchreibenWasErWill:
    """Die Sperre gilt dem Modell, nicht dem Anwalt."""

    def test_ein_eingetragener_betreff_wird_genommen(self, entwurf):
        _, c, e = entwurf
        neu = c.put(f"/api/entwuerfe/{e['id']}",
                    json={"betreff": "Unfall vom 12.05.2025, Ihr Zeichen 4711",
                          "text": e["text"]}).json()
        assert neu["betreff"] == "Unfall vom 12.05.2025, Ihr Zeichen 4711"

    def test_und_die_freigabepruefsumme_bindet_ihn(self, entwurf):
        """Befund F06: Der Betreff steht in der Freigabevorlage."""
        _, c, e = entwurf
        neu = c.put(f"/api/entwuerfe/{e['id']}",
                    json={"betreff": "Von Hand", "text": e["text"]}).json()
        assert neu["freigabe_pruefsumme"] != e["freigabe_pruefsumme"]
        alt = c.post(f"/api/entwuerfe/{e['id']}/freigabe",
                     json={"bestaetigung": True,
                           "freigabe_pruefsumme": e["freigabe_pruefsumme"]})
        assert alt.status_code == 422


class TestWennDasModellGarKeinJsonLiefert:
    """Der zweite Weg durch dieselbe Stelle."""

    def test_auch_dann_steht_der_betreff_aus_der_akte(self):
        p = SkriptProvider([f"Kein JSON, nur Text. {BELEGT}"])
        d = dienste(provider=p)
        c = client(d)
        sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
        c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
        e = c.post(f"/api/sitzungen/{sid}/entwuerfe",
                   json={"art": "mahnung", "anweisung": "mahnen"}).json()
        akte = d.adapter.akte("VU-2026-0042")
        assert e["betreff"] == betreff_aus_der_akte(EntwurfArt.MAHNUNG, akte)
