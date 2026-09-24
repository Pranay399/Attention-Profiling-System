"""
Data access layer — encapsulates all database queries.

Keeps SQLAlchemy query logic out of services and route handlers.
Each method is a single, focused query.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis import (
    AnalysisJob,
    AnalysisStatus,
    DetectedParticipant,
    Observation,
)
from app.models.course import Course, CourseEnrollment
from app.models.recording import Recording
from app.models.session import Session
from app.models.user import User


# ── User ──────────────────────────────────────────────────────────────────

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        return user


# ── Course ────────────────────────────────────────────────────────────────

class CourseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(self, user_id: str, role: str) -> list[Course]:
        """List courses accessible to a user based on their role."""
        if role == "teacher":
            stmt = (
                select(Course)
                .where(Course.instructor_id == user_id)
                .order_by(Course.created_at.desc())
            )
        elif role == "student":
            stmt = (
                select(Course)
                .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
                .where(CourseEnrollment.student_id == user_id)
                .order_by(Course.created_at.desc())
            )
        else:
            # Administrator sees all courses
            stmt = select(Course).order_by(Course.created_at.desc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, course_id: str) -> Course | None:
        result = await self.db.execute(
            select(Course)
            .options(selectinload(Course.instructor))
            .options(selectinload(Course.sessions))
            .where(Course.id == course_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Course | None:
        result = await self.db.execute(
            select(Course).where(Course.code == code)
        )
        return result.scalar_one_or_none()

    async def create(self, course: Course) -> Course:
        self.db.add(course)
        await self.db.flush()
        return course

    async def get_session_count(self, course_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Session.id)).where(Session.course_id == course_id)
        )
        return result.scalar_one()


# ── Session ───────────────────────────────────────────────────────────────

class SessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_course(self, course_id: str) -> list[Session]:
        result = await self.db.execute(
            select(Session)
            .where(Session.course_id == course_id)
            .order_by(Session.session_date.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, session_id: str) -> Session | None:
        result = await self.db.execute(
            select(Session)
            .options(selectinload(Session.recordings))
            .where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def create(self, session: Session) -> Session:
        self.db.add(session)
        await self.db.flush()
        return session


# ── Recording ─────────────────────────────────────────────────────────────

class RecordingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, recording_id: str) -> Recording | None:
        result = await self.db.execute(
            select(Recording)
            .options(selectinload(Recording.analysis_jobs))
            .where(Recording.id == recording_id)
        )
        return result.scalar_one_or_none()

    async def create(self, recording: Recording) -> Recording:
        self.db.add(recording)
        await self.db.flush()
        return recording

    async def update_status(
        self, recording_id: str, status: str, error_message: str | None = None
    ) -> None:
        recording = await self.db.get(Recording, recording_id)
        if recording:
            recording.status = status
            if error_message:
                recording.error_message = error_message
            await self.db.flush()


# ── Analysis ──────────────────────────────────────────────────────────────

class AnalysisRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, analysis_id: str) -> AnalysisJob | None:
        return await self.db.get(AnalysisJob, analysis_id)

    async def create(self, job: AnalysisJob) -> AnalysisJob:
        self.db.add(job)
        await self.db.flush()
        return job

    async def update_progress(
        self, analysis_id: str, frames_processed: int
    ) -> None:
        job = await self.db.get(AnalysisJob, analysis_id)
        if job:
            job.frames_processed = frames_processed
            await self.db.flush()

    async def update_status(
        self,
        analysis_id: str,
        status: AnalysisStatus,
        error_message: str | None = None,
        completed_at=None,
        started_at=None,
        frames_total: int | None = None,
    ) -> None:
        job = await self.db.get(AnalysisJob, analysis_id)
        if job:
            job.status = status
            if error_message is not None:
                job.error_message = error_message
            if completed_at is not None:
                job.completed_at = completed_at
            if started_at is not None:
                job.started_at = started_at
            if frames_total is not None:
                job.frames_total = frames_total
            await self.db.flush()

    async def get_participants(self, analysis_id: str) -> list[DetectedParticipant]:
        result = await self.db.execute(
            select(DetectedParticipant)
            .where(DetectedParticipant.analysis_id == analysis_id)
            .order_by(DetectedParticipant.label)
        )
        return list(result.scalars().all())

    async def get_observations(
        self, analysis_id: str, participant_id: str | None = None,
        limit: int = 1000, offset: int = 0,
    ) -> list[Observation]:
        stmt = (
            select(Observation)
            .where(Observation.analysis_id == analysis_id)
            .order_by(Observation.timestamp_sec)
            .limit(limit)
            .offset(offset)
        )
        if participant_id:
            stmt = stmt.where(Observation.participant_id == participant_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_observation_count(self, analysis_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Observation.id))
            .where(Observation.analysis_id == analysis_id)
        )
        return result.scalar_one()

    async def bulk_create_participants(
        self, participants: list[DetectedParticipant]
    ) -> None:
        self.db.add_all(participants)
        await self.db.flush()

    async def bulk_create_observations(
        self, observations: list[Observation]
    ) -> None:
        self.db.add_all(observations)
        await self.db.flush()
