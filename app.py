import gradio as gr
import logging
from main import run_finance_crawl
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
    gr.Markdown("# 🏮 AI 財經新聞監控控制台")

    # 隱藏的計時器
    timer = gr.Timer(value=600, active=False)

    # 狀態變數：儲存歷史紀錄列表
    history_state = gr.State([])

    with gr.Row():
        with gr.Column(scale=3):
            status_light = gr.HTML(STATUS_IDLE)

            timer_input = gr.Number(label="設定巡邏間隔 (分鐘)", value=10, precision=1)

            with gr.Row():
                start_btn = gr.Button("🚀 啟動自動巡邏", variant="primary")
                stop_btn = gr.Button("🛑 暫停巡邏", variant="stop")

            # 這裡就是你要的：明確提示目前的排程時間
            status_display = gr.Textbox(
                label="排程狀態與下次預告", value="目前狀態：待機中", interactive=False
            )

        with gr.Column(scale=5):
            report_output = gr.Markdown("### 📋 待機中，請啟動巡邏...")

        with gr.Column(scale=4):
            history_output = gr.Markdown("### 📜 歷史紀錄\n(尚無紀錄)")

    # --- 邏輯處理 ---

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
        # 簡單過濾無效內容
        if (
            not current_content
            or "待機中" in current_content
            or "正在處理" in current_content
        ):
            return history, format_history(history)

        # 避免重複 (比對最新的一筆)
        if history and history[0]["content"] == current_content:
            return history, format_history(history)

        # 解析時間與標題
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

        # 插入新紀錄
        history.insert(0, {"title": title, "content": current_content})
        if len(history) > 10:
            history = history[:10]

        return history, format_history(history)

    def format_history(history):
        if not history:
            return "### 📜 歷史紀錄\n(尚無紀錄)"

        md_text = "### 📜 歷史紀錄 (最近 10 筆)\n"
        for item in history:
            # 使用 HTML details 標籤製作折疊效果，並確保 markdown 內容前後有空行
            md_text += f"""
<details>
<summary style="font-weight:bold; cursor:pointer;">{item['title']}</summary>

{item['content']}

</details>
---
"""
        return md_text

    # 1. 點擊啟動
    start_btn.click(
        fn=enable_timer,
        inputs=[timer_input],
        outputs=[status_light, status_display, timer],
    ).then(
        fn=run_finance_crawl,  # 立即執行第一次 (逐字輸出)
        inputs=None,
        outputs=report_output,
        show_progress="minimal",
    ).then(
        fn=update_history,  # 執行完畢後更新歷史
        inputs=[report_output, history_state],
        outputs=[history_state, history_output],
    )

    # 2. 每次計時器觸發 (循環核心)
    timer.tick(
        fn=run_finance_crawl,
        inputs=None,
        outputs=report_output,
        show_progress="minimal",
    ).then(
        fn=update_history,  # 執行完畢後更新歷史
        inputs=[report_output, history_state],
        outputs=[history_state, history_output],
    ).then(
        # 重要：每次跑完後，更新介面上的「下次預告時間」
        fn=lambda m: get_next_run_time(m),
        inputs=[timer_input],
        outputs=[status_display],
    )

    # 3. 點擊暫停
    stop_btn.click(
        fn=disable_timer,
        inputs=None,
        outputs=[status_light, status_display, timer],
    )

if __name__ == "__main__":
    demo.launch(share=True)
