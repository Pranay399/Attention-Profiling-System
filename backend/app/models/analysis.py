"""
Analysis models — analysis jobs, detected participants, and observations.

This is the core data model for CV pipeline output.
"""

import enum

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid


class AnalysisStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BehaviorType(str, enum.Enum):
    ATTENTIVE = "attentive"
    LOOKING_AWAY = "looking_away"
    HEAD_DOWN = "head_down"
    NOT_VISIBLE = "not_visible"


class AnalysisJob(TimestampMixin, Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    recording_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recordings.id"), nullable=False, index=True
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus), nullable=False, default=AnalysisStatus.QUEUED
    )
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    frames_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frames_processed: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    started_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    recording = relationship("Recording", back_populates="analysis_jobs")
    participants = relationship(
        "DetectedParticipant", back_populates="analysis_job",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AnalysisJob {self.id[:8]} ({self.status.value})>"


class DetectedParticipant(TimestampMixin, Base):
    __tablename__ = "detected_participants"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_jobs.id"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    student_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    first_seen_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_seen_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    frame_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    analysis_job = relationship("AnalysisJob", back_populates="participants")
    student = relationship("User")
    observations = relationship(
        "Observation", back_populates="participant",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<DetectedParticipant {self.label}>"


class Observation(Base):
    """
    Per-participant, per-frame behavioral observation.

    This is the highest-volume table. No TimestampMixin to save space —
    the timestamp_sec field serves as the temporal reference within the video.
    created_at is inherited from the analysis job.
    """

    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_jobs.id"), nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("detected_participants.id"), nullable=False
    )
    timestamp_sec: Mapped[float] = mapped_column(Float, nullable=False)
    frame_number: Mapped[int] = mapped_column(Integer, nullable=False)
    behavior: Mapped[BehaviorType] = mapped_column(
        Enum(BehaviorType), nullable=False
    )
    head_yaw: Mapped[float | None] = mapped_column(Float, nullable=True)
    head_pitch: Mapped[float | None] = mapped_column(Float, nullable=True)
    head_roll: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    face_bbox: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index(
            "ix_observations_lookup",
            "analysis_id", "participant_id", "timestamp_sec",
        ),
    )

    # Relationships
    participant = relationship("DetectedParticipant", back_populates="observations")

    def __repr__(self) -> str:
        return f"<Observation {self.behavior.value} @ {self.timestamp_sec:.1f}s>"
