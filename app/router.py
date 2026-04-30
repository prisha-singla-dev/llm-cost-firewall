# """
# LLM Router - handles model selection and API calls
# UPDATED FOR GEMINI API
# """
# import time
# import google.generativeai as genai
# from typing import Dict, Any, Optional
# from app.config import config
# from app.cache import cache
# from app.analyzer import analyzer
# from app.semantic_cache import semantic_cache
# from app.ml_router import ml_router


# class LLMRouter:
#     """Routes queries to optimal LLM model"""
    
#     def __init__(self):
#         self.total_cost = 0.0
#         self.query_count = 0
#         self.cache_hits = 0
        
#         if config.GEMINI_API_KEY:
#             try:
#                 genai.configure(api_key=config.GEMINI_API_KEY)
#                 self.gemini_configured = True
#                 print("[ROUTER] Gemini API configured successfully ✅")
#             except Exception as e:
#                 print(f"[ROUTER] Gemini initialization failed: {e}")
#                 self.gemini_configured = False
#         else:
#             self.gemini_configured = False
#             print("[ROUTER] No GEMINI_API_KEY found - running in MOCK mode")
    
#     async def route_query(self, query: str, user_id: str = "default") -> Dict[str, Any]:
#         """
#         Main routing logic:
#         1. Check cache
#         2. Analyze complexity
#         3. Select model
#         4. Call LLM (real or mock)
#         5. Track cost
#         """
#         start_time = time.time()
    
#         # Step 1: Analyze complexity FIRST (we need this for cache key)
#         analysis = analyzer.analyze(query)
#         complexity_score = analysis["complexity_score"]
        
#         # Step 2: Select model based on complexity
#         # Try ML router first, fallback to heuristic
#         try:
#             model, confidence = ml_router.predict_model(query)
#             print(f"[ROUTER] ML predicted: {model} (confidence: {confidence:.2f})")
#         except Exception as e:
#             model = config.select_model(complexity_score)
#             confidence = 0.0
#             print(f"[ROUTER] ML fallback: {model}")

#         # model = config.select_model(complexity_score)
#         # confidence = 0.0
#         # print(f"[ROUTER] Heuristic routing: {model}")

#         # Step 3: Check cache with CORRECT model
#         print(f"\n[ROUTER] Query: '{query[:50]}...'")
#         print(f"[ROUTER] Complexity: {complexity_score} → Model: {model}")
        
#         cached = cache.get(query, model)
#         if cached:
#             self.cache_hits += 1
#             latency = round((time.time() - start_time) * 1000, 2)
            
#             return {
#                 "response": cached["text"],
#                 "model": cached["model"],
#                 "cost_usd": 0.0,
#                 "cache_hit": True,
#                 "latency_ms": latency,
#                 "routing_reason": "Cache hit - query seen before",
#                 "complexity_score": complexity_score
#             }
        
#         # Step 3b: Check SEMANTIC cache
#         semantic_cached = semantic_cache.get(query, model)
#         if semantic_cached:
#             self.cache_hits += 1
#             return {
#                 "response": semantic_cached["text"],
#                 "model": semantic_cached["model"],
#                 "cost_usd": 0.0,
#                 "cache_hit": True,
#                 "cache_type": "semantic",
#                 "similarity_score": semantic_cached.get("similarity_score", 0),
#                 "matched_query": semantic_cached.get("matched_query", ""),
#                 "latency_ms": round((time.time() - start_time) * 1000, 2)
#             }   

#         # Step 4: Call LLM (cache miss)
#         print(f"[ROUTER] Cache miss, calling LLM...")
        
#         try:
#             if config.MOCK_MODE or not self.gemini_configured:
#                 response_text, input_tokens, output_tokens = self._mock_llm_call(query, model)
#             else:
#                 response_text, input_tokens, output_tokens = self._real_gemini_call(query, model)
#         except Exception as e:
#             print(f"[ROUTER] Error: {e}")
#             response_text, input_tokens, output_tokens = self._mock_llm_call(query, model)
#             response_text = f"[FALLBACK MODE] {response_text}"
        
