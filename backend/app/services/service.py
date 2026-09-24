"""
Business logic services.

Services contain the application logic. They use repositories for data access
and are called by route handlers. No HTTP concepts here — just domain logic.
"""

import os
import shutil
import uuid
from collections import Counter
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ProcessingError,
    ValidationError,
)
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.course import Course
from app.models.recording import Recording, RecordingStatus
from app.models.session import Session
from app.models.user import User, UserRole
from app.repositories.repository import (
    AnalysisRepository,
    CourseRepository,
    RecordingRepository,
    SessionRepository,
    UserRepository,
)
from app.schemas.schemas import (
    AnalysisSummary,
    BehaviorCount,
    ParticipantSummary,
    TimelineBucket,
)

logger = get_logger(__name__)


# ── Auth Service ──────────────────────────────────────────────────────────

class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def register(
        self, email: str, password: str, full_name: str, role: str
    ) -> User:
        existing = await self.repo.get_by_email(email)
        if existing:
            raise ConflictError(f"An account with email '{email}' already exists")

        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=UserRole(role),
        )
        return await self.repo.create(user)

    async def login(self, email: str, password: str) -> str:
        user = await self.repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise ValidationError("Invalid email or password")

        if not user.is_active:
            raise ValidationError("Account is deactivated")

        return create_access_token(subject=user.id)


# ── Course Service ────────────────────────────────────────────────────────

class CourseService:
    def __init__(self, db: AsyncSession):
        self.repo = CourseRepository(db)

    async def list_courses(self, user: User) -> list[Course]:
        return await self.repo.list_for_user(user.id, user.role.value)

    async def get_course(self, course_id: str, user: User) -> Course:
        course = await self.repo.get_by_id(course_id)
        if not course:
            raise NotFoundError("Course", course_id)
        return course

    async def create_course(
        self, name: str, code: str, description: str | None, user: User
    ) -> Course:
        if user.role not in (UserRole.TEACHER, UserRole.ADMINISTRATOR):
            raise AuthorizationError("Only teachers can create courses")

        existing = await self.repo.get_by_code(code)
        if existing:
            raise ConflictError(f"Course code '{code}' is already in use")

        course = Course(
            name=name,
            code=code.upper(),
            description=description,
            instructor_id=user.id,
        )
        return await self.repo.create(course)

    async def get_session_count(self, course_id: str) -> int:
        return await self.repo.get_session_count(course_id)


# ── Session Service ───────────────────────────────────────────────────────

class SessionService:
    def __init__(self, db: AsyncSession):
        self.repo = SessionRepository(db)
        self.course_repo = CourseRepository(db)

    async def list_sessions(self, course_id: str) -> list[Session]:
        return await self.repo.list_for_course(course_id)

    async def get_session(self, session_id: str) -> Session:
        session = await self.repo.get_by_id(session_id)
        if not session:
            raise NotFoundError("Session", session_id)
        return session

    async def create_session(
        self, course_id: str, title: str, description: str | None,
        session_date, user: User
    ) -> Session:
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise NotFoundError("Course", course_id)

        session = Session(
            course_id=course_id,
            title=title,
            description=description,
            session_date=session_date,
            created_by=user.id,
        )
        return await self.repo.create(session)


# ── Recording Service ────────────────────────────────────────────────────

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB


class RecordingService:
    def __init__(self, db: AsyncSession):
        self.repo = RecordingRepository(db)
        self.session_repo = SessionRepository(db)

    async def upload_recording(
        self, session_id: str, file: UploadFile, user: User
    ) -> Recording:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise NotFoundError("Session", session_id)

        # Validate file extension
        _, ext = os.path.splitext(file.filename or "")
        if ext.lower() not in ALLOWED_VIDEO_EXTENSIONS:
            raise ValidationError(
                f"Unsupported file format '{ext}'. "
                f"Supported formats: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}"
            )

        # Generate unique filename to prevent collisions
        safe_filename = f"{uuid.uuid4().hex}{ext.lower()}"
        file_path = settings.upload_dir / safe_filename

        # Stream file to disk (not loaded into memory)
        file_size = 0
        with open(file_path, "wb") as f:
            while chunk := await file.read(8192):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    os.unlink(file_path)
                    raise ValidationError(
                        f"File exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)} MB"
                    )
                f.write(chunk)

        recording = Recording(
            session_id=session_id,
            filename=file.filename or safe_filename,
            file_path=str(file_path),
            file_size_bytes=file_size,
            status=RecordingStatus.UPLOADED,
            uploaded_by=user.id,
        )
        result = await self.repo.create(recording)
        logger.info(
            "recording_uploaded",
            recording_id=result.id,
            filename=file.filename,
            size_bytes=file_size,
            user_id=user.id,
        )
        return result

    async def get_recording(self, recording_id: str) -> Recording:
        recording = await self.repo.get_by_id(recording_id)
        if not recording:
            raise NotFoundError("Recording", recording_id)
        return recording


# ── Analysis Service ──────────────────────────────────────────────────────

