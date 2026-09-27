"""Session management endpoints."""

from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
import json
import base64
import numpy as np
import cv2
from backend.app.services.analysis_service import analysis_service
from meeting.capture.video_processor import FrameProcessor
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role, UserRole
from backend.app.models.models import Session, Classroom, Participant
from backend.app.schemas.schemas import SessionCreate, SessionUpdate, SessionResponse, ParticipantResponse

router = APIRouter()


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    classroom_id: int = None,
    status: str = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List sessions, optionally filtered by classroom and status."""
    query = select(Session)
    if classroom_id:
        query = query.where(Session.classroom_id == classroom_id)
    if status:
        query = query.where(Session.status == status)
    query = query.order_by(Session.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=SessionResponse, status_code=201)
async def create_session(
    data: SessionCreate,
    current_user: dict = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new class session."""
    # Verify classroom exists
    result = await db.execute(
        select(Classroom).where(Classroom.id == data.classroom_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Classroom not found")

    session = Session(
        classroom_id=data.classroom_id,
        title=data.title,
        scheduled_start=data.scheduled_start,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get session details."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/start", response_model=SessionResponse)
async def start_session(
    session_id: int,
    current_user: dict = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    """Start a session (begin analysis)."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status not in ("pending", "completed"):
        raise HTTPException(status_code=400, detail=f"Cannot start session in {session.status} state")

    session.status = "active"
    session.actual_start = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(session)
    return session


@router.post("/{session_id}/stop", response_model=SessionResponse)
async def stop_session(
    session_id: int,
    current_user: dict = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    """Stop a session (end analysis)."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.status = "completed"
    session.actual_end = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(session)
    return session


@router.get("/{session_id}/participants", response_model=List[ParticipantResponse])
async def get_session_participants(
    session_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get participants of a session."""
    result = await db.execute(
        select(Participant).where(Participant.session_id == session_id)
    )
    return result.scalars().all()

@router.websocket("/{session_id}/stream")
async def websocket_stream(websocket: WebSocket, session_id: int):
    await websocket.accept()
    processor = FrameProcessor(target_fps=10)
    try:
        while True:
            data_str = await websocket.receive_text()
            try:
                message = json.loads(data_str)
                if message.get("type") == "video_frame":
                    base64_data = message.get("data", "")
                    participant_id = message.get("participant_id", "unknown")
                    if "," in base64_data:
                        base64_data = base64_data.split(",")[1]
                    img_data = base64.b64decode(base64_data)
                    np_arr = np.frombuffer(img_data, np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    if frame is not None:
                        cv_features = processor.process_frame(frame)
                        if cv_features:
                            event = analysis_service.process_frame_features(
                                participant_id=participant_id, 
                                cv_features=cv_features
                            )
                            if event:
                                event['type'] = 'attention_alert'
                                await websocket.send_json(event)
                            
                            import time
                            current_time = time.time()
                            if not hasattr(processor, '_last_state_time') or current_time - processor._last_state_time > 1.0:
                                state = analysis_service.get_participant_state(participant_id)
                                if state:
                                    state['type'] = 'participant_state'
                                    state['timestamp'] = current_time
                                    await websocket.send_json(state)
                                processor._last_state_time = current_time
            except Exception as e:
                import logging
                logging.error(f"Error processing frame: {e}")
    except WebSocketDisconnect:
        processor.release()

