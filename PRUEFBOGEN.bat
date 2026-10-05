@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem Ein echter Lauf ueber die grosse Testakte 44/26 BA, gemessen an der
rem Aufloesung. Sagt, welcher der fuenf eingebauten Funde benannt wurde,
rem mit welchen Fundstellen - und welcher nicht.
rem
rem Wichtig: Der Bogen misst die Guete der Antworten. Dafuer braucht es ein
rem echtes Modell. Ohne gesetzten Anbieter laeuft er mit dem Demo-Anbieter
rem durch und findet nichts; das sagt er dann auch ausdruecklich.

if not exist ".venv\Scripts\python.exe" goto keinevenv

if not defined JUSPERFECT_ANBIETER set JUSPERFECT_ANBIETER=bedrock
if not defined JUSPERFECT_BETRIEBSART set JUSPERFECT_BETRIEBSART=lokal
if not defined AWS_REGION set AWS_REGION=eu-central-1

REM --- Welches Modell gemessen wird -----------------------------------------
REM
REM Diese Zeilen setzen unbedingt, nicht "if not defined". Das ist Absicht.
REM
REM Am 16.09.2026 lief der Bogen in der Kanzlei mit Sonnet 4.5, obwohl
REM START-AWS.bat Opus 4.6 einstellt. Die Ursache: Diese Datei setzte gar kein
REM Modell und uebernahm damit eine dauerhafte Windows-Einstellung (setx) aus
REM einer frueheren Einrichtung. Im Bogen stand dann zwar die richtige
REM Kennung - aber wer sie nicht eigens nachliest, haelt das Ergebnis fuer das
REM des Modells, das er eingestellt zu haben glaubt.
REM
REM Ein Messgeraet darf nicht davon abhaengen, was jemand vor Monaten einmal
REM gesetzt hat. Hier steht deshalb dieselbe Einstellung wie in START-AWS.bat:
REM gemessen wird, womit die Kanzlei arbeitet.
REM Die Kennungen stammen aus MODELLE-ANZEIGEN.bat, abgefragt am 16.09.2026.
REM Sie sind nicht nach einem Muster gebaut: Opus 4.6 traegt "-v1" ohne Datum,
REM Haiku 4.5 Datum und Fassung. Hier stand einmal eine abgekuerzte Fassung,
REM aus dem Anzeigenamen im AWS-Katalog abgeleitet - AWS hat den Lauf
REM abgewiesen. Eine Kennung wird abgefragt, nicht hergeleitet.
set JUSPERFECT_MODELL_ID=anthropic.claude-opus-4-6-v1
set JUSPERFECT_MODELL_ID_KLEIN=anthropic.claude-haiku-4-5-20251001-v1:0

REM Und jetzt die vier uebrigen ausdruecklich leeren. Das ist keine
REM Umstaendlichkeit, sondern die Lehre aus dem Lauf vom 17.09.2026, 12:32 Uhr:
REM Im Kopf stand "Modell: anthropic.claude-opus-4-6-v1" - gemessen hat der
REM Bogen mit Opus 4.5. Ursache war ein dauerhaftes
REM JUSPERFECT_MODELL_ANALYSE aus einer frueheren Einrichtung.
REM
REM Diese Datei setzte nur zwei der sechs Modelleinstellungen und ueberliess
REM vier dem Zufall. Der Anspruch darueber - ein Messgeraet darf nicht davon
REM abhaengen, was jemand vor Monaten einmal gesetzt hat - war damit zur
REM Haelfte unerfuellt. Leer heisst: nimmt die Zeile darueber.
set JUSPERFECT_MODELL_FRAGE=
set JUSPERFECT_MODELL_ANALYSE=
set JUSPERFECT_MODELL_ENTWURF=
set JUSPERFECT_MODELL_TRIAGE=

