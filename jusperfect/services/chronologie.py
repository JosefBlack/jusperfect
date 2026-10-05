"""Die Chronologie aufräumen, bevor sie jemand liest.

Der erste Durchgang an einer echten Akte hat gezeigt, dass die Anweisung an
das Modell allein nicht genügt: Von achtundvierzig Zeilen waren rund dreißig
kein Ereignis, sondern abgeschriebener Rohtext –

    „Gelsenkirchen, den 20.08.2018"        (eine Briefkopfzeile)
    „Stand: 15.03.2026"
    „- 13.07.2026 bis 31.07.2026 (15 Tage)"
    „Wir weisen darauf hin, dass sich die Mitarbeiterin am 08.04.2026 an den"

– und fast jedes echte Ereignis stand zweimal da, einmal als Fetzen und
einmal als Satz. Alle erwarteten Ereignisse waren enthalten; man musste sie
nur suchen. Bei einer Akte mit vierhundert Dokumenten sucht sie niemand mehr.

Deshalb steht die Prüfung hier, im Programm, und nicht nur im Auftragstext:
Eine Anweisung befolgt das Modell meistens, ein Filter immer. Verworfenes
wird gezählt und als Hinweis genannt – wer eine Chronologie prüft, muss
wissen, dass etwas herausgefallen ist.

Die Regeln sind bewusst grob und in eine Richtung vorsichtig: Ein zu Unrecht
gestrichenes Ereignis wäre der schwerere Fehler als eine überflüssige Zeile.
Gestrichen wird deshalb nur, was sich sicher als Rohtext ausweist.
"""

from __future__ import annotations

import re

from jusperfect.domain.models import Passage

# Wortmengen ab vier Zeichen; kuerzere tragen kaum Bedeutung ("und", "der").
_WORT = re.compile(r"[a-zäöüß0-9]{4,}")
# Ab diesem Anteil gemeinsamer Woerter gelten zwei Saetze als derselbe Vorgang.
_AEHNLICH_AB = 0.7

# Unterhalb dieser Laenge wird NICHT auf Abschrift geprueft. Ein kurzes,
# richtiges Ereignis - "Unfall", "Klageerhebung" - steht als Wort natuerlich
# auch im Dokument; es deswegen zu streichen waere falsch. Die Laenge ist
# also eine Schutzschwelle gegen Zufallstreffer, kein Mass fuer Qualitaet:
# Ein Eintrag darf so kurz sein, wie das Ereignis es zulaesst.
_ABSCHRIFT_AB = 16

# Aufzaehlungszeichen am Anfang: der Eintrag ist aus einer Liste kopiert.
_LISTENANFANG = re.compile(r"^\s*[-–—•*]\s")
# Ein richtiges Datum. Alles andere ("Anfang April 2026", "im Fruehjahr") ist
# eine Naeherung - brauchbar, aber der genauen Angabe nachgeordnet.
_ISO_DATUM = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Nur Datum, Uhrzeit, Zahlen und Bindewoerter - keine Aussage.
_NUR_DATUM = re.compile(r"^[\W\d]*$")

#: Schriftstuecke, deren EIGENES Datum ein Ereignis der Akte ist.
#:
#: Die Liste steht hier, weil der Filter sie braucht, und ``prompts.py`` baut
#: die Regel im Auftrag daraus. Beide muessen von denselben Dokumentarten
#: sprechen - sonst verlangt die eine, was der andere streicht. Genau das war
#: am 28.09.2026 der Fall: Der Auftrag forderte "Leistungsverzeichnis vom
#: 14.02.2025", und der Filter strich es als abgeschriebenen Dokumenttext.
SCHRIFTSTUECKARTEN = (
    "Klageschrift", "Schriftsatz", "Duplik", "Replik", "Gutachten",
    "Ergänzungsgutachten", "Zeugenbenennung", "Kündigung", "Mahnung",
    "Fristsetzung", "Mängelanzeige", "Beschluss", "Ladung", "Vertrag",
    "Leistungsverzeichnis", "Rechnung", "Schlussrechnung", "Abnahmeprotokoll",
    # Das Empfangsbekenntnis stand bis zum 01.10.2026 bei den laufenden
    # Aufzeichnungen, sein eigenes Datum sollte also nichts tragen. Das ist
    # fuer eine Kanzlei falsch herum: Sein Datum IST das Ereignis, denn an ihm
    # beginnen Fristen. Die grosse Testakte sagt dasselbe - "21.06.2025
    # Empfangsbekenntnis des Geschaeftsfuehrers" ist einer der dreizehn
    # geforderten Tage und traegt den Zugang der Maengelruege.
    #
    # Aufgefallen beim Nachrechnen des Laufs vom 01.10.2026: Der neue Filter
    # haette genau diesen Tag gestrichen - 12 von 13 statt 13 von 13. Die
    # Regel und die Aufloesung widersprachen einander, und das Modell hatte
    # recht daran getan, die Regel zu missachten.
    "Empfangsbekenntnis",
)