#         # Step 5: Calculate cost
#         cost = config.get_model_cost(model, int(input_tokens), int(output_tokens))
#         self.total_cost += cost
#         self.query_count += 1
        
#         # Step 6: Cache the response for EXACT model
#         cache.set(query, model, {
#             "text": response_text,
#             "model": model,
#             "tokens": {"input": input_tokens, "output": output_tokens}
#         })

#         semantic_cache.set(query, model, {
#             "text": response_text,
#             "model": model,
#             "tokens": {"input": input_tokens, "output": output_tokens}
#         })
        
#         latency = round((time.time() - start_time) * 1000, 2)
        
#         # Determine routing reason
#         if complexity_score < config.SIMPLE_QUERY_THRESHOLD:
#             routing_reason = f"Simple query (score {complexity_score}) → cheap model"
#         elif complexity_score < config.COMPLEX_QUERY_THRESHOLD:
#             routing_reason = f"Medium complexity (score {complexity_score}) → balanced model"
#         else:
#             routing_reason = f"Complex query (score {complexity_score}) → powerful model"
        
#         return {
#             "response": response_text,
#             "model": model,
#             "cost_usd": round(cost, 6),
#             "cache_hit": False,
#             "complexity_score": complexity_score,
#             "tokens": {"input": int(input_tokens), "output": int(output_tokens)},
#             "latency_ms": latency,
#             "routing_reason": routing_reason,
#             "mode": "mock" if config.MOCK_MODE else "real",
#             "analysis_breakdown": analysis.get("breakdown", {}),
#             "routing_method": "ml" if ml_router.model is not None else "heuristic",
#             "routing_confidence": round(confidence, 2)
#         }
    
#     def _real_gemini_call(self, query: str, model: str) -> tuple:
#         """
#         Real Gemini API call
#         CHANGED: Completely new method for Gemini
#         """
#         try:
#             gemini_model = genai.GenerativeModel(model)
#             response = gemini_model.generate_content(query)
#             response_text = response.text

#             # Use rough estimation: ~1.3 tokens per word
#             input_tokens = len(query.split()) * 1.3
#             output_tokens = len(response_text.split()) * 1.3
            
#             print(f"[ROUTER] ✅ Gemini {model} responded successfully")
            
#             return response_text, int(input_tokens), int(output_tokens)
            
#         except Exception as e:
#             error_msg = str(e)
#             print(f"[ERROR] Gemini API error: {error_msg}")
            
#             if "API_KEY_INVALID" in error_msg or "invalid api key" in error_msg.lower():
#                 raise Exception("Invalid Gemini API key - get one at https://aistudio.google.com/app/apikey")
#             elif "quota" in error_msg.lower() or "rate" in error_msg.lower():
#                 raise Exception("Gemini rate limit exceeded - wait 1 minute (15 req/min limit)")
#             else:
#                 raise Exception(f"Gemini API error: {error_msg}")
    
   
#     def _mock_llm_call(self, query: str, model: str) -> tuple:
#         """Mock LLM response for testing without API costs"""
#         time.sleep(0.1)  # Simulate API latency
        
#         response = f"This is a simulated response from {model}. "
        
#         if "what" in query.lower() or "explain" in query.lower():
#             response += f"In a real scenario, I would explain: {query[:100]}... "
#         elif "how" in query.lower():
#             response += f"Here's how: {query[:100]}... "
#         else:
#             response += f"Regarding your query: {query[:100]}... "
        
#         response += "This is MOCK mode - set GEMINI_API_KEY environment variable for real responses."
        
#         # Estimate tokens (rough approximation)
#         input_tokens = len(query.split()) * 1.3
#         output_tokens = len(response.split()) * 1.3
        
#         return response, input_tokens, output_tokens
    
#     def get_stats(self) -> Dict[str, Any]:
#         """Get router statistics"""
#         cache_rate = round(self.cache_hits / max(self.query_count, 1) * 100, 1)
#         avg_cost = round(self.total_cost / max(self.query_count, 1), 4)
        
