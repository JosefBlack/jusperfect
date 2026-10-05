@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title jusperfect - Zugangstest

rem Python schreibt Haken und Striche in die Ausgabe. Geht sie in eine Datei
rem statt auf den Bildschirm, nimmt Python die alte Windows-Zeichentabelle -
rem und bricht beim ersten Sonderzeichen ab, also in der ersten Zeile. Aus der
rem Kanzlei: "Bricht sofort ab - kann ich nicht lesen."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ============================================
echo    jusperfect - AWS-Zugang pruefen
echo ============================================
echo.
echo Geht die Schritte der Reihe nach durch und sagt bei jedem,
echo was zu tun ist. Es geht KEIN Aktentext hinaus.
echo.

if exist ".venv\Scripts\python.exe" goto umgebung_da
echo   Die Umgebung ist noch nicht eingerichtet.
echo.
echo   Bitte zuerst einmal START-DEMO.bat oder START-AWS.bat starten.
echo   Danach diese Datei erneut oeffnen.
echo.
pause
exit /b 1
:umgebung_da

rem Der Befund geht in eine Datei und danach auf den Bildschirm. Wer das
rem Fenster verliert oder den Befund weitergeben will, hat ihn trotzdem.
rem Es steht kein Aktentext darin - nur Zugang, Region und Modellkennung.
set "BERICHT=%~dp0zugangstest.txt"

echo Der Test laeuft - einen Augenblick bitte.
echo.
".venv\Scripts\python.exe" -m jusperfect.awstest > "%BERICHT%" 2>&1
set ERG=%errorlevel%
type "%BERICHT%"

echo.
echo --------------------------------------------
echo   Nachzulesen in:  %BERICHT%
if not "%ERG%"=="0" goto gescheitert
echo   Der Zugang steht.
goto ende

:gescheitert
echo   Der Test ist nicht durchgelaufen - siehe oben.
echo   Die Datei duerfen Sie weitergeben, es steht kein Aktentext darin.

:ende
echo --------------------------------------------
echo.
pause
endlocal
