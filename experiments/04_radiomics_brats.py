#!/usr/bin/env python3
"""
Extract PyRadiomics features from BraTS 2024 GLI NIfTI (when raw data is present).

Expected layout (per case folder BraTS-GLI-XXXXX-YYY):
  {case}-t1n.nii.gz, {case}-t1c.nii.gz, {case}-t2w.nii.gz, {case}-t2f.nii.gz, {case}-seg.nii.gz

BraTS 2024 GLI labels (nnUNet convention): 1=NETC, 2=SNFH, 3=ET, 4=RC.
Legacy BraTS (1,2,4) is detected automatically when label 3 is absent.

Requires: pip install pyradiomics nibabel

Usage:
  python experiments/04_radiomics_brats.py
  python experiments/04_radiomics_brats.py --modality t1c --regions wt,et
  python experiments/04_radiomics_brats.py --limit 5   # smoke test on first 5 cases
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd


MODALITIES = ("t1n", "t1c", "t2w", "t2f")
REGIONS = ("wt", "et", "net", "edema")


def find_patient_dirs(data_dir: Path, require_seg: bool = False) -> list[Path]:
    """Return case folders; supports flat, one-level nested, or Synapse v2 extract trees."""
    def _is_case_dir(p: Path) -> bool:
        if not p.is_dir() or not p.name.startswith("BraTS-GLI-"):
            return False
        # Exclude split roots like BraTS2024-BraTS-GLI-TrainingData (no trailing case suffix).
        parts = p.name.split("-")
        if len(parts) < 4:
            return False
        if require_seg and not any(p.glob("*-seg.nii.gz")):
            return False
        return True

    direct = sorted(p for p in data_dir.glob("BraTS-GLI-*") if _is_case_dir(p))
    if direct:
        return direct

    nested = sorted(
        p
        for sub in data_dir.iterdir()
        if sub.is_dir()
        for p in sub.glob("BraTS-GLI-*")
        if _is_case_dir(p)
    )
    if nested:
        return nested

    deep = sorted(p for p in data_dir.rglob("BraTS-GLI-*") if _is_case_dir(p))
    if deep:
        return deep

    return sorted(p for p in data_dir.iterdir() if p.is_dir())


def case_id_from_dir(case_dir: Path) -> str:
    name = case_dir.name
    if name.startswith("BraTS-GLI-"):
        return name
    seg = next(case_dir.glob("*-seg.nii.gz"), None)
    if seg is not None:
        return seg.name.replace("-seg.nii.gz", "")
    return name


def find_modality(case_dir: Path, case_id: str, modality: str) -> Path | None:
    candidates = [
        case_dir / f"{case_id}-{modality}.nii.gz",
        *case_dir.glob(f"*{modality}.nii.gz"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def find_seg(case_dir: Path, case_id: str) -> Path | None:
    candidates = [
        case_dir / f"{case_id}-seg.nii.gz",
        *case_dir.glob("*-seg.nii.gz"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def et_label_values(unique_labels: set[int]) -> list[int]:
    """Return enhancing-tumor label(s) for 2024 GLI (3) or legacy BraTS (4)."""
    if 3 in unique_labels:
        return [3]
    if 4 in unique_labels:
        return [4]
    return []


def region_mask(seg_data: np.ndarray, region: str) -> np.ndarray:
    labels = set(int(v) for v in np.unique(seg_data) if v > 0)
    if region == "wt":
        return seg_data > 0
    if region == "et":
        et_vals = et_label_values(labels)
        if not et_vals:
            return np.zeros_like(seg_data, dtype=bool)
        return np.isin(seg_data, et_vals)
    if region == "net":
        # NETC (2024) or necrotic/non-enhancing (legacy label 1)
        return seg_data == 1
    if region == "edema":
        # SNFH/edema: label 2 in both conventions
        return seg_data == 2
    raise ValueError(f"Unknown region: {region}")


def build_extractor(settings_path: Path | None):
    from radiomics import featureextractor

    if settings_path and settings_path.exists():
        return featureextractor.RadiomicsFeatureExtractor(str(settings_path))

    extractor = featureextractor.RadiomicsFeatureExtractor()
    extractor.disableAllFeatures()
    for group in ("firstorder", "shape", "glcm", "glrlm"):
        extractor.enableFeatureClassByName(group)
    extractor.settings["binWidth"] = 25
    extractor.settings["normalize"] = True
    return extractor


def extract_case(
    case_dir: Path,
    modality: str,
    regions: list[str],
    extractor,
    tmp_dir: Path,
) -> dict[str, float | str]:
    import nibabel as nib

    case_id = case_id_from_dir(case_dir)
    image_path = find_modality(case_dir, case_id, modality)
    seg_path = find_seg(case_dir, case_id)
    if image_path is None or seg_path is None:
        raise FileNotFoundError(f"{case_id}: missing {modality} or seg under {case_dir}")

    seg_img = nib.load(str(seg_path))
    seg_data = np.asanyarray(seg_img.dataobj).astype(np.int16)

    row: dict[str, float | str] = {"patient_id": case_id, "modality": modality}

    for region in regions:
        mask_bool = region_mask(seg_data, region)
        if not mask_bool.any():
            continue

        mask_path = tmp_dir / f"{case_id}_{region}_mask.nii.gz"
        mask_arr = mask_bool.astype(np.uint8)
        nib.save(nib.Nifti1Image(mask_arr, seg_img.affine, seg_img.header), str(mask_path))

        result = extractor.execute(str(image_path), str(mask_path), label=1)
        prefix = f"radiomics_{region}_"
        for key, val in result.items():
            if key.startswith("diagnostics_"):
                continue
            if isinstance(val, (int, float, np.floating, np.integer)):
                row[prefix + key.split("_", 1)[-1]] = float(val)

    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="BraTS 2024 GLI PyRadiomics extraction")
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw/brats2024_training"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/radiomics_features.csv"))
    parser.add_argument("--modality", choices=MODALITIES, default="t1c")
    parser.add_argument("--regions", default="wt,et", help="Comma-separated: wt,et,net,edema")
    parser.add_argument("--settings", type=Path, default=None, help="Optional PyRadiomics YAML settings")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N cases (smoke test)")
    parser.add_argument(
        "--require-seg",
        action="store_true",
        help="Skip validation-style folders without *-seg.nii.gz",
    )
    parser.add_argument("--manifest", type=Path, default=None, help="Write JSON manifest of processed cases")
    args = parser.parse_args()

    if not args.data_dir.exists():
        raise SystemExit(
            f"Data directory missing: {args.data_dir}\n"
            "Run: synapse login && synapse get -r syn64952546 --downloadLocation data/raw/brats2024_training"
        )

    try:
        import nibabel as nib  # noqa: F401
        from radiomics import featureextractor  # noqa: F401
    except ImportError as exc:
        raise SystemExit("Install: pip install pyradiomics nibabel") from exc

    regions = [r.strip() for r in args.regions.split(",") if r.strip()]
    for r in regions:
        if r not in REGIONS:
            raise SystemExit(f"Invalid region {r!r}; choose from {REGIONS}")

    patients = find_patient_dirs(args.data_dir, require_seg=args.require_seg)
    if not patients:
        raise SystemExit(f"No BraTS-GLI-* folders under {args.data_dir}")

    if args.limit:
        patients = patients[: args.limit]

    extractor = build_extractor(args.settings)
    rows: list[dict] = []
    errors: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="brats_radiomics_") as tmp:
        tmp_dir = Path(tmp)
        for i, case_dir in enumerate(patients, 1):
            case_id = case_id_from_dir(case_dir)
            try:
                row = extract_case(case_dir, args.modality, regions, extractor, tmp_dir)
                rows.append(row)
                print(f"[{i}/{len(patients)}] OK {case_id} ({len(row) - 2} features)")
            except Exception as exc:
                errors.append({"patient_id": case_id, "error": str(exc)})
                print(f"[{i}/{len(patients)}] SKIP {case_id}: {exc}")

    if not rows:
        raise SystemExit("No features extracted — check NIfTI paths and PyRadiomics install.")

    df = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    print(f"\nWrote {len(df)} cases x {len(df.columns)} columns -> {args.output.resolve()}")

    if errors:
        err_path = args.output.with_suffix(".errors.json")
        err_path.write_text(json.dumps(errors, indent=2), encoding="utf-8")
        print(f"Skipped {len(errors)} cases — see {err_path}")

    if args.manifest:
        manifest = {
            "data_dir": str(args.data_dir.resolve()),
            "modality": args.modality,
            "regions": regions,
            "n_ok": len(rows),
            "n_errors": len(errors),
            "output": str(args.output.resolve()),
        }
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
