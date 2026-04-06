# 🏮 AI 財經監控平台 - 簡約版

## 概述
這是將原 Gradio 應用轉換為 **HTML5/JavaScript/CSS** 的簡約風格網站版本。採用現代化設計，無需外部依賴框架，輕量級運行。

## ✨ 特色
- 🎨 **簡約設計**：極簡主義風格，清爽的用戶界面
- 🚀 **高效運行**：原生 JavaScript 實現，無框架依賴
- 📱 **響應式設計**：支持桌面和移動設備
- 🔄 **實時更新**：與 Flask API 分離，前後端獨立
- 💾 **歷史記錄**：智能保存監控日誌

## 📦 系統要求
- Python 3.8+
- 虛擬環境 (已配置)
- 依賴套件：Flask, Flask-CORS, requests 等

## 🛠️ 安裝與運行

### 方案 1：使用啟動腳本（推薦）

```bash
# Windows
start.bat

# 將自動：
# 1. 啟動 Flask API 伺服器 (port 5000)
# 2. 啟動本地 Web 伺服器 (port 8000)
# 3. 打開瀏覽器訪問 http://localhost:8000
```

### 方案 2：手動啟動

#### 步驟 1：啟動 Flask API 伺服器
```bash
# 激活虛擬環境
.venv\Scripts\activate  (Windows)
source .venv/bin/activate  (Mac/Linux)

# 安裝必要的 Flask 套件
pip install flask flask-cors

# 啟動 API 伺服器
python api_server.py
```

#### 步驟 2：啟動 Web 伺服器
```bash
# 在新的終端中
cd <項目目錄>

# 使用 Python 內置伺服器（推薦）
python -m http.server 8000

# 或使用 Node.js http-server（如已安裝）
npx http-server -p 8000

# 或直接在瀏覽器中打開
file:///path/to/index.html
```

#### 步驟 3：訪問應用
打開瀏覽器訪問：`http://localhost:8000`

## 📁 文件結構

```
.
├── index.html          # 前端頁面（簡約 HTML5 結構）
├── styles.css          # 樣式表（現代化設計）
├── script.js           # 交互邏輯和 API 通信
├── api_server.py       # Flask API 伺服器
├── app.py              # 原 Gradio 應用（可選保留）
├── main.py             # 新聞爬蟲邏輯
├── data_engine.py      # 數據分析引擎
├── start.bat           # 快速啟動腳本
└── README.md           # 本文件
```

## 🚀 功能說明

### 📈 股票分析標簽
1. **輸入股票代碼**：填寫股票代碼（如 0050、2330、1101）
2. **點擊「完整分析」按鈕**
3. **查看結果**：
   - 📈 **股價走勢**：股票價格數據和走勢分析
   - 📊 **籌碼追蹤**：大戶持股和籌碼分佈
   - 🤖 **AI 深度分析**：使用 Gemini AI 的深層分析
   - 📰 **相關新聞**：最新財經新聞

### 📰 新聞監控標簽
1. **設定巡邏間隔**：選擇自動爬蟲的執行頻率（分鐘）
2. **點擊「啟動巡邏」按鈕**：開始自動監控
3. **查看結果**：
   - 📋 **監控日誌**：最新的爬蟲執行結果
   - 📜 **歷史紀錄**：保存最近 10 筆的監控記錄

## 🔧 API 端點

Flask API 提供以下端點（默認運行在 `http://localhost:5000`）：

### 1. 完整股票分析
```
POST /api/analyze
Content-Type: application/json

{
  "stock_code": "0050"
}

Response:
{
  "success": true,
  "stock_code": "0050",
  "timestamp": "2026-04-06 12:34:56",
  "price_summary": "...",
  "chip_summary": "...",
  "ai_analysis": "...",
  "latest_news": "..."
}
```

### 2. 啟動新聞爬蟲
```
POST /api/crawl

Response:
{
  "success": true,
  "message": "爬蟲已啟動"
}
```

### 3. 獲取爬蟲狀態
```
GET /api/crawl-status

Response:
{
  "active": false,
  "history": [
    {
      "timestamp": "12:34:56",
      "status": "success",
      "content": "..."
    }
  ]
}
```

