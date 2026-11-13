# MSc dissertation — draft chapter text

Paste into your Word/LaTeX thesis. **Numeric results:** use [results/thesis_results.md](../results/thesis_results.md) and tables under `results/tables/` only (regenerate after long jobs finish). **Submission steps:** see [thesis_submission_checklist.md](thesis_submission_checklist.md).

## Abstract (draft)

We reimplemented Norman et al. (2024) deep accelerated failure time (deepAFT) models in Python and extended them for settings where standard deep survival assumptions fail: covariate-dependent censoring, degenerate inverse-probability weights, and heteroscedastic log-residuals in grouped cohorts. A Monte Carlo study (scenarios A–D, 50 replications each) compares deepAFT with Cox, random survival forests, log-normal AFT, and DeepSurv under controlled violations of those assumptions. **Real-data chapters** cover (i) TCGA adult glioma overall survival with gene expression (IDH1, MGMT, TP53) and GDC vital status (671 cases), and (ii) **BraTS 2024 GLI** imaging—PTG splits, segmentation and/or imaging-derived features, and PTG label prediction. Multimodal survival merging 2024 PTG cases to TCGA OS is **future work** when the challenge publishes a matching crosswalk; merge scripts are implemented and tested on TCGA-only and imaging-only tracks. Proportional hazards testing (Schoenfeld) on the TCGA gene panel supports comparing AFT-style models with Cox where appropriate. **Contribution:** limitation-aware extensions plus glioma evaluation on simulation, TCGA, and BraTS tracks; **not** a claim of inventing deepAFT (Norman et al., doi:10.1002/sim.10152).

## 1 Introduction

Accelerated failure time (AFT) models express log survival time as a regression on covariates plus noise, yielding direct time predictions. Norman et al. (2024) combine AFT structure with a ReLU network for the log-time mean and three censoring-aware losses (Buckley–James, IPCW, Fan–Gijbels transform). Official reference implementation: R package `dnn::deepAFT`.

This dissertation (1) ports that methodology to an installable Python package `deepaft`, (2) documents failure modes from the Norman paper and literature, (3) implements pragmatic extensions, and (4) applies the toolkit on **three empirical tracks**: simulation, **TCGA** adult glioma survival (gene panel + GDC), and **BraTS 2024 GLI** MRI with PTG protocol splits, imaging-derived features, and multimodal joins to TCGA survival when identifiers are resolved.

## 2 Background

### 2.1 deepAFT (reproduced)

Model: \(\log \tilde T = \mu_\theta(z) + \varepsilon\), with \(\mu_\theta\) a feed-forward network. Training targets depend on `method`: iterative Buckley–James imputation (primary, as in Norman), IPCW-adjusted MSE, or transform-based MSE. Survival curves follow Eq. (5) in Norman et al. using an estimated baseline \(\hat S_0\).

### 2.2 Limitations motivating extensions

- **Covariate-dependent censoring:** marginal \(\hat G(t)\) can bias IPCW/transform; we allow covariate-stratified \(\hat G(t\mid z)\) (scenario B).
- **Degenerate weights:** when no events remain in a stratum, IPCW/transform become unstable; `auto_fallback` reverts to Buckley–James (scenario C).
- **Heteroscedastic residuals:** glioma subtypes differ in dispersion; group- or network-scaled \(\sigma(z)\) on log-residuals (scenario D).

## 3 Methods (this work)

### 3.1 Python package `deepaft`

Implementation in `src/deepaft/`: `DeepAFT` with `method`, `censoring`, `scale`, `auto_fallback`. Metrics: Harrell C-index, AMSE where applicable. Simulation generators `scenario_a`–`scenario_d` mirror dissertation scenarios A–D.

### 3.2 Data sources

| Modality | Source | Role |
|----------|--------|------|
| OS, vital status | GDC TCGA | **Primary** outcome labels for real-data chapter |
| Gene expression | Xena HiSeqV2 | IDH1, MGMT, TP53 |
| MRI, segmentations | BraTS 2024 GLI (e.g. Synapse) | Imaging chapter: splits, radiomics/segmentation, multimodal survival when mapped to TCGA |

