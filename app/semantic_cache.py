"""
Semantic Cache - Finds similar queries, not just exact matches
"""
import time
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Optional, Dict, Any, List, Tuple


class SemanticCache:
    """
    Advanced caching using semantic similarity
    
    Example:
    - Query 1: "What is machine learning?"
    - Query 2: "What's ML?"
    - Semantic cache recognizes these are similar → cache hit!
    """
    
    def __init__(self, similarity_threshold: float = 0.85, ttl_seconds: int = 3600):
        """
        Args:
            similarity_threshold: Minimum similarity (0-1) to consider a cache hit
            ttl_seconds: Time-to-live for cached entries
        """
        self.threshold = similarity_threshold
        self.ttl = ttl_seconds
        
        # Load embedding model (lightweight, fast)
        print("[SEMANTIC CACHE] Loading embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast, good quality
        print("[SEMANTIC CACHE] Model loaded ✓")
        
        # Storage: list of (embedding, query, response, timestamp, model)
        self.cache: List[Tuple[np.ndarray, str, Dict[str, Any], float, str]] = []
    
    def _embed_query(self, query: str) -> np.ndarray:
        """Convert query to embedding vector"""
        return self.model.encode([query])[0]
    
    def get(self, query: str, model: str) -> Optional[Dict[str, Any]]:
        """
        Find semantically similar cached query
        
        Returns cached response if:
        1. Similar query exists (cosine similarity > threshold)
        2. Same model was used
        3. Not expired
        """
        if not self.cache:
            print(f"[SEMANTIC CACHE] Empty cache")
            return None
        
        # Embed the query
        query_embedding = self._embed_query(query)
        
        # Check each cached entry
        best_match = None
        best_similarity = 0.0
        
        current_time = time.time()
        
        for cached_embedding, cached_query, cached_response, timestamp, cached_model in self.cache:
            # Skip if expired
            if current_time - timestamp >= self.ttl:
                continue
            
            # Skip if different model
            if cached_model != model:
                continue
            
            # Calculate similarity
            similarity = cosine_similarity(
                [query_embedding], 
                [cached_embedding]
            )[0][0]
            
            # Update best match if this is better
            if similarity > best_similarity and similarity >= self.threshold:
                best_similarity = similarity
                best_match = (cached_query, cached_response, similarity)
        
        if best_match:
            cached_query, response, similarity = best_match
            print(f"[SEMANTIC CACHE] HIT! Similarity: {similarity:.3f}")
            print(f"  Original: '{cached_query[:50]}...'")
            print(f"  Current:  '{query[:50]}...'")
            
            # Add metadata about cache hit
            response_copy = response.copy()
            response_copy["semantic_cache_hit"] = True
            response_copy["similarity_score"] = round(float(similarity), 3)
            response_copy["matched_query"] = cached_query[:100]
            
            return response_copy
        else:
            print(f"[SEMANTIC CACHE] MISS (best similarity: {best_similarity:.3f})")
            return None
    
    def set(self, query: str, model: str, response: Dict[str, Any]):
        """Cache a query response with its embedding"""
        embedding = self._embed_query(query)
        timestamp = time.time()
        
        self.cache.append((embedding, query, response, timestamp, model))
        print(f"[SEMANTIC CACHE] Cached query (total: {len(self.cache)})")
        
        # Cleanup old entries (keep cache manageable)
        if len(self.cache) > 1000:
            self._cleanup()
    
    def _cleanup(self):
        """Remove expired entries"""
        current_time = time.time()
        self.cache = [
            entry for entry in self.cache
            if current_time - entry[3] < self.ttl
        ]
        print(f"[SEMANTIC CACHE] Cleaned up, {len(self.cache)} entries remain")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = time.time()
        active_entries = sum(
            1 for entry in self.cache 
            if current_time - entry[3] < self.ttl
        )
        
        return {
            "total_cached": len(self.cache),
            "active_entries": active_entries,
            "similarity_threshold": self.threshold,
            "ttl_seconds": self.ttl
        }
    
    def clear(self):
        """Clear all cached entries"""
        count = len(self.cache)
        self.cache.clear()
        print(f"[SEMANTIC CACHE] Cleared {count} entries")


# Global semantic cache instance
semantic_cache = SemanticCache(similarity_threshold=0.85)