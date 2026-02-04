# Manual Vercel URL Update Script
# Run this script manually (not as SYSTEM) to update Vercel with the tunnel URL
# This fixes the issue where scheduled tasks can't update Vercel due to npm path issues

$ErrorActionPreference = "Continue"

# Set working directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$tunnelUrlFile = Join-Path $scriptDir "tunnel_url.txt"
$frontendDir = Join-Path $scriptDir "..\frontend"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Vercel URL Update Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if tunnel URL file exists
if (-not (Test-Path $tunnelUrlFile)) {
    Write-Host "ERROR: Tunnel URL file not found!" -ForegroundColor Red
    Write-Host "Expected: $tunnelUrlFile" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Make sure the tunnel is running first." -ForegroundColor Yellow
    exit 1
}

# Read tunnel URL
$tunnelUrl = Get-Content $tunnelUrlFile -ErrorAction SilentlyContinue | Where-Object { $_ -match "https://" } | Select-Object -First 1

if (-not $tunnelUrl) {
    Write-Host "ERROR: Could not read tunnel URL from file!" -ForegroundColor Red
    Write-Host "File contents:" -ForegroundColor Yellow
    Get-Content $tunnelUrlFile
    exit 1
}

# Clean up URL (remove any whitespace or newlines)
$tunnelUrl = $tunnelUrl.Trim()

Write-Host "Tunnel URL: $tunnelUrl" -ForegroundColor Green
Write-Host ""

# Verify tunnel is accessible
Write-Host "Verifying tunnel is accessible..." -ForegroundColor Yellow
try {
    $healthCheck = Invoke-WebRequest -Uri "$tunnelUrl/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    if ($healthCheck.StatusCode -eq 200) {
        Write-Host "[OK] Tunnel is accessible!" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Tunnel returned status $($healthCheck.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERROR] Tunnel is not accessible!" -ForegroundColor Red
    Write-Host "  $_" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please check:" -ForegroundColor Yellow
    Write-Host "  1. Is the tunnel running?" -ForegroundColor White
    Write-Host "  2. Is the backend running on port 8000?" -ForegroundColor White
    exit 1
}

Write-Host ""

# Check if frontend directory exists
if (-not (Test-Path $frontendDir)) {
    Write-Host "ERROR: Frontend directory not found!" -ForegroundColor Red
    Write-Host "Expected: $frontendDir" -ForegroundColor Yellow
    exit 1
}

# Check if Vercel is linked
Set-Location $frontendDir
$vercelLinked = Test-Path ".vercel\project.json"

if (-not $vercelLinked) {
    Write-Host "⚠ WARNING: Vercel project not linked!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To link the project:" -ForegroundColor White
    Write-Host "  1. cd frontend" -ForegroundColor Cyan
    Write-Host "  2. npx vercel link" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Or manually set the environment variable in Vercel dashboard:" -ForegroundColor White
    Write-Host "  1. Go to https://vercel.com/dashboard" -ForegroundColor Cyan
    Write-Host "  2. Select your project" -ForegroundColor Cyan
    Write-Host "  3. Settings -> Environment Variables" -ForegroundColor Cyan
    Write-Host "  4. Add/Update: VITE_API_URL = $tunnelUrl" -ForegroundColor Cyan
    Write-Host "  5. Redeploy" -ForegroundColor Cyan
    exit 1
}

Write-Host "Vercel project is linked. Updating environment variable..." -ForegroundColor Yellow
Write-Host ""

# Remove old env var
Write-Host "Removing old VITE_API_URL..." -ForegroundColor Yellow
try {
    $removeResult = & npx --yes vercel env rm VITE_API_URL production -y 2>&1
    Write-Host "  $removeResult" -ForegroundColor Gray
} catch {
    Write-Host "  Note: Old env var may not exist (this is OK)" -ForegroundColor Gray
}

# Add new env var
Write-Host ""
Write-Host "Adding new VITE_API_URL: $tunnelUrl" -ForegroundColor Yellow
$addResult = $tunnelUrl | & npx --yes vercel env add VITE_API_URL production 2>&1

if ($LASTEXITCODE -eq 0 -or $addResult -match "success|added|updated|What") {
    Write-Host "[OK] Environment variable updated!" -ForegroundColor Green
    Write-Host ""
    
    # Trigger redeployment
    Write-Host "Triggering Vercel redeployment..." -ForegroundColor Yellow
    $deployOutput = & npx --yes vercel --prod -y 2>&1
    
    # Check for deployment URL
    $deployUrl = $deployOutput | Where-Object { $_ -match "https://[a-z0-9-]+\.vercel\.app" } | Select-Object -First 1
    if ($deployUrl -and $deployUrl -match "(https://[a-z0-9-]+\.vercel\.app)") {
        $deploymentUrl = $matches[1]
        Write-Host "✓ Deployment URL: $deploymentUrl" -ForegroundColor Green
        Write-Host ""
        Write-Host "Setting alias..." -ForegroundColor Yellow
        $aliasResult = & npx --yes vercel alias set $deploymentUrl ed-sensor-dashboard.vercel.app 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Alias set successfully!" -ForegroundColor Green
        }
    }
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✓ SUCCESS!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Frontend will be updated with new backend URL:" -ForegroundColor White
    Write-Host "  $tunnelUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Dashboard: https://ed-sensor-dashboard.vercel.app" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Note: It may take 1-2 minutes for the deployment to complete." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "[ERROR] Failed to update environment variable" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please update manually:" -ForegroundColor Yellow
    Write-Host "  1. Go to https://vercel.com/dashboard" -ForegroundColor White
    Write-Host "  2. Select your project" -ForegroundColor White
    Write-Host "  3. Settings -> Environment Variables" -ForegroundColor White
    Write-Host "  4. Add/Update: VITE_API_URL = $tunnelUrl" -ForegroundColor White
    Write-Host "  5. Redeploy"
}

Set-Location $scriptDir
