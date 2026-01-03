"""
Simple in-memory cache (no Redis needed for MVP)
"""
import hashlib
import time
from typing import Optional, Dict, Any


class SimpleCache:
    """In-memory cache using Python dict"""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds
        print(f"[CACHE] Initialized with TTL={ttl_seconds}s")
    
    def _generate_key(self, query: str, model: str) -> str:
        """Generate cache key - NORMALIZED"""
        # Normalize: lowercase + strip whitespace
        normalized_query = query.lower().strip()
        content = f"{normalized_query}:{model}"
        key = hashlib.sha256(content.encode()).hexdigest()[:16]  # Shorter hash for readability
        return key
    
    def get(self, query: str, model: str) -> Optional[Dict[str, Any]]:
        """Get cached response"""
        key = self._generate_key(query, model)
        
        print(f"[CACHE] GET attempt - Key: {key}, Query: '{query[:50]}...'")
        
        if key in self.cache:
            cached_data = self.cache[key]
            age = time.time() - cached_data["timestamp"]
            
            # Check if expired
            if age < self.ttl:
                print(f"[CACHE] HIT! Age: {age:.1f}s")
                return cached_data["response"]
            else:
                # Expired, remove it
                print(f"[CACHE] EXPIRED (age: {age:.1f}s > {self.ttl}s)")
                del self.cache[key]
        else:
            print(f"[CACHE] MISS - Key not found. Total cached: {len(self.cache)}")
        
        return None
    
    def set(self, query: str, model: str, response: Dict[str, Any]):
        """Cache response"""
        key = self._generate_key(query, model)
        
        self.cache[key] = {
            "response": response,
            "timestamp": time.time(),
            "query_preview": query[:50]  # For debugging
        }
        
        print(f"[CACHE] ✅ SET - Key: {key}, Total cached: {len(self.cache)}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        # Clean expired entries
        current_time = time.time()
        expired_keys = [
            k for k, v in self.cache.items() 
            if current_time - v["timestamp"] >= self.ttl
        ]
        
        for k in expired_keys:
            del self.cache[k]
        
        return {
            "total_cached": len(self.cache),
            "ttl_seconds": self.ttl
        }
    
    def clear(self):
        """Clear all cache"""
        count = len(self.cache)
        self.cache.clear()
        print(f"[CACHE] Cleared {count} entries")
    
    def debug_print(self):
        """Print all cached keys for debugging"""
        print(f"\n[CACHE DEBUG] Total entries: {len(self.cache)}")
        for key, data in list(self.cache.items())[:5]:  # Show first 5
            age = time.time() - data["timestamp"]
            print(f"  Key: {key}, Query: {data['query_preview']}, Age: {age:.1f}s")


# Global cache instance
cache = SimpleCache()