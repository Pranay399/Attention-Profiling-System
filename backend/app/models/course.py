"""
Course and enrollment models.
"""

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid


class Course(TimestampMixin, Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )

    # Relationships
    instructor = relationship("User", back_populates="courses_taught")
    sessions = relationship(
        "Session", back_populates="course", order_by="Session.session_date.desc()"
    )
    enrollments = relationship("CourseEnrollment", back_populates="course")

    def __repr__(self) -> str:
        return f"<Course {self.code}: {self.name}>"


class CourseEnrollment(TimestampMixin, Base):
    __tablename__ = "course_enrollments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    course_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("courses.id"), nullable=False
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("course_id", "student_id", name="uq_enrollment"),
    )

    # Relationships
    course = relationship("Course", back_populates="enrollments")
    student = relationship("User")
