"""Verknüpfung und Programmsymbol.

Aus der Kanzlei: „Eine Verknüpfung für den Desktop kann ich auch noch nicht
herstellen oder?" Eine Batchdatei sieht auf dem Schreibtisch aus wie ein
Zahnrad und ist von der nächsten nicht zu unterscheiden.

Zwei Verknüpfungen, nicht eine: Der Unterschied zwischen „ruft das Modell und
kostet Geld" und „kostet nichts" ist zu wichtig, um hinter einem Symbol zu
verschwinden.
"""

from __future__ import annotations

import struct
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
SYMBOL = WURZEL / "jusperfect" / "static" / "jusperfect.ico"
SKRIPT = WURZEL / "VERKNUEPFUNG.bat"


class Verknuepfung(unittest.TestCase):
    def test_es_gibt_die_datei(self):
        self.assertTrue(SKRIPT.exists())

    def test_zeilenenden_bleiben_windowstauglich(self):
        roh = SKRIPT.read_bytes()
        self.assertEqual(roh.count(b"\n"), roh.count(b"\r\n"))

    def test_beide_betriebsarten_bekommen_eine(self):
        """Berichtigt am 13.10.2026: die erste fuehrt zu den ECHTEN Akten.

        Hier stand ``START-AWS.bat`` - und die Verknuepfung hiess dabei
        schlicht "jusperfect". Wer sie vom Schreibtisch nahm, arbeitete mit
        erfundenen Akten und merkte es erst an den Namen darin. Die Pruefung
        war gruen: Sie fragte, ob eine Datei genannt wird, nicht welche.
        """
        t = SKRIPT.read_text(encoding="utf-8")
        self.assertIn("START-JUSPERFECT.bat", t)
        self.assertIn("START-DEMO.bat", t)

    def test_der_name_sagt_was_kostet(self):
        """Wer das Demo-Symbol anklickt, soll wissen, dass kein Modell läuft."""
        t = SKRIPT.read_text(encoding="utf-8")
        self.assertIn("Demo, ohne KI", t)

    def test_ohne_klammernbloecke(self):
        """cmd wertet in Klammernblöcken früher aus, als man denkt."""
        t = SKRIPT.read_text(encoding="utf-8")
        # Die geschweiften Klammern in der PowerShell-Zeile sind deren Syntax,
        # nicht die von cmd - nur runde Bloecke sind hier gemeint.
        cmd_teil = t[: t.index(":verknuepfen")]
        self.assertNotIn("(", cmd_teil.replace("%~dp0", "").replace("(Demo", ""))

    def test_ein_fehlendes_symbol_wird_gemeldet(self):
        """Sonst entsteht eine Verknüpfung ohne Bild, und niemand weiß warum.

        Genau das ist passiert: Die Bedingung um IconLocation herum übersprang
        das Symbol stillschweigend, wenn die Datei fehlte. Auf dem Schreibtisch
        lag dann ein Symbol ohne Bild und der Grund stand nirgends.
        """
        t = SKRIPT.read_text(encoding="utf-8")
        self.assertIn('if exist "%SYMBOL%" goto symbol_da', t)
        self.assertIn("Das Programmsymbol fehlt", t)
        # Und wer trotzdem will, darf - aber er hat es dann gelesen.
        self.assertIn("choice /C JN", t)

    def test_die_werte_stehen_in_einfachen_anfuehrungszeichen(self):
        """Sonst bricht cmd die Klammerung der PowerShell-Zeile auf.

        So ist es passiert: Die Zeile lautete
        ``"$pfad = Join-Path $schreibtisch (%1 + '.lnk');"``. cmd setzt fuer
        %1 den Wert *samt seinen doppelten Anfuehrungszeichen* ein - mitten in
        eine Zeile, die selbst schon doppelt gequotet ist. Die Klammerung
        endet dort vorzeitig, und PowerShell bekommt ein nacktes Wort:
        „Die Benennung jusperfect wurde nicht als Name eines Cmdlet erkannt."
        Danach war $v leer und jede weitere Eigenschaft schlug fehl.

        %~1 liefert den Wert ohne Anfuehrungszeichen; die einfachen hier
        vertragen ausserdem die Klammern und das Komma aus
        „jusperfect (Demo, ohne KI)".
        """
        t = SKRIPT.read_text(encoding="utf-8")
        routine = t[t.index(":verknuepfen"):]
        for roh, gesetzt in (("%1", "'%~1"), ("%2", "'%~2'"), ("%3", "'%~3'")):
            self.assertIn(gesetzt, routine, f"{roh} nicht in einfachen Anfuehrungszeichen")
        # Und kein unmaskiertes %1/%2/%3 mehr in der PowerShell-Zeile selbst.
        for zeile in routine.splitlines():
            if not zeile.strip().startswith(("rem", "%1", ":")):
                for roh in ("%1", "%2", "%3"):
                    self.assertNotIn(roh, zeile, f"{roh} steht noch roh in: {zeile.strip()}")

    def test_es_prueft_den_ordner(self):
        """Im falschen Ordner ausgeführt, legt es keine toten Verknüpfungen an."""
        t = SKRIPT.read_text(encoding="utf-8")
        self.assertIn('if exist "%ORDNER%\\START-JUSPERFECT.bat" goto gefunden', t)


class Symbol(unittest.TestCase):
    def test_es_gibt_das_symbol(self):
        self.assertTrue(SYMBOL.exists())

    def test_es_traegt_die_kleinen_groessen(self):
        """16 und 32 sind Taskleiste und Schreibtisch - ohne sie rechnet Windows
        selbst herunter, und aus dem Punkt auf dem j wird Matsch."""
        roh = SYMBOL.read_bytes()
        self.assertEqual(roh[:4], b"\x00\x00\x01\x00", "keine ICO-Datei")
        anzahl = struct.unpack("<H", roh[4:6])[0]
        groessen = set()
        for i in range(anzahl):
            eintrag = roh[6 + i * 16: 6 + (i + 1) * 16]
            breite = eintrag[0] or 256
            groessen.add(breite)
        self.assertIn(16, groessen)
        self.assertIn(32, groessen)
        self.assertIn(256, groessen)

    def test_die_oberflaeche_zeigt_es_im_tab(self):
        html = (WURZEL / "jusperfect" / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/static/jusperfect.ico"', html)

    def test_es_wird_mitverpackt(self):
        """Ohne diesen Eintrag fehlt das Symbol in einer richtigen Installation."""
        pyproject = (WURZEL / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('"static/*"', pyproject)


if __name__ == "__main__":
    unittest.main()
