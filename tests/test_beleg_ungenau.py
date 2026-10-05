"""Eine Fundstelle, deren Aussage sich im Absatz nicht wiederfinden lässt.

Aus der Kanzlei am 05.10.2026: „Ich kann die Dateien nicht finden. Stammen die
Dateien vielleicht aus gebildeten Mustern?"

Die Frage ist berechtigt, und das Programm konnte sie bisher nicht beantworten.
Geprüft wird die **Kennung**: Eine erfundene löst auf keine mitgelieferte
Passage auf und fällt heraus – fail closed, so steht es in `belegpflicht.py`.
Der **Inhalt** wurde nicht geprüft. Fand sich die Aussage nicht in der Passage
wieder, stand auf der Karte still der Anfang des Absatzes, und die Karte sah
aus wie jede andere.

Was hier **nicht** behauptet wird: dass eine solche Stelle erfunden sei. Das
wäre ein Urteil, das das Programm nicht fällen kann – eine Umschreibung mit
anderen Worten findet sich zu Recht nicht wortwörtlich wieder, und
``fundstelle.py`` rät ausdrücklich nicht. Gesagt wird, was bekannt ist: Die
Stelle ließ sich nicht zuordnen, oben steht der Anfang des Absatzes, bitte
nachlesen.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

STATISCH = Path(__file__).resolve().parent.parent / "jusperfect" / "static"


@pytest.fixture(scope="module")
def app() -> str:
    return (STATISCH / "app.js").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def css() -> str:
    return (STATISCH / "styles.css").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def belege(app: str) -> str:
    return re.search(r"function zeigeBelege\(\) \{(.*?)\n\}", app, re.S).group(1)


class TestDieKarteSagtEs:
    def test_eine_nicht_zuzuordnende_stelle_wird_gekennzeichnet(self, belege: str) -> None:
        assert 'karte.classList.add("ungenau")' in belege
        assert "if (!genau)" in belege

    def test_der_hinweis_steht_auf_der_karte(self, belege: str) -> None:
        assert "nicht zuordnen" in belege
        assert "nachlesen" in belege

    def test_sie_unterscheidet_sich_auch_im_aussehen(self, css: str) -> None:
        """Ein Hinweis, der aussieht wie alles andere, ist keiner."""
        assert ".beleg-karte.ungenau" in css
        assert ".beleg-hinweis" in css

    def test_woran_genau_haengt(self, belege: str) -> None:
        """An ``treffer_start`` – gesetzt nur, wenn die Stelle gefunden wurde."""
        assert "const genau = !!(q && Number.isInteger(q.treffer_start));" in belege


class TestWasNichtBehauptetWird:
    def test_das_wort_erfunden_kommt_nicht_vor(self, belege: str) -> None:
        """Das Programm kann nicht wissen, ob eine Aussage erfunden ist.

        Es weiß nur, dass es die Stelle nicht zuordnen konnte. Alles darüber
        hinaus wäre ein Urteil – und ein falsches Urteil über einen Beleg ist
        schlimmer als gar keines.
        """
        # Ohne die Kommentarzeilen: Dort steht gerade die Begruendung, WARUM
        # das Wort nicht faellt - sie darf es nennen, die Karte nicht.
        sichtbar = "\n".join(z for z in belege.splitlines()
                             if not z.strip().startswith("//")).lower()
        for wort in ("erfunden", "falsch", "unbelegt", "halluzination"):
            assert wort not in sichtbar, wort

    def test_der_grund_steht_im_quelltext(self, app: str) -> None:
        stelle = app[app.index("// Die Aussage liess sich in der Passage NICHT"):]
        kopf = stelle[:stelle.index("if (!genau)")]
        assert "Umschreibung" in kopf
        assert "fail closed" in kopf


class TestDieBelegpflichtBleibtWieSieWar:
    def test_eine_erfundene_kennung_faellt_weiter_heraus(self) -> None:
        """Das ist der härtere Riegel, und er bleibt unberührt."""
        from jusperfect.domain.models import Passage
        from jusperfect.services.belegpflicht import ENTFERNT, aussage_fail_closed

        echt = Passage(kennung="D1-S1-P1", dokument_id="D1", dokument_titel="T",
                       seite=1, text="Die Kündigung ging am 04.05.2026 zu.")
        ergebnis = aussage_fail_closed(
            "Die Kündigung ging am 04.05.2026 zu. [Q: D1-S1-P1] "
            "Der Betriebsrat wurde angehört. [Q: D47-S1-P1]",
            {"D1-S1-P1": echt})
        assert ENTFERNT in ergebnis.text
        assert "Betriebsrat" not in ergebnis.text
        assert "04.05.2026" in ergebnis.text
