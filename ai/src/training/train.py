"""
Training pipeline for the Student Attention Classification models.
Trains: Logistic Regression, Random Forest, XGBoost, MLP.
Compares all models and selects the best based on macro F1 + inference latency.
Logs everything to MLflow.
"""

import time
import json
import warnings
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import joblib
import mlflow
import mlflow.sklearn
import mlflow.xgboost

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
)
from sklearn.model_selection import GridSearchCV

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("WARNING: xgboost not installed")

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data.preprocessing import (
    load_dataset, build_preprocessing_pipeline, split_dataset,
    save_pipeline, save_feature_schema,
    NUMERICAL_FEATURES, CATEGORICAL_FEATURES, ALL_FEATURES, TARGET_COL,
)
from evaluation.metrics import evaluate_model, print_metrics

warnings.filterwarnings("ignore", category=UserWarning)

# Paths
AI_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = AI_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR = AI_DIR / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
MLFLOW_DIR = AI_DIR / "mlflow"




def get_model_size_kb(model, path=None):
    """Get model size in KB."""
    import tempfile
    if path is None:
        path = Path(tempfile.mktemp(suffix=".joblib"))
    joblib.dump(model, path)
    size_kb = path.stat().st_size / 1024
    if "tmp" in str(path):
        path.unlink()
    return size_kb


def train_logistic_regression(X_train, y_train, X_val, y_val):
    """Train Logistic Regression baseline."""
    print("\n" + "=" * 60)
    print("MODEL 1: Logistic Regression (Baseline)")
    print("=" * 60)

    model = LogisticRegression(
        max_iter=1000,
        random_state=42,
        class_weight="balanced",
        solver="lbfgs",
        C=1.0,
    )
    model.fit(X_train, y_train)

    val_metrics = evaluate_model(model, X_val, y_val, "validation")
    print_metrics(val_metrics, "LogisticRegression")

    return model, val_metrics


def train_random_forest(X_train, y_train, X_val, y_val):
    """Train Random Forest with basic hyperparameter tuning."""
    print("\n" + "=" * 60)
    print("MODEL 2: Random Forest")
    print("=" * 60)

    # Quick grid search on validation-relevant params
    param_grid = {
        "n_estimators": [100, 200],
        "max_depth": [10, 20, None],
        "min_samples_split": [2, 5],
    }

    rf = RandomForestClassifier(
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )

    grid = GridSearchCV(
        rf, param_grid, cv=3, scoring="f1_macro",
        n_jobs=-1, verbose=0,
    )
    grid.fit(X_train, y_train)

    model = grid.best_estimator_
    print(f"  Best params: {grid.best_params_}")

    val_metrics = evaluate_model(model, X_val, y_val, "validation")
    print_metrics(val_metrics, "RandomForest")

    return model, val_metrics


def train_xgboost(X_train, y_train, X_val, y_val):
    """Train XGBoost gradient boosting model."""
    print("\n" + "=" * 60)
    print("MODEL 3: XGBoost")
    print("=" * 60)

    if not HAS_XGBOOST:
        print("  SKIPPED: xgboost not available")
        return None, None

    # Compute scale_pos_weight for imbalanced classes
    n_pos = (y_train == 1).sum()
    n_neg = (y_train == 0).sum()
    scale_pos_weight = n_neg / n_pos

    param_grid = {
        "n_estimators": [100, 200],
        "max_depth": [4, 6, 8],
        "learning_rate": [0.05, 0.1],
    }

    xgb = XGBClassifier(
        random_state=42,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        use_label_encoder=False,
        n_jobs=-1,
    )

    grid = GridSearchCV(
        xgb, param_grid, cv=3, scoring="f1_macro",
        n_jobs=-1, verbose=0,
    )
    grid.fit(X_train, y_train)

    model = grid.best_estimator_
    print(f"  Best params: {grid.best_params_}")

    val_metrics = evaluate_model(model, X_val, y_val, "validation")
    print_metrics(val_metrics, "XGBoost")

    return model, val_metrics


def train_mlp(X_train, y_train, X_val, y_val):
    """Train MLP neural network."""
    print("\n" + "=" * 60)
    print("MODEL 4: MLP (Neural Network)")
    print("=" * 60)

    model = MLPClassifier(
        hidden_layer_sizes=(128, 64, 32),
        activation="relu",
        solver="adam",
        max_iter=500,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.15,
        learning_rate="adaptive",
        batch_size=64,
    )
    model.fit(X_train, y_train)

    val_metrics = evaluate_model(model, X_val, y_val, "validation")
    print_metrics(val_metrics, "MLP")

    return model, val_metrics


