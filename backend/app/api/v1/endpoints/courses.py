"""Course and session endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.schemas import (
    CourseCreate,
    CourseDetailResponse,
    CourseResponse,
    SessionCreate,
    SessionDetailResponse,
    SessionResponse,
)
from app.services.service import CourseService, SessionService

router = APIRouter(tags=["courses"])


# ── Courses ───────────────────────────────────────────────────────────────

@router.get("/courses", response_model=list[CourseResponse])
async def list_courses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CourseService(db)
    return await service.list_courses(current_user)


@router.post("/courses", response_model=CourseResponse, status_code=201)
async def create_course(
    body: CourseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CourseService(db)
    return await service.create_course(
        name=body.name,
        code=body.code,
        description=body.description,
        user=current_user,
    )


@router.get("/courses/{course_id}", response_model=CourseDetailResponse)
async def get_course(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CourseService(db)
    course = await service.get_course(course_id, current_user)
    session_count = await service.get_session_count(course_id)
    return CourseDetailResponse(
        id=course.id,
        name=course.name,
        code=course.code,
        description=course.description,
        instructor_id=course.instructor_id,
        created_at=course.created_at,
        instructor=course.instructor,
        session_count=session_count,
    )


# ── Sessions ──────────────────────────────────────────────────────────────

@router.get("/courses/{course_id}/sessions", response_model=list[SessionResponse])
async def list_sessions(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SessionService(db)
    return await service.list_sessions(course_id)


@router.post(
    "/courses/{course_id}/sessions",
    response_model=SessionResponse,
    status_code=201,
)
async def create_session(
    course_id: str,
    body: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SessionService(db)
    return await service.create_session(
        course_id=course_id,
        title=body.title,
        description=body.description,
        session_date=body.session_date,
        user=current_user,
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SessionService(db)
    return await service.get_session(session_id)