### 4. 停止爬蟲
```
POST /api/stop-crawl

Response:
{
  "success": true,
  "message": "爬蟲已停止"
}
```

### 5. 健康檢查
```
GET /health

Response:
{
  "status": "ok",
  "timestamp": "2026-04-06T12:34:56.123456"
}
```

## 🎨 設計特點

### 色彩方案
- **主色**：藍色 (#2563eb) - 現代感
- **危險色**：紅色 (#dc2626) - 警示
- **成功色**：綠色 (#16a34a) - 正常
- **中性色**：灰色系 - 簡潔

### 響應式設計
- 桌面版：多列網格布局
- 平板版：2 列適應
- 移動版：單列堆疊

## 🔌 環境變數

確保 `.env` 文件包含：
```
GEMINI_API_KEY=your-api-key
FINMIND_API_KEY=your-finmind-key
```

## ⚙️ 配置與自訂

### 修改 API 基礎 URL
在 `script.js` 中修改：
```javascript
const API_BASE_URL = 'http://localhost:5000/api';
```

### 修改 Web 伺服器端口
```bash
# Python http.server
python -m http.server 8080  # 改為 8080

# 或在瀏覽器訪問
http://localhost:8080
```

### 修改樣式
編輯 `styles.css` 中的 CSS 變數：
```css
:root {
    --primary-color: #2563eb;  /* 修改主色 */
    --danger-color: #dc2626;   /* 修改危險色 */
}
```

## 🐛 疑難排解

### 問題 1：「API 未連接」警告
**解決方案**：確保 Flask API 伺服器正在運行
```bash
python api_server.py
```

### 問題 2：CORS 錯誤
**原因**：API 和網站運行在不同的端口
**解決方案**：已在 `api_server.py` 中配置 CORS，無需調整

### 問題 3：無法載入數據
**檢查清單**：
- [ ] .env 文件中是否設置了 API 密鑰？
- [ ] Internet 連接是否正常？
- [ ] Flask 伺服器是否運行在 localhost:5000？

### 問題 4：頁面樣式顯示異常
**解決方案**：
```bash
# 清除瀏覽器快取
Ctrl+Shift+Delete (Chrome)
Cmd+Shift+Delete (Safari)

# 或強制刷新
Ctrl+F5 (Windows)
Cmd+Shift+R (Mac)
```

## 📈 與原 Gradio 版本的對比

| 特性 | Gradio 版本 | HTML5 版本 |
|------|-----------|-----------|
| 框架 | Gradio UI | 原生 HTML5/JS |
| 包大小 | ~50MB | ~200KB |
| 啟動時間 | ~3-5 秒 | ~1 秒 |
| 依賴 | 重（Gradio + 多數依賴） | 輕（僅 Flask） |
| 設計風格 | Gradio 預設主題 | 簡約現代風 |
| 自訂性 | 受限 | 完全自訂 |
| 響應式設計 | 有限 | 完整支持 |

## 🚀 優化建議

### 1. 使用生產級 Web 伺服器
```bash
# 安裝 Gunicorn
pip install gunicorn

# 啟動 Flask API
gunicorn -w 4 api_server:app

# 使用 Nginx 伺服 靜態文件
# 配置 Nginx 反向代理到 :5000
```

### 2. 啟用緩存
在 `script.js` 中添加本地存儲：
```javascript
// 緩存分析結果
localStorage.setItem('lastAnalysis', JSON.stringify(data));
```

### 3. 離線支持
添加 Service Worker 以支持離線模式。

## 📝 更新日誌

### v1.0 (2026-04-06)
- ✅ 完成從 Gradio 到 HTML5 的轉換
- ✅ 實現簡約設計風格
- ✅ 添加響應式布局
- ✅ 實現 Flask API 後端
- ✅ 添加完整文檔

## 📞 支持

如有問題或建議，請檢查：
1. 終端輸出的錯誤信息
2. 瀏覽器開發者工具 (F12) 的控制台
3. Flask API 伺服器的日誌輸出

## 📄 許可證

依照原專案的許可證。

---

**祝你使用愉快！** 🎉
