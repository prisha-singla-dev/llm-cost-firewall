# 🔥 LLM Cost Firewall

[![Tests](https://github.com/prisha-singla-dev/llm-cost-firewall/actions/workflows/test.yml/badge.svg)](https://github.com/prisha-singla-dev/llm-cost-firewall/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![Deployed on Render](https://img.shields.io/badge/deployed-Render-purple.svg)](https://render.com)

An intelligent LLM proxy that cuts Gemini API costs by **60%** through smart routing, dual-layer semantic caching, budget enforcement, and rate limiting.

**Live API:** `https://your-service.onrender.com/docs`  
**Tech:** Python · FastAPI · Gemini API · scikit-learn · sentence-transformers · GitHub Actions

---

## The Problem

Every LLM-powered product treats all queries the same — a "what is Python?" hits the same expensive model as a 6-paragraph architecture analysis. This proxy fixes that.

## Architecture

```
Your App
    │
    ▼
┌─────────────────────────────────────────┐
│           LLM Cost Firewall             │
│                                         │
│  1. Rate Limiter  (sliding window)      │
│  2. Budget Enforcer  (HTTP 402 on hit)  │
│  3. Complexity Analyzer  (6 factors)    │
│  4. ML Router  (Random Forest)          │
│  5. Dual Cache  (exact + semantic)      │
│  6. Gemini API  (with retry backoff)    │
└─────────────────────────────────────────┘
    │
    ▼
Gemini API (gemini-2.5-flash / gemini-2.5-pro)
```

## Features

| Feature | How it works |
|---|---|
| **ML Routing** | Random Forest classifier trained on request logs. Routes simple queries to `gemini-2.5-flash` (cheap), complex to `gemini-2.5-pro`. Falls back to 6-factor heuristic until 50+ samples collected. |
| **Dual Semantic Cache** | Layer 1: SHA-256 exact hash match. Layer 2: `all-MiniLM-L6-v2` embeddings + cosine similarity > 0.85. Similar questions share cached answers. |
| **Budget Enforcement** | Hard daily + hourly spend limits. Returns HTTP 402 when exceeded. Configurable per user. |
| **Sliding Window Rate Limiter** | Per-user request deque. More accurate than fixed-window counters — no burst abuse at window boundaries. |
| **Exponential Backoff Retry** | 429 quota errors trigger automatic retry: wait 2s → 4s → 8s before failing cleanly. |
| **Cost Prediction** | `GET /predict` estimates cost before making the actual API call. |

## Quick Start

```bash
git clone https://github.com/prisha-singla-dev/llm-cost-firewall.git
cd llm-cost-firewall

python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: add GEMINI_API_KEY, set MOCK_MODE=false
```

Get a free Gemini API key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) — no credit card needed.

```bash
uvicorn app.main:app --reload
# API docs: http://localhost:8000/docs
# Dashboard: open frontend/dashboard/index.html in browser
```

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/chat` | POST | Send query, get routed LLM response |
| `/stats` | GET | Live metrics: cache, budget, routing, latency |
| `/predict` | GET | Estimate cost before making a call |
| `/compare` | GET | Cost comparison across all models |
| `/history` | GET | Request log (filterable by user_id) |
| `/export/csv` | GET | Download full request history |
| `/train` | POST | Train ML router on accumulated logs |
| `/budget/configure` | POST | Update spend limits at runtime |
| `/cache` | DELETE | Clear both caches |

### Example

```bash
curl -X POST https://your-service.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain transformers in deep learning", "user_id": "user_1"}'
```

```json
{
  "response": "Transformers are...",
  "model": "gemini-2.5-flash",
  "cost_usd": 0.0000387,
  "cache_hit": false,
  "complexity_score": 0.44,
  "latency_ms": 342.1,
  "routing_reason": "Heuristic routing (complexity: 0.44)"
}
```

## Running Tests

```bash
python -m pytest tests/ -v     # 37 tests across 5 modules
python test_endpoints.py       # 44 logic checks, no server needed
```

## Project Structure

```
llm-cost-firewall/
├── app/
│   ├── main.py           # FastAPI app, all endpoints
│   ├── router.py         # 6-layer pipeline orchestrator
│   ├── analyzer.py       # Complexity scorer (6 weighted signals)
│   ├── cache.py          # Exact match cache (LRU + TTL)
│   ├── semantic_cache.py # Embedding similarity cache
│   ├── budget.py         # Spend tracking + enforcement
│   ├── rate_limiter.py   # Sliding window per-user limiter
│   ├── ml_router.py      # Random Forest routing model
│   ├── analytics.py      # pandas-based stats aggregation
│   ├── logger.py         # CSV request logger
│   └── config.py         # All settings via env vars
├── tests/                # 37 unit + integration tests
├── frontend/dashboard/   # Plain HTML dashboard (no build step)
├── .github/workflows/    # GitHub Actions CI
├── render.yaml           # Render deployment config
└── requirements-render.txt  # Lightweight deploy requirements
```

## What I Learned Building This

- Semantic caching threshold matters — 0.85 has edge cases, 0.92 is safer for production
- The `google-genai` SDK is a complete rewrite of `google-generativeai`. Model names changed too (`gemini-2.5-flash` not `gemini-1.5-flash`)
- Render free tier has 512MB RAM — `sentence-transformers` + `torch` alone exceed that. Always maintain a separate deploy requirements file
- ML routing only makes sense after 50+ real requests. Heuristics win early

## Author

**Prisha Singla** — AI Engineer at Capgemini  
[GitHub](https://github.com/prisha-singla-dev)
[LinkedIn](https://linkedin.com/in/prisha-singla)