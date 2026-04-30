# """
# Simple CSV logger for tracking all requests
# FIXED: Now logs actual query text for ML training
# """
# import csv
# from datetime import datetime
# from pathlib import Path
# from typing import Dict, Any

# class RequestLogger:
#     def __init__(self):
#         self.log_dir = Path("logs")
#         self.log_dir.mkdir(exist_ok=True)
#         self.log_file = self.log_dir / "requests.csv"
        
#         # Create CSV with headers if doesn't exist
#         if not self.log_file.exists():
#             with open(self.log_file, 'w', newline='') as f:
#                 writer = csv.writer(f)
#                 writer.writerow([
#                     "timestamp", "query", "model", "complexity_score",  
#                     "cost_usd", "latency_ms", "cache_hit", "input_tokens", "output_tokens"
#                 ])
    
#     def log(self, query: str, result: Dict[str, Any]):
#         """Log a request to CSV"""
#         try:
#             with open(self.log_file, 'a', newline='') as f:
#                 writer = csv.writer(f)
#                 writer.writerow([
#                     datetime.utcnow().isoformat(),
#                     query[:200],  
#                     result.get("model", "unknown"),
#                     result.get("complexity_score", 0),
#                     result.get("cost_usd", 0),
#                     result.get("latency_ms", 0),
#                     result.get("cache_hit", False),
#                     result.get("tokens", {}).get("input", 0),
#                     result.get("tokens", {}).get("output", 0)
#                 ])
#         except Exception as e:
#             print(f"Logging error: {e}")

# # Global logger
# request_logger = RequestLogger()

"""
logger.py - CSV Request Logger  [UPGRADED]

Every single request is logged to a CSV file.
This serves two purposes:
  1. Analytics (who used what model, how much did it cost, was it cached)
  2. ML Training data (ml_router.py reads this to train the Random Forest)

CSV FORMAT:
  timestamp, user_id, query_preview, model_used, complexity_score,
  tokens_in, tokens_out, cost_usd, cache_hit, cache_type, latency_ms

WHY CSV NOT A DATABASE:
  - Zero dependencies (no Postgres, no SQLite setup)
  - Easy to open in Excel / pandas
  - Simple to parse for ML training
  - Adequate for <100K rows
  For production scale, swap with SQLAlchemy + Postgres.
"""

import csv
import os
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict


class RequestLogger:
    HEADERS = [
        "timestamp", "user_id", "query_preview", "model_used",
        "complexity_score", "tokens_in", "tokens_out", "cost_usd",
        "cache_hit", "cache_type", "latency_ms",
    ]

    def __init__(self, log_file: str = "logs/requests.csv"):
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Write header if file is new/empty
        if not os.path.exists(log_file) or os.path.getsize(log_file) == 0:
            with open(log_file, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.HEADERS)
                writer.writeheader()

    def log(
        self,
        user_id:          str,
        query:            str,
        model_used:       str,
        complexity_score: float,
        tokens_in:        int,
        tokens_out:       int,
        cost_usd:         float,
        cache_hit:        bool,
        cache_type:       str,   # "none" | "exact" | "semantic"
        latency_ms:       float,
    ):
        row = {
            "timestamp":        datetime.now(timezone.utc).isoformat(),
            "user_id":          user_id,
            "query_preview":    query[:120].replace("\n", " "),
            "model_used":       model_used,
            "complexity_score": round(complexity_score, 4),
            "tokens_in":        tokens_in,
            "tokens_out":       tokens_out,
            "cost_usd":         round(cost_usd, 8),
            "cache_hit":        cache_hit,
            "cache_type":       cache_type,
            "latency_ms":       round(latency_ms, 2),
        }
        try:
            with open(self.log_file, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.HEADERS)
                writer.writerow(row)
        except Exception:
            pass  # never crash the app because of logging

    def read_all(self, limit: int = 200) -> List[Dict]:
        """Read the last `limit` rows from the CSV."""
        if not os.path.exists(self.log_file):
            return []
        try:
            with open(self.log_file, "r") as f:
                reader = list(csv.DictReader(f))
            return list(reversed(reader))[:limit]
        except Exception:
            return []

    def export_csv_string(self) -> str:
        """Return entire CSV as a string for the /export/csv endpoint."""
        try:
            with open(self.log_file, "r") as f:
                return f.read()
        except Exception:
            return ""