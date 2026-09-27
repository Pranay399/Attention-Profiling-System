"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field


# ─── Auth ───
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8)
    full_name: str
    role: str = "student"


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Classroom ───
class ClassroomCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ClassroomUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ClassroomResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Session ───
class SessionCreate(BaseModel):
    classroom_id: int
    title: str
    scheduled_start: Optional[datetime] = None


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None


class SessionResponse(BaseModel):
    id: int
    classroom_id: int
    title: str
    status: str
    scheduled_start: Optional[datetime]
    actual_start: Optional[datetime]
    actual_end: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Participant ───
class ParticipantCreate(BaseModel):
    session_id: int
    participant_identifier: str
    display_name: Optional[str] = None
    user_id: Optional[int] = None
    video_authorized: bool = False


class ParticipantResponse(BaseModel):
    id: int
    session_id: int
    participant_identifier: str
    display_name: Optional[str]
    user_id: Optional[int]
    is_active: bool
    video_authorized: bool
    joined_at: datetime
    left_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Meeting Integration ───
class MeetingIntegrationCreate(BaseModel):
    session_id: int
    provider: str = "google_meet"
    meeting_url: Optional[str] = None
    meeting_id: Optional[str] = None


class MeetingIntegrationResponse(BaseModel):
    id: int
    session_id: int
    provider: str
    meeting_url: Optional[str]
    meeting_id: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Attention Event ───
class AttentionEventCreate(BaseModel):
    session_id: int
    participant_id: int
    event_type: str
    probability: float
    confidence: float
    duration_seconds: float = 0.0
    model_version: str
    metadata_json: Optional[Dict[str, Any]] = None


class AttentionEventResponse(BaseModel):
    id: int
    session_id: int
    participant_id: int
    event_type: str
    probability: float
    confidence: float
    duration_seconds: float
    model_version: str
    metadata_json: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Attention Metrics ───
class AttentionMetricResponse(BaseModel):
    id: int
    session_id: int
    participant_id: int
    window_start: datetime
    window_end: datetime
    avg_attentive_prob: float
    avg_inattentive_prob: float
    avg_confidence: float
    attention_state: str
    face_visible_pct: float
    data_quality: str

    class Config:
        from_attributes = True


# ─── Session Summary ───
class SessionSummaryResponse(BaseModel):
    id: int
    session_id: int
    total_duration_seconds: float
    total_participants: int
    avg_attention_probability: Optional[float]
    attention_distribution: Optional[Dict[str, int]]
    total_events: int
    event_breakdown: Optional[Dict[str, int]]
    model_version: Optional[str]
    data_quality_summary: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Model Version ───
class ModelVersionCreate(BaseModel):
    model_name: str
    version: str
    training_dataset: Optional[str] = None
    feature_schema_version: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    model_path: Optional[str] = None
    status: str = "staging"
    parameters: Optional[Dict[str, Any]] = None
    git_commit: Optional[str] = None


class ModelVersionResponse(BaseModel):
    id: int
    model_name: str
    version: str
    training_dataset: Optional[str]
    feature_schema_version: Optional[str]
    training_date: Optional[datetime]
    metrics: Optional[Dict[str, Any]]
    model_path: Optional[str]
    status: str
    parameters: Optional[Dict[str, Any]]
    git_commit: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── WebSocket Messages ───
class WSAttentionEvent(BaseModel):
    """WebSocket message for attention events."""
    type: str = "attention_event"
    session_id: int
    participant_id: str
    event_type: str
    probability: float
    duration_seconds: float
    timestamp: str
    confidence: float
    model_version: str


class WSParticipantState(BaseModel):
    """WebSocket message for participant state updates."""
    type: str = "participant_state"
    session_id: int
    participant_id: str
    smoothed_inattentive_prob: float
    current_state: str
    state_duration: float
    confidence: float


# ─── Analytics ───
class SessionAnalytics(BaseModel):
    session_id: int
    total_duration_seconds: float
    total_participants: int
    avg_attention_probability: Optional[float]
    attention_distribution: Dict[str, int]
    events_over_time: List[Dict[str, Any]]
    participant_timelines: List[Dict[str, Any]]
    model_confidence_distribution: Dict[str, int]
    model_version: str
    data_quality_indicators: Dict[str, Any]


# ─── System Health ───
class SystemHealth(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
    database_connected: bool
    active_sessions: int
    active_websockets: int
    inference_stats: Dict[str, Any]


# ─── Config Update ───
class ThresholdConfigUpdate(BaseModel):
    inattentive_threshold: Optional[float] = None
    persistence_seconds: Optional[float] = None
    cooldown_seconds: Optional[float] = None
    confidence_threshold: Optional[float] = None
    smoothing_window: Optional[int] = None
    target_fps: Optional[int] = None
