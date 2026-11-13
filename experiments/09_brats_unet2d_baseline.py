#!/usr/bin/env python3
"""
2D axial-slice U-Net baseline: predict WT (+ ET channel) vs official seg.

Exploratory segmentation chapter metric (Dice on held-out PTG train cases).

On Windows, run with Python 3.12 if Application Control blocks torch on 3.14:
  py -3.12 experiments/09_brats_unet2d_baseline.py
"""

from __future__ import annotations

import argparse
import importlib.util
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[1]


def _radiomics():
    spec = importlib.util.spec_from_file_location("r", ROOT / "experiments" / "04_radiomics_brats.py")
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def dice_binary(pred: np.ndarray, gt: np.ndarray, eps: float = 1e-6) -> float:
    pred = pred.astype(bool)
    gt = gt.astype(bool)
    if not gt.any() and not pred.any():
        return 1.0
    inter = np.logical_and(pred, gt).sum()
    return float(2 * inter / (pred.sum() + gt.sum() + eps))


class SliceSet(Dataset):
    def __init__(self, case_dirs: list[Path], mod: object, z_mode: str = "center") -> None:
        self.items: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
        import nibabel as nib

        for case_dir in case_dirs:
            cid = mod.case_id_from_dir(case_dir)
            img_p = mod.find_modality(case_dir, cid, "t1c")
            seg_p = mod.find_seg(case_dir, cid)
            if img_p is None or seg_p is None:
                continue
            img = np.asanyarray(nib.load(str(img_p)).dataobj).astype(np.float32)
            seg = np.asanyarray(nib.load(str(seg_p)).dataobj).astype(np.int16)
            z = img.shape[2] // 2 if z_mode == "center" else int(np.argmax((seg > 0).sum(axis=(0, 1))))
            sl = img[:, :, z]
            sl = (sl - sl.mean()) / (sl.std() + 1e-6)
            wt = (seg[:, :, z] > 0).astype(np.float32)
            et_mask = mod.region_mask(seg[:, :, z], "et").astype(np.float32)
            self.items.append((sl, wt, et_mask))

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        sl, wt, et = self.items[idx]
        x = torch.from_numpy(sl[None, ...])
        y = torch.from_numpy(np.stack([wt, et], axis=0))
        return x, y


class TinyUNet(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.enc = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.ReLU(),
        )
        self.dec = nn.Sequential(
            nn.Conv2d(32, 16, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 2, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dec(self.enc(x))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw/brats2024_training"))
    parser.add_argument("--ptg", type=Path, default=Path("data/processed/brats_ptg_metadata.csv"))
    parser.add_argument("--max-train", type=int, default=250)
    parser.add_argument("--max-val", type=int, default=80)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("results/tables/brats_unet2d_dice.csv"))
    args = parser.parse_args()

    mod = _radiomics()
    meta = pd.read_csv(args.ptg)
    train_ids = set(meta.loc[meta["official_split"].astype(str).str.lower() == "train", "brats_id"])
    all_dirs = mod.find_patient_dirs(args.data_dir, require_seg=True)
    train_dirs = [d for d in all_dirs if mod.case_id_from_dir(d) in train_ids]
    random.seed(args.seed)
    random.shuffle(train_dirs)
    n_val = min(args.max_val, max(10, len(train_dirs) // 5))
    val_dirs = train_dirs[:n_val]
    tr_dirs = train_dirs[n_val : n_val + args.max_train]

    train_ds = SliceSet(tr_dirs, mod)
    val_ds = SliceSet(val_dirs, mod)
    if len(train_ds) < 10 or len(val_ds) < 5:
        raise SystemExit("Too few cases for U-Net baseline")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TinyUNet().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.BCEWithLogitsLoss()
    loader = DataLoader(train_ds, batch_size=8, shuffle=True)

    model.train()
    for _ in range(args.epochs):
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            opt.step()

    model.eval()
    d_wt, d_et = [], []
    with torch.no_grad():
        for xb, yb in DataLoader(val_ds, batch_size=1):
            xb = xb.to(device)
            logits = model(xb)
            prob = torch.sigmoid(logits)[0].cpu().numpy()
            gt = yb[0].numpy()
            d_wt.append(dice_binary(prob[0] > 0.5, gt[0] > 0.5))
            d_et.append(dice_binary(prob[1] > 0.5, gt[1] > 0.5))

    row = {
        "n_train_slices": len(train_ds),
        "n_val_slices": len(val_ds),
        "epochs": args.epochs,
        "dice_wt_mean": round(float(np.mean(d_wt)), 4),
        "dice_wt_std": round(float(np.std(d_wt)), 4),
        "dice_et_mean": round(float(np.mean(d_et)), 4),
        "dice_et_std": round(float(np.std(d_et)), 4),
        "note": "2D center/single-slice U-Net exploratory baseline; not nnU-Net challenge tier",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_csv(args.output, index=False)
    print(f"Wrote {args.output}")
    for k, v in row.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