REM Das Aktengedaechtnis liest die fuenfzig Dokumente ein, und die Analyse
REM arbeitet danach nur noch mit dem, was dabei herauskam. Was hier
REM verlorengeht, findet spaeter niemand mehr - darum steht hier dasselbe
REM Modell wie in START-AWS.bat, START-JURNODES.bat und START-KANZLEI.bat.
REM
REM Bis zum 28.09.2026 war diese Zeile leer, der Bogen fiel auf das kleine
REM Modell zurueck und las mit Haiku ein, wo die Kanzlei mit Opus liest. Der
REM Anspruch drei Absaetze weiter oben - "gemessen wird, womit die Kanzlei
REM arbeitet" - war damit unerfuellt, und zwar an der teuersten Stelle: Der
REM Lauf vom 28.09.2026 verlor die 402,00 m2 Daemmflaeche aus D-002, genau
REM wie der Haiku-Lauf vom 17.09.2026. Eine Probe, die anders fragt als der
REM Betrieb, prueft etwas anderes als den Betrieb.
REM
REM tests/test_starter.py haelt die vier Dateien jetzt gegeneinander.
set JUSPERFECT_MODELL_GEDAECHTNIS=anthropic.claude-opus-4-6-v1

REM Zum Vergleichen, was ein schwaecheres Modell an dieser Stelle kostet:
REM bei der naechsten Zeile das REM wegnehmen und den Bogen ein zweites Mal
REM laufen lassen. Gemessen am 17.09.2026: 3 von 5 Funden statt 5, und die
REM Urkunden fehlten - dafuer 0,51 EUR statt 2,56 EUR beim Einlesen.
REM set JUSPERFECT_MODELL_GEDAECHTNIS=anthropic.claude-haiku-4-5-20251001-v1:0

REM --- Wie lang die Antwort werden darf ------------------------------------
REM Auch das gehoert zum Messgeraet und nicht in die Windows-Einstellungen.
REM Die Analyse ueber fuenfzig Dokumente brauchte in zwei gemessenen Laeufen
REM 6.753 und 7.777 Ausgabetoken; beim dritten war die frueher eingestellte
REM Grenze von 8.000 ueberschritten, die Antwort brach mitten im JSON ab, und
REM das bezahlte Einlesen davor war verloren.
set JUSPERFECT_MAX_AUSGABE_TOKENS=16000

REM --- Welcher Programmstand liegt hier? ------------------------------------
REM FASSUNG.txt traegt Nummer und Datum der Aenderung; beim Auspacken einer ZIP
REM setzt Git sie ein. Am 16.09.2026 lief in der Kanzlei ein Ordner, in dem der
REM Programmteil neu und die Startdateien alt waren - von aussen sah das aus wie
REM ein Fehler im Programm. Diese Zeile haette es in einem Blick gezeigt.
set "FASSUNG=unbekannt - vor dem 17.09.2026 ausgepackt"
if exist "FASSUNG.txt" for /f "usebackq delims=" %%z in ("FASSUNG.txt") do set "FASSUNG=%%z"

