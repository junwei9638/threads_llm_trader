import json
import os
import pandas as pd
import numpy as np
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
請針對每一則貼文判斷是否包含投資建議。

請嚴格輸出 JSON 陣列，每個元素格式如下（包含原貼文 ID 以便對應）：
{
    "id": "貼文ID",
    "has_signal": true/false,
    "stocks": [
        {
            "symbol": "股票代碼 (例如 2330)",
            "action": "buy",
            "confidence": 0.0 ~ 1.0,
            "reason": "看好法說與外資買盤"
        }
    ]
}

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
                            # Fallback try to match by ID direct if strictly passed
                            original_post = next((p for p in batch if p.id == res.get("id")), None)

                        if not original_post:
                            continue

                        for s in res.get("stocks", []):
                            # User only requested BUY logic mainly, assuming 'action' checks
                            if s["action"].lower() != "buy":
                                continue

                            signals.append(Signal(
                                post_id=original_post.id or res.get("id"),
                                author=original_post.influencer,
                                post_time=original_post.post_time,
                                fetch_time=original_post.fetch_time,
                                gemini_decision="BUY",
                                confidence=float(s["confidence"]),
                                ticker=s["symbol"],
                                reason=s["reason"],
                                timestamp=original_post.timestamp,
                                entry_price=None,
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

class InfluencerManager:
    def __init__(self, stats_file: str = "data/influencer_stats.csv", trades_file: str = "data/trades.csv"):
        self.stats_file = stats_file
        self.trades_file = trades_file
        self.stats = self._load_stats()

    def _load_stats(self) -> pd.DataFrame:
        if os.path.exists(self.stats_file):
            return pd.read_csv(self.stats_file)
        # Cold start
        return pd.DataFrame(columns=["author", "total_trades", "wins", "losses", "win_rate", "weight"])

    def get_all_stats(self) -> pd.DataFrame:
        return self.stats

    def get_weight(self, author: str) -> float:
        if author not in self.stats["author"].values:
            return 1.0
        return float(self.stats[self.stats["author"] == author]["weight"].iloc[0])

    def update_stats(self):
        if not os.path.exists(self.trades_file):
            return
            
        trades = pd.read_csv(self.trades_file)
        # Assuming trades.csv has columns: symbol, author, buy_price, sell_price, pnl
        # If standard schema is different, we might need adjustments. 
        # User request says: symbol,author,buy_price,sell_price,pnl
        # But my Trade entity currently only saves when BUYING.
        # Implication: Another process (or manual) updates trades.csv with sell info?
        # OR I should calculate PnL if I had sell info.
        # For now, I'll assume trades.csv is the source of truth for COMPLETED trades.
        
        needed_cols = ["author", "pnl"]
        if not all(col in trades.columns for col in needed_cols):
             # If simple trades (just buys), we can't update performance yet.
             return

        for _, t in trades.iterrows():
            author = t["author"]
            pnl = t["pnl"]

            row = self.stats[self.stats["author"] == author]

            if row.empty:
                new_row = pd.DataFrame({"author": [author], "total_trades": [0], "wins": [0], "losses": [0], "win_rate": [0.5], "weight": [1.0]})
                self.stats = pd.concat([self.stats, new_row], ignore_index=True)
                row = self.stats[self.stats["author"] == author]

            idx = row.index[0]
            # Accumulate stats - Note: this simple logic re-counts trades if called repeatedly on same CSV.
            # In a real system we'd need a 'processed' flag or load only new trades.
            # But per user instructions "更新網紅績效程式", it reads whole file and iterates. 
            # I will assume this runs once or blindly re-calculates. 
            # To avoid double counting, I should probably Re-calculate from scratch based on trades.csv?
            # The prompt implies: "stats = pd.read... trades = pd.read... for ... iterrows".
            # If I run this repeatedly, I need to start from cold start stats each time to avoid infinite increment.
            pass
        
        # Re-calculate from scratch to be safe/idempotent
        self.stats = pd.DataFrame(columns=["author", "total_trades", "wins", "losses", "win_rate", "weight"])
        
        for _, t in trades.iterrows():
            author = t["author"]
            pnl = t["pnl"]

            if author not in self.stats["author"].values:
                new_row = pd.DataFrame({"author": [author], "total_trades": [0], "wins": [0], "losses": [0], "win_rate": [0.5], "weight": [1.0]})
                self.stats = pd.concat([self.stats, new_row], ignore_index=True)
            
            idx = self.stats[self.stats["author"] == author].index[0]
            self.stats.at[idx, "total_trades"] += 1
            if pnl > 0:
                self.stats.at[idx, "wins"] += 1
            else:
                self.stats.at[idx, "losses"] += 1
        
        # Calculate rates and weights
        self.stats["win_rate"] = self.stats["wins"] / self.stats["total_trades"].clip(lower=1)
        self.stats["weight"] = self.stats.apply(
            lambda r: self._calc_weight(r["win_rate"], r["total_trades"]),
            axis=1
        )
        
        # Save
        self.stats.to_csv(self.stats_file, index=False)

    def _calc_weight(self, win_rate, total_trades):
        confidence = min(1.0, total_trades / 20)
        return 0.5 + confidence * (win_rate - 0.5)
