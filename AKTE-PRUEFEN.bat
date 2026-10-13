@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
title jusperfect - welcher Eintrag dieser Akte laesst sich nicht lesen?

echo ==============================================================
echo    Welcher Eintrag dieser Akte laesst sich nicht lesen?
echo ==============================================================
echo.
echo Diese Probe geht denselben Weg wie das Programm beim Oeffnen
echo einer Akte - aber Eintrag fuer Eintrag, mit einer Zeile je
echo Eintrag. Scheitert einer, steht hier, welcher und woran.
echo.
echo Sie LIEST NUR. Sie schreibt nichts, holt keinen Dokumentinhalt
echo und kostet keinen Modellaufruf und keine Texterkennung. Das
echo Aktengedaechtnis wird nicht einmal gelesen - die Probe muss
echo auch dann arbeiten, wenn gerade es das Problem ist.
echo.
echo In der Ausgabe steht KEIN Akteninhalt: kein Betreff, kein
echo Dateiname, kein Beteiligter. Kennungen stehen verdeckt. Diese
echo Ausgabe laesst sich weitergeben.
echo.

REM Dieselben Angaben wie START-JURNODES.bat - gemessen werden soll ja,
REM was beim Oeffnen geschieht, und nicht etwas Aehnliches.
set JUSPERFECT_BETRIEBSART=lokal
set JUSPERFECT_ANBIETER=bedrock
set JUSPERFECT_AWS_REGION=eu-central-1
set JUSPERFECT_JURNODES_ADAPTER=http
set JUSPERFECT_IDENTITAET=header
set JUSPERFECT_NUTZER_DATEI=nutzer-kanzlei.json
set JUSPERFECT_GEDAECHTNIS=aus

REM Das Gedaechtnis steht hier auf AUS, und zwar mit Absicht: Die Probe
REM liest es ohnehin nicht, und ohne Ablageort braucht sie auch keinen
REM AWS-Zugang. Sie laeuft damit selbst dann, wenn an AWS etwas fehlt.

if defined JUSPERFECT_JURNODES_URL goto zugang_da
echo   Es ist kein jur^|nodes-Zugang hinterlegt. Bitte zuerst
echo   JURNODES-ZUGANG.bat starten, dieses Fenster schliessen und
echo   es neu oeffnen.
echo.
pause
exit /b 1

:zugang_da
call "%~dp0_UMGEBUNG.bat" 2
if errorlevel 1 exit /b 1

"%PY%" -m jusperfect.aktenprobe
echo.
pause
endlocal
