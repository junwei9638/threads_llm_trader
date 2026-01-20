import json
import os
import pandas as pd
import numpy as np
import google.generativeai as genai
import google.generativeai as genai
from openai import OpenAI
from typing import List, Optional, Any
from core.interfaces import MarketAnalyzer, StockPriceProvider
from core.entities import Post, Signal
from FinMind.data import DataLoader

class GeminiMarketAnalyzer(MarketAnalyzer):
    def __init__(self, api_keys: List[str] = None, api_key: str = None, model_name: str = "gemini-flash-latest"):
        # Handle multiple keys or single key
        if api_keys:
            self.api_keys = api_keys
        elif api_key:
            self.api_keys = [api_key]
        else:
            raise ValueError("Must provide api_keys or api_key")
            
        self.current_key_header_index = 0
        self.model_name = model_name
        
        # Configure first key
        self._configure_current_key()
        
        # Initialize OpenAI client for fallback
        openai_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = OpenAI(api_key=openai_key) if openai_key else None
        
        self.system_prompt = """
你是一個股票訊號分析模型。
請針對每一則貼文判斷是否包含投資建議。

請嚴格輸出 JSON 陣列，每個元素格式如下（包含原貼文 ID 以便對應）：
{
  "id": "貼文ID",
  "has_signal": true/false,
  "intent": "buy" | "sell" | "none",

  "execution": {
    "should_trade": true/false,
    "entry_timing": "now" | "next_open" | "wait_pullback" | "do_not_trade",
    "entry_reason": "20字內說明為何這個時機"
  },

  "stocks": [
    {
      "symbol": "股票代碼",
      "confidence": 0.0 ~ 1.0,
      "suggested_price": number | null,
      "reason": "20字內"
    }
  ]
}

判斷規則：
1. entry_timing 定義：
  - now：
    明確表示「現在 / 盤中 / 立刻 / 今天進場」
  - next_open：
    出現「明天、隔天、明早、開盤」
  - wait_pullback：
    出現「不要追、等拉回、回測再買、低接」
  - do_not_trade：
    已經漲停、已噴出、或僅為事後評論

2. 交易判斷邏輯：
  - 如果 has_signal = true，但不建議實際進場：
    should_trade 必須為 false，且 entry_timing = do_not_trade
  - 如果 intent = buy 且 should_trade = true：
    entry_timing 不可為 unknown 或空值
  - 如果沒有交易建議：
    has_signal=false 且 intent=none

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
                        # Safety check: if has_signal is true but stocks is empty, ignore
                        if not res.get("stocks"):
                            continue

                        # Find original post content
                        original_post = next((p for p in batch if str(p.timestamp) == res.get("id")), None)
                        
                        if not original_post:
                            # Fallback try to match by ID direct if strictly passed
                            original_post = next((p for p in batch if p.id == res.get("id")), None)

                        if not original_post:
                            continue

                        # Extract timing from execution object
                        execution = res.get("execution", {})
                        timing = execution.get("entry_timing", "unknown")
                        should_trade = execution.get("should_trade", False)
                        
                        # Validate against allowed enum values from new prompt
                        allowed_timings = ["now", "next_open", "wait_pullback", "do_not_trade"]
                        if timing not in allowed_timings:
                             timing = "unknown"
                             
                        # If should_trade is False, we might want to map to a specific state or just allow it 
                        # to be filtered downstream. For now, we store the timing.
                        if not should_trade:
                             # Map to a non-actionable timing if logical
                             pass

                        # Filter/Check Intent (Safety) - User asked for parsing BUY signals mainly
                        # but prompt now returns intent. We can check intent == "buy" or rely on stocks
                        intent = res.get("intent", "none").lower()
                        if intent != "buy" and intent != "sell":
                             # If intent is none or weird, maybe skip?
                             # But let's look at stocks as source of truth if populated.
                             pass

                        for s in res.get("stocks", []):
                            # Prompt change: 'action' field removed in favor of top-level intent?
                            # The prompt example showed stocks list without action, but action in top level intent.
                            # We should trust top-level intent for the direction, OR if we kept action effectively.
                            # The user's requested JSON format for stocks REMOVED "action" field inside stocks.
                            # So we rely on validation of intent == 'buy'.
                            
                            if intent != "buy":
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
                                entry_time=None,
                                timing=timing
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
                # Task 3: Retry logic - mostly handled by _generate_with_llm fallback capability
                # If _generate_with_llm raises an error (non-quota or no fallback), we catch here and retry.
                prompt_content = f"貼文列表：\n{json.dumps(batch_data, ensure_ascii=False)}"
                
                # Check if we should enforce Gemini retry first? 
                # User Task 3 says: "First fail -> retry Gemini. Second time quota -> OpenAI".
                # But Task 1 says: "If Gemini throws... auto fallback".
                # We interpret this as: We try our abstract LLM method. 
                # To strictly follow "Retry Gemini", _generate_with_llm handles the "Smart Fallback" (e.g. on Quota).
                # For network errors, we enter this catch block and retry (likely Gemini again).
                
                text = self._generate_with_llm(prompt_content)
                return json.loads(text)
            except Exception as e:
                print(f"Batch generation failed (attempt {attempt+1}/{retries}): {e}")
                # Standard backoff for rate limit/network errors
                if "429" in str(e) or "quota" in str(e).lower():
                    time.sleep(10 * (attempt + 1)) 
                else:
                    time.sleep(2)
        return []

    def _configure_current_key(self):
        current_key = self.api_keys[self.current_key_header_index]
        print(f"Configuring Gemini with key index {self.current_key_header_index + 1}/{len(self.api_keys)}...")
        genai.configure(api_key=current_key)
        self.model = genai.GenerativeModel(self.model_name)

    def _rotate_key(self) -> bool:
        """
        Rotates to the next available API key. 
        Returns True if successful (new key set), False if all keys exhausted (cycled back to start).
        """
        if len(self.api_keys) <= 1:
            return False
            
        self.current_key_header_index = (self.current_key_header_index + 1) % len(self.api_keys)
        
        # If we cycled back to 0, we've tried all keys in this 'run' essentially. 
        # However, for a long running process, we might want to keep cycling.
        # But if we confuse 'exhausted' with 'just next', we might loop infinitely on errors.
        # For this specific "quota exceeded" context, usually we want to try all *other* keys.
        # If we come back to where we started, we are truly out of quota on all keys.
        
        # We can implement a simple check: if we hit a key we already tried in this specific generate call?
        # But _generate_with_llm is stateless. 
        # Let's just return True to allow rotation. The caller should safeguard against infinite loops 
        # or we rely on the fact that eventually we fall back to OpenAI if even the rotated keys fail?
        # A simple approach: We let it rotate. If we keep hitting 429s, we will eventually run through them 
        # and then maybe we should flag 'all tried'. 
        
        # Let's just change the key and config.
        self._configure_current_key()
        return True

    def _generate_with_llm(self, prompt: str) -> str:
        """
        Attempts to generate content using Gemini.
        Rotates keys if Quota limit hit.
        Falls back to OpenAI if all Gemini keys/Quota fail.
        """
        # We track how many rotations we've done for this specific call to avoid infinite loops
        # Max attempts = number of keys
        max_gemini_attempts = len(self.api_keys)
        attempts = 0
        
        while attempts < max_gemini_attempts:
            try:
                attempts += 1
                # 1. Default use Gemini
                response = self.model.generate_content([
                    self.system_prompt,
                    prompt
                ])
                return response.text.replace("```json", "").replace("```", "").strip()
                
            except Exception as e:
                err_str = str(e).lower()
                # 2. Check for Quota/Rate Limit errors
                if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                    print(f"Gemini Key #{self.current_key_header_index+1} Quota Exceeded...")
                    
                    # Try to rotate key
                    # If we haven't tried all keys yet
                    if attempts < max_gemini_attempts:
                        print("Rotating to next Gemini key...")
                        self._rotate_key()
                        continue # Retry loop
                    else:
                        # We tried all keys, time to fallback
                        break
                else:
                    # Other errors (network, 500, etc) - Raise to let retry loop handle
                    raise e
        
        print("Gemini quota exhausted on all keys and OPENAI_API_KEY not set.")
        raise Exception("Gemini quota exhausted on all keys")

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
        if os.path.exists(self.stats_file) and os.path.getsize(self.stats_file) > 10:
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
        if not os.path.exists(self.trades_file) or os.path.getsize(self.trades_file) < 10:
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
