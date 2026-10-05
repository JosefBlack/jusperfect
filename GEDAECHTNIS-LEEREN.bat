@echo off
setlocal
cd /d "%~dp0"
title jusperfect - Aktengedaechtnis leeren

echo ============================================
echo    Aktengedaechtnis der Testakten leeren
echo ============================================
echo.
echo Der Ordner .jusperfect-gedaechtnis beginnt mit einem Punkt und ist im
echo Windows-Explorer deshalb ausgeblendet. Diese Datei loescht ihn fuer Sie.
echo.
echo Danach faengt jede Testakte wieder bei null an: keine gespeicherten
echo Dokumentauszuege, keine frueheren Fragen, keine Chronologie. Das ist
echo genau das, was man fuer einen sauberen zweiten Durchgang braucht.
echo.

if not exist ".jusperfect-gedaechtnis" (
  echo Es ist nichts da - der Ordner existiert nicht.
  echo.
  pause
  exit /b 0
)

for /f %%N in ('dir /b ".jusperfect-gedaechtnis\*.json" 2^>nul ^| find /c /v ""') do set ANZAHL=%%N
echo Gespeicherte Akten: %ANZAHL%
echo.

REM Sicherheitsnetz: Diese Datei darf niemals echte Mandantenakten treffen.
REM Das kann sie auch nicht - das Programm laesst das lokale Gedaechtnis nur
REM mit den Testakten zu -, aber die Nachfrage bleibt trotzdem stehen.
set /p ANTWORT="Wirklich loeschen? (j/n): "
if /i not "%ANTWORT%"=="j" (
  echo.
  echo Abgebrochen. Es wurde nichts geloescht.
  echo.
  pause
  exit /b 0
)

rmdir /s /q ".jusperfect-gedaechtnis"
if exist ".jusperfect-gedaechtnis" (
  echo.
  echo Der Ordner liess sich nicht loeschen. Laeuft jusperfect noch?
  echo Bitte das schwarze Serverfenster schliessen und es erneut versuchen.
  echo.
  pause
  exit /b 1
)

echo.
echo Geleert. Beim naechsten Start ist alles wieder wie beim ersten Mal.
echo.
pause
endlocal
