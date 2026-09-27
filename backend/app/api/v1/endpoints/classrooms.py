"""Classroom management endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role, UserRole
from backend.app.models.models import Classroom
from backend.app.schemas.schemas import ClassroomCreate, ClassroomUpdate, ClassroomResponse

router = APIRouter()


@router.get("/", response_model=List[ClassroomResponse])
async def list_classrooms(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List classrooms for the current user."""
    if current_user["role"] == UserRole.ADMIN:
        result = await db.execute(select(Classroom).where(Classroom.is_active == True))
    elif current_user["role"] == UserRole.TEACHER:
        result = await db.execute(
            select(Classroom).where(
                Classroom.owner_id == current_user["user_id"],
                Classroom.is_active == True,
            )
        )
    else:
        # Students see classrooms they're enrolled in
        result = await db.execute(select(Classroom).where(Classroom.is_active == True))

    return result.scalars().all()


@router.post("/", response_model=ClassroomResponse, status_code=201)
async def create_classroom(
    data: ClassroomCreate,
    current_user: dict = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new classroom."""
    classroom = Classroom(
        name=data.name,
        description=data.description,
        owner_id=current_user["user_id"],
    )
    db.add(classroom)
    await db.flush()
    await db.refresh(classroom)
    return classroom


@router.get("/{classroom_id}", response_model=ClassroomResponse)
async def get_classroom(
    classroom_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get classroom by ID."""
    result = await db.execute(
        select(Classroom).where(Classroom.id == classroom_id)
    )
    classroom = result.scalar_one_or_none()
    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")
    return classroom


@router.put("/{classroom_id}", response_model=ClassroomResponse)
async def update_classroom(
    classroom_id: int,
    data: ClassroomUpdate,
    current_user: dict = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    """Update a classroom."""
    result = await db.execute(
        select(Classroom).where(Classroom.id == classroom_id)
    )
    classroom = result.scalar_one_or_none()
    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")

    if data.name is not None:
        classroom.name = data.name
    if data.description is not None:
        classroom.description = data.description

    await db.flush()
    await db.refresh(classroom)
    return classroom


@router.delete("/{classroom_id}", status_code=204)
async def delete_classroom(
    classroom_id: int,
    current_user: dict = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a classroom."""
    result = await db.execute(
        select(Classroom).where(Classroom.id == classroom_id)
    )
    classroom = result.scalar_one_or_none()
    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")

    classroom.is_active = False
