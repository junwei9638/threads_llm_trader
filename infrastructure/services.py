import json
import pandas as pd
import google.generativeai as genai
from typing import List, Optional, Any
from core.interfaces import MarketAnalyzer, StockPriceProvider
from core.entities import Post, Signal
from FinMind.data import DataLoader

class GeminiMarketAnalyzer(MarketAnalyzer):
    def __init__(self, api_key: str, model_name: str = "gemini-pro"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.system_prompt = """
你是一個股票訊號分析模型。
請從貼文中判斷是否包含投資建議。

請嚴格輸出 JSON，格式如下：
{
  "has_signal": true/false,
  "stocks": [
    {
      "symbol": "股票代碼 (例如 2330)",
      "action": "buy" | "sell",
      "confidence": 0.0 ~ 1.0,
      "reason": "簡短理由"
    }
  ]
}
如果沒有投資訊號，has_signal 為 false，stocks 為空陣列。
絕對不要包含任何 Markdown 格式（如 ```json），只回傳純 JSON 字串。
"""

    def analyze_posts(self, posts: List[Post]) -> List[Signal]:
        signals = []
        for p in posts:
            try:
                result = self._generate_content(p.content)
                if result.get("has_signal"):
                    for s in result.get("stocks", []):
                        signals.append(Signal(
                            symbol=s["symbol"],
                            action=s["action"],
                            confidence=float(s["confidence"]),
                            reason=s["reason"],
                            timestamp=p.timestamp,
                            original_content=p.content
                        ))
            except Exception as e:
                print(f"Error analyzing post: {e}")
        return signals

    def _generate_content(self, text: str) -> dict:
        try:
            response = self.model.generate_content([
                self.system_prompt,
                f"貼文內容：{text}"
            ])
            text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception:
            return {"has_signal": False}

class FinMindPriceProvider(StockPriceProvider):
    def __init__(self, token: str = ""):
        self.dl = DataLoader()
        if token:
            self.dl.login_by_token(api_token=token)

    def get_current_price(self, symbol: str) -> Optional[float]:
        try:
            # Fetch last 5 days
            df = self.dl.taiwan_stock_daily(
                stock_id=symbol,
                start_date=(pd.Timestamp.now() - pd.Timedelta(days=5)).strftime('%Y-%m-%d'),
            )
            if not df.empty:
                return float(df.iloc[-1]['close'])
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
        return None
