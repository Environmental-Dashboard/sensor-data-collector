# Sensor Data Collector - Cloudflare Quick Tunnel Startup Script
# This script starts the Cloudflare Tunnel and captures the URL

$ErrorActionPreference = "SilentlyContinue"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Starting Cloudflare Quick Tunnel..." -ForegroundColor Cyan  
Write-Host "============================================" -ForegroundColor Cyan

# Wait for backend to start first
Write-Host "Waiting for backend to start..."
Start-Sleep -Seconds 5

# Test if backend is running
$backendReady = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $backendReady = $true
            Write-Host "Backend is ready!" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "Waiting for backend... ($($i+1)/10)"
        Start-Sleep -Seconds 2
    }
}

if (-not $backendReady) {
    Write-Host "WARNING: Backend may not be running!" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Starting Cloudflare Tunnel..." -ForegroundColor Green
Write-Host "The tunnel URL will be displayed below." -ForegroundColor Yellow
Write-Host "Copy it and update your Vercel VITE_API_URL if needed." -ForegroundColor Yellow
Write-Host ""

# Start the tunnel
cloudflared tunnel --url http://localhost:8000
