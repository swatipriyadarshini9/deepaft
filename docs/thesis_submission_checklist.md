# Submission checklist

Pipeline: **[PLAN.md](PLAN.md)**.

## Done in repository

- [x] Simulation R=50 — `simulation_chapter_summary.csv`
- [x] TCGA cohort + benchmark — `glioma_benchmark.csv`, PH test JSON
- [x] BraTS 2024 extract + 1621 imaging features — `radiomics_features.csv`
- [x] BraTS PTG baselines (glioma type, site) — `brats_imaging_baseline*.csv`
- [x] Thesis numbers compiled — `results/thesis_results.md` (includes **Model choice — deepAFT vs Cox**)
- [x] Draft chapters with BraTS §6 numbers — `dissertation_chapters.md`
- [x] GitHub URLs in `pyproject.toml` + `CITATION.cff`
- [x] **Appendix A** — PyPI / package build (`dissertation_chapters.md`)
- [x] **Appendix B** — Supplementary graph baseline (`brats_gnn_glioma_type.csv`)
- [x] **Appendix C** — Reproducibility (`results/reproducibility_snapshot.txt`; dual Python runtimes)

## Python runtimes (this project)

| Workload | Command |
|----------|---------|
| deepAFT, simulation, TCGA, 04b imaging (1621 cases) | `python` (3.14.x on author machine) |
| 2D U-Net, optional PyRadiomics | **`py -3.12`** (torch 2.15+cpu; 3.14 torch blocked by policy) |

Document both in Appendix C.

## Your steps before hand-in

1. Export dissertation Word/PDF from `dissertation_chapters.md` (appendices A–C are drafted; add figures if required).
2. In the **TCGA results / Discussion**, include the justified model-choice prose from `results/thesis_results.md` (section *Model choice — deepAFT vs Cox*), or the short pointer already in §5 of `dissertation_chapters.md`.
3. **Appendix C:** use existing `reproducibility_snapshot.txt`; re-run `.\scripts\capture_reproducibility.ps1` only if package versions or commands change.
4. Confirm ethics / data-use statements cite Norman (2024), TCGA/GDC, BraTS 2024 Synapse (syn53708249 / syn60086071).
5. PyPI: version **0.1.2** — [pypi_upload.md](pypi_upload.md) — not required for the degree if supervisor agrees.

## Data-use citations (paste in thesis)

- Norman et al. (2024) deepAFT — doi:10.1002/sim.10152  
- TCGA via NCI GDC — https://portal.gdc.cancer.gov/  
- BraTS 2024 GLI — Synapse challenge materials (cite challenge paper + data version you extracted)
