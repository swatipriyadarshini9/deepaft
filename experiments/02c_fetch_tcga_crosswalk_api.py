#!/usr/bin/env python3
"""
Build BraTS-GLI → TCGA case crosswalk from public GDC API + PTG demographics.

The official BraTS→TCGA spreadsheet (syn51615438) is Synapse access-controlled.
When that file is unavailable, this script links cases by **unique** demographic
agreement (project LGG/GBM, age, sex) between:

  - `data/processed/brats_ptg_metadata.csv` (from ingest_ptg_metadata.py)
  - GDC `cases` endpoint (TCGA-LGG, TCGA-GBM)

Output includes `match_method` and `match_confidence` for audit. Review low-confidence
rows before thesis claims. Prefer the official mapping when you have Synapse access.

Usage:
  python experiments/02c_fetch_tcga_crosswalk_api.py
  python experiments/02c_fetch_tcga_crosswalk_api.py --age-tolerance 2
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

GDC_CASES = "https://api.gdc.cancer.gov/cases"

GBM_TYPES = {
    "glioblastoma",
    "glioblastoma multiforme",
    "gbm",
}
LGG_TYPES = {
    "oligodendroglioma",
    "astrocytoma",
    "oligoastrocytoma",
    "glioma nos",
    "glioma",
    "anaplastic astrocytoma",
    "anaplastic oligodendroglioma",
    "low grade glioma",
}


def patient_key(brats_id: str) -> str:
    """BraTS-GLI-01234-101 -> BraTS-GLI-01234 (one row per patient for matching)."""
    m = re.match(r"(BraTS-GLI-\d+)", str(brats_id).strip(), re.I)
    return m.group(1) if m else str(brats_id).strip()


def normalize_glioma_type(val: str) -> str:
    return re.sub(r"\s+", " ", str(val).strip().lower())


def project_hint(glioma_type: str) -> str | None:
    g = normalize_glioma_type(glioma_type)
    if any(k in g for k in GBM_TYPES):
        return "TCGA-GBM"
    if any(k in g for k in LGG_TYPES):
        return "TCGA-LGG"
    return None


def normalize_sex(val: str) -> str | None:
    s = str(val).strip().upper()
    if s in ("M", "MALE"):
        return "male"
    if s in ("F", "FEMALE"):
        return "female"
    return None


def fetch_gdc_glioma_cases() -> pd.DataFrame:
    filters = {
        "op": "and",
        "content": [
            {
                "op": "in",
                "content": {"field": "project.project_id", "value": ["TCGA-LGG", "TCGA-GBM"]},
            }
        ],
    }
    fields = (
        "submitter_id,project.project_id,"
        "demographic.sex_at_birth,demographic.age_at_index,"
        "diagnoses.primary_diagnosis"
    )
    rows: list[dict] = []
    offset = 0
    page_size = 500
    total = None
    while True:
        params = {
            "filters": json.dumps(filters),
            "fields": fields,
            "expand": "demographic,diagnoses",
            "format": "JSON",
            "size": str(page_size),
            "from": str(offset),
        }
        url = GDC_CASES + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=120) as resp:
            payload = json.loads(resp.read())
        hits = payload["data"]["hits"]
        if total is None:
            total = payload["data"]["pagination"]["total"]
        for case in hits:
            demo = case.get("demographic") or {}
            diags = case.get("diagnoses") or []
            diag = diags[0].get("primary_diagnosis") if diags else None
            gender = (demo.get("sex_at_birth") or demo.get("gender") or "").strip().lower()
            age = demo.get("age_at_index")
            if age is None and diags:
                days = diags[0].get("age_at_diagnosis")
                if days is not None:
                    try:
                        age = int(float(days) / 365.25)
                    except (TypeError, ValueError):
                        age = None
            rows.append(
                {
                    "tcga_barcode": case["submitter_id"].upper(),
                    "project": case["project"]["project_id"],
                    "gender": gender,
                    "age_years": int(age) if age is not None else None,
                    "primary_diagnosis": diag,
                }
            )
        offset += page_size
        if offset >= total or not hits:
            break
    return pd.DataFrame(rows)


def load_brats_patients(metadata_path: Path) -> pd.DataFrame:
    meta = pd.read_csv(metadata_path)
    meta["patient_key"] = meta["brats_id"].map(patient_key)
    meta["project_hint"] = meta["glioma_type"].map(project_hint)
    meta["gender"] = meta["sex"].map(normalize_sex)
    meta["age_years"] = pd.to_numeric(meta["age"], errors="coerce").astype("Int64")

    # One record per patient: prefer lowest timepoint suffix (-100)
    meta["_suffix"] = meta["brats_id"].str.extract(r"-(\d+)$").astype(float)
    meta = meta.sort_values(["patient_key", "_suffix"])
    patients = meta.groupby("patient_key", as_index=False).first()
    return patients


def diagnosis_keywords(glioma_type: str) -> list[str]:
    g = normalize_glioma_type(glioma_type)
    if "glioblast" in g:
        return ["glioblast", "gbm"]
    if "oligodendroglioma" in g:
        return ["oligodendroglioma"]
    if "astrocytoma" in g:
        return ["astrocytoma"]
    if "glioma" in g:
        return ["glioma"]
    return []


def refine_pool(pool: pd.DataFrame, glioma_type: str) -> pd.DataFrame:
    keys = diagnosis_keywords(glioma_type)
    if not keys or pool.empty:
        return pool
    diag = pool["primary_diagnosis"].fillna("").str.lower()
    mask = False
    for k in keys:
        mask = mask | diag.str.contains(k, na=False)
    narrowed = pool[mask]
    return narrowed if not narrowed.empty else pool


def match_patients(
    brats: pd.DataFrame, gdc: pd.DataFrame, age_tolerance: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    gdc = gdc.dropna(subset=["age_years", "gender"])
    gdc = gdc[gdc["gender"].isin(("male", "female"))]

    linked_rows: list[dict] = []
    ambiguous: list[dict] = []

    for _, row in brats.iterrows():
        if row["project_hint"] is None or pd.isna(row["age_years"]) or row["gender"] is None:
            continue
        age = int(row["age_years"])
        pool = gdc[
            (gdc["project"] == row["project_hint"])
            & (gdc["gender"] == row["gender"])
            & (gdc["age_years"].between(age - age_tolerance, age + age_tolerance))
        ]
        pool = refine_pool(pool, str(row["glioma_type"]))
        if len(pool) == 1:
            hit = pool.iloc[0]
            linked_rows.append(
                {
                    "brats_id": row["brats_id"],
                    "patient_key": row["patient_key"],
                    "tcga_barcode": hit["tcga_barcode"],
                    "project": hit["project"],
                    "match_method": "gdc_demographic_unique",
                    "match_confidence": "high" if age_tolerance == 0 else "medium",
                    "brats_age": age,
                    "brats_glioma_type": row["glioma_type"],
                    "gdc_age": int(hit["age_years"]),
                    "gdc_diagnosis": hit["primary_diagnosis"],
                }
            )
        elif len(pool) > 1:
            ambiguous.append(
                {
                    "brats_id": row["brats_id"],
                    "patient_key": row["patient_key"],
                    "n_candidates": len(pool),
                    "project_hint": row["project_hint"],
                    "age": age,
                    "gender": row["gender"],
                }
            )

    # Expand to all BraTS timepoint IDs sharing patient_key
    cross = pd.DataFrame(linked_rows)
    if cross.empty:
        return cross, pd.DataFrame(ambiguous)

    meta = pd.read_csv(Path("data/processed/brats_ptg_metadata.csv"))
    meta["patient_key"] = meta["brats_id"].map(patient_key)
    expanded = meta.merge(
        cross.drop(columns=["brats_id"]),
        on="patient_key",
        how="inner",
    )
    out = expanded[
        [
            "brats_id",
            "tcga_barcode",
            "project",
            "match_method",
            "match_confidence",
            "official_split",
        ]
    ].drop_duplicates(subset=["brats_id"])
    return out, pd.DataFrame(ambiguous)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, default=Path("data/processed/brats_ptg_metadata.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/brats_tcga_crosswalk.csv"))
    parser.add_argument("--ambiguous", type=Path, default=Path("data/processed/brats_tcga_crosswalk_ambiguous.csv"))
    parser.add_argument("--age-tolerance", type=int, default=1, help="Years ± for age match (default 1)")
    args = parser.parse_args()

    if not args.metadata.exists():
        raise SystemExit(f"Missing {args.metadata}. Run ingest_ptg_metadata.py first.")

    print("Fetching GDC TCGA-LGG/GBM cases ...")
    gdc = fetch_gdc_glioma_cases()
    print(f"GDC cases: {len(gdc)}")

    brats = load_brats_patients(args.metadata)
    print(f"BraTS patients (deduped): {len(brats)}")

    cross, amb = match_patients(brats, gdc, args.age_tolerance)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cross.to_csv(args.output, index=False)
    amb.to_csv(args.ambiguous, index=False)

    print(f"Linked BraTS timepoints: {len(cross)}")
    print(f"Ambiguous (skipped): {len(amb)}")
    print(f"Wrote {args.output.resolve()}")
    if len(cross) == 0:
        raise SystemExit(
            "No unique matches. Request Synapse syn51615438 mapping or increase --age-tolerance with caution."
        )
    if len(cross) < 30:
        print(
            "WARNING: few links — prefer an official BraTS GLI PTG↔TCGA mapping spreadsheet when the challenge publishes it."
        )


if __name__ == "__main__":
    main()
