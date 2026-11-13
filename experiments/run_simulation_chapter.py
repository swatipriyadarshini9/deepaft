#!/usr/bin/env python3
"""
Simulation chapter: scenarios A-D comparing Norman deepAFT vs extensions vs baselines.

Outputs CSV tables to results/tables/ (thesis-ready simulation results, not fabricated).

Usage:
  python experiments/run_simulation_chapter.py
  python experiments/run_simulation_chapter.py --replications 50 --epochs 80
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from benchmarks import available_baselines  # noqa: E402
from deepaft import DeepAFT, amse, harrell_c_index, scenario_a, scenario_b, scenario_c, scenario_d  # noqa: E402
from deepaft.censoring import censoring_survival  # noqa: E402


def train_test_split(n: int, seed: int, frac: float = 0.75) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    idx = np.arange(n)
    rng.shuffle(idx)
    n_train = int(n * frac)
    return idx[:n_train], idx[n_train:]


def eval_model(name: str, pred_time: np.ndarray, y_time: np.ndarray, y_event: np.ndarray, pred_log: np.ndarray | None = None) -> dict:
    ghat = censoring_survival(y_time, y_event, mode="marginal")
    row = {
        "model": name,
        "c_index": harrell_c_index(pred_time, y_time, y_event),
    }
    if pred_log is not None:
        row["amse"] = amse(pred_log, y_time, y_event, ghat)
    return row


def run_one_replication(
    scenario: str,
    seed: int,
    epochs: int,
) -> list[dict]:
    groups = None
    if scenario == "A":
        X, time, event = scenario_a(n=300, seed=seed)
    elif scenario == "B":
        X, time, event, groups = scenario_b(n=300, seed=seed)
    elif scenario == "C":
        X, time, event = scenario_c(n=300, seed=seed)
    elif scenario == "D":
        X, time, event, groups = scenario_d(n=300, seed=seed)
    else:
        raise ValueError(scenario)

    tr, te = train_test_split(len(X), seed)
    X_tr, X_te = X[tr], X[te]
    t_tr, t_te = time[tr], time[te]
    e_tr, e_te = event[tr], event[te]
    g_tr = groups[tr] if groups is not None else None
    g_te = groups[te] if groups is not None else None

    rows: list[dict] = []

    # Norman: Buckley-James
    m_bj = DeepAFT(method="buckley_james", hidden=(8, 6), epochs=epochs, random_state=seed)
    m_bj.fit(X_tr, t_tr, e_tr)
    pred = m_bj.predict_time(X_te)
    rows.append({**eval_model("deepAFT_BJ", pred, t_te, e_te, np.log(np.clip(pred, 1e-8, None))), "scenario": scenario, "rep": seed})

    # Extension: covariate censoring (B, D)
    if scenario in ("B", "D") and g_tr is not None:
        m_cov = DeepAFT(
            method="buckley_james",
            censoring="covariate",
            hidden=(8, 6),
            epochs=epochs,
            random_state=seed,
        )
        m_cov.fit(X_tr, t_tr, e_tr, groups=g_tr)
        pred = m_cov.predict_time(X_te, groups=g_te)
        rows.append({**eval_model("deepAFT_BJ_covariate", pred, t_te, e_te), "scenario": scenario, "rep": seed})

    # Extension: group scale (D)
    if scenario == "D" and g_tr is not None:
        m_grp = DeepAFT(
            method="buckley_james",
            scale="group",
            hidden=(8, 6),
            epochs=epochs,
            random_state=seed,
        )
        m_grp.fit(X_tr, t_tr, e_tr, groups=g_tr)
        pred = m_grp.predict_time(X_te, groups=g_te)
        rows.append({**eval_model("deepAFT_BJ_group_scale", pred, t_te, e_te), "scenario": scenario, "rep": seed})

    # Scenario C: IPCW should fallback
    if scenario == "C":
        m_ipcw = DeepAFT(method="ipcw", auto_fallback=True, hidden=(8, 6), epochs=epochs, random_state=seed)
        m_ipcw.fit(X_tr, t_tr, e_tr)
        pred = m_ipcw.predict_time(X_te)
        rows.append({
            **eval_model("deepAFT_IPCW_or_fallback", pred, t_te, e_te),
            "scenario": scenario,
            "rep": seed,
            "effective_method": m_ipcw.effective_method,
            "fallback_reason": m_ipcw.fallback_reason or "",
        })

    # Baselines
    for bname, cls in available_baselines().items():
        try:
            model = cls()
            model.fit(X_tr, t_tr, e_tr)
            pred = model.predict_time(X_te)
            rows.append({**eval_model(bname, pred, t_te, e_te), "scenario": scenario, "rep": seed})
        except Exception as exc:
            rows.append({"model": bname, "scenario": scenario, "rep": seed, "c_index": float("nan"), "error": str(exc)})

    return rows


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    agg = df.groupby(["scenario", "model"], dropna=False).agg(
        c_index_mean=("c_index", "mean"),
        c_index_std=("c_index", "std"),
        n=("c_index", "count"),
    )
    if "amse" in df.columns:
        amse_agg = df.groupby(["scenario", "model"])["amse"].agg(["mean", "std"])
        agg = agg.join(amse_agg.add_prefix("amse_"))
    return agg.reset_index()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run simulation chapter scenarios A-D")
    parser.add_argument("--replications", type=int, default=10, help="Monte Carlo replications per scenario")
    parser.add_argument("--epochs", type=int, default=60, help="Training epochs for neural models")
    parser.add_argument("--scenarios", nargs="+", default=["A", "B", "C", "D"])
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore existing simulation_chapter_raw.csv and start fresh",
    )
    args = parser.parse_args()

    out_dir = ROOT / "results" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "simulation_chapter_raw.csv"
    sum_path = out_dir / "simulation_chapter_summary.csv"

    all_rows: list[dict] = []
    done_seeds: set[int] = set()
    if not args.no_resume and raw_path.exists():
        prev = pd.read_csv(raw_path)
        all_rows = prev.to_dict(orient="records")
        if "rep" in prev.columns:
            done_seeds = set(prev["rep"].astype(int).tolist())
        print(f"Resume: loaded {len(all_rows)} rows; {len(done_seeds)} replications complete")

    def checkpoint() -> None:
        raw = pd.DataFrame(all_rows)
        raw.to_csv(raw_path, index=False)
        summarize(raw).to_csv(sum_path, index=False)

    checkpoint_every = max(1, args.replications // 10)

    for sc in args.scenarios:
        print(f"Scenario {sc} ({args.replications} replications, epochs={args.epochs})...", flush=True)
        n_new = 0
        for rep in range(args.replications):
            seed = rep + 1000 * (ord(sc[0]) - ord("A") + 1)
            if seed in done_seeds:
                continue
            if rep == 0 or (rep + 1) % checkpoint_every == 0:
                print(f"  {sc} rep {rep + 1}/{args.replications} (seed={seed})", flush=True)
            all_rows.extend(run_one_replication(sc, seed, args.epochs))
            done_seeds.add(seed)
            n_new += 1
            if n_new % checkpoint_every == 0:
                checkpoint()
                print(f"  checkpoint -> {raw_path.name} ({len(all_rows)} rows)", flush=True)

        checkpoint()
        print(f"  scenario {sc} done -> {raw_path.name} ({len(all_rows)} rows)", flush=True)

    raw = pd.DataFrame(all_rows)
    summary = summarize(raw)
    raw.to_csv(raw_path, index=False)
    summary.to_csv(sum_path, index=False)

    print(f"\nWrote {raw_path}")
    print(f"Wrote {sum_path}")
    print("\nSummary (C-index mean by scenario/model):")
    print(summary.pivot(index="model", columns="scenario", values="c_index_mean").round(3).to_string())

    gen = ROOT / "experiments" / "generate_thesis_results.py"
    if gen.exists():
        print("\nRegenerating results/thesis_results.md ...", flush=True)
        subprocess.run([sys.executable, str(gen)], cwd=ROOT, check=False)


if __name__ == "__main__":
    main()
