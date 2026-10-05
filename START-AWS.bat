@echo off
chcp 65001 >nul
setlocal
rem Python schreibt Haken und Striche. Ohne diese Zeichentabelle bricht
rem die Ausgabe beim ersten Sonderzeichen ab. Hinter setlocal, damit die
rem Einstellung das Fenster des Nutzers nicht ueberdauert.
set PYTHONUTF8=1
cd /d "%~dp0"
title jusperfect - AWS (Testakten)

echo ============================================
echo    jusperfect - AWS-Betrieb
echo    Echtes Modell, ERFUNDENE Testakten
echo ============================================
echo.
echo Diese Datei arbeitet mit dem echten Sprachmodell bei AWS -
echo aber ausschliesslich mit den beiliegenden erfundenen Akten.
echo Es gehen KEINE Mandantendaten hinaus.
echo.

REM --- Arbeitsumgebung: Python, .venv, Bausteine ----------------------------
REM Steht in _UMGEBUNG.bat, damit beide Startdateien dasselbe tun.
call "%~dp0_UMGEBUNG.bat" 4
if errorlevel 1 exit /b 1

REM Die Pruefung, ob die Programmdateien richtig liegen, steht seit dem
REM 28.09.2026 in _UMGEBUNG.bat - sie stand in drei Startdateien, und eine
REM der drei Fassungen war schon schwaecher.


REM --- Betriebsart: echtes Modell, erfundene Akten ---------------------------
set JUSPERFECT_BETRIEBSART=lokal
set JUSPERFECT_ANBIETER=bedrock
set JUSPERFECT_AWS_REGION=eu-central-1
set JUSPERFECT_JURNODES_ADAPTER=fixture

REM --- Das Schutzgelaender (bei den Testakten freiwillig) ------------------
REM
REM Mit den erfundenen Testakten laeuft jusperfect ohne. Sobald der
REM Aktenadapter auf einen echten Ordner zeigt, startet es ohne Guardrail
REM nicht mehr - das ist gewollt; dafuer ist START-KANZLEI.bat da.
REM
REM Hier steht die Zeile trotzdem, und zwar leer. Wer das Gelaender angelegt
REM hat, traegt die Kennung ein und kann es mit den Testakten ausprobieren,
REM bevor eine echte Akte davon abhaengt. Der Modell-Testlauf im Selbsttest
REM schickt dann fuenf erfundene Saetze aus verschiedenen Rechtsgebieten
REM hindurch. Ein Filter, der eine Koerperverletzungssache anhaelt, faellt
REM sonst erst vor der ersten echten Akte auf - unter Zeitdruck.
REM
REM Einzutragen ist die Guardrail-ID von der Seite des fertigen Gelaenders
REM in der Bedrock-Konsole - die kurze Folge aus Buchstaben und Ziffern,
REM NICHT sein Name. Anlegen nach AWS-EINRICHTEN.md, Schritt 9, mit den
REM Inhaltsfiltern AUS: In einer Kanzlei ist Gewalt der Fall, nicht der
REM Missbrauch. Leer lassen ist zulaessig - dann laeuft es wie bisher.
set JUSPERFECT_GUARDRAIL_ID=

REM --- Welches Modell welche Arbeit tut ------------------------------------
REM
REM Zwei Zeilen genuegen fuer alles.
REM
REM   Opus 4.6  denkt am besten von dem, was das Konto der Kanzlei hat -
REM             fuer Fragen, Analyse, Entwuerfe UND das Aktengedaechtnis.
REM   Haiku 4.5 ist schnell und guenstig - fuer die Eingangspruefung.
REM
REM Opus 4.7, 4.8 und 5 sowie Sonnet 5 sind diesem Konto nicht zugeteilt.
REM Das ist kein Einrichtungsfehler und laesst sich hier nicht beheben.
REM
REM Die Kennungen sehen willkuerlich aus, und das sind sie auch. Aus dem
REM Konto der Kanzlei, abgefragt am 16.09.2026 mit MODELLE-ANZEIGEN.bat:
REM
REM   Opus 4.6    anthropic.claude-opus-4-6-v1              "-v1", kein Datum
REM   Opus 4.5    anthropic.claude-opus-4-5-20251101-v1:0   Datum und Fassung
REM   Sonnet 4.6  anthropic.claude-sonnet-4-6               weder noch
REM   Sonnet 4.5  anthropic.claude-sonnet-4-5-20250929-v1:0 Datum und Fassung
REM   Haiku 4.5   anthropic.claude-haiku-4-5-20251001-v1:0  Datum und Fassung
REM
REM Es gibt also kein Muster. Hier stand einmal ein abgekuerztes
REM "anthropic.claude-opus-4-6" - abgeleitet aus dem Anzeigenamen im
REM AWS-Katalog, nicht abgefragt. AWS hat die Anfrage abgewiesen, und die
REM Meldung sah aus wie eine fehlende Freischaltung. Eine Kennung wird hier
REM nicht hergeleitet; sie wird abgefragt und Zeichen fuer Zeichen
REM abgeschrieben. MODELLE-ANZEIGEN.bat tut das.
REM
REM Den europaeischen Vorsatz "eu." setzt das Programm selbst, wenn die
REM Kennung mit "anthropic." beginnt.
set JUSPERFECT_MODELL_ID=anthropic.claude-opus-4-6-v1
set JUSPERFECT_MODELL_ID_KLEIN=anthropic.claude-haiku-4-5-20251001-v1:0

