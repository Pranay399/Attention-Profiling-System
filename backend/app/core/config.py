"""
Core configuration for the backend application.
All settings are loaded from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
import os


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    # Application
    APP_NAME: str = "Attention Profiling System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///attention_profiling.db"
    DATABASE_URL_SYNC: str = "sqlite:///attention_profiling.db"

    # JWT Auth
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]

    # ML Model
    MODEL_PATH: str = str(Path(__file__).resolve().parent.parent.parent.parent / "ai" / "models" / "attention_classifier_best.joblib")
    PIPELINE_PATH: str = str(Path(__file__).resolve().parent.parent.parent.parent / "ai" / "data" / "pipelines" / "preprocessing_pipeline.joblib")
    FEATURE_SCHEMA_PATH: str = str(Path(__file__).resolve().parent.parent.parent.parent / "ai" / "data" / "pipelines" / "feature_schema.json")
    MODEL_VERSION: str = "attention-v1"

    # Attention thresholds (configurable)
    ATTENTION_INATTENTIVE_THRESHOLD: float = 0.65
    ATTENTION_PERSISTENCE_SECONDS: float = 5.0
    ATTENTION_COOLDOWN_SECONDS: float = 30.0
    ATTENTION_CONFIDENCE_THRESHOLD: float = 0.5
    ATTENTION_SMOOTHING_WINDOW: int = 10

    # Video processing
    TARGET_FPS: int = 10
    MIN_FPS: int = 5
    MAX_FPS: int = 15

    # Data retention
    DATA_RETENTION_DAYS: int = 90
    AUDIT_LOG_RETENTION_DAYS: int = 365

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
