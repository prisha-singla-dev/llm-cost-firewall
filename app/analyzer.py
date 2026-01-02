"""
Query complexity analyzer
"""


class QueryAnalyzer:
    """Analyzes query complexity for model routing"""
    
    COMPLEX_KEYWORDS = [
        "analyze", "explain", "compare", "detailed", "comprehensive",
        "step-by-step", "reasoning", "evaluate", "critique"
    ]
    
    SIMPLE_KEYWORDS = [
        "what is", "who is", "define", "translate", "summarize"
    ]
    
    def analyze(self, query: str) -> dict:
        """
        Analyze query and return complexity score (0-1)
        Simple heuristic: length + keywords
        """
        query_lower = query.lower()
        
        # Length score (longer = more complex)
        length_score = min(len(query) / 500, 1.0)
        
        # Complex keywords
        complex_count = sum(1 for kw in self.COMPLEX_KEYWORDS if kw in query_lower)
        complex_score = min(complex_count / 3, 1.0)
        
        # Simple keywords (penalty)
        simple_count = sum(1 for kw in self.SIMPLE_KEYWORDS if kw in query_lower)
        simple_penalty = min(simple_count / 2, 0.5)
        
        # Final score
        complexity_score = max(0.0, min(1.0, 
            length_score * 0.3 + complex_score * 0.5 - simple_penalty * 0.3
        ))
        
        return {
            "complexity_score": round(complexity_score, 3),
            "length": len(query),
            "recommendation": "simple" if complexity_score < 0.3 else "medium" if complexity_score < 0.7 else "complex"
        }


# Global analyzer
analyzer = QueryAnalyzer()