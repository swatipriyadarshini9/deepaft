#!/usr/bin/env python3
"""Write BraTS GLI cohort counts under data/raw to JSON + CSV for thesis tables."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "data" / "raw" / "brats2024_training"


def main() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("radiomics", ROOT / "experiments" / "04_radiomics_brats.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    data_dir = DEFAULT_DIR
    all_cases = mod.find_patient_dirs(data_dir, require_seg=False)
    seg_cases = mod.find_patient_dirs(data_dir, require_seg=True)

    by_parent: dict[str, int] = {}
    for p in all_cases:
        key = str(p.parent.name)
        by_parent[key] = by_parent.get(key, 0) + 1

    out = {
        "data_dir": str(data_dir),
        "n_cases_total": len(all_cases),
        "n_cases_with_seg": len(seg_cases),
        "by_immediate_parent": by_parent,
    }

    tables = ROOT / "results" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    json_path = tables / "brats_cohort_inventory.json"
    json_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    rows = [{"split_folder": k, "n_cases": v} for k, v in sorted(by_parent.items())]
    rows.append({"split_folder": "_TOTAL", "n_cases": len(all_cases)})
    rows.append({"split_folder": "_WITH_SEG", "n_cases": len(seg_cases)})
    pd.DataFrame(rows).to_csv(tables / "brats_cohort_counts.csv", index=False)
    print(f"Wrote {json_path} and brats_cohort_counts.csv ({len(all_cases)} cases, {len(seg_cases)} with seg)")


if __name__ == "__main__":
    main()
