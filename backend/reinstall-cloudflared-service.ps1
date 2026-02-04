# Reinstall Cloudflared service with named tunnel config
# Run this script as Administrator

$ErrorActionPreference = "Stop"

Write-Host "Reinstalling Cloudflared service..." -ForegroundColor Yellow

# Stop and uninstall the old service
Write-Host "Stopping and uninstalling old service..." -ForegroundColor Yellow
sc.exe stop Cloudflared
Start-Sleep -Seconds 2
cloudflared service uninstall
Start-Sleep -Seconds 2

# Verify it's gone
$service = Get-Service -Name Cloudflared -ErrorAction SilentlyContinue
if ($service) {
    Write-Host "WARNING: Service still exists, forcing removal..." -ForegroundColor Yellow
    sc.exe delete Cloudflared
    Start-Sleep -Seconds 2
}

# Now install the service with the correct config
Write-Host "Installing service with new configuration..." -ForegroundColor Yellow

$configFile = "C:\Users\ethan\sensor_data_collector\backend\cloudflared\config.yml"
$tunnelName = "sensor-backend"

# Install the service
cloudflared service install

# Wait a moment for service to be created
Start-Sleep -Seconds 3

# Now update it to use our config
Write-Host "Updating service to use config file..." -ForegroundColor Yellow

$cloudflaredExe = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$binPath = "`"$cloudflaredExe`" tunnel --config `"$configFile`" run $tunnelName"

# Use WMI Change method
try {
    $service = Get-WmiObject Win32_Service -Filter "Name='Cloudflared'"
    if ($service) {
        $result = $service.Change($null, $null, $null, $null, $null, $null, $binPath, $null, $null, $null, $null)
        if ($result.ReturnValue -eq 0) {
            Write-Host "Service updated successfully!" -ForegroundColor Green
        } else {
            Write-Host "WARNING: Service update returned code: $($result.ReturnValue)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "ERROR: Service not found after install" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "ERROR updating service: $_" -ForegroundColor Red
    exit 1
}

# Start the service
Write-Host "Starting service..." -ForegroundColor Yellow
sc.exe start Cloudflared
Start-Sleep -Seconds 5

# Verify configuration
Write-Host ""
Write-Host "Verifying configuration..." -ForegroundColor Yellow
$config = sc.exe qc Cloudflared
$config | Select-String "BINARY_PATH_NAME"

Write-Host ""
Write-Host "Service status:" -ForegroundColor Yellow
sc.exe query Cloudflared

Write-Host ""
Write-Host "Done! Test the tunnel at:" -ForegroundColor Green
Write-Host "  https://sensor-dashboard.environmentaldashboard.org/health" -ForegroundColor Cyan
