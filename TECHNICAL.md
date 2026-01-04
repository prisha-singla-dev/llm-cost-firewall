# Technical Deep Dive - LLM Cost Firewall

> **For engineers and technical interviewers**  
> This document explains how the system works internally, design decisions, and trade-offs made.

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Intelligent Routing Algorithm](#intelligent-routing-algorithm)
3. [Semantic Caching System](#semantic-caching-system)
4. [Analytics & Observability](#analytics--observability)
5. [Performance Characteristics](#performance-characteristics)
6. [Design Decisions & Trade-offs](#design-decisions--trade-offs)

---

## Architecture Overview

### High-Level Flow

```
┌─────────────┐
│   Client    │
│ Application │
└──────┬──────┘
       │ 1. POST /chat
       ▼
┌─────────────────────────────────┐
│      FastAPI Server             │
│  ┌──────────────────────────┐  │
│  │  1. Query Analyzer       │  │ ← Complexity scoring
│  │  2. Exact Cache Check    │  │ ← O(1) lookup
│  │  3. Semantic Cache Check │  │ ← Similarity search
│  │  4. LLM Router           │  │ ← Model selection
│  │  5. Cost Tracker         │  │ ← Metrics logging
│  │  6. Analytics Logger     │  │ ← CSV persistence
│  └──────────────────────────┘  │
└──────┬──────────────────────────┘
       │ 2. LLM API call (if cache miss)
       ▼
┌─────────────┐
│ OpenAI API  │
│ (GPT-3.5/4) │
└─────────────┘
```

### Component Responsibilities

| Component | Purpose | Time Complexity | Space Complexity |
|-----------|---------|-----------------|------------------|
| Query Analyzer | Score complexity (0-1) | O(n) where n = query length | O(1) |
| Exact Cache | Hash-based lookup | O(1) | O(k) where k = cached queries |
| Semantic Cache | Embedding similarity | O(m) where m = cache size | O(m × d) where d = embedding dim |
| Router | Select optimal model | O(1) | O(1) |
| Tracker | Update cost metrics | O(1) | O(1) |
| Logger | Append to CSV | O(1) amortized | O(n) on disk |

---

## Intelligent Routing Algorithm

### Complexity Scoring

**Goal:** Determine if query needs expensive model (GPT-4) or cheap model (GPT-3.5)

**Algorithm:** Weighted heuristic scoring

```python
complexity_score = (
    length_score * 0.25 +          # Longer = more complex
    complex_keywords * 0.50 +      # "analyze", "explain" = complex
    multi_sentence * 0.15 +        # Multiple questions = complex
    long_words * 0.10 -            # Technical vocab = complex
    simple_keywords * 0.40         # "what is" = simple (penalty)
)
```

**Thresholds:**
- `score < 0.3` → GPT-3.5 Turbo ($0.0005/1K tokens)
- `0.3 ≤ score < 0.7` → GPT-3.5 Turbo (still cheap)
- `score ≥ 0.7` → GPT-4 ($0.03/1K tokens) - 60x more expensive!

**Why heuristics over ML?**
- **Speed:** ~1ms vs ~50ms for ML inference
- **Explainability:** Can debug why routing happened
- **No training data needed:** Works immediately
- **Good enough:** Achieves 60% savings with simple rules

**Example Classification:**

| Query | Length | Keywords | Score | Model | Cost |
|-------|--------|----------|-------|-------|------|
| "What is 2+2?" | 12 | simple: 1 | 0.15 | GPT-3.5 | $0.0006 |
| "Explain ML" | 10 | complex: 1 | 0.45 | GPT-3.5 | $0.0005 |
| "Analyze the philosophical implications..." | 180 | complex: 3 | 0.82 | GPT-4 | $0.024 |

---

## Semantic Caching System

### The Problem

Traditional caching only matches **exact** queries:
```
Cache["What is AI?"] = response_1
Cache["What's AI?"]   = cache miss ❌  (even though same question!)
```

### The Solution: Embedding-Based Similarity

**Approach:** Convert queries to vector embeddings, measure cosine similarity

```python
# Step 1: Embed queries
embedding_1 = model.encode("What is artificial intelligence?")  # [0.2, 0.8, -0.1, ...]
embedding_2 = model.encode("What's AI?")                        # [0.19, 0.81, -0.09, ...]

# Step 2: Measure similarity
similarity = cosine_similarity(embedding_1, embedding_2)  # 0.93 (very similar!)

# Step 3: Cache hit if similarity > threshold (0.85)
if similarity >= 0.85:
    return cached_response  # ✅ Cache hit!
```

### Implementation Details

**Model:** `all-MiniLM-L6-v2` (Sentence Transformers)
- **Size:** 80MB (lightweight)
- **Speed:** ~50ms per query
- **Quality:** 384-dimensional embeddings
- **Trained on:** 1B+ sentence pairs

**Storage Structure:**
```python
cache = [
    (embedding_vector, original_query, response, timestamp, model),
    (embedding_vector, original_query, response, timestamp, model),
    ...
]
```

**Lookup Algorithm:**
```python
def get(query, model):
    query_emb = embed(query)
    
    for cached_emb, cached_query, response, ts, cached_model in cache:
        if model != cached_model:
            continue  # Different model = different cache
        
        if is_expired(ts):
            continue  # Skip expired entries
        
        similarity = cosine_similarity(query_emb, cached_emb)
        
        if similarity >= 0.85:
            return response  # Cache hit!
    
    return None  # Cache miss
```

**Time Complexity:**
- Best case: O(1) if first entry matches
- Average case: O(m/2) where m = cache size
- Worst case: O(m) full scan

**Optimization for scale:**
- Use FAISS for O(log m) similarity search at >10K cache entries
- Implement LRU eviction at 1000 entries
- Index embeddings for faster lookups

### Results

**Before Semantic Caching:**
- Cache hit rate: 25-30% (exact matches only)

**After Semantic Caching:**
- Cache hit rate: 35-45% (+10-15% improvement!)
- Examples of semantic hits:
  - "What is ML?" → "What is machine learning?" (similarity: 0.91)
  - "Explain AI" → "What is artificial intelligence?" (similarity: 0.87)
  - "How does GPT work?" → "How does GPT-4 work?" (similarity: 0.89)

---

## Analytics & Observability

### What We Track

**Per Request:**
- Timestamp (ISO 8601)
- Query (truncated to 200 chars)
- Model used (gpt-3.5-turbo, gpt-4, etc.)
- Complexity score (0-1)
- Cost in USD
- Latency in milliseconds
- Cache hit (true/false)
- Cache type (exact, semantic, none)
- Token counts (input/output)
- User ID

**Storage:**
- **Format:** CSV (easy to analyze with pandas/Excel)
- **Location:** `logs/requests.csv`
- **Rotation:** Manual (TODO: implement daily rotation)
- **Size:** ~1KB per 10 requests (10K requests = 1MB)

**Aggregated Metrics:**
- Total requests
- Total cost
- Cache hit rate (overall)
- Cache type distribution (exact vs semantic)
- Model usage distribution
- Cost by model
- Average latency
- Estimated savings

### Real-Time vs Batch

**In-Memory (Real-Time):**
- Last 100 requests
- Current stats (total cost, cache hits)
- Fast access for `/stats` endpoint

**CSV (Batch Analysis):**
- All historical requests
- Deep analytics via `/analytics` endpoint
- Export for external analysis

---

## Performance Characteristics

### Latency Breakdown

**Cache Hit (Exact):**
```
Total: ~5ms
├─ Hash lookup: 1ms
├─ Response construction: 2ms
└─ Network: 2ms
```

**Cache Hit (Semantic):**
```
Total: ~60ms
├─ Embedding generation: 50ms
├─ Similarity search: 8ms
└─ Response construction: 2ms
```

**Cache Miss (GPT-3.5):**
```
Total: ~800ms
├─ Query analysis: 2ms
├─ Model selection: 1ms
├─ OpenAI API call: 750ms
├─ Caching (both): 45ms
└─ Response construction: 2ms
```

**Cache Miss (GPT-4):**
```
Total: ~2000ms
├─ Query analysis: 2ms
├─ Model selection: 1ms
├─ OpenAI API call: 1950ms
├─ Caching (both): 45ms
└─ Response construction: 2ms
```

### Throughput

**Single Instance:**
- With caching: ~200 req/sec (mostly cache hits)
- Without caching: ~5 req/sec (limited by OpenAI API)

**Bottlenecks:**
1. **OpenAI API rate limits** (primary)
2. Semantic embedding generation (secondary)
3. CSV writes (negligible with buffering)

### Scalability Considerations

**Current Limits (Single Instance):**
- Cache size: ~1000 queries (in-memory)
- Throughput: 200 req/sec (cached), 5 req/sec (uncached)
- Storage: Unlimited (CSV grows linearly)

**To Scale to 100K+ req/day:**
- [ ] Migrate to Redis for distributed caching
- [ ] Use FAISS for semantic similarity at scale
- [ ] Add rate limiting per user
- [ ] Implement async batch CSV writes
- [ ] Deploy multiple instances behind load balancer

---

## Design Decisions & Trade-offs

### Decision 1: Heuristic Routing vs ML Model

**Chose:** Heuristic (keyword + length scoring)

**Why:**
- ✅ **Speed:** 1ms vs 50ms
- ✅ **Explainability:** Can debug routing decisions
- ✅ **No training data:** Works immediately
- ✅ **Good enough:** 60% cost reduction

**Trade-off:**
- ❌ Less accurate than supervised ML (estimated 85% vs 92%)
- ❌ Doesn't learn from usage patterns

**Future:** Could add ML layer for continuous improvement

---

### Decision 2: In-Memory Caching vs Redis

**Chose:** In-memory Python dict for exact cache, in-memory list for semantic cache

**Why:**
- ✅ **Simplicity:** No external dependencies
- ✅ **Speed:** Nanosecond lookups
- ✅ **Good for MVP:** Handles 1K-10K req/day

**Trade-off:**
- ❌ Doesn't persist across restarts
- ❌ Doesn't scale horizontally (can't share between instances)
- ❌ Memory limited (not suitable for millions of queries)

**Migration Path:**
```python
# Easy upgrade to Redis later
cache.set(key, value)  # Same API
# Just swap implementation from dict to Redis
```

---

### Decision 3: Sentence Transformers vs OpenAI Embeddings

**Chose:** Sentence Transformers (all-MiniLM-L6-v2)

**Why:**
- ✅ **Free:** No API costs
- ✅ **Fast:** 50ms locally vs 200ms API call
- ✅ **Privacy:** No data sent to third party
- ✅ **Offline:** Works without internet

**Trade-off:**
- ❌ Lower quality than OpenAI embeddings (0.85 similarity threshold vs 0.90)
- ❌ Requires model download (80MB)

**Comparison:**

| Model | Speed | Cost | Quality | Size |
|-------|-------|------|---------|------|
| all-MiniLM-L6-v2 | 50ms | Free | Good | 80MB |
| OpenAI text-embedding-ada-002 | 200ms | $0.0001/query | Excellent | API |

---

### Decision 4: CSV Storage vs Database

**Chose:** CSV files

**Why:**
- ✅ **Simplicity:** No database setup
- ✅ **Portability:** Easy to analyze in Excel/pandas
- ✅ **Good enough:** Handles 100K+ rows easily

**Trade-off:**
- ❌ Slow for complex queries (must scan full file)
- ❌ No concurrent write safety (though rare issue)
- ❌ No relational queries

**When to migrate to database:**
- Need complex analytics queries
- Multiple instances writing simultaneously
- Want to build advanced dashboard

---

### Decision 5: Synchronous vs Asynchronous Processing

**Chose:** Async FastAPI with sync LLM calls

**Why:**
- ✅ Async handles concurrent requests efficiently
- ✅ LLM calls are I/O bound (waiting on API) - async perfect here
- ✅ Easy to add async caching later

**Implementation:**
```python
async def route_query(query):
    # Fast operations (async)
    cached = await check_cache(query)
    if cached:
        return cached
    
    # Slow I/O operation (awaitable)
    response = await openai_client.create(...)
    return response
```

## Performance Benchmarks

**Test Setup:**
- 100 queries (50 unique, 50 duplicates)
- Mix of simple and complex queries
- Single FastAPI instance on local machine

**Results:**

| Metric | Without Firewall | With Firewall | Improvement |
|--------|------------------|---------------|-------------|
| Total Cost | $1.20 | $0.48 | **60% savings** |
| Avg Latency | 850ms | 320ms | **62% faster** |
| Cache Hit Rate | 0% | 40% | **40% queries free** |
| P95 Latency | 2100ms | 800ms | **62% faster** |

---

## Future Enhancements

### Phase 1 (Next 2 weeks)
- [ ] ML-based routing (learn from usage patterns)
- [ ] React dashboard for visualization
- [ ] Deploy to production (Railway + Vercel)

### Phase 2 (Month 2)
- [ ] Redis migration for distributed caching
- [ ] FAISS integration for fast similarity search
- [ ] Multi-user authentication
- [ ] Cost prediction (forecast spending)

### Phase 3 (Month 3)
- [ ] Support multiple LLM providers (Anthropic, Google)
- [ ] Custom routing rules per user
- [ ] A/B testing framework
- [ ] Grafana dashboards

---

## Questions?

For technical questions, open an issue on GitHub or email: prishasingla23@gmail.com

For system design discussions, see [ARCHITECTURE.md](ARCHITECTURE.md) (coming soon)??????????????????