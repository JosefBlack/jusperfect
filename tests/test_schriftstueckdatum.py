"""Das Datum eines Schriftstuecks muss das Einlesen ueberleben.

Vier Pruefbogenlaeufe ueber die grosse Testakte haben **dieselben fuenf Tage**
vermisst - bei drei verschiedenen Modellen:

    14.02.2025 Leistungsverzeichnis · 02.09.2025 Schlussrechnung ·
    18.02.2026 Gutachten · 11.03.2026 Schriftsatz der Gegenseite ·
    08.04.2026 Zeugenbenennung

Am 22.09.2026 wurde die ``CHRONOLOGIE_REGEL`` dafuer umgeschrieben. Der Lauf
vom 28.09.2026 zeigte dieselben fuenf Luecken - die Regel stand an der
falschen Stelle.

Der Zeitstrahl entsteht in der Analyse, und die sieht die Dokumente nicht
mehr: ``material_gedaechtnis`` schickt ihr den Lebenssachverhalt, die
Stammdaten und den bisherigen Zeitstrahl, aber keine Passage. Ein Datum, das
beim Einlesen nicht aufgeschrieben wurde, kann sie nicht nachtragen.

Diese Pruefungen halten die Stelle fest, an der es aufgeschrieben wird. Sie
messen nicht, ob das Modell folgt - das kann nur ein Pruefbogenlauf. Sie
messen, dass der Auftrag es verlangt.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
# Nicht "from werkzeug import ...": So heisst auch ein Paket auf PyPI, das
# andere Bausteine mitbringen (moto zieht es ueber Flask herein). Dann
# verdeckt das Paket den Projektordner, und die Einfuhr bricht - an einer
# Stelle, die mit der Aenderung nichts zu tun hat.
sys.path.insert(0, str(WURZEL / "werkzeug"))

from jusperfect.domain.models import Akte, Passage
from jusperfect.services import chronologie, prompts


class _Eintrag:
    """Ein Chronologieeintrag, wie das Modell ihn liefert."""

    def __init__(self, datum: str, ereignis: str, kennungen: list[str]) -> None:
        self.datum = datum
        self.ereignis = ereignis
        self.quellen = [_Quelle(k) for k in kennungen]


class _Quelle:
    def __init__(self, kennung: str) -> None:
        self.kennung = kennung


def test_das_einlesen_verlangt_das_eigene_datum_des_schriftstuecks() -> None:
    auftrag = prompts.aufgabe_gedaechtnis()
    assert "WELCHES DATUM ES SELBST" in auftrag
    # Mit Beispiel, nicht als Grundsatz: "Nur Wichtiges" stand schon da, als
    # die fuenf Tage fehlten.
    assert "14.02.2025" in auftrag
    assert "11.03.2026" in auftrag


def test_das_einlesen_nennt_die_schriftstuecke_und_die_gegenliste() -> None:
    auftrag = prompts.aufgabe_gedaechtnis()
    assert prompts.SCHRIFTSTUECKE_MIT_EIGENEM_DATUM in auftrag
    assert prompts.LAUFENDE_AUFZEICHNUNGEN in auftrag


def test_das_einlesen_sagt_warum_es_darauf_ankommt() -> None:
    """Eine Anweisung ohne Grund wird eher weggelassen als eine mit."""
    auftrag = prompts.aufgabe_gedaechtnis()
    assert "für die Akte verloren" in auftrag


def test_beide_auftraege_teilen_dieselben_listen() -> None:
    """Zwei Kopien einer Liste laufen auseinander.

    Das Einlesen schreibt das Datum auf, der Zeitstrahl macht daraus einen
    Eintrag. Naehme eine der beiden Stellen eine Dokumentart nicht auf, fiele
    genau diese Art lautlos aus - und "was nicht da ist, fällt nicht auf".
    """
    assert prompts.SCHRIFTSTUECKE_MIT_EIGENEM_DATUM in prompts.CHRONOLOGIE_REGEL
    assert prompts.LAUFENDE_AUFZEICHNUNGEN in prompts.CHRONOLOGIE_REGEL


def test_die_fuenf_vermissten_arten_stehen_in_der_liste() -> None:
    """Jede der fuenf fehlenden Tage haengt an einer dieser Arten."""
    for art in ("Leistungsverzeichnis", "Schlussrechnung", "Gutachten",
                "Schriftsatz", "Zeugenbenennung"):
        assert art in prompts.SCHRIFTSTUECKE_MIT_EIGENEM_DATUM, art


def test_die_gegenliste_haelt_die_laufenden_aufzeichnungen_draussen() -> None:
    """Der Preis der Regel. Der Rauschwert stand in zwei Laeufen bei 0 %."""
    for art in ("Bautagebücher", "Aufmaßblätter", "Stundenzettel"):
        assert art in prompts.LAUFENDE_AUFZEICHNUNGEN, art


def test_das_empfangsbekenntnis_steht_auf_der_anderen_liste() -> None:
    """Es stand bis zum 01.10.2026 bei den laufenden Aufzeichnungen - falsch.

    Das Datum eines Empfangsbekenntnisses IST das Ereignis: An ihm beginnen
    Fristen. In der grossen Testakte traegt "21.06.2025 Empfangsbekenntnis des
    Geschaeftsfuehrers" den Zugang der Maengelruege und damit zwei der fuenf
    Funde. Der Filter vom 01.10.2026 haette den Tag gestrichen - aufgefallen
    beim Nachrechnen eines echten Laufs, nicht in einer Pruefung.
    """
    assert "Empfangsbekenntnis" in prompts.SCHRIFTSTUECKE_MIT_EIGENEM_DATUM
    assert "Empfangsbekenntnis" not in prompts.LAUFENDE_AUFZEICHNUNGEN


def test_die_analyse_ueber_das_gedaechtnis_sieht_keine_passage() -> None:
    """Der Grund, warum es beim Einlesen stehen muss und nicht spaeter reicht.

    Bricht diese Pruefung, weil die Analyse wieder Passagen mitbekommt, dann
    ist die Begruendung oben ueberholt - und diese Datei gehoert gelesen,
    bevor jemand den Auftrag wieder kuerzt.
    """
    akte = Akte(id="A1", aktenzeichen="44/26 BA", bezeichnung="Bau",
                rechtsgebiet="Baurecht")
    material = prompts.material_gedaechtnis(
        akte, [], [], "Die Dämmung war mit 24 cm geschuldet. [Q: D2-S1-P1]", [])
    assert "Lebenssachverhalt" in material
    # Kein Passagentext, nur das Konzentrat.
    assert "D2-S1-P1" in material
    assert "## Dokument" not in material


def test_der_filter_streicht_eine_selbstbenennung_nicht_mehr() -> None:
    """Der Befund des Laufs vom 28.09.2026, 13:04 Uhr.

    Der Auftrag verlangte das Datum des Schriftstuecks, das Modell lieferte es -
    und ``aufraeumen`` strich es als "abgeschriebener Dokumenttext". Die
    Kopfzeile eines Leistungsverzeichnisses *ist* "Leistungsverzeichnis vom
    14.02.2025"; ein Eintrag, der das Schriftstueck benennt, kann dem
    Dokumenttext nicht ausweichen, ohne ungenau zu werden.

    Zwei Regeln, die einander widersprechen, sind schlimmer als eine falsche:
    Die eine verlangte, was die andere entfernte, und keine von beiden meldete
    es.
    """
    passage = Passage(kennung="D2-S1-P1", dokument_id="D-002", dokument_nummer=2,
                      dokument_titel="Leistungsverzeichnis", seite=1, nummer=1,
                      text="Leistungsverzeichnis vom 14.02.2025 zum Bauvorhaben "
                           "Wohnanlage Lindenhof. Position 3.4 Wärmedämmung WDVS, "
                           "Dämmstärke 24 cm, Fläche 402,00 m².")
    behalten, _ = chronologie.aufraeumen(
        [_Eintrag("2025-02-14", "Leistungsverzeichnis vom 14.02.2025", ["D2-S1-P1"])],
        {"D2-S1-P1": passage})
    assert len(behalten) == 1


def test_die_fuenf_vermissten_tage_ueberstehen_den_filter() -> None:
    """Jeder der fuenf Tage in der Formulierung, die er natuerlich hat."""
    for text in ("Leistungsverzeichnis vom 14.02.2025",
                 "Schlussrechnung vom 02.09.2025",
                 "Gutachten vom 18.02.2026",
                 "Schriftsatz der Gegenseite vom 11.03.2026",
                 "Zeugenbenennung vom 08.04.2026"):
        assert chronologie.benennt_ein_schriftstueck(text), text


def test_die_routine_bleibt_abschrift() -> None:
    """Die Ausnahme darf kein Loch reissen - der Rauschwert stand bei 0 %."""
    for text in ("Gewerk Fenster, Kolonne 6 Personen, Arbeiten fortgesetzt",
                 "Göttingen, den 04.05.2026",
                 "Stand: 15.03.2026"):
        assert not chronologie.benennt_ein_schriftstueck(text), text


def test_eine_halbe_seite_bleibt_abschrift() -> None:
    """Wer die Positionsliste anhaengt, schreibt wieder ab."""
    lang = ("Leistungsverzeichnis vom 14.02.2025 zum Bauvorhaben Wohnanlage "
            "Lindenhof, Position 3.4 Wärmedämmung WDVS, Dämmstärke 24 cm, "
            "Fläche 402,00 m², Einheitspreis 48,50 EUR, Gesamtbetrag 19.497,00 EUR")
    assert not chronologie.benennt_ein_schriftstueck(lang)


def test_ohne_datum_ist_es_keine_selbstbenennung() -> None:
    """Ein Schriftstueck ohne Datum traegt keine Frist."""
    assert not chronologie.benennt_ein_schriftstueck("Leistungsverzeichnis der Auftraggeberin")


def test_der_bogen_sagt_was_der_filter_gestrichen_hat() -> None:
    """Sonst ist ein fehlender Tag zweideutig.

    Hat das Modell ihn nicht genannt, oder hat ``aufraeumen`` ihn wieder
    entfernt? Am 28.09.2026 war es das Zweite - und drei Laeufe zu je drei Euro
    haben es nicht gezeigt, weil der Bogen es nicht sagte.

    Die Pruefung haelt die Kette ganz: Der Satz muss aus der Analyse ins
    Ergebnis kommen. Zuerst las der Bogen ihn aus dem Ergebnis, wo er nie
    stand - die Zeile war eine stumme Attrappe.
    """
    import pruefbogen

    analyse = {
        "hinweise": [
            "Diese Analyse beruht auf dem Lebenssachverhalt aus dem Aktengedächtnis.",
            "2 Chronologie-Zeile(n) waren abgeschriebener Dokumenttext statt eines "
            "Ereignisses und wurden entfernt.",
        ],
        "chronologie": [], "zahlen": [], "widersprueche": [],
    }
    ergebnis = pruefbogen.messen(analyse)
    assert any("Chronologie-Zeile" in s for s in ergebnis["gestrichen"])
    bogen = pruefbogen.bogen(ergebnis, {}, "prüfstand")
    assert "abgeschriebener Dokumenttext" in bogen


def test_der_bogen_haelt_einen_lauf_ohne_einlesen_aus() -> None:
    """Beim Wiederverwenden des Gedaechtnisses gibt es keinen Einlese-Lauf.

    Beim ersten Ausprobieren stuerzte der Bogen genau daran ab - an der
    zweiten Stelle, die den Lauf abfragte, nicht an der ersten. Ein Feld auf
    None zu pruefen reicht dort nicht, wo es zweimal vorkommt.
    """
    import pruefbogen

    ergebnis = pruefbogen.messen({"hinweise": [], "chronologie": [],
                                  "zahlen": [], "widersprueche": []})
    text = pruefbogen.bogen(ergebnis, None, "bedrock", {"analyse": "opus"})
    assert "in einem früheren Lauf" in text
    assert "NUR die Analyse gemessen" in text
    # Kein erfundener Betrag fuer etwas, das dieser Lauf nicht bezahlt hat.
    assert "In diesem Lauf bezahlt:" in text
    assert "Zusammen:" not in text


def test_nur_analyse_ohne_gedaechtnisordner_wird_abgewiesen() -> None:
    """Sonst liefe ein voller Lauf, wo ein billiger gemeint war."""
    import subprocess
    import sys

    def pruefbogen_abbruch() -> int:
        import pruefbogen
        return pruefbogen.ABBRUCH

    fertig = subprocess.run(
        [sys.executable, "werkzeug/pruefbogen.py", "--nur-analyse"],
        capture_output=True, text=True, cwd=WURZEL)
    assert fertig.returncode == pruefbogen_abbruch()
    assert "braucht --gedaechtnis" in fertig.stdout


def test_das_material_nennt_das_datum_des_dokuments() -> None:
    """Die eigentliche Ursache der fuenf fehlenden Tage.

    Fuenf Pruefbogenlaeufe mit drei Modellen haben dieselben fuenf Tage
    vermisst. Weder das Modell noch der Auftrag noch der Filter waren schuld:
    Die fuenf Daten stehen in ``akte.json`` im Feld ``datum`` und in keinem
    Dokumenttext. Das Material nannte Titel und Seite, nie das Datum - das
    Modell sollte etwas aufschreiben, was es nicht sehen konnte.

    Belegt am Aktengedaechtnis des Laufs vom 28.09.2026, 13:23 Uhr: keiner der
    fuenf Tage stand darin, weder im Lebenssachverhalt noch in der Chronologie.
    """
    akte = Akte(id="A1", aktenzeichen="44/26 BA", bezeichnung="Bau",
                rechtsgebiet="Baurecht")
    passage = Passage(kennung="D2-S1-P1", dokument_id="D-002",
                      dokument_titel="Leistungsverzeichnis", seite=1,
                      dokument_datum=date(2025, 2, 14),
                      text="Position 3.4 Wärmedämmung WDVS, Dämmstärke 24 cm.")
    material = prompts.material_bauen(akte, [], [], [passage])
    assert "datiert 14.02.2025" in material


def test_ohne_datum_bleibt_die_kopfzeile_wie_bisher() -> None:
    """Kanzleiwissen und Dokumente ohne Datum duerfen kein „datiert None" tragen."""
    akte = Akte(id="A1", aktenzeichen="44/26 BA", bezeichnung="Bau")
    passage = Passage(kennung="D1-S1-P1", dokument_id="D-001",
                      dokument_titel="Aktennotiz", seite=1, text="Text.")
    material = prompts.material_bauen(akte, [], [], [passage])
    assert "datiert" not in material
    assert "None" not in material


