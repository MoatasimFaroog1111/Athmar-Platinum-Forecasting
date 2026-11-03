$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== Athmar Platinum Intelligence - Local ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Python was not found. Install Python 3.11+ and reopen PowerShell."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm was not found. Install Node.js 22+ and reopen PowerShell."
}

if (-not (Test-Path ".venv")) {
  Write-Host "[1/5] Creating Python virtual environment..."
  python -m venv .venv
} else {
  Write-Host "[1/5] Python virtual environment already exists."
}

$python = Join-Path $PWD ".venv\Scripts\python.exe"

Write-Host "[2/5] Installing Python requirements..."
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip." }

& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Failed to install Python requirements." }

Write-Host "[3/5] Running safety tests..."
& $python -m pytest -q tests/test_shadow_forecast.py tests/test_platform_snapshot.py tests/test_prospective_lock.py
if ($LASTEXITCODE -ne 0) { throw "Safety tests failed." }

Write-Host "[4/5] Installing web dependencies..."
Push-Location web
try {
  npm install --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { throw "npm install failed." }

  Write-Host "[5/5] Starting dashboard at http://localhost:3000 ..."
  Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow
  npm run dev
} finally {
  Pop-Location
}
