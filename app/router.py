"""
LLM Router - handles model selection and API calls
UPDATED FOR GEMINI API
"""
import time
import google.generativeai as genai
from typing import Dict, Any, Optional
from app.config import config
from app.cache import cache
from app.analyzer import analyzer
from app.semantic_cache import semantic_cache
from app.ml_router import ml_router


class LLMRouter:
    """Routes queries to optimal LLM model"""
    
    def __init__(self):
        self.total_cost = 0.0
        self.query_count = 0
        self.cache_hits = 0
        
        if config.GEMINI_API_KEY:
            try:
                genai.configure(api_key=config.GEMINI_API_KEY)
                self.gemini_configured = True
                print("[ROUTER] Gemini API configured successfully ✅")
            except Exception as e:
                print(f"[ROUTER] Gemini initialization failed: {e}")
                self.gemini_configured = False
        else:
            self.gemini_configured = False
            print("[ROUTER] No GEMINI_API_KEY found - running in MOCK mode")
    
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
        # Try ML router first, fallback to heuristic
        try:
            model, confidence = ml_router.predict_model(query)
            print(f"[ROUTER] ML predicted: {model} (confidence: {confidence:.2f})")
        except Exception as e:
            model = config.select_model(complexity_score)
            confidence = 0.0
            print(f"[ROUTER] ML fallback: {model}")

        # model = config.select_model(complexity_score)
        # confidence = 0.0
        # print(f"[ROUTER] Heuristic routing: {model}")

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
        
        # Step 3b: Check SEMANTIC cache
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
            if config.MOCK_MODE or not self.gemini_configured:
                response_text, input_tokens, output_tokens = self._mock_llm_call(query, model)
            else:
                response_text, input_tokens, output_tokens = self._real_gemini_call(query, model)
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
            "analysis_breakdown": analysis.get("breakdown", {}),
            "routing_method": "ml" if ml_router.model is not None else "heuristic",
            "routing_confidence": round(confidence, 2)
        }
    
    def _real_gemini_call(self, query: str, model: str) -> tuple:
        """
        Real Gemini API call
        CHANGED: Completely new method for Gemini
        """
        try:
            gemini_model = genai.GenerativeModel(model)
            response = gemini_model.generate_content(query)
            response_text = response.text

            # Use rough estimation: ~1.3 tokens per word
            input_tokens = len(query.split()) * 1.3
            output_tokens = len(response_text.split()) * 1.3
            
            print(f"[ROUTER] ✅ Gemini {model} responded successfully")
            
            return response_text, int(input_tokens), int(output_tokens)
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Gemini API error: {error_msg}")
            
            if "API_KEY_INVALID" in error_msg or "invalid api key" in error_msg.lower():
                raise Exception("Invalid Gemini API key - get one at https://aistudio.google.com/app/apikey")
            elif "quota" in error_msg.lower() or "rate" in error_msg.lower():
                raise Exception("Gemini rate limit exceeded - wait 1 minute (15 req/min limit)")
            else:
                raise Exception(f"Gemini API error: {error_msg}")
    
   
    def _mock_llm_call(self, query: str, model: str) -> tuple:
        """Mock LLM response for testing without API costs"""
        time.sleep(0.1)  # Simulate API latency
        
        response = f"This is a simulated response from {model}. "
        
        if "what" in query.lower() or "explain" in query.lower():
            response += f"In a real scenario, I would explain: {query[:100]}... "
        elif "how" in query.lower():
            response += f"Here's how: {query[:100]}... "
        else:
            response += f"Regarding your query: {query[:100]}... "
        
        response += "This is MOCK mode - set GEMINI_API_KEY environment variable for real responses."
        
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