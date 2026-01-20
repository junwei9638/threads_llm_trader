from dataclasses import dataclass
from typing import List, Literal, Optional, Dict

@dataclass
class Order:
    ticker: str
    action: Literal["BUY"]
    price: float
    shares: int
    timing: Literal["next_open"]

class DecisionEngine:
    def __init__(self, total_cash: float = 50000.0):
        self.total_cash = total_cash

    def generate_orders(self, signals: List) -> List[Order]:
        # 1. Filter signals: gemini_decision == "BUY" and timing == "next_open"
        valid_signals = [
            s for s in signals 
            if getattr(s, "gemini_decision", "").upper() == "BUY" 
            and getattr(s, "timing", "") == "next_open"
        ]
        
        if not valid_signals:
            return []

        # 2. Aggregation by ticker: Combine multiple signals
        # score = Σ(confidence × weight)
        ticker_data = {}
        for s in valid_signals:
            ticker = s.ticker
            if ticker not in ticker_data:
                ticker_data[ticker] = {
                    "score_sum": 0.0,
                    "price": getattr(s, "entry_price", 0.0) or 0.0
                }
            
            confidence = getattr(s, "confidence", 0.0) or 0.0
            weight = getattr(s, "weight", 1.0) or 1.0
            ticker_data[ticker]["score_sum"] += confidence * weight
            
            # Use current signal's price if available
            if getattr(s, "entry_price", None):
                ticker_data[ticker]["price"] = s.entry_price

        # 3. Sort by score and take top 3
        sorted_tickers = sorted(
            ticker_data.items(), 
            key=lambda x: x[1]["score_sum"], 
            reverse=True
        )
        top_3 = sorted_tickers[:3]

        # 4. Cash allocation: Divided equally among 3 slots
        capital_per_stock = self.total_cash / 3

        orders = []
        for ticker, data in top_3:
            price = data["price"]
            
            # 5. Shares calculation logic
            shares = 0
            if price > 0:
                shares = int(capital_per_stock // price)
                
                # Shares logic rules
                if shares < 1:
                    shares = 0
                elif shares >= 1000:
                    # 無條件捨去到 1000 的倍數 (Standard lot rounding)
                    shares = (shares // 1000) * 1000
                # else: 1 <= shares < 1000 stays as is (Odd lot)

            orders.append(Order(
                ticker=ticker,
                action="BUY",
                price=float(price),
                shares=shares,
                timing="next_open"
            ))

        return orders
