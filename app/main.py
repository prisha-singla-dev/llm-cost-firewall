"""
FastAPI server for LLM Cost Firewall
"""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from app.router import router
from app.cache import cache

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)