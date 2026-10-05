"""Das Aktengedächtnis: dauerhaft, berechtigungsgebunden und belegt."""

from __future__ import annotations

import io
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from jusperfect.domain.models import Akte, Aktengedaechtnis, GedaechtnisDokument, Seite, Sitzung
from jusperfect.gedaechtnis.aws import AwsGedaechtnisSpeicher
from jusperfect.gedaechtnis.lokal import LokalerGedaechtnisSpeicher
from jusperfect.providers.base import Nutzung, ProviderAntwort
from jusperfect.services.gedaechtnis import Gedaechtnisdienst
from tests.hilfen import client, dienste, einstellungen


class SkriptProvider:
    modell_id = "skript"

    def __init__(self, antwort: str) -> None:
        self.antwort = antwort
        self.aufrufe = []

    def fragen(self, system, material, aufgabe, *, max_tokens=8000, modell_id=None):
        self.aufrufe.append({"material": material, "aufgabe": aufgabe, "modell": modell_id})
        return ProviderAntwort(text=self.antwort, nutzung=Nutzung(100, 20), modell=modell_id or self.modell_id)


def _gedaechtnis() -> Aktengedaechtnis:
    return Aktengedaechtnis(
        akte_id="A/1", aktenzeichen="1/26", bezeichnung="Test",
        dokumente=[GedaechtnisDokument(dokument_id="D1", titel="Schreiben", seiten=[Seite(nummer=1, text="Inhalt")])],
    )


class Lokal(unittest.TestCase):
    def test_datei_bleibt_ueber_neue_instanz_erhalten_und_hat_gehashten_namen(self):
        with tempfile.TemporaryDirectory() as tmp:
            erster = LokalerGedaechtnisSpeicher(Path(tmp))
            erster.ablegen(_gedaechtnis())
            dateien = [p for p in Path(tmp).iterdir() if p.is_file()]
            self.assertEqual(len(dateien), 1)
            self.assertTrue(dateien[0].name.endswith(".json.gz"), dateien[0].name)
            self.assertNotIn("A", dateien[0].name)
            zweiter = LokalerGedaechtnisSpeicher(Path(tmp))
            self.assertEqual(zweiter.lesen("A/1").dokumente[0].seiten[0].text, "Inhalt")
            zweiter.loeschen("A/1")
            self.assertIsNone(erster.lesen("A/1"))


class _NichtGefunden(Exception):
    response = {"Error": {"Code": "NoSuchKey"}}


class _S3:
    def __init__(self) -> None:
        self.objekte = {}
        self.put_argumente = None

    def put_object(self, **kwargs):
        self.put_argumente = kwargs
        self.objekte[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]
        return {"ETag": '"etag-neu"'}

    def get_object(self, **kwargs):
        try:
            daten = self.objekte[(kwargs["Bucket"], kwargs["Key"])]
        except KeyError as e:
            raise _NichtGefunden() from e
        return {"Body": io.BytesIO(daten), "ETag": '"etag-neu"'}

    def delete_object(self, **kwargs):
        self.objekte.pop((kwargs["Bucket"], kwargs["Key"]), None)


class Aws(unittest.TestCase):
    def test_s3_nutzt_kms_und_keine_aktenkennung_im_schluessel(self):
        s3 = _S3()
        speicher = AwsGedaechtnisSpeicher("b", "eu-central-1", "kms-1", s3=s3)
        speicher.ablegen(_gedaechtnis())
        self.assertEqual(s3.put_argumente["ServerSideEncryption"], "aws:kms")
        self.assertEqual(s3.put_argumente["SSEKMSKeyId"], "kms-1")
        self.assertNotIn("A/1", s3.put_argumente["Key"])
        self.assertEqual(s3.put_argumente["IfNoneMatch"], "*")
        self.assertEqual(speicher.lesen("A/1").aktenzeichen, "1/26")
        speicher.ablegen(_gedaechtnis())
        self.assertEqual(s3.put_argumente["IfMatch"], '"etag-neu"')
        speicher.loeschen("A/1")
        self.assertIsNone(speicher.lesen("A/1"))


