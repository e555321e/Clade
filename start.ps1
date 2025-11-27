# Clade Launcher - PowerShell Script
$Host.UI.RawUI.WindowTitle = "Clade Launcher"

$cTitle = "Cyan"
$cSuccess = "Green"
$cWarning = "Yellow"
$cError = "Red"
$cInfo = "Gray"

function Write-Step {
    param([string]$Step, [string]$Message)
    Write-Host "[$Step] " -ForegroundColor $cTitle -NoNewline
    Write-Host $Message
}

function Write-Status {
    param([string]$Status, [string]$Message, [string]$Color = "Green")
    Write-Host "      [$Status] " -ForegroundColor $Color -NoNewline
    Write-Host $Message
}

Clear-Host
Write-Host ""
Write-Host "  ============================================================" -ForegroundColor $cTitle
Write-Host "              Clade Launcher - AI Evolution Sandbox           " -ForegroundColor $cTitle
Write-Host "  ============================================================" -ForegroundColor $cTitle
Write-Host ""

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
Write-Host "  Directory: $scriptDir" -ForegroundColor $cInfo
Write-Host ""

Write-Step "1/6" "Checking Python..."
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Status "ERROR" "Python not found! Please install Python 3.11+" $cError
    Write-Host "  Download: https://www.python.org/downloads/" -ForegroundColor $cInfo
    Read-Host "Press Enter to exit"
    exit 1
}
$pythonVersion = (& python --version 2>&1).ToString()
Write-Status "OK" $pythonVersion $cSuccess

Write-Step "2/6" "Checking Node.js..."
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    Write-Status "ERROR" "Node.js not found! Please install Node.js 18+" $cError
    Write-Host "  Download: https://nodejs.org/" -ForegroundColor $cInfo
    Read-Host "Press Enter to exit"
    exit 1
}
$nodeVersion = (& node --version 2>&1).ToString()
Write-Status "OK" "Node.js $nodeVersion" $cSuccess

Write-Step "3/6" "Setting up backend..."
Set-Location "$scriptDir\backend"

if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Status "CREATE" "Creating Python virtual environment..." $cWarning
    & python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Status "ERROR" "Failed to create venv!" $cError
        Read-Host "Press Enter to exit"
        exit 1
    }
}

& .\venv\Scripts\Activate.ps1

$check = & pip show fastapi 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Status "INSTALL" "Installing backend dependencies..." $cWarning
    & pip install -e ".[dev]" --quiet --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) {
        Write-Status "ERROR" "Failed!" $cError
        Read-Host "Press Enter to exit"
        exit 1
    }
}
Write-Status "OK" "Backend ready" $cSuccess

Write-Step "4/6" "Setting up frontend..."
Set-Location "$scriptDir\frontend"

$needInstall = $false
if (-not (Test-Path "node_modules")) { $needInstall = $true }
elseif (-not (Test-Path "node_modules\.bin\vite.cmd")) { $needInstall = $true }

if ($needInstall) {
    Write-Status "INSTALL" "Installing frontend dependencies..." $cWarning
    if (Test-Path "node_modules") {
        Remove-Item -Recurse -Force "node_modules" -ErrorAction SilentlyContinue
    }
    & npm install --silent --no-fund --no-audit
    if ($LASTEXITCODE -ne 0) {
        Write-Status "ERROR" "Failed!" $cError
        Read-Host "Press Enter to exit"
        exit 1
    }
}
Write-Status "OK" "Frontend ready" $cSuccess

Write-Step "5/6" "Starting services..."
Set-Location $scriptDir

$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
$port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if ($port8000 -or $port5173) {
    Write-Status "WARN" "Clearing occupied ports..." $cWarning
    if ($port8000) { $port8000 | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }
    if ($port5173) { $port5173 | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Status "START" "Starting backend (port 8000)..." $cWarning

$be = "Set-Location '$scriptDir\backend'; & .\venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $be

Start-Sleep -Seconds 4

Write-Status "START" "Starting frontend (port 5173)..." $cWarning

$fe = "Set-Location '$scriptDir\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $fe

Write-Step "6/6" "Waiting for services..."
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "  ============================================================" -ForegroundColor $cSuccess
Write-Host "                      STARTUP COMPLETE!                       " -ForegroundColor $cSuccess
Write-Host "  ============================================================" -ForegroundColor $cSuccess
Write-Host ""
Write-Host "     Game:     http://localhost:5173" -ForegroundColor Cyan
Write-Host "     Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "     API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""

Start-Process "http://localhost:5173"

Write-Host "  Press any key to close (services keep running)..." -ForegroundColor $cInfo
[void][System.Console]::ReadKey($true)