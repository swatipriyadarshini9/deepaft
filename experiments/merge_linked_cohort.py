#!/usr/bin/env python3
"""Merge crosswalk + GDC survival + genes + optional radiomics → linked_cohort.csv."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def normalize_barcode(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper()


def merge_radiomics(merged: pd.DataFrame, radiomics: pd.DataFrame) -> pd.DataFrame:
    """Join radiomics on brats_id (patient_id column in radiomics output)."""
    radio = radiomics.copy()
    key = "patient_id" if "patient_id" in radio.columns else radio.columns[0]
    radio = radio.rename(columns={key: "brats_id"})
    radio["brats_id"] = radio["brats_id"].astype(str).str.strip()

    meta_cols = {"brats_id", "modality", "patient_id"}
    feature_cols = [c for c in radio.columns if c not in meta_cols]
    if not feature_cols:
        return merged

    return merged.merge(radio[["brats_id"] + feature_cols], on="brats_id", how="left")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crosswalk", type=Path, default=Path("data/processed/brats_tcga_crosswalk.csv"))
    parser.add_argument(
        "--survival",
        type=Path,
        default=Path("data/processed/gdc_survival.csv"),
        help="GDC survival table (case_id, time_days, event, ...)",
    )
    parser.add_argument(
        "--cohort",
        type=Path,
        default=Path("data/processed/tcga_glioma_cohort.csv"),
        help="TCGA gene expression cohort (optional enrichment)",
    )
    parser.add_argument("--radiomics", type=Path, default=None, help="radiomics_features.csv from experiment 04")
    parser.add_argument("--output", type=Path, default=Path("data/processed/linked_cohort.csv"))
    args = parser.parse_args()

    if not args.crosswalk.exists():
        raise SystemExit(
            f"Crosswalk missing: {args.crosswalk}\n"
            "Run: python experiments/02_build_tcga_crosswalk.py --auto-find"
        )

    surv_path = args.survival if args.survival.exists() else args.cohort
    if not surv_path.exists():
        raise SystemExit("Need gdc_survival.csv or tcga_glioma_cohort.csv for survival columns.")

    xw = pd.read_csv(args.crosswalk)
    surv = pd.read_csv(surv_path)

    case_col = "case_id" if "case_id" in surv.columns else "tcga_barcode"
    xw["tcga_barcode"] = normalize_barcode(xw["tcga_barcode"])
    surv[case_col] = normalize_barcode(surv[case_col])

    merged = xw.merge(surv, left_on="tcga_barcode", right_on=case_col, how="inner")

    if args.cohort.exists() and args.cohort != surv_path:
        cohort = pd.read_csv(args.cohort)
        ckey = "case_id" if "case_id" in cohort.columns else cohort.columns[0]
        cohort[ckey] = normalize_barcode(cohort[ckey])
        gene_cols = [c for c in ("IDH1", "MGMT", "TP53") if c in cohort.columns]
        if gene_cols:
            merged = merged.merge(
                cohort[[ckey] + gene_cols],
                left_on="tcga_barcode",
                right_on=ckey,
                how="left",
            )

    if args.radiomics and args.radiomics.exists():
        radio = pd.read_csv(args.radiomics)
        merged = merge_radiomics(merged, radio)
        n_radio = merged.filter(like="radiomics_").notna().any(axis=1).sum()
        print(f"Cases with radiomics features: {n_radio}")

    if "project" not in merged.columns:
        if "project_x" in merged.columns:
            merged["project"] = merged["project_x"]
        elif "project_y" in merged.columns:
            merged["project"] = merged["project_y"]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(args.output, index=False)

    print(f"BraTS mapping rows: {len(xw)}")
    print(f"TCGA-linked with survival: {len(merged)}")
    if "event" in merged.columns:
        print(f"Events: {int(merged['event'].sum())} / {len(merged)}")
    print(f"Wrote {args.output.resolve()}")


if __name__ == "__main__":
    main()
