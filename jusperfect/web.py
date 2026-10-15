"""Die HTTP-Schnittstelle – lokal mit uvicorn, in AWS hinter API Gateway in Lambda.

Alle Wege führen über ``_identitaet``: In AWS aus dem JWT-Authorizer, lokal
aus der Kopfzeile. Danach entscheidet ``Berechtigungen``. Jede fachliche
Ausnahme wird in eine Antwort mit Klartext übersetzt; Stapelspuren oder
fremde Fehlertexte erreichen die Oberfläche nicht.
"""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from jusperfect import __version__
from jusperfect.config import Einstellungen, KonfigurationsFehler
from jusperfect.domain.models import MAX_FRAGE, EntwurfArt, Kosten
from jusperfect.fehlergrenze import (
    UNBEKANNT, Fehlergrenze, ausnahmekette, protokolle_eindaemmen,
)
from jusperfect.jurnodes.base import AkteNichtGefunden, DokumentNichtGefunden, JurNodesAdapter, JurNodesFehler
from jusperfect.modellprotokoll import Befund, beim_start_pruefen
from jusperfect.ocr.base import OcrDienst
from jusperfect.providers.base import GuardrailEingriff, LLMProvider, ProviderFehler
from jusperfect.security.approval import FreigabeUngueltig, Freigabestelle, text_pruefsumme
from jusperfect.security.berechtigungen import Berechtigungen, UnbekannterNutzer, ZugriffVerweigert
from jusperfect.security.identitaet import Identitaet, NichtAngemeldet, aus_cognito_ereignis, aus_kopfzeile
from jusperfect.security.protokoll import MAX_WERT_LAENGE, ereignis, protokoll, stoerung
from jusperfect.services.analyse import AktenZuGross, AnalyseFehler, Analysedienst
from jusperfect.services.fundstelle import treffer_finden
from jusperfect.services.quellen import ohne_belege
from jusperfect.services.auftraege import AuftragFehler, Auftragsdienst
from jusperfect.services.auftragsvorschlag import Vorschlagsdienst, VorschlagFehler
from jusperfect.services.ausgang import Ausgang
from jusperfect.services.posteingang import PosteingangFehler, Posteingangsdienst
from jusperfect.services import promptbibliothek
from jusperfect.services.promptbibliothek import BibliothekFehler
from jusperfect.services.referenzen import ReferenzFehler, Referenzendienst
from jusperfect.services.entwuerfe import (
    EntwurfFehler, EntwurfNichtGefunden, Entwurfsdienst, freigabevorlage,
)
from jusperfect.services.kosten import BudgetErschoepft, Kostenwaechter
from jusperfect.security import zweiter_faktor as zf
from jusperfect.services.abschluss import AbschlussFehler, Abschlussdienst
from jusperfect.services.aufbewahrung import (FRAGE as AUFBEWAHRUNG_FRAGE,
                                              AufbewahrungFehler, Aufbewahrungsdienst)
from jusperfect.services.aufsicht import Aufsichtsdienst
from jusperfect.services import briefbogen
from jusperfect.services.briefbogen import BriefbogenFehler
from jusperfect.services.gedaechtnis import Gedaechtnisdienst
from jusperfect.services.selbsttest import (
    Selbsttest, gelaender_anprobieren, modelle_anprobieren)
from jusperfect.services.sitzung import SitzungNichtGefunden, Sitzungsdienst
from jusperfect.services.workflow import PackNichtGefunden, WorkflowFehler
from jusperfect.speicher.base import SitzungsSpeicher, SpeicherFehler
from jusperfect.gedaechtnis.base import GedaechtnisFehler, GedaechtnisSpeicher

STATISCH = Path(__file__).parent / "static"
_log = protokoll("web")


# ── Aufbau ──────────────────────────────────────────────────────────────────

def _speicher_bauen(e: Einstellungen) -> SitzungsSpeicher:
    if e.speicher == "aws":
        from jusperfect.speicher.aws import AwsSpeicher

        return AwsSpeicher(e.dynamodb_tabelle, e.s3_bucket, e.aws_region, e.kms_schluessel_id,
                           e.sitzung_ttl_sekunden, e.entwurf_ttl_sekunden)
    from jusperfect.speicher.lokal import LokalerSpeicher

    return LokalerSpeicher(e.sitzung_ttl_sekunden, e.entwurf_ttl_sekunden)


def _berechtigungen_bauen(e: Einstellungen) -> Berechtigungen:
    if e.identitaet == "cognito":
        from jusperfect.security.berechtigungen import DynamoDbBerechtigungen

        return DynamoDbBerechtigungen(e.dynamodb_tabelle, e.aws_region, e.gruppe_alle_akten)
    from jusperfect.security.berechtigungen import DateiBerechtigungen

    assert e.nutzer_datei is not None
    return DateiBerechtigungen.aus_datei(e.nutzer_datei, e.gruppe_alle_akten)


def _adapter_bauen(e: Einstellungen, freigabestelle: Freigabestelle) -> JurNodesAdapter:
    if e.jurnodes_adapter == "http":
        from jusperfect.jurnodes.http_adapter import HttpJurNodesAdapter
        from jusperfect.security.geheimnisse import (jurnodes_benutzer, jurnodes_schluessel,
                                                      jurnodes_token)

        # Zwei Angaben, nicht eine: jur|nodes verlangt Benutzer UND Schluessel.
        # Hier stand nur das Token - ein Rest der frueheren Annahme, die
        # Anmeldung laufe ueber ein Bearer-Token.
        return HttpJurNodesAdapter.aus_einstellungen(
            e, freigabestelle, jurnodes_token(e),
            benutzer=jurnodes_benutzer(e), schluessel=jurnodes_schluessel())
    if e.jurnodes_adapter == "webdav":
        from jusperfect.jurnodes.webdav_adapter import WebDavJurNodesAdapter

        return WebDavJurNodesAdapter(Path(e.jurnodes_webdav_pfad), freigabestelle, schreibbar=True,
                                    archiv_kennung=e.archiv_kennung)
    from jusperfect.jurnodes.fixture_adapter import FixtureJurNodesAdapter

    return FixtureJurNodesAdapter(e.fixture_pfad, freigabestelle, schreibbar=True)


def _ocr_bauen(e: Einstellungen) -> OcrDienst:
    if e.ocr == "textract":
        from jusperfect.ocr.textract import TextractOcr

        return TextractOcr(e.aws_region, e.s3_bucket, e.kms_schluessel_id)
    from jusperfect.ocr.base import KeinOcr

    return KeinOcr()


def _gedaechtnisspeicher_bauen(e: Einstellungen,
                               adapter: JurNodesAdapter) -> GedaechtnisSpeicher | None:
    if e.gedaechtnis == "aus":
        return None
    if e.gedaechtnis == "akte":
        from jusperfect.gedaechtnis.akte import AkteGedaechtnisSpeicher

        return AkteGedaechtnisSpeicher(adapter)
    if e.gedaechtnis == "aws":
        from jusperfect.gedaechtnis.aws import AwsGedaechtnisSpeicher

        assert e.kms_schluessel_id is not None
        return AwsGedaechtnisSpeicher(e.gedaechtnis_bucket, e.aws_region, e.kms_schluessel_id)
    from jusperfect.gedaechtnis.lokal import LokalerGedaechtnisSpeicher

    return LokalerGedaechtnisSpeicher(e.gedaechtnis_pfad)


class Dienste:
    def __init__(self, e: Einstellungen, *, provider: LLMProvider | None = None, adapter: JurNodesAdapter | None = None,
                 speicher: SitzungsSpeicher | None = None, berechtigungen: Berechtigungen | None = None,
                 ocr: OcrDienst | None = None, freigabestelle: Freigabestelle | None = None,
                 gedaechtnis_speicher: GedaechtnisSpeicher | None = None) -> None:
        self.einstellungen = e
        # Wird beim Start gesetzt (app_erstellen); ohne Bedrock bleibt es None.
        self.modellprotokoll: Befund | None = None
        self.freigabestelle = freigabestelle or Freigabestelle()
        self.speicher = speicher or _speicher_bauen(e)
        self.berechtigungen = berechtigungen or _berechtigungen_bauen(e)
        self.adapter = adapter or _adapter_bauen(e, self.freigabestelle)
        self.ocr = ocr or _ocr_bauen(e)
        if provider is None:
            from jusperfect.providers.aufbau import provider_erstellen

            provider = provider_erstellen(e)
        self.provider = provider
        self.kosten = Kostenwaechter(self.speicher, e.monatsbudget_eur, e.usd_eur_kurs)
        self.ausgang = Ausgang(self.provider, self.kosten, e)
        # ``None`` kann sowohl "nicht injiziert" als auch "aus" bedeuten;
        # nur eine aktivierte Konfiguration baut deshalb selbst einen Speicher.
        if gedaechtnis_speicher is None and e.gedaechtnis != "aus":
            gedaechtnis_speicher = _gedaechtnisspeicher_bauen(e, self.adapter)
        self.gedaechtnis = Gedaechtnisdienst(gedaechtnis_speicher, self.speicher, self.ausgang, e)
        wissen = None
        if e.kanzleiwissen_kb_id:
            from jusperfect.services.kanzleiwissen import Kanzleiwissen

            wissen = Kanzleiwissen(e.kanzleiwissen_kb_id, e.aws_region)
        from jusperfect.services.workflow import Workflowdienst

        self.sitzungen = Sitzungsdienst(
            self.adapter, self.speicher, self.berechtigungen, self.ocr,
            self.gedaechtnis, e.dialog_max_runden,
        )
        self.analyse = Analysedienst(self.ausgang, e, wissen)
        self.entwuerfe = Entwurfsdienst(self.ausgang, self.speicher, self.adapter,
                                        self.freigabestelle, e, self.berechtigungen)
        self.workflow = Workflowdienst()
        self.abschluss = Abschlussdienst(self.gedaechtnis, self.adapter, self.berechtigungen,
                                         self.speicher, self.freigabestelle, e)
        self.aufbewahrung = Aufbewahrungsdienst(self.gedaechtnis, self.berechtigungen, e)
        # Der zweite Faktor: Geheimnisse auf der Platte, Bestaetigungen nur im
        # Arbeitsspeicher. Ein Neustart verlangt ihn erneut - das ist gewollt.
        self.zf_ablage = zf.Geheimnisablage(e.zweiter_faktor_datei)
        self.zf_bestaetigt = zf.Bestaetigungen()
        self.aufsicht = Aufsichtsdienst(self.gedaechtnis, self.adapter, self.berechtigungen)
        self.posteingang = Posteingangsdienst(e, self.ocr)
        self.auftraege = Auftragsdienst(e.auftrag_ordner)
        self.auftragsvorschlag = Vorschlagsdienst(self.ausgang)
        self.referenzen = Referenzendienst(e.referenz_ordner, self.ocr)


