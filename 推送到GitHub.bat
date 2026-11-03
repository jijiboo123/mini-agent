@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ================================================
echo   mini-agent  -^>  github.com/jijiboo123/mini-agent
echo ================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0push.ps1" -User "jijiboo123"
