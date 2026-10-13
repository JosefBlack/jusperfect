"""Entwürfe: erzeugen, bearbeiten, freigeben – und erst dann nach jurnodes.

Ein Entwurf ist bis zur Freigabe ein temporäres Objekt im Sitzungsspeicher.
Freigeben kann nur, wer ihn erstellt hat, und nur mit ausdrücklicher
Bestätigung des exakt angezeigten Textes. Die Freigabe ist an diesen Text
gebunden; der jur|nodes-Adapter prüft sie, bevor er schreibt.
"""

from __future__ import annotations

import json
import re
import threading
import uuid

from jusperfect.config import Einstellungen
from jusperfect.domain.models import (
    Beteiligter, Entwurf, EntwurfArt, Entwurfsfassung, EntwurfStatus, ENTWURF_BEZEICHNUNG,
    Frist, MAX_VORFASSUNGEN, Passage, Sitzung,
)
from jusperfect.jurnodes.base import JurNodesAdapter
from jusperfect.security.approval import Freigabestelle
from jusperfect.security.identitaet import Identitaet
from jusperfect.security.protokoll import ereignis, protokoll
from jusperfect.services import prompts
# Umbenannt: siehe analyse.py - der Parameter "fristen" wuerde das
# Modul innerhalb der Methode ueberdecken.
from jusperfect.services.belegpflicht import entwurf_fail_closed
from jusperfect.services.fristen import (
    entschaerfen as frist_entschaerfen,
    hinweis as frist_hinweis,
)
from jusperfect.services.ausgang import Ausgang, Ausgangskontext
from jusperfect.services.json_ausgabe import AusgabeUnbrauchbar, json_extrahieren
from jusperfect.services.passagen import budget_anwenden, relevante_passagen
from jusperfect.services.quellen import bis_zum_letzten_beleg, index_bauen
from jusperfect.speicher.base import SitzungsSpeicher

_log = protokoll("entwuerfe")

KENNZEICHNUNG = "ENTWURF – anwaltliche Prüfung erforderlich"


class EntwurfFehler(RuntimeError):
    pass


class EntwurfNichtGefunden(LookupError):
    pass


FREIGABE_FASSUNG = "1"


def freigabevorlage(entwurf) -> str:
    """Genau das, was nach jurnodes geschrieben wird – als ein Text.

    Befund F06 der Zweitprüfung vom 05.10.2026. Bestätigt wurde bisher die
    Prüfsumme **des Textes**. Geschrieben werden aber vier Dinge: Akte, Art,
    Betreff und Text. Fenster A lud den Entwurf, Fenster B änderte nur den
    Betreff, Fenster A gab mit der alten Prüfsumme frei – und der neue, dort
    nie gesehene Betreff ging in den Vermerktext **und** in den Titel nach
    jur|nodes.

    Die Kryptografie war dabei nicht gebrochen; sie signierte nur das, was ihr
    gegeben wurde, und das war zu wenig. Deshalb steht hier eine *Vorlage*:
    eine feste, benannte Reihenfolge über alle geschriebenen Felder. Ändert
    sich eines, ändert sich die Prüfsumme, und die Freigabe wird abgewiesen.

    Die Fassungsnummer in der ersten Zeile ist kein Zierrat: Kommt ein Feld
    hinzu, bekommt sie eine neue Nummer, und alte Prüfsummen passen nicht mehr
    – was richtig ist, denn sie bezeugen eine Ansicht, die es nicht mehr gibt.
    """
    return "\n".join([
        f"jusperfect-freigabe/{FREIGABE_FASSUNG}",
        f"akte: {entwurf.akte_id}",
        f"art: {getattr(entwurf.art, 'value', entwurf.art)}",
        f"betreff: {entwurf.betreff}",
        "text:",
        entwurf.text,
    ])


