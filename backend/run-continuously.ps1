# Sensor Data Collector - Continuous Runner
# This script runs backend and tunnel continuously
# Designed to be run by Windows Scheduled Task

$ErrorActionPreference = "Continue"

# Set working directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Log file
$logFile = "$scriptDir\continuous.log"

function Log {
    param([string]$message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$timestamp] $message" | Out-File -FilePath $logFile -Append
    Write-Host "[$timestamp] $message"
}

Log "=========================================="
Log "Starting Sensor Data Collector (Continuous Mode)"
Log "PID: $PID"

# Check if venv exists
$pythonExe = Join-Path $scriptDir "venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Log "ERROR: Python virtual environment not found at $pythonExe"
    Log "Please run: python -m venv venv"
    exit 1
}

# Start backend
Log "Starting backend server..."
$backendScript = Join-Path $scriptDir "start-backend.ps1"

# Kill any existing backend processes first
$existingProcesses = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($existingProcesses) {
    Log "Killing existing processes on port 8000..."
    foreach ($procId in $existingProcesses) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

# Start backend in a new process
$backendProcess = Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File `"$backendScript`"" -WindowStyle Hidden -PassThru
Log "Backend process started (PID: $($backendProcess.Id))"

# Wait for backend to be ready (increased timeout to 120 seconds)
Log "Waiting for backend to start..."
$backendReady = $false
for ($i = 0; $i -lt 120; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $backendReady = $true
            Log "Backend is ready!"
            break
        }
    } catch {
        if ($i % 10 -eq 0 -and $i -gt 0) {
            Log "Still waiting for backend... ($i/120 seconds)"
            # Check if backend process is still running
            if (-not (Get-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue)) {
                Log "ERROR: Backend process died! Check backend.log for errors"
                # Try to read last few lines of backend.log
                if (Test-Path "$scriptDir\backend.log") {
                    $lastErrors = Get-Content "$scriptDir\backend.log" -Tail 10
                    Log "Last backend.log entries:"
                    $lastErrors | ForEach-Object { Log "  $_" }
                }
            }
        }
        Start-Sleep -Seconds 1
    }
}

if (-not $backendReady) {
    Log "ERROR: Backend failed to start after 120 seconds!"
    Log "Check backend.log for detailed error messages"
    if (Test-Path "$scriptDir\backend.log") {
        $lastErrors = Get-Content "$scriptDir\backend.log" -Tail 20
        Log "Last backend.log entries:"
        $lastErrors | ForEach-Object { Log "  $_" }
    }
    Log "Will continue monitoring and retry..."
}

# Start tunnel
Log "Starting Cloudflare tunnel..."
$tunnelScript = Join-Path $scriptDir "start-tunnel.ps1"
Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File `"$tunnelScript`"" -WindowStyle Hidden

Log "Both backend and tunnel started. Monitoring..."

# Track backend process
$backendProcessId = $null
$lastBackendCheck = Get-Date
$consecutiveFailures = 0

# Monitor processes and restart if needed
while ($true) {
    Start-Sleep -Seconds 30
    
    # Check backend
    $backendRunning = $false
    $healthCheckSuccess = $false
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $backendRunning = $true
            $healthCheckSuccess = $true
            $consecutiveFailures = 0
        }
    } catch {
        $backendRunning = $false
        $consecutiveFailures++
    }
    
    # Check if there's a process on port 8000 (backend might be starting)
    $portProcesses = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    $hasPortProcess = $portProcesses -ne $null
    
    # Only restart if:
    # 1. Health check failed AND
    # 2. No process on port 8000 OR
    # 3. Multiple consecutive failures (backend might be stuck)
    if (-not $healthCheckSuccess) {
        if (-not $hasPortProcess) {
            # No process on port - definitely need to restart
            Log "WARNING: Backend not responding and no process on port 8000, restarting..."
            
            # Check backend.log for errors
            if (Test-Path "$scriptDir\backend.log") {
                $recentErrors = Get-Content "$scriptDir\backend.log" -Tail 10 | Where-Object { $_ -match "ERROR|Traceback|Exception|Failed" }
                if ($recentErrors) {
                    Log "Recent errors in backend.log:"
                    $recentErrors | ForEach-Object { Log "  $_" }
                }
            }
            
            # Restart backend
            $backendProcess = Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File `"$backendScript`"" -WindowStyle Hidden -PassThru
            Log "Backend restart initiated (PID: $($backendProcess.Id))"
            $backendProcessId = $backendProcess.Id
            $consecutiveFailures = 0
            Start-Sleep -Seconds 15  # Give it time to start
        } elseif ($consecutiveFailures -ge 3) {
            # Process exists but health check failing repeatedly - might be stuck
            Log "WARNING: Backend process exists but health check failing ($consecutiveFailures times), restarting..."
            
            # Kill process on port 8000
            foreach ($procId in $portProcesses) {
                try {
                    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                    Log "Killed stuck process $procId on port 8000"
                } catch {
                    # Ignore errors
                }
            }
            
            Start-Sleep -Seconds 3
            
            # Restart
            $backendProcess = Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File `"$backendScript`"" -WindowStyle Hidden -PassThru
            Log "Backend restart initiated (PID: $($backendProcess.Id))"
            $backendProcessId = $backendProcess.Id
            $consecutiveFailures = 0
            Start-Sleep -Seconds 15
        } else {
            # Process exists but not responding yet - might still be starting
            if ($consecutiveFailures -eq 1) {
                Log "Backend process exists but not responding yet (may still be starting)..."
            }
        }
    } else {
        # Backend is healthy
        if ($consecutiveFailures -gt 0) {
            Log "Backend recovered! Health check successful."
        }
    }
    
    # Check tunnel
    $tunnelRunning = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
    if (-not $tunnelRunning) {
        Log "WARNING: Tunnel not running, restarting..."
        Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File `"$tunnelScript`"" -WindowStyle Hidden
    }
}
