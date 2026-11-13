# PyPI and TestPyPI upload

Package metadata is defined in `pyproject.toml`; the project page long description is `README.md` (rendered as Markdown on PyPI).

## One-time token setup (PowerShell)

Create an API token on [TestPyPI](https://test.pypi.org/manage/account/) and [PyPI](https://pypi.org/manage/account/). Do not commit tokens.

```powershell
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-AgEN..."   # paste token once per session
```

Optional persistent config (user home only): `~/.pypirc` with `[testpypi]` and `[pypi]` repositories — see [Twine documentation](https://twine.readthedocs.io/).

## Build wheel and sdist

From the repository root:

```powershell
cd "C:\Users\Swati\Downloads\MSc. Dissertation"
python -m pip install build twine
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
python -m build
```

Artifacts: `dist/deepaft-0.1.2-py3-none-any.whl` and `dist/deepaft-0.1.2.tar.gz` (version must match `pyproject.toml`).

## Upload to TestPyPI (verify README first)

```powershell
python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

Smoke install:

```powershell
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ deepaft==0.1.2
python -c "from deepaft import DeepAFT; print(DeepAFT)"
```

## Upload to production PyPI

After TestPyPI metadata and README look correct:

```powershell
python -m twine upload dist/*
```

Use a **new token** scoped to PyPI (not TestPyPI). Each `twine upload` must target a **new version** number; you cannot overwrite an existing release.

## Suggested project summary (TestPyPI / PyPI web form)

If the site asks for a one-line summary separate from `description` in `pyproject.toml`:

> Python deep accelerated failure time models after Norman et al. (2024), with statistically motivated extensions for censoring mechanics and glioma cohort evaluation scripts.

## GitHub sync

Remote: `https://github.com/swatipriyadarshini9/deepaft`. Push the same commit that produced the release tag so PyPI `Homepage` matches the tree users inspect.
