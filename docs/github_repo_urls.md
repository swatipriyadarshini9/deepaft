# Where to put your GitHub (or Git host) URL

Do **not** commit secrets here — only **public** repo URLs.

## Files to edit (same URL in both)

1. **[pyproject.toml](../pyproject.toml)** — `[project.urls]`

```toml
[project.urls]
Homepage = "https://github.com/YOUR_ACCOUNT/YOUR_REPO"
Documentation = "https://github.com/YOUR_ACCOUNT/YOUR_REPO#readme"
```

Replace `YOUR_ACCOUNT/YOUR_REPO` with your real path (e.g. `SwatiP9/deepaft`).

2. **[CITATION.cff](../CITATION.cff)** — `repository-code`

```yaml
repository-code: "https://github.com/YOUR_ACCOUNT/YOUR_REPO"
```

Also set `authors` in `CITATION.cff` to your name (replace placeholder `YourName` if still present).

## After you change them

- Re-run `python -m build` if you care about METADATA in the wheel reflecting the new URLs.
- Optional: `git remote -v` — your **remote** URL can be HTTPS (`https://github.com/...`) or SSH; it does not have to match `pyproject.toml`, but matching avoids confusion.

## If you do not use GitHub

Use your GitLab / Bitbucket / institution URL in the same two places.
