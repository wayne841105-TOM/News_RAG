"""
Flask API 伺服器 - 提供 REST API 給前端調用
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import logging
import threading
import time

from main import run_finance_crawl
from data_engine import (
    refresh_all_data,
    run_deep_analysis,
    get_chip_analysis,
    get_price_summary,
    get_latest_news,
)

# 設置日誌
logging.getLogger("asyncio").setLevel(logging.ERROR)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

# 全局狀態
crawl_thread = None
crawl_active = False
crawl_history = []


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """完整股票分析端點"""
    try:
        data = request.get_json()
        stock_code = data.get("stock_code", "0050")

        # 第一步：抓取數據
        if not refresh_all_data(stock_code):
            return jsonify({"success": False, "error": "無法載入數據"}), 400

        # 第二步：獲取股價摘要
        price_summary = get_price_summary(stock_code)

        # 第三步：獲取籌碼追蹤
        chip_summary = get_chip_analysis(stock_code)

        # 第四步：抓取最新新聞
        latest_news = get_latest_news(stock_code, count=10)

        # 第五步：執行 AI 分析
        ai_analysis = run_deep_analysis(stock_code)

        return jsonify(
            {
                "success": True,
                "stock_code": stock_code,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "price_summary": price_summary,
                "chip_summary": chip_summary,
                "ai_analysis": ai_analysis,
                "latest_news": latest_news,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/crawl", methods=["POST"])
def start_crawl():
    """啟動新聞爬蟲"""
    global crawl_thread, crawl_active

    try:
        if crawl_active:
            return jsonify({"success": False, "error": "爬蟲已在運行"}), 400

        crawl_active = True

        def run_crawl():
            global crawl_active, crawl_history
            try:
                result = run_finance_crawl()
                crawl_history.insert(
                    0,
                    {
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "status": "success",
                        "content": result,
                    },
                )
                if len(crawl_history) > 10:
                    crawl_history = crawl_history[:10]
            except Exception as e:
                crawl_history.insert(
                    0,
                    {
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "status": "error",
                        "content": str(e),
                    },
                )
            finally:
                crawl_active = False

        crawl_thread = threading.Thread(target=run_crawl, daemon=True)
        crawl_thread.start()

        return jsonify({"success": True, "message": "爬蟲已啟動"})
    except Exception as e:
        crawl_active = False
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/crawl-status", methods=["GET"])
def crawl_status():
    """獲取爬蟲狀態"""
    return jsonify({"active": crawl_active, "history": crawl_history})


@app.route("/api/stop-crawl", methods=["POST"])
def stop_crawl():
    """停止爬蟲"""
    global crawl_active
    crawl_active = False
    return jsonify({"success": True, "message": "爬蟲已停止"})


@app.route("/health", methods=["GET"])
def health():
    """健康檢查"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


if __name__ == "__main__":
    app.run(debug=True, host="localhost", port=5000)
