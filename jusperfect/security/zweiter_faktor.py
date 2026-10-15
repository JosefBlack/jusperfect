"""Der zweite Faktor beim Öffnen von jusperfect.

Aus der Folgenabschätzung, Risiko R7 — das einzige, das dort auf **hoch**
steht:

    Die Anmeldung ist im Laufwerks- und Schnittstellenbetrieb **kein
    Kennwort**, sondern eine Kennung. Wer am Rechner sitzt, kann eine andere
    eintragen.

Das ist vertretbar, solange der Rechner selbst geschützt ist — und es trägt
nicht mehr, sobald ein Arbeitsplatz unbeaufsichtigt entsperrt bleibt. Dann
öffnet jeder jede Akte unter fremdem Namen, und der Nutzungsnachweis nennt
den Falschen.

**Was dieses Modul leistet und was nicht.** Es setzt einen zweiten Faktor vor
das Programm: ein Einmalkennwort aus einer Authentifizierungs-App (TOTP nach
RFC 6238 — dieselbe Technik wie bei AWS, der Bank und dem beA). Es ersetzt
nicht den Schutz des Windows-Kontos; es sorgt dafür, dass ein unbeaufsichtigter
Rechner allein nicht genügt, um Mandatsakten zu öffnen.

**Freiwillig, und mit Absicht.** Voreingestellt ist „aus": Eine Kanzlei, die
mit einem geschützten Einzelplatz arbeitet, soll nicht zu einem zweiten Gerät
gezwungen werden. Wer ihn einschaltet, schaltet ihn für alle ein.

**Ohne fremde Bibliothek.** TOTP ist ein HMAC über einen Zähler; das sind
zwanzig Zeilen. Eine Abhängigkeit mehr in einem Programm, das Mandatsakten
verarbeitet, wiegt schwerer als zwanzig Zeilen, die man lesen kann.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

#: Sekunden je Zeitschritt. 30 ist der Wert, den alle Apps voreinstellen.
SCHRITT = 30
#: Stellen des Einmalkennworts.
STELLEN = 6
#: Wie viele Schritte vor und zurück noch gelten. Eine Uhr, die um zwanzig
#: Sekunden abweicht, ist in einer Kanzlei der Normalfall und kein Angriff.
FENSTER = 1


class ZweiterFaktorFehler(PermissionError):
    """Der zweite Faktor fehlt oder stimmt nicht."""


def geheimnis_erzeugen() -> str:
    """Ein neues Geheimnis, Base32 ohne Füllzeichen — so wollen es die Apps."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _code(geheimnis: str, zaehler: int) -> str:
    roh = base64.b32decode(geheimnis.upper() + "=" * (-len(geheimnis) % 8))
    marke = hmac.new(roh, struct.pack(">Q", zaehler), hashlib.sha1).digest()
    stelle = marke[-1] & 0x0F
    zahl = struct.unpack(">I", marke[stelle:stelle + 4])[0] & 0x7FFFFFFF
    return str(zahl % (10 ** STELLEN)).zfill(STELLEN)


