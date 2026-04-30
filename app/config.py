# """
# Configuration for LLM Cost Firewall - UPDATED FOR GEMINI
# """
# import os
# from dotenv import load_dotenv

# load_dotenv()

# class Config:
#     GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
#     OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "") 
#     ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    
#     # Mock mode for testing without real API keys
#     MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true" or not GEMINI_API_KEY
    
#     # Budget Limits
#     DAILY_BUDGET_USD = float(os.getenv("DAILY_BUDGET_USD", "100"))
#     HOURLY_BUDGET_USD = float(os.getenv("HOURLY_BUDGET_USD", "10"))
    
#     # Model pricing (per 1K tokens)
#     MODEL_COSTS = {
#         "gemini-flash-latest": {"input": 0.0, "output": 0.0},  # Free - Latest Flash
#         "gemini-pro-latest": {"input": 0.0, "output": 0.0},  # Free - Latest Pro
#         "gemini-2.5-flash": {"input": 0.0, "output": 0.0},  # Free - Stable 2.5
#         "gemini-2.5-pro": {"input": 0.0, "output": 0.0},  # Free - Stable 2.5 Pro

#         "gpt-4": {"input": 0.03, "output": 0.06},
#         "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
#         "claude-opus-3": {"input": 0.015, "output": 0.075},
#         "claude-haiku-3": {"input": 0.00025, "output": 0.00125},
#     }
    
#     # Routing thresholds (unchanged)
#     SIMPLE_QUERY_THRESHOLD = 0.3
#     COMPLEX_QUERY_THRESHOLD = 0.7
    
#     @staticmethod
#     def get_model_cost(model: str, input_tokens: int, output_tokens: int) -> float:
#         """Calculate cost for a model call"""
#         if model not in Config.MODEL_COSTS:
#             return 0.0
#         costs = Config.MODEL_COSTS[model]
#         return (input_tokens / 1000) * costs["input"] + (output_tokens / 1000) * costs["output"]
    
#     @staticmethod
#     def select_model(complexity_score: float) -> str:
#         """
#         Select model based on complexity
#         CHANGED: Now routes to Gemini models (verified working names)
#         """
#         if complexity_score < Config.SIMPLE_QUERY_THRESHOLD:
#             return "gemini-flash-latest"  # Simple → Fast & Free
#         elif complexity_score < Config.COMPLEX_QUERY_THRESHOLD:
#             return "gemini-flash-latest"  # Medium → Balanced
#         else:
#             return "gemini-pro-latest"  # Complex → Powerful


# config = Config()

"""
config.py - All configuration in one place
Reads from .env file. Never hardcode secrets.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Gemini Models ────────────────────────────────────────────────────────────
# gemini-1.5-flash  = fast + cheap  → use for simple queries
# gemini-1.5-pro    = smart + costs → use for complex queries
GEMINI_FLASH = "gemini-1.5-flash"
GEMINI_PRO   = "gemini-1.5-pro"

# ─── Cost per 1K tokens (USD) ─────────────────────────────────────────────────
# Source: Google AI pricing page (April 2025)
MODEL_COSTS = {
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},   # very cheap
    "gemini-1.5-pro":   {"input": 0.00125,  "output": 0.005},    # ~17x more expensive
}

# ─── Routing thresholds ───────────────────────────────────────────────────────
# complexity score 0.0 → 1.0 (calculated by analyzer.py)
# Below SIMPLE_THRESHOLD  → use Flash (cheap)
# Above COMPLEX_THRESHOLD → use Pro (smart)
SIMPLE_THRESHOLD  = 0.35
COMPLEX_THRESHOLD = 0.65

# ─── Cache settings ───────────────────────────────────────────────────────────
CACHE_TTL_SECONDS          = int(os.getenv("CACHE_TTL_SECONDS", "3600"))      # 1 hour
SEMANTIC_SIMILARITY_THRESHOLD = float(os.getenv("SEMANTIC_THRESHOLD", "0.85"))
CACHE_MAX_SIZE             = int(os.getenv("CACHE_MAX_SIZE", "500"))

# ─── Rate limiting ────────────────────────────────────────────────────────────
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "100"))

# ─── Budget enforcement ───────────────────────────────────────────────────────
DAILY_BUDGET_USD  = float(os.getenv("DAILY_BUDGET_USD",  "10.0"))
HOURLY_BUDGET_USD = float(os.getenv("HOURLY_BUDGET_USD", "2.0"))

# ─── API keys ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ─── App mode ─────────────────────────────────────────────────────────────────
# MOCK_MODE=true  → fake responses, zero cost, for testing
# MOCK_MODE=false → real Gemini calls
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_FILE = os.getenv("LOG_FILE", "logs/requests.csv")