#         return {
#             "total_queries": self.query_count,
#             "total_cost_usd": round(self.total_cost, 4),
#             "cache_hits": self.cache_hits,
#             "cache_hit_rate": cache_rate,
#             "avg_cost_per_query": avg_cost,
#             "estimated_savings_usd": round(self.cache_hits * avg_cost, 2),
#             "mode": "mock" if config.MOCK_MODE else "real"
#         }


# # Global router instance
# router = LLMRouter()

"""
router.py - Main LLM Router  [HEAVILY UPGRADED]

This is the heart of the system. Every /chat request flows through here.
It orchestrates all the other modules in the right order.

REQUEST FLOW:
  1. Rate limit check     → block abusers
  2. Budget check         → stop runaway spend
  3. Complexity analysis  → score the query 0–1
  4. Model selection      → Flash or Pro?
  5. Exact cache check    → free response?
  6. Semantic cache check → similar query cached?
  7. Gemini API call      → real response (if not cached)
  8. Store in both caches
  9. Log to CSV
  10. Return to caller

KEY DESIGN DECISION - Why not call ML router here?
  The ML router (ml_router.py) runs async in the background.
  It reads the CSV logs and re-trains periodically.
  When trained, it overrides step 4 if confidence > 0.7.
  This keeps the hot path fast.
"""

import time
import random
from typing import Dict, Any, Optional
from app.analyzer    import compute_complexity, select_model
from app.cache       import ExactCache
from app.semantic_cache import SemanticCache
from app.budget      import BudgetEnforcer, BudgetExceededError
from app.rate_limiter import RateLimiter
from app.logger      import RequestLogger
from app.config      import (
    GEMINI_API_KEY, MOCK_MODE, MODEL_COSTS,
    GEMINI_FLASH, GEMINI_PRO,
)

