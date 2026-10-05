@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
title jusperfect - ECHTE AKTEN

echo ==================================================
echo    jusperfect - ECHTE AKTEN DER KANZLEI
echo ==================================================
echo.
echo Diese Datei arbeitet mit dem echten Aktenbestand ueber das
echo eingebundene Laufwerk. Fuer die Testakten ist START-AWS.bat da.
echo.

REM ===================================================================
REM   HIER TRAGEN SIE ZWEI DINGE EIN. Ohne sie startet nichts.
REM ===================================================================
REM
REM 1. Der Aktenordner - die Wurzel des jur|nodes-Laufwerks.
REM    Erwartet wird darunter: <Anwalt>\<Jahr>\<Aktenzeichen Bezeichnung>\
REM    Ob Ihr Bestand so gebaut ist, sagt ORDNER-PRUEFEN.bat.
set JUSPERFECT_JURNODES_WEBDAV=

REM 2. Die Kennung des Schutzgelaenders aus der Bedrock-Konsole.
REM    Einrichten nach AWS-EINRICHTEN.md, Schritt 9 - mit den
REM    Inhaltsfiltern AUS. In einer Kanzlei ist Gewalt der Fall, nicht
REM    der Missbrauch. Ob Ihre Filter die Sprache einer Akte
REM    durchlassen, sagt der Modell-Testlauf im Selbsttest.
set JUSPERFECT_GUARDRAIL_ID=

REM ===================================================================

REM --- Ab hier ist nichts mehr einzutragen ---------------------------
set JUSPERFECT_BETRIEBSART=lokal
set JUSPERFECT_ANBIETER=bedrock
set JUSPERFECT_AWS_REGION=eu-central-1
set JUSPERFECT_JURNODES_ADAPTER=webdav
set JUSPERFECT_IDENTITAET=header

REM --- Wer in dieser Kanzlei arbeitet -------------------------------
REM Ohne diese Zeile stuenden auf dem Anmeldebild die erfundenen
REM Testnutzer (RA Dr. Weber und so fort). Mit echten Akten ist das
REM nicht nur unschoen, sondern irrefuehrend: Der Name steht im
REM Verarbeitungsnachweis jedes Modellaufrufs.
set JUSPERFECT_NUTZER_DATEI=nutzer-kanzlei.json

REM Das Aktengedaechtnis liegt IN DER AKTE, als Datei im Aktenordner.
REM Das ist beim Laufwerksweg die saubere Wahl: kein zweiter
REM Aufbewahrungsort, und Sicherung wie Loeschung der Akte erfassen es
REM mit. Ein Gedaechtnis auf dem Rechner ("lokal") ist mit echten Akten
REM nicht zulaessig - das Programm weist es ab, und das ist gewollt.
set JUSPERFECT_GEDAECHTNIS=akte

REM Dieselben Modelle wie im Testbetrieb, gemessen am 17.09.2026.
set JUSPERFECT_MODELL_ID=anthropic.claude-opus-4-6-v1
set JUSPERFECT_MODELL_ID_KLEIN=anthropic.claude-haiku-4-5-20251001-v1:0
set JUSPERFECT_MODELL_GEDAECHTNIS=anthropic.claude-opus-4-6-v1
set JUSPERFECT_MODELL_FRAGE=
set JUSPERFECT_MODELL_ANALYSE=
set JUSPERFECT_MODELL_ENTWURF=
set JUSPERFECT_MODELL_TRIAGE=
set JUSPERFECT_MAX_AUSGABE_TOKENS=16000

if not defined JUSPERFECT_MONATSBUDGET_EUR set JUSPERFECT_MONATSBUDGET_EUR=100

REM --- Die beiden Pflichtangaben pruefen, bevor irgendetwas laeuft ---
rem Ohne diese Pruefung bekaeme der Bearbeiter eine Python-Meldung zu
rem sehen. Sie waere richtig und unbrauchbar.
if not defined JUSPERFECT_JURNODES_WEBDAV goto kein_ordner
if not defined JUSPERFECT_GUARDRAIL_ID goto kein_gelaender
goto angaben_geprueft

