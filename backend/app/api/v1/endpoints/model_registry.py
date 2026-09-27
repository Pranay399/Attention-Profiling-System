"""Model registry endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role, UserRole
from backend.app.models.models import ModelVersion
from backend.app.schemas.schemas import ModelVersionCreate, ModelVersionResponse

router = APIRouter()


@router.get("/", response_model=List[ModelVersionResponse])
async def list_model_versions(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all model versions."""
    result = await db.execute(
        select(ModelVersion).order_by(ModelVersion.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=ModelVersionResponse, status_code=201)
async def register_model_version(
    data: ModelVersionCreate,
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Register a new model version."""
    model_version = ModelVersion(
        model_name=data.model_name,
        version=data.version,
        training_dataset=data.training_dataset,
        feature_schema_version=data.feature_schema_version,
        metrics=data.metrics,
        model_path=data.model_path,
        status=data.status,
        parameters=data.parameters,
        git_commit=data.git_commit,
    )
    db.add(model_version)
    await db.flush()
    await db.refresh(model_version)
    return model_version


@router.get("/active")
async def get_active_model(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the currently active (production) model version."""
    result = await db.execute(
        select(ModelVersion).where(ModelVersion.status == "production")
    )
    model = result.scalar_one_or_none()
    if not model:
        return {"status": "no_production_model", "message": "No model in production"}
    return model
