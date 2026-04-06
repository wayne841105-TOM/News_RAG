"""
數據整合引擎 - 統一管理 FINMIND、ANALYZE、NEWS 相關功能
"""

import os
import json
import requests
import pandas as pd
import pandas_ta as ta
import datetime
import difflib
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

# ==========================================
# 常數配置
# ==========================================
FINMIND_API_KEY = os.getenv("FINMIND_API_KEY")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
DEFAULT_STOCK_ID = "0050"  # 預設股票
FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"
NEWS_FOLDER = "news_data"

# 初始化 Gemini 模型（延遲初始化，避免啟動時驗證）
llm = None


def get_llm():
    """延遲初始化 Gemini 模型"""
    global llm
    if llm is None:
        if not GEMINI_API_KEY:
            raise ValueError("❌ 缺少 GEMINI_API_KEY 或 GOOGLE_API_KEY 環境變數")
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=GEMINI_API_KEY,
            temperature=0.1,
        )
    return llm


# ==========================================
# 1. FINMIND 數據抓取模塊
# ==========================================
def fetch_finmind_data(stock_id=DEFAULT_STOCK_ID):
    """
    抓取 FINMIND 數據：價格、籌碼、技術指標
    返回：(df, news_data)
    """
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=120)).strftime(
        "%Y-%m-%d"
    )
    news_start_date = (datetime.date.today() - datetime.timedelta(days=7)).strftime(
        "%Y-%m-%d"
    )

    # 確保新聞資料夾存在
    if not os.path.exists(NEWS_FOLDER):
        os.makedirs(NEWS_FOLDER)

    # --- 1.1 抓取價格數據 ---
    price_param = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": start_date,
        "token": FINMIND_API_KEY,
    }
    price_resp = requests.get(FINMIND_URL, params=price_param)
    price_data = price_resp.json().get("data", [])

    if not price_data:
        raise Exception("❌ 抓取價格數據失敗")

    df = pd.DataFrame(price_data)
    df.columns = [c.lower().strip() for c in df.columns]
    df = df.rename(
        columns={
            "max": "high",
            "min": "low",
            "trading_volume": "volume",
            "vol": "volume",
        }
    )
    required = ["open", "high", "low", "close", "volume"]
    df[required] = df[required].apply(pd.to_numeric, errors="coerce")
    df["date"] = pd.to_datetime(df["date"])

    # --- 1.2 抓取籌碼數據 ---
    chip_param = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
        "data_id": stock_id,
        "start_date": start_date,
        "token": FINMIND_API_KEY,
    }
    chip_resp = requests.get(FINMIND_URL, params=chip_param)
    chip_data = chip_resp.json().get("data", [])

    if chip_data:
        chip_df = pd.DataFrame(chip_data)
        chip_df["net_buy"] = chip_df["buy"] - chip_df["sell"]
        chip_pivot = chip_df.pivot_table(
            index="date", columns="name", values="net_buy", aggfunc="sum"
        ).fillna(0)
        chip_pivot.index = pd.to_datetime(chip_pivot.index)
        df = df.merge(chip_pivot, left_on="date", right_index=True, how="left").fillna(
            0
        )
        name_map = {
            "外資及陸資(不含外資自營商)": "foreign_investor",
            "投信": "investment_trust",
            "自營商": "dealer",
        }
        df = df.rename(columns=name_map)
        df["total_institutional_net"] = (
            df.get("foreign_investor", 0)
            + df.get("investment_trust", 0)
            + df.get("dealer", 0)
        )

    # --- 1.3 抓取新聞數據 ---
    news_raw_data = fetch_and_deduplicate_news(stock_id, news_start_date, today_str)

    # --- 1.4 計算技術指標 ---
    df = df.sort_values("date").reset_index(drop=True)
    df["rsi"] = ta.rsi(df["close"], length=14)
    df["ma5"] = ta.sma(df["close"], length=5)
    df["ma20"] = ta.sma(df["close"], length=20)
    bb = ta.bbands(df["close"], length=20, std=2)
    df["bb_upper"] = bb.iloc[:, 2]
    df["bb_lower"] = bb.iloc[:, 0]
    kd = ta.stoch(df["high"], df["low"], df["close"], k=9, d=3)
    df["k"] = kd.iloc[:, 0]
    df["d"] = kd.iloc[:, 1]

    # 斐波那契計算
    recent_high, recent_low = df["high"].max(), df["low"].min()
    diff = recent_high - recent_low
    df["fib_0.382"] = round(recent_high - (diff * 0.382), 2)
    df["fib_0.500"] = round(recent_high - (diff * 0.500), 2)
    df["fib_0.618"] = round(recent_high - (diff * 0.618), 2)
    df["fib_1.618"] = round(recent_low + (diff * 1.618), 2)

    # 輸出 JSON
    df = df.dropna()
    if len(df) > 0:
        df_output = df.tail(20).copy()
        df_output["date"] = df_output["date"].dt.strftime("%Y-%m-%d")
        df_output_rounded = df_output.round(2)
        kline_file = f"{stock_id}_daily_kline.json"
        df_output_rounded.to_json(
            kline_file, orient="records", force_ascii=False, indent=4
        )

    return df, news_raw_data


