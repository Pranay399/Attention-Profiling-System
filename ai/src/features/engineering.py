import numpy as np
import pandas as pd

def compute_eye_aspect_ratio(eye_points):
    """
    Computes the Eye Aspect Ratio (EAR) given a set of 6 eye landmarks.
    EAR is commonly used to detect blinking or drowsiness.
    """
    if not eye_points or len(eye_points) < 6:
        return 0.0

    # compute the euclidean distances between the two sets of vertical eye landmarks
    A = np.linalg.norm(np.array(eye_points[1]) - np.array(eye_points[5]))
    B = np.linalg.norm(np.array(eye_points[2]) - np.array(eye_points[4]))

    # compute the euclidean distance between the horizontal eye landmark (x, y)-coordinates
    C = np.linalg.norm(np.array(eye_points[0]) - np.array(eye_points[3]))

    # compute the eye aspect ratio
    ear = (A + B) / (2.0 * C)
    return ear


def compute_head_pose_deviation(pitch, yaw, roll, baseline=(0, 0, 0)):
    """
    Computes the absolute deviation of the head pose from a neutral baseline.
    """
    return np.sqrt((pitch - baseline[0])**2 + (yaw - baseline[1])**2 + (roll - baseline[2])**2)


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds derived spatial and contextual features to the dataset.
    This is useful for augmenting the base feature set before passing to the model.
    """
    df = df.copy()

    # 1. Total Head Movement Deviation (Assuming neutral is 0,0,0)
    if all(col in df.columns for col in ["head_pitch", "head_yaw", "head_roll"]):
        df["head_pose_deviation"] = np.sqrt(
            df["head_pitch"]**2 + df["head_yaw"]**2 + df["head_roll"]**2
        )

    # 2. Distraction index (Proxy logic combining phone presence and gaze)
    if "phone_present" in df.columns and "gaze_on_screen" in df.columns:
        # High distraction if phone is present and gaze is off screen
        df["distraction_index"] = (df["phone_present"] == 1) & (df["gaze_on_screen"] == 0)
        df["distraction_index"] = df["distraction_index"].astype(int)

    return df
