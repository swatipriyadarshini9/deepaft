# Quick gate checks for dissertation milestones (read-only).
param([switch]$Quick)  # -Quick: skip stat on large partial (faster while downloading)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (Test-Path (Join-Path $Root ".env")) {
    Get-Content (Join-Path $Root ".env") | ForEach-Object {
        if ($_ -match '^DISSERTATION_BRATS_DIR=(.+)$') { $env:DISSERTATION_BRATS_DIR = $matches[1].Trim() }
    }
}
$BratsRel = if ($env:DISSERTATION_BRATS_DIR) { $env:DISSERTATION_BRATS_DIR } else { "data\raw\brats2024_training" }
if ([System.IO.Path]::IsPathRooted($BratsRel)) { $bratsDirFromEnv = $BratsRel } else { $bratsDirFromEnv = Join-Path $Root ($BratsRel -replace '/', '\') }

Write-Host "`n=== Simulation (R=50 target) ===" -ForegroundColor Cyan
$sim = Join-Path $Root "results\tables\simulation_chapter_summary.csv"
if (Test-Path $sim) {
    Import-Csv $sim | Group-Object scenario | ForEach-Object {
        $n = ($_.Group | Select-Object -First 1).n
        $ok = if ([int]$n -ge 50) { "OK" } else { "pending" }
        Write-Host "  Scenario $($_.Name): n=$n  [$ok]"
    }
} else {
    Write-Host "  Missing $sim"
}

Write-Host "`n=== BraTS GLI zip (syn60086071) ===" -ForegroundColor Cyan
$bratsDir = $bratsDirFromEnv
if ($env:DISSERTATION_BRATS_DIR) {
    Write-Host "  BraTS data dir: $bratsDir (DISSERTATION_BRATS_DIR)"
}
$bratsRoot = Split-Path -Parent $bratsDir
if (Test-Path $bratsRoot) {
    $drive = (Resolve-Path $bratsRoot).Drive.Name
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$drive`:'" -ErrorAction SilentlyContinue
    if ($disk) {
        $freeGb = [math]::Round($disk.FreeSpace / 1GB, 1)
        Write-Host "  Disk ${drive}: free $freeGb GB (need ~40 GB for zip; more for extract)"
        if ($freeGb -lt 40) {
            Write-Host "  WARNING: low disk space - download/extract will fail until you free space or use --output on another drive" -ForegroundColor Yellow
            $okDrives = @(Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" -ErrorAction SilentlyContinue |
                Where-Object { ($_.FreeSpace / 1GB) -ge 40 } |
                ForEach-Object { "$($_.DeviceID) $([math]::Round($_.FreeSpace / 1GB, 0)) GB free" })
            if ($okDrives.Count -gt 0) {
                Write-Host "  Drives with enough space: $($okDrives -join '; ') -> set DISSERTATION_BRATS_DIR"
            } else {
                Write-Host "  No fixed drive shows >= 40 GB free; free space or attach storage before download"
                $gliOpt = Join-Path $bratsDir "BraTS-GLI"
                if (Test-Path $gliOpt) {
                    $optZips = Get-ChildItem -Path $gliOpt -File -ErrorAction SilentlyContinue |
                        Where-Object { $_.Name -match 'additional|validation' -and $_.Extension -eq '.zip' }
                    if ($optZips) {
                        $r = [math]::Round((($optZips | Measure-Object Length -Sum).Sum / 1GB), 1)
                        Write-Host "  Hint: optional additional/validation zips under BraTS-GLI reclaim ~$r GB (see disk_recovery_hints.ps1)"
                    }
                }
            }
        }
    }
}
$zipName = "BraTS2024-BraTS-GLI-TrainingData.zip"
$zip = $null
$trackedPartial = $null
if (Test-Path $bratsDir) {
    $zipPath = Join-Path $bratsDir $zipName
    if (Test-Path $zipPath) { $zip = Get-Item $zipPath }
    if (-not $zip) {
        $zip = Get-ChildItem -Path $bratsDir -Filter $zipName -Depth 4 -ErrorAction SilentlyContinue |
            Select-Object -First 1
    }
}
if ($zip) {
    $gb = [math]::Round($zip.Length / 1GB, 2)
    Write-Host "  Zip: $($zip.FullName) ($gb GB)"
} else {
    $partials = @()
    $partialQuickDone = $false
    if (Test-Path $bratsDir) {
        $knownPartial = Join-Path $bratsDir "brats2024-brats-gli-trainingdata.zip.synapse_download_143397620"
        $partialCandidate = $null
        if (Test-Path -LiteralPath $knownPartial) { $partialCandidate = $knownPartial }
        else {
            $found = Get-ChildItem -Path $bratsDir -File -Filter "*trainingdata*.synapse_download*" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($found) { $partialCandidate = $found.FullName }
        }
        if ($partialCandidate) {
            $trackedPartial = $partialCandidate
            if ($Quick) {
                $partialGb = [math]::Round((Get-Item -LiteralPath $partialCandidate).Length / 1GB, 2)
                $pct = [math]::Min(100, [math]::Round(100 * $partialGb / 37.5, 1))
                Write-Host "  Partial download: $partialGb GB / ~37.5 GB ($pct%)  ($(Split-Path -Leaf $partialCandidate))"
                $partialQuickDone = $true
            } else {
                $partials = @(Get-Item -LiteralPath $partialCandidate)
            }
        }
    }
    if (-not $partialQuickDone) {
        if ($partials) {
            Write-Host "  Partial download file(s):"
            $partials | ForEach-Object { Write-Host "    $([math]::Round($_.Length/1GB,2)) GB  $($_.Name)" }
        } else {
            Write-Host "  No zip or partial file found under $bratsDir"
        }
    }
}
$dlProcs = @(Get-CimInstance Win32_Process -Filter "name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match '01_download_brats2024' })
if ($dlProcs.Count -gt 1) {
    Write-Host "  WARNING: $($dlProcs.Count) BraTS download processes (stop extras; one zip client only)" -ForegroundColor Yellow
} elseif ($dlProcs.Count -eq 1) {
    Write-Host "  Active download: PID $($dlProcs[0].ProcessId)"
}
if (-not $zip -and $trackedPartial -and (Test-Path -LiteralPath $trackedPartial)) {
    $staleMin = ((Get-Date) - (Get-Item -LiteralPath $trackedPartial).LastWriteTime).TotalMinutes
    if ($dlProcs.Count -eq 0) {
        Write-Host "  WARNING: partial on disk but no download process - re-run download (Synapse resumes)" -ForegroundColor Yellow
    } elseif ($staleMin -gt 15) {
        Write-Host "  WARNING: partial unchanged ~$([math]::Round($staleMin)) min (download may be stuck)" -ForegroundColor Yellow
    }
}
$metaXlsx = $null
if (Test-Path $bratsDir) {
    $metaXlsx = Get-ChildItem -Path $bratsDir -File -Filter "*metadata*.xlsx" -ErrorAction SilentlyContinue | Select-Object -First 1
}
if ($metaXlsx) {
    Write-Host "  GLI metadata xlsx: $($metaXlsx.Name)"
} else {
    Write-Host "  GLI metadata xlsx: not yet (optional: .\scripts\run_dissertation_jobs.ps1 -Job metadata)"
}
$caseDirs = @(Get-ChildItem -Path $bratsDir -Directory -Filter "BraTS-GLI-*" -ErrorAction SilentlyContinue)
Write-Host "  Extracted BraTS-GLI case dirs: $($caseDirs.Count)"
$crosswalk = Join-Path $Root "data\processed\brats_tcga_crosswalk.csv"
if (Test-Path $crosswalk) {
    $header = (Get-Content $crosswalk -TotalCount 1)
    if ($header -match "tcga_barcode") { Write-Host "  BraTS-TCGA crosswalk: OK ($crosswalk)" }
    else { Write-Host "  BraTS-TCGA crosswalk: invalid (no tcga_barcode); re-run 02 after zip extract" -ForegroundColor Yellow }
} else {
    Write-Host "  BraTS-TCGA crosswalk: missing (inside training zip mapping; run pipeline after extract)"
}

Write-Host "`n=== Benchmarks ===" -ForegroundColor Cyan
foreach ($f in @("glioma_benchmark.csv", "glioma_benchmark_linked.csv")) {
    $p = Join-Path $Root "results\tables\$f"
    if (Test-Path $p) { Write-Host "  OK  $f" } else { Write-Host "  --  $f (missing)" }
}

Write-Host ""
