"""Recording and analysis endpoints."""

import asyncio
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db, async_session_factory
from app.models.user import User
from app.schemas.schemas import (
    AnalysisJobResponse,
    AnalysisSummary,
    ObservationResponse,
    ParticipantResponse,
    RecordingResponse,
    TimelineBucket,
)
from app.services.service import AnalysisService, RecordingService

router = APIRouter(tags=["recordings"])


# ── Recordings ────────────────────────────────────────────────────────────

@router.post(
    "/sessions/{session_id}/recordings/upload",
    response_model=RecordingResponse,
    status_code=201,
)
async def upload_recording(
    session_id: str,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecordingService(db)
    return await service.upload_recording(session_id, file, current_user)


@router.get("/recordings/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    recording_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecordingService(db)
    return await service.get_recording(recording_id)


@router.get("/recordings/{recording_id}/stream")
async def stream_recording(
    recording_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecordingService(db)
    recording = await service.get_recording(recording_id)
    file_path = Path(recording.file_path)
    if not file_path.exists():
        from app.core.errors import NotFoundError
        raise NotFoundError("Recording file")
    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=recording.filename,
    )


# ── Analysis ──────────────────────────────────────────────────────────────

@router.post(
    "/recordings/{recording_id}/analyze",
    response_model=AnalysisJobResponse,
    status_code=201,
)
async def start_analysis(
    recording_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnalysisService(db)
    job = await service.start_analysis(recording_id)

    # Run the CV pipeline in a background task
    # We pass IDs rather than ORM objects to avoid session issues
    background_tasks.add_task(
        _run_analysis_background, job.id, recording_id
    )

    return job


async def _run_analysis_background(analysis_id: str, recording_id: str):
    """
    Run the CV pipeline in the background.

    Uses its own database session since the request session is closed
    by the time this runs.
    """
    from app.pipeline.video_processor import VideoProcessor

    async with async_session_factory() as db:
        try:
            processor = VideoProcessor(db)
            await processor.process(analysis_id, recording_id)
            await db.commit()
        except Exception as e:
            await db.rollback()
            # Update the job status to failed
            from app.repositories.repository import AnalysisRepository
            from app.models.analysis import AnalysisStatus
            from app.core.logging import get_logger

            logger = get_logger("analysis_background")
            logger.error(
                "analysis_failed",
                analysis_id=analysis_id,
                error=str(e),
            )

            async with async_session_factory() as err_db:
                repo = AnalysisRepository(err_db)
                await repo.update_status(
                    analysis_id,
                    AnalysisStatus.FAILED,
                    error_message=f"Analysis failed: {str(e)[:500]}",
                )
                await err_db.commit()


@router.get("/analysis/{analysis_id}", response_model=AnalysisJobResponse)
async def get_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnalysisService(db)
    return await service.get_analysis(analysis_id)


@router.get(
    "/analysis/{analysis_id}/participants",
    response_model=list[ParticipantResponse],
)
async def get_participants(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnalysisService(db)
    return await service.get_participants(analysis_id)


@router.get(
    "/analysis/{analysis_id}/timeline",
    response_model=list[TimelineBucket],
)
async def get_timeline(
    analysis_id: str,
    bucket_seconds: float = 5.0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnalysisService(db)
    return await service.get_timeline(analysis_id, bucket_seconds)


@router.get(
    "/analysis/{analysis_id}/observations",
    response_model=list[ObservationResponse],
)
async def get_observations(
    analysis_id: str,
    participant_id: str | None = None,
    limit: int = 1000,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnalysisService(db)
    return await service.get_observations(
        analysis_id, participant_id, limit, offset
    )


@router.get("/analysis/{analysis_id}/summary", response_model=AnalysisSummary)
async def get_summary(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnalysisService(db)
    return await service.get_summary(analysis_id)
