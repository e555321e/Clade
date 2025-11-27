# Clade 启动器 - PowerShell 脚本
$Host.UI.RawUI.WindowTitle = "Clade 启动器"

# 颜色定义
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

# 清屏并显示标题
Clear-Host
Write-Host ""
Write-Host "  ============================================================" -ForegroundColor $cTitle
Write-Host "              Clade 启动器 - AI 生物演化沙盒                  " -ForegroundColor $cTitle
Write-Host "  ============================================================" -ForegroundColor $cTitle
Write-Host ""

# 获取脚本所在目录
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
Write-Host "  工作目录: $scriptDir" -ForegroundColor $cInfo
Write-Host ""

# ============================================================
# 步骤 1: 检查 Python
# ============================================================
Write-Step "1/6" "检查 Python 环境..."

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Status "错误" "未找到 Python!" $cError
    Write-Host ""
    Write-Host "  请先安装 Python 3.11 或更高版本:" -ForegroundColor $cWarning
    Write-Host "  下载地址: https://www.python.org/downloads/" -ForegroundColor $cInfo
    Write-Host ""
    Write-Host "  安装时请务必勾选 'Add Python to PATH'" -ForegroundColor $cWarning
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

$pythonVersion = (& python --version 2>&1).ToString()
Write-Status "完成" $pythonVersion $cSuccess

# ============================================================
# 步骤 2: 检查 Node.js
# ============================================================
Write-Step "2/6" "检查 Node.js 环境..."

$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    Write-Status "错误" "未找到 Node.js!" $cError
    Write-Host ""
    Write-Host "  请先安装 Node.js 18 或更高版本:" -ForegroundColor $cWarning
    Write-Host "  下载地址: https://nodejs.org/zh-cn" -ForegroundColor $cInfo
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

$nodeVersion = (& node --version 2>&1).ToString()
Write-Status "完成" "Node.js $nodeVersion" $cSuccess

# 检查 npm
$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCmd) {
    Write-Status "错误" "未找到 npm!" $cError
    Read-Host "按回车键退出"
    exit 1
}

# ============================================================
# 步骤 3: 配置后端环境
# ============================================================
Write-Step "3/6" "配置后端环境..."

Set-Location "$scriptDir\backend"

# 创建虚拟环境
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Status "创建" "正在创建 Python 虚拟环境..." $cWarning
    & python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Status "错误" "创建虚拟环境失败!" $cError
        Read-Host "按回车键退出"
        exit 1
    }
    Write-Status "完成" "虚拟环境创建成功" $cSuccess
}

# 激活虚拟环境
try {
    & .\venv\Scripts\Activate.ps1
} catch {
    Write-Status "错误" "激活虚拟环境失败!" $cError
    Read-Host "按回车键退出"
    exit 1
}

