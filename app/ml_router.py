# """
# ML-based routing - learns from actual usage patterns
# UPDATED FOR GEMINI MODELS
# """
# import pickle
# from pathlib import Path
# import numpy as np
# from sklearn.ensemble import RandomForestClassifier
# from sklearn.feature_extraction.text import TfidfVectorizer
# from typing import Tuple

# class MLRouter:
#     """
#     Machine learning model for routing decisions
#     Learns from logged requests to improve over time
#     """
    
#     def __init__(self):
#         self.model = None
#         self.vectorizer = None
#         self.model_path = Path("models/routing_model.pkl")
#         self.vectorizer_path = Path("models/vectorizer.pkl")
        
#         self.model_mapping = {
#             "gpt-3.5-turbo": "gemini-flash-latest",
#             "gpt-4": "gemini-pro-latest",
#             "claude-haiku-3": "gemini-flash-latest",
#             "claude-opus-3": "gemini-pro-latest",
#             "gemini-flash-latest": "gemini-flash-latest",
#             "gemini-pro-latest": "gemini-pro-latest",
#         }
        
#         # Load existing model if available
#         self._load_model()
    
#     def _load_model(self):
#         """Load trained model from disk"""
#         try:
#             if self.model_path.exists() and self.vectorizer_path.exists():
#                 with open(self.model_path, 'rb') as f:
#                     self.model = pickle.load(f)
#                 with open(self.vectorizer_path, 'rb') as f:
#                     self.vectorizer = pickle.load(f)
#                 print("[ML ROUTER] Loaded trained model ✓")
#                 print("[ML ROUTER] Note: Model trained on old data, will map to Gemini models")
#             else:
#                 print("[ML ROUTER] No trained model found - using heuristics")
#         except Exception as e:
#             print(f"[ML ROUTER] Error loading model: {e}")
    
#     def predict_model(self, query: str) -> Tuple[str, float]:
#         """
#         Predict which model to use based on query
#         Returns: (model_name, confidence)
#         CHANGED: Now maps predictions to Gemini models
#         """
#         if self.model is None or self.vectorizer is None:
#             # Fallback to heuristic if no model
#             from app.config import config
#             from app.analyzer import analyzer
            
#             analysis = analyzer.analyze(query)
#             model = config.select_model(analysis["complexity_score"])
#             return model, analysis["complexity_score"]
        
#         try:
#             # Vectorize query
#             query_vec = self.vectorizer.transform([query])
            
#             # Predict
#             prediction = self.model.predict(query_vec)[0]
#             confidence = self.model.predict_proba(query_vec).max()
            
#             # CHANGED: Map old model names to new Gemini models
#             mapped_model = self.model_mapping.get(prediction, "gemini-flash-latest")
            
#             if prediction != mapped_model:
#                 print(f"[ML ROUTER] Mapped {prediction} → {mapped_model}")
            
#             return mapped_model, confidence
            
#         except Exception as e:
#             print(f"[ML ROUTER] Prediction error: {e}")
#             # Fallback to Gemini flash
#             return "gemini-flash-latest", 0.5
    
#     def train_from_logs(self, min_samples: int = 50):
#         """
#         Train model from request logs
#         Only trains if we have enough data
#         CHANGED: Now trains with Gemini model names
#         """
#         import csv
#         from pathlib import Path
        
#         log_file = Path("logs/requests.csv")
#         if not log_file.exists():
#             print("[ML ROUTER] No logs found - cannot train")
#             return False
        
#         # Read logs
#         queries = []
#         models = []
        
#         with open(log_file, 'r') as f:
#             reader = csv.DictReader(f)
#             for row in reader:
#                 if row.get('query') and row.get('model'):
#                     query = row['query']
#                     model = row['model']
                    
#                     model = self.model_mapping.get(model, model)
                    
#                     queries.append(query)
#                     models.append(model)
        
#         if len(queries) < min_samples:
#             print(f"[ML ROUTER] Need {min_samples} samples, have {len(queries)} - skipping training")
#             return False
        
#         print(f"[ML ROUTER] Training on {len(queries)} requests...")
        
