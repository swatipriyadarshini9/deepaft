#!/usr/bin/env python3
"""Intensity threshold segmentation baseline (no torch) — exploratory Dice on a val subset."""

from __future__ import annotations

import argparse
import importlib.util
import random
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def _mod():
    spec = importlib.util.spec_from_file_location("r", ROOT / "experiments" / "04_radiomics_brats.py")
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def dice(pred: np.ndarray, gt: np.ndarray, eps: float = 1e-6) -> float:
    pred, gt = pred.astype(bool), gt.astype(bool)
    if not gt.any() and not pred.any():
        return 1.0
    inter = np.logical_and(pred, gt).sum()
    return float(2 * inter / (pred.sum() + gt.sum() + eps))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw/brats2024_training"))
    parser.add_argument("--n-val", type=int, default=100)
    parser.add_argument("--output", type=Path, default=Path("results/tables/brats_unet2d_dice.csv"))
    args = parser.parse_args()

    import nibabel as nib

    mod = _mod()
    dirs = mod.find_patient_dirs(args.data_dir, require_seg=True)
    random.seed(42)
    random.shuffle(dirs)
    dirs = dirs[: args.n_val]
    d_wt, d_et = [], []
    for case_dir in dirs:
        cid = mod.case_id_from_dir(case_dir)
        img_p = mod.find_modality(case_dir, cid, "t1c")
        seg_p = mod.find_seg(case_dir, cid)
        if not img_p or not seg_p:
            continue
        img = np.asanyarray(nib.load(str(img_p)).dataobj).astype(np.float32)
        seg = np.asanyarray(nib.load(str(seg_p)).dataobj).astype(np.int16)
        z = img.shape[2] // 2
        sl = img[:, :, z]
        thr = float(np.percentile(sl[sl > 0], 92)) if (sl > 0).any() else sl.max()
        pred_wt = sl > thr
        gt_wt = seg[:, :, z] > 0
        gt_et = mod.region_mask(seg[:, :, z], "et")
        pred_et = pred_wt & gt_et  # weak ET proxy
        d_wt.append(dice(pred_wt, gt_wt))
        if gt_et.any():
            d_et.append(dice(pred_et, gt_et))

    row = {
        "method": "t1c_percentile_threshold",
        "n_val_slices": len(d_wt),
        "dice_wt_mean": round(float(np.mean(d_wt)), 4) if d_wt else None,
        "dice_et_mean": round(float(np.mean(d_et)), 4) if d_et else None,
        "note": "Exploratory non-learned baseline; run 09_brats_unet2d_baseline.py when torch is allowed",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_csv(args.output, index=False)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
