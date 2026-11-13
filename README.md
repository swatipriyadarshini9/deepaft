# deepaft

Python implementation of **deep accelerated failure time (deepAFT)** models for right-censored survival data (Norman et al., 2024, *Statistics in Medicine*, doi:[10.1002/sim.10152](https://doi.org/10.1002/sim.10152); R reference: `dnn::deepAFT`). The library supports Buckley–James, inverse-probability-of-censoring-weighted (IPCW), and Fan–Gijbels transform training objectives, plus **extensions** for covariate-stratified censoring survival, automatic Buckley–James fallback when IPCW weights are degenerate, and group- or input-dependent scaling of log-time residuals.

This repository couples the installable package (`src/deepaft/`) with reproducible **glioma** evaluation code (`experiments/`) and frozen **aggregate** result tables (`results/tables/`). It does **not** redistribute TCGA case-level downloads or BraTS magnetic resonance imaging volumes.

---

## Package contents

| Component | Description |
|-----------|-------------|
| `DeepAFT` | Feed-forward network for the AFT log-time mean; methods `buckley_james`, `ipcw`, `transform` |
| `limitations` / `censoring` | Covariate censoring, `auto_fallback`, residual `scale` options |
| `simulate.scenario_a`–`d` | Monte Carlo generators aligned with scenarios A–D (assumption stress tests) |
| `metrics` | Harrell concordance index, AMSE helpers |
| `tests/` | Unit tests for censoring, estimation, simulation |

```python
from deepaft import DeepAFT, scenario_a, harrell_c_index

X, time, event = scenario_a(n=300, seed=42)
model = DeepAFT(method="buckley_james", hidden=(8, 6), epochs=100)
model.fit(X, time, event)
print(harrell_c_index(model.predict_time(X), time, event))
```

### Installation

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
```

Cohort scripts (GDC, Xena, BraTS path utilities): `python -m pip install -e ".[experiments,dev]"`. PyTorch ≥ 2.0 is required for `DeepAFT`. Imaging-side PyTorch baselines (2D U-Net) were run on **Python 3.12** with CPU wheels where host policy blocked PyTorch on newer interpreters; see `experiments/09_brats_unet2d_baseline.py`.

---

## Empirical evaluation (glioma)

**Methodological attribution:** cite Norman et al. (2024) for deepAFT. Cite this repository for the Python port, extensions, and benchmark protocol ([`CITATION.cff`](CITATION.cff)).

| Track | Design | Outputs in `results/tables/` |
|-------|--------|------------------------------|
| **Simulation A–D** | 50 replications; scenarios stress covariate censoring, degenerate IPCW, group heteroscedasticity | `simulation_chapter_summary.csv` |
| **TCGA adult glioma** | 671 cases; OS from NCI GDC; expression IDH1, MGMT, TP53 (Xena HiSeqV2); 5-fold CV; Schoenfeld PH on Cox model | `glioma_benchmark.csv`, `glioma_ph_test.json` |
| **BraTS 2024 GLI (PTG)** | Adult Glioma Post-Treatment challenge training release; 1809 cases inventoried locally, 1621 with segmentations for feature extraction; PTG glioma-type and site prediction (5-fold CV); exploratory 2D U-Net Dice on held-out slices | `brats_cohort_counts.csv`, `brats_imaging_baseline*.csv`, `brats_unet2d_dice.csv`, `brats_validation_qc.csv` |

Extended diagnostics: subregion volume descriptives, sklearn graph baseline on ET/NET/edema features, LGG↔GBM project holdout (`glioma_benchmark_external.csv`), PTG↔TCGA linkage report (`brats_tcga_linkage_report.json`). **Multimodal overall survival on the full 2024 PTG identifier set was not performed** in the reported tables because stored crosswalks did not overlap PTG feature IDs (see linkage JSON).

Narrative compilation (auto-generated): `python experiments/generate_thesis_results.py` → `results/thesis_results.md` (includes proportional-hazards assessment and deepAFT-versus-Cox discussion tied to frozen CSVs).

---

## TCGA data (survival and expression)

- **Clinical and vital status:** [NCI Genomic Data Commons](https://portal.gdc.cancer.gov/) for projects TCGA-LGG and TCGA-GBM, subject to GDC data-use and publication policies.
- **Gene expression:** public Xena / legacy archive alignments used only for the three-gene panel; OncoLnc-style tables may supplement demographics but **GDC** is the authority for vital status (2016 freeze not used for GBM OS in this work).

No TCGA BAM/FASTQ or patient identifiers are committed to this repository.

---

## BraTS 2024 GLI data — terms, access, and attribution

Imaging experiments use **BraTS 2024 Adult Glioma Post-Treatment (GLI)** data from the Brain Tumor Segmentation (BraTS) Challenge distributed on **Sage Bionetworks Synapse**. Access requires a Synapse account, **Request Access** on the data entity, and acceptance of the **post-challenge Terms and Conditions** on the BraTS 2024 project.

### Synapse entities used in this work

| Item | Synapse ID | Use |
|------|------------|-----|
| BraTS 2024 Challenge (project hub, wiki, terms) | [syn53708249](https://www.synapse.org/Synapse:syn53708249) | Registration, data-use agreement, citations |
| GLI training data (folder / download root) | [syn64952546](https://www.synapse.org/Synapse:syn64952546) | Authorized retrieval target for local extract (`data/raw/brats2024_training/`, git-ignored) |
| `BraTS2024-BraTS-GLI-TrainingData.zip` (version 2) | [syn60086071](https://www.synapse.org/Synapse:syn60086071) | Primary training archive referenced in `configs/data_paths.yaml` |

**Task documentation:** [BraTS 2024 GLI wiki](https://www.synapse.org/Synapse:syn53708249/wiki/627500) (data description; Synapse discussion [thread 11134](https://www.synapse.org/Synapse:syn53708249/discussion/threadId=11134) links the GLI task paper).

### Required literature citations (BraTS 2024)

When you use BraTS 2024 GLI data or report imaging results derived from them, cite **at minimum** the GLI task manuscript named on Synapse for this task, and the BraTS 2024 cluster experimental-design document:

1. **GLI task (post-treatment adult glioma MRI):** Correia de Verdier, M., Saluja, R., Gagnon, L., LaBella, D., et al. (2024). *The 2024 Brain Tumor Segmentation (BraTS) Challenge: Glioma Segmentation on Post-treatment MRI.* arXiv:2405.18368. [https://doi.org/10.48550/arXiv.2405.18368](https://doi.org/10.48550/arXiv.2405.18368) · [arXiv](https://arxiv.org/abs/2405.18368)

2. **BraTS 2024 cluster (experimental design, all tasks):** Bakas, S., Baid, U., Rudie, J. D., Calabrese, E., et al. (2024). *BraTS 2024 Cluster of Challenges (BraTS + Beyond-BraTS).* Zenodo record 10978907. [https://doi.org/10.5281/zenodo.10978907](https://doi.org/10.5281/zenodo.10978907) · [Zenodo](https://zenodo.org/records/10978907)

BibTeX (GLI task):

```bibtex
@article{brats2024gli,
  title   = {The 2024 Brain Tumor Segmentation ({BraTS}) Challenge: Glioma Segmentation on Post-treatment {MRI}},
  author  = {Correia de Verdier, Maria and Saluja, Rachit and others},
  year    = {2024},
  eprint  = {2405.18368},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CV},
  doi     = {10.48550/arXiv.2405.18368},
  url     = {https://arxiv.org/abs/2405.18368}
}
```

### License and permitted use (summary)

BraTS 2024 challenge data are made available under **Creative Commons Attribution–NonCommercial 4.0 International ([CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/))**. In accepting Synapse terms you agree that:

1. **Non-commercial use:** data may be used for non-commercial research and education only, consistent with CC BY-NC 4.0.
2. **Citation:** cite the GLI task paper (arXiv:2405.18368) and the BraTS 2024 cluster design document (Zenodo 10.5281/zenodo.10978907), in addition to any updated citation list on the Synapse wiki.
3. **Attribution:** research outputs must acknowledge the BraTS challenge organizers. For this repository’s imaging chapter, use wording along the lines of:

   > *Imaging data used in this work were obtained from the Brain Tumor Segmentation (BraTS) 2024 Challenge, Adult Glioma Post-Treatment (GLI) task, through Sage Bionetworks Synapse (project ID: syn53708249).*

4. **No redistribution:** this **Git repository, PyPI/TestPyPI source distribution, and README do not include BraTS DICOM/NIfTI volumes, official segmentations, or participant-level challenge metadata.** Obtain data only through Synapse after accepting the live terms on the project page.
5. **User information (Synapse):** by downloading BraTS data you consent that Sage Bionetworks may share download activity and account profile fields with challenge organizers for data-governance and usage evaluation, as stated in the Synapse data-use agreement and [Sage Bionetworks Privacy Policy](https://sagebionetworks.org/privacy-policy/).

### What this repository publishes derived from BraTS

Only **aggregate, non-imaging** artifacts generated on authorized local copies, for example cohort counts, cross-validated classifier metrics on hand-crafted imaging features, validation-split modality QC, and exploratory segmentation scores. Scripts: `experiments/04b_brats_imaging_features.py`, `07_brats_ptg_baseline.py`, `08_brats_validation_qc.py`, `09_brats_unet2d_baseline.py`, and related utilities under `experiments/`.

---

## Repository scope (not included in git)

The following are **intentionally excluded** from version control (see [`.gitignore`](.gitignore)):

- BraTS and TCGA **raw** downloads (`data/raw/`, `data/processed/`, `*.nii`, `*.nii.gz`)
- Synapse credentials (`.synapseConfig`, `.env`)
- Local dissertation working documents not required for the public package (`docs/dissertation_chapters.md`, `docs/PLAN.md`, `AGENTS.md`)
- Third-party **publisher PDFs** (e.g. Norman et al. full text)

---

## Release (PyPI / TestPyPI)

```powershell
python -m pip install build twine
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
python -m build
```

Upload steps: [`docs/pypi_upload.md`](docs/pypi_upload.md). The **long description** on PyPI is this README (including the BraTS data-use section above).

---

## License

**Source code:** [MIT](LICENSE).

**Data:** TCGA and BraTS are subject to their respective host agreements (GDC; Synapse CC BY-NC 4.0 for BraTS 2024 GLI). Compliance with those terms is the responsibility of anyone who downloads primary data or reproduces this work.