def fetch_and_deduplicate_news(stock_id, news_start_date, today_str):
    """抓取新聞並去重"""

    def fetch_content(url):
        """通用型新聞內文抓取函數 - 支援多種新聞網站"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            # 移除不必要的標籤
            for script in soup(["script", "style", "footer", "nav", "iframe"]):
                script.extract()

            # 多種選擇器嘗試 (優先順序)
            article = None
            if not article:
                article = soup.find("article")
            if not article:
                article = soup.find(
                    "div", class_=lambda x: x and "article-content" in x
                )
            if not article:
                article = soup.find("div", class_=lambda x: x and "story" in x)
            if not article:
                article = soup.find("div", class_=lambda x: x and "content" in x)
            if not article:
                article = soup.find("main")

            # 提取段落
            paragraphs = []
            if article:
                paragraphs = article.find_all("p", recursive=True)
            else:
                paragraphs = soup.find_all("p", limit=50)

            # 清理並組合文本
            content_parts = []
            for p in paragraphs:
                text = p.get_text().strip()
                if (
                    len(text) > 15
                    and not text.startswith("（")
                    and not text.endswith("）")
                ):
                    content_parts.append(text)

            content = "\n".join(content_parts)

            # 如果內容為空，嘗試取得所有文本
            if len(content) < 100:
                content = soup.get_text(separator="\n").strip()

            # 清理多餘換行
            content = "\n".join(
                line.strip() for line in content.split("\n") if line.strip()
            )

            return content[:3000]  # 增加到 3000 字限制
        except Exception as e:
            print(f"⚠️ 爬取 {url} 失敗: {e}")
            return ""

    news_param = {
        "dataset": "TaiwanStockNews",
        "data_id": stock_id,
        "start_date": news_start_date,
        "token": FINMIND_API_KEY,
    }
    news_resp = requests.get(FINMIND_URL, params=news_param)
    news_raw_data = news_resp.json().get("data", [])

    if news_raw_data:
        unique_news = []
        for news in news_raw_data:
            title = news["title"]
            link = news.get("link", "")
            clean_title = title.split(" - ")[0].split(" | ")[0].replace(" ", "").strip()

            is_duplicate = False
            for existing in unique_news:
                if (
                    difflib.SequenceMatcher(
                        None, clean_title, existing["clean_title"]
                    ).ratio()
                    > 0.8
                ):
                    is_duplicate = True
                    break

            if not is_duplicate and link:
                content = news.get("content", "")
                if not content or len(content) < 50:
                    content = fetch_content(link)

                news["clean_title"] = clean_title
                news["content"] = content
                unique_news.append(news)

        clean_news_output = [
            {
                "date": n["date"],
                "title": n["title"],
                "source": n.get("source", "N/A"),
                "content": n.get("content", ""),
                "link": n.get("link", ""),
            }
            for n in unique_news
        ]

        news_filename = f"{NEWS_FOLDER}/{stock_id}_news_{today_str}.json"
        with open(news_filename, "w", encoding="utf-8") as f:
            json.dump(clean_news_output, f, indent=4, ensure_ascii=False)

        return clean_news_output

    return []


# ==========================================
# 2. 新聞摘要模塊（LLM 驅動的摘要提取）
# ==========================================
def summarize_news(news_data, stock_id=DEFAULT_STOCK_ID):
    """
    對新聞內容進行 AI 摘要檢索
    將完整新聞內容濃縮為重點關鍵信息

    Args:
        news_data: [{"title": "...", "content": "...", "source": "..."}, ...]
        stock_id: 股票代碼

    Returns:
        [{"title": "...", "summary": "...", "source": "..."}, ...]
    """
    if not news_data or len(news_data) == 0:
        print("📝 查無新聞數據，跳過摘要")
        return []

    try:
        print(f"📝 開始新聞摘要流程，共 {len(news_data)} 則新聞")
        summarized_news = []

        for idx, news in enumerate(news_data[:5]):  # 最多摘要 5 則
            title = news.get("title", "N/A")
            content = news.get("content", "")
            source = news.get("source", "N/A")

            # 如果內容太短或為空，跳過摘要
            if len(content) < 50:
                summarized_news.append(
                    {
                        "title": title,
                        "summary": content if content else "內容不足，無法摘要",
                        "source": source,
                    }
                )
                continue

            # 使用 LLM 進行摘要
            try:
                prompt = f"""請簡潔地摘要以下新聞，提取對 {stock_id} 股價最相關的關鍵信息。摘要需要包括：
