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
    author: str  # Renamed from influencer to match user request
    post_time: str
    fetch_time: str
    gemini_decision: str  # "BUY" or "SELL"
    confidence: float
    ticker: str
    reason: str
    weight: float = 1.0 # Influencer weight
    timestamp: float = 0.0 # Internal sort key
    entry_price: Optional[float] = None
    entry_time: Optional[str] = None
    timing: str = "unknown" # immediate, next_open, unknown

@dataclass
class Trade:
    symbol: str
    author: str # Added author field
    qty: int
    price: float
    total_cost: float
    timestamp: datetime
