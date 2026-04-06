@echo off
REM ==========================================
REM AI 財經監控平台 - 啟動腳本
REM ==========================================

echo.
echo 💹 AI 財經監控平台 - 簡約版啟動
echo.

REM 啟動虛擬環境
call .venv\Scripts\activate.bat

REM 檢查必要的 Python 套件
echo 檢查必要的依賴...
pip show flask-cors >nul 2>&1
if errorlevel 1 (
    echo 正在安裝 Flask-CORS...
    pip install flask-cors
)

pip show flask >nul 2>&1
if errorlevel 1 (
    echo 正在安裝 Flask...
    pip install flask
)

REM 啟動 Flask API 伺服器
echo.
echo 🚀 啟動 Flask API 伺服器 (port 5000)...
start "" cmd /k python api_server.py

REM 等待 API 伺服器啟動
timeout /t 3 /nobreak

REM 啟動本地 Web 伺服器並打開瀏覽器
echo.
echo 🌐 啟動 Web 伺服器...

REM 使用 Python 內置 HTTP 伺服器
cd /d "%cd%"
python -m http.server 8000 >nul 2>&1 &

REM 打開瀏覽器
timeout /t 2 /nobreak
start http://localhost:8000/index.html

echo.
echo ✅ 平台已啟動！
echo 🌐 Web 界面: http://localhost:8000
echo 📡 API 伺服器: http://localhost:5000
echo.
echo 按 Ctrl+C 停止伺服器
echo.

pause
