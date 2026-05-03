"""
analytics.py - Real-Time Analytics  [UPGRADED from your existing file]

Reads logs/requests.csv and computes summary statistics.
Called by GET /stats and GET /analytics endpoints.

WHY PANDAS:
  You already have it in requirements.txt.
  It makes groupby, sum, mean trivial vs manual dict iteration.
  For this data size (< 100K rows) pandas is fast.
"""

import os
from typing import Dict, Any

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def compute_analytics(log_file: str = "logs/requests.csv") -> Dict[str, Any]:
    """
    Returns a dict with all stats for the /stats endpoint.
    Works even if pandas not installed (returns empty stats).
    """
    if not PANDAS_AVAILABLE or not os.path.exists(log_file):
        return _empty_stats()

    try:
        df = pd.read_csv(log_file)
        if df.empty:
            return _empty_stats()

        df["cost_usd"]    = pd.to_numeric(df["cost_usd"],    errors="coerce").fillna(0)
        df["latency_ms"]  = pd.to_numeric(df["latency_ms"],  errors="coerce").fillna(0)
        df["tokens_in"]   = pd.to_numeric(df["tokens_in"],   errors="coerce").fillna(0)
        df["tokens_out"]  = pd.to_numeric(df["tokens_out"],  errors="coerce").fillna(0)
        df["cache_hit"]   = df["cache_hit"].astype(str).str.lower() == "true"

        total_requests = len(df)
        total_cost     = float(df["cost_usd"].sum())
        cache_hits     = int(df["cache_hit"].sum())
        cache_hit_rate = round(cache_hits / total_requests * 100, 1) if total_requests else 0

        # Cost per model
        model_breakdown = (
            df.groupby("model_used")
            .agg(requests=("cost_usd", "count"), total_cost=("cost_usd", "sum"))
            .round(6)
            .to_dict("index")
        )

        # Cache type breakdown
        cache_breakdown = df["cache_type"].value_counts().to_dict()

        # Latency percentiles
        latency_p50 = float(df["latency_ms"].quantile(0.50))
        latency_p95 = float(df["latency_ms"].quantile(0.95))

        # Cost saved from cache hits
        avg_cost_non_cached = float(df[~df["cache_hit"]]["cost_usd"].mean()) if any(~df["cache_hit"]) else 0
        cost_saved = round(cache_hits * avg_cost_non_cached, 6)

        # Recent 10 requests
        recent = df.tail(10).to_dict("records")

        return {
            "total_requests":      total_requests,
            "total_cost_usd":      round(total_cost, 6),
            "avg_cost_per_req":    round(total_cost / max(total_requests, 1), 6),
            "cache_hits":          cache_hits,
            "cache_hit_rate_pct":  cache_hit_rate,
            "cost_saved_usd":      cost_saved,
            "model_breakdown":     model_breakdown,
            "cache_breakdown":     cache_breakdown,
            "latency_p50_ms":      round(latency_p50, 1),
            "latency_p95_ms":      round(latency_p95, 1),
            "recent_requests":     recent,
        }
    except Exception as e:
        return {**_empty_stats(), "error": str(e)}


def _empty_stats() -> Dict:
    return {
        "total_requests":     0,
        "total_cost_usd":     0.0,
        "avg_cost_per_req":   0.0,
        "cache_hits":         0,
        "cache_hit_rate_pct": 0.0,
        "cost_saved_usd":     0.0,
        "model_breakdown":    {},
        "cache_breakdown":    {},
        "latency_p50_ms":     0.0,
        "latency_p95_ms":     0.0,
        "recent_requests":    [],
    }