# ── Anfragemodelle ──────────────────────────────────────────────────────────

class ZfCode(BaseModel):
    """Ein Einmalkennwort aus der Authentifizierungs-App."""

    code: str


class LaeuftNoch(BaseModel):
    """Die Antwort auf die Frage, ob die Akte noch läuft."""

    laeuft_noch: bool


class SitzungAnlegen(BaseModel):
    akte_id: str


class FundstelleAnfrage(BaseModel):
    """Welche Passage, und welcher Satz soll darin gefunden werden.

    Auf Modulebene und nicht in app_erstellen: Mit ``from __future__ import
    annotations`` sind alle Typangaben Zeichenketten, die FastAPI erst zur
    Laufzeit auf Modulebene aufloest. Eine dort verschachtelte Klasse findet es
    nicht - und behandelt den Rumpf still als Abfrageparameter. Die Meldung
    ("Field required: query.daten") zeigt dabei auf etwas ganz anderes.
    """

    kennung: str
    aussage: str = ""


class DokumenteLaden(BaseModel):
    dokument_ids: list[str] = Field(min_length=1)
    #: Auch das neu einlesen, was schon in der Arbeitsakte liegt - und sagen,
    #: ob sich etwas geaendert hat (Befund R01 vom 15.10.2026).
    neu_laden: bool = False


class FrageStellen(BaseModel):
    frage: str = Field(min_length=1, max_length=MAX_FRAGE)


class TriageAnfrage(BaseModel):
    dokument_id: str


class EntwurfAnlegen(BaseModel):
    art: EntwurfArt
    anweisung: str = Field(default="", max_length=MAX_FRAGE)
    empfaenger: str = Field(default="", max_length=400)
    muster: str = Field(default="", max_length=20000)
    auftrag: str = Field(default="", max_length=300)  # Name eines eigenen Auftrags; sein Material wird Muster


class AuftragsvorschlagAnfrage(BaseModel):
    entwurf_id: str = Field(max_length=100)
    # Die Anweisung, mit der der Entwurf erstellt wurde. Sie ist das einzige,
    # was hinausgeht - der Entwurf selbst und die Akte bleiben hier.
    anweisung: str = Field(default="", max_length=MAX_FRAGE)


class AuftragAnlegen(BaseModel):
    name: str = Field(max_length=300)
    text: str = Field(max_length=60000)


class ReferenzenWaehlen(BaseModel):
    namen: list[str] = Field(default_factory=list, max_length=20)


class BlattEinstellen(BaseModel):
    """Vier Werte; jeder leer bedeutet „wie in der Vorlage"."""
    textbeginn_mm: float | None = Field(default=None, ge=0, le=250)
    schrift: str = Field(default="", max_length=80)
    groesse_pt: float | None = Field(default=None, ge=6, le=24)
    zeilenabstand: float | None = Field(default=None, ge=0.8, le=3)


class EntwurfAendern(BaseModel):
    anweisung: str = Field(max_length=MAX_FRAGE)


class EntwurfBearbeiten(BaseModel):
    betreff: str = Field(default="", max_length=400)
    text: str = Field(min_length=1, max_length=60000)


class EntwurfFreigeben(BaseModel):
    bestaetigung: bool
    # Ueber die ganze Freigabevorlage (Akte, Art, Betreff, Text), nicht nur
    # ueber den Text - siehe services/entwuerfe.freigabevorlage.
    freigabe_pruefsumme: str = Field(min_length=64, max_length=64)


class AbschlussAusfuehren(BaseModel):
    bestaetigung: bool
    text_pruefsumme: str = Field(min_length=64, max_length=64)


class PromptAblegen(BaseModel):
    titel: str = Field(default="", max_length=promptbibliothek.MAX_TITEL)
    text: str = Field(max_length=promptbibliothek.MAX_ZEICHEN)
    #: Leer heisst: das Rechtsgebiet der Akte.
    rechtsgebiet: str = Field(default="", max_length=120)


class PromptVergessen(BaseModel):
    titel: str = Field(max_length=promptbibliothek.MAX_TITEL)
    rechtsgebiet: str = Field(default="", max_length=120)


class PackAnfrage(BaseModel):
    pack_id: str = Field(default="", max_length=64)


# ── Anwendung ───────────────────────────────────────────────────────────────

