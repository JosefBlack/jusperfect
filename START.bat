@echo off
REM ====================================================================
REM   START.bat - der Weg zu den ECHTEN Akten der Kanzlei.
REM ====================================================================
REM
REM Aus der Kanzlei am 13.10.2026: "Warum heisst die Startdatei
REM START-JURNODES - ist doch unlogisch, und die Eingabeaufforderung
REM schreibt, ich kann START-AWS benutzen."
REM
REM Beides stimmt. Die vier Startdateien sind nacheinander entstanden und
REM jede nach etwas anderem benannt: DEMO nach dem Zweck, AWS nach dem
REM Modellanbieter, KANZLEI nach dem Ort, JURNODES nach der Schnittstelle.
REM Keiner der Namen sagt das Einzige, worauf es ankommt - echte Akten
REM oder erfundene. Und "AWS" trennt nach etwas, das gar nicht trennt:
REM Das Modell kommt in allen vier Faellen von dort.
REM
REM Entschieden wurde am 13.10.2026, die Namen zu LASSEN - eine
REM Verknuepfung auf dem Schreibtisch, ein zweiter Rechner und rund 240
REM Stellen in den Unterlagen haengen daran - und diese Datei
REM danebenzulegen. Wer nicht weiss, welche er nehmen soll, nimmt diese.
REM
REM Hier stehen KEINE Einstellungen. Eine zweite Stelle, an der
REM dieselben Werte stuenden, waere genau der Fehler, den die Pruefungen
REM seit dem 25.09.2026 verbieten: Eine Verbesserung an der einen und
REM nicht an der anderen, und niemand sieht es. Deshalb ruft diese Datei
REM die andere auf, und sonst nichts.
REM ====================================================================
call "%~dp0START-JURNODES.bat" %*
