@echo off
REM ===================================================================
REM   Die Arbeitsumgebung: Python finden, .venv anlegen, Bausteine
REM   installieren. NICHT zum Doppelklicken - die Startdateien rufen
REM   sie auf.
REM
REM   Warum eine eigene Datei: Bis zum 25.09.2026 stand dieser Block
REM   nur in START-AWS.bat. START-JURNODES.bat schickte den Anwender
REM   dorthin ("bitte zuerst einmal START-AWS.bat ausfuehren") - also
REM   erst die Testakten starten, um an die echten zu kommen. Aus der
REM   Kanzlei: "warum muss ich jedes mal eine arbeitsumgebung schaffen
REM   bevor ich zum programm will". Zu Recht.
REM
REM   Kopieren waere das Naheliegende gewesen und das Falsche: Was in
REM   diesem Block steht, ist in Monaten zusammengetragen worden - die
REM   Store-Attrappe von Windows, die falsche Python-Fassung, der
REM   fehlende PATH-Haken. Zwei Kopien laufen auseinander, und dann
REM   hilft der einen Startdatei, was in der anderen laengst steht.
REM
REM   Sie setzt PY auf das Python der Umgebung. Bei einem Fehler
REM   bricht sie mit exit /b 1 ab; der Aufrufer prueft errorlevel.
REM
REM   Erster Parameter: wie viele Schritte der Aufrufer insgesamt hat.
REM   Ohne Angabe vier. START-DEMO.bat hat drei und zaehlte sonst
REM   "[1/4] ... [2/4] ... [3/3]" - eine Zahl, die der Anwender liest.
REM ===================================================================
set "SCHRITTE=%~1"
if not defined SCHRITTE set "SCHRITTE=4"

REM --- Python finden ---------------------------------------------------------
rem jusperfect braucht Python 3.11 oder 3.12. "py -3" nimmt die NEUESTE
rem Installation - auf einem frischen Rechner also 3.13 oder neuer, denn das
rem bietet python.org heute an. Die Einrichtung braeche dann mit einer
rem Meldung ab, die nicht sagt, woran es liegt. Deshalb gezielt fragen.
rem Keine Klammerbloecke hier: cmd loest %VARIABLEN% darin zu frueh auf.
set "PYCMD="
py -3.12 --version >nul 2>&1 && set "PYCMD=py -3.12"
if not defined PYCMD py -3.11 --version >nul 2>&1 && set "PYCMD=py -3.11"
if not defined PYCMD python -c "import sys; sys.exit(0 if (3,11) <= sys.version_info < (3,13) else 1)" >nul 2>&1 && set "PYCMD=python"
if defined PYCMD goto python_gefunden

rem Ab hier steht fest: keine brauchbare Fassung. Drei Faelle, drei Texte -
rem "Python fehlt" waere falsch und teuer, wenn Python laengst da ist.
rem
rem Der dritte Fall ist der gemeinste. Windows legt unter WindowsApps eine
rem Attrappe namens python.exe an, die nichts tut, als auf den Microsoft Store
rem zu verweisen. Sie liegt im Suchpfad und faengt jedes "python" ab - auch dann
rem noch, wenn Python laengst installiert ist, weil die Attrappe im Suchpfad
rem weiter vorn steht. Aus der Kanzlei, 17.09.2026: "er sagt python nicht
rem gefunden", unmittelbar nach einer erfolgreichen Installation. Ohne diese
rem Unterscheidung haette hier gestanden, es sei kein Python installiert.
rem Reihenfolge mit Bedacht: Erst fragen, ob ueberhaupt ein echtes Python
rem antwortet. Die Attrappe antwortet nicht - sie bricht mit einem Fehler ab.
rem Wer zuerst nach WindowsApps suchte, schickte jeden, der Python 3.13 UND
rem die Attrappe hat, an die falsche Stelle.
py -3 --version >nul 2>&1 && goto falsche_fassung
python --version >nul 2>&1 && goto falsche_fassung
where python 2>nul | find /i "WindowsApps" >nul && goto store_attrappe
goto kein_python

:store_attrappe
echo.
echo   Python ist da, aber Windows laesst es nicht durch.
echo.
echo   Im Suchpfad steht eine Attrappe von Windows, die nur auf den
echo   Microsoft Store verweist. Sie faengt jeden Aufruf von "python" ab.
echo.
echo   Abhilfe, eine Minute:
echo     1. Windows-Taste druecken, "App-Ausfuehrungsaliase" tippen, oeffnen
echo        (Einstellungen - Apps - Erweiterte App-Einstellungen -
echo         App-Ausfuehrungsaliase)
echo     2. Die beiden Schalter "python.exe" und "python3.exe" AUSschalten
echo     3. Dieses Fenster schliessen und diese Datei erneut doppelklicken
echo.
echo   Falls dort gar kein "python.exe" steht, war beim Installieren der
echo   Haken "Add python.exe to PATH" nicht gesetzt. Dann den Installer
echo   noch einmal starten, "Modify" waehlen und ihn nachtragen.
echo.
pause
exit /b 1

