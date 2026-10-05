@echo off
setlocal
cd /d "%~dp0"

rem Die grosse Testakte erzeugen - 50 Dokumente zu je zehn Seiten.
rem
rem Aus der Kanzlei: "Kann man das nicht schon einmal ausprobieren anhand einer
rem Akte mit 50 Dokumenten a 10 Seiten mindestens?"
rem
rem Die Akte wird erzeugt statt mitgeliefert: 880.000 Zeichen Fuelltext gehoeren
rem nicht in ein Programmpaket, und bei fester Saat entsteht jedes Mal dieselbe.

if exist "jusperfect\web.py" goto ordner_ok
echo.
echo   Bitte diese Datei im Programmordner ausfuehren.
echo.
pause
exit /b 1

:ordner_ok
if exist ".venv\Scripts\python.exe" goto umgebung_da
echo.
echo   Die Umgebung fehlt. Bitte zuerst START-DEMO.bat einmal ausfuehren.
echo.
pause
exit /b 1

:umgebung_da
echo.
echo   Die grosse Testakte wird erzeugt ...
echo.
.venv\Scripts\python.exe werkzeug\grosse_testakte.py
echo.
echo   Fertig. So arbeiten Sie damit:
echo.
echo     set JUSPERFECT_FIXTURE_PFAD=testdaten\grosse-akte
echo     START-AWS.bat
echo.
echo   Danach steht in der Aktenliste "44/26 BA". Die Aufloesung liegt in
echo   testdaten\grosse-akte\AUFLOESUNG.md - erst arbeiten, dann nachsehen.
echo.
pause
