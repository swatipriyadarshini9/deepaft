#!/usr/bin/env python3
"""Descriptive segmentation statistics (volumes, ET fraction) by PTG glioma type and site."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def _radiomics():
    spec = importlib.util.spec_from_file_location("r", ROOT / "experiments" / "04_radiomics_brats.py")
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, default=Path("data/processed/radiomics_features.csv"))
    parser.add_argument("--ptg", type=Path, default=Path("data/processed/brats_ptg_metadata.csv"))
    parser.add_argument("--output", type=Path, default=Path("results/tables/brats_seg_descriptive.csv"))
    args = parser.parse_args()

    feat = pd.read_csv(args.features)
    meta = pd.read_csv(args.ptg)
    df = feat.merge(meta, left_on="patient_id", right_on="brats_id", how="inner")
    if "vol_mm3_wt" not in df.columns:
        raise SystemExit("Need vol_mm3_wt from 04b features")

    df["et_fraction"] = df["vol_mm3_et"] / np.clip(df["vol_mm3_wt"], 1e-6, None)

    rows: list[dict] = []
    for label_col in ("glioma_type", "site"):
        for level, grp in df.groupby(label_col, dropna=True):
            rows.append(
                {
                    "stratify_by": label_col,
                    "level": level,
                    "n_cases": len(grp),
                    "wt_vol_mm3_mean": float(grp["vol_mm3_wt"].mean()),
                    "et_vol_mm3_mean": float(grp["vol_mm3_et"].mean()),
                    "et_fraction_mean": float(grp["et_fraction"].mean()),
                }
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False)
    print(f"Wrote {args.output} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
