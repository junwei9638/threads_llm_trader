from typing import List
from .entities import Signal, Trade, Post
from .interfaces import PostRepository, SignalRepository, TradeRepository, MarketAnalyzer, StockPriceProvider
from datetime import datetime

class ProcessMarketData:
    def __init__(
        self,
        post_repo: PostRepository,
        signal_repo: SignalRepository,
        trade_repo: TradeRepository,
        analyzer: MarketAnalyzer,
        price_provider: StockPriceProvider,
        initial_cash: float
    ):
        self.post_repo = post_repo
        self.signal_repo = signal_repo
        self.trade_repo = trade_repo
        self.analyzer = analyzer
        self.price_provider = price_provider
        self.initial_cash = initial_cash

    def run(self):
        # 1. Load posts (In a real scenario, this might trigger a fetch)
        # For now, we assume crawler has run or we trigger it via another service.
        # But per clean arch, we just "load" what's available or use a CrawlerService.
        # Let's assume we load what's available for analysis.
        posts = self.post_repo.load_posts()
        if not posts:
            print("No posts to analyze.")
            return

        # 2. Analyze
        print(f"Analyzing {len(posts)} posts...")
        signals = self.analyzer.analyze_posts(posts)
        if not signals:
            print("No signals found.")
            return

        # 3. Save Signals
        self.signal_repo.save_signals(signals)
        print(f"Saved {len(signals)} signals.")

        # 4. Execute Trades (Simple Logic)
        self._execute_trades(signals)

    def _execute_trades(self, signals: List[Signal]):
        # Filter buy signals
        buy_signals = [s for s in signals if s.action == "buy"]
        if not buy_signals:
            print("No buy signals.")
            return

        # Simple strategy: top 3 by score (count * confidence)
        # Group by symbol
        grouped = {}
        for s in buy_signals:
            if s.symbol not in grouped:
                grouped[s.symbol] = {"count": 0, "conf_sum": 0.0}
            grouped[s.symbol]["count"] += 1
            grouped[s.symbol]["conf_sum"] += s.confidence
        
        scored = []
        for sym, data in grouped.items():
            avg_conf = data["conf_sum"] / data["count"]
            score = data["count"] * avg_conf
            scored.append((sym, score))
        
        # Sort and take top 3
        scored.sort(key=lambda x: x[1], reverse=True)
        top3 = scored[:3]

        if not top3:
            return

        print(f"Top 3: {top3}")
        
        # Calculate budget per stock
        budget = self.initial_cash / len(top3)

        for sym, score in top3:
            price = self.price_provider.get_current_price(sym)
            if not price:
                print(f"Could not get price for {sym}")
                continue
            
            qty = int(budget // price)
            if qty > 0:
                total_cost = qty * price
                trade = Trade(
                    symbol=sym,
                    qty=qty,
                    price=price,
                    total_cost=total_cost,
                    timestamp=datetime.now()
                )
                self.trade_repo.save_trade(trade)
                print(f"Executed Trade: {trade}")
