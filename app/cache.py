"""
cache.py - Exact Match Cache (Layer 1)

HOW IT WORKS:
  Every (query, model) pair is hashed with SHA-256.
  If the same exact query+model was seen before → return stored response.
  
  Uses Python's OrderedDict for LRU eviction:
  - When cache is full, the OLDEST entry is dropped (Least Recently Used)
  - Accessed entries are moved to the "end" (most recent position)

WHY SHA-256 for keys:
  - Normalizes whitespace differences
  - Constant-size key regardless of query length
  - Collision probability: astronomically low

TTL (Time-To-Live):
  Entries expire after CACHE_TTL_SECONDS (default 1 hour).
  Why? LLM responses to factual questions can become stale.
"""

import hashlib
import time
from collections import OrderedDict
from typing import Optional, Dict, Any
from app.config import CACHE_TTL_SECONDS, CACHE_MAX_SIZE


class ExactCache:
    def __init__(self, ttl: int = CACHE_TTL_SECONDS, max_size: int = CACHE_MAX_SIZE):
        self.ttl      = ttl
        self.max_size = max_size
        # OrderedDict preserves insertion order → enables LRU eviction
        self._store: OrderedDict = OrderedDict()
        # Stats counters
        self.hits   = 0
        self.misses = 0

    def _make_key(self, query: str, model: str) -> str:
        """SHA-256 of lowercased+stripped query + model name"""
        normalized = f"{query.strip().lower()}|{model}"
        return hashlib.sha256(normalized.encode()).hexdigest()

    def _is_expired(self, entry: Dict) -> bool:
        return (time.time() - entry["stored_at"]) > self.ttl

    def get(self, query: str, model: str) -> Optional[Dict]:
        """Return cached entry or None. Moves hit to end (LRU)."""
        key   = self._make_key(query, model)
        entry = self._store.get(key)

        if entry is None:
            self.misses += 1
            return None

        if self._is_expired(entry):
            del self._store[key]
            self.misses += 1
            return None

        # Cache hit! Move to end (most recently used)
        self._store.move_to_end(key)
        self.hits += 1
        return entry

    def set(self, query: str, model: str, response: str, cost: float = 0.0):
        """Store an entry. Evicts oldest if at capacity."""
        key = self._make_key(query, model)

        if len(self._store) >= self.max_size:
            # Pop the FIRST item = least recently used
            self._store.popitem(last=False)

        self._store[key] = {
            "response":  response,
            "model":     model,
            "cost":      cost,
            "stored_at": time.time(),
        }

    def clear(self):
        self._store.clear()

    def stats(self) -> Dict:
        total    = self.hits + self.misses
        hit_rate = round(self.hits / total * 100, 1) if total > 0 else 0.0
        return {
            "size":          len(self._store),
            "max_size":      self.max_size,
            "hits":          self.hits,
            "misses":        self.misses,
            "hit_rate_pct":  hit_rate,
            "ttl_seconds":   self.ttl,
        }