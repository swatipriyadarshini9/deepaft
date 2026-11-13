#!/usr/bin/env python3
"""
Extract BraTS GLI zips into separate trees so training and challenge data never mix.

Recommended layout (matches PTG metadata splits):
  data/raw/brats2024_training/     <- TrainingData.zip (1350 train cases)
  data/raw/brats2024_challenge/additional/  <- AdditionalTrainingData.zip (271)
  data/raw/brats2024_challenge/validation/  <- ValidationData.zip (188, no seg)

Usage:
  python experiments/stage_brats_challenge.py \\
    --training-zip "C:/Users/.../BraTS2024-BraTS-GLI-TrainingData.zip" \\
    --additional-zip "C:/Users/.../BraTS2024-BraTS-GLI-AdditionalTrainingData.zip" \\
    --validation-zip "C:/Users/.../BraTS2024-BraTS-GLI-ValidationData.zip"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from brats_challenge import extract_zip as _extract


def extract_zip(zip_path: Path, output: Path, force: bool = False) -> None:
    if not zip_path.is_file():
        raise SystemExit(f"Zip not found: {zip_path}")
    if not force and any(output.rglob("BraTS-GLI-*")):
        print(f"Skip extract (cases present): {output}")
        return
    _extract(zip_path, output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-zip", type=Path, default=None)
    parser.add_argument("--training-out", type=Path, default=Path("data/raw/brats2024_training"))
    parser.add_argument("--additional-zip", type=Path, default=None)
    parser.add_argument("--validation-zip", type=Path, default=None)
    parser.add_argument("--challenge-root", type=Path, default=Path("data/raw/brats2024_challenge"))
    parser.add_argument("--force", action="store_true", help="Re-extract even if case folders exist")
    args = parser.parse_args()

    if args.training_zip:
        extract_zip(args.training_zip, args.training_out, force=args.force)

    challenge = args.challenge_root
    if args.additional_zip:
        extract_zip(args.additional_zip, challenge / "additional", force=args.force)
    if args.validation_zip:
        extract_zip(args.validation_zip, challenge / "validation", force=args.force)

    print("\nStaging complete. Use train tree for fit/CV; challenge trees only in 06_holdout_challenge.py.")


if __name__ == "__main__":
    main()
