# Threads LLM Trader

A sophisticated automated trading bot that crawls **Threads**, analyzes influencer sentiment using **Google Gemini 1.5 Flash**, and executes simulated trades based on generated signals. Built with **Clean Architecture** principles.

## 🚀 Features

*   **Automated Crawler**: Uses Playwright to automatically log in to Threads and scrape posts from your following feed.
*   **AI Analysis**: Utilizes **Gemini 1.5 Flash** to analyze post content for stock tips, sentiment, and trading signals.
    *   **Batch Processing**: Optimizes API usage (10 posts/request) to avoid rate limits (429 errors).
*   **Smart Parsing**: Extracts influencer names, post timestamps, and maps them to stock tickers (e.g., 2330).
*   **Trading Simulation**:
    *   Fetches real-time stock prices via **FinMind**.
    *   Calculates entry price and cost.
    *   Logs trades to `data/trades.csv`.
*   **Clean Architecture**: Modular design separating Domain (Core), Infrastructure (Adapters), and Application layers.

## 📂 Project Structure

```
threads_llm_trader/
├── core/                   # Domain Logic
│   ├── entities.py         # Data models (Post, Signal, Trade)
│   ├── interfaces.py       # Abstract Base Classes
│   └── use_cases.py        # Application Business Rules
├── infrastructure/         # Implementation Details
│   ├── repositories.py     # JSON/CSV file storage
│   └── services.py         # Gemini API & FinMind integration
├── crawler/                
│   └── threads_fetch.py    # Playwright crawler with auto-login
├── data/                   # Generated data (posts, signals, trades)
├── config.py               # Configuration & Credentials
├── main.py                 # Application Entry Point
└── requirements.txt        # Dependencies
```

## 🛠️ Setup

1.  **Clone the repository** (or download source).

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```

3.  **Environment Variables**:
    Create a `.env` file in the root directory with the following keys:
    ```ini
    GEMINI_API_KEY=your_gemini_api_key
    FINMIND_TOKEN=your_finmind_token (optional)
    threads_acc=your_threads_username
    threads_pwd=your_threads_password
    ```

## 🏃 Usage

Run the main application:
```bash
python main.py
```

**Interactive Workflow**:
1.  **Startup**: The app checks if `data/posts.json` exists.
2.  **Prompt**: You will be asked if you want to fetch new posts:
    *   `y`: Launches a browser (headed mode), automatically logs in using credentials from `.env`, and scrapes 10-20 posts from your feed.
    *   `n`: Uses the existing scraped data for analysis.
3.  **Analysis**: The app processes posts in batches using Gemini to find "BUY/SELL" signals.
4.  **Execution**: Valid signals are "executed" (price fetched + logged) and saved to `data/signals.json` and `data/trades.csv`.

## 📊 Data Output

*   **`data/signals.json`**: Detailed signals including influencer, confidence, and Gemini's reasoning.
*   **`data/trades.csv`**: Record of executed trades with price and total cost.

## ⚠️ Disclaimer
This project is for educational purposes only. Do not use for real money trading without verification and proper risk management.
