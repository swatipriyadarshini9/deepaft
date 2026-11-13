# Optional: PyRadiomics on Python 3.12 (limit 50 cases). Run from repo root.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$py = "py"
if (-not (Get-Command $py -ErrorAction SilentlyContinue)) {
    Write-Host "Python launcher 'py' not found; install Python 3.12."
    exit 1
}

& $py -3.12 -m pip install numpy setuptools wheel SimpleITK nibabel "pyradiomics==3.0.1" --no-build-isolation 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyRadiomics install failed on 3.12 — keep using 04b_brats_imaging_features.py on your default Python."
    exit 1
}

& $py -3.12 experiments/04_radiomics_brats.py --require-seg --limit 50 --output data/processed/radiomics_pyradiomics_smoke.csv
Write-Host "Wrote data/processed/radiomics_pyradiomics_smoke.csv (50-case smoke test)"
