@echo off
cd /d "%~dp0"
if exist "dist\FlashDesk\FlashDesk.exe" (
    start "" "dist\FlashDesk\FlashDesk.exe"
    exit /b
)
if not exist ".venv\Scripts\pythonw.exe" (
    echo Please run setup.ps1 first.
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "main.py"
