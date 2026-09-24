"""
Recording model — an uploaded video file linked to a session.
"""

import enum

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid


class RecordingStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Recording(TimestampMixin, Base):
    __tablename__ = "recordings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[RecordingStatus] = mapped_column(
        Enum(RecordingStatus), nullable=False, default=RecordingStatus.UPLOADED
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )

    # Relationships
    session = relationship("Session", back_populates="recordings")
    uploader = relationship("User")
    analysis_jobs = relationship("AnalysisJob", back_populates="recording")

    def __repr__(self) -> str:
        return f"<Recording {self.filename} ({self.status.value})>"
