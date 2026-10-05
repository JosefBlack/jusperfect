"""Das Aktengedächtnis liegt gepackt – und bleibt dabei unversehrt.

Aus der Kanzlei: „Problem ist, dass der Serverspeicher sehr teuer ist."

Gepackt wird verlustfrei: Was hineingeht, kommt wieder heraus. Diese Datei
prüft genau das, und zusätzlich die beiden Stellen, an denen so eine Umstellung
sonst still Schaden anrichtet:

* Ein Gedächtnis, das vor der Umstellung entstanden ist, muss weiter lesbar
  sein. Sonst wäre die Arbeit einer Akte verloren, und zwar unbemerkt.
* Nach dem Speichern darf der ungepackte Vorgänger nicht liegen bleiben. Zwei
  Stände desselben Gedächtnisses nebeneinander sind eine Fehlerquelle – und der
  ungepackte ist zugleich der ungeschütztere.
"""

from __future__ import annotations

import gzip
import tempfile
import unittest
from pathlib import Path

from jusperfect.domain.models import (
    Aktengedaechtnis,
    ChronologieEintrag,
    GedaechtnisDokument,
    Seite,
)
from jusperfect.gedaechtnis.base import GedaechtnisFehler
from jusperfect.gedaechtnis.lokal import ENDUNG, ENDUNG_ALT, LokalerGedaechtnisSpeicher
from jusperfect.gedaechtnis.packen import entpacken, ist_gepackt, packen


def _gedaechtnis(akte_id: str = "BA-2026-0044") -> Aktengedaechtnis:
    return Aktengedaechtnis(
        akte_id=akte_id,
        aktenzeichen="44/26 BA",
        bezeichnung="Kettenbach ./. Steinacker Bau GmbH",
        lebenssachverhalt="Die Bauherrin rügte am 20.06.2025 Feuchtigkeit im Keller.",
        dokumente=[GedaechtnisDokument(
            dokument_id="D-008", titel="Mängelanzeige der Bauherrin", nummer=8,
            seiten=[Seite(nummer=1, text="Zur Beseitigung setze ich Ihnen eine Frist "
                                         "bis zum 11.07.2025. " * 40)])],
        chronologie=[ChronologieEintrag(datum="2025-06-20", ereignis="Mängelanzeige")],
    )


class Packen(unittest.TestCase):

    def test_was_hineingeht_kommt_wieder_heraus(self):
        vorher = _gedaechtnis()
        nachher = entpacken(packen(vorher))
        self.assertEqual(vorher.model_dump(), nachher.model_dump())

    def test_es_wird_wirklich_kleiner(self):
        g = _gedaechtnis()
        ungepackt = len(g.model_dump_json().encode("utf-8"))
        gepackt = len(packen(g))
        self.assertLess(gepackt * 2, ungepackt,
                        f"Nur von {ungepackt} auf {gepackt} Byte – das lohnt den Aufwand nicht.")

    def test_dieselben_daten_ergeben_dieselben_bytes(self):
        """Sonst sähe jede Sicherung eine Änderung, wo keine ist."""
        g = _gedaechtnis()
        self.assertEqual(packen(g), packen(g))

    def test_ungepacktes_wird_weiter_gelesen(self):
        roh = _gedaechtnis().model_dump_json().encode("utf-8")
        self.assertFalse(ist_gepackt(roh))
        self.assertEqual("BA-2026-0044", entpacken(roh).akte_id)

    def test_beschaedigtes_paket_sagt_es_deutlich(self):
        kaputt = packen(_gedaechtnis())[:-20]
        with self.assertRaises(GedaechtnisFehler) as fehler:
            entpacken(kaputt)
        self.assertIn("entpacken", str(fehler.exception))


