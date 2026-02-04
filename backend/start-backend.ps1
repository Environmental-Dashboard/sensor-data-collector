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
$maxPortWait = 10  # Maximum wait time for port to be released
$portWaitCount = 0

# First, kill all Python processes that might be running uvicorn
$allPythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
if ($allPythonProcesses) {
    Log "Found $($allPythonProcesses.Count) Python process(es), checking for uvicorn..."
    foreach ($proc in $allPythonProcesses) {
        try {
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($proc.Id)" -ErrorAction SilentlyContinue).CommandLine
            if ($cmdLine -and ($cmdLine -like "*uvicorn*" -or $cmdLine -like "*app.main*")) {
                Log "Killing uvicorn process (PID: $($proc.Id))"
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            }
        } catch {
            # Ignore errors getting command line
        }
    }
    Start-Sleep -Seconds 2
}

# Kill processes using port 8000
# Get all connections on port 8000, including those in TIME_WAIT
$allConnections = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
$existingProcesses = $allConnections | Where-Object { $_.State -ne 'TimeWait' } | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -gt 0 }

if ($existingProcesses) {
    Log "Found $($existingProcesses.Count) active process(es) on port 8000: $($existingProcesses -join ', ')"
    foreach ($procId in $existingProcesses) {
        # Skip invalid PIDs (0 is System Idle Process, negative PIDs are invalid)
        if ($procId -le 0) {
            Log "Skipping invalid PID: $procId"
            continue
        }
        
        # Check if process actually exists
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) {
            Log "Killing process on port 8000 (PID: $procId, Name: $($proc.ProcessName))"
            try {
                Stop-Process -Id $procId -Force -ErrorAction Stop
                Start-Sleep -Milliseconds 500
            } catch {
                Log "Warning: Could not kill process $procId : $_"
            }
        } else {
            Log "Process $procId no longer exists (may have exited)"
        }
    }
    
    # Wait for port to be released and verify it's free
    while ($portWaitCount -lt $maxPortWait) {
        Start-Sleep -Seconds 1
        $portWaitCount++
        
        # Check for active connections (not TIME_WAIT)
        $activeConnections = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Where-Object { $_.State -ne 'TimeWait' -and $_.OwningProcess -gt 0 }
        if (-not $activeConnections) {
            Log "Port 8000 is now free (waited $portWaitCount seconds)"
            break
        }
        
        # Log remaining connections
        if ($portWaitCount % 3 -eq 0) {
            $remainingPids = $activeConnections | Select-Object -ExpandProperty OwningProcess -Unique
            Log "Port 8000 still has active connections from PID(s): $($remainingPids -join ', ')"
        }
        
        if ($portWaitCount -eq $maxPortWait) {
            Log "WARNING: Port 8000 may still be in use after $maxPortWait seconds"
        }
    }
} else {
    Log "Port 8000 is free (no active connections)"
}