#         # Train vectorizer
#         self.vectorizer = TfidfVectorizer(max_features=100)
#         X = self.vectorizer.fit_transform(queries)
        
#         # Train classifier
#         self.model = RandomForestClassifier(n_estimators=50, random_state=42)
#         self.model.fit(X, models)
        
#         # Save model
#         self.model_path.parent.mkdir(exist_ok=True)
#         with open(self.model_path, 'wb') as f:
#             pickle.dump(self.model, f)
#         with open(self.vectorizer_path, 'wb') as f:
#             pickle.dump(self.vectorizer, f)
        
#         print(f"[ML ROUTER] Training complete! Accuracy: {self.model.score(X, models):.2%}")
#         print(f"[ML ROUTER] Model now predicts: {set(models)}")
#         return True
    
#     def get_stats(self):
#         """Get model statistics"""
#         if self.model is None:
#             return {"status": "untrained", "using": "heuristics"}
        
#         return {
#             "status": "trained",
#             "using": "ml_model",
#             "model_type": "RandomForest",
#             "features": len(self.vectorizer.get_feature_names_out()) if self.vectorizer else 0,
#             "supported_models": list(set(self.model_mapping.values()))
#         }


# # Global ML router
# ml_router = MLRouter()

"""
ml_router.py - Random Forest ML Router  [UPGRADED from your existing file]

WHAT THIS DOES:
  Learns from your actual request logs to improve routing decisions.
  After seeing enough real queries, it replaces the heuristic analyzer.

HOW RANDOM FOREST WORKS:
  1. Feature extraction: convert each query → numeric feature vector
     [word_count, question_count, has_code, complex_keyword_count, ...]
  2. Training: fit RandomForestClassifier on (features → model_used) pairs
  3. Prediction: given a new query, predict which model should handle it
     + return confidence score (probability of that class)

WHY RANDOM FOREST:
  - Handles non-linear patterns the heuristic misses
  - Built-in feature importance (tells you WHAT makes queries complex)
  - Fast prediction (<1ms)
  - Doesn't need GPU / large model
  - You already have scikit-learn installed

TRAINING TRIGGER:
  - Called via POST /train endpoint
  - Requires ≥50 logged requests to be meaningful
  - Re-training takes ~100ms

FEATURE VECTOR (12 features per query):
  0: word_count
  1: char_count
  2: question_count
  3: has_code (0/1)
  4: complex_keyword_count
  5: simple_keyword_count
  6: avg_words_per_sentence
  7: technical_term_count
  8: sentence_count
  9: has_numbers (0/1)
  10: uppercase_ratio
  11: punctuation_count
"""

import os
import re
import pickle
from typing import Dict, List, Optional, Any

try:
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score
    import pandas as pd
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

from app.analyzer import COMPLEX_KEYWORDS, SIMPLE_KEYWORDS, TECHNICAL_TERMS
from app.config   import GEMINI_FLASH, GEMINI_PRO, LOG_FILE

MODEL_SAVE_PATH = "models/rf_router.pkl"


def _extract_features(query: str) -> List[float]:
    """Convert a query string into a 12-element numeric feature vector."""
    q_lower   = query.lower()
    words     = query.split()
    sentences = [s.strip() for s in re.split(r"[.!?]", query) if s.strip()]

    return [
        len(words),                                                     # 0: word count
        len(query),                                                     # 1: char count
        query.count("?"),                                               # 2: question marks
        float(bool(re.search(r"```|def |class |import |function\s*\(", query))),  # 3: has code
        sum(1 for kw in COMPLEX_KEYWORDS if kw in q_lower),            # 4: complex keywords
        sum(1 for kw in SIMPLE_KEYWORDS  if kw in q_lower),            # 5: simple keywords
        sum(len(s.split()) for s in sentences) / max(len(sentences), 1),  # 6: avg words/sentence
        len(re.findall(r"\b(" + "|".join(TECHNICAL_TERMS) + r")\b", q_lower)),  # 7: tech terms
        len(sentences),                                                  # 8: sentence count
        float(bool(re.search(r"\d+", query))),                          # 9: has numbers
        sum(1 for c in query if c.isupper()) / max(len(query), 1),      # 10: uppercase ratio
        sum(1 for c in query if c in ".,;:!?"),                         # 11: punctuation count
    ]


