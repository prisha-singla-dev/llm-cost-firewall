"""
semantic_cache.py - Semantic Similarity Cache (Layer 2)

WHAT IS SEMANTIC CACHING?
  Normal cache: only hits if query is EXACTLY identical.
  Semantic cache: hits if query is SIMILAR ENOUGH in meaning.

  Example:
    Cached:  "What is machine learning?"
    New:     "Can you explain machine learning to me?"
    → Cosine similarity ≈ 0.94 → CACHE HIT (same answer, free!)

HOW IT WORKS:
  1. Convert query to a 384-dim embedding vector using sentence-transformers
     Model: all-MiniLM-L6-v2 (22MB, runs on CPU, fast)
  2. Compare new query against all cached embeddings using COSINE SIMILARITY
  3. If best match ≥ threshold (default 0.85) → return that cached response

COSINE SIMILARITY:
  Measures angle between two vectors in high-dimensional space.
  1.0 = identical direction (same meaning)
  0.0 = perpendicular (unrelated)
  -1.0 = opposite direction

  cos(θ) = (A · B) / (|A| × |B|)

WHY sentence-transformers vs OpenAI embeddings?
  - Free (runs locally, no API cost)
  - all-MiniLM-L6-v2 is fast (50ms per query on CPU)
  - Good enough for semantic matching (not for generation quality)

GRACEFUL FALLBACK:
  If sentence-transformers not installed → semantic cache is silently disabled.
  The system continues working with exact cache only.
"""

import time
import math
from typing import Optional, Dict, List, Any
from app.config import SEMANTIC_SIMILARITY_THRESHOLD, CACHE_TTL_SECONDS, CACHE_MAX_SIZE

# Try importing - graceful fallback if not installed
try:
    from sentence_transformers import SentenceTransformer
    _MODEL_AVAILABLE = True
except ImportError:
    _MODEL_AVAILABLE = False


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Pure Python cosine similarity (no numpy needed)"""
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class SemanticCache:
    def __init__(
        self,
        threshold: float = SEMANTIC_SIMILARITY_THRESHOLD,
        ttl: int = CACHE_TTL_SECONDS,
        max_size: int = CACHE_MAX_SIZE,
    ):
        self.threshold = threshold
        self.ttl       = ttl
        self.max_size  = max_size

        # List of {"embedding": [...], "response": "...", "stored_at": float, ...}
        self._entries: List[Dict] = []

        # Load embedding model once at startup
        self._model = None
        if _MODEL_AVAILABLE:
            try:
                # all-MiniLM-L6-v2: 22MB, 384 dimensions, ~50ms/query on CPU
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                self._model = None

        # Stats
        self.hits   = 0
        self.misses = 0

    @property
    def enabled(self) -> bool:
        return self._model is not None

    def _embed(self, text: str) -> Optional[List[float]]:
        """Convert text → embedding vector. Returns None on failure."""
        if self._model is None:
            return None
        try:
            vec = self._model.encode(text, normalize_embeddings=True)
            return vec.tolist()
        except Exception:
            return None

    def _clean_expired(self):
        """Remove entries older than TTL."""
        now = time.time()
        self._entries = [
            e for e in self._entries
            if (now - e["stored_at"]) <= self.ttl
        ]

    def get(self, query: str) -> Optional[Dict]:
        """
        Find the most similar cached entry.
        Returns entry dict if similarity ≥ threshold, else None.
        """
        if not self.enabled:
            self.misses += 1
            return None

        self._clean_expired()
        if not self._entries:
            self.misses += 1
            return None

        query_emb = self._embed(query)
        if query_emb is None:
            self.misses += 1
            return None

        # Linear scan — fast enough up to ~500 entries
        best_score = 0.0
        best_entry = None
        for entry in self._entries:
            score = _cosine_similarity(query_emb, entry["embedding"])
            if score > best_score:
                best_score = score
                best_entry = entry

        if best_entry and best_score >= self.threshold:
            self.hits += 1
            return {**best_entry, "similarity_score": round(best_score, 4)}

        self.misses += 1
        return None

    def set(self, query: str, response: str, model: str, cost: float = 0.0):
        """Store a new semantic cache entry."""
        if not self.enabled:
            return

        emb = self._embed(query)
        if emb is None:
            return

        # Evict oldest entry if at capacity
        if len(self._entries) >= self.max_size:
            self._entries.pop(0)

        self._entries.append({
            "embedding":  emb,
            "response":   response,
            "model":      model,
            "cost":       cost,
            "query":      query[:200],   # store preview for debugging
            "stored_at":  time.time(),
        })

    def clear(self):
        self._entries.clear()

    def stats(self) -> Dict:
        total    = self.hits + self.misses
        hit_rate = round(self.hits / total * 100, 1) if total > 0 else 0.0
        return {
            "enabled":         self.enabled,
            "size":            len(self._entries),
            "hits":            self.hits,
            "misses":          self.misses,
            "hit_rate_pct":    hit_rate,
            "threshold":       self.threshold,
            "ttl_seconds":     self.ttl,
        }