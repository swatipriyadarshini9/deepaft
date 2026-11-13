#!/usr/bin/env python3
"""
NIfTI-derived imaging features (volumes + t1c first-order stats) without PyRadiomics.

Use when PyRadiomics cannot be installed (e.g. Python 3.14). Output CSV columns are
compatible with merge scripts (patient_id + feature columns).

  python experiments/04b_brats_imaging_features.py --limit 20
  python experiments/04b_brats_imaging_features.py --require-seg
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
_RADIOMICS = ROOT / "experiments" / "04_radiomics_brats.py"


def _radiomics_mod():
    spec = importlib.util.spec_from_file_location("radiomics_brats", _RADIOMICS)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def features_for_case(case_dir: Path, modality: str = "t1c") -> dict[str, float | str]:
    import nibabel as nib

    mod = _radiomics_mod()
    case_id = mod.case_id_from_dir(case_dir)
    img_path = mod.find_modality(case_dir, case_id, modality)
    seg_path = mod.find_seg(case_dir, case_id)
    if img_path is None or seg_path is None:
        raise FileNotFoundError(f"{case_id}: missing {modality} or seg")

    img = np.asanyarray(nib.load(str(img_path)).dataobj).astype(np.float32)
    seg = np.asanyarray(nib.load(str(seg_path)).dataobj).astype(np.int16)

    row: dict[str, float | str] = {"patient_id": case_id, "modality": modality}
    voxel_mm3 = float(np.prod(nib.load(str(seg_path)).header.get_zooms()[:3]))

    for region in ("wt", "et", "net", "edema"):
        mask = mod.region_mask(seg, region)
        if not mask.any():
            continue
        voxels = int(mask.sum())
        row[f"vol_mm3_{region}"] = voxels * voxel_mm3
        vals = img[mask]
        row[f"mean_{modality}_{region}"] = float(np.mean(vals))
        row[f"std_{modality}_{region}"] = float(np.std(vals))
        row[f"median_{modality}_{region}"] = float(np.median(vals))

    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw/brats2024_training"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/radiomics_features.csv"))
    parser.add_argument("--modality", default="t1c", choices=("t1n", "t1c", "t2w", "t2f"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--require-seg", action="store_true")
    args = parser.parse_args()

    mod = _radiomics_mod()
    patients = mod.find_patient_dirs(args.data_dir, require_seg=args.require_seg)
    if args.limit:
        patients = patients[: args.limit]

    rows: list[dict] = []
    errors: list[tuple[str, str]] = []
    for i, case_dir in enumerate(patients, 1):
        case_id = mod.case_id_from_dir(case_dir)
        try:
            rows.append(features_for_case(case_dir, args.modality))
            if i % 50 == 0 or i == len(patients):
                print(f"[{i}/{len(patients)}] {case_id}")
        except Exception as exc:
            errors.append((case_id, str(exc)))
            print(f"[{i}/{len(patients)}] SKIP {case_id}: {exc}")

    if not rows:
        raise SystemExit("No features extracted.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False)
    print(f"Wrote {len(rows)} cases -> {args.output.resolve()}")
    if errors:
        print(f"Skipped {len(errors)} cases")


if __name__ == "__main__":
    main()
