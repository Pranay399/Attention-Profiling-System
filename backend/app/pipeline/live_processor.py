"""
Live processor — orchestrates the real-time CV pipeline.

Workflow:
1. Capture screen using mss
2. Detect faces using YOLO + MediaPipe
3. Track identities
4. Estimate pose and classify behavior
5. Push results via callback (WebSockets)
"""

import time
import numpy as np

from app.core.config import settings
from app.core.logging import get_logger
from app.pipeline.behavior_classifier import BehaviorClassifier
from app.pipeline.face_detector import FaceDetector
from app.pipeline.face_tracker import FaceTracker
from app.pipeline.head_pose_estimator import HeadPoseEstimator

logger = get_logger("live_pipeline")


class LiveProcessor:
    """
    Processes single video frames through the CV pipeline and maintains tracking state.
    """

    def __init__(self):
        # Initialize pipeline components
        self.detector = FaceDetector(
            min_detection_confidence=settings.face_detection_confidence,
        )
        self.tracker = FaceTracker(max_distance=0.20, max_missing_frames=15)
        self.pose_estimator = HeadPoseEstimator()
        self.classifier = BehaviorClassifier(
            yaw_threshold=settings.yaw_threshold,
            pitch_threshold=settings.pitch_threshold,
        )

    def process_frame(self, frame: np.ndarray, timestamp_sec: float) -> list[dict]:
        """
        Process a single BGR frame, returning a list of observations.
        """
        try:
            # 1. Detect faces (YOLO + MediaPipe)
            faces = self.detector.detect(frame)

            # 2. Track faces
            tracked = self.tracker.update(faces, timestamp_sec)

            observations = []
            
            # 3 & 4. Estimate pose & classify
            for track_id, face in tracked.items():
                pose = self.pose_estimator.estimate(face)
                result = self.classifier.classify(pose, face.confidence)
                
                observations.append({
                    "participant_id": str(track_id),
                    "label": f"Student {track_id}",
                    "timestamp_sec": round(timestamp_sec, 3),
                    "behavior": result.behavior,
                    "head_yaw": result.head_yaw,
                    "head_pitch": result.head_pitch,
                    "head_roll": result.head_roll,
                    "confidence": round(result.confidence, 4),
                    "face_bbox": face.bbox.to_dict(),
                })

            return observations
        except Exception as e:
            logger.error("frame_processing_error", error=str(e), exc_info=True)
            return []

    def close(self):
        """Release underlying model resources."""
        self.detector.close()
