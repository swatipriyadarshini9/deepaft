#!/usr/bin/env python3
"""
Build BraTS patient ID → TCGA barcode crosswalk from mapping spreadsheet.

The BraTS 2024 GLI release includes a mapping file (xlsx/csv) with BraTS subject
IDs and TCGA/TCIA identifiers for TCGA-derived cases.

Usage:
  python experiments/02_build_tcga_crosswalk.py --mapping data/raw/brats2024_mapping.xlsx
  python experiments/02_build_tcga_crosswalk.py --auto-find --brats-dir data/raw/brats2024_training
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


def find_mapping_file(brats_dir: Path) -> Path | None:
    """Search download tree for BraTS→TCGA mapping spreadsheets."""
    patterns = (
        "*mapping*tcga*",
        "*Mapping*TCGA*",
        "*mapping*tcia*",
        "*Mapping*TCIA*",
        "*BraTS*Mapping*",
        "*crosswalk*",
        "*demographic*metadata*",
        "*supplementary*metadata*",
        "*metadata*.xlsx",
    )
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(brats_dir.rglob(pattern))
    # Prefer xlsx/csv at shallow depth
    candidates = [
        p
        for p in candidates
        if p.is_file() and p.suffix.lower() in (".xlsx", ".xls", ".csv")
    ]
    if not candidates:
        # Fallback: any mapping xlsx in raw data/
        raw = brats_dir.parent if brats_dir.name.startswith("brats") else brats_dir
        candidates = list(raw.glob("*mapping*.xlsx")) + list(raw.glob("*Mapping*.xlsx"))
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: (len(p.parts), str(p)))[0]


def normalize_tcga_barcode(val: str) -> str | None:
    s = str(val).strip().upper()
    if not s or s in ("NAN", "NONE", "NA"):
        return None
    if "TCGA-" in s:
        # Keep full sample barcode when present (TCGA-XX-XXXX-XX)
        parts = s.split("TCGA-", 1)[1]
        return "TCGA-" + parts.split()[0].split(",")[0]
    return None


def load_mapping(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path)
    return pd.read_csv(path)


_YEAR_RE = re.compile(r"BraTS20\d{2}", re.I)


def pick_columns(df: pd.DataFrame) -> tuple[str, str | None, str | None]:
    """Return (brats_id_column, tcga_barcode_column, optional cohort/project_column)."""
    cols = list(df.columns)

    # BraTS subject: prefer newest BraTS20YY column with BraTS-GLI IDs
    year_cols = [c for c in cols if _YEAR_RE.search(str(c))]
    if year_cols:
        def score(col) -> int:
            return int(df[col].astype(str).str.contains(r"BraTS-GLI", case=False, na=False).sum())

        brats_col = max(year_cols, key=score)
    else:
        id_cols = [
            c
            for c in cols
            if any(k in str(c).upper() for k in ("BRA TS", "SUBJECT", "CASE", "PATIENT", "GLI"))
        ]
        if not id_cols:
            id_cols = [c for c in cols if "BraTS" in str(c) or "GLI" in str(c)]
        brats_col = id_cols[0] if id_cols else cols[0]

    tcga_col: str | None = None
    # Some organizer mapping sheets use "Local ID " for the TCGA patient barcode column
    for c in cols:
        if "local id" in str(c).lower():
            tcga_col = c
            break
    if tcga_col is None:
        tcga_cols = [
            c
            for c in cols
            if any(k in str(c).upper() for k in ("TCGA", "TCIA", "BARCODE", "SAMPLE"))
        ]
        tcga_col = tcga_cols[0] if tcga_cols else None
    if tcga_col is None:
        for c in cols:
            if df[c].astype(str).str.contains("TCGA-", case=False, na=False).any():
                tcga_col = c
                break

    cohort_col: str | None = None
    for c in cols:
        if "cohort name" in str(c).lower():
            cohort_col = c
            break

    return brats_col, tcga_col, cohort_col


def _normalize_project(val) -> str | None:
    s = str(val).strip().upper()
    if s in ("", "NAN", "NONE", "NA"):
        return None
    if s.startswith("TCGA-LGG"):
        return "TCGA-LGG"
    if s.startswith("TCGA-GBM"):
        return "TCGA-GBM"
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", type=Path, default=None, help="BraTS mapping xlsx/csv")
    parser.add_argument(
        "--auto-find",
        action="store_true",
        help="Search --brats-dir for mapping file",
    )
    parser.add_argument(
        "--brats-dir",
        type=Path,
        default=Path("data/raw/brats2024_training"),
    )
    parser.add_argument("--output", type=Path, default=Path("data/processed/brats_tcga_crosswalk.csv"))
    args = parser.parse_args()

    mapping_path = args.mapping
    if args.auto_find or mapping_path is None:
        found = find_mapping_file(args.brats_dir)
        if found is not None:
            mapping_path = found
            print(f"Auto-found mapping: {mapping_path}")
        elif mapping_path is None:
            raise SystemExit(
                "No mapping file. Provide --mapping or download BraTS 2024 GLI (includes TCGA mapping).\n"
                "Expected: data/raw/brats2024_mapping.xlsx after synapse get -r syn64952546"
            )

    if not mapping_path.exists():
        raise SystemExit(f"Mapping file not found: {mapping_path}")

    df = load_mapping(mapping_path)
    brats_col, tcga_col, cohort_col = pick_columns(df)

    out = pd.DataFrame()
    out["brats_id"] = df[brats_col].astype(str).str.strip()
    out = out[out["brats_id"].str.contains("BraTS", na=False, case=False)]

    if not tcga_col:
        raise SystemExit(
            "No TCGA/TCIA column in this spreadsheet (PTG metadata is not the TCGA crosswalk). "
            "Extract BraTS2024-BraTS-GLI-TrainingData.zip and re-run with --auto-find."
        )

    out["tcga_barcode"] = df.loc[out.index, tcga_col].map(normalize_tcga_barcode)
    out = out.dropna(subset=["tcga_barcode"])
    if cohort_col is not None:
        out["project"] = df.loc[out.index, cohort_col].map(_normalize_project)
    out = out.drop_duplicates(subset=["brats_id"])
    if out.empty:
        raise SystemExit("No BraTS rows with TCGA barcodes after filtering.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    extra = f", cohort={cohort_col!r}" if cohort_col else ""
    print(f"Source columns: brats={brats_col!r}, tcga={tcga_col!r}{extra}")
    print(f"Wrote {len(out)} linked rows -> {args.output.resolve()}")


if __name__ == "__main__":
    main()
