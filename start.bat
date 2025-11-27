@echo off
title Clade Launcher
chcp 65001 >nul 2>&1
cd /d "%~dp0"

:: Run PowerShell script with UTF-8 encoding
powershell -ExecutionPolicy Bypass -NoProfile -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; & '%~dp0start.ps1'"

if errorlevel 1 (
    echo.
    echo [Error] Startup failed
    echo.
)
pause
