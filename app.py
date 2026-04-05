import gradio as gr
import logging
from main import run_finance_crawl
from data_engine import (
    refresh_all_data,
    run_deep_analysis,
    get_chip_analysis,
    get_price_summary,
    get_latest_news,
)
from datetime import datetime, timedelta
import re

# 1. 忽略雜訊
logging.getLogger("asyncio").setLevel(logging.ERROR)

STATUS_IDLE = '<div style="display:flex;align-items:center;"><div style="width:12px;height:12px;background-color:#bbb;border-radius:50%;margin-right:8px;"></div><span style="color:#666;">巡邏停止中</span></div>'
STATUS_RUNNING = """
<div style="display:flex;align-items:center;">
    <div style="width:12px;height:12px;background-color:#2ecc71;border-radius:50%;margin-right:8px;box-shadow: 0 0 8px #2ecc71;animation: breathe 2s infinite;"></div>
    <span style="color:#27ae60;font-weight:bold;">自動巡邏守衛運行中...</span>
    <style>
        @keyframes breathe {
            0% { opacity: 0.4; box-shadow: 0 0 2px #2ecc71; }
            50% { opacity: 1; box-shadow: 0 0 12px #2ecc71; }
            100% { opacity: 0.4; box-shadow: 0 0 2px #2ecc71; }
        }
    </style>
</div>
"""


def get_next_run_time(minutes):
    """計算下一次巡邏的時間點"""
    next_time = datetime.now() + timedelta(minutes=minutes)
    return f"🟢 運行中 | 下次巡邏預計：{next_time.strftime('%H:%M:%S')}"


