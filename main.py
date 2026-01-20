import os
from config import (
    POSTS_FILE,
    SIGNALS_FILE,
    TRADES_FILE,
    GEMINI_API_KEY,
    GEMINI_API_KEYS,
    FINMIND_TOKEN,
    INITIAL_CASH
)
from infrastructure.repositories import (
    JsonPostRepository,
    JsonSignalRepository,
    CsvTradeRepository
)
from infrastructure.services import (
    GeminiMarketAnalyzer,
    FinMindPriceProvider,
    InfluencerManager
)
from core.use_cases import ProcessMarketData

def main():
    print("Starting Threads LLM Trader (Clean Architecture)")

    # Check data availability
    if not os.path.exists(POSTS_FILE):
        print(f"Data file {POSTS_FILE} not found.")
        choice = input("Would you like to fetch new posts from Threads? (y/n): ").strip().lower()
        if choice == 'y':
            from crawler.threads_fetch import fetch_following_posts
            fetch_following_posts()
    else:
        choice = input(f"Data found at {POSTS_FILE}. Fetch new posts anyway? (y/n): ").strip().lower()
        if choice == 'y':
            from crawler.threads_fetch import fetch_following_posts
            fetch_following_posts()

    # 1. Instantiate Infrastructure (Adapters)
    post_repo = JsonPostRepository(POSTS_FILE)
    signal_repo = JsonSignalRepository(SIGNALS_FILE)
    trade_repo = CsvTradeRepository(TRADES_FILE)
    
    analyzer = GeminiMarketAnalyzer(api_keys=GEMINI_API_KEYS)
    price_provider = FinMindPriceProvider(token=FINMIND_TOKEN)
    
    influencer_stats_file = os.path.join(os.path.dirname(TRADES_FILE), "influencer_stats.csv")
    influencer_tracker = InfluencerManager(stats_file=influencer_stats_file, trades_file=TRADES_FILE)

    # 2. Instantiate Use Case (Application Layer)
    # Inject dependencies
    processor = ProcessMarketData(
        post_repo=post_repo,
        signal_repo=signal_repo,
        trade_repo=trade_repo,
        analyzer=analyzer,
        price_provider=price_provider,
        influencer_tracker=influencer_tracker,
        initial_cash=INITIAL_CASH
    )

    # 3. Execution
    try:
        processor.run()
        print("Execution completed successfully.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Execution failed: {e}")

if __name__ == "__main__":
    main()
