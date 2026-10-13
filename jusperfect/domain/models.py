"""Fachliche Datenmodelle.

Zwei Gruppen: Was aus jur|nodes kommt (Akte, Dokument, Beteiligter, Frist)
und was jusperfect daraus erzeugt (Antwort, Analyse, Entwurf). Alles, was
jusperfect erzeugt, trägt Quellen – ohne Quelle keine Aussage.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, PrivateAttr


# ── Aus jur|nodes ───────────────────────────────────────────────────────────

class Akte(BaseModel):
    id: str
    aktenzeichen: str
    bezeichnung: str
    rechtsgebiet: str = ""
    sachbearbeiter: str = ""
    status: str = "offen"


class Dokument(BaseModel):
    id: str
    akte_id: str
    titel: str
    dateiname: str
    mime_typ: str = "application/octet-stream"
    datum: date | None = None
    kategorie: str = ""
    #: In welchem Ordner der Akte das Dokument liegt - leer heisst: unmittelbar
    #: im Aktenordner. Bei mehreren Ebenen mit "/" verbunden
    #: ("Schriftsaetze/Gegenseite"). Was aus der E-Akte kommt - Mails, deren
    #: Anlagen und Vermerke - traegt "E-Akte"; es liegt in einem anderen Baum
    #: als die Dateien, und das soll man sehen.
    #:
    #: Eingefuehrt am 12.10.2026: In X-100-2026 standen 55 Eintraege aus acht
    #: Ordnern in einer Reihe. Ein Aktenordner, der seine Gliederung verliert,
    #: ist schwerer zu lesen als ein Papierordner mit Registern.
    ordner: str = ""
    groesse_bytes: int | None = None


class Beteiligter(BaseModel):
    id: str
    name: str
    rolle: str                      # Mandant, Gegner, Versicherung, RSV, Zeuge …
    organisation: str = ""
    kontakt: str = ""


class Frist(BaseModel):
    id: str
    bezeichnung: str
    datum: date
    status: str = "offen"


# ── Verarbeitung ────────────────────────────────────────────────────────────

class Seite(BaseModel):
    nummer: int
    text: str


class Passage(BaseModel):
    """Ein Textausschnitt mit eindeutiger Kennung, die die KI zitieren muss."""
    kennung: str                    # z. B. D2-S3-P1
    dokument_id: str
    dokument_titel: str
    seite: int
    text: str
    # Das Datum des Dokuments aus den Stammdaten - nicht aus seinem Text.
    #
    # Es steht hier, weil es dem Modell sonst nie zu Gesicht kommt. Am
    # 28.09.2026 fehlten in fuenf Pruefbogenlaeufen mit drei Modellen dieselben
    # fuenf Tage im Zeitstrahl. Der Grund war weder das Modell noch der Auftrag
    # noch der Filter: Die fuenf Daten stehen in akte.json im Feld "datum" und
    # in keinem Dokumenttext. Das Material nannte Titel und Seite, nie das
    # Datum - das Modell sollte etwas aufschreiben, was es nicht sehen konnte.
    #
    # Optional, weil nicht jede Quelle ein Datum hat: Kanzleiwissen hat keines,
    # und ein Dokument ohne Datum in jur|nodes gibt es auch.
    dokument_datum: date | None = None


class Quelle(BaseModel):
    # Die genaue Stelle innerhalb der Passage, in Zeichen ab deren Anfang.
    # Eine Fundstelle zeigt auf eine Passage von bis zu 1.500 Zeichen; wer sie
    # nachliest, sucht darin noch einmal von Hand. treffer_start/treffer_ende
    # nennen den Satz, der die Aussage traegt, marken die harten Angaben darin
    # (Datum, Betrag, Eigenname). Alles drei ist optional: Findet sich keine
    # hinreichend gute Stelle, bleibt es bei der ganzen Passage - eine falsch
    # markierte Stelle waere schlimmer als eine unmarkierte.
    kennung: str
    dokument_id: str
    dokument_titel: str
    seite: int
    zitat: str = ""
    treffer_start: int | None = None
    treffer_ende: int | None = None
    marken: list[tuple[int, int]] = Field(default_factory=list)


class Kosten(BaseModel):
    eingabe_tokens: int = 0
    ausgabe_tokens: int = 0
    betrag_eur: float = 0.0


# ── Ergebnisse von jusperfect ────────────────────────────────────────────────

class Antwort(BaseModel):
    text: str
    quellen: list[Quelle] = Field(default_factory=list)
    hinweise: list[str] = Field(default_factory=list)
    modell: str = ""
    kosten: Kosten = Field(default_factory=Kosten)


# ── Dauerhaftes Aktengedächtnis ────────────────────────────────────────────

class GedaechtnisDokument(BaseModel):
    """Ein bereits extrahiertes Dokument im kanzleieigenen Fallgedächtnis."""
    dokument_id: str
    titel: str
    # Die Nummer, die in jeder Fundstellenkennung steht (``D12-S1-P3``). Sie
    # wird beim Aufnehmen einmal vergeben und danach nie wieder verändert -
    # auch dann nicht, wenn ein davorliegendes Dokument entfällt. Früher ergab
    # sie sich aus der Stellung in der Liste; dann zeigte nach jedem Entfernen
    # jede gespeicherte Kennung dahinter auf das falsche Dokument, und alles
    # Abgeleitete musste verworfen werden. Eine feste Nummer ist die
    # Voraussetzung dafür, dass ein Gedächtnis über Jahre wachsen kann.
    # 0 bedeutet: noch nicht vergeben (Gedächtnis aus Fassung 3).
    nummer: int = 0
    seiten: list[Seite] = Field(default_factory=list)
    ocr: bool = False
    # Das Datum des Dokuments aus den Stammdaten von jur|nodes.
    #
    # Es steht hier, weil das Einlesen NICHT ueber die Dokumente der Akte
    # geht, sondern ueber die Auszuege im Gedaechtnis: ``_passagen`` baut sich
    # aus jedem Auszug ein Dokument zusammen, und was hier fehlt, fehlt dort.
    # Am 28.09.2026 war das Datum in Passage und Material schon vorgesehen -
    # und kam trotzdem nicht an, weil es an dieser Stelle verlorenging.
    #
    # Ein Gedaechtnis aus einer aelteren Fassung hat hier None. Das ist
    # hinnehmbar: Beim naechsten Einlesen eines Dokuments wird es gefuellt,
    # und ohne Datum verhaelt sich alles wie vorher.
    datum: date | None = None
    hinzugefuegt_am: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def zeichen(self) -> int:
        return sum(len(seite.text) for seite in self.seiten)


class GedaechtnisAntwort(BaseModel):
    """Nur die bereits fail-closed geprüfte Fassung einer Frage und Antwort."""
    frage: str
    antwort: str
    quellen: list[Quelle] = Field(default_factory=list)
    modell: str = ""
    zeitpunkt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChronologieEintrag(BaseModel):
    datum: str                      # ISO oder Text, wenn nur ungefähr bekannt
    ereignis: str
    quellen: list[Quelle] = Field(default_factory=list)


class Aktengedaechtnis(BaseModel):
    """Dauerhafte, aktenbezogene Arbeitskopie im eigenen Kanzlei-AWS-Konto."""

    # Die Revision, mit der GENAU DIESER Stand gelesen wurde.
    #
    # Kein Inhalt und kein Bestandteil der Ablage - ein privates Feld geht
    # weder in `model_dump_json` noch nach S3. Es haengt am Objekt, und das
    # ist der ganze Punkt (Befund F03 der Zweitpruefung, 05.10.2026): Vorher
    # fuehrte der Speicher eine gemeinsame Tabelle je Objektname. Lasen zwei
    # Vorgaenge denselben Stand und schrieb der zweite zuerst, nahm der erste
    # beim Speichern dessen neue Revision - und ueberschrieb damit eine
    # Loeschung, die er nie gesehen hatte. Die Bedingung schuetzte nichts,
    # weil sie nicht mehr zum Inhalt gehoerte, den sie schuetzen sollte.
    _revision: str | None = PrivateAttr(default=None)

    schema_version: int = 4
    akte_id: str
    aktenzeichen: str = ""
    bezeichnung: str = ""
    # Der Status aus jurnodes steuert die Aufbewahrung. Eine bloße
    # Bearbeitungspause setzt niemals selbst eine Löschfrist in Gang.
    aktenstatus: str = "offen"
    retention_reason: str = "laufende_mandatsbearbeitung"
    status_geprueft_am: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    abgeschlossen_am: datetime | None = None
    loeschung_vorgesehen_am: datetime | None = None
    dokumente: list[GedaechtnisDokument] = Field(default_factory=list)
    # Der Zähler für die festen Dokumentnummern. Er wird nur hochgezählt, nie
    # zurückgesetzt: Eine einmal vergebene Nummer gehört diesem Dokument, und
    # eine Kennung, die auf ein entferntes Dokument zeigte, soll ins Leere
    # zeigen und nicht auf ein anderes.
    letzte_dokumentnummer: int = 0
    # Welche Auszuege ausdruecklich entfernt worden sind.
    #
    # Eine Grabmarke, kein Inhalt: nur die Kennung, die in jur|nodes ohnehin
    # steht. Sie beantwortet die eine Frage, die sich sonst nicht beantworten
    # laesst - ob ein Dokument nie hier war oder bewusst entfernt wurde.
    #
    # Gebraucht wird das gegen verspaetete Ergebnisse (Befund F02.3 der
    # Zweitpruefung, 05.10.2026): Eine Antwort, die waehrend des Loeschens
    # noch unterwegs war, darf nicht hinterher wieder abgelegt werden. Ohne
    # die Marke liesse sich das nicht von einem Dokument unterscheiden, das
    # bloss noch nicht eingelesen ist.
    #
    # Wird das Dokument spaeter bewusst neu eingelesen, faellt die Marke -
    # das ist dann eine eigene Handlung des Bearbeiters.
    vergessene_dokumente: list[str] = Field(default_factory=list)
    lebenssachverhalt: str = ""
    lebenssachverhalt_quellen: list[Quelle] = Field(default_factory=list)
    verarbeitete_passagen: list[str] = Field(default_factory=list)
    fragen_antworten: list[GedaechtnisAntwort] = Field(default_factory=list)
    # Die Chronologie steht dauerhaft und wird fortgeschrieben, nicht bei jeder
    # Analyse neu erzeugt. Ein Vorgang zieht sich über Wochen; die Antwort der
    # Gegenseite soll zwei Zeilen ergänzen, nicht einen zweiten Aufruf über die
    # ganze Akte kosten.
    chronologie: list[ChronologieEintrag] = Field(default_factory=list)
    # Eigene Marke neben verarbeitete_passagen: Lebenssachverhalt und
    # Chronologie werden getrennt fortgeschrieben. Eine gemeinsame Marke
    # hiesse, dass der eine Lauf dem anderen die Arbeit wegnimmt.
    chronologie_passagen: list[str] = Field(default_factory=list)
    # Die zuletzt gelaufene Aktenanalyse. Sie kostet einen Modellaufruf ueber
    # die ganze Akte und war bis zum 05.10.2026 weg, sobald das Programm
    # geschlossen wurde - das teuerste Zwischenergebnis und das einzige, das
    # niemand aufbewahrt hat.
    analyse: Aktenanalyse | None = None
    analyse_am: datetime | None = None
    # Zwei Listen, zwei verschiedene Fragen.
    #   analyse_dokumente - was in die Analyse eingegangen IST. Daran haengt,
    #       wofuer ihre Aussagen gelten.
    #   analyse_akte_dokumente - was die Akte in jurnodes zu dem Zeitpunkt
    #       ueberhaupt enthielt. Nur daran laesst sich spaeter erkennen, ob
    #       seitdem etwas NEU dazugekommen ist. Ohne diese zweite Liste zaehlte
    #       jedes bewusst nicht vorgewaehlte Dokument - eine Rechnung etwa -
    #       bei jedem Oeffnen wieder als "neu", und die Warnung waere nach
    #       einer Woche nichts mehr wert.
    analyse_dokumente: list[str] = Field(default_factory=list)
    analyse_akte_dokumente: list[str] = Field(default_factory=list)
    # Gesetzt, wenn aus der gespeicherten Analyse nachtraeglich ein Dokument
    # entfernt wurde. Eine Analyse, der ihre Grundlage fehlt, sieht genauso
    # vollstaendig aus wie eine vollstaendige - das muss dabeistehen.
    analyse_hinweis: str = ""
    aktualisiert_am: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Chronologieergebnis(BaseModel):
    """Was ein reiner Chronologielauf zurueckgibt - ohne die uebrigen Listen."""
    chronologie: list[ChronologieEintrag] = Field(default_factory=list)
    hinweise: list[str] = Field(default_factory=list)
    modell: str = ""
    kosten: Kosten = Field(default_factory=Kosten)


class BeteiligtenEintrag(BaseModel):
    bezeichnung: str
    rolle: str
    quellen: list[Quelle] = Field(default_factory=list)


class Forderung(BaseModel):
    gegenstand: str
    betrag: str = ""
    glaeubiger: str = ""
    schuldner: str = ""
    status: str = ""
    quellen: list[Quelle] = Field(default_factory=list)


class Beweismittel(BaseModel):
    bezeichnung: str
    art: str = ""                   # Urkunde, Zeuge, Sachverständiger, Augenschein
    beweisthema: str = ""
    quellen: list[Quelle] = Field(default_factory=list)


class OffenerPunkt(BaseModel):
    beschreibung: str
    prioritaet: str = "mittel"      # hoch | mittel | niedrig
    quellen: list[Quelle] = Field(default_factory=list)


class Widerspruch(BaseModel):
    beschreibung: str
    quellen: list[Quelle] = Field(default_factory=list)


class Aktenanalyse(BaseModel):
    chronologie: list[ChronologieEintrag] = Field(default_factory=list)
    beteiligte: list[BeteiligtenEintrag] = Field(default_factory=list)
    forderungen: list[Forderung] = Field(default_factory=list)
    beweismittel: list[Beweismittel] = Field(default_factory=list)
    offene_punkte: list[OffenerPunkt] = Field(default_factory=list)
    widersprueche: list[Widerspruch] = Field(default_factory=list)
    hinweise: list[str] = Field(default_factory=list)
    modell: str = ""
    kosten: Kosten = Field(default_factory=Kosten)


class EntwurfArt(str, Enum):
    MANDANT = "mandant"
    GEGNER = "gegner"
    VERSICHERUNG = "versicherung"
    RSV = "rsv"
    MAHNUNG = "mahnung"
    AKTENVERMERK = "aktenvermerk"


ENTWURF_BEZEICHNUNG: dict[EntwurfArt, str] = {
    EntwurfArt.MANDANT: "Schreiben an den Mandanten",
    EntwurfArt.GEGNER: "Schreiben an die Gegenseite",
    EntwurfArt.VERSICHERUNG: "Schreiben an die Versicherung",
    EntwurfArt.RSV: "Schreiben an die Rechtsschutzversicherung",
    EntwurfArt.MAHNUNG: "Mahnung",
    EntwurfArt.AKTENVERMERK: "Aktenvermerk",
}


class EntwurfStatus(str, Enum):
    ENTWURF = "entwurf"
    FREIGEGEBEN = "freigegeben"
    VERWORFEN = "verworfen"


class Entwurfsfassung(BaseModel):
    """Eine fruehere Fassung eines Entwurfs - und wodurch sie abgeloest wurde.

    Aus der Kanzlei am 13.10.2026: „Hier waere dann ein Vorschaufenster sehr
    schoen, in welchem der Entwurf nach und nach entsteht und durch den Chat
    geaendert werden kann."

    Wer ueber den Chat aendert, aendert ohne Netz: Das Modell schreibt den
    Entwurf neu, und die vorige Fassung waere weg. Deshalb wird sie hier
    aufgehoben, samt der Anweisung, die zu ihrer Abloesung gefuehrt hat -
    sonst steht am Ende eine Fassung da, von der niemand mehr weiss, warum
    sie so aussieht.
    """
    nummer: int
    betreff: str
    text: str
    #: Was der Bearbeiter gesagt hat. Leer bei der ersten Fassung.
    anweisung: str = ""
    abgeloest_am: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


#: So viele Vorfassungen werden aufgehoben. Mehr waere ein Archiv im
#: Sitzungsspeicher; ein Entwurf ist bis zur Freigabe etwas Fluechtiges.
MAX_VORFASSUNGEN = 10


class Entwurf(BaseModel):
    id: str
    akte_id: str
    art: EntwurfArt
    betreff: str
    text: str
    quellen: list[Quelle] = Field(default_factory=list)
    hinweise: list[str] = Field(default_factory=list)
    status: EntwurfStatus = EntwurfStatus.ENTWURF
    erstellt_von: str
    erstellt_am: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    jurnodes_referenz: str | None = None
    modell: str = ""
    kosten: Kosten = Field(default_factory=Kosten)
    #: Die laufende Nummer der jetzigen Fassung. Faengt bei 1 an.
    fassung: int = 1
    #: Die frueheren, aelteste zuerst. Gehen nicht nach jur|nodes und nicht
    #: in die Freigabevorlage - freigegeben wird, was dasteht.
    vorfassungen: list[Entwurfsfassung] = Field(default_factory=list)


class Nutzer(BaseModel):
    id: str
    name: str
    akten: list[str] = Field(default_factory=list)   # Akten-IDs oder "*"

    def darf_akte(self, akte_id: str) -> bool:
        return "*" in self.akten or akte_id in self.akten


# ── Sitzung und Nutzung ─────────────────────────────────────────────────────

class GeladenesDokument(BaseModel):
    dokument_id: str
    titel: str
    seiten: int
    zeichen: int
    ocr: bool = False
    # Die Nummer aus dem Aktengedaechtnis, wenn es eines gibt. Ohne sie zaehlte
    # die Sitzung die Dokumente nach ihrer Reihenfolge durch - und wich damit
    # vom Gedaechtnis ab, sobald dort eine Nummer entfallen ist. Die
    # Fundstellen des Lebenssachverhalts zeigten dann in der Sitzung auf das
    # falsche Dokument. 0 heisst: kein Gedaechtnis, es gilt die Reihenfolge.
    nummer: int = 0


class DialogEintrag(BaseModel):
    """Eine geprüfte Frage-Antwort-Runde im flüchtigen Sitzungskontext."""

    frage: str = Field(max_length=4000)
    antwort: str = Field(max_length=8000)
    quellen: list[str] = Field(default_factory=list, max_length=50)
    zeitpunkt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Sitzung(BaseModel):
    """Eine Aktensitzung: ein Nutzer, eine Akte, einige geladene Dokumente.

    Der Dokumenttext selbst liegt nicht hier, sondern im Sitzungsspeicher
    (verschlüsselt, mit Ablauf). Die Sitzung kennt nur, was geladen ist.
    """
    id: str
    nutzer_id: str
    akte_id: str
    akte: Akte
    geladen: list[GeladenesDokument] = Field(default_factory=list)
    # Namen der in den Kontext gezogenen Referenzen (veröffentlichtes Material).
    referenzen: list[str] = Field(default_factory=list)
    # Nur fail-closed geprüfte Antworten. Der Verlauf läuft mit der Sitzung ab.
    dialog: list[DialogEintrag] = Field(default_factory=list)
    hinweise: list[str] = Field(default_factory=list)
    erstellt_am: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


#: Wie ein Modellaufruf ausgegangen ist. Siehe ``Nutzungseintrag.ausgang``.
AUSGANG_VERSUCHT = "versucht"            # das Material ist hinausgegangen
AUSGANG_BEANTWORTET = "beantwortet"      # eine Antwort kam zurück
AUSGANG_FEHLGESCHLAGEN = "fehlgeschlagen"   # der Anbieter hat abgelehnt oder versagt
AUSGANG_ABGEBROCHEN = "abgebrochen"      # der Strom endete vor der Antwort
AUSGANG_UNBEKANNT = "unbekannt"          # hinausgegangen, Ausgang nicht vermerkt


class Nutzungseintrag(BaseModel):
    """Wer hat wann welche Funktion auf welcher Akte genutzt – ohne Inhalte.

    Dieser Eintrag ist zugleich der Verarbeitungsnachweis: die Zeile, die
    festhält, dass etwas in den gesicherten Bedrock-Bereich hinausgegangen
    ist. Anders als bei Perfect Shield, dessen Protokoll den vollständigen –
    weil anonymisierten – Text mitschreibt, steht hier bewusst **kein**
    Aktentext. Das Material geht unverschlüsselt in den Bedrock-Bereich; es ein
    zusätzlich im Verarbeitungsnachweis abzulegen, würde auch bei aktiviertem
    Aktengedächtnis eine unnötige weitere Inhaltskopie schaffen. Statt des
    Textes stehen hier seine
    Kurzkennung (Prüfsumme und Länge) und sein Umfang – genug, um später zu
    belegen, *welches* Material *wann* an *welches* Modell ging, ohne es zu
    verdoppeln.
    """
    zeitpunkt: datetime
    nutzer_id: str
    akte_id: str
    funktion: str
    modell: str
    eingabe_tokens: int
    ausgabe_tokens: int
    betrag_eur: float
    # Nachweis-Felder (ohne Inhalte): Herkunft und Fingerabdruck des Materials.
    sitzung_id: str = ""
    material_kennung: str = ""   # kurzkennung(): sha256:12 + Länge des Materials
    aufgabe_kennung: str = ""    # kurzkennung() der Frage/Anweisung
    passagen: int = 0            # wie viele Passagen mitgingen
    antwort_zeichen: int = 0     # Länge der Antwort, nicht ihr Text
    # Welcher Versuch – und wie er ausging.
    #
    # Befund F10 der Zweitprüfung vom 05.10.2026: Der Nachweis entstand erst
    # NACH einer erfolgreichen Antwort. Ging der Aufruf schief, nachdem das
    # Material längst übertragen war, blieb das Nachweisfenster leer – und
    # „keine Zeile" las sich wie „nichts hinausgegangen".
    #
    # Seitdem gibt es je Aufruf zwei Zeilen mit derselben ``versuch_id``: eine
    # beim Hinausgehen und eine beim Ausgang. Angehängt, nicht überschrieben –
    # ein Nachweis, den man ändern kann, ist ein schwächerer Nachweis.
    versuch_id: str = ""
    ausgang: str = AUSGANG_BEANTWORTET


# ── Posteingangs-Triage ─────────────────────────────────────────────────────

class Fristausloeser(BaseModel):
    """Ein Hinweis auf eine Frist im Text – nie eine Berechnung."""
    text: str
    quellen: list[Quelle] = Field(default_factory=list)


class Triage(BaseModel):
    dokumentart: str = ""
    absender: str = ""
    kernaussage: str = ""
    fristausloeser: list[Fristausloeser] = Field(default_factory=list)
    empfohlene_schritte: list[str] = Field(default_factory=list)
    quellen: list[Quelle] = Field(default_factory=list)
    hinweise: list[str] = Field(default_factory=list)
    modell: str = ""
    kosten: Kosten = Field(default_factory=Kosten)


# ── Workflow-Packs ──────────────────────────────────────────────────────────

class PackAnforderung(BaseModel):
    """Ein Beweis oder Punkt, den eine Akte dieser Art braucht."""
    id: str
    titel: str
    pflicht: bool = True
    stichworte: list[str] = Field(default_factory=list)
    fehlt_hinweis: str = ""
    min_treffer: int = 1


class Workflowpack(BaseModel):
    """Beweisprofil eines Rechtsgebiets – austauschbares JSON, kein Code."""
    id: str
    rechtsgebiet: str = ""
    titel: str
    beschreibung: str = ""
    anforderungen: list[PackAnforderung] = Field(default_factory=list)


class PackBefund(BaseModel):
    anforderung_id: str
    titel: str
    pflicht: bool
    status: str                      # "vorhanden" | "fehlt"
    belege: list[Quelle] = Field(default_factory=list)
    hinweis: str = ""


class PackErgebnis(BaseModel):
    pack_id: str
    titel: str
    befunde: list[PackBefund] = Field(default_factory=list)
    vorhanden: int = 0
    fehlt_pflicht: int = 0
    offene_schritte: list[str] = Field(default_factory=list)
