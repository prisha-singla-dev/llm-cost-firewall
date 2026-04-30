# """
# FastAPI server for LLM Cost Firewall
# """
# import time
# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# from typing import Optional
# from collections import defaultdict
# from fastapi.responses import FileResponse
# from app.router import router
# from app.cache import cache
# from app.logger import request_logger
# from app.analytics import analytics
# from app.ml_router import ml_router
# from fastapi.middleware.cors import CORSMiddleware


# app = FastAPI(
#     title="LLM Cost Firewall",
#     description="Intelligent proxy that cuts LLM costs by 60%",
#     version="0.1.0"
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000"], 
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# class QueryRequest(BaseModel):
#     query: str
#     user_id: Optional[str] = "default"

# # Rate limiter
# request_counts = defaultdict(list)
# RATE_LIMIT_HOURLY = 100

# def check_rate_limit(user_id: str):
#     """Check if user has exceeded rate limit"""
#     now = time.time()
#     hour_ago = now - 3600
    
#     # Clean old requests
#     request_counts[user_id] = [
#         t for t in request_counts[user_id] if t > hour_ago
#     ]
    
#     # Check limit
#     if len(request_counts[user_id]) >= RATE_LIMIT_HOURLY:
#         raise HTTPException(
#             status_code=429,
#             detail=f"Rate limit exceeded. Max {RATE_LIMIT_HOURLY} requests/hour."
#         )
    
#     # Record this request
#     request_counts[user_id].append(now)

# @app.get("/")
# async def root():
#     """Health check endpoint"""
#     return {
#         "status": "running",
#         "message": "LLM Cost Firewall is active",
#         "docs": "/docs"
#     }

# @app.post("/chat")
# async def chat(request: QueryRequest):
#     """
#     Main endpoint: Send query, get optimized response
#     + Analytics
#     Example:
#     POST /chat
#     {
#         "query": "What is machine learning?",
#         "user_id": "user_123"
#     }
#     """
#     check_rate_limit(request.user_id)
#     result = await router.route_query(request.query, request.user_id)
#     request_logger.log(request.query, result)
#     analytics.log_request(request.query, result, request.user_id)
#     return result

# @app.get("/rate-limit/{user_id}")
# async def get_rate_limit_status(user_id: str):
#     """Check user's current rate limit status"""
#     now = time.time()
#     hour_ago = now - 3600
    
#     recent_requests = [
#         t for t in request_counts.get(user_id, []) if t > hour_ago
#     ]
    
#     return {
#         "user_id": user_id,
#         "requests_this_hour": len(recent_requests),
#         "limit": RATE_LIMIT_HOURLY,
#         "remaining": RATE_LIMIT_HOURLY - len(recent_requests),
#         "reset_in_seconds": int(3600 - (now - min(recent_requests, default=now)))
#     }

# @app.get("/stats")
# async def get_stats():
#     """Get cost and usage statistics"""
#     router_stats = router.get_stats()
#     cache_stats = cache.get_stats()
    
#     return {
#         "router": router_stats,
#         "cache": cache_stats,
#         "savings": {
#             "cache_saved_usd": round(
#                 router_stats["cache_hits"] * router_stats["avg_cost_per_query"], 2
#             )
#         }
#     }

# @app.get("/analytics")
# async def get_analytics():
#     """Get comprehensive analytics"""
#     return analytics.get_analytics()

# @app.get("/history")
# async def get_history(limit: int = 20):
#     """Get recent request history"""
#     return {
#         "recent_requests": analytics.get_recent(limit)
#     }

# @app.get("/export/csv")
# async def export_csv():
#     """Download full request log as CSV"""
#     csv_path = analytics.export_csv()
#     return FileResponse(
#         csv_path,
#         media_type="text/csv",
#         filename="cost_firewall_requests.csv"
#     )

# @app.post("/cache/clear")
# async def clear_cache():
#     """Clear all cached responses (admin endpoint)"""
#     cache.clear()
#     return {"message": "Cache cleared successfully"}

# @app.post("/compare")
# async def compare_models(request: QueryRequest):
#     """
#     Compare costs across different models for same query
#     Useful for analyzing routing decisions
#     """
#     from app.analyzer import analyzer
#     from app.config import config
    
#     analysis = analyzer.analyze(request.query)
#     complexity = analysis["complexity_score"]
    
#     # Estimate cost for different models
#     input_tokens = len(request.query.split()) * 1.3
#     output_tokens = 100
    
