@echo off
:: Clade 停止服务入口 - 调用 PowerShell 脚本
powershell -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
