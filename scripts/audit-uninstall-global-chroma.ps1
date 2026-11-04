# Uninstall Chroma stack from default (global) python — project uses .venv + sqlite vector
# Run only if you previously pip-installed chromadb/langchain-chroma globally

$ErrorActionPreference = "Continue"
$packages = @("langchain-chroma", "chromadb")

Write-Host "Uninstalling from global python: $($packages -join ', ')" -ForegroundColor Yellow

foreach ($pkg in $packages) {
    python -m pip uninstall -y $pkg 2>&1 | Out-Host
}

Write-Host "Done. Use .venv: .\.venv\Scripts\Activate.ps1 then setup-venv.ps1" -ForegroundColor Green
