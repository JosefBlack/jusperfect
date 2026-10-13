@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
title jusperfect - gesperrte Namen hinterlegen

echo ============================================
echo    Gesperrte Namen hinterlegen
echo ============================================
echo.
echo Diese Liste sagt dem Prueflauf, nach welchen Namen er suchen
echo soll. Findet er einen im Programmordner, faellt er rot aus -
echo so kommt kein echter Name aus einer Akte in eine ZIP oder in
echo ein Pruefpaket fuer einen Dritten.
echo.
echo Die Liste bleibt auf diesem Rechner, neben dem Programmordner.
echo Sie kommt NICHT in den Programmordner und NICHT in eine ZIP -
echo denn dann stuenden die Namen in genau dem Paket, das sie
echo heraushalten soll. Genau das ist am 12.10.2026 passiert.
echo.
echo Auf jedem Kanzleirechner einmal. Die Liste wird nicht
echo mitgeschickt und nicht abgeglichen.
echo.

REM Diese Datei braucht die Arbeitsumgebung NICHT - sie legt eine
REM Textdatei an und kommt mit dem aus, was in jedem Python steckt.
REM Dieselbe Erwaegung wie bei JURNODES-ZUGANG.bat: Eine Huerde, die
REM nichts schuetzt, ist keine Sperre, sondern ein Fehler.
set "PY=.venv\Scripts\python.exe"
if exist "%PY%" goto losgehts

REM Kein eigener Ordner da - dann das Python des Rechners.
set "PY=python"
where python >nul 2>&1
if errorlevel 1 goto keinpython

:losgehts
"%PY%" -m jusperfect.sperrliste
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
