# Clade Launcher with Chinese UI
$Host.UI.RawUI.WindowTitle = "Clade"

# Load Chinese language file
$langFile = Join-Path $PSScriptRoot "lang_zh.json"
if (Test-Path $langFile) {
    $lang = Get-Content $langFile -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    # Fallback to English
    $lang = @{
        title = "Clade Launcher"
        directory = "Directory"
        step1 = "Checking Python..."
        step2 = "Checking Node.js..."
        step3 = "Setting up backend..."
        step4 = "Setting up frontend..."
        step5 = "Starting services..."
        step6 = "Waiting..."
        ok = "OK"
        error = "ERROR"
        warn = "WARN"
        install = "INSTALL"
        create = "CREATE"
        start = "START"
        pythonNotFound = "Python not found!"
        nodeNotFound = "Node.js not found!"
        download = "Download"
        pressEnter = "Press Enter to exit"
        creatingVenv = "Creating venv..."
        venvFailed = "Failed!"
        installingBackend = "Installing backend..."
        backendReady = "Backend ready"
        installingFrontend = "Installing frontend..."
        frontendReady = "Frontend ready"
        clearingPorts = "Clearing ports..."
        startingBackend = "Starting backend (8000)..."
        startingFrontend = "Starting frontend (5173)..."
        complete = "COMPLETE!"
        game = "Game"
        backend = "Backend"
        docs = "API Docs"
        tip1 = "Configure AI in Settings"
        tip2 = "Run stop.bat to stop"
        pressAnyKey = "Press any key to close..."
    }
}

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
Write-Host "              $($lang.title)                                 " -ForegroundColor $cTitle
Write-Host "  ============================================================" -ForegroundColor $cTitle
Write-Host ""

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
Write-Host "  $($lang.directory): $scriptDir" -ForegroundColor $cInfo
Write-Host ""

Write-Step "1/6" $lang.step1
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Status $lang.error $lang.pythonNotFound $cError
    Write-Host "  $($lang.download): https://www.python.org/downloads/" -ForegroundColor $cInfo
    Read-Host $lang.pressEnter
    exit 1
}
$pythonVersion = (& python --version 2>&1).ToString()
Write-Status $lang.ok $pythonVersion $cSuccess

Write-Step "2/6" $lang.step2
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    Write-Status $lang.error $lang.nodeNotFound $cError
    Write-Host "  $($lang.download): https://nodejs.org/" -ForegroundColor $cInfo
    Read-Host $lang.pressEnter
    exit 1
}
$nodeVersion = (& node --version 2>&1).ToString()
Write-Status $lang.ok "Node.js $nodeVersion" $cSuccess

Write-Step "3/6" $lang.step3
Set-Location "$scriptDir\backend"

if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Status $lang.create $lang.creatingVenv $cWarning
    & python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Status $lang.error $lang.venvFailed $cError
        Read-Host $lang.pressEnter
        exit 1
    }
}

& .\venv\Scripts\Activate.ps1

$check = & pip show fastapi 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Status $lang.install $lang.installingBackend $cWarning
    & pip install -e ".[dev]" --quiet --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) {
        Write-Status $lang.error $lang.venvFailed $cError
        Read-Host $lang.pressEnter
        exit 1
    }
}
Write-Status $lang.ok $lang.backendReady $cSuccess

Write-Step "4/6" $lang.step4
Set-Location "$scriptDir\frontend"

$needInstall = $false
if (-not (Test-Path "node_modules")) { $needInstall = $true }
elseif (-not (Test-Path "node_modules\.bin\vite.cmd")) { $needInstall = $true }

if ($needInstall) {
    Write-Status $lang.install $lang.installingFrontend $cWarning
    if (Test-Path "node_modules") {
        Remove-Item -Recurse -Force "node_modules" -ErrorAction SilentlyContinue
    }
    & npm install --silent --no-fund --no-audit
    if ($LASTEXITCODE -ne 0) {
        Write-Status $lang.error $lang.venvFailed $cError
        Read-Host $lang.pressEnter
        exit 1
    }
}
Write-Status $lang.ok $lang.frontendReady $cSuccess

Write-Step "5/6" $lang.step5
Set-Location $scriptDir

$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
$port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if ($port8000 -or $port5173) {
    Write-Status $lang.warn $lang.clearingPorts $cWarning
    if ($port8000) { $port8000 | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }
    if ($port5173) { $port5173 | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Status $lang.start $lang.startingBackend $cWarning

$be = "Set-Location '$scriptDir\backend'; & .\venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $be

Start-Sleep -Seconds 4

Write-Status $lang.start $lang.startingFrontend $cWarning

$fe = "Set-Location '$scriptDir\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $fe

Write-Step "6/6" $lang.step6
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "  ============================================================" -ForegroundColor $cSuccess
Write-Host "                      $($lang.complete)                      " -ForegroundColor $cSuccess
Write-Host "  ============================================================" -ForegroundColor $cSuccess
Write-Host ""
Write-Host "     $($lang.game):     http://localhost:5173" -ForegroundColor Cyan
Write-Host "     $($lang.backend):  http://localhost:8000" -ForegroundColor Cyan
Write-Host "     $($lang.docs):     http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ------------------------------------------------------------" -ForegroundColor $cInfo
Write-Host "     $($lang.tip1)" -ForegroundColor $cInfo
Write-Host "     $($lang.tip2)" -ForegroundColor $cInfo
Write-Host "  ------------------------------------------------------------" -ForegroundColor $cInfo
Write-Host ""

Start-Process "http://localhost:5173"

Write-Host "  $($lang.pressAnyKey)" -ForegroundColor $cInfo
[void][System.Console]::ReadKey($true)
