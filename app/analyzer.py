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