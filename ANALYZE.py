import os
import json
import pandas as pd
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

# 1. 初始化 Gemini-2.5-flash 模型
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.1,  # 保持分析的嚴謹性
)


def run_deep_analysis():
    try:
        # 2. 讀取最新產出的 JSON 數據
        with open("0050_daily_kline.json", "r", encoding="utf-8") as f:
            kline_data = json.load(f)

        # 將 JSON 轉為美化字串，方便 AI 閱讀
        json_str = json.dumps(kline_data, indent=2, ensure_ascii=False)

        # 3. 定義專業分析 Prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是一位精通量化與籌碼分析的首席交易員。
                你的任務是解析 JSON 數據，並將技術指標與籌碼動向結合，產出具備實戰價值的 0050 分析報告。
                請保持語氣專業、嚴謹，直接點出關鍵位與警訊，避免冗贅言論。""",
                ),
                (
                    "user",
                    """以下是 0050 最新 20 筆技術指標與籌碼 JSON 數據：
                    
                {kline_json}

                請根據數據完成一份【0050 綜合診斷報告】：

                1. **趨勢與動量**：結合 MA5/MA20 判定多空，並利用 RSI、KD 判斷目前動能是否過熱或具備反彈契機。
                2. **籌碼面追蹤**：分析三大法人（外資/投信/自營商）近期買賣慣性。是否有「法人轉買、股價止跌」的底背離訊號？
                3. **斐波那契與空間**：
                    - **止跌區**：觀察收盤價與 fib_0.618、fib_0.500 的距離，評估支撐強度。
                    - **止盈點**：計算目前股價與 fib_1.618 (延伸位) 的空間。
                4. **布林軌道定位**：判斷價格位處通道何處（上軌、中軌、下軌），通道目前是擴張（噴發預兆）還是擠壓（盤整準備）。
                5. **實戰結論**：
                    - **短線預測**：看漲/看跌/盤整。
                    - **關鍵位**：支撐位（下方的 fib 位）與壓力位（上軌或 fib 延伸位）。
                    - **操作建議**：給出具體的「進場、觀望、或減碼」策略。
                6. **預測**:給出下個交易日的價格走勢預測，並說明理由。
                請使用繁體中文回覆，重點數值請加粗顯示。""",
                ),
            ]
        )

        # 4. 執行 Chain
        print("🤖 AI 正在掃描技術指標並撰寫報告...")
        chain = prompt | llm

        # 傳入 JSON 字串到 Prompt 中的 kline_json 變數
        response = chain.invoke({"kline_json": json_str})

        print("\n" + "★" * 60)
        print("📈 0050 深度 AI 技術分析報告")
        print("★" * 60)
        print(response.content)
        print("★" * 60)

    except FileNotFoundError:
        print("❌ 錯誤：找不到數據檔案，請先運行 FINMIND.py。")
    except Exception as e:
        print(f"💥 分析失敗: {e}")


if __name__ == "__main__":
    run_deep_analysis()
