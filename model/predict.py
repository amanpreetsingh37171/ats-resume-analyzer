import joblib
from pathlib import Path
import os
import numpy as np

class Predictor:
    def __init__(self, artifacts_dir='./artifacts'):
        self.artifacts_dir = Path(artifacts_dir)
        self.model = None
        self.vectorizer = None
        self.ready = False
        self._load()

    def _load(self):
        try:
            self.model = joblib.load(self.artifacts_dir / 'model.joblib')
            self.vectorizer = joblib.load(self.artifacts_dir / 'vectorizer.joblib')
            self.ready = True
        except Exception:
            self.ready = False

    def predict_text(self, text):
        if not self.ready:
            raise RuntimeError('Artifacts not loaded.')
        X = self.vectorizer.transform([text])
        pred = self.model.predict(X)[0]
        score = None
        if hasattr(self.model, 'predict_proba'):
            score = float(self.model.predict_proba(X)[0].max())
        elif hasattr(self.model, 'decision_function'):
            try:
                score = float(self.model.decision_function(X)[0])
            except Exception:
                score = None
        return pred, score