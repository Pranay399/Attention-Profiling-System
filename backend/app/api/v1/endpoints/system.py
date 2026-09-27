"""System health and configuration endpoints."""

from fastapi import APIRouter, Depends
from backend.app.core.security import get_current_user, require_role, UserRole
from backend.app.core.config import settings
from backend.app.schemas.schemas import SystemHealth, ThresholdConfigUpdate

router = APIRouter()


@router.get("/health")
async def system_health():
    """Comprehensive system health check."""
    health = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "model_version": settings.MODEL_VERSION,
        "components": {
            "api": "healthy",
            "database": "unknown",
            "model": "unknown",
            "websocket": "unknown",
        },
    }

    # Check model
    try:
        from backend.app.services.analysis_service import analysis_service
        model_health = analysis_service.health_check()
        health["components"]["model"] = model_health.get("status", "unknown")
        health["inference_stats"] = analysis_service.get_stats()
    except Exception as e:
        health["components"]["model"] = f"error: {str(e)}"

    return health


@router.get("/config")
async def get_config(
    current_user: dict = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Get current system configuration (thresholds)."""
    return {
        "attention": {
            "inattentive_threshold": settings.ATTENTION_INATTENTIVE_THRESHOLD,
            "persistence_seconds": settings.ATTENTION_PERSISTENCE_SECONDS,
            "cooldown_seconds": settings.ATTENTION_COOLDOWN_SECONDS,
            "confidence_threshold": settings.ATTENTION_CONFIDENCE_THRESHOLD,
            "smoothing_window": settings.ATTENTION_SMOOTHING_WINDOW,
        },
        "video": {
            "target_fps": settings.TARGET_FPS,
            "min_fps": settings.MIN_FPS,
            "max_fps": settings.MAX_FPS,
        },
        "data_retention": {
            "retention_days": settings.DATA_RETENTION_DAYS,
            "audit_log_retention_days": settings.AUDIT_LOG_RETENTION_DAYS,
        },
    }


@router.put("/config/thresholds")
async def update_thresholds(
    config: ThresholdConfigUpdate,
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
):
    """Update attention detection thresholds at runtime."""
    updates = {}
    if config.inattentive_threshold is not None:
        settings.ATTENTION_INATTENTIVE_THRESHOLD = config.inattentive_threshold
        updates["inattentive_threshold"] = config.inattentive_threshold
    if config.persistence_seconds is not None:
        settings.ATTENTION_PERSISTENCE_SECONDS = config.persistence_seconds
        updates["persistence_seconds"] = config.persistence_seconds
    if config.cooldown_seconds is not None:
        settings.ATTENTION_COOLDOWN_SECONDS = config.cooldown_seconds
        updates["cooldown_seconds"] = config.cooldown_seconds
    if config.confidence_threshold is not None:
        settings.ATTENTION_CONFIDENCE_THRESHOLD = config.confidence_threshold
        updates["confidence_threshold"] = config.confidence_threshold
    if config.smoothing_window is not None:
        settings.ATTENTION_SMOOTHING_WINDOW = config.smoothing_window
        updates["smoothing_window"] = config.smoothing_window
    if config.target_fps is not None:
        settings.TARGET_FPS = config.target_fps
        updates["target_fps"] = config.target_fps

    return {"updated": updates, "status": "ok"}
