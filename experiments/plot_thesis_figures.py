#!/usr/bin/env python3
"""Generate dissertation figures (aggregate plots + optional anonymized BraTS GLI slice)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"

# Thesis styling
plt.rcParams.update(
    {
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    }
)

BRATS_CC_BY_NC_FIGURE_CAPTION = """\
Figure (illustrative BraTS 2024 GLI case). Post-treatment multiparametric brain MRI from the \
BraTS 2024 Adult Glioma Post-Treatment (GLI) challenge (Sage Bionetworks Synapse project \
syn53708249). Left: native T1-weighted appearance; centre: post-contrast T1-weighted (T1c); \
right: T1c with co-registered expert segmentation overlay (enhancing tumour, non-enhancing \
subregions, resection cavity per BraTS 2024 label protocol). Case identifier withheld; image \
shown at a single post-treatment time point only (not longitudinal pre-operative imaging). \
Data subject to Creative Commons Attribution–NonCommercial 4.0 (CC BY-NC 4.0). Cite \
Correia de Verdier et al. (2024) arXiv:2405.18368 and Bakas et al. (2024) Zenodo \
10.5281/zenodo.10978907. Not for clinical use.
"""


def _ensure_out() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)


def fig_deepaft_pipeline(out: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")

    boxes = [
        (0.3, 1.0, "Covariates z\n(genes / imaging features)"),
        (2.5, 1.0, "ReLU network\nμθ(z)"),
        (4.7, 1.0, "Log-time AFT\nlog T̃ = μθ + ε"),
        (6.6, 1.0, "Censoring-aware loss\n(BJ / IPCW / transform)"),
        (8.5, 1.0, "Predictions\nŷ time, Ŝ(t)"),
    ]
    for x, y, text in boxes:
        patch = FancyBboxPatch(
            (x, y),
            1.7,
            1.1,
            boxstyle="round,pad=0.05",
            linewidth=1.2,
            edgecolor="#2c5282",
            facecolor="#ebf8ff",
        )
        ax.add_patch(patch)
        ax.text(x + 0.85, y + 0.55, text, ha="center", va="center", fontsize=8.5)

    for x0, x1 in [(2.0, 2.5), (4.2, 4.7), (6.4, 6.6), (8.3, 8.5)]:
        ax.add_patch(
            FancyArrowPatch(
                (x0 + 0.1, 1.55),
                (x1 - 0.05, 1.55),
                arrowstyle="-|>",
                mutation_scale=12,
                color="#4a5568",
            )
        )

    ax.text(
        5.0,
        2.55,
        "deepAFT pipeline (after Norman et al. 2024; extensions: covariate censoring, IPCW fallback, group scale)",
        ha="center",
        fontsize=9,
        style="italic",
    )
    fig.savefig(out)
    plt.close(fig)


def fig_simulation_cindex(out: Path) -> None:
    path = TABLES / "simulation_chapter_summary.csv"
    df = pd.read_csv(path)
    models = ["cox", "rsf", "lognormal", "deepsurv", "deepAFT_BJ"]
    scenarios = ["A", "B", "C", "D"]
    sub = df[df["model"].isin(models)].copy()
    pivot = sub.pivot(index="model", columns="scenario", values="c_index_mean")
    pivot = pivot.reindex(models)

    x = np.arange(len(scenarios))
    width = 0.15
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = ["#718096", "#a0aec0", "#48bb78", "#ed8936", "#3182ce"]
    labels = ["Cox", "RSF", "Log-normal AFT", "DeepSurv", "deepAFT (BJ)"]

    for i, (model, label, color) in enumerate(zip(models, labels, colors)):
        vals = pivot.loc[model, scenarios].values.astype(float)
        ax.bar(x + (i - 2) * width, vals, width, label=label, color=color, edgecolor="white")

    ax.set_xticks(x)
    ax.set_xticklabels([f"Scenario {s}" for s in scenarios])
    ax.set_ylabel("Harrell C-index (mean, R=50)")
    ax.set_title("Simulation study — discrimination by scenario")
    ax.set_ylim(0, 1.0)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=8)
    fig.savefig(out)
    plt.close(fig)


def fig_tcga_cindex(out: Path) -> None:
    path = TABLES / "glioma_benchmark.csv"
    df = pd.read_csv(path)
    sub = df[df["features"] == "genes"].copy()
    order = ["cox", "rsf", "deepsurv", "deepAFT_BJ_group", "lognormal"]
    labels = ["Cox PH", "RSF", "DeepSurv", "deepAFT (BJ, group scale)", "Log-normal AFT"]
    sub = sub.set_index("model").reindex(order)

    fig, ax = plt.subplots(figsize=(6, 4))
    yerr = sub["c_index_std"].values
    bars = ax.bar(
        labels,
        sub["c_index_mean"].values,
        yerr=yerr,
        capsize=4,
        color=["#e53e3e", "#a0aec0", "#ed8936", "#3182ce", "#48bb78"],
        edgecolor="white",
    )
    ax.set_ylabel("Harrell C-index (5-fold CV mean ± SD)")
    ax.set_title("TCGA adult glioma (671 cases; IDH1, MGMT, TP53)")
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
    ax.set_ylim(0, 1.0)
    ax.axhline(0.5, color="#cbd5e0", linestyle="--", linewidth=0.8)
    fig.savefig(out)
    plt.close(fig)


def fig_brats_volume_boxplot(out: Path) -> None:
    path = TABLES / "brats_seg_descriptive.csv"
    df = pd.read_csv(path)
    gli = df[df["stratify_by"] == "glioma_type"].copy()
    gli = gli[~gli["level"].str.lower().eq("glioma nos") & (gli["n_cases"] >= 10)]
    gli = gli.sort_values("wt_vol_mm3_mean")

    fig, axes = plt.subplots(1, 2, figsize=(8, 3.8))
    for ax, col, title in zip(
        axes,
        ["wt_vol_mm3_mean", "et_vol_mm3_mean"],
        ["Whole tumour volume (mm³, mean by type)", "Enhancing tumour volume (mm³, mean by type)"],
    ):
        ax.barh(gli["level"], gli[col], color="#4299e1", edgecolor="white")
        ax.set_xlabel("Mean volume (descriptive cohort table)")
        ax.set_title(title, fontsize=9)
    fig.suptitle("BraTS 2024 GLI — segmentation-derived volumes by PTG glioma type (n per type in table)", y=1.02)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def fig_brats_cohort_flow(out: Path) -> None:
    counts = pd.read_csv(TABLES / "brats_cohort_counts.csv")
    total = int(counts.loc[counts["split_folder"] == "_TOTAL", "n_cases"].iloc[0])
    with_seg = int(counts.loc[counts["split_folder"] == "_WITH_SEG", "n_cases"].iloc[0])
    val = int(counts.loc[counts["split_folder"] == "validation_data", "n_cases"].iloc[0])
    train_main = int(counts.loc[counts["split_folder"] == "training_data1_v2", "n_cases"].iloc[0])
    train_add = int(counts.loc[counts["split_folder"] == "training_data_additional", "n_cases"].iloc[0])

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.axis("off")
    steps = [
        (0.05, 0.72, f"BraTS 2024 GLI\nlocal inventory\nN = {total}"),
        (0.38, 0.72, f"Training + additional\n{train_main} + {train_add}"),
        (0.72, 0.72, f"With expert seg\nn = {with_seg}\n(imaging features)"),
        (0.38, 0.28, f"Validation split\nn = {val}\n(no public seg)"),
        (0.72, 0.28, f"PTG label benchmarks\n5-fold CV\n(type + site)"),
    ]
    for x, y, text in steps:
        patch = FancyBboxPatch(
            (x, y),
            0.26,
            0.18,
            boxstyle="round,pad=0.02",
            transform=ax.transAxes,
            linewidth=1.2,
            edgecolor="#2d3748",
            facecolor="#f7fafc",
        )
        ax.add_patch(patch)
        ax.text(x + 0.13, y + 0.09, text, ha="center", va="center", transform=ax.transAxes, fontsize=8)

    arrows = [
        ((0.31, 0.81), (0.38, 0.81)),
        ((0.64, 0.81), (0.72, 0.81)),
        ((0.51, 0.72), (0.51, 0.46)),
        ((0.64, 0.37), (0.72, 0.37)),
    ]
    for (x0, y0), (x1, y1) in arrows:
        ax.annotate(
            "",
            xy=(x1, y1),
            xytext=(x0, y0),
            xycoords="axes fraction",
            textcoords="axes fraction",
            arrowprops=dict(arrowstyle="-|>", color="#4a5568"),
        )
    ax.set_title("BraTS 2024 GLI cohort flow (this dissertation)")
    fig.savefig(out)
    plt.close(fig)


def _best_axial_slice(vol: np.ndarray, mask: np.ndarray | None = None) -> int:
    if mask is not None and mask.any():
        counts = mask.sum(axis=(0, 1))
        if counts.max() > 0:
            return int(np.argmax(counts))
    return int(vol.shape[2] // 2)


def _normalize_slice(sl: np.ndarray, pct: tuple[float, float] = (1, 99)) -> np.ndarray:
    sl = np.asarray(sl, dtype=np.float32)
    finite = sl[np.isfinite(sl)]
    if finite.size == 0:
        return np.zeros_like(sl)
    lo, hi = np.percentile(finite, pct)
    if hi <= lo:
        hi = lo + 1e-6
    sl = np.clip(sl, lo, hi)
    return (sl - lo) / (hi - lo)


def fig_brats_illustrative(
    out: Path,
    data_dir: Path,
    case_id: str | None,
    caption_path: Path,
) -> bool:
    try:
        import nibabel as nib
    except ImportError:
        print("nibabel not installed; skip clinical figure", file=sys.stderr)
        return False

    sys.path.insert(0, str(ROOT / "experiments"))
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "radiomics_brats", ROOT / "experiments" / "04_radiomics_brats.py"
    )
    assert spec and spec.loader
    rb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rb)

    patients = rb.find_patient_dirs(data_dir, require_seg=True)
    if not patients:
        print(f"No BraTS cases under {data_dir}", file=sys.stderr)
        return False

    case_dir = None
    if case_id:
        for p in patients:
            if rb.case_id_from_dir(p) == case_id or case_id in p.name:
                case_dir = p
                break
    if case_dir is None:
        case_dir = patients[0]

    cid = rb.case_id_from_dir(case_dir)
    t1n_path = rb.find_modality(case_dir, cid, "t1n")
    t1c_path = rb.find_modality(case_dir, cid, "t1c")
    seg_path = rb.find_seg(case_dir, cid)
    if not t1c_path or not seg_path:
        print(f"Missing modalities for {cid}", file=sys.stderr)
        return False

    t1c = np.asanyarray(nib.load(str(t1c_path)).dataobj)
    t1n = np.asanyarray(nib.load(str(t1n_path)).dataobj) if t1n_path else t1c
    seg = np.asanyarray(nib.load(str(seg_path)).dataobj).astype(np.int16)
    wt = seg > 0
    sl = _best_axial_slice(t1c, wt)

    t1n_sl = _normalize_slice(t1n[:, :, sl])
    t1c_sl = _normalize_slice(t1c[:, :, sl])
    seg_sl = seg[:, :, sl]

    overlay = np.stack([t1c_sl, t1c_sl, t1c_sl], axis=-1)
    # ET (3 or 4), NETC (1), SNFH (2), RC (4 in 2024) — colour map
    cmap = {
        1: (0.2, 0.6, 1.0),
        2: (0.2, 0.85, 0.4),
        3: (1.0, 0.25, 0.25),
        4: (1.0, 0.85, 0.2),
    }
    for lab, rgb in cmap.items():
        m = seg_sl == lab
        if m.any():
            overlay[m] = 0.55 * np.array(rgb) + 0.45 * overlay[m]

    fig, axes = plt.subplots(1, 3, figsize=(9, 3.2))
    axes[0].imshow(np.rot90(t1n_sl), cmap="gray", aspect="equal")
    axes[0].set_title("Native T1 (t1n)")
    axes[1].imshow(np.rot90(t1c_sl), cmap="gray", aspect="equal")
    axes[1].set_title("Post-contrast T1c")
    axes[2].imshow(np.rot90(overlay), aspect="equal")
    axes[2].set_title("T1c + segmentation overlay")
    for ax in axes:
        ax.axis("off")
    fig.suptitle(
        "Illustrative post-treatment case (identifier withheld; BraTS 2024 GLI)",
        fontsize=10,
    )
    # Legend
    handles = [
        mpatches.Patch(color=cmap[3], label="ET (label 3)"),
        mpatches.Patch(color=cmap[1], label="NETC (1)"),
        mpatches.Patch(color=cmap[2], label="SNFH (2)"),
        mpatches.Patch(color=cmap[4], label="RC (4)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=7, frameon=False)
    fig.savefig(out)
    plt.close(fig)

    caption_path.write_text(
        BRATS_CC_BY_NC_FIGURE_CAPTION
        + f"\n\n(Source case: Synapse-authorized local extract; internal folder omitted from publication.)\n",
        encoding="utf-8",
    )
    (FIGURES / "fig06_brats_illustrative_README.txt").write_text(
        "Generated from one Synapse-authorized BraTS 2024 GLI case (identifier withheld).\n",
        encoding="utf-8",
    )
    print("Clinical figure: OK (case identifier withheld in outputs)")
    return True


def write_captions_index() -> None:
    lines = [
        "# Thesis figure captions",
        "",
        "## fig01_deepaft_pipeline.png",
        "Schematic of the deepAFT estimation pipeline (Norman et al. 2024) with dissertation extensions.",
        "",
        "## fig02_simulation_cindex.png",
        "Mean Harrell C-index across 50 replications per scenario A–D (`simulation_chapter_summary.csv`).",
        "",
        "## fig03_tcga_cindex.png",
        "TCGA glioma gene-panel benchmark, 5-fold CV (`glioma_benchmark.csv`). IDH1 violates PH (p≈0.03).",
        "",
        "## fig04_brats_volumes_by_type.png",
        "Mean whole-tumour and enhancing-tumour volumes by PTG glioma type (`brats_seg_descriptive.csv`).",
        "",
        "## fig05_brats_cohort_flow.png",
        "Cohort flow for BraTS 2024 GLI local extract (`brats_cohort_counts.csv`).",
        "",
        "## fig06_brats_illustrative_mri.png",
        BRATS_CC_BY_NC_FIGURE_CAPTION.strip(),
        "",
    ]
    (FIGURES / "FIGURE_CAPTIONS.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate thesis figures into results/figures/")
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw/brats2024_training"))
    parser.add_argument("--case-id", type=str, default=None, help="BraTS-GLI-* folder name; default first case")
    parser.add_argument("--skip-clinical", action="store_true")
    args = parser.parse_args()

    _ensure_out()
    fig_deepaft_pipeline(FIGURES / "fig01_deepaft_pipeline.png")
    fig_simulation_cindex(FIGURES / "fig02_simulation_cindex.png")
    fig_tcga_cindex(FIGURES / "fig03_tcga_cindex.png")
    fig_brats_volume_boxplot(FIGURES / "fig04_brats_volumes_by_type.png")
    fig_brats_cohort_flow(FIGURES / "fig05_brats_cohort_flow.png")

    if not args.skip_clinical:
        fig_brats_illustrative(
            FIGURES / "fig06_brats_illustrative_mri.png",
            args.data_dir,
            args.case_id,
            FIGURES / "fig06_brats_illustrative_CAPTION.txt",
        )

    write_captions_index()
    print(f"Wrote figures to {FIGURES}")


if __name__ == "__main__":
    main()