1. 新聞核心事件（1-2 句）
2. 對股票的潛在影響（利多/利空/中立）
3. 預期影響程度（高/中/低）

新聞標題：{title}

新聞內容：
{content[:1500]}

請用繁體中文回覆，控制在 100 字以內。"""

                print(f"   🔄 [摘要 {idx+1}/5] 正在處理: {title[:50]}...")
                print(f"   📊 Prompt 字數: {len(prompt)}, 內容長度: {len(content)}")

                try:
                    llm_instance = get_llm()
                    print(f"   ✅ LLM 實例已初始化")

                    response = llm_instance.invoke(prompt)

                    if response and hasattr(response, "content"):
                        summary = response.content.strip()
                        print(f"   ✅ 摘要成功 (字數: {len(summary)})")
                        summarized_news.append(
                            {"title": title, "summary": summary, "source": source}
                        )
                    else:
                        print(f"   ⚠️ LLM 響應異常: {response}")
                        first_paragraph = content.split("\n")[0]
                        summarized_news.append(
                            {
                                "title": title,
                                "summary": first_paragraph[:200],
                                "source": source,
                            }
                        )

                except ValueError as ve:
                    print(f"   ❌ API 額度錯誤: {ve}")
                    print(f"   💡 請檢查 GEMINI_API_KEY 額度是否不足")
                    first_paragraph = content.split("\n")[0]
                    summarized_news.append(
                        {
                            "title": title,
                            "summary": first_paragraph[:200],
                            "source": source,
                        }
                    )
                except PermissionError as pe:
                    print(f"   ❌ 權限錯誤: {pe}")
                    print(f"   💡 請檢查 API Key 是否正確")
                    first_paragraph = content.split("\n")[0]
                    summarized_news.append(
                        {
                            "title": title,
                            "summary": first_paragraph[:200],
                            "source": source,
                        }
                    )
                except Exception as llm_e:
                    print(f"   ❌ LLM 呼叫失敗: {type(llm_e).__name__}: {llm_e}")
                    print(f"   📋 詳細錯誤: {str(llm_e)}")
                    first_paragraph = content.split("\n")[0]
                    summarized_news.append(
                        {
                            "title": title,
                            "summary": first_paragraph[:200],
                            "source": source,
                        }
                    )

            except Exception as e:
                print(f"⚠️ 摘要生成失敗 ({title}): {e}")
                # 降級：使用首段作為摘要
                first_paragraph = content.split("\n")[0]
                summarized_news.append(
                    {"title": title, "summary": first_paragraph[:200], "source": source}
                )

        return summarized_news

    except Exception as e:
        print(f"❌ 新聞摘要流程失敗: {type(e).__name__}: {e}")
        print(f"📋 詳細錯誤訊息: {str(e)}")
        return []


# ==========================================
# 3. 深度分析模塊（基於 ANALYZE.py）
# ==========================================
def run_deep_analysis(stock_id=DEFAULT_STOCK_ID, news_data=None):
    """執行 AI 深度技術分析

    Args:
        stock_id: 股票代碼
        news_data: 最新新聞列表，格式為 [{"title": "...", "content": "..."}, ...]
    """
    try:
        print(f"\n{'='*60}")
        print(f"🚀 開始執行深度分析流程: {stock_id}")
        print(f"{'='*60}")

        kline_file = f"{stock_id}_daily_kline.json"
        print(f"📂 加載 K 線數據: {kline_file}")

        with open(kline_file, "r", encoding="utf-8") as f:
            kline_data = json.load(f)

        print(f"   ✅ K 線數據加載成功，{len(kline_data)} 筆記錄")

        json_str = json.dumps(kline_data, indent=2, ensure_ascii=False)

        # 【新增：新聞摘要檢索】先對新聞進行 AI 摘要
        summarized_news = []
        news_section = ""
        if news_data and len(news_data) > 0:
            print(f"\n📰 進行新聞摘要檢索...")
            summarized_news = summarize_news(news_data, stock_id)

            if summarized_news:
                print(f"   ✅ 新聞摘要完成，{len(summarized_news)} 則新聞已精煉")
                news_section = "\n\n### 📰 最新新聞摘要（已精煉）：\n"
                for idx, news in enumerate(summarized_news, 1):
                    news_section += f"{idx}. **{news.get('title', 'N/A')}**（來源：{news.get('source', 'N/A')}）\n"
                    news_section += f"   摘要：{news.get('summary', 'N/A')}\n\n"
            else:
                print(f"   ⚠️ 新聞摘要失敗或無有效數據")
        else:
            print(f"   ℹ️  無新聞數據，跳過新聞摘要")

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    f"""你是一位精通量化與籌碼分析的首席交易員。
                    你的任務是解析 JSON 數據，並將技術指標與籌碼動向，以及最新新聞事件結合，產出具備實戰價值的 {stock_id} 分析報告。
                    請保持語氣專業、嚴謹，直接點出關鍵位與警訊，避免冗贅言論。""",
                ),
                (
                    "user",
                    f"""以下是 {stock_id} 最新 20 筆技術指標與籌碼 JSON 數據：
                    
