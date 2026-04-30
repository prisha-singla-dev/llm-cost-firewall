"""
rate_limiter.py - Per-User Rate Limiting  [UPGRADED]

Your existing code had basic hourly rate limiting.
This upgrades it to a SLIDING WINDOW algorithm.

WHY SLIDING WINDOW > FIXED WINDOW:
  Fixed window problem: if limit = 100/hour, a user can send
  100 at 12:59 and 100 more at 13:01 → 200 requests in 2 minutes. Bug!

  Sliding window: we track exact timestamps of the last N requests.
  The window "slides" with time → always accurate.

HOW IT WORKS:
  Each user has a deque (double-ended queue) of request timestamps.
  On each request:
    1. Remove timestamps older than the window (60 min)
    2. Check if remaining count ≥ limit → if so, BLOCK
    3. Otherwise, append current timestamp → ALLOW

  Memory: each entry is just a float64 (8 bytes). 100 entries = 800 bytes/user.
"""

import time
from collections import defaultdict, deque
from typing import Dict
from app.config import RATE_LIMIT_PER_HOUR


class RateLimiter:
    def __init__(self, requests_per_hour: int = RATE_LIMIT_PER_HOUR):
        self.limit = requests_per_hour
        # user_id → deque of Unix timestamps (float)
        self._windows: Dict[str, deque] = defaultdict(deque)
        # Stats
        self.total_allowed = 0
        self.total_blocked = 0

    def _clean_window(self, window: deque, cutoff: float):
        """Remove timestamps older than cutoff from the left of the deque."""
        while window and window[0] < cutoff:
            window.popleft()

    def check(self, user_id: str) -> Dict:
        """
        Returns {"allowed": True/False, ...metadata}
        Call this before processing any request.
        """
        now     = time.time()
        cutoff  = now - 3600  # 1 hour ago
        window  = self._windows[user_id]

        self._clean_window(window, cutoff)
        current_count = len(window)

        if current_count >= self.limit:
            self.total_blocked += 1
            # How long until the oldest request falls out of the window?
            oldest     = window[0]
            retry_secs = int(oldest + 3600 - now) + 1
            return {
                "allowed":      False,
                "current":      current_count,
                "limit":        self.limit,
                "retry_after":  retry_secs,
                "reason":       "hourly_rate_limit",
            }

        # Allow: record this request
        window.append(now)
        self.total_allowed += 1
        return {
            "allowed":   True,
            "current":   current_count + 1,
            "limit":     self.limit,
            "remaining": self.limit - current_count - 1,
        }

    def stats(self) -> Dict:
        total = self.total_allowed + self.total_blocked
        return {
            "total_allowed":  self.total_allowed,
            "total_blocked":  self.total_blocked,
            "block_rate_pct": round(self.total_blocked / total * 100, 1) if total else 0,
            "limit_per_hour": self.limit,
            "active_users":   len(self._windows),
        }