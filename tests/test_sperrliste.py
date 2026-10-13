"""Die Liste der gesperrten Namen — wo sie liegt und wie sie dort hinkommt.

**Befund N01 der dritten Zweitprüfung vom 12.10.2026, Variante A.** Die echten
Namen liegen seit dem 13.10.2026 außerhalb des Programmordners. Diese Prüfung
hält drei Dinge fest:

1. **Die Orte liegen draußen.** Eine Liste echter Namen *im* Programmordner
   wäre in jedem ZIP — genau der Fehler, den Variante A behebt.
2. **Der Ort steht einmal im Programm**, nicht zweimal. Zwei Listen von Orten,
   die auseinanderlaufen können, wären derselbe Fehler wie zwei Zähler für
   dieselbe Sache (Befund N04).
3. **Die Datei wird geführt angelegt.** Aus der Kanzlei mehrfach gelernt: Ein
   Nichtprogrammierer soll keine Datei mit der richtigen Zeichenkodierung an
   einem abgezählten Pfad anlegen müssen. Notepad hängt ein zweites „.txt" an
   und speichert nach Laune in ANSI — und ein Umlaut in ANSI heißt: **Die
   Prüfung findet den Namen nicht und ist grün.**

Geprüft wird hier mit **erfundenen** Namen. Die echten stehen nirgends in
diesem Bestand, und das ist der Zweck der Änderung.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from jusperfect.sperrliste import (
    KOPF, PROGRAMMORDNER, SPERRLISTE_NAME, finden, main, orte, schreiben,
    verdeckt, woerter,
)

#: Erfundene Namen, wie sie in den Testakten vorkommen.
ERFUNDEN = ("Vellinghausen", "Krämer", "Kraemer")


class TestDieOrteLiegenDraussen:
    def test_kein_ort_liegt_im_programmordner(self) -> None:
        """Der ganze Punkt von Variante A."""
        for ort in orte():
            assert PROGRAMMORDNER not in ort.parents, ort
            assert ort != PROGRAMMORDNER

    def test_es_sind_der_nachbar_und_der_benutzerordner(self) -> None:
        assert orte()[0] == PROGRAMMORDNER.parent / SPERRLISTE_NAME
        assert any(o == Path.home() / SPERRLISTE_NAME for o in orte())

    def test_derselbe_ort_steht_nicht_zweimal_da(self) -> None:
        """Auf einem Arbeitsplatz sind beide Orte oft dasselbe Verzeichnis."""
        assert len(set(orte())) == len(orte())

    def test_der_name_ist_an_beiden_orten_derselbe(self) -> None:
        for ort in orte():
            assert ort.name == SPERRLISTE_NAME


class TestDieListeWirdGelesen:
    def test_ein_wort_je_zeile(self, tmp_path: Path) -> None:
        datei = tmp_path / SPERRLISTE_NAME
        datei.write_text("\n".join(ERFUNDEN) + "\n", encoding="utf-8")
        assert woerter(datei) == ERFUNDEN

    def test_kommentare_und_leerzeilen_zaehlen_nicht(self, tmp_path: Path) -> None:
        datei = tmp_path / SPERRLISTE_NAME
        datei.write_text("# Erklaerung\n\nVellinghausen   # dazu etwas\n\n",
                         encoding="utf-8")
        assert woerter(datei) == ("Vellinghausen",)

    def test_doppeltes_steht_einmal(self, tmp_path: Path) -> None:
        datei = tmp_path / SPERRLISTE_NAME
        datei.write_text("Krämer\nKrämer\n", encoding="utf-8")
        assert woerter(datei) == ("Krämer",)

    def test_ohne_liste_kommt_ein_leeres_tupel(self, monkeypatch, tmp_path: Path) -> None:
        """Keine Liste an den vorgesehenen Orten: leeres Tupel, kein Fehler.

        So verhält sich ein Prüfpaket bei einem Dritten — dort soll der Lauf
        nicht rot sein, sondern die Namenssuche überspringen und das sagen.
        """
        monkeypatch.setattr("jusperfect.sperrliste.orte",
                            lambda: (tmp_path / SPERRLISTE_NAME,))
        assert finden() is None
        assert woerter() == ()

    def test_eine_ausdruecklich_genannte_fehlende_datei_wirft(self, tmp_path) -> None:
        """Wer einen Pfad NENNT, meint ihn. Dann ist sein Fehlen ein Fehler.

        Dasselbe fail closed wie bei der unlesbaren Datei darunter: Still grün
        darf keiner der beiden Fälle sein.
        """
        with pytest.raises(OSError):
            woerter(tmp_path / "gibt-es-nicht.txt")

    def test_eine_unlesbare_liste_wirft(self, tmp_path: Path) -> None:
        """Fail closed: Eine kaputte Liste ist etwas anderes als keine.

        Im ersten Fall ist etwas kaputt, im zweiten ist es Absicht — und still
        grün darf keiner von beiden sein.
        """
        datei = tmp_path / SPERRLISTE_NAME
        datei.write_bytes(b"\xff\xfe\x00Unlesbar")
        with pytest.raises(UnicodeDecodeError):
            woerter(datei)


class TestNichtsWirdImWortlautGemeldet:
    def test_verdeckt_zeigt_erster_buchstabe_und_laenge(self) -> None:
        """Das kurze Beispiel ist ein Platzhalter und keine Abkürzung.

        Hier stand zuerst die echte des Gegners — zum siebten Mal dasselbe
        Muster, und diesmal in der Prüfdatei des Mechanismus selbst. Gefangen
        hat es ein Nachlauf mit der Liste. Mein blinder Fleck ist dabei immer
        derselbe: Ein kurzes Kürzel sieht für mich nicht aus wie ein Name.
        """
        assert verdeckt("Vellinghausen") == "V............ (13 Zeichen)"
        assert verdeckt("XYZ") == "X.. (3 Zeichen)"

    def test_ein_einzelnes_zeichen_bleibt_lesbar(self) -> None:
        """Dort gibt es nichts zu verdecken, und „. (1 Zeichen)" wäre Unsinn."""
        assert verdeckt("X") == "X (1 Zeichen)"

    def test_der_rest_des_wortes_steht_nicht_darin(self) -> None:
        for wort in ERFUNDEN:
            gezeigt = verdeckt(wort)
            assert wort not in gezeigt
            assert wort[1:] not in gezeigt


