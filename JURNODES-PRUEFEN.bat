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

rem Die Beschreibung der Schnittstelle, falls sie als Datei vorliegt.
rem
rem Aus der Kanzlei am 05.10.2026: "Die Korrespondenz bei jurnodes und die
rem Vermerke finden sich in der E-Akte." Damit ist es EINE Frage und nicht
rem zwei - wer den Weg in die E-Akte kennt, hat beides.
rem
rem Der Server gibt seine Beschreibung nicht heraus (36 Pfade geprueft, alle
rem 404). Die Kanzlei hat sie aber: Am 23.09.2026 wurde die
rem OpenAPI-Beschreibung des Servers schon einmal geliefert, und daraus sind
rem die Pfade abgeschrieben, mit denen das Programm heute arbeitet.
rem
rem Liegt diese Datei noch irgendwo, beantwortet sie die Frage in einem Lauf.
rem Hier den vollstaendigen Pfad eintragen, etwa C:\Temp\jurnodes-api.json -
rem oder leer lassen, dann wird nur die Schnittstelle gefragt.
set "BESCHREIBUNG="
set /p BESCHREIBUNG=Datei mit der Schnittstellenbeschreibung (leer lassen geht auch): 

echo.
set "ZUSATZ="
if defined BESCHREIBUNG set "ZUSATZ=--beschreibung "%BESCHREIBUNG%""
if defined AKTE goto mitakte
rem Das Programm schreibt selbst mit - auf den Schirm UND in die Datei.
rem Eine Umleitung mit ">" liesse den Schirm still und ginge an einem
rem offenen Editor zugrunde; beides ist am 23.09.2026 passiert.
"%PY%" -m jusperfect.jurnodestest %ZUSATZ%
goto fertig
:mitakte
"%PY%" -m jusperfect.jurnodestest --akte "%AKTE%" %ZUSATZ%

:fertig
echo.
echo Diese Datei koennen Sie weitergeben - es steht kein Akteninhalt darin.
echo.
pause
goto ende


:ende
