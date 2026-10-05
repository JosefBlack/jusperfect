@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
title jusperfect - nimmt jur^|nodes das Aktengedaechtnis an?

echo ============================================
echo    Nimmt jur^|nodes das Aktengedaechtnis an?
echo ============================================
echo.
echo ACHTUNG: Diese Probe SCHREIBT. Alle anderen lesen nur.
echo.
echo Sie legt in der genannten Akte die eine Datei ab, die jusperfect
echo dort ohnehin fuehrt. Darin steht eine einzige Zeile: Datum und
echo Zweck. Kein Akteninhalt, kein Mandantenname.
echo.
echo Wird sie abgewiesen, ist nichts geschrieben worden - und der
echo Wortlaut des Servers steht danach auf dem Schirm. Genau darum
echo geht es: Er sagt, welche Angabe ihm nicht passt.
echo.
echo Geht sie durch, liegt die Datei dort, wo sie hingehoert. Loeschen
echo laesst sie sich in jur^|nodes jederzeit.
echo.
echo Ohne ein ausdrueckliches "ja" geschieht nichts.
echo.

set "FASSUNG=unbekannt - vor dem 17.09.2026 ausgepackt"
if exist "FASSUNG.txt" for /f "usebackq delims=" %%z in ("FASSUNG.txt") do set "FASSUNG=%%z"
echo Programmstand: %FASSUNG%
echo.

REM Die Arbeitsumgebung anlegen, falls sie fehlt - dieselbe Datei,
REM die auch die Startdateien dafuer aufrufen.
call "%~dp0_UMGEBUNG.bat" 2
if errorlevel 1 exit /b 1

set "AKTE="
set /p AKTE=Aktenzeichen der Akte:
if not defined AKTE goto keineakte

echo.
"%PY%" werkzeug\ablageprobe.py "%AKTE%"

echo.
echo Bitte die Zeile "Der Server sagt dazu" weitergeben.
echo.
pause
goto ende

:keineakte
echo.
echo   Ohne Aktenzeichen gibt es nichts zu pruefen. Es wurde nichts
echo   geschrieben.
echo.
pause
goto ende


:ende
