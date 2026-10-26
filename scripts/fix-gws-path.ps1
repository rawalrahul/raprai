Write-Host ""
Write-Host "=== GWS PATH Fix Script v2 ===" -ForegroundColor Cyan

# Step 1: Remove incorrect "C" entry
Write-Host ""
Write-Host "[1/3] Cleaning up incorrect PATH entry..." -ForegroundColor Yellow
$currentUserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathEntries = $currentUserPath -split ";" | Where-Object { $_ -ne "C" -and $_ -ne "" }
$cleanedPath = ($pathEntries -join ";")
[Environment]::SetEnvironmentVariable("Path", $cleanedPath, "User")
Write-Host "  Removed incorrect C entry from user PATH." -ForegroundColor Green

# Step 2: Add correct npm directory
Write-Host ""
Write-Host "[2/3] Adding correct npm path..." -ForegroundColor Yellow
$npmDir = Join-Path $env:APPDATA "npm"

if (Test-Path (Join-Path $npmDir "gws.cmd")) {
    Write-Host "  Confirmed gws.cmd exists at: $npmDir" -ForegroundColor Green
} else {
    Write-Host "  gws.cmd not found at $npmDir" -ForegroundColor Red
    exit 1
}

$alreadyInPath = $pathEntries | Where-Object { $_ -eq $npmDir }
if ($alreadyInPath) {
    Write-Host "  $npmDir is already in user PATH." -ForegroundColor Green
} else {
    $newPath = $cleanedPath + ";" + $npmDir
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "  Added $npmDir to user PATH." -ForegroundColor Green
}

$env:Path = $env:Path + ";" + $npmDir

# Step 3: Verify
Write-Host ""
Write-Host "[3/3] Verifying..." -ForegroundColor Yellow
$verify = Get-Command gws -ErrorAction SilentlyContinue
if ($verify) {
    Write-Host "  gws is now accessible!" -ForegroundColor Green
} else {
    Write-Host "  PATH updated. Close and reopen your terminal." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "=== Done! Restart your terminal and helm. ===" -ForegroundColor Cyan
