@echo off
cd /d "%~dp0"

echo Starte YD.py...
start "" /B pythonw "%~dp0YD.py"

timeout /t 2 >nul
exit