def select_best_model(results):
    """
    Select the best model based on:
    1. Primary: macro F1 (weighted higher for imbalanced data)
    2. Secondary: inference latency (for real-time use)
    """
    print("\n" + "=" * 60)
    print("MODEL COMPARISON & SELECTION")
    print("=" * 60)

    # Comparison table
    print(f"\n{'Model':<25} {'F1 Macro':>10} {'Accuracy':>10} {'ROC-AUC':>10} "
          f"{'Latency(ms)':>12} {'Size(KB)':>10}")
    print("-" * 80)

    best_model = None
    best_score = -1
    best_name = None

    for name, data in results.items():
        model = data["model"]
        metrics = data["val_metrics"]
        size_kb = data["size_kb"]

        roc_str = f"{metrics['roc_auc']:.4f}" if metrics['roc_auc'] else "N/A"
        print(f"{name:<25} {metrics['f1_macro']:>10.4f} {metrics['accuracy']:>10.4f} "
              f"{roc_str:>10} {metrics['per_sample_latency_ms']:>12.4f} {size_kb:>10.1f}")

        # Score: macro F1 with a small penalty for high latency
        # Latency penalty: reduce score if > 1ms/sample
        latency_penalty = max(0, (metrics['per_sample_latency_ms'] - 1.0) * 0.01)
        combined_score = metrics['f1_macro'] - latency_penalty

        if combined_score > best_score:
            best_score = combined_score
            best_model = model
            best_name = name

    print(f"\nBest model: {best_name} (combined score: {best_score:.4f})")
    return best_name, best_model


