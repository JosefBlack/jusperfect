"""Schnittstelle zu jur|nodes.

jur|nodes ist die Single Source of Truth. jusperfect liest über diese
Schnittstelle bedarfsbezogen – nie die ganze Kanzlei, nie dauerhaft – und
schreibt zurück: einen Aktenvermerk oder Entwurf, den ein Mensch ausdrücklich
freigegeben hat. Löschen gibt es dort nicht.

Daneben steht seit der Entscheidung der Kanzlei ein zweiter, eng begrenzter
Schreibweg: **genau eine eigene Datei je Akte, das Aktengedächtnis.** Nur diese
eine Datei darf jusperfect ohne Einzelfreigabe anlegen, überschreiben und
löschen. Sie trägt einen festen Namen, den der Aufrufer nicht wählen kann –
über diesen Weg kann deshalb nichts anderes in die Akte gelangen. Auf alle
übrigen Inhalte der Akte bleibt der Zugriff lesend.

Phase 0 des Konzepts prüft genau diese sechs Funktionen gegen die echte API:
Akte suchen, Akte lesen, Dokumentliste, Dokument laden, Beteiligte, Fristen.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from jusperfect.domain.models import Akte, Beteiligter, Dokument, Frist
from jusperfect.security.approval import Freigabe


class JurNodesFehler(RuntimeError):
    """Ein Fehler, dessen Text der Kanzlei angezeigt werden darf.

    ``serverwort`` traegt zusaetzlich den Wortlaut, den jur|nodes der
    Abweisung beigelegt hat. Er wird **nicht** angezeigt: Er kommt von einem
    fremden Server, niemand liest ihn vorher, und im Alltag stehen echte
    Akten daneben. Nur die Proben holen ihn sich hier ab - dort ist er die
    einzige Auskunft, die eine Ratepartie beendet.

    So mit der Kanzlei entschieden am 25.09.2026.
    """

    def __init__(self, *args: object, serverwort: str = "") -> None:
        super().__init__(*args)
        self.serverwort = serverwort


class AkteNichtGefunden(JurNodesFehler):
    pass


class DokumentNichtGefunden(JurNodesFehler):
    pass


def serverwort(antwort: Any, grenze: int = 200) -> str:
    """Was der Server zu einer Abweisung sagt - im Wortlaut.

    jur|nodes legt jeder Abweisung einen Satz bei: im Feld ``error``, bei
    einer 400 auch ``message`` und ``errorStrings``. Bis zum 25.09.2026
    druckte diese Probe nur "Status 405" und warf den Satz weg.

    Genau der hätte zwei Tage gespart. **405 heißt bei diesem Hersteller
    nicht "diesen Weg gibt es nicht", sondern "ungültige Eingabe"** - so
    steht es 94mal in seiner eigenen Beschreibung und keinmal anders. Wer
    die Zahl nach der Norm liest, sucht den Pfad, und der war die ganze
    Zeit richtig.

    Nur die Probe zeigt den Satz. Im Alltag bleibt er aus: Er kommt von
    einem fremden Server, niemand liest ihn vorher, und dort arbeitet das
    Programm mit echten Akten. So entschieden am 25.09.2026.
    """
    try:
        daten = antwort.json()
    except Exception:
        daten = None
    stuecke: list[str] = []
    if isinstance(daten, Mapping):
        for feld in ("error", "message"):
            wert = daten.get(feld)
            if isinstance(wert, str) and wert.strip():
                stuecke.append(wert.strip())
        einzeln = daten.get("errorStrings")
        if isinstance(einzeln, list):
            stuecke += [s.strip() for s in einzeln if isinstance(s, str) and s.strip()]
    if not stuecke:
        # Kein JSON oder keines der bekannten Felder: der nackte Text, soweit
        # er wie Text aussieht. Eine HTML-Seite hilft niemandem.
        roh = (getattr(antwort, "text", "") or "").strip()
        if roh and not roh.lstrip().startswith("<"):
            stuecke.append(roh)
    if not stuecke:
        return ""
    satz = " | ".join(stuecke)
    # Zeilenumbrueche wuerden die Ausrichtung des Befundes zerreissen.
    satz = " ".join(satz.split())
    if len(satz) > grenze:
        satz = satz[:grenze - 1] + "…"
    return satz



# Der Name der einen Datei, die jusperfect in der Akte führen darf.
#
# "Die Kanzlei will sie sehen, nicht suchen" - deshalb muss sie im Ordner ganz
# oben stehen. Die naheliegende Loesung, ein fuehrender Unterstrich, taugt
# dafuer nicht: Er steht in der einfachen Sortierung HINTER den Ziffern und
# landete in der grossen Testakte auf Platz 51 von 52. Ziffern stehen dagegen
# in jeder Sortierung vorn, und "00" vor jeder anderen Nummer.
#
# Geschrieben ohne Umlaut, damit die Datei ueber ein eingebundenes
# Netzlaufwerk zuverlaessig wiedergefunden wird: Verschiedene Systeme
# verschluesseln Umlaute unterschiedlich, und eine Datei, die das Programm
# nicht mehr findet, waere die Arbeit einer ganzen Akte.
GEDAECHTNIS_DATEI = "00_Aktengedaechtnis.json.gz"

#: Der Stamm, den jede Fassung traegt, und die Endung dahinter.
GEDAECHTNIS_STAMM = "00_Aktengedaechtnis"
GEDAECHTNIS_ENDUNG = ".json.gz"


def gedaechtnis_dateiname(zeitpunkt: datetime | None = None) -> str:
    """Der Name der Fassung, die jetzt abgelegt wird.

    **Warum nicht mehr der eine feste Name:** jur|nodes ersetzt eine
    vorhandene Datei nicht - es weist sie ab (405, "Der ausgewaehlte
    Dateiname wird bereits verwendet", gemessen am 25.09.2026). Gesichert
    wird aber bei jedem Sitzungsende. Ohne Loeschrecht, das die Kanzlei
    bewusst nicht erteilt, bleibt nur: jede Fassung bekommt einen eigenen
    Namen.

    **Warum der Zeitstempel von uns kommt und nicht vom Server:** jur|nodes
    kann selbst umbenennen (``autoRenameIfExist``), aber WIE es das tut,
    steht nirgends. Ein Name, den wir nicht kennen, ist ein Name, den wir
    spaeter nicht wiederfinden - und das Wiederfinden ist der ganze Zweck.
    Was wir selbst vergeben, kennen wir.

    Der Name bleibt fest gebaut und ist **von aussen nicht waehlbar**: Stamm,
    Zeitpunkt, Endung. Ueber diesen Weg kann deshalb weiterhin nichts anderes
    in die Akte gelangen.

    Der Zeitstempel ist so geschrieben, dass er sich sortieren laesst - und
    ohne Doppelpunkte, die in Dateinamen unter Windows nicht zulaessig sind.
    """
    wann = zeitpunkt or datetime.now(timezone.utc)
    return f"{GEDAECHTNIS_STAMM}-{wann.strftime('%Y%m%d-%H%M%S')}{GEDAECHTNIS_ENDUNG}"


def gedaechtnis_stand(dateiname: str) -> str:
    """Der Zeitstempel einer Fassung - oder "" fuer die alte, feste.

    Nach diesem Wert wird sortiert. Die alte Datei ohne Zeitstempel gilt als
    die aelteste: Sie stammt aus der Zeit vor dieser Umstellung.

    **Nicht nach dem Dateinamen sortieren.** "-" steht im Zeichensatz vor
    ".", also stuende "00_Aktengedaechtnis-20260925....gz" VOR
    "00_Aktengedaechtnis.json.gz" - und die aelteste Datei waere die
    juengste. Solche Fehler fallen erst auf, wenn Arbeit verloren ist.
    """
    name = dateiname.strip()
    if not name.startswith(GEDAECHTNIS_STAMM):
        return ""
    rest = name[len(GEDAECHTNIS_STAMM):]
    if not rest.startswith("-"):
        return ""
    stempel = rest[1:]
    for endung in (GEDAECHTNIS_ENDUNG, ".gz", ".json"):
        if stempel.endswith(endung):
            stempel = stempel[:-len(endung)]
            break
    return stempel


def ist_gedaechtnis_datei(dateiname: str) -> bool:
    """Gehoert diese Datei zum Aktengedaechtnis?

    Sowohl die alte feste Fassung als auch jede mit Zeitstempel. Andere
    Dateien der Akte werden dabei nicht getroffen: Der Stamm steht fest, und
    hinter ihm darf nur ein Bindestrich mit Zeitstempel folgen.
    """
    name = dateiname.strip()
    if name == GEDAECHTNIS_DATEI:
        return True
    if not name.startswith(GEDAECHTNIS_STAMM + "-"):
        return False
    stempel = gedaechtnis_stand(name)
    # Nur Ziffern und ein Bindestrich - sonst ist es eine fremde Datei, die
    # zufaellig so anfaengt.
    return bool(stempel) and all(z.isdigit() or z == "-" for z in stempel)


@runtime_checkable
class JurNodesAdapter(Protocol):
    def akten_suchen(self, suchbegriff: str = "") -> list[Akte]: ...
    def akte(self, akte_id: str) -> Akte: ...
    def dokumente(self, akte_id: str) -> list[Dokument]: ...
    def dokument_laden(self, akte_id: str, dokument_id: str) -> tuple[Dokument, bytes]: ...
    def beteiligte(self, akte_id: str) -> list[Beteiligter]: ...
    def fristen(self, akte_id: str) -> list[Frist]: ...
    def vermerk_schreiben(self, akte_id: str, titel: str, text: str, freigabe: Freigabe) -> str:
        """Legt einen Vermerk/Entwurf in der Akte ab und gibt dessen Kennung zurück.

        Ohne gültige ``Freigabe`` darf keine Implementierung schreiben.
        """
        ...

    # ── Das Aktengedächtnis in der Akte ─────────────────────────────────────
    # Rohe Bytes, keine Fachobjekte: Der Adapter soll nicht wissen muessen, was
    # in der Datei steht. Was hineingehoert, entscheidet der Gedaechtnisdienst.

    def gedaechtnis_lesen(self, akte_id: str) -> bytes | None:
        """Den Inhalt von ``GEDAECHTNIS_DATEI`` oder ``None``, wenn es sie nicht gibt."""
        ...

    def gedaechtnis_ablegen(self, akte_id: str, rohdaten: bytes) -> None:
        """Schreibt ``GEDAECHTNIS_DATEI`` in die Akte – ohne Einzelfreigabe."""
        ...

    def gedaechtnis_loeschen(self, akte_id: str) -> None:
        """Entfernt ``GEDAECHTNIS_DATEI`` aus der Akte. Fehlt sie, ist nichts zu tun."""
        ...
