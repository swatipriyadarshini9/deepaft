#!/usr/bin/env python3
"""
Extract BraTS validation + additional zips into a single holdout tree.

Use only after development (training zip + 5-fold CV on linked cohort).
Validation zip has no segmentations — radiomics runs on additional cases only;
genes-only survival metrics can still run on TCGA-linked validation IDs.

Usage:
  python experiments/brats_prepare_challenge.py \\
    --validation-zip "C:/Users/.../BraTS2024-BraTS-GLI-ValidationData.zip" \\
    --additional-zip "C:/Users/.../BraTS2024-BraTS-GLI-AdditionalTrainingData.zip"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from brats_challenge import build_manifest, extract_zip, seg_count_in_zip, write_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract BraTS GLI challenge holdout zips")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/brats2024_challenge"),
        help="Extract both zips here (nested validation_data/ + training_data_additional/)",
    )
    parser.add_argument("--validation-zip", type=Path, default=None)
    parser.add_argument("--additional-zip", type=Path, default=None)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/processed/brats_challenge_manifest.json"),
    )
    args = parser.parse_args()

    if not args.validation_zip and not args.additional_zip:
        raise SystemExit("Provide at least one of --validation-zip or --additional-zip")

    for label, zpath in (
        ("validation", args.validation_zip),
        ("additional", args.additional_zip),
    ):
        if zpath is None:
            continue
        if not zpath.is_file():
            raise SystemExit(f"Missing {label} zip: {zpath}")
        n_seg = seg_count_in_zip(zpath)
        print(f"{label}: {zpath.name} ({n_seg} seg volumes in archive)")
        if label == "validation" and n_seg == 0:
            print(
                "  Note: validation release has no seg — use for genes-only holdout or "
                "pipeline smoke tests, not radiomics C-index."
            )
        extract_zip(zpath, args.output)

    manifest = build_manifest(args.output)
    write_manifest(manifest, args.manifest)


if __name__ == "__main__":
    main()
