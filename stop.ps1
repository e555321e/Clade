# Clade Stop Services
$Host.UI.RawUI.WindowTitle = "Clade - Stop"

# Load Chinese language
$langFile = Join-Path $PSScriptRoot "lang_zh.json"
if (Test-Path $langFile) {
    $lang = Get-Content $langFile -Raw -Encoding UTF8 | ConvertFrom-Json
    $stopTitle = "停止 Clade 服务"
    $stoppingBackend = "停止后端服务 (端口 8000)..."
    $stoppingFrontend = "停止前端服务 (端口 5173)..."
    $cleanup = "关闭相关窗口..."
    $stopped = "已停止"
    $notRunning = "未在运行"
    $allStopped = "所有服务已停止"
    $stoppingProcess = "停止进程"
    $closingWindow = "关闭窗口"
} else {
    $stopTitle = "Stopping Clade Services"
    $stoppingBackend = "Stopping backend (port 8000)..."
    $stoppingFrontend = "Stopping frontend (port 5173)..."
    $cleanup = "Closing windows..."
    $stopped = "Stopped"
    $notRunning = "Not running"
    $allStopped = "All Services Stopped"
    $stoppingProcess = "Stopping"
    $closingWindow = "Closing"
}

Clear-Host
Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Red
Write-Host "                    $stopTitle                               " -ForegroundColor Red
Write-Host "  ============================================================" -ForegroundColor Red
Write-Host ""

Write-Host "  [1/2] $stoppingBackend" -ForegroundColor Yellow
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    $port8000 | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        $proc = Get-Process -Id $_ -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "        $stoppingProcess: $($proc.ProcessName) (PID: $_)" -ForegroundColor Gray
            Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "        [OK] $stopped" -ForegroundColor Green
} else {
    Write-Host "        [INFO] $notRunning" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  [2/2] $stoppingFrontend" -ForegroundColor Yellow
$port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if ($port5173) {
    $port5173 | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        $proc = Get-Process -Id $_ -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "        $stoppingProcess: $($proc.ProcessName) (PID: $_)" -ForegroundColor Gray
            Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "        [OK] $stopped" -ForegroundColor Green
} else {
    Write-Host "        [INFO] $notRunning" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  [3/3] $cleanup" -ForegroundColor Yellow
Get-Process powershell -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -like "*Clade*" -and $_.Id -ne $PID
} | ForEach-Object {
    Write-Host "        $closingWindow: $($_.MainWindowTitle)" -ForegroundColor Gray
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Green
Write-Host "                    $allStopped                              " -ForegroundColor Green
Write-Host "  ============================================================" -ForegroundColor Green
Write-Host ""

Start-Sleep -Seconds 2
