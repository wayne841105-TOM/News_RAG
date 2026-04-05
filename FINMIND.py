import os
import requests
import pandas as pd
import pandas_ta as ta
import datetime
import json
import difflib
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

FINMIND_API_KEY = os.getenv("FINMIND_API_KEY")
STOCK_ID = "0050"
URL = "https://api.finmindtrade.com/api/v4/data"

# 1. 時間與資料夾設定
today_str = datetime.date.today().strftime("%Y-%m-%d")
start_date = (datetime.date.today() - datetime.timedelta(days=120)).strftime("%Y-%m-%d")
news_start_date = (datetime.date.today() - datetime.timedelta(days=7)).strftime(
    "%Y-%m-%d"
)

NEWS_FOLDER = "news_data"
if not os.path.exists(NEWS_FOLDER):
    os.makedirs(NEWS_FOLDER)
    print(f"📁 已建立資料夾：{NEWS_FOLDER}")

# ==========================================
# 1. 抓取價格數據 (TaiwanStockPrice)
# ==========================================
price_param = {
    "dataset": "TaiwanStockPrice",
    "data_id": STOCK_ID,
    "start_date": start_date,
    "token": FINMIND_API_KEY,
}

price_resp = requests.get(URL, params=price_param)
price_data = price_resp.json().get("data", [])

if not price_data:
    print("❌ 抓取價格數據失敗")
    exit()

df = pd.DataFrame(price_data)
df.columns = [c.lower().strip() for c in df.columns]
df = df.rename(
    columns={"max": "high", "min": "low", "trading_volume": "volume", "vol": "volume"}
)
required = ["open", "high", "low", "close", "volume"]
df[required] = df[required].apply(pd.to_numeric, errors="coerce")
df["date"] = pd.to_datetime(df["date"])

# ==========================================
# 2. 抓取籌碼數據 (InstitutionalInvestorsBuySell)
# ==========================================
chip_param = {
    "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
    "data_id": STOCK_ID,
    "start_date": start_date,
    "token": FINMIND_API_KEY,
}

chip_resp = requests.get(URL, params=chip_param)
chip_data = chip_resp.json().get("data", [])

if chip_data:
    chip_df = pd.DataFrame(chip_data)
    chip_df["net_buy"] = chip_df["buy"] - chip_df["sell"]
    chip_pivot = chip_df.pivot_table(
        index="date", columns="name", values="net_buy", aggfunc="sum"
    ).fillna(0)
    chip_pivot.index = pd.to_datetime(chip_pivot.index)
    df = df.merge(chip_pivot, left_on="date", right_index=True, how="left").fillna(0)
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


# ==========================================
# 2.5 抓取新聞數據 (含內文抓取與去重)
# ==========================================
def fetch_content(url):
    """通用型新聞內文抓取函數"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")

        for script in soup(["script", "style", "footer", "nav"]):
            script.extract()

        article = (
            soup.find("article")
            or soup.find("div", class_="article-content")
            or soup.find("div", class_="story")
        )
        paragraphs = article.find_all("p") if article else soup.find_all("p")

        content = "\n".join(
            [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 10]
        )
        return content[:2000]
    except Exception:
        return ""


print(f"📰 正在處理 {STOCK_ID} 新聞去重與內文提取...")
news_param = {
    "dataset": "TaiwanStockNews",
    "data_id": STOCK_ID,
    "start_date": news_start_date,
    "token": FINMIND_API_KEY,
}
news_resp = requests.get(URL, params=news_param)
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
            # 如果 FinMind 已經有內文就直接用，沒有才去爬
            content = news.get("content", "")
            if not content or len(content) < 50:
                print(f"  └─ 正在爬取內文: {title[:15]}...")
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

    news_filename = f"{NEWS_FOLDER}/{STOCK_ID}_news_{today_str}.json"
    with open(news_filename, "w", encoding="utf-8") as f:
        json.dump(clean_news_output, f, indent=4, ensure_ascii=False)
    print(f"✅ 完成！儲存 {len(clean_news_output)} 則新聞內文。")

# ==========================================
# 3. 計算技術指標
# ==========================================
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

# ==========================================
# 4. 輸出 JSON
# ==========================================
df = df.dropna()
df_output = df.tail(20).copy()
df_output["date"] = df_output["date"].dt.strftime("%Y-%m-%d")
df_output = df_output.round(2)
df_output.to_json(
    "0050_daily_kline.json", orient="records", force_ascii=False, indent=4
)

print(f"✅ 數據整合成功！(價格/籌碼/技術/消息)")