REM --- Das Einlesen bekommt das starke Modell ------------------------------
REM
REM Gemessen am 17.09.2026 an der grossen Testakte, zwei Laeufe, sonst gleich:
REM
REM                        Haiku liest ein     Opus liest ein
REM   Funde belegt         3 von 5             5 von 5
REM   Zahlen               4 von 5             5 von 5
REM   Einlesen             0,51 EUR            2,56 EUR
REM   Zusammen             0,78 EUR            2,83 EUR
REM
REM Der Lauf mit dem SCHLECHTEREN Ergebnis hatte dabei das BESSERE
REM Analysemodell (Opus 4.6 gegen 4.5). Es liegt also nicht an der Auswertung.
REM
REM Im Haiku-Lauf fehlten im ganzen Ergebnis zwei Dokumente: D-002, das
REM Leistungsverzeichnis, und D-008, die Maengelanzeige - der Vertrag und die
REM Ruege. Ohne das Leistungsverzeichnis laesst sich "geschuldet 24 cm,
REM ausgefuehrt 18 cm" nicht sagen; der Widerspruch zerfaellt in zwei halbe.
REM Das schwache Modell hat die Akte nicht falsch gelesen - es hat beim
REM Zusammenfassen die Urkunden weggelassen und das Geschehen behalten. Fuer
REM eine Kanzlei ist das die falsche Auswahl.
REM
REM Das Einlesen geschieht EINMAL je Akte, nicht je Frage; danach arbeitet
REM alles aus dem Gedaechtnis. Die zwei Euro fallen einmal an.
set JUSPERFECT_MODELL_GEDAECHTNIS=anthropic.claude-opus-4-6-v1

REM Feiner geht es auch. Was hier nicht gesetzt ist, nimmt die Zeile oben -
REM Eingangspruefung und Aktengedaechtnis nehmen davor MODELL_ID_KLEIN.
REM Zum Benutzen das REM wegnehmen.
REM set JUSPERFECT_MODELL_FRAGE=anthropic.claude-opus-4-6-v1
REM set JUSPERFECT_MODELL_ANALYSE=anthropic.claude-opus-4-6-v1
REM set JUSPERFECT_MODELL_ENTWURF=anthropic.claude-sonnet-4-6
REM set JUSPERFECT_MODELL_TRIAGE=anthropic.claude-haiku-4-5-20251001-v1:0
REM Das Aktengedaechtnis steht oben schon fest. Wer wieder sparen will,
REM traegt hier Haiku ein - und weiss aus der Messung, was er dafuer aufgibt.
REM set JUSPERFECT_MODELL_GEDAECHTNIS=anthropic.claude-haiku-4-5-20251001-v1:0
REM Voreinstellung, keine Festlegung: Wer vorher
REM   set JUSPERFECT_FIXTURE_PFAD=testdaten/grosse-akte
REM gesetzt hat, soll die grosse Testakte auch bekommen. Vorher stand hier
REM ein unbedingtes set - es hat die eigene Wahl still ueberschrieben, und
REM in der Aktenliste standen wieder nur die vier kleinen. Genau den Weg
REM empfiehlt GROSSE-TESTAKTE.bat am Ende.
if not defined JUSPERFECT_FIXTURE_PFAD set JUSPERFECT_FIXTURE_PFAD=testdaten/akten
if not defined JUSPERFECT_NUTZER_DATEI set JUSPERFECT_NUTZER_DATEI=testdaten/nutzer.json
set JUSPERFECT_IDENTITAET=header

