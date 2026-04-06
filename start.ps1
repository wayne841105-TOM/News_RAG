# ==========================================
# AI 財經監控平台 - PowerShell 啟動腳本
# ==========================================

Write-Host ""
Write-Host "💹 AI 財經監控平台 - 簡約版啟動" -ForegroundColor Cyan
Write-Host ""

# 啟用虛擬環境
& .\.venv\Scripts\Activate.ps1

# 檢查必要的 Python 套件
Write-Host "檢查必要的依賴..." -ForegroundColor Yellow

$packages = @("flask", "flask-cors")
foreach ($package in $packages) {
    $check = pip show $package 2>$null
    if (-not $check) {
        Write-Host "正在安裝 $package..." -ForegroundColor Yellow
        pip install $package
    }
}

# 啟動 Flask API 伺服器
Write-Host ""
Write-Host "🚀 啟動 Flask API 伺服器 (port 5000)..." -ForegroundColor Green

$apiProcess = Start-Process python -ArgumentList "api_server.py" -PassThru -NoNewWindow
Write-Host "API 伺服器進程 ID: $($apiProcess.Id)" -ForegroundColor Gray

# 等待 API 伺服器啟動
Write-Host "等待 API 伺服器啟動..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# 檢查 API 是否運行
try {
    $healthCheck = Invoke-WebRequest -Uri "http://localhost:5000/health" -ErrorAction SilentlyContinue
    if ($healthCheck.StatusCode -eq 200) {
        Write-Host "✅ API 伺服器已啟動！" -ForegroundColor Green
    }
}
catch {
    Write-Host "⚠️ API 伺服器可能未正確啟動，請檢查終端輸出" -ForegroundColor Yellow
}

# 啟動本地 Web 伺服器
Write-Host ""
Write-Host "🌐 啟動 Web 伺服器 (port 8000)..." -ForegroundColor Green

$webProcess = Start-Process python -ArgumentList "-m", "http.server", "8000" -PassThru -NoNewWindow
Write-Host "Web 伺服器進程 ID: $($webProcess.Id)" -ForegroundColor Gray

# 等待 Web 伺服器啟動
Start-Sleep -Seconds 2

# 打開瀏覽器
Write-Host ""
Write-Host "📱 打開瀏覽器..." -ForegroundColor Green
Start-Process "http://localhost:8000/index.html"

Write-Host ""
Write-Host "✅ 平台已啟動！" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Web 界面: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📡 API 伺服器: http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
Write-Host "進程信息:" -ForegroundColor Yellow
Write-Host "  - API 進程 ID: $($apiProcess.Id)"
Write-Host "  - Web 進程 ID: $($webProcess.Id)"
Write-Host ""
Write-Host "⛔ 若要停止伺服器，執行以下命令:" -ForegroundColor Gray
Write-Host "  Stop-Process -Id $($apiProcess.Id)" -ForegroundColor Gray
Write-Host "  Stop-Process -Id $($webProcess.Id)" -ForegroundColor Gray
Write-Host ""
Write-Host "按任意鍵繼續..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
