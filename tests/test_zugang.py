"""Zugangsdaten hinterlegen, ohne die AWS CLI.

Aus der Kanzlei: Das Installationspaket der AWS CLI ließ sich nicht laden, und
damit stand die Einrichtung still. Sie wird aber gar nicht gebraucht – sie
schreibt nur zwei Textdateien, die boto3 ohnehin von dort liest.
"""

from __future__ import annotations

import configparser
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jusperfect import zugang

KENNUNG = "AKIAIOSFODNN7EXAMPLE"
GEHEIM = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"


class Hinterlegen(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.heim = Path(self.tmp.name)
        self.aws = self.heim / ".aws"

    def _lauf(self, eingaben, geheim=GEHEIM, umgebung=None):
        with patch("os.path.expanduser", return_value=str(self.heim)), \
             patch("builtins.input", side_effect=list(eingaben)), \
             patch("getpass.getpass", return_value=geheim), \
             patch.dict("os.environ", umgebung or {}, clear=False):
            return zugang.main()

    def _gelesen(self, datei: str) -> configparser.ConfigParser:
        konf = configparser.ConfigParser()
        konf.read(self.aws / datei, encoding="utf-8")
        return konf

    def test_legt_beide_dateien_an(self):
        self.assertEqual(self._lauf([KENNUNG, ""]), 0)
        zugangsdatei = self._gelesen("credentials")
        self.assertEqual(zugangsdatei["default"]["aws_access_key_id"], KENNUNG)
        self.assertEqual(zugangsdatei["default"]["aws_secret_access_key"], GEHEIM)
        # Die Region gehört in config, so hält es die AWS CLI auch.
        self.assertEqual(self._gelesen("config")["default"]["region"], "eu-central-1")

    def test_boto3_findet_die_geschriebenen_daten(self):
        """Der eigentliche Beweis – nicht die Datei, sondern ihre Wirkung."""
        try:
            import boto3  # noqa: F401
        except ImportError:
            self.skipTest("boto3 ist in dieser Umgebung nicht installiert.")
        import os
        import boto3
        self._lauf([KENNUNG, ""])
        # Umgebungsvariablen gehen der Datei vor. Stehen welche im System -
        # in dieser Prueflandschaft setzt sie der Proxy -, pruefte der Test
        # sonst etwas anderes, als er zu pruefen meint.
        ohne = {k: "" for k in os.environ
                if k.startswith("AWS_") and k not in ("AWS_SHARED_CREDENTIALS_FILE", "AWS_CONFIG_FILE")}
        with patch.dict("os.environ", {
            **{k: "" for k in ohne},
            "AWS_SHARED_CREDENTIALS_FILE": str(self.aws / "credentials"),
            "AWS_CONFIG_FILE": str(self.aws / "config"),
        }, clear=False):
            for k in ohne:
                os.environ.pop(k, None)
            sitzung = boto3.Session()
            gefunden = sitzung.get_credentials()
        self.assertIsNotNone(gefunden, "boto3 muss die Daten finden – sonst nützt die Datei nichts.")
        self.assertEqual(gefunden.access_key, KENNUNG)

    def test_eigene_region_wird_uebernommen(self):
        self._lauf([KENNUNG, "eu-west-1"])
        self.assertEqual(self._gelesen("config")["default"]["region"], "eu-west-1")

    def test_fremde_profile_bleiben_erhalten(self):
        """Wer schon mit AWS arbeitet, darf seine übrigen Zugänge nicht verlieren."""
        self.aws.mkdir(parents=True)
        (self.aws / "credentials").write_text(
            "[andere-kanzlei]\naws_access_key_id = AKIAFREMD\n"
            "aws_secret_access_key = fremd\n", encoding="utf-8")
        self._lauf([KENNUNG, ""])
        konf = self._gelesen("credentials")
        self.assertEqual(konf["andere-kanzlei"]["aws_access_key_id"], "AKIAFREMD")
        self.assertEqual(konf["default"]["aws_access_key_id"], KENNUNG)

    def test_vorhandenes_profil_wird_nicht_stillschweigend_ueberschrieben(self):
        self.aws.mkdir(parents=True)
        (self.aws / "credentials").write_text(
            "[default]\naws_access_key_id = AKIAALT\naws_secret_access_key = alt\n",
            encoding="utf-8")
        self.assertEqual(self._lauf(["n"]), 1)
        self.assertEqual(self._gelesen("credentials")["default"]["aws_access_key_id"], "AKIAALT")

    def test_nach_zustimmung_wird_ueberschrieben(self):
        self.aws.mkdir(parents=True)
        (self.aws / "credentials").write_text(
            "[default]\naws_access_key_id = AKIAALT\naws_secret_access_key = alt\n",
            encoding="utf-8")
        self.assertEqual(self._lauf(["j", KENNUNG, ""]), 0)
        self.assertEqual(self._gelesen("credentials")["default"]["aws_access_key_id"], KENNUNG)

    def test_leere_eingaben_werden_abgewiesen(self):
        self.assertEqual(self._lauf([""]), 2)
        self.assertFalse((self.aws / "credentials").exists())
        self.assertEqual(self._lauf([KENNUNG, ""], geheim=""), 2)

    def test_verwechselte_werte_werden_erkannt(self):
        """Beides gleich heisst: einmal derselbe Wert zweimal eingefügt."""
        self.assertEqual(self._lauf([KENNUNG, ""], geheim=KENNUNG), 2)

    def test_der_geheime_schluessel_erscheint_nirgends_in_der_ausgabe(self):
        """Was im schwarzen Fenster steht, liest der Nächste mit."""
        import io
        from contextlib import redirect_stdout
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            self._lauf([KENNUNG, ""])
        ausgabe = puffer.getvalue()
        self.assertNotIn(GEHEIM, ausgabe)
        # Auch die Kennung steht nur maskiert da.
        self.assertNotIn(KENNUNG, ausgabe)
        self.assertIn("AKIA…MPLE", ausgabe)

    def test_eigenes_profil_aus_der_umgebung(self):
        self._lauf([KENNUNG, ""], umgebung={"AWS_PROFILE": "kanzlei"})
        self.assertEqual(self._gelesen("credentials")["kanzlei"]["aws_access_key_id"], KENNUNG)
        # In config traegt ein benanntes Profil den Vorsatz "profile".
        self.assertEqual(self._gelesen("config")["profile kanzlei"]["region"], "eu-central-1")


if __name__ == "__main__":
    unittest.main()


class DerZugangstestNenntDieKennung(unittest.TestCase):
    """Aus der Kanzlei: „Die Access Key ID kennt AWS nicht."

    Das war die richtige Auskunft – und half trotzdem nicht weiter, weil der
    Test nicht sagte, *welche* Kennung er verschickt hat. Ohne sie lässt sich
    in der AWS-Konsole nichts vergleichen; man tippt beide Werte neu ein und
    hofft. Die Access Key ID ist kein Geheimnis (AWS zeigt sie selbst an),
    verkürzt steht sie hier trotzdem: Diese Ausgabe wird weitergegeben.
    """

    def test_der_geheime_schluessel_bleibt_unsichtbar(self):
        self.assertNotIn(GEHEIM[4:-4], zugang._maskiert(GEHEIM))

    def test_die_kennung_bleibt_wiedererkennbar(self):
        verkuerzt = zugang._maskiert(KENNUNG)
        self.assertTrue(verkuerzt.startswith("AKIA"))
        self.assertTrue(verkuerzt.endswith(KENNUNG[-4:]))
        self.assertNotIn(KENNUNG[4:-4], verkuerzt)

    def test_zwei_schluessel_lassen_sich_unterscheiden(self):
        """Genau dafür ist die Zeile da – sonst genügte „ein Schlüssel"."""
        self.assertNotEqual(zugang._maskiert("AKIAAAAAAAAAAAAAAAA1"),
                            zugang._maskiert("AKIAAAAAAAAAAAAAAAA2"))

    def test_der_zugangstest_zeigt_sie_an(self):
        quelle = (Path(__file__).resolve().parent.parent
                  / "jusperfect" / "awstest.py").read_text(encoding="utf-8")
        self.assertIn("Zugangsdaten gefunden: {_maskiert(", quelle)


class DieFormFaelltAuf(unittest.TestCase):
    """Ein abgeschnittener Schlüssel sieht aus wie ein guter.

    Aus der Kanzlei: „Ich habe den Schlüssel von dem anderen Rechner genommen"
    – und AWS meldete „Die Access Key ID kennt AWS nicht". Ein Schlüssel gehört
    zu einem Benutzer, nicht zu einem Rechner; das Übertragen war also richtig.
    Beim Übertragen von Hand geht aber leicht ein Zeichen verloren, und zwei
    Zeichen zu wenig fallen niemandem auf. Die Länge schon.
    """

    def test_die_richtige_form_gibt_keinen_hinweis(self):
        self.assertEqual([], zugang._form_pruefen(
            "Die Access Key ID", KENNUNG, zugang.LAENGE_KENNUNG, ("AKIA", "ASIA")))
        self.assertEqual([], zugang._form_pruefen(
            "Der geheime Schlüssel", GEHEIM, zugang.LAENGE_GEHEIM))

    def test_abgeschnitten_faellt_auf(self):
        hinweise = zugang._form_pruefen("Die Access Key ID", KENNUNG[:-2],
                                        zugang.LAENGE_KENNUNG, ("AKIA", "ASIA"))
        self.assertTrue(any("abgeschnitten" in h for h in hinweise), hinweise)
        self.assertTrue(any("18 Zeichen" in h for h in hinweise), hinweise)

    def test_ein_zeichen_zu_viel_faellt_auch_auf(self):
        hinweise = zugang._form_pruefen("Die Access Key ID", KENNUNG + "X",
                                        zugang.LAENGE_KENNUNG, ("AKIA", "ASIA"))
        self.assertTrue(any("zu viel" in h for h in hinweise), hinweise)

    def test_ein_leerzeichen_darin_faellt_auf(self):
        hinweise = zugang._form_pruefen("Die Access Key ID", KENNUNG[:10] + " " + KENNUNG[11:],
                                        zugang.LAENGE_KENNUNG, ("AKIA", "ASIA"))
        self.assertTrue(any("Leerzeichen" in h for h in hinweise), hinweise)

    def test_der_falsche_vorsatz_faellt_auf(self):
        hinweise = zugang._form_pruefen("Die Access Key ID", "X" * 20,
                                        zugang.LAENGE_KENNUNG, ("AKIA", "ASIA"))
        self.assertTrue(any("AKIA" in h for h in hinweise), hinweise)

    def test_zweimal_die_kennung_wird_abgewiesen(self):
        """Wer beide Werte aus derselben Zeile kopiert, erwischt leicht zweimal
        dieselbe – und der geheime Schlüssel beginnt nie mit AKIA."""
        quelle = (Path(zugang.__file__)).read_text(encoding="utf-8")
        self.assertIn('geheim.startswith(("AKIA", "ASIA"))', quelle)