# 安装后端依赖
$fastapiInstalled = & pip show fastapi 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Status "安装" "正在安装后端依赖 (首次安装需要几分钟)..." $cWarning
    & pip install -e ".[dev]" --quiet --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) {
        Write-Status "错误" "安装后端依赖失败!" $cError
        Write-Host "      尝试手动运行: cd backend; pip install -e `".[dev]`"" -ForegroundColor $cInfo
        Read-Host "按回车键退出"
        exit 1
    }
    Write-Status "完成" "后端依赖安装成功" $cSuccess
} else {
    Write-Status "完成" "后端依赖已就绪" $cSuccess
}

# ============================================================
# 步骤 4: 配置前端环境
# ============================================================
Write-Step "4/6" "配置前端环境..."

Set-Location "$scriptDir\frontend"

# 检查 node_modules 和 vite
$needInstall = $false
if (-not (Test-Path "node_modules")) {
    $needInstall = $true
    Write-Status "提示" "未找到 node_modules 目录" $cWarning
} elseif (-not (Test-Path "node_modules\.bin\vite.cmd")) {
    $needInstall = $true
    Write-Status "提示" "vite 未正确安装，需要重新安装" $cWarning
}

if ($needInstall) {
    Write-Status "安装" "正在安装前端依赖 (首次安装需要几分钟)..." $cWarning
    
    # 删除损坏的 node_modules
    if (Test-Path "node_modules") {
        Remove-Item -Recurse -Force "node_modules" -ErrorAction SilentlyContinue
    }
    
    & npm install --silent --no-fund --no-audit
    if ($LASTEXITCODE -ne 0) {
        Write-Status "错误" "安装前端依赖失败!" $cError
        Write-Host "      尝试手动运行: cd frontend; npm install" -ForegroundColor $cInfo
        Read-Host "按回车键退出"
        exit 1
    }
    Write-Status "完成" "前端依赖安装成功" $cSuccess
} else {
    Write-Status "完成" "前端依赖已就绪" $cSuccess
}

# ============================================================
# 步骤 5: 启动服务
# ============================================================
Write-Step "5/6" "启动服务..."

Set-Location $scriptDir

# 检查并清理端口
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
$port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue

if ($port8000 -or $port5173) {
    Write-Status "警告" "检测到端口被占用，正在清理..." $cWarning
    
    if ($port8000) {
        $pids = $port8000 | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($p in $pids) {
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
    if ($port5173) {
        $pids = $port5173 | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($p in $pids) {
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 2
    Write-Status "完成" "端口已清理" $cSuccess
}

Write-Host ""
Write-Status "启动" "正在启动后端服务 (端口 8000)..." $cWarning

# 启动后端
$backendScript = @"
`$Host.UI.RawUI.WindowTitle = 'Clade Backend - Port 8000'
chcp 65001 | Out-Null
Set-Location '$scriptDir\backend'
& .\venv\Scripts\Activate.ps1
Write-Host ''
Write-Host '  ========================================' -ForegroundColor Green
Write-Host '       Clade Backend Service' -ForegroundColor Green
Write-Host '       http://localhost:8000' -ForegroundColor Cyan
Write-Host '       http://localhost:8000/docs' -ForegroundColor Cyan
Write-Host '  ========================================' -ForegroundColor Green
Write-Host ''
Write-Host '  Press Ctrl+C to stop' -ForegroundColor Gray
Write-Host ''
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendScript

# 等待后端启动
Write-Host "      等待后端初始化..." -ForegroundColor $cInfo
Start-Sleep -Seconds 4

Write-Status "启动" "正在启动前端服务 (端口 5173)..." $cWarning

# 启动前端
$frontendScript = @"
`$Host.UI.RawUI.WindowTitle = 'Clade Frontend - Port 5173'
chcp 65001 | Out-Null
Set-Location '$scriptDir\frontend'
Write-Host ''
Write-Host '  ========================================' -ForegroundColor Magenta
Write-Host '       Clade Frontend Service' -ForegroundColor Magenta
Write-Host '       http://localhost:5173' -ForegroundColor Cyan
Write-Host '  ========================================' -ForegroundColor Magenta
Write-Host ''
Write-Host '  Press Ctrl+C to stop' -ForegroundColor Gray
Write-Host ''
npm run dev
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendScript

# ============================================================
# 步骤 6: 完成
# ============================================================
Write-Host ""
Write-Step "6/6" "等待服务就绪..."
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "  ============================================================" -ForegroundColor $cSuccess
Write-Host "                        启动完成!                             " -ForegroundColor $cSuccess
Write-Host "  ============================================================" -ForegroundColor $cSuccess
Write-Host ""
Write-Host "     游戏界面:  " -NoNewline; Write-Host "http://localhost:5173" -ForegroundColor Cyan
Write-Host "     后端API:   " -NoNewline; Write-Host "http://localhost:8000" -ForegroundColor Cyan
Write-Host "     API文档:   " -NoNewline; Write-Host "http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ------------------------------------------------------------" -ForegroundColor $cInfo
Write-Host "     提示:" -ForegroundColor $cInfo
Write-Host "     - 首次使用请先配置 AI 服务 (设置 -> AI 服务)" -ForegroundColor $cInfo
Write-Host "     - 关闭服务请运行 stop.bat" -ForegroundColor $cInfo
Write-Host "  ------------------------------------------------------------" -ForegroundColor $cInfo
Write-Host ""

# 打开浏览器
Write-Host "  正在打开浏览器..." -ForegroundColor $cInfo
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "  按任意键关闭此窗口 (服务将继续在后台运行)..." -ForegroundColor $cInfo
[void][System.Console]::ReadKey($true)