REM --- Aktengedaechtnis: an, und hier spart es zusaetzlich Geld ---
REM Ein wiederaufgenommenes Dokument wird nicht erneut ausgelesen, und
REM "Chronologie aktualisieren" geht nur ueber das, was neu dazugekommen ist.
REM Nur die erfundenen Testakten, unverschluesselt im Programmordner.
REM Zum Zuruecksetzen: GEDAECHTNIS-LEEREN.bat
REM Wer das AWS-Gedaechtnis eingerichtet hat (setx JUSPERFECT_GEDAECHTNIS=aws
REM samt Bucket und Schluessel), soll es hier nicht wieder verlieren. Ohne
REM Voreinstellung bleibt es beim lokalen Gedaechtnis fuer die Testakten.
if not defined JUSPERFECT_GEDAECHTNIS set JUSPERFECT_GEDAECHTNIS=lokal
if not defined JUSPERFECT_GEDAECHTNIS_PFAD set JUSPERFECT_GEDAECHTNIS_PFAD=.jusperfect-gedaechtnis

REM --- Eigene Auftraege: aus, bis die Kanzlei einen Ordner dafuer hat ---
REM Ein eigener Auftrag ist eine Textdatei: Dateiname wird die Beschriftung,
REM Unterordner das Rechtsgebiet. Wer das nutzen will, nimmt bei der naechsten
REM Zeile das REM weg und traegt seinen Ordner ein. Ohne Ordner fehlen die
REM Auswahl beim Entwurf und der Knopf "Als eigenen Auftrag vormerken" -
REM das ist so gewollt und kein Fehler.
REM set JUSPERFECT_AUFTRAG_ORDNER=J:\Kanzlei\jusperfect-auftraege

REM Kostenbremse fuer den Test. Ist sie erreicht, verweigert das Programm
REM weitere Modellaufrufe, statt weiterzulaufen.
if not defined JUSPERFECT_MONATSBUDGET_EUR set JUSPERFECT_MONATSBUDGET_EUR=100

REM --- Welcher Programmstand liegt hier? ------------------------------------
REM FASSUNG.txt traegt Nummer und Datum der Aenderung; beim Auspacken einer ZIP
REM setzt Git sie ein. Am 16.09.2026 lief in der Kanzlei ein Ordner, in dem der
REM Programmteil neu und die Startdateien alt waren - von aussen sah das aus wie
REM ein Fehler im Programm. Diese Zeile haette es in einem Blick gezeigt.
set "FASSUNG=unbekannt - vor dem 17.09.2026 ausgepackt"
if exist "FASSUNG.txt" for /f "usebackq delims=" %%z in ("FASSUNG.txt") do set "FASSUNG=%%z"

echo   Programmstand: %FASSUNG%
echo [3/4] AWS-Zugang pruefen ...
echo.
"%PY%" -m jusperfect.awstest
if errorlevel 1 (
  echo.
  echo Der Zugangstest ist nicht durchgelaufen - siehe oben.
  echo.
  echo Fehlen die Zugangsdaten? Dann ZUGANG-EINTRAGEN.bat starten. Es fragt
  echo die beiden Werte aus IAM ab und legt sie ab. Die AWS CLI wird dafuer
  echo nicht gebraucht.
  echo.
  echo Die uebrigen Schritte stehen in AWS-EINRICHTEN.md.
  echo.
  pause
  exit /b 1
)

echo [4/4] jusperfect wird gestartet ...
echo.
echo    Im Browser: http://127.0.0.1:8765
echo    Nutzerkennung eintragen: ra-weber
echo.
echo    Zum Beenden dieses Fenster schliessen.
echo.
REM Der Browser geht erst auf, wenn der Server wirklich antwortet.
REM Vorher stand hier ein "start", das den Browser VOR dem Server
REM oeffnete - die Folge war jedesmal eine Fehlerseite und ein Klick
REM auf Neuladen. Aus der Kanzlei gemeldet am 25.09.2026.
set JUSPERFECT_BROWSER_OEFFNEN=1
"%PY%" -m jusperfect
pause