class TestDieListeWirdGeschrieben:
    def test_sie_traegt_ihre_eigene_erklaerung(self, tmp_path: Path) -> None:
        """Eine Datei, die ein Nichtprogrammierer bearbeiten soll, muss ihre
        Anleitung bei sich tragen — sonst steht sie woanders."""
        ort, _ = schreiben(tmp_path / SPERRLISTE_NAME, ["Vellinghausen"])
        text = ort.read_text(encoding="utf-8")
        assert text.startswith(KOPF)
        assert "NICHT in den Programmordner" in text
        assert "Befund N01" in text

    def test_vorhandenes_bleibt(self, tmp_path: Path) -> None:
        datei = tmp_path / SPERRLISTE_NAME
        schreiben(datei, ["Vellinghausen"])
        _, anzahl = schreiben(datei, ["Krämer"])
        assert anzahl == 2
        assert woerter(datei) == ("Vellinghausen", "Krämer")

    def test_doppeltes_wird_nicht_angehaengt(self, tmp_path: Path) -> None:
        datei = tmp_path / SPERRLISTE_NAME
        schreiben(datei, ["Vellinghausen"])
        _, anzahl = schreiben(datei, ["Vellinghausen"])
        assert anzahl == 1

    def test_sie_wird_als_utf8_geschrieben(self, tmp_path: Path) -> None:
        """Der Fehler, den Notepad macht: ANSI statt UTF-8. Dann findet die
        Prüfung „Krämer" nicht — und ist grün."""
        ort, _ = schreiben(tmp_path / SPERRLISTE_NAME, ["Krämer"])
        assert "Krämer" in ort.read_text(encoding="utf-8")
        assert "Krämer".encode("utf-8") in ort.read_bytes()
        assert "Krämer".encode("cp1252") not in ort.read_bytes()


