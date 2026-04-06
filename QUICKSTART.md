# 🚀 快速開始指南

## ⚡ 5 分鐘快速啟動

### 第 1 步：開啟終端
按 `Win + R`，輸入 `cmd`，進入項目目錄：

```bash
cd e:\OneDrive\Desktop\new_2
```

### 第 2 步：運行啟動腳本

#### 選項 A：使用批處理文件（最簡單）
```bash
start.bat
```

#### 選項 B：使用 PowerShell
```bash
powershell -ExecutionPolicy Bypass -File start.ps1
```

#### 選項 C：手動啟動
**終端 1 - 啟動 API 伺服器：**
```bash
# 激活虛擬環境
.venv\Scripts\activate

# 啟動 Flask API
python api_server.py
```

**終端 2 - 啟動 Web 伺服器：**
```bash
# 激活虛擬環境
.venv\Scripts\activate

# 啟動 Python HTTP 伺服器
python -m http.server 8000
```

### 第 3 步：訪問應用
在瀏覽器中打開：
```
http://localhost:8000
```

✅ 完成！應用已啟動。

---

## 📂 項目文件結構

```
e:\OneDrive\Desktop\new_2\
│
├── 📄 index.html              ← 主頁面（簡約 HTML5）
├── 🎨 styles.css              ← 樣式表（現代設計）
├── ⚙️ script.js               ← 交互邏輯和 API 通信
│
├── 🐍 api_server.py           ← Flask API 後端（新建）
├── 🐍 main.py                 ← 新聞爬蟲邏輯
├── 🐍 data_engine.py          ← 數據分析引擎
├── 🐍 FINMIND.py              ← 財務數據接口
├── 🐍 ANALYZE.py              ← 數據分析功能
│
├── 🧪 test.html               ← 系統測試頁面（新建）
├── 📝 README.md               ← 詳細文檔（新建）
├── 🚀 start.bat               ← Windows 批處理啟動（新建）
├── 🚀 start.ps1               ← PowerShell 啟動佈本（新建）
├── 📦 requirements.txt         ← Python 依賴列表（新建）
│
├── 📂 news_data/              ← 新聞數據文件夾
├── 📂 news_archive/           ← 歷史新聞存檔
├── 📄 *.json                  ← 股票數據文件
│
├── 📂 .venv/                  ← Python 虛擬環境
└── .env                       ← 環境變數配置（需自行添加）
```

---

## 🔐 環境變數配置

在項目根目錄創建 `.env` 文件，並添加：

```bash
# Google Gemini API
GEMINI_API_KEY=your-api-key-here

# FINMIND API
FINMIND_API_KEY=your-finmind-key-here

# 其他配置
DEBUG=True
FLASK_ENV=development
```

---

## 🌐 訪問頁面清單

| 頁面 | URL | 功能 |
|------|-----|------|
| **主應用** | http://localhost:8000 | 股票分析和新聞監控 |
| **主頁面** | http://localhost:8000/index.html | 完整應用界面 |
| **測試頁面** | http://localhost:8000/test.html | 系統診斷工具 |
| **API 健康檢查** | http://localhost:5000/health | API 運行狀態 |

---

## 📋 應用功能

### 📈 股票分析
- 輸入股票代碼（如 0050、2330、1101）
- 點擊「完整分析」按鈕
- 查看：
  - 股價走勢數據
  - 籌碼追蹤信息  
  - AI 深度分析報告
  - 相關財經新聞

### 📰 新聞監控
- 設定自動爬蟲間隔（分鐘）
- 啟動定期新聞爬取
- 查看最新監控報告
- 查看歷史記錄（最近 10 筆）

---

## 🖥️ 系統需求

| 項目 | 要求 |
|------|------|
| Python | 3.8+ |
| 操作系統 | Windows / Mac / Linux |
| RAM | 最小 512MB |
| 磁盤空間 | ~500MB（含虛擬環境） |

---

## ⚙️ 如何安裝依賴

### 方法 1：使用 requirements.txt
```bash
# 激活虛擬環境
.venv\Scripts\activate

# 安裝所有依賴
pip install -r requirements.txt
```

### 方法 2：手動安裝
```bash
pip install flask flask-cors requests beautifulsoup4 python-dotenv
pip install langchain langchain-google-genai
pip install pandas pandas-ta
```

---

## 🔧 常見問題

### ❌ 「API 未連接」
**解決方案**：
1. 確認 Flask API 伺服器已啟動（`python api_server.py`）
2. 檢查 terminal 中是否有錯誤信息
3. 確認 localhost:5000 可訪問

### ❌ 「CORS 錯誤」
**解決方案**：
- 該錯誤已在 `api_server.py` 中配置解決
- 若仍存在，檢查 Flask 版本是否最新

### ❌ 「分析失敗」
**解決方案**：
1. 檢查 `.env` 文件中的 API 密鑰
2. 確認互聯網連接正常
3. 檢查 FINMIND 和 Gemini API 是否有效

### ❌ 「頁面樣式異常」
**解決方案**：
- 刷新頁面（Ctrl+F5）
- 清除瀏覽器快取（Ctrl+Shift+Delete）

---

## 📊 新舊版本對比

| 特性 | Gradio 版本 | HTML5 版本 |
|------|-----------|-----------|
| 框架 | Gradio UI | 原生 HTML5 |
| 包大小 | ~50MB | ~200KB |
| 啟動時間 | 3-5 秒 | <1 秒 |
| 設計風格 | Gradio 預設 | 極簡現代 |
| 自訂性 | 有限 | 完全 |
| 移動端支持 | 一般 | 完美 |

---

## 📞 獲取幫助

### 檢查清單
- [ ] Python 已安裝？
- [ ] 虛擬環境已激活？
- [ ] 依賴已安裝完成？
- [ ] .env 文件已配置？
- [ ] Flask API 正在運行（:5000）？
- [ ] Web 伺服器正在運行（:8000）？

### 調試步驟
1. 打開瀏覽器開發者工具（F12）
2. 查看 Console 選項卡中的任何錯誤
3. 查看 Network 選項卡以檢查 API 請求
4. 訪問測試頁面：http://localhost:8000/test.html

---

## 💡 後續優化建議

1. **使用 Gunicorn 部署**
   ```bash
   pip install gunicorn
   gunicorn -w 4 api_server:app
   ```

2. **添加數據庫存儲**
   - SQLite 用於本地存儲
   - PostgreSQL 用於生產環境

3. **實現用戶認證**
   - 添加登錄功能
   - 保存用戶偏好設置

4. **移動應用打包**
   - Electron / Tauri 桌面應用
   - React Native 移動應用

---

**祝你使用愉快！** 🎉

更多詳細信息請查看 [`README.md`](README.md)
