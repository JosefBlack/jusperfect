@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
title jusperfect - ECHTE AKTEN ueber die jur^|nodes-Schnittstelle

echo ==================================================
echo    jusperfect - ECHTE AKTEN ueber die Schnittstelle
echo ==================================================
echo.
echo Diese Datei arbeitet mit dem echten Aktenbestand ueber die
echo REST-Schnittstelle von jur^|nodes. Fuer den Weg ueber das
echo eingebundene Laufwerk ist START-KANZLEI.bat da, fuer die
echo erfundenen Testakten START-AWS.bat.
echo.

REM ===================================================================
REM   HIER TRAGEN SIE EIN EINZIGES DING EIN. Ohne es startet nichts.
REM ===================================================================
REM
REM Hier ist nichts mehr einzutragen. Auch die Kennung des
REM Schutzgelaenders liegt jetzt in Ihrem Windows-Konto und wird
REM mit JURNODES-ZUGANG.bat eingetragen.
REM
REM Warum das umgestellt wurde: Am 25.09.2026 stand sie hier, in einer
REM Datei des Programmordners. Beim Auspacken einer neuen Fassung wurde
REM diese Datei ueberschrieben, die Kennung war weg, und die Kanzlei kam
REM nicht mehr an die echten Akten. Was eine Einrichtung ueberleben soll,
REM darf nicht in dem Ordner stehen, den wir austauschen.
REM
REM Eine von Hand eingetragene Kennung gilt weiterhin - sie wird unten
REM nur genommen, wenn im Windows-Konto keine liegt.
set "GELAENDER_VON_HAND="
if not defined JUSPERFECT_GUARDRAIL_ID if defined GELAENDER_VON_HAND set "JUSPERFECT_GUARDRAIL_ID=%GELAENDER_VON_HAND%"
REM ===================================================================

REM --- Ab hier ist nichts mehr einzutragen ---------------------------
set JUSPERFECT_BETRIEBSART=lokal
set JUSPERFECT_ANBIETER=bedrock
set JUSPERFECT_AWS_REGION=eu-central-1
set JUSPERFECT_JURNODES_ADAPTER=http
set JUSPERFECT_IDENTITAET=header

REM --- Wer in dieser Kanzlei arbeitet -------------------------------
REM Ohne diese Zeile stuenden auf dem Anmeldebild die erfundenen
REM Testnutzer (RA Dr. Weber und so fort). Mit echten Akten ist das
REM nicht nur unschoen, sondern irrefuehrend: Der Name steht im
REM Verarbeitungsnachweis jedes Modellaufrufs.
set JUSPERFECT_NUTZER_DATEI=nutzer-kanzlei.json

REM --- Das Aktengedaechtnis liegt IN DER AKTE ------------------------
REM
REM Eine einzige Datei je Akte, im Dateiordner der Akte in jur|nodes.
REM Kein zweiter Aufbewahrungsort; Sicherung und Loeschung der Akte
REM erfassen sie mit.
REM
REM Ohne Gedaechtnis wird eine Akte bei JEDER Sitzung neu gelesen.
REM Gemessen am 23.09.2026 an einer echten Akte: 23 Cent die erste
REM Frage, 4 Cent jede weitere - aber nur, solange der Cache lebt,
REM und der lebt Minuten. Am naechsten Tag beginnt es wieder bei 23.
REM
REM Der Schluessel braucht dafuer im Bereich Dateisystem das Recht,
REM eine Datei zu erzeugen. Fehlt es, sagt das Programm es beim
REM Sichern - gearbeitet werden kann trotzdem.
REM
REM NICHT MEHR IN DIE AKTE. Entschieden in der Kanzlei am 25.09.2026;
REM seit dem 01.10.2026 geht das Gedaechtnis stattdessen nach AWS (unten).
REM
REM Der Grund: jur|nodes ersetzt eine vorhandene Datei nicht, sondern
REM weist sie ab, und das Recht "Datei loeschen" gaelte fuer JEDE Datei
REM des Bestands - dafuer ist der Preis zu hoch. Ein Zeitstempel je
REM Fassung wurde versucht und wieder verworfen: In einer Mandatsakte
REM sammelten sich Fassungen neben den Schriftsaetzen.
REM
REM Solange es aus ist, wird jede Akte bei jeder Sitzung neu eingelesen -
REM rund 23 Cent je Akte und Tag. Es geht nichts verloren, und in
REM jur|nodes entsteht keine einzige Datei.
REM
REM Der naechste Schritt ist "aws": derselbe Nutzen, im Konto der
REM Kanzlei, ohne Dateien in der Akte.
REM Eingeschaltet am 01.10.2026 auf ausdrueckliche Anweisung der Kanzlei
REM ("Schalte das Aktengedaechtnis nun ein"). Vorher stand hier "aus".
REM
REM WAS SICH DAMIT AENDERT: jusperfect legt ab jetzt dauerhaft Akteninhalt
REM ausserhalb von jur|nodes ab - Mandatsgut, kein Protokoll. Derselbe
REM Auftragsverarbeiter wie fuer die Verarbeitung (AWS Frankfurt), also kein
REM neuer AV-Vertrag; Zweck, Kategorien, Speicherdauer, Empfaenger und
REM Betroffenenrechte muessen es aber nennen. Das ist Ziffer 6.2 des
REM Verarbeitungsverzeichnisses, und die ist noch offen.
REM
REM Zurueckgeschaltet wird mit einer Zeile: aus "aws" wieder "aus" machen.
REM Was bereits abgelegt ist, bleibt dann liegen - GEDAECHTNIS-LEEREN.bat
REM raeumt es weg.

