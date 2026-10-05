@echo off
chcp 65001 >nul
setlocal
rem Python schreibt Haken und Striche. Ohne diese Zeichentabelle bricht
rem die Ausgabe beim ersten Sonderzeichen ab. Hinter setlocal, damit die
rem Einstellung das Fenster des Nutzers nicht ueberdauert.
set PYTHONUTF8=1
cd /d "%~dp0"
title jusperfect - welche Modelle darf mein Konto?

echo ============================================
echo    Welche Modelle darf dieses AWS-Konto?
echo ============================================
echo.
echo Fragt Ihr Konto direkt. Ruft KEIN Modell auf und kostet nichts.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo   Die Umgebung ist noch nicht eingerichtet.
  echo   Bitte zuerst einmal START-AWS.bat starten.
  echo.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m jusperfect.modelle
echo.
pause
endlocal
