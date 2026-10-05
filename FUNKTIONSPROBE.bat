@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem Alle Funktionen einmal durchgehen - ohne KI, ohne AWS, ohne Kosten.
rem Sagt nach jedem Schritt, ob er haelt, was er verspricht.

if not exist ".venv\Scripts\python.exe" goto keinevenv

.venv\Scripts\python.exe werkzeug\funktionsprobe.py
set ERG=%errorlevel%
echo.
if %ERG%==0 echo Alles bestanden.
if not %ERG%==0 echo Es sind Pruefungen fehlgeschlagen - bitte die Zeilen mit x weitergeben.
echo Zum Schliessen eine Taste druecken.
pause >nul
goto ende

:keinevenv
echo Es fehlt die Arbeitsumgebung .venv. Bitte zuerst START-DEMO.bat ausfuehren.
pause

:ende
