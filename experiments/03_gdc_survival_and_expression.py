#!/usr/bin/env python3
"""
Fetch TCGA-LGG and TCGA-GBM clinical survival from GDC API (current vital status).

Uses expanded demographic + follow_ups for days_to_death / follow-up time.

Usage:
  python experiments/03_gdc_survival_and_expression.py \\
    --projects TCGA-LGG TCGA-GBM \\
    --output data/processed/gdc_survival.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import requests

GDC_CASES = "https://api.gdc.cancer.gov/cases"


def fetch_cases(project_id: str, page_size: int = 500) -> list[dict]:
    filters = {
        "op": "and",
        "content": [{"op": "in", "content": {"field": "project.project_id", "value": [project_id]}}],
    }
    fields = "submitter_id,demographic.vital_status,demographic.days_to_death"
    offset = 0
    hits: list[dict] = []
    while True:
        params = {
            "filters": json.dumps(filters),
            "fields": fields,
            "expand": "demographic,follow_ups,diagnoses",
            "format": "JSON",
            "size": str(page_size),
            "from": str(offset),
        }
        resp = requests.get(GDC_CASES, params=params, timeout=120)
        resp.raise_for_status()
        batch = resp.json()["data"]["hits"]
        if not batch:
            break
        hits.extend(batch)
        offset += page_size
        if len(batch) < page_size:
            break
    return hits


def _max_follow_up(case: dict) -> float | None:
    days: list[float] = []
    for fu in case.get("follow_ups") or []:
        d = fu.get("days_to_follow_up")
        if d is not None and str(d) not in ("", "'--"):
            days.append(float(d))
    for diag in case.get("diagnoses") or []:
        d = diag.get("days_to_last_follow_up")
        if d is not None and str(d) not in ("", "'--"):
            days.append(float(d))
    return max(days) if days else None


def case_to_row(case: dict, project_id: str) -> dict | None:
    demo = case.get("demographic") or {}
    vital = (demo.get("vital_status") or "").strip().lower()
    days_death = demo.get("days_to_death")

    if vital == "dead":
        if days_death is None or str(days_death) in ("", "'--"):
            days_death = _max_follow_up(case)
        if days_death is None:
            return None
        time = float(days_death)
        event = 1
    elif vital == "alive":
        days_fup = _max_follow_up(case)
        if days_fup is None:
            return None
        time = float(days_fup)
        event = 0
    else:
        return None

    if time <= 0:
        return None

    return {
        "case_id": case["submitter_id"],
        "project": project_id,
        "time_days": time,
        "event": event,
        "vital_status": demo.get("vital_status", ""),
    }


def cases_to_dataframe(hits: list[dict], project_id: str) -> pd.DataFrame:
    rows = [case_to_row(h, project_id) for h in hits]
    rows = [r for r in rows if r is not None]
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projects", nargs="+", default=["TCGA-LGG", "TCGA-GBM"])
    parser.add_argument("--output", type=Path, default=Path("data/processed/gdc_survival.csv"))
    args = parser.parse_args()

    frames = [cases_to_dataframe(fetch_cases(p), p) for p in args.projects]
    df = pd.concat(frames, ignore_index=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    n_events = int(df["event"].sum())
    print(f"Wrote {len(df)} cases to {args.output}")
    print(f"Events: {n_events}/{len(df)} ({100*n_events/len(df):.1f}%)")
    print("Use GDC/Xena for expression; do NOT use OncoLnc 2016 vital status for GBM.")


if __name__ == "__main__":
    main()
