# SkuPhase dev bootstrap (Windows PowerShell)
# Usage:  .\scripts\bootstrap_dev.ps1
$ErrorActionPreference = "Stop"

Write-Host "== SkuPhase dev bootstrap ==" -ForegroundColor Cyan

# 1. Postgres via Docker (skip if already running locally)
$dbUp = $false
try {
    $null = Test-NetConnection -ComputerName localhost -Port 5432 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($?) { $dbUp = $true; Write-Host "Postgres detected on :5432 — reusing it" }
} catch {}

if (-not $dbUp) {
    Write-Host "Starting Postgres via docker compose..."
    docker compose up -d db
    Start-Sleep -Seconds 5
}

# 2. Environment file
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from example — EDIT IT (JWT secret, GROQ key, SMTP creds)." -ForegroundColor Yellow
}

# 3. Python deps
& venv\Scripts\python.exe -m pip install -q -r requirements.txt

# 4. Migrate + seed
& venv\Scripts\python.exe init_db.py
& venv\Scripts\python.exe -m app.scripts.seed_curriculum_postgres
& venv\Scripts\python.exe init_default_plans.py 2>$null

Write-Host ""
Write-Host "Bootstrap complete. Run the API with:" -ForegroundColor Green
Write-Host "  venv\Scripts\python.exe run_server.py"
