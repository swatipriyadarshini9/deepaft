# Run long dissertation jobs in YOUR terminal (Cursor agent sessions may timeout ~20 min).
# Usage:
#   cd "C:\Users\Swati\Downloads\MSc. Dissertation"
#   .\scripts\run_dissertation_jobs.ps1 -Job download
#   .\scripts\run_dissertation_jobs.ps1 -Job simulation
#   .\scripts\run_dissertation_jobs.ps1 -Job pipeline
#   .\scripts\run_dissertation_jobs.ps1 -Job all

param(
    [ValidateSet("download", "metadata", "simulation", "pipeline", "thesis", "all")]
    [string]$Job = "all"
)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not $env:SYNAPSE_AUTH_TOKEN -and (Test-Path ".env")) {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.+)$') {
            $k = $matches[1].Trim()
            $v = $matches[2].Trim()
            if ($k -eq "SYNAPSE_AUTH_TOKEN" -or -not (Get-Item "Env:$k" -ErrorAction SilentlyContinue)) {
                Set-Item -Path "Env:$k" -Value $v
            }
        }
    }
}

$BratsRel = if ($env:DISSERTATION_BRATS_DIR) { $env:DISSERTATION_BRATS_DIR } else { "data/raw/brats2024_training" }
if ([System.IO.Path]::IsPathRooted($BratsRel)) {
    $BratsDir = $BratsRel
} else {
    $BratsDir = Join-Path $Root ($BratsRel -replace '/', '\')
}

function Run-Download {
    Write-Host "=== BraTS GLI training zip (syn60086071, ~37-48 GB) -> $BratsDir ===" -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path (Join-Path $Root "results\logs") | Out-Null
    python experiments/01_download_brats2024.py --output $BratsDir
}

function Run-Metadata {
    Write-Host "=== BraTS GLI metadata xlsx (syn64735496, small; OK while zip downloads) ===" -ForegroundColor Cyan
    python experiments/01_download_brats2024.py --metadata-only --output $BratsDir
}

function Run-Simulation {
    Write-Host "=== Simulation chapter R=50 (several hours) ===" -ForegroundColor Cyan
    python experiments/run_simulation_chapter.py --replications 50 --epochs 80
}

function Run-Pipeline {
    Write-Host "=== BraTS -> TCGA pipeline (brats-dir: $BratsDir) ===" -ForegroundColor Cyan
    python experiments/run_brats_pipeline.py --brats-dir $BratsDir
}

function Run-Thesis {
    python experiments/generate_thesis_results.py
}

switch ($Job) {
    "download"   { Run-Download }
    "metadata"   { Run-Metadata }
    "simulation" { Run-Simulation; Run-Thesis }
    "pipeline"   { Run-Pipeline }
    "thesis"     { Run-Thesis }
    "all"        { Run-Download; Run-Simulation; Run-Pipeline; Run-Thesis }
}

Write-Host "Done." -ForegroundColor Green
