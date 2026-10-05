"""Zwei Mitarbeiter in derselben Akte.

Das Aktengedächtnis gehört der Akte, nicht dem Bearbeiter. Sobald es in AWS
liegt, arbeiten mehrere Personen auf demselben Objekt. Die Frage ist dann
nicht, ob es Zusammenstöße gibt, sondern ob einer davon still etwas verliert.
"""

from __future__ import annotations

import io
import unittest

from jusperfect.domain.models import Aktengedaechtnis, GedaechtnisDokument, Seite
from jusperfect.gedaechtnis.aws import AwsGedaechtnisSpeicher
from jusperfect.gedaechtnis.base import GedaechtnisFehler


class _Vorbedingung(Exception):
    response = {"Error": {"Code": "PreconditionFailed"}}


class _NichtGefunden(Exception):
    response = {"Error": {"Code": "NoSuchKey"}}


class _S3MitBedingung:
    """Ein S3, das IfMatch und IfNoneMatch tatsächlich durchsetzt.

    Das bisherige Testdouble nahm jeden put an. Damit ließ sich prüfen, dass
    die Bedingung mitgeschickt wird – nicht aber, was passiert, wenn sie
    verletzt ist. Genau das ist hier der Fall.
    """

    def __init__(self) -> None:
        self.objekte: dict[tuple[str, str], bytes] = {}
        self.etags: dict[tuple[str, str], str] = {}
        self._zaehler = 0

    def put_object(self, **kw):
        adresse = (kw["Bucket"], kw["Key"])
        vorhanden = self.etags.get(adresse)
        if "IfNoneMatch" in kw and vorhanden is not None:
            raise _Vorbedingung()
        if "IfMatch" in kw and kw["IfMatch"] != vorhanden:
            raise _Vorbedingung()
        self._zaehler += 1
        etag = f'"etag-{self._zaehler}"'
        self.objekte[adresse] = kw["Body"]
        self.etags[adresse] = etag
        return {"ETag": etag}

    def get_object(self, **kw):
        adresse = (kw["Bucket"], kw["Key"])
        if adresse not in self.objekte:
            raise _NichtGefunden()
        return {"Body": io.BytesIO(self.objekte[adresse]), "ETag": self.etags[adresse]}

    def delete_object(self, **kw):
        adresse = (kw["Bucket"], kw["Key"])
        self.objekte.pop(adresse, None)
        self.etags.pop(adresse, None)


def _gedaechtnis(titel: str = "Schreiben") -> Aktengedaechtnis:
    return Aktengedaechtnis(
        akte_id="A/1", aktenzeichen="1/26", bezeichnung="Test",
        dokumente=[GedaechtnisDokument(dokument_id="D1", titel=titel,
                                       seiten=[Seite(nummer=1, text="Inhalt")])],
    )


