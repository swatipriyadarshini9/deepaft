#!/usr/bin/env python3
"""
Subregion graph baseline without PyG/torch: 4 nodes (WT, ET, NET, edema), neighbour-mean features + logistic CV.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
REGIONS = ("wt", "et", "net", "edema")


def graph_features(df: pd.DataFrame) -> np.ndarray:
    rows = []
    for _, row in df.iterrows():
        nodes = []
        for r in REGIONS:
            vol = float(row.get(f"vol_mm3_{r}", 0.0) or 0.0)
            mean = float(row.get(f"mean_t1c_{r}", 0.0) or 0.0)
            nodes.append([vol, mean])
        x = np.asarray(nodes, dtype=np.float64)  # (4, 2)
        nb = (x.sum(axis=0, keepdims=True) - x) / 3.0  # neighbour mean per node
        rows.append(np.concatenate([x.reshape(-1), nb.reshape(-1)]))
    return np.asarray(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, default=Path("data/processed/radiomics_features.csv"))
    parser.add_argument("--ptg", type=Path, default=Path("data/processed/brats_ptg_metadata.csv"))
    parser.add_argument("--output", type=Path, default=Path("results/tables/brats_gnn_glioma_type.csv"))
    args = parser.parse_args()

    feat = pd.read_csv(args.features)
    meta = pd.read_csv(args.ptg)
    df = feat.merge(meta, left_on="patient_id", right_on="brats_id", how="inner").dropna(subset=["glioma_type"])
    X = graph_features(df)
    y = df["glioma_type"].astype(str).values
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    pipe = Pipeline(
        [
            ("imp", SimpleImputer(strategy="median")),
            ("sc", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]
    )
    pred = np.empty_like(y)
    for tr, te in cv.split(X, y):
        pipe.fit(X[tr], y[tr])
        pred[te] = pipe.predict(X[te])

    row = {
        "target": "glioma_type",
        "n_cases": len(df),
        "n_classes": int(pd.Series(y).nunique()),
        "balanced_accuracy": round(float(balanced_accuracy_score(y, pred)), 4),
        "macro_f1": round(float(f1_score(y, pred, average="macro")), 4),
        "note": "Graph-style neighbour aggregation on 4 subregions; sklearn logistic (no torch)",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_csv(args.output, index=False)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
