"""Der Selbsttest beim Start: Stehen die Absicherungen?

Aus der Kanzlei: „ein Testlauf beim Start des Programms mit Hinweis auf den
Testablauf, was gerade gemacht wird."

Bisher liefen die Prüfungen still. Ging nichts schief, sah man nichts – und
„nichts gesehen" ist bei einer Absicherung keine Auskunft, sondern nur die
Abwesenheit einer Beschwerde. Wer am Montag eine echte Akte öffnet, will
schwarz auf weiß lesen, dass die Region in Europa liegt, dass AWS nichts
mitschreibt und dass die Kostenbremse steht.

**Dieser Test kostet nichts und schickt keinen Aktentext hinaus.** Er fragt die
eigenen Einstellungen, den Aktenzugang und zwei Verwaltungsauskünfte bei AWS ab.
Er ruft **kein Modell auf**: Das kostet Geld, und mit mehreren eingebundenen
Modellen kostete es bei jedem Start ein Vielfaches. Ob ein Modell wirklich
antwortet, ist deshalb ein eigener, ausdrücklicher Handgriff
(``modelle_anprobieren``) – mit dem Preis dabei.

**Mehrere Modelle.** jusperfect kann je Funktion ein eigenes Modell benutzen –
ein kleines schnelles für die Eingangsprüfung, ein starkes für die Analyse. Der
Selbsttest zeigt sie deshalb nicht als eine Zeile, sondern als Liste: welches
Modell welche Arbeit tut, und ob die Zugriffsrichtlinie der Kanzlei es
überhaupt abdeckt. Ein Modell, das die Richtlinie nicht kennt, wird beim ersten
Aufruf abgewiesen – das soll im Startbild stehen und nicht mitten in der Arbeit
auffallen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from jusperfect.config import Einstellungen
from jusperfect.modellprotokoll import AN, AUS, Befund

#: Alles in Ordnung.
GUT = "gut"
#: Kein Fehler, aber eine offene Frage – der Fall, den man sonst übersieht.
OFFEN = "offen"
#: Etwas stimmt nicht.
SCHLECHT = "schlecht"
#: Trifft in diesem Betrieb nicht zu (z. B. AWS-Punkte im Demo-Betrieb).
ENTFAELLT = "entfaellt"
#: Ließe sich prüfen, kostet aber – also nur auf Knopfdruck.
UNGEPRUEFT = "ungeprueft"

FUNKTION_NAME = {
    "frage": "Fragen",
    "analyse": "Analyse",
    "triage": "Eingangsprüfung",
    "entwurf": "Entwürfe",
    "gedaechtnis": "Gedächtnis",
}

# Was die Zugriffsrichtlinie der Kanzlei abdeckt (infra/iam-nur-claude.json):
# Claude von Anthropic, unmittelbar oder über das europäische Inferenzprofil.
_GEDECKT = re.compile(r"^(eu\.)?anthropic\.claude-")
_ARN_PROFIL = re.compile(r"^arn:aws:bedrock:eu-[a-z0-9-]+:\d+:inference-profile/eu\.anthropic\.claude-")


@dataclass(frozen=True, slots=True)
class Punkt:
    """Eine Zeile im Startbild – in ganzen Sätzen, nicht als Code."""

    schluessel: str
    titel: str
    zustand: str
    satz: str
    hinweis: str = ""

    def uebersicht(self) -> dict:
        return {"schluessel": self.schluessel, "titel": self.titel,
                "zustand": self.zustand, "satz": self.satz, "hinweis": self.hinweis}


@dataclass(frozen=True, slots=True)
class Modellzeile:
    """Ein eingebundenes Modell und die Arbeit, die es tut."""

    kennung: str
    funktionen: tuple[str, ...]
    zustand: str
    satz: str

    @property
    def arbeit(self) -> str:
        return ", ".join(FUNKTION_NAME.get(f, f) for f in self.funktionen)

    def uebersicht(self) -> dict:
        return {"kennung": self.kennung, "funktionen": list(self.funktionen),
                "arbeit": self.arbeit, "zustand": self.zustand, "satz": self.satz}


@dataclass(frozen=True, slots=True)
class Ergebnis:
    punkte: tuple[Punkt, ...] = field(default_factory=tuple)
    modelle: tuple[Modellzeile, ...] = field(default_factory=tuple)

    @property
    def offen(self) -> int:
        return sum(1 for p in self.punkte if p.zustand in (OFFEN, SCHLECHT))

    def uebersicht(self) -> dict:
        return {"punkte": [p.uebersicht() for p in self.punkte],
                "modelle": [m.uebersicht() for m in self.modelle],
                "offen": self.offen}


def modelle_je_kennung(e: Einstellungen) -> dict[str, tuple[str, ...]]:
    """Welches Modell tut welche Arbeit – ein Eintrag je Modell, nicht je Funktion."""
    gebuendelt: dict[str, list[str]] = {}
    for funktion, kennung in e.modelle_uebersicht().items():
        gebuendelt.setdefault(kennung, []).append(funktion)
    return {kennung: tuple(funktionen) for kennung, funktionen in gebuendelt.items()}


def _richtlinie_deckt(kennung: str) -> bool:
    return bool(_GEDECKT.match(kennung) or _ARN_PROFIL.match(kennung))


# Was AWS bei einem abgewiesenen Zugang zurueckmeldet - und was es fuer den
# Bearbeiter heisst. „ClientError" allein half niemandem: Es sagte nicht, ob
# die Kennung oder der geheime Schluessel nicht stimmt, und das sind zwei ganz
# verschiedene Handgriffe.
_ZUGANGSFEHLER = {
    "InvalidClientTokenId": (
        "Die Access Key ID kennt AWS nicht.",
        "Entweder ein Tippfehler in der Kennung, oder der Schlüssel wurde in AWS "
        "gelöscht. Nachsehen: IAM → Benutzer → Sicherheitsanmeldeinformationen."),
    "UnrecognizedClientException": (
        "Die Access Key ID kennt AWS nicht.",
        "Entweder ein Tippfehler in der Kennung, oder der Schlüssel wurde in AWS "
        "gelöscht. Nachsehen: IAM → Benutzer → Sicherheitsanmeldeinformationen."),
    "SignatureDoesNotMatch": (
        "Die Kennung stimmt, aber die Unterschrift passt nicht.",
        "Zwei Ursachen, und die zweite übersieht man leicht. Erstens der "
        "geheime Schlüssel: Er wird beim Eintragen nicht angezeigt, ein "
        "abgeschnittenes Einfügen fällt deshalb nicht auf; AWS zeigt ihn nur "
        "einmal an, ist er weg, in IAM einen neuen erstellen. Zweitens die "
        "Uhr dieses Rechners: AWS unterschreibt jede Anfrage mit der Zeit und "
        "weist sie ab, wenn sie mehr als ein paar Minuten danebenliegt – "
        "Windows-Einstellungen, Zeit und Sprache, „Uhrzeit automatisch "
        "festlegen“ und einmal „Jetzt synchronisieren“."),
    "InvalidSignatureException": (
        "Die Kennung stimmt, aber die Unterschrift passt nicht.",
        "Meist die Uhr dieses Rechners: AWS unterschreibt jede Anfrage mit der "
        "Zeit und weist sie ab, wenn sie mehr als ein paar Minuten "
        "danebenliegt. Windows-Einstellungen, Zeit und Sprache, „Uhrzeit "
        "automatisch festlegen“ und einmal „Jetzt synchronisieren“. Sonst der "
        "geheime Schlüssel."),
    "RequestTimeTooSkewed": (
        "Die Uhr dieses Rechners geht falsch.",
        "AWS unterschreibt jede Anfrage mit der Zeit und weist sie ab, wenn "
        "sie zu weit danebenliegt. Windows-Einstellungen, Zeit und Sprache, "
        "„Uhrzeit automatisch festlegen“ und einmal „Jetzt synchronisieren“."),
    "ExpiredToken": (
        "Der Zugang ist abgelaufen.",
        "Das sind zeitlich befristete Zugangsdaten (Kennung beginnt mit ASIA). "
        "Für den Dauerbetrieb einen eigenen IAM-Benutzer mit dauerhaftem "
        "Schlüssel anlegen."),
    "AccessDenied": (
        "Die Zugangsdaten stimmen, aber der Benutzer darf nicht einmal sich "
        "selbst abfragen.",
        "Der Zugriffsrichtlinie fehlt sts:GetCallerIdentity, oder sie hängt "
        "nicht am Benutzer (IAM → Benutzer → Berechtigungen). Siehe infra/IAM.md."),
}


def zugangsfehler(fehler: Exception) -> tuple[str, str]:
    """Aus einem AWS-Fehler zwei verständliche Sätze machen."""
    art = type(fehler).__name__
    if art == "NoCredentialsError":
        return ("Es sind gar keine AWS-Zugangsdaten hinterlegt.",
                "ZUGANG-EINTRAGEN.bat starten; es legt sie in %USERPROFILE%\\.aws ab.")
    code = ""
    antwort = getattr(fehler, "response", None)
    if isinstance(antwort, dict):
        code = str(antwort.get("Error", {}).get("Code", ""))
    if code in _ZUGANGSFEHLER:
        return _ZUGANGSFEHLER[code]
    if art in ("EndpointConnectionError", "ConnectTimeoutError", "ReadTimeoutError"):
        return ("AWS ist von diesem Rechner aus nicht erreichbar.",
                "Internetverbindung, Firewall oder Proxy der Kanzlei prüfen.")
    return (f"Der Zugang lässt sich nicht bestätigen ({code or art}).",
            "python -m jusperfect.awstest sagt genauer, woran es liegt.")


class Selbsttest:
    """Führt die Prüfungen aus. Jede für sich; keine reißt die anderen mit."""

    def __init__(self, e: Einstellungen, *, adapter=None, kosten=None,
                 modellprotokoll: Befund | None = None, sts=None) -> None:
        self._e = e
        self._adapter = adapter
        self._kosten = kosten
        self._befund = modellprotokoll
        self._sts = sts

    def ausfuehren(self) -> Ergebnis:
        pruefungen = (self._anbieter, self._region, self._zugang, self._mitschrift,
                      self._guardrail, self._akten, self._gedaechtnis, self._kostenbremse)
        punkte = []
        for pruefung in pruefungen:
            try:
                punkte.append(pruefung())
            except Exception as fehler:  # eine kaputte Prüfung ist kein kaputtes Startbild
                punkte.append(Punkt(pruefung.__name__.strip("_"), pruefung.__name__.strip("_").capitalize(),
                                    OFFEN, f"Diese Prüfung ist selbst fehlgeschlagen ({type(fehler).__name__})."))
        return Ergebnis(tuple(punkte), self._modelle())

    # ── Die einzelnen Prüfungen ────────────────────────────────────────────

    def _anbieter(self) -> Punkt:
        if self._e.anbieter == "demo":
            return Punkt("anbieter", "Wer antwortet", ENTFAELLT,
                         "Demo-Anbieter: Die Antworten entstehen auf diesem Rechner, ohne KI.",
                         "Es geht kein Aktentext hinaus, und es entstehen keine Kosten.")
        return Punkt("anbieter", "Wer antwortet", GUT,
                     "Claude bei AWS Bedrock im gesicherten Bereich der Kanzlei.")

    def _region(self) -> Punkt:
        if self._e.anbieter == "demo":
            return Punkt("region", "Region", ENTFAELLT, "Ohne AWS gibt es keine Region.")
        # Die Einstellungen lassen nichts anderes zu; das Startbild sagt trotzdem,
        # welche es ist - "Europa" ohne Namen beantwortet die Frage nur halb.
        return Punkt("region", "Region", GUT,
                     f"{self._e.aws_region} – innerhalb der Europäischen Union.")

    def _zugang(self) -> Punkt:
        if self._e.anbieter == "demo":
            return Punkt("zugang", "Zugang zu AWS", ENTFAELLT, "Im Demo-Betrieb nicht nötig.")
        try:
            sts = self._sts
            if sts is None:
                import boto3
                sts = boto3.Session(region_name=self._e.aws_region).client("sts")
            wer = sts.get_caller_identity()
        except Exception as fehler:
            satz, hinweis = zugangsfehler(fehler)
            return Punkt("zugang", "Zugang zu AWS", SCHLECHT, satz, hinweis)
        return Punkt("zugang", "Zugang zu AWS", GUT,
                     f"Angemeldet als {wer.get('Arn', '(unbekannt)')}.")

    def _mitschrift(self) -> Punkt:
        if self._befund is None:
            return Punkt("mitschrift", "AWS schreibt nichts mit", ENTFAELLT,
                         "Ohne Modellaufrufe gibt es nichts mitzuschreiben.")
        if self._befund.zustand == AUS:
            return Punkt("mitschrift", "AWS schreibt nichts mit", GUT, self._befund.satz)
        if self._befund.zustand == AN:
            # Hierher kommt das Programm nicht: Es startet dann gar nicht.
            return Punkt("mitschrift", "AWS schreibt nichts mit", SCHLECHT, self._befund.satz)
        return Punkt("mitschrift", "AWS schreibt nichts mit", OFFEN, self._befund.satz,
                     " ".join(self._befund.einzelheiten))

    def _guardrail(self) -> Punkt:
        if self._e.anbieter == "demo":
            return Punkt("guardrail", "Schutzgeländer", ENTFAELLT, "Ohne Modell kein Geländer.")
        if self._e.guardrail_id:
            return Punkt("guardrail", "Schutzgeländer", GUT,
                         f"Bedrock-Guardrail {self._e.guardrail_id} ist vorgeschaltet.")
        # Ohne Guardrail und mit echten Akten startet das Programm gar nicht
        # (siehe config.py). Hierher kommt der Fall also nur mit den erfundenen
        # Akten - und dann gehoert der Satz dazu, warum es so nicht weitergeht.
        return Punkt("guardrail", "Schutzgeländer", OFFEN,
                     "Es ist kein Bedrock-Guardrail hinterlegt.",
                     "Mit den erfundenen Testakten läuft es ohne. Mit echten Akten "
                     "startet das Programm ohne Guardrail nicht; einrichten nach "
                     "AWS-EINRICHTEN.md und unter JUSPERFECT_GUARDRAIL_ID eintragen.")

    @staticmethod
    def _akten_fehler(fehler: Exception) -> str:
        """Was schiefging – mit Grund, wo einer bekannt ist.

        Hier stand nur der Name der Ausnahme: „nicht erreichbar
        (JurNodesFehler)". Das ist wahr und sagt nichts. Die Meldungen des
        Adapters nennen dagegen den Grund und sind eigens so gebaut, dass sie
        keinen Akteninhalt enthalten – sie tragen einen Statuscode, nie den
        Antworttext eines Servers. Genau die gehören hierher.

        Bei einer fremden Ausnahme bleibt es beim Namen: Was darin steht, ist
        nicht geprüft, und die Oberfläche ist der falsche Ort für einen
        ungeprüften Text.
        """
        from jusperfect.jurnodes.base import JurNodesFehler

        if isinstance(fehler, JurNodesFehler) and str(fehler):
            return f"Der Aktenbestand ist nicht erreichbar: {fehler}"
        return f"Der Aktenbestand ist nicht erreichbar ({type(fehler).__name__})."

    def _akten_rat(self) -> str:
        """Der Rat muss zum eingestellten Weg passen.

        „Liegt das Laufwerk an?" stand hier auch dann, wenn ueberhaupt kein
        Laufwerk im Spiel ist. Wer ueber die Schnittstelle arbeitet, sucht
        danach an einer Stelle, die es in seiner Einrichtung nicht gibt.
        """
        if self._e.jurnodes_adapter == "http":
            return ("Antwortet die Schnittstelle? Das sagt JURNODES-PRUEFEN.bat. "
                    "Bei 401 fehlt dem Schlüssel ein Bereich oder ein Recht; "
                    "eingetragen wird der Zugang mit JURNODES-ZUGANG.bat.")
        if self._e.jurnodes_adapter == "webdav":
            return ("Liegt das Laufwerk an? Ist der Ordner richtig eingetragen? "
                    "Das prüft ORDNER-PRUEFEN.bat.")
        return "Liegt der Ordner mit den Testakten dort, wo er erwartet wird?"

    def _akten(self) -> Punkt:
        echt = self._e.jurnodes_adapter != "fixture"
        titel = "Aktenzugang" if echt else "Testakten"
        if self._adapter is None:
            return Punkt("akten", titel, OFFEN, "Der Aktenzugang wurde nicht geprüft.")
        try:
            akten = self._adapter.akten_suchen("")
        except Exception as fehler:
            return Punkt("akten", titel, SCHLECHT,
                         self._akten_fehler(fehler), self._akten_rat())
        wie = {"fixture": "erfundene Testakten", "webdav": "Aktenordner auf dem Laufwerk",
               "http": "jurnodes über die Schnittstelle"}.get(self._e.jurnodes_adapter, self._e.jurnodes_adapter)
        # Erreichbar ist erreichbar - auch bei den erfundenen Akten. Dass darin
        # kein Mandantengeheimnis steht, gehoert in den Hinweis, nicht in den
        # Zustand: Sonst stuende im Demo-Betrieb nirgends ein Haken, und ein
        # Startbild ohne Haken liest niemand zweimal.
        return Punkt("akten", titel, GUT, f"{len(akten)} Akte(n) erreichbar – {wie}.",
                     "" if echt else "Erfundene Akten: Es steht kein Mandantengeheimnis darin.")

    def _gedaechtnis(self) -> Punkt:
        ort = self._e.gedaechtnis
        if ort == "aus":
            return Punkt("gedaechtnis", "Gedächtnis", ENTFAELLT,
                         "Abgeschaltet – eine Sitzung lebt, solange sie offen ist.")
        # Der Ablageort in AWS wird genannt, aber nicht behauptet.
        #
        # Hier stand für "aws" ein GUT - abgeleitet allein daraus, dass in der
        # Startdatei ein Bucketname steht. Ob der Bucket existiert, in
        # Frankfurt liegt, das Schreiben zulässt und den Kanzleischlüssel
        # annimmt, hat niemand gefragt. Ein Haken, der aus einer Einstellung
        # entsteht, gibt Sicherheit, wo keine ist - und beim Aktengedächtnis
        # fiele das Fehlen erst auf, wenn eine Akte geschlossen wird und das
        # Gedächtnis nicht gesichert werden kann.
        #
        # Dieselbe Trennung wie beim Schutzgeländer: Dass etwas hinterlegt
        # ist, sagt der Selbsttest. Ob es arbeitet, sagt eine Probe.
        if ort == "aws":
            return Punkt(
                "gedaechtnis", "Gedächtnis", UNGEPRUEFT,
                f"Eingestellt auf den S3-Bucket „{self._e.gedaechtnis_bucket}“ mit dem "
                f"Kanzleischlüssel.",
                "Dass beides hinterlegt ist, steht hier. Ob der Bucket das Ablegen "
                "annimmt, sagt GEDAECHTNIS-AWS-PRUEFEN.bat - einmal nach dem "
                "Einrichten. Die Probe schreibt eine Zeile und liest sie zurück.")
        wo = {
            "akte": ("in der Akte selbst, als eine Datei neben den Dokumenten", GUT),
            "lokal": ("als unverschlüsselte Datei auf diesem Rechner", GUT),
        }.get(ort, (ort, OFFEN))
        satz, zustand = wo
        hinweis = ("Nur mit den erfundenen Testakten zulässig; die Einstellungen lassen "
                   "es mit echten Akten nicht zu.") if ort == "lokal" else ""
        return Punkt("gedaechtnis", "Gedächtnis", zustand, f"Es liegt {satz}.", hinweis)

    def _kostenbremse(self) -> Punkt:
        if self._e.anbieter == "demo":
            return Punkt("kosten", "Kostenbremse", ENTFAELLT, "Der Demo-Anbieter kostet nichts.")
        grenze = self._e.monatsbudget_eur
        stand = None
        if self._kosten is not None:
            stand = self._kosten.stand()
        if stand is None:
            return Punkt("kosten", "Kostenbremse", GUT,
                         f"Bei {grenze:.0f} EUR im Monat verweigert das Programm weitere Aufrufe.")
        verbraucht = float(stand.get("verbraucht_eur", 0.0))
        zustand = OFFEN if verbraucht >= grenze else GUT
        # Komma, nicht Punkt: Im Rest des Programms stehen Betraege deutsch.
        satz = f"{verbraucht:.2f}".replace(".", ",") + f" von {grenze:.0f} EUR in diesem Monat verbraucht."
        hinweis = ("Die Grenze ist erreicht; weitere Modellaufrufe werden verweigert. "
                   "Das ist kein Fehler, sondern die Bremse.") if zustand == OFFEN else ""
        return Punkt("kosten", "Kostenbremse", zustand, satz, hinweis)

    # ── Die eingebundenen Modelle ──────────────────────────────────────────

    def _modelle(self) -> tuple[Modellzeile, ...]:
        if self._e.anbieter == "demo":
            return (Modellzeile("demo-ohne-ki", tuple(FUNKTION_NAME), ENTFAELLT,
                                "Muster im Programm, keine KI."),)
        zeilen = []
        for kennung, funktionen in modelle_je_kennung(self._e).items():
            if _richtlinie_deckt(kennung):
                zeilen.append(Modellzeile(kennung, funktionen, UNGEPRUEFT,
                                          "Von der Zugriffsrichtlinie abgedeckt."))
            else:
                zeilen.append(Modellzeile(
                    kennung, funktionen, SCHLECHT,
                    "Die Zugriffsrichtlinie deckt diese Kennung nicht ab – der Aufruf "
                    "würde abgewiesen. Erlaubt sind Claude-Modelle von Anthropic, "
                    "unmittelbar oder über das europäische Inferenzprofil."))
        return tuple(sorted(zeilen, key=lambda z: z.kennung))


#: Saetze in der Sprache einer Akte, je einer aus einem Rechtsgebiet, in dem
#: ein Inhaltsfilter typischerweise zuschlaegt. Alles erfunden, keine Namen von
#: Beteiligten, kein Mandantengeheimnis.
#:
#: Der erste ist die Kontrolle: Er ist unverfaenglich und muss immer durch. Geht
#: schon er nicht durch, liegt es nicht an den Inhaltsfiltern.
GELAENDERPROBEN: tuple[tuple[str, str], ...] = (
    ("Bausache (Kontrolle)",
     "Die Auftragnehmerin rechnete eine Dämmstärke von 24 cm ab; "
     "der Sachverständige misst 18 cm."),
    ("Kündigungsschutz",
     "Der Arbeitgeber kündigte fristlos und stützt sich auf den Verdacht "
     "einer Unterschlagung."),
    ("Körperverletzung",
     "Der Mandant soll dem Geschädigten mit der Faust ins Gesicht geschlagen "
     "und ihn zu Boden gebracht haben."),
    ("Beleidigung",
     "Der Nachbar bezeichnete die Mandantin nach deren Angaben als Lügnerin "
     "und Betrügerin."),
    ("Familien- und Sexualstrafrecht",
     "Die Mandantin erstattete Strafanzeige wegen einer Sexualstraftat zum "
     "Nachteil ihrer Tochter."),
)


def _gelaenderbefund(durch: bool, grund: str) -> str:
    """Zwei Faelle, zwei Saetze - sie verlangen Verschiedenes.

    Gesperrt heisst: Das Geländer arbeitet, ist aber zu scharf eingestellt. Das
    ist ein Handgriff in der AWS-Konsole.

    Nicht gefragt heisst: Es liess sich gar nicht prüfen - ein fehlendes Recht,
    eine falsche Kennung, kein Netz. Das ist etwas anderes, und wer beides in
    einem Satz liest, stellt an der falschen Stelle nach.
    """
    if durch:
        return "Durchgelassen."
    from jusperfect.modelle import GESPERRT
    if grund == GESPERRT:
        return ("Vom Geländer angehalten. Dieser Filter ist für eine Kanzlei zu "
                "scharf - in einer Akte ist genau das der Fall. Abschwächen nach "
                "AWS-EINRICHTEN.md, Schritt 9.")
    return f"Nicht geprüft - {grund}."


def gelaender_anprobieren(e: Einstellungen, *, anprobe=None) -> tuple[Modellzeile, ...]:
    """Laesst das Schutzgelaender die Sprache einer Akte durch?

    Das ist die Probe, die vor der ersten echten Akte fehlt. Der Selbsttest
    sagt bisher nur, DASS ein Geländer hinterlegt ist - nicht, ob es
    brauchbar eingestellt ist.

    Die Gefahr ist einseitig: Die Voreinstellungen von AWS sind fuer
    Anwendungen gedacht, in denen Gewalt, Sexuelles und Beleidigungen nichts zu
    suchen haben. In einer Kanzlei sind genau das die Faelle. Eine
    Koerperverletzungssache IST Gewalt; eine Beleidigungsklage muss die
    Beleidigung wiedergeben duerfen. Ein zu scharfer Filter faellt sonst zum
    ersten Mal vor einer echten Akte auf.

    Gibt eine leere Liste zurueck, wenn es nichts zu pruefen gibt - ohne
    Geländer oder ohne Modell ist die Frage gegenstandslos.
    """
    if e.anbieter == "demo" or not e.guardrail_id:
        return ()
    if anprobe is None:
        from jusperfect.modelle import _gelaender_anprobieren as anprobe
    kennung = e.modell_fuer("frage")
    zeilen = []
    for gebiet, satz in GELAENDERPROBEN:
        durch, grund = anprobe(e.aws_region, kennung, e.guardrail_id,
                               e.guardrail_version, satz)
        zeilen.append(Modellzeile(
            f"Schutzgeländer · {gebiet}", (f"„{satz}“",),
            GUT if durch else SCHLECHT, _gelaenderbefund(durch, grund)))
    return tuple(zeilen)


def modelle_anprobieren(e: Einstellungen, *, anprobe=None) -> tuple[Modellzeile, ...]:
    """Jedes eingebundene Modell einmal wirklich fragen – ein Wort, ein Token.

    Das kostet, deshalb geschieht es nur auf ausdrücklichen Wunsch. Der Katalog
    von AWS beantwortet die Frage nicht zuverlässig: „In Frankfurt vorhanden"
    heißt nicht „dieses Konto darf es" (siehe modelle.py).
    """
    if e.anbieter == "demo":
        return (Modellzeile("demo-ohne-ki", tuple(FUNKTION_NAME), ENTFAELLT,
                            "Muster im Programm, keine KI."),)
    if anprobe is None:
        from jusperfect.modelle import _anprobieren as anprobe
    zeilen = []
    for kennung, funktionen in modelle_je_kennung(e).items():
        if not _richtlinie_deckt(kennung):
            zeilen.append(Modellzeile(kennung, funktionen, SCHLECHT,
                                      "Die Zugriffsrichtlinie deckt diese Kennung nicht ab."))
            continue
        geht, grund = anprobe(e.aws_region, kennung)
        zeilen.append(Modellzeile(kennung, funktionen, GUT if geht else SCHLECHT,
                                  "Antwortet." if geht else f"Antwortet nicht – {grund}"))
    return tuple(sorted(zeilen, key=lambda z: z.kennung))
