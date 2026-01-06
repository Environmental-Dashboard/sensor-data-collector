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
    foreach ($pid in $existingProcesses) {
        Log "Killing existing process on port 8000 (PID: $pid)"
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
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
& $pythonExe -m $uvicornModule app.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | ForEach-Object {
    $_ | Out-File -FilePath $logFile -Append
}