#     comparisons = []
#     for model in ["gpt-3.5-turbo", "gpt-4", "claude-haiku-3", "claude-opus-3"]:
#         cost = config.get_model_cost(model, int(input_tokens), int(output_tokens))
#         comparisons.append({
#             "model": model,
#             "estimated_cost_usd": round(cost, 6),
#             "would_route_here": config.select_model(complexity) == model
#         })
    
#     # Sort by cost
#     comparisons.sort(key=lambda x: x["estimated_cost_usd"])
    
#     return {
#         "query": request.query,
#         "complexity_score": complexity,
#         "selected_model": config.select_model(complexity),
#         "comparison": comparisons,
#         "savings_vs_always_gpt4": round(
#             comparisons[-1]["estimated_cost_usd"] - comparisons[0]["estimated_cost_usd"], 
#             6
#         )
#     }

# @app.post("/train-ml-router")
# async def train_ml_router(min_samples: int = 20):
#     """
#     Train ML routing model from request logs
#     Requires at least 50 logged requests
#     """
#     success = ml_router.train_from_logs(min_samples)
    
#     if success:
#         return {
#             "status": "trained",
#             "message": "ML routing model trained successfully",
#             "stats": ml_router.get_stats()
#         }
#     else:
#         return {
#             "status": "skipped",
#             "message": f"Need at least {min_samples} requests to train",
#             "current_logs": "Check logs/requests.csv"
#         }

# @app.get("/ml-router/stats")
# async def get_ml_router_stats():
#     """Get ML router statistics"""
#     return ml_router.get_stats()

# @app.get("/test/routing")
# async def test_routing():
#     """Test routing with sample queries"""
#     from app.analyzer import analyzer
#     from app.config import config
    
#     test_queries = [
#         "What is 2+2?",
#         "Explain machine learning",
#         "Analyze the philosophical implications of artificial consciousness in detail"
#     ]
    
#     results = []
#     for query in test_queries:
#         analysis = analyzer.analyze(query)
#         model = config.select_model(analysis["complexity_score"])
#         results.append({
#             "query": query,
#             "complexity": analysis["complexity_score"],
#             "model_selected": model,
#             "breakdown": analysis.get("breakdown", {})
#         })
    
#     return {"test_results": results}

# @app.get("/test/cache")
# async def test_cache():
#     """Test cache functionality"""
#     from app.cache import cache
    
#     cache.clear()
    
#     test_query = "What is AI?"
#     cache.set(test_query, "gpt-4", {"text": "AI is...", "model": "gpt-4"})
    
#     result = cache.get(test_query, "gpt-4")
    
#     return {
#         "cache_working": result is not None,
#         "cached_response": result if result else "Cache miss",
#         "stats": cache.get_stats()
#     }

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)

"""
main.py - FastAPI Application  [HEAVILY UPGRADED]

All HTTP endpoints live here.
The LLMRouter (router.py) does the actual work — main.py just handles
HTTP concerns: request parsing, error codes, response format.

ENDPOINTS:
  POST /chat              → main query endpoint
  GET  /health            → liveness probe (for Railway/Render)
  GET  /stats             → full system statistics
  GET  /history           → recent request log
  GET  /export/csv        → download full CSV log
  GET  /predict           → cost prediction BEFORE making a call
  GET  /compare           → compare cost across both models
  POST /train             → trigger ML router training
  POST /budget/configure  → update budget limits at runtime
  DELETE /cache           → clear both caches
"""

import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
from contextlib import asynccontextmanager

from app.router  import LLMRouter
from app.ml_router import MLRouter
from app.budget  import BudgetExceededError
from app.config  import MOCK_MODE, MODEL_COSTS


# ─── Pydantic models (request/response shapes) ────────────────────────────────

class ChatRequest(BaseModel):
    query:       str            = Field(..., min_length=1, max_length=10000)
    user_id:     Optional[str]  = "anonymous"
    force_model: Optional[str]  = None  # override routing if set

    class Config:
        json_schema_extra = {"example": {
            "query":   "Explain how transformers work in deep learning",
            "user_id": "user_123",
        }}

class BudgetConfig(BaseModel):
    daily_budget_usd:  Optional[float] = Field(None, gt=0)
    hourly_budget_usd: Optional[float] = Field(None, gt=0)


# ─── App lifecycle ────────────────────────────────────────────────────────────

router_instance:    LLMRouter = None
ml_router_instance: MLRouter  = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global router_instance, ml_router_instance
    ml_router_instance = MLRouter()         # load trained model if exists
    router_instance    = LLMRouter()
    router_instance.load_ml_router(ml_router_instance)
    print(f"✅ LLM Cost Firewall started | MOCK_MODE={MOCK_MODE}")
    yield
    print("🛑 Shutting down")