def main():
    print("=" * 70)
    print("STUDENT ATTENTION CLASSIFICATION — TRAINING PIPELINE")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    # --- Setup MLflow ---
    MLFLOW_DIR.mkdir(parents=True, exist_ok=True)
    mlflow_db_path = MLFLOW_DIR / "mlflow.db"
    mlflow.set_tracking_uri(f"sqlite:///{mlflow_db_path.as_posix()}")
    mlflow.set_experiment("attention_classification")

    # --- Load & preprocess ---
    df = load_dataset()
    X_train, X_val, X_test, y_train, y_val, y_test = split_dataset(df)

    preprocessor = build_preprocessing_pipeline()
    X_train_proc = preprocessor.fit_transform(X_train)
    X_val_proc = preprocessor.transform(X_val)
    X_test_proc = preprocessor.transform(X_test)

    save_pipeline(preprocessor)
    save_feature_schema()

    print(f"\nProcessed shapes: train={X_train_proc.shape}, "
          f"val={X_val_proc.shape}, test={X_test_proc.shape}")

    # --- Train all models ---
    results = {}

    # 1. Logistic Regression
    lr_model, lr_metrics = train_logistic_regression(
        X_train_proc, y_train, X_val_proc, y_val)
    results["LogisticRegression"] = {
        "model": lr_model,
        "val_metrics": lr_metrics,
        "size_kb": get_model_size_kb(lr_model),
    }

    # 2. Random Forest
    rf_model, rf_metrics = train_random_forest(
        X_train_proc, y_train, X_val_proc, y_val)
    results["RandomForest"] = {
        "model": rf_model,
        "val_metrics": rf_metrics,
        "size_kb": get_model_size_kb(rf_model),
    }

    # 3. XGBoost
    xgb_model, xgb_metrics = train_xgboost(
        X_train_proc, y_train, X_val_proc, y_val)
    if xgb_model is not None:
        results["XGBoost"] = {
            "model": xgb_model,
            "val_metrics": xgb_metrics,
            "size_kb": get_model_size_kb(xgb_model),
        }

    # 4. MLP
    mlp_model, mlp_metrics = train_mlp(
        X_train_proc, y_train, X_val_proc, y_val)
    results["MLP"] = {
        "model": mlp_model,
        "val_metrics": mlp_metrics,
        "size_kb": get_model_size_kb(mlp_model),
    }

    # --- Select best model ---
    best_name, best_model = select_best_model(results)

    # --- Evaluate best model on test set ---
    print("\n" + "=" * 60)
    print(f"FINAL EVALUATION: {best_name} on TEST set")
    print("=" * 60)

    test_metrics = evaluate_model(best_model, X_test_proc, y_test, "test")
    print_metrics(test_metrics, best_name)

    # --- Log to MLflow ---
    for name, data in results.items():
        with mlflow.start_run(run_name=name):
            mlflow.log_param("model_type", name)
            mlflow.log_param("dataset", "attention_detection_v3")
            mlflow.log_param("n_train", len(y_train))
            mlflow.log_param("n_val", len(y_val))
            mlflow.log_param("n_test", len(y_test))
            mlflow.log_param("feature_schema_version", "v1")
            mlflow.log_param("num_features", X_train_proc.shape[1])

            metrics = data["val_metrics"]
            mlflow.log_metric("val_accuracy", metrics["accuracy"])
            mlflow.log_metric("val_f1_macro", metrics["f1_macro"])
            mlflow.log_metric("val_precision_macro", metrics["precision_macro"])
            mlflow.log_metric("val_recall_macro", metrics["recall_macro"])
            if metrics["roc_auc"] is not None:
                mlflow.log_metric("val_roc_auc", metrics["roc_auc"])
            mlflow.log_metric("val_latency_ms", metrics["per_sample_latency_ms"])
            mlflow.log_metric("model_size_kb", data["size_kb"])

            if name == best_name:
                # Also log test metrics for the best model
                mlflow.log_metric("test_accuracy", test_metrics["accuracy"])
                mlflow.log_metric("test_f1_macro", test_metrics["f1_macro"])
                mlflow.log_metric("test_precision_macro", test_metrics["precision_macro"])
                mlflow.log_metric("test_recall_macro", test_metrics["recall_macro"])
                if test_metrics["roc_auc"] is not None:
                    mlflow.log_metric("test_roc_auc", test_metrics["roc_auc"])
                mlflow.set_tag("best_model", "true")

            # Log model — handle skops trusted types for each model type
            if name == "XGBoost":
                mlflow.xgboost.log_model(data["model"], "model")
            elif name == "RandomForest":
                mlflow.sklearn.log_model(
                    data["model"], "model",
                    skops_trusted_types=["sklearn.tree._tree.Tree"]
                )
            elif name == "MLP":
                mlflow.sklearn.log_model(
                    data["model"], "model",
                    skops_trusted_types=[
                        "sklearn.neural_network._stochastic_optimizers.AdamOptimizer"
                    ]
                )
            else:
                mlflow.sklearn.log_model(data["model"], "model")

    # --- Save best model + pipeline ---
    best_model_path = MODEL_DIR / "attention_classifier_best.joblib"
    joblib.dump(best_model, best_model_path)
    print(f"\nBest model saved to {best_model_path}")

    # Save all models
    for name, data in results.items():
        model_path = MODEL_DIR / f"attention_classifier_{name.lower()}.joblib"
        joblib.dump(data["model"], model_path)
        print(f"  {name} saved to {model_path}")

    # --- Save model registry entry ---
    registry_entry = {
        "model_name": "attention_classifier",
        "version": "v1.0",
        "best_model": best_name,
        "training_dataset": "Students Attention Detection Dataset v3",
        "training_date": datetime.now().isoformat(),
        "feature_schema_version": "v1",
        "status": "production",
        "metrics": {
            "test": test_metrics,
            "validation": {name: data["val_metrics"] for name, data in results.items()},
        },
        "model_path": str(best_model_path),
        "preprocessing_pipeline_path": str(
            AI_DIR / "data" / "pipelines" / "preprocessing_pipeline.joblib"
        ),
        "parameters": {
            name: str(data["model"].get_params()) for name, data in results.items()
        },
        "splitting_strategy": {
            "method": "stratified_random",
            "ratios": "70/15/15",
            "reason": "No participant/session IDs in dataset; random split with stratification",
            "random_state": 42,
        },
    }

    registry_path = MODEL_DIR / "model_registry.json"
    with open(registry_path, "w") as f:
        json.dump(registry_entry, f, indent=2, default=str)
    print(f"\nModel registry saved to {registry_path}")

    # --- Evaluation report ---
    report = {
        "summary": {
            "best_model": best_name,
            "test_f1_macro": test_metrics["f1_macro"],
            "test_accuracy": test_metrics["accuracy"],
        },
        "all_models": {
            name: {
                "val_metrics": data["val_metrics"],
                "size_kb": data["size_kb"],
            }
            for name, data in results.items()
        },
        "best_model_test_metrics": test_metrics,
    }

    report_path = REPORTS_DIR / "model_evaluation_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Evaluation report saved to {report_path}")

    print("\n" + "=" * 70)
    print("TRAINING COMPLETE")
    print("=" * 70)

    return best_model, preprocessor, test_metrics


if __name__ == "__main__":
    main()
