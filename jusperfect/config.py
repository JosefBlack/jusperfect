"""Konfiguration aus der Umgebung.

Alles, was zwischen lokaler Entwicklung und AWS-Betrieb variiert, steht hier
und nichts davon im Quellcode: kein Token, kein Schlüssel, keine Kanzlei-URL.
In AWS setzt die SAM-Vorlage diese Variablen an der Lambda-Funktion; lokal
kommen sie aus einer ``.env`` (siehe ``.env.example``).

Zwei Betriebsarten:

* ``lokal`` – Speicher im Arbeitsspeicher, Nutzer per Kopfzeile, Demo-Anbieter
  möglich. Für Entwicklung, Tests und Vorführung.
* ``aws``   – Cognito-Identität aus dem API-Gateway-Authorizer, DynamoDB und
  S3 als Sitzungsspeicher, Textract, Bedrock, Secrets Manager.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


#: Was Anwender aus einer Anleitung abschreiben, statt die eigene Kennung
#: einzusetzen. Kleingeschrieben verglichen.
PLATZHALTER_GELAENDER = frozenset({
    "ihre-kennung", "ihre_kennung", "ihrekennung", "kennung",
    "abcd1234efgh", "abcd1234", "guardrail-id", "guardrail_id",
    "xxxxxxxx", "hier-eintragen", "bitte-eintragen", "todo", "tbd",
})


#: Dasselbe fuer die AWS-Ablage des Aktengedaechtnisses.
#:
#: START-JURNODES.bat haelt die drei Zeilen fuer "aws" auskommentiert bereit,
#: mit HIER-DEN-BUCKETNAMEN und HIER-DIE-SCHLUESSELKENNUNG darin. Wer das REM
#: wegnimmt und das Eintragen vergisst, bekaeme sonst eine Meldung von S3 -
#: "NoSuchBucket" -, die nach einem Programmfehler aussieht.
#:
#: Die Lehre stammt vom 25.09.2026: Im Windows-Konto stand woertlich
#: "IHRE-KENNUNG" aus unserer eigenen Anleitung. Die Pruefung "ist etwas
#: eingetragen?" war zufrieden, und erst der Modellaufruf scheiterte. Wer eine
#: Anleitung schreibt, muss damit rechnen, dass sie befolgt wird - und wer
#: einen Platzhalter hinschreibt, muss ihn selbst abweisen.
PLATZHALTER_ABLAGE = frozenset({
    "hier-den-bucketnamen", "hier-die-schluesselkennung",
    "ihr-bucketname", "ihr-bucket", "bucketname", "bucket",
    "schluesselkennung", "schluessel", "key-id", "keyid", "kms-key-id",
    "hier-eintragen", "bitte-eintragen", "todo", "tbd", "xxxxxxxx",
})


class KonfigurationsFehler(ValueError):
    """Eine Einstellung fehlt oder ist unbrauchbar."""


def _zahl(env: Mapping[str, str], name: str, standard: float) -> float:
    wert = env.get(name, "").strip()
    if not wert:
        return standard
    try:
        return float(wert.replace(",", "."))
    except ValueError as e:
        raise KonfigurationsFehler(f"{name} ist keine Zahl: {wert!r}") from e


def _wahl(env: Mapping[str, str], name: str, standard: str, erlaubt: tuple[str, ...]) -> str:
    wert = env.get(name, standard).strip().lower() or standard
    if wert not in erlaubt:
        raise KonfigurationsFehler(f"{name} muss eines von {erlaubt} sein, nicht {wert!r}.")
    return wert


def _schalter(env: Mapping[str, str], name: str, standard: bool) -> bool:
    wert = env.get(name, "").strip().lower()
    if not wert:
        return standard
    return wert in ("1", "true", "ja", "yes", "on")


# Anthropic gibt seine Modelle in Europa ueber Inferenzprofile frei, nicht
# unmittelbar. Eine Abfrage in Frankfurt zeigt es deutlich: Von dreizehn
# Claude-Modellen laesst sich genau eines unmittelbar aufrufen, ein Haiku von
# 2024; alle uebrigen verlangen ein Profil. Die Profilkennung ist dieselbe
# Kennung mit dem Vorsatz "eu.".
#
# Ohne diesen Vorsatz weist AWS den Aufruf mit AccessDeniedException ab - also
# mit derselben Meldung wie eine fehlende Berechtigung. Wer das nicht weiss,
# sucht den Fehler bei der Richtlinie und findet ihn dort nicht. Genau das ist
# in der Kanzlei passiert und hat einen Vormittag gekostet.
_PROFILREGIONEN = ("eu-",)


#: Die AWS-Regionen, die wirklich in der EU oder im EWR liegen.
#:
#: **Aus der Kanzlei am 05.10.2026: „Zuerich ist eu-central-2 und nicht
#: eu-central-1."** Das stimmt - und es deckt einen Fehler auf, der bis dahin
#: in der Pruefung stand: Geprueft wurde auf den Vorsatz "eu-", und
#: "eu-central-2" faengt mit "eu-" an. Der Vorsatz ist eine Namenskonvention
#: von AWS und keine Aussage ueber die Europaeische Union.
#:
#: Zwei Regionen tragen ihn und liegen ausserhalb der EU und des EWR:
#:
#:   eu-central-2  Zuerich      Schweiz
#:   eu-west-2     London       Vereinigtes Koenigreich
#:
#: Fuer eine Kanzlei, deren Unterlage "Uebermittlung in Drittlaender: keine"
#: sagt, ist das der Unterschied zwischen einem Satz, der stimmt, und einem,
#: der sich auf eine Buchstabenfolge stuetzt.
#:
#: **Fail closed, mit Ansage.** Eine neue EU-Region, die AWS erst spaeter
#: eroeffnet, wird hier abgewiesen, bis sie in dieser Liste steht. Das ist die
#: sichere Richtung, und der Fehlertext sagt, wo die Liste steht.
#:
#: Die Liste gehoert gegen das Regionenverzeichnis von AWS geprueft; sie ist
#: hier aufgeschrieben und nicht abgeleitet, weil sie sich nicht ableiten
#: laesst - genau das war der Fehler.
EU_EWR_REGIONEN = (
    "eu-central-1",   # Frankfurt am Main, Deutschland
    "eu-west-1",      # Irland
    "eu-west-3",      # Paris, Frankreich
    "eu-south-1",     # Mailand, Italien
    "eu-south-2",     # Spanien (Aragon)
    "eu-north-1",     # Stockholm, Schweden
)

#: Was wie eine EU-Region aussieht und keine ist. Nur fuer die Fehlermeldung:
#: "nicht erlaubt" hilft weniger als "das liegt in der Schweiz".
_SCHEIN_EU_REGIONEN = {
    "eu-central-2": "Zürich, Schweiz",
    "eu-west-2": "London, Vereinigtes Königreich",
}


def _woerter(wert: str | None, standard: tuple[str, ...]) -> tuple[str, ...]:
    """Eine durch Komma getrennte Liste – oder die Vorgabe.

    Ist nichts gesetzt, gilt die Vorgabe. Ein ausdrücklich leerer Wert ist
    dagegen eine Angabe und schaltet ab: Wer ``JUSPERFECT_NICHT_VORWAEHLEN=``
    setzt, will keine Vorauswahl, und nicht die Vorgabe.
    """
    if wert is None:
        return standard
    return tuple(teil.strip() for teil in wert.split(",") if teil.strip())


#: Vorsaetze von Inferenzprofilen, die AUSSERHALB der EU verteilen.
#:
#: Ein Inferenzprofil ist kein Modellname, sondern eine Verteilregel: Es sagt,
#: in welche Regionen AWS den Aufruf schicken darf. "global." heisst
#: ausdruecklich "weltweit". Die Aufrufregion sagt daruber nichts - sie ist der
#: Ort, an dem die Anfrage ankommt, nicht der, an dem gerechnet wird.
#:
#: Befund F13 der Zweitpruefung vom 05.10.2026: Frankfurt plus
#: "global.anthropic.claude-opus-4-6-v1" kam durch die Einstellungspruefung.
#: Die mitgelieferte Zugriffsrichtlinie haette den Aufruf abgewiesen - aber
#: eine Zusage, die nur von der Kontoeinstellung getragen wird, haelt das
#: Programm nicht selbst.
FREMDE_PROFILE = ("global.", "us.", "us-gov.", "apac.", "ap.", "ca.", "sa.", "jp.", "au.")


def profil_befund(kennung: str) -> str:
    """Warum diese Modellkennung die EU verlassen würde – „" wenn nicht.

    Drei Formen kommen vor:

    * ``eu.anthropic.…`` – ein EU-Inferenzprofil. In Ordnung.
    * ``global.…``/``us.…`` – ein Profil, das anderswohin verteilt. Nicht.
    * eine vollständige ARN – dann entscheidet die Region **in der ARN**,
      nicht die Aufrufregion.

    Eine Kennung ohne Vorsatz (``anthropic.…``) bekommt in Europa von
    ``_modellkennung`` das ``eu.`` vorangestellt und erreicht diese Prüfung gar
    nicht mehr ohne; steht sie dennoch so da, ist sie ein Modell in genau der
    Aufrufregion und damit ebenfalls in Ordnung.
    """
    kennung = kennung.strip()
    if not kennung:
        return ""
    klein = kennung.lower()
    if klein.startswith("arn:"):
        teile = kennung.split(":")
        region = teile[3] if len(teile) > 4 else ""
        if region and region not in EU_EWR_REGIONEN:
            wo = _SCHEIN_EU_REGIONEN.get(region)
            return (f"die ARN zeigt auf {region!r}"
                    + (f" – das liegt in {wo}" if wo else " – das ist keine EU-/EWR-Region"))
        return ""
    for vorsatz in FREMDE_PROFILE:
        if klein.startswith(vorsatz):
            return (f"{vorsatz!r} ist ein Inferenzprofil, das außerhalb der EU "
                    f"verteilt – die Aufrufregion ändert daran nichts")
    return ""


def _modellkennung(kennung: str, region: str) -> str:
    """Setzt in europaeischen Regionen den Profilvorsatz, wo er noetig ist.

    Nur fuer Anthropic-Kennungen ohne eigenen Vorsatz. Wer ausdruecklich etwas
    anderes eintraegt - eine vollstaendige ARN, eine bereits mit "eu." -, oder
    wer ausserhalb Europas arbeitet, bekommt es unveraendert: Die
    Voreinstellung soll den Regelfall treffen, nicht die Wahl abnehmen.
    """
    kennung = kennung.strip()
    if not kennung or not region.startswith(_PROFILREGIONEN):
        return kennung
    if not kennung.startswith("anthropic."):
        return kennung
    return f"eu.{kennung}"


@dataclass(frozen=True)
class Einstellungen:
    betriebsart: str = "lokal"                 # "lokal" | "aws"

    # KI
    anbieter: str = "demo"                     # "bedrock" | "demo"
    aws_region: str = "eu-central-1"
    # Die Voreinstellung muss ein Modell sein, das aufrufbar IST. Hier stand
    # das neueste - und das Konto der Kanzlei fuehrt es nicht. Wer ohne
    # Startdatei arbeitet oder eine alte benutzt, lief damit in
    # "AccessDeniedException: is not available for this account", also in
    # dieselbe Meldung wie bei einer fehlenden Berechtigung. Eine Voreinstellung,
    # die niemand aufrufen kann, ist keine.
    # Teilt AWS spaeter mehr zu, zeigt MODELLE-ANZEIGEN.bat es.
    # Die Kennungen sind NICHT nach einem Muster gebaut. Opus 4.6 traegt
    # "-v1" ohne Datum, Haiku 4.5 Datum UND Fassung, Sonnet 4.6 keines von
    # beidem. Wer eine davon abkuerzt, bekommt von AWS eine Abweisung, die
    # wie eine fehlende Freischaltung aussieht. Was dieses Konto wirklich
    # fuehrt, sagt allein MODELLE-ANZEIGEN.bat - geraten wird hier nicht.
    modell_id: str = "anthropic.claude-opus-4-6-v1"
    modell_id_klein: str = ""                  # für Triage/Klassifikation; leer = wie modell_id
    # Modell je Aufgabe: leer = wie modell_id (Triage zusätzlich modell_id_klein).
    # Bedrock-Kennungen mit „anthropic."-Präfix, z. B. anthropic.claude-sonnet-5
    # (ausgewogen) oder anthropic.claude-haiku-4-5-20251001-v1:0 (schnell/günstig).
    modell_frage: str = ""
    modell_analyse: str = ""
    modell_triage: str = ""
    modell_entwurf: str = ""
    modell_gedaechtnis: str = ""             # leer = modell_id_klein, dann modell_id
    #: Wird die E-Akte (Korrespondenz) einer Akte mitgelesen?
    #:
    #: **Seit dem 08.10.2026 ein - gemessen am Server der Kanzlei.**
    #:
    #: Der Lauf vom 08.10.2026 an X-100-2026 beantwortet, worauf gewartet
    #: wurde: ``POST /correspondence/search`` gibt 26 Eintraege (22 mail,
    #: 4 note), und drei Vermerke wurden ueber
    #: ``GET /record/note?id=..&record=..`` wirklich geholt - mit Inhalt,
    #: ``type=phonecall``, ``contentType=html``. Damit ist der Weg belegt und
    #: nicht mehr vermutet.
    #:
    #: **Was als Befund vom 02.10.2026 im Weg stand, hat sich aufgeloest.**
    #: Dreimal trug der Ordner hinter ``correspondenceFolderId`` Dateien, die
    #: aelter waren als die Akte:
    #:
    #:   X-100-2026  angelegt 30.07.2026  Korrespondenzordner 2871, befuellt 2022/23
    #:   X-103-2026  angelegt 23.02.2026  Korrespondenzordner 2616, befuellt 2022/23
    #:   X-104-2023  angelegt 28.12.2023  Korrespondenzordner 1478, befuellt 2022/23
    #:
    #: Das Feld war die ganze Zeit richtig. jur|nodes fuehrt **zwei getrennte
    #: Ordnerbaeume mit je eigenen Nummern**, und 2871 wurde am Pfad des
    #: FALSCHEN gelesen: ``/file-system/folder/content`` liefert den
    #: Datei-Ordner Nr. 2871, nicht den Korrespondenz-Ordner Nr. 2871. Beide
    #: gibt es, beide tragen dieselbe Zahl, und sie haben nichts miteinander
    #: zu tun. Der Lauf vom 08.10.2026 zeigt es: Alle 26 Eintraege der E-Akte
    #: nennen als ``folderId`` genau die 2871 aus ``correspondenceFolderId``,
    #: und ihre Poststempel liegen zwischen dem 30.07. und dem 25.09.2026 -
    #: innerhalb der Lebenszeit der Akte.
    #:
    #: Es war also derselbe Fehler wie am 02.10.2026, nur an einer zweiten
    #: Stelle: eine Nummer am Pfad des anderen Baumes. Gelesen wird die E-Akte
    #: jetzt ueber ``POST /correspondence/search``, also ueber den Weg, den
    #: der Hersteller dafuer nennt - und dieser Weg nennt die Akte in der
    #: Anfrage, kann sie also gar nicht verwechseln.
    #:
    #: Aus geht es mit JUSPERFECT_KORRESPONDENZ=aus.
    korrespondenz: bool = True

    #: Woerter im Titel, die ein Dokument NICHT vorwaehlen.
    #:
    #: Aus der Kanzlei am 05.10.2026: "Grundsaetzlich gehoert die Rechnung
    #: nicht ins Aktengedaechtnis und Korrespondenz mit der RSV."
    #:
    #: Ein Dokument, dessen Titel eines dieser Woerter traegt, kommt ohne Haken
    #: ins Fenster "Arbeitsakte" - sichtbar, mit dem Grund daneben, mit einem
    #: Klick anzuhaken. **Nichts verschwindet stillschweigend.** Ein Programm,
    #: das Akteninhalt heimlich weglaesst, ist schlimmer als eines, das zu viel
    #: mitnimmt: Was fehlt, faellt niemandem auf.
    #:
    #: Die Liste trifft den TITEL, nicht den Inhalt. Eine Rechnung, die
    #: "Schreiben vom 14.03." heisst, erwischt sie nicht. Das ist eine Hilfe,
    #: keine Gewaehr, und so steht es auch in der Oberflaeche.
    #:
    #: Aendern ueber JUSPERFECT_NICHT_VORWAEHLEN, durch Komma getrennt. Der
    #: Wert ersetzt die Liste; ein leerer Wert schaltet die Vorauswahl ab.
    #: Er gehoert in das Windows-Konto (setx), nicht in den Programmordner -
    #: dort ueberlebt er das Auspacken der naechsten Fassung.
    nicht_vorwaehlen: tuple[str, ...] = (
        "Rechnung", "Kostennote", "Gebühren", "Vorschuss", "Honorar",
        "RSV", "Rechtsschutz", "Deckungszusage", "Deckungsanfrage",
    )

    guardrail_id: str | None = None
    guardrail_version: str = "DRAFT"
    prompt_cache: bool = True
    # Gemessen an der grossen Testakte: Die Analyse ueber fuenfzig Dokumente
    # brauchte 6.753 und 7.777 Ausgabetoken - 84 und 97 Prozent der frueheren
    # Grenze von 8.000. Beim dritten Lauf war sie ueberschritten, die Antwort
    # brach mitten im JSON ab, und das bezahlte Einlesen davor war verloren.
    # Eine Grenze, die zu 97 Prozent ausgereizt wird, ist keine Reserve.
    max_ausgabe_tokens: int = 16000
    kanzleiwissen_kb_id: str | None = None     # Bedrock Knowledge Base (Phase 2)

    # jur|nodes
    jurnodes_adapter: str = "fixture"          # "http" | "fixture" | "webdav"
    jurnodes_url: str = ""
    # Die Anmeldung an jur|nodes geht ueber ZWEI Kopfzeilen, nicht ueber ein
    # Token: X-Auth-User und X-Auth-Key (jur|nodes API 1.0.1). Hier stehen die
    # Namen der Umgebungsvariablen, in denen die Werte liegen - die Werte
    # selbst gehoeren nie in eine Datei des Programmordners.
    jurnodes_token_var: str = "JURNODES_API_KEY"
    jurnodes_benutzer_var: str = "JURNODES_API_USER"
    jurnodes_secret_arn: str | None = None     # AWS Secrets Manager statt Umgebungsvariable
    jurnodes_timeout_sekunden: float = 30.0
    # Die Pfade der jur|nodes-Schnittstelle stehen als plausible Annahme im
    # Quelltext (jurnodes/http_adapter.py::Endpunkte). Stimmen sie beim
    # Hersteller anders, ist das eine Zeile in dieser Datei und kein neuer
    # Programmstand - der Unterschied zwischen einem Anruf und einer Auslieferung.
    jurnodes_endpunkte_datei: str = ""
    fixture_pfad: Path = Path("testdaten/akten")
    # Wurzel des jur|nodes-Ordnerexports (WebDAV/OneDrive/Nextcloud), Aufbau
    # <Wurzel>/<Anwalt>/<Jahr>/<Aktenzeichen Bezeichnung>/. Für JUSPERFECT_JURNODES_ADAPTER=webdav.
    jurnodes_webdav_pfad: str = ""
    # Im Ordnerexport wird eine archivierte Akte in jurnodes von Hand
    # gekennzeichnet; das Kennwort steht dann im Ordnernamen. Daraus liest
    # jusperfect den Aktenstatus, an dem die Aufbewahrung hängt. Leer =
    # keine Konvention, dann bleibt der Status ausdrücklich unbekannt.
    archiv_kennung: str = "archiviert"

    # Identität und Berechtigungen
    identitaet: str = "header"                 # "header" (lokal) | "cognito" (aws)
    nutzer_datei: Path | None = Path("testdaten/nutzer.json")
    gruppe_alle_akten: str = "alle-akten"      # Cognito-Gruppe mit Zugriff auf alle Akten

    # Sitzungsspeicher
    speicher: str = "lokal"                    # "lokal" | "aws"
    dynamodb_tabelle: str = ""
    s3_bucket: str = ""
    kms_schluessel_id: str | None = None
    # Fortsetzbarer technischer Arbeitskontext. Das Aktengedächtnis ist davon
    # unabhängig und folgt dem Aktenstatus in jurnodes.
    sitzung_ttl_sekunden: int = 7 * 24 * 3600
    entwurf_ttl_sekunden: int = 7 * 24 * 3600

    # Dauerhaftes Aktengedächtnis. Wegen DSFA/Verarbeitungsverzeichnis ist es
    # bewusst opt-in.
    #   akte  – in der Akte selbst, als eine Datei im Aktenordner. Kein zweiter
    #           Aufbewahrungsort: Sicherung und Löschung der Akte erfassen es
    #           mit. Braucht einen Aktenzugang über Ordner (webdav, fixture).
    #   aws   – eigener S3-Eimer mit Kanzleischlüssel.
    #   lokal – Datei auf dem Rechner; für Demo und Test.
    gedaechtnis: str = "aus"                  # "aus" | "akte" | "lokal" | "aws"
    gedaechtnis_pfad: Path = Path(".jusperfect-gedaechtnis")
    gedaechtnis_bucket: str = ""
    gedaechtnis_max_fragen: int = 100
    # Obergrenze der dauerhaften Chronologie. Grosszuegig: Ein Zeitstrahl, der
    # in der Mitte abbricht, ist schlimmer als einer, der lang ist - und ein
    # Eintrag kostet zwei Zeilen Text.
    gedaechtnis_max_chronologie: int = 500
    # Übergangsfrist nach einem *bestätigten* Abschluss der Akte in jurnodes.
    # Sie beginnt ausschließlich mit diesem Ereignis, niemals durch Zeitablauf
    # oder Nichtbenutzung. Vor dem Ende der Frist wird nichts gelöscht.
    gedaechtnis_uebergangsfrist_tage: int = 30

    # OCR
    ocr: str = "keine"                         # "keine" | "textract"

    # Haufe-Recherche: Direktlink zum Haufe-Copilot (juristische Datenbank).
    # jusperfect öffnet ihn im Browser (bestehende Login-Sitzung des Nutzers),
    # fasst keine Zugangsdaten an. Leer = Knopf aus. Ein optionaler
    # Suchparameter (z. B. "q") hängt die Frage an die URL; leer = nur öffnen
    # und die Frage in die Zwischenablage legen.
    haufe_url: str = "https://law.copilot.haufe.ai/"
    haufe_suche_param: str = ""

    # Gesetzestexte: derselbe Weg wie bei Haufe - ein Sprung in den Browser,
    # nichts im Programmordner. Aus der Kanzlei am 25.09.2026: "wie hast du
    # Recherche Haufe eingebunden, genauso wollte ich das auch mit den
    # Gesetzestexten machen."
    #
    # Das ist besser als ein mitgefuehrter Bestand: nichts zu aktualisieren,
    # nichts, was veraltet, keine Urheberrechtsfrage - und der Stand ist immer
    # der von heute.
    #
    # Das Adressmuster wurde am 25.09.2026 von der Kanzlei am lebenden Server
    # geprueft ("geht auf"), nicht geraten. {gesetz} ist das Kuerzel in
    # Kleinbuchstaben, {paragraf} die Nummer mit einem etwaigen Buchstaben.
    # Leer = kein Sprung; dann wird nur die Startseite geoeffnet und der
    # Verweis in die Zwischenablage gelegt - wie bei Haufe ohne Suchparameter.
    gesetze_url: str = "https://www.gesetze-im-internet.de/"
    gesetze_muster: str = "{gesetz}/__{paragraf}.html"

    # Posteingang (beobachteter Ordner): ein Pfad, den die Cloud selbst füllt
    # (eingebundenes OneDrive/Nextcloud/WebDAV). Leer = aus. Nur im lokalen
    # Betrieb sinnvoll; er bereitet Dokumente vor, entscheidet aber nichts.
    posteingang_ordner: str = ""

    # Eigene Aufträge: ein Ordner mit .txt/.md-Dateien der Kanzlei. Dateiname =
    # Beschriftung, Unterordner = Rechtsgebiet, Trennlinie teilt Anweisung und
    # Material. Leer = aus. Erscheinen als Entwurfsvorlagen.
    auftrag_ordner: str = ""

    # Referenzen: ein Ordner mit veröffentlichtem Material (Urteile, Gesetze,
    # Tarifverträge) als .txt/.md/.pdf. Der Bearbeiter zieht einzelne davon in
    # den Kontext einer Sitzung; sie werden mitzitiert. Leer = aus.
    referenz_ordner: str = ""

    # Verarbeitung
    max_passagen_zeichen: int = 160_000
    max_frage_passagen: int = 14
    dialog_max_runden: int = 6                 # flüchtiger Kontext für Rückfragen

    # Kosten
    monatsbudget_eur: float = 125.0
    usd_eur_kurs: float = 0.92

    # Vorschaltstufe Perfect Shield: die lokale Anonymisierung vor jusperfect,
    # je Akte wählbar für hochsensible Fälle. Bewusst noch nicht eingebaut, um
    # das Programm schlank zu halten - der Schalter ist angelegt und steht auf
    # "nicht aktiv". Erst wenn Perfect Shield angebunden ist, wird er scharf.
    perfect_shield_aktiv: bool = False

    # Lokaler Server
    host: str = "127.0.0.1"
    port: int = 8765

    @classmethod
    def aus_umgebung(cls, env: Mapping[str, str] | None = None) -> "Einstellungen":
        env = os.environ if env is None else env
        betriebsart = _wahl(env, "JUSPERFECT_BETRIEBSART", cls.betriebsart, ("lokal", "aws"))
        in_aws = betriebsart == "aws"
        # Die Region steht vor den Modellkennungen: Ob ein Inferenzprofil noetig
        # ist, haengt an ihr, und sie wird gleich mehrfach gebraucht.
        _region = (env.get("JUSPERFECT_AWS_REGION", "").strip()
                   or env.get("AWS_REGION", "").strip() or cls.aws_region)
        nutzer_datei = env.get("JUSPERFECT_NUTZER_DATEI", "").strip()
        e = cls(
            betriebsart=betriebsart,
            anbieter=_wahl(env, "JUSPERFECT_ANBIETER", "bedrock" if in_aws else cls.anbieter, ("bedrock", "demo")),
            aws_region=env.get("JUSPERFECT_AWS_REGION", "").strip() or env.get("AWS_REGION", "").strip() or cls.aws_region,
            modell_id=_modellkennung(
                env.get("JUSPERFECT_MODELL_ID", "").strip() or cls.modell_id, _region),
            # Der Profilvorsatz gehoert an JEDE Modellkennung, nicht nur an die
            # eine. Vorher bekam ihn allein modell_id: Wer ein zweites Modell je
            # Aufgabe eintrug - genau der Fall, fuer den es die Felder gibt -,
            # erhielt es unveraendert und lief in Europa in eine Abweisung, die
            # nach einer fehlenden Freischaltung aussieht.
            modell_id_klein=_modellkennung(env.get("JUSPERFECT_MODELL_ID_KLEIN", ""), _region),
            modell_frage=_modellkennung(env.get("JUSPERFECT_MODELL_FRAGE", ""), _region),
            modell_analyse=_modellkennung(env.get("JUSPERFECT_MODELL_ANALYSE", ""), _region),
            modell_triage=_modellkennung(env.get("JUSPERFECT_MODELL_TRIAGE", ""), _region),
            modell_entwurf=_modellkennung(env.get("JUSPERFECT_MODELL_ENTWURF", ""), _region),
            modell_gedaechtnis=_modellkennung(env.get("JUSPERFECT_MODELL_GEDAECHTNIS", ""), _region),
            korrespondenz=env.get("JUSPERFECT_KORRESPONDENZ", "ein").strip().lower()
                          in ("ein", "an", "1", "ja", "true"),
            nicht_vorwaehlen=_woerter(env.get("JUSPERFECT_NICHT_VORWAEHLEN"),
                                      cls.nicht_vorwaehlen),
            guardrail_id=env.get("JUSPERFECT_GUARDRAIL_ID", "").strip() or None,
            guardrail_version=env.get("JUSPERFECT_GUARDRAIL_VERSION", cls.guardrail_version).strip() or cls.guardrail_version,
            prompt_cache=_schalter(env, "JUSPERFECT_PROMPT_CACHE", cls.prompt_cache),
            max_ausgabe_tokens=int(_zahl(env, "JUSPERFECT_MAX_AUSGABE_TOKENS", cls.max_ausgabe_tokens)),
            kanzleiwissen_kb_id=env.get("JUSPERFECT_KANZLEIWISSEN_KB_ID", "").strip() or None,
            jurnodes_adapter=_wahl(env, "JUSPERFECT_JURNODES_ADAPTER", cls.jurnodes_adapter, ("http", "fixture", "webdav")),
            jurnodes_url=env.get("JUSPERFECT_JURNODES_URL", "").strip(),
            jurnodes_token_var=env.get("JUSPERFECT_JURNODES_TOKEN_VAR", cls.jurnodes_token_var).strip() or cls.jurnodes_token_var,
            jurnodes_benutzer_var=env.get("JUSPERFECT_JURNODES_BENUTZER_VAR", cls.jurnodes_benutzer_var).strip() or cls.jurnodes_benutzer_var,
            jurnodes_secret_arn=env.get("JUSPERFECT_JURNODES_SECRET_ARN", "").strip() or None,
            jurnodes_timeout_sekunden=_zahl(env, "JUSPERFECT_JURNODES_TIMEOUT", cls.jurnodes_timeout_sekunden),
            jurnodes_endpunkte_datei=env.get("JUSPERFECT_JURNODES_ENDPUNKTE", "").strip(),
            fixture_pfad=Path(env.get("JUSPERFECT_FIXTURE_PFAD", str(cls.fixture_pfad))),
            jurnodes_webdav_pfad=env.get("JUSPERFECT_JURNODES_WEBDAV", "").strip(),
            archiv_kennung=env.get("JUSPERFECT_ARCHIV_KENNUNG", cls.archiv_kennung).strip(),
            identitaet=_wahl(env, "JUSPERFECT_IDENTITAET", "cognito" if in_aws else cls.identitaet, ("header", "cognito")),
            nutzer_datei=Path(nutzer_datei) if nutzer_datei else (None if in_aws else cls.nutzer_datei),
            gruppe_alle_akten=env.get("JUSPERFECT_GRUPPE_ALLE_AKTEN", cls.gruppe_alle_akten).strip() or cls.gruppe_alle_akten,
            speicher=_wahl(env, "JUSPERFECT_SPEICHER", "aws" if in_aws else cls.speicher, ("lokal", "aws")),
            dynamodb_tabelle=env.get("JUSPERFECT_DYNAMODB_TABELLE", "").strip(),
            s3_bucket=env.get("JUSPERFECT_S3_BUCKET", "").strip(),
            kms_schluessel_id=env.get("JUSPERFECT_KMS_SCHLUESSEL_ID", "").strip() or None,
            sitzung_ttl_sekunden=int(_zahl(env, "JUSPERFECT_SITZUNG_TTL_SEKUNDEN", cls.sitzung_ttl_sekunden)),
            entwurf_ttl_sekunden=int(_zahl(env, "JUSPERFECT_ENTWURF_TTL_SEKUNDEN", cls.entwurf_ttl_sekunden)),
            gedaechtnis=_wahl(env, "JUSPERFECT_GEDAECHTNIS", cls.gedaechtnis,
                              ("aus", "akte", "lokal", "aws")),
            gedaechtnis_pfad=Path(env.get("JUSPERFECT_GEDAECHTNIS_PFAD", str(cls.gedaechtnis_pfad))),
            gedaechtnis_bucket=env.get("JUSPERFECT_GEDAECHTNIS_BUCKET", "").strip(),
            gedaechtnis_max_fragen=int(_zahl(env, "JUSPERFECT_GEDAECHTNIS_MAX_FRAGEN", cls.gedaechtnis_max_fragen)),
            gedaechtnis_max_chronologie=int(_zahl(env, "JUSPERFECT_GEDAECHTNIS_MAX_CHRONOLOGIE", cls.gedaechtnis_max_chronologie)),
            gedaechtnis_uebergangsfrist_tage=int(_zahl(env, "JUSPERFECT_GEDAECHTNIS_UEBERGANGSFRIST_TAGE", cls.gedaechtnis_uebergangsfrist_tage)),
            ocr=_wahl(env, "JUSPERFECT_OCR", "textract" if in_aws else cls.ocr, ("keine", "textract")),
            haufe_url=env.get("JUSPERFECT_HAUFE_URL", cls.haufe_url).strip(),
            haufe_suche_param=env.get("JUSPERFECT_HAUFE_SUCHE_PARAM", "").strip(),
            gesetze_url=env.get("JUSPERFECT_GESETZE_URL", cls.gesetze_url).strip(),
            gesetze_muster=env.get("JUSPERFECT_GESETZE_MUSTER", cls.gesetze_muster).strip(),
            posteingang_ordner=env.get("JUSPERFECT_POSTEINGANG_ORDNER", "").strip(),
            auftrag_ordner=env.get("JUSPERFECT_AUFTRAG_ORDNER", "").strip(),
            referenz_ordner=env.get("JUSPERFECT_REFERENZ_ORDNER", "").strip(),
            max_passagen_zeichen=int(_zahl(env, "JUSPERFECT_MAX_PASSAGEN_ZEICHEN", cls.max_passagen_zeichen)),
            max_frage_passagen=int(_zahl(env, "JUSPERFECT_MAX_FRAGE_PASSAGEN", cls.max_frage_passagen)),
            dialog_max_runden=int(_zahl(env, "JUSPERFECT_DIALOG_MAX_RUNDEN", cls.dialog_max_runden)),
            monatsbudget_eur=_zahl(env, "JUSPERFECT_MONATSBUDGET_EUR", cls.monatsbudget_eur),
            usd_eur_kurs=_zahl(env, "JUSPERFECT_USD_EUR_KURS", cls.usd_eur_kurs),
            perfect_shield_aktiv=_schalter(env, "JUSPERFECT_PERFECT_SHIELD", cls.perfect_shield_aktiv),
            host=env.get("JUSPERFECT_HOST", cls.host).strip() or cls.host,
            port=int(_zahl(env, "JUSPERFECT_PORT", cls.port)),
        )
        e.pruefen()
        return e

    def pruefen(self) -> None:
        """Widersprüche früh melden, nicht erst beim ersten Aufruf."""
        if self.speicher == "aws" and not (self.dynamodb_tabelle and self.s3_bucket):
            raise KonfigurationsFehler("Für JUSPERFECT_SPEICHER=aws sind JUSPERFECT_DYNAMODB_TABELLE und JUSPERFECT_S3_BUCKET nötig.")
        if self.betriebsart == "aws" and self.identitaet == "header":
            raise KonfigurationsFehler("In AWS ist die Identität aus der Kopfzeile nicht zulässig; JUSPERFECT_IDENTITAET=cognito.")
        if self.betriebsart == "aws" and self.anbieter == "demo":
            raise KonfigurationsFehler("Der Demo-Anbieter ist nur lokal zulässig.")
        if self.identitaet == "header" and self.nutzer_datei is None:
            raise KonfigurationsFehler("Für die Kopfzeilen-Identität ist JUSPERFECT_NUTZER_DATEI nötig.")
        if self.jurnodes_adapter == "http" and not self.jurnodes_url:
            raise KonfigurationsFehler("JUSPERFECT_JURNODES_URL ist nicht gesetzt.")
        if self.jurnodes_adapter == "webdav" and not self.jurnodes_webdav_pfad:
            raise KonfigurationsFehler("Für JUSPERFECT_JURNODES_ADAPTER=webdav ist JUSPERFECT_JURNODES_WEBDAV (der Aktenordner) nötig.")
        if self.aws_region not in EU_EWR_REGIONEN:
            # Der Vorsatz "eu-" ist eine Namenskonvention von AWS und keine
            # Aussage ueber die EU. Wer eu-central-2 eintraegt, soll nicht
            # "nicht erlaubt" lesen, sondern "das liegt in der Schweiz".
            wo = _SCHEIN_EU_REGIONEN.get(self.aws_region)
            grund = (f"{self.aws_region!r} liegt in {wo} – außerhalb der EU und des EWR."
                     if wo else f"{self.aws_region!r} ist keine EU- oder EWR-Region.")
            raise KonfigurationsFehler(
                f"{grund} Zulässig sind: {', '.join(EU_EWR_REGIONEN)}. "
                "Die Liste steht in jusperfect/config.py::EU_EWR_REGIONEN; eine "
                "neue EU-Region von AWS ist dort einzutragen.")
        # Die Region allein genuegt nicht: Ein ausdruecklich eingetragenes
        # globales Profil verteilt weltweit, gleich aus welcher Region es
        # aufgerufen wird (Befund F13, siehe profil_befund).
        if self.anbieter == "bedrock":
            for funktion, (name, wert) in self._modellquellen().items():
                befund = profil_befund(wert)
                if befund:
                    raise KonfigurationsFehler(
                        f"{name} steht auf {wert.strip()!r}: {befund}. "
                        f"Zulässig sind Kennungen mit dem Vorsatz 'eu.' oder eine ARN "
                        f"in einer EU-/EWR-Region. Die Liste der erlaubten Regionen "
                        f"steht in jusperfect/config.py::EU_EWR_REGIONEN.")
        if self.sitzung_ttl_sekunden <= 0 or self.monatsbudget_eur <= 0:
            raise KonfigurationsFehler("Lebensdauer und Monatsbudget müssen positiv sein.")
        # Platzhalter statt Werte: derselbe Fehler wie beim Schutzgelaender,
        # nur an einer anderen Stelle. Siehe PLATZHALTER_ABLAGE.
        if self.gedaechtnis == "aws":
            for name, wert, wo in (
                ("JUSPERFECT_GEDAECHTNIS_BUCKET", self.gedaechtnis_bucket,
                 "der Name steht in der S3-Konsole (Region Frankfurt)"),
                ("JUSPERFECT_KMS_SCHLUESSEL_ID", self.kms_schluessel_id or "",
                 "die Key ID steht in der KMS-Konsole auf der Seite des Schlüssels"),
            ):
                if wert.strip().lower() in PLATZHALTER_ABLAGE:
                    raise KonfigurationsFehler(
                        f"{name} steht auf '{wert}'. Das ist der Platzhalter aus der "
                        f"Startdatei, kein Wert: {wo}. Anleitung: AWS-EINRICHTEN.md, "
                        "Schritt 11."
                    )
        if self.gedaechtnis == "aws" and not (
            self.gedaechtnis_bucket and self.kms_schluessel_id
        ):
            raise KonfigurationsFehler(
                "Für JUSPERFECT_GEDAECHTNIS=aws sind JUSPERFECT_GEDAECHTNIS_BUCKET und "
                "JUSPERFECT_KMS_SCHLUESSEL_ID nötig. Die Löschung wird nicht über eine "
                "Inaktivitätsfrist, sondern kontrolliert über den Aktenstatus in jurnodes ausgelöst."
            )
        if self.betriebsart == "aws" and self.gedaechtnis == "lokal":
            raise KonfigurationsFehler("In AWS ist das lokale Aktengedächtnis nicht zulässig.")
        # Das lokale Gedächtnis schreibt unverschlüsselten Klartext auf die
        # Platte – gut genug für erfundene Testakten, nicht für Mandantendaten.
        # Ohne diese Prüfung genügte es, in einer Startdatei den Adapter auf das
        # Kanzleilaufwerk umzustellen: Das Gedächtnis bliebe eingeschaltet, und
        # echte Akten lägen ungeschützt im Programmordner, ohne dass jemand
        # etwas davon merkt.
        if self.gedaechtnis == "lokal" and self.jurnodes_adapter != "fixture":
            raise KonfigurationsFehler(
                "Das lokale Aktengedächtnis speichert unverschlüsselt auf der Festplatte und "
                "ist deshalb nur zusammen mit den Testakten zulässig "
                "(JUSPERFECT_JURNODES_ADAPTER=fixture). Für echte Akten "
                "JUSPERFECT_GEDAECHTNIS=aws mit Bucket und Kanzleischlüssel setzen."
            )
        # Dieselbe Grenze wie beim Gedächtnis, nur für das Schutzgeländer.
        #
        # Die Guardrail war bisher nur in der AWS-Aufstellung zwingend. Im
        # örtlichen Betrieb war sie es nicht - und genau dort führt der Weg zur
        # ersten echten Akte: in der Startdatei den Adapter auf das
        # Kanzleilaufwerk stellen. Das Programm startete dann ohne
        # Schutzgeländer, und niemand sah es. Aus der Kanzlei: "Schließe die
        # Guardrail-Lücke."
        #
        # Nur mit Bedrock: Die Guardrail sitzt vor dem Modell. Wo kein Modell
        # gefragt wird, gibt es nichts zu schützen - eine echte Akte nur zu
        # lesen, ohne dass etwas hinausgeht, bleibt zulässig.
        # Ein Platzhalter ist schlimmer als eine Luecke: Die Pruefung unten
        # ist zufrieden, das Programm startet, und erst der erste Modellaufruf
        # scheitert - im Browser als graue Flaeche ohne Grund.
        #
        # Aus der Kanzlei am 25.09.2026: Im Konto stand "IHRE-KENNUNG". Das
        # war woertlich der Platzhalter aus der Anleitung; "abcd1234efgh" aus
        # AWS-EINRICHTEN.md ist der zweite Kandidat. Wer eine Anleitung
        # schreibt, muss damit rechnen, dass sie befolgt wird.
        if self.guardrail_id and self.guardrail_id.strip().lower() in PLATZHALTER_GELAENDER:
            raise KonfigurationsFehler(
                f"JUSPERFECT_GUARDRAIL_ID steht auf '{self.guardrail_id}'. Das ist der "
                "Platzhalter aus der Anleitung, keine Kennung. Die echte steht in der "
                "AWS-Konsole: Bedrock (Region Frankfurt) -> Guardrails -> Ihr Gelaender "
                "-> 'Guardrail ID', eine kurze Folge aus Buchstaben und Ziffern. "
                "Eintragen mit JURNODES-ZUGANG.bat."
            )
        if self.anbieter == "bedrock" and self.jurnodes_adapter != "fixture" and not self.guardrail_id:
            raise KonfigurationsFehler(
                "Mit echten Akten ist ein Bedrock-Guardrail zwingend; JUSPERFECT_GUARDRAIL_ID "
                "fehlt. Es ist die letzte Stelle, an der eine entgleiste Frage oder Antwort "
                "noch aufgehalten wird. Einrichten: siehe AWS-EINRICHTEN.md. Zum Ausprobieren "
                "ohne Guardrail die erfundenen Testakten nehmen "
                "(JUSPERFECT_JURNODES_ADAPTER=fixture)."
            )
        # Fail closed im Echtbetrieb: Was echte Mandantendaten sieht, muss
        # vollständig abgesichert sein. Eine halb eingerichtete Umgebung
        # startet nicht, statt unbemerkt ungeschützt zu laufen.
        if self.betriebsart == "aws":
            if not self.guardrail_id:
                raise KonfigurationsFehler(
                    "Im Echtbetrieb ist ein Bedrock-Guardrail zwingend; JUSPERFECT_GUARDRAIL_ID fehlt."
                )
            if self.jurnodes_adapter == "fixture":
                raise KonfigurationsFehler(
                    "Im Echtbetrieb sind die Testakten nicht zulässig; "
                    "JUSPERFECT_JURNODES_ADAPTER muss http oder webdav sein."
                )
            if self.speicher == "aws" and not self.kms_schluessel_id:
                raise KonfigurationsFehler(
                    "Im Echtbetrieb müssen Sitzungsdaten mit dem Kanzleischlüssel verschlüsselt "
                    "werden; JUSPERFECT_KMS_SCHLUESSEL_ID fehlt."
                )
        if self.gedaechtnis_max_fragen <= 0:
            raise KonfigurationsFehler("JUSPERFECT_GEDAECHTNIS_MAX_FRAGEN muss positiv sein.")
        if self.gedaechtnis_max_chronologie <= 0:
            raise KonfigurationsFehler("JUSPERFECT_GEDAECHTNIS_MAX_CHRONOLOGIE muss positiv sein.")
        if self.gedaechtnis_uebergangsfrist_tage < 0:
            raise KonfigurationsFehler("JUSPERFECT_GEDAECHTNIS_UEBERGANGSFRIST_TAGE darf nicht negativ sein.")
        if self.dialog_max_runden <= 0:
            raise KonfigurationsFehler("JUSPERFECT_DIALOG_MAX_RUNDEN muss positiv sein.")
        if self.perfect_shield_aktiv:
            raise KonfigurationsFehler(
                "Perfect Shield hat noch keine technische Anonymisierungs-Schnittstelle zu jusperfect; "
                "JUSPERFECT_PERFECT_SHIELD darf bis zur geprüften Anbindung nicht aktiviert werden."
            )

    @property
    def modell_fuer_triage(self) -> str:
        return self.modell_fuer("triage")

    def modell_fuer(self, funktion: str) -> str:
        """Das Modell für eine Funktion – eigene Wahl, sonst modell_id.

        Triage fällt zusätzlich auf modell_id_klein zurück (das kleine, schnelle
        Modell für Klassifikation), wenn nichts Eigenes gesetzt ist.
        """
        je_funktion = {
            "frage": self.modell_frage,
            "analyse": self.modell_analyse,
            "triage": self.modell_triage or self.modell_id_klein,
            "entwurf": self.modell_entwurf,
            "gedaechtnis": self.modell_gedaechtnis or self.modell_id_klein,
        }
        return (je_funktion.get(funktion) or "").strip() or self.modell_id

    def _modellquellen(self) -> dict[str, tuple[str, str]]:
        """Jede gesetzte Modellkennung mit der Einstellung, aus der sie stammt.

        Gebraucht für die Profilprüfung: Sie muss **jede** Kennung ansehen,
        nicht nur die eine. Wer ein zweites Modell je Aufgabe einträgt – genau
        der Fall, für den es die Felder gibt –, käme sonst an ihr vorbei.
        """
        quellen = {
            "modell_id": ("JUSPERFECT_MODELL_ID", self.modell_id),
            "modell_id_klein": ("JUSPERFECT_MODELL_ID_KLEIN", self.modell_id_klein),
            "frage": ("JUSPERFECT_MODELL_FRAGE", self.modell_frage),
            "analyse": ("JUSPERFECT_MODELL_ANALYSE", self.modell_analyse),
            "triage": ("JUSPERFECT_MODELL_TRIAGE", self.modell_triage),
            "entwurf": ("JUSPERFECT_MODELL_ENTWURF", self.modell_entwurf),
            "gedaechtnis": ("JUSPERFECT_MODELL_GEDAECHTNIS", self.modell_gedaechtnis),
        }
        return {f: (name, wert) for f, (name, wert) in quellen.items() if wert.strip()}

    def modelle_uebersicht(self) -> dict[str, str]:
        """Welches Modell je Funktion tatsächlich genutzt wird – für den Überblick."""
        return {f: self.modell_fuer(f) for f in ("frage", "analyse", "triage", "entwurf", "gedaechtnis")}

    def modell_herkunft(self, funktion: str) -> str:
        """Aus welcher Einstellung die Kennung für diese Funktion stammt.

        Weist AWS eine Kennung ab, ist die Kennung selbst nur die halbe
        Auskunft. Die andere Hälfte ist, **wo sie herkommt** – sechs
        Einstellungen kommen in Frage, und wer die falsche aufmacht, sucht
        umsonst. Aus der Kanzlei: „Die Modellkennung
        eu.anthropic.claude-haiku-4-5 kennt AWS nicht." Dass damit die
        Eingangsprüfung und das Aktengedächtnis gemeint waren und die Kennung
        in JUSPERFECT_MODELL_ID_KLEIN stand, stand nirgends.
        """
        eigen = {
            "frage": ("JUSPERFECT_MODELL_FRAGE", self.modell_frage),
            "analyse": ("JUSPERFECT_MODELL_ANALYSE", self.modell_analyse),
            "triage": ("JUSPERFECT_MODELL_TRIAGE", self.modell_triage),
            "entwurf": ("JUSPERFECT_MODELL_ENTWURF", self.modell_entwurf),
            "gedaechtnis": ("JUSPERFECT_MODELL_GEDAECHTNIS", self.modell_gedaechtnis),
        }
        name, wert = eigen.get(funktion, ("", ""))
        if wert.strip():
            return name
        if funktion in ("triage", "gedaechtnis") and self.modell_id_klein.strip():
            return "JUSPERFECT_MODELL_ID_KLEIN"
        return "JUSPERFECT_MODELL_ID"
