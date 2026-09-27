import time
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix
)

def evaluate_model(model, X, y, dataset_name="test"):
    """Evaluate model and return metrics dict."""
    # Predictions
    start = time.perf_counter()
    y_pred = model.predict(X)
    inference_time = time.perf_counter() - start
    per_sample_latency_ms = (inference_time / len(X)) * 1000

    # Probabilities
    if hasattr(model, "predict_proba"):
        y_proba = model.predict_proba(X)[:, 1]
        roc_auc = roc_auc_score(y, y_proba)
    else:
        roc_auc = None

    # Metrics
    metrics = {
        "dataset": dataset_name,
        "accuracy": accuracy_score(y, y_pred),
        "precision_macro": precision_score(y, y_pred, average="macro", zero_division=0),
        "recall_macro": recall_score(y, y_pred, average="macro", zero_division=0),
        "f1_macro": f1_score(y, y_pred, average="macro", zero_division=0),
        "f1_class_0": f1_score(y, y_pred, average=None, zero_division=0)[0],
        "f1_class_1": f1_score(y, y_pred, average=None, zero_division=0)[1],
        "roc_auc": roc_auc,
        "confusion_matrix": confusion_matrix(y, y_pred).tolist(),
        "per_sample_latency_ms": per_sample_latency_ms,
        "total_inference_time_ms": inference_time * 1000,
        "n_samples": len(y),
    }

    return metrics


def print_metrics(metrics, model_name=None):
    """Print evaluation metrics."""
    if model_name:
        print(f"\nEvaluating Model: {model_name}")
    print(f"\n  --- {metrics['dataset'].upper()} Metrics ---")
    print(f"  Accuracy:          {metrics['accuracy']:.4f}")
    print(f"  Precision (macro): {metrics['precision_macro']:.4f}")
    print(f"  Recall (macro):    {metrics['recall_macro']:.4f}")
    print(f"  F1 (macro):        {metrics['f1_macro']:.4f}")
    print(f"  F1 (class 0):      {metrics['f1_class_0']:.4f}")
    print(f"  F1 (class 1):      {metrics['f1_class_1']:.4f}")
    if metrics['roc_auc'] is not None:
        print(f"  ROC-AUC:           {metrics['roc_auc']:.4f}")
    print(f"  Latency/sample:    {metrics['per_sample_latency_ms']:.4f} ms")
    cm = metrics['confusion_matrix']
    print(f"  Confusion Matrix:  [[{cm[0][0]:4d}, {cm[0][1]:4d}],")
    print(f"                      [{cm[1][0]:4d}, {cm[1][1]:4d}]]")