echo.
echo   Anbieter: %JUSPERFECT_ANBIETER%   Region: %AWS_REGION%
echo   Programmstand: %FASSUNG%
echo   Modell:   %JUSPERFECT_MODELL_ID%
echo   Gedaechtnis und Eingangspruefung: %JUSPERFECT_MODELL_ID_KLEIN%
if defined JUSPERFECT_MODELL_GEDAECHTNIS echo   Gedaechtnis abweichend: %JUSPERFECT_MODELL_GEDAECHTNIS%
echo.
echo   Der Lauf liest fuenfzig Dokumente abschnittsweise ein - rund 882.000
echo   Zeichen - und analysiert danach ueber das Aktengedaechtnis. Das dauert
echo   einige Minuten.
echo.
echo   Kosten: Das Einlesen traegt die ganze Akte und ist der groessere Posten;
echo   er haengt am kleinen Modell. Die Analyse traegt nur die Zusammenfassung.
echo   Groessenordnung mit Haiku beim Einlesen: unter einem Euro. Laesst man
echo   Opus einlesen (die Zeile oben), das Mehrfache davon. Der Bogen weist
echo   beide Posten am Ende getrennt aus - dann wissen Sie es genau.
echo.
REM -- Das Aktengedaechtnis aufheben und wiederbenutzen ----------------------
REM
REM Am 28.09.2026 kostete jeder Versuch an der Chronologie-Regel 3,04 EUR,
REM davon 2,73 EUR fuer das Einlesen - und das Einlesen war an der Frage
REM unbeteiligt. Vier Laeufe, zwoelf Euro, und die eigentliche Frage blieb
REM offen, weil niemand in das Gedaechtnis hineinsehen konnte.
REM
REM Es bleibt jetzt im Ordner pruefbogen-gedaechtnis liegen. Ist eines da,
REM fragt die Datei, ob es wiederbenutzt wird.
set "GORDNER=pruefbogen-gedaechtnis"
set "WEITER=--gedaechtnis %GORDNER%"
if not exist "%GORDNER%\*.json*" goto vollerlauf

echo   ------------------------------------------------------------------
echo   Im Ordner %GORDNER% liegt ein Aktengedaechtnis von einem
echo   fruehen Lauf. Sie haben die Wahl:
echo.
echo     [1] Wiederverwenden - nur die Analyse laufen lassen.
echo         Rund 0,31 EUR, etwa eine Minute. Gemessen wird dann NUR die
echo         Analyse, nicht das Einlesen.
echo.
echo     [2] Neu einlesen - der volle Lauf.
echo         Rund 3,04 EUR mit Opus, einige Minuten. Das vorhandene
echo         Gedaechtnis wird dabei ueberschrieben.
echo   ------------------------------------------------------------------
echo.
set "WAHL="
set /p WAHL=Ihre Wahl (1 oder 2): 
if "%WAHL%"=="1" goto nuranalyse
if "%WAHL%"=="2" goto vollerlauf
echo.
echo   Das war weder 1 noch 2 - es wird nichts getan.
pause
goto ende

:nuranalyse
set "WEITER=--gedaechtnis %GORDNER% --nur-analyse"
echo.
echo   Gut - nur die Analyse. Das Einlesen wird uebersprungen.
goto starten

:vollerlauf
echo.
echo   Der volle Lauf. Das Gedaechtnis bleibt danach in %GORDNER%
echo   liegen, damit der naechste Versuch Centbetraege kostet.

:starten
echo.
echo   Weiter mit einer Taste, Abbruch mit Strg+C.
pause >nul

.venv\Scripts\python.exe werkzeug\pruefbogen.py --speichern pruefbogen %WEITER%
set ERG=%errorlevel%
echo.
REM Drei Faelle, nicht zwei. Bis zum 28.09.2026 endete auch ein Abbruch
REM mit 1, und dann stand hier "Nicht alle Funde wurden benannt - der
REM Bogen sagt, welche" samt Verweis auf einen Ordner, den es nicht gab:
REM Es gab keinen Bogen, der Lauf war gar nicht gelaufen.
if %ERG%==3 goto abgebrochen
if %ERG%==0 echo Alle fuenf Funde wurden benannt und belegt.
if not %ERG%==0 echo Nicht alle Funde wurden benannt - der Bogen sagt, welche.
echo.
if exist "pruefbogen\*.txt" echo Der Bogen liegt zusaetzlich im Ordner pruefbogen.
goto schluss

:abgebrochen
echo Der Lauf ist abgebrochen - es gibt keinen Bogen. Was oben steht,
echo sagt, woran es lag.

:schluss
echo Zum Schliessen eine Taste druecken.
pause >nul
goto ende

:keinevenv
echo Es fehlt die Arbeitsumgebung .venv. Bitte zuerst START-DEMO.bat ausfuehren.
pause

:ende
