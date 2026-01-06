"""
LLM Router - handles model selection and API calls
"""
import time
import openai
from typing import Dict, Any, Optional
from app.config import config
from app.cache import cache
from app.analyzer import analyzer
from app.semantic_cache import semantic_cache


class LLMRouter:
    """Routes queries to optimal LLM model"""
    
    def __init__(self):
        self.total_cost = 0.0
        self.query_count = 0
        self.cache_hits = 0
        
        # Initialize OpenAI client if API key exists
        if config.OPENAI_API_KEY:
            try:
                self.openai_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            except Exception as e:
                print(f"OpenAI initialization failed: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
    
    async def route_query(self, query: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Main routing logic:
        1. Check cache
        2. Analyze complexity
        3. Select model
        4. Call LLM (real or mock)
        5. Track cost
        """
        start_time = time.time()
    
        # Step 1: Analyze complexity FIRST (we need this for cache key)
        analysis = analyzer.analyze(query)
        complexity_score = analysis["complexity_score"]
        
        # Step 2: Select model based on complexity
        model = config.select_model(complexity_score)
        
        # Step 3: Check cache with CORRECT model
        print(f"\n[ROUTER] Query: '{query[:50]}...'")
        print(f"[ROUTER] Complexity: {complexity_score} → Model: {model}")
        
        cached = cache.get(query, model)
        if cached:
            self.cache_hits += 1
            latency = round((time.time() - start_time) * 1000, 2)
            
            return {
                "response": cached["text"],
                "model": cached["model"],
                "cost_usd": 0.0,
                "cache_hit": True,
                "latency_ms": latency,
                "routing_reason": "Cache hit - query seen before",
                "complexity_score": complexity_score
            }
        
        # Step 3: Check SEMANTIC cache (NEW!)
        semantic_cached = semantic_cache.get(query, model)
        if semantic_cached:
            self.cache_hits += 1
            return {
                "response": semantic_cached["text"],
                "model": semantic_cached["model"],
                "cost_usd": 0.0,
                "cache_hit": True,
                "cache_type": "semantic",
                "similarity_score": semantic_cached.get("similarity_score", 0),
                "matched_query": semantic_cached.get("matched_query", ""),
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }   

        # Step 4: Call LLM (cache miss)
        print(f"[ROUTER] Cache miss, calling LLM...")
        
        try:
            if config.MOCK_MODE or not self.openai_client:
                response_text, input_tokens, output_tokens = self._mock_llm_call(query, model)
            else:
                response_text, input_tokens, output_tokens = await self._real_openai_call(query, model)
        except Exception as e:
            print(f"[ROUTER] Error: {e}")
            response_text, input_tokens, output_tokens = self._mock_llm_call(query, model)
            response_text = f"[FALLBACK MODE] {response_text}"
        
        # Step 5: Calculate cost
        cost = config.get_model_cost(model, int(input_tokens), int(output_tokens))
        self.total_cost += cost
        self.query_count += 1
        
        # Step 6: Cache the response for EXACT model
        cache.set(query, model, {
            "text": response_text,
            "model": model,
            "tokens": {"input": input_tokens, "output": output_tokens}
        })

        semantic_cache.set(query, model, {
            "text": response_text,
            "model": model,
            "tokens": {"input": input_tokens, "output": output_tokens}
        })
        
        latency = round((time.time() - start_time) * 1000, 2)
        
        # Determine routing reason
        if complexity_score < config.SIMPLE_QUERY_THRESHOLD:
            routing_reason = f"Simple query (score {complexity_score}) → cheap model"
        elif complexity_score < config.COMPLEX_QUERY_THRESHOLD:
            routing_reason = f"Medium complexity (score {complexity_score}) → balanced model"
        else:
            routing_reason = f"Complex query (score {complexity_score}) → powerful model"
        
        return {
            "response": response_text,
            "model": model,
            "cost_usd": round(cost, 6),
            "cache_hit": False,
            "complexity_score": complexity_score,
            "tokens": {"input": int(input_tokens), "output": int(output_tokens)},
            "latency_ms": latency,
            "routing_reason": routing_reason,
            "mode": "mock" if config.MOCK_MODE else "real",
            "analysis_breakdown": analysis.get("breakdown", {})
        }
    
    async def _real_openai_call(self, query: str, model: str) -> tuple:
        """Real OpenAI API call"""
        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant. Be concise and accurate."},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=500,
                timeout=30
            )
            
            response_text = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            return response_text, input_tokens, output_tokens
            
        except openai.AuthenticationError:
            print(f"[ERROR] Invalid API key")
            raise Exception("Invalid OpenAI API key - check .env file")
        except openai.RateLimitError:
            print(f"[ERROR] Rate limit exceeded")
            raise Exception("OpenAI rate limit exceeded - try again later")
        except openai.APITimeoutError:
            print(f"[ERROR] API timeout")
            raise Exception("OpenAI API timeout - try again")
        except Exception as e:
            print(f"[ERROR] OpenAI API error: {e}")
            # Fallback to mock on any error
            return self._mock_llm_call(query, model)
    
    def _mock_llm_call(self, query: str, model: str) -> tuple:
        """Mock LLM response for testing without API costs"""
        time.sleep(0.1)  # Simulate API latency
        
        # Generate realistic-looking response based on query
        response = f"This is a simulated response from {model}. "
        
        if "what" in query.lower() or "explain" in query.lower():
            response += f"In a real scenario, I would explain: {query[:100]}... "
        elif "how" in query.lower():
            response += f"Here's how: {query[:100]}... "
        else:
            response += f"Regarding your query: {query[:100]}... "
        
        response += "This is MOCK mode - set MOCK_MODE=false and add OPENAI_API_KEY for real responses."
        
        # Estimate tokens (rough approximation)
        input_tokens = len(query.split()) * 1.3
        output_tokens = len(response.split()) * 1.3
        
        return response, input_tokens, output_tokens
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics"""
        cache_rate = round(self.cache_hits / max(self.query_count, 1) * 100, 1)
        avg_cost = round(self.total_cost / max(self.query_count, 1), 4)
        
        return {
            "total_queries": self.query_count,
            "total_cost_usd": round(self.total_cost, 4),
            "cache_hits": self.cache_hits,
            "cache_hit_rate": cache_rate,
            "avg_cost_per_query": avg_cost,
            "estimated_savings_usd": round(self.cache_hits * avg_cost, 2),
            "mode": "mock" if config.MOCK_MODE else "real"
        }


# Global router instance
router = LLMRouter()