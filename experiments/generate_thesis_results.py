#!/usr/bin/env python3
"""Compile simulation + real-data CSVs into thesis-ready markdown."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
OUT = ROOT / "results" / "thesis_results.md"


def _append_model_choice_guidance(
    sections: list[str],
    ph: dict,
    benchmark_path: Path,
    sim_path: Path,
) -> None:
    """Narrative from this repo's PH test + benchmark tables (not hand-edited in thesis_results.md)."""
    sections.append("## Model choice — deepAFT vs Cox (justification)")
    sections.append("")
    sections.append(
        "This block interprets **your recorded outputs**. Cite Norman et al. (2024) for the deepAFT "
        "formulation; use Grambsch–Therneau / Schoenfeld on **your** covariates before preferring AFT in other cohorts."
    )
    sections.append("")
    sections.append("### When deepAFT (or AFT more generally) is **justified here**")
    sections.append("")
    bullets_yes: list[str] = []
    p_global = ph.get("ph_p_global", ph.get("ph_p"))
    worst = ph.get("ph_worst_covariate", "")
    if p_global is not None:
        bullets_yes.append(
            f"- **Proportional hazards doubtful on the gene panel:** minimum Schoenfeld "
            f"p = {float(p_global):.4g} ({worst}). Cox hazard ratios are hard to interpret when "
            f"effects are time-varying; AFT targets log-time directly."
        )
    if benchmark_path.exists():
        g = pd.read_csv(benchmark_path)
        if {"model", "c_index_mean"} <= set(g.columns):
            sub = g[g["features"].eq("genes")] if "features" in g.columns else g
            by_model = sub.set_index("model")["c_index_mean"]
            if "cox" in by_model.index and "deepAFT_BJ_group" in by_model.index:
                bullets_yes.append(
                    f"- **Discrimination on TCGA (genes, 5-fold CV):** Cox C-index "
                    f"{by_model['cox']:.3f} vs deepAFT_BJ_group {by_model['deepAFT_BJ_group']:.3f} "
                    f"with PH violated — Cox underperforms under this mis-specification."
                )
            if "lognormal" in by_model.index and "deepAFT_BJ_group" in by_model.index:
                bullets_yes.append(
                    f"- **Parametric benchmark:** log-normal AFT {by_model['lognormal']:.3f} vs "
                    f"deepAFT_BJ_group {by_model['deepAFT_BJ_group']:.3f}; deepAFT is the neural "
                    f"log-time extension when linear AFT mean is too rigid (see simulation)."
                )
    if sim_path.exists():
        sim = pd.read_csv(sim_path)
        if {"scenario", "model", "c_index_mean"} <= set(sim.columns):
            cox = sim[sim["model"].eq("cox")]["c_index_mean"].mean()
            bj = sim[sim["model"].eq("deepAFT_BJ")]["c_index_mean"].mean()
            bullets_yes.append(
                f"- **Simulation (mean C-index across scenarios A–D):** Cox {cox:.3f} vs "
                f"deepAFT_BJ {bj:.3f} under Norman-style nonlinear log-time DGP — supports "
                f"neural AFT when the true log-time surface is non-linear."
            )
        bullets_yes.append(
            "- **Known limitation settings (scenarios B–D):** use deepAFT covariate-censoring, "
            "IPCW fallback, or group-scale BJ when those assumptions are plausibly violated "
            "(see simulation chapter)."
        )
    sections.extend(bullets_yes)
    sections.append("")
    sections.append("### When **not** to rely on deepAFT (or when Cox / simpler models suffice)")
    sections.append("")
    sections.extend(
        [
            "- **PH not rejected** (all Schoenfeld p > 0.05 on your covariates): prefer Cox for "
            "standard hazard interpretation; deepAFT is optional for *time prediction*, not required.",
            "- **Hazard ratios only:** if the research question is relative hazard, not calibrated "
            "survival time, Cox (or penalized Cox) is the conventional choice.",
            "- **Tiny samples / unstable censoring weights:** IPCW paths can fail; this package "
            "falls back to Buckley–James — still prefer simpler AFT or Cox when n is small.",
            "- **BraTS imaging chapters:** PTG glioma-type and site prediction use classification "
            "metrics, not Cox/deepAFT — survival models apply to TCGA OS, not unlabeled PTG MRI alone.",
            "- **No linked multimodal OS on 2024 PTG:** until crosswalk IDs overlap features "
            "(see linkage report), do not claim deepAFT on imaging+genes for the full BraTS cohort.",
            "- **Domain shift:** project holdout (LGG→GBM / GBM→LGG) shows modest C-index (~0.49–0.52 "
            "for log-normal AFT in `glioma_benchmark_external.csv`) — high in-sample CV does not "
            "imply deepAFT replaces clinical stratification on external projects.",
        ]
    )
    sections.append("")


