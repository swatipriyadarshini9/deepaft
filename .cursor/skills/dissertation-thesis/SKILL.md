---
name: dissertation-thesis
description: Frame MSc dissertation claims, README, and viva-defensible wording for deepAFT glioma work. Use when writing thesis text, README results sections, or explaining reproduced vs contributed work.
---

# Dissertation thesis framing

## Contribution statement (thesis + PyPI)

"We reimplemented Norman et al. (2024) deepAFT in Python, proposed limitation-aware extensions, and evaluate on **simulation**, **TCGA** adult glioma survival (GDC + Xena), and **BraTS 2024 GLI** imaging (PTG splits, radiomics/segmentation, multimodal merge where mapping files exist). Report only metrics that appear in `results/`; mark BraTS imaging pipelines still running as in progress in prose, not as out of scope."

## README results section

- List metrics and models with **empty cells** until runs exist.
- Never claim beating RSF unless measured on your cohort.

## PH vs AFT

Run Grambsch–Therneau before preferring AFT. If PH holds, Cox is primary; deepAFT is time-prediction secondary.

## Linked

- Rule: `.cursor/rules/project-core.mdc`
- Citation: CITATION.cff, Norman 2024 doi:10.1002/sim.10152