class Ablauf(unittest.TestCase):
    def test_dokument_und_belegte_antwort_werden_am_naechsten_tag_wieder_geladen(self):
        with tempfile.TemporaryDirectory() as tmp:
            e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp)
            d1 = dienste(einstellungen=e, provider=SkriptProvider("Der Mandant fuhr 90 km/h. [Q: D1-S1-P1]"))
            c1 = client(d1)
            sid = c1.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
            c1.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
            antwort = c1.post(f"/api/sitzungen/{sid}/frage", json={"frage": "Welche Geschwindigkeit?"})
            self.assertEqual(antwort.status_code, 200)
            self.assertTrue(antwort.json()["quellen"])
            c1.delete(f"/api/sitzungen/{sid}")

            # Neuer Prozess/Sitzungsspeicher, derselbe dauerhafte Gedächtnisordner.
            d2 = dienste(einstellungen=e)
            r = client(d2).post("/api/sitzungen", json={"akte_id": "VU-2026-0042"})
            self.assertEqual(r.status_code, 201)
            daten = r.json()
            self.assertEqual([x["dokument_id"] for x in daten["sitzung"]["geladen"]], ["D-001"])
            self.assertEqual(daten["gedaechtnis"]["fragen"], 1)
            self.assertEqual(daten["gedaechtnis"]["fragen_antworten"][0]["frage"], "Welche Geschwindigkeit?")
            self.assertEqual(daten["sitzung"]["dialog"][0]["frage"], "Welche Geschwindigkeit?")

    def test_lebenssachverhalt_nutzt_kleines_modell_und_nur_neue_dokumente(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = SkriptProvider("Der Mandant fuhr 90 km/h. [Q: D1-S1-P1]")
            e = einstellungen(
                JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp,
                JUSPERFECT_MODELL_ID="gross", JUSPERFECT_MODELL_ID_KLEIN="klein",
            )
            d = dienste(einstellungen=e, provider=provider)
            c = client(d)
            sid = c.post("/api/sitzungen", json={"akte_id": "VU-2026-0042"}).json()["sitzung"]["id"]
            c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-001"]})
            r = c.post(f"/api/sitzungen/{sid}/gedaechtnis/aktualisieren")
            self.assertEqual(r.status_code, 200)
            self.assertIn("90 km/h", r.json()["lebenssachverhalt"])
            self.assertEqual(r.json()["offene_dokumente"], 0)
            self.assertEqual(provider.aufrufe[0]["modell"], "klein")
            self.assertIn("AUFGABE: AKTENGEDÄCHTNIS", provider.aufrufe[0]["aufgabe"])
            # Ohne neues Dokument kein zweiter Modellaufruf.
            c.post(f"/api/sitzungen/{sid}/gedaechtnis/aktualisieren")
            self.assertEqual(len(provider.aufrufe), 1)

    def test_laufende_akte_stoppt_vorgemerkte_loeschung(self):
        g = _gedaechtnis()
        g.aktenstatus = "abgeschlossen"
        g.retention_reason = "abschlusspruefung_erforderlich"
        g.abgeschlossen_am = datetime.now(timezone.utc)
        g.loeschung_vorgesehen_am = datetime.now(timezone.utc)
        sitzung = Sitzung(
            id="S1", nutzer_id="N1", akte_id="A/1",
            akte=Akte(id="A/1", aktenzeichen="1/26", bezeichnung="Test", status="offen"),
        )

        Gedaechtnisdienst._status_synchronisieren(g, sitzung)

        self.assertEqual(g.aktenstatus, "offen")
        self.assertEqual(g.retention_reason, "laufende_mandatsbearbeitung")
        self.assertIsNone(g.abgeschlossen_am)
        self.assertIsNone(g.loeschung_vorgesehen_am)

    def test_ruhend_und_unbekannt_werden_nicht_als_loeschgrund_behandelt(self):
        self.assertEqual(
            Gedaechtnisdienst._aufbewahrungsgrund("ausgesetzt"),
            "laufendes_verfahren_ruhend",
        )
        self.assertEqual(
            Gedaechtnisdienst._aufbewahrungsgrund("unbekannt"),
            "status_ungeklaert_nicht_loeschen",
        )

    def test_unberechtigter_nutzer_kann_gedaechtnis_nicht_loeschen(self):
        with tempfile.TemporaryDirectory() as tmp:
            e = einstellungen(JUSPERFECT_GEDAECHTNIS="lokal", JUSPERFECT_GEDAECHTNIS_PFAD=tmp)
            d = dienste(einstellungen=e)
            c = client(d)
            sid = c.post("/api/sitzungen", json={"akte_id": "MV-2026-0007"}).json()["sitzung"]["id"]
            c.post(f"/api/sitzungen/{sid}/dokumente", json={"dokument_ids": ["D-101"]})
            fremd = client(d, "refa-lorenz")
            self.assertEqual(fremd.delete("/api/akten/MV-2026-0007/gedaechtnis").status_code, 403)
            self.assertTrue(d.gedaechtnis.lesen("MV-2026-0007").dokumente)


if __name__ == "__main__":
    unittest.main()
