@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
title jusperfect - nimmt AWS die Texterkennung an?

echo ============================================
echo    Nimmt AWS die Texterkennung an?
echo ============================================
echo.
echo Diese Probe schickt EIN selbst gebautes Blatt an die Texterkennung
echo und sieht nach, ob das Wort darauf zurueckkommt.
echo.
echo Aus der Kanzlei geht nichts hinaus. Das Blatt baut die Probe selbst;
echo es enthaelt kein Akteninhalt und keinen Mandantennamen.
echo.
echo Warum es die Probe gibt: Der Selbsttest sagt, dass die Texterkennung
echo eingeschaltet ist. Ob die Zugriffsrichtlinie das Recht dazu traegt,
echo sagt er nicht. Ohne diese Probe faellt das Fehlen erst auf, wenn eine
echo Akte offen ist - dann bleiben die gescannten Blaetter ungelesen, und
echo das sieht aus wie ein Mangel der Erkennung statt einer Berechtigung.
echo.
echo Es wird KEIN Modell aufgerufen. Die Probe kostet rund 0,15 Cent.
echo.
echo Weiter mit einer Taste, Abbruch mit Strg+C.
pause >nul

call "%~dp0_UMGEBUNG.bat" 2
if errorlevel 1 exit /b 1

echo.
"%PY%" werkzeug\texterkennung_probe.py
set ERG=%errorlevel%
echo.
if %ERG%==0 echo Die Texterkennung arbeitet. Gescannte Blaetter werden gelesen.
if %ERG%==1 echo Die Probe ist gescheitert. Bitte die Meldung darueber weitergeben.
echo.
echo Zum Schliessen eine Taste druecken.
pause >nul
endlocal
