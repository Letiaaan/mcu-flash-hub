@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1" %*
if errorlevel 1 (
    echo.
    echo FlashDesk could not start. See startup.log in this folder.
    if not defined FLASHDESK_NO_PAUSE pause
    exit /b 1
)
exit /b 0
