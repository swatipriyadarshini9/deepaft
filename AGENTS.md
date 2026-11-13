# Agent orchestration — MSc Dissertation / deepaft

This file links **subagents**, **skills**, **rules**, **hooks**, **MCPs**, and **tasks** for this repository. Read it at the start of every session.

## Project identity

| Item | Value |
|------|-------|
| Package | `deepaft` — Python reimplementation of Norman et al. (2024) + limitation extensions |
| Dissertation | deepAFT + extensions; **simulation**, **TCGA** glioma survival, **BraTS 2024 GLI** imaging/multimodal (`experiments/`) |
| Supervisor note | Optional GNN over ET / NET / edema subregions |

**Originality rule:** Cite Norman et al. 2024 for the core formula. Claim **extensions + glioma evaluation** as contribution — not “novel DeepAFT.” Never add fabricated C-index numbers to README.

---

## Subagents — when to launch

| Subagent | Use when | Prompt must include |
|----------|----------|---------------------|
| `explore` | Finding files, BraTS/OncoLnc patterns, codebase structure | Thoroughness: `medium` or `very thorough` |
| `generalPurpose` | Multi-step experiments, linkage scripts, radiomics pipeline | Full repo path + data constraints |
| `bugbot` | User asks for code review of local changes | `Full Repository Path`, `Diff: branch changes` or `uncommitted changes` |
| `security-review` | User explicitly asks security review | Same diff format as bugbot |
| `ci-investigator` | A CI check failed on a PR | PR URL or check name |

**Do not** use Task/subagents for simple single-file edits in `src/deepaft/`.

### Dissertation workflow subagent map

```
Simulation / package fixes     → agent directly (src/deepaft, tests/)
BraTS extract / radiomics / linkage → follow docs/PLAN.md Phase 1; explore then generalPurpose for long jobs
Radiomics batch job            → generalPurpose
Benchmark vs Cox/RSF/DeepSurv  → generalPurpose
Thesis README / methods text   → agent directly + dissertation-thesis skill
```

---

## Skills — project and user

### Project skills (`.cursor/skills/`)

| Skill | Path | Trigger |
|-------|------|---------|
| deepaft-development | `.cursor/skills/deepaft-development/SKILL.md` | Editing `src/deepaft/`, tests, pyproject |
| glioma-experiments | `.cursor/skills/glioma-experiments/SKILL.md` | `experiments/`, BraTS, GDC, OncoLnc |
| dissertation-thesis | `.cursor/skills/dissertation-thesis/SKILL.md` | README, thesis claims, viva framing |

### User skills (invoke when relevant)

| Skill | Path | Use for |
|-------|------|---------|
| create-rule | `~/.cursor/skills-cursor/create-rule/SKILL.md` | New `.cursor/rules/*.mdc` |
| create-hook | `~/.cursor/skills-cursor/create-hook/SKILL.md` | Hook changes |
| create-skill | `~/.cursor/skills-cursor/create-skill/SKILL.md` | New project skills |
| review-bugbot | `~/.cursor/skills-cursor/review-bugbot/SKILL.md` | `/review-bugbot` |
| share / new-repo | `~/.cursor/skills-cursor/share/SKILL.md` | Back up repo to Cursor |
| spreadsheets | `~/.codex/skills/.../spreadsheets/SKILL.md` | Cohort tables, results CSV |

---

## Rules (`.cursor/rules/`)

| Rule file | Scope |
|-----------|--------|
| `project-core.mdc` | Always — originality, Norman citation, no fake metrics |
| `deepaft-package.mdc` | `src/deepaft/**`, `tests/**` |
| `experiments-data.mdc` | `experiments/**`, `data/**` |

---

## Hooks (`.cursor/hooks.json`)

| Event | Script | Purpose |
|-------|--------|---------|
| `sessionStart` | `.cursor/hooks/session_start.py` | Inject project map + task checklist |
| `afterFileEdit` | `.cursor/hooks/after_deepaft_edit.py` | Remind to run pytest after package edits |

---

## MCPs — built-in namespaces for this project

Configure in Cursor Settings → MCP; project notes in `.cursor/mcp.json`.

| Namespace | Use in this repo |
|-----------|------------------|
| `cursor-ide-browser` | GDC portal, OncoLnc, Synapse BraTS pages (manual auth) |
| `cursor-app-control` | Open resources, rename chat, project root |
| `cursor` → `CreateGoal` / `UpdateGoal` | Long-running dissertation milestones |

**Not on PyPI:** BraTS loaders, NIfTI paths — keep in `experiments/` only.

---

## Tasks — dissertation milestones

See [docs/PLAN.md](docs/PLAN.md) for the full checklist (main work, BraTS, PyPI, future directions).

Current phase: **package complete** → next **experiments/data linkage**.

Quick commands:

```powershell
pip install -e ".[dev]"
python -m pytest -q
# BraTS zip ~37 GB: need ~40+ GB free on download drive. If C: is full, set DISSERTATION_BRATS_DIR in .env
# Long jobs: run in your terminal, not agent session
.\scripts\start_detached_jobs.ps1 -Job download   # or -Job download via run_dissertation_jobs
.\scripts\run_dissertation_jobs.ps1 -Job metadata  # small xlsx while zip runs
.\scripts\wait_and_pipeline.ps1                    # after zip completes → linked benchmark
.\scripts\check_dissertation_status.ps1 -Quick
.\scripts\run_dissertation_jobs.ps1 -Job simulation  # R=50 done; --resume if extending
.\scripts\run_dissertation_jobs.ps1 -Job pipeline
```

---

## Repository map

```
src/deepaft/          # PyPI package (Norman + extensions)
tests/                # Scenarios A–D
experiments/          # BraTS, TCGA, radiomics (dissertation only)
.cursor/              # Rules, skills, hooks, MCP notes
```
