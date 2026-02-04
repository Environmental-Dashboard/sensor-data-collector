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

# Start cloudflared using named tunnel with config file
Log "Starting Cloudflare named tunnel..."

# Config file path
$configFile = Join-Path $scriptDir "cloudflared\config.yml"
$tunnelName = "sensor-backend"

# Verify config file exists
if (-not (Test-Path $configFile)) {
    Log "ERROR: Config file not found at: $configFile"
    Log "Please ensure cloudflared\config.yml exists with your tunnel configuration"
    exit 1
}

# Start cloudflared process with config file
$pinfo = New-Object System.Diagnostics.ProcessStartInfo
$pinfo.FileName = "cloudflared"
$pinfo.Arguments = "tunnel --config `"$configFile`" run $tunnelName"
$pinfo.RedirectStandardError = $true
$pinfo.RedirectStandardOutput = $true
$pinfo.UseShellExecute = $false
$pinfo.CreateNoWindow = $true

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $pinfo
$process.Start() | Out-Null

Log "Cloudflared process started (PID: $($process.Id))"
Log "Using named tunnel: $tunnelName"
Log "Config file: $configFile"

# For named tunnel, the URL is stable: sensor-dashboard.environmentaldashboard.org
# No need to extract URL from output - it's already configured in DNS
$tunnelUrl = "https://sensor-dashboard.environmentaldashboard.org"
Log "Tunnel URL (stable): $tunnelUrl"

# Wait a moment for tunnel to connect
Start-Sleep -Seconds 5

# Save the stable tunnel URL to a file
$tunnelUrl | Out-File -FilePath $tunnelUrlFile -Force
Log "Tunnel URL saved to: $tunnelUrlFile"
    
    # Verify tunnel is accessible
    Log "Verifying tunnel is accessible..."
    $tunnelVerified = $false
    for ($i = 0; $i -lt 10; $i++) {
        try {
            $healthCheck = Invoke-WebRequest -Uri "$tunnelUrl/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
            if ($healthCheck.StatusCode -eq 200) {
                $tunnelVerified = $true
                Log "Tunnel verified! Backend is accessible at $tunnelUrl"
                break
            }
        } catch {
            if ($i -eq 0) {
                Log "Waiting for tunnel to be ready... (attempt $($i+1)/10)"
            }
            Start-Sleep -Seconds 2
        }
    }
    
    if (-not $tunnelVerified) {
        Log "WARNING: Tunnel health check failed. Tunnel may still be initializing."
        Log "This is normal - named tunnels can take 30-60 seconds to fully connect."
    }
    
    # Try to update Vercel environment variable using CLI
    # Note: This may fail when running as SYSTEM user due to npm path issues
    # If it fails, run update-vercel-url.ps1 manually
    Log "Attempting to update Vercel environment variable..."
    
    $frontendDir = "$scriptDir\..\frontend"
    if (Test-Path $frontendDir) {
        try {
            Set-Location $frontendDir
            
            # Check if Vercel is linked (required for env updates)
            $vercelLinked = Test-Path ".vercel\project.json"
            if (-not $vercelLinked) {
                Log "WARNING: Vercel project not linked. Skipping automatic Vercel update."
                Log "Please run: cd frontend && npx vercel link"
                Log "Then run: backend\update-vercel-url.ps1"
                Log "Or manually set VITE_API_URL in Vercel dashboard: $tunnelUrl"
                Set-Location $scriptDir
            } else {
                Log "Vercel project is linked. Updating environment variable..."
                
                # Try to find npm/node in common locations (for SYSTEM user)
                $npmPath = $null
                $nodePaths = @(
                    "$env:ProgramFiles\nodejs\npm.cmd",
                    "$env:ProgramFiles (x86)\nodejs\npm.cmd",
                    "$env:USERPROFILE\AppData\Roaming\npm\npm.cmd",
                    "npm"  # Fallback to PATH
                )
                
                foreach ($path in $nodePaths) {
                    if (Get-Command $path -ErrorAction SilentlyContinue) {
                        $npmPath = $path
                        break
                    }
                }
                
                if (-not $npmPath) {
                    Log "WARNING: npm not found. Cannot update Vercel automatically."
                    Log "This is common when running as SYSTEM user."
                    Log "Please run update-vercel-url.ps1 manually (not as SYSTEM):"
                    Log "  cd backend"
                    Log "  .\update-vercel-url.ps1"
                    Log "Or manually set VITE_API_URL in Vercel dashboard: $tunnelUrl"
                    Set-Location $scriptDir
                } else {
                    # Remove old env var (ignore errors if it doesn't exist)
                    try {
                        $removeResult = & $npmPath --yes vercel env rm VITE_API_URL production -y 2>&1
                        Log "Remove old env result: $removeResult"
                    } catch {
                        Log "Note: Old env var may not exist (this is OK)"
                    }
                    
                    # Add new env var
                    Log "Adding new VITE_API_URL: $tunnelUrl"
                    $addResult = $tunnelUrl | & $npmPath --yes vercel env add VITE_API_URL production 2>&1
                    $addResult | ForEach-Object { Log "  $_" }
                    
                    if ($LASTEXITCODE -eq 0 -or $addResult -match "success|added|updated|What") {
                        Log "Environment variable updated successfully!"
                        
                        Log "Triggering Vercel redeployment..."
                        # Trigger redeployment
                        $deployOutput = & $npmPath --yes vercel --prod -y 2>&1
                        $deployOutput | ForEach-Object { Log "  $_" }
                        
                        # Extract deployment URL and set alias
                        $deployUrl = $deployOutput | Where-Object { $_ -match "https://[a-z0-9-]+\.vercel\.app" } | Select-Object -First 1
                        if ($deployUrl -and $deployUrl -match "(https://[a-z0-9-]+\.vercel\.app)") {
                            $deploymentUrl = $matches[1]
                            Log "Deployment URL: $deploymentUrl"
                            Log "Setting alias to ed-sensor-dashboard.vercel.app..."
                            $aliasResult = & $npmPath --yes vercel alias set $deploymentUrl ed-sensor-dashboard.vercel.app 2>&1
                            $aliasResult | ForEach-Object { Log "  $_" }
                        }
                        
                        Log "Vercel update complete! Frontend should be connected to backend at: $tunnelUrl"
                    } else {
                        Log "WARNING: Vercel env update may have failed. Check logs above."
                        Log "This is common when running as SYSTEM user."
                        Log "Please run update-vercel-url.ps1 manually (not as SYSTEM):"
                        Log "  cd backend"
                        Log "  .\update-vercel-url.ps1"
                        Log "Or manually set VITE_API_URL in Vercel dashboard: $tunnelUrl"
                    }
                    
                    Set-Location $scriptDir
                }
            }
        } catch {
            Log "ERROR: Vercel update failed: $_"
            Log "This is common when running as SYSTEM user (scheduled task)."
            Log ""
            Log "SOLUTION: Run update-vercel-url.ps1 manually (not as SYSTEM):"
            Log "  1. Open PowerShell as your user (not SYSTEM)"
            Log "  2. cd c:\Users\ethan\sensor_data_collector\backend"
            Log "  3. .\update-vercel-url.ps1"
            Log ""
            Log "Or manually set VITE_API_URL in Vercel dashboard:"
            Log "  Dashboard: https://vercel.com/dashboard"
            Log "  Variable: VITE_API_URL = $tunnelUrl"
            Set-Location $scriptDir
        }
    } else {
        Log "WARNING: Frontend directory not found at: $frontendDir"
        Log "Cannot update Vercel automatically. Manual step required:"
        Log "Set VITE_API_URL in Vercel dashboard to: $tunnelUrl"
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
