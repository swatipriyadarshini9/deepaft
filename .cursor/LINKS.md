# Cursor integration index

Single map of all agent tooling for this repository.

## Hub documents

| Document | Role |
|----------|------|
| [AGENTS.md](../AGENTS.md) | Subagents, skills, rules, hooks, MCPs |
| [PROJECT_TASKS.md](../PROJECT_TASKS.md) | Dissertation checklist |
| [README.md](../README.md) | Public package + pipeline docs |

## Rules (`.cursor/rules/`)

| File | alwaysApply | globs |
|------|-------------|-------|
| `project-core.mdc` | yes | — |
| `deepaft-package.mdc` | no | `src/deepaft/**`, `tests/**` |
| `experiments-data.mdc` | no | `experiments/**`, `data/**` |

## Skills (`.cursor/skills/`)

| Skill | Directory |
|-------|-----------|
| deepaft-development | `deepaft-development/SKILL.md` |
| glioma-experiments | `glioma-experiments/SKILL.md` |
| dissertation-thesis | `dissertation-thesis/SKILL.md` |

## User skills (reference only)

| Skill | Path |
|-------|------|
| create-rule | `~/.cursor/skills-cursor/create-rule/SKILL.md` |
| create-hook | `~/.cursor/skills-cursor/create-hook/SKILL.md` |
| create-skill | `~/.cursor/skills-cursor/create-skill/SKILL.md` |
| review-bugbot | `~/.cursor/skills-cursor/review-bugbot/SKILL.md` |
| share | `~/.cursor/skills-cursor/share/SKILL.md` |

## Hooks (`.cursor/hooks.json`)

| Event | Script |
|-------|--------|
| sessionStart | `hooks/session_start.py` |
| afterFileEdit | `hooks/after_deepaft_edit.py` |
| subagentStart | `hooks/subagent_context.py` |

## Subagents

| Type | Dissertation use |
|------|------------------|
| explore | Codebase / data layout |
| generalPurpose | experiments/ pipelines |
| bugbot | Pre-submit review |
| security-review | Explicit security audit |
| ci-investigator | PR CI failures |

## MCPs

See [mcp.json](mcp.json). Built-in: `cursor-ide-browser`, `cursor-app-control`, `cursor` (Goals).

## Verify hooks load

Cursor → Settings → Hooks → confirm `.cursor/hooks.json` is active. Restart Cursor if hooks do not appear after save.
