---
name: deepaft-development
description: Develop and test the deepaft Python package (Norman 2024 reproduction + limitation extensions). Use when editing src/deepaft, tests, pyproject.toml, or running simulation scenarios A-D.
---

# deepaft development

## Before coding

1. Read [AGENTS.md](../../AGENTS.md) originality rules.
2. Distinguish **reproduced** (BJ/IPCW/Transform) vs **contributed** (covariate G, scale, guard).

## Package layout

- `estimator.py` — `DeepAFT` API
- `censoring.py` — KM, BJ imputation, IPCW weights, Fan-Gijbels
- `simulate.py` — scenarios A–D

## After every change

```powershell
python -m pytest -q
```

## API pattern

```python
from deepaft import DeepAFT
model = DeepAFT(method="buckley_james", censoring="covariate", scale="group")
model.fit(X, time, event, groups=groups)
```

## Do not

- Add Weibull/log-normal parametric likelihood as default (that contradicts Norman semi-parametric model).
- Put BraTS-specific code in `src/deepaft/`.

## Linked

- Rule: `.cursor/rules/deepaft-package.mdc`
- Tasks: PROJECT_TASKS.md Phase 1–3
