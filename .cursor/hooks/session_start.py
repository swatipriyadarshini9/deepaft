#!/usr/bin/env python3
"""Inject dissertation project context at session start."""
import json
import sys

CONTEXT = """
MSc Dissertation / deepaft session started.

Read first: AGENTS.md, PROJECT_TASKS.md
Package: src/deepaft (Norman 2024 + limitation extensions)
Next milestone: experiments/ data linkage (BraTS + GDC TCGA)

Quick verify: python -m pytest -q
Skills: .cursor/skills/deepaft-development, glioma-experiments, dissertation-thesis
Rules: .cursor/rules/project-core.mdc (always apply)
""".strip()

def main() -> None:
    try:
        json.load(sys.stdin)
    except json.JSONDecodeError:
        pass
    print(json.dumps({"continue": True, "additional_context": CONTEXT}))

if __name__ == "__main__":
    main()