def app_erstellen(einstellungen: Einstellungen | None = None, dienste: Dienste | None = None) -> FastAPI:
    e = einstellungen or (dienste.einstellungen if dienste else Einstellungen.aus_umgebung())
    d = dienste or Dienste(e)
    # Bevor irgendetwas hinausgeht: Schreibt AWS die Modellaufrufe mit? Dann
    # laege der Aktentext in einer Protokollablage neben der Akte, und das
    # Programm startet nicht (Grundsatz 5, siehe modellprotokoll.py). Der
    # Befund steht danach im Status, damit die Kanzlei nicht raten muss.
    d.modellprotokoll = beim_start_pruefen(e)
    app = FastAPI(title="jusperfect", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.dienste = d

    def identitaet(request: Request) -> Identitaet:
        try:
            if e.identitaet == "cognito":
                return aus_cognito_ereignis(request.scope.get("aws.event"))
            if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
                # Sicherung gegen Fehlkonfiguration: In Lambda nie der Kopfzeile trauen.
                raise NichtAngemeldet("Kopfzeilen-Identität ist in Lambda nicht zulässig.")
            ident = aus_kopfzeile(request.headers.get("x-jusperfect-nutzer"))
            d.berechtigungen.nutzer(ident)  # unbekannte Kennung -> 403
            _zweiten_faktor_verlangen(request, ident)
            return ident
        except NichtAngemeldet as ex:
            raise HTTPException(401, str(ex)) from ex
        except UnbekannterNutzer as ex:
            raise HTTPException(403, str(ex)) from ex

    #: Die Wege, die ohne zweiten Faktor offenstehen muessen - sonst kaeme
    #: man nie dahin, ihn zu zeigen.
    OHNE_ZWEITEN_FAKTOR = ("/api/anmeldung/",)

    def _zweiten_faktor_verlangen(request: Request, ident: Identitaet) -> None:
        """Ohne zweiten Faktor kein Zugriff – wenn er eingeschaltet ist.

        Die Sperre sitzt in der Identitaet und nicht an den einzelnen Wegen:
        Ein halb geschuetztes Programm ist keines, und ein vergessener
        Endpunkt waere genau das Loch, gegen das der Faktor gebaut ist.

        Der Code 428 sagt der Oberflaeche, dass noch etwas zu tun ist - im
        Unterschied zu 401 (nicht angemeldet) und 403 (nicht berechtigt).
        """
        if e.zweiter_faktor != "an":
            return
        if request.url.path.startswith(OHNE_ZWEITEN_FAKTOR):
            return
        if d.zf_bestaetigt.gilt(ident.nutzer_id):
            return
        raise HTTPException(
            428,
            "Zweiter Faktor erforderlich."
            if d.zf_ablage.eingerichtet(ident.nutzer_id)
            else "Zweiter Faktor ist noch nicht eingerichtet.")

    # Fachliche Fehler -> verständliche Antworten
    _abbildung: list[tuple[type[Exception], int]] = [
        (ZugriffVerweigert, 403), (UnbekannterNutzer, 403), (FreigabeUngueltig, 403),
        (SitzungNichtGefunden, 404), (EntwurfNichtGefunden, 404), (AkteNichtGefunden, 404), (DokumentNichtGefunden, 404),
        (PackNichtGefunden, 404), (WorkflowFehler, 422), (PosteingangFehler, 422), (AuftragFehler, 422),
        (VorschlagFehler, 422),
        # Kein Serverfehler: Die Akte ist in Ordnung, sie passt nur nicht in
        # einen Aufruf. Die Oberflaeche zeigt den Text unveraendert an.
        (AktenZuGross, 422),
        (ReferenzFehler, 422), (GedaechtnisFehler, 422), (AbschlussFehler, 409),
        (BibliothekFehler, 422), (BriefbogenFehler, 422),
        (BudgetErschoepft, 429), (GuardrailEingriff, 422), (AnalyseFehler, 422), (EntwurfFehler, 422),
        (KonfigurationsFehler, 500), (JurNodesFehler, 502), (ProviderFehler, 502), (SpeicherFehler, 503),
    ]

    def _status_fuer(exc: Exception) -> tuple[int, str]:
        for typ, status in _abbildung:
            if isinstance(exc, typ):
                return status, str(exc)
        return 500, UNBEKANNT

    # Je Fehlertyp ein eigener Handler, nicht mehr einer fuer ``Exception``.
    #
    # Der Unterschied ist nicht Geschmack, sondern Befund F01 der
    # Zweitprueferin: Ist ein Handler fuer ``Exception`` eingetragen, sendet
    # Starlettes ServerErrorMiddleware zwar dessen Antwort - und **wirft die
    # Ausnahme danach erneut**. Uvicorn protokolliert daraufhin den
    # vollstaendigen Traceback samt Ursache, und in der Ursache steht der
    # Wortlaut von AWS. Ein eigener Handler je Typ wird von
    # ExceptionMiddleware behandelt und nicht erneut geworfen.
    def _handler(status: int):
        async def behandeln(request: Request, exc: Exception) -> JSONResponse:
            return JSONResponse({"fehler": str(exc)}, status_code=status)
        return behandeln

    for _typ, _status in _abbildung:
        app.add_exception_handler(_typ, _handler(_status))

    # Und die Grenze darum: Was dennoch durchkommt - ein Programmfehler, ein
    # Fehler aus einer anderen Schicht -, wird hier inhaltsfrei beantwortet
    # und inhaltsfrei protokolliert. Nach aussen tritt keine Ausnahme.
    protokolle_eindaemmen()
    app.add_middleware(Fehlergrenze, status_fuer=_status_fuer)

    # ── Status ────────────────────────────────────────────────────────────

    @app.get("/api/status")
    def status(ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        nutzer = d.berechtigungen.nutzer(ident)
        return {
            "version": __version__, "betriebsart": e.betriebsart, "anbieter": e.anbieter, "modell": e.modell_id,
            "region": e.aws_region, "guardrail": bool(e.guardrail_id), "ocr": e.ocr, "jurnodes": e.jurnodes_adapter,
            "modelle": e.modelle_uebersicht(),
            "kanzleiwissen": bool(e.kanzleiwissen_kb_id), "nutzer": {"id": nutzer.id, "name": nutzer.name},
            # Die Grenze, an der die Aktenanalyse abbricht. Der Explorer zeigt
            # sie beim Auswaehlen an; eine fest eingetragene Zahl in der
            # Oberflaeche wuerde bei geaenderter Einstellung luegen.
            "max_passagen_zeichen": e.max_passagen_zeichen,
            # Welche Woerter im Titel ein Dokument nicht vorwaehlen. Die Liste
            # gehoert in die Oberflaeche, weil dort die Auswahl geschieht -
            # und als LISTE, nicht als fertiges Ergebnis: Der Anwender soll
            # sehen, WELCHES Wort gegriffen hat.
            "nicht_vorwaehlen": list(e.nicht_vorwaehlen),
            "kosten": d.kosten.stand(),
            # Vorschaltstufe Perfect Shield: angelegt, aber noch nicht scharf.
            # Schreibt AWS die Modellaufrufe mit? Der Befund vom Start. Ohne
            # Bedrock gibt es nichts mitzuschreiben, dann steht hier nichts.
            "modellprotokoll": (
                {"zustand": d.modellprotokoll.zustand, "satz": d.modellprotokoll.satz}
                if d.modellprotokoll else None),
            "perfect_shield_aktiv": e.perfect_shield_aktiv,
            "posteingang_aktiv": d.posteingang.aktiv,
            "auftraege_aktiv": d.auftraege.aktiv,
            "referenzen_aktiv": d.referenzen.aktiv,
            "gedaechtnis_aktiv": d.gedaechtnis.aktiv,
            # Wo es liegt, steht in der Oberflaeche an der Auswahl. Seit das
            # Gedaechtnis auch in der Akte liegen kann, waere "bei jusperfect,
            # nicht in jur|nodes" dort je nach Einstellung schlicht falsch.
            "gedaechtnis_ort": e.gedaechtnis,
            # Die Aufsicht führt Akten zusammen und ist deshalb nur für
            # Berechtigte mit Zugriff auf alle Akten sichtbar.
            "verwaltung": "*" in nutzer.akten,
            # Haufe-Recherche: Direktlink (Browser des Nutzers), keine Zugangsdaten hier.
            "haufe_aktiv": bool(e.haufe_url),
            "haufe": {"url": e.haufe_url, "suche_param": e.haufe_suche_param},
            # Gesetzestexte: derselbe Weg wie Haufe - ein Sprung in den
            # Browser, nichts im Programmordner.
            "gesetze_aktiv": bool(e.gesetze_url),
            "gesetze": {"url": e.gesetze_url, "muster": e.gesetze_muster},
        }

    @app.post("/api/sitzungen/{sitzung_id}/fundstelle")
    def fundstelle(sitzung_id: str, daten: FundstelleAnfrage,
                   ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Wo genau in der Passage steht, was dieser eine Satz behauptet?

        Warum eigens gefragt wird: Eine Quelle gehoert zu einer Passage, eine
        Fundstelle aber zu einer *Aussage*. Zitieren zwei Saetze der Antwort
        dieselbe Passage - "Das Gehalt betrug 3.940,00 EUR" und "Gekuendigt
        wurde am 04.05.2026" -, gibt es nur eine Quelle, und sie kann nur eine
        der beiden Stellen tragen. Der zweite Verweis sprang deshalb an die
        Stelle des ersten. Aus der Kanzlei: "wenn man dann schon auf den
        zweiten Verweis draufdrueckt, dann springt er leider nicht genau wie
        bei der ersten Markierung zur Quelle."

        Kein Modellaufruf, keine Kosten: Der Vergleich laeuft im Programm
        (services/fundstelle.py) und markiert nur Text, der in der Passage
        wirklich steht.
        """
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        passage = next((p for p in d.sitzungen.passagen(sitzung) if p.kennung == daten.kennung), None)
        if passage is None:
            raise HTTPException(404, "Diese Fundstelle gehört nicht zu den geladenen Dokumenten.")
        treffer = treffer_finden(daten.aussage, passage.text)
        if treffer is None:
            return {"kennung": passage.kennung, "treffer_start": None, "treffer_ende": None,
                    "marken": [], "zitat": ""}
        return {"kennung": passage.kennung, "treffer_start": treffer.start,
                "treffer_ende": treffer.ende, "marken": [list(m) for m in treffer.marken],
                "zitat": treffer.zitat}

    @app.get("/api/nutzer")
    def nutzer_waehlbar() -> dict[str, Any]:
        """Die waehlbaren Benutzer - ausschliesslich im oertlichen Betrieb.

        Oertlich sagt der Kopf der Anfrage, wer da ist; ein Kennwort gibt es
        nicht. Die Liste hier anzuzeigen erspart das Abtippen einer Kennung und
        gibt nichts preis, was auf demselben Rechner nicht ohnehin offen laege.

        Im AWS-Betrieb gibt es diesen Weg nicht. Dort stellt Cognito die
        Identitaet fest, und wer noch nicht angemeldet ist, hat keinen Anspruch
        darauf zu erfahren, wer in dieser Kanzlei arbeitet. Deshalb 404 und
        nicht 403: Der Weg existiert dort nicht, statt verboten zu sein.
        """
        auflisten = getattr(d.berechtigungen, "auflisten", None)
        if e.identitaet != "header" or auflisten is None:
            raise HTTPException(404, "Diesen Weg gibt es in diesem Betrieb nicht.")
        return {"nutzer": [{"id": n.id, "name": n.name} for n in auflisten()]}

    @app.get("/api/nachweis")
    def nachweis(limit: int = 25, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Verarbeitungsnachweis: was ist wann an welches Modell gegangen.

        Ohne Inhalte – nur Kurzkennungen, Umfänge, Kosten. Auf die eigenen
        Vorgänge beschränkt. Beantwortet die Rechenschaftsfrage, ohne den
        Aktentext ein zweites Mal abzulegen.
        """
        d.berechtigungen.nutzer(ident)  # nur angemeldete, bekannte Nutzer
        grenze = max(1, min(int(limit), 100))
        return {"eintraege": d.kosten.nachweis(ident.nutzer_id, grenze)}

    # ── Posteingang (beobachteter Ordner) ──────────────────────────────────

    @app.get("/api/posteingang")
    def posteingang(ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Die vorbereiteten Eingänge – ein kanzleiinterner Überblick vor der Einordnung."""
        d.berechtigungen.nutzer(ident)
        return d.posteingang.uebersicht()

    @app.post("/api/posteingang/pruefen")
    def posteingang_pruefen(ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        d.berechtigungen.nutzer(ident)
        return d.posteingang.pruefen()

    @app.get("/api/posteingang/{eintrag_id}/passagen")
    def posteingang_passagen(eintrag_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        d.berechtigungen.nutzer(ident)
        return {"passagen": [p.model_dump() for p in d.posteingang.passagen(eintrag_id)]}

    @app.post("/api/posteingang/{eintrag_id}/triage")
    def posteingang_triage(eintrag_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Eingangsprüfung eines vorbereiteten Eingangs – ein Lesen, kein Handeln."""
        d.berechtigungen.nutzer(ident)
        sitzung, passagen = d.posteingang.als_sitzung(ident, eintrag_id)
        return d.analyse.triage(ident, sitzung, passagen, [], []).model_dump()

    @app.delete("/api/posteingang/{eintrag_id}", status_code=204)
    def posteingang_verwerfen(eintrag_id: str, ident: Identitaet = Depends(identitaet)) -> None:
        d.berechtigungen.nutzer(ident)
        d.posteingang.verwerfen(eintrag_id)

    @app.post("/api/posteingang/{eintrag_id}/zurueckholen")
    def posteingang_zurueckholen(eintrag_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Ein Verwerfen rückgängig machen, solange die Rücklage reicht."""
        d.berechtigungen.nutzer(ident)
        return d.posteingang.zurueckholen(eintrag_id)

    # ── Eigene Aufträge (Entwurfsvorlagen der Kanzlei) ─────────────────────

    @app.get("/api/auftraege")
    def auftraege(ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        d.berechtigungen.nutzer(ident)
        return {"aktiv": d.auftraege.aktiv, "eintraege": d.auftraege.liste()}

    @app.get("/api/auftraege/{name:path}")
    def auftrag_lesen(name: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Anweisung eines Auftrags zum Vorbelegen; das Material bleibt im Dienst."""
        d.berechtigungen.nutzer(ident)
        a = d.auftraege.laden(name)
        return {"name": a.name, "label": a.label, "kategorie": a.kategorie,
                "anweisung": a.anweisung, "hat_material": bool(a.material)}

    @app.post("/api/auftraege", status_code=201)
    def auftrag_anlegen(daten: AuftragAnlegen, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Einen freigegebenen Vorschlag als Datei ablegen.

        Der Weg hierher führt über den Vorschlag und über die Augen eines
        Menschen. Angelegt wird nur Neues; Vorhandenes bleibt unangetastet.
        """
        d.berechtigungen.nutzer(ident)
        a = d.auftraege.anlegen(daten.name, daten.text)
        ereignis(_log, "auftrag_angelegt", auftrag=a.name, kategorie=a.kategorie,
                 nutzer=ident.nutzer_id, zeichen=len(daten.text))
        return {"name": a.name, "label": a.label, "kategorie": a.kategorie,
                "anweisung": a.anweisung, "hat_material": bool(a.material)}

    # ── Promptbibliothek (waechst waehrend der Arbeit) ────────────────────
    #
    # Das Rechtsgebiet kommt aus der Akte (jur|nodes: lawCategory), nicht aus
    # einer Abfrage. Die Oberflaeche muss es deshalb nirgends mitschicken und
    # kann es auch nicht aus Versehen falsch setzen.

    def _gebiet(sitzung: Any) -> str:
        return (sitzung.akte.rechtsgebiet if sitzung.akte else "") or ""

    def _bibliothek_antwort(sitzung: Any, wahl: str = "") -> dict[str, Any]:
        """Die Leiste - zum Rechtsgebiet der Akte oder zu einem gewaehlten.

        Aus der Kanzlei am 14.10.2026: „Rechtsgebiet wechseln." Die Akte
        gibt vor, die Wahl geht vor: Eine Verkehrssache kann eine
        arbeitsrechtliche Frage aufwerfen.
        """
        aus_akte = _gebiet(sitzung)
        gebiet = wahl.strip() or aus_akte
        # In Gruppen: erst das Rechtsgebiet der Akte, dann was in jedem
        # Verfahren gilt (die Gerichtsmuster). Jede Gruppe traegt ihren
        # eigenen Vorspann; die Oberflaeche setzt ihn SICHTBAR ins
        # Eingabefeld, nie heimlich davor.
        # Zur Wahl stehen alle hinterlegten Gebiete und das der Akte - auch
        # wenn zu ihm noch nichts dasteht: Sonst koennte man zu der Akte,
        # die gerade offen ist, nichts ablegen.
        waehlbar = set(promptbibliothek.alle_gebiete())
        if aus_akte:
            waehlbar.add(promptbibliothek._schluessel(aus_akte))
        waehlbar.add(promptbibliothek._schluessel(gebiet))
        return {"rechtsgebiet": gebiet or promptbibliothek.OHNE_GEBIET,
                "aus_akte": bool(aus_akte),
                "gebiet_der_akte": aus_akte or promptbibliothek.OHNE_GEBIET,
                "gewaehlt": bool(wahl.strip()) and wahl.strip() != aus_akte,
                "gebiete": sorted(waehlbar),
                "gruppen": [{"name": g["name"], "basis": g["basis"],
                             "immer": g["immer"],
                             "eintraege": [dict(e) for e in g["eintraege"]]}
                            for g in promptbibliothek.gruppen(gebiet)],
                "max_titel": promptbibliothek.MAX_TITEL,
                "max_zeichen": promptbibliothek.MAX_ZEICHEN}

    @app.get("/api/sitzungen/{sitzung_id}/prompts")
    def prompts_lesen(sitzung_id: str, rechtsgebiet: str = "",
                      ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Die Prompts zum Rechtsgebiet dieser Akte - oder zu einem gewaehlten."""
        return _bibliothek_antwort(d.sitzungen.laden(ident, sitzung_id), rechtsgebiet)

    @app.post("/api/sitzungen/{sitzung_id}/prompts", status_code=201)
    def prompt_ablegen(sitzung_id: str, daten: PromptAblegen,
                       ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Einen Prompt hinterlegen, der sich bewaehrt hat.

        Abgelegt wird unter dem Gebiet, das gerade in der Leiste steht - nicht
        unter dem der Akte. Wer zum Arbeitsrecht gewechselt hat und dort etwas
        merkt, meint das Arbeitsrecht.

        Protokolliert werden Rechtsgebiet und Laenge, nie der Wortlaut: Ein
        Prompt aus der Arbeit kann einen Namen enthalten.
        """
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        gebiet = daten.rechtsgebiet.strip() or _gebiet(sitzung)
        promptbibliothek.merken(gebiet, daten.titel, daten.text)
        ereignis(_log, "prompt_abgelegt", rechtsgebiet=gebiet or "-",
                 nutzer=ident.nutzer_id, zeichen=len(daten.text))
        return _bibliothek_antwort(sitzung, daten.rechtsgebiet)

    @app.post("/api/sitzungen/{sitzung_id}/prompts/vergessen")
    def prompt_vergessen(sitzung_id: str, daten: PromptVergessen,
                         ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Einen Prompt herausnehmen; mitgelieferte werden ausgeblendet.

        Ein eigener Aufruf statt DELETE: Die Ueberschrift steht im Rumpf, und
        ein DELETE mit Rumpf wird unterwegs nicht ueberall mitgenommen.
        """
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        gebiet = daten.rechtsgebiet.strip() or _gebiet(sitzung)
        promptbibliothek.vergessen(gebiet, daten.titel)
        ereignis(_log, "prompt_vergessen", rechtsgebiet=gebiet or "-",
                 nutzer=ident.nutzer_id)
        return _bibliothek_antwort(sitzung, daten.rechtsgebiet)

    # ── Selbsttest: Stehen die Absicherungen? ─────────────────────────────

    @app.get("/api/selbsttest")
    def selbsttest(ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Das Startbild. Kostet nichts und ruft kein Modell auf."""
        d.berechtigungen.nutzer(ident)
        ergebnis = Selbsttest(e, adapter=d.adapter, kosten=d.kosten,
                              modellprotokoll=d.modellprotokoll).ausfuehren()
        return ergebnis.uebersicht()

    @app.post("/api/selbsttest/modelle")
    def selbsttest_modelle(ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Jedes eingebundene Modell einmal wirklich fragen – ein Wort.

        Eigener Aufruf, weil er kostet: Mit mehreren Modellen kostete er bei
        jedem Start ein Vielfaches. Der Katalog von AWS taugt als Ersatz nicht
        („vorhanden" heißt nicht „dieses Konto darf es", siehe modelle.py).

        Ist ein Schutzgeländer hinterlegt, gehen fünf erfundene Sätze in der
        Sprache einer Akte mit hindurch. Denn der Selbsttest sagt sonst nur,
        DASS ein Geländer vorgeschaltet ist – nicht, ob es brauchbar
        eingestellt ist. Ein zu scharfer Filter fiele erst vor einer echten
        Akte auf, und dann als Sperrmeldung ohne erkennbaren Grund.
        """
        d.berechtigungen.nutzer(ident)
        zeilen = modelle_anprobieren(e) + gelaender_anprobieren(e)
        ereignis(_log, "selbsttest_modelle", nutzer=ident.nutzer_id, anzahl=len(zeilen))
        return {"modelle": [z.uebersicht() for z in zeilen]}

    # ── Referenzen (veröffentlichtes Material im Kontext) ──────────────────

    @app.get("/api/referenzen")
    def referenzen(ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        d.berechtigungen.nutzer(ident)
        return {"aktiv": d.referenzen.aktiv, "eintraege": d.referenzen.liste()}

    @app.get("/api/sitzungen/{sitzung_id}/referenzen")
    def referenzen_lesen(sitzung_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        return {"namen": sitzung.referenzen}

    @app.put("/api/sitzungen/{sitzung_id}/referenzen")
    def referenzen_setzen(sitzung_id: str, daten: ReferenzenWaehlen, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Welche Referenzen in den Kontext der Sitzung gehören – der Bearbeiter wählt."""
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        sitzung.referenzen = d.referenzen.pruefen(daten.namen)  # nur vorhandene, nur aus dem Ordner
        d.speicher.sitzung_ablegen(sitzung)
        return {"namen": sitzung.referenzen}

    # ── Akten und Sitzungen ───────────────────────────────────────────────

    @app.get("/api/akten")
    def akten(suche: str = "", ident: Identitaet = Depends(identitaet)) -> list[dict[str, Any]]:
        return [a.model_dump() for a in d.sitzungen.akten_suchen(ident, suche)]

    @app.post("/api/sitzungen", status_code=201)
    def sitzung_anlegen(daten: SitzungAnlegen, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        # Die Rueckfrage ZUERST lesen, dann die Nutzung vermerken: Sonst
        # verschoebe das Oeffnen der Akte den Fragetermin, und die Frage
        # waere nie faellig, solange jemand hineinschaut.
        stand = d.aufbewahrung.stand(ident, daten.akte_id)
        sitzung = d.sitzungen.eroeffnen(ident, daten.akte_id)
        d.aufbewahrung.benutzt(daten.akte_id)
        antwort = _sitzung_antwort(d, sitzung)
        antwort["aufbewahrung"] = stand.als_dict()
        return antwort

    @app.get("/api/sitzungen/{sitzung_id}")
    def sitzung_lesen(sitzung_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        return _sitzung_antwort(d, d.sitzungen.laden(ident, sitzung_id))

    @app.post("/api/sitzungen/{sitzung_id}/dokumente")
    def dokumente_laden(sitzung_id: str, daten: DokumenteLaden, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        sitzung = d.sitzungen.dokumente_laden(ident, sitzung_id, daten.dokument_ids, neu_laden=daten.neu_laden)
        return _sitzung_antwort(d, sitzung)

    @app.delete("/api/sitzungen/{sitzung_id}/dokumente/{dokument_id:path}")
    def dokument_entfernen(sitzung_id: str, dokument_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        sitzung = d.sitzungen.dokument_entfernen(ident, sitzung_id, dokument_id)
        return _sitzung_antwort(d, sitzung)

    @app.get("/api/sitzungen/{sitzung_id}/passagen")
    def passagen(sitzung_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        # Der echte Dokumenttext mit Fundstellen-Kennungen, damit die
        # Arbeitsfläche ihn links zeigen und ein Beleg ihn hervorheben kann.
        # Anders als bei Perfect Shield gibt es keinen Platzhalter-Umweg.
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        return {"passagen": [p.model_dump() for p in d.sitzungen.passagen(sitzung)]}

    @app.delete("/api/sitzungen/{sitzung_id}", status_code=204)
    def sitzung_schliessen(sitzung_id: str, ident: Identitaet = Depends(identitaet)) -> None:
        d.sitzungen.schliessen(ident, sitzung_id)

    # ── Dauerhaftes Aktengedächtnis ───────────────────────────────────────

    @app.get("/api/sitzungen/{sitzung_id}/gedaechtnis")
    def gedaechtnis_lesen(sitzung_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        return d.gedaechtnis.uebersicht(d.gedaechtnis.lesen(sitzung.akte_id))

    @app.post("/api/sitzungen/{sitzung_id}/gedaechtnis/sichern")
    def gedaechtnis_sichern(sitzung_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Beim Schließen: ablegen und zurückmelden, was wirklich gesichert ist.

        Antwortet auch dann, wenn kein Gedächtnis besteht - dann mit
        "gesichert": false. Die Oberfläche soll den Unterschied benennen können
        zwischen "gespeichert" und "es gab nichts zu speichern". Beides ist eine
        Meldung wert; verschweigen darf man weder das eine noch das andere.
        """
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        g = d.gedaechtnis.sichern(sitzung)
        return {"gesichert": g is not None,
                "aktiv": d.gedaechtnis.aktiv,
                "aktenzeichen": sitzung.akte.aktenzeichen,
                "bezeichnung": sitzung.akte.bezeichnung} | d.gedaechtnis.uebersicht(g)

    @app.post("/api/sitzungen/{sitzung_id}/gedaechtnis/aktualisieren")
    def gedaechtnis_aktualisieren(sitzung_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Eine Portion nachlesen – der Knopf für den neuen Schriftsatz."""
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        ergebnis = d.gedaechtnis.lebenssachverhalt_aktualisieren(ident, sitzung)
        return d.gedaechtnis.uebersicht(ergebnis.gedaechtnis) | {"lauf": ergebnis.als_dict()}

    @app.post("/api/sitzungen/{sitzung_id}/gedaechtnis/einlesen")
    def gedaechtnis_einlesen(sitzung_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Die ganze Akte am Stück ins Gedächtnis lesen – Portion für Portion.

        Der Weg für die grosse Akte, die nicht in einen Aufruf passt. Er kostet
        so viele Aufrufe, wie Portionen nötig sind, und wird deshalb ausdrücklich
        ausgelöst und nie von selbst. Was gelesen ist, bleibt auch dann
        gespeichert, wenn der Lauf vorzeitig endet.
        """
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        ergebnis = d.gedaechtnis.akte_einlesen(ident, sitzung)
        return d.gedaechtnis.uebersicht(ergebnis.gedaechtnis) | {"lauf": ergebnis.als_dict()}

    @app.delete("/api/akten/{akte_id}/gedaechtnis", status_code=204)
    def gedaechtnis_loeschen(akte_id: str, sitzung: str = "",
                             ident: Identitaet = Depends(identitaet)) -> None:
        """Das ganze Aktengedaechtnis verwerfen - und die offene Sitzung mit.

        ``sitzung`` ist freigestellt. Steht sie da, werden aus DIESER Sitzung
        die Dokumente mitgenommen, die aus dem Gedaechtnis stammen - in einem
        Zug, nicht in einem Aufruf je Dokument.

        Aus der Kanzlei am 13.10.2026: "Gedaechtnis verwerfen scheint nicht
        abzuschliessen." Die Oberflaeche schickte einen Aufruf je Dokument,
        und jede Antwort las die ganze Akte neu bei jur|nodes.

        Welche Dokumente aus dem Gedaechtnis stammen, muss VOR dem Loeschen
        gelesen werden - danach steht es nirgends mehr. Laesst sich das
        Gedaechtnis nicht lesen, wird aus der Sitzung nichts genommen: Dann
        hat `bei_eroeffnen` auch nichts hineingelegt, und was dort liegt, hat
        der Bearbeiter selbst geholt.
        """
        d.berechtigungen.pruefen(ident, akte_id)
        aus_dem_gedaechtnis: list[str] = []
        try:
            vorhanden = d.gedaechtnis.lesen(akte_id)
        except GedaechtnisFehler:
            vorhanden = None
        if vorhanden is not None:
            aus_dem_gedaechtnis = [x.dokument_id for x in vorhanden.dokumente]
        d.gedaechtnis.loeschen(akte_id)
        if sitzung and aus_dem_gedaechtnis:
            d.sitzungen.dokumente_entfernen(ident, sitzung, aus_dem_gedaechtnis)

    @app.delete("/api/akten/{akte_id}/gedaechtnis/dokumente/{dokument_id}")
    def gedaechtnis_dokument_vergessen(akte_id: str, dokument_id: str,
                                       ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        d.berechtigungen.pruefen(ident, akte_id)
        return d.gedaechtnis.uebersicht(d.gedaechtnis.dokument_vergessen(akte_id, dokument_id))

    @app.delete("/api/akten/{akte_id}/gedaechtnis/fragen/{nummer}")
    def gedaechtnis_antwort_vergessen(akte_id: str, nummer: int,
                                      ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        d.berechtigungen.pruefen(ident, akte_id)
        return d.gedaechtnis.uebersicht(d.gedaechtnis.antwort_vergessen(akte_id, nummer))

    @app.get("/api/verwaltung/arbeitsbereiche")
    def arbeitsbereiche(ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Aufsicht über alle Arbeitsbereiche – Zustände, keine Akteninhalte."""
        return d.aufsicht.uebersicht(ident)

    # ── Abschluss der Akte ────────────────────────────────────────────────
    # Erst exportieren, dann löschen. Ausgelöst wird der Abschluss vom
    # Aktenstatus in jurnodes, nie vom Zeitablauf.

    # ── Der zweite Faktor ─────────────────────────────────────────────────
    #
    # Diese Wege stehen ohne ihn offen - sonst kaeme man nie dahin, ihn zu
    # zeigen. Sie geben nichts preis: Der Stand sagt nur, ob einer noetig und
    # ob einer eingerichtet ist.

    @app.get("/api/anmeldung/zweiter-faktor")
    def zf_stand(request: Request) -> dict[str, Any]:
        ident = aus_kopfzeile(request.headers.get("x-jusperfect-nutzer"))
        return {
            "noetig": e.zweiter_faktor == "an",
            "eingerichtet": d.zf_ablage.eingerichtet(ident.nutzer_id),
            "bestaetigt": d.zf_bestaetigt.gilt(ident.nutzer_id),
            "stellen": zf.STELLEN,
        }

    @app.post("/api/anmeldung/zweiter-faktor/einrichten")
    def zf_einrichten(request: Request) -> dict[str, Any]:
        """Ein neues Geheimnis – einmal angezeigt, dann nie wieder.

        Abgelegt wird es erst, wenn der Nutzer mit einem Einmalkennwort
        nachweist, dass seine App es gelesen hat. Sonst sperrte ein
        misslungener Scan den Zugang aus.
        """
        ident = aus_kopfzeile(request.headers.get("x-jusperfect-nutzer"))
        d.berechtigungen.nutzer(ident)
        if d.zf_ablage.eingerichtet(ident.nutzer_id):
            raise HTTPException(409, "Für diese Kennung ist bereits ein zweiter Faktor eingerichtet.")
        geheimnis = zf.geheimnis_erzeugen()
        app.state.zf_offen = getattr(app.state, "zf_offen", {})
        app.state.zf_offen[ident.nutzer_id] = geheimnis
        return {"geheimnis": geheimnis,
                "link": zf.einrichtungslink(ident.nutzer_id, geheimnis),
                "hinweis": "Dieses Geheimnis wird nur jetzt angezeigt. "
                           "In die Authentifizierungs-App übernehmen und dann "
                           "das angezeigte Einmalkennwort eingeben."}

    @app.post("/api/anmeldung/zweiter-faktor/bestaetigen")
    def zf_bestaetigen(daten: ZfCode, request: Request) -> dict[str, Any]:
        ident = aus_kopfzeile(request.headers.get("x-jusperfect-nutzer"))
        d.berechtigungen.nutzer(ident)
        offen = getattr(app.state, "zf_offen", {}).get(ident.nutzer_id)
        if not offen:
            raise HTTPException(409, "Es ist keine Einrichtung offen. Bitte neu beginnen.")
        if not zf.code_pruefen(offen, daten.code):
            raise HTTPException(401, "Das Einmalkennwort stimmt nicht.")
        d.zf_ablage.merken(ident.nutzer_id, offen)
        app.state.zf_offen.pop(ident.nutzer_id, None)
        d.zf_bestaetigt.bestaetigen(ident.nutzer_id, daten.code)
        ereignis(_log, "zweiter_faktor_eingerichtet", nutzer=ident.nutzer_id)
        return {"eingerichtet": True, "bestaetigt": True}

    @app.post("/api/anmeldung/zweiter-faktor/pruefen")
    def zf_pruefen(daten: ZfCode, request: Request) -> dict[str, Any]:
        ident = aus_kopfzeile(request.headers.get("x-jusperfect-nutzer"))
        d.berechtigungen.nutzer(ident)
        geheimnis = d.zf_ablage.geheimnis(ident.nutzer_id)
        if not geheimnis:
            raise HTTPException(409, "Für diese Kennung ist kein zweiter Faktor eingerichtet.")
        # Ein Einmalkennwort gilt EINMAL. Ohne das waere ein abgelesener Code
        # dreissig Sekunden lang ein Nachschluessel.
        if d.zf_bestaetigt.schon_benutzt(ident.nutzer_id, daten.code):
            raise HTTPException(401, "Dieses Einmalkennwort wurde schon verwendet. "
                                     "Bitte das nächste abwarten.")
        if not zf.code_pruefen(geheimnis, daten.code):
            ereignis(_log, "zweiter_faktor_falsch", nutzer=ident.nutzer_id)
            raise HTTPException(401, "Das Einmalkennwort stimmt nicht.")
        d.zf_bestaetigt.bestaetigen(ident.nutzer_id, daten.code)
        ereignis(_log, "zweiter_faktor_bestaetigt", nutzer=ident.nutzer_id)
        return {"bestaetigt": True}

    # ── Läuft die Akte noch? ───────────────────────────────────────────────
    #
    # Die Frage ist ein eigener Weg und nicht Teil des Abschlusses: Sie wird
    # gestellt, BEVOR irgendetwas vorgemerkt ist, und eine unbeantwortete
    # Frage loescht nichts.

    @app.get("/api/aufbewahrung/faellig")
    def aufbewahrung_faellig(ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        staende = d.aufbewahrung.faellige(ident)
        return {"frage": AUFBEWAHRUNG_FRAGE, "monate": d.aufbewahrung.monate,
                "akten": [s.als_dict() for s in staende]}

    @app.get("/api/akten/{akte_id}/aufbewahrung")
    def aufbewahrung_stand(akte_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        return d.aufbewahrung.stand(ident, akte_id).als_dict()

    @app.post("/api/akten/{akte_id}/aufbewahrung/antwort")
    def aufbewahrung_antwort(akte_id: str, daten: LaeuftNoch,
                             ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        try:
            return d.aufbewahrung.beantworten(ident, akte_id, daten.laeuft_noch).als_dict()
        except AufbewahrungFehler as fehler:
            raise HTTPException(status_code=409, detail=str(fehler)) from fehler

    @app.get("/api/akten/{akte_id}/abschluss")
    def abschluss_stand(akte_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        return d.abschluss.stand(ident, akte_id).als_dict()

    @app.get("/api/akten/{akte_id}/abschluss/vorschau")
    def abschluss_vorschau(akte_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        return d.abschluss.export_vorschau(ident, akte_id)

    @app.post("/api/akten/{akte_id}/abschluss/vormerken")
    def abschluss_vormerken(akte_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        return d.abschluss.vormerken(ident, akte_id).als_dict()

    @app.post("/api/akten/{akte_id}/abschluss/ausfuehren")
    def abschluss_ausfuehren(akte_id: str, daten: AbschlussAusfuehren,
                             ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        return d.abschluss.ausfuehren(ident, akte_id, daten.bestaetigung, daten.text_pruefsumme).als_dict()

    # ── KI-Funktionen ─────────────────────────────────────────────────────

    @app.post("/api/sitzungen/{sitzung_id}/frage")
    def frage(sitzung_id: str, daten: FrageStellen, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        antwort = d.analyse.frage(ident, sitzung, d.sitzungen.passagen(sitzung), daten.frage,
                                  d.sitzungen.beteiligte(sitzung), d.sitzungen.fristen(sitzung),
                                  d.referenzen.passagen(sitzung.referenzen))
        d.sitzungen.dialog_merken(ident, sitzung.id, daten.frage, antwort)
        d.gedaechtnis.antwort_merken(sitzung, daten.frage, antwort)
        return antwort.model_dump()

    @app.post("/api/sitzungen/{sitzung_id}/frage/stream")
    def frage_stream(sitzung_id: str, daten: FrageStellen, ident: Identitaet = Depends(identitaet)) -> StreamingResponse:
        # Auth und "Sitzung nicht gefunden" werden hier, vor dem Strom,
        # entschieden - so bekommt der Aufrufer noch einen sauberen Statuscode.
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        passagen = d.sitzungen.passagen(sitzung)
        beteiligte = d.sitzungen.beteiligte(sitzung)
        fristen = d.sitzungen.fristen(sitzung)
        referenzen = d.referenzen.passagen(sitzung.referenzen)

        def strom():
            try:
                for art, wert in d.analyse.frage_stream(ident, sitzung, passagen, daten.frage, beteiligte, fristen, referenzen):
                    if art == "fortschritt":
                        # Nur die Zeichenzahl: dass gearbeitet wird, nicht was
                        # dasteht (Befund F05 der Zweitpruefung, 05.10.2026).
                        yield json.dumps({"type": "fortschritt", "zeichen": wert}) + "\n"
                    elif art == "geprueft":
                        yield json.dumps({"type": "geprueft", "text": wert}, ensure_ascii=False) + "\n"
                    else:
                        d.sitzungen.dialog_merken(ident, sitzung.id, daten.frage, wert)
                        d.gedaechtnis.antwort_merken(sitzung, daten.frage, wert)
                        yield json.dumps({"type": "fertig", "antwort": wert.model_dump()}, ensure_ascii=False, default=str) + "\n"
            except Exception as exc:  # nach Beginn des Stroms bleibt nur ein Ereignis
                for typ, _status in _abbildung:
                    if isinstance(exc, typ):
                        yield json.dumps({"type": "fehler", "detail": str(exc)}) + "\n"
                        return
                # Hier stand der Satz ohne Nummer und ohne Protokollzeile.
                #
                # Die Fehlergrenze gibt bei einem unerwarteten Fehler eine
                # Vorgangsnummer heraus und schreibt eine Zeile dazu - aber
                # sie sieht diesen Fehler nie: Der Strom hat begonnen, die
                # Antwort ist unterwegs, und was hier geschieht, bleibt in
                # dieser Schleife. Aus der Kanzlei am 13.10.2026 kam der Satz
                # mit einer Nummer; waere er aus einer Frage gekommen, haette
                # er nicht einmal die gehabt.
                yield json.dumps(
                    {"type": "fehler", "detail": _unerwartet_im_strom(exc, "frage")}
                ) + "\n"

        return StreamingResponse(strom(), media_type="application/x-ndjson")

    @app.post("/api/sitzungen/{sitzung_id}/analyse")
    def analyse(sitzung_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Die Aktenanalyse – über die Dokumente, sonst über das Gedächtnis.

        Passt die Akte in einen Aufruf, geht es wie immer über die Dokumente
        selbst. Passt sie nicht und ist sie vollständig ins Aktengedächtnis
        gelesen, geht es über den Lebenssachverhalt: Er ist abschnittsweise aus
        allen Dokumenten entstanden, ein Bruchteil so lang und deckt die Akte
        doch ganz ab. Erst dadurch lässt sich ein Widerspruch finden, der
        zwischen Dokument 8 und Dokument 44 liegt.

        Der Wechsel geschieht nicht still: Der erste Hinweis der Analyse sagt,
        worauf sie beruht. Ist die Akte nur teilweise gelesen, bleibt es bei
        der Verweigerung – eine Analyse über zwei Drittel sähe aus wie eine
        über die ganze Akte, und das ist der Zustand, den dieses Programm
        gerade verhindern soll.
        """
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        passagen = d.sitzungen.passagen(sitzung)
        beteiligte, fristen = d.sitzungen.beteiligte(sitzung), d.sitzungen.fristen(sitzung)
        # Wofuer die Aussagen der Analyse gelten. Ueber die Dokumente gerechnet
        # sind es die geladenen; ueber das Gedaechtnis gerechnet deckt sie die
        # ganze eingelesene Akte ab, weil der Lebenssachverhalt aus allen
        # Dokumenten entstanden ist. Das ist nicht dasselbe, und es als
        # dasselbe zu speichern hiesse, die Reichweite der Analyse falsch zu
        # protokollieren.
        erfasst = {x.dokument_id for x in passagen}
        try:
            ergebnis = d.analyse.analysieren(ident, sitzung, passagen, beteiligte, fristen)
        except AktenZuGross as zu_gross:
            g = d.gedaechtnis.lesen(sitzung.akte_id)
            offen = (g and Gedaechtnisdienst.uebersicht(g).get("offene_dokumente", 0)) or 0
            if g is None or not g.lebenssachverhalt.strip() or offen:
                if g is not None and g.lebenssachverhalt.strip() and offen:
                    raise AktenZuGross(
                        f"{zu_gross}\n\nDas Gedächtnis ist erst zum Teil gelesen: "
                        f"{offen} Dokument(e) fehlen noch im Lebenssachverhalt. Eine Analyse "
                        f"darüber sähe aus wie eine über die ganze Akte. Bitte „Akte einlesen“ "
                        f"zu Ende laufen lassen."
                    ) from zu_gross
                raise
            ergebnis = d.analyse.analysieren_ueber_gedaechtnis(
                ident, sitzung, g.lebenssachverhalt, g.chronologie, passagen, beteiligte, fristen)
            erfasst |= {x.dokument_id for x in g.dokumente}
        # Die Chronologie wird fortgeschrieben, nicht ersetzt: Der zweite
        # Durchgang nach drei Wochen ergaenzt die neuen Ereignisse, statt den
        # Zeitstrahl von vorn zu bauen. Zurueck geht der vollstaendige Stand -
        # die Oberflaeche zeigt damit auch, was frueher schon feststand.
        antwort = ergebnis.model_dump()
        antwort["chronologie"] = [
            x.model_dump() for x in d.gedaechtnis.chronologie_fortschreiben(sitzung, ergebnis)
        ]
        # Die Analyse kostet einen Modellaufruf ueber die ganze Akte und war
        # bis zum 05.10.2026 weg, sobald das Programm geschlossen wurde.
        # Mitgeschrieben wird auch, was die Akte in jurnodes gerade enthaelt -
        # nur daran laesst sich spaeter erkennen, ob etwas NEU dazugekommen ist.
        # Einmal abgefragt, zweimal gebraucht: Die Dokumentliste kommt ueber die
        # Schnittstelle von jurnodes, und zwei Abrufe waeren zwei Netzaufrufe
        # mit der Moeglichkeit, zwei verschiedene Antworten zu bekommen.
        in_der_akte = d.sitzungen.dokumente(sitzung)
        d.gedaechtnis.analyse_merken(
            sitzung, ergebnis,
            erfasste_dokumente=sorted(erfasst),
            akte_dokumente=[x.id for x in in_der_akte])
        antwort["stand"] = d.gedaechtnis.analyse_stand(sitzung.akte_id, in_der_akte)
        return antwort

    @app.get("/api/sitzungen/{sitzung_id}/analyse")
    def analyse_stand(sitzung_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Die zuletzt gelaufene Analyse - und ob sie noch zur Akte passt.

        Kostet nichts: kein Modellaufruf, nur ein Vergleich im Programm. Genau
        deshalb darf die Oberflaeche das bei jedem Oeffnen der Akte abrufen.
        """
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        g = d.gedaechtnis.lesen(sitzung.akte_id)
        stand = d.gedaechtnis.analyse_stand(sitzung.akte_id, d.sitzungen.dokumente(sitzung))
        return {"stand": stand,
                "analyse": g.analyse.model_dump() if (g and g.analyse) else None}

    @app.post("/api/sitzungen/{sitzung_id}/chronologie/aktualisieren")
    def chronologie_aktualisieren(sitzung_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Traegt nach, was seit dem letzten Lauf dazugekommen ist.

        Der Unterschied zur Analyse ist der Preis: Es geht nur ueber Passagen,
        die die Chronologie noch nicht gesehen hat, und nur nach Ereignissen -
        nicht nach sechs Listen ueber die ganze Akte. Ist nichts Neues da,
        kostet der Knopfdruck nichts.
        """
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        passagen = d.sitzungen.passagen(sitzung)
        g = d.gedaechtnis.lesen(sitzung.akte_id)
        if g is not None:
            erledigt = set(g.chronologie_passagen)
            offen = [p for p in passagen if p.kennung not in erledigt]
            if not offen:
                return {"chronologie": [x.model_dump() for x in g.chronologie],
                        "hinweise": ["Seit dem letzten Lauf ist nichts dazugekommen."],
                        "neue_passagen": 0, "kosten": Kosten().model_dump(), "modell": ""}
            passagen = offen
        ergebnis = d.analyse.chronologie(
            ident, sitzung, passagen, d.sitzungen.beteiligte(sitzung), d.sitzungen.fristen(sitzung),
            bekannt=[f"{x.datum}: {x.ereignis}" for x in (g.chronologie if g else [])],
        )
        antwort = ergebnis.model_dump()
        antwort["chronologie"] = [
            x.model_dump() for x in d.gedaechtnis.chronologie_fortschreiben(sitzung, ergebnis)
        ]
        # Auch ein Lauf ohne Fund ist erledigt - sonst liefe er jedes Mal neu.
        d.gedaechtnis.chronologie_merken(sitzung.akte_id, [p.kennung for p in passagen])
        antwort["neue_passagen"] = len(passagen)
        return antwort

    @app.post("/api/sitzungen/{sitzung_id}/triage")
    def triage(sitzung_id: str, daten: TriageAnfrage, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        ergebnis = d.analyse.triage(ident, sitzung, d.sitzungen.passagen(sitzung, nur_dokument=daten.dokument_id),
                                    d.sitzungen.beteiligte(sitzung), d.sitzungen.fristen(sitzung))
        return ergebnis.model_dump()

    # ── Workflow-Packs ────────────────────────────────────────────────────

    @app.get("/api/packs")
    def packs(ident: Identitaet = Depends(identitaet)) -> list[dict[str, Any]]:
        return [{"id": p.id, "titel": p.titel, "rechtsgebiet": p.rechtsgebiet,
                 "beschreibung": p.beschreibung, "anforderungen": len(p.anforderungen)}
                for p in d.workflow.liste()]

    @app.post("/api/sitzungen/{sitzung_id}/pack")
    def pack_pruefen(sitzung_id: str, daten: PackAnfrage, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        # Deterministische Beweisprüfung: kein Modellaufruf, jeder Fund belegt.
        # Ohne pack_id wählt jusperfect das Pack nach dem Rechtsgebiet der Akte.
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        pack = d.workflow.pack(daten.pack_id) if daten.pack_id else d.workflow.vorschlag(sitzung.akte.rechtsgebiet)
        if pack is None:
            raise PackNichtGefunden(
                f"Für das Rechtsgebiet „{sitzung.akte.rechtsgebiet or 'unbekannt'}“ gibt es kein Pack. "
                "Bitte eines wählen."
            )
        return d.workflow.pruefen(pack, d.sitzungen.passagen(sitzung)).model_dump()

    # ── Entwürfe ──────────────────────────────────────────────────────────

    @app.post("/api/sitzungen/{sitzung_id}/entwuerfe", status_code=201)
    def entwurf_anlegen(sitzung_id: str, daten: EntwurfAnlegen, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        muster = daten.muster
        # Ein eigener Auftrag steuert das Material bei; die Anweisung kam schon
        # (bearbeitbar) mit der Anfrage.
        if daten.auftrag:
            muster = d.auftraege.laden(daten.auftrag).material or muster
        entwurf = d.entwuerfe.erstellen(ident, sitzung, d.sitzungen.passagen(sitzung), daten.art, daten.anweisung,
                                        daten.empfaenger, d.sitzungen.beteiligte(sitzung), d.sitzungen.fristen(sitzung),
                                        muster)
        return _entwurf_antwort(entwurf)

    def _entwurf_strom(schritte, woher: str):
        """Der gemeinsame Strom von Erstellen und Ändern.

        Dieselbe Form wie bei der Frage: `fortschritt`, `geprueft`, `fertig`,
        `fehler`. Das Vorschaufenster kommt damit mit einem Leser aus.
        """
        def strom():
            try:
                for art, wert in schritte():
                    if art == "fortschritt":
                        # Nur die Zeichenzahl: dass gearbeitet wird, nicht was
                        # dasteht (Befund F05 der Zweitpruefung, 05.10.2026).
                        yield json.dumps({"type": "fortschritt", "zeichen": wert}) + "\n"
                    elif art == "geprueft":
                        yield json.dumps({"type": "geprueft", "text": wert}, ensure_ascii=False) + "\n"
                    else:
                        yield json.dumps({"type": "fertig", "entwurf": _entwurf_antwort(wert)},
                                         ensure_ascii=False, default=str) + "\n"
            except Exception as exc:  # nach Beginn des Stroms bleibt nur ein Ereignis
                for typ, _status in _abbildung:
                    if isinstance(exc, typ):
                        yield json.dumps({"type": "fehler", "detail": str(exc)}) + "\n"
                        return
                yield json.dumps(
                    {"type": "fehler", "detail": _unerwartet_im_strom(exc, woher)}
                ) + "\n"

        return StreamingResponse(strom(), media_type="application/x-ndjson")

    @app.post("/api/sitzungen/{sitzung_id}/entwuerfe/stream")
    def entwurf_anlegen_stream(sitzung_id: str, daten: EntwurfAnlegen,
                               ident: Identitaet = Depends(identitaet)) -> StreamingResponse:
        """Der Entwurf entsteht im Vorschaufenster, Stück für Stück.

        Aus der Kanzlei am 13.10.2026: „Hier wäre dann ein Vorschaufenster
        sehr schön, in welchem der Entwurf nach und nach entsteht."

        Auth und „Sitzung nicht gefunden" werden hier, vor dem Strom,
        entschieden - so bekommt der Aufrufer noch einen sauberen Statuscode.
        """
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        passagen = d.sitzungen.passagen(sitzung)
        beteiligte = d.sitzungen.beteiligte(sitzung)
        fristen = d.sitzungen.fristen(sitzung)
        muster = daten.muster
        if daten.auftrag:
            muster = d.auftraege.laden(daten.auftrag).material or muster
        return _entwurf_strom(
            lambda: d.entwuerfe.erstellen_stream(ident, sitzung, passagen, daten.art,
                                                 daten.anweisung, daten.empfaenger,
                                                 beteiligte, fristen, muster),
            "entwurf")

    @app.post("/api/sitzungen/{sitzung_id}/entwuerfe/{entwurf_id}/aendern/stream")
    def entwurf_aendern_stream(sitzung_id: str, entwurf_id: str, daten: EntwurfAendern,
                               ident: Identitaet = Depends(identitaet)) -> StreamingResponse:
        """Den Entwurf über den Chat ändern - die vorige Fassung bleibt.

        Die Sitzung steht im Pfad: Aus ihr kommen die Passagen, an denen die
        neue Fassung belegt wird. Dass sie zur selben Akte gehört wie der
        Entwurf, wird hier geprüft und nicht angenommen - sonst würde ein
        Entwurf an den Dokumenten einer fremden Akte belegt.
        """
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        entwurf = d.entwuerfe.lesen(ident, entwurf_id)
        if entwurf.akte_id != sitzung.akte_id:
            raise HTTPException(404, "Der Entwurf gehört nicht zu dieser Akte.")
        passagen = d.sitzungen.passagen(sitzung)
        beteiligte = d.sitzungen.beteiligte(sitzung)
        fristen = d.sitzungen.fristen(sitzung)
        return _entwurf_strom(
            lambda: d.entwuerfe.ueberarbeiten_stream(ident, sitzung, passagen, entwurf_id,
                                                     daten.anweisung, beteiligte, fristen),
            "entwurf-aendern")

    @app.post("/api/entwuerfe/{entwurf_id}/zuruecknehmen")
    def entwurf_zuruecknehmen(entwurf_id: str,
                              ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Eine Fassung zurück. Ohne diesen Weg wäre jede Änderung endgültig."""
        return _entwurf_antwort(d.entwuerfe.zuruecknehmen(ident, entwurf_id))

    @app.post("/api/sitzungen/{sitzung_id}/auftragsvorschlag")
    def auftragsvorschlag(sitzung_id: str, daten: AuftragsvorschlagAnfrage,
                          ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Woraus ließe sich ein wiederverwendbarer Auftrag machen?

        Hinaus geht nur die Anweisung des Bearbeiters, nicht der Entwurf und
        nicht die Akte (siehe services/auftragsvorschlag.py). Angelegt wird
        hier nichts - das tut erst POST /api/auftraege nach der Freigabe.
        """
        sitzung = d.sitzungen.laden(ident, sitzung_id)
        entwurf = d.entwuerfe.lesen(ident, daten.entwurf_id)
        vorschlag = d.auftragsvorschlag.vorschlagen(ident, sitzung, entwurf, daten.anweisung)
        return {"vorschlag": vorschlag.uebersicht(), "auftraege_aktiv": d.auftraege.aktiv}

    @app.get("/api/entwuerfe/{entwurf_id}")
    def entwurf_lesen(entwurf_id: str, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        return _entwurf_antwort(d.entwuerfe.lesen(ident, entwurf_id))

    @app.put("/api/entwuerfe/{entwurf_id}")
    def entwurf_bearbeiten(entwurf_id: str, daten: EntwurfBearbeiten, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        return _entwurf_antwort(d.entwuerfe.bearbeiten(ident, entwurf_id, daten.betreff, daten.text))

    @app.post("/api/entwuerfe/{entwurf_id}/freigabe")
    def entwurf_freigeben(entwurf_id: str, daten: EntwurfFreigeben, ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        return _entwurf_antwort(d.entwuerfe.freigeben(ident, entwurf_id, daten.bestaetigung,
                                                     daten.freigabe_pruefsumme))

    @app.get("/api/briefbogen")
    def briefbogen_stand(ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Liegt ein Briefbogen bereit, und wenn nicht: wohin gehoert er?"""
        d.berechtigungen.nutzer(ident)
        ort = briefbogen.finden()
        return {"vorhanden": ort is not None,
                "dateiname": briefbogen.DATEINAME,
                "ordner": str(briefbogen.orte()[0].parent)}

    @app.get("/api/briefbogen/ansicht")
    def briefbogen_ansicht(ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Das Blatt, wie es aussieht - gelesen aus der Vorlage der Kanzlei.

        Aus der Kanzlei am 13.10.2026: „Kann der Entwurf nicht gleich das
        fertige Schreiben mit Briefkopf angeben? Schließlich muss auch
        optisch zum Teil aktualisiert werden."

        Es wird nichts nachgezeichnet: Seitenmaß, Ränder, die festgesetzten
        Stücke des Kopfes und ihre Texte kommen aus der Datei. Ändert die
        Kanzlei ihren Briefbogen, ändert sich diese Ansicht mit.
        """
        d.berechtigungen.nutzer(ident)
        return briefbogen.seitenbild()

    @app.put("/api/briefbogen/einstellungen")
    def briefbogen_einstellen(daten: BlattEinstellen,
                              ident: Identitaet = Depends(identitaet)) -> dict[str, Any]:
        """Was am Blatt eingestellt werden kann - und sonst nichts.

        Aus der Kanzlei am 14.10.2026: „ob die KI das Schreiben inklusive
        Briefbogen generieren kann, so dass die Vorschau besser anpassbar
        ist." Der Briefbogen bleibt eine Datei; anpassbar wird, was
        dazwischen liegt: Textbeginn, Schrift, Größe, Zeilenabstand.

        Die Werte gelten für die Ansicht UND für die Word-Datei. Eine
        Ansicht, die anders aussieht als das Blatt, wäre schlimmer als
        keine.
        """
        d.berechtigungen.nutzer(ident)
        briefbogen.einstellungen_speichern(daten.model_dump())
        ereignis(_log, "blatt_eingestellt", nutzer=ident.nutzer_id)
        return briefbogen.seitenbild()

    @app.get("/api/briefbogen/bild")
    def briefbogen_bild(teil: str, ident: Identitaet = Depends(identitaet)) -> Response:
        """Ein Bild aus der Vorlage - Logo, Marke, was der Kopf eben trägt.

        ``teil`` kommt aus der Ansicht zurück und geht unverändert wieder
        hinein; gelesen wird nur, was das Paket selbst auflistet.
        """
        d.berechtigungen.nutzer(ident)
        inhalt, art = briefbogen.bild_lesen(teil)
        # Ein Briefbogen ändert sich selten; der Browser darf ihn behalten.
        return Response(content=inhalt, media_type=art,
                        headers={"Cache-Control": "private, max-age=600"})

    @app.get("/api/entwuerfe/{entwurf_id}/briefbogen")
    def entwurf_auf_briefbogen(entwurf_id: str,
                               ident: Identitaet = Depends(identitaet)) -> Response:
        """Den Entwurf auf dem Briefbogen der Kanzlei - als Word-Datei.

        Es wird nichts auf die Platte geschrieben: Das Dokument entsteht im
        Arbeitsspeicher und geht an den Browser. Wohin es kommt, entscheidet
        der Bearbeiter im Speichern-Dialog.
        """
        entwurf = d.entwuerfe.lesen(ident, entwurf_id)
        inhalt = briefbogen.erzeugen(briefbogentext(entwurf))
        ereignis(_log, "entwurf_auf_briefbogen", entwurf_id=entwurf.id,
                 nutzer=ident.nutzer_id, bytes=len(inhalt))
        name = f"Entwurf-{entwurf.id}.docx"
        return Response(
            content=inhalt,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @app.delete("/api/entwuerfe/{entwurf_id}", status_code=204)
    def entwurf_verwerfen(entwurf_id: str, ident: Identitaet = Depends(identitaet)) -> None:
        d.entwuerfe.verwerfen(ident, entwurf_id)

    # ── Oberfläche ────────────────────────────────────────────────────────

    if STATISCH.is_dir():
        @app.get("/", include_in_schema=False)
        def startseite() -> FileResponse:
            return FileResponse(STATISCH / "index.html")

        app.mount("/static", StaticFiles(directory=STATISCH), name="static")

    return app


def _sitzung_antwort(d: Dienste, sitzung: Any) -> dict[str, Any]:
    dokumente = d.sitzungen.dokumente(sitzung)
    return {
        "sitzung": sitzung.model_dump(),
        "dokumente": [x.model_dump() for x in dokumente],
        # Was in der E-Akte liegt und noch keinen Inhalt hat: Mail, beA, Post.
        # Was fehlt, soll sichtbar fehlen - sonst sieht eine unvollstaendige
        # Liste aus wie eine vollstaendige.
        "korrespondenz_ohne_inhalt": getattr(d.adapter, "letzte_korrespondenz_ohne_inhalt", 0),
        # E-Mails, deren Inhalt nicht geholt werden konnte. Aus der Kanzlei am
        # 08.10.2026: „Obergrenze sollte festgelegt werden, bei Ueberschreitung
        # sollte der Bearbeiter gewarnt werden und aufmerksam gemacht werden."
        # Die Warnung steht auch in der Zeile des Dokuments selbst; hier steht
        # die Zahl, damit sie niemand zaehlen muss.
        "mails_ohne_inhalt": {
            "zu_gross": getattr(d.adapter, "letzte_mails_zu_gross", 0),
            "gesamtmass": getattr(d.adapter, "letzte_mails_ueber_budget", 0),
            "ohne_antwort": getattr(d.adapter, "letzte_mails_ohne_antwort", 0),
        },
        "mail_anhaenge": getattr(d.adapter, "letzte_mail_anhaenge", 0),
        # Was beim Zerlegen der Mails nicht uebernommen wurde, mit Grund.
        # Befund N04 der dritten Zweitpruefung vom 12.10.2026: Der Parser
        # kannte diese Zahlen, der Adapter nahm sie nicht, und die Anzeige
        # zeigte nur die angenommenen Anlagen - eine unvollstaendige Liste,
        # die vollstaendig aussah. Grund -> Anzahl, damit die Oberflaeche
        # sagen kann, WARUM etwas fehlt.
        "mail_ausgelassen": dict(getattr(d.adapter, "letzte_mail_ausgelassen", {})),
        # Angehaengte Nachrichten, deren Text mitgekommen ist (Befund N03).
        "mail_nachrichten": getattr(d.adapter, "letzte_mail_nachrichten", 0),
        # Die Akte nennt keinen Dateiordner. Dann fehlen die Dateien - aber
        # die E-Akte steht trotzdem da (Befund N07). Eine leere Liste sieht
        # sonst aus wie "die Akte ist leer" und heisst "ich habe nicht
        # nachgesehen".
        "akte_ohne_dateiordner": bool(
            getattr(d.adapter, "letzte_akte_ohne_dateiordner", False)),
        # Eintraege, an denen das Aufbauen der Liste gescheitert ist:
        # Ausnahmekette -> Anzahl. Die Kette traegt Typen und Codestellen,
        # keinen Wortlaut und keine Aktenkennung - sie darf angezeigt werden.
        #
        # Aus der Kanzlei am 13.10.2026: "Akte oeffnen nicht moeglich". Ein
        # einziger unerwarteter Eintrag riss das Oeffnen mit. Jetzt faellt
        # dieser eine aus und steht hier - der Bearbeiter sieht, dass etwas
        # fehlt, und kann sagen, was.
        "eintraege_mit_fehler": dict(
            getattr(d.adapter, "letzte_eintraege_mit_fehler", {})),
        "beteiligte": [x.model_dump() for x in d.sitzungen.beteiligte(sitzung)],
        "fristen": [x.model_dump() for x in d.sitzungen.fristen(sitzung)],
        "gedaechtnis": _gedaechtnis_uebersicht(d, sitzung),
        # Was eine Frage mit den geladenen Dokumenten ungefähr kostet. Der
        # Umfang steht schon in der Sitzung; es wird nichts nachgelesen.
        "kostenschaetzung": _kostenschaetzung(d, sitzung),
    }


def _unerwartet_im_strom(fehler: Exception, woher: str) -> str:
    """Ein unerwarteter Fehler mitten im Strom - mit Nummer und Protokollzeile.

    Die Fehlergrenze kann hier nicht helfen: Der Strom hat begonnen, die
    Antwort ist unterwegs, und mehr als ein letztes Ereignis geht nicht
    hinaus. Damit fehlte diesem Weg genau das, was den anderen
    wiederauffindbar macht - eine Nummer und eine Zeile im Fenster.

    Hinaus geht kein Wortlaut: ``str(fehler)`` kann ein Stueck der Akte
    tragen. Die Kette traegt Typen und Codestellen.
    """
    nummer = secrets.token_hex(4)
    stoerung(_log, "fehler_im_strom", woher=woher, nummer=nummer,
             kette=ausnahmekette(fehler)[:MAX_WERT_LAENGE])
    return (f"{UNBEKANNT} Vorgangsnummer {nummer}. Im schwarzen Fenster des "
            f"Servers steht eine Zeile mit dieser Nummer - sie nennt die "
            f"Ursache.")


def _gedaechtnis_uebersicht(d: Dienste, sitzung: Any) -> dict[str, Any]:
    """Die Uebersicht - und wenn sie nicht zu lesen ist, dann das.

    Aus der Kanzlei am 13.10.2026: "Akte oeffnen nicht moeglich". Ein
    Gedaechtnis, das sich nicht mehr einlesen laesst, machte auch diese
    Antwort unmoeglich - und damit war die Akte nicht nur ohne Erinnerung,
    sondern ueberhaupt nicht zu oeffnen. Die Oberflaeche braucht die
    Uebersicht fuer jedes Fenster.

    Hier steht deshalb der ehrliche Ersatz: nichts vorhanden, dazu der Grund
    (``unlesbar``). Genau dort steht in der Oberflaeche der Weg hinaus, und
    "Gedaechtnis verwerfen" braucht die Uebersicht nicht - es loescht.
    """
    try:
        return d.gedaechtnis.uebersicht(d.gedaechtnis.lesen(sitzung.akte_id))
    except GedaechtnisFehler as fehler:
        return d.gedaechtnis.uebersicht(None) | {"unlesbar": str(fehler)}


def _kostenschaetzung(d: Dienste, sitzung: Any) -> dict[str, Any]:
    """Obergrenze: alle geladenen Dokumente, begrenzt durch das Passagenbudget.

    Die tatsächliche Auswahl hängt an der Frage und ist meist kleiner. Die
    Schätzung darf deshalb nach oben abweichen, aber nicht nach unten – eine
    zu niedrige Zahl wäre schlimmer als gar keine.
    """
    zeichen = min(sum(x.zeichen for x in sitzung.geladen), d.einstellungen.max_passagen_zeichen)
    werte = d.kosten.schaetzen(d.einstellungen.modell_fuer("frage"), zeichen)
    werte["dokumente"] = len(sitzung.geladen)
    return werte


def briefbogentext(entwurf: Any) -> str:
    """Was auf dem Briefbogen steht: der Betreff und der Brief. Sonst nichts.

    **Hier stand bis zum 14.10.2026 auch ein Block mit den Hinweisen der
    Belegpruefung**, eingeleitet von einer Trennlinie. Die Begruendung war
    ernst gemeint: Ein Entwurf, dem eine Aussage fehlt, sieht ohne diesen
    Satz aus wie ein fertiger Brief.

    Am gedruckten Blatt gemessen war sie trotzdem falsch. Aus der Kanzlei:
    „Es gab keinen vernuenftigen Text." Der Block schob den Brief auf eine
    zweite Seite, auf der dann drei Zeilen interner Vermerk unter dem
    vollstaendigen Briefkopf standen - und die haette jemand loeschen
    muessen, bevor das Schreiben hinausgeht. Ein Brief, an dem vor dem
    Versand noch etwas zu entfernen ist, ist kein fertiger Brief.

    Die Hinweise sind damit nicht verschwunden: Sie stehen im
    Vorschaufenster unmittelbar ueber dem Entwurf, in der Blattansicht
    daneben, in der Chatkarte und in der Meldung beim Herunterladen. Vier
    Stellen im Programm statt einer auf dem Papier, das hinausgeht.

    Die Fundstellen kommen ebenfalls nicht mit - sie sind der Weg zum Beleg
    im Programm; der Auftragstext sagt dem Modell dasselbe: „die Kanzlei
    entfernt sie nach der Pruefung."
    """
    zeilen: list[str] = []
    if entwurf.betreff:
        # Fett, wie die Betreffzeile eines deutschen Geschaeftsbriefs.
        zeilen += [f"**{entwurf.betreff}**", ""]
    zeilen.append(ohne_belege(entwurf.text))
    return "\n".join(zeilen)


def _entwurf_antwort(entwurf: Any) -> dict[str, Any]:
    daten = entwurf.model_dump()
    # Ueber die ganze Freigabevorlage, nicht nur ueber den Text: Betreff, Art
    # und Akte werden mitgeschrieben und gehoeren deshalb in die Pruefsumme
    # (Befund F06 der Zweitpruefung, 05.10.2026).
    daten["freigabe_pruefsumme"] = text_pruefsumme(freigabevorlage(entwurf))
    return daten
