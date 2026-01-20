from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from .entities import Post, Signal, Trade
import pandas as pd

class PostRepository(ABC):
    @abstractmethod
    def save_posts(self, posts: List[Post]) -> None:
        pass

    @abstractmethod
    def load_posts(self) -> List[Post]:
        pass

class SignalRepository(ABC):
    @abstractmethod
    def save_signals(self, signals: List[Signal]) -> None:
        pass

    @abstractmethod
    def load_signals(self) -> List[Signal]:
        pass

class TradeRepository(ABC):
    @abstractmethod
    def save_trade(self, trade: Trade) -> None:
        pass

    @abstractmethod
    def load_trades(self) -> List[Trade]:
        pass

class StockPriceProvider(ABC):
    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        pass

class MarketAnalyzer(ABC):
    @abstractmethod
    def analyze_posts(self, posts: List[Post]) -> List[Signal]:
        pass

class InfluencerTracker(ABC):
    @abstractmethod
    def update_stats(self) -> None:
        pass

    @abstractmethod
    def get_weight(self, author: str) -> float:
        pass
