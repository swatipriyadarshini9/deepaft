# Top-level folder sizes under common C: locations (read-only; helps free ~40 GB for BraTS).
param([int]$Top = 12)

function Get-FolderSizeBytes {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $null }
    $sum = (Get-ChildItem -LiteralPath $Path -Recurse -File -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
    return [int64]$sum
}

$disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'" -ErrorAction SilentlyContinue
if ($disk) {
    $free = [math]::Round($disk.FreeSpace / 1GB, 1)
    $need = 40
    Write-Host "C: free $free GB (BraTS training zip + headroom needs ~$need GB on download drive)" -ForegroundColor Cyan
    if ($free -lt $need) {
        Write-Host "Shortfall: ~$([math]::Round($need - $free, 0)) GB still needed on C: unless DISSERTATION_BRATS_DIR points elsewhere." -ForegroundColor Yellow
    }
    Write-Host ""
}

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$scanRoots = @(
    (Join-Path $env:USERPROFILE "Downloads"),
    (Join-Path $env:LOCALAPPDATA "Temp"),
    (Join-Path $env:LOCALAPPDATA "pip\Cache"),
    $Root
) | Select-Object -Unique

$rows = @()
foreach ($root in $scanRoots) {
    if (-not (Test-Path $root)) { continue }
    Write-Host "Scanning immediate children of: $root" -ForegroundColor DarkGray
    Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $bytes = Get-FolderSizeBytes -Path $_.FullName
        if ($null -ne $bytes -and $bytes -gt 0) {
            $rows += [pscustomobject]@{ GB = [math]::Round($bytes / 1GB, 2); Path = $_.FullName }
        }
    }
}

Write-Host "`nLargest immediate subfolders (approximate):" -ForegroundColor Cyan
$rows | Sort-Object GB -Descending | Select-Object -First $Top | Format-Table -AutoSize

Write-Host "In-repo reclaim: .\scripts\disk_recovery_hints.ps1" -ForegroundColor DarkGray
Write-Host "After >=40 GB free: .\scripts\run_dissertation_jobs.ps1 -Job download" -ForegroundColor DarkGray
