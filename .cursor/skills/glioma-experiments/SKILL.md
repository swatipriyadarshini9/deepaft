---
name: glioma-experiments
description: BraTS 2024 GLI download, GDC/Xena TCGA cohort scripts, radiomics, and multimodal linkage. Use when working in experiments/, data/. Follow docs/PLAN.md for run order.
---

# Glioma experiments pipeline

## Data sources

| Source | ID | Survival? |
|--------|-----|-----------|
| BraTS 2024 GLI | Synapse syn51156910 | No OS in release |
| GDC TCGA-LGG/GBM | portal.gdc.cancer.gov | Yes |
| OncoLnc | oncolnc.org | Expression only; stale clinical |

## Script order (create in experiments/)

1. `01_download_brats2024.py`
2. `02_build_tcga_crosswalk.py`
3. `03_gdc_survival_and_expression.py`
4. `04_radiomics_brats.py`
5. `05_train_glioma_models.py` — imports `deepaft.DeepAFT`

## Subagent

Use `generalPurpose` for multi-file pipeline work; `explore` for finding existing linkage patterns.

## MCP

- `cursor-ide-browser` — navigate GDC/Synapse when user must authenticate manually.

## Linked

- Rule: `.cursor/rules/experiments-data.mdc`
- Tasks: PROJECT_TASKS.md Phase 2–4
