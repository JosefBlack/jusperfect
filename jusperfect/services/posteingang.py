"""Posteingang: eingehende Dokumente vorbereiten – der Mensch entscheidet.

Der Dienst hält den beobachteten Ordner im Blick und bereitet jede vollständig
übertragene Datei vor: Text herauslösen, als Vorgang bereitstellen. Mehr nicht.
Öffnen, prüfen und einordnen bleibt Sache eines Menschen (siehe
``services/watchfolder.py``).

Der Stand liegt bewusst im Arbeitsspeicher des Prozesses – wie schon bei
Perfect Shield der Fall des Aufrufers. Das passt zum lokalen Dauerbetrieb, für
den ein beobachteter Ordner überhaupt gedacht ist (ein eingebundenes
Cloud-Laufwerk auf dem Kanzleirechner). In einer zustandslosen Lambda ergäbe
ein Ordner keinen Sinn; dort wäre der Weg ein S3-Ereignis, das eine eigene
Vorbereitung anstößt – ein anderer Mechanismus, hier absichtlich nicht gebaut.

Ein Vorgang trägt den Dateinamen (der im Ordner ohnehin sichtbar ist) und den
herausgelösten Text. Der Text bleibt im Prozess und läuft mit der
Sitzungsfrist ab; nach draußen geht aus dem Posteingang nur, was Umfang und
Herkunft beschreibt – nie der Inhalt.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from jusperfect.config import Einstellungen
from jusperfect.domain.models import Akte, Dokument, Passage, Seite, Sitzung
from jusperfect.ocr.base import OcrDienst, OcrFehler
from jusperfect.security.identitaet import Identitaet
from jusperfect.security.protokoll import ereignis, protokoll
from jusperfect.services.extraktion import NichtUnterstuetzt, text_extrahieren
from jusperfect.services.passagen import passagen_bilden
from jusperfect.services.watchfolder import (
    GeseheneDatei, scan, status_schreiben, status_text,
)

_log = protokoll("posteingang")

# Nur Dateitypen, aus denen die Extraktion Text holen kann. Ausführbares und
# Unbekanntes bleibt liegen; der Ordner gehört der Kanzlei.
ENDUNGEN = frozenset({".pdf", ".docx", ".txt", ".md", ".csv", ".png", ".jpg", ".jpeg", ".tif", ".tiff"})

# So lange darf ein vorbereiteter Vorgang unberührt liegen, bevor er verfällt –
# wie die Dokumenttexte einer Sitzung. Der Posteingang ist keine Parallelakte.
VORGANG_TTL_SEKUNDEN = 24 * 3600

# So viele Verwerfungen bleiben für ein Rückgängig liegen. Klein gehalten: Das
# ist eine Rücklage für den Fehlgriff von eben, kein Papierkorb.
RUECKLAGE = 5


class PosteingangFehler(RuntimeError):
    pass


@dataclass(slots=True)
class _Vorgang:
    id: str
    dateiname: str
    groesse: int
    seiten: list[Seite]
    ocr: bool
    erkannt_am: str
    erstellt: float  # Uhr-Zeitpunkt für den Ablauf

    @property
    def zeichen(self) -> int:
        return sum(len(s.text) for s in self.seiten)

    def uebersicht(self) -> dict:
        """Was über einen Vorgang nach außen darf – ohne Inhalt."""
        return {
            "id": self.id, "dateiname": self.dateiname, "groesse": self.groesse,
            "seiten": len(self.seiten), "zeichen": self.zeichen, "ocr": self.ocr,
            "erkannt_am": self.erkannt_am,
        }


class Posteingangsdienst:
    def __init__(self, einstellungen: Einstellungen, ocr: OcrDienst,
                 uhr=time.monotonic) -> None:
        self._e = einstellungen
        self._ocr = ocr
        self._uhr = uhr
        self._ordner = Path(einstellungen.posteingang_ordner) if einstellungen.posteingang_ordner else None
        self._gesehen: dict[str, GeseheneDatei] = {}
        self._verarbeitet: set[str] = set()
        self._vorgaenge: dict[str, _Vorgang] = {}
        # Verworfenes wartet hier auf ein mögliches Rückgängig - siehe verwerfen().
        self._verworfen: dict[str, _Vorgang] = {}
        self._fehler: dict[str, str] = {}
        self._geprueft_am: datetime | None = None
        self._sperre = threading.Lock()

    @property
    def aktiv(self) -> bool:
        return self._ordner is not None

    # ── Durchgang ──────────────────────────────────────────────────────────

    def pruefen(self) -> dict:
        """Einmal durch den Ordner: fertige Dateien vorbereiten, Status schreiben."""
        if self._ordner is None:
            raise PosteingangFehler("Es ist kein Posteingang-Ordner eingerichtet (JUSPERFECT_POSTEINGANG_ORDNER).")
        try:
            self._ordner.mkdir(parents=True, exist_ok=True)
            durchgang = scan(self._ordner, ENDUNGEN, self._gesehen,
                             frozenset(self._verarbeitet), self._uhr())
        except OSError as e:
            raise PosteingangFehler("Der Posteingang-Ordner ist nicht erreichbar. Ist das Laufwerk verbunden?") from e
        with self._sperre:
            self._gesehen = durchgang.gesehen
            self._aufraeumen_gesperrt()
            for datei in durchgang.bereit:
                self._vorbereiten_gesperrt(datei)
            self._geprueft_am = datetime.now(timezone.utc)
            wartend = len(durchgang.wartend)
        status_schreiben(self._ordner, status_text(
            self._ordner, len(self._vorgaenge), wartend, dict(self._fehler),
            self._geprueft_am or datetime.now(timezone.utc)))
        return self.uebersicht(wartend=wartend)

    def _vorbereiten_gesperrt(self, datei: Path) -> None:
        self._verarbeitet.add(datei.name)  # jede Datei nur einmal, ob sie taugt oder nicht
        try:
            daten = datei.read_bytes()
        except OSError as e:
            self._fehler[datei.name] = f"nicht lesbar ({type(e).__name__})"
            return
        eid = uuid.uuid4().hex[:12]
        dokument = Dokument(id=eid, akte_id="posteingang", titel=datei.name, dateiname=datei.name)
        try:
            seiten, ocr = text_extrahieren(dokument, daten, self._ocr, "posteingang")
        except (NichtUnterstuetzt, OcrFehler) as e:
            self._fehler[datei.name] = str(e)
            ereignis(_log, "posteingang_uebersprungen", datei_kennung=eid, grund=type(e).__name__)
            return
        finally:
            del daten
        if sum(len(s.text) for s in seiten) == 0:
            self._fehler[datei.name] = "kein erkennbarer Text"
            return
        self._fehler.pop(datei.name, None)
        self._vorgaenge[eid] = _Vorgang(
            id=eid, dateiname=datei.name, groesse=datei.stat().st_size if datei.exists() else 0,
            seiten=seiten, ocr=ocr, erkannt_am=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            erstellt=self._uhr())
        ereignis(_log, "posteingang_vorbereitet", datei_kennung=eid, seiten=len(seiten), ocr=ocr)

    def _aufraeumen_gesperrt(self) -> None:
        jetzt = self._uhr()
        verfallen = [eid for eid, v in self._vorgaenge.items() if jetzt - v.erstellt >= VORGANG_TTL_SEKUNDEN]
        for eid in verfallen:
            del self._vorgaenge[eid]
        # Die Rücklage läuft nach derselben Frist ab. Sie ist eine Bequemlichkeit
        # und darf Aktentext nicht länger halten als der Posteingang selbst.
        for eid in [eid for eid, v in self._verworfen.items() if jetzt - v.erstellt >= VORGANG_TTL_SEKUNDEN]:
            del self._verworfen[eid]

    # ── Auskunft und Zugriff ─────────────────────────────────────────────────

    def uebersicht(self, wartend: int = 0) -> dict:
        with self._sperre:
            self._aufraeumen_gesperrt()
            eintraege = [v.uebersicht() for v in sorted(self._vorgaenge.values(),
                                                        key=lambda v: v.erkannt_am, reverse=True)]
            fehler = dict(self._fehler)
        return {
            "aktiv": self.aktiv, "ordner": str(self._ordner) if self._ordner else "",
            "eintraege": eintraege, "wartend": wartend, "fehler": fehler,
            "geprueft_am": self._geprueft_am.isoformat(timespec="seconds") if self._geprueft_am else None,
        }

    def _holen(self, eintrag_id: str) -> _Vorgang:
        with self._sperre:
            self._aufraeumen_gesperrt()
            vorgang = self._vorgaenge.get(eintrag_id)
        if vorgang is None:
            raise PosteingangFehler("Der Vorgang ist unbekannt oder abgelaufen. Bitte den Posteingang erneut prüfen.")
        return vorgang

    def passagen(self, eintrag_id: str) -> list[Passage]:
        vorgang = self._holen(eintrag_id)
        dokument = Dokument(id=vorgang.id, akte_id="posteingang", titel=vorgang.dateiname, dateiname=vorgang.dateiname)
        return passagen_bilden(1, dokument, vorgang.seiten)

    def als_sitzung(self, identitaet: Identitaet, eintrag_id: str) -> tuple[Sitzung, list[Passage]]:
        """Ein vorbereiteter Vorgang als flüchtige Sitzung für die Eingangsprüfung.

        Die Sitzung wird nicht gespeichert; sie ist nur das Gefäß, mit dem die
        vorhandene Triage einen losen Eingang lesen kann. Eine Akte in jur|nodes
        entsteht dadurch nicht – der Eingang ist noch nicht eingeordnet.
        """
        vorgang = self._holen(eintrag_id)
        akte = Akte(id="posteingang", aktenzeichen="Posteingang", bezeichnung=vorgang.dateiname)
        sitzung = Sitzung(id=f"posteingang-{vorgang.id}", nutzer_id=identitaet.nutzer_id,
                          akte_id="posteingang", akte=akte)
        return sitzung, self.passagen(eintrag_id)

    def verwerfen(self, eintrag_id: str) -> None:
        """Einen vorbereiteten Vorgang aus dem Blick nehmen – ohne die Datei anzurühren.

        Die Datei im Ordner bleibt unberührt (der Ordner gehört der Kanzlei);
        sie bleibt nur als „verarbeitet" vermerkt, damit sie nicht gleich wieder
        eingelesen wird.

        Der Vorgang wird nicht sofort weggeworfen, sondern beiseitegelegt: Ein
        Fehlgriff im Posteingang ist schnell passiert, und ohne diese Rücklage
        müsste die Datei erst wieder aus dem Ordner eingelesen und – bei einem
        Scan – erneut durch die Texterkennung geschickt werden. Das kostet Zeit
        und, bei Textract, Geld.

        Die Rücklage ist bewusst kurz und klein: Sie ist ein Rückgängig, kein
        Papierkorb. Ein Vorgang trägt Aktentext; er darf nicht laenger liegen
        als er ohnehin duerfte.
        """
        with self._sperre:
            vorgang = self._vorgaenge.pop(eintrag_id, None)
            if vorgang is not None:
                self._verworfen[eintrag_id] = vorgang
                self._ruecklage_kuerzen_gesperrt()

    def zurueckholen(self, eintrag_id: str) -> dict:
        """Ein Verwerfen rückgängig machen.

        Gibt die Übersicht des wiederhergestellten Vorgangs zurück, damit die
        Oberfläche sagen kann, was zurückgekommen ist.
        """
        with self._sperre:
            self._aufraeumen_gesperrt()
            vorgang = self._verworfen.pop(eintrag_id, None)
            if vorgang is None:
                raise PosteingangFehler(
                    "Der Vorgang lässt sich nicht mehr zurückholen. Er ist abgelaufen "
                    "oder wurde inzwischen überschrieben. Der Posteingang liest die "
                    "Datei beim nächsten Blick in den Ordner erneut ein.")
            self._vorgaenge[eintrag_id] = vorgang
            return vorgang.uebersicht()

    def _ruecklage_kuerzen_gesperrt(self) -> None:
        """Nur die letzten Verwerfungen behalten – ältere fallen heraus."""
        while len(self._verworfen) > RUECKLAGE:
            # dict behält die Einfügereihenfolge: das älteste steht vorn.
            self._verworfen.pop(next(iter(self._verworfen)))
