"""
config.py - All configuration in one place

MODEL NAMES (updated May 2025):
  google-generativeai (old SDK) is DEPRECATED as of Nov 2025.
  We now use google-genai (new SDK) with current model names.

  gemini-2.0-flash  = fast + cheap  → simple queries
  gemini-2.5-pro    = powerful       → complex queries

COST (approximate, Google AI Studio free tier has generous limits):
  gemini-2.0-flash: ~$0.075 / 1M input tokens  (essentially free for dev)
  gemini-2.5-pro:   ~$1.25  / 1M input tokens
"""
import os
from dotenv import load_dotenv
load_dotenv()

# ── Current Gemini model names (2025) ─────────────────────────────────────────
GEMINI_FLASH = "gemini-2.0-flash"   # fast, cheap, free tier
GEMINI_PRO   = "gemini-2.5-pro"     # smart, costs more

# ── Cost per 1K tokens (USD) ──────────────────────────────────────────────────
MODEL_COSTS = {
    "gemini-2.0-flash": {"input": 0.000075,  "output": 0.0003},
    "gemini-2.5-pro":   {"input": 0.00125,   "output": 0.005},
    # Keep old names as aliases so existing logs don't break
    "gemini-1.5-flash": {"input": 0.000075,  "output": 0.0003},
    "gemini-1.5-pro":   {"input": 0.00125,   "output": 0.005},
}

# ── Routing thresholds ────────────────────────────────────────────────────────
SIMPLE_THRESHOLD  = 0.35
COMPLEX_THRESHOLD = 0.65

# ── Cache ─────────────────────────────────────────────────────────────────────
CACHE_TTL_SECONDS             = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
SEMANTIC_SIMILARITY_THRESHOLD = float(os.getenv("SEMANTIC_THRESHOLD", "0.85"))
CACHE_MAX_SIZE                = int(os.getenv("CACHE_MAX_SIZE", "500"))

# ── Rate limiting ─────────────────────────────────────────────────────────────
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "100"))

# ── Budget ────────────────────────────────────────────────────────────────────
DAILY_BUDGET_USD  = float(os.getenv("DAILY_BUDGET_USD",  "10.0"))
HOURLY_BUDGET_USD = float(os.getenv("HOURLY_BUDGET_USD", "2.0"))

# ── API key ───────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── Mode ──────────────────────────────────────────────────────────────────────
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = os.getenv("LOG_FILE", "logs/requests.csv")