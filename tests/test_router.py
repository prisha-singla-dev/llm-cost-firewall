"""
tests/test_router.py — Integration tests for the full router pipeline
These test the whole flow end-to-end in mock mode.
"""
import sys, os
sys.path.insert(0, ".")
os.environ["MOCK_MODE"] = "true"

from app.router import LLMRouter
from app.budget import BudgetExceededError
import pytest


class TestLLMRouter:

    def setup_method(self):
        """Create fresh router for each test."""
        self.router = LLMRouter()

    def test_basic_response_returned(self):
        result = self.router.process("What is Python?", user_id="test_user")
        assert "response" in result
        assert len(result["response"]) > 0

    def test_response_has_all_metadata(self):
        result = self.router.process("Explain ML", user_id="test_user")
        for field in ["response", "model", "cost_usd", "cache_hit", "cache_type",
                      "complexity_score", "tokens", "latency_ms"]:
            assert field in result, f"Missing field: {field}"

    def test_simple_query_uses_flash(self):
        result = self.router.process("What is 2+2?", user_id="test")
        assert "flash" in result["model"].lower(), \
            f"Simple query should use flash, got {result['model']}"

    def test_second_identical_query_is_cache_hit(self):
        query = "What is Python programming language?"
        self.router.process(query, user_id="test")
        result2 = self.router.process(query, user_id="test")
        assert result2["cache_hit"] is True
        assert result2["cache_type"] == "exact"
        assert result2["cost_usd"] == 0.0

    def test_cache_hit_is_free(self):
        self.router.process("Tell me about AI", user_id="u1")
        result = self.router.process("Tell me about AI", user_id="u1")
        assert result["cost_usd"] == 0.0

    def test_budget_exceeded_raises(self):
        self.router.budget.update_limits(daily=0.000001)
        self.router.budget.record_cost(0.001)  # exceed budget
        with pytest.raises((BudgetExceededError, ValueError)):
            self.router.process("any query", user_id="test")

    def test_rate_limit_blocks_after_limit(self):
        # Set very low limit
        from app.rate_limiter import RateLimiter
        self.router.rate_limiter = RateLimiter(requests_per_hour=2)
        self.router.process("q1", user_id="heavy_user")
        self.router.process("q2", user_id="heavy_user")
        with pytest.raises(ValueError, match="Rate limit"):
            self.router.process("q3", user_id="heavy_user")

    def test_complexity_score_in_range(self):
        for query in ["Hi", "What is AI?", "Analyze architectural trade-offs in depth"]:
            result = self.router.process(query, user_id="test")
            assert 0.0 <= result["complexity_score"] <= 1.0

    def test_full_stats_has_all_sections(self):
        self.router.process("test query", user_id="test")
        stats = self.router.get_full_stats()
        for section in ["exact_cache", "semantic_cache", "budget", "rate_limiter"]:
            assert section in stats, f"Missing stats section: {section}"