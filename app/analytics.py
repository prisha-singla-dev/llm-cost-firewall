"""
Advanced request logger with analytics
"""
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List


class Analytics:
    """Track and analyze all requests"""
    
    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # CSV log file
        self.csv_file = self.log_dir / "requests.csv"
        self._init_csv()
        
        # In-memory storage for fast queries
        self.recent_requests = []  # Last 100 requests
    
    def _init_csv(self):
        """Initialize CSV with headers"""
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "query", "model", "complexity_score",
                    "cost_usd", "latency_ms", "cache_hit", "cache_type",
                    "input_tokens", "output_tokens", "user_id"
                ])
    
    def log_request(self, query: str, result: Dict[str, Any], user_id: str = "default"):
        """Log a request"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": query[:200],  # Truncate long queries
            "model": result.get("model", "unknown"),
            "complexity_score": result.get("complexity_score", 0),
            "cost_usd": result.get("cost_usd", 0),
            "latency_ms": result.get("latency_ms", 0),
            "cache_hit": result.get("cache_hit", False),
            "cache_type": result.get("cache_type", "none"),
            "input_tokens": result.get("tokens", {}).get("input", 0),
            "output_tokens": result.get("tokens", {}).get("output", 0),
            "user_id": user_id
        }
        
        # Write to CSV
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                log_entry["timestamp"],
                log_entry["query"],
                log_entry["model"],
                log_entry["complexity_score"],
                log_entry["cost_usd"],
                log_entry["latency_ms"],
                log_entry["cache_hit"],
                log_entry["cache_type"],
                log_entry["input_tokens"],
                log_entry["output_tokens"],
                log_entry["user_id"]
            ])
        
        # Add to in-memory
        self.recent_requests.append(log_entry)
        if len(self.recent_requests) > 100:
            self.recent_requests.pop(0)
    
    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent requests"""
        return self.recent_requests[-limit:]
    
    def get_analytics(self) -> Dict[str, Any]:
        """Calculate analytics from CSV"""
        if not self.csv_file.exists():
            return {"error": "No data yet"}
        
        # Read CSV
        with open(self.csv_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            return {"error": "No data yet"}
        
        # Calculate metrics
        total_requests = len(rows)
        total_cost = sum(float(r["cost_usd"]) for r in rows)
        cache_hits = sum(1 for r in rows if r["cache_hit"] == "True")
        
        # Model distribution
        model_counts = defaultdict(int)
        for r in rows:
            model_counts[r["model"]] += 1
        
        # Cache type distribution
        cache_types = defaultdict(int)
        for r in rows:
            if r["cache_hit"] == "True":
                cache_types[r.get("cache_type", "exact")] += 1
        
        # Cost by model
        cost_by_model = defaultdict(float)
        for r in rows:
            cost_by_model[r["model"]] += float(r["cost_usd"])
        
        # Average latency
        avg_latency = sum(float(r["latency_ms"]) for r in rows) / total_requests
        
        return {
            "total_requests": total_requests,
            "total_cost_usd": round(total_cost, 4),
            "cache_hit_rate": round(cache_hits / total_requests * 100, 1) if total_requests > 0 else 0,
            "cache_types": dict(cache_types),
            "model_distribution": dict(model_counts),
            "cost_by_model": {k: round(v, 4) for k, v in cost_by_model.items()},
            "avg_latency_ms": round(avg_latency, 2),
            "cost_without_cache": round(total_cost / (1 - cache_hits/total_requests if cache_hits < total_requests else 0.5), 4) if cache_hits > 0 else total_cost,
            "estimated_savings_usd": round(total_cost * (cache_hits / total_requests), 4) if total_requests > 0 else 0
        }
    
    def export_csv(self) -> str:
        """Get path to CSV file for download"""
        return str(self.csv_file)


# Global analytics instance
analytics = Analytics()