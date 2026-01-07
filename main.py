import os
from config import (
    POSTS_FILE,
    SIGNALS_FILE,
    TRADES_FILE,
    GEMINI_API_KEY,
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
    FinMindPriceProvider
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
    
    analyzer = GeminiMarketAnalyzer(api_key=GEMINI_API_KEY)
    price_provider = FinMindPriceProvider(token=FINMIND_TOKEN)

    # 2. Instantiate Use Case (Application Layer)
    # Inject dependencies
    processor = ProcessMarketData(
        post_repo=post_repo,
        signal_repo=signal_repo,
        trade_repo=trade_repo,
        analyzer=analyzer,
        price_provider=price_provider,
        initial_cash=INITIAL_CASH
    )

    # 3. Execution
    try:
        processor.run()
        print("Execution completed successfully.")
    except Exception as e:
        print(f"Execution failed: {e}")

if __name__ == "__main__":
    main()