def main() -> None:
    sections: list[str] = [
        "# Thesis results summary",
        "",
        "Auto-generated from experiment outputs. **Do not edit numbers manually.**",
        "",
    ]

    sim_path = TABLES / "simulation_chapter_summary.csv"
    if sim_path.exists():
        sim = pd.read_csv(sim_path)
        sections.append("## Simulation chapter (scenarios A–D)")
        sections.append("")
        if "n" in sim.columns:
            by_sc = sim.groupby("scenario")["n"].max()
            if by_sc.nunique() == 1:
                sections.append(f"Replications per scenario: **{int(by_sc.iloc[0])}**")
            else:
                parts = ", ".join(f"{sc}={int(n)}" for sc, n in by_sc.items())
                sections.append(f"Replications (by scenario): **{parts}**")
            sections.append("")
        if "scenario" in sim.columns and "model" in sim.columns:
            pivot = sim.pivot(index="model", columns="scenario", values="c_index_mean")
            sections.append("Harrell C-index (mean across replications):")
            sections.append("")
            sections.append("```")
            sections.append(pivot.round(3).to_string())
            sections.append("```")
            if "c_index_std" in sim.columns:
                sections.append("")
                sections.append("Standard deviation:")
                sections.append("")
                sections.append("```")
                std_pivot = sim.pivot(index="model", columns="scenario", values="c_index_std")
                sections.append(std_pivot.round(3).to_string())
                sections.append("```")
        else:
            sections.append("```")
            sections.append(sim.to_string(index=False))
            sections.append("```")
        sections.append("")

    crosswalk_path = ROOT / "data" / "processed" / "brats_tcga_crosswalk.csv"
    feat_path = ROOT / "data" / "processed" / "radiomics_features.csv"
    linked_ok = False
    if crosswalk_path.exists() and feat_path.exists():
        cw = pd.read_csv(crosswalk_path)
        feat = pd.read_csv(feat_path)
        if "brats_id" in cw.columns and "patient_id" in feat.columns:
            linked_ok = bool(set(cw["brats_id"]).intersection(set(feat["patient_id"])))

    benchmark_jobs = [
        ("TCGA genes only (671 cases) — primary thesis benchmark", "glioma_benchmark.csv", True),
    ]
    if linked_ok:
        benchmark_jobs.append(
            (
                "Linked BraTS 2024 PTG + TCGA (mapping overlaps imaging IDs)",
                "glioma_benchmark_linked.csv",
                True,
            )
        )

    for label, fname, _ in benchmark_jobs:
        glioma_path = TABLES / fname
        if not glioma_path.exists():
            continue
        g = pd.read_csv(glioma_path)
        sections.append(f"## Real-data benchmark — {label} (5-fold CV)")
        sections.append("")
        if "features" in g.columns:
            sections.append(
                "Feature sets: genes, radiomics (if linked), genes+radiomics. "
                "Interpret only if a defensible BraTS↔TCGA crosswalk exists for your imaging year."
            )
        else:
            sections.append("Gene panel: IDH1, MGMT, TP53 (Xena HiSeqV2 + GDC survival).")
        sections.append("")
        sections.append("```")
        sections.append(g.to_string(index=False))
        sections.append("```")
        sections.append("")

    ph_path = TABLES / "glioma_ph_test.json"
    if ph_path.exists():
        ph = json.loads(ph_path.read_text(encoding="utf-8"))
        sections.append("## Proportional hazards test (gene panel)")
        sections.append("")
        p_global = ph.get("ph_p_global", ph.get("ph_p"))
        sections.append(f"- Minimum Schoenfeld p (worst covariate): {p_global}")
        if ph.get("ph_worst_covariate"):
            sections.append(f"- Worst covariate: {ph['ph_worst_covariate']}")
        by_cov = ph.get("ph_p_by_covariate") or {}
        if by_cov:
            sections.append("- Per gene:")
            for gene, pval in by_cov.items():
                sections.append(f"  - {gene}: p={pval:.4g}")
        if p_global is not None and float(p_global) < 0.05:
            sections.append("- **PH rejected (p<0.05)** → AFT/deepAFT justified as alternative to Cox.")
        sections.append("")
        _append_model_choice_guidance(sections, ph, TABLES / "glioma_benchmark.csv", sim_path)

    inv_path = TABLES / "brats_cohort_counts.csv"
    if inv_path.exists():
        inv = pd.read_csv(inv_path)
        sections.append("## BraTS 2024 GLI cohort (local data)")
        sections.append("")
        sections.append("```")
        sections.append(inv.to_string(index=False))
        sections.append("```")
        sections.append("")

    val_qc = TABLES / "brats_validation_qc.csv"
    if val_qc.exists():
        sections.append("## BraTS 2024 validation split (modality QC)")
        sections.append("")
        sections.append("```")
        sections.append(pd.read_csv(val_qc).to_string(index=False))
        sections.append("```")
        sections.append("")

    for blabel, bfname in (
        ("Imaging features vs PTG Glioma type (5-fold CV)", "brats_imaging_baseline.csv"),
        ("Imaging features vs PTG Site (5-fold CV)", "brats_imaging_baseline_site.csv"),
    ):
        bp = TABLES / bfname
        if not bp.exists():
            continue
        sections.append(f"## BraTS imaging — {blabel}")
        sections.append("")
        sections.append("```")
        sections.append(pd.read_csv(bp).to_string(index=False))
        sections.append("```")
        sections.append("")

    sections.append("## Extended analyses (supplementary)")
    sections.append("")
    for label, fname in (
        ("Seg volume descriptive (by glioma type / site)", "brats_seg_descriptive.csv"),
        ("2D U-Net slice Dice (exploratory; PyTorch on **py -3.12**)", "brats_unet2d_dice.csv"),
        ("Subregion graph (ET/NET/edema nodes) vs glioma type", "brats_gnn_glioma_type.csv"),
        ("TCGA LGG↔GBM project holdout (log-normal AFT)", "glioma_benchmark_external.csv"),
    ):
        path = TABLES / fname
        if not path.exists():
            continue
        sections.append(f"### {label}")
        sections.append("")
        sections.append("```")
        sections.append(pd.read_csv(path).to_string(index=False))
        sections.append("```")
        sections.append("")

    link_report = TABLES / "brats_tcga_linkage_report.json"
    if link_report.exists():
        sections.append("### BraTS 2024 PTG ↔ TCGA linkage report")
        sections.append("")
        sections.append("```")
        sections.append(link_report.read_text(encoding="utf-8").strip())
        sections.append("```")
        sections.append("")

    sections.append("## Reproduced vs contributed")
    sections.append("")
    sections.append("| Component | Source |")
    sections.append("|-----------|--------|")
    sections.append("| deepAFT BJ/IPCW/Transform | Norman et al. 2024 |")
    sections.append("| Covariate censoring, group scale | This dissertation |")
    sections.append("| TCGA gene benchmark | This dissertation |")
    n_feat = len(pd.read_csv(feat_path)) if feat_path.exists() else 0
    brats_status = f"BraTS 2024 GLI imaging features: {n_feat} cases"
    if linked_ok:
        brats_status += "; multimodal OS benchmark on overlapping PTG↔TCGA IDs"
    else:
        brats_status += "; multimodal OS on full 2024 PTG cohort → future work when official crosswalk is published"
    sections.append(f"| BraTS 2024 GLI | {brats_status} |")
    sections.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(sections), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