class MLRouter:
    def __init__(self):
        self._clf:       Optional[Any] = None
        self._classes:   List[str]     = []
        self.is_trained: bool          = False
        self.accuracy:   float         = 0.0
        self.n_samples:  int           = 0

        # Try loading a previously trained model
        self._load()

    def _load(self):
        """Load persisted model from disk if it exists."""
        if not ML_AVAILABLE:
            return
        if os.path.exists(MODEL_SAVE_PATH):
            try:
                with open(MODEL_SAVE_PATH, "rb") as f:
                    saved = pickle.load(f)
                self._clf       = saved["clf"]
                self._classes   = saved["classes"]
                self.is_trained = True
                self.accuracy   = saved.get("accuracy", 0.0)
                self.n_samples  = saved.get("n_samples", 0)
            except Exception:
                self._clf       = None
                self.is_trained = False

    def _save(self):
        """Persist trained model to disk."""
        os.makedirs("models", exist_ok=True)
        with open(MODEL_SAVE_PATH, "wb") as f:
            pickle.dump({
                "clf":       self._clf,
                "classes":   self._classes,
                "accuracy":  self.accuracy,
                "n_samples": self.n_samples,
            }, f)

    def train(self, log_file: str = LOG_FILE) -> Dict:
        """
        Train the RF classifier from the request CSV log.
        Called via POST /train endpoint.

        Minimum 50 samples required for a meaningful model.
        Returns training report dict.
        """
        if not ML_AVAILABLE:
            return {"success": False, "reason": "scikit-learn not installed"}

        if not os.path.exists(log_file):
            return {"success": False, "reason": "No log file found. Make some requests first."}

        df = pd.read_csv(log_file)

        # Only use real (non-cached) requests for training
        df = df[df["cache_hit"].astype(str).str.lower() == "false"]
        df = df.dropna(subset=["query_preview", "model_used"])

        if len(df) < 50:
            return {
                "success": False,
                "reason": f"Need ≥50 real requests to train. Have {len(df)}.",
                "have":   len(df),
                "need":   50,
            }

        X = np.array([_extract_features(q) for q in df["query_preview"]])
        y = df["model_used"].values

        clf = RandomForestClassifier(
            n_estimators=100,       # 100 trees
            max_depth=10,           # prevent overfitting
            min_samples_leaf=3,     # require at least 3 samples per leaf
            random_state=42,
        )

        # Cross-validation to estimate real accuracy
        try:
            cv_scores    = cross_val_score(clf, X, y, cv=min(5, len(df) // 10), scoring="accuracy")
            self.accuracy = round(float(cv_scores.mean()), 3)
        except Exception:
            self.accuracy = 0.0

        clf.fit(X, y)
        self._clf       = clf
        self._classes   = list(clf.classes_)
        self.is_trained = True
        self.n_samples  = len(df)
        self._save()

        # Feature importance
        feature_names = [
            "word_count", "char_count", "question_count", "has_code",
            "complex_keywords", "simple_keywords", "avg_words_sentence",
            "tech_terms", "sentence_count", "has_numbers",
            "uppercase_ratio", "punctuation_count",
        ]
        importance = {
            name: round(float(imp), 4)
            for name, imp in zip(feature_names, clf.feature_importances_)
        }

        return {
            "success":           True,
            "samples_used":      len(df),
            "cv_accuracy":       self.accuracy,
            "classes":           self._classes,
            "top_features":      dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]),
        }

    def predict(self, query: str) -> Dict:
        """
        Predict the best model for a query.
        Returns {"model": str, "confidence": float}
        """
        if not self.is_trained or self._clf is None:
            return {"model": GEMINI_FLASH, "confidence": 0.0, "source": "heuristic_fallback"}

        features = np.array([_extract_features(query)])
        proba    = self._clf.predict_proba(features)[0]
        idx      = proba.argmax()
        model    = self._classes[idx]
        conf     = float(proba[idx])

        return {"model": model, "confidence": round(conf, 4), "source": "ml_router"}