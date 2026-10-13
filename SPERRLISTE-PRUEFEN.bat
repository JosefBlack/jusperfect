@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
title jusperfect - steht ein echter Name im Programmordner?

echo ============================================
echo    Steht ein echter Name im Programmordner?
echo ============================================
echo.
echo Diese Probe durchsucht jede Datei des Programmordners nach den
echo Namen aus der Sperrliste und nach echten Aktenzeichen.
echo.
echo Sie kostet nichts: kein Modellaufruf, keine Verbindung nach
echo aussen, keine Akte wird angefasst.
echo.
echo Vor jeder Weitergabe des Ordners und vor jeder ZIP.
echo.

REM Diese Datei braucht die Arbeitsumgebung NICHT - sie liest Dateien und
REM kommt mit dem aus, was in jedem Python steckt.
REM
REM Und sie gibt es, weil ich der Kanzlei zweimal gesagt habe, sie solle
REM dafuer PRUEFBOGEN.bat starten. Das ist der Messlauf ueber die grosse
REM Testakte und kostet einige Euro. Eine Auskunft, die Geld kostet, holt
REM sich niemand - und ein Riegel, den niemand nachsieht, ist keiner.
set "PY=.venv\Scripts\python.exe"
if exist "%PY%" goto losgehts

REM Kein eigener Ordner da - dann das Python des Rechners.
set "PY=python"
where python >nul 2>&1
if errorlevel 1 goto keinpython

:losgehts
"%PY%" -m jusperfect.sperrliste --pruefen
echo.
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
