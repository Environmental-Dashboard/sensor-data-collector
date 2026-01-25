# Sensor Data Collector - Backend Startup Script
# This script starts the FastAPI backend server (runs hidden)

$ErrorActionPreference = "Continue"

# Set working directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Log file for debugging
$logFile = "$scriptDir\backend.log"

function Log {
    param([string]$message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$timestamp] $message" | Out-File -FilePath $logFile -Append
}

Log "=========================================="
Log "Starting backend server..."

# Kill any existing uvicorn/python processes on port 8000
Log "Checking for existing processes on port 8000..."
$existingProcesses = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($existingProcesses) {
    foreach ($procId in $existingProcesses) {
        Log "Killing existing process on port 8000 (PID: $procId)"
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    # Wait for port to be released
    Start-Sleep -Seconds 2
}

# Also kill any orphaned python processes running uvicorn
$uvicornProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn*app.main*" -or $_.MainWindowTitle -like "*uvicorn*"
}
if ($uvicornProcesses) {
    Log "Killing orphaned uvicorn processes..."
    $uvicornProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

# Use the venv's python and uvicorn directly
$pythonExe = "$scriptDir\venv\Scripts\python.exe"
$uvicornModule = "uvicorn"

if (-not (Test-Path $pythonExe)) {
    Log "ERROR: Python not found at $pythonExe"
    exit 1
}

Log "Using Python: $pythonExe"
Log "Starting uvicorn on port 8000..."

# Start uvicorn using the venv's python (with --reload for auto-refresh on code changes)
# Use Start-Process with file redirection to capture output
$outputFile = "$scriptDir\uvicorn_output.log"
$errorFile = "$scriptDir\uvicorn_error.log"

# Start the process in the background
$process = Start-Process -FilePath $pythonExe `
    -ArgumentList "-m", $uvicornModule, "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" `
    -WorkingDirectory $scriptDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $outputFile `
    -RedirectStandardError $errorFile `
    -PassThru `
    -NoNewWindow

if ($process) {
    Log "Uvicorn process started (PID: $($process.Id))"
    
    # Monitor the process and log output
    $maxWait = 30  # Wait up to 30 seconds for startup
    $waited = 0
    $started = $false
    
    while ($waited -lt $maxWait -and -not $started) {
        Start-Sleep -Seconds 1
        $waited++
        
        # Check if process is still running
        if (-not (Get-Process -Id $process.Id -ErrorAction SilentlyContinue)) {
            Log "ERROR: Uvicorn process died immediately. Check $errorFile for errors."
            if (Test-Path $errorFile) {
                $errors = Get-Content $errorFile -Tail 10
                $errors | ForEach-Object { Log "  $_" }
            }
            exit 1
        }
        
        # Check if port 8000 is listening
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                $started = $true
                Log "Backend is ready and responding!"
                break
            }
        } catch {
            # Not ready yet, continue waiting
        }
        
        # Log output periodically
        if ($waited % 5 -eq 0 -and (Test-Path $outputFile)) {
            $recentOutput = Get-Content $outputFile -Tail 3 -ErrorAction SilentlyContinue
            if ($recentOutput) {
                $recentOutput | ForEach-Object { Log "  $_" }
            }
        }
    }
    
    if (-not $started) {
        Log "WARNING: Backend may not be fully started, but process is running (PID: $($process.Id))"
        if (Test-Path $errorFile) {
            $errors = Get-Content $errorFile -Tail 5 -ErrorAction SilentlyContinue
            if ($errors) {
                Log "Recent errors:"
                $errors | ForEach-Object { Log "  $_" }
            }
        }
    }
    
    # Keep the script running and monitor the process
    while ($true) {
        Start-Sleep -Seconds 10
        
        if (-not (Get-Process -Id $process.Id -ErrorAction SilentlyContinue)) {
            $exitCode = $process.ExitCode
            Log "Uvicorn process exited (Exit Code: $exitCode)"
            
            if (Test-Path $errorFile) {
                $errors = Get-Content $errorFile -Tail 20
                Log "Last errors:"
                $errors | ForEach-Object { Log "  $_" }
            }
            exit $exitCode
        }
        
        # Periodically append output to main log
        if (Test-Path $outputFile) {
            $newOutput = Get-Content $outputFile -Tail 5 -ErrorAction SilentlyContinue
            if ($newOutput) {
                $newOutput | ForEach-Object {
                    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
                    "[$timestamp] $_" | Out-File -FilePath $logFile -Append
                }
            }
        }
    }
} else {
    Log "ERROR: Failed to start uvicorn process"
    exit 1
}