def betreff_aus_der_akte(art: EntwurfArt, akte) -> str:
    """Der Betreff eines Entwurfs – aus der Akte, nicht aus dem Modell.

    Befund N12 der dritten Zweitprüfung vom 12.10.2026: Das Modell liefert
    ``betreff`` und ``text``. Nur ``text`` ging durch die Belegprüfung. Ein
    Betreff wie „Anerkenntnis der Haftung vom 14.03.2026" blieb unverändert
    stehen, sobald der Brieftext irgendeinen tragenden Beleg hatte – und kam
    mit HTTP 201 heraus.

    Der Betreff ist dabei nicht nur Zierrat: Bei der Freigabe geht er in den
    **Vermerktext** und in den **Titel** des Vermerks nach jur|nodes. Eine
    erfundene Behauptung landete also an der sichtbarsten Stelle der Akte.

    Zu belegen ist ein Betreff schwer – er ist kein Satz, und ein ``[Q: …]``
    im Betreff wäre unbrauchbar. Deshalb wird er hier **nicht geprüft, sondern
    gar nicht erst vom Modell genommen**: Art des Schreibens, Aktenzeichen und
    Bezeichnung der Akte stehen alle in jur|nodes. Keine dieser drei Angaben
    kann das Modell erfinden.

    Wer einen anderen Betreff will, trägt ihn ein – ``bearbeiten`` nimmt ihn,
    und die Freigabeprüfsumme bindet ihn (Befund F06). Dann steht dort, was
    ein Mensch geschrieben hat.
    """
    teile = [ENTWURF_BEZEICHNUNG[art]]
    for angabe in (getattr(akte, "aktenzeichen", ""), getattr(akte, "bezeichnung", "")):
        angabe = str(angabe or "").strip()
        if angabe:
            teile.append(angabe)
    return " · ".join(teile)


#: Wo im JSON der Entwurfstext anfaengt. Das Modell antwortet mit
#: ``{"betreff": "...", "text": "..."}``; beim Stroemen ist davon immer nur
#: ein Anfang da.
_TEXT_ANFANG = re.compile(r'"text"\s*:\s*"')


def teiltext(roh: str) -> str:
    """Der bisher angekommene Wert von ``"text"`` aus unvollstaendigem JSON.

    Aus der Kanzlei am 13.10.2026: „Ein Vorschaufenster, in welchem der
    Entwurf nach und nach entsteht."

    Dafuer muss der Text waehrend des Schreibens lesbar sein - und er steckt
    in einem JSON-Objekt, das erst am Ende schliesst. ``json.loads`` kann
    damit nichts anfangen; es braucht ein vollstaendiges Objekt.

    Hier wird deshalb nur **dieses eine Feld** gelesen, und zwar bis zu der
    Stelle, an der es sicher vollstaendig ist: Ein halb angekommenes
    Fluchtzeichen (``\\`` ohne sein Zeichen, ``\\u`` ohne seine vier
    Ziffern) wird weggelassen und kommt im naechsten Stueck mit. Das ist
    wichtiger, als es aussieht: ``json.loads('"...\\u00e"')`` wirft, und ein
    Fehler mitten im Strom saehe fuer den Bearbeiter aus, als sei der Entwurf
    gescheitert.

    Gibt ``""`` zurueck, solange nichts Brauchbares dasteht. Nie eine
    Ausnahme: Was hier ankommt, ist die Ausgabe eines Modells, also alles.
    """
    treffer = _TEXT_ANFANG.search(roh)
    if treffer is None:
        return ""
    rest = roh[treffer.end():]
    stueck: list[str] = []
    stelle = 0
    while stelle < len(rest):
        zeichen = rest[stelle]
        if zeichen == '"':                     # Ende des Feldes
            break
        if zeichen != "\\":
            stueck.append(zeichen)
            stelle += 1
            continue
        if stelle + 1 >= len(rest):            # Fluchtzeichen halb da
            break
        if rest[stelle + 1] == "u":
            if stelle + 6 > len(rest):         # \uXXXX halb da
                break
            stueck.append(rest[stelle:stelle + 6])
            stelle += 6
            continue
        stueck.append(rest[stelle:stelle + 2])
        stelle += 2
    try:
        return json.loads('"' + "".join(stueck) + '"')
    except ValueError:
        return ""