**Linkage:** TCGA barcodes supply OS for the survival chapter. **BraTS 2024 GLI** PTG IDs in this extract are reported in the imaging chapter; joining them to TCGA for multimodal OS requires an **official BraTS 2024 PTG ↔ TCGA mapping table** (`02_build_tcga_crosswalk.py`, `merge_linked_cohort.py`)—planned extension in Discussion, not part of the current 2024 imaging results tables.

### 3.3 Benchmarks

- **Simulation:** 75/25 train–test split per replication; neural models trained with configured epochs; baselines from `experiments/benchmarks.py`.
- **Real data:** 5-fold cross-validation; models include Cox PH, log-normal AFT, RSF, DeepSurv, deepAFT (BJ with group scale where noted).
- **PH assessment:** lifelines Grambsch–Therneau (`proportional_hazard_test`) on the gene panel; report worst covariate p-value.

### 3.4 BraTS tooling (`experiments/`)

`01_download_brats2024.py`, `ingest_ptg_metadata.py`, `stage_brats_challenge.py`, `02_build_tcga_crosswalk.py`, `04_radiomics_brats.py`, `merge_linked_cohort.py`, `06_eval_brats_challenge.py` implement the **imaging and multimodal** dissertation track. Populate `results/tables/` after extract and long jobs; until then, cite TCGA and simulation tables that are already fixed.

## 4 Simulation study (chapter results)

**Design:** Scenarios A–D (see `experiments/run_simulation_chapter.py`), **R=50** replications, checkpoints in `simulation_chapter_raw.csv`.

**Interpretation (use latest table in thesis_results.md):**

- **A (baseline):** deepAFT_BJ typically matches or exceeds DeepSurv/log-normal on C-index; tree Cox/RSF underperform under nonlinear log-time structure.
- **B (covariate censoring):** compare `deepAFT_BJ` vs `deepAFT_BJ_covariate` — extension should not harm and may stabilize IPCW path when enabled.
- **C (degenerate IPCW):** `deepAFT_IPCW_or_fallback` documents fallback to BJ when IPCW is ill-defined.
- **D (group scale):** compare BJ vs `deepAFT_BJ_group_scale` / covariate variant under heteroscedastic groups.

Report mean ± SD C-index and AMSE for deepAFT rows from `simulation_chapter_summary.csv`.

## 5 Real-data results — TCGA genes

Cohort: `data/processed/tcga_glioma_cohort.csv` (671 cases). Benchmark: `results/tables/glioma_benchmark.csv`.

**Findings (fixed run):**

- Schoenfeld: IDH1 p≈0.030 → PH questionable for Cox as primary interpretable model.
- deepAFT_BJ_group C-index ≈0.751 ± 0.019; competitive with log-normal AFT; Cox ≈0.386 on this panel (mis-specified PH).

**When to prefer deepAFT over Cox (this cohort):** PH rejected on IDH1; Cox discrimination collapses while AFT/deepAFT track log-time under non-PH gene effects; simulation shows Cox weak under nonlinear log-time DGP. **When not to:** if PH holds, use Cox for hazard interpretation; BraTS PTG tasks are classification, not OS; no multimodal deepAFT on full 2024 PTG until crosswalk overlap; external LGG↔GBM holdout stays modest — see `results/thesis_results.md` (section *Model choice — deepAFT vs Cox*).
- DeepSurv ≈0.718; RSF ≈0.330.

Discuss AMSE scale differences (DeepSurv vs AFT targets) cautiously—metrics are not directly comparable across model families without harmonized prediction type.

## 6 BraTS 2024 GLI — imaging results

**Cohort (local Synapse extract):** 1809 PTG cases — 1350 training, 271 additional training, 188 validation (`results/tables/brats_cohort_counts.csv`). **1621** cases include segmentations used for imaging features.

**Features:** NIfTI-derived volumes and T1c first-order statistics per subregion (whole tumour, enhancing tumour, net, edema) for all segmented cases (`data/processed/radiomics_features.csv`, 1621 rows). Pipeline: `04b_brats_imaging_features.py` with `--require-seg` on the default Python install. **Torch-based** segmentation / optional PyRadiomics use **Python 3.12** (`py -3.12`) because enterprise Application Control blocked PyTorch DLLs on Python 3.14 on the author’s workstation.