class TestDerGefuehrteWeg:
    """`main()` mit vorgegebener Eingabe — der Weg, den die Kanzlei geht."""

    def _lauf(self, eingaben: list[str], monkeypatch, tmp_path: Path):
        monkeypatch.setattr("jusperfect.sperrliste.orte",
                            lambda: (tmp_path / SPERRLISTE_NAME,))
        folge = iter(eingaben + [""])
        monkeypatch.setattr("builtins.input", lambda *a: next(folge))
        return main()

    def test_er_legt_die_liste_an(self, monkeypatch, tmp_path, capsys) -> None:
        assert self._lauf(["Vellinghausen", "Krämer"], monkeypatch, tmp_path) == 0
        assert woerter(tmp_path / SPERRLISTE_NAME) == ("Vellinghausen", "Krämer")

    def test_er_nennt_die_woerter_nicht_im_wortlaut(self, monkeypatch, tmp_path,
                                                   capsys) -> None:
        """Sonst stünde der Name im Fenster — und in einem Bildschirmfoto."""
        self._lauf(["Vellinghausen"], monkeypatch, tmp_path)
        ausgabe = capsys.readouterr().out
        assert "Vellinghausen" not in ausgabe
        assert "V............ (13 Zeichen)" in ausgabe

    def test_ein_zu_kurzes_wort_wird_abgewiesen(self, monkeypatch, tmp_path,
                                                capsys) -> None:
        """„Ei" stünde in jedem zweiten Satz, und eine Prüfung, die immer rot
        ist, wird nach einer Woche abgeschaltet."""
        self._lauf(["XY", "Vellinghausen"], monkeypatch, tmp_path)
        assert "zu kurz" in capsys.readouterr().out
        assert woerter(tmp_path / SPERRLISTE_NAME) == ("Vellinghausen",)

    def test_eine_zeile_mit_raute_wird_abgewiesen(self, monkeypatch, tmp_path,
                                                  capsys) -> None:
        """Sonst stünde der Name als Kommentar da und wäre still unwirksam."""
        self._lauf(["#Vellinghausen", "Krämer"], monkeypatch, tmp_path)
        assert "faengt nicht mit # an" in capsys.readouterr().out
        assert woerter(tmp_path / SPERRLISTE_NAME) == ("Krämer",)

    def test_ohne_eingabe_wird_nichts_angelegt(self, monkeypatch, tmp_path,
                                               capsys) -> None:
        assert self._lauf([], monkeypatch, tmp_path) == 1
        assert not (tmp_path / SPERRLISTE_NAME).exists()

    def test_er_sagt_dass_der_zweite_rechner_fehlt(self, monkeypatch, tmp_path,
                                                   capsys) -> None:
        """Die Liste liegt je Rechner. Wer das nicht weiß, hält einen Rechner
        für geprüft, der es nicht ist."""
        self._lauf(["Vellinghausen"], monkeypatch, tmp_path)
        ausgabe = capsys.readouterr().out
        assert "ZWEITEN Kanzleirechner" in ausgabe
        assert "PRUEFBOGEN.bat" in ausgabe

    def test_er_zeigt_eine_vorhandene_liste_verdeckt(self, monkeypatch, tmp_path,
                                                     capsys) -> None:
        schreiben(tmp_path / SPERRLISTE_NAME, ["Vellinghausen"])
        self._lauf([], monkeypatch, tmp_path)
        ausgabe = capsys.readouterr().out
        assert "schon eine Liste mit 1 Wort" in ausgabe
        assert "Vellinghausen" not in ausgabe


class TestDieStartdatei:
    @staticmethod
    def _bat() -> str:
        pfad = Path(__file__).resolve().parent.parent / "SPERRLISTE-ANLEGEN.bat"
        return io.open(pfad, encoding="utf-8").read()

    def test_sie_ist_da(self) -> None:
        assert self._bat()

    def test_sie_hat_windows_zeilenenden(self) -> None:
        """Ohne CRLF stolpert cmd.exe — deshalb steht es in .gitattributes."""
        pfad = Path(__file__).resolve().parent.parent / "SPERRLISTE-ANLEGEN.bat"
        rohe = pfad.read_bytes()
        assert b"\r\n" in rohe
        assert rohe.count(b"\n") == rohe.count(b"\r\n")

    def test_sie_ruft_das_programm(self) -> None:
        assert "-m jusperfect.sperrliste" in self._bat()

    def test_sie_verlangt_keine_arbeitsumgebung(self) -> None:
        """Dieselbe Erwägung wie bei JURNODES-ZUGANG.bat am 25.09.2026: Eine
        Hürde, die nichts schützt, ist keine Sperre, sondern ein Fehler."""
        text = self._bat()
        assert 'set "PY=python"' in text
        assert "where python" in text

    def test_sie_sagt_warum_die_liste_draussen_liegt(self) -> None:
        text = self._bat()
        assert "NICHT in den Programmordner" in text
        assert "NICHT in eine ZIP" in text

    def test_sie_steht_in_der_anleitung_der_zeichen(self) -> None:
        """UTF-8 im Fenster: Ohne chcp 65001 wird aus „ä" Buchstabensalat."""
        assert "chcp 65001" in self._bat()
        assert "PYTHONUTF8=1" in self._bat()