:kein_ordner
echo.
echo   Es fehlt der Aktenordner.
echo.
echo   Oeffnen Sie diese Datei mit dem Editor (Rechtsklick - Oeffnen mit)
echo   und tragen Sie hinter "set JUSPERFECT_JURNODES_WEBDAV=" den Pfad
echo   ein, zum Beispiel:
echo.
echo       set JUSPERFECT_JURNODES_WEBDAV=J:\Akten
echo.
echo   Ob der Bestand dort so gebaut ist, wie jusperfect ihn erwartet,
echo   sagt ORDNER-PRUEFEN.bat. Das ist der Schritt davor.
echo.
pause
exit /b 1

:kein_gelaender
echo.
echo   Es fehlt das Schutzgelaender.
echo.
echo   Mit echten Akten startet jusperfect ohne Guardrail nicht. Das ist
echo   keine Huerde, sondern die Sperre, die wir eingebaut haben.
echo.
echo   Einrichten: AWS-EINRICHTEN.md, Schritt 9. Danach die Kennung
echo   hinter "set JUSPERFECT_GUARDRAIL_ID=" eintragen.
echo.
pause
exit /b 1

:angaben_geprueft

REM --- Python und Arbeitsumgebung ------------------------------------
REM Bis zum 28.09.2026 stand hier "Es fehlt die Arbeitsumgebung .venv,
REM bitte zuerst einmal START-AWS.bat ausfuehren" - also erst die
REM erfundenen Testakten starten, um an die echten zu kommen. Genau das
REM hat die Kanzlei am 25.09.2026 bei START-JURNODES.bat beanstandet
REM ("warum muss ich jedes mal eine arbeitsumgebung schaffen bevor ich
REM zum programm will"); dort wurde es behoben, hier blieb es stehen.
REM
REM _UMGEBUNG.bat legt sie selbst an und prueft auch, ob die
REM Programmdateien richtig liegen - ausfuehrlicher, als es hier stand.
call "%~dp0_UMGEBUNG.bat" 2
if errorlevel 1 exit /b 1

echo.
echo   Aktenordner:    %JUSPERFECT_JURNODES_WEBDAV%
echo   Schutzgelaender: %JUSPERFECT_GUARDRAIL_ID%
echo   Modell:         %JUSPERFECT_MODELL_ID%
echo   Gedaechtnis:    in der Akte
echo   Kostenbremse:   %JUSPERFECT_MONATSBUDGET_EUR% EUR im Monat
echo.
set "FASSUNG=unbekannt"
if exist "FASSUNG.txt" for /f "usebackq delims=" %%z in ("FASSUNG.txt") do set "FASSUNG=%%z"
echo   Programmstand:  %FASSUNG%
echo.
echo   ==============================================================
echo   Ab hier geht ECHTER Aktentext an AWS Frankfurt. Weiter mit
echo   einer Taste, Abbruch mit Strg+C.
echo   ==============================================================
pause >nul

echo.
echo   AWS-Zugang pruefen ...
"%PY%" -m jusperfect.awstest
if errorlevel 1 goto kein_zugang

echo.
echo   jusperfect wird gestartet ...
echo   Im Browser: http://127.0.0.1:8765
echo.
REM Der Browser geht erst auf, wenn der Server wirklich antwortet.
REM Vorher stand hier ein "start", das den Browser VOR dem Server
REM oeffnete - die Folge war jedesmal eine Fehlerseite und ein Klick
REM auf Neuladen. Aus der Kanzlei gemeldet am 25.09.2026.
set JUSPERFECT_BROWSER_OEFFNEN=1
"%PY%" -m jusperfect
pause
goto ende

:kein_zugang
echo.
echo   Der Zugangstest ist nicht durchgelaufen - siehe oben. Mit echten
echo   Akten wird hier nicht weitergemacht.
echo.
pause
exit /b 1

:ende
