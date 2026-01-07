import sys
import os

# Fix for Python 3.9 and google-generativeai compatibility
if sys.version_info < (3, 10):
    try:
        import importlib.metadata
        import importlib_metadata
        importlib.metadata.packages_distributions = importlib_metadata.packages_distributions
    except ImportError:
        pass

import google.generativeai as genai
import json
# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import GEMINI_API_KEY, POSTS_FILE, SIGNALS_FILE

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-3-pro")

SYSTEM_PROMPT = """
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

def analyze_post(text):
    try:
        response = model.generate_content([
            SYSTEM_PROMPT,
            f"貼文內容：{text}"
        ])
        
        # Strip potential markdown formatting if Gemini adds it
        json_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(json_text)
    except Exception as e:
        print(f"Error analyzing post with Gemini: {e}")
        return {"has_signal": False, "stocks": []}

def analyze_all_posts():
    if not os.path.exists(POSTS_FILE):
        print(f"{POSTS_FILE} not found. Please run the crawler first.")
        return

    with open(POSTS_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)

    all_signals = []
    print(f"Analyzing {len(posts)} posts...")

    for p in posts:
        result = analyze_post(p["content"])
        if result.get("has_signal"):
            for s in result.get("stocks", []):
                all_signals.append({
                    "timestamp": p["timestamp"],
                    "original_content": p["content"][:100] + "...", # for debugging
                    **s
                })

    with open(SIGNALS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_signals, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(all_signals)} signals to {SIGNALS_FILE}")

if __name__ == "__main__":
    analyze_all_posts()
