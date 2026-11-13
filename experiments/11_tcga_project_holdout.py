#!/usr/bin/env python3
"""External-style validation: train Log-normal AFT on TCGA-LGG, test on TCGA-GBM (and reverse)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import importlib.util

_metrics = importlib.util.spec_from_file_location("metrics", ROOT / "src" / "deepaft" / "metrics.py")
assert _metrics and _metrics.loader
_metrics_mod = importlib.util.module_from_spec(_metrics)
_metrics.loader.exec_module(_metrics_mod)
harrell_c_index = _metrics_mod.harrell_c_index
amse = _metrics_mod.amse

_cens = importlib.util.spec_from_file_location("censoring", ROOT / "src" / "deepaft" / "censoring.py")
assert _cens and _cens.loader
_cens_mod = importlib.util.module_from_spec(_cens)
_cens.loader.exec_module(_cens_mod)
censoring_survival = _cens_mod.censoring_survival

from benchmarks import LogNormalAFTBaseline  # noqa: E402

GENE_COLS = ["IDH1", "MGMT", "TP53"]


def eval_split(df_tr: pd.DataFrame, df_te: pd.DataFrame) -> dict:
    X_tr = df_tr[GENE_COLS].values.astype(float)
    X_te = df_te[GENE_COLS].values.astype(float)
    time_col = "time_days" if "time_days" in df_tr.columns else "time"
    t_tr, e_tr = df_tr[time_col].values, df_tr["event"].values.astype(bool)
    t_te, e_te = df_te[time_col].values, df_te["event"].values.astype(bool)
    model = LogNormalAFTBaseline()
    model.fit(X_tr, t_tr, e_tr)
    pred = model.predict_time(X_te)
    ghat = censoring_survival(t_te, e_te, mode="marginal")
    log_pred = np.log(np.clip(pred, 1e-8, None))
    return {
        "n_train": len(df_tr),
        "n_test": len(df_te),
        "c_index": round(float(harrell_c_index(pred, t_te, e_te)), 4),
        "amse": round(float(amse(log_pred, t_te, e_te, ghat)), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", type=Path, default=Path("data/processed/tcga_glioma_cohort.csv"))
    parser.add_argument("--output", type=Path, default=Path("results/tables/glioma_benchmark_external.csv"))
    args = parser.parse_args()

    df = pd.read_csv(args.cohort)
    if "project" not in df.columns:
        raise SystemExit("Need project column for LGG/GBM holdout")

    rows = []
    for train_proj, test_proj in (("TCGA-LGG", "TCGA-GBM"), ("TCGA-GBM", "TCGA-LGG")):
        tr = df[df["project"] == train_proj]
        te = df[df["project"] == test_proj]
        if len(tr) < 30 or len(te) < 30:
            continue
        r = eval_split(tr, te)
        r["train_project"] = train_proj
        r["test_project"] = test_proj
        r["model"] = "lognormal_aft"
        rows.append(r)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
