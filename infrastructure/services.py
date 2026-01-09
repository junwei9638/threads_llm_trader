import json
import pandas as pd
import google.generativeai as genai
from typing import List, Optional, Any
from core.interfaces import MarketAnalyzer, StockPriceProvider
from core.entities import Post, Signal
from FinMind.data import DataLoader

class GeminiMarketAnalyzer(MarketAnalyzer):
    def __init__(self, api_key: str, model_name: str = "gemini-flash-latest"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.system_prompt = """
你是一個股票訊號分析模型。
我會提供多則貼文，請針對每一則貼文判斷是否包含投資建議。

請嚴格輸出 JSON 陣列，格式如下：
[
    {
        "id": "貼文ID",
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
]
如果該貼文沒有投資訊號，has_signal 為 false，stocks 為空陣列。
絕對不要包含任何 Markdown 格式（如 ```json），只回傳純 JSON 字串。
"""

    def analyze_posts(self, posts: List[Post]) -> List[Signal]:
        signals = []
        batch_size = 10
        import time

        # Process in batches
        for i in range(0, len(posts), batch_size):
            batch = posts[i : i + batch_size]
            print(f"Processing batch {i//batch_size + 1} ({len(batch)} posts)...")
            
            # Prepare batch input
            batch_input = []
            for p in batch:
                # Use timestamp as temp ID if ID is missing or ensure ID mapping
                p_id = str(p.timestamp) 
                batch_input.append({"id": p_id, "content": p.content})
            
            try:
                batch_results = self._generate_batch_content_with_retry(batch_input)
                
                # Map results back to signals
                for res in batch_results:
                    if res.get("has_signal"):
                        # Find original post content
                        original_post = next((p for p in batch if str(p.timestamp) == res.get("id")), None)
                        
                        if not original_post:
                            continue

                        for s in res.get("stocks", []):
                            signals.append(Signal(
                                post_id=original_post.id or res.get("id"),
                                influencer=original_post.influencer,
                                post_time=original_post.post_time,
                                fetch_time=original_post.fetch_time,
                                gemini_decision=s["action"].upper(), # Normalize to BUY/SELL
                                confidence=float(s["confidence"]),
                                ticker=s["symbol"],
                                reason=s["reason"],
                                timestamp=original_post.timestamp,
                                entry_price=None, # To be filled by Use Case
                                entry_time=None
                            ))
            except Exception as e:
                print(f"Error processing batch: {e}")
            
            # Rate limit buffer
            time.sleep(2)
            
        return signals

    def _generate_batch_content_with_retry(self, batch_data: List[dict], retries=3) -> List[dict]:
        import time
        for attempt in range(retries):
            try:
                prompt_content = f"貼文列表：\n{json.dumps(batch_data, ensure_ascii=False)}"
                response = self.model.generate_content([
                    self.system_prompt,
                    prompt_content
                ])
                text = response.text.replace("```json", "").replace("```", "").strip()
                return json.loads(text)
            except Exception as e:
                print(f"Batch generation failed (attempt {attempt+1}/{retries}): {e}")
                if "429" in str(e) or "quota" in str(e).lower():
                    time.sleep(10 * (attempt + 1)) # Exponential backoff for rate limit
                else:
                    time.sleep(2)
        return []

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
