import json
import csv
import os
from typing import List
from datetime import datetime
from core.interfaces import PostRepository, SignalRepository, TradeRepository
from core.entities import Post, Signal, Trade

class JsonPostRepository(PostRepository):
    def __init__(self, filepath: str):
        self.filepath = filepath

    def save_posts(self, posts: List[Post]) -> None:
        data = [
            {
                "id": p.id,
                "content": p.content,
                "timestamp": p.timestamp,
                "influencer": p.influencer,
                "post_time": p.post_time,
                "fetch_time": p.fetch_time
            }
            for p in posts
        ]
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_posts(self) -> List[Post]:
        if not os.path.exists(self.filepath):
            return []
        
        with open(self.filepath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return []
                
        return [
            Post(
                content=item["content"],
                timestamp=item.get("timestamp", 0.0),
                id=item.get("id"),
                influencer=item.get("influencer", "Unknown"),
                post_time=item.get("post_time", ""),
                fetch_time=item.get("fetch_time", "")
            )
            for item in data
        ]

class JsonSignalRepository(SignalRepository):
    def __init__(self, filepath: str):
        self.filepath = filepath

    def save_signals(self, signals: List[Signal]) -> None:
        data = [
            {
                "post_id": s.post_id,
                "post_id": s.post_id,
                "author": s.author,
                "post_time": s.post_time,
                "fetch_time": s.fetch_time,
                "gemini_decision": s.gemini_decision,
                "confidence": s.confidence,
                "ticker": s.ticker,
                "entry_price": s.entry_price,
                "entry_time": s.entry_time
            }
            for s in signals
        ]
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_signals(self) -> List[Signal]:
        if not os.path.exists(self.filepath):
            return []
        
        with open(self.filepath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return []

        return [
            Signal(
                post_id=item.get("post_id", ""),
                author=item.get("author", item.get("influencer", "")), # Fallback for old data
                post_time=item.get("post_time", ""),
                fetch_time=item.get("fetch_time", ""),
                gemini_decision=item.get("gemini_decision", ""),
                confidence=item.get("confidence", 0.0),
                ticker=item.get("ticker", ""),
                entry_price=item.get("entry_price"),
                entry_time=item.get("entry_time"),
                reason=item.get("reason", ""),  # Optional backward combatibility if re-analyzing
                timestamp=0.0 # Not critical for display
            )
            for item in data
        ]

class CsvTradeRepository(TradeRepository):
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.fieldnames = ["timestamp", "author", "symbol", "qty", "price", "total_cost"]

    def _ensure_file(self):
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()

    def save_trade(self, trade: Trade) -> None:
        self._ensure_file()
        with open(self.filepath, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writerow({
                "timestamp": trade.timestamp.isoformat(),
                "author": trade.author,
                "symbol": trade.symbol,
                "qty": trade.qty,
                "price": trade.price,
                "total_cost": trade.total_cost
            })

    def load_trades(self) -> List[Trade]:
        if not os.path.exists(self.filepath):
            return []
        
        trades = []
        with open(self.filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trades.append(Trade(
                    symbol=row["symbol"],
                    author=row.get("author", "Unknown"), # Handle migration
                    qty=int(row["qty"]),
                    price=float(row["price"]),
                    total_cost=float(row["total_cost"]),
                    timestamp=datetime.fromisoformat(row["timestamp"])
                ))
        return trades
