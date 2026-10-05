"""Demo-Anbieter ohne KI.

Für Entwicklung, Tests und die erste Vorführung ohne AWS-Konto. Er liest die
Passagen aus dem Prompt und baut daraus mit einfachen Mustern (Daten,
Beträge, Rollenwörter) ein Ergebnis im selben Format, das das echte Modell
liefern würde – inklusive Quellenangaben. Die Qualität ist bewusst
bescheiden; der Zweck ist, den vollständigen Ablauf ohne Kosten zu prüfen.
"""

from __future__ import annotations

import json
import re

from jusperfect.providers.base import Nutzung, ProviderAntwort

_PASSAGE_RE = re.compile(r"^### Passage (?P<kennung>[A-Za-z0-9\-]+) \((?P<kopf>[^\n]*)\)\n(?P<text>.*?)(?=^### Passage |^### Ende der Passagen|\Z)", re.S | re.M)
_DATUM_RE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
_BETRAG_RE = re.compile(r"\b\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s?(?:EUR|€)")
# Ein Aktenzeichen der Kanzlei: 42/26 VU, 31/26 SC - Zahl, Jahr, Kuerzel.
_AKTENZEICHEN_RE = re.compile(r"\b\d{1,4}/\d{2,4}\s?[A-ZÄÖÜ]{1,3}\b")
_ROLLEN = ["Mandant", "Mandantin", "Kläger", "Klägerin", "Beklagte", "Beklagter", "Gegner", "Gegnerin",
           "Versicherung", "Rechtsschutzversicherung", "Zeuge", "Zeugin", "Sachverständige", "Sachverständiger",
           "Unfallgegner", "Halter", "Fahrer"]
_BEWEIS = ["Gutachten", "Kostenvoranschlag", "Rechnung", "Lichtbild", "Foto", "Unfallanzeige", "Polizeibericht",
           "Zeuge", "Zeugin", "Attest", "Vertrag", "Protokoll"]
_OFFEN = ["offen", "fehlt", "noch nicht", "bitte", "ausstehend", "unklar", "Frist", "erbeten", "nachreichen"]


_BELEGZEILE = re.compile(r"(?P<text>[^\n]*?)\s*\[Q:\s*(?P<kennungen>[^\]]+)\]")


def _aus_belegen(nutzer_text: str) -> list[tuple[str, str]]:
    """Aus belegten Saetzen Passagen machen - je Fundstelle eine.

    Der Lebenssachverhalt ist kein Dokument, sondern belegter Fliesstext. Fuer
    den Demo-Anbieter ist beides dasselbe, sobald man weiss, welche Kennung zu
    welchem Satz gehoert: der Satz davor.
    """
    ergebnis: list[tuple[str, str]] = []
    for m in _BELEGZEILE.finditer(nutzer_text):
        satz = m.group("text").strip(" -–•\t")
        if not satz:
            continue
        for kennung in (k.strip() for k in m.group("kennungen").split(",")):
            if kennung:
                ergebnis.append((kennung, satz))
    return ergebnis


