# List large files under this repo (helps free ~40 GB for BraTS on C:).
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (Test-Path (Join-Path $Root ".env")) {
    Get-Content (Join-Path $Root ".env") | ForEach-Object {
        if ($_ -match '^DISSERTATION_BRATS_DIR=(.+)$') { $env:DISSERTATION_BRATS_DIR = $matches[1].Trim() }
    }
}
$BratsRel = if ($env:DISSERTATION_BRATS_DIR) { $env:DISSERTATION_BRATS_DIR } else { "data\raw\brats2024_training" }
if ([System.IO.Path]::IsPathRooted($BratsRel)) { $bratsDir = $BratsRel } else { $bratsDir = Join-Path $Root ($BratsRel -replace '/', '\') }
$gli = Join-Path $bratsDir "BraTS-GLI"
if (Test-Path $gli) {
    $optional = Get-ChildItem -Path $gli -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match 'additional|validation' -and $_.Extension -eq '.zip' }
    if ($optional) {
        $reclaim = ($optional | Measure-Object -Property Length -Sum).Sum / 1GB
        Write-Host "Thesis needs training zip only (syn60086071). Optional BraTS zips (safe to delete if you do not need them):" -ForegroundColor Yellow
        $optional | ForEach-Object { Write-Host ("  {0:N2} GB  {1}" -f ($_.Length / 1GB), $_.FullName) }
        Write-Host ("  -> reclaims ~{0:N1} GB on this drive (still need ~40 GB total for download+extract)" -f $reclaim)
        Write-Host ""
    }
}
Write-Host "Largest files under $Root (top 15):" -ForegroundColor Cyan
Get-ChildItem -Path $Root -Recurse -File -ErrorAction SilentlyContinue |
    Sort-Object Length -Descending |
    Select-Object -First 15 @{ N = "GB"; E = { [math]::Round($_.Length / 1GB, 2) } }, FullName |
    Format-Table -AutoSize
$disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'" -ErrorAction SilentlyContinue
if ($disk) {
    Write-Host "C: free $([math]::Round($disk.FreeSpace / 1GB, 1)) GB (BraTS zip needs ~40 GB on download drive)"
}
