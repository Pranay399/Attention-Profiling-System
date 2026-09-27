"""Participant management endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role, UserRole
from backend.app.models.models import Participant
from backend.app.schemas.schemas import ParticipantCreate, ParticipantResponse

router = APIRouter()


@router.post("/", response_model=ParticipantResponse, status_code=201)
async def add_participant(
    data: ParticipantCreate,
    current_user: dict = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    """Add a participant to a session."""
    participant = Participant(
        session_id=data.session_id,
        participant_identifier=data.participant_identifier,
        display_name=data.display_name,
        user_id=data.user_id,
        video_authorized=data.video_authorized,
    )
    db.add(participant)
    await db.flush()
    await db.refresh(participant)
    return participant


@router.get("/{participant_id}", response_model=ParticipantResponse)
async def get_participant(
    participant_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get participant details."""
    result = await db.execute(
        select(Participant).where(Participant.id == participant_id)
    )
    participant = result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    return participant
