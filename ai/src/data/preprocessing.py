"""
Preprocessing pipeline for the Students Attention Detection Dataset v3.
Builds a reusable sklearn Pipeline that is saved alongside the model.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder
from sklearn.model_selection import train_test_split
import joblib

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATASET_PATH = DATA_DIR / "attention_detection_dataset_v3.csv"
SPLITS_DIR = DATA_DIR / "splits"
PIPELINE_DIR = DATA_DIR / "pipelines"

# Feature schema — derived from actual dataset inspection
FEATURE_SCHEMA = {
    "face_features": [
        "face_present", "no_of_face", "face_x", "face_y",
        "face_w", "face_h", "face_conf"
    ],
    "landmark_features": [
        "left_eye_x", "left_eye_y", "right_eye_x", "right_eye_y",
        "nose_tip_x", "nose_tip_y", "mouth_x", "mouth_y"
    ],
    "hand_features": [
        "hand_count", "left_hand_x", "left_hand_y",
        "right_hand_x", "right_hand_y", "hand_obj_interaction"
    ],
    "head_pose_features": [
        "head_pose",  # categorical
        "head_pitch", "head_yaw", "head_roll"
    ],
    "phone_features": [
        "phone_present", "phone_loc_x", "phone_loc_y", "phone_conf"
    ],
    "gaze_features": [
        "gaze_on_screen", "gaze_direction",  # gaze_direction is categorical
        "gazePoint_x", "gazePoint_y"
    ],
    "pupil_features": [
        "pupil_left_x", "pupil_left_y",
        "pupil_right_x", "pupil_right_y"
    ],
}

TARGET_COL = "label"

NUMERICAL_FEATURES = [
    "face_present", "no_of_face", "face_x", "face_y", "face_w", "face_h",
    "left_eye_x", "left_eye_y", "right_eye_x", "right_eye_y",
    "nose_tip_x", "nose_tip_y", "mouth_x", "mouth_y", "face_conf",
    "hand_count", "left_hand_x", "left_hand_y",
    "right_hand_x", "right_hand_y", "hand_obj_interaction",
    "head_pitch", "head_yaw", "head_roll",
    "phone_present", "phone_loc_x", "phone_loc_y", "phone_conf",
    "gaze_on_screen", "gazePoint_x", "gazePoint_y",
    "pupil_left_x", "pupil_left_y", "pupil_right_x", "pupil_right_y",
]

CATEGORICAL_FEATURES = [
    "head_pose",
    "gaze_direction",
]

ALL_FEATURES = NUMERICAL_FEATURES + CATEGORICAL_FEATURES


def load_dataset():
    """Load raw dataset."""
    df = pd.read_csv(DATASET_PATH)
    return df


def build_preprocessing_pipeline():
    """
    Build a sklearn ColumnTransformer that handles:
    - StandardScaler for numerical features
    - OneHotEncoder for categorical features (head_pose, gaze_direction)
    """
    numerical_transformer = Pipeline(steps=[
        ("scaler", StandardScaler()),
    ])

    categorical_transformer = Pipeline(steps=[
        ("encoder", OneHotEncoder(handle_unknown="infrequent_if_exist",
                                   sparse_output=False, drop="first")),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numerical_transformer, NUMERICAL_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ],
        remainder="drop",  # Drop any columns not in our feature list
    )

    return preprocessor


def split_dataset(df, random_state=42):
    """
    Split dataset into train/val/test (70/15/15).

    The dataset has NO participant/session ID columns, so we cannot do
    subject-aware splitting. We use stratified random splitting instead.
    This is documented as a known limitation.
    """
    X = df[ALL_FEATURES]
    y = df[TARGET_COL]

    # First split: 70% train, 30% temp
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=random_state, stratify=y
    )

    # Second split: 50/50 on temp → 15% val, 15% test
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=random_state, stratify=y_temp
    )

    print(f"Split sizes:")
    print(f"  Train: {len(X_train)} ({len(X_train)/len(df)*100:.1f}%)")
    print(f"  Val:   {len(X_val)} ({len(X_val)/len(df)*100:.1f}%)")
    print(f"  Test:  {len(X_test)} ({len(X_test)/len(df)*100:.1f}%)")

    print(f"\nClass distribution:")
    for name, ys in [("Train", y_train), ("Val", y_val), ("Test", y_test)]:
        dist = ys.value_counts(normalize=True)
        print(f"  {name}: class 0={dist.get(0,0):.3f}, class 1={dist.get(1,0):.3f}")

    return X_train, X_val, X_test, y_train, y_val, y_test


def save_splits(X_train, X_val, X_test, y_train, y_val, y_test):
    """Save data splits to disk."""
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)

    X_train.to_csv(SPLITS_DIR / "X_train.csv", index=False)
    X_val.to_csv(SPLITS_DIR / "X_val.csv", index=False)
    X_test.to_csv(SPLITS_DIR / "X_test.csv", index=False)
    y_train.to_csv(SPLITS_DIR / "y_train.csv", index=False)
    y_val.to_csv(SPLITS_DIR / "y_val.csv", index=False)
    y_test.to_csv(SPLITS_DIR / "y_test.csv", index=False)
    print(f"\nSplits saved to {SPLITS_DIR}")


def save_pipeline(preprocessor, path=None):
    """Save fitted preprocessing pipeline."""
    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    path = path or PIPELINE_DIR / "preprocessing_pipeline.joblib"
    joblib.dump(preprocessor, path)
    print(f"Pipeline saved to {path}")


def save_feature_schema():
    """Save the feature schema for the feature adapter."""
    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    schema = {
        "version": "v1",
        "dataset": "Students Attention Detection Dataset v3",
        "target": TARGET_COL,
        "numerical_features": NUMERICAL_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "all_features": ALL_FEATURES,
        "feature_groups": {k: v for k, v in FEATURE_SCHEMA.items()},
    }
    path = PIPELINE_DIR / "feature_schema.json"
    with open(path, "w") as f:
        json.dump(schema, f, indent=2)
    print(f"Feature schema saved to {path}")


def main():
    print("=" * 70)
    print("PREPROCESSING PIPELINE")
    print("=" * 70)

    # Load
    df = load_dataset()
    print(f"Loaded {len(df)} rows")

    # Split
    X_train, X_val, X_test, y_train, y_val, y_test = split_dataset(df)

    # Build and fit preprocessor
    preprocessor = build_preprocessing_pipeline()
    X_train_processed = preprocessor.fit_transform(X_train)
    X_val_processed = preprocessor.transform(X_val)
    X_test_processed = preprocessor.transform(X_test)

    print(f"\nProcessed feature dimensions:")
    print(f"  Train: {X_train_processed.shape}")
    print(f"  Val:   {X_val_processed.shape}")
    print(f"  Test:  {X_test_processed.shape}")

    # Get feature names after encoding
    feature_names = preprocessor.get_feature_names_out()
    print(f"\nTotal features after preprocessing: {len(feature_names)}")
    print(f"Feature names: {list(feature_names)}")

    # Save everything
    save_splits(X_train, X_val, X_test, y_train, y_val, y_test)
    save_pipeline(preprocessor)
    save_feature_schema()

    return preprocessor, X_train_processed, X_val_processed, X_test_processed, y_train, y_val, y_test


if __name__ == "__main__":
    main()
