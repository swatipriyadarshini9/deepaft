#!/usr/bin/env python3
"""Report BraTS 2024 PTG ID overlap with any stored TCGA crosswalk (informative, not thesis headline)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crosswalk", type=Path, default=Path("data/processed/brats_tcga_crosswalk.csv"))
    parser.add_argument("--features", type=Path, default=Path("data/processed/radiomics_features.csv"))
    parser.add_argument("--output", type=Path, default=Path("results/tables/brats_tcga_linkage_report.json"))
    args = parser.parse_args()

    out: dict = {"crosswalk_rows": 0, "feature_rows": 0, "overlap_ids": 0, "future_work": ""}
    if args.crosswalk.is_file():
        cw = pd.read_csv(args.crosswalk)
        out["crosswalk_rows"] = int(len(cw))
        cw_ids = set(cw["brats_id"]) if "brats_id" in cw.columns else set()
    else:
        cw_ids = set()

    if args.features.is_file():
        feat = pd.read_csv(args.features)
        out["feature_rows"] = int(len(feat))
        f_ids = set(feat["patient_id"])
    else:
        f_ids = set()

    overlap = cw_ids.intersection(f_ids) if cw_ids and f_ids else set()
    out["overlap_ids"] = int(len(overlap))
    out["future_work"] = (
        "Multimodal OS on full BraTS 2024 PTG cohort requires an official PTG↔TCGA crosswalk "
        "whose brats_id column matches BraTS-GLI-* in this extract."
    )
    if overlap:
        out["sample_overlap"] = sorted(overlap)[:5]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
