# Clade 停止服务
$Host.UI.RawUI.WindowTitle = "Clade - 停止服务"

Clear-Host
Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Red
Write-Host "                    停止 Clade 服务                           " -ForegroundColor Red
Write-Host "  ============================================================" -ForegroundColor Red
Write-Host ""

Write-Host "  [1/2] 停止后端服务 (端口 8000)..." -ForegroundColor Yellow
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    $port8000 | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        $proc = Get-Process -Id $_ -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "        停止进程: $($proc.ProcessName) (PID: $_)" -ForegroundColor Gray
            Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "        [完成] 后端服务已停止" -ForegroundColor Green
} else {
    Write-Host "        [提示] 后端服务未在运行" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  [2/2] 停止前端服务 (端口 5173)..." -ForegroundColor Yellow
$port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if ($port5173) {
    $port5173 | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        $proc = Get-Process -Id $_ -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "        停止进程: $($proc.ProcessName) (PID: $_)" -ForegroundColor Gray
            Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "        [完成] 前端服务已停止" -ForegroundColor Green
} else {
    Write-Host "        [提示] 前端服务未在运行" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  [清理] 关闭相关窗口..." -ForegroundColor Yellow
Get-Process powershell -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -like "*Clade*" -and $_.Id -ne $PID
} | ForEach-Object {
    Write-Host "        关闭窗口: $($_.MainWindowTitle)" -ForegroundColor Gray
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Green
Write-Host "                    所有服务已停止                            " -ForegroundColor Green
Write-Host "  ============================================================" -ForegroundColor Green
Write-Host ""

Start-Sleep -Seconds 2