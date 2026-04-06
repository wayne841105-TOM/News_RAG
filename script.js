/* ==========================================
   JavaScript - UI 互動與 API 通信
   ========================================== */

const API_BASE_URL = 'http://localhost:5000/api';
let crawlTimer = null;
let crawlInterval = 10;
let crawlActive = false;

// ========== DOM 元素 ==========
const analyzeBtn = document.getElementById('analyze-btn');
const stockInput = document.getElementById('stock-input');
const statusText = document.getElementById('status-text');
const priceDisplay = document.getElementById('price-display');
const chipDisplay = document.getElementById('chip-display');
const analysisDisplay = document.getElementById('analysis-display');
const newsDisplay = document.getElementById('news-display');

const startBtn = document.getElementById('start-btn');
const stopBtn = document.getElementById('stop-btn');
const statusLight = document.getElementById('status-light');
const statusLabel = document.getElementById('status-label');
const timerInput = document.getElementById('timer-input');
const scheduleInfo = document.getElementById('schedule-info');
const reportOutput = document.getElementById('report-output');
const historyOutput = document.getElementById('history-output');

// ========== 標簽導航 ==========
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const tabName = e.target.dataset.tab;
        
        // 移除所有標簽頁的 active
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelectorAll('.tab-btn').forEach(tab => {
            tab.classList.remove('active');
        });
        
        // 激活選定的標簽頁
        document.getElementById(tabName).classList.add('active');
        e.target.classList.add('active');
    });
});

// ========== 股票分析功能 ==========
analyzeBtn.addEventListener('click', async () => {
    const stockCode = stockInput.value.trim();
    
    if (!stockCode) {
        showStatus('❌ 請輸入股票代碼', 'error');
        return;
    }
    
    await performAnalysis(stockCode);
});

// 允許按 Enter 鍵進行分析
stockInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        analyzeBtn.click();
    }
});

async function performAnalysis(stockCode) {
    try {
        // UI 狀態：分析進行中
        analyzeBtn.disabled = true;
        showStatus('🔄 正在抓取數據...', 'loading');
        priceDisplay.innerHTML = '<div class="spinner"></div> 載入中...';
        chipDisplay.innerHTML = '<div class="spinner"></div> 載入中...';
        analysisDisplay.innerHTML = '<div class="spinner"></div> 載入中...';
        newsDisplay.innerHTML = '<div class="spinner"></div> 載入中...';
        
        // 調用 API
        const response = await fetch(`${API_BASE_URL}/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ stock_code: stockCode })
        });
        
        if (!response.ok) {
            throw new Error(`API 錯誤: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || '分析失敗');
        }
        
        // 更新顯示內容
        priceDisplay.innerHTML = formatMarkdown(data.price_summary);
        chipDisplay.innerHTML = formatMarkdown(data.chip_summary);
        analysisDisplay.innerHTML = formatMarkdown(data.ai_analysis);
        newsDisplay.innerHTML = formatMarkdown(data.latest_news);
        
        showStatus(`✅ 分析完成 @ ${data.timestamp}`, 'success');
        
    } catch (error) {
        console.error('分析錯誤:', error);
        showStatus(`❌ 分析失敗: ${error.message}`, 'error');
        priceDisplay.innerHTML = `❌ 錯誤: ${error.message}`;
        chipDisplay.innerHTML = `❌ 錯誤: ${error.message}`;
        analysisDisplay.innerHTML = `❌ 錯誤: ${error.message}`;
        newsDisplay.innerHTML = `❌ 錯誤: ${error.message}`;
    } finally {
        analyzeBtn.disabled = false;
    }
}

// ========== 新聞監控功能 ==========
startBtn.addEventListener('click', async () => {
    try {
        const minutes = parseFloat(timerInput.value);
        
        if (isNaN(minutes) || minutes <= 0) {
            showMonitorStatus('⚠️ 請輸入有效的間隔時間');
            return;
        }
        
        startBtn.disabled = true;
        stopBtn.disabled = false;
        crawlInterval = minutes;
        
        // 更新 UI
        statusLight.classList.remove('idle');
        statusLight.classList.add('running');
        statusLabel.textContent = '自動巡邏運行中';
        
        // 立即執行一次爬蟲
        await runCrawl();
        
        // 設置定期執行
        crawlTimer = setInterval(() => {
            runCrawl();
        }, minutes * 60 * 1000);
        
        crawlActive = true;
        updateScheduleInfo(minutes);
        
    } catch (error) {
        console.error('啟動爬蟲錯誤:', error);
        showMonitorStatus(`❌ 啟動失敗: ${error.message}`);
        startBtn.disabled = false;
    }
});

