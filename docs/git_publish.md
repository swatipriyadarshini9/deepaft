# Git and GitHub (`swatipriyadarshini9/deepaft`)

Use a **repository root at this dissertation folder**, not your Windows user profile (an accidental `git init` under `C:\Users\Swati` will track your entire home directory).

## First-time setup (if this folder is not yet its own repo)

```powershell
cd "C:\Users\Swati\Downloads\MSc. Dissertation"
git init
git branch -M main
git remote add origin https://github.com/swatipriyadarshini9/deepaft.git
```

If `origin` already exists, update it:

```powershell
git remote set-url origin https://github.com/swatipriyadarshini9/deepaft.git
```

## Commit release 0.1.2 (README + pyproject)

```powershell
cd "C:\Users\Swati\Downloads\MSc. Dissertation"
git add README.md pyproject.toml CITATION.cff docs/pypi_upload.md docs/pypi_credentials.md docs/git_publish.md docs/PLAN.md docs/thesis_submission_checklist.md experiments/generate_thesis_results.py docs/dissertation_chapters.md results/thesis_results.md results/reproducibility_snapshot.txt
git status
git commit -m "$( @'
Release 0.1.2: scientific PyPI README and metadata.

Align package description with dissertation evidence (simulation, TCGA, BraTS 2024); document TestPyPI/PyPI upload and git workflow.
'@ )"
git tag v0.1.2
git push -u origin main
git push origin v0.1.2
```

Add any other modified files shown by `git status` before committing. Do not commit `.env`, `data/raw/`, or tokens.

## If GitHub already has history

```powershell
git pull origin main --rebase
# resolve conflicts if any, then push
git push origin main
```
