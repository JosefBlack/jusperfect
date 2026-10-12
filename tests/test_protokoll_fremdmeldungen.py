"""Was eine fremde Bibliothek ins Protokoll schreibt — Befund N02.

Dritte Zweitprüfung vom 12.10.2026. Die Protokollfabrik aus
`jusperfect/fehlergrenze.py` nahm den **angehängten Traceback** ab und ließ
**Meldungstext und Argumente** unverändert stehen.

`pypdf` schreibt beim Lesen eines beschädigten PDF Bestandteile des Dokuments
als gewöhnliche **Warnung**:

    pypdf._reader|WARNING|invalid pdf header: b'GEHEI'

Kein Traceback, keine eigene Protokollfunktion, also auch keine Feldsperre aus
`security/protokoll.py`. Derselbe Ausgang wie bei F01 am 05.10.2026 — nur ein
anderer Weg dorthin. **Eine saubere HTTP-Antwort beweist kein sauberes
Protokoll, und ein abgenommener Traceback auch nicht.**

Die Lehre dieses Befundes ist eine Richtung, keine Liste: Nicht der Traceback
ist das Gefährliche, sondern **jeder Wortlaut, den eine Bibliothek schreibt,
die Akteninhalt in der Hand hat**. Deshalb steht in `fehlergrenze.py` eine
Positivliste — was nicht darin steht, ist stumm, auch eine Bibliothek, die
erst morgen dazukommt.

Gemessen wird hier am **Ausgang**: an dem, was ein Protokoll-Handler
tatsächlich formatiert. Eine Prüfung, die nur den Quelltext liest, hätte
diesen Befund nicht gefunden — er stand ja nicht im Quelltext, sondern in dem,
was pypdf tut.
"""

from __future__ import annotations

import io
import logging
import warnings

import pytest

from jusperfect.fehlergrenze import (
    WORTLAUT_ERLAUBT, protokolle_eindaemmen, wortlaut_erlaubt,
)

#: Ein erfundener Inhalt, der niemals in einem Protokoll stehen darf. Er steht
#: am Anfang der Datei, weil pypdf die ersten Bytes meldet.
MARKE = "GEHEIMERAKTENINHALTXYZ"


