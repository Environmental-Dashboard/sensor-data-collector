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

Log "Starting backend server..."

# Use the venv's python and uvicorn directly
$pythonExe = "$scriptDir\venv\Scripts\python.exe"
$uvicornModule = "uvicorn"

if (-not (Test-Path $pythonExe)) {
    Log "ERROR: Python not found at $pythonExe"
    exit 1
}

Log "Using Python: $pythonExe"
Log "Starting uvicorn on port 8000..."

# Start uvicorn using the venv's python
& $pythonExe -m $uvicornModule app.main:app --host 0.0.0.0 --port 8000 2>&1 | ForEach-Object {
    $_ | Out-File -FilePath $logFile -Append
}
