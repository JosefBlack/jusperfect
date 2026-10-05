@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
title jusperfect - nimmt der S3-Bucket das Aktengedaechtnis an?

echo ============================================
echo    Nimmt der S3-Bucket das Aktengedaechtnis an?
echo ============================================
echo.
echo ACHTUNG: Diese Probe SCHREIBT. Fast alle anderen lesen nur.
echo.
echo Sie legt ein Aktengedaechtnis zu einer ERFUNDENEN Akte ab - darin
echo steht ein Satz mit Datum und Zweck. Kein Akteninhalt, kein
echo Mandantenname. Danach liest sie es zurueck, vergleicht es Zeichen
echo fuer Zeichen und entfernt es wieder.
echo.
echo Warum sie schreibt: Der Selbsttest sagt, dass ein Bucket hinterlegt
echo ist. Ob er das Ablegen annimmt, in Frankfurt liegt und den
echo Kanzleischluessel akzeptiert, sagt nur ein echter Versuch. Ohne ihn
echo fiele das Fehlen erst auf, wenn eine Akte geschlossen wird und das
echo Gedaechtnis sich nicht sichern laesst - beim teuersten Zeitpunkt,
echo denn dann ist die Arbeit getan und waere verloren.
echo.
echo Es wird KEIN Modell aufgerufen. Die Probe kostet nichts ausser
echo Bruchteilen eines Cents fuer die S3-Anfragen.
echo.
echo Weiter mit einer Taste, Abbruch mit Strg+C.
pause >nul

call "%~dp0_UMGEBUNG.bat" 2
if errorlevel 1 exit /b 1

REM --- Die zwei Werte fragt die Probe selbst ---------------------------
REM
REM Sie standen zuerst nicht hier, und das war ein Fehler: Die Probe las
REM nur, was im Windows-Konto steht. Dort steht das Gedaechtnis auf "aus",
REM also haette sie abgebrochen mit "gilt nur fuer die Ablage in AWS" -
REM und der Anwender haette die Einrichtung umsonst gemacht.
REM
REM Fragen statt voraussetzen hat noch einen Vorteil: Die Probe laeuft,
REM BEVOR die Startdatei geaendert wird. Wer erst eintraegt und dann
REM prueft, hat im Fehlerfall zwei Baustellen statt einer.
echo.
echo   Zwei Angaben aus der AWS-Konsole:
echo.
echo     der Name des Buckets      (S3, Region Frankfurt)
echo     die Schluessel-ID         (KMS, Ihr Schluessel, "Allgemeine
echo                                Konfiguration", die Folge mit
echo                                Bindestrichen - NICHT die ARN)
echo.
set "BUCKET="
set /p BUCKET=Bucketname: 
set "KMSID="
set /p KMSID=Schluessel-ID: 

if not defined BUCKET goto keineangabe
if not defined KMSID goto keineangabe

REM Nur fuer dieses Fenster. Es wird nichts dauerhaft hinterlegt und
REM nichts in eine Datei geschrieben - die Probe soll nichts einrichten.
set JUSPERFECT_GEDAECHTNIS=aws
set "JUSPERFECT_GEDAECHTNIS_BUCKET=%BUCKET%"
set "JUSPERFECT_KMS_SCHLUESSEL_ID=%KMSID%"
if not defined JUSPERFECT_AWS_REGION set JUSPERFECT_AWS_REGION=eu-central-1
REM Die Probe ruft kein Modell auf; der Anbieter steht nur da, damit die
REM Einstellungen ohne Guardrail-Kennung durchgehen.
set JUSPERFECT_ANBIETER=demo
set JUSPERFECT_BETRIEBSART=lokal
set JUSPERFECT_JURNODES_ADAPTER=fixture
if not defined JUSPERFECT_FIXTURE_PFAD set JUSPERFECT_FIXTURE_PFAD=testdaten\akten
if not defined JUSPERFECT_NUTZER_DATEI set JUSPERFECT_NUTZER_DATEI=testdaten\nutzer.json

echo.
"%PY%" werkzeug\gedaechtnis_aws_probe.py
set ERG=%errorlevel%
echo.
if %ERG%==0 echo Die Ablage arbeitet. Das Aktengedaechtnis kann eingeschaltet werden.
if %ERG%==2 echo Es ist nichts geprueft worden - siehe die Erklaerung darueber.
if %ERG%==1 echo Die Probe ist gescheitert. Bitte die Meldung darueber weitergeben.
echo.
echo Zum Schliessen eine Taste druecken.
pause >nul
goto ende

:keineangabe
echo.
echo   Es fehlt eine der beiden Angaben - es wurde nichts geprueft.
echo.
echo   Beide stehen in der AWS-Konsole:
echo     S3  -^> Ihr Bucket -^> der Name steht in der Liste
echo     KMS -^> Customer managed keys -^> Ihr Schluessel -^>
echo            "Allgemeine Konfiguration" -^> Schluessel-ID
echo.
pause

:ende
endlocal
