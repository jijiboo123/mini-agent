@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   mini-agent push diagnostics
echo   output -^> 诊断结果.txt
echo ============================================
echo.

echo [1] git version > "诊断结果.txt"
git --version >> "诊断结果.txt" 2>&1

echo. >> "诊断结果.txt"
echo [2] credential helper >> "诊断结果.txt"
git config --get credential.helper >> "诊断结果.txt" 2>&1

echo. >> "诊断结果.txt"
echo [3] remote >> "诊断结果.txt"
git remote -v >> "诊断结果.txt" 2>&1

echo. >> "诊断结果.txt"
echo [4] branch / commits >> "诊断结果.txt"
git branch --show-current >> "诊断结果.txt" 2>&1
git rev-list --count HEAD >> "诊断结果.txt" 2>&1

echo. >> "诊断结果.txt"
echo [5] git ls-remote (no prompt) >> "诊断结果.txt"
set GIT_TERMINAL_PROMPT=0
git ls-remote https://github.com/jijiboo/mini-agent.git >> "诊断结果.txt" 2>&1

echo. >> "诊断结果.txt"
echo [6] can we open github.com over HTTPS >> "诊断结果.txt"
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'https://github.com/jijiboo/mini-agent' -UseBasicParsing -TimeoutSec 20; 'HTTP ' + $r.StatusCode } catch { 'ERR: ' + $_.Exception.Message }" >> "诊断结果.txt" 2>&1

echo. >> "诊断结果.txt"
echo [7] push attempt >> "诊断结果.txt"
git push -u origin main >> "诊断结果.txt" 2>&1

echo.
echo Done. Please send the content of 诊断结果.txt back.
echo File: %~dp0诊断结果.txt
echo.
pause
