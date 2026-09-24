"""
Head pose estimation using Perspective-n-Point (PnP).

Takes Face Mesh landmarks and estimates the 3D orientation of the head
(yaw, pitch, roll) using OpenCV's solvePnP with a generic 3D face model.
"""

from dataclasses import dataclass

import cv2
import numpy as np

from app.pipeline.face_detector import DetectedFace


@dataclass
class HeadPose:
    """Estimated head orientation in degrees."""
    yaw: float    # left/right rotation (negative = left, positive = right)
    pitch: float  # up/down rotation (negative = down, positive = up)
    roll: float   # tilt (negative = tilt left, positive = tilt right)


# 3D model points for a generic face.
# These correspond to the 5 YOLO facial keypoints (Nose, L_Eye, R_Eye, L_Ear, R_Ear).
# Selected for being anatomically stable and spread across the face.
_LANDMARK_INDICES = {
    "nose": 0,
    "left_eye": 1,
    "right_eye": 2,
    "left_ear": 3,
    "right_ear": 4,
}

# Approximate 3D coordinates of these landmarks on a generic face model.
# Units are arbitrary but proportionally correct.
_MODEL_POINTS_3D = np.array([
    (0.0, 0.0, 0.0),         # nose tip (origin)
    (-43.3, 32.7, -26.0),    # left eye
    (43.3, 32.7, -26.0),     # right eye
    (-75.0, 40.0, -80.0),    # left ear
    (75.0, 40.0, -80.0),     # right ear
], dtype=np.float64)


class HeadPoseEstimator:
    """
    Estimates head pose from Face Mesh landmarks using solvePnP.

    The estimation uses 6 stable facial landmarks mapped to a generic
    3D face model. This is a well-established technique that works
    reliably for frontal and moderate-angle face views.

    Limitations:
    - Accuracy degrades at extreme angles (>60°)
    - Assumes a generic face shape (no per-person calibration)
    """

    def estimate(self, face: DetectedFace) -> HeadPose:
        """
        Estimate head pose for a detected face.

        Args:
            face: A DetectedFace with landmarks.

        Returns:
            HeadPose with yaw, pitch, roll in degrees.
        """
        # Extract the 5 key landmarks in pixel coordinates
        pixel_landmarks = face.get_pixel_landmarks()
        image_points = pixel_landmarks[:5, :2].astype(np.float64)

        # Camera intrinsic parameters (approximate using image dimensions)
        focal_length = face.image_width
        center = (face.image_width / 2, face.image_height / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1],
        ], dtype=np.float64)

        # No lens distortion assumed
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        # Solve PnP
        success, rotation_vector, translation_vector = cv2.solvePnP(
            _MODEL_POINTS_3D,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_SQPNP,
        )

        if not success:
            # Return neutral pose if solvePnP fails
            return HeadPose(yaw=0.0, pitch=0.0, roll=0.0)

        # Convert rotation vector to rotation matrix, then to Euler angles
        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
        euler_angles = self._rotation_matrix_to_euler(rotation_matrix)

        return HeadPose(
            yaw=round(float(euler_angles[1]), 1),
            pitch=round(float(euler_angles[0]), 1),
            roll=round(float(euler_angles[2]), 1),
        )

    @staticmethod
    def _rotation_matrix_to_euler(R: np.ndarray) -> np.ndarray:
        """
        Convert a 3x3 rotation matrix to Euler angles (pitch, yaw, roll)
        in degrees using the ZYX convention.
        """
        sy = np.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)
        singular = sy < 1e-6

        if not singular:
            pitch = np.arctan2(R[2, 1], R[2, 2])
            yaw = np.arctan2(-R[2, 0], sy)
            roll = np.arctan2(R[1, 0], R[0, 0])
        else:
            pitch = np.arctan2(-R[1, 2], R[1, 1])
            yaw = np.arctan2(-R[2, 0], sy)
            roll = 0.0

        return np.degrees(np.array([pitch, yaw, roll]))
