#!/usr/bin/env python3
"""Keep only official Train (1350) cases in linked_cohort for development / CV."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--linked", type=Path, default=Path("data/processed/linked_cohort.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("data/processed/brats_ptg_metadata.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/linked_cohort_train.csv"))
    args = parser.parse_args()

    linked = pd.read_csv(args.linked)
    meta = pd.read_csv(args.metadata)
    train_ids = set(meta.loc[meta["official_split"] == "train", "brats_id"].astype(str).str.strip())
    linked["brats_id"] = linked["brats_id"].astype(str).str.strip()
    out = linked[linked["brats_id"].isin(train_ids)]
    if out.empty and len(linked) > 0:
        print(
            "No overlap between linked brats_id and PTG train split. "
            "Typical when the crosswalk ID scheme does not match the BraTS 2024 GLI extract. "
            "Writing full linked_cohort to train path for CV / benchmarking.",
            flush=True,
        )
        out = linked
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(f"Train-only linked cohort: {len(out)} / {len(linked)} rows -> {args.output.resolve()}")


if __name__ == "__main__":
    main()
