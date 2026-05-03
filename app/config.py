"""
config.py

IMPORTANT MODEL UPDATE (May 2026):
  gemini-2.0-flash  → shutting down June 1 2026. Replaced by gemini-2.5-flash.
  gemini-2.5-flash  → best free tier limits (15 RPM, ~500 RPD on free tier)
  gemini-2.5-pro    → for complex queries (5 RPM free tier, use sparingly)

FREE TIER LIMITS (per project, as of 2025-2026):
  gemini-2.5-flash: 15 RPM, ~500 RPD → use this as your default
  gemini-2.5-pro:   5 RPM,  50 RPD   → only for truly complex queries

HOW TO GET MORE QUOTA (free):
  Add a credit card at aistudio.google.com → billing enabled = Tier 1
  Tier 1 gives you 150 RPM for Flash, unlimited daily requests.
  You won't be charged unless you exceed very high thresholds.
"""
import os
from dotenv import load_dotenv
load_dotenv()

# ── Current model names (updated for June 2026 deprecations) ──────────────────
GEMINI_FLASH = "gemini-2.5-flash"   # fast, cheap, best free quota
GEMINI_PRO   = "gemini-2.5-pro"     # powerful, use sparingly on free tier

# ── Cost per 1M tokens (USD) — converted to per 1K for calculation ───────────
MODEL_COSTS = {
    "gemini-2.5-flash": {"input": 0.0003,  "output": 0.0024},   # $0.30/1M in
    "gemini-2.5-pro":   {"input": 0.00125, "output": 0.005},    # $1.25/1M in
    # Backwards compat for existing log entries
    "gemini-2.0-flash": {"input": 0.0001,  "output": 0.0004},
    "gemini-1.5-flash": {"input": 0.000075,"output": 0.0003},
    "gemini-1.5-pro":   {"input": 0.00125, "output": 0.005},
}

# ── Routing thresholds ────────────────────────────────────────────────────────
SIMPLE_THRESHOLD  = 0.35   # below → use Flash (cheap)
COMPLEX_THRESHOLD = 0.65   # above → use Pro (smart, use sparingly on free tier)

# ── Cache ─────────────────────────────────────────────────────────────────────
CACHE_TTL_SECONDS             = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
SEMANTIC_SIMILARITY_THRESHOLD = float(os.getenv("SEMANTIC_THRESHOLD", "0.85"))
CACHE_MAX_SIZE                = int(os.getenv("CACHE_MAX_SIZE", "500"))

# ── Rate limiting ─────────────────────────────────────────────────────────────
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "100"))

# ── Budget ────────────────────────────────────────────────────────────────────
DAILY_BUDGET_USD  = float(os.getenv("DAILY_BUDGET_USD",  "10.0"))
HOURLY_BUDGET_USD = float(os.getenv("HOURLY_BUDGET_USD", "2.0"))

# ── API ───────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MOCK_MODE      = os.getenv("MOCK_MODE", "true").lower() == "true"
LOG_FILE       = os.getenv("LOG_FILE", "logs/requests.csv")

# ── Retry settings for 429 handling ──────────────────────────────────────────
MAX_RETRIES       = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BASE_DELAY  = float(os.getenv("RETRY_BASE_DELAY", "2.0"))  # seconds