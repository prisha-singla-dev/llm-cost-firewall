# """
# Query complexity analyzer
# """

# class QueryAnalyzer:
#     """Analyzes query complexity for model routing"""
    
#     # Keywords that strongly indicate complexity
#     COMPLEX_KEYWORDS = [
#         "analyze", "analyse", "explain in detail", "compare", "detailed", 
#         "comprehensive", "step-by-step", "reasoning", "evaluate", "critique",
#         "implications", "philosophical", "in depth", "thoroughly",
#         "pros and cons", "advantages and disadvantages"
#     ]
    
#     # Keywords for simple queries
#     SIMPLE_KEYWORDS = [
#         "what is", "who is", "when", "where", "which",
#         "define", "meaning", "translate", "2+2", "calculate",
#         "is it", "are you", "can you"
#     ]
    
#     def analyze(self, query: str) -> dict:
#         """
#         Analyze query and return complexity score (0-1)
        
#         Scoring logic:
#         - Base score from length
#         - Boost for complex keywords (strong signal)
#         - Penalty for simple keywords
#         - Boost for multiple sentences/questions
#         """
#         query_lower = query.lower()
        
#         # Feature 1: Length score (longer queries tend to be more complex)
#         length_score = min(len(query) / 300, 1.0)  # Lowered threshold from 500 to 300
        
#         # Feature 2: Complex keywords (THIS IS KEY - give high weight)
#         complex_count = sum(1 for kw in self.COMPLEX_KEYWORDS if kw in query_lower)
#         complex_score = min(complex_count / 2, 1.0)  # Max out at just 2 keywords
        
#         # Feature 3: Simple keywords (negative signal)
#         simple_count = sum(1 for kw in self.SIMPLE_KEYWORDS if kw in query_lower)
#         simple_penalty = min(simple_count / 2, 0.4)  # Cap penalty at 0.4
        
#         # Feature 4: Multiple sentences/questions
#         sentence_count = query.count('.') + query.count('?') + query.count('!')
#         multi_sentence_boost = min(sentence_count / 3, 0.3)
        
#         # Feature 5: Long words (complex vocabulary)
#         words = query.split()
#         long_word_count = sum(1 for w in words if len(w) > 10)
#         long_word_boost = min(long_word_count / 5, 0.2)
        
#         # Calculate FINAL score with proper weights
#         complexity_score = (
#             length_score * 0.25 +          # Length contributes 25%
#             complex_score * 0.50 +         # Complex keywords contribute 50% (KEY!)
#             multi_sentence_boost * 0.15 +  # Multiple sentences contribute 15%
#             long_word_boost * 0.10 -       # Long words contribute 10%
#             simple_penalty * 0.40          # Simple keywords penalty
#         )
        
#         # Clamp between 0 and 1
#         complexity_score = max(0.0, min(1.0, complexity_score))
        
#         # Determine category
#         if complexity_score < 0.3:
#             category = "simple"
#         elif complexity_score < 0.7:
#             category = "medium"
#         else:
#             category = "complex"
        
#         return {
#             "complexity_score": round(complexity_score, 3),
#             "length": len(query),
#             "complex_keywords_found": complex_count,
#             "simple_keywords_found": simple_count,
#             "recommendation": category,
#             "breakdown": {
#                 "length_score": round(length_score, 2),
#                 "complex_score": round(complex_score, 2),
#                 "simple_penalty": round(simple_penalty, 2),
#                 "final": round(complexity_score, 3)
#             }
#         }


# # Global analyzer
# analyzer = QueryAnalyzer()

"""
analyzer.py - Query Complexity Analyzer
Scores any query from 0.0 (trivially simple) to 1.0 (very complex).

HOW IT WORKS:
  We compute 6 independent signals, weight them, and sum to a composite score.
  Each signal is clipped to [0, 1] before weighting.

  Signal               Weight  What it detects
  ─────────────────────────────────────────────────────────────
  length_score          0.15   Longer queries tend to need more reasoning
  keyword_score         0.40   "analyze", "compare" etc = complex intent
  question_score        0.10   Multiple ?s = multi-part question
  code_score            0.20   Code blocks need a capable model
  technical_score       0.10   Domain jargon (API, LLM, architecture...)
  sentence_score        0.05   Long sentences = complex sentence structure

WHY THIS APPROACH (vs ML):
  - Works with zero training data
  - Deterministic and debuggable
  - Fast (no model load)
  - The ML router (ml_router.py) REPLACES this once enough logs exist
"""

import re
from typing import Dict, Any

