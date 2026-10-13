@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
title jusperfect - Briefbogen hinterlegen

echo ============================================
echo    Briefbogen hinterlegen
echo ============================================
echo.
echo Auf diesen Briefbogen setzt jusperfect einen Entwurf, wenn Sie
echo beim Entwurf auf "Auf Briefbogen (Word)" klicken.
echo.
echo Gebraucht wird Ihre eigene Word-Vorlage (.docx) mit Kopfzeile,
echo Fusszeile und Logo - und einem leeren Rumpf. Alles darin bleibt,
echo wie es ist; nur der leere Rumpf bekommt den Text. Nachgebaut
echo wird nichts: Ein nachgezeichneter Briefbogen ist aehnlich genug,
echo um es nicht zu merken, und irgendwo falsch.
echo.
echo Die Datei bleibt auf diesem Rechner, NEBEN dem Programmordner -
echo nicht darin, denn sonst ginge sie mit jeder ZIP mit und waere
echo beim naechsten Herunterladen weg.
echo.
echo Auf jedem Kanzleirechner einmal.
echo.

REM Wie SPERRLISTE-ANLEGEN.bat: Diese Datei braucht die Arbeitsumgebung
REM nicht - sie kopiert eine Datei und kommt mit dem aus, was in jedem
REM Python steckt. Eine Huerde, die nichts schuetzt, ist keine Sperre,
REM sondern ein Fehler.
set "PY=.venv\Scripts\python.exe"
if exist "%PY%" goto losgehts

set "PY=python"
where python >nul 2>&1
if errorlevel 1 goto keinpython

:losgehts
"%PY%" -m jusperfect.services.briefbogen
if errorlevel 1 echo   Es wurde nichts hinterlegt.
pause
goto ende

:keinpython
echo.
echo   Auf diesem Rechner ist kein Python zu finden.
echo.
echo   Starten Sie einmal START-DEMO.bat - sie richtet die
echo   Arbeitsumgebung ein. Danach geht es hier weiter.
echo.
pause

:ende
endlocal
