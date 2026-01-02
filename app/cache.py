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
    
    def _generate_key(self, query: str, model: str) -> str:
        """Generate cache key"""
        content = f"{query}:{model}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(self, query: str, model: str) -> Optional[Dict[str, Any]]:
        """Get cached response"""
        key = self._generate_key(query, model)
        
        if key in self.cache:
            cached_data = self.cache[key]
            # Check if expired
            if time.time() - cached_data["timestamp"] < self.ttl:
                return cached_data["response"]
            else:
                # Expired, remove it
                del self.cache[key]
        
        return None
    
    def set(self, query: str, model: str, response: Dict[str, Any]):
        """Cache response"""
        key = self._generate_key(query, model)
        self.cache[key] = {
            "response": response,
            "timestamp": time.time()
        }
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            "total_cached": len(self.cache),
            "ttl_seconds": self.ttl
        }
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()


# Global cache instance
cache = SimpleCache()