def test_die_passage_traegt_das_datum_ihres_dokuments() -> None:
    """Zwischen Stammdaten und Material darf es nicht verlorengehen."""
    from jusperfect.domain.models import Dokument, Seite
    from jusperfect.services.passagen import passagen_bilden

    dokument = Dokument(id="D-002", akte_id="A1", titel="Leistungsverzeichnis",
                        dateiname="lv.pdf", datum=date(2025, 2, 14))
    passagen = passagen_bilden(2, dokument, [Seite(nummer=1, text="Position 3.4.")])
    assert passagen[0].dokument_datum == date(2025, 2, 14)


def test_die_fuenf_tage_stehen_in_den_stammdaten_der_testakte() -> None:
    """Sonst verlangt der Pruefbogen, was die Testakte nicht hergibt.

    Waeren sie dort nicht, waere nicht das Programm falsch, sondern die
    Messlatte - und das waere der wichtigere Befund. Diese Pruefung haelt fest,
    woran es wirklich lag.
    """
    import json

    akte = json.loads((WURZEL / "testdaten"
                       / "grosse-akte" / "BA-2026-0044" / "akte.json").read_text(encoding="utf-8"))
    daten = {d.get("datum") for d in akte.get("dokumente", [])}
    for iso in ("2025-02-14", "2025-09-02", "2026-02-18", "2026-03-11", "2026-04-08"):
        assert iso in daten, iso


