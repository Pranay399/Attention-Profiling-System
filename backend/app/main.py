"""
Attention Profiling System — Application entry point.

Configures FastAPI with:
- Global exception handling (user-friendly error responses)
- CORS middleware
- Structured logging
- Database table creation on startup
- API router mounting
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ProcessingError,
    ValidationError,
)
from app.core.logging import generate_request_id, get_logger, setup_logging
from app.db.base import Base
from app.db.session import engine

# Import all models so Base.metadata knows about them
from app.models import analysis, course, recording, session, user  # noqa: F401

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    setup_logging(debug=settings.debug)
    logger.info("starting", app=settings.app_name, version=settings.app_version)

    # Create tables (dev only — use Alembic migrations in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_ready", url=settings.database_url)

    yield

    await engine.dispose()
    logger.info("shutdown_complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

# ── CORS ──────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handlers ────────────────────────────────────────────

ERROR_STATUS_MAP = {
    NotFoundError: 404,
    ValidationError: 422,
    AuthenticationError: 401,
    AuthorizationError: 403,
    ConflictError: 409,
    ProcessingError: 500,
}


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """Convert application exceptions to structured JSON responses."""
    status_code = ERROR_STATUS_MAP.get(type(exc), 500)
    request_id = getattr(request.state, "request_id", generate_request_id())

    if status_code >= 500:
        logger.error(
            "server_error",
            request_id=request_id,
            error_code=exc.code,
            error_message=exc.message,
            path=str(request.url),
        )
    else:
        logger.warning(
            "client_error",
            request_id=request_id,
            error_code=exc.code,
            error_message=exc.message,
            path=str(request.url),
        )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions. Never expose internals."""
    request_id = getattr(request.state, "request_id", generate_request_id())
    logger.error(
        "unhandled_error",
        request_id=request_id,
        error_type=type(exc).__name__,
        error=str(exc),
        path=str(request.url),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again.",
            },
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
    )


# ── Request ID Middleware ─────────────────────────────────────────────────

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach a request ID to every request for tracing."""
    request_id = generate_request_id()
    request.state.request_id = request_id
    import structlog
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Mount Router ──────────────────────────────────────────────────────────

app.include_router(api_router)


# ── Health Check ──────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "version": settings.app_version}
