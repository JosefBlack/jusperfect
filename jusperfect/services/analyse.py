"""Frage, Aktenanalyse und Eingangsprüfung – jede Aussage mit Beleg.

Jeder Weg zum Modell läuft über den ``Ausgang``: er prüft die Eingabe, bremst
am Budget, ruft den Anbieter und schreibt den Verarbeitungsnachweis. Dieser
Dienst kümmert sich um das Fachliche davor und danach – Auswahl der Passagen,
Aufbau des Materials und die Belegpflicht über die Antwort.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, ValidationError

from jusperfect.config import Einstellungen
from jusperfect.domain.models import (
    Aktenanalyse, Antwort, Beteiligter, Chronologieergebnis, Frist, Passage, Sitzung, Triage,
)
from jusperfect.security.identitaet import Identitaet
from jusperfect.services import prompts
from jusperfect.services.ausgang import Ausgang, Ausgangskontext, Durchgang
from jusperfect.services.json_ausgabe import AusgabeUnbrauchbar, json_extrahieren
from jusperfect.services.kanzleiwissen import Kanzleiwissen
from jusperfect.services.passagen import budget_anwenden, passagen_waehlen
from jusperfect.services.chronologie import aufraeumen as chronologie_aufraeumen
# Einzeln und umbenannt eingefuehrt: Die Methoden hier haben einen
# Parameter "fristen" - die Fristen aus jur|nodes -, der das Modul sonst
# innerhalb der Methode ueberdeckt. Genau daran ist der erste Einbau
# gescheitert, mit einer Meldung, die auf etwas ganz anderes zeigte.
from jusperfect.services.fristen import (
    entschaerfen as frist_entschaerfen,
    felder_entschaerfen as frist_felder_entschaerfen,
    hinweis as frist_hinweis,
)
from jusperfect.services.belegpflicht import aussage_fail_closed, eintraege_fail_closed
from jusperfect.services.quellen import index_bauen, quellen_aus_kennungen

M = TypeVar("M", bound=BaseModel)


class AktenZuGross(RuntimeError):
    """Die Akte passt nicht in einen Aufruf - und wird deshalb nicht analysiert.

    Frueher wurde in diesem Fall stillschweigend gekuerzt und ein Ergebnis
    geliefert. Das ist der gefaehrlichste Zustand, den dieses Programm kennt:
    Eine Analyse ueber die halbe Akte sieht aus wie eine ueber die ganze -
    dieselbe Chronologie, dieselben sauberen Fundstellen, dieselbe Ruhe. Nur
    fehlt der Schriftsatz von letzter Woche.

    Ein Werkzeug, das Fehler verhindern soll, darf an dieser Stelle keinen
    machen. Kein Ergebnis ist ehrlicher als eines, dem man die Luecke nicht
    ansieht - derselbe Grundsatz, nach dem schon die Belegpflicht arbeitet.

    Die Kanzlei hat es so entschieden: Verweigerung, sobald nicht alle
    uebernommenen Dokumente in den Aufruf passen.
    """


class AnalyseFehler(RuntimeError):
    pass


class Analysedienst:
    def __init__(self, ausgang: Ausgang, einstellungen: Einstellungen,
                 kanzleiwissen: Kanzleiwissen | None = None) -> None:
        self._ausgang = ausgang
        self._e = einstellungen
        self._wissen = kanzleiwissen

    # ── Gemeinsames ────────────────────────────────────────────────────────

    def _strukturiert(self, kontext: Ausgangskontext, material: str, aufgabe: str,
                      modell_typ: type[M], modell: str | None = None) -> tuple[M, Durchgang, dict]:
        """Ein Versuch, bei unbrauchbarem JSON genau ein zweiter mit deutlicher Erinnerung."""
        durchgang = self._ausgang.fragen(kontext, prompts.SYSTEM, material, aufgabe, modell_id=modell)
        for versuch in (1, 2):
            try:
                roh = json_extrahieren(durchgang.antwort.text)
                return modell_typ.model_validate(_quellen_roh_entfernen(roh, modell_typ)), durchgang, roh
            except (AusgabeUnbrauchbar, ValidationError) as e:
                # Abgeschnitten ist etwas anderes als unbrauchbar, und es
                # verdient eine eigene Auskunft. Aus der Kanzlei, 17.09.2026:
                # Ein Prüfbogenlauf über fünfzig Dokumente scheiterte nach dem
                # bezahlten Einlesen an „kein verwertbares Ergebnis" – dabei
                # hatte das Modell sauber gearbeitet und war nur an eine Grenze
                # des Programms gestoßen. Der Lauf davor nutzte 6.753 von 8.000
                # Ausgabetoken, der vom Vortag 7.777. Es war eine Frage der Zeit.
                #
                # Kein zweiter Versuch: Er liefe in dieselbe Grenze und kostete
                # noch einmal Geld.
                if durchgang.antwort.stop_grund == "max_tokens":
                    raise AnalyseFehler(
                        f"Die Antwort war nach {self._e.max_ausgabe_tokens} Token zu Ende und "
                        "damit mitten im Satz abgeschnitten; auswerten ließ sie sich deshalb "
                        "nicht. Das liegt weder am Modell noch an der Akte, sondern an einer "
                        "Grenze im Programm. Sie lässt sich heraufsetzen: "
                        "JUSPERFECT_MAX_AUSGABE_TOKENS, etwa 16000.") from e
                if versuch == 2:
                    raise AnalyseFehler("Das Modell hat kein verwertbares Ergebnis geliefert. Bitte erneut versuchen.") from e
                durchgang = self._ausgang.fragen(
                    kontext, prompts.SYSTEM, material,
                    aufgabe + "\n\nWICHTIG: Antworten Sie ausschließlich mit dem gültigen JSON-Objekt.", modell_id=modell)
        raise AssertionError("unerreichbar")

    # ── Funktionen ─────────────────────────────────────────────────────────

    def frage(self, identitaet: Identitaet, sitzung: Sitzung, passagen: list[Passage], frage: str,
              beteiligte: list[Beteiligter], fristen: list[Frist],
              referenzen: list[Passage] = ()) -> Antwort:
        auswahl, hinweise, material = self._frage_vorbereiten(sitzung, passagen, frage, beteiligte, fristen, referenzen)
        kontext = Ausgangskontext(identitaet, sitzung.id, sitzung.akte_id, "frage", passagen=len(auswahl))
        durchgang = self._ausgang.fragen(kontext, prompts.SYSTEM, material, prompts.aufgabe_frage(frage))
        return self._frage_belegen(durchgang, auswahl, hinweise, fristen)

    def frage_stream(self, identitaet: Identitaet, sitzung: Sitzung, passagen: list[Passage], frage: str,
                     beteiligte: list[Beteiligter], fristen: list[Frist],
                     referenzen: list[Passage] = ()):
        """Wie ``frage``, aber stückweise: erst ("text", Stück), zuletzt
        ("fertig", Antwort). Der Text strömt roh; die Belegpflicht greift am
        Ende über den vollständigen Text, damit keine unbelegte Aussage
        stehen bleibt.
        """
        auswahl, hinweise, material = self._frage_vorbereiten(sitzung, passagen, frage, beteiligte, fristen, referenzen)
        kontext = Ausgangskontext(identitaet, sitzung.id, sitzung.akte_id, "frage", passagen=len(auswahl))
        durchgang: Durchgang | None = None
        for stueck in self._ausgang.fragen_stream(kontext, prompts.SYSTEM, material, prompts.aufgabe_frage(frage)):
            if isinstance(stueck, str):
                yield ("text", stueck)
            else:
                durchgang = stueck
        if durchgang is None:
            raise AnalyseFehler("Der Anbieter lieferte keine Antwort.")
        yield ("fertig", self._frage_belegen(durchgang, auswahl, hinweise, fristen))

    def _frage_vorbereiten(self, sitzung: Sitzung, passagen: list[Passage], frage: str,
                           beteiligte: list[Beteiligter], fristen: list[Frist],
                           referenzen: list[Passage] = ()) -> tuple[list[Passage], list[str], str]:
        if not frage.strip():
            raise AnalyseFehler("Die Frage ist leer.")
        if not passagen:
            raise AnalyseFehler("Es sind keine Dokumente geladen.")
        gewaehlt = passagen_waehlen(frage, passagen, self._e.max_frage_passagen)
        auswahl = gewaehlt.passagen
        hinweise: list[str] = []
        if not gewaehlt.treffer:
            # Ohne diesen Hinweis sähe eine Antwort über den Aktenanfang aus wie
            # eine Antwort auf die gestellte Frage.
            hinweise.append(
                f"Kein Wort der Frage kommt in den {gewaehlt.durchsucht} Passagen der "
                "Arbeitsakte vor. Es ging ersatzweise der Anfang der Akte mit – die "
                "Antwort beruht also nicht auf einer gezielten Auswahl. Bitte anders "
                "formulieren oder andere Dokumente in die Arbeitsakte legen."
            )
        verlauf = sitzung.dialog[-self._e.dialog_max_runden:]
        # Rückfragen wie „Wann war das?“ brauchen neben dem geprüften Verlauf
        # dessen Originalbelege. Sie werden erneut mitgeschickt und bleiben so
        # auch in der neuen Antwort maschinell prüfbar.
        bekannte = {p.kennung for p in auswahl}
        historische_kennungen = {kennung for runde in verlauf for kennung in runde.quellen}
        for passage in passagen:
            if passage.kennung in historische_kennungen and passage.kennung not in bekannte:
                auswahl.append(passage)
                bekannte.add(passage.kennung)
        if self._wissen is not None:
            auswahl = auswahl + self._wissen.suchen(frage)
        # Referenzen (veröffentlichtes Material) kommen wie das Kanzleiwissen
        # nach der Auswahl dazu – vom Bearbeiter gewählt, nicht gerankt.
        if referenzen:
            auswahl = auswahl + list(referenzen)
            hinweise.append(f"{len(referenzen)} Referenzpassage(n) im Kontext (veröffentlichtes Material).")
        vorher = len(auswahl)
        auswahl, gekuerzt = budget_anwenden(auswahl, self._e.max_passagen_zeichen)
        if gekuerzt:
            hinweise.append(
                f"Nur {len(auswahl)} von {vorher} ausgewählten Passagen passten in den Aufruf; "
                "die Antwort beruht auf diesem Teil."
            )
        material = prompts.material_bauen(sitzung.akte, beteiligte, fristen, auswahl)
        if verlauf:
            material += "\n\n" + prompts.dialog_bauen(verlauf)
        return auswahl, hinweise, material

    @staticmethod
    def _frage_belegen(durchgang: Durchgang, auswahl: list[Passage], hinweise: list[str],
                       fristen: list[Frist] = ()) -> Antwort:
        # Fail closed: unbelegte Aussagen fallen aus der Antwort, statt markiert
        # stehen zu bleiben. Geprüft wird über den vollständigen Text.
        antwort = durchgang.antwort
        index = index_bauen(auswahl)
        belegt = aussage_fail_closed(antwort.text, index)
        # Und dann die Fristen: Ein Datum, das in keiner Passage steht, kann
        # nicht aus der Akte stammen - in einem Fristsatz ist es gerechnet.
        text, gerechnet = frist_entschaerfen(belegt.text, index, fristen)
        weitere = [frist_hinweis(gerechnet)] if gerechnet else []
        return Antwort(text=text, quellen=belegt.quellen,
                       hinweise=hinweise + belegt.hinweise + weitere,
                       modell=antwort.modell, kosten=durchgang.kosten)

    def analysieren(self, identitaet: Identitaet, sitzung: Sitzung, passagen: list[Passage],
                    beteiligte: list[Beteiligter], fristen: list[Frist]) -> Aktenanalyse:
        if not passagen:
            raise AnalyseFehler("Es sind keine Dokumente geladen.")
        auswahl, gekuerzt = budget_anwenden(passagen, self._e.max_passagen_zeichen)
        if gekuerzt:
            raise AktenZuGross(_zu_gross("Aktenanalyse", auswahl, passagen, self._e.max_passagen_zeichen,
                                         self._e.gedaechtnis != "aus"))
        material = prompts.material_bauen(sitzung.akte, beteiligte, fristen, auswahl)
        kontext = Ausgangskontext(identitaet, sitzung.id, sitzung.akte_id, "analyse", passagen=len(auswahl))
        analyse, durchgang, roh = self._strukturiert(kontext, material, prompts.aufgabe_analyse(), Aktenanalyse)
        return self._analyse_pruefen(analyse, roh, index_bauen(auswahl), durchgang, fristen)

    def _analyse_pruefen(self, analyse: Aktenanalyse, roh: dict, index: dict,
                         durchgang: Durchgang, fristen: list[Frist]) -> Aktenanalyse:
        """Belegpflicht, Aufräumen und Fristensperre über ein Analyseergebnis.

        Eigens herausgezogen, weil es zwei Wege zur Analyse gibt: über die
        Dokumente und - bei einer Akte, die nicht in einen Aufruf passt - über
        den Lebenssachverhalt aus dem Gedächtnis. Was danach geprüft wird, muss
        auf beiden Wegen dasselbe sein; zwei Fassungen dieser Prüfung wären mit
        der Zeit zwei verschiedene Prüfungen.
        """
        hinweise = list(analyse.hinweise)
        # Fail closed: Ein Eintrag ohne gültige Quelle wird nicht aufgenommen.
        for liste_name in ("chronologie", "beteiligte", "forderungen", "beweismittel", "offene_punkte", "widersprueche"):
            behalten, verworfen = eintraege_fail_closed(
                getattr(analyse, liste_name), roh.get(liste_name, []), index, _kennungen
            )
            setattr(analyse, liste_name, behalten)
            if verworfen:
                hinweise.append(f"{verworfen} Eintrag/Einträge ohne belastbaren Beleg in „{liste_name}“ entfernt.")
        # Erst nach der Belegpruefung: Das Aufraeumen vergleicht den Eintrag mit
        # der Passage, aus der er stammt - dafuer muessen die Quellen stehen.
        analyse.chronologie, aufraeumhinweise = chronologie_aufraeumen(analyse.chronologie, index)
        hinweise += aufraeumhinweise
        # Fristen werden erkannt, nie berechnet. Der Auftragstext sagt es seit
        # jeher; im ersten Durchgang an einer echten Akte hat das Modell es
        # trotzdem getan - und richtig gerechnet, was es schlimmer macht.
        gerechnet = frist_felder_entschaerfen(analyse.offene_punkte, "beschreibung", index, fristen)
        gerechnet += frist_felder_entschaerfen(analyse.widersprueche, "beschreibung", index, fristen)
        gerechnet += frist_felder_entschaerfen(analyse.chronologie, "ereignis", index, fristen)
        gerechnet += frist_felder_entschaerfen(analyse.forderungen, "gegenstand", index, fristen)
        saubere_hinweise = []
        for h in hinweise:
            neu_h, zahl = frist_entschaerfen(h, index, fristen)
            gerechnet += zahl
            saubere_hinweise.append(neu_h)
        hinweise = saubere_hinweise
        if gerechnet:
            hinweise.append(frist_hinweis(gerechnet))
        analyse.hinweise = hinweise
        analyse.modell = durchgang.antwort.modell
        analyse.kosten = durchgang.kosten
        return analyse

    def analysieren_ueber_gedaechtnis(self, identitaet: Identitaet, sitzung: Sitzung,
                                      lebenssachverhalt: str, chronologie: list,
                                      alle_passagen: list[Passage],
                                      beteiligte: list[Beteiligter], fristen: list[Frist]) -> Aktenanalyse:
        """Die Analyse über eine Akte, die nicht in einen Aufruf passt.

        Nicht über die Dokumente, sondern über den Lebenssachverhalt, der
        abschnittsweise aus ihnen entstanden ist. Er ist ein Bruchteil so lang
        und deckt die Akte doch ganz ab – erst dadurch lässt sich ein
        Widerspruch finden, der zwischen Dokument 8 und Dokument 44 liegt.

        Der entscheidende Punkt steht drei Zeilen weiter unten: Geprüft wird
        gegen **alle** Passagen der Akte, nicht gegen das, was mitgegangen ist.
        Die Kennungen im Lebenssachverhalt zeigen auf Passagen, die in diesem
        Aufruf gar nicht vorkamen; gegen die mitgeschickten geprüft, fiele jede
        einzelne Aussage als unbelegt heraus. Die Prüfung kostet nichts – sie
        läuft im Programm – und bleibt so streng wie sonst: Was auf keine
        wirkliche Passage zeigt, fällt weiterhin.
        """
        if not lebenssachverhalt.strip():
            raise AnalyseFehler("Das Aktengedächtnis enthält noch keinen Lebenssachverhalt.")
        material = prompts.material_gedaechtnis(sitzung.akte, beteiligte, fristen,
                                                lebenssachverhalt, chronologie)
        kontext = Ausgangskontext(identitaet, sitzung.id, sitzung.akte_id, "analyse",
                                  passagen=len(alle_passagen))
        analyse, durchgang, roh = self._strukturiert(
            kontext, material, prompts.aufgabe_analyse_gedaechtnis(), Aktenanalyse)
        index = index_bauen(alle_passagen)
        hinweise = [
            "Diese Analyse beruht auf dem Lebenssachverhalt aus dem Aktengedächtnis, "
            f"nicht unmittelbar auf den Dokumenten. Er ist abschnittsweise aus allen "
            f"{len({p.dokument_id for p in alle_passagen})} Dokumenten dieser Akte entstanden; "
            "die Fundstellen zeigen auf die Originalpassagen und sind gegen diese geprüft."
        ] + list(analyse.hinweise)
        analyse.hinweise = hinweise
        return self._analyse_pruefen(analyse, roh, index, durchgang, fristen)

    def chronologie(self, identitaet: Identitaet, sitzung: Sitzung, passagen: list[Passage],
                    beteiligte: list[Beteiligter], fristen: list[Frist],
                    bekannt: list[str] = ()) -> Chronologieergebnis:
        """Nur den Zeitstrahl - und nur ueber die uebergebenen Passagen.

        Getrennt von ``analysieren``, weil der Anlass ein anderer ist: Nach drei
        Wochen kommt ein Schriftsatz, und gefragt ist, was er dem Zeitstrahl
        hinzufuegt. Die volle Analyse verlangte dafuer sechs Listen ueber die
        ganze Akte. Hier geht das kleine Modell ueber die neuen Passagen.

        ``bekannt`` nennt dem Modell, was schon vermerkt ist. Das ist kein
        Ersatz fuer die Doppelungspruefung beim Speichern, sondern spart den
        Weg dorthin: Was gar nicht erst kommt, muss nicht ausgesondert werden.
        """
        if not passagen:
            raise AnalyseFehler("Es sind keine Dokumente geladen.")
        auswahl, gekuerzt = budget_anwenden(passagen, self._e.max_passagen_zeichen)
        if gekuerzt:
            raise AktenZuGross(_zu_gross("Chronologie", auswahl, passagen, self._e.max_passagen_zeichen,
                                         self._e.gedaechtnis != "aus"))
        material = prompts.material_bauen(sitzung.akte, beteiligte, fristen, auswahl)
        kontext = Ausgangskontext(identitaet, sitzung.id, sitzung.akte_id, "gedaechtnis",
                                  passagen=len(auswahl))
        ergebnis, durchgang, roh = self._strukturiert(
            kontext, material, prompts.aufgabe_chronologie(list(bekannt)), Chronologieergebnis,
            modell=self._e.modell_fuer("gedaechtnis"),
        )
        index = index_bauen(auswahl)
        hinweise = list(ergebnis.hinweise)
        # Fail closed: Ein Ereignis ohne gueltige Quelle ist kein Ereignis.
        ergebnis.chronologie, verworfen = eintraege_fail_closed(
            ergebnis.chronologie, roh.get("chronologie", []), index, _kennungen
        )
        if verworfen:
            hinweise.append(f"{verworfen} Ereignis(se) ohne belastbaren Beleg entfernt.")
        ergebnis.chronologie, aufraeumhinweise = chronologie_aufraeumen(ergebnis.chronologie, index)
        hinweise += aufraeumhinweise
        gerechnet = frist_felder_entschaerfen(ergebnis.chronologie, "ereignis", index, fristen)
        if gerechnet:
            hinweise.append(frist_hinweis(gerechnet))
        ergebnis.hinweise = hinweise
        ergebnis.modell = durchgang.antwort.modell
        ergebnis.kosten = durchgang.kosten
        return ergebnis

    def triage(self, identitaet: Identitaet, sitzung: Sitzung, passagen: list[Passage],
               beteiligte: list[Beteiligter], fristen: list[Frist]) -> Triage:
        if not passagen:
            raise AnalyseFehler("Das Dokument ist nicht geladen.")
        auswahl, gekuerzt = budget_anwenden(passagen, self._e.max_passagen_zeichen)
        material = prompts.material_bauen(sitzung.akte, beteiligte, fristen, auswahl)
        kontext = Ausgangskontext(identitaet, sitzung.id, sitzung.akte_id, "triage", passagen=len(auswahl))
        # Das Modell wählt der Ausgang anhand der Funktion („triage").
        triage, durchgang, roh = self._strukturiert(kontext, material, prompts.aufgabe_triage(), Triage)
        index = index_bauen(auswahl)
        hinweise = list(triage.hinweise)
        if gekuerzt:
            hinweise.insert(0, "Das Dokument war zu lang für einen Aufruf; die Prüfung beruht auf dem Anfang.")
        triage.quellen = quellen_aus_kennungen(_kennungen(roh), index, hinweise)
        # Fail closed: Ein Fristauslöser ohne Beleg ist kein Fristauslöser.
        triage.fristausloeser, verworfen = eintraege_fail_closed(
            triage.fristausloeser, roh.get("fristausloeser", []), index, _kennungen
        )
        if verworfen:
            hinweise.append(f"{verworfen} Fristauslöser ohne belastbaren Beleg entfernt.")
        # Gerade die Eingangspruefung ist der Ort, an dem eine gerechnete Frist
        # Schaden anrichtet: Sie liest ein frisch eingegangenes Schreiben, und
        # wer sie benutzt, will genau wissen, was zu tun ist.
        gerechnet = frist_felder_entschaerfen(triage.fristausloeser, "text", index, fristen)
        kern, zahl = frist_entschaerfen(triage.kernaussage, index, fristen)
        triage.kernaussage = kern
        gerechnet += zahl
        schritte = []
        for schritt in triage.empfohlene_schritte:
            neu_s, zahl_s = frist_entschaerfen(schritt, index, fristen)
            gerechnet += zahl_s
            schritte.append(neu_s)
        triage.empfohlene_schritte = schritte
        if gerechnet:
            hinweise.append(frist_hinweis(gerechnet))
        triage.hinweise = hinweise
        triage.modell = durchgang.antwort.modell
        triage.kosten = durchgang.kosten
        return triage


def _tausender(zahl: int) -> str:
    """700000 -> 700.000. Ein Punkt, wie im Deutschen ueblich."""
    return f"{zahl:,}".replace(",", ".")


def _zu_gross(was: str, auswahl: list[Passage], alle: list[Passage], grenze: int,
              gedaechtnis_aktiv: bool = False) -> str:
    """Sagt, warum abgebrochen wird und was der Bearbeiter jetzt tun kann.

    Zahlen statt "zu gross": Wer liest, dass 22 von 100 Dokumenten gepasst
    haetten, versteht sofort, dass hier nicht nachgebessert, sondern anders
    vorgegangen werden muss.
    """
    zeichen = sum(len(p.text) for p in alle)
    dokumente = len({p.dokument_id for p in alle})
    gepasst = len({p.dokument_id for p in auswahl})
    letzte = auswahl[-1].dokument_titel if auswahl else "—"
    return (
        f"Diese Akte ist zu groß für eine {was} in einem Zug. "
        f"{dokumente} Dokumente mit {_tausender(zeichen)} Zeichen; in einen Aufruf "
        f"passen {_tausender(grenze)}. "
        f"Es käme eine Auswertung über {gepasst} Dokumente heraus, zuletzt „{letzte}“ – "
        f"die späteren Schriftsätze fehlten darin, und dem Ergebnis sähe man das nicht an. "
        f"Deshalb wird nicht gekürzt, sondern abgebrochen.\n\n"
        f"{_ausweg(was, zeichen, grenze, gedaechtnis_aktiv)}"
    )


def _ausweg(was: str, zeichen: int, grenze: int, gedaechtnis_aktiv: bool) -> str:
    """Was jetzt hilft – und zwar der beste Weg zuerst.

    Bis das abschnittsweise Lesen gebaut war, blieb nur, Dokumente aus der
    Arbeitsakte zu nehmen. Das ist bei einer Akte, die man ganz lesen will, ein
    Rat und keine Lösung. Ist das Aktengedächtnis eingeschaltet, gibt es den
    besseren Weg, und dann soll er hier auch stehen – eine Meldung, die den
    vorhandenen Ausweg verschweigt, kostet mehr Zeit als sie spart.
    """
    if not gedaechtnis_aktiv:
        return (
            "Was jetzt hilft: im Explorer weniger Dokumente in die Arbeitsakte legen und "
            f"abschnittsweise vorgehen – oder eine Frage stellen statt der {was}. "
            "Fragen suchen sich die passenden Stellen aus der ganzen Akte und sind von "
            "dieser Grenze kaum betroffen.\n\n"
            "Der bequemere Weg wäre das Aktengedächtnis: Damit liest jusperfect die Akte "
            "in Portionen ein und arbeitet danach auf dem Gelesenen. Es ist derzeit nicht "
            "eingeschaltet."
        )
    portionen = max(2, -(-zeichen // max(1, grenze)))
    return (
        f"Was jetzt hilft: die Akte abschnittsweise ins Aktengedächtnis lesen – der Knopf "
        f"„Akte einlesen“ im Fenster Aktengedächtnis. Sie wird dann in etwa {portionen} "
        f"Portionen gelesen, jede knüpft an die vorige an, und am Ende steht der "
        f"Lebenssachverhalt der ganzen Akte. Das dauert und kostet entsprechend viele "
        f"Modellaufrufe – dafür muss es nur einmal geschehen.\n\n"
        f"Sofort und ohne Kosten geht stattdessen eine Frage: Fragen suchen sich die "
        f"passenden Stellen aus der ganzen Akte und sind von dieser Grenze kaum betroffen."
    )


def _kennungen(roh: object) -> list[str]:
    if isinstance(roh, dict):
        q = roh.get("quellen", [])
        return [str(k) for k in q] if isinstance(q, list) else [str(q)]
    return []


def _quellen_roh_entfernen(roh: dict, modell_typ: type[BaseModel]) -> dict:
    """Das Modell liefert Quellen als Kennungen; die Modelle erwarten Quelle-Objekte.

    Die Kennungen werden hier entfernt und nach der Validierung getrennt
    aufgelöst und geprüft (siehe quellen_aus_kennungen).
    """
    def bereinigen(wert: object) -> object:
        if isinstance(wert, dict):
            return {k: ([] if k == "quellen" else bereinigen(v)) for k, v in wert.items()}
        if isinstance(wert, list):
            return [bereinigen(v) for v in wert]
        return wert
    return bereinigen(roh)  # type: ignore[return-value]
