@echo off
:: Clade 停止服务入口 - 调用 PowerShell 脚本
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -NoExit -File "stop.ps1"
pause
