# Sensor Data Collector - Backend Startup Script
# This script starts the FastAPI backend server

$ErrorActionPreference = "Stop"

# Set working directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Activate virtual environment and start server
Write-Host "Starting Sensor Data Collector Backend..." -ForegroundColor Green
& "$scriptDir\venv\Scripts\Activate.ps1"
uvicorn app.main:app --host 0.0.0.0 --port 8000