REM --- So wird daraus "aws" ------------------------------------------
REM
REM Der Programmteil ist fertig: jusperfect legt das Gedaechtnis dann in
REM S3 ab, verschluesselt mit dem Schluessel der Kanzlei. Was fehlt, ist
REM eingerichtet zu werden - Ablageort und Schluessel in AWS anlegen.
REM Anleitung: AWS-EINRICHTEN.md, Abschnitt "Das Aktengedaechtnis in AWS".
REM
REM Danach in den vier Zeilen unten das REM wegnehmen, die zwei Werte
REM eintragen und EINMAL GEDAECHTNIS-AWS-PRUEFEN.bat starten. Die Probe
REM legt eine Zeile ab, liest sie zurueck und entfernt sie wieder; erst
REM wenn sie gruen ist, arbeitet das Gedaechtnis auch wirklich.
REM
REM Das Einschalten ist eine Entscheidung der Kanzlei, nicht eine
REM technische: Damit legt jusperfect erstmals dauerhaft etwas ausserhalb
REM von jur|nodes ab. SICHERHEIT.md, KONZEPT.md und DSFA-ANGABEN.md
REM nennen es; AVV, DSFA und Mandantenhinweise gehoeren dazu.
REM
set JUSPERFECT_GEDAECHTNIS=aws
set JUSPERFECT_GEDAECHTNIS_BUCKET=dortschy-thunert-jusperfect-aktengedaechtnis
set JUSPERFECT_KMS_SCHLUESSEL_ID=cf389440-c627-488d-8104-4989a1393a5d

REM --- Texterkennung fuer gescannte Blaetter (Aufgabe 1) ---------------------
REM
REM 17 von 55 Dokumenten der echten Akte sind Scans ohne Textschicht -
REM Rueckscheine, Einschreiben, die Vollmacht. Das Programm liest sie, findet
REM nichts und sagt das auch. Mit Textract liest es sie.
REM
REM Gebraucht wird genau EINE Berechtigung: textract:DetectDocumentText in der
REM Zugriffsrichtlinie des Benutzers. Kein neuer Auftragsverarbeiter - es ist
REM derselbe wie fuer die Texte (AWS Frankfurt); die DSFA muss es aber nennen.
REM
REM EIN ABLAGEORT IST DAFUER NICHT NOETIG - auch bei vielen Seiten nicht.
REM Das Programm zerlegt ein PDF auf DIESEM Rechner in einzelne Blaetter und
REM schickt jedes Blatt fuer sich. Bei AWS wird damit nichts gespeichert,
REM sondern nur verarbeitet - ein Unterschied, der in der DSFA zaehlt.
REM
REM Nur ein PDF, das sich nicht zerlegen laesst (beschaedigt oder mit Kennwort),
REM braucht noch einen Bucket. Dann sagt das Programm genau das.
REM
REM Kosten: rund 1,50 EUR je 1000 Seiten. Fuer eine Akte Bruchteile eines Cents.
REM
REM Eingeschaltet am 02.10.2026 auf ausdrueckliche Anweisung der Kanzlei.
REM Vorbedingung: Die Zugriffsrichtlinie in AWS muss die Fassung mit
REM TexterkennungFuerScans tragen. Fehlt sie, sagt das Programm beim ersten
REM Scan genau das - der Rest der Akte wird trotzdem gelesen.
set JUSPERFECT_OCR=textract

