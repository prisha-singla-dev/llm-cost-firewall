"""
budget.py - Budget Enforcement  [NEW FILE - didn't exist before]

WHY THIS EXISTS:
  Without budget limits, a bug or attack can send thousands of API requests
  and rack up hundreds of dollars in minutes. This module hard-stops that.

HOW IT WORKS:
  We track spending in time-bucketed dicts:
    daily_spend["2025-04-29"]  = 3.42  (total $ spent today)
    hourly_spend["2025-04-29-14"] = 0.87 (total $ in this hour)

  On every request, check_budget() compares current spend vs limits.
  If exceeded → raise BudgetExceededError → FastAPI returns HTTP 402.

DESIGN CHOICE - in-memory vs database:
  In-memory is fine for single-instance deployments.
  For multi-instance (scaled), you'd replace with Redis or Postgres.
  We keep it simple but the interface makes it easy to swap later.
"""

from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, Optional
from app.config import DAILY_BUDGET_USD, HOURLY_BUDGET_USD


class BudgetExceededError(Exception):
    """Raised when a spending limit is hit. Caught in main.py → HTTP 402."""
    def __init__(self, message: str, spent: float, limit: float):
        self.message = message
        self.spent   = spent
        self.limit   = limit
        super().__init__(message)


class BudgetEnforcer:
    def __init__(
        self,
        daily_limit:  float = DAILY_BUDGET_USD,
        hourly_limit: float = HOURLY_BUDGET_USD,
    ):
        self.daily_limit  = daily_limit
        self.hourly_limit = hourly_limit

        # key = "YYYY-MM-DD", value = total USD spent that day
        self._daily:  Dict[str, float] = defaultdict(float)
        # key = "YYYY-MM-DD-HH", value = total USD spent that hour
        self._hourly: Dict[str, float] = defaultdict(float)

        # Cumulative totals for reporting
        self.total_cost     = 0.0
        self.total_requests = 0

    def _day_key(self)  -> str: return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    def _hour_key(self) -> str: return datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")

    def check_budget(self):
        """
        Call this BEFORE making an API request.
        Raises BudgetExceededError if any limit is hit.
        """
        day_spent  = self._daily[self._day_key()]
        hour_spent = self._hourly[self._hour_key()]

        if self.daily_limit and day_spent >= self.daily_limit:
            raise BudgetExceededError(
                f"Daily budget ${self.daily_limit:.2f} exceeded (spent ${day_spent:.4f})",
                spent=day_spent,
                limit=self.daily_limit,
            )

        if self.hourly_limit and hour_spent >= self.hourly_limit:
            raise BudgetExceededError(
                f"Hourly budget ${self.hourly_limit:.2f} exceeded (spent ${hour_spent:.4f})",
                spent=hour_spent,
                limit=self.hourly_limit,
            )

    def record_cost(self, cost_usd: float):
        """Call this AFTER a successful API request to record the cost."""
        self._daily[self._day_key()]   += cost_usd
        self._hourly[self._hour_key()] += cost_usd
        self.total_cost     += cost_usd
        self.total_requests += 1

    def update_limits(self, daily: Optional[float] = None, hourly: Optional[float] = None):
        """Update limits at runtime via /budget/configure endpoint."""
        if daily  is not None: self.daily_limit  = daily
        if hourly is not None: self.hourly_limit = hourly

    def status(self) -> Dict:
        day_spent  = self._daily[self._day_key()]
        hour_spent = self._hourly[self._hour_key()]
        return {
            "daily_spent_usd":    round(day_spent,  6),
            "daily_limit_usd":    self.daily_limit,
            "daily_remaining_usd": round(max(0, self.daily_limit - day_spent), 6),
            "daily_pct_used":     round(day_spent / self.daily_limit * 100, 1) if self.daily_limit else 0,
            "hourly_spent_usd":   round(hour_spent, 6),
            "hourly_limit_usd":   self.hourly_limit,
            "total_cost_usd":     round(self.total_cost, 6),
            "total_requests":     self.total_requests,
        }