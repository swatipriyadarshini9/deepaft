# PyPI and TestPyPI upload

`pyproject.toml` holds version and short `description`; **`README.md`** is the long description (BraTS 2024 Synapse syn53708249 attribution; no imaging data in the package).

```powershell
cd "C:\Users\Swati\Downloads\MSc. Dissertation"
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-..."   # TestPyPI token first

python -m pip install build twine
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
python -m build
python -m twine upload --repository-url https://test.pypi.org/legacy/ dist\*
```

After checking the TestPyPI page, upload to production with a PyPI-scoped token:

```powershell
python -m twine upload dist\*
```

Bump `version` in `pyproject.toml` for each new release.
