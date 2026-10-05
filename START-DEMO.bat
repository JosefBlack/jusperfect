@echo off
chcp 65001 >nul
setlocal
rem Python schreibt Haken und Striche. Ohne diese Zeichentabelle bricht
rem die Ausgabe beim ersten Sonderzeichen ab. Hinter setlocal, damit die
rem Einstellung das Fenster des Nutzers nicht ueberdauert.
set PYTHONUTF8=1
cd /d "%~dp0"
title jusperfect - Demo

echo ============================================
echo    jusperfect - Demo (Testakten, ohne KI)
echo ============================================
echo.

REM --- Die Arbeitsumgebung -------------------------------------------------
REM Python finden, .venv anlegen, Bausteine installieren, den Aufbau des
REM Ordners pruefen: Das steht in _UMGEBUNG.bat, damit alle Startdateien
REM dasselbe tun.
REM
REM Bis zum 28.09.2026 hatte diese Datei eine eigene Kopie davon - 134
REM Zeilen, entstanden vor _UMGEBUNG.bat und seither nicht mitgewandert.
REM Sie wich schon ab: VPY statt PY, kein boto3, eine eigene Fehlermarke.
REM Darin steckt die Arbeit von Monaten - die Store-Attrappe von Windows,
REM die falsche Python-Fassung, der fehlende PATH-Haken. Zwei Kopien laufen
REM auseinander, und dann hilft der einen Startdatei, was in der anderen
REM laengst steht.
REM
REM Die 3 ist die Zahl der Schritte, die diese Datei anzeigt.
call "%~dp0_UMGEBUNG.bat" 3
if errorlevel 1 exit /b 1


REM --- Demo-Einstellungen: Testakten, kein AWS, keine KI, keine Kosten ---
set JUSPERFECT_BETRIEBSART=lokal
set JUSPERFECT_ANBIETER=demo
set JUSPERFECT_JURNODES_ADAPTER=fixture
REM Voreinstellung, keine Festlegung: Wer vorher
REM   set JUSPERFECT_FIXTURE_PFAD=testdaten\grosse-akte
REM gesetzt hat, soll die grosse Testakte auch bekommen. Vorher stand hier
REM ein unbedingtes set - es hat die eigene Wahl still ueberschrieben, und
REM in der Aktenliste standen wieder nur die vier kleinen. Genau den Weg
REM empfiehlt GROSSE-TESTAKTE.bat am Ende.
if not defined JUSPERFECT_FIXTURE_PFAD set JUSPERFECT_FIXTURE_PFAD=testdaten\akten
if not defined JUSPERFECT_NUTZER_DATEI set JUSPERFECT_NUTZER_DATEI=testdaten\nutzer.json

REM --- Aktengedaechtnis: an, weil ein Mandat ueber Tage laeuft ---
REM Ohne Gedaechtnis lebt eine Sitzung 15 Minuten. Wer am Dienstag weiterarbeiten
REM will, faengt sonst wieder von vorn an. Der Ordner wird beim ersten Start
REM angelegt und enthaelt NUR die erfundenen Testakten - unverschluesselt.
REM Deshalb laesst das Programm diese Einstellung auch nur mit den Testakten zu.
REM Zum Zuruecksetzen: GEDAECHTNIS-LEEREN.bat
set JUSPERFECT_GEDAECHTNIS=lokal
set JUSPERFECT_GEDAECHTNIS_PFAD=.jusperfect-gedaechtnis

REM --- Eigene Auftraege: aus, bis die Kanzlei einen Ordner dafuer hat ---
REM Ein eigener Auftrag ist eine Textdatei: Dateiname wird die Beschriftung,
REM Unterordner das Rechtsgebiet. Wer das nutzen will, nimmt bei der naechsten
REM Zeile das REM weg und traegt seinen Ordner ein. Ohne Ordner fehlen die
REM Auswahl beim Entwurf und der Knopf "Als eigenen Auftrag vormerken" -
REM das ist so gewollt und kein Fehler.
REM set JUSPERFECT_AUFTRAG_ORDNER=J:\Kanzlei\jusperfect-auftraege

set JUSPERFECT_HOST=127.0.0.1
set JUSPERFECT_PORT=8765

echo [3/3] jusperfect startet - der Browser oeffnet sich gleich von selbst.
echo.
echo    Adresse:  http://127.0.0.1:8765
echo    Nutzer:   ra-weber    (eintippen, dann auf "Suchen" klicken)
echo.
echo    Das Aktengedaechtnis ist AN: Was Sie heute aufnehmen und fragen,
echo    steht morgen noch da. Es liegt in .jusperfect-gedaechtnis und
echo    enthaelt nur die erfundenen Testakten.
echo.
echo    Zum Beenden einfach dieses schwarze Fenster schliessen.
echo ============================================
echo.

REM Der Browser geht erst auf, wenn der Server wirklich antwortet.
REM Vorher wurden hier vier Sekunden gewartet - das ist auf einem
REM langsamen Rechner zu kurz und auf einem schnellen zu lang.
set JUSPERFECT_BROWSER_OEFFNEN=1

REM Server im Vordergrund starten (laeuft, bis das Fenster geschlossen wird)
"%PY%" -m jusperfect

goto ende

REM Hier stand eine Marke :fehler mit dem Satz "Bei der Einrichtung ist etwas
REM schiefgegangen". Sie wird nicht mehr angesprungen - _UMGEBUNG.bat meldet
REM jeden dieser Faelle selbst, und zwar mit dem Satz, der zur Ursache passt.

:ende
endlocal
