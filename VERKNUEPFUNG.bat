@echo off
setlocal
cd /d "%~dp0"

rem Zwei Verknuepfungen auf dem Schreibtisch, mit Symbol.
rem
rem Aus der Kanzlei: "Eine Verknuepfung fuer den Desktop kann ich auch noch
rem nicht herstellen oder?" Doch - Perfect Shield hat so etwas schon, und
rem beide Programme sollen sich gleich anfuehlen.
rem
rem Eine Batchdatei sieht auf dem Schreibtisch aus wie ein Zahnrad und ist von
rem der naechsten nicht zu unterscheiden. Diese Verknuepfungen zeigen auf
rem dieselben Dateien, tragen aber das Programmsymbol und einen Namen, der
rem sagt, was passiert.
rem
rem Zwei, nicht eine: Der Unterschied zwischen "kostet Geld und ruft das
rem Modell" und "kostet nichts" ist zu wichtig, um hinter einem Symbol zu
rem verschwinden.
rem
rem Ohne Klammernbloecke geschrieben - cmd wertet darin frueher aus, als man
rem denkt.

set "ORDNER=%CD%"
set "SYMBOL=%ORDNER%\jusperfect\static\jusperfect.ico"

if exist "%ORDNER%\START-AWS.bat" goto gefunden
echo.
echo   START-AWS.bat wurde nicht gefunden.
echo   Bitte diese Datei im Programmordner ausfuehren - dort, wo auch
echo   START-AWS.bat und START-DEMO.bat liegen.
echo.
pause
exit /b 1

:gefunden
echo.
if exist "%SYMBOL%" goto symbol_da
echo.
echo   Das Programmsymbol fehlt:
echo     %SYMBOL%
echo.
echo   Die Verknuepfungen bekommen dann kein Bild. Genau dieser Fall ist in
echo   der Kanzlei aufgetreten: Aus dem ZIP war nur diese eine Datei kopiert
echo   worden, nicht der ganze Inhalt - und das Symbol liegt im Unterordner
echo   jusperfect\static\.
echo.
echo   Abhilfe: den GESAMTEN Inhalt des Ordners "jusperfect-programm" aus dem
echo   ZIP hierher kopieren, ueberschreiben lassen, und diese Datei erneut
echo   ausfuehren.
echo.
choice /C JN /M "Trotzdem jetzt anlegen, ohne Bild"
if errorlevel 2 exit /b 1

:symbol_da
echo.
echo   Verknuepfungen werden angelegt ...
echo.

call :verknuepfen "jusperfect" "START-AWS.bat" "jusperfect starten - echtes Sprachmodell bei AWS, Kosten je Aufruf"
call :verknuepfen "jusperfect (Demo, ohne KI)" "START-DEMO.bat" "jusperfect zum Ausprobieren - erfundene Akten, kein Modell, keine Kosten"

echo.
echo   Fertig. Wenn etwas fehlt, geht es auch von Hand:
echo   Rechtsklick auf START-AWS.bat, "Senden an" - "Desktop".
echo   Das Symbol liegt hier: %SYMBOL%
echo.
pause
exit /b 0

:verknuepfen
rem %1 Name  %2 Zieldatei  %3 Beschreibung
rem
rem Die Werte kommen mit %~1 ohne Anfuehrungszeichen an und werden hier in
rem einfache gesetzt. Mit %1 samt seinen doppelten ging es schief: cmd setzt
rem sie mitten in die schon doppelt gequotete PowerShell-Zeile ein, die
rem Klammerung bricht auf, und PowerShell sieht statt Text ein nacktes Wort -
rem "Die Benennung jusperfect wurde nicht als Name eines Cmdlet erkannt".
rem Einfache Anfuehrungszeichen vertragen ausserdem Klammern und Kommata,
rem wie sie im Namen "jusperfect (Demo, ohne KI)" vorkommen.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$schreibtisch = [Environment]::GetFolderPath('Desktop');" ^
  "$pfad = Join-Path $schreibtisch '%~1.lnk';" ^
  "$v = (New-Object -ComObject WScript.Shell).CreateShortcut($pfad);" ^
  "$v.TargetPath = Join-Path '%ORDNER%' '%~2';" ^
  "$v.WorkingDirectory = '%ORDNER%';" ^
  "if (Test-Path '%SYMBOL%') { $v.IconLocation = '%SYMBOL%,0' };" ^
  "$v.Description = '%~3';" ^
  "$v.Save();" ^
  "Write-Host ('   angelegt: ' + $pfad)"
exit /b 0
