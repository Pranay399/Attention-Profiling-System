"""
Session model — represents a single class meeting or lecture.
"""

from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid


class Session(TimestampMixin, Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    course_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("courses.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )

    # Relationships
    course = relationship("Course", back_populates="sessions")
    creator = relationship("User")
    recordings = relationship(
        "Recording", back_populates="session", order_by="Recording.created_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<Session {self.title} ({self.session_date})>"
