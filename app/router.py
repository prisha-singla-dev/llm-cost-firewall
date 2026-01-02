"""
LLM Router - handles model selection and API calls
"""
import time
from typing import Dict, Any
from app.config import config
from app.cache import cache
from app.analyzer import analyzer


class LLMRouter:
    """Routes queries to optimal LLM model"""
    
    def __init__(self):
        self.total_cost = 0.0
        self.query_count = 0
        self.cache_hits = 0
    
    async def route_query(self, query: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Main routing logic:
        1. Check cache
        2. Analyze complexity
        3. Select model
        4. Call LLM (or mock)
        5. Track cost
        """
        start_time = time.time()
        
        # Step 1: Check cache
        cached = cache.get(query, "any")
        if cached:
            self.cache_hits += 1
            return {
                "response": cached["text"],
                "model": cached["model"],
                "cost_usd": 0.0,
                "cache_hit": True,
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
        
        # Step 2: Analyze complexity
        analysis = analyzer.analyze(query)
        complexity_score = analysis["complexity_score"]
        
        # Step 3: Select model
        model = config.select_model(complexity_score)
        
        # Step 4: Call LLM (or mock in dev mode)
        if config.MOCK_MODE:
            response_text = self._mock_llm_call(query, model)
            input_tokens = len(query.split()) * 1.3  # Rough estimate
            output_tokens = len(response_text.split()) * 1.3
        else:
            response_text, input_tokens, output_tokens = await self._real_llm_call(query, model)
        
        # Step 5: Calculate cost
        cost = config.get_model_cost(model, int(input_tokens), int(output_tokens))
        self.total_cost += cost
        self.query_count += 1
        
        # Cache the response
        cache.set(query, model, {
            "text": response_text,
            "model": model,
            "tokens": {"input": input_tokens, "output": output_tokens}
        })
        
        latency = round((time.time() - start_time) * 1000, 2)
        
        return {
            "response": response_text,
            "model": model,
            "cost_usd": round(cost, 6),
            "cache_hit": False,
            "complexity_score": complexity_score,
            "tokens": {"input": int(input_tokens), "output": int(output_tokens)},
            "latency_ms": latency
        }
    
    def _mock_llm_call(self, query: str, model: str) -> str:
        """Mock LLM response for testing"""
        time.sleep(0.1)  # Simulate API latency
        return f"[MOCK {model}] This is a simulated response to: {query[:50]}..."
    
    async def _real_llm_call(self, query: str, model: str) -> tuple:
        """Real LLM API call (implement when you have API keys)"""
        # TODO: Implement real OpenAI/Anthropic calls
        return self._mock_llm_call(query, model), 100, 50
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics"""
        return {
            "total_queries": self.query_count,
            "total_cost_usd": round(self.total_cost, 2),
            "cache_hits": self.cache_hits,
            "cache_hit_rate": round(self.cache_hits / max(self.query_count, 1) * 100, 1),
            "avg_cost_per_query": round(self.total_cost / max(self.query_count, 1), 4)
        }


# Global router
router = LLMRouter()