# Learned 2D U-Net + PyRadiomics smoke test (uses py -3.12 when 3.14 torch is blocked).
#
#   cd "C:\Users\Swati\Downloads\MSc. Dissertation"
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
#   .\scripts\run_torch_and_pyradiomics.ps1

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Test-Torch312 {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & py -3.12 -c "import torch; print(torch.__version__)" 1>$null 2>$null
    $ok = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prev
    return $ok
}

function Test-TorchDefault {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & python -c "import torch; print(torch.__version__)" 1>$null 2>$null
    $ok = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prev
    return $ok
}

$TorchPy = $null
if ((Get-Command py -ErrorAction SilentlyContinue) -and (Test-Torch312)) {
    $TorchPy = "py -3.12"
    Write-Host "Using py -3.12 for torch." -ForegroundColor Green
} elseif (Test-TorchDefault) {
    $TorchPy = "python"
    Write-Host "Using default python for torch." -ForegroundColor Green
}

if (-not $TorchPy) {
    Write-Host ""
    Write-Host "torch could not be imported." -ForegroundColor Red
    Write-Host "Install CPU torch on 3.12:"
    Write-Host "  py -3.12 -m pip install torch --index-url https://download.pytorch.org/whl/cpu"
    Write-Host "  py -3.12 -m pip install nibabel pandas"
    exit 1
}

function Run-TorchPy {
    param([string[]]$Rest, [switch]$AllowFail)
    if ($TorchPy -eq "py -3.12") {
        & py -3.12 @Rest
    } else {
        & python @Rest
    }
    if (-not $AllowFail -and $LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    return $LASTEXITCODE
}

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== Install nibabel/pandas for U-Net ===" -ForegroundColor Cyan
Run-TorchPy -Rest @("-m", "pip", "install", "nibabel", "pandas", "-q")

Write-Host ""
Write-Host "=== Learned 2D U-Net (several minutes) ===" -ForegroundColor Cyan
Run-TorchPy -Rest @("experiments/09_brats_unet2d_baseline.py")

Write-Host ""
Write-Host "=== PyRadiomics smoke (50 cases) ===" -ForegroundColor Cyan
Run-TorchPy -Rest @("-m", "pip", "install", "numpy", "scipy", "setuptools", "wheel", "SimpleITK", "-q") -AllowFail
$radOk = (Run-TorchPy -Rest @("-m", "pip", "install", "pyradiomics==3.0.1", "--no-build-isolation") -AllowFail) -eq 0

if ($radOk) {
    Run-TorchPy -Rest @(
        "experiments/04_radiomics_brats.py", "--require-seg", "--limit", "50",
        "--output", "data/processed/radiomics_pyradiomics_smoke.csv",
        "--manifest", "data/processed/radiomics_pyradiomics_smoke.json"
    )
    Write-Host "Wrote data/processed/radiomics_pyradiomics_smoke.csv"
} else {
    Write-Host "PyRadiomics install failed. Thesis already uses 04b (1621 cases)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Refresh thesis_results.md ===" -ForegroundColor Cyan
& python experiments/generate_thesis_results.py

Write-Host ""
Write-Host "Done. Check results/tables/brats_unet2d_dice.csv" -ForegroundColor Green