{{kline_json}}{news_section}

請根據數據與新聞事件完成一份【{stock_id} 綜合診斷報告】：

1. **趨勢與動量**：結合 MA5/MA20 判定多空，並利用 RSI、KD 判斷目前動能是否過熱或具備反彈契機。
2. **籌碼面追蹤**：分析三大法人（外資/投信/自營商）近期買賣慣性。是否有「法人轉買、股價止跌」的底背離訊號？
3. **斐波那契與空間**：
    - **止跌區**：觀察收盤價與 fib_0.618、fib_0.500 的距離，評估支撐強度。
    - **止盈點**：計算目前股價與 fib_1.618 (延伸位) 的空間。
4. **布林軌道定位**：判斷價格位處通道何處（上軌、中軌、下軌），通道目前是擴張（噴發預兆）還是擠壓（盤整準備）。
5. **新聞面影響分析**：根據最新新聞事件摘要，評估對股價的潛在影響。是否有利多、利空訊號？
6. **實戰結論**：
    - **短線預測**：看漲/看跌/盤整。
    - **關鍵位**：支撐位（下方的 fib 位）與壓力位（上軌或 fib 延伸位）。
    - **操作建議**：給出具體的「進場、觀望、或減碼」策略。
7. **預測**:給出下個交易日的價格走勢預測，並說明理由。
請使用繁體中文回覆，重點數值請加粗顯示。""",
                ),
            ]
        )

        chain = prompt | get_llm()

        print(f"\n🤖 開始 AI 深度分析：{stock_id}")
        print(f"📊 技術數據點數: {len(kline_data)}")
        print(f"📰 新聞摘要段數: {len(summarized_news) if news_section else 0}")

        try:
            print(f"   🔄 正在調用 Gemini LLM 進行綜合分析...")
            response = chain.invoke({"kline_json": json_str})

            if response and response.content:
                result_length = len(response.content)
                print(f"   ✅ AI 分析成功 (回應字數: {result_length})")
                return response.content
            else:
                print(f"   ⚠️ AI 分析結果異常: {response}")
                return "❌ AI 回應異常，無法生成分析報告"

        except ValueError as ve:
            print(f"   ❌ API 額度錯誤: {ve}")
            print(f"   💡 可能原因:")
            print(f"       • GEMINI_API_KEY 月額度已用盡")
            print(f"       • API Key 格式錯誤")
            print(
                f"       • 請至 Google AI Studio 檢查額度: https://aistudio.google.com/app/apikey"
            )
            return f"❌ API 額度不足或配置錯誤: {ve}"

        except PermissionError as pe:
            print(f"   ❌ 權限/認證錯誤: {pe}")
            print(f"   💡 可能原因:")
            print(f"       • API Key 無效或過期")
            print(f"       • GEMINI_API_KEY 環境變數設置錯誤")
            return f"❌ API 認證失敗: {pe}"

        except Exception as analysis_e:
            print(f"   ❌ LLM 分析失敗: {type(analysis_e).__name__}")
            print(f"   📋 錯誤詳情: {str(analysis_e)}")
            import traceback

            print(f"   🔍 完整堆棧:")
            traceback.print_exc()
            return f"💥 分析失敗: {type(analysis_e).__name__}: {analysis_e}"

    except FileNotFoundError as fnf:
        print(f"\n❌ 文件未找到錯誤: {fnf}")
        print(f"💡 請確保已執行以下步驟:")
        print(f"   1. 點擊「🚀 完整分析」按鈕進行數據抓取")
        print(f"   2. 等待 K 線數據文件生成: {stock_id}_daily_kline.json")
        return "❌ 錯誤：找不到數據檔案，請先執行數據抓取。"

    except json.JSONDecodeError as je:
        print(f"\n❌ JSON 解析錯誤: {je}")
        print(f"💡 K 線數據文件可能損壞，請重新抓取")
        return "❌ 數據文件損壞，請重新執行數據抓取。"

    except Exception as e:
        print(f"\n❌ 未預期的錯誤: {type(e).__name__}")
        print(f"📋 錯誤訊息: {str(e)}")
        import traceback

        print(f"🔍 完整堆棧:")
        traceback.print_exc()
        return f"💥 分析失敗: {type(e).__name__}: {str(e)}"


# ==========================================
# 4. 籌碼追蹤模塊
# ==========================================
def get_chip_analysis(stock_id=DEFAULT_STOCK_ID):
    """獲取籌碼面分析"""
    try:
        kline_file = f"{stock_id}_daily_kline.json"
        with open(kline_file, "r", encoding="utf-8") as f:
            kline_data = json.load(f)

        if not kline_data:
            return "📊 暫無籌碼數據"

        df_display = pd.DataFrame(kline_data)

        # 只保留有籌碼數據的欄位
        chip_cols = [
            "date",
            "close",
            "foreign_investor",
            "investment_trust",
            "dealer",
            "total_institutional_net",
        ]
        available_cols = [col for col in chip_cols if col in df_display.columns]
        df_chip = df_display[available_cols].tail(10)

        # 轉為 markdown 表格
        markdown_table = df_chip.to_markdown(index=False)

        # 簡要分析
        latest = df_display.iloc[-1]
        total_net = latest.get("total_institutional_net", 0)
        sentiment = (
            "👍 法人淨買"
            if total_net > 0
            else ("👎 法人淨賣" if total_net < 0 else "➡️ 法人中立")
        )

        return f"""### 📊 籌碼追蹤

