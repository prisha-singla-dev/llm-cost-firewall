"""
ML-based routing - learns from actual usage patterns
UPDATED FOR GEMINI MODELS
"""
import pickle
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import Tuple

class MLRouter:
    """
    Machine learning model for routing decisions
    Learns from logged requests to improve over time
    """
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.model_path = Path("models/routing_model.pkl")
        self.vectorizer_path = Path("models/vectorizer.pkl")
        
        self.model_mapping = {
            "gpt-3.5-turbo": "gemini-flash-latest",
            "gpt-4": "gemini-pro-latest",
            "claude-haiku-3": "gemini-flash-latest",
            "claude-opus-3": "gemini-pro-latest",
            "gemini-flash-latest": "gemini-flash-latest",
            "gemini-pro-latest": "gemini-pro-latest",
        }
        
        # Load existing model if available
        self._load_model()
    
    def _load_model(self):
        """Load trained model from disk"""
        try:
            if self.model_path.exists() and self.vectorizer_path.exists():
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                with open(self.vectorizer_path, 'rb') as f:
                    self.vectorizer = pickle.load(f)
                print("[ML ROUTER] Loaded trained model ✓")
                print("[ML ROUTER] Note: Model trained on old data, will map to Gemini models")
            else:
                print("[ML ROUTER] No trained model found - using heuristics")
        except Exception as e:
            print(f"[ML ROUTER] Error loading model: {e}")
    
    def predict_model(self, query: str) -> Tuple[str, float]:
        """
        Predict which model to use based on query
        Returns: (model_name, confidence)
        CHANGED: Now maps predictions to Gemini models
        """
        if self.model is None or self.vectorizer is None:
            # Fallback to heuristic if no model
            from app.config import config
            from app.analyzer import analyzer
            
            analysis = analyzer.analyze(query)
            model = config.select_model(analysis["complexity_score"])
            return model, analysis["complexity_score"]
        
        try:
            # Vectorize query
            query_vec = self.vectorizer.transform([query])
            
            # Predict
            prediction = self.model.predict(query_vec)[0]
            confidence = self.model.predict_proba(query_vec).max()
            
            # CHANGED: Map old model names to new Gemini models
            mapped_model = self.model_mapping.get(prediction, "gemini-flash-latest")
            
            if prediction != mapped_model:
                print(f"[ML ROUTER] Mapped {prediction} → {mapped_model}")
            
            return mapped_model, confidence
            
        except Exception as e:
            print(f"[ML ROUTER] Prediction error: {e}")
            # Fallback to Gemini flash
            return "gemini-flash-latest", 0.5
    
    def train_from_logs(self, min_samples: int = 50):
        """
        Train model from request logs
        Only trains if we have enough data
        CHANGED: Now trains with Gemini model names
        """
        import csv
        from pathlib import Path
        
        log_file = Path("logs/requests.csv")
        if not log_file.exists():
            print("[ML ROUTER] No logs found - cannot train")
            return False
        
        # Read logs
        queries = []
        models = []
        
        with open(log_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('query') and row.get('model'):
                    query = row['query']
                    model = row['model']
                    
                    model = self.model_mapping.get(model, model)
                    
                    queries.append(query)
                    models.append(model)
        
        if len(queries) < min_samples:
            print(f"[ML ROUTER] Need {min_samples} samples, have {len(queries)} - skipping training")
            return False
        
        print(f"[ML ROUTER] Training on {len(queries)} requests...")
        
        # Train vectorizer
        self.vectorizer = TfidfVectorizer(max_features=100)
        X = self.vectorizer.fit_transform(queries)
        
        # Train classifier
        self.model = RandomForestClassifier(n_estimators=50, random_state=42)
        self.model.fit(X, models)
        
        # Save model
        self.model_path.parent.mkdir(exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
        with open(self.vectorizer_path, 'wb') as f:
            pickle.dump(self.vectorizer, f)
        
        print(f"[ML ROUTER] Training complete! Accuracy: {self.model.score(X, models):.2%}")
        print(f"[ML ROUTER] Model now predicts: {set(models)}")
        return True
    
    def get_stats(self):
        """Get model statistics"""
        if self.model is None:
            return {"status": "untrained", "using": "heuristics"}
        
        return {
            "status": "trained",
            "using": "ml_model",
            "model_type": "RandomForest",
            "features": len(self.vectorizer.get_feature_names_out()) if self.vectorizer else 0,
            "supported_models": list(set(self.model_mapping.values()))
        }


# Global ML router
ml_router = MLRouter()