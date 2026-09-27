"""API v1 router."""

from fastapi import APIRouter
from .endpoints import auth, classrooms, sessions, participants, events, analytics, model_registry, system

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(classrooms.router, prefix="/classrooms", tags=["Classrooms"])
router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
router.include_router(participants.router, prefix="/participants", tags=["Participants"])
router.include_router(events.router, prefix="/events", tags=["Attention Events"])
router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
router.include_router(model_registry.router, prefix="/models", tags=["Model Registry"])
router.include_router(system.router, prefix="/system", tags=["System"])