with gr.Blocks(theme=gr.themes.Soft(), title="AI 財經監控") as demo:
    gr.Markdown("# 🏮 AI 財經綜合監控平台")
    gr.Markdown("**整合新聞爬取、技術分析、籌碼追蹤、趨勢預測**")

    # 全局狀態變數
    timer = gr.Timer(value=600, active=False)
    history_state = gr.State([])
    data_refresh_state = gr.State(False)

    with gr.Tabs():
        # ========================================
        # 標簽 1: 📈 股票分析 (整合儀表板 + 技術分析)
        # ========================================
        with gr.Tab("📈 股票分析"):
            # 控制面板：股票輸入 + 分析按鈕
            with gr.Row():
                with gr.Column(scale=1):
                    stock_input = gr.Textbox(
                        label="輸入股票代碼",
                        value="0050",
                        placeholder="如: 0050, 2330, 1101",
                    )

                with gr.Column(scale=1):
                    gr.Markdown("### ")  # 空間
                    analyze_btn = gr.Button(
                        "🚀 完整分析 (數據+AI)", variant="primary", size="lg"
                    )

            status_text = gr.Textbox(
                label="分析狀態", value="✅ 就緒", interactive=False
            )

            # 分析結果展示區
            with gr.Row():
                price_display = gr.Markdown("### 📈 股價走勢\n等待分析...")

            with gr.Row():
                chip_display = gr.Markdown("### 📊 籌碼追蹤\n等待分析...")

            with gr.Row():
                analysis_output = gr.Markdown("### 🤖 AI 深度分析\n等待分析...")

            # 整合分析邏輯：抓取數據 + 顯示結果 + AI 分析
            def full_analysis(stock_code):
                status = "🔄 正在抓取數據..."

                # 第一步：抓取數據
                if not refresh_all_data(stock_code):
                    return (
                        "❌ 數據抓取失敗",
                        "❌ 無法載入數據",
                        "❌ 無法載入數據",
                        "❌ 無法載入數據",
                    )

                # 第二步：獲取股價摘要
                price_summary = get_price_summary(stock_code)

                # 第三步：獲取籌碼追蹤
                chip_summary = get_chip_analysis(stock_code)

                # 第四步：執行 AI 深度分析
                status = "🔄 正在執行 AI 分析..."
                ai_analysis = run_deep_analysis(stock_code)

                status = "✅ 分析完成 @ " + datetime.now().strftime("%H:%M:%S")

                return status, price_summary, chip_summary, ai_analysis

            # 點擊【完整分析】按鈕 → 執行完整流程
            analyze_btn.click(
                fn=full_analysis,
                inputs=[stock_input],
                outputs=[status_text, price_display, chip_display, analysis_output],
            )

        # ========================================
        # 標簽 2: 📰 新聞監控 (奇摩新聞自動巡邏)
        # ========================================
        with gr.Tab("📰 新聞監控"):
            gr.Markdown("**自動巡邏奇摩新聞，定期爬取財經相關內容**")

            status_light = gr.HTML(STATUS_IDLE)
            timer_input = gr.Number(label="設定巡邏間隔 (分鐘)", value=10, precision=1)

            with gr.Row():
                start_btn = gr.Button("🚀 啟動自動巡邏", variant="primary")
                stop_btn = gr.Button("🛑 暫停巡邏", variant="stop")

            status_display = gr.Textbox(
                label="排程狀態與下次預告", value="目前狀態：待機中", interactive=False
            )

            with gr.Row():
                with gr.Column(scale=3):
                    report_output = gr.Markdown("### 📋 待機中，請啟動巡邏...")
                with gr.Column(scale=2):
                    history_output = gr.Markdown("### 📜 歷史紀錄\n(尚無紀錄)")

            # 新聞監控邏輯
            def enable_timer(minutes):
                return (
                    STATUS_RUNNING,
                    get_next_run_time(minutes),
                    gr.Timer(value=minutes * 60, active=True),
                )

            def disable_timer():
                return STATUS_IDLE, "🔴 已停止巡邏", gr.Timer(active=False)

            def update_history(current_content, history):
                """更新歷史紀錄，只保留前 10 筆"""
                if (
                    not current_content
                    or "待機中" in current_content
                    or "正在處理" in current_content
                ):
                    return history, format_history(history)

                if history and history[0]["content"] == current_content:
                    return history, format_history(history)

                timestamp = datetime.now().strftime("%H:%M")
                time_match = re.search(r"本次巡邏日誌 \((.*?)\)", current_content)
                if time_match:
                    timestamp = time_match.group(1)

                title_suffix = (
                    "💰 發現財經焦點"
                    if "深度財經 AI 報告" in current_content
                    else "💤 無重大發現"
                )
                title = f"[{timestamp}] {title_suffix}"

                history.insert(0, {"title": title, "content": current_content})
                if len(history) > 10:
                    history = history[:10]

                return history, format_history(history)

            def format_history(history):
                if not history:
                    return "### 📜 歷史紀錄\n(尚無紀錄)"

                md_text = "### 📜 歷史紀錄 (最近 10 筆)\n"
                for item in history:
                    md_text += f"""
<details>
<summary style="font-weight:bold; cursor:pointer;">{item['title']}</summary>

{item['content']}

</details>
---
"""
                return md_text

            start_btn.click(
                fn=enable_timer,
                inputs=[timer_input],
                outputs=[status_light, status_display, timer],
            ).then(
                fn=run_finance_crawl,
                inputs=None,
                outputs=report_output,
                show_progress="minimal",
            ).then(
                fn=update_history,
                inputs=[report_output, history_state],
                outputs=[history_state, history_output],
            )

            timer.tick(
                fn=run_finance_crawl,
                inputs=None,
                outputs=report_output,
                show_progress="minimal",
            ).then(
                fn=update_history,
                inputs=[report_output, history_state],
                outputs=[history_state, history_output],
            ).then(
                fn=lambda m: get_next_run_time(m),
                inputs=[timer_input],
                outputs=[status_display],
            )

            stop_btn.click(
                fn=disable_timer,
                inputs=None,
                outputs=[status_light, status_display, timer],
            )

        # ========================================
        # 標簽 3: 📑 最新新聞
        # ========================================
        with gr.Tab("📑 最新新聞"):
            with gr.Row():
                with gr.Column(scale=2):
                    stock_input_news_list = gr.Textbox(
                        label="輸入股票代碼",
                        value="0050",
                        placeholder="如: 0050, 2330, 1101",
                    )
                with gr.Column(scale=1):
                    news_count = gr.Slider(
                        minimum=1, maximum=20, value=5, step=1, label="顯示新聞數量"
                    )

            news_output = gr.Markdown("### 📰 最新新聞\n載入中...")
            news_refresh_btn = gr.Button("🔄 重新載入新聞", variant="primary")

            def load_news(stock_code, count):
                return get_latest_news(stock_code, int(count))

            def on_news_change(stock_code, count):
                return load_news(stock_code, count)

            news_refresh_btn.click(
                fn=load_news,
                inputs=[stock_input_news_list, news_count],
                outputs=news_output,
            )
            stock_input_news_list.change(
                fn=on_news_change,
                inputs=[stock_input_news_list, news_count],
                outputs=news_output,
            )
            news_count.change(
                fn=on_news_change,
                inputs=[stock_input_news_list, news_count],
                outputs=news_output,
            )

if __name__ == "__main__":
    demo.launch(share=True)
