# Clade 启动器
$Host.UI.RawUI.WindowTitle = "Clade 启动器"

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
Write-Host "              Clade 启动器 - AI 生物演化沙盒                  " -ForegroundColor $cTitle
Write-Host "  ============================================================" -ForegroundColor $cTitle
Write-Host ""

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
Write-Host "  工作目录: $scriptDir" -ForegroundColor $cInfo
Write-Host ""

Write-Step "1/6" "检查 Python 环境..."
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Status "错误" "未找到 Python! 请安装 Python 3.11+" $cError
    Write-Host "  下载地址: https://www.python.org/downloads/" -ForegroundColor $cInfo
    Read-Host "按回车键退出"
    exit 1
}
$pythonVersion = (& python --version 2>&1).ToString()
Write-Status "完成" $pythonVersion $cSuccess

Write-Step "2/6" "检查 Node.js 环境..."
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    Write-Status "错误" "未找到 Node.js! 请安装 Node.js 18+" $cError
    Write-Host "  下载地址: https://nodejs.org/zh-cn" -ForegroundColor $cInfo
    Read-Host "按回车键退出"
    exit 1
}
$nodeVersion = (& node --version 2>&1).ToString()
Write-Status "完成" "Node.js $nodeVersion" $cSuccess

Write-Step "3/6" "配置后端环境..."
Set-Location "$scriptDir\backend"

if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Status "创建" "正在创建 Python 虚拟环境..." $cWarning
    & python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Status "错误" "创建虚拟环境失败!" $cError
        Read-Host "按回车键退出"
        exit 1
    }
}

& .\venv\Scripts\Activate.ps1

$check = & pip show fastapi 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Status "安装" "正在安装后端依赖 (首次需要几分钟)..." $cWarning
    & pip install -e ".[dev]" --quiet --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) {
        Write-Status "错误" "安装失败!" $cError
        Read-Host "按回车键退出"
        exit 1
    }
}
Write-Status "完成" "后端环境就绪" $cSuccess

Write-Step "4/6" "配置前端环境..."
Set-Location "$scriptDir\frontend"

$needInstall = $false
if (-not (Test-Path "node_modules")) { $needInstall = $true }
elseif (-not (Test-Path "node_modules\.bin\vite.cmd")) { $needInstall = $true }

if ($needInstall) {
    Write-Status "安装" "正在安装前端依赖 (首次需要几分钟)..." $cWarning
    if (Test-Path "node_modules") {
        Remove-Item -Recurse -Force "node_modules" -ErrorAction SilentlyContinue
    }
    & npm install --silent --no-fund --no-audit
    if ($LASTEXITCODE -ne 0) {
        Write-Status "错误" "安装失败!" $cError
        Read-Host "按回车键退出"
        exit 1
    }
}
Write-Status "完成" "前端环境就绪" $cSuccess

Write-Step "5/6" "启动服务..."
Set-Location $scriptDir

$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
$port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if ($port8000 -or $port5173) {
    Write-Status "警告" "检测到端口被占用，正在清理..." $cWarning
    if ($port8000) { $port8000 | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }
    if ($port5173) { $port5173 | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Status "启动" "正在启动后端服务 (端口 8000)..." $cWarning

$be = "Set-Location '$scriptDir\backend'; & .\venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $be

Start-Sleep -Seconds 4

Write-Status "启动" "正在启动前端服务 (端口 5173)..." $cWarning

$fe = "Set-Location '$scriptDir\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $fe

Write-Step "6/6" "等待服务就绪..."
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "  ============================================================" -ForegroundColor $cSuccess
Write-Host "                        启动完成!                             " -ForegroundColor $cSuccess
Write-Host "  ============================================================" -ForegroundColor $cSuccess
Write-Host ""
Write-Host "     游戏界面:  http://localhost:5173" -ForegroundColor Cyan
Write-Host "     后端API:   http://localhost:8000" -ForegroundColor Cyan
Write-Host "     API文档:   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ------------------------------------------------------------" -ForegroundColor $cInfo
Write-Host "     提示: 首次使用请先配置 AI 服务 (设置 -> AI 服务)" -ForegroundColor $cInfo
Write-Host "           关闭服务请运行 stop.bat" -ForegroundColor $cInfo
Write-Host "  ------------------------------------------------------------" -ForegroundColor $cInfo
Write-Host ""

Start-Process "http://localhost:5173"

Write-Host "  按任意键关闭此窗口 (服务将继续在后台运行)..." -ForegroundColor $cInfo
[void][System.Console]::ReadKey($true)