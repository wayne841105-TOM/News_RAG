import os
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime
import re
import json
from langchain_google_genai import ChatGoogleGenerativeAI

# [1. 環境初始化]
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# 延遲初始化模型
model = None


def get_model():
    """延遲初始化 Gemini 模型"""
    global model
    if model is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ 缺少 GEMINI_API_KEY 環境變數")
        model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=api_key)
    return model


SAVE_DIR = "news_archive"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)


# [輔助函式維持不變...]
def cleanup_old_news():
    now = time.time()
    expiry_seconds = 1200
    if os.path.exists(SAVE_DIR):
        for filename in os.listdir(SAVE_DIR):
            file_path = os.path.join(SAVE_DIR, filename)
            if (
                os.path.isfile(file_path)
                and (now - os.path.getmtime(file_path)) > expiry_seconds
            ):
                os.remove(file_path)


def clean_filename(filename):
    return re.sub(r'[\\/:\*\?"<>|]', "_", filename)


def check_if_exists(title):
    safe_title = clean_filename(title)
    if os.path.exists(SAVE_DIR):
        for f in os.listdir(SAVE_DIR):
            if safe_title in f:
                return True
    return False


def get_news_content(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    }
    try:
        if url.startswith("/"):
            url = "https://tw.news.yahoo.com" + url
        res = requests.get(url, headers=headers, timeout=15)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        # 移除不必要的標籤
        for script in soup(["script", "style", "footer", "nav", "iframe"]):
            script.extract()

        # 多種選擇器嘗試
        article = (
            soup.find("article")
            or soup.find("div", class_=lambda x: x and "article" in x)
            or soup.find("div", class_=lambda x: x and "story" in x)
        )

        if article:
            paragraphs = article.find_all("p", recursive=True)
        else:
            paragraphs = soup.find_all("p", limit=50)

        # 清理並組合文本
        content_parts = []
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 15:
                content_parts.append(text)

        content = "\n".join(content_parts)

        # 清理多餘換行
        if len(content) < 100:
            content = soup.get_text(separator="\n").strip()

        content = "\n".join(
            line.strip() for line in content.split("\n") if line.strip()
        )

        return content[:3000]
    except Exception as e:
        print(f"⚠️ 爬取內容失敗: {e}")
        return ""


def batch_filter_finance(news_list):
    if not news_list:
        return []
    prompt = "請從以下列表挑選出與『財經、股市、投資、宏觀政策、國際政治』相關的項目。僅回傳項目『編號』，以逗號分隔。若皆無相關回傳'None'。\n\n"
    for i, item in enumerate(news_list):
        prompt += f"{i}. {item['title']}\n"
    try:
        response = get_model().invoke(prompt)
        ans = response.content.strip().lower()
        if "none" in ans:
            return []
        return [int(s) for s in re.findall(r"\d+", ans)]
    except:
        return []


def send_line_message(text):
    """使用 Messaging API 發送訊息 (取代已過時的 Notify)"""
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.getenv("LINE_USER_ID")
    if not token or not user_id:
        return

    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    # Messaging API 格式：必須包含 messages 陣列
    payload = {"to": user_id, "messages": [{"type": "text", "text": text}]}

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"LINE 推送失敗: {res.text}")
    except Exception as e:
        print(f"LINE 連線錯誤: {e}")


# ---------------------------------------------------------
# [核心邏輯：改為 Generator 以支援逐字輸出]
# ---------------------------------------------------------
def run_finance_crawl():
    cleanup_old_news()
    # --- [修正點] 在最前面初始化變數，避免未定義錯誤 ---
    ui_logs = []
    log_content = "暫無新進日誌內容。"
    new_news_candidates = []

    url = "https://tw.news.yahoo.com/archive"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    current_time = datetime.now().strftime("%H:%M:%S")
    print(f"[{current_time}] 🔍 巡邏開始...")

    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        container = soup.find(id="stream-container-scroll-template")
        if not container:
            yield "❌ 警告：找不到新聞列表容器"
            return

        all_h3 = container.find_all("h3")[:5]

        # A. 第一階段：篩選新新聞
        for h3 in all_h3:
            a = h3.find("a")
            if not a:
                continue
            title = a.get_text(strip=True)
            if not check_if_exists(title):
                new_news_candidates.append({"title": title, "link": a.get("href")})

        header = f"### 📝 本次巡邏日誌 ({current_time})\n"

        # --- [修正點] 沒新聞時也確保有 header ---
        if not new_news_candidates:
            yield f"{header}\n\n😴 **系統狀態：** 目前前 5 則皆已處理過，系統進入待機模式。"
            return

        # B. 第二階段：批次分類
        finance_indices = batch_filter_finance(new_news_candidates)
        finance_news_for_analysis = []

        # C. 第三階段：處理內容
        for i, item in enumerate(new_news_candidates):
            content = get_news_content(item["link"])
            if content:
                # ... (中間存檔邏輯保持不變) ...
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                safe_title = clean_filename(item["title"])
                with open(
                    os.path.join(SAVE_DIR, f"{timestamp}_{safe_title}.txt"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(
                        f"標題: {item['title']}\n連結: {item['link']}\n內容:\n{content}"
                    )

                if i in finance_indices:
                    ui_logs.append(f"- 💰 **[新財經]** {item['title']}")
                    finance_news_for_analysis.append(
                        {"title": item["title"], "content": content}
                    )
                else:
                    ui_logs.append(f"- 📄 **[新一般]** {item['title']}")

            # --- [修正點] 更新 log_content 以供 yield 使用 ---
            log_content = "\n\n".join(ui_logs)
            yield f"{header}\n\n{log_content}\n\n---\n\n⏳ 正在處理中 ({i+1}/{len(new_news_candidates)})..."
            time.sleep(0.1)

        # D. 最終 AI 輸出
        if finance_news_for_analysis:
            payload = "\n".join(
                [
                    f"標題：{n['title']}\n內文：{n['content'][:800]}"
                    for n in finance_news_for_analysis
                ]
            )
            full_report = ""
            for chunk in get_model().stream(
                f"你是資深財經專家，請整合分析以新聞且不要超過300字：\n{payload}"
            ):
                full_report += chunk.content
                yield f"{header}\n\n{log_content}\n\n---\n\n### 🏮 深度財經 AI 報告\n\n{full_report}"

            # --- [關鍵新增] AI 報告生成完畢後，發送到 LINE ---
            line_push_text = f"💰 【AI 財經巡邏報告】\n\n{full_report}"
            # 如果內容太長，截斷避免 LINE 拒收 (上限 5000 字，建議 1000 以內閱讀體驗較佳)
            if len(line_push_text) > 800:
                line_push_text = line_push_text[:800] + "...\n(完整報告請見控制台)"

            send_line_message(line_push_text)
            # ---------------------------------------------

        else:
            msg = f"{header}\n\n{log_content}\n\n---\n\n✅ 掃描完成，無財經相關內容。"
            # 可選：若想確保系統有在動，沒財經新聞時也可發個簡短通知
            # send_line_message(f"✅ 巡邏完畢 ({current_time})\n目前無重大財經新聞。")
            yield msg

    except Exception as e:
        # --- [修正點] 錯誤發生時提供最後已知的資訊 ---
        yield f"⚠️ 執行出錯: {str(e)}"
