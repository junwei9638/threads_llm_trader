from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Post:
    content: str
    timestamp: float
    id: Optional[str] = None

@dataclass
class Signal:
    symbol: str
    action: str  # "buy" or "sell"
    confidence: float
    reason: str
    timestamp: float
    original_content: str

@dataclass
class Trade:
    symbol: str
    qty: int
    price: float
    total_cost: float
    timestamp: datetime
