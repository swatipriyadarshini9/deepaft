#!/usr/bin/env python3
"""QC summary for BraTS 2024 GLI validation split (modalities present, no seg labels)."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
_RADIOMICS = ROOT / "experiments" / "04_radiomics_brats.py"
MODALITIES = ("t1n", "t1c", "t2w", "t2f")


def _mod():
    spec = importlib.util.spec_from_file_location("r", _RADIOMICS)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/raw/brats2024_training/BraTS-GLI/BraTS2024-BraTS-GLI-ValidationData/validation_data"),
    )
    parser.add_argument("--output", type=Path, default=Path("results/tables/brats_validation_qc.csv"))
    args = parser.parse_args()

    mod = _mod()
    cases = mod.find_patient_dirs(args.data_dir, require_seg=False)
    rows: list[dict] = []
    for case_dir in cases:
        cid = mod.case_id_from_dir(case_dir)
        present = {m: mod.find_modality(case_dir, cid, m) is not None for m in MODALITIES}
        rows.append(
            {
                "patient_id": cid,
                "all_four_modalities": all(present.values()),
                **{f"has_{m}": present[m] for m in MODALITIES},
                "has_seg": mod.find_seg(case_dir, cid) is not None,
            }
        )

    df = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame(
        [
            {
                "n_cases": len(df),
                "all_four_modalities": int(df["all_four_modalities"].sum()) if len(df) else 0,
                "with_seg": int(df["has_seg"].sum()) if len(df) else 0,
            }
        ]
    )
    summary.to_csv(args.output, index=False)
    detail = args.output.with_name("brats_validation_qc_detail.csv")
    df.to_csv(detail, index=False)
    print(f"Wrote {args.output} ({len(df)} validation cases)")


if __name__ == "__main__":
    main()
