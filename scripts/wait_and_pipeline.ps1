# Poll until BraTS training zip exists (after Synapse download + rename), then run full pipeline.
# Use in a dedicated PowerShell while the zip downloads elsewhere:
#   .\scripts\wait_and_pipeline.ps1
#   .\scripts\wait_and_pipeline.ps1 -PollMinutes 30

param(
    [int]$PollMinutes = 15,
    [double]$MinZipGB = 35
)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (Test-Path (Join-Path $Root ".env")) {
    Get-Content (Join-Path $Root ".env") | ForEach-Object {
        if ($_ -match '^DISSERTATION_BRATS_DIR=(.+)$') { $env:DISSERTATION_BRATS_DIR = $matches[1].Trim() }
    }
}
$BratsRel = if ($env:DISSERTATION_BRATS_DIR) { $env:DISSERTATION_BRATS_DIR } else { "data\raw\brats2024_training" }
if ([System.IO.Path]::IsPathRooted($BratsRel)) { $BratsDir = $BratsRel } else { $BratsDir = Join-Path $Root ($BratsRel -replace '/', '\') }

$zip = Join-Path $BratsDir "BraTS2024-BraTS-GLI-TrainingData.zip"
$partial = Join-Path $BratsDir "brats2024-brats-gli-trainingdata.zip.synapse_download_143397620"

Write-Host "Waiting for $zip (>= $MinZipGB GB)..." -ForegroundColor Cyan

while ($true) {
    if (Test-Path $zip) {
        $gb = (Get-Item $zip).Length / 1GB
        if ($gb -ge $MinZipGB) {
            Write-Host "Zip ready: $([math]::Round($gb, 2)) GB" -ForegroundColor Green
            break
        }
        Write-Host "Zip present but small ($([math]::Round($gb, 2)) GB); still writing?"
    } elseif (Test-Path $partial) {
        $gb = (Get-Item $partial).Length / 1GB
        $pct = [math]::Min(100, [math]::Round(100 * $gb / 37.5, 1))
        Write-Host "$(Get-Date -Format 'HH:mm') partial $([math]::Round($gb, 2)) GB (~$pct%)"
    } else {
        Write-Host "$(Get-Date -Format 'HH:mm') no zip or partial yet"
    }
    Start-Sleep -Seconds ($PollMinutes * 60)
}

$env:DISSERTATION_BRATS_DIR = $BratsDir
& (Join-Path $Root "scripts\run_dissertation_jobs.ps1") -Job pipeline
