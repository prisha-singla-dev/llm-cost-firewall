# 🔥 LLM Cost Firewall

[![Tests](https://github.com/prisha-singla-dev/llm-cost-firewall/actions/workflows/test.yml/badge.svg)](https://github.com/prisha-singla-dev/llm-cost-firewall/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![Deployed on Render](https://img.shields.io/badge/deployed-Render-purple.svg)](https://render.com)

> Intelligent LLM proxy that cuts Gemini API costs by **60%** through smart routing,
> dual-layer semantic caching, budget enforcement, and rate limiting.

---

## 🔗 Live Demo

| | Link |
|---|---|
| **📊 Dashboard** | https://prisha-singla-dev.github.io/llm-cost-firewall/ |
| **🚀 API (Swagger)** | https://YOUR-RENDER-URL.onrender.com/docs |
| **💻 Source Code** | https://github.com/prisha-singla-dev/llm-cost-firewall |

> ⚠️ API runs on Render free tier — first request after inactivity takes ~30s to wake up. The dashboard is always instant.

---

## The Problem

Every LLM-powered product treats all queries the same — a *"What is Python?"* hits the same expensive model as a 6-paragraph architecture analysis. That's like hiring a senior architect to answer "where's the bathroom."

This proxy fixes that. It sits between your app and the Gemini API, routing each query to the cheapest model that can handle it.

---

## Architecture

```
Your App
    │
    ▼
┌──────────────────────────────────────────────┐
│             LLM Cost Firewall                │
│                                              │
│  1. Sliding Window Rate Limiter              │
│         ↓                                   │
│  2. Budget Enforcer  (HTTP 402 on breach)    │
│         ↓                                   │
│  3. 6-Factor Complexity Analyzer            │
│         ↓                                   │
│  4. ML Router  (Random Forest)               │
│         ↓                                   │
│  5. Dual Semantic Cache                      │
│         ↓  (cache miss only)                │
│  6. Gemini API  (retry on 429)               │
└──────────────────────────────────────────────┘
    │
    ▼
gemini-2.5-flash  /  gemini-2.5-pro
(17× cost difference between the two)
```

---

## Features

| Feature | How it works |
|---|---|
| **6-Factor Complexity Analyzer** | Scores every query 0→1 using keyword density, word count, sentence structure, code block presence (+0.35 boost), technical jargon count, and question count |
| **ML Router (Random Forest)** | Trained on your own request logs via `POST /train`. 12-feature classifier routes to Flash or Pro. Falls back to heuristic until 50+ samples collected. Overrides heuristic when confidence > 70% |
| **Dual Semantic Cache** | Layer 1: SHA-256 exact hash match. Layer 2: `all-MiniLM-L6-v2` embeddings + cosine similarity ≥ 0.92. *"What is ML?"* and *"Explain machine learning briefly"* share the same cache entry. Cache hit = $0.00 cost |
| **Budget Enforcer** | Hard daily + hourly spend limits. Returns HTTP 402 when exceeded. Configurable at runtime via `POST /budget/configure` without restart |
| **Sliding Window Rate Limiter** | Per-user request deque. More accurate than fixed-window counters — no burst abuse at window resets. Returns exact retry-after seconds |
| **Exponential Backoff Retry** | 429 quota errors trigger automatic retry: wait 2s → 4s → 8s before returning a clean human-readable error |
| **Cost Prediction** | `GET /predict` estimates cost and predicts routing decision before making the actual API call |
| **CSV Export** | `GET /export/csv` downloads full request history for business analysis |

---

## Quick Start

```bash
git clone https://github.com/prisha-singla-dev/llm-cost-firewall.git
cd llm-cost-firewall

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Open .env and set:
#   GEMINI_API_KEY=your-key-here
#   MOCK_MODE=false
```

Get a **free** Gemini API key (no credit card) at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

```bash
uvicorn app.main:app --reload
```

- **API docs:** http://localhost:8000/docs
- **Dashboard:** open `frontend/dashboard/index.html` in your browser, set API Base to `http://localhost:8000`

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/chat` | POST | Send a query — get routed LLM response with full metadata |
| `/stats` | GET | Live metrics: cache hit rate, budget status, model distribution, latency |
| `/predict` | GET | Estimate cost and model before making the actual call |
| `/compare` | GET | Cost comparison across all models for a given query |
| `/history` | GET | Request log, filterable by `user_id` |
| `/export/csv` | GET | Download full request history as CSV |
| `/train` | POST | Train Random Forest router on accumulated request logs |
| `/budget/configure` | POST | Update daily/hourly spend limits at runtime |
| `/cache` | DELETE | Clear both exact and semantic caches |
| `/health` | GET | Liveness probe (used by Render) |

### Example Request

```bash
curl -X POST https://YOUR-RENDER-URL.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain transformer architecture in deep learning", "user_id": "user_1"}'
```

### Example Response

```json
{
  "response": "Transformers use self-attention mechanisms...",
  "model": "gemini-2.5-flash",
  "cost_usd": 0.0000387,
  "cache_hit": false,
  "cache_type": "none",
  "complexity_score": 0.44,
  "complexity_factors": {
    "length": 0.07,
    "keywords": 0.15,
    "technical": 0.24,
    "code": 0.0,
    "questions": 0.0,
    "sentence": 0.23
  },
  "tokens": {"input": 12, "output": 126},
  "latency_ms": 541.34,
  "routing_reason": "Heuristic routing (complexity: 0.44)"
}
```

---

## Running Tests

```bash
# 37 unit + integration tests across 5 modules
python -m pytest tests/ -v

# 44 logic checks — no running server needed
python test_endpoints.py
```

Tests cover: complexity analyzer, exact cache (LRU + TTL), semantic cache, budget enforcer, sliding window rate limiter, full router pipeline (mock mode).

---

## Project Structure

```
llm-cost-firewall/
├── app/
│   ├── main.py             # FastAPI app — all 10 endpoints
│   ├── router.py           # 6-layer pipeline orchestrator
│   ├── analyzer.py         # Complexity scorer (6 weighted signals)
│   ├── cache.py            # Exact match cache (LRU eviction + TTL)
│   ├── semantic_cache.py   # Embedding similarity cache
│   ├── budget.py           # Spend tracking + HTTP 402 enforcement
│   ├── rate_limiter.py     # Sliding window per-user limiter
│   ├── ml_router.py        # Random Forest routing model (12 features)
│   ├── analytics.py        # pandas-based stats aggregation
│   ├── logger.py           # CSV request logger
│   └── config.py           # All settings via environment variables
├── tests/                  # 37 unit + integration tests
│   ├── test_analyzer.py
│   ├── test_cache.py
│   ├── test_budget.py
│   ├── test_rate_limiter.py
│   └── test_router.py
├── frontend/
│   └── dashboard/
│       └── index.html      # Plain HTML dashboard — no build step needed
├── docs/
│   └── index.html          # GitHub Pages live dashboard
├── .github/
│   └── workflows/
│       └── test.yml        # GitHub Actions CI — runs on every push
├── render.yaml             # Render deployment config
├── requirements-render.txt # Lightweight deploy requirements (no torch/cuda)
├── requirements.txt        # Full local dev requirements
├── runtime.txt             # Python 3.12.3 for Render
└── .env.example            # Environment variable template
```

---

## Deployment

Deployed free on [Render](https://render.com) (Oregon region).

```bash
# After forking, set these environment variables in Render dashboard:
GEMINI_API_KEY=your-key
MOCK_MODE=false
DAILY_BUDGET_USD=2.0
HOURLY_BUDGET_USD=0.50
RATE_LIMIT_PER_HOUR=100
```

Build command: `pip install -r requirements-render.txt`  
Start command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`

> **Note:** `requirements-render.txt` excludes `sentence-transformers` (pulls PyTorch + CUDA = 2GB, exceeds free tier 512MB RAM). Semantic cache runs in exact-match-only mode on the deployed version.

---

## Production Lessons Learned

- **Semantic cache threshold matters.** 0.85 returns wrong cached responses for similar-but-different queries. 0.92 is the safe production value.
- **`google-genai` ≠ `google-generativeai`.** Completely different SDKs, different model names. `gemini-1.5-flash` 404s — use `gemini-2.5-flash`.
- **Render free tier has 512MB RAM.** `sentence-transformers` pulls PyTorch + all CUDA drivers = 2GB+. Always maintain a separate deploy requirements file.
- **Python version pinning is critical.** Render defaulted to Python 3.14 which had no pre-built wheels for `scikit-learn`, `numpy`, or `pydantic-core`. Fixed by pinning `3.12.3` in `runtime.txt` and using `--only-binary=:all:` flag.
- **Render Singapore blocks Gemini API.** Google restricts API access by server IP region. Oregon works. Singapore doesn't (as of May 2026).
- **ML routing needs data first.** Random Forest is meaningless with <50 samples. Heuristic wins early — build the fallback before the model.

---

## Author

**Prisha Singla** — AI Engineer  
[GitHub](https://github.com/prisha-singla-dev) · [LinkedIn](https://linkedin.com/in/prisha-singla)

---

*Built to solve real production LLM cost problems. If this helped you, star the repo ⭐*