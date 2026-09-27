"""
SQLAlchemy ORM models for all database tables.
Tables: users, classrooms, students, sessions, participants,
        meeting_integrations, video_sources, analysis_jobs,
        attention_events, attention_metrics, session_summaries,
        model_versions, audit_logs
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum as SAEnum, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from ..core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="student")  # admin, teacher, student
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    classrooms_owned = relationship("Classroom", back_populates="owner")
    audit_logs = relationship("AuditLog", back_populates="user")


# ─────────────────────────────────────────────────
# Classrooms
# ─────────────────────────────────────────────────
class Classroom(Base):
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    owner = relationship("User", back_populates="classrooms_owned")
    students = relationship("Student", back_populates="classroom")
    sessions = relationship("Session", back_populates="classroom")


# ─────────────────────────────────────────────────
# Students (enrollment in classrooms)
# ─────────────────────────────────────────────────
class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), default=utcnow)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("user_id", "classroom_id", name="uq_student_classroom"),
    )


# ─────────────────────────────────────────────────
# Sessions (class sessions)
# ─────────────────────────────────────────────────
class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(20), default="pending")  # pending, active, completed, cancelled
    scheduled_start = Column(DateTime(timezone=True), nullable=True)
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    classroom = relationship("Classroom", back_populates="sessions")
    participants = relationship("Participant", back_populates="session")
    meeting_integration = relationship("MeetingIntegration", back_populates="session", uselist=False)
    attention_events = relationship("AttentionEvent", back_populates="session")
    attention_metrics = relationship("AttentionMetric", back_populates="session")
    session_summary = relationship("SessionSummary", back_populates="session", uselist=False)
    analysis_jobs = relationship("AnalysisJob", back_populates="session")


# ─────────────────────────────────────────────────
# Participants (per-session)
# ─────────────────────────────────────────────────
class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    participant_identifier = Column(String(255), nullable=False)  # tracking ID
    display_name = Column(String(255), nullable=True)
    joined_at = Column(DateTime(timezone=True), default=utcnow)
    left_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    video_authorized = Column(Boolean, default=False)

    # Relationships
    session = relationship("Session", back_populates="participants")
    attention_events = relationship("AttentionEvent", back_populates="participant")
    attention_metrics = relationship("AttentionMetric", back_populates="participant")


# ─────────────────────────────────────────────────
# Meeting Integrations
# ─────────────────────────────────────────────────
class MeetingIntegration(Base):
    __tablename__ = "meeting_integrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, unique=True)
    provider = Column(String(50), nullable=False)  # google_meet, zoom, teams
    meeting_url = Column(String(512), nullable=True)
    meeting_id = Column(String(255), nullable=True)
    status = Column(String(20), default="pending")  # pending, connected, disconnected, error
    connection_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    session = relationship("Session", back_populates="meeting_integration")


# ─────────────────────────────────────────────────
# Video Sources
# ─────────────────────────────────────────────────
class VideoSource(Base):
    __tablename__ = "video_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=True)
    source_type = Column(String(50), nullable=False)  # webcam, screen_capture, meeting
    status = Column(String(20), default="pending")
    resolution = Column(String(20), nullable=True)
    fps = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


# ─────────────────────────────────────────────────
# Analysis Jobs
# ─────────────────────────────────────────────────
class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    model_version = Column(String(50), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    frames_processed = Column(Integer, default=0)
    events_generated = Column(Integer, default=0)
    avg_inference_latency_ms = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    session = relationship("Session", back_populates="analysis_jobs")


# ─────────────────────────────────────────────────
# Attention Events
# ─────────────────────────────────────────────────
class AttentionEvent(Base):
    __tablename__ = "attention_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    probability = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    duration_seconds = Column(Float, default=0.0)
    model_version = Column(String(50), nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_attention_events_session_time", "session_id", "created_at"),
        Index("ix_attention_events_participant", "participant_id", "created_at"),
    )

    # Relationships
    session = relationship("Session", back_populates="attention_events")
    participant = relationship("Participant", back_populates="attention_events")


# ─────────────────────────────────────────────────
# Attention Metrics (periodic aggregates, not per-frame)
# ─────────────────────────────────────────────────
class AttentionMetric(Base):
    __tablename__ = "attention_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    avg_attentive_prob = Column(Float, nullable=False)
    avg_inattentive_prob = Column(Float, nullable=False)
    avg_confidence = Column(Float, nullable=False)
    attention_state = Column(String(30), nullable=False)  # attentive, inattentive, unknown
    face_visible_pct = Column(Float, default=1.0)
    data_quality = Column(String(20), default="good")  # good, partial, poor

    __table_args__ = (
        Index("ix_attention_metrics_session", "session_id", "window_start"),
    )

    # Relationships
    session = relationship("Session", back_populates="attention_metrics")
    participant = relationship("Participant", back_populates="attention_metrics")


# ─────────────────────────────────────────────────
# Session Summaries
# ─────────────────────────────────────────────────
class SessionSummary(Base):
    __tablename__ = "session_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, unique=True)
    total_duration_seconds = Column(Float, default=0.0)
    total_participants = Column(Integer, default=0)
    avg_attention_probability = Column(Float, nullable=True)
    attention_distribution = Column(JSON, nullable=True)  # {"attentive": N, "inattentive": N, "unknown": N}
    total_events = Column(Integer, default=0)
    event_breakdown = Column(JSON, nullable=True)  # {"attention_drop": N, "recovered": N, ...}
    model_version = Column(String(50), nullable=True)
    data_quality_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    session = relationship("Session", back_populates="session_summary")


# ─────────────────────────────────────────────────
# Model Versions
# ─────────────────────────────────────────────────
class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    training_dataset = Column(String(255), nullable=True)
    feature_schema_version = Column(String(50), nullable=True)
    training_date = Column(DateTime(timezone=True), nullable=True)
    metrics = Column(JSON, nullable=True)
    model_path = Column(String(512), nullable=True)
    status = Column(String(20), default="staging")  # staging, production, archived
    parameters = Column(JSON, nullable=True)
    git_commit = Column(String(40), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("model_name", "version", name="uq_model_version"),
    )


# ─────────────────────────────────────────────────
# Audit Logs
# ─────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_audit_logs_user", "user_id", "created_at"),
        Index("ix_audit_logs_action", "action", "created_at"),
    )

    # Relationships
    user = relationship("User", back_populates="audit_logs")
