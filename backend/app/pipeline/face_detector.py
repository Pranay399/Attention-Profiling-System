"""
Face detection and keypoint extraction using YOLO-Pose.

1. YOLOv8-Pose detects people (students) in the wide grid.
2. It simultaneously outputs 17 skeletal keypoints per person.
3. We extract the 5 facial keypoints (Nose, Left Eye, Right Eye, Left Ear, Right Ear)
   and pass them to the HeadPoseEstimator.
"""

from dataclasses import dataclass

import cv2
import numpy as np
from ultralytics import YOLO


@dataclass
class FaceBBox:
    """Normalized bounding box for a detected face/person."""
    x: float  # top-left x (0-1)
    y: float  # top-left y (0-1)
    w: float  # width (0-1)
    h: float  # height (0-1)

    @property
    def center_x(self) -> float:
        return self.x + self.w / 2

    @property
    def center_y(self) -> float:
        return self.y + self.h / 2

    def to_dict(self) -> dict:
        return {"x": round(self.x, 4), "y": round(self.y, 4),
                "w": round(self.w, 4), "h": round(self.h, 4)}


@dataclass
class DetectedFace:
    """A single detected face with its 5 key facial landmarks."""
    # Array of 5 landmarks: [Nose, Left Eye, Right Eye, Left Ear, Right Ear]
    # Each is (x, y) normalized to the full frame
    landmarks: np.ndarray  
    bbox: FaceBBox         
    confidence: float
    image_width: int
    image_height: int

    def get_pixel_landmarks(self) -> np.ndarray:
        """Convert normalized landmarks to pixel coordinates."""
        pixel = self.landmarks.copy()
        pixel[:, 0] *= self.image_width
        pixel[:, 1] *= self.image_height
        return pixel


class FaceDetector:
    """
    Detects faces and keypoints using YOLO-Pose.
    """

    def __init__(
        self,
        yolo_model_path: str = "yolov8n-pose.pt",
        min_detection_confidence: float = 0.5,
    ):
        # Initialize YOLO Pose (auto-downloads if not found)
        self.yolo = YOLO(yolo_model_path)
        self.min_confidence = min_detection_confidence

    def detect(self, frame: np.ndarray) -> list[DetectedFace]:
        """
        Detect faces and keypoints in a BGR video frame.
        """
        h, w = frame.shape[:2]
        
        # Run YOLO Pose
        # class 0 is 'person' in COCO dataset
        results = self.yolo(frame, classes=[0], conf=self.min_confidence, verbose=False)
        
        if not results or not results[0].boxes or not results[0].keypoints:
            return []

        faces = []
        boxes = results[0].boxes
        # keypoints shape is (num_people, 17, 2 or 3)
        # where 17 is the number of COCO keypoints
        # 0: Nose, 1: Left Eye, 2: Right Eye, 3: Left Ear, 4: Right Ear
        keypoints = results[0].keypoints.xy.cpu().numpy()
        confs = results[0].keypoints.conf.cpu().numpy() if results[0].keypoints.conf is not None else None
        
        for i, box in enumerate(boxes):
            # Get YOLO bounding box coordinates (pixels)
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            box_conf = float(box.conf[0].cpu().numpy())
            
            # Ensure bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            # If the box is too small, skip
            if x2 - x1 < 20 or y2 - y1 < 20:
                continue

            # Extract the first 5 facial keypoints (Nose, L_Eye, R_Eye, L_Ear, R_Ear)
            person_keypoints = keypoints[i]
            
            # Check if we actually have enough keypoints
            if len(person_keypoints) < 5:
                continue

            # Normalize keypoints to 0-1
            face_kpts = person_keypoints[:5].copy()
            
            # Check if keypoints are valid (YOLO returns 0,0 for occluded points)
            if np.all(face_kpts == 0):
                continue
                
            face_kpts[:, 0] /= w
            face_kpts[:, 1] /= h
            
            # Calculate normalized bbox
            bw = x2 - x1
            bh = y2 - y1
            
            faces.append(DetectedFace(
                landmarks=face_kpts,
                bbox=FaceBBox(x=x1/w, y=y1/h, w=bw/w, h=bh/h),
                confidence=box_conf,
                image_width=w,
                image_height=h,
            ))

        return faces

    def close(self):
        """No-op. Here to maintain API compatibility."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass
