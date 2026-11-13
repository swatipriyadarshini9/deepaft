# Start long jobs in a NEW PowerShell window (survives Cursor agent timeout).
# Usage:
#   .\scripts\start_detached_jobs.ps1 -Job download
#   .\scripts\start_detached_jobs.ps1 -Job simulation
#   .\scripts\start_detached_jobs.ps1 -Job all

param(
    [ValidateSet("download", "metadata", "simulation", "pipeline", "all")]
    [string]$Job = "all"
)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Runner = Join-Path $Root "scripts\run_dissertation_jobs.ps1"

$cmd = "& '$Runner' -Job $Job"
Start-Process powershell -ArgumentList @("-NoExit", "-Command", "Set-Location '$Root'; $cmd")
Write-Host "Started $Job in new window. Watch progress there."
