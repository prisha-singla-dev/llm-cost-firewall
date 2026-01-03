"""
Query complexity analyzer
"""

class QueryAnalyzer:
    """Analyzes query complexity for model routing"""
    
    # Keywords that strongly indicate complexity
    COMPLEX_KEYWORDS = [
        "analyze", "analyse", "explain in detail", "compare", "detailed", 
        "comprehensive", "step-by-step", "reasoning", "evaluate", "critique",
        "implications", "philosophical", "in depth", "thoroughly",
        "pros and cons", "advantages and disadvantages"
    ]
    
    # Keywords for simple queries
    SIMPLE_KEYWORDS = [
        "what is", "who is", "when", "where", "which",
        "define", "meaning", "translate", "2+2", "calculate",
        "is it", "are you", "can you"
    ]
    
    def analyze(self, query: str) -> dict:
        """
        Analyze query and return complexity score (0-1)
        
        Scoring logic:
        - Base score from length
        - Boost for complex keywords (strong signal)
        - Penalty for simple keywords
        - Boost for multiple sentences/questions
        """
        query_lower = query.lower()
        
        # Feature 1: Length score (longer queries tend to be more complex)
        length_score = min(len(query) / 300, 1.0)  # Lowered threshold from 500 to 300
        
        # Feature 2: Complex keywords (THIS IS KEY - give high weight)
        complex_count = sum(1 for kw in self.COMPLEX_KEYWORDS if kw in query_lower)
        complex_score = min(complex_count / 2, 1.0)  # Max out at just 2 keywords
        
        # Feature 3: Simple keywords (negative signal)
        simple_count = sum(1 for kw in self.SIMPLE_KEYWORDS if kw in query_lower)
        simple_penalty = min(simple_count / 2, 0.4)  # Cap penalty at 0.4
        
        # Feature 4: Multiple sentences/questions
        sentence_count = query.count('.') + query.count('?') + query.count('!')
        multi_sentence_boost = min(sentence_count / 3, 0.3)
        
        # Feature 5: Long words (complex vocabulary)
        words = query.split()
        long_word_count = sum(1 for w in words if len(w) > 10)
        long_word_boost = min(long_word_count / 5, 0.2)
        
        # Calculate FINAL score with proper weights
        complexity_score = (
            length_score * 0.25 +          # Length contributes 25%
            complex_score * 0.50 +         # Complex keywords contribute 50% (KEY!)
            multi_sentence_boost * 0.15 +  # Multiple sentences contribute 15%
            long_word_boost * 0.10 -       # Long words contribute 10%
            simple_penalty * 0.40          # Simple keywords penalty
        )
        
        # Clamp between 0 and 1
        complexity_score = max(0.0, min(1.0, complexity_score))
        
        # Determine category
        if complexity_score < 0.3:
            category = "simple"
        elif complexity_score < 0.7:
            category = "medium"
        else:
            category = "complex"
        
        return {
            "complexity_score": round(complexity_score, 3),
            "length": len(query),
            "complex_keywords_found": complex_count,
            "simple_keywords_found": simple_count,
            "recommendation": category,
            "breakdown": {
                "length_score": round(length_score, 2),
                "complex_score": round(complex_score, 2),
                "simple_penalty": round(simple_penalty, 2),
                "final": round(complexity_score, 3)
            }
        }


# Global analyzer
analyzer = QueryAnalyzer()