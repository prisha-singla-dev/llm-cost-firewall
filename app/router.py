"""
router.py - Main LLM Router

Uses the NEW google-genai SDK (not deprecated google-generativeai).
New SDK pattern: client = genai.Client() then client.models.generate_content()
"""

import time
import random
import os
from typing import Dict, Any, Optional

from app.analyzer      import compute_complexity, select_model
from app.cache         import ExactCache
from app.semantic_cache import SemanticCache
from app.budget        import BudgetEnforcer, BudgetExceededError
from app.rate_limiter  import RateLimiter
from app.logger        import RequestLogger
from app.config        import (
    GEMINI_API_KEY, MOCK_MODE, MODEL_COSTS,
    GEMINI_FLASH, GEMINI_PRO,
)

# ── New SDK import ────────────────────────────────────────────────────────────
_gemini_client = None
GEMINI_AVAILABLE = False

if not MOCK_MODE and GEMINI_API_KEY:
    try:
        from google import genai as _genai_module
        _gemini_client = _genai_module.Client(api_key=GEMINI_API_KEY)
        GEMINI_AVAILABLE = True
        print(f"✅ Gemini client initialized (new google-genai SDK)")
    except Exception as e:
        print(f"⚠️  Gemini init failed: {e} — falling back to mock mode")

MOCK_RESPONSES = [
    "This is a detailed mock response demonstrating the system works correctly.",
    "Based on your query, here is a comprehensive answer covering all key aspects.",
    "Great question! Here is a structured response with the key information you need.",
    "The answer involves several important concepts. Let me break them down clearly.",
]


def _calculate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    pricing = MODEL_COSTS.get(model, MODEL_COSTS[GEMINI_FLASH])
    return (tokens_in / 1000 * pricing["input"]) + (tokens_out / 1000 * pricing["output"])


class LLMRouter:
    def __init__(self):
        self.exact_cache    = ExactCache()
        self.semantic_cache = SemanticCache()
        self.budget         = BudgetEnforcer()
        self.rate_limiter   = RateLimiter()
        self.logger         = RequestLogger()
        self._ml_router     = None

    def load_ml_router(self, ml_router):
        self._ml_router = ml_router

    def _call_gemini(self, query: str, model: str) -> Dict:
        """
        Call Gemini using the NEW google-genai SDK.
        Pattern: client.models.generate_content(model=..., contents=...)
        """
        response = _gemini_client.models.generate_content(
            model=model,
            contents=query,
        )
        text = response.text

        # Token counts from usage_metadata
        usage      = getattr(response, "usage_metadata", None)
        tokens_in  = getattr(usage, "prompt_token_count",      50) if usage else 50
        tokens_out = getattr(usage, "candidates_token_count",  80) if usage else 80

        return {"response": text, "tokens_in": tokens_in, "tokens_out": tokens_out}

    def _mock_call(self, query: str, model: str) -> Dict:
        """Fake call for testing — realistic latency, correct cost calculation."""
        time.sleep(random.uniform(0.05, 0.15))
        tokens_in  = max(10, len(query.split()) + 5)
        tokens_out = random.randint(60, 180)
        response   = f"[MOCK {model}] {random.choice(MOCK_RESPONSES)} | Query: '{query[:50]}'"
        return {"response": response, "tokens_in": tokens_in, "tokens_out": tokens_out}

    def process(
        self,
        query:       str,
        user_id:     str = "anonymous",
        force_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()

        # 1. Rate limiting
        rate_check = self.rate_limiter.check(user_id)
        if not rate_check["allowed"]:
            raise ValueError(
                f"Rate limit exceeded. Limit: {rate_check['limit']}/hour. "
                f"Retry after {rate_check['retry_after']}s."
            )

        # 2. Budget check
        self.budget.check_budget()

        # 3. Complexity analysis + model selection
        complexity_result = compute_complexity(query)
        complexity_score  = complexity_result["composite"]

        if force_model:
            model = force_model
        elif self._ml_router and self._ml_router.is_trained:
            ml_result = self._ml_router.predict(query)
            model = ml_result["model"] if ml_result["confidence"] > 0.7 else select_model(complexity_score)
        else:
            model = select_model(complexity_score)

        # 4. Exact cache check
        cached = self.exact_cache.get(query, model)
        if cached:
            latency_ms = (time.time() - start_time) * 1000
            self.logger.log(user_id, query, model, complexity_score, 0, 0, 0.0, True, "exact", latency_ms)
            return {
                "response":          cached["response"],
                "model":             model,
                "cost_usd":          0.0,
                "cache_hit":         True,
                "cache_type":        "exact",
                "complexity_score":  complexity_score,
                "tokens":            {"input": 0, "output": 0},
                "latency_ms":        round(latency_ms, 2),
            }

        # 5. Semantic cache check
        sem_cached = self.semantic_cache.get(query)
        if sem_cached:
            latency_ms = (time.time() - start_time) * 1000
            self.logger.log(user_id, query, sem_cached["model"], complexity_score, 0, 0, 0.0, True, "semantic", latency_ms)
            return {
                "response":           sem_cached["response"],
                "model":              sem_cached["model"],
                "cost_usd":           0.0,
                "cache_hit":          True,
                "cache_type":         "semantic",
                "similarity_score":   sem_cached.get("similarity_score"),
                "complexity_score":   complexity_score,
                "tokens":             {"input": 0, "output": 0},
                "latency_ms":         round(latency_ms, 2),
            }

        # 6. LLM call
        try:
            if GEMINI_AVAILABLE:
                llm_result = self._call_gemini(query, model)
            else:
                llm_result = self._mock_call(query, model)
        except Exception as e:
            # Fallback to mock on any API error — app never returns 500
            llm_result = self._mock_call(query, model)
            llm_result["response"] += f" [API_ERROR: {str(e)[:100]}]"

        cost = _calculate_cost(model, llm_result["tokens_in"], llm_result["tokens_out"])

        # 7. Record cost, cache, log
        self.budget.record_cost(cost)
        self.exact_cache.set(query, model, llm_result["response"], cost)
        self.semantic_cache.set(query, llm_result["response"], model, cost)

        latency_ms = (time.time() - start_time) * 1000
        self.logger.log(
            user_id, query, model, complexity_score,
            llm_result["tokens_in"], llm_result["tokens_out"],
            cost, False, "none", latency_ms,
        )

        return {
            "response":           llm_result["response"],
            "model":              model,
            "cost_usd":           round(cost, 8),
            "cache_hit":          False,
            "cache_type":         "none",
            "complexity_score":   complexity_score,
            "complexity_factors": complexity_result["factors"],
            "tokens":             {"input": llm_result["tokens_in"], "output": llm_result["tokens_out"]},
            "latency_ms":         round(latency_ms, 2),
        }

    def get_full_stats(self) -> Dict:
        from app.analytics import compute_analytics
        from app.config    import LOG_FILE
        return {
            "exact_cache":    self.exact_cache.stats(),
            "semantic_cache": self.semantic_cache.stats(),
            "budget":         self.budget.status(),
            "rate_limiter":   self.rate_limiter.stats(),
            "analytics":      compute_analytics(LOG_FILE),
            "ml_router": {
                "trained":    self._ml_router.is_trained if self._ml_router else False,
                "model_type": "RandomForest" if (self._ml_router and self._ml_router.is_trained) else "heuristic",
            },
            "gemini_available": GEMINI_AVAILABLE,
            "mock_mode":        MOCK_MODE,
        }