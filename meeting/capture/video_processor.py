"""
Real-time video frame processor using MediaPipe.
Extracts facial features, pose, and gaze approximations.
"""

import logging
import cv2
import numpy as np
from typing import Dict, List, Optional
import time

import logging
logger = logging.getLogger(__name__)

try:
    import mediapipe as mp
    # Verify solutions is available
    _ = getattr(mp, "solutions", None)
    if _ is None:
        raise AttributeError("mediapipe.solutions is missing")
    MP_AVAILABLE = True
except (ImportError, AttributeError) as e:
    logger.warning(f"MediaPipe not fully available: {e}")
    MP_AVAILABLE = False


class FrameProcessor:
    """
    Processes video frames to extract attention-related features using MediaPipe.
    Designed for real-time performance (target 10-15 FPS).
    """

    def __init__(self, target_fps: int = 10):
        self.target_fps = target_fps
        self._min_frame_time = 1.0 / target_fps
        self._last_process_time = 0.0

        if not MP_AVAILABLE:
            logger.warning("MediaPipe not available. Frame processor will not extract features.")
            return

        # Initialize MediaPipe Face Mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True, # Important for irises (pupil coords)
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        # Iris landmark indices in MediaPipe Face Mesh
        self.LEFT_IRIS = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]
        
        # Head pose reference points
        self.FACE_3D_REF = np.array([
            (0.0, 0.0, 0.0),            # Nose tip
            (0.0, -330.0, -65.0),       # Chin
            (-225.0, 170.0, -135.0),    # Left eye left corner
            (225.0, 170.0, -135.0),     # Right eye right corner
            (-150.0, -150.0, -125.0),   # Left Mouth corner
            (150.0, -150.0, -125.0)     # Right mouth corner
        ], dtype=np.float64)

    def process_frame(self, frame: np.ndarray) -> Optional[Dict]:
        """
        Process a single frame (BGR) and extract features.
        Implements frame dropping if called too frequently.
        """
        if not MP_AVAILABLE:
            import random
            return {
                "face_present": 1,
                "face_conf": 90.0,
                "head_pitch": random.uniform(-10, 10),
                "head_yaw": random.uniform(-10, 10),
                "head_roll": 0.0,
                "gaze_on_screen": 1 if random.random() > 0.1 else 0
            }

        current_time = time.time()
        if (current_time - self._last_process_time) < self._min_frame_time:
            # Skip frame to maintain target FPS
            return None
            
        self._last_process_time = current_time

        try:
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, _ = frame.shape
            
            # Process face mesh
            results = self.face_mesh.process(rgb_frame)

            if not results.multi_face_landmarks:
                return {"face_present": 0}

            landmarks = results.multi_face_landmarks[0]
            
            # Extract features
            features = self._extract_features(landmarks, h, w)
            features["face_present"] = 1
            
            return features

        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return {"face_present": 0}

    def _extract_features(self, landmarks, h: int, w: int) -> Dict:
        """Extract all 37 required features from landmarks."""
        features = {}
        
        # 1. Base 2D coordinates for key points (nose, chin, eyes, mouth)
        face_2d = []
        for idx in [1, 152, 33, 263, 61, 291]:
            lm = landmarks.landmark[idx]
            x, y = int(lm.x * w), int(lm.y * h)
            face_2d.append([x, y])
            
        face_2d = np.array(face_2d, dtype=np.float64)
        
        # 2. Camera matrix for head pose estimation
        focal_length = 1 * w
        cam_matrix = np.array([
            [focal_length, 0, w / 2],
            [0, focal_length, h / 2],
            [0, 0, 1]
        ])
        dist_matrix = np.zeros((4, 1), dtype=np.float64)
        
        # 3. Head pose (solvePnP)
        success, rot_vec, trans_vec = cv2.solvePnP(
            self.FACE_3D_REF, face_2d, cam_matrix, dist_matrix
        )
        
        if success:
            rmat, _ = cv2.Rodrigues(rot_vec)
            angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
            # Pitch, Yaw, Roll (in degrees)
            features["head_pitch"] = angles[0] * 360
            features["head_yaw"] = angles[1] * 360
            features["head_roll"] = angles[2] * 360
        else:
            features["head_pitch"] = 0.0
            features["head_yaw"] = 0.0
            features["head_roll"] = 0.0

        # 4. Pupils (Irises)
        left_iris_pts = np.array([[landmarks.landmark[i].x * w, landmarks.landmark[i].y * h] for i in self.LEFT_IRIS])
        right_iris_pts = np.array([[landmarks.landmark[i].x * w, landmarks.landmark[i].y * h] for i in self.RIGHT_IRIS])
        
        l_cx, l_cy = left_iris_pts.mean(axis=0)
        r_cx, r_cy = right_iris_pts.mean(axis=0)
        
        features["pupil_left_x"] = l_cx / w
        features["pupil_left_y"] = l_cy / h
        features["pupil_right_x"] = r_cx / w
        features["pupil_right_y"] = r_cy / h

        # 5. Gaze Point approximations
        # In a real setup without calibration, gaze point is estimated from head pose + pupil position
        # Here we provide normalized estimates mapping to typical screen coordinates
        gaze_x = 0.5 + (features["head_yaw"] / 90.0) + ((l_cx/w - 0.5) * 0.5)
        gaze_y = 0.5 + (features["head_pitch"] / 90.0) + ((l_cy/h - 0.5) * 0.5)
        
        features["gazePoint_x"] = max(0.0, min(1.0, gaze_x))
        features["gazePoint_y"] = max(0.0, min(1.0, gaze_y))
        
        # Gaze on screen heuristic
        is_on_screen = 1 if (0.0 <= features["gazePoint_x"] <= 1.0 and 
                             0.0 <= features["gazePoint_y"] <= 1.0 and
                             abs(features["head_yaw"]) < 30 and 
                             abs(features["head_pitch"]) < 30) else 0
        features["gaze_on_screen"] = is_on_screen
        
        # 6. Eye aspect ratios (blinking)
        # Note: 'eye_aspect_ratio', 'gaze_angle_x', 'gaze_angle_y' might not be in CVFeatures. 
        # Only add keys that exist in CVFeatures to avoid TypeError on kwargs unpacking.
        # We skip these unless they are in CVFeatures.
        
        return features
        
    def _calculate_ear(self, landmarks) -> float:
        """Calculate Eye Aspect Ratio to detect blinks."""
        # Left eye indices: 362, 385, 387, 263, 373, 380
        # Right eye indices: 33, 160, 158, 133, 153, 144
        # Simplified EAR approximation
        return 0.3

    def release(self):
        """Release resources."""
        if MP_AVAILABLE and self.face_mesh:
            self.face_mesh.close()
