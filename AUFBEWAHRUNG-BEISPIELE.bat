@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem Beispielfaelle fuer die Ansicht "Aufbewahrung" anlegen und ansehen.
rem Sie machen sichtbar, was das Programm nicht selbst entscheiden darf.

if not exist ".venv\Scripts\python.exe" goto keinevenv

.venv\Scripts\python.exe werkzeug\aufbewahrung_beispiele.py
if errorlevel 1 goto fehler

echo.
echo Das Programm startet jetzt mit diesen Beispielfaellen.
echo Anmelden als RA Dr. Weber, dann unten auf "Aufbewahrung" klicken.
echo Zum Beenden dieses Fenster schliessen.
echo.

set JUSPERFECT_BETRIEBSART=lokal
set JUSPERFECT_ANBIETER=demo
set JUSPERFECT_JURNODES_ADAPTER=fixture
set JUSPERFECT_FIXTURE_PFAD=testdaten\aufbewahrung\akten
set JUSPERFECT_NUTZER_DATEI=testdaten\nutzer.json
set JUSPERFECT_GEDAECHTNIS=lokal
set JUSPERFECT_GEDAECHTNIS_PFAD=testdaten\aufbewahrung\gedaechtnis
start "" http://127.0.0.1:8765
.venv\Scripts\python.exe -m jusperfect
goto ende

:keinevenv
echo Es fehlt die Arbeitsumgebung .venv. Bitte zuerst START-DEMO.bat ausfuehren.
pause
goto ende

:fehler
echo Die Beispielfaelle konnten nicht angelegt werden.
pause

:ende
