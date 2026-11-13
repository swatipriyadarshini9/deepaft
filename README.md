# deepaft

Python library for **deep accelerated failure time (AFT)** models with right-censored survival times. Training objectives follow Norman et al. (2024, *Statistics in Medicine*, doi:[10.1002/sim.10152](https://doi.org/10.1002/sim.10152)): Buckley–James imputation, inverse-probability-of-censoring weighting (IPCW), and the Fan–Gijbels transform. Reference implementation in R: `dnn::deepAFT`.

**Extensions in this codebase** (not in the original paper) address documented failure modes: covariate-stratified censoring survival for IPCW/transform, fallback to Buckley–James when IPCW weights are degenerate, and group- or input-dependent scaling of log-time residuals.

| Component | Location |
|-----------|----------|
| Installable API | `src/deepaft/` — `DeepAFT`, Harrell C-index, AMSE, `scenario_a`–`scenario_d` |
| Glioma evaluation scripts | `experiments/` (TCGA, BraTS 2024 GLI, simulation chapter) |
| Reported metrics | `results/tables/` (regenerate via `experiments/generate_thesis_results.py`) |

**Attribution.** Cite Norman et al. (2024) for deepAFT. Cite this repository for the Python reimplementation, the extensions above, and the glioma benchmark protocol ([`CITATION.cff`](CITATION.cff)).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## Installation

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
```

Optional cohort tooling (GDC/Xena, BraTS paths, lifelines PH tests):

```powershell
python -m pip install -e ".[experiments,dev]"
```

Requires PyTorch ≥ 2.0 for `DeepAFT`. On Windows hosts with application-control policies that block PyTorch on newer Python builds, install CPU torch on **Python 3.12** for imaging-only scripts in `experiments/`; the core package benchmarks in this project were run on the default interpreter where torch imports successfully.

## Usage

```python
from deepaft import DeepAFT, scenario_a, harrell_c_index

X, time, event = scenario_a(n=300, seed=42)
model = DeepAFT(method="buckley_james", hidden=(8, 6), epochs=100)
model.fit(X, time, event)
print(harrell_c_index(model.predict_time(X), time, event))
```

## Empirical evaluation (glioma)

Peer-reviewed methodology is Norman (2024); empirical claims below are from this repository’s frozen tables when present:

| Study | Design | Primary output |
|-------|--------|----------------|
| Simulation A–D | 50 replications, controlled assumption violations | `simulation_chapter_summary.csv` |
| TCGA adult glioma | 671 cases; IDH1, MGMT, TP53; GDC OS; 5-fold CV; Schoenfeld PH | `glioma_benchmark.csv`, `glioma_ph_test.json` |
| BraTS 2024 GLI | PTG training splits; imaging features; PTG label prediction | `brats_cohort_counts.csv`, `brats_imaging_baseline*.csv` |

Multimodal overall survival on the full 2024 PTG identifier set requires a published PTG↔TCGA crosswalk; linkage diagnostics are in `brats_tcga_linkage_report.json`. Narrative and model-choice discussion: `results/thesis_results.md` and `docs/dissertation_chapters.md`.

## Release

```powershell
python -m pip install build twine
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
python -m build
```

Upload instructions: [`docs/pypi_upload.md`](docs/pypi_upload.md).

## License

MIT for this source code. TCGA and BraTS data are subject to [GDC](https://portal.gdc.cancer.gov/) and Synapse data-use agreements respectively.
