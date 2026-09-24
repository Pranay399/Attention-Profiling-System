"""
Pydantic schemas for request/response validation.

Grouped by domain. Each schema has a clear purpose:
- *Create: incoming request for creating a resource
- *Update: incoming request for updating a resource
- *Response: outgoing response to the client
"""

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


# ── Meta ──────────────────────────────────────────────────────────────────

class ResponseMeta(BaseModel):
    request_id: str
    timestamp: datetime


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
    meta: ResponseMeta


# ── Auth ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    role: str = Field(default="teacher", pattern="^(teacher|administrator|student)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Course ────────────────────────────────────────────────────────────────

class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=20)
    description: str | None = None


class CourseResponse(BaseModel):
    id: str
    name: str
    code: str
    description: str | None
    instructor_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseDetailResponse(CourseResponse):
    instructor: UserResponse
    session_count: int = 0


# ── Session ───────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    session_date: date


class SessionResponse(BaseModel):
    id: str
    course_id: str
    title: str
    description: str | None
    session_date: date
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailResponse(SessionResponse):
    recordings: list["RecordingResponse"] = []


# ── Recording ─────────────────────────────────────────────────────────────

class RecordingResponse(BaseModel):
    id: str
    session_id: str
    filename: str
    file_size_bytes: int | None
    duration_seconds: float | None
    status: str
    error_message: str | None
    uploaded_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Analysis ──────────────────────────────────────────────────────────────

class AnalysisJobResponse(BaseModel):
    id: str
    recording_id: str
    status: str
    model_version: str
    frames_total: int | None
    frames_processed: int | None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ParticipantResponse(BaseModel):
    id: str
    label: str
    student_id: str | None
    first_seen_sec: float | None
    last_seen_sec: float | None
    frame_count: int

    model_config = {"from_attributes": True}


class ObservationResponse(BaseModel):
    id: str
    participant_id: str
    timestamp_sec: float
    frame_number: int
    behavior: str
    head_yaw: float | None
    head_pitch: float | None
    head_roll: float | None
    confidence: float | None

    model_config = {"from_attributes": True}


class BehaviorCount(BaseModel):
    behavior: str
    count: int
    percentage: float


class ParticipantSummary(BaseModel):
    participant_id: str
    label: str
    total_observations: int
    behavior_breakdown: list[BehaviorCount]
    avg_confidence: float | None


class AnalysisSummary(BaseModel):
    analysis_id: str
    total_participants: int
    total_observations: int
    duration_seconds: float | None
    overall_behavior_distribution: list[BehaviorCount]
    participant_summaries: list[ParticipantSummary]


class TimelineBucket(BaseModel):
    """A time bucket for the behavior timeline chart."""
    timestamp_sec: float
    participant_id: str
    label: str
    behavior: str
    count: int


# Forward reference resolution
SessionDetailResponse.model_rebuild()