#: Laufende Aufzeichnungen - ihr EIGENES Datum ist kein Ereignis.
#:
#: Das Gegenstueck zu ``SCHRIFTSTUECKARTEN``, und aus demselben Grund hier:
#: ``prompts.py`` baut die Regel im Auftrag daraus, der Filter setzt sie durch.
#: Je Art die Ein- und die Mehrzahl, weil der Auftrag in Mehrzahl spricht und
#: deutsche Mehrzahlen sich nicht errechnen lassen ("Aufmassblatt" steckt nicht
#: in "Aufmassblaetter"). Zwei handgeschriebene Listen waeren wieder zwei, die
#: auseinanderlaufen.
#:
#: Am 01.10.2026 stand im Zeitstrahl "Bautagebuch April abgeschlossen und der
#: Bauherrin uebergeben" - am 30.04.2025, dem Datum des Bautagebuchs selbst.
#: Der Auftrag sagte das schon in Worten; durchgesetzt hat es niemand.
LAUFENDE_AUFZEICHNUNGSARTEN = (
    ("Bautagebuch", "Bautagebücher"),
    ("Aufmaßblatt", "Aufmaßblätter"),
    ("Stundenzettel", "Stundenzettel"),
    ("Lichtbildmappe", "Lichtbildmappen"),
    ("Besuchsliste", "Besuchslisten"),
)

#: So lang darf eine Selbstbenennung hoechstens sein.
#:
#: "Leistungsverzeichnis vom 14.02.2025, Grundlage des Vertrages" ist eine
#: Benennung. Wer die halbe erste Seite anhaengt, schreibt wieder ab - und die
#: Ausnahme soll kein Loch in die Abschriftpruefung reissen.
_BENENNUNG_BIS = 120

_DATUM_IRGENDWO = re.compile(r"\d{1,2}\.\d{1,2}\.\d{4}|\d{4}-\d{2}-\d{2}")


def benennt_ein_schriftstueck(ereignis: str) -> bool:
    """Benennt der Eintrag ein Schriftstueck samt seinem eigenen Datum?

    Dann ist er ein Ereignis, auch wenn er wortwoertlich in der Passage steht:
    Die Kopfzeile eines Leistungsverzeichnisses *ist* "Leistungsverzeichnis vom
    14.02.2025". Ein Eintrag, der das Schriftstueck benennt, kann dem
    Dokumenttext gar nicht ausweichen, ohne ungenau zu werden.

    Daran hingen fuenf Tage der grossen Testakte - 14.02.2025
    Leistungsverzeichnis, 02.09.2025 Schlussrechnung, 18.02.2026 Gutachten,
    11.03.2026 Schriftsatz, 08.04.2026 Zeugenbenennung -, und sie fehlten in
    fuenf Laeufen mit drei Modellen.
    """
    text = ereignis.strip()
    if len(text) > _BENENNUNG_BIS:
        return False
    if not _DATUM_IRGENDWO.search(text):
        return False
    klein = text.lower()
    return any(art.lower() in klein for art in SCHRIFTSTUECKARTEN)


def _normal(text: str) -> str:
    """Fuer den Vergleich mit dem Quelltext: Kleinschreibung, ein Leerzeichen."""
    return re.sub(r"\s+", " ", text.strip().lower())


def stamm(text: str) -> set[str]:
    """Wortmenge auf fuenf Zeichen gekuerzt.

    Deutsch beugt am Wortende: "Betriebsrat"/"Betriebsrats",
    "Kuendigung"/"Kuendigungen". Ungekuerzt gaelte das als zwei verschiedene
    Woerter, und zwei Fassungen desselben Satzes haetten fast nichts gemeinsam.
    Fuenf Zeichen fassen die Beugung, ohne verschiedene Woerter zusammenzuziehen.
    """
    return {wort[:5] for wort in _WORT.findall(text.lower())}


