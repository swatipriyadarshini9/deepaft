"""BraTS GLI holdout challenge utilities (validation + additional zips).

Development (5-fold CV) uses the main training zip only via run_brats_pipeline.py.
After models are tuned, extract challenge zips and run 06_eval_brats_challenge.py.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

CHALLENGE_SOURCES = ("validation", "additional")


def case_ids_in_zip(zip_path: Path) -> set[str]:
    ids: set[str] = set()
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            parts = name.split("/")
            if len(parts) >= 2 and "BraTS-GLI-" in parts[1]:
                ids.add(parts[1])
    return ids


def extract_zip(zip_path: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    print(f"Extracting {zip_path.name} -> {output}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(output)


def seg_count_in_zip(zip_path: Path) -> int:
    with zipfile.ZipFile(zip_path, "r") as zf:
        return sum(1 for n in zf.namelist() if n.endswith("-seg.nii.gz"))


def infer_case_source(case_dir: Path) -> str:
    for parent in case_dir.parents:
        name = parent.name.lower()
        if "validation" in name:
            return "validation"
        if "additional" in name:
            return "additional"
    return "unknown"


def _radiomics_helpers():
    import importlib.util

    mod_path = Path(__file__).resolve().parent / "04_radiomics_brats.py"
    spec = importlib.util.spec_from_file_location("radiomics_brats", mod_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_manifest(challenge_dir: Path) -> dict:
    """Scan extracted tree; record BraTS-GLI case folders and seg availability."""
    mod = _radiomics_helpers()
    cases: list[dict] = []
    for case_dir in mod.find_patient_dirs(challenge_dir):
        cid = mod.case_id_from_dir(case_dir)
        has_seg = mod.find_seg(case_dir, cid) is not None
        cases.append(
            {
                "brats_id": cid,
                "source": infer_case_source(case_dir),
                "has_seg": has_seg,
                "path": str(case_dir.resolve()),
            }
        )
    by_source: dict[str, int] = {}
    for c in cases:
        by_source[c["source"]] = by_source.get(c["source"], 0) + 1
    return {
        "challenge_dir": str(challenge_dir.resolve()),
        "n_cases": len(cases),
        "by_source": by_source,
        "n_with_seg": sum(1 for c in cases if c["has_seg"]),
        "cases": cases,
    }


def write_manifest(manifest: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote challenge manifest ({manifest['n_cases']} cases) -> {path.resolve()}")
