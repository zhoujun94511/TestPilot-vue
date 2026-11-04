# 在已有项目虚拟环境中安装/更新依赖（默认 .venv/）
# 用法: powershell -ExecutionPolicy Bypass -File scripts/setup-venv.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Get-ProjectVenvPython {
    $dotVenv = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path $dotVenv) { return $dotVenv }
    $venv = Join-Path $Root "venv\Scripts\python.exe"
    if (Test-Path $venv) { return $venv }
    return $null
}

$venvPython = Get-ProjectVenvPython
if (-not $venvPython) {
    Write-Host "未找到 .venv 或 venv，创建 .venv ..." -ForegroundColor Cyan
    python -m venv .venv
    $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
}

Write-Host "使用: $venvPython" -ForegroundColor DarkGray
Write-Host "安装/更新依赖 (requirements.txt) ..." -ForegroundColor Cyan
& $venvPython -m pip install -U pip wheel
& $venvPython -m pip install -r requirements.txt

Write-Host ""
Write-Host "完成。激活:  .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host "启动:    `$env:DEBUG='true'; python run.py" -ForegroundColor Green
