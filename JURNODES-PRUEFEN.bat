@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
title jusperfect - antwortet jur^|nodes?

echo ============================================
echo    Antwortet die jur^|nodes-Schnittstelle?
echo ============================================
echo.
echo Dieses Programm LIEST NUR. Es schreibt nichts, legt nichts an
echo und loescht nichts. In der Ausgabe stehen Feldnamen und Anzahl,
echo kein Akteninhalt - sie laesst sich weitergeben.
echo.
echo Gebraucht werden zwei Angaben vom jur^|nodes-Server der Kanzlei:
echo   die Adresse     in JUSPERFECT_JURNODES_URL
echo   der Benutzer    in JURNODES_API_USER
echo   der Schluessel  in JURNODES_API_KEY
echo.

set "FASSUNG=unbekannt - vor dem 17.09.2026 ausgepackt"
if exist "FASSUNG.txt" for /f "usebackq delims=" %%z in ("FASSUNG.txt") do set "FASSUNG=%%z"
echo Programmstand: %FASSUNG%
echo.

REM Die Arbeitsumgebung anlegen, falls sie fehlt - dieselbe Datei,
REM die auch die Startdateien dafuer aufrufen.
call "%~dp0_UMGEBUNG.bat" 2
if errorlevel 1 exit /b 1

rem Ein Aktenzeichen als Beispiel macht die Probe erst vollstaendig: Ohne
rem eines wird nur die Aktensuche gefragt, mit einem auch Akte, Dokumente,
rem Beteiligte und Fristen. Es steht nur in der eigenen Ausgabe.
set "AKTE="
set /p AKTE=Aktenzeichen fuer die Probe (leer lassen geht auch): 

echo.
if defined AKTE goto mitakte
rem Das Programm schreibt selbst mit - auf den Schirm UND in die Datei.
rem Eine Umleitung mit ">" liesse den Schirm still und ginge an einem
rem offenen Editor zugrunde; beides ist am 23.09.2026 passiert.
"%PY%" -m jusperfect.jurnodestest
goto fertig
:mitakte
"%PY%" -m jusperfect.jurnodestest --akte "%AKTE%"

:fertig
echo.
echo Diese Datei koennen Sie weitergeben - es steht kein Akteninhalt darin.
echo.
pause
goto ende


:ende
