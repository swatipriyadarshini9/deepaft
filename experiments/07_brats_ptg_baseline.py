#!/usr/bin/env python3
"""Join imaging features with PTG metadata; baseline Site / Glioma type classifier."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, default=Path("data/processed/radiomics_features.csv"))
    parser.add_argument("--ptg", type=Path, default=Path("data/processed/brats_ptg_metadata.csv"))
    parser.add_argument(
        "--target",
        choices=("site", "glioma_type"),
        default="glioma_type",
    )
    parser.add_argument("--output", type=Path, default=Path("results/tables/brats_imaging_baseline.csv"))
    args = parser.parse_args()

    if not args.features.is_file():
        raise SystemExit(f"Missing {args.features} — run 04b_brats_imaging_features.py or 04_radiomics_brats.py")

    feat = pd.read_csv(args.features)
    meta = pd.read_csv(args.ptg)
    merged = feat.merge(meta, left_on="patient_id", right_on="brats_id", how="inner")
    if merged.empty:
        raise SystemExit("No overlap between feature patient_id and brats_ptg_metadata.")

    label = "site" if args.target == "site" else "glioma_type"
    merged = merged.dropna(subset=[label])
    feature_cols = [c for c in merged.columns if c.startswith(("vol_", "mean_", "std_", "median_", "radiomics_"))]

    X = merged[feature_cols]
    y = merged[label].astype(str)
    n_classes = y.nunique()
    if n_classes < 2:
        raise SystemExit(f"Need >=2 classes for {label}, got {n_classes}")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    pipe = Pipeline(
        [
            (
                "prep",
                ColumnTransformer(
                    [("num", Pipeline([("imp", SimpleImputer()), ("sc", StandardScaler())]), feature_cols)]
                ),
            ),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]
    )

    pred = cross_val_predict(pipe, X, y, cv=cv, method="predict")
    rows = [
        {
            "target": label,
            "n_cases": len(merged),
            "n_features": len(feature_cols),
            "n_classes": int(n_classes),
            "accuracy": round(accuracy_score(y, pred), 4),
            "balanced_accuracy": round(balanced_accuracy_score(y, pred), 4),
            "macro_f1": round(f1_score(y, pred, average="macro"), 4),
        }
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False)
    print(f"Wrote {args.output} — {label} on {len(merged)} cases")
    for k, v in rows[0].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
