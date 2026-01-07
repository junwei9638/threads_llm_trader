import pandas as pd
import os
import json
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from FinMind.data import DataLoader
from config import SIGNALS_FILE, TRADES_FILE, INITIAL_CASH, FINMIND_TOKEN

def get_current_price(symbol):
    dl = DataLoader()
    if FINMIND_TOKEN:
        dl.login_by_token(api_token=FINMIND_TOKEN)
    
    # We use Taiwan stock data as default behavior based on the prompt's example (2330)
    # Getting the latest price. For simplification, we'll get the last 2 days and take the latest.
    try:
        # FinMind symbol usually needs '2330' for TW
        # However, it expects something like '2330' as input.
        # We assume the symbol is a standard Taiwan stock code.
        df = dl.taiwan_stock_daily(
            stock_id=symbol,
            start_date=(pd.Timestamp.now() - pd.Timedelta(days=5)).strftime('%Y-%m-%d'),
        )
        if not df.empty:
            return df.iloc[-1]['close']
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
    return None

def run_simulation():
    if not os.path.exists(SIGNALS_FILE):
        print(f"{SIGNALS_FILE} not found. Please run the analyzer first.")
        return

    # Load signals
    with open(SIGNALS_FILE, "r", encoding="utf-8") as f:
        signals = json.load(f)
    
    if not signals:
        print("No signals to process.")
        return

    df = pd.DataFrame(signals)
    
    # Only process buy signals for now as per prompt
    buy_signals = df[df["action"] == "buy"]
    if buy_signals.empty:
        print("No buy signals found.")
        return

    # Aggregate signals
    summary = (
        buy_signals
        .groupby("symbol")
        .agg(
            count=("confidence", "count"),
            avg_conf=("confidence", "mean")
        )
    )

    # Calculate score
    summary["score"] = summary["count"] * summary["avg_conf"]
    top3 = summary.sort_values("score", ascending=False).head(3)

    print("Top 3 Stock Signals:")
    print(top3)

    # Trade logic
    # Load existing trades or initialize
    if os.path.exists(TRADES_FILE):
        trades_df = pd.read_csv(TRADES_FILE)
        # For simplicity, we assume we reset or just log.
        # In a real paper trader, we'd track cumulative cash/positions.
        # Here we follow the logic in the prompt: recalculate based on INITIAL_CASH.
    else:
        trades_df = pd.DataFrame(columns=["timestamp", "symbol", "qty", "price", "total_cost"])

    cash = INITIAL_CASH
    positions = {}
    new_trades = []

    for symbol in top3.index:
        price = get_current_price(symbol)
        if price is None:
            print(f"Could not get price for {symbol}, skipping.")
            continue
            
        budget = INITIAL_CASH / len(top3)
        qty = int(budget // price)

        if qty > 0:
            total_cost = qty * price
            print(f"Simulating BUY: {symbol} | Qty: {qty} | Price: {price} | Total: {total_cost}")
            new_trades.append({
                "timestamp": pd.Timestamp.now(),
                "symbol": symbol,
                "qty": qty,
                "price": price,
                "total_cost": total_cost
            })

    if new_trades:
        new_trades_df = pd.DataFrame(new_trades)
        trades_df = pd.concat([trades_df, new_trades_df], ignore_index=True)
        trades_df.to_csv(TRADES_FILE, index=False)
        print(f"Trades saved to {TRADES_FILE}")

if __name__ == "__main__":
    run_simulation()
