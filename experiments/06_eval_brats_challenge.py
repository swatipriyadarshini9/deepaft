#!/usr/bin/env python3
"""
Post-training holdout check: fit on official **train** split only, then score challenge splits.

Designed for BraTS 2024 GLI release layout:
  - train (1350): main TrainingData zip — use in run_brats_pipeline / CV
  - train_additional (271): AdditionalTrainingData — radiomics + survival if TCGA-linked
  - validation (188): ValidationData — **no segmentations**; imaging QC only

Requires PTG metadata CSV from ingest_ptg_metadata.py (not the TCGA crosswalk).

Usage (after linked train cohort + models validated on CV):
  python experiments/filter_linked_cohort_train.py
  python experiments/06_eval_brats_challenge.py \\
    --train-cohort data/processed/linked_cohort_train.csv
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from deepaft import DeepAFT, amse, harrell_c_index  # noqa: E402
from deepaft.censoring import censoring_survival  # noqa: E402

GENE_COLS = ["IDH1", "MGMT", "TP53"]


def load_feature_matrix(df: pd.DataFrame, feature_set: str) -> np.ndarray:
    gene_cols = [c for c in GENE_COLS if c in df.columns]
    if not gene_cols:
        raise ValueError(f"Need gene columns {GENE_COLS}")
    radio_cols = [c for c in df.columns if c.startswith("radiomics_") or c.startswith("shape_")]
    if feature_set == "genes":
        return df[gene_cols].values.astype(float)
    if feature_set == "radiomics":
        if not radio_cols:
            raise ValueError("No radiomics columns in cohort")
        return df[radio_cols].values.astype(float)
    if feature_set == "genes_radiomics":
        return df[gene_cols + radio_cols].values.astype(float)
    raise ValueError(feature_set)


def project_groups(df: pd.DataFrame) -> np.ndarray | None:
    if "project" not in df.columns:
        return None
    return (df["project"] == "TCGA-GBM").astype(int).values


def filter_cohort_by_split(cohort: pd.DataFrame, metadata: pd.DataFrame, split: str) -> pd.DataFrame:
    meta = metadata[metadata["official_split"] == split][["brats_id"]]
    key = "brats_id" if "brats_id" in cohort.columns else None
    if key is None:
        raise ValueError("Train cohort must include brats_id for split filtering")
    cohort = cohort.copy()
    cohort[key] = cohort[key].astype(str).str.strip()
    meta["brats_id"] = meta["brats_id"].astype(str).str.strip()
    return cohort.merge(meta, on="brats_id", how="inner")


def run_radiomics(data_dir: Path, output: Path, limit: int | None = None) -> None:
    cmd = [
        sys.executable,
        str(ROOT / "experiments" / "04_radiomics_brats.py"),
        "--data-dir",
        str(data_dir),
        "--output",
        str(output),
    ]
    if limit:
        cmd.extend(["--limit", str(limit)])
    subprocess.run(cmd, cwd=ROOT, check=True)


def merge_radiomics_cohort(
    radiomics_csv: Path,
    crosswalk: Path,
    survival_csv: Path,
    tcga_cohort: Path,
) -> pd.DataFrame:
    out = radiomics_csv.with_name("linked_holdout_tmp.csv")
    cmd = [
        sys.executable,
        str(ROOT / "experiments" / "merge_linked_cohort.py"),
        "--crosswalk",
        str(crosswalk),
        "--survival",
        str(survival_csv),
        "--cohort",
        str(tcga_cohort),
        "--radiomics",
        str(radiomics_csv),
        "--output",
        str(out),
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)
    return pd.read_csv(out)


def validation_imaging_qc(validation_dir: Path) -> dict:
    """Validation release has modalities but no seg — report coverage only."""
    if not validation_dir.exists():
        return {"status": "missing_dir", "path": str(validation_dir)}

    case_dirs = sorted(p for p in validation_dir.rglob("BraTS-GLI-*") if p.is_dir())
    n_cases = len(case_dirs)
    n_seg = sum(1 for p in case_dirs if list(p.glob("*-seg.nii.gz")))
    modality_hits = {m: 0 for m in ("t1n", "t1c", "t2w", "t2f")}
    for case_dir in case_dirs[:5000]:
        for m in modality_hits:
            if list(case_dir.glob(f"*-{m}.nii.gz")):
                modality_hits[m] += 1
    return {
        "status": "ok",
        "n_cases": n_cases,
        "n_with_seg": n_seg,
        "modality_coverage": modality_hits,
        "note": "Validation split is for imaging QC only; radiomics/survival holdout uses train_additional.",
    }


def eval_holdout(model, model_name: str, df: pd.DataFrame, feature_set: str) -> dict:
    X = load_feature_matrix(df, feature_set)
    t = df["time_days"].values.astype(float)
    e = df["event"].values.astype(int)
    g = project_groups(df)
    if model_name.startswith("deepAFT"):
        pred = model.predict_time(X, groups=g)
    else:
        pred = model.predict_time(X)
    ghat = censoring_survival(t, e, mode="marginal")
    log_pred = np.log(np.clip(pred, 1e-8, None))
    return {
        "n": len(df),
        "c_index": float(harrell_c_index(pred, t, e)),
        "amse": float(amse(log_pred, t, e, ghat)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-cohort", type=Path, default=Path("data/processed/linked_cohort_train.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("data/processed/brats_ptg_metadata.csv"))
    parser.add_argument("--crosswalk", type=Path, default=Path("data/processed/brats_tcga_crosswalk.csv"))
    parser.add_argument("--survival", type=Path, default=Path("data/processed/gdc_survival.csv"))
    parser.add_argument("--tcga-cohort", type=Path, default=Path("data/processed/tcga_glioma_cohort.csv"))
    parser.add_argument("--additional-data-dir", type=Path, default=Path("data/raw/brats2024_challenge/additional"))
    parser.add_argument("--validation-data-dir", type=Path, default=Path("data/raw/brats2024_challenge/validation"))
    parser.add_argument("--feature-set", choices=("genes", "radiomics", "genes_radiomics"), default="genes_radiomics")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--radiomics-limit", type=int, default=None, help="Smoke test on additional split")
    parser.add_argument("--skip-additional", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("results/tables/holdout_challenge.json"))
    args = parser.parse_args()

    for path in (args.train_cohort, args.metadata, args.crosswalk):
        if not path.exists():
            raise SystemExit(f"Missing required file: {path}")

    train_full = pd.read_csv(args.train_cohort)
    meta = pd.read_csv(args.metadata)
    train_df = filter_cohort_by_split(train_full, meta, "train")
    if train_df.empty:
        print("Warning: no brats_id overlap with official train split; using full train cohort.")
        train_df = train_full

    time = train_df["time_days"].values.astype(float)
    event = train_df["event"].values.astype(int)
    groups = project_groups(train_df)
    X_tr = load_feature_matrix(train_df, args.feature_set)

    report: dict = {
        "train_split_n": len(train_df),
        "feature_set": args.feature_set,
        "validation_qc": validation_imaging_qc(args.validation_data_dir),
        "holdout_additional": {},
    }

    model = DeepAFT(
        method="buckley_james",
        censoring="covariate",
        scale="group",
        hidden=(8, 6),
        epochs=args.epochs,
        random_state=args.seed,
    )
    model.fit(X_tr, time, event, groups=groups)
    report["train_fit"] = {"model": "deepAFT_BJ_group", "n": len(train_df)}

    if not args.skip_additional and args.additional_data_dir.exists():
        with tempfile.TemporaryDirectory(prefix="holdout_radio_") as tmp:
            radio_out = Path(tmp) / "radiomics_additional.csv"
            run_radiomics(args.additional_data_dir, radio_out, limit=args.radiomics_limit)
            holdout = merge_radiomics_cohort(
                radio_out, args.crosswalk, args.survival, args.tcga_cohort
            )
            meta_add = meta[meta["official_split"] == "train_additional"]["brats_id"].astype(str)
            holdout["brats_id"] = holdout["brats_id"].astype(str).str.strip()
            holdout = holdout[holdout["brats_id"].isin(set(meta_add))]
            report["holdout_additional"]["n_linked_with_survival"] = len(holdout)
            if len(holdout) >= 5:
                report["holdout_additional"]["deepAFT_BJ_group"] = eval_holdout(
                    model, "deepAFT", holdout, args.feature_set
                )
            else:
                report["holdout_additional"]["note"] = (
                    "Fewer than 5 TCGA-linked additional cases with survival; "
                    "check crosswalk and radiomics merge."
                )
    else:
        report["holdout_additional"]["status"] = "skipped_or_missing_dir"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nWrote {args.output.resolve()}")


if __name__ == "__main__":
    main()