def gleicher_vorgang(a: str, b: str) -> bool:
    """Zwei Formulierungen desselben Ereignisses erkennen.

    Ein Modell schreibt denselben Vorgang beim zweiten Lauf anders auf
    ("Unfall auf der Kreuzung" / "Kreuzung: Unfall ereignet"). Ohne diesen
    Vergleich waechst die Chronologie bei jeder Analyse um Doppelungen, und der
    Zeitstrahl wird mit jedem Durchgang unbrauchbarer statt genauer.

    Der Vergleich ist bewusst zurueckhaltend: Er erkennt Umstellungen,
    Beugungen und zusaetzliche Fuellwoerter - nicht aber eine Umschreibung mit
    anderem Wortstamm ("Kuendigung zugegangen" / "Zugang der Kuendigung"). Im
    Zweifel bleiben beide Eintraege stehen. Ein verlorenes Ereignis waere der
    schwerere Fehler.

    Genauer ginge es nur mit einem Modellaufruf - und ein Aufruf, um
    Doppelungen zu erkennen, waere teurer als der, den wir sparen wollen.
    """
    menge_a = stamm(a)
    menge_b = stamm(b)
    if not menge_a or not menge_b:
        return a.strip() == b.strip()
    gemeinsam = len(menge_a & menge_b)
    return gemeinsam / min(len(menge_a), len(menge_b)) >= _AEHNLICH_AB


def _ist_abschrift(ereignis: str, quellen, index: dict[str, Passage]) -> bool:
    """Steht der Eintrag wortwoertlich so in der Passage, aus der er stammt?

    Das ist der schaerfste und zugleich sicherste Hinweis auf Rohtext. Eine
    Beschreibung ("Beginn des Arbeitsverhaeltnisses der Mandantin bei der
    Nordwerk Metallbau GmbH") entsteht aus mehreren Stellen und steht nirgends
    so im Text. Ein Fetzen ("Die Anhoerung ist uns am 06.05.2026 zugegangen.")
    steht genau so darin.

    Verglichen wird gegen die volle Passage, nicht gegen das Zitat im Beleg -
    das ist auf 240 Zeichen gekuerzt, und ein Fetzen von weiter hinten fiele
    sonst durch.
    """
    # Ein Schriftstueck, das sich selbst benennt, ist keine Abschrift. Siehe
    # benennt_ein_schriftstueck - diese Zeile ist der Grund, warum fuenf Tage
    # der grossen Testakte in fuenf Laeufen fehlten.
    if benennt_ein_schriftstueck(ereignis):
        return False
    nadel = _normal(ereignis).rstrip(" .;,:")
    if len(nadel) < _ABSCHRIFT_AB:
        return False
    for quelle in quellen:
        passage = index.get(getattr(quelle, "kennung", ""))
        if passage is not None and nadel in _normal(passage.text):
            return True
    return False


def _ist_eigenes_datum_einer_aufzeichnung(datum: str, quellen, index: dict[str, Passage]) -> bool:
    """Eine laufende Aufzeichnung an ihrem eigenen Datum ist kein Ereignis.

    Ein Bautagebuch wird gefuehrt, abgeschlossen und uebergeben - das treibt
    den Fall nicht voran. Ein besonderes Vorkommnis DARIN sehr wohl, und
    deshalb faellt hier nur der eine Tag weg, an dem das Dokument selbst
    datiert: der Eintrag muss BEIDES sein, aus einer laufenden Aufzeichnung
    UND an deren eigenem Datum.

    Die Unterscheidung ist nicht fein, sondern tragend. Fund 3 der grossen
    Testakte - der Polier, der am 11.06.2025 nicht auf der Baustelle war -
    stammt aus genau so einem Bautagebuch. Wer die Quelle allein zum Massstab
    nimmt, streicht ihn mit.
    """
    if not _ISO_DATUM.match(str(datum or "")):
        return False
    for quelle in quellen or ():
        passage = index.get(getattr(quelle, "kennung", ""))
        if passage is None or passage.dokument_datum is None:
            continue
        titel = (passage.dokument_titel or "").lower()
        if not any(art.lower() in titel for art, _ in LAUFENDE_AUFZEICHNUNGSARTEN):
            continue
        if passage.dokument_datum.isoformat() == str(datum):
            return True
    return False


