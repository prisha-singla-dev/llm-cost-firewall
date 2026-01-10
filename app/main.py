"""
FastAPI server for LLM Cost Firewall
"""
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from collections import defaultdict
from fastapi.responses import FileResponse
from app.router import router
from app.cache import cache
from app.logger import request_logger
from app.analytics import analytics
from app.ml_router import ml_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="LLM Cost Firewall",
    description="Intelligent proxy that cuts LLM costs by 60%",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = "default"

# Rate limiter
request_counts = defaultdict(list)
RATE_LIMIT_HOURLY = 100

def check_rate_limit(user_id: str):
    """Check if user has exceeded rate limit"""
    now = time.time()
    hour_ago = now - 3600
    
    # Clean old requests
    request_counts[user_id] = [
        t for t in request_counts[user_id] if t > hour_ago
    ]
    
    # Check limit
    if len(request_counts[user_id]) >= RATE_LIMIT_HOURLY:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_HOURLY} requests/hour."
        )
    
    # Record this request
    request_counts[user_id].append(now)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "LLM Cost Firewall is active",
        "docs": "/docs"
    }

@app.post("/chat")
async def chat(request: QueryRequest):
    """
    Main endpoint: Send query, get optimized response
    + Analytics
    Example:
    POST /chat
    {
        "query": "What is machine learning?",
        "user_id": "user_123"
    }
    """
    check_rate_limit(request.user_id)
    result = await router.route_query(request.query, request.user_id)
    request_logger.log(request.query, result)
    analytics.log_request(request.query, result, request.user_id)
    return result

@app.get("/rate-limit/{user_id}")
async def get_rate_limit_status(user_id: str):
    """Check user's current rate limit status"""
    now = time.time()
    hour_ago = now - 3600
    
    recent_requests = [
        t for t in request_counts.get(user_id, []) if t > hour_ago
    ]
    
    return {
        "user_id": user_id,
        "requests_this_hour": len(recent_requests),
        "limit": RATE_LIMIT_HOURLY,
        "remaining": RATE_LIMIT_HOURLY - len(recent_requests),
        "reset_in_seconds": int(3600 - (now - min(recent_requests, default=now)))
    }

@app.get("/stats")
async def get_stats():
    """Get cost and usage statistics"""
    router_stats = router.get_stats()
    cache_stats = cache.get_stats()
    
    return {
        "router": router_stats,
        "cache": cache_stats,
        "savings": {
            "cache_saved_usd": round(
                router_stats["cache_hits"] * router_stats["avg_cost_per_query"], 2
            )
        }
    }

@app.get("/analytics")
async def get_analytics():
    """Get comprehensive analytics"""
    return analytics.get_analytics()

@app.get("/history")
async def get_history(limit: int = 20):
    """Get recent request history"""
    return {
        "recent_requests": analytics.get_recent(limit)
    }

@app.get("/export/csv")
async def export_csv():
    """Download full request log as CSV"""
    csv_path = analytics.export_csv()
    return FileResponse(
        csv_path,
        media_type="text/csv",
        filename="cost_firewall_requests.csv"
    )

@app.post("/cache/clear")
async def clear_cache():
    """Clear all cached responses (admin endpoint)"""
    cache.clear()
    return {"message": "Cache cleared successfully"}

@app.post("/compare")
async def compare_models(request: QueryRequest):
    """
    Compare costs across different models for same query
    Useful for analyzing routing decisions
    """
    from app.analyzer import analyzer
    from app.config import config
    
    analysis = analyzer.analyze(request.query)
    complexity = analysis["complexity_score"]
    
    # Estimate cost for different models
    input_tokens = len(request.query.split()) * 1.3
    output_tokens = 100
    
    comparisons = []
    for model in ["gpt-3.5-turbo", "gpt-4", "claude-haiku-3", "claude-opus-3"]:
        cost = config.get_model_cost(model, int(input_tokens), int(output_tokens))
        comparisons.append({
            "model": model,
            "estimated_cost_usd": round(cost, 6),
            "would_route_here": config.select_model(complexity) == model
        })
    
    # Sort by cost
    comparisons.sort(key=lambda x: x["estimated_cost_usd"])
    
    return {
        "query": request.query,
        "complexity_score": complexity,
        "selected_model": config.select_model(complexity),
        "comparison": comparisons,
        "savings_vs_always_gpt4": round(
            comparisons[-1]["estimated_cost_usd"] - comparisons[0]["estimated_cost_usd"], 
            6
        )
    }

@app.post("/train-ml-router")
async def train_ml_router(min_samples: int = 20):
    """
    Train ML routing model from request logs
    Requires at least 50 logged requests
    """
    success = ml_router.train_from_logs(min_samples)
    
    if success:
        return {
            "status": "trained",
            "message": "ML routing model trained successfully",
            "stats": ml_router.get_stats()
        }
    else:
        return {
            "status": "skipped",
            "message": f"Need at least {min_samples} requests to train",
            "current_logs": "Check logs/requests.csv"
        }

@app.get("/ml-router/stats")
async def get_ml_router_stats():
    """Get ML router statistics"""
    return ml_router.get_stats()

@app.get("/test/routing")
async def test_routing():
    """Test routing with sample queries"""
    from app.analyzer import analyzer
    from app.config import config
    
    test_queries = [
        "What is 2+2?",
        "Explain machine learning",
        "Analyze the philosophical implications of artificial consciousness in detail"
    ]
    
    results = []
    for query in test_queries:
        analysis = analyzer.analyze(query)
        model = config.select_model(analysis["complexity_score"])
        results.append({
            "query": query,
            "complexity": analysis["complexity_score"],
            "model_selected": model,
            "breakdown": analysis.get("breakdown", {})
        })
    
    return {"test_results": results}

@app.get("/test/cache")
async def test_cache():
    """Test cache functionality"""
    from app.cache import cache
    
    cache.clear()
    
    test_query = "What is AI?"
    cache.set(test_query, "gpt-4", {"text": "AI is...", "model": "gpt-4"})
    
    result = cache.get(test_query, "gpt-4")
    
    return {
        "cache_working": result is not None,
        "cached_response": result if result else "Cache miss",
        "stats": cache.get_stats()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)