class Entwurfsdienst:
    def __init__(self, ausgang: Ausgang, speicher: SitzungsSpeicher,
                 adapter: JurNodesAdapter, freigabestelle: Freigabestelle,
                 einstellungen: Einstellungen, berechtigungen=None) -> None:
        self._ausgang = ausgang
        self._speicher = speicher
        self._adapter = adapter
        self._freigabestelle = freigabestelle
        self._e = einstellungen
        # Befund F07: Die Aktenberechtigung wurde beim Entwurf nie geprueft -
        # nur, ob der Nutzer ihn selbst angelegt hat. Wer die Akte verlor,
        # konnte den fertigen Entwurf weiter lesen und freigeben.
        self._berechtigungen = berechtigungen
        # Pruefen, Statuswechsel und Schreiben gehoeren zusammen. Ohne diese
        # Klammer gaben zwei gleichzeitige Freigaben beide den Statustest frei
        # und schrieben zwei Vermerke in dieselbe Akte.
        self._freigabeschloss = threading.Lock()

    # ── Vorbereiten, aufrufen, pruefen ───────────────────────────────────
    #
    # Herausgeloest am 13.10.2026 fuer das Vorschaufenster. Vier Wege gehen
    # jetzt hier hindurch - erstellen, erstellen_stream, ueberarbeiten,
    # ueberarbeiten_stream -, und sie muessen dieselben Pruefungen bestehen.
    # Vorher stand alles einmal in `erstellen`; eine zweite Abschrift davon
    # waere eine zweite Stelle, an der die Belegpflicht vergessen werden
    # kann.

    def _vorbereiten(self, sitzung: Sitzung, passagen: list[Passage], art: EntwurfArt,
                     anweisung: str, empfaenger: str, beteiligte: list[Beteiligter],
                     fristen: list[Frist], referenzen: list[Passage] = ()):
        if not passagen:
            raise EntwurfFehler("Es sind keine Dokumente geladen.")
        auswahl = relevante_passagen(f"{ENTWURF_BEZEICHNUNG[art]} {anweisung} {empfaenger}",
                                     passagen, self._e.max_frage_passagen * 2)
        if referenzen:
            auswahl = auswahl + list(referenzen)
        auswahl, gekuerzt = budget_anwenden(auswahl, self._e.max_passagen_zeichen)
        # Der eine Aufruf, der das Aktenzeichen braucht: Ein Anschreiben traegt
        # "Unser Zeichen". Ueberall sonst bleibt es drinnen (Befund F11).
        material = prompts.material_bauen(sitzung.akte, beteiligte, fristen, auswahl,
                                          mit_aktenzeichen=True)
        return auswahl, gekuerzt, material

    def _aus_antwort(self, antworttext: str, auswahl: list[Passage], gekuerzt: bool,
                     fristen: list[Frist], art: EntwurfArt, akte) -> tuple[str, str, list, list[str]]:
        """Aus der Modellantwort wird ein prueffaehiger Entwurf - oder nichts.

        Der Betreff kommt aus der Akte, nicht aus der Antwort (Befund N12,
        siehe ``betreff_aus_der_akte``). Sagt das Modell trotzdem einen, wird
        er nicht verworfen, sondern als ungeprueft gekennzeichneter Vorschlag
        in die Hinweise gelegt - sichtbar fuer den Bearbeiter, aber ausserhalb
        von Entwurf, Vermerktext und Vermerktitel.
        """
        betreff = betreff_aus_der_akte(art, akte)
        vorschlag = ""
        try:
            roh = json_extrahieren(antworttext)
            text = str(roh.get("text", "")).strip()
            vorschlag = str(roh.get("betreff", "")).strip()
        except AusgabeUnbrauchbar:
            text = antworttext.strip()
        if not text:
            raise EntwurfFehler("Das Modell hat keinen Entwurf geliefert.")
        index = index_bauen(auswahl)
        # Fail closed, auch im Entwurf (Befund F04 der Zweitpruefung,
        # 05.10.2026). Vorher stand hier nur `zitate_aufloesen`: Das setzt an
        # die Stelle eines nicht auflösbaren Belegs die Marke „[Q: ohne
        # Beleg]" und laesst die Behauptung stehen. Ein vollstaendig
        # erfundener Entwurf kam so mit HTTP 201 und leerer Quellenliste
        # heraus - die leere Liste sagt es dem Programm, gesehen hat sie
        # niemand.
        ergebnis = entwurf_fail_closed(text, index)
        text, quellen, hinweise = ergebnis.text, ergebnis.quellen, list(ergebnis.hinweise)
        if not quellen:
            raise EntwurfFehler(
                "Der Entwurf trug keinen einzigen belastbaren Beleg und wird deshalb "
                "nicht ausgegeben. Bitte die Anweisung genauer fassen oder die Auswahl "
                "der Dokumente prüfen.")
        if ergebnis.verworfen:
            hinweise.insert(0, f"{ergebnis.verworfen} Aussage(n) ohne belastbaren Beleg "
                               f"aus dem Entwurf entfernt.")
        # Ein Entwurf geht am Ende hinaus. Eine gerechnete Frist darin waere der
        # teuerste Fehler, den dieses Programm machen kann.
        text, gerechnet = frist_entschaerfen(text, index, fristen)
        if gerechnet:
            hinweise.append(frist_hinweis(gerechnet))
        if gekuerzt:
            hinweise.append("Nicht alle Passagen passten in den Aufruf; der Entwurf beruht auf einer Auswahl.")
        # Der Vorschlag des Modells, falls es einen gemacht hat: ungeprueft und
        # als Vorschlag benannt. Er geht nicht nach jur|nodes - Hinweise tun
        # das nicht - und nicht in die Freigabevorlage.
        if vorschlag and vorschlag != betreff:
            hinweise.append(
                f"Betreffvorschlag des Modells, nicht übernommen und nicht belegt: "
                f"„{vorschlag}“. Der Betreff oben steht aus der Akte. Wer den "
                f"Vorschlag will, trägt ihn ein.")
        return betreff, text, quellen, hinweise

    def _vorschau(self, roh: str, index: dict, fristen: list[Frist]) -> str:
        """Was vom bisher Angekommenen schon gezeigt werden darf.

        Dieselbe Regel wie bei der Frage (Befund F05 der Zweitpruefung,
        05.10.2026): Es stroemt **nur Geprueftes**. Gezeigt wird erst, was
        mit einem vollstaendigen Beleg endet und durch Belegpflicht und
        Fristensperre gelaufen ist. Ein Text, der erst dasteht und dann
        verschwindet, ist gezeigt worden.
        """
        text = teiltext(roh)
        if not text:
            return ""
        abgeschlossen = bis_zum_letzten_beleg(text)
        if not abgeschlossen:
            return ""
        ergebnis = entwurf_fail_closed(abgeschlossen, index)
        if not ergebnis.quellen:
            return ""
        sauber, _ = frist_entschaerfen(ergebnis.text, index, fristen)
        return sauber

    # ── Erstellen ────────────────────────────────────────────────────────

    def erstellen(self, identitaet: Identitaet, sitzung: Sitzung, passagen: list[Passage], art: EntwurfArt,
                  anweisung: str, empfaenger: str, beteiligte: list[Beteiligter], fristen: list[Frist],
                  muster: str = "", referenzen: list[Passage] = ()) -> Entwurf:
        auswahl, gekuerzt, material = self._vorbereiten(
            sitzung, passagen, art, anweisung, empfaenger, beteiligte, fristen, referenzen)
        aufgabe = prompts.aufgabe_entwurf(art, anweisung, empfaenger, muster)
        kontext = Ausgangskontext(identitaet, sitzung.id, sitzung.akte_id, "entwurf",
                                  passagen=len(auswahl), detail=art.value)
        durchgang = self._ausgang.fragen(kontext, prompts.SYSTEM, material, aufgabe)
        betreff, text, quellen, hinweise = self._aus_antwort(
            durchgang.antwort.text, auswahl, gekuerzt, fristen, art, sitzung.akte)
        entwurf = Entwurf(
            id=uuid.uuid4().hex, akte_id=sitzung.akte_id, art=art, betreff=betreff,
            text=text, quellen=quellen, hinweise=hinweise, erstellt_von=identitaet.nutzer_id,
            modell=durchgang.antwort.modell, kosten=durchgang.kosten,
        )
        self._speicher.entwurf_ablegen(entwurf)
        return entwurf

    def erstellen_stream(self, identitaet: Identitaet, sitzung: Sitzung, passagen: list[Passage],
                         art: EntwurfArt, anweisung: str, empfaenger: str,
                         beteiligte: list[Beteiligter], fristen: list[Frist],
                         muster: str = "", referenzen: list[Passage] = ()):
        """Wie ``erstellen``, aber stueckweise - und **nur Geprueftes**.

        Aus der Kanzlei am 13.10.2026: „Ein Vorschaufenster, in welchem der
        Entwurf nach und nach entsteht."

        Drei Arten von Ereignissen, wie bei der Frage:

        * ``("fortschritt", Zeichenzahl)`` - das Modell schreibt. Kein Inhalt.
        * ``("geprueft", Text)`` - alles bis hier Abgeschlossene, durch
          Belegpflicht und Fristensperre. Ersetzt die vorige Fassung.
        * ``("fertig", Entwurf)`` - der abgelegte Entwurf.
        """
        auswahl, gekuerzt, material = self._vorbereiten(
            sitzung, passagen, art, anweisung, empfaenger, beteiligte, fristen, referenzen)
        aufgabe = prompts.aufgabe_entwurf(art, anweisung, empfaenger, muster)
        kontext = Ausgangskontext(identitaet, sitzung.id, sitzung.akte_id, "entwurf",
                                  passagen=len(auswahl), detail=art.value)
        durchgang, antworttext = yield from self._stroemen(
            kontext, material, aufgabe, index_bauen(auswahl), fristen)
        betreff, text, quellen, hinweise = self._aus_antwort(
            antworttext, auswahl, gekuerzt, fristen, art, sitzung.akte)
        entwurf = Entwurf(
            id=uuid.uuid4().hex, akte_id=sitzung.akte_id, art=art, betreff=betreff,
            text=text, quellen=quellen, hinweise=hinweise, erstellt_von=identitaet.nutzer_id,
            modell=durchgang.antwort.modell, kosten=durchgang.kosten,
        )
        self._speicher.entwurf_ablegen(entwurf)
        yield ("fertig", entwurf)

    def _stroemen(self, kontext, material: str, aufgabe: str, index: dict, fristen: list[Frist]):
        """Der gemeinsame Strom von Erstellen und Ueberarbeiten."""
        durchgang = None
        roh, gesendet = "", ""
        for stueck in self._ausgang.fragen_stream(kontext, prompts.SYSTEM, material, aufgabe):
            if not isinstance(stueck, str):
                durchgang = stueck
                continue
            roh += stueck
            # Nur die Zeichenzahl: dass gearbeitet wird, nicht was dasteht.
            yield ("fortschritt", len(roh))
            vorschau = self._vorschau(roh, index, fristen)
            if vorschau and vorschau != gesendet:
                gesendet = vorschau
                yield ("geprueft", vorschau)
        if durchgang is None:
            raise EntwurfFehler("Der Anbieter lieferte keine Antwort.")
        return durchgang, durchgang.antwort.text

    # ── Ueberarbeiten: der Entwurf aendert sich durch den Chat ───────────

    def ueberarbeiten(self, identitaet: Identitaet, sitzung: Sitzung, passagen: list[Passage],
                      entwurf_id: str, anweisung: str, beteiligte: list[Beteiligter],
                      fristen: list[Frist], referenzen: list[Passage] = ()) -> Entwurf:
        """Den vorhandenen Entwurf nach einer Anweisung aendern.

        Die bisherige Fassung bleibt erhalten (``vorfassungen``): Wer ueber
        den Chat aendert, soll zurueckgehen koennen, wenn die neue Fassung
        schlechter ist als die alte.
        """
        for art, wert in self.ueberarbeiten_stream(
                identitaet, sitzung, passagen, entwurf_id, anweisung,
                beteiligte, fristen, referenzen):
            if art == "fertig":
                return wert
        raise EntwurfFehler("Der Anbieter lieferte keine Antwort.")

    def ueberarbeiten_stream(self, identitaet: Identitaet, sitzung: Sitzung,
                             passagen: list[Passage], entwurf_id: str, anweisung: str,
                             beteiligte: list[Beteiligter], fristen: list[Frist],
                             referenzen: list[Passage] = ()):
        if not anweisung.strip():
            raise EntwurfFehler("Es steht keine Änderung da.")
        alt = self.lesen(identitaet, entwurf_id)
        if alt.status != EntwurfStatus.ENTWURF:
            raise EntwurfFehler("Ein freigegebener oder verworfener Entwurf wird nicht mehr geändert.")
        auswahl, gekuerzt, material = self._vorbereiten(
            sitzung, passagen, alt.art, anweisung, "", beteiligte, fristen, referenzen)
        aufgabe = prompts.aufgabe_entwurf_ueberarbeiten(alt.art, anweisung, alt.text)
        kontext = Ausgangskontext(identitaet, sitzung.id, sitzung.akte_id, "entwurf",
                                  passagen=len(auswahl), detail=alt.art.value)
        durchgang, antworttext = yield from self._stroemen(
            kontext, material, aufgabe, index_bauen(auswahl), fristen)
        betreff, text, quellen, hinweise = self._aus_antwort(
            antworttext, auswahl, gekuerzt, fristen, alt.art, sitzung.akte)
        yield ("fertig", self._fassung_ablegen(alt, anweisung, betreff, text, quellen,
                                               hinweise, durchgang))

    def _fassung_ablegen(self, alt: Entwurf, anweisung: str, betreff: str, text: str,
                         quellen, hinweise: list[str], durchgang) -> Entwurf:
        """Die neue Fassung - mit der alten im Ruecken.

        Der Betreff der alten Fassung bleibt stehen, wenn er von Hand
        gesetzt wurde: ``betreff_aus_der_akte`` liefert immer denselben Wert,
        und eine Ueberarbeitung soll eine Eintragung des Bearbeiters nicht
        stillschweigend zuruecknehmen.
        """
        vorher = Entwurfsfassung(nummer=alt.fassung, betreff=alt.betreff, text=alt.text,
                                 anweisung=anweisung)
        behalten = (list(alt.vorfassungen) + [vorher])[-MAX_VORFASSUNGEN:]
        neu = alt.model_copy(update={
            "betreff": alt.betreff or betreff,
            "text": text,
            "quellen": quellen,
            "hinweise": hinweise,
            "modell": durchgang.antwort.modell,
            "kosten": durchgang.kosten,
            "fassung": alt.fassung + 1,
            "vorfassungen": behalten,
        })
        self._speicher.entwurf_ablegen(neu)
        ereignis(_log, "entwurf_ueberarbeitet", entwurf_id=neu.id, fassung=neu.fassung,
                 nutzer=alt.erstellt_von, zeichen=len(text))
        return neu

    def zuruecknehmen(self, identitaet: Identitaet, entwurf_id: str) -> Entwurf:
        """Eine Fassung zurueck.

        Ohne diesen Weg waere jede Aenderung ueber den Chat endgueltig, und
        der Bearbeiter muesste die vorige Fassung aus dem Gedaechtnis
        nachtippen. Zurueckgenommen wird nur der Text; die Quellen werden am
        zurueckgeholten Text neu bestimmt - sonst stuenden Belege darunter,
        die in ihm gar nicht mehr vorkommen.
        """
        entwurf = self.lesen(identitaet, entwurf_id)
        if entwurf.status != EntwurfStatus.ENTWURF:
            raise EntwurfFehler("Ein freigegebener oder verworfener Entwurf wird nicht mehr geändert.")
        if not entwurf.vorfassungen:
            raise EntwurfFehler("Es gibt keine frühere Fassung.")
        vorher = entwurf.vorfassungen[-1]
        zurueck = entwurf.model_copy(update={
            "betreff": vorher.betreff,
            "text": vorher.text,
            "quellen": [q for q in entwurf.quellen if q.kennung in vorher.text],
            "hinweise": [h for h in entwurf.hinweise if not h.startswith("Betreffvorschlag")],
            "fassung": vorher.nummer,
            "vorfassungen": entwurf.vorfassungen[:-1],
        })
        self._speicher.entwurf_ablegen(zurueck)
        ereignis(_log, "entwurf_zurueckgenommen", entwurf_id=zurueck.id,
                 fassung=zurueck.fassung, nutzer=identitaet.nutzer_id)
        return zurueck

    def lesen(self, identitaet: Identitaet, entwurf_id: str) -> Entwurf:
        """Der Entwurf – und nur, wenn die Akte jetzt noch offensteht.

        Befund F07 der Zweitprüfung vom 05.10.2026: Geprüft wurde allein die
        Erstellerkennung. Ein Nutzer, dem die Akte entzogen worden war, bekam
        auf die Sitzung richtig 403 – und konnte denselben Entwurf weiter
        lesen und sogar freigeben, also in genau diese Akte schreiben.

        Geprüft wird bei **jedem** Zugriff neu, nicht beim Anlegen: Eine
        Rechteänderung wirkt sonst erst beim nächsten Entwurf, und der
        vorbereitete Schreibweg bleibt offen.

        Dass in dieser Kanzlei alle alle Akten sehen, ändert daran nichts –
        dann geht die Prüfung eben immer durch. Die Lücke bestand für den
        eingeschränkten Betrieb, den das Programm ausdrücklich kann.
        """
        entwurf = self._speicher.entwurf_lesen(entwurf_id)
        if entwurf is None or entwurf.erstellt_von != identitaet.nutzer_id:
            raise EntwurfNichtGefunden("Der Entwurf ist unbekannt oder abgelaufen.")
        if self._berechtigungen is not None:
            self._berechtigungen.pruefen(identitaet, entwurf.akte_id)
        return entwurf

    def bearbeiten(self, identitaet: Identitaet, entwurf_id: str, betreff: str, text: str) -> Entwurf:
        entwurf = self.lesen(identitaet, entwurf_id)
        if entwurf.status != EntwurfStatus.ENTWURF:
            raise EntwurfFehler("Ein freigegebener oder verworfener Entwurf wird nicht mehr geändert.")
        if not text.strip():
            raise EntwurfFehler("Der Text darf nicht leer sein.")
        entwurf = entwurf.model_copy(update={"betreff": betreff.strip() or entwurf.betreff, "text": text})
        self._speicher.entwurf_ablegen(entwurf)
        return entwurf

    def freigeben(self, identitaet: Identitaet, entwurf_id: str, bestaetigung: bool,
                  freigabe_pruefsumme: str) -> Entwurf:
        """Schreibt den Entwurf als Vermerk in die jurnodes-Akte.

        ``freigabe_pruefsumme`` ist die Prüfsumme der **Freigabevorlage** –
        Akte, Art, Betreff und Text zusammen, also alles, was geschrieben
        wird. Bis zum 05.10.2026 war es die Prüfsumme des Textes allein; ein
        in einem anderen Fenster geänderter Betreff kam damit ungesehen in den
        Vermerk und in den Titel (Befund F06, siehe ``freigabevorlage``).

        Prüfen, Statuswechsel und Schreiben stehen unter einem Schloss und in
        dieser Reihenfolge. Vorher wurde erst geschrieben und dann der Status
        gesetzt: Zwei gleichzeitige Freigaben kamen beide am Statustest vorbei
        und schrieben zwei Vermerke in dieselbe Akte.
        """
        from jusperfect.security.approval import text_pruefsumme as pruefsumme

        with self._freigabeschloss:
            entwurf = self.lesen(identitaet, entwurf_id)
            if not bestaetigung:
                raise EntwurfFehler("Ohne ausdrückliche Bestätigung wird nichts nach jurnodes geschrieben.")
            if entwurf.status != EntwurfStatus.ENTWURF:
                raise EntwurfFehler("Der Entwurf wurde bereits freigegeben oder verworfen.")
            if pruefsumme(freigabevorlage(entwurf)) != freigabe_pruefsumme:
                raise EntwurfFehler(
                    "Der angezeigte Entwurf stimmt nicht mehr mit dem gespeicherten überein – "
                    "Betreff oder Text wurden zwischenzeitlich geändert. Bitte neu laden.")
            # Erst sperren, dann schreiben: Schlaegt das Schreiben fehl, geht
            # der Entwurf zurueck in den Entwurfsstand, und der Fehler geht
            # weiter. Ein zweiter Aufruf findet bis dahin "bereits freigegeben".
            gesperrt = entwurf.model_copy(update={"status": EntwurfStatus.FREIGEGEBEN})
            self._speicher.entwurf_ablegen(gesperrt)
            text_fuer_akte = f"{KENNZEICHNUNG}\n{entwurf.betreff}\n\n{entwurf.text}"
            try:
                freigabe = self._freigabestelle.erteilen(entwurf.id, entwurf.akte_id,
                                                         identitaet.nutzer_id, text_fuer_akte)
                referenz = self._adapter.vermerk_schreiben(
                    entwurf.akte_id, f"{ENTWURF_BEZEICHNUNG[entwurf.art]}: {entwurf.betreff}",
                    text_fuer_akte, freigabe)
            except Exception:
                self._speicher.entwurf_ablegen(entwurf)
                raise
            entwurf = gesperrt.model_copy(update={"jurnodes_referenz": referenz})
            self._speicher.entwurf_ablegen(entwurf)
        ereignis(_log, "entwurf_freigegeben", entwurf_id=entwurf.id, akte=entwurf.akte_id, nutzer=identitaet.nutzer_id,
                 referenz=referenz, pruefsumme=freigabe_pruefsumme[:12])
        return entwurf

    def verwerfen(self, identitaet: Identitaet, entwurf_id: str) -> None:
        entwurf = self.lesen(identitaet, entwurf_id)
        self._speicher.entwurf_loeschen(entwurf.id)
        ereignis(_log, "entwurf_verworfen", entwurf_id=entwurf_id)