**最新籌碼狀態**：{sentiment} (淨額：{total_net:+.0f})

**近 10 日籌碼數據**：
{markdown_table}

**分析**：
- 外資(GSIS)：{latest.get('foreign_investor', 0):+.0f}
- 投信：{latest.get('investment_trust', 0):+.0f}
- 自營商：{latest.get('dealer', 0):+.0f}
"""

    except Exception as e:
        return f"❌ 籌碼分析失敗: {e}"


# ==========================================
# 5. 股價走勢摘要
# ==========================================
def get_price_summary(stock_id=DEFAULT_STOCK_ID):
    """獲取股價走勢摘要"""
    try:
        kline_file = f"{stock_id}_daily_kline.json"
        with open(kline_file, "r", encoding="utf-8") as f:
            kline_data = json.load(f)

        if not kline_data:
            return "📈 暫無股價數據"

        df = pd.DataFrame(kline_data)
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        change = latest["close"] - prev["close"]
        change_pct = (change / prev["close"] * 100) if prev["close"] != 0 else 0

        arrow = "📈" if change > 0 else ("📉" if change < 0 else "➡️")

        summary = f"""### 📈 股價走勢

**最新行情** (日期：{latest['date']})：
- **收盤價**：${latest['close']:.2f} {arrow}
- **漲跌**：{change:+.2f} ({change_pct:+.2f}%)
- **開盤**：${latest['open']:.2f}
- **高**：${latest['high']:.2f}
- **低**：${latest['low']:.2f}
- **成交量**：{int(latest.get('volume', 0)):,}

