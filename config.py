import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Gemini API Keys (Scan for all GEMINI_API_KEY*)
GEMINI_API_KEYS = [val for key, val in os.environ.items() if key.startswith("GEMINI_API_KEY") and val]
# Fallback for code expecting single key
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else os.getenv("GEMINI_API_KEY", "")

# FinMind Token (optional)
FINMIND_TOKEN = os.getenv("FINMIND_TOKEN", "")

# Threads Credentials
THREADS_USERNAME = os.getenv("threads_acc", "")
THREADS_PASSWORD = os.getenv("threads_pwd", "")

# Paths
DATA_DIR = "data"
POSTS_FILE = os.path.join(DATA_DIR, "posts.json")
SIGNALS_FILE = os.path.join(DATA_DIR, "signals.json")
TRADES_FILE = os.path.join(DATA_DIR, "trades.csv")

# Simulation Settings
INITIAL_CASH = 50000