def _ist_fetzen(ereignis: str) -> bool:
    """Angefangene Saetze und Listenzeilen.

    Ein Ereignis wird als Satz beschrieben. Was mit einem Kleinbuchstaben
    beginnt, ist mitten aus einem Satz herausgeschnitten ("beobachtet und uns
    am 29.04.2026 gemeldet."); was mit einem Spiegelstrich beginnt, stammt aus
    einer Aufzaehlung im Dokument.
    """
    text = ereignis.strip()
    if not text:
        return True
    if _LISTENANFANG.match(text):
        return True
    if _NUR_DATUM.match(text):
        return True
    erstes = text[0]
    return erstes.isalpha() and erstes.islower()


def _passt_zusammen(a: str, b: str) -> bool:
    """Zwei Datumsangaben, die dasselbe meinen koennen.

    Gleich ist gleich. Darueber hinaus gilt eine Naeherung ("Anfang April
    2026") als vereinbar mit einem genauen Datum: Beschreiben beide denselben
    Vorgang, ist es derselbe - und die genaue Angabe ist die bessere.
    Zwei verschiedene genaue Daten bleiben zwei Eintraege, auch bei gleichem
    Wortlaut; dort koennte sich ein Vorgang wiederholt haben.
    """
    if a == b:
        return True
    return bool(_ISO_DATUM.match(a)) != bool(_ISO_DATUM.match(b))


def aufraeumen(eintraege: list, index: dict[str, Passage]) -> tuple[list, list[str]]:
    """Rohtext streichen, Doppelungen zusammenfassen, Reihenfolge behalten.

    Gibt die bereinigten Eintraege und Hinweise zurueck. Die Hinweise sind
    nicht Zierde: Wer eine Chronologie zur Fristenpruefung heranzieht, muss
    wissen, dass gestrichen wurde.
    """
    behalten: list = []
    abschriften = 0
    fetzen = 0
    doppelt = 0
    aufzeichnungen = 0

    for eintrag in eintraege:
        ereignis = getattr(eintrag, "ereignis", "") or ""
        if _ist_fetzen(ereignis):
            fetzen += 1
            continue
        if _ist_abschrift(ereignis, getattr(eintrag, "quellen", ()), index):
            abschriften += 1
            continue
        if _ist_eigenes_datum_einer_aufzeichnung(
                getattr(eintrag, "datum", ""), getattr(eintrag, "quellen", ()), index):
            aufzeichnungen += 1
            continue

        # Doppelung: derselbe Vorgang am selben Tag - oder derselbe Vorgang
        # einmal mit Datum und einmal mit einer Naeherung ("Anfang April
        # 2026"). Der zweite Fall kam im Durchgang tatsaechlich vor und ist
        # laestiger, als er aussieht: Im Zeitstrahl steht die Naeherung ganz
        # unten, weit weg von dem Tag, den sie meint.
        datum = getattr(eintrag, "datum", "")
        vorhanden = next(
            (e for e in behalten
             if _passt_zusammen(getattr(e, "datum", ""), datum)
             and gleicher_vorgang(getattr(e, "ereignis", ""), ereignis)),
            None,
        )
        if vorhanden is not None:
            doppelt += 1
            bekannt = {q.kennung for q in vorhanden.quellen}
            vorhanden.quellen = list(vorhanden.quellen) + [
                q for q in getattr(eintrag, "quellen", ()) if q.kennung not in bekannt
            ]
            # Das genaue Datum gewinnt gegen die Naeherung.
            if not _ISO_DATUM.match(getattr(vorhanden, "datum", "")) and _ISO_DATUM.match(datum):
                vorhanden.datum = datum
            continue

        behalten.append(eintrag)

    hinweise: list[str] = []
    gestrichen = abschriften + fetzen
    if gestrichen:
        hinweise.append(
            f"{gestrichen} Chronologie-Zeile(n) waren abgeschriebener Dokumenttext "
            f"statt eines Ereignisses und wurden entfernt."
        )
    if aufzeichnungen:
        hinweise.append(
            f"{aufzeichnungen} Chronologie-Zeile(n) nannten eine laufende Aufzeichnung "
            f"an ihrem eigenen Datum und wurden entfernt."
        )
    if doppelt:
        hinweise.append(f"{doppelt} doppelte Chronologie-Zeile(n) zusammengefasst.")
    return behalten, hinweise
