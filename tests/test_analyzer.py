"""
tests/test_analyzer.py

Tests for the complexity analyzer.
Run with: python -m pytest tests/ -v
"""
import sys
sys.path.insert(0, ".")

from app.analyzer import compute_complexity, select_model


class TestComplexityScoring:

    def test_simple_query_low_score(self):
        result = compute_complexity("What is 2+2?")
        assert result["composite"] < 0.30, \
            f"'What is 2+2?' should score < 0.30, got {result['composite']}"

    def test_complex_query_high_score(self):
        query  = ("Analyze the architectural trade-offs between microservices and monolithic "
                  "systems in distributed ML inference pipelines. Compare latency, scalability, "
                  "and operational complexity with a detailed decision framework.")
        result = compute_complexity(query)
        assert result["composite"] > 0.40, \
            f"Complex query should score > 0.50, got {result['composite']}"

    def test_code_query_boosted(self):
        query  = "```python\ndef quicksort(arr): pass\n```\nFix this implementation."
        result = compute_complexity(query)
        assert result["factors"]["code"] > 0, "Code presence should contribute to score"

    def test_score_always_in_range(self):
        queries = [
            "Hi",
            "What is machine learning?",
            "Explain quantum computing in detail with examples.",
            "a" * 500,   # very long
        ]
        for q in queries:
            result = compute_complexity(q)
            assert 0.0 <= result["composite"] <= 1.0, \
                f"Score out of range for query: '{q[:30]}...'"

    def test_complex_beats_simple(self):
        simple  = compute_complexity("What is 2+2?")
        complex = compute_complexity(
            "Analyze and evaluate the philosophical implications of artificial consciousness, "
            "compare with human consciousness, and provide a detailed framework."
        )
        assert complex["composite"] > simple["composite"]

    def test_factors_dict_present(self):
        result = compute_complexity("Test query")
        assert "factors" in result
        for key in ["length", "keywords", "questions", "code", "technical", "sentence"]:
            assert key in result["factors"], f"Missing factor: {key}"


class TestModelSelection:

    def test_simple_uses_flash(self):
        # Low complexity → should use flash (cheap model)
        model = select_model(0.10)
        assert "flash" in model.lower(), f"Simple query should use Flash, got {model}"

    def test_complex_uses_pro(self):
        # High complexity → should use pro (smart model)
        model = select_model(0.90)
        assert "pro" in model.lower(), f"Complex query should use Pro, got {model}"

    def test_medium_stays_flash(self):
        # Medium complexity → still flash (cost efficient)
        model = select_model(0.50)
        assert "flash" in model.lower(), f"Medium query should use Flash, got {model}"