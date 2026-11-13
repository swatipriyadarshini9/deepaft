# Writes results/reproducibility_snapshot.txt for thesis Appendix C.
# Run from repo root: .\scripts\capture_reproducibility.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$out = Join-Path $Root "results\reproducibility_snapshot.txt"
New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null

$lines = @()
$lines += "MSc Dissertation reproducibility snapshot"
$lines += "Generated (local): $(Get-Date -Format 'yyyy-MM-dd HH:mm zzz')"
$lines += ""
$lines += "=== Python ==="
$lines += (python -V 2>&1 | Out-String).Trim()
$lines += ""
$lines += "=== Key packages ==="
$lines += (python -c "import pandas, sklearn; print('pandas', pandas.__version__); print('sklearn', sklearn.__version__)" 2>&1 | Out-String).Trim()
$lines += ""
$lines += "=== Python 3.12 (torch / U-Net / PyRadiomics) ==="
if (Get-Command py -ErrorAction SilentlyContinue) {
    $lines += (py -3.12 -V 2>&1 | Out-String).Trim()
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $lines += (py -3.12 -c "import torch; print('torch', torch.__version__)" 2>&1 | Out-String).Trim()
    $ErrorActionPreference = $prev
} else {
    $lines += "(py launcher not found)"
}
$lines += ""
$lines += "=== Git (if repo) ==="
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
Push-Location $Root
$gitHead = & git rev-parse HEAD 2>&1
$gitStatus = & git status -sb 2>&1
Pop-Location
$ErrorActionPreference = $prevEap
if ($LASTEXITCODE -eq 0 -and $gitHead) {
    $lines += ($gitHead | Out-String).Trim()
    $lines += ($gitStatus | Out-String).Trim()
} else {
    $lines += "(git not available or not a repo)"
}
$lines += ""
$lines += "=== Core commands (thesis primary evidence) ==="
$lines += "pip install -e `".[experiments,dev]`""
$lines += "python -m pytest -q"
$lines += "python experiments/run_simulation_chapter.py --replications 50  # or use checkpoints --resume"
$lines += "python experiments/03_gdc_survival_and_expression.py"
$lines += "python experiments/03b_fetch_tcga_expression.py"
$lines += "python experiments/05_train_glioma_models.py --cohort data/processed/tcga_glioma_cohort.csv --output results/tables/glioma_benchmark.csv"
$lines += "python experiments/04b_brats_imaging_features.py --require-seg"
$lines += "python experiments/07_brats_ptg_baseline.py"
$lines += "python experiments/07_brats_ptg_baseline.py --target site --output results/tables/brats_imaging_baseline_site.csv"
$lines += "python experiments/08_brats_validation_qc.py"
$lines += ".\\scripts\\run_torch_and_pyradiomics.ps1"
$lines += "python experiments/generate_thesis_results.py"

$text = ($lines -join "`n") + "`n"
[System.IO.File]::WriteAllText($out, $text, [System.Text.UTF8Encoding]::new($false))
Write-Host "Wrote $out" -ForegroundColor Green
