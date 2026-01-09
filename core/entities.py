from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Post:
    content: str
    timestamp: float
    id: Optional[str] = None
    influencer: str = "Unknown"
    post_time: str = ""
    fetch_time: str = ""

@dataclass
class Signal:
    post_id: str
    influencer: str
    post_time: str
    fetch_time: str
    gemini_decision: str  # "BUY" or "SELL"
    confidence: float
    ticker: str
    reason: str
    timestamp: float # Internal sort key
    entry_price: Optional[float] = None
    entry_time: Optional[str] = None

@dataclass
class Trade:
    symbol: str
    qty: int
    price: float
    total_cost: float
    timestamp: datetime
