# Push policy for `swatipriyadarshini9/deepaft`

Public pushes must **not** include BraTS/TCGA raw data, Norman PDFs, or local dissertation planning files. Those paths are in [`.gitignore`](../.gitignore).

## Before the first `git push`

Remove previously tracked exclusions (keeps files on disk):

```powershell
cd "C:\Users\Swati\Downloads\MSc. Dissertation"
git rm --cached "Statistics in Medicine - 2024 - Norman - deepAFT  A nonlinear accelerated failure time model with artificial neural network.pdf" 2>$null
git rm --cached AGENTS.md docs/dissertation_chapters.md docs/PLAN.md docs/thesis_submission_checklist.md PROJECT_TASKS.md 2>$null
git add README.md .gitignore pyproject.toml CITATION.cff LICENSE src tests experiments results docs/pypi_upload.md docs/pypi_credentials.md docs/github_repo_urls.md configs .cursor
git status
git commit -m "docs: README with BraTS 2024 GLI CC BY-NC attribution; exclude data and thesis-only files"
```

If the initial commit still contained a PDF and you have **not** pushed yet, rewrite history once:

```powershell
git reset --soft HEAD~1
git add -A
git status   # verify no PDF, no data/, no excluded md files
git commit -m "Initial public release: deepaft 0.1.2 with compliant README"
git tag -f v0.1.2
```

## Remote and push

```powershell
git remote add origin https://github.com/swatipriyadarshini9/deepaft.git
git push -u origin main
git push origin v0.1.2
```

PyPI/TestPyPI long description = `README.md` from the same commit you tag for release.