:falsche_fassung
echo.
echo   Auf diesem Rechner ist Python installiert, aber keine Fassung, mit der
echo   jusperfect laeuft. Gebraucht wird 3.11 oder 3.12.
echo.
echo   Bitte Python 3.12 zusaetzlich installieren. Die vorhandene Fassung
echo   kann bleiben, sie stoert nicht:
echo     https://www.python.org/downloads/release/python-3128/
echo   Im Setup unten "Add python.exe to PATH" ankreuzen.
echo.
start "" https://www.python.org/downloads/release/python-3128/
pause
exit /b 1

:kein_python
echo.
echo   Auf diesem Rechner ist noch kein Python installiert.
echo.
echo   Bitte Python 3.12 installieren:
echo     https://www.python.org/downloads/release/python-3128/
echo   WICHTIG: im Setup ganz unten "Add python.exe to PATH" ankreuzen.
echo   Danach diese Datei erneut doppelklicken.
echo.
start "" https://www.python.org/downloads/release/python-3128/
pause
exit /b 1

:python_gefunden

REM --- Umgebung anlegen (nur beim ersten Mal) --------------------------------
set "ERSTMALS="
if not exist ".venv\Scripts\python.exe" (
  echo [1/%SCHRITTE%] Einmalige Einrichtung ...
  set "ERSTMALS=ja"
  %PYCMD% -m venv .venv || (echo Die Umgebung liess sich nicht anlegen. & pause & exit /b 1)
)
set "PY=.venv\Scripts\python.exe"

REM Beim ersten Mal werden hier rund dreissig Pakete heruntergeladen. Das
REM dauert Minuten, und alle drei Aufrufe sind stumm gestellt - auf dem Schirm
REM steht dann unveraendert "Bausteine pruefen ...".
REM
REM Aus der Kanzlei am 01.10.2026: "Bausteine pruefen hakt das Programm beim
REM ersten Start." Es hakte nicht, es arbeitete. Eine Arbeit, die Minuten
REM braucht und kein Lebenszeichen gibt, ist von einem Stillstand nicht zu
REM unterscheiden - und wer abbricht, faengt beim naechsten Mal von vorn an.
echo [2/%SCHRITTE%] Bausteine pruefen ...
if defined ERSTMALS echo.
if defined ERSTMALS echo     Beim ersten Mal werden sie heruntergeladen - das dauert
if defined ERSTMALS echo     einige Minuten. Solange steht hier nichts Neues; das
if defined ERSTMALS echo     Fenster haengt nicht, es arbeitet. Bitte nicht schliessen.
if defined ERSTMALS echo.
"%PY%" -m pip install --quiet --upgrade pip >nul 2>&1
"%PY%" -m pip install --quiet -e . >nul 2>&1 || (echo Die Bausteine liessen sich nicht installieren. & pause & exit /b 1)
"%PY%" -m pip install --quiet boto3 >nul 2>&1

REM --- Liegen die Programmdateien richtig? ------------------------------------
REM Diese Pruefung hat in der Kanzlei einen halben Nachmittag gekostet, bevor
REM es sie gab: Beim Auspacken war der INNERE Ordner "jusperfect" genommen
REM worden statt des aeusseren. Dann liegt web.py neben der Startdatei statt in
REM einem Unterordner - pip laeuft anscheinend durch, installiert aber nichts
REM Brauchbares, und der Fehler zeigt sich erst zwei Schritte spaeter als
REM "No module named 'jusperfect'". Wer das liest, sucht an der falschen Stelle.
REM
REM Sie stand am 28.09.2026 in DREI Startdateien, und eine der drei Fassungen
REM war schon schwaecher: START-JURNODES.bat sagte nur "ein Unterordner muss
REM hier liegen" und unterschied nicht, ob web.py daneben liegt - also den
REM einen Fall, in dem man dem Anwender genau sagen kann, was er falsch
REM gemacht hat. Genau so laufen Kopien auseinander: nicht durch eine falsche
REM Zeile, sondern dadurch, dass eine Verbesserung nur an einer Stelle ankommt.
REM
REM Ohne Klammernbloecke geschrieben: cmd wertet darin frueher aus, als man
REM denkt - das hat an anderer Stelle schon einmal Zeit gekostet.
"%PY%" -c "import jusperfect" >nul 2>&1
if not errorlevel 1 goto aufbau_geprueft
echo.
echo   Die Programmdateien liegen nicht dort, wo sie liegen muessen.
echo.
echo   In diesem Ordner muessen die Startdatei UND ein Unterordner namens
echo   "jusperfect" nebeneinander liegen:
echo.
echo       START-DEMO.bat  - oder eine andere Startdatei
echo       pyproject.toml
echo       jusperfect\          ^<-- dieser Ordner
echo           web.py, config.py, static\ ...
echo.
if not exist "web.py" goto aufbau_fehlt
echo   Hier liegt web.py unmittelbar neben der Startdatei - der Unterordner
echo   fehlt. Beim Auspacken wurde der innere Ordner genommen statt des
echo   aeusseren: Im ZIP stecken zwei gleichnamige ineinander. Gebraucht wird
echo   der, in dem die Startdateien liegen.
goto aufbau_abhilfe
:aufbau_fehlt
echo   Der Unterordner "jusperfect" fehlt oder ist unvollstaendig.
:aufbau_abhilfe
echo.
echo   Abhilfe: diesen Ordner umbenennen, das ZIP neu auspacken und den
echo   Ordner nehmen, in dem die Startdateien liegen.
echo.
pause
exit /b 1
:aufbau_geprueft
