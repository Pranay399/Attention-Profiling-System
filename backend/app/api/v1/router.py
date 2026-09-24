"""Aggregates all v1 API routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, courses, recordings, live

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(courses.router)
api_router.include_router(recordings.router)
api_router.include_router(live.router)
