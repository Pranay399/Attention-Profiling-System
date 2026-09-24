"""
Application configuration.

All settings are loaded from environment variables with sensible defaults
for local development. In production, set these via environment or .env file.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable loading."""

    # Application
    app_name: str = "Attention Profiling System"
    app_version: str = "0.1.0"
    debug: bool = True

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    data_dir: Path = base_dir / "data"
    upload_dir: Path = data_dir / "uploads"

    # Database
    database_url: str = f"sqlite+aiosqlite:///{base_dir / 'data' / 'app.db'}"

    # Auth
    secret_key: str = "CHANGE-ME-IN-PRODUCTION-use-openssl-rand-hex-32"
    access_token_expire_minutes: int = 60 * 24  # 24 hours for dev
    algorithm: str = "HS256"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # CV Pipeline
    frame_sample_rate: float = 2.0  # frames per second to analyze
    face_detection_confidence: float = 0.5
    face_mesh_confidence: float = 0.5

    # Behavior classification thresholds (degrees)
    yaw_threshold: float = 30.0  # looking away if |yaw| > this
    pitch_threshold: float = -20.0  # head down if pitch < this

    # Model metadata
    model_version: str = "mediapipe-facemesh-0.10"

    model_config = {"env_prefix": "APS_", "env_file": ".env"}


settings = Settings()

# Ensure directories exist at import time
settings.upload_dir.mkdir(parents=True, exist_ok=True)
