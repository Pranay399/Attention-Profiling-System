"""Attention events endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.models import AttentionEvent
from backend.app.schemas.schemas import AttentionEventResponse

router = APIRouter()


@router.get("/session/{session_id}", response_model=List[AttentionEventResponse])
async def get_session_events(
    session_id: int,
    event_type: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get attention events for a session."""
    query = select(AttentionEvent).where(
        AttentionEvent.session_id == session_id
    )
    if event_type:
        query = query.where(AttentionEvent.event_type == event_type)
    query = query.order_by(AttentionEvent.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/participant/{participant_id}", response_model=List[AttentionEventResponse])
async def get_participant_events(
    participant_id: int,
    limit: int = Query(default=100, le=500),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get attention events for a specific participant."""
    query = (
        select(AttentionEvent)
        .where(AttentionEvent.participant_id == participant_id)
        .order_by(AttentionEvent.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/session/{session_id}/summary")
async def get_event_summary(
    session_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get event count summary for a session."""
    result = await db.execute(
        select(
            AttentionEvent.event_type,
            func.count(AttentionEvent.id).label("count"),
        )
        .where(AttentionEvent.session_id == session_id)
        .group_by(AttentionEvent.event_type)
    )
    rows = result.all()
    return {
        "session_id": session_id,
        "event_counts": {row.event_type: row.count for row in rows},
        "total": sum(row.count for row in rows),
    }
