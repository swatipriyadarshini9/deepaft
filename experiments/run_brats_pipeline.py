#!/usr/bin/env python3
"""
Run BraTS -> TCGA linkage pipeline after Synapse download completes.

Steps:
  1. Build BraTS-TCGA crosswalk from mapping spreadsheet
  2. Extract PyRadiomics features from BraTS-GLI NIfTI
  3. Merge crosswalk + survival + genes + radiomics
  4. Train models on linked cohort (genes, radiomics, genes+radiomics)
  5. Regenerate thesis_results.md

Usage:
  python experiments/run_brats_pipeline.py
  python experiments/run_brats_pipeline.py --radiomics-limit 10   # smoke test
  python experiments/run_brats_pipeline.py --skip-radiomics
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _default_brats_dir() -> Path:
    import os

    raw = os.environ.get("DISSERTATION_BRATS_DIR")
    return Path(raw) if raw else Path("data/raw/brats2024_training")


def run(cmd: list[str]) -> None:
    print("\n>>", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brats-dir", type=Path, default=None)
    parser.add_argument("--crosswalk", type=Path, default=Path("data/processed/brats_tcga_crosswalk.csv"))
    parser.add_argument("--radiomics", type=Path, default=Path("data/processed/radiomics_features.csv"))
    parser.add_argument("--linked", type=Path, default=Path("data/processed/linked_cohort.csv"))
    parser.add_argument("--radiomics-limit", type=int, default=None)
    parser.add_argument("--skip-radiomics", action="store_true")
    args = parser.parse_args()
    if args.brats_dir is None:
        args.brats_dir = _default_brats_dir()

    py = sys.executable

    if not args.brats_dir.exists():
        raise SystemExit(f"BraTS dir missing: {args.brats_dir}. Wait for Synapse download.")

    crosswalk_cmd = [
        py,
        "experiments/02_build_tcga_crosswalk.py",
        "--auto-find",
        "--brats-dir",
        str(args.brats_dir),
        "--output",
        str(args.crosswalk),
    ]
    def _crosswalk_ready() -> bool:
        if not args.crosswalk.is_file() or args.crosswalk.stat().st_size == 0:
            return False
        lines = args.crosswalk.read_text(encoding="utf-8").splitlines()
        return len(lines) > 1 and "tcga_barcode" in lines[0]

    if _crosswalk_ready():
        print(f"Using existing crosswalk: {args.crosswalk}")
    else:
        try:
            run(crosswalk_cmd)
        except subprocess.CalledProcessError:
            print("Official mapping not found; building GDC demographic crosswalk (02c) ...")
            run([
                py,
                "experiments/02c_fetch_tcga_crosswalk_api.py",
                "--output",
                str(args.crosswalk),
            ])

    if not args.skip_radiomics:
        radio_cmd = [
            py,
            "experiments/04_radiomics_brats.py",
            "--data-dir",
            str(args.brats_dir),
            "--output",
            str(args.radiomics),
            "--require-seg",
        ]
        if args.radiomics_limit:
            radio_cmd.extend(["--limit", str(args.radiomics_limit)])
        try:
            run(radio_cmd)
        except subprocess.CalledProcessError:
            print("PyRadiomics path failed; using nibabel features (04b) ...")
            fallback = [
                py,
                "experiments/04b_brats_imaging_features.py",
                "--data-dir",
                str(args.brats_dir),
                "--output",
                str(args.radiomics),
                "--require-seg",
            ]
            if args.radiomics_limit:
                fallback.extend(["--limit", str(args.radiomics_limit)])
            run(fallback)

    merge_cmd = [
        py,
        "experiments/merge_linked_cohort.py",
        "--crosswalk",
        str(args.crosswalk),
        "--output",
        str(args.linked),
    ]
    if args.radiomics.exists():
        merge_cmd.extend(["--radiomics", str(args.radiomics)])
    run(merge_cmd)

    run([
        py,
        "experiments/05_train_glioma_models.py",
        "--cohort",
        str(args.linked),
        "--output",
        "results/tables/glioma_benchmark_linked.csv",
    ])

    run([py, "experiments/generate_thesis_results.py"])
    print("\nPipeline complete.")


if __name__ == "__main__":
    main()