class LokaleAblage(unittest.TestCase):

    def test_abgelegt_wird_gepackt(self):
        with tempfile.TemporaryDirectory() as tmp:
            LokalerGedaechtnisSpeicher(Path(tmp)).ablegen(_gedaechtnis())
            datei = next(Path(tmp).glob("*" + ENDUNG))
            self.assertTrue(ist_gepackt(datei.read_bytes()))

    def test_ein_altes_ungepacktes_gedaechtnis_bleibt_lesbar(self):
        """Der Fall, der sonst still eine Akte verlöre."""
        with tempfile.TemporaryDirectory() as tmp:
            speicher = LokalerGedaechtnisSpeicher(Path(tmp))
            alt = speicher._pfad("BA-2026-0044", ENDUNG_ALT)
            alt.write_text(_gedaechtnis().model_dump_json(), encoding="utf-8")

            gelesen = speicher.lesen("BA-2026-0044")
            self.assertIsNotNone(gelesen)
            self.assertEqual("44/26 BA", gelesen.aktenzeichen)
            self.assertEqual(1, len(speicher.auflisten()))

    def test_beim_speichern_verschwindet_der_ungepackte_vorgaenger(self):
        with tempfile.TemporaryDirectory() as tmp:
            speicher = LokalerGedaechtnisSpeicher(Path(tmp))
            alt = speicher._pfad("BA-2026-0044", ENDUNG_ALT)
            alt.write_text(_gedaechtnis().model_dump_json(), encoding="utf-8")

            speicher.ablegen(speicher.lesen("BA-2026-0044"))

            self.assertFalse(alt.exists(), "Der ungepackte Stand liegt noch da.")
            self.assertTrue(speicher._pfad("BA-2026-0044").exists())
            self.assertEqual(1, len(speicher.auflisten()))

    def test_loeschen_raeumt_beide_formen_weg(self):
        with tempfile.TemporaryDirectory() as tmp:
            speicher = LokalerGedaechtnisSpeicher(Path(tmp))
            speicher._pfad("BA-2026-0044", ENDUNG_ALT).write_text(
                _gedaechtnis().model_dump_json(), encoding="utf-8")
            speicher._pfad("BA-2026-0044").write_bytes(packen(_gedaechtnis()))

            speicher.loeschen("BA-2026-0044")

            self.assertIsNone(speicher.lesen("BA-2026-0044"))
            self.assertEqual([], [p for p in Path(tmp).iterdir() if p.is_file()])

    def test_auflisten_zaehlt_eine_akte_nicht_doppelt(self):
        """Liegen beide Formen vor, gilt die gepackte – sie ist die neuere."""
        with tempfile.TemporaryDirectory() as tmp:
            speicher = LokalerGedaechtnisSpeicher(Path(tmp))
            veraltet = _gedaechtnis()
            veraltet.bezeichnung = "alter Stand"
            speicher._pfad("BA-2026-0044", ENDUNG_ALT).write_text(
                veraltet.model_dump_json(), encoding="utf-8")
            speicher._pfad("BA-2026-0044").write_bytes(packen(_gedaechtnis()))

            liste = speicher.auflisten()
            self.assertEqual(1, len(liste))
            self.assertEqual("Kettenbach ./. Steinacker Bau GmbH", liste[0].bezeichnung)


class AwsAblage(unittest.TestCase):
    """Derselbe Vertrag in S3 – gepackt hingelegt, gekennzeichnet, lesbar zurück."""

    def _speicher(self):
        from jusperfect.gedaechtnis.aws import AwsGedaechtnisSpeicher

        class _S3:
            def __init__(self):
                self.objekte: dict[str, bytes] = {}
                self.argumente: dict | None = None

            def put_object(self, **kw):
                self.argumente = kw
                self.objekte[kw["Key"]] = kw["Body"]
                return {"ETag": '"1"'}

            def get_object(self, Bucket, Key):
                if Key not in self.objekte:
                    class _Fehlt(Exception):
                        response = {"Error": {"Code": "NoSuchKey"}}
                    raise _Fehlt()
                return {"Body": __import__("io").BytesIO(self.objekte[Key]), "ETag": '"1"'}

            def list_objects_v2(self, **kw):
                return {"Contents": [{"Key": k} for k in self.objekte], "IsTruncated": False}

        s3 = _S3()
        return AwsGedaechtnisSpeicher("eimer", "eu-central-1", "kms-1", s3=s3), s3

    def test_gepackt_abgelegt_und_als_solches_gekennzeichnet(self):
        speicher, s3 = self._speicher()
        speicher.ablegen(_gedaechtnis())
        self.assertEqual("gzip", s3.argumente["ContentEncoding"])
        self.assertEqual("aws:kms", s3.argumente["ServerSideEncryption"])
        self.assertTrue(ist_gepackt(s3.argumente["Body"]))

    def test_zurueckgelesen_ist_es_dasselbe(self):
        speicher, _ = self._speicher()
        vorher = _gedaechtnis()
        speicher.ablegen(vorher)
        self.assertEqual(vorher.model_dump_json(),
                         speicher.lesen("BA-2026-0044").model_dump_json())

    def test_ein_altes_ungepacktes_objekt_bleibt_lesbar(self):
        speicher, s3 = self._speicher()
        s3.objekte[speicher._schluessel("BA-2026-0044")] = \
            _gedaechtnis().model_dump_json().encode("utf-8")
        self.assertEqual("44/26 BA", speicher.lesen("BA-2026-0044").aktenzeichen)
        self.assertEqual(1, len(speicher.auflisten()))


class WieVielBringtEs(unittest.TestCase):
    """Eine Zahl zum Vorzeigen, keine Prüfung im engeren Sinn."""

    def test_ersparnis_an_einem_lebensnahen_gedaechtnis(self):
        g = _gedaechtnis()
        g.dokumente[0].seiten[0].text *= 20
        ungepackt = len(g.model_dump_json().encode("utf-8"))
        gepackt = len(packen(g))
        self.assertLess(gepackt, ungepackt // 4)
        self.assertEqual(g.model_dump(), entpacken(gzip.compress(
            g.model_dump_json().encode("utf-8"))).model_dump())


if __name__ == "__main__":
    unittest.main()
