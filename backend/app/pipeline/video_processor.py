"""
Video processor — orchestrates the full CV pipeline.

Workflow:
1. Open video file with OpenCV
2. Sample frames at the configured rate
3. For each sampled frame:
   a. Detect faces
   b. Track faces across frames
   c. Estimate head pose per face
   d. Classify behavior per face
4. Batch-write observations to the database
5. Update analysis job progress throughout

This runs in a background task, not in the request thread.
It uses its own database session.
"""

import asyncio
from datetime import datetime, timezone

import cv2

from app.core.config import settings
from app.core.logging import get_logger
from app.models.analysis import (
    AnalysisJob,
    AnalysisStatus,
    BehaviorType,
    DetectedParticipant,
    Observation,
)
from app.pipeline.behavior_classifier import BehaviorClassifier
from app.pipeline.face_detector import FaceDetector
from app.pipeline.face_tracker import FaceTracker
from app.pipeline.head_pose_estimator import HeadPoseEstimator
from app.repositories.repository import AnalysisRepository, RecordingRepository
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger("pipeline")

# How many observations to batch before writing to DB
_BATCH_SIZE = 100


class VideoProcessor:
    """
    Processes a video recording through the full CV pipeline.

    This class is instantiated per analysis job. It coordinates:
    - FaceDetector (MediaPipe)
    - FaceTracker (centroid-based)
    - HeadPoseEstimator (solvePnP)
    - BehaviorClassifier (rule-based)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.analysis_repo = AnalysisRepository(db)
        self.recording_repo = RecordingRepository(db)

    async def process(self, analysis_id: str, recording_id: str) -> None:
        """
        Run the full pipeline for an analysis job.

        Updates the job status and progress in the database as it runs.
        """
        logger.info("pipeline_start", analysis_id=analysis_id, recording_id=recording_id)

        # Load the recording to get the file path
        recording = await self.recording_repo.get_by_id(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        # Mark as processing
        await self.analysis_repo.update_status(
            analysis_id,
            AnalysisStatus.PROCESSING,
            started_at=datetime.now(timezone.utc),
        )
        await self.db.commit()

        # Open video
        cap = cv2.VideoCapture(recording.file_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {recording.file_path}")

        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0

            # Update recording duration if not set
            if not recording.duration_seconds:
                recording.duration_seconds = round(duration, 2)
                await self.db.flush()

            # Calculate frame sampling
            sample_interval = int(fps / settings.frame_sample_rate) if settings.frame_sample_rate > 0 else 1
            sample_interval = max(1, sample_interval)
            frames_to_process = total_frames // sample_interval

            await self.analysis_repo.update_status(
                analysis_id,
                AnalysisStatus.PROCESSING,
                frames_total=frames_to_process,
            )
            await self.db.commit()

            logger.info(
                "video_info",
                analysis_id=analysis_id,
                fps=fps,
                total_frames=total_frames,
                duration_sec=round(duration, 1),
                sample_interval=sample_interval,
                frames_to_process=frames_to_process,
            )

            # Initialize pipeline components
            detector = FaceDetector(
                max_faces=10,
                min_detection_confidence=settings.face_detection_confidence,
                min_tracking_confidence=settings.face_mesh_confidence,
            )
            tracker = FaceTracker(max_distance=0.15, max_missing_frames=10)
            pose_estimator = HeadPoseEstimator()
            classifier = BehaviorClassifier(
                yaw_threshold=settings.yaw_threshold,
                pitch_threshold=settings.pitch_threshold,
            )

            # Track ID → participant DB ID mapping
            track_to_participant: dict[int, str] = {}
            # Buffer for batch DB writes
            observation_buffer: list[dict] = []
            frames_processed = 0

            try:
                frame_number = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # Only process sampled frames
                    if frame_number % sample_interval != 0:
                        frame_number += 1
                        continue

                    timestamp_sec = frame_number / fps

                    # Step 1: Detect faces
                    faces = detector.detect(frame)

                    # Step 2: Track faces across frames
                    tracked = tracker.update(faces, timestamp_sec)

                    # Step 3 & 4: Estimate pose and classify for each tracked face
                    for track_id, face in tracked.items():
                        # Ensure this track has a participant record
                        if track_id not in track_to_participant:
                            participant = DetectedParticipant(
                                analysis_id=analysis_id,
                                label=f"Participant {track_id}",
                                first_seen_sec=timestamp_sec,
                                last_seen_sec=timestamp_sec,
                                frame_count=0,
                            )
                            self.db.add(participant)
                            await self.db.flush()
                            track_to_participant[track_id] = participant.id

                        participant_id = track_to_participant[track_id]

                        # Estimate head pose
                        pose = pose_estimator.estimate(face)

                        # Classify behavior
                        result = classifier.classify(pose, face.confidence)

                        observation_buffer.append({
                            "analysis_id": analysis_id,
                            "participant_id": participant_id,
                            "timestamp_sec": round(timestamp_sec, 3),
                            "frame_number": frame_number,
                            "behavior": result.behavior,
                            "head_yaw": result.head_yaw,
                            "head_pitch": result.head_pitch,
                            "head_roll": result.head_roll,
                            "confidence": round(result.confidence, 4),
                            "face_bbox": face.bbox.to_dict(),
                        })

                        # Update participant last_seen and frame_count
                        p = await self.db.get(DetectedParticipant, participant_id)
                        if p:
                            p.last_seen_sec = timestamp_sec
                            p.frame_count += 1

                    # Batch write observations
                    if len(observation_buffer) >= _BATCH_SIZE:
                        await self._flush_observations(observation_buffer)
                        observation_buffer.clear()

                    frames_processed += 1

                    # Update progress periodically (every 50 frames)
                    if frames_processed % 50 == 0:
                        await self.analysis_repo.update_progress(
                            analysis_id, frames_processed
                        )
                        await self.db.commit()
                        logger.debug(
                            "pipeline_progress",
                            analysis_id=analysis_id,
                            frames_processed=frames_processed,
                            frames_total=frames_to_process,
                        )

                    frame_number += 1

                    # Yield control to event loop periodically
                    if frames_processed % 10 == 0:
                        await asyncio.sleep(0)

            finally:
                detector.close()

            # Flush remaining observations
            if observation_buffer:
                await self._flush_observations(observation_buffer)
                observation_buffer.clear()

            # Mark as completed
            await self.analysis_repo.update_status(
                analysis_id,
                AnalysisStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc),
            )
            await self.analysis_repo.update_progress(analysis_id, frames_processed)
            await self.db.commit()

            logger.info(
                "pipeline_complete",
                analysis_id=analysis_id,
                frames_processed=frames_processed,
                participants_found=len(track_to_participant),
            )

        finally:
            cap.release()

    async def _flush_observations(self, buffer: list[dict]) -> None:
        """Write a batch of observations to the database."""
        observations = [
            Observation(**data)
            for data in buffer
        ]
        await self.analysis_repo.bulk_create_observations(observations)
        await self.db.flush()
