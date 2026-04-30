"""tests/test_budget.py — Tests for budget enforcement"""
import sys
sys.path.insert(0, ".")
import pytest
from app.budget import BudgetEnforcer, BudgetExceededError


class TestBudgetEnforcer:

    def test_no_block_when_under_limit(self):
        b = BudgetEnforcer(daily_limit=10.0, hourly_limit=2.0)
        b.check_budget()  # should not raise

    def test_blocks_when_daily_exceeded(self):
        b = BudgetEnforcer(daily_limit=0.001, hourly_limit=100.0)
        b.record_cost(0.002)  # exceed daily
        with pytest.raises(BudgetExceededError) as exc_info:
            b.check_budget()
        assert "Daily" in exc_info.value.message

    def test_blocks_when_hourly_exceeded(self):
        b = BudgetEnforcer(daily_limit=100.0, hourly_limit=0.001)
        b.record_cost(0.002)  # exceed hourly
        with pytest.raises(BudgetExceededError) as exc_info:
            b.check_budget()
        assert "Hourly" in exc_info.value.message

    def test_cost_accumulates(self):
        b = BudgetEnforcer(daily_limit=100.0, hourly_limit=100.0)
        b.record_cost(0.01)
        b.record_cost(0.02)
        b.record_cost(0.03)
        status = b.status()
        assert abs(status["total_cost_usd"] - 0.06) < 1e-9

    def test_update_limits_runtime(self):
        b = BudgetEnforcer(daily_limit=10.0, hourly_limit=2.0)
        b.update_limits(daily=0.001)    # tighten daily
        b.record_cost(0.002)
        with pytest.raises(BudgetExceededError):
            b.check_budget()

    def test_status_has_all_fields(self):
        b = BudgetEnforcer(daily_limit=5.0, hourly_limit=1.0)
        b.record_cost(0.5)
        s = b.status()
        for key in ["daily_spent_usd", "daily_limit_usd", "daily_remaining_usd",
                    "hourly_spent_usd", "total_cost_usd", "total_requests"]:
            assert key in s, f"Missing key: {key}"

    def test_remaining_never_negative(self):
        b = BudgetEnforcer(daily_limit=0.001, hourly_limit=100.0)
        b.record_cost(5.0)   # way over
        s = b.status()
        assert s["daily_remaining_usd"] >= 0