# Update Cloudflared Windows Service to use named tunnel
# Run this script as Administrator

$ErrorActionPreference = "Stop"

Write-Host "Updating Cloudflared service configuration..." -ForegroundColor Yellow

# Stop the service first
Write-Host "Stopping Cloudflared service..." -ForegroundColor Yellow
sc.exe stop Cloudflared
Start-Sleep -Seconds 2

# Build the new command path
$cloudflaredExe = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$configFile = "C:\Users\ethan\sensor_data_collector\backend\cloudflared\config.yml"
$tunnelName = "sensor-backend"

# Construct the full command - sc.exe needs the path in a specific format
# Escape quotes properly for sc.exe
$binPath = "`"$cloudflaredExe`" tunnel --config `"$configFile`" run $tunnelName"

Write-Host "Setting service binPath to:" -ForegroundColor Yellow
Write-Host "  $binPath" -ForegroundColor Cyan

# Update the service - sc.exe needs binPath= followed by the quoted path
# Use & to execute sc.exe with proper argument handling
$result = & sc.exe config Cloudflared binPath= $binPath 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to update service configuration" -ForegroundColor Red
    Write-Host $result
    Write-Host ""
    Write-Host "Trying alternative method..." -ForegroundColor Yellow
    
    # Alternative: Use WMI to update the service
    try {
        $service = Get-WmiObject Win32_Service -Filter "Name='Cloudflared'"
        $service.Change($null, $null, $null, $null, $null, $null, $binPath, $null, $null, $null, $null)
        Write-Host "Service updated via WMI!" -ForegroundColor Green
    } catch {
        Write-Host "WMI method also failed: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Service configuration updated successfully!" -ForegroundColor Green

# Start the service
Write-Host "Starting Cloudflared service..." -ForegroundColor Yellow
sc.exe start Cloudflared
Start-Sleep -Seconds 3

# Verify it's running
$status = sc.exe query Cloudflared
Write-Host ""
Write-Host "Service status:" -ForegroundColor Yellow
$status

# Check the new configuration
Write-Host ""
Write-Host "Verifying new configuration..." -ForegroundColor Yellow
$config = sc.exe qc Cloudflared
$config | Select-String "BINARY_PATH_NAME"

Write-Host ""
Write-Host "Done! Test the tunnel at:" -ForegroundColor Green
Write-Host "  https://sensor-dashboard.environmentaldashboard.org/health" -ForegroundColor Cyan