def _saetze(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


class DemoProvider:
    modell_id = "demo-ohne-ki"

    def __init__(self) -> None:
        self.aufrufe: list[tuple[str, str]] = []

    def fragen_stream(self, system: str, material: str, aufgabe: str, *, max_tokens: int = 8000,
                      modell_id: str | None = None):
        # Der Demo-Anbieter rechnet die Antwort in einem Zug und gibt sie dann
        # stückweise heraus - genug, um den Streaming-Weg ohne KI zu prüfen.
        antwort = self.fragen(system, material, aufgabe, max_tokens=max_tokens, modell_id=modell_id)
        stuecke = re.findall(r"\S+\s*", antwort.text) or [antwort.text]
        for stueck in stuecke:
            yield stueck
        yield antwort

    def fragen(self, system: str, material: str, aufgabe: str, *, max_tokens: int = 8000,
               modell_id: str | None = None) -> ProviderAntwort:
        nutzer_text = material + "\n" + aufgabe
        self.aufrufe.append((system, material, aufgabe))
        passagen = [(m.group("kennung"), m.group("text").strip()) for m in _PASSAGE_RE.finditer(nutzer_text)]
        if not passagen:
            # Kein Material aus Passagenbloecken - dann ist es der
            # Lebenssachverhalt aus dem Aktengedaechtnis. Er traegt seine
            # Fundstellen am Satzende statt in Ueberschriften. Ohne diesen
            # Rueckfall lieferte der Demo-Anbieter bei einer grossen Akte
            # leere Listen, und die Analyse ueber das Gedaechtnis saehe kaputt
            # aus, obwohl der Weg richtig ist.
            passagen = _aus_belegen(nutzer_text)
        if "AUFGABE: ANALYSE" in nutzer_text:
            text = json.dumps(self._analyse(passagen), ensure_ascii=False, indent=1)
        elif "AUFGABE: CHRONOLOGIE" in nutzer_text:
            # Derselbe Zeitstrahl wie in der Analyse, ohne die uebrigen Listen.
            # Ohne diesen Zweig bricht "aktualisieren" im Probelauf mit
            # "kein verwertbares Ergebnis" ab - und der Probelauf ist genau der
            # Weg, auf dem die Kanzlei das Programm kennenlernt.
            voll = self._analyse(passagen)
            text = json.dumps({"chronologie": voll["chronologie"], "hinweise": voll["hinweise"]},
                              ensure_ascii=False, indent=1)
        elif "AUFGABE: AKTENGEDÄCHTNIS" in nutzer_text:
            # Ohne diesen Zweig fiel die Gedaechtnisaufgabe auf die Frage-Antwort
            # zurueck. Dort wird nach "FRAGE:" gesucht - die es hier nicht gibt -,
            # und heraus kam "keine belastbaren Angaben" ohne Beleg. Die
            # Belegpflicht warf das richtigerweise weg, und im Gedaechtnis landete
            # nie etwas. Das dauerhafte Aktengedaechtnis war damit ohne AWS
            # ueberhaupt nicht zu erleben - also genau in dem Betrieb nicht, in
            # dem die Kanzlei das Programm kennenlernt.
            text = self._gedaechtnis(nutzer_text, passagen)
        elif "AUFGABE: TRIAGE" in nutzer_text:
            text = json.dumps(self._triage(passagen), ensure_ascii=False, indent=1)
        elif "AUFGABE: VORSCHLAG FÜR EINEN EIGENEN AUFTRAG" in nutzer_text:
            # Ohne diesen Zweig fiele der Vorschlag auf die Frage-Antwort
            # zurueck, die kein JSON liefert - der Weg endete im Demo-Betrieb
            # mit "kein brauchbarer Vorschlag". Genau dort lernt die Kanzlei
            # das Programm aber kennen.
            text = json.dumps(self._auftragsvorschlag(nutzer_text), ensure_ascii=False, indent=1)
        elif "AUFGABE: ENTWURF" in nutzer_text:
            text = json.dumps(self._entwurf(nutzer_text, passagen), ensure_ascii=False, indent=1)
        else:
            text = self._antwort(nutzer_text, passagen, aufgabe)
        nutzung = Nutzung(eingabe_tokens=len(nutzer_text) // 4, ausgabe_tokens=len(text) // 4)
        return ProviderAntwort(text=text, nutzung=nutzung, modell=self.modell_id)

    # ── Frage ──────────────────────────────────────────────────────────────

    def _antwort(self, nutzer_text: str, passagen: list[tuple[str, str]], aufgabe: str = "") -> str:
        frage = ""
        # Die gestellte Frage steht im Auftrag, nicht irgendwo im Material.
        # Vorher wurde das erste "FRAGE:" im ganzen Text gesucht - und sobald
        # ein frueherer Dialog mitging, stand dort die Frage von vorhin. Der
        # Demo-Anbieter beantwortete dann die vorige Frage, und im Probelauf
        # sah es aus, als erfinde er Antworten auf alles.
        m = re.search(r"FRAGE:\s*(.+)", aufgabe or nutzer_text)
        if m:
            frage = m.group(1).strip()
        woerter = {w.lower() for w in re.findall(r"\w{4,}", frage)}
        treffer: list[tuple[int, str, str]] = []
        for kennung, text in passagen:
            for satz in _saetze(text):
                punkte = sum(1 for w in woerter if w in satz.lower())
                if punkte:
                    treffer.append((punkte, kennung, satz))
        treffer.sort(key=lambda t: -t[0])
        if not treffer:
            return "Zu dieser Frage finden sich in den geladenen Dokumenten keine belastbaren Angaben."
        # Keine Kopfzeile "Demo-Antwort (ohne KI, …)".
        #
        # Sie stand hier und war ein technischer Hinweis mitten in einer
        # Aussage - genau die Vermischung, die Befund F04 der Zweitpruefung
        # beanstandet. Seit dem 05.10.2026 traegt jede Einheit ihren eigenen
        # Beleg; die Kopfzeile traegt keinen und wurde folgerichtig
        # zurueckgehalten. Dass es der Demo-Anbieter ist, steht in der
        # Kopfleiste der Oberflaeche ("Demo (ohne KI)") und gehoert nicht in
        # den Antworttext.
        return "\n".join(f"- {satz} [Q: {kennung}]" for _, kennung, satz in treffer[:4])

    # ── Aktengedaechtnis ───────────────────────────────────────────────────

    def _gedaechtnis(self, nutzer_text: str, passagen: list[tuple[str, str]]) -> str:
        """Eine belegte Fortschreibung aus dem, was der Demo-Anbieter erkennen kann.

        Dieselben groben Muster wie in der Analyse: Saetze mit einem Datum,
        einem Betrag oder einem Rollenwort. Das ist kein Lebenssachverhalt, wie
        ihn ein Modell schreibt, und soll es nicht sein - es ist ein Satz je
        Fund mit seiner Fundstelle, damit der ganze Weg ohne Kosten pruefbar
        ist: fortschreiben, belegen, speichern, beim naechsten Mal nur Neues.
        """
        bisher = ""
        m = re.search(r"BISHERIGER, BEREITS GEPRÜFTER LEBENSSACHVERHALT:\n(.*)", nutzer_text, re.S)
        if m:
            bisher = m.group(1)
        zeilen: list[str] = []
        for kennung, text in passagen:
            for satz in _saetze(text):
                if not (_DATUM_RE.search(satz) or _BETRAG_RE.search(satz)
                        or any(re.search(rf"\b{r}\b", satz) for r in _ROLLEN)):
                    continue
                kurz = satz[:200].strip()
                # Was schon im Lebenssachverhalt steht, wird nicht wiederholt -
                # der Auftrag verlangt es, und ohne diese Pruefung wuechse der
                # Text bei jedem Lauf um dieselben Saetze.
                if kurz[:60] and kurz[:60] in bisher:
                    continue
                zeilen.append(f"{kurz} [Q: {kennung}]")
                break            # ein Satz je Passage genuegt fuer den Zweck
        if not zeilen:
            # Ehrlich bleiben: Ohne Fund keine Behauptung. Die Belegpflicht
            # macht daraus einen sichtbaren Verzicht.
            return "In diesen Passagen findet der Demo-Anbieter keine Angabe mit Datum, Betrag oder Rolle."
        # Keine Ueberschrift: Der Lebenssachverhalt waechst ueber Wochen, und
        # jede Fortschreibung wird angehaengt. Eine Zeile wie "Demo-Fortschreibung"
        # stuende dann alle paar Absaetze mitten im Text - und weil sie vor dem
        # ersten Beleg steht, haenge sie sich an dessen Fundstelle, obwohl sie
        # nichts aus der Akte behauptet.
        return "\n".join(zeilen)

    # ── Analyse ────────────────────────────────────────────────────────────

    def _analyse(self, passagen: list[tuple[str, str]]) -> dict:
        chronologie, forderungen, beteiligte, beweismittel, offene = [], [], [], [], []
        gesehen_bet: set[str] = set()
        gesehen_bew: set[str] = set()
        for kennung, text in passagen:
            for satz in _saetze(text):
                for d in _DATUM_RE.finditer(satz):
                    tag, monat, jahr = d.groups()
                    # "Laut Dokument:" davor, und nicht der ganze Satz: Ein
                    # Chronologieeintrag beschreibt ein Ereignis, er zitiert
                    # es nicht. Die Aufraeumung streicht abgeschriebenen
                    # Dokumenttext - und der Demo-Anbieter soll zeigen, wie ein
                    # brauchbares Ergebnis aussieht, nicht daran scheitern.
                    chronologie.append({"datum": f"{jahr}-{int(monat):02d}-{int(tag):02d}",
                                        "ereignis": f"Laut Dokument: {satz[:160].strip()}",
                                        "quellen": [kennung]})
                    break
                for b in _BETRAG_RE.finditer(satz):
                    forderungen.append({"gegenstand": satz[:160], "betrag": b.group(0), "quellen": [kennung]})
                    break
                for rolle in _ROLLEN:
                    m = re.search(rf"\b{rolle}\b[:\s]+([A-ZÄÖÜ][\wäöüß\-]+(?:\s+[A-ZÄÖÜ][\wäöüß\-]+)?)", satz)
                    if m and (rolle, m.group(1)) not in gesehen_bet:
                        gesehen_bet.add((rolle, m.group(1)))
                        beteiligte.append({"bezeichnung": m.group(1), "rolle": rolle, "quellen": [kennung]})
                for bw in _BEWEIS:
                    if bw.lower() in satz.lower() and (bw, kennung) not in gesehen_bew:
                        gesehen_bew.add((bw, kennung))
                        beweismittel.append({"bezeichnung": satz[:120], "art": bw, "beweisthema": "", "quellen": [kennung]})
                if any(o.lower() in satz.lower() for o in _OFFEN):
                    offene.append({"beschreibung": satz[:200], "prioritaet": "mittel", "quellen": [kennung]})
        chronologie.sort(key=lambda e: e["datum"])
        return {
            "chronologie": chronologie[:40],
            "beteiligte": beteiligte[:20],
            "forderungen": forderungen[:20],
            "beweismittel": beweismittel[:20],
            "offene_punkte": offene[:20],
            "widersprueche": [],
            "hinweise": ["Demo-Analyse ohne KI: nur Muster (Daten, Beträge, Rollenwörter). Widersprüche werden im Demo-Modus nicht erkannt."],
        }

    # ── Triage ─────────────────────────────────────────────────────────────

    def _triage(self, passagen: list[tuple[str, str]]) -> dict:
        fristen, schritte = [], []
        erste_kennung = passagen[0][0] if passagen else ""
        erster_text = passagen[0][1] if passagen else ""
        absender = ""
        for kennung, text in passagen:
            for satz in _saetze(text):
                if re.search(r"\b(Frist|bis zum|bis spätestens|Zustellung|zugestellt|Stellungnahme bis)\b", satz, re.I):
                    fristen.append({"text": satz[:200], "quellen": [kennung]})
                if re.search(r"\b(nachreichen|bitte reichen|bitten um|erbeten|vorlegen)\b", satz, re.I):
                    schritte.append(satz[:160])
        m = re.search(r"^([A-ZÄÖÜ][^\n]{3,80})$", erster_text, re.M)
        if m:
            absender = m.group(1).strip()
        return {
            "dokumentart": "Schreiben (Demo-Einstufung)",
            "absender": absender,
            "kernaussage": (_saetze(erster_text)[0][:200] if erster_text else "") + (f" [Q: {erste_kennung}]" if erste_kennung else ""),
            "fristausloeser": fristen[:5],
            "empfohlene_schritte": schritte[:5] or ["Dokument durchsehen und Wiedervorlage setzen."],
            "quellen": [erste_kennung] if erste_kennung else [],
            "hinweise": ["Demo-Triage ohne KI: nur Mustererkennung für Fristwörter."],
        }

    # ── Entwurf ────────────────────────────────────────────────────────────

    def _entwurf(self, nutzer_text: str, passagen: list[tuple[str, str]]) -> dict:
        art = re.search(r"ART:\s*(.+)", nutzer_text)
        anweisung = re.search(r"ANWEISUNG:\s*(.+)", nutzer_text)
        erste = passagen[0][0] if passagen else ""
        zeilen = [
            "Sehr geehrte Damen und Herren,",
            "",
            f"in der oben bezeichneten Angelegenheit nehmen wir Bezug auf den Vorgang ({anweisung.group(1).strip() if anweisung else 'ohne Anweisung'}).",
            "",
            "[Demo-Entwurf ohne KI – die Sachverhaltsdarstellung ist aus den Dokumenten zu ergänzen.]"
            + (f" [Q: {erste}]" if erste else ""),
            "",
            "Mit freundlichen Grüßen",
            "",
            "Rechtsanwalt / Rechtsanwältin",
        ]
        return {"betreff": (art.group(1).strip() if art else "Entwurf"), "text": "\n".join(zeilen)}

    # ── Vorschlag für einen eigenen Auftrag ────────────────────────────────

    def _auftragsvorschlag(self, nutzer_text: str) -> dict:
        """Verallgemeinern kann der Demo-Anbieter nicht - er kann nur streichen.

        Das echte Modell formuliert aus der Anweisung dieses einen Falles eine
        Fassung, die bei der naechsten gleichartigen Sache wieder passt. Ohne KI
        geht das nicht, und es zu behaupten waere schlimmer als es zu lassen:
        Der Text hier landet in einer Datei, die spaeter bei *jeder* Akte
        mitgeht. Deshalb ersetzt der Demo-Anbieter nur, was er sicher als
        Einzelfall erkennt - Daten, Betraege, Aktenzeichen -, und sagt im
        Hinweis deutlich, dass der Rest von Hand zu schreiben ist.
        """
        art = re.search(r"ART DES SCHREIBENS:\s*(.+)", nutzer_text)
        block = re.search(r"ANWEISUNG DIESES EINEN FALLES:\n(.*?)\n\n", nutzer_text, re.S)
        anweisung = (block.group(1).strip() if block else "")
        allgemein = _DATUM_RE.sub("(Datum)", anweisung)
        allgemein = _BETRAG_RE.sub("(Betrag)", allgemein)
        allgemein = _AKTENZEICHEN_RE.sub("(Aktenzeichen)", allgemein)
        bezeichnung = art.group(1).strip() if art else "Eigener Auftrag"
        return {
            "titel": bezeichnung,
            "anweisung": allgemein or f"Entwirf ein {bezeichnung}.",
            "hinweis": "Demo-Betrieb ohne KI: Daten, Beträge und Aktenzeichen wurden "
                       "ersetzt, mehr nicht. Namen und der übrige Bezug zu dieser Akte "
                       "stehen noch darin und sind vor dem Anlegen von Hand zu streichen.",
        }
