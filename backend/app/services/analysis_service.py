"""
Analysis service that connects the CV pipeline -> Event Engine -> DB.
This is the core business logic layer, NOT in route handlers.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Optional

# Add AI source to path
AI_SRC = Path(__file__).resolve().parent.parent.parent.parent / "ai" / "src"
sys.path.insert(0, str(AI_SRC))

from ..core.config import settings

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Service layer that orchestrates:
    - Model loading and inference
    - Feature adaptation
    - Temporal smoothing and event detection
    - Event persistence
    """

    def __init__(self):
        self.model_server = None
        self.feature_adapter = None
        self.alert_manager = None
        self._is_initialized = False

    def load_model(self):
        """Load the ML model and initialize the inference pipeline."""
        try:
            from inference.model_server import AttentionModelServer
            from inference.event_engine import AlertManager, SmoothingConfig
            from pipeline.feature_adapter import FeatureAdapter

            # Load model
            self.model_server = AttentionModelServer(
                model_path=settings.MODEL_PATH,
                pipeline_path=settings.PIPELINE_PATH,
                schema_path=settings.FEATURE_SCHEMA_PATH,
                model_version=settings.MODEL_VERSION,
            )
            success = self.model_server.load()
            if not success:
                logger.error("Failed to load model")
                return

            # Initialize feature adapter
            self.feature_adapter = FeatureAdapter(
                feature_schema_path=settings.FEATURE_SCHEMA_PATH
            )

            # Initialize event engine with configurable thresholds
            config = SmoothingConfig(
                window_size=settings.ATTENTION_SMOOTHING_WINDOW,
                inattentive_threshold=settings.ATTENTION_INATTENTIVE_THRESHOLD,
                persistence_seconds=settings.ATTENTION_PERSISTENCE_SECONDS,
                cooldown_seconds=settings.ATTENTION_COOLDOWN_SECONDS,
                confidence_threshold=settings.ATTENTION_CONFIDENCE_THRESHOLD,
            )
            self.alert_manager = AlertManager(config)

            self._is_initialized = True
            logger.info("Analysis service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize analysis service: {e}")
            self._is_initialized = False

    def process_frame_features(
        self,
        participant_id: str,
        cv_features,
    ) -> Optional[Dict]:
        """
        Process CV features from a single frame through the full pipeline:
        CVFeatures -> FeatureAdapter -> Model -> Smoother -> EventDetector

        Returns event dict if an event was generated, None otherwise.
        """
        if not self._is_initialized:
            logger.warning("Analysis service not initialized")
            return None

        try:
            # 1. Convert dict to CVFeatures object
            from pipeline.feature_adapter import CVFeatures
            import dataclasses
            
            valid_fields = {f.name for f in dataclasses.fields(CVFeatures)}
            filtered_cv = {k: v for k, v in cv_features.items() if k in valid_fields}
            
            cv_obj = CVFeatures(**filtered_cv)
            
            # 2. Validate features
            validation = self.feature_adapter.validate_features(cv_obj)

            # 3. Convert to model input format
            feature_df = self.feature_adapter.cv_features_to_dataframe(cv_obj)

            # 4. Run inference
            result = self.model_server.predict(feature_df, validation)

            # 5. Process through event engine
            event = self.alert_manager.process_prediction(
                participant_id=participant_id,
                inattentive_prob=result.inattentive_probability,
                confidence=result.confidence,
                face_visible=cv_obj.face_present == 1,
                model_version=result.model_version,
            )

            if event:
                return event.to_dict()

            return None

        except Exception as e:
            logger.error(f"Frame processing error for {participant_id}: {e}")
            return None

    def get_participant_state(self, participant_id: str) -> Dict:
        """Get current attention state for a participant."""
        if not self._is_initialized:
            return {
                "participant_id": participant_id,
                "state": "unavailable",
                "reason": "Analysis service not initialized",
            }
        return self.alert_manager.get_participant_state(participant_id)

    def get_recent_events(self, limit: int = 50):
        """Get recent events from the event engine."""
        if not self._is_initialized:
            return []
        return self.alert_manager.get_recent_events(limit)

    def health_check(self) -> Dict:
        """Health check."""
        if not self._is_initialized:
            return {"status": "unavailable", "reason": "Not initialized"}

        model_health = self.model_server.health_check()
        return {
            "status": "healthy" if model_health["model_loaded"] else "degraded",
            **model_health,
        }

    def get_stats(self) -> Dict:
        """Get inference statistics."""
        if not self._is_initialized:
            return {}
        return self.model_server.get_stats()


# Singleton instance
analysis_service = AnalysisService()
