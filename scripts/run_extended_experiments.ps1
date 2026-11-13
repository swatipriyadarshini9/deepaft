# Extended dissertation experiments (no torch required except optional U-Net).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

python experiments/08_brats_validation_qc.py
python experiments/09_brats_seg_descriptive.py
python experiments/09c_brats_threshold_seg_baseline.py
python experiments/10_brats_subregion_gnn.py
python experiments/11_tcga_project_holdout.py
python experiments/12_brats_tcga_linkage_report.py
python experiments/generate_thesis_results.py

Write-Host "Done. See results/thesis_results.md (Extended analyses) and docs/extended_tasks_status.md"

# Optional when torch Application Control allows:
# python experiments/09_brats_unet2d_baseline.py
# .\scripts\run_pyradiomics_py312.ps1
