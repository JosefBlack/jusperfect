@echo off
chcp 65001 >nul
setlocal
rem Python schreibt Haken und Striche. Ohne diese Zeichentabelle bricht
rem die Ausgabe beim ersten Sonderzeichen ab. Hinter setlocal, damit die
rem Einstellung das Fenster des Nutzers nicht ueberdauert.
set PYTHONUTF8=1
cd /d "%~dp0"
title jusperfect - AWS-Zugangsdaten hinterlegen

echo ============================================
echo    AWS-Zugangsdaten hinterlegen
echo ============================================
echo.
echo Die AWS CLI wird dafuer NICHT gebraucht. Diese Datei schreibt
echo dasselbe, was "aws configure" geschrieben haette.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo   Die Umgebung ist noch nicht eingerichtet.
  echo.
  echo   Bitte zuerst einmal START-DEMO.bat oder START-AWS.bat starten.
  echo   Danach diese Datei erneut oeffnen.
  echo.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m jusperfect.zugang
if errorlevel 1 (
  echo.
  echo   Es wurde nichts hinterlegt.
  echo.
)
pause
endlocal
