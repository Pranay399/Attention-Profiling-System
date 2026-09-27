"""
Feature Adapter: bridges dataset feature schema with real-time CV features.

The dataset has 37 features extracted from webcam video using:
- Face detection (face_present, no_of_face, face_x/y/w/h, face_conf)
- Facial landmarks (left_eye, right_eye, nose_tip, mouth coordinates)
- Hand tracking (hand_count, left/right_hand coords, hand_obj_interaction)
- Head pose estimation (head_pose category, pitch, yaw, roll)
- Phone detection (phone_present, phone_loc_x/y, phone_conf)
- Gaze tracking (gaze_on_screen, gaze_direction, gazePoint_x/y)
- Pupil tracking (pupil_left_x/y, pupil_right_x/y)

This adapter maps real-time CV pipeline outputs to the exact schema
the trained model expects.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class CVFeatures:
    """Raw features extracted from a single video frame by the CV pipeline."""
    # Face detection
    face_present: int = 0
    no_of_face: int = 0
    face_x: float = 0.0
    face_y: float = 0.0
    face_w: float = 0.0
    face_h: float = 0.0
    face_conf: float = 0.0

    # Facial landmarks
    left_eye_x: float = 0.0
    left_eye_y: float = 0.0
    right_eye_x: float = 0.0
    right_eye_y: float = 0.0
    nose_tip_x: float = 0.0
    nose_tip_y: float = 0.0
    mouth_x: float = 0.0
    mouth_y: float = 0.0

    # Hand tracking
    hand_count: int = 0
    left_hand_x: float = 0.0
    left_hand_y: float = 0.0
    right_hand_x: float = 0.0
    right_hand_y: float = 0.0
    hand_obj_interaction: int = 0

    # Head pose
    head_pose: str = "forward"
    head_pitch: float = 0.0
    head_yaw: float = 0.0
    head_roll: float = 0.0

    # Phone detection
    phone_present: int = 0
    phone_loc_x: int = 0
    phone_loc_y: int = 0
    phone_conf: float = 0.0

    # Gaze
    gaze_on_screen: int = 0
    gaze_direction: str = "center"
    gazePoint_x: int = 0
    gazePoint_y: int = 0

    # Pupil
    pupil_left_x: int = 0
    pupil_left_y: int = 0
    pupil_right_x: int = 0
    pupil_right_y: int = 0

    # Metadata (not features)
    timestamp: float = 0.0
    frame_number: int = 0
    extraction_confidence: float = 0.0


# Feature compatibility matrix
FEATURE_COMPATIBILITY = {
    # Dataset Feature       | Available | Real-time Method          | Confidence
    "face_present":         {"available": True,  "method": "MediaPipe Face Detection",   "confidence": "High"},
    "no_of_face":           {"available": True,  "method": "MediaPipe Face Detection",   "confidence": "High"},
    "face_x":               {"available": True,  "method": "MediaPipe Face Mesh bbox",   "confidence": "High"},
    "face_y":               {"available": True,  "method": "MediaPipe Face Mesh bbox",   "confidence": "High"},
    "face_w":               {"available": True,  "method": "MediaPipe Face Mesh bbox",   "confidence": "High"},
    "face_h":               {"available": True,  "method": "MediaPipe Face Mesh bbox",   "confidence": "High"},
    "face_conf":            {"available": True,  "method": "MediaPipe detection score",  "confidence": "High"},
    "left_eye_x":           {"available": True,  "method": "MediaPipe Face Mesh landmarks", "confidence": "High"},
    "left_eye_y":           {"available": True,  "method": "MediaPipe Face Mesh landmarks", "confidence": "High"},
    "right_eye_x":          {"available": True,  "method": "MediaPipe Face Mesh landmarks", "confidence": "High"},
    "right_eye_y":          {"available": True,  "method": "MediaPipe Face Mesh landmarks", "confidence": "High"},
    "nose_tip_x":           {"available": True,  "method": "MediaPipe Face Mesh landmarks", "confidence": "High"},
    "nose_tip_y":           {"available": True,  "method": "MediaPipe Face Mesh landmarks", "confidence": "High"},
    "mouth_x":              {"available": True,  "method": "MediaPipe Face Mesh landmarks", "confidence": "High"},
    "mouth_y":              {"available": True,  "method": "MediaPipe Face Mesh landmarks", "confidence": "High"},
    "hand_count":           {"available": True,  "method": "MediaPipe Hands",            "confidence": "High"},
    "left_hand_x":          {"available": True,  "method": "MediaPipe Hands landmarks",  "confidence": "Medium"},
    "left_hand_y":          {"available": True,  "method": "MediaPipe Hands landmarks",  "confidence": "Medium"},
    "right_hand_x":         {"available": True,  "method": "MediaPipe Hands landmarks",  "confidence": "Medium"},
    "right_hand_y":         {"available": True,  "method": "MediaPipe Hands landmarks",  "confidence": "Medium"},
    "hand_obj_interaction": {"available": True,  "method": "Phone-hand proximity heuristic", "confidence": "Medium"},
    "head_pose":            {"available": True,  "method": "PnP solver + MediaPipe landmarks", "confidence": "High"},
    "head_pitch":           {"available": True,  "method": "PnP solver rotation angles", "confidence": "High"},
    "head_yaw":             {"available": True,  "method": "PnP solver rotation angles", "confidence": "High"},
    "head_roll":            {"available": True,  "method": "PnP solver rotation angles", "confidence": "High"},
    "phone_present":        {"available": True,  "method": "YOLOv8-nano cell phone class", "confidence": "Medium"},
    "phone_loc_x":          {"available": True,  "method": "YOLO bbox center x",        "confidence": "Medium"},
    "phone_loc_y":          {"available": True,  "method": "YOLO bbox center y",        "confidence": "Medium"},
    "phone_conf":           {"available": True,  "method": "YOLO detection confidence",  "confidence": "Medium"},
    "gaze_on_screen":       {"available": True,  "method": "Gaze estimator from eye landmarks", "confidence": "Medium"},
    "gaze_direction":       {"available": True,  "method": "Gaze vector discretization", "confidence": "Medium"},
    "gazePoint_x":          {"available": True,  "method": "Gaze ray intersection estimate", "confidence": "Low"},
    "gazePoint_y":          {"available": True,  "method": "Gaze ray intersection estimate", "confidence": "Low"},
    "pupil_left_x":         {"available": True,  "method": "MediaPipe iris landmarks",   "confidence": "Medium"},
    "pupil_left_y":         {"available": True,  "method": "MediaPipe iris landmarks",   "confidence": "Medium"},
    "pupil_right_x":        {"available": True,  "method": "MediaPipe iris landmarks",   "confidence": "Medium"},
    "pupil_right_y":        {"available": True,  "method": "MediaPipe iris landmarks",   "confidence": "Medium"},
}

# Features in exact dataset column order
DATASET_FEATURE_ORDER = [
    "face_present", "no_of_face", "face_x", "face_y", "face_w", "face_h",
    "left_eye_x", "left_eye_y", "right_eye_x", "right_eye_y",
    "nose_tip_x", "nose_tip_y", "mouth_x", "mouth_y", "face_conf",
    "hand_count", "left_hand_x", "left_hand_y",
    "right_hand_x", "right_hand_y", "hand_obj_interaction",
    "head_pose", "head_pitch", "head_yaw", "head_roll",
    "phone_present", "phone_loc_x", "phone_loc_y", "phone_conf",
    "gaze_on_screen", "gaze_direction", "gazePoint_x", "gazePoint_y",
    "pupil_left_x", "pupil_left_y", "pupil_right_x", "pupil_right_y",
]


class FeatureAdapter:
    """
    Converts raw CV pipeline outputs (CVFeatures) into a pandas DataFrame
    with the exact same schema as the training dataset, ready for the
    preprocessing pipeline and model inference.
    """

    def __init__(self, feature_schema_path: Optional[str] = None):
        """
        Initialize the feature adapter.

        Args:
            feature_schema_path: Path to the feature_schema.json produced
                                 during training.
        """
        self.feature_order = DATASET_FEATURE_ORDER
        self.compatibility = FEATURE_COMPATIBILITY

        if feature_schema_path and Path(feature_schema_path).exists():
            with open(feature_schema_path) as f:
                self.schema = json.load(f)
            self.feature_order = self.schema["all_features"]
        else:
            self.schema = None

    def cv_features_to_dataframe(self, features: CVFeatures) -> pd.DataFrame:
        """
        Convert a CVFeatures object to a single-row DataFrame matching
        the training dataset schema.

        Args:
            features: CVFeatures extracted from a video frame.

        Returns:
            DataFrame with one row, columns matching the training schema.
        """
        row = {}
        for col in self.feature_order:
            val = getattr(features, col, None)
            if val is None:
                # Feature not available — use default
                if col in ("head_pose",):
                    val = "forward"
                elif col in ("gaze_direction",):
                    val = "center"
                else:
                    val = 0
            row[col] = val

        df = pd.DataFrame([row])
        return df

    def batch_to_dataframe(self, feature_list: list) -> pd.DataFrame:
        """Convert a list of CVFeatures to a DataFrame."""
        rows = []
        for features in feature_list:
            row = {}
            for col in self.feature_order:
                val = getattr(features, col, None)
                if val is None:
                    val = "forward" if col == "head_pose" else (
                        "center" if col == "gaze_direction" else 0
                    )
                row[col] = val
            rows.append(row)
        return pd.DataFrame(rows)

    def validate_features(self, features: CVFeatures) -> Dict[str, Any]:
        """
        Validate that extracted features are reasonable.
        Returns a dict with validation results.
        """
        issues = []
        confidence = 1.0

        # Face presence check
        if features.face_present == 0:
            issues.append("face_not_visible")
            confidence *= 0.1

        # Face confidence check
        if features.face_conf < 50.0 and features.face_present == 1:
            issues.append("low_face_confidence")
            confidence *= 0.5

        # Coordinate sanity checks (negative values for spatial coords)
        spatial_features = [
            "face_x", "face_y", "face_w", "face_h",
            "left_eye_x", "left_eye_y", "right_eye_x", "right_eye_y",
        ]
        for feat in spatial_features:
            val = getattr(features, feat, 0)
            if val < 0:
                issues.append(f"negative_{feat}")
                confidence *= 0.8

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "confidence": max(0.0, min(1.0, confidence)),
        }

    def get_compatibility_matrix(self) -> pd.DataFrame:
        """Return the feature compatibility matrix as a DataFrame."""
        rows = []
        for feature, info in self.compatibility.items():
            rows.append({
                "Dataset Feature": feature,
                "Available": "Yes" if info["available"] else "No",
                "Real-time Extraction Method": info["method"],
                "Confidence": info["confidence"],
            })
        return pd.DataFrame(rows)


def print_compatibility_matrix():
    """Print the compatibility matrix for documentation."""
    adapter = FeatureAdapter()
    matrix = adapter.get_compatibility_matrix()
    print("\nFEATURE COMPATIBILITY MATRIX")
    print("=" * 100)
    print(matrix.to_string(index=False))


if __name__ == "__main__":
    print_compatibility_matrix()
