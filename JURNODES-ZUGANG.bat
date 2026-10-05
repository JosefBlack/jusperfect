@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
title jusperfect - jur^|nodes-Zugang hinterlegen

echo ============================================
echo    Zugang hinterlegen - jur^|nodes und Schutzgelaender
echo ============================================
echo.
echo Gebraucht werden drei Angaben aus jur^|nodes:
echo   die Adresse der Schnittstelle
echo   der Benutzername (z. B. user_2)
echo   der Token
echo.
echo Dazu die Kennung des Schutzgelaenders aus der Bedrock-Konsole.
echo Haben Sie sie frueher schon einmal eingetragen, wird sie in den
echo aelteren Ordnern gesucht und steht dann bereits da - Sie druecken
echo nur die Eingabetaste. Gelesen wird dabei nichts ausser dieser
echo einen Zeile, geschrieben wird dort gar nichts.
echo.
echo Sie bleiben auf diesem Rechner, in Ihrem Windows-Konto. Sie kommen
echo in keine Datei des Programmordners und in keine ZIP.
echo.

REM Diese Datei braucht die Arbeitsumgebung NICHT. Sie hinterlegt vier
REM Werte im Windows-Konto und kommt dabei mit dem aus, was in jedem
REM Python steckt - kein einziges Zusatzpaket.
REM
REM Sie verlangte trotzdem die .venv, und am 25.09.2026 stand die Kanzlei
REM damit vor einem frisch ausgepackten Ordner: Zugang eintragen ging
REM nicht, weil zuerst etwas ganz anderes zu starten gewesen waere. Eine
REM Huerde, die nichts schuetzt, ist keine Sperre, sondern ein Fehler.
set "PY=.venv\Scripts\python.exe"
if exist "%PY%" goto losgehts

REM Kein eigener Ordner da - dann das Python des Rechners.
set "PY=python"
where python >nul 2>&1
if errorlevel 1 goto keinpython

:losgehts
"%PY%" -m jusperfect.jurnodeszugang
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
