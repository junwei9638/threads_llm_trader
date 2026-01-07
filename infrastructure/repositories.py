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
                "content": p.content,
                "timestamp": p.timestamp,
                "id": p.id
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
            Post(content=item["content"], timestamp=item.get("timestamp", 0.0), id=item.get("id"))
            for item in data
        ]

class JsonSignalRepository(SignalRepository):
    def __init__(self, filepath: str):
        self.filepath = filepath

    def save_signals(self, signals: List[Signal]) -> None:
        data = [
            {
                "symbol": s.symbol,
                "action": s.action,
                "confidence": s.confidence,
                "reason": s.reason,
                "timestamp": s.timestamp,
                "original_content": s.original_content
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
                symbol=item["symbol"],
                action=item["action"],
                confidence=item["confidence"],
                reason=item["reason"],
                timestamp=item.get("timestamp", 0.0),
                original_content=item.get("original_content", "")
            )
            for item in data
        ]

class CsvTradeRepository(TradeRepository):
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.fieldnames = ["timestamp", "symbol", "qty", "price", "total_cost"]

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
                    qty=int(row["qty"]),
                    price=float(row["price"]),
                    total_cost=float(row["total_cost"]),
                    timestamp=datetime.fromisoformat(row["timestamp"])
                ))
        return trades