class AnalysisService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AnalysisRepository(db)
        self.recording_repo = RecordingRepository(db)

    async def start_analysis(self, recording_id: str) -> AnalysisJob:
        recording = await self.recording_repo.get_by_id(recording_id)
        if not recording:
            raise NotFoundError("Recording", recording_id)

        if recording.status == RecordingStatus.PROCESSING:
            raise ConflictError("This recording is already being processed")

        # Check for existing completed analysis
        for job in recording.analysis_jobs:
            if job.status == AnalysisStatus.PROCESSING:
                raise ConflictError("An analysis is already in progress for this recording")

        job = AnalysisJob(
            recording_id=recording_id,
            status=AnalysisStatus.QUEUED,
            model_version=settings.model_version,
            config={
                "frame_sample_rate": settings.frame_sample_rate,
                "face_detection_confidence": settings.face_detection_confidence,
                "yaw_threshold": settings.yaw_threshold,
                "pitch_threshold": settings.pitch_threshold,
            },
        )
        result = await self.repo.create(job)
        logger.info(
            "analysis_job_created",
            analysis_id=result.id,
            recording_id=recording_id,
            model_version=settings.model_version,
        )
        return result

    async def get_analysis(self, analysis_id: str) -> AnalysisJob:
        job = await self.repo.get_by_id(analysis_id)
        if not job:
            raise NotFoundError("Analysis job", analysis_id)
        return job

    async def get_participants(self, analysis_id: str):
        return await self.repo.get_participants(analysis_id)

    async def get_observations(
        self, analysis_id: str, participant_id: str | None = None,
        limit: int = 1000, offset: int = 0,
    ):
        return await self.repo.get_observations(
            analysis_id, participant_id, limit, offset
        )

    async def get_summary(self, analysis_id: str) -> AnalysisSummary:
        """Build a complete analysis summary with behavior distributions."""
        job = await self.get_analysis(analysis_id)
        participants = await self.repo.get_participants(analysis_id)
        observations = await self.repo.get_observations(analysis_id)

        # Overall behavior distribution
        overall_counter: Counter[str] = Counter()
        participant_counters: dict[str, Counter[str]] = {}
        participant_labels: dict[str, str] = {}
        participant_confidences: dict[str, list[float]] = {}

        for p in participants:
            participant_counters[p.id] = Counter()
            participant_labels[p.id] = p.label
            participant_confidences[p.id] = []

        for obs in observations:
            behavior = obs.behavior.value if hasattr(obs.behavior, 'value') else obs.behavior
            overall_counter[behavior] += 1
            if obs.participant_id in participant_counters:
                participant_counters[obs.participant_id][behavior] += 1
            if obs.confidence is not None and obs.participant_id in participant_confidences:
                participant_confidences[obs.participant_id].append(obs.confidence)

        total_obs = sum(overall_counter.values())

        def make_behavior_counts(counter: Counter[str], total: int) -> list[BehaviorCount]:
            return [
                BehaviorCount(
                    behavior=b,
                    count=c,
                    percentage=round(c / total * 100, 1) if total > 0 else 0,
                )
                for b, c in counter.most_common()
            ]

        # Get recording duration
        recording = await self.recording_repo.get_by_id(job.recording_id)
        duration = recording.duration_seconds if recording else None

        return AnalysisSummary(
            analysis_id=analysis_id,
            total_participants=len(participants),
            total_observations=total_obs,
            duration_seconds=duration,
            overall_behavior_distribution=make_behavior_counts(overall_counter, total_obs),
            participant_summaries=[
                ParticipantSummary(
                    participant_id=pid,
                    label=participant_labels[pid],
                    total_observations=sum(pcounter.values()),
                    behavior_breakdown=make_behavior_counts(pcounter, sum(pcounter.values())),
                    avg_confidence=(
                        round(sum(participant_confidences[pid]) / len(participant_confidences[pid]), 3)
                        if participant_confidences[pid] else None
                    ),
                )
                for pid, pcounter in participant_counters.items()
            ],
        )

    async def get_timeline(
        self, analysis_id: str, bucket_seconds: float = 5.0
    ) -> list[TimelineBucket]:
        """
        Aggregate observations into time buckets for the timeline chart.

        Each bucket contains the dominant behavior for each participant
        in that time window.
        """
        participants = await self.repo.get_participants(analysis_id)
        observations = await self.repo.get_observations(analysis_id)

        # Group by (participant, time_bucket)
        buckets: dict[tuple[str, float], Counter[str]] = {}
        participant_label_map = {p.id: p.label for p in participants}

        for obs in observations:
            bucket_key = (
                obs.participant_id,
                int(obs.timestamp_sec / bucket_seconds) * bucket_seconds,
            )
            if bucket_key not in buckets:
                buckets[bucket_key] = Counter()
            behavior = obs.behavior.value if hasattr(obs.behavior, 'value') else obs.behavior
            buckets[bucket_key][behavior] += 1

        result = []
        for (pid, ts), counter in sorted(buckets.items(), key=lambda x: (x[0][1], x[0][0])):
            dominant_behavior, count = counter.most_common(1)[0]
            result.append(TimelineBucket(
                timestamp_sec=ts,
                participant_id=pid,
                label=participant_label_map.get(pid, "Unknown"),
                behavior=dominant_behavior,
                count=count,
            ))

        return result
