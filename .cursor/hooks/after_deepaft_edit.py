#!/usr/bin/env python3
"""Remind agent to run pytest after deepaft package edits."""
import json
import sys
from pathlib import Path

PACKAGE_PREFIXES = ("src/deepaft/", "src\\deepaft\\", "tests/")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    paths: list[str] = []
    for key in ("file_path", "path", "filePath"):
        if key in payload and payload[key]:
            paths.append(str(payload[key]))
    for edit in payload.get("edits") or []:
        if isinstance(edit, dict) and edit.get("path"):
            paths.append(str(edit["path"]))

    touched = any(
        any(p.replace("\\", "/").startswith(prefix.replace("\\", "/")) for prefix in PACKAGE_PREFIXES)
        for p in paths
    )
    if not touched:
        # Also check cwd-relative common patterns
        for p in paths:
            if "deepaft" in p.replace("\\", "/") and p.endswith(".py"):
                touched = True
                break

    if touched:
        print(
            json.dumps(
                {
                    "additional_context": (
                        "deepaft package file edited. Run: python -m pytest -q "
                        "(see .cursor/skills/deepaft-development/SKILL.md)"
                    )
                }
            )
        )


if __name__ == "__main__":
    main()
