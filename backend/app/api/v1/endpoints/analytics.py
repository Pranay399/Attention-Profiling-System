"""Analytics endpoints for post-session analysis."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.models import (
    Session, AttentionEvent, AttentionMetric, SessionSummary, Participant
)
from backend.app.schemas.schemas import SessionSummaryResponse, SessionAnalytics

router = APIRouter()


@router.get("/session/{session_id}/summary", response_model=Optional[SessionSummaryResponse])
async def get_session_summary(
    session_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the post-session summary."""
    result = await db.execute(
        select(SessionSummary).where(SessionSummary.session_id == session_id)
    )
    summary = result.scalar_one_or_none()
    if not summary:
        raise HTTPException(status_code=404, detail="Session summary not available yet")
    return summary


@router.get("/session/{session_id}/dashboard")
async def get_session_analytics_dashboard(
    session_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive analytics dashboard data for a session."""
    # Session info
    session_result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Participants
    participants_result = await db.execute(
        select(Participant).where(Participant.session_id == session_id)
    )
    participants = participants_result.scalars().all()

    # Events
    events_result = await db.execute(
        select(AttentionEvent)
        .where(AttentionEvent.session_id == session_id)
        .order_by(AttentionEvent.created_at)
    )
    events = events_result.scalars().all()

    # Metrics
    metrics_result = await db.execute(
        select(AttentionMetric)
        .where(AttentionMetric.session_id == session_id)
        .order_by(AttentionMetric.window_start)
    )
    metrics = metrics_result.scalars().all()

    # Compute aggregates
    event_breakdown = {}
    for e in events:
        event_breakdown[e.event_type] = event_breakdown.get(e.event_type, 0) + 1

    # Duration
    duration = 0
    if session.actual_start and session.actual_end:
        duration = (session.actual_end - session.actual_start).total_seconds()

    # Average attention
    avg_attention = None
    if metrics:
        avg_attention = sum(m.avg_attentive_prob for m in metrics) / len(metrics)

    # Confidence distribution
    confidence_buckets = {"high": 0, "medium": 0, "low": 0}
    for m in metrics:
        if m.avg_confidence >= 0.8:
            confidence_buckets["high"] += 1
        elif m.avg_confidence >= 0.5:
            confidence_buckets["medium"] += 1
        else:
            confidence_buckets["low"] += 1

    # Per-participant timeline
    participant_timelines = []
    for p in participants:
        p_metrics = [m for m in metrics if m.participant_id == p.id]
        p_events = [e for e in events if e.participant_id == p.id]
        participant_timelines.append({
            "participant_id": p.id,
            "participant_identifier": p.participant_identifier,
            "display_name": p.display_name,
            "metrics": [
                {
                    "window_start": m.window_start.isoformat(),
                    "avg_attentive_prob": m.avg_attentive_prob,
                    "attention_state": m.attention_state,
                    "data_quality": m.data_quality,
                }
                for m in p_metrics
            ],
            "events": [
                {
                    "event_type": e.event_type,
                    "probability": e.probability,
                    "timestamp": e.created_at.isoformat(),
                }
                for e in p_events
            ],
        })

    return {
        "session_id": session_id,
        "status": session.status,
        "total_duration_seconds": duration,
        "total_participants": len(participants),
        "avg_attention_probability": avg_attention,
        "event_breakdown": event_breakdown,
        "total_events": len(events),
        "model_confidence_distribution": confidence_buckets,
        "participant_timelines": participant_timelines,
        "events_over_time": [
            {
                "timestamp": e.created_at.isoformat(),
                "event_type": e.event_type,
                "participant_id": e.participant_id,
                "probability": e.probability,
            }
            for e in events
        ],
        "data_quality_indicators": {
            "total_metrics": len(metrics),
            "good_quality_pct": (
                sum(1 for m in metrics if m.data_quality == "good") / len(metrics) * 100
                if metrics else 0
            ),
        },
    }


@router.get("/student/{user_id}/session/{session_id}")
async def get_student_session_analytics(
    user_id: int,
    session_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Student view: get own attention analytics for a session.
    Students can only see their own data — no rankings.
    """
    # Verify the requesting user is viewing their own data
    if current_user["role"] == "student" and current_user["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Cannot view other students' data")

    # Find participant record
    result = await db.execute(
        select(Participant).where(
            Participant.session_id == session_id,
            Participant.user_id == user_id,
        )
    )
    participant = result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=404, detail="No participation record found")

    # Get metrics
    metrics_result = await db.execute(
        select(AttentionMetric)
        .where(
            AttentionMetric.session_id == session_id,
            AttentionMetric.participant_id == participant.id,
        )
        .order_by(AttentionMetric.window_start)
    )
    metrics = metrics_result.scalars().all()

    # Session duration
    session_result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = session_result.scalar_one_or_none()

    duration = 0
    if session and session.actual_start and session.actual_end:
        duration = (session.actual_end - session.actual_start).total_seconds()

    return {
        "session_id": session_id,
        "session_duration_seconds": duration,
        "attention_timeline": [
            {
                "window_start": m.window_start.isoformat(),
                "window_end": m.window_end.isoformat(),
                "attention_state": m.attention_state,
                "avg_attentive_prob": round(m.avg_attentive_prob, 3),
                "data_quality": m.data_quality,
            }
            for m in metrics
        ],
        "insufficient_data_periods": [
            {
                "window_start": m.window_start.isoformat(),
                "window_end": m.window_end.isoformat(),
            }
            for m in metrics if m.data_quality == "poor"
        ],
        "avg_attention": (
            sum(m.avg_attentive_prob for m in metrics) / len(metrics)
            if metrics else None
        ),
    }

@router.get("/system/dashboard")
async def get_system_dashboard(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """System-wide dashboard stats for the frontend."""
    # This is a basic implementation for the dashboard prototype
    sessions_result = await db.execute(select(Session))
    all_sessions = sessions_result.scalars().all()
    active_sessions = [s for s in all_sessions if s.status == "active"]
    
    participants_result = await db.execute(select(func.count(Participant.id)))
    total_participants = participants_result.scalar_one()

    # Get recent attention events to show "Attention Drops"
    events_result = await db.execute(
        select(func.count(AttentionEvent.id))
        .where(AttentionEvent.event_type == "attention_drop")
    )
    attention_drops = events_result.scalar_one()

    return {
        "avg_attention_rate": 0, # Requires complex aggregation, simplified for now
        "active_sessions_count": len(active_sessions),
        "total_students": total_participants,
        "attention_drops_today": attention_drops,
        "active_sessions": [
            {
                "id": s.id,
                "name": s.title,
                "status": s.status,
            }
            for s in active_sessions
        ],
        "chart_data": [] # Could fetch timeline metrics for today
    }

