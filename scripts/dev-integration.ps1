# 前后端联调：Flask API + Vite 热更新（Windows）
# 用法：powershell -ExecutionPolicy Bypass -File scripts/dev-integration.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    $alt = Join-Path $Root "venv\Scripts\python.exe"
    if (Test-Path $alt) { $venvPython = $alt }
}

if (-not (Test-Path $venvPython)) {
    Write-Host "未找到 .venv。请先: python -m venv .venv  然后 scripts/setup-venv.ps1" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".env")) {
    Write-Host "提示: 未找到 .env，可从 .env.example 复制并配置 API Key。" -ForegroundColor Yellow
}

$env:DEBUG = "true"
$env:PORT = if ($env:PORT) { $env:PORT } else { "5001" }

Write-Host "Python: $venvPython" -ForegroundColor DarkGray
Write-Host "启动 TestPilot（DEBUG）API :$($env:PORT) + Vite :5173 ..." -ForegroundColor Cyan
Write-Host "界面: http://127.0.0.1:5173  （/api 代理至 http://127.0.0.1:$($env:PORT)）" -ForegroundColor Cyan

& $venvPython run.py
