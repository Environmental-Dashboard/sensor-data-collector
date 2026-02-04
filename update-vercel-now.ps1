# Quick script to update Vercel with current tunnel URL
# Run this from the project root

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Updating Vercel with Tunnel URL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get tunnel URL
$tunnelUrlFile = "backend\tunnel_url.txt"
if (-not (Test-Path $tunnelUrlFile)) {
    Write-Host "ERROR: Tunnel URL file not found!" -ForegroundColor Red
    Write-Host "Expected: $tunnelUrlFile" -ForegroundColor Yellow
    exit 1
}

$tunnelUrl = (Get-Content $tunnelUrlFile -Raw) -replace '[^\x20-\x7E]','' -replace '\s',''
if (-not $tunnelUrl -or -not $tunnelUrl.StartsWith("https://")) {
    Write-Host "ERROR: Invalid tunnel URL in file!" -ForegroundColor Red
    exit 1
}

Write-Host "Tunnel URL: $tunnelUrl" -ForegroundColor Green
Write-Host ""

# Verify tunnel is accessible
Write-Host "Verifying tunnel..." -ForegroundColor Yellow
try {
    $health = Invoke-WebRequest -Uri "$tunnelUrl/health" -UseBasicParsing -TimeoutSec 5
    if ($health.StatusCode -eq 200) {
        Write-Host "[OK] Tunnel is accessible!" -ForegroundColor Green
    }
} catch {
    Write-Host "[WARNING] Tunnel health check failed: $_" -ForegroundColor Yellow
    Write-Host "Continuing anyway..." -ForegroundColor Yellow
}

Write-Host ""

# Update Vercel
Write-Host "Updating Vercel environment variable..." -ForegroundColor Yellow
Set-Location frontend

try {
    # Remove old
    Write-Host "Removing old VITE_API_URL..." -ForegroundColor Gray
    & npx --yes vercel env rm VITE_API_URL production -y 2>&1 | Out-Null
    
    # Add new
    Write-Host "Adding new VITE_API_URL: $tunnelUrl" -ForegroundColor Gray
    $tunnelUrl | & npx --yes vercel env add VITE_API_URL production 2>&1 | Out-Null
    
    Write-Host ""
    Write-Host "[OK] Environment variable updated!" -ForegroundColor Green
    Write-Host ""
    
    # Redeploy
    Write-Host "Triggering Vercel redeployment..." -ForegroundColor Yellow
    $deploy = & npx --yes vercel --prod -y 2>&1
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "[SUCCESS]" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Frontend will be updated with:" -ForegroundColor White
    Write-Host "  $tunnelUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Dashboard: https://ed-sensor-dashboard.vercel.app" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Note: Deployment takes 1-2 minutes" -ForegroundColor Yellow
    
} catch {
    Write-Host ""
    Write-Host "[ERROR] Failed to update Vercel: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual update required:" -ForegroundColor Yellow
    Write-Host "  1. Go to https://vercel.com/dashboard" -ForegroundColor White
    Write-Host "  2. Settings -> Environment Variables" -ForegroundColor White
    Write-Host "  3. Set VITE_API_URL = $tunnelUrl" -ForegroundColor White
    Write-Host "  4. Redeploy" -ForegroundColor White
}

Set-Location ..
