"""Aus einer einmaligen Anweisung einen wiederverwendbaren Auftrag vorschlagen.

Aus der Kanzlei: „Ich denke auch einen Wissenstempel bauen, dass sich KI
gleiche Vorgänge merkt. Wie kann dieser Wissenstempel gefüttert werden, kann
die KI entsprechende Vorschläge machen."

Sie kann – und die Form dafür steht bereits im Sicherheitsmodell: Es entsteht
nichts Dauerhaftes ohne ausdrückliche Freigabe durch einen Menschen. Dieser
Dienst macht deshalb nur das eine: **Er schlägt vor.** Angelegt wird die Datei
erst, wenn der Bearbeiter den Text gesehen, bei Bedarf geändert und freigegeben
hat (``Auftragsdienst.anlegen``).

**Die Akte geht dabei nicht mit hinaus.** Das ist keine Sorgfalt im Nachhinein,
sondern der Aufbau: Das Modell bekommt hier weder Passagen noch den Entwurf,
sondern nur die Art des Schreibens, das Rechtsgebiet und die Anweisung, die der
Bearbeiter selbst getippt hat. Ein Vorschlag, der aus dem Entwurf entstünde,
trüge die Tatsachen dieses Mandats – Namen, Beträge, Daten – in eine Datei, die
danach bei *jeder* anderen Akte mitgeht. Das wäre die eine Stelle, an der ein
Wissensspeicher das Mandantengeheimnis über die Mandatsgrenze trägt, und es
geschähe unbemerkt.

Was trotzdem an Tatsachen in der Anweisung selbst steckte, soll das Modell
weglassen; das steht in der Aufgabe. Verlassen wird sich darauf nicht – dafür
ist die Freigabe da.
"""

from __future__ import annotations

from dataclasses import dataclass

from jusperfect.domain.models import Entwurf, Sitzung
from jusperfect.security.identitaet import Identitaet
from jusperfect.services import prompts
from jusperfect.services.ausgang import Ausgang, Ausgangskontext
from jusperfect.services.json_ausgabe import AusgabeUnbrauchbar, json_extrahieren

#: Ein Dateiname, kein Aufsatz.
MAX_TITEL = 60

# Was ein Titel nicht enthalten darf, damit daraus ein Dateiname werden kann.
# Bewusst streng: Der Name geht in einen Pfad, und der Auftragsordner liegt auf
# einem Netzlaufwerk der Kanzlei.
_ERLAUBT = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜäöüß0123456789 -_")


class VorschlagFehler(RuntimeError):
    """Ein Fehler, dessen Text der Kanzlei angezeigt werden darf."""


@dataclass(frozen=True, slots=True)
class Auftragsvorschlag:
    """Ein Vorschlag – noch keine Datei."""

    titel: str
    anweisung: str
    hinweis: str
    dateiname: str

    def als_text(self) -> str:
        """So, wie er in der Datei stünde."""
        return self.anweisung.strip()

    def uebersicht(self) -> dict:
        return {"titel": self.titel, "anweisung": self.anweisung,
                "hinweis": self.hinweis, "dateiname": self.dateiname}


def dateiname(titel: str) -> str:
    """Aus einem Titel einen Dateinamen, der auf jedem Laufwerk trägt."""
    sauber = "".join(z if z in _ERLAUBT else " " for z in titel.strip())
    sauber = " ".join(sauber.split())[:MAX_TITEL].strip(" -_")
    return (sauber or "Eigener Auftrag") + ".txt"


class Vorschlagsdienst:
    def __init__(self, ausgang: Ausgang) -> None:
        self._ausgang = ausgang

    def vorschlagen(self, identitaet: Identitaet, sitzung: Sitzung, entwurf: Entwurf,
                    anweisung: str) -> Auftragsvorschlag:
        """Den Vorschlag holen – ohne der Akte auch nur eine Passage mitzugeben."""
        if not anweisung.strip():
            raise VorschlagFehler(
                "Für einen Vorschlag braucht es die Anweisung, mit der der Entwurf "
                "erstellt wurde. Ohne sie gibt es nichts zu verallgemeinern.")
        aufgabe = prompts.aufgabe_auftragsvorschlag(
            entwurf.art, anweisung, sitzung.akte.rechtsgebiet if sitzung.akte else "")
        kontext = Ausgangskontext(identitaet, sitzung.id, sitzung.akte_id,
                                  "auftragsvorschlag", passagen=0, detail=entwurf.art.value)
        # Material ist leer: Es gibt keins. Genau das ist der Punkt.
        durchgang = self._ausgang.fragen(kontext, prompts.SYSTEM, "", aufgabe)
        try:
            roh = json_extrahieren(durchgang.antwort.text)
        except AusgabeUnbrauchbar as e:
            raise VorschlagFehler(
                "Das Modell hat keinen brauchbaren Vorschlag geliefert.") from e
        titel = str(roh.get("titel", "")).strip()
        vorschlag = str(roh.get("anweisung", "")).strip()
        if not vorschlag:
            raise VorschlagFehler("Das Modell hat keine Anweisung vorgeschlagen.")
        return Auftragsvorschlag(
            titel=titel or "Eigener Auftrag",
            anweisung=vorschlag,
            hinweis=str(roh.get("hinweis", "")).strip(),
            dateiname=dateiname(titel),
        )
