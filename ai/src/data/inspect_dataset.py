"""
Dataset Inspection & EDA for Students Attention Detection Dataset v3.
Reads the actual dataset, inspects schema, identifies all features,
analyzes distributions, checks for leakage, and outputs a complete report.
"""

import pandas as pd
import numpy as np
import json
import os
import sys
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATASET_PATH = DATA_DIR / "attention_detection_dataset_v3.csv"
REPORT_DIR = DATA_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def load_dataset():
    """Load the dataset and return the DataFrame."""
    print("=" * 70)
    print("STUDENTS ATTENTION DETECTION DATASET v3 — INSPECTION REPORT")
    print("=" * 70)

    df = pd.read_csv(DATASET_PATH)
    print(f"\nDataset loaded: {DATASET_PATH}")
    print(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    return df


def inspect_schema(df):
    """Inspect and report on the dataset schema."""
    print("\n" + "=" * 70)
    print("1. SCHEMA INSPECTION")
    print("=" * 70)

    print(f"\nTotal columns: {df.shape[1]}")
    print(f"Total rows: {df.shape[0]}")

    print("\n--- Column Names and Data Types ---")
    for i, (col, dtype) in enumerate(zip(df.columns, df.dtypes)):
        print(f"  [{i:2d}] {col:30s} {str(dtype):15s}")

    return df.columns.tolist()


def identify_target(df):
    """Identify the target column."""
    print("\n" + "=" * 70)
    print("2. TARGET COLUMN IDENTIFICATION")
    print("=" * 70)

    target_col = "label"
    if target_col not in df.columns:
        # Try to find it
        possible = [c for c in df.columns if "label" in c.lower() or "target" in c.lower()]
        if possible:
            target_col = possible[0]
        else:
            print("WARNING: No obvious target column found!")
            return None

    print(f"\nTarget column: '{target_col}'")
    print(f"Target dtype: {df[target_col].dtype}")
    print(f"Target unique values: {df[target_col].unique()}")
    print(f"\nClass distribution:")
    dist = df[target_col].value_counts()
    for val, count in dist.items():
        pct = count / len(df) * 100
        print(f"  {val}: {count:5d} ({pct:.1f}%)")

    # Check for imbalance
    ratio = dist.min() / dist.max()
    print(f"\nImbalance ratio (min/max): {ratio:.3f}")
    if ratio < 0.5:
        print("⚠ WARNING: Significant class imbalance detected!")
    else:
        print("✓ Classes are reasonably balanced.")

    return target_col


def identify_features(df, target_col):
    """Categorize features into groups."""
    print("\n" + "=" * 70)
    print("3. FEATURE IDENTIFICATION")
    print("=" * 70)

    feature_cols = [c for c in df.columns if c != target_col]
    print(f"\nTotal feature columns: {len(feature_cols)}")

    # Categorize by type
    numerical = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
    categorical = df[feature_cols].select_dtypes(exclude=[np.number]).columns.tolist()

    print(f"\nNumerical features ({len(numerical)}):")
    for col in numerical:
        print(f"  - {col}")

    print(f"\nCategorical features ({len(categorical)}):")
    for col in categorical:
        unique = df[col].nunique()
        print(f"  - {col} (unique values: {unique})")
        if unique <= 20:
            print(f"    Values: {df[col].unique().tolist()}")

    # Group features by prefix
    groups = {}
    for col in feature_cols:
        parts = col.split("_")
        prefix = parts[0] if len(parts) > 1 else col
        groups.setdefault(prefix, []).append(col)

    print(f"\nFeature groups by prefix:")
    for prefix, cols in sorted(groups.items()):
        print(f"  {prefix}: {cols}")

    return feature_cols, numerical, categorical


def check_missing_values(df, feature_cols, target_col):
    """Check for missing values."""
    print("\n" + "=" * 70)
    print("4. MISSING VALUES ANALYSIS")
    print("=" * 70)

    missing = df.isnull().sum()
    total_missing = missing.sum()
    print(f"\nTotal missing values: {total_missing}")

    if total_missing > 0:
        print("\nColumns with missing values:")
        for col in df.columns:
            if missing[col] > 0:
                pct = missing[col] / len(df) * 100
                print(f"  {col:30s}: {missing[col]:5d} ({pct:.1f}%)")
    else:
        print("✓ No missing values found.")

    # Also check for special sentinel values
    print("\nChecking for sentinel values (e.g., -1, 999, NaN strings):")
    for col in feature_cols:
        if df[col].dtype in [np.float64, np.int64, np.float32, np.int32]:
            neg_count = (df[col] == -1).sum()
            if neg_count > 0:
                print(f"  {col}: {neg_count} values of -1 (possible sentinel)")
        elif df[col].dtype == object:
            for sentinel in ["nan", "NaN", "None", "null", "N/A", "NA", ""]:
                count = (df[col] == sentinel).sum()
                if count > 0:
                    print(f"  {col}: {count} values of '{sentinel}'")


def check_duplicates(df):
    """Check for duplicate records."""
    print("\n" + "=" * 70)
    print("5. DUPLICATE RECORDS")
    print("=" * 70)

    total_dupes = df.duplicated().sum()
    print(f"\nExact duplicate rows: {total_dupes}")
    if total_dupes > 0:
        print(f"Percentage: {total_dupes / len(df) * 100:.2f}%")
        print("⚠ Consider removing duplicates before training.")
    else:
        print("✓ No exact duplicate rows found.")


def descriptive_statistics(df, numerical, categorical):
    """Generate descriptive statistics."""
    print("\n" + "=" * 70)
    print("6. DESCRIPTIVE STATISTICS (NUMERICAL)")
    print("=" * 70)

    if numerical:
        stats = df[numerical].describe().T
        stats["skew"] = df[numerical].skew()
        stats["kurtosis"] = df[numerical].kurtosis()
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", 200)
        pd.set_option("display.float_format", lambda x: f"{x:.4f}")
        print("\n", stats.to_string())

    if categorical:
        print("\n--- Categorical Statistics ---")
        for col in categorical:
            print(f"\n  {col}:")
            vc = df[col].value_counts()
            for val, cnt in vc.items():
                print(f"    {val}: {cnt} ({cnt/len(df)*100:.1f}%)")


def detect_leakage(df, feature_cols, target_col):
    """Detect potential data leakage."""
    print("\n" + "=" * 70)
    print("7. DATA LEAKAGE ANALYSIS")
    print("=" * 70)

    # Check for participant/session identifiers
    id_candidates = [c for c in df.columns if any(kw in c.lower() for kw in
                     ["id", "participant", "student", "session", "subject",
                      "user", "frame", "sequence", "timestamp", "time"])]

    if id_candidates:
        print(f"\nPotential ID/temporal columns detected:")
        for col in id_candidates:
            print(f"  - {col} (unique: {df[col].nunique()}, dtype: {df[col].dtype})")
        print("\n⚠ If these represent participant or session IDs,")
        print("  a subject-aware split is required to avoid leakage.")
    else:
        print("\n✓ No obvious participant/session ID columns detected.")
        print("  Random splitting is acceptable, but temporal leakage")
        print("  should still be considered if data is sequential.")

    # Check for high-correlation features with target
    print("\nFeature-target correlations (top features):")
    num_features = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
    if num_features and target_col:
        corrs = df[num_features + [target_col]].corr()[target_col].drop(target_col).abs().sort_values(ascending=False)
        for col, corr_val in corrs.head(15).items():
            flag = " ⚠ SUSPICIOUS" if corr_val > 0.95 else ""
            print(f"  {col:30s}: {corr_val:.4f}{flag}")

        suspicious = corrs[corrs > 0.95]
        if len(suspicious) > 0:
            print(f"\n⚠ {len(suspicious)} features have >0.95 correlation with target.")
            print("  Investigate for potential data leakage!")
        else:
            print("\n✓ No suspiciously high feature-target correlations found.")


def feature_target_analysis(df, numerical, target_col):
    """Analyze feature-target relationships."""
    print("\n" + "=" * 70)
    print("8. FEATURE-TARGET RELATIONSHIPS")
    print("=" * 70)

    if not target_col or not numerical:
        print("Skipping — insufficient data")
        return

    # Group means by target
    print("\nMean feature values by target class:")
    grouped = df.groupby(target_col)[numerical].mean()
    print(grouped.T.to_string())

    # Feature importance via mutual information (basic)
    print("\nFeature discrimination (absolute mean difference / pooled std):")
    effects = {}
    classes = df[target_col].unique()
    if len(classes) == 2:
        g0 = df[df[target_col] == classes[0]][numerical]
        g1 = df[df[target_col] == classes[1]][numerical]
        for col in numerical:
            pooled_std = np.sqrt((g0[col].std()**2 + g1[col].std()**2) / 2)
            if pooled_std > 0:
                effect = abs(g0[col].mean() - g1[col].mean()) / pooled_std
            else:
                effect = 0
            effects[col] = effect

        for col, eff in sorted(effects.items(), key=lambda x: -x[1])[:15]:
            strength = "Strong" if eff > 0.8 else "Medium" if eff > 0.5 else "Weak"
            print(f"  {col:30s}: {eff:.4f} ({strength})")


def generate_report_json(df, target_col, feature_cols, numerical, categorical):
    """Save a machine-readable report."""
    report = {
        "dataset": "Students Attention Detection Dataset v3",
        "source": "https://data.mendeley.com/datasets/smzggbnkd2/3",
        "shape": {"rows": df.shape[0], "columns": df.shape[1]},
        "target": {
            "column": target_col,
            "dtype": str(df[target_col].dtype),
            "classes": df[target_col].unique().tolist(),
            "distribution": df[target_col].value_counts().to_dict(),
        },
        "features": {
            "total": len(feature_cols),
            "numerical": numerical,
            "categorical": categorical,
            "all": feature_cols,
        },
        "missing_values": df.isnull().sum().to_dict(),
        "duplicates": int(df.duplicated().sum()),
        "schema": {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)},
    }

    report_path = REPORT_DIR / "dataset_inspection_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n✓ Report saved to {report_path}")
    return report


def main():
    df = load_dataset()
    columns = inspect_schema(df)
    target_col = identify_target(df)

    feature_cols, numerical, categorical = identify_features(df, target_col)
    check_missing_values(df, feature_cols, target_col)
    check_duplicates(df)
    descriptive_statistics(df, numerical, categorical)
    detect_leakage(df, feature_cols, target_col)
    feature_target_analysis(df, numerical, target_col)

    report = generate_report_json(df, target_col, feature_cols, numerical, categorical)

    print("\n" + "=" * 70)
    print("INSPECTION COMPLETE")
    print("=" * 70)
    return df, report


if __name__ == "__main__":
    df, report = main()
