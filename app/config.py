"""
Simplified configuration for LLM Cost Firewall
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Mock mode for testing without real API keys
    MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
    
    # Budget Limits
    DAILY_BUDGET_USD = float(os.getenv("DAILY_BUDGET_USD", "100"))
    HOURLY_BUDGET_USD = float(os.getenv("HOURLY_BUDGET_USD", "10"))
    
    # Model pricing (per 1K tokens)
    MODEL_COSTS = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-opus-3": {"input": 0.015, "output": 0.075},
        "claude-haiku-3": {"input": 0.00025, "output": 0.00125},
    }
    
    # Routing thresholds
    SIMPLE_QUERY_THRESHOLD = 0.3
    COMPLEX_QUERY_THRESHOLD = 0.7
    
    @staticmethod
    def get_model_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a model call"""
        if model not in Config.MODEL_COSTS:
            return 0.0
        costs = Config.MODEL_COSTS[model]
        return (input_tokens / 1000) * costs["input"] + (output_tokens / 1000) * costs["output"]
    
    @staticmethod
    def select_model(complexity_score: float) -> str:
        """Select model based on complexity"""
        if complexity_score < Config.SIMPLE_QUERY_THRESHOLD:
            return "gpt-3.5-turbo"
        elif complexity_score < Config.COMPLEX_QUERY_THRESHOLD:
            return "gpt-3.5-turbo"  # Still cheap for medium queries
        else:
            return "gpt-4"


config = Config()