# Final verification - check for active connections only (ignore TIME_WAIT)
$finalCheck = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Where-Object { $_.State -ne 'TimeWait' -and $_.OwningProcess -gt 0 }
if ($finalCheck) {
    $blockingPids = $finalCheck | Select-Object -ExpandProperty OwningProcess -Unique
    Log "WARNING: Port 8000 still has active connections from process(es): $($blockingPids -join ', ')"
    Log "Attempting aggressive cleanup..."
    
    # Try killing again with more force
    foreach ($procId in $blockingPids) {
        if ($procId -le 0) { continue }
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) {
            Log "Force killing process $procId ($($proc.ProcessName))"
            try {
                Stop-Process -Id $procId -Force -ErrorAction Stop
            } catch {
                # Try taskkill as last resort
                Log "Using taskkill for process $procId"
                Start-Process -FilePath "taskkill" -ArgumentList "/F", "/PID", $procId -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue
            }
        }
    }
    
    Start-Sleep -Seconds 3
    
    # Final check - if still blocked, check if it's just TIME_WAIT (which is harmless)
    $finalCheck2 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Where-Object { $_.State -ne 'TimeWait' -and $_.OwningProcess -gt 0 }
    if ($finalCheck2) {
        $stillBlocking = $finalCheck2 | Select-Object -ExpandProperty OwningProcess -Unique
        $existingProcs = @()
        foreach ($procId in $stillBlocking) {
            $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
            if ($proc) {
                $existingProcs += $procId
            }
        }
        
        if ($existingProcs.Count -gt 0) {
            Log "WARNING: Port 8000 is still blocked by running process(es): $($existingProcs -join ', ')"
            Log "These processes may need to be manually stopped, but proceeding anyway..."
        } else {
            Log "Port 8000 connections are from dead processes - will clear automatically"
        }
        # Don't exit - let uvicorn try to bind anyway, it might work
        Log "Proceeding - uvicorn will attempt to bind to port 8000..."
    } else {
        Log "Port 8000 is now free (only TIME_WAIT connections remain, which are harmless)"
    }
} else {
    Log "Port 8000 verified free"
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

# Start the process in the background using ProcessStartInfo for better control
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $pythonExe
# Use --reload only if RELOAD_MODE env var is set (for development)
# In production/continuous mode, don't use --reload as it can cause issues
$reloadFlag = if ($env:RELOAD_MODE -eq "true") { "--reload" } else { "" }
$psi.Arguments = "-m $uvicornModule app.main:app --host 0.0.0.0 --port 8000 $reloadFlag".Trim()
$psi.WorkingDirectory = $scriptDir
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true
$psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $psi

# Set up output handlers
$outputBuilder = New-Object System.Text.StringBuilder
$errorBuilder = New-Object System.Text.StringBuilder

$outputHandler = {
    if (-not [string]::IsNullOrEmpty($EventArgs.Data)) {
        $outputBuilder.AppendLine($EventArgs.Data) | Out-Null
        $EventArgs.Data | Out-File -FilePath $outputFile -Append -Encoding utf8
    }
}

$errorHandler = {
    if (-not [string]::IsNullOrEmpty($EventArgs.Data)) {
        $errorBuilder.AppendLine($EventArgs.Data) | Out-Null
        $EventArgs.Data | Out-File -FilePath $errorFile -Append -Encoding utf8
    }
}

$process.add_OutputDataReceived($outputHandler)
$process.add_ErrorDataReceived($errorHandler)

try {
    # Ensure log files exist and are empty
    if (Test-Path $outputFile) { Remove-Item $outputFile -Force }
    if (Test-Path $errorFile) { Remove-Item $errorFile -Force }
    New-Item -Path $outputFile -ItemType File -Force | Out-Null
    New-Item -Path $errorFile -ItemType File -Force | Out-Null
    
    $process.Start() | Out-Null
    $process.BeginOutputReadLine()
    $process.BeginErrorReadLine()
    
    Log "Uvicorn process started (PID: $($process.Id))"
    
    # Give the process a moment to start and potentially write errors
    Start-Sleep -Milliseconds 500
    
    # Check immediately if process exited
    if ($process.HasExited) {
        $exitCode = $process.ExitCode
        Log "ERROR: Uvicorn process died immediately (Exit Code: $exitCode)"
        
        # Wait a moment for error handlers to finish writing
        Start-Sleep -Milliseconds 500
        
        # Read error output
        if (Test-Path $errorFile) {
            $errors = Get-Content $errorFile -ErrorAction SilentlyContinue
            if ($errors) {
                Log "Error output from uvicorn:"
                $errors | ForEach-Object { Log "  $_" }
            } else {
                Log "No error output captured (file exists but is empty)"
            }
        } else {
            Log "Error file not created - process may have failed before writing"
        }
        
        # Read standard output
        if (Test-Path $outputFile) {
            $output = Get-Content $outputFile -ErrorAction SilentlyContinue
            if ($output) {
                Log "Standard output from uvicorn:"
                $output | ForEach-Object { Log "  $_" }
            }
        }
        
        # Try to get any buffered error data
        $errorText = $errorBuilder.ToString()
        if ($errorText) {
            Log "Buffered error data: $errorText"
        }
        
        exit 1
    }
    
    # Monitor the process and log output
    $maxWait = 30  # Wait up to 30 seconds for startup
    $waited = 0
    $started = $false
    
    while ($waited -lt $maxWait -and -not $started) {
        Start-Sleep -Seconds 1
        $waited++
        
        # Check if process is still running
        if ($process.HasExited) {
            $exitCode = $process.ExitCode
            Log "ERROR: Uvicorn process died during startup (Exit Code: $exitCode, waited $waited seconds)"
            
            # Wait for error handlers
            Start-Sleep -Milliseconds 500
            
            if (Test-Path $errorFile) {
                $errors = Get-Content $errorFile -Tail 30 -ErrorAction SilentlyContinue
                if ($errors) {
                    Log "Error output:"
                    $errors | ForEach-Object { Log "  $_" }
                }
            }
            if (Test-Path $outputFile) {
                $output = Get-Content $outputFile -Tail 15 -ErrorAction SilentlyContinue
                if ($output) {
                    Log "Standard output:"
                    $output | ForEach-Object { Log "  $_" }
                }
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
            $errors = Get-Content $errorFile -Tail 10 -ErrorAction SilentlyContinue
            if ($errors) {
                Log "Recent errors:"
                $errors | ForEach-Object { Log "  $_" }
            }
        }
    }
    
    # Keep the script running and monitor the process
    while ($true) {
        Start-Sleep -Seconds 10
        
        if ($process.HasExited) {
            $exitCode = $process.ExitCode
            Log "Uvicorn process exited (Exit Code: $exitCode)"
            
            if (Test-Path $errorFile) {
                $errors = Get-Content $errorFile -Tail 20 -ErrorAction SilentlyContinue
                if ($errors) {
                    Log "Last errors:"
                    $errors | ForEach-Object { Log "  $_" }
                }
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
} catch {
    Log "ERROR: Failed to start uvicorn process: $_"
    if (Test-Path $errorFile) {
        $errors = Get-Content $errorFile -Tail 10 -ErrorAction SilentlyContinue
        if ($errors) {
            $errors | ForEach-Object { Log "  $_" }
        }
    }
    exit 1
}
