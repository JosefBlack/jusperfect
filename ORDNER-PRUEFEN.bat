@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
title jusperfect - taugt der Aktenordner?

echo ============================================
echo    Taugt der Aktenordner fuer jusperfect?
echo ============================================
echo.
echo Diese Probe SIEHT NUR NACH. Sie aendert nichts, legt nichts an
echo und loescht nichts. Nur fuer das Schreibrecht wird eine einzelne
echo Probedatei angelegt und sofort wieder entfernt.
echo.
echo Sie beantwortet die Frage, an der der Laufwerksweg haengt:
echo Ist der Ordnerbaum so gebaut, wie jusperfect ihn erwartet?
echo.
echo     ^<Wurzel^>\^<Anwalt^>\^<Jahr^>\^<Aktenzeichen Bezeichnung^>\
echo.

rem Welcher Programmstand liegt hier? Am 16.09.2026 lief in der Kanzlei
rem ein Ordner, in dem der Programmteil neu und die Startdateien alt
rem waren; gesucht wurde zweimal an der falschen Stelle. Am 23.09.2026
rem dasselbe noch einmal - die Probe gab kein Lebenszeichen, und es war
rem nicht zu erkennen, ob der alte oder der neue Stand lief. Diese eine
rem Zeile beantwortet das vor dem ersten Tastendruck.
set "FASSUNG=unbekannt - vor dem 17.09.2026 ausgepackt"
if exist "FASSUNG.txt" for /f "usebackq delims=" %%z in ("FASSUNG.txt") do set "FASSUNG=%%z"
echo Programmstand: %FASSUNG%
echo.

if not exist ".venv\Scripts\python.exe" goto keinevenv

rem Der Pfad steht meist schon in der Startdatei; dann genuegt die
rem Eingabetaste. Netzlaufwerke sind je Windows-Konto verbunden - im
rem neuen Konto fehlt das Laufwerk zunaechst.
set "ORDNER=%JUSPERFECT_JURNODES_WEBDAV%"
if defined ORDNER echo Voreingestellt: %ORDNER%
set /p ORDNER=Aktenordner (z. B. J:\Akten), Eingabetaste uebernimmt: 

if not defined ORDNER goto keinordner
echo.
rem Die Probe schreibt selbst mit - auf den Schirm UND in die Datei.
rem Vorher ging die Ausgabe erst in die Datei und danach per "type" auf
rem den Schirm. Auf einem echten Kanzleilaufwerk blieb das Fenster damit
rem minutenlang leer, und es war nicht zu erkennen, ob die Probe arbeitet.
".venv\Scripts\python.exe" -m jusperfect.ordnerpruefung "%ORDNER%"
echo.
echo Bitte die Beispielzeilen kurz durchsehen, bevor Sie die Datei
echo weitergeben - dort stehen Aktenzeichen und Bezeichnungen.
echo.
pause
goto ende

:keinordner
echo.
echo Kein Ordner angegeben. Ohne Pfad gibt es nichts zu pruefen.
pause
goto ende

:keinevenv
echo Es fehlt die Arbeitsumgebung .venv. Bitte zuerst START-AWS.bat ausfuehren.
pause

:ende
