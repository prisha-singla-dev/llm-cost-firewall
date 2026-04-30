# """
# Advanced request logger with analytics
# """
# import csv
# import json
# from datetime import datetime, timedelta
# from pathlib import Path
# from collections import defaultdict
# from typing import Dict, Any, List


# class Analytics:
#     """Track and analyze all requests"""
    
#     def __init__(self):
#         self.log_dir = Path("logs")
#         self.log_dir.mkdir(exist_ok=True)
        
#         # CSV log file
#         self.csv_file = self.log_dir / "requests.csv"
#         self._init_csv()
        
#         # In-memory storage for fast queries
#         self.recent_requests = []  # Last 100 requests
    
#     def _init_csv(self):
#         """Initialize CSV with headers"""
#         if not self.csv_file.exists():
#             with open(self.csv_file, 'w', newline='') as f:
#                 writer = csv.writer(f)
#                 writer.writerow([
#                     "timestamp", "query", "model", "complexity_score",
#                     "cost_usd", "latency_ms", "cache_hit", "cache_type",
#                     "input_tokens", "output_tokens", "user_id"
#                 ])
    
#     def log_request(self, query: str, result: Dict[str, Any], user_id: str = "default"):
#         """Log a request"""
#         log_entry = {
#             "timestamp": datetime.utcnow().isoformat(),
#             "query": query[:200],  # Truncate long queries
#             "model": result.get("model", "unknown"),
#             "complexity_score": result.get("complexity_score", 0),
#             "cost_usd": result.get("cost_usd", 0),
#             "latency_ms": result.get("latency_ms", 0),
#             "cache_hit": result.get("cache_hit", False),
#             "cache_type": result.get("cache_type", "none"),
#             "input_tokens": result.get("tokens", {}).get("input", 0),
#             "output_tokens": result.get("tokens", {}).get("output", 0),
#             "user_id": user_id
#         }
        
#         # Write to CSV
#         with open(self.csv_file, 'a', newline='') as f:
#             writer = csv.writer(f)
#             writer.writerow([
#                 log_entry["timestamp"],
#                 log_entry["query"],
#                 log_entry["model"],
#                 log_entry["complexity_score"],
#                 log_entry["cost_usd"],
#                 log_entry["latency_ms"],
#                 log_entry["cache_hit"],
#                 log_entry["cache_type"],
#                 log_entry["input_tokens"],
#                 log_entry["output_tokens"],
#                 log_entry["user_id"]
#             ])
        
#         # Add to in-memory
#         self.recent_requests.append(log_entry)
#         if len(self.recent_requests) > 100:
#             self.recent_requests.pop(0)
    
#     def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
#         """Get recent requests"""
#         return self.recent_requests[-limit:]
    
#     def get_analytics(self) -> Dict[str, Any]:
#         """Calculate analytics from CSV"""
#         if not self.csv_file.exists():
#             return {"error": "No data yet"}
        
#         # Read CSV
#         with open(self.csv_file, 'r') as f:
#             reader = csv.DictReader(f)
#             rows = list(reader)
        
#         if not rows:
#             return {"error": "No data yet"}
        
#         # Calculate metrics
#         total_requests = len(rows)
#         total_cost = sum(float(r["cost_usd"]) for r in rows)
#         cache_hits = sum(1 for r in rows if r["cache_hit"] == "True")
        
#         # Model distribution
#         model_counts = defaultdict(int)
#         for r in rows:
#             model_counts[r["model"]] += 1
        
#         # Cache type distribution
#         cache_types = defaultdict(int)
#         for r in rows:
#             if r["cache_hit"] == "True":
#                 cache_types[r.get("cache_type", "exact")] += 1
        
#         # Cost by model
#         cost_by_model = defaultdict(float)
#         for r in rows:
#             cost_by_model[r["model"]] += float(r["cost_usd"])
        
#         # Average latency
#         avg_latency = sum(float(r["latency_ms"]) for r in rows) / total_requests
        
#         return {
#             "total_requests": total_requests,
#             "total_cost_usd": round(total_cost, 4),
#             "cache_hit_rate": round(cache_hits / total_requests * 100, 1) if total_requests > 0 else 0,
#             "cache_types": dict(cache_types),
#             "model_distribution": dict(model_counts),
#             "cost_by_model": {k: round(v, 4) for k, v in cost_by_model.items()},
#             "avg_latency_ms": round(avg_latency, 2),
#             "cost_without_cache": round(total_cost / (1 - cache_hits/total_requests if cache_hits < total_requests else 0.5), 4) if cache_hits > 0 else total_cost,
#             "estimated_savings_usd": round(total_cost * (cache_hits / total_requests), 4) if total_requests > 0 else 0
#         }
    
#     def export_csv(self) -> str:
#         """Get path to CSV file for download"""
#         return str(self.csv_file)


# # Global analytics instance
# analytics = Analytics()

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