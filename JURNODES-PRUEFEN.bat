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
echo.
echo --- FRAGE 1 von 2 -------------------------------------------
echo Welche Akte soll geprueft werden? Zum Beispiel  X-100-2026
echo Leer lassen geht auch - dann wird nur die Schnittstelle gefragt.
echo.
set "AKTE="
set /p AKTE=Aktenzeichen: 

rem Die Beschreibung der Schnittstelle.
rem
rem Sie liegt seit dem 05.10.2026 IM PROGRAMMORDNER - die Kanzlei hat sie an
rem diesem Tag geliefert (jur|nodes API 1.0.2, 85 Pfade). Es muss also nichts
rem mehr eingetragen werden; die Probe nimmt sie von selbst.
rem
rem Gefragt wird nur noch, wenn die Datei fehlt - oder wenn jemand bewusst
rem eine andere nehmen will, etwa eine neuere Fassung vom Hersteller.
set "BESCHREIBUNG=%~dp0schnittstelle\jurnodes-api-1.0.2.json"
if exist "%BESCHREIBUNG%" goto beschreibung_da

echo Die Beschreibung der Schnittstelle liegt nicht im Programmordner.
echo Erwartet unter: schnittstelle\jurnodes-api-1.0.2.json
echo.
set "BESCHREIBUNG="
set /p BESCHREIBUNG=Pfad zu einer Beschreibung (leer lassen geht auch): 
goto beschreibung_fertig

:beschreibung_da
echo.
echo --- FRAGE 2 von 2 -------------------------------------------
echo Die Beschreibung der Schnittstelle liegt schon bereit:
echo    schnittstelle\jurnodes-api-1.0.2.json
echo.
echo HIER GEHOERT KEIN AKTENZEICHEN HIN. Diese Zeile will einen
echo DATEIPFAD - und fast immer ist die Antwort: einfach Eingabe
echo druecken. Nur wer eine neuere Beschreibung bekommen hat,
echo traegt hier deren Pfad ein.
echo.
set /p BESCHREIBUNG=Andere Datei (einfach Eingabe = die obige nehmen): 
if not defined BESCHREIBUNG set "BESCHREIBUNG=%~dp0schnittstelle\jurnodes-api-1.0.2.json"

:beschreibung_fertig
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
