# Dissertation master plan

**One checklist** for the MSc: **BraTS 2024 GLI** imaging results, lock thesis numbers, then refresh TestPyPI/PyPI with plain English text.

Thesis prose: [dissertation_chapters.md](dissertation_chapters.md). Upload tokens: [pypi_credentials.md](pypi_credentials.md).

---

## Where you are now

| Track | State |
|-------|--------|
| **deepaft package + tests** | Done |
| **Simulation A–D (R=50)** | Done → `results/tables/simulation_chapter_summary.csv` |
| **TCGA survival + genes** | Done → `glioma_benchmark.csv`, 671 cases |
| **BraTS 2024 GLI** | Done → 1809 cases; **1621** imaging features; PTG baselines in `results/tables/` |
| **Multimodal OS (2024 PTG ↔ TCGA)** | **Future directions** until an official crosswalk overlaps your PTG IDs |
| **TestPyPI** | `deepaft` 0.1.0 uploaded — re-publish **0.1.1+** after README pass |
| **Production PyPI** | After TestPyPI looks right |

```powershell
.\scripts\check_dissertation_status.ps1 -Quick
```

---

## Phase 1 — BraTS 2024 (complete on your machine)

Local layout:

- `data/raw/brats2024_training/.../training_data1_v2` — 1350 cases  
- `.../training_data_additional` — 271  
- `.../validation_data` — 188 (no seg)

Already run:

- `summarize_brats_inventory.py` → `brats_cohort_counts.csv`  
- `04b_brats_imaging_features.py --require-seg` → `radiomics_features.csv` (1621 rows)  
- `07_brats_ptg_baseline.py` → glioma type + site metrics  

### Phase 1 remaining (optional polish)

- [x] BraTS numbers in [dissertation_chapters.md](dissertation_chapters.md) §6  
- [x] Validation QC — `08_brats_validation_qc.py`  
- [x] Segmentation Dice — **2D U-Net** via **`py -3.12`** → `brats_unet2d_dice.csv`  
- [x] Appendix C snapshot in `results/reproducibility_snapshot.txt` (re-run `capture_reproducibility.ps1` only if versions change)

**Do not** present `glioma_benchmark_linked.csv` as 2024 PTG multimodal evidence until `brats_tcga_crosswalk.csv` shares IDs with `radiomics_features.csv` (currently **zero overlap** — rebuild crosswalk when the **2024** mapping file exists).

---

## Phase 2 — Thesis submission

- Word/LaTeX from `dissertation_chapters.md`; figures from `results/tables/`  
- [thesis_submission_checklist.md](thesis_submission_checklist.md)  
- Ethics: GDC TCGA, Synapse BraTS  
- Discussion: three evidence blocks — **simulation**, **TCGA OS**, **BraTS 2024 imaging**; multimodal OS on full 2024 cohort as **future directions** (§6 in chapters)

---

## Phase 3 — TestPyPI / PyPI

1. Short human `README.md` + `pyproject.toml` description (see below).  
2. Bump version; `python -m build`  
3. `python -m twine upload` — [pypi_credentials.md](pypi_credentials.md)  
4. Fix Homepages: [github_repo_urls.md](github_repo_urls.md)

Release text (also in `pyproject.toml` / README):

> Deep accelerated failure time models (Norman et al., 2024): Buckley–James, IPCW, and transform losses with extensions for covariate-dependent censoring, degenerate IPCW, and group residual scale; glioma evaluation scripts and tables in the companion repository.

---

## Additional tasks (extended scope)

| Task | Notes |
|------|--------|
| **Segmentation (Dice/HD95)** | PTG Train / Train-additional only |
| **Validation holdout** | Modality QC / domain; no public seg on validation split |
| **PyRadiomics (full)** | **`py -3.12`** — `run_pyradiomics_py312.ps1` or `run_torch_and_pyradiomics.ps1` (smoke); thesis features = **04b** on default `python` |
| **GNN on ET/NET/edema** | sklearn graph baseline done; torch GNN optional on **3.12** |
| **U-Net chapter** | **Done** — `09_brats_unet2d_baseline.py` on **3.12** (torch CPU) |
| **`02c_fetch_tcga_crosswalk_api.py`** | Exploratory demographic matching only; cite caveats |
| **Multimodal OS on 2024 PTG** | When official PTG↔TCGA table exists: `02_build_tcga_crosswalk.py` → `run_brats_pipeline.py` |
| **External validation** | Second glioma cohort / held-out TCGA |

---

## Future directions (thesis Discussion)

1. Official **BraTS 2024 PTG ↔ TCGA** mapping → full multimodal deepAFT on imaging + GDC OS.  
2. Joint radiomics + genes on linked cases.  
3. Institutional linkage beyond public Synapse bundles.  
4. External validation cohorts.

---

## Commands cheat sheet

```powershell
python -m pytest -q
python experiments/generate_thesis_results.py
.\scripts\capture_reproducibility.ps1
.\scripts\run_torch_and_pyradiomics.ps1   # py -3.12: U-Net + optional PyRadiomics
python -m build
```

---

## Docs map

| File | Role |
|------|------|
| **PLAN.md** | This checklist |
| [dissertation_chapters.md](dissertation_chapters.md) | Thesis text |
| [pypi_credentials.md](pypi_credentials.md) | Upload secrets |
| [github_repo_urls.md](github_repo_urls.md) | PyPI URLs |
