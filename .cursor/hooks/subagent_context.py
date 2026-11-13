#!/usr/bin/env python3
"""Inject AGENTS.md routing hints when subagents start."""
import json
import sys

HINT = """
Subagent working on MSc Dissertation / deepaft repo.

Hub: AGENTS.md — subagent/skill/MCP map
Package changes: src/deepaft + tests only for PyPI
Data/experiments: experiments/ (BraTS CC BY-NC-SA, not PyPI)
Never fabricate survival metrics in README.
""".strip()


def main() -> None:
    try:
        json.load(sys.stdin)
    except json.JSONDecodeError:
        pass
    print(json.dumps({"permission": "allow", "user_message": HINT[:200]}))


if __name__ == "__main__":
    main()
