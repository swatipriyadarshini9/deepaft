#!/usr/bin/env python3
"""
Ingest BraTS-PTG supplementary demographic metadata (Synapse syn64735496).

This spreadsheet lists official Train / Train-additional / Validation splits.
It is **not** the BraTS→TCGA crosswalk (use 02_build_tcga_crosswalk.py for barcodes).

Usage:
  python experiments/ingest_ptg_metadata.py \\
    --input "C:/Users/.../BraTS-PTG supplementary demographic information and metadata.xlsx"
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pandas as pd

SPLIT_COL_CANDIDATES = (
    "Train/Test/Validation ",
    "Train/Test/Validation",
    "Split",
)
ID_COL = "BraTS Subject ID"


def normalize_split(raw: str) -> str:
    s = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    if s in ("train", "training"):
        return "train"
    if s in ("train_additional", "additional", "trainadditional"):
        return "train_additional"
    if s in ("validation", "val", "test"):
        return "validation"
    return s or "unknown"


def load_ptg_table(path: Path) -> pd.DataFrame:
    xl = pd.ExcelFile(path)
    sheet = "Individual Data" if "Individual Data" in xl.sheet_names else xl.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet)
    split_col = next((c for c in SPLIT_COL_CANDIDATES if c in df.columns), None)
    if split_col is None:
        for c in df.columns:
            if "train" in c.lower() and "validation" in c.lower():
                split_col = c
                break
    if split_col is None or ID_COL not in df.columns:
        raise SystemExit(f"Unexpected columns in {path.name}: {list(df.columns)}")

    out = pd.DataFrame(
        {
            "brats_id": df[ID_COL].astype(str).str.strip(),
            "official_split": df[split_col].map(normalize_split),
            "glioma_type": df.get("Glioma type ", df.get("Glioma type")),
            "age": df.get("Patient's Age"),
            "sex": df.get("Patient's Sex"),
            "site": df.get("Site"),
        }
    )
    out = out.drop_duplicates(subset=["brats_id"], keep="first")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="PTG supplementary metadata xlsx")
    parser.add_argument("--output", type=Path, default=Path("data/processed/brats_ptg_metadata.csv"))
    parser.add_argument(
        "--copy-to-raw",
        type=Path,
        default=Path("data/raw/brats_ptg_supplementary_metadata.xlsx"),
        help="Optional copy of xlsx into repo raw/ (still gitignored if under data/raw)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Missing: {args.input}")

    df = load_ptg_table(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)

    if args.copy_to_raw:
        args.copy_to_raw.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.input, args.copy_to_raw)
        print(f"Copied xlsx -> {args.copy_to_raw.resolve()}")

    print(df["official_split"].value_counts().to_string())
    print(f"\nWrote {len(df)} rows -> {args.output.resolve()}")


if __name__ == "__main__":
    main()