REM --- Der Korrespondenzordner: AUS -----------------------------------
REM
REM Am 02.10.2026 fielen in der Bausache X-100-2026 drei Schriftstuecke
REM aus einer fremden Verkehrsunfallsache auf. Drei Laeufe an drei Akten
REM zeigten am 05.10. dasselbe Muster: Der Dateiordner passt jedesmal zur
REM Akte, der Korrespondenzordner nie - niedrige Nummer, befuellt stets
REM 2022/23, unabhaengig davon, wann die Akte angelegt wurde.
REM
REM AUFGEKLAERT am Abend des 05.10.2026, und es war UNSER Fehler:
REM jur|nodes fuehrt ZWEI getrennte Ordnerbaeume mit je eigenen Nummern -
REM das Dateisystem und die Korrespondenz. Das Programm hat die Nummer des
REM Korrespondenzordners am Pfad des Dateisystems abgefragt. Dort gibt es
REM die Nummer auch, sie gehoert nur zu einem anderen Ordner - dem einer
REM fremden Akte.
REM
REM Der richtige Weg steht fest: POST /correspondence/search. Er ist in der
REM Probe gemessen, aber noch nicht im Betrieb - erst ein Lauf an einer
REM echten Akte zeigt, was der Server wirklich liefert.
REM
REM Diese Zeile bleibt deshalb aus. Sie einzuschalten wuerde den FALSCHEN
REM Weg wieder gehen.
REM set JUSPERFECT_KORRESPONDENZ=ein

REM --- Was nicht von selbst angehakt wird ------------------------------
REM
REM Aus der Kanzlei am 05.10.2026: "Grundsaetzlich gehoert die Rechnung
REM nicht ins Aktengedaechtnis und Korrespondenz mit der RSV."
REM
REM Traegt der TITEL eines dieser Woerter, kommt das Dokument ohne Haken
REM ins Fenster "Dokumente der Akte". Es steht weiter da, nur blasser,
REM mit dem Grund daneben - wer es doch braucht, hakt es an. "alle
REM anhaken" laesst es aus; ein zweiter Klick holt es dazu.
REM
REM Geprueft wird der Titel, nicht der Inhalt: eine Hilfe, keine Gewaehr.
REM
REM Eigene Liste? Das REM der naechsten Zeile weg und die Woerter mit
REM Komma trennen. Ganz leer lassen schaltet die Vorauswahl ab.
REM
REM Umlaute bitte nicht in diese Zeile: Windows liest diese Datei in
REM einer anderen Zeichentabelle als das Programm, aus "Gebuehren"
REM wuerde dort etwas, das auf keinen Titel passt. Die Vorgabe im
REM Programm kennt "Gebuehren" mit Umlaut; wer die Zeile hier setzt,
REM ersetzt die Vorgabe vollstaendig.
REM set JUSPERFECT_NICHT_VORWAEHLEN=Rechnung,Kostennote,Vorschuss,Honorar,RSV,Rechtsschutz

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

REM --- Die Pflichtangaben pruefen, bevor irgendetwas laeuft ----------
REM
REM Fehlt etwas, wird gezeigt, was da ist und was nicht. Am 25.09.2026
REM sagte die Meldung nur "es fehlt das Schutzgelaender" und dann, wie man
REM es eintraegt - und nach dem Eintragen kam sie wieder. Wer nicht sieht,
REM was angekommen ist, kann nur raten, woran es lag.
set "STAND_URL=FEHLT"
set "STAND_USER=FEHLT"
set "STAND_KEY=FEHLT"
set "STAND_GELAENDER=FEHLT"
if defined JUSPERFECT_JURNODES_URL set "STAND_URL=%JUSPERFECT_JURNODES_URL%"
if defined JURNODES_API_USER set "STAND_USER=%JURNODES_API_USER%"
if defined JURNODES_API_KEY set "STAND_KEY=hinterlegt"
if defined JUSPERFECT_GUARDRAIL_ID set "STAND_GELAENDER=%JUSPERFECT_GUARDRAIL_ID%"

if not defined JUSPERFECT_GUARDRAIL_ID goto kein_gelaender
if not defined JUSPERFECT_JURNODES_URL goto kein_zugang_hinterlegt
if not defined JURNODES_API_USER goto kein_zugang_hinterlegt
if not defined JURNODES_API_KEY goto kein_zugang_hinterlegt
goto angaben_geprueft

