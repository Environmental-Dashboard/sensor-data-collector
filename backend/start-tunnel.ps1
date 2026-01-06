# Sensor Data Collector - Cloudflare Quick Tunnel Startup Script
# This script starts the tunnel, captures URL, and updates Vercel automatically

$ErrorActionPreference = "Continue"

# Set working directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Log file for debugging
$logFile = "$scriptDir\tunnel.log"
$tunnelUrlFile = "$scriptDir\tunnel_url.txt"
$tunnelOutput = "$scriptDir\tunnel_output.tmp"
$lockFile = "$scriptDir\tunnel.lock"

function Log {
    param([string]$message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$timestamp] $message" | Out-File -FilePath $logFile -Append
}

Log "=========================================="
Log "Starting tunnel script (PID: $PID)..."

# Always clean up old lock file and cloudflared processes on startup
# This ensures a fresh start after reboot
Remove-Item $lockFile -ErrorAction SilentlyContinue

# Kill ALL existing cloudflared processes
$existingCloudflareds = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
if ($existingCloudflareds) {
    Log "Killing existing cloudflared processes..."
    $existingCloudflareds | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Write our PID to lock file
$PID | Out-File -FilePath $lockFile -Force

# Clear old files
Remove-Item $tunnelOutput -ErrorAction SilentlyContinue

# Wait for backend to be ready (increased timeout)
Log "Waiting for backend to start..."
$backendReady = $false
for ($i = 0; $i -lt 90; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $backendReady = $true
            Log "Backend is ready!"
            break
        }
    } catch {
        if ($i % 10 -eq 0) {
            Log "Waiting for backend... ($($i+1)/90)"
        }
        Start-Sleep -Seconds 1
    }
}

if (-not $backendReady) {
    Log "WARNING: Backend may not be running after 90 seconds!"
    # Continue anyway - the tunnel might still work
}

# Start cloudflared and capture output to extract URL
Log "Starting Cloudflare tunnel..."

# Start cloudflared process with stderr redirected
$pinfo = New-Object System.Diagnostics.ProcessStartInfo
$pinfo.FileName = "cloudflared"
$pinfo.Arguments = "tunnel --url http://localhost:8000"
$pinfo.RedirectStandardError = $true
$pinfo.RedirectStandardOutput = $true
$pinfo.UseShellExecute = $false
$pinfo.CreateNoWindow = $true

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $pinfo
$process.Start() | Out-Null

Log "Cloudflared process started (PID: $($process.Id))"

# Read output asynchronously to find the URL
$tunnelUrl = $null
$startTime = Get-Date

while (((Get-Date) - $startTime).TotalSeconds -lt 90) {
    if ($process.HasExited) {
        Log "ERROR: Cloudflared process exited unexpectedly"
        break
    }
    
    # Try to read stderr (cloudflared outputs to stderr)
    $line = $process.StandardError.ReadLine()
    if ($line) {
        $line | Out-File -FilePath $tunnelOutput -Append
        
        if ($line -match "(https://[a-z0-9-]+\.trycloudflare\.com)") {
            $tunnelUrl = $matches[1]
            Log "Tunnel URL found: $tunnelUrl"
            break
        }
    }
    
    Start-Sleep -Milliseconds 100
}

if ($tunnelUrl) {
    # Save the tunnel URL to a file
    $tunnelUrl | Out-File -FilePath $tunnelUrlFile -Force
    Log "Tunnel URL saved to: $tunnelUrlFile"
    
    # Try to update Vercel environment variable using CLI
    Log "Attempting to update Vercel..."
    
    $frontendDir = "$scriptDir\..\frontend"
    if (Test-Path $frontendDir) {
        try {
            Set-Location $frontendDir
            
            # Remove old env var (ignore errors)
            $removeResult = & npx --yes vercel env rm VITE_API_URL production -y 2>&1
            Log "Remove old env: $removeResult"
            
            # Add new env var
            $tunnelUrl | & npx --yes vercel env add VITE_API_URL production 2>&1 | ForEach-Object { Log $_ }
            
            Log "Environment variable updated. Triggering redeploy..."
            
            # Trigger redeployment and capture the deployment URL
            $deployOutput = & npx --yes vercel --prod -y 2>&1
            $deployOutput | ForEach-Object { Log $_ }
            
            # Extract deployment URL and set alias
            $deployUrl = $deployOutput | Where-Object { $_ -match "https://frontend-[a-z0-9]+-environment-dashboards-projects\.vercel\.app" } | Select-Object -First 1
            if ($deployUrl -match "(https://frontend-[a-z0-9]+-environment-dashboards-projects\.vercel\.app)") {
                $deploymentUrl = $matches[1]
                Log "Setting alias for deployment: $deploymentUrl"
                & npx --yes vercel alias set $deploymentUrl ed-sensor-dashboard.vercel.app 2>&1 | ForEach-Object { Log $_ }
            }
            
            Log "Vercel update complete!"
        } catch {
            Log "Vercel update error: $_"
        }
        
        Set-Location $scriptDir
    }
} else {
    Log "ERROR: Could not capture tunnel URL within 90 seconds"
}

# Keep monitoring the process (don't restart - let the startup script handle that)
Log "Tunnel monitoring started. Will exit if tunnel dies."
while ($true) {
    if ($process.HasExited) {
        Log "Tunnel process exited with code: $($process.ExitCode). Cleaning up..."
        Remove-Item $lockFile -ErrorAction SilentlyContinue
        exit 1
    }
    Start-Sleep -Seconds 30
}
