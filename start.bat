@echo off
:: Clade 启动器入口 - 调用 PowerShell 脚本
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -NoExit -File "start.ps1"
pause
