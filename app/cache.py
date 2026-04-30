# """
# Simple in-memory cache (no Redis needed for MVP)
# """
# import hashlib
# import time
# from typing import Optional, Dict, Any


# class SimpleCache:
#     """In-memory cache using Python dict"""
    
#     def __init__(self, ttl_seconds: int = 3600):
#         self.cache: Dict[str, Dict[str, Any]] = {}
#         self.ttl = ttl_seconds
#         print(f"[CACHE] Initialized with TTL={ttl_seconds}s")
    
#     def _generate_key(self, query: str, model: str) -> str:
#         """Generate cache key - NORMALIZED"""
#         # Normalize: lowercase + strip whitespace
#         normalized_query = query.lower().strip()
#         content = f"{normalized_query}:{model}"
#         key = hashlib.sha256(content.encode()).hexdigest()[:16]
#         return key
    
#     def get(self, query: str, model: str) -> Optional[Dict[str, Any]]:
#         """Get cached response"""
#         key = self._generate_key(query, model)
        
#         print(f"[CACHE] GET attempt - Key: {key}, Query: '{query[:50]}...'")
        
#         if key in self.cache:
#             cached_data = self.cache[key]
#             age = time.time() - cached_data["timestamp"]
            
#             # Check if expired
#             if age < self.ttl:
#                 print(f"[CACHE] HIT! Age: {age:.1f}s")
#                 return cached_data["response"]
#             else:
#                 # Expired, remove it
#                 print(f"[CACHE] EXPIRED (age: {age:.1f}s > {self.ttl}s)")
#                 del self.cache[key]
#         else:
#             print(f"[CACHE] MISS - Key not found. Total cached: {len(self.cache)}")
        
#         return None
    
#     def set(self, query: str, model: str, response: Dict[str, Any]):
#         """Cache response"""
#         key = self._generate_key(query, model)
        
#         self.cache[key] = {
#             "response": response,
#             "timestamp": time.time(),
#             "query_preview": query[:50]  # For debugging
#         }
        
#         print(f"[CACHE] SET - Key: {key}, Total cached: {len(self.cache)}")
    
#     def get_stats(self) -> Dict[str, int]:
#         """Get cache statistics"""
#         # Clean expired entries
#         current_time = time.time()
#         expired_keys = [
#             k for k, v in self.cache.items() 
#             if current_time - v["timestamp"] >= self.ttl
#         ]
        
#         for k in expired_keys:
#             del self.cache[k]
        
#         return {
#             "total_cached": len(self.cache),
#             "ttl_seconds": self.ttl
#         }
    
#     def clear(self):
#         """Clear all cache"""
#         count = len(self.cache)
#         self.cache.clear()
#         print(f"[CACHE] Cleared {count} entries")
    
#     def debug_print(self):
#         """Print all cached keys for debugging"""
#         print(f"\n[CACHE DEBUG] Total entries: {len(self.cache)}")
#         for key, data in list(self.cache.items())[:5]:  # Show first 5
#             age = time.time() - data["timestamp"]
#             print(f"  Key: {key}, Query: {data['query_preview']}, Age: {age:.1f}s")


# # Global cache instance
# cache = SimpleCache()

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