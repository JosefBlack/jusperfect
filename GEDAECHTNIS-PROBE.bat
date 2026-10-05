@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem Ein gefuehrter Durchgang durch das Aktengedaechtnis - ohne KI, ohne Kosten,
rem ohne Browser. Acht Schritte, nach jedem steht da, was im Gedaechtnis liegt.

if not exist ".venv\Scripts\python.exe" goto keinevenv

.venv\Scripts\python.exe werkzeug\gedaechtnis_probe.py
if errorlevel 1 goto fehler
echo.
echo Fertig. Zum Schliessen eine Taste druecken.
pause >nul
goto ende

:keinevenv
echo Es fehlt die Arbeitsumgebung .venv. Bitte zuerst START-DEMO.bat ausfuehren.
pause
goto ende

:fehler
echo.
echo Der Durchgang ist abgebrochen. Bitte die Meldung darueber weitergeben.
pause

:ende
