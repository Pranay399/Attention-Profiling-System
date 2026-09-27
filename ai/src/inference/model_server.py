"""
Real-time inference engine for the attention classification model.
Loads the trained model + preprocessing pipeline and performs inference
on feature vectors extracted from the CV pipeline.
"""

import time
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

import numpy as np
import joblib

logger = logging.getLogger(__name__)

AI_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODEL_PATH = AI_DIR / "models" / "attention_classifier_best.joblib"
DEFAULT_PIPELINE_PATH = AI_DIR / "data" / "pipelines" / "preprocessing_pipeline.joblib"
DEFAULT_SCHEMA_PATH = AI_DIR / "data" / "pipelines" / "feature_schema.json"


@dataclass
class InferenceResult:
    """Result of a single attention inference."""
    attentive_probability: float
    inattentive_probability: float
    predicted_class: int  # 0=attentive, 1=inattentive
    confidence: float
    inference_latency_ms: float
    model_version: str
    feature_validation: Dict


class AttentionModelServer:
    """
    Serves the trained attention classification model for real-time inference.
    Handles model loading, preprocessing, and prediction with latency tracking.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        pipeline_path: Optional[str] = None,
        schema_path: Optional[str] = None,
        model_version: str = "attention-v1",
    ):
        self.model_path = Path(model_path or DEFAULT_MODEL_PATH)
        self.pipeline_path = Path(pipeline_path or DEFAULT_PIPELINE_PATH)
        self.schema_path = Path(schema_path or DEFAULT_SCHEMA_PATH)
        self.model_version = model_version

        self.model = None
        self.preprocessor = None
        self.is_loaded = False
        self._load_count = 0
        self._inference_count = 0
        self._total_latency_ms = 0

    def load(self) -> bool:
        """Load model and preprocessing pipeline."""
        try:
            if not self.model_path.exists():
                logger.error(f"Model not found: {self.model_path}")
                return False
            if not self.pipeline_path.exists():
                logger.error(f"Pipeline not found: {self.pipeline_path}")
                return False

            self.model = joblib.load(self.model_path)
            self.preprocessor = joblib.load(self.pipeline_path)
            self.is_loaded = True
            self._load_count += 1
            logger.info(f"Model loaded: {self.model_path.name} (v{self.model_version})")
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.is_loaded = False
            return False

    def predict(self, feature_df, validation: Optional[Dict] = None) -> InferenceResult:
        """
        Run inference on a feature DataFrame (single row or batch).

        Args:
            feature_df: pandas DataFrame with columns matching training schema
            validation: Optional validation results from FeatureAdapter

        Returns:
            InferenceResult with attention probabilities

        Raises:
            RuntimeError: if model is not loaded
            ValueError: if features are invalid
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        start = time.perf_counter()

        try:
            # Preprocess
            X = self.preprocessor.transform(feature_df)

            # Predict
            if hasattr(self.model, "predict_proba"):
                proba = self.model.predict_proba(X)
                predicted_class = int(np.argmax(proba[0]))
                attentive_prob = float(proba[0][0])
                inattentive_prob = float(proba[0][1])
            else:
                predicted_class = int(self.model.predict(X)[0])
                attentive_prob = 1.0 - predicted_class
                inattentive_prob = float(predicted_class)

            # Confidence = max probability
            confidence = max(attentive_prob, inattentive_prob)

            # Apply validation penalty
            if validation and not validation.get("valid", True):
                confidence *= validation.get("confidence", 0.5)

        except Exception as e:
            logger.error(f"Inference error: {e}")
            raise ValueError(f"Inference failed: {e}")

        latency_ms = (time.perf_counter() - start) * 1000
        self._inference_count += 1
        self._total_latency_ms += latency_ms

        return InferenceResult(
            attentive_probability=attentive_prob,
            inattentive_probability=inattentive_prob,
            predicted_class=predicted_class,
            confidence=confidence,
            inference_latency_ms=latency_ms,
            model_version=self.model_version,
            feature_validation=validation or {"valid": True, "issues": [], "confidence": 1.0},
        )

    def get_stats(self) -> Dict:
        """Get inference statistics."""
        avg_latency = (
            self._total_latency_ms / self._inference_count
            if self._inference_count > 0
            else 0
        )
        return {
            "is_loaded": self.is_loaded,
            "model_version": self.model_version,
            "model_path": str(self.model_path),
            "inference_count": self._inference_count,
            "avg_latency_ms": avg_latency,
            "total_latency_ms": self._total_latency_ms,
        }

    def health_check(self) -> Dict:
        """Health check for the model server."""
        return {
            "status": "healthy" if self.is_loaded else "unavailable",
            "model_loaded": self.is_loaded,
            "model_version": self.model_version,
            "inference_count": self._inference_count,
        }
