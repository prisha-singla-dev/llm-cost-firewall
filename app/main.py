"""
FastAPI server for LLM Cost Firewall
"""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from app.router import router
from app.cache import cache
from app.logger import request_logger

app = FastAPI(
    title="LLM Cost Firewall",
    description="Intelligent proxy that cuts LLM costs by 60%",
    version="0.1.0"
)


class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = "default"


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
    
    Example:
    POST /chat
    {
        "query": "What is machine learning?",
        "user_id": "user_123"
    }
    """
    result = await router.route_query(request.query, request.user_id)
    request_logger.log(request.query, result)
    return result


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
    output_tokens = 100  # Assume 100 token response
    
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
    
    # Clear cache first
    cache.clear()
    
    # Test set and get
    test_query = "What is AI?"
    cache.set(test_query, "gpt-4", {"text": "AI is...", "model": "gpt-4"})
    
    # Try to get it back
    result = cache.get(test_query, "gpt-4")
    
    return {
        "cache_working": result is not None,
        "cached_response": result if result else "Cache miss",
        "stats": cache.get_stats()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)