app = FastAPI(
    title="LLM Cost Firewall",
    description="Intelligent LLM proxy — cuts Gemini API costs by 60% through smart routing + dual caching",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """
    Liveness probe — Railway/Render call this to check if the app is up.
    Must return 200 quickly.
    """
    return {"status": "ok", "mock_mode": MOCK_MODE}


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Main endpoint. Send a query, get an LLM response + full metadata.
    
    The metadata (cost_usd, model, cache_hit, complexity_score) is what makes
    this system observable. You can see exactly why each routing decision was made.
    """
    try:
        result = router_instance.process(
            query=req.query,
            user_id=req.user_id,
            force_model=req.force_model,
        )
        return result

    except BudgetExceededError as e:
        # HTTP 402 Payment Required — semantically correct for budget exceeded
        raise HTTPException(status_code=402, detail={
            "error":   "budget_exceeded",
            "message": e.message,
            "spent":   e.spent,
            "limit":   e.limit,
        })

    except ValueError as e:
        # Rate limit or validation error
        raise HTTPException(status_code=429, detail={"error": "rate_limited", "message": str(e)})

    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "internal_error", "message": str(e)})


@app.get("/stats")
async def stats():
    """
    Full system statistics.
    Shows cache performance, budget status, model distribution, latency percentiles.
    The React dashboard polls this every 10 seconds.
    """
    return router_instance.get_full_stats()


@app.get("/history")
async def history(limit: int = 50, user_id: Optional[str] = None):
    """Recent request history from the CSV log."""
    rows = router_instance.logger.read_all(limit=limit)
    if user_id:
        rows = [r for r in rows if r.get("user_id") == user_id]
    return {"total": len(rows), "requests": rows}


@app.get("/export/csv")
async def export_csv():
    """Download the full request log as CSV."""
    content = router_instance.logger.export_csv_string()
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=llm_requests.csv"},
    )


@app.get("/predict")
async def predict(query: str):
    """
    Estimate cost BEFORE making a real call.
    Useful for showing users "this will cost ~$0.0002" before they confirm.
    """
    from app.analyzer import compute_complexity, select_model

    complexity = compute_complexity(query)
    model      = select_model(complexity["composite"])
    tokens_est = max(10, len(query.split()) + 5)
    pricing    = MODEL_COSTS.get(model, list(MODEL_COSTS.values())[0])
    cost_est   = (tokens_est / 1000 * pricing["input"]) * 2.0  # rough estimate

    return {
        "predicted_model":    model,
        "complexity_score":   complexity["composite"],
        "complexity_factors": complexity["factors"],
        "estimated_cost_usd": round(cost_est, 8),
        "query_length_chars": len(query),
        "query_word_count":   len(query.split()),
    }


@app.get("/compare")
async def compare(query: str):
    """Show what each model would cost for this query."""
    from app.analyzer import compute_complexity
    tokens_est = max(10, len(query.split()) + 5)
    complexity = compute_complexity(query)

    return {
        "query_complexity": complexity["composite"],
        "models": {
            model: {
                "estimated_cost_usd": round(
                    (tokens_est / 1000 * pricing["input"]) * 2.0, 8
                ),
                "input_price_per_1k":  pricing["input"],
                "output_price_per_1k": pricing["output"],
            }
            for model, pricing in MODEL_COSTS.items()
        },
    }


@app.post("/train")
async def train():
    """
    Train the ML router on accumulated request logs.
    Needs ≥50 real (non-cached) requests first.
    After training, the ML model replaces the heuristic analyzer.
    """
    result = ml_router_instance.train()
    if result["success"]:
        router_instance.load_ml_router(ml_router_instance)
    return result


@app.post("/budget/configure")
async def configure_budget(config: BudgetConfig):
    """Update budget limits without restarting the server."""
    router_instance.budget.update_limits(
        daily=config.daily_budget_usd,
        hourly=config.hourly_budget_usd,
    )
    return {"message": "Budget updated", "status": router_instance.budget.status()}


@app.delete("/cache")
async def clear_cache():
    """Clear both caches. Useful after updating prompts or for testing."""
    router_instance.exact_cache.clear()
    router_instance.semantic_cache.clear()
    return {"message": "Both caches cleared"}


@app.get("/")
async def root():
    return {
        "service": "LLM Cost Firewall",
        "version": "2.0.0",
        "docs":    "/docs",
        "health":  "/health",
        "status":  "running",
    }