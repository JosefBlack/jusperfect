"""Das Gedächtnis liegt in der Akte selbst.

Aus der Kanzlei: „Ich möchte das Gedächtnis in der Akte haben. Ich möchte nicht
lange nach dem Gedächtnis suchen müssen. Problem ist, dass der Serverspeicher
sehr teuer ist."

Dieser Speicher legt das Gedächtnis dorthin, wo die Akte ohnehin liegt – in
ihren Ordner, als eine Datei, die im Ordner oben steht. Das hat drei Folgen,
die sich gut fügen:

* **Auffindbar.** Wer die Akte öffnet, sieht das Gedächtnis. Kein zweiter Ort,
  kein Suchen, kein Klicken.
* **Mitgesichert.** Die Sicherung des Aktenservers erfasst es mit. Es entsteht
  kein weiterer Aufbewahrungsort, der eigens gesichert und beschrieben werden
  müsste.
* **Mitgelöscht.** Wird die Akte gelöscht, verschwindet das Gedächtnis mit ihr.
  Eine verwaiste Kopie kann so gar nicht erst entstehen.

Die Grenze bleibt dabei scharf. Der Adapter kennt genau einen Dateinamen, und
der Aufrufer kann ihn nicht wählen: Über diesen Weg entsteht diese eine Datei
und keine andere. Für alles Übrige gilt weiter, was immer galt – gelesen wird
frei, geschrieben nur nach ausdrücklicher Freigabe durch einen Menschen.

Abgelegt wird gepackt (siehe ``gedaechtnis/packen.py``), gelesen wird beides.
"""

from __future__ import annotations

from jusperfect.domain.models import Aktengedaechtnis
from jusperfect.gedaechtnis.base import GedaechtnisFehler
from jusperfect.gedaechtnis.packen import entpacken, packen
from jusperfect.jurnodes.base import JurNodesAdapter, JurNodesFehler


class AkteGedaechtnisSpeicher:
    """Führt das Gedächtnis als Datei in der Akte, über den jurnodes-Adapter.

    Seit dem 25.09.2026 sind es mehrere Fassungen nebeneinander statt einer
    übereinander: jur|nodes ersetzt eine vorhandene Datei nicht, sondern
    weist sie ab, und das Löschrecht hat die Kanzlei bewusst nicht erteilt.
    Gelesen wird die jüngste.
    """

    #: Ab wie vielen Fassungen beim Öffnen darauf hingewiesen wird.
    FASSUNGEN_HINWEIS = 20

    def __init__(self, adapter: JurNodesAdapter) -> None:
        for name in ("gedaechtnis_lesen", "gedaechtnis_ablegen", "gedaechtnis_loeschen"):
            if not hasattr(adapter, name):
                raise GedaechtnisFehler(
                    "Dieser Aktenzugang kann das Gedächtnis nicht in der Akte führen. "
                    "Bitte JUSPERFECT_GEDAECHTNIS=lokal oder =aws verwenden."
                )
        self._adapter = adapter

    @property
    def letzte_fassungen(self) -> int:
        """Wie viele Fassungen beim letzten Lesen in der Akte lagen."""
        return int(getattr(self._adapter, "letzte_fassungen", 0))

    def lesen(self, akte_id: str) -> Aktengedaechtnis | None:
        try:
            rohdaten = self._adapter.gedaechtnis_lesen(akte_id)
        except JurNodesFehler as e:
            raise GedaechtnisFehler(str(e)) from e
        if rohdaten is None:
            return None
        gedaechtnis = entpacken(rohdaten)
        if gedaechtnis.akte_id != akte_id:
            # Eine Gedaechtnisdatei, die in der falschen Akte liegt, ist
            # gefaehrlicher als keine: Sie brachte fremden Aktentext in diese
            # Sache. Kopierte Aktenordner sind der uebliche Weg dorthin.
            raise GedaechtnisFehler(
                "Das Gedächtnis in diesem Aktenordner gehört zu einer anderen Akte."
            )
        return gedaechtnis

    def ablegen(self, gedaechtnis: Aktengedaechtnis) -> None:
        try:
            self._adapter.gedaechtnis_ablegen(gedaechtnis.akte_id, packen(gedaechtnis))
        except JurNodesFehler as e:
            raise GedaechtnisFehler(str(e)) from e

    def loeschen(self, akte_id: str) -> None:
        try:
            self._adapter.gedaechtnis_loeschen(akte_id)
        except JurNodesFehler as e:
            raise GedaechtnisFehler(str(e)) from e

    def auflisten(self) -> list[Aktengedaechtnis]:
        """Alle vorhandenen Gedächtnisse – für die Aufsicht.

        Anders als bei einer eigenen Ablage gibt es hier keine Liste der
        Gedächtnisse; es gibt nur die Liste der Akten. Wir gehen sie durch und
        nehmen mit, was ein Gedächtnis trägt. Eine Akte, deren Gedächtnis
        unlesbar ist, darf die Aufsicht nicht zum Stehen bringen – sonst
        verdeckt ein einzelner beschädigter Ordner alle anstehenden Fristen.
        """
        ergebnis: list[Aktengedaechtnis] = []
        try:
            akten = self._adapter.akten_suchen("")
        except JurNodesFehler as e:
            raise GedaechtnisFehler(str(e)) from e
        for akte in akten:
            try:
                gedaechtnis = self.lesen(akte.id)
            except GedaechtnisFehler:
                continue
            if gedaechtnis is not None:
                ergebnis.append(gedaechtnis)
        return ergebnis