:kein_gelaender
echo.
echo   Es fehlt das Schutzgelaender.
echo.
echo   Mit echten Akten startet jusperfect ohne Guardrail nicht. Das ist
echo   keine Huerde, sondern die Sperre, die wir eingebaut haben.
echo.
echo   So geht es weiter: JURNODES-ZUGANG.bat starten.
echo.
echo   Hatten Sie die Kennung schon einmal eingetragen, sucht sie
echo   diese Datei selbst - in den Ordnern neben diesem und in
echo   Downloads, auf dem Schreibtisch und in Dokumenten. Sie steht
echo   dann schon da, und die Eingabetaste genuegt.
echo.
echo   Beim ersten Mal: AWS-EINRICHTEN.md, Schritt 9.
echo.
echo   Danach dieses Fenster SCHLIESSEN und neu starten. Windows gibt
echo   die Werte erst an ein NEUES Fenster weiter.
echo.
echo   Einmal eingetragen, bleibt sie - auch nach der naechsten ZIP.
echo.
goto stand_zeigen

:stand_zeigen
echo   ------------------------------------------------------------
echo   Das steht gerade in Ihrem Windows-Konto:
echo.
echo     Adresse:          %STAND_URL%
echo     Benutzer:         %STAND_USER%
echo     Token:            %STAND_KEY%
echo     Schutzgelaender:  %STAND_GELAENDER%
echo   ------------------------------------------------------------
echo.
echo   Steht bei einer Zeile FEHLT, ist der Wert nicht angekommen.
echo   Steht er da und die Meldung kam trotzdem, war dieses Fenster
echo   schon offen, als Sie ihn eingetragen haben - dann genuegt es,
echo   es zu schliessen und neu zu starten.
echo.
pause
exit /b 1

:kein_zugang_hinterlegt
echo.
echo   Es ist kein jur^|nodes-Zugang hinterlegt.
echo.
echo   Gebraucht werden drei Angaben: die Adresse der Schnittstelle,
echo   der Benutzername und der Token. Sie werden nicht hier
echo   eingetragen, sondern mit JURNODES-ZUGANG.bat.
echo.
echo   Wichtig: Nach dem Eintragen dieses Fenster schliessen und die
echo   Datei neu starten. Windows gibt die Werte erst an ein NEUES
echo   Fenster weiter.
echo.
goto stand_zeigen

:angaben_geprueft

REM --- Python und Arbeitsumgebung ------------------------------------
REM Hier stand bis zum 25.09.2026 "bitte zuerst einmal START-AWS.bat
REM ausfuehren; es legt sie an" - also erst die erfundenen Testakten
REM starten, um an die echten zu kommen. Aus der Kanzlei: "warum muss
REM ich jedes mal eine arbeitsumgebung schaffen bevor ich zum programm
REM will". Eine Huerde ohne Zweck; jede neue ZIP verlangte sie erneut.
REM
REM _UMGEBUNG.bat tut, was START-AWS.bat dafuer tat - dieselbe Datei,
REM nicht dieselben Zeilen zweimal.
call "%~dp0_UMGEBUNG.bat" 2
if errorlevel 1 exit /b 1

REM Ob die Programmdateien richtig liegen, prueft _UMGEBUNG.bat - und zwar
REM ausfuehrlicher, als es hier stand: Hier fehlte die Unterscheidung, ob
REM web.py neben der Startdatei liegt. Das ist der eine Fall, in dem man dem
REM Anwender genau sagen kann, was er falsch gemacht hat.

echo.
echo   Schnittstelle:   %JUSPERFECT_JURNODES_URL%
echo   Benutzer:        %JURNODES_API_USER%
echo   Schutzgelaender: %JUSPERFECT_GUARDRAIL_ID%
echo   Modell:          %JUSPERFECT_MODELL_ID%
echo   Gedaechtnis:     AUS (siehe Erklaerung in dieser Datei)
echo   Kostenbremse:    %JUSPERFECT_MONATSBUDGET_EUR% EUR im Monat
echo.
set "FASSUNG=unbekannt"
if exist "FASSUNG.txt" for /f "usebackq delims=" %%z in ("FASSUNG.txt") do set "FASSUNG=%%z"
echo   Programmstand:   %FASSUNG%
echo.
echo   ==============================================================
echo   Ab hier geht ECHTER Aktentext an AWS Frankfurt. Weiter mit
echo   einer Taste, Abbruch mit Strg+C.
echo   ==============================================================
pause >nul

echo.
echo   AWS-Zugang pruefen ...
"%PY%" -m jusperfect.awstest
if errorlevel 1 goto kein_awszugang

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

:kein_awszugang
echo.
echo   Der AWS-Zugangstest ist nicht durchgelaufen - siehe oben. Mit
echo   echten Akten wird hier nicht weitergemacht.
echo.
pause
exit /b 1

:ende
endlocal