# Try to import Gemini SDK
try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_AVAILABLE = not MOCK_MODE and bool(GEMINI_API_KEY)
except ImportError:
    GEMINI_AVAILABLE = False

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
        self.exact_cache   = ExactCache()
        self.semantic_cache = SemanticCache()
        self.budget        = BudgetEnforcer()
        self.rate_limiter  = RateLimiter()
        self.logger        = RequestLogger()
        # Optional ML router - loaded lazily after training
        self._ml_router    = None

    def load_ml_router(self, ml_router):
        """Called by ml_router.py after training completes."""
        self._ml_router = ml_router

    def _call_gemini(self, query: str, model: str) -> Dict:
        """
        Call real Gemini API.
        Returns {"response": str, "tokens_in": int, "tokens_out": int}
        """
        model_obj = genai.GenerativeModel(model)
        result    = model_obj.generate_content(query)
        text      = result.text

        # Gemini SDK provides usage metadata
        usage     = getattr(result, "usage_metadata", None)
        tokens_in  = getattr(usage, "prompt_token_count",     50)  if usage else 50
        tokens_out = getattr(usage, "candidates_token_count",  80)  if usage else 80

        return {"response": text, "tokens_in": tokens_in, "tokens_out": tokens_out}

    def _mock_call(self, query: str, model: str) -> Dict:
        """
        Fake LLM call for testing. Simulates realistic latency.
        Cost is calculated correctly so budget/analytics are realistic.
        """
        time.sleep(random.uniform(0.05, 0.15))  # realistic latency
        tokens_in  = max(10, len(query.split()) + 5)
        tokens_out = random.randint(60, 180)
        response   = f"[MOCK {model}] {random.choice(MOCK_RESPONSES)} | Query: '{query[:50]}'"
        return {"response": response, "tokens_in": tokens_in, "tokens_out": tokens_out}

    def process(
        self,
        query:    str,
        user_id:  str = "anonymous",
        force_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point. Called by POST /chat.
        Returns full response dict including metadata.
        """
        start_time = time.time()

        # ── 1. Rate limiting ──────────────────────────────────────────────────
        rate_check = self.rate_limiter.check(user_id)
        if not rate_check["allowed"]:
            raise ValueError(
                f"Rate limit exceeded. Limit: {rate_check['limit']}/hour. "
                f"Retry after {rate_check['retry_after']}s."
            )

        # ── 2. Budget check ───────────────────────────────────────────────────
        self.budget.check_budget()  # raises BudgetExceededError if over limit

        # ── 3. Complexity analysis ────────────────────────────────────────────
        complexity_result = compute_complexity(query)
        complexity_score  = complexity_result["composite"]

        # ── 4. Model selection ────────────────────────────────────────────────
        if force_model:
            model = force_model  # caller explicitly chose a model
        elif self._ml_router and self._ml_router.is_trained:
            # ML router overrides heuristic when confidence > 0.7
            ml_result = self._ml_router.predict(query)
            model     = ml_result["model"] if ml_result["confidence"] > 0.7 else select_model(complexity_score)
        else:
            model = select_model(complexity_score)

        # ── 5. Exact cache check ──────────────────────────────────────────────
        cached = self.exact_cache.get(query, model)
        if cached:
            latency_ms = (time.time() - start_time) * 1000
            self.logger.log(user_id, query, model, complexity_score, 0, 0, 0.0, True, "exact", latency_ms)
            return {
                "response":        cached["response"],
                "model":           model,
                "cost_usd":        0.0,
                "cache_hit":       True,
                "cache_type":      "exact",
                "complexity_score": complexity_score,
                "tokens":          {"input": 0, "output": 0},
                "latency_ms":      round(latency_ms, 2),
            }

        # ── 6. Semantic cache check ───────────────────────────────────────────
        sem_cached = self.semantic_cache.get(query)
        if sem_cached:
            latency_ms = (time.time() - start_time) * 1000
            self.logger.log(user_id, query, sem_cached["model"], complexity_score, 0, 0, 0.0, True, "semantic", latency_ms)
            return {
                "response":          sem_cached["response"],
                "model":             sem_cached["model"],
                "cost_usd":          0.0,
                "cache_hit":         True,
                "cache_type":        "semantic",
                "semantic_similarity": sem_cached.get("similarity_score"),
                "complexity_score":  complexity_score,
                "tokens":            {"input": 0, "output": 0},
                "latency_ms":        round(latency_ms, 2),
            }

        # ── 7. LLM API call ───────────────────────────────────────────────────
        try:
            if GEMINI_AVAILABLE:
                llm_result = self._call_gemini(query, model)
            else:
                llm_result = self._mock_call(query, model)
        except Exception as e:
            # API failure → fall back to mock so the app never 500s
            llm_result = self._mock_call(query, model)
            llm_result["response"] += f" [FALLBACK: {str(e)[:80]}]"

        cost = _calculate_cost(model, llm_result["tokens_in"], llm_result["tokens_out"])

        # ── 8. Record cost ────────────────────────────────────────────────────
        self.budget.record_cost(cost)

        # ── 9. Store in both caches ───────────────────────────────────────────
        self.exact_cache.set(query, model, llm_result["response"], cost)
        self.semantic_cache.set(query, llm_result["response"], model, cost)

        # ── 10. Log to CSV ────────────────────────────────────────────────────
        latency_ms = (time.time() - start_time) * 1000
        self.logger.log(
            user_id, query, model, complexity_score,
            llm_result["tokens_in"], llm_result["tokens_out"],
            cost, False, "none", latency_ms,
        )

        return {
            "response":         llm_result["response"],
            "model":            model,
            "cost_usd":         round(cost, 8),
            "cache_hit":        False,
            "cache_type":       "none",
            "complexity_score": complexity_score,
            "complexity_factors": complexity_result["factors"],
            "tokens":           {"input": llm_result["tokens_in"], "output": llm_result["tokens_out"]},
            "latency_ms":       round(latency_ms, 2),
        }

    def get_full_stats(self) -> Dict:
        """Aggregated stats for GET /stats endpoint."""
        from app.analytics import compute_analytics
        from app.config    import LOG_FILE
        return {
            "exact_cache":    self.exact_cache.stats(),
            "semantic_cache": self.semantic_cache.stats(),
            "budget":         self.budget.status(),
            "rate_limiter":   self.rate_limiter.stats(),
            "analytics":      compute_analytics(LOG_FILE),
            "ml_router":      {
                "trained":    self._ml_router.is_trained if self._ml_router else False,
                "model_type": "RandomForest" if self._ml_router else "heuristic",
            },
        }