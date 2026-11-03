# 诊断.ps1 — 收集 git / GitHub 连接状态，写到 诊断结果.txt
# 由「一键诊断.bat」调用，不要单独双击（执行策略会拦）。

$ErrorActionPreference = "Continue"
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
Set-Location -Path $PSScriptRoot
$out = Join-Path $PSScriptRoot "诊断结果.txt"
$lines = New-Object System.Collections.Generic.List[string]

function Add-Text($t) { $lines.Add($t); Write-Host $t }

Add-Text "=== mini-agent 推送诊断 ==="
Add-Text ("时间: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
Add-Text ""

Add-Text "[1] git 版本"
Add-Text ("    " + ((& git --version 2>&1) -join " "))
Add-Text ""

Add-Text "[2] credential.helper"
Add-Text ("    " + (((& git config --get credential.helper 2>&1) -join " ")))
Add-Text ""

Add-Text "[3] remote"
Add-Text ("    " + (((& git remote -v 2>&1) -join " | ")))
Add-Text ""

Add-Text "[4] 分支 / 提交数"
Add-Text ("    branch=" + ((& git branch --show-current 2>&1) -join " "))
Add-Text ("    commits=" + ((& git rev-list --count HEAD 2>&1) -join " "))
Add-Text ""

Add-Text "[5] 匿名读取远端（不弹登录）"
$env:GIT_TERMINAL_PROMPT = "0"
$env:GCM_INTERACTIVE = "never"
Add-Text ("    " + (((& git ls-remote "https://github.com/jijiboo123/mini-agent.git" 2>&1) -join " `n    ")))
Add-Text ""

Add-Text "[6] HTTPS 打开仓库页面"
Add-Text ("    " + ((& powershell -NoProfile -Command "try { `$r = Invoke-WebRequest -Uri 'https://github.com/jijiboo123/mini-agent' -UseBasicParsing -TimeoutSec 20; 'HTTP ' + `$r.StatusCode } catch { 'ERR: ' + `$_.Exception.Message }" 2>&1) -join " "))
Add-Text ""

Add-Text "[7] 推送（会尝试登录，失败也会记录原因）"
$env:GIT_TERMINAL_PROMPT = "1"
$env:GCM_INTERACTIVE = "auto"
$pushOut = & git push -u origin main 2>&1
$code = $LASTEXITCODE
Add-Text ("    exit=" + $code)
foreach ($line in $pushOut) { Add-Text ("    " + $line) }
Add-Text ""

if ($code -eq 0) { Add-Text "结论：推送成功。仓库地址 https://github.com/jijiboo123/mini-agent" }
else { Add-Text "结论：推送失败，看上面 [5] 和 [7] 的报错原文。" }

[System.IO.File]::WriteAllLines($out, $lines, (New-Object System.Text.UTF8Encoding($true)))
Write-Host ""
Write-Host ("诊断结果已写入：" + $out) -ForegroundColor Green
