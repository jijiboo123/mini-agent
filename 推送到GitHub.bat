@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   mini-agent 推送到 GitHub  (jijiboo)
echo ============================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0push.ps1" -User "jijiboo"
