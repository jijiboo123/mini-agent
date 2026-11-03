# push.ps1 — 把 mini-agent 推到 GitHub
# 不要直接双击 .ps1（执行策略会拦），双击同目录的「推送到GitHub.bat」。
# 用法：  .\push.ps1 -User 你的GitHub用户名
# 只检查： .\push.ps1 -User 你的GitHub用户名 -DryRun

param(
    [string]$User = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
Set-Location -Path $PSScriptRoot

$logPath = Join-Path $PSScriptRoot "push-log.txt"
try { Start-Transcript -Path $logPath -Force | Out-Null } catch { }
Write-Host "日志文件：$logPath" -ForegroundColor DarkGray

function Info($m) { Write-Host "[i] $m" -ForegroundColor Cyan }
function Ok($m) { Write-Host "[OK] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "[!] $m" -ForegroundColor Yellow }
function Die($m) { Write-Host "[X] $m" -ForegroundColor Red; Read-Host "按回车退出" | Out-Null; exit 1 }

Info "工作目录：$PWD"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Die "找不到 git。先关掉窗口重新打开；或确认 Git 已安装（开始菜单能打开 Git Bash 就是装了）。"
}

if (-not $User) {
    $User = Read-Host "请输入你的 GitHub 用户名（github.com/ 后面那一段，不是邮箱）"
}
if ($User) { $User = $User.Trim().TrimEnd('/') }
if (-not $User) { Die "没有用户名，退出。" }

$repoUrl = "https://github.com/$User/mini-agent.git"
Info "目标仓库：$repoUrl"

$count = (& git rev-list --count HEAD 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $count) { Die "这个目录不是 git 仓库，或没有任何提交。" }
Ok "本地已有 $count 个提交"

$remotes = @(& git remote 2>$null)
if ($remotes -contains "origin") {
    $existing = (& git remote get-url origin 2>$null)
    Info "已有 origin：$existing"
    if ($existing -ne $repoUrl) {
        if ($DryRun) { Info "[dry-run] git remote set-url origin $repoUrl" }
        else { & git remote set-url origin $repoUrl }
        Ok "origin 已指向 $repoUrl"
    }
}
else {
    if ($DryRun) { Info "[dry-run] git remote add origin $repoUrl" }
    else { & git remote add origin $repoUrl }
    Ok "已设置 origin"
}

$branch = (& git branch --show-current 2>$null)
if ($branch -ne "main") {
    if ($DryRun) { Info "[dry-run] git branch -M main" }
    else { & git branch -M main }
    Ok "分支已改名为 main"
}
else { Ok "分支已经是 main" }

if ($DryRun) {
    Info "[dry-run] git push -u origin main"
    Ok "dry-run 结束：没有真的推送。"
    Read-Host "按回车退出" | Out-Null
    exit 0
}

Warn "接下来会弹出登录窗口：选 Sign in with your browser，用浏览器授权 GitHub（不要输密码）。"
& git push -u origin main
$code = $LASTEXITCODE

if ($code -eq 0) {
    Write-Host ""
    Ok "推送成功！"
    Write-Host "仓库地址： https://github.com/$User/mini-agent" -ForegroundColor Green
    Write-Host ""
    Warn "接下来两件事："
    Write-Host "  1) 浏览器打开上面的地址，确认 README、agent/、tests/ 都在"
    Write-Host "  2) 把简历里项目那行的『Github 个人项目』改成 https://github.com/$User/mini-agent"
}
else {
    Write-Host ""
    Warn "推送失败（退出码 $code）。按顺序排查："
    Write-Host "  1) 仓库还没建 → https://github.com/new ，名字填 mini-agent，"
    Write-Host "     不要勾 README / .gitignore / license（本地已有），再运行一次本脚本。"
    Write-Host "  2) 报 Repository not found 或 403 → 用户名错了或没登录成功，重跑并走浏览器登录。"
    Write-Host "  3) 报 non-fast-forward / fetch first → 建仓库时勾了 README，先运行："
    Write-Host "     git pull --rebase origin main ，再运行本脚本。"
    Write-Host "  4) 登录窗口卡住 → 改用 token：GitHub → Settings → Developer settings →"
    Write-Host "     Personal access tokens → Fine-grained tokens → Generate new token，"
    Write-Host "     勾 Contents: Read and write，然后："
    Write-Host "     git remote set-url origin https://用户名:token@github.com/用户名/mini-agent.git"
    Write-Host "     推完改回不带 token 的地址。"
}

Read-Host "按回车退出" | Out-Null
try { Stop-Transcript | Out-Null } catch { }