def test_das_datum_ueberlebt_den_weg_durch_das_gedaechtnis() -> None:
    """Die Stelle, an der es am 28.09.2026 zum zweiten Mal verlorenging.

    Das Einlesen geht NICHT ueber die Dokumente der Akte, sondern ueber die
    Auszuege im Gedaechtnis: ``Gedaechtnisdienst._passagen`` baut sich aus
    jedem Auszug ein Dokument zusammen. ``GedaechtnisDokument`` trug kein
    Datum, und das zusammengebaute Dokument bekam keines - also stand in der
    Kopfzeile jeder Passage keines, obwohl Passage und Material es schon
    vorsahen.

    Belegt an zwei Aktengedaechtnissen echter Laeufe (13:23 und 13:47 Uhr):
    keiner der fuenf Tage stand darin. Danach oertlich nachgestellt: 50 von 50
    Dokumenten tragen ihr Datum, alle 670 Passagen, und das Material nennt
    alle fuenf.
    """
    from jusperfect.domain.models import Aktengedaechtnis, GedaechtnisDokument, Seite
    from jusperfect.services.gedaechtnis import Gedaechtnisdienst

    g = Aktengedaechtnis(
        akte_id="A1", aktenzeichen="44/26 BA", bezeichnung="Bau",
        dokumente=[GedaechtnisDokument(
            dokument_id="D-002", titel="Leistungsverzeichnis", nummer=2,
            datum=date(2025, 2, 14),
            seiten=[Seite(nummer=1, text="Position 3.4 Wärmedämmung, 24 cm.")])])

    passagen = Gedaechtnisdienst._passagen(g)
    assert passagen, "Keine Passage gebaut."
    assert passagen[0].dokument_datum == date(2025, 2, 14)

    material = prompts.material_bauen(
        Akte(id="A1", aktenzeichen="44/26 BA", bezeichnung="Bau"), [], [], passagen)
    assert "datiert 14.02.2025" in material


def test_ein_altes_gedaechtnis_ohne_datum_bleibt_lesbar() -> None:
    """Ein Gedaechtnis aus einer aelteren Fassung hat kein Datum.

    Das ist hinnehmbar - beim naechsten Einlesen wird es gefuellt -, aber es
    darf nicht zum Fehler fuehren und keine Kopfzeile "datiert None" erzeugen.
    """
    from jusperfect.domain.models import Aktengedaechtnis, GedaechtnisDokument, Seite
    from jusperfect.services.gedaechtnis import Gedaechtnisdienst

    g = Aktengedaechtnis(
        akte_id="A1", aktenzeichen="44/26 BA", bezeichnung="Bau",
        dokumente=[GedaechtnisDokument(
            dokument_id="D-002", titel="Leistungsverzeichnis", nummer=2,
            seiten=[Seite(nummer=1, text="Position 3.4.")])])
    passagen = Gedaechtnisdienst._passagen(g)
    assert passagen[0].dokument_datum is None
    material = prompts.material_bauen(
        Akte(id="A1", aktenzeichen="44/26 BA", bezeichnung="Bau"), [], [], passagen)
    assert "datiert" not in material
    assert "None" not in material
