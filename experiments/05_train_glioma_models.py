#!/usr/bin/env python3
"""
Train deepAFT and baselines on TCGA glioma cohort with stratified K-fold CV.

Usage:
  python experiments/05_train_glioma_models.py \\
    --cohort data/processed/tcga_glioma_cohort.csv \\
    --output results/tables/glioma_benchmark.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from benchmarks import available_baselines  # noqa: E402
from deepaft import DeepAFT, amse, harrell_c_index  # noqa: E402
from deepaft.censoring import censoring_survival  # noqa: E402

GENE_COLS = ["IDH1", "MGMT", "TP53"]


def load_feature_sets(df: pd.DataFrame) -> dict[str, np.ndarray]:
    gene_cols = [c for c in GENE_COLS if c in df.columns]
    if not gene_cols:
        raise ValueError(f"Expected gene columns {GENE_COLS} in cohort")
    radio_cols = [c for c in df.columns if c.startswith("radiomics_") or c.startswith("shape_")]
    sets: dict[str, np.ndarray] = {"genes": df[gene_cols].values.astype(float)}
    if radio_cols:
        sets["radiomics"] = df[radio_cols].values.astype(float)
        sets["genes_radiomics"] = df[gene_cols + radio_cols].values.astype(float)
    return sets


def project_groups(df: pd.DataFrame) -> np.ndarray | None:
    if "project" not in df.columns:
        return None
    return (df["project"] == "TCGA-GBM").astype(int).values


def run_ph_test(X: np.ndarray, time: np.ndarray, event: np.ndarray, gene_names: list[str] | None = None) -> dict:
    try:
        from lifelines import CoxPHFitter
        from lifelines.statistics import proportional_hazard_test
    except ImportError:
        return {"ph_p_global": None, "ph_p_by_covariate": {}, "ph_note": "lifelines missing"}

    cols = gene_names if gene_names and len(gene_names) == X.shape[1] else [f"x{i}" for i in range(X.shape[1])]
    d = pd.DataFrame(X, columns=cols)
    d["time"] = time
    d["event"] = event
    cph = CoxPHFitter(penalizer=0.01)
    cph.fit(d, duration_col="time", event_col="event")
    try:
        ph = proportional_hazard_test(cph, d, time_transform="rank")
        summary = ph.summary
        p_col = "p" if "p" in summary.columns else summary.columns[-1]
        by_cov = {str(idx): float(summary.loc[idx, p_col]) for idx in summary.index}
        min_p = min(by_cov.values()) if by_cov else None
        worst = min(by_cov, key=by_cov.get) if by_cov else None
        return {
            "ph_p_global": min_p,
            "ph_p_by_covariate": by_cov,
            "ph_worst_covariate": worst,
            "ph_note": "Schoenfeld proportional_hazard_test (lifelines, rank transform)",
        }
    except Exception as exc:
        return {"ph_p_global": None, "ph_p_by_covariate": {}, "ph_note": str(exc)}


def eval_fold(
    model_name: str,
    model,
    X_te: np.ndarray,
    t_te: np.ndarray,
    e_te: np.ndarray,
    groups_te: np.ndarray | None = None,
) -> dict:
    if model_name.startswith("deepAFT"):
        pred = model.predict_time(X_te, groups=groups_te)
    else:
        pred = model.predict_time(X_te)
    ghat = censoring_survival(t_te, e_te, mode="marginal")
    log_pred = np.log(np.clip(pred, 1e-8, None))
    return {
        "c_index": harrell_c_index(pred, t_te, e_te),
        "amse": amse(log_pred, t_te, e_te, ghat),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cohort",
        type=Path,
        default=Path("data/processed/tcga_glioma_cohort.csv"),
    )
    parser.add_argument("--output", type=Path, default=Path("results/tables/glioma_benchmark.csv"))
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not args.cohort.exists():
        raise SystemExit(
            f"Cohort missing: {args.cohort}\n"
            "Run: python experiments/03_gdc_survival_and_expression.py\n"
            "     python experiments/03b_fetch_tcga_expression.py"
        )

    df = pd.read_csv(args.cohort)
    gene_cols_present = [c for c in GENE_COLS if c in df.columns]
    if gene_cols_present:
        df = df.dropna(subset=gene_cols_present)
    time = df["time_days"].values.astype(float)
    event = df["event"].values.astype(int)
    groups_all = project_groups(df)
    feature_sets = load_feature_sets(df)

    gene_cols = [c for c in GENE_COLS if c in df.columns]
    ph = run_ph_test(feature_sets["genes"], time, event, gene_names=gene_cols)
    print(
        f"Schoenfeld PH test (gene panel): min p={ph.get('ph_p_global', 'NA')}, "
        f"worst={ph.get('ph_worst_covariate', 'NA')}"
    )

    strat = df["project"].astype(str) + "_" + df["event"].astype(str) if "project" in df.columns else event.astype(str)
    skf = StratifiedKFold(n_splits=args.folds, shuffle=True, random_state=args.seed)

    rows: list[dict] = []
    baselines = available_baselines()

    for feat_name, X in feature_sets.items():
        for fold, (tr, te) in enumerate(skf.split(X, strat)):
            X_tr, X_te = X[tr], X[te]
            t_tr, t_te = time[tr], time[te]
            e_tr, e_te = event[tr], event[te]
            g_tr = groups_all[tr] if groups_all is not None else None
            g_te = groups_all[te] if groups_all is not None else None

            # deepAFT with covariate censoring + group scale (LGG vs GBM)
            m = DeepAFT(
                method="buckley_james",
                censoring="covariate",
                scale="group",
                hidden=(8, 6),
                epochs=args.epochs,
                random_state=args.seed + fold,
            )
            m.fit(X_tr, t_tr, e_tr, groups=g_tr)
            metrics = eval_fold("deepAFT", m, X_te, t_te, e_te, g_te)
            rows.append({"features": feat_name, "model": "deepAFT_BJ_group", "fold": fold, **metrics})

            for bname, cls in baselines.items():
                try:
                    b = cls(random_state=args.seed + fold) if bname == "rsf" else cls()
                    b.fit(X_tr, t_tr, e_tr)
                    metrics = eval_fold(bname, b, X_te, t_te, e_te)
                    rows.append({"features": feat_name, "model": bname, "fold": fold, **metrics})
                except Exception as exc:
                    rows.append({
                        "features": feat_name,
                        "model": bname,
                        "fold": fold,
                        "c_index": float("nan"),
                        "amse": float("nan"),
                        "error": str(exc),
                    })

    out = pd.DataFrame(rows)
    summary = out.groupby(["features", "model"], dropna=False).agg(
        c_index_mean=("c_index", "mean"),
        c_index_std=("c_index", "std"),
        amse_mean=("amse", "mean"),
        amse_std=("amse", "std"),
    ).reset_index()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output.with_name("glioma_benchmark_folds.csv"), index=False)
    summary.to_csv(args.output, index=False)

    ph_path = args.output.with_name("glioma_ph_test.json")
    ph_path.write_text(json.dumps(ph, indent=2), encoding="utf-8")

    print("\nSummary:")
    print(summary.to_string(index=False))
    print(f"\nWrote {args.output}")
    print(f"Wrote {ph_path}")


if __name__ == "__main__":
    main()
