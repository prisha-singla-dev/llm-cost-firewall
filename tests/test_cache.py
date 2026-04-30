"""tests/test_cache.py — Tests for exact cache"""
import sys, time
sys.path.insert(0, ".")

from app.cache import ExactCache


class TestExactCache:

    def test_miss_on_empty(self):
        c = ExactCache()
        assert c.get("hello", "flash") is None

    def test_set_then_get(self):
        c = ExactCache()
        c.set("What is Python?", "flash", "Python is a language.", 0.001)
        result = c.get("What is Python?", "flash")
        assert result is not None
        assert result["response"] == "Python is a language."

    def test_different_model_is_miss(self):
        c = ExactCache()
        c.set("What is Python?", "flash", "Python is a language.", 0.001)
        result = c.get("What is Python?", "pro")  # different model
        assert result is None

    def test_ttl_expiry(self):
        c = ExactCache(ttl=0)  # 0 second TTL → expires immediately
        c.set("test", "flash", "response", 0.0)
        time.sleep(0.01)
        assert c.get("test", "flash") is None, "Entry should have expired"

    def test_hit_rate_tracking(self):
        c = ExactCache()
        c.set("q1", "flash", "r1", 0.0)
        c.get("q1", "flash")    # hit
        c.get("q2", "flash")    # miss
        stats = c.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate_pct"] == 50.0

    def test_lru_eviction(self):
        c = ExactCache(max_size=3)
        c.set("q1", "flash", "r1", 0.0)
        c.set("q2", "flash", "r2", 0.0)
        c.set("q3", "flash", "r3", 0.0)
        c.set("q4", "flash", "r4", 0.0)  # should evict q1
        assert c.get("q1", "flash") is None, "q1 should have been evicted (LRU)"
        assert c.get("q4", "flash") is not None, "q4 should still be cached"

    def test_clear(self):
        c = ExactCache()
        c.set("q1", "flash", "r1", 0.0)
        c.clear()
        assert c.get("q1", "flash") is None
        assert c.stats()["size"] == 0