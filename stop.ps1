# Clade Stop Services - PowerShell Script
$Host.UI.RawUI.WindowTitle = "Clade - Stop Services"

Clear-Host
Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Red
Write-Host "                    Stopping Clade Services                   " -ForegroundColor Red
Write-Host "  ============================================================" -ForegroundColor Red
Write-Host ""

Write-Host "  [1/2] Stopping backend (port 8000)..." -ForegroundColor Yellow
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    $port8000 | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        $proc = Get-Process -Id $_ -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "        Stopping: $($proc.ProcessName) (PID: $_)" -ForegroundColor Gray
            Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "        [OK] Backend stopped" -ForegroundColor Green
} else {
    Write-Host "        [INFO] Backend not running" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  [2/2] Stopping frontend (port 5173)..." -ForegroundColor Yellow
$port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if ($port5173) {
    $port5173 | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        $proc = Get-Process -Id $_ -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "        Stopping: $($proc.ProcessName) (PID: $_)" -ForegroundColor Gray
            Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "        [OK] Frontend stopped" -ForegroundColor Green
} else {
    Write-Host "        [INFO] Frontend not running" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  [Cleanup] Closing related windows..." -ForegroundColor Yellow
Get-Process powershell -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -like "*Clade*" -and $_.Id -ne $PID
} | ForEach-Object {
    Write-Host "        Closing: $($_.MainWindowTitle)" -ForegroundColor Gray
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Green
Write-Host "                    All Services Stopped                      " -ForegroundColor Green
Write-Host "  ============================================================" -ForegroundColor Green
Write-Host ""

Start-Sleep -Seconds 2