**技術指標**：
- **RSI(14)**：{latest.get('rsi', 'N/A')}
- **MA5**：${latest.get('ma5', 'N/A'):.2f}
- **MA20**：${latest.get('ma20', 'N/A'):.2f}
- **K值**：{latest.get('k', 'N/A')}
- **D值**：{latest.get('d', 'N/A')}

**支撐壓力**：
- **上軌(BB)**：${latest.get('bb_upper', 'N/A'):.2f}
- **下軌(BB)**：${latest.get('bb_lower', 'N/A'):.2f}
- **斐波0.618**：${latest.get('fib_0.618', 'N/A'):.2f}
- **斐波1.618**：${latest.get('fib_1.618', 'N/A'):.2f}
"""
        return summary

    except Exception as e:
        return f"❌ 股價摘要失敗: {e}"


# ==========================================
# 6. 新聞數據模塊
# ==========================================
def get_latest_news(stock_id=DEFAULT_STOCK_ID, count=5):
    """獲取最新新聞"""
    try:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        news_file = f"{NEWS_FOLDER}/{stock_id}_news_{today_str}.json"

        if not os.path.exists(news_file):
            return "📰 暫無今日新聞"

        with open(news_file, "r", encoding="utf-8") as f:
            news_data = json.load(f)

        news_list = news_data[:count]
        markdown_news = "### 📰 最新新聞\n\n"

        for idx, news in enumerate(news_list, 1):
            markdown_news += f"""
<details>
<summary><strong>{idx}. {news.get('title', 'N/A')}</strong> (來源：{news.get('source', 'N/A')})</summary>

{news.get('content', '內容載入中...')[:500]}

[完整文章→]({news.get('link', '#')})

</details>
"""

        return markdown_news

    except Exception as e:
        return f"❌ 新聞載入失敗: {e}"


# ==========================================
# 7. 整體更新函數
# ==========================================
def refresh_all_data(stock_id=DEFAULT_STOCK_ID):
    """一次更新所有數據"""
    try:
        print(f"🔄 正在更新 {stock_id} 的所有數據...")
        fetch_finmind_data(stock_id)
        print("✅ 數據更新完成")
        return True
    except Exception as e:
        print(f"❌ 數據更新失敗: {e}")
        return False