def code_jetzt(geheimnis: str, jetzt: float | None = None) -> str:
    """Das Einmalkennwort dieses Augenblicks – für Einrichtung und Prüfung."""
    return _code(geheimnis, int((jetzt if jetzt is not None else time.time()) // SCHRITT))


def code_pruefen(geheimnis: str, eingabe: str, jetzt: float | None = None) -> bool:
    """Stimmt die Eingabe – mit einem Schritt Nachsicht in beide Richtungen.

    Verglichen wird mit `compare_digest`: Ein Vergleich, der beim ersten
    falschen Zeichen abbricht, verrät über die Laufzeit, wie weit man gekommen
    ist. Bei sechs Stellen ist das keine große Hilfe für einen Angreifer —
    aber es kostet nichts, es richtig zu machen.
    """
    ziffern = "".join(z for z in (eingabe or "") if z.isdigit())
    if len(ziffern) != STELLEN:
        return False
    schritt = int((jetzt if jetzt is not None else time.time()) // SCHRITT)
    for versatz in range(-FENSTER, FENSTER + 1):
        if hmac.compare_digest(_code(geheimnis, schritt + versatz), ziffern):
            return True
    return False


def einrichtungslink(nutzer_id: str, geheimnis: str,
                     herausgeber: str = "jusperfect") -> str:
    """Der ``otpauth:``-Link, den die App einliest.

    Er enthält das Geheimnis. Er wird **einmal** angezeigt und nirgends
    abgelegt — weder im Protokoll noch im Nachweis.
    """
    kennung = quote(f"{herausgeber}:{nutzer_id}")
    return (f"otpauth://totp/{kennung}?secret={geheimnis}"
            f"&issuer={quote(herausgeber)}&digits={STELLEN}&period={SCHRITT}")


@dataclass
class Bestaetigungen:
    """Wer den zweiten Faktor in dieser Programmsitzung schon gezeigt hat.

    Im Arbeitsspeicher und nicht auf der Platte: Ein Neustart des Programms
    verlangt den Faktor erneut, und das ist gewollt. Eine Bestätigung, die
    einen Neustart überlebt, ist beim nächsten Einschalten des Rechners wieder
    da — und dann schützt sie vor genau dem nicht mehr, wogegen sie gebaut ist.
    """

    gueltig_sekunden: int = 12 * 3600
    _bis: dict[str, float] = field(default_factory=dict)
    #: Gegen Wiedereinspielung: Ein Einmalkennwort gilt einmal.
    _verbraucht: dict[str, float] = field(default_factory=dict)

    def bestaetigen(self, nutzer_id: str, code: str, jetzt: float | None = None) -> None:
        t = jetzt if jetzt is not None else time.time()
        self._bis[nutzer_id] = t + self.gueltig_sekunden
        self._verbraucht[f"{nutzer_id}:{code}"] = t + SCHRITT * (FENSTER + 1)

    def schon_benutzt(self, nutzer_id: str, code: str, jetzt: float | None = None) -> bool:
        t = jetzt if jetzt is not None else time.time()
        self._aufraeumen(t)
        return self._verbraucht.get(f"{nutzer_id}:{code}", 0) > t

    def gilt(self, nutzer_id: str, jetzt: float | None = None) -> bool:
        t = jetzt if jetzt is not None else time.time()
        self._aufraeumen(t)
        return self._bis.get(nutzer_id, 0) > t

    def zuruecknehmen(self, nutzer_id: str) -> None:
        self._bis.pop(nutzer_id, None)

    def _aufraeumen(self, jetzt: float) -> None:
        for k in [k for k, v in self._bis.items() if v <= jetzt]:
            del self._bis[k]
        for k in [k for k, v in self._verbraucht.items() if v <= jetzt]:
            del self._verbraucht[k]


@dataclass
class Geheimnisablage:
    """Die Geheimnisse der Nutzer – eine Datei neben der Nutzerdatei.

    **Nicht in der Nutzerdatei selbst**, und das ist keine Geschmacksfrage:
    Die Nutzerdatei wird von Hand gepflegt, liegt in der Sicherung und wandert
    zwischen Rechnern. Ein Geheimnis, das den zweiten Faktor trägt, hat darin
    nichts zu suchen.

    Die Datei ist zu schützen wie ein Schlüssel. Wer sie liest, kann die
    Einmalkennwörter aller Nutzer erzeugen — dann bleibt nur noch der erste
    Faktor, und der ist in dieser Betriebsart eine Kennung.
    """

    pfad: Path

    def _alle(self) -> dict[str, str]:
        if not self.pfad.exists():
            return {}
        try:
            roh = json.loads(self.pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return {str(k): str(v) for k, v in (roh.get("geheimnisse") or {}).items()}

    def geheimnis(self, nutzer_id: str) -> str | None:
        return self._alle().get(nutzer_id)

    def eingerichtet(self, nutzer_id: str) -> bool:
        return bool(self.geheimnis(nutzer_id))

    def merken(self, nutzer_id: str, geheimnis: str) -> None:
        alle = self._alle()
        alle[nutzer_id] = geheimnis
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        self.pfad.write_text(json.dumps({"geheimnisse": alle}, indent=2, ensure_ascii=False),
                             encoding="utf-8")
        # Nur der Eigentuemer darf lesen. Unter Windows wirkt das nicht; dort
        # traegt der Ordner den Schutz. Gesagt ist es trotzdem.
        try:
            self.pfad.chmod(0o600)
        except OSError:
            pass

    def vergessen(self, nutzer_id: str) -> None:
        alle = self._alle()
        if alle.pop(nutzer_id, None) is None:
            return
        self.pfad.write_text(json.dumps({"geheimnisse": alle}, indent=2, ensure_ascii=False),
                             encoding="utf-8")
