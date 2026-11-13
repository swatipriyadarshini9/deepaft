#!/usr/bin/env python3
"""
Fetch IDH1, MGMT, TP53 expression from UCSC Xena HiSeqV2 and merge with GDC survival.

Produces data/processed/tcga_glioma_cohort.csv (TCGA-only; BraTS linkage is separate).

Usage:
  python experiments/03b_fetch_tcga_expression.py
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
SURVIVAL_PATH = ROOT / "data/processed/gdc_survival.csv"
OUTPUT_PATH = ROOT / "data/processed/tcga_glioma_cohort.csv"

GENES = ["IDH1", "MGMT", "TP53"]
XENA_URLS = {
    "TCGA-LGG": "https://tcga.xenahubs.net/download/TCGA.LGG.sampleMap/HiSeqV2.gz",
    "TCGA-GBM": "https://tcga.xenahubs.net/download/TCGA.GBM.sampleMap/HiSeqV2.gz",
}


def case_id_from_sample(sample: str) -> str:
    """TCGA-XX-XXXX from TCGA-XX-XXXX-01Z-..."""
    m = re.match(r"(TCGA-[A-Z0-9]{2}-[A-Z0-9]{4})", sample)
    return m.group(1) if m else sample[:12]


def download_hiseq2(url: str) -> pd.DataFrame:
    print(f"Downloading {url}...", flush=True)
    resp = requests.get(url, timeout=300)
    resp.raise_for_status()
    raw = pd.read_csv(io.BytesIO(resp.content), sep="\t", index_col=0, compression="gzip")
    # rows = genes, cols = samples
    missing = [g for g in GENES if g not in raw.index]
    if missing:
        # try uppercase
        idx_upper = {str(i).upper(): i for i in raw.index}
        for g in missing[:]:
            if g.upper() in idx_upper:
                raw.loc[g] = raw.loc[idx_upper[g.upper()]]
                missing.remove(g)
    avail = [g for g in GENES if g in raw.index]
    if not avail:
        raise RuntimeError(f"No target genes found in {url}")
    sub = raw.loc[avail].T
    sub.index.name = "sample_id"
    sub = sub.reset_index()
    sub["case_id"] = sub["sample_id"].map(case_id_from_sample)
    return sub


def main() -> None:
    if not SURVIVAL_PATH.exists():
        raise SystemExit(f"Run 03_gdc_survival first: {SURVIVAL_PATH} missing")

    surv = pd.read_csv(SURVIVAL_PATH)
    expr_frames = []
    for project, url in XENA_URLS.items():
        df = download_hiseq2(url)
        df["project"] = project
        expr_frames.append(df)

    expr = pd.concat(expr_frames, ignore_index=True)
    # One row per case: mean log2 expression across samples
    gene_cols = [g for g in GENES if g in expr.columns]
    agg = expr.groupby("case_id", as_index=False)[gene_cols].mean()

    cohort = surv.merge(agg, on="case_id", how="inner")
    cohort = cohort.dropna(subset=gene_cols)
    cohort = cohort[cohort["time_days"] > 0]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cohort.to_csv(OUTPUT_PATH, index=False)

    print(f"Survival cases: {len(surv)}")
    print(f"Expression matched: {len(cohort)}")
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Genes: {gene_cols}, events: {cohort['event'].sum()}/{len(cohort)}")


if __name__ == "__main__":
    main()
