# API Reference

Complete API documentation for LLM Cost Firewall.

**Base URL:** `http://localhost:8000`  
**Interactive Docs:** `http://localhost:8000/docs`

---

## Core Endpoints

### POST /chat
Send a query and get optimized response.

**Request:**
```json
{
  "query": "Explain machine learning",
  "user_id": "user123"  // optional, default: "default"
}
```

**Response:**
```json
{
  "response": "Machine learning is...",
  "model": "gemini-flash-latest",
  "cost_usd": 0.0,
  "cache_hit": false,
  "complexity_score": 0.45,
  "tokens": {
    "input": 26,
    "output": 156
  },
  "latency_ms": 487,
  "routing_reason": "Medium complexity → balanced model",
  "mode": "real",
  "routing_method": "ml",
  "routing_confidence": 0.87
}
```

**Status Codes:**
- `200` - Success
- `429` - Rate limit exceeded
- `500` - Server error

---

### GET /analytics
Get comprehensive analytics.

**Response:**
```json
{
  "total_requests": 150,
  "total_cost": 0.45,
  "total_savings": 0.23,
  "cache_stats": {
    "exact_hits": 35,
    "semantic_hits": 15,
    "misses": 100,
    "hit_rate": 33.3
  },
  "model_usage": {
    "gemini-flash-latest": 120,
    "gemini-pro-latest": 30
  }
}
```

---

### GET /stats
Get router statistics.

**Response:**
```json
{
  "router": {
    "total_queries": 150,
    "total_cost_usd": 0.45,
    "cache_hits": 50,
    "cache_hit_rate": 33.3,
    "avg_cost_per_query": 0.003,
    "estimated_savings_usd": 0.15,
    "mode": "real"
  },
  "cache": {
    "total_cached": 105,
    "ttl_seconds": 3600
  }
}
```

---

### GET /history
Get recent request history.

**Query Parameters:**
- `limit` (optional, default: 20) - Number of recent requests

**Response:**
```json
{
  "requests": [
    {
      "timestamp": "2026-01-08T10:30:00",
      "query": "what is AI?",
      "model": "gemini-flash-latest",
      "cost": 0.0,
      "cached": true
    }
  ],
  "total": 150
}
```

---

### GET /rate-limit/{user_id}
Check rate limit status for a user.

**Response:**
```json
{
  "user_id": "user123",
  "requests_used": 45,
  "requests_remaining": 55,
  "limit": 100,
  "reset_time": "2026-01-08T11:30:00"
}
```

---

### POST /train-ml-router
Train ML routing model from logs.

**Query Parameters:**
- `min_samples` (optional, default: 50) - Minimum samples needed

**Response:**
```json
{
  "status": "trained",
  "message": "ML routing model trained successfully",
  "stats": {
    "status": "trained",
    "using": "ml_model",
    "model_type": "RandomForest",
    "features": 100,
    "supported_models": ["gemini-flash-latest", "gemini-pro-latest"]
  }
}
```

---

### GET /ml-router/stats
Get ML router status.

**Response:**
```json
{
  "status": "trained",
  "using": "ml_model",
  "model_type": "RandomForest",
  "features": 100,
  "supported_models": ["gemini-flash-latest", "gemini-pro-latest"]
}
```

---

## Testing Endpoints

### GET /test/routing
Test routing logic with sample queries.

**Response:**
```json
{
  "routing_tests": [
    {
      "query": "What is 2+2?",
      "complexity": 0.15,
      "routed_to": "gemini-flash-latest"
    },
    {
      "query": "Analyze quantum physics...",
      "complexity": 0.85,
      "routed_to": "gemini-pro-latest"
    }
  ]
}
```

---

### GET /test/cache
Test cache functionality.

**Response:**
```json
{
  "exact_match": {
    "query": "What is machine learning?",
    "cached": true,
    "type": "exact"
  },
  "semantic_match": {
    "query": "What is ML?",
    "cached": true,
    "type": "semantic"
  }
}
```

---

## Admin Endpoints

### POST /cache/clear
Clear all cached responses.

**Response:**
```json
{
  "message": "Cache cleared successfully"
}
```

---

### GET /export/csv
Download full request log as CSV.

**Returns:** CSV file download

---

## Error Responses

All endpoints may return these error formats:

**Rate Limit Error (429):**
```json
{
  "detail": "Rate limit exceeded. Max 100 requests/hour."
}
```

**Server Error (500):**
```json
{
  "detail": "Gemini API error: quota exceeded"
}
```

---

## Rate Limits

- **Per User:** 100 requests/hour
- **Gemini API:** 15 requests/minute (free tier)
- **Reset:** Rolling 1-hour window

---

## Best Practices

1. **Include user_id** for proper rate limiting
2. **Handle 429 errors** with exponential backoff
3. **Cache responses** on your end when possible
4. **Monitor /stats** endpoint for usage patterns
5. **Train ML router** after collecting 50+ requests