stopBtn.addEventListener('click', async () => {
    try {
        // 停止定時器
        if (crawlTimer) {
            clearInterval(crawlTimer);
            crawlTimer = null;
        }
        
        // 調用 API 停止爬蟲
        await fetch(`${API_BASE_URL}/stop-crawl`, {
            method: 'POST'
        });
        
        // 更新 UI
        startBtn.disabled = false;
        stopBtn.disabled = true;
        crawlActive = false;
        
        statusLight.classList.remove('running');
        statusLight.classList.add('idle');
        statusLabel.textContent = '巡邏停止中';
        scheduleInfo.textContent = '🔴 已停止巡邏';
        
    } catch (error) {
        console.error('停止爬蟲錯誤:', error);
        showMonitorStatus(`❌ 停止失敗: ${error.message}`);
    }
});

async function runCrawl() {
    try {
        // 更新狀態
        reportOutput.innerHTML = '<div class="spinner"></div> 正在爬取新聞...';
        
        const response = await fetch(`${API_BASE_URL}/crawl`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`API 錯誤: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || '爬蟲執行失敗');
        }
        
        // 等待一下後查詢狀態
        setTimeout(fetchCrawlStatus, 2000);
        
    } catch (error) {
        console.error('爬蟲執行錯誤:', error);
        reportOutput.innerHTML = `❌ 爬蟲錯誤: ${error.message}`;
    }
}

async function fetchCrawlStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/crawl-status`);
        
        if (!response.ok) {
            throw new Error(`API 錯誤: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.history && data.history.length > 0) {
            const latestReport = data.history[0];
            reportOutput.innerHTML = formatMarkdown(latestReport.content);
            
            // 更新歷史記錄
            updateHistory(data.history);
        }
        
    } catch (error) {
        console.error('查詢爬蟲狀態錯誤:', error);
    }
}

function updateHistory(historyList) {
    if (!historyList || historyList.length === 0) {
        historyOutput.innerHTML = '<p class="placeholder">(尚無紀錄)</p>';
        return;
    }
    
    let historyHtml = '';
    historyList.forEach((item, index) => {
        const timestamp = item.timestamp || '未知時間';
        const hasFocus = item.content.includes('深度財經 AI 報告');
        const icon = hasFocus ? '💰 發現財經焦點' : '💤 無重大發現';
        const title = `[${timestamp}] ${icon}`;
        
        historyHtml += `
            <div class="history-item" onclick="toggleHistoryItem(this)">
                <div class="history-item-title">${escapeHtml(title)}</div>
                <div class="history-item-content">${formatMarkdown(item.content)}</div>
            </div>
        `;
    });
    
    historyOutput.innerHTML = historyHtml;
}

function toggleHistoryItem(element) {
    element.classList.toggle('expanded');
}

function updateScheduleInfo(minutes) {
    const nextTime = new Date(Date.now() + minutes * 60 * 1000);
    const timeStr = nextTime.toLocaleTimeString('zh-TW');
    scheduleInfo.textContent = `🟢 運行中 | 下次巡邏預計：${timeStr}`;
}

// ========== 輔助函式 ==========

function showStatus(message, type = 'info') {
    statusText.textContent = message;
    statusText.style.backgroundColor = getStatusBgColor(type);
    statusText.style.color = getStatusTextColor(type);
}

function showMonitorStatus(message) {
    scheduleInfo.textContent = message;
}

function getStatusBgColor(type) {
    const colors = {
        'success': '#ecfdf5',
        'error': '#fee2e2',
        'loading': '#fef3c7',
        'info': '#dbeafe'
    };
    return colors[type] || colors['info'];
}

function getStatusTextColor(type) {
    const colors = {
        'success': '#166534',
        'error': '#991b1b',
        'loading': '#92400e',
        'info': '#0c4a6e'
    };
    return colors[type] || colors['info'];
}

function formatMarkdown(text) {
    if (!text) return '';
    
    // 將文本中的換行符轉換為 HTML
    let html = escapeHtml(String(text));
    
    // 加粗文本 (**text** 或 __text__)
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');
    
    // 斜體文本 (*text* 或 _text_)
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    html = html.replace(/_(.*?)_/g, '<em>$1</em>');
    
    // 標題 (# text)
    html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
    
    // 連結 [text](url)
    html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>');
    
    // 新行符
    html = html.replace(/\n/g, '<br>');
    
    // 列表 (- item)
    html = html.replace(/^- (.*?)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*?<\/li>)/s, '<ul>$1</ul>');
    
    return html;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', () => {
    // 設置初始狀態
    stopBtn.disabled = true;
    
    // 檢查 API 連接
    fetch(`${API_BASE_URL.replace('/api', '')}/health`)
        .then(r => r.json())
        .catch(() => {
            console.warn('⚠️ 後端 API 未連接，請確保 api_server.py 正在運行');
        });
});

// 頁面卸載時停止爬蟲
window.addEventListener('beforeunload', () => {
    if (crawlTimer) {
        clearInterval(crawlTimer);
    }
});
