"""
FastAPI main application.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.database import init_db
from .api.v1 import router as api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    # Startup
    logger.info("Starting Attention Profiling System backend...")
    await init_db()
    logger.info("Database initialized")

    # Load ML model
    try:
        from .services.analysis_service import analysis_service
        analysis_service.load_model()
        logger.info("ML model loaded successfully")
    except Exception as e:
        logger.warning(f"ML model not loaded: {e}")

    yield

    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Real-Time Student Attention Profiling System API",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    return {"message": "Welcome to the Attention Profiling System API", "docs_url": "/docs"}

@app.get("/health")
async def health_check():
    """System health endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "app": settings.APP_NAME,
    }