**PTG label prediction (5-fold stratified CV, logistic regression on 16 imaging features):**

| Target | *n* | Balanced accuracy | Macro F1 |
|--------|-----|-------------------|----------|
| Glioma type (6 classes) | 1621 | 0.303 | 0.258 |
| Acquisition site (5 classes) | 1621 | 0.624 | 0.535 |

Source: `results/tables/brats_imaging_baseline.csv`, `brats_imaging_baseline_site.csv`.

**Validation split:** 188 cases; all 188 have four MRI modalities; 0 public segmentations in this release (`results/tables/brats_validation_qc.csv`).

**Multimodal OS on 2024 PTG IDs:** **Future work** — when the challenge publishes an official **BraTS 2024 PTG ↔ TCGA** crosswalk, merge scripts (`02_build_tcga_crosswalk.py`, `run_brats_pipeline.py`) extend Section 5-style survival models to the full imaging cohort without code changes.

## 6b Extended analyses (supplementary)

Summaries in `results/thesis_results.md` (**Extended analyses**):

- **Segmentation:** volume statistics by glioma type and site; exploratory **2D U-Net** on axial T1c (250 train / 80 internal val slices, 6 epochs, **py -3.12**, torch CPU): mean Dice WT **0.125 ± 0.33**, ET **0.35 ± 0.48** (`brats_unet2d_dice.csv`). Optional PyRadiomics smoke: same 3.12 interpreter.
- **Subregion graph:** four-node WT/ET/NET/edema neighbour features for glioma-type prediction (`brats_gnn_glioma_type.csv`) — compare balanced accuracy to the tabular imaging baseline.
- **TCGA generalization:** train log-normal AFT on LGG, test on GBM (and reverse) — `glioma_benchmark_external.csv`.
- **Linkage:** `brats_tcga_linkage_report.json` documents PTG↔TCGA ID overlap for the 2024 extract (multimodal OS deferred to future official mapping).

## 7 Discussion

- **Reproducibility:** Python deepAFT aligns with Norman BJ/IPCW/transform; extensions are opt-in and tested in B–D.
- **Clinical framing:** gene panel is illustrative; IDH/MGMT/TP53 motivate AFT when PH fails—not a production prognostic signature without external validation.
- **Imaging:** radiomics and segmentation on BraTS; GNN over ET/NET/edema subregions as supervisor-suggested extension where implemented.

## 8 Conclusion

We delivered a limitation-aware Python deepAFT reimplementation, simulation evidence under controlled violations (50 replications per scenario), **TCGA** glioma survival benchmarks on 671 cases (deepAFT with group scale C-index ≈0.75), and **BraTS 2024 GLI** imaging analysis on 1621 segmented cases with PTG glioma-type and site prediction benchmarks. Multimodal overall-survival on the full 2024 PTG cohort is left to future work once an official PTG↔TCGA mapping is available.

## References (core)

- Norman, Li, Jiang, Chen (2024). deepAFT. *Statistics in Medicine*. doi:10.1002/sim.10152
- BraTS 2024 Challenge (Synapse syn53708249); GLI training zip syn60086071
- TCGA / GDC data access policies

## Appendix A — PyPI package release

Package builds with `python -m build`; wheel under `dist/`. TestPyPI upload is **user-operated** (`twine upload --repository testpypi dist/*`) with your credentials—not automated in this repo.

## Appendix B — Supplementary subregion graph baseline

Exploratory **classification** on ET/NET/edema graph features (`brats_gnn_glioma_type.csv`; sklearn, no torch). Supplements tabular imaging baselines in §6; **not** a substitute for deepAFT survival on TCGA OS.

## Appendix C — Reproducibility (versions and commands)

**Included in submission:** `results/reproducibility_snapshot.txt` (dual Python: default `python` for package/TCGA/04b; `py -3.12` for torch U-Net). To refresh after dependency upgrades, run from the repository root (PowerShell):

```powershell
.\scripts\capture_reproducibility.ps1
```

That writes **`results/reproducibility_snapshot.txt`** with Python versions and commands. **Note:** package and TCGA jobs use the default `python` (3.14.x here); **torch** jobs use **`py -3.12`** (torch 2.15+cpu). Paste or attach the snapshot in the thesis appendix.