class ZweiBearbeiter(unittest.TestCase):
    def _speicher(self, s3):
        return AwsGedaechtnisSpeicher("b", "eu-central-1", "kms-1", s3=s3)

    def test_der_zweite_schreiber_wird_abgewiesen_statt_zu_ueberschreiben(self):
        """Der eigentliche Schutz: kein stiller Verlust.

        Beide lesen denselben Stand, beide schreiben. Ohne Bedingung gewänne
        der Letzte, und die Arbeit des Ersten wäre spurlos weg – niemand
        bekäme das mit.
        """
        s3 = _S3MitBedingung()
        weber, kaminski = self._speicher(s3), self._speicher(s3)
        weber.ablegen(_gedaechtnis("Erstes Schreiben"))

        # Beide holen denselben Stand – und schreiben GENAU DEN zurück.
        #
        # Seit dem 05.10.2026 (Befund F03) haengt die erwartete Revision am
        # gelesenen Stand und nicht mehr an einer Tabelle des Speichers. Ein
        # frisch gebautes Gedaechtnis traegt keine und kann deshalb nichts
        # ueberschreiben – auch das ist richtig so, siehe unten.
        weber_stand = weber.lesen("A/1")
        kaminski_stand = kaminski.lesen("A/1")
        self.assertIsNotNone(weber_stand)
        self.assertIsNotNone(kaminski_stand)

        weber_stand.dokumente[0].titel = "Von Weber ergaenzt"
        weber.ablegen(weber_stand)
        kaminski_stand.dokumente[0].titel = "Von Kaminski ergaenzt"
        with self.assertRaises(GedaechtnisFehler) as fehler:
            kaminski.ablegen(kaminski_stand)
        self.assertIn("zwischenzeitlich", str(fehler.exception))

        # Webers Fassung steht noch da – nichts ist verloren gegangen.
        self.assertEqual(weber.lesen("A/1").dokumente[0].titel, "Von Weber ergaenzt")

    def test_derselbe_speicher_schuetzt_zwei_vorgaenge_ebenso(self):
        """Befund F03 der Zweitprüfung vom 05.10.2026, Gegenprobe 15.

        Hier lag die Lücke: **eine** Speicherinstanz, zwei Vorgänge. Der
        Speicher führte eine Tabelle je Objektname. Las der Löschvorgang
        denselben Stand und schrieb zuerst, nahm der ältere Vorgang beim
        Speichern dessen **neue** Revision – und überschrieb damit eine
        Löschung, die er nie gesehen hatte. Das gelöschte Dokument war wieder
        da. Die Bedingung schützte nichts, weil sie nicht mehr zu dem Inhalt
        gehörte, den sie schützen sollte.

        Zwei Fenster auf einem Kanzleirechner sind genau dieser Fall.
        """
        s3 = _S3MitBedingung()
        speicher = self._speicher(s3)
        speicher.ablegen(_gedaechtnis("Erstes Schreiben"))

        alter_lauf = speicher.lesen("A/1")
        loesch_lauf = speicher.lesen("A/1")
        loesch_lauf.dokumente = []
        speicher.ablegen(loesch_lauf)
        self.assertEqual(speicher.lesen("A/1").dokumente, [])

        alter_lauf.bezeichnung = "Später fertige Analyse"
        with self.assertRaises(GedaechtnisFehler):
            speicher.ablegen(alter_lauf)
        # Die Löschung steht – das entfernte Dokument ist nicht zurückgekehrt.
        self.assertEqual(speicher.lesen("A/1").dokumente, [])

    def test_ein_frisch_gebautes_gedaechtnis_ueberschreibt_nichts(self):
        """Ohne gelesene Revision ist es eine Erstanlage, kein Fortschreiben.

        Das ist die strengere Seite derselben Regel: Wer nicht gelesen hat,
        weiß nicht, was er überschreibt.
        """
        s3 = _S3MitBedingung()
        speicher = self._speicher(s3)
        speicher.ablegen(_gedaechtnis("Erstes Schreiben"))
        with self.assertRaises(GedaechtnisFehler):
            speicher.ablegen(_gedaechtnis("Ohne gelesen zu haben"))
        self.assertEqual(speicher.lesen("A/1").dokumente[0].titel, "Erstes Schreiben")

    def test_nach_erneutem_lesen_gelingt_der_zweite_versuch(self):
        """„Bitte Vorgang wiederholen" muss auch wirklich funktionieren."""
        s3 = _S3MitBedingung()
        weber, kaminski = self._speicher(s3), self._speicher(s3)
        weber.ablegen(_gedaechtnis("Erstes Schreiben"))
        kaminski_stand = kaminski.lesen("A/1")
        weber_stand = weber.lesen("A/1")
        weber_stand.dokumente[0].titel = "Von Weber ergaenzt"
        weber.ablegen(weber_stand)
        kaminski_stand.dokumente[0].titel = "Von Kaminski ergaenzt"
        with self.assertRaises(GedaechtnisFehler):
            kaminski.ablegen(kaminski_stand)

        neuer_stand = kaminski.lesen("A/1")         # den neuen Stand holen
        neuer_stand.dokumente[0].titel = "Von Kaminski ergaenzt"
        kaminski.ablegen(neuer_stand)
        self.assertEqual(weber.lesen("A/1").dokumente[0].titel, "Von Kaminski ergaenzt")

    def test_zwei_gleichzeitige_erstanlagen_koennen_nicht_beide_gewinnen(self):
        """Zwei öffnen eine Akte, die noch kein Gedächtnis hat."""
        s3 = _S3MitBedingung()
        weber, kaminski = self._speicher(s3), self._speicher(s3)
        self.assertIsNone(weber.lesen("A/1"))
        self.assertIsNone(kaminski.lesen("A/1"))
        weber.ablegen(_gedaechtnis("Von Weber angelegt"))
        with self.assertRaises(GedaechtnisFehler):
            kaminski.ablegen(_gedaechtnis("Von Kaminski angelegt"))

    def test_nach_dem_loeschen_darf_wieder_angelegt_werden(self):
        """Sonst bliebe die Akte nach einem Abschluss dauerhaft blockiert."""
        s3 = _S3MitBedingung()
        speicher = self._speicher(s3)
        speicher.ablegen(_gedaechtnis())
        speicher.loeschen("A/1")
        speicher.ablegen(_gedaechtnis("Neu begonnen"))
        self.assertEqual(speicher.lesen("A/1").dokumente[0].titel, "Neu begonnen")


if __name__ == "__main__":
    unittest.main()