# Keywords that strongly signal complex reasoning needed
COMPLEX_KEYWORDS = [
    "analyze", "analyse", "evaluate", "critique", "compare", "contrast",
    "explain in detail", "deep dive", "comprehensive", "elaborate",
    "research", "investigate", "synthesize", "design", "architect",
    "philosophy", "implications", "trade-offs", "tradeoffs", "optimize",
    "strategy", "framework", "algorithm", "implement", "debug", "review",
    "refactor", "advanced", "complex", "nuanced", "pros and cons",
    "advantages and disadvantages", "step by step", "in depth",
]

# Keywords that signal simple lookup / factual queries
SIMPLE_KEYWORDS = [
    "what is", "define", "list", "name", "when", "who is", "how many",
    "yes or no", "simple", "quick", "brief", "tldr", "translate",
    "convert", "what does", "spell", "meaning of", "definition of",
]

# Technical jargon that implies a technical audience → more capable model
TECHNICAL_TERMS = [
    "api", "ml", "ai", "llm", "neural", "model", "architecture", "system",
    "database", "scalab", "latency", "throughput", "microservice",
    "kubernetes", "docker", "async", "concurrency", "distributed",
    "embedding", "vector", "transformer", "fine-tun", "inference",
]


def compute_complexity(query: str) -> Dict[str, Any]:
    """
    Returns a dict with:
      - composite: float 0–1, the final complexity score
      - factors:   dict of each individual signal (useful for debugging)
    """
    q_lower = query.lower()
    factors: Dict[str, float] = {}

    # ── Signal 1: Length ──────────────────────────────────────────────────────
    # Scale: 0 words = 0.0,  100+ words = 1.0
    word_count = len(query.split())
    factors["length"] = min(word_count / 100.0, 1.0)

    # ── Signal 2: Complex keywords (minus simple keywords) ────────────────────
    complex_hits = sum(1 for kw in COMPLEX_KEYWORDS if kw in q_lower)
    simple_hits  = sum(1 for kw in SIMPLE_KEYWORDS  if kw in q_lower)
    raw_keyword  = (complex_hits * 0.15) - (simple_hits * 0.10)
    factors["keywords"] = max(0.0, min(raw_keyword, 1.0))

    # ── Signal 3: Multiple questions ─────────────────────────────────────────
    # Each ? adds 0.15, capped at 0.45 (3 questions)
    factors["questions"] = min(query.count("?") * 0.15, 0.45)

    # ── Signal 4: Code presence ───────────────────────────────────────────────
    # Code block markers or common Python/JS patterns
    has_code = bool(re.search(
        r"```|def |class |import |function\s*\(|=>|<[a-z]+>|\$\{", query
    ))
    factors["code"] = 0.35 if has_code else 0.0

    # ── Signal 5: Technical jargon density ────────────────────────────────────
    tech_hits = len(re.findall(
        r"\b(" + "|".join(TECHNICAL_TERMS) + r")\b", q_lower
    ))
    factors["technical"] = min(tech_hits * 0.08, 0.4)

    # ── Signal 6: Average words per sentence ─────────────────────────────────
    sentences = [s.strip() for s in re.split(r"[.!?]", query) if s.strip()]
    if sentences:
        avg_words = sum(len(s.split()) for s in sentences) / len(sentences)
        factors["sentence"] = min(avg_words / 30.0, 1.0)
    else:
        factors["sentence"] = 0.0

    # ── Weighted composite ────────────────────────────────────────────────────
    weights = {
        "length":    0.15,
        "keywords":  0.40,
        "questions": 0.10,
        "code":      0.20,
        "technical": 0.10,
        "sentence":  0.05,
    }
    composite = sum(factors[k] * weights[k] for k in weights)
    composite = round(max(0.0, min(1.0, composite)), 4)

    return {"composite": composite, "factors": factors}


def select_model(complexity: float) -> str:
    """
    Map complexity score → Gemini model name.
    
    Why two tiers?
      Flash is ~17x cheaper than Pro. We only pay for Pro when truly needed.
      The thresholds (0.35, 0.65) are tunable via config.py.
    """
    from app.config import SIMPLE_THRESHOLD, COMPLEX_THRESHOLD, GEMINI_FLASH, GEMINI_PRO

    if complexity <= SIMPLE_THRESHOLD:
        return GEMINI_FLASH   # simple: "What is 2+2?" → cheapest
    elif complexity <= COMPLEX_THRESHOLD:
        return GEMINI_FLASH   # medium: still Flash, it handles most things
    else:
        return GEMINI_PRO     # complex: heavy reasoning → Pro