class Sammler(logging.Handler):
    """Ein Protokoll-Handler, der aufschreibt, was wirklich hinausgeht.

    Nicht `caplog`: Der liest `record.message` über denselben Weg, aber hier
    soll ausdrücklich der **formatierte** Eintrag geprüft werden — das ist,
    was in einer Datei oder auf stderr landet.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.setFormatter(logging.Formatter("%(name)s|%(levelname)s|%(message)s"))
        self.zeilen: list[str] = []

    def emit(self, eintrag: logging.LogRecord) -> None:
        self.zeilen.append(self.format(eintrag))


@pytest.fixture
def ausgang():
    """Die Eindämmung ist aktiv, und ein Sammler hängt an der Wurzel."""
    protokolle_eindaemmen()
    wurzel = logging.getLogger()
    alte_stufe = wurzel.level
    sammler = Sammler()
    wurzel.addHandler(sammler)
    wurzel.setLevel(logging.DEBUG)
    # pypdf wird von LAUTE_BIBLIOTHEKEN nicht gedämpft; auf DEBUG gestellt,
    # damit die Prüfung nicht aus Versehen grün wird, weil nichts kam.
    logging.getLogger("pypdf").setLevel(logging.DEBUG)
    try:
        yield sammler
    finally:
        wurzel.removeHandler(sammler)
        wurzel.setLevel(alte_stufe)


def _kaputtes_pdf() -> bytes:
    """Ein PDF, dessen Kopf nicht stimmt — der Inhalt steht davor."""
    return (MARKE.encode() + b"\n%PDF-1.4\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n")


class TestDerWortlautVonPypdf:
    """Der eigentliche Fang."""

    def test_die_ersten_bytes_des_dokuments_erreichen_das_protokoll_nicht(self, ausgang):
        from pypdf import PdfReader
        try:
            leser = PdfReader(io.BytesIO(_kaputtes_pdf()))
            for seite in leser.pages:
                seite.extract_text()
        except Exception:
            pass        # Dass es scheitert, ist nicht der Gegenstand.
        assert ausgang.zeilen, "pypdf hat nichts gemeldet – dann prüft das hier nichts."
        alles = "\n".join(ausgang.zeilen)
        assert MARKE not in alles, alles
        assert MARKE[:5] not in alles, alles

    def test_dass_sich_pypdf_gemeldet_hat_steht_weiter_da(self, ausgang):
        """Verschwiegen wird nichts: Kanal, Stufe und Code-Stelle bleiben.

        Sonst wäre die Fehlersuche in der Kanzlei beendet, und ein stummes
        Protokoll ist auch ein Schaden.
        """
        from pypdf import PdfReader
        try:
            PdfReader(io.BytesIO(_kaputtes_pdf())).pages
        except Exception:
            pass
        alles = "\n".join(ausgang.zeilen)
        assert "pypdf" in alles
        assert "unterdrückt" in alles

    def test_die_echte_extraktion_geht_denselben_weg(self, ausgang):
        """Nicht pypdf allein – der Weg, den das Programm tatsächlich nimmt."""
        from jusperfect.domain.models import Dokument
        from jusperfect.services import extraktion
        dokument = Dokument(id="D1", akte_id="X-1", titel="Ein Scan",
                            dateiname="scan.pdf", mime_typ="application/pdf")
        try:
            extraktion.seiten(dokument, _kaputtes_pdf(), None)
        except Exception:
            pass
        assert MARKE not in "\n".join(ausgang.zeilen)


class TestJederFremdeKanal:
    """Nicht pypdf ist der Befund, sondern die Richtung."""

    @pytest.mark.parametrize("kanal", ["pypdf._reader", "docx.text", "PIL.Image",
                                       "ein.morgen.hinzugekommener.parser",
                                       "py.warnings", "asyncio", "botocore.auth"])
    def test_der_wortlaut_wird_ersetzt(self, ausgang, kanal):
        logging.getLogger(kanal).setLevel(logging.DEBUG)
        logging.getLogger(kanal).warning("Inhalt: %s", MARKE)
        assert ausgang.zeilen
        assert MARKE not in "\n".join(ausgang.zeilen)

    def test_auch_die_argumente_gehen_nicht_mit(self, ausgang):
        """`args` war der zweite Weg: Der Text ist eine Maske, der Inhalt steht daneben."""
        logging.getLogger("pypdf._reader").setLevel(logging.DEBUG)
        logging.getLogger("pypdf._reader").warning("%(was)s", {"was": MARKE})
        assert MARKE not in "\n".join(ausgang.zeilen)

    def test_warnungen_werden_ins_protokoll_umgeleitet(self, ausgang):
        """Manche Bibliothek protokolliert nicht, sondern warnt — und das
        schreibt unmittelbar nach stderr, vorbei an jeder Fabrik.

        Gemessen in zwei Teilen, statt hier eine echte Warnung auszulösen:
        pytest setzt um jede Prüfung sein eigenes `catch_warnings` und nimmt
        die Umleitung damit zurück. Eine hier ausgelöste Warnung liefe also an
        der Umleitung vorbei, und die Prüfung wäre still grün, ohne etwas
        gemessen zu haben.

        Teil eins: Die Umleitung ist eingeschaltet. Teil zwei: Der Kanal, in
        den sie umleitet, ist stumm (siehe die Prüfung darüber).
        """
        with warnings.catch_warnings():     # sichert showwarning und stellt es zurueck
            # logging.captureWarnings leitet nur um, wenn es nicht schon
            # umgeleitet hat - und eine fruehere Pruefung hat das getan. Also
            # erst zurueckstellen, sonst messe ich einen leeren Aufruf.
            logging.captureWarnings(False)
            protokolle_eindaemmen()
            assert warnings.showwarning.__module__ == "logging", (
                "logging.captureWarnings(True) wird nicht gesetzt – dann geht "
                "eine Warnung weiter unmittelbar nach stderr.")
        assert not wortlaut_erlaubt("py.warnings")


class TestWasBleibenMuss:
    """Eine Sperre, die alles verschluckt, macht das Programm unbedienbar."""

    def test_der_eigene_kanal_bleibt_unberuehrt(self, ausgang):
        """Er geht durch `ereignis()` und damit durch die Feldsperren."""
        logging.getLogger("jusperfect.probe").warning("Vorgangsnummer %s", "ab12cd34")
        assert "ab12cd34" in "\n".join(ausgang.zeilen)

    def test_uvicorn_meldet_weiter_dass_es_laeuft(self, ausgang):
        """Ohne diese Ausnahme stünde beim Start kein Lebenszeichen im Fenster."""
        logging.getLogger("uvicorn.error").info("Application startup complete.")
        assert "Application startup complete." in "\n".join(ausgang.zeilen)

    def test_die_ausnahmeliste_ist_kurz_und_begruendet(self):
        """Sie ist eine Positivliste; jeder Eintrag ist eine Entscheidung."""
        assert WORTLAUT_ERLAUBT == ("uvicorn",)

    def test_wortlaut_erlaubt_zieht_die_grenze_am_punkt(self):
        """„jusperfectfremd" ist nicht „jusperfect.…" – ein Vorsatzvergleich
        ohne Punkt hätte einen fremden Kanal durchgelassen."""
        assert wortlaut_erlaubt("jusperfect")
        assert wortlaut_erlaubt("jusperfect.entwuerfe")
        assert wortlaut_erlaubt("uvicorn.error")
        assert not wortlaut_erlaubt("jusperfectfremd")
        assert not wortlaut_erlaubt("uvicornfremd")
        assert not wortlaut_erlaubt("pypdf")
        assert not wortlaut_erlaubt("")


class TestDerKanalnameSelbst:
    """Protokolliert wird auch der Name – und `getLogger` nimmt jede Zeichenkette.

    Der Name ist die eine Angabe, die sagt, *welche* Bibliothek sich gemeldet
    hat; ohne ihn ist die Meldung zur Fehlersuche wertlos. Er darf deshalb
    stehen bleiben, solange er Programmtext **ist** — und nicht bloß so
    aussieht.
    """

    @pytest.mark.parametrize("kanal", [
        f"parser {MARKE}",                  # mit Leerzeichen: keine Bezeichnerform
        f"{MARKE}.pdf",                     # sieht aus wie ein Bezeichner, ist ein Dateiname
        f"Klage {MARKE} 2026.docx",
        f"/akten/{MARKE}/scan.pdf",
    ])
    def test_ein_kanalname_mit_inhalt_wird_zur_kurzkennung(self, ausgang, kanal):
        """Die zweite Bedingung trägt hier: Das erste Stück ist kein geladenes
        Modul. Die Form allein hätte `GEHEIM….pdf` durchgelassen."""
        logging.getLogger(kanal).setLevel(logging.DEBUG)
        logging.getLogger(kanal).warning("egal")
        # Nur der formatierte Text, nicht das Namensfeld des Formatierers:
        # Dass logging selbst den Namen kennt, ist unvermeidlich; geprüft wird,
        # was DIESES Modul hineinschreibt.
        geschrieben = "\n".join(z.split("|", 2)[2] for z in ausgang.zeilen)
        assert MARKE not in geschrieben, geschrieben
        assert "Kanal " in geschrieben

    def test_der_name_einer_wirklich_geladenen_bibliothek_bleibt_lesbar(self, ausgang):
        import pypdf                                            # noqa: F401
        logging.getLogger("pypdf._reader").setLevel(logging.DEBUG)
        logging.getLogger("pypdf._reader").warning("egal")
        assert "Kanal pypdf._reader" in "\n".join(ausgang.zeilen)

    def test_kanalname_sagt_was_er_tut(self):
        from jusperfect.fehlergrenze import kanalname
        import pypdf                                            # noqa: F401
        assert kanalname("pypdf._reader") == "pypdf._reader"
        assert kanalname("py.warnings") == "py.warnings"
        assert kanalname("") == "(ohne Namen)"
        for erfunden in (f"{MARKE}.pdf", f"parser {MARKE}", "Klage.pdf"):
            assert MARKE not in kanalname(erfunden)
            assert ":" in kanalname(erfunden), "eine Kurzkennung nennt ihre Länge mit"
