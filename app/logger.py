"""
Simple CSV logger for tracking all requests
"""
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

class RequestLogger:
    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / "requests.csv"
        
        # Create CSV with headers if doesn't exist
        if not self.log_file.exists():
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "query_length", "model", "complexity_score",
                    "cost_usd", "latency_ms", "cache_hit", "input_tokens", "output_tokens"
                ])
    
    def log(self, query: str, result: Dict[str, Any]):
        """Log a request to CSV"""
        try:
            with open(self.log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.utcnow().isoformat(),
                    len(query),
                    result.get("model", "unknown"),
                    result.get("complexity_score", 0),
                    result.get("cost_usd", 0),
                    result.get("latency_ms", 0),
                    result.get("cache_hit", False),
                    result.get("tokens", {}).get("input", 0),
                    result.get("tokens", {}).get("output", 0)
                ])
        except Exception as e:
            print(f"Logging error: {e}")

# Global logger
request_logger = RequestLogger()