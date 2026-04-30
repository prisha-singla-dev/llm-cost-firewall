"""tests/test_rate_limiter.py — Tests for sliding window rate limiter"""
import sys
sys.path.insert(0, ".")
from app.rate_limiter import RateLimiter


class TestRateLimiter:

    def test_allows_under_limit(self):
        lim = RateLimiter(requests_per_hour=5)
        result = lim.check("user1")
        assert result["allowed"] is True

    def test_blocks_at_limit(self):
        lim = RateLimiter(requests_per_hour=3)
        for _ in range(3):
            lim.check("user1")
        result = lim.check("user1")  # 4th request
        assert result["allowed"] is False
        assert result["reason"] == "hourly_rate_limit"

    def test_retry_after_present_when_blocked(self):
        lim = RateLimiter(requests_per_hour=1)
        lim.check("user1")
        result = lim.check("user1")
        assert "retry_after" in result
        assert result["retry_after"] > 0

    def test_different_users_independent(self):
        lim = RateLimiter(requests_per_hour=1)
        lim.check("user1")
        lim.check("user1")  # user1 now blocked
        result = lim.check("user2")  # user2 should be fine
        assert result["allowed"] is True

    def test_stats_track_blocked(self):
        lim = RateLimiter(requests_per_hour=2)
        lim.check("u"); lim.check("u"); lim.check("u")  # 3rd is blocked
        stats = lim.stats()
        assert stats["total_blocked"] >= 1
        assert stats["total_allowed"] == 2