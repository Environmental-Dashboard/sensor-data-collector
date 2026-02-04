# Setup Windows Scheduled Task for Sensor Data Collector
# This creates a task that runs continuously, even when not logged in

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Sensor Data Collector - Scheduled Task Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runScript = Join-Path $scriptDir "backend\run-continuously.ps1"
$taskName = "SensorDataCollector"

# Check if script exists
if (-not (Test-Path $runScript)) {
    Write-Host "ERROR: Cannot find run-continuously.ps1 at:" -ForegroundColor Red
    Write-Host "  $runScript" -ForegroundColor Yellow
    exit 1
}

Write-Host "Script: $runScript" -ForegroundColor White
Write-Host "Task Name: $taskName" -ForegroundColor White
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  This script requires Administrator privileges!" -ForegroundColor Yellow
    Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To run as Administrator:" -ForegroundColor White
    Write-Host "  1. Right-click PowerShell" -ForegroundColor White
    Write-Host "  2. Select 'Run as Administrator'" -ForegroundColor White
    Write-Host "  3. Run this script again" -ForegroundColor White
    exit 1
}

# Remove existing task if it exists
Write-Host "Removing existing task (if any)..." -ForegroundColor Yellow
try {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "  Removed old task" -ForegroundColor Green
}
catch {
    Write-Host "  No existing task found" -ForegroundColor Green
}

# Create the action (run PowerShell script)
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -NoProfile -File `"$runScript`"" `
    -WorkingDirectory $scriptDir

# Create the trigger (at startup)
$trigger = New-ScheduledTaskTrigger -AtStartup

# Create settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Create principal (run as SYSTEM so it works even when not logged in)
$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Register the task
Write-Host "Creating scheduled task..." -ForegroundColor Yellow
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "Runs Sensor Data Collector backend and tunnel continuously" | Out-Null
    
    Write-Host ""
    Write-Host "✅ SUCCESS!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Scheduled Task Created:" -ForegroundColor White
    Write-Host "  Name: $taskName" -ForegroundColor Cyan
    Write-Host "  Runs: At Windows startup" -ForegroundColor White
    Write-Host "  User: SYSTEM (runs even when not logged in)" -ForegroundColor White
    Write-Host "  Restart: Automatically restarts if it fails" -ForegroundColor White
    Write-Host ""
    Write-Host "The task will:" -ForegroundColor Yellow
    Write-Host "  ✓ Start automatically when Windows boots" -ForegroundColor Green
    Write-Host "  ✓ Run even when you're not logged in" -ForegroundColor Green
    Write-Host "  ✓ Restart backend/tunnel if they crash" -ForegroundColor Green
    Write-Host "  ✓ Monitor and keep services running" -ForegroundColor Green
    Write-Host ""
    Write-Host "To start it now:" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
    Write-Host ""
    Write-Host "To stop it:" -ForegroundColor Yellow
    Write-Host "  Stop-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
    Write-Host ""
    Write-Host "To view status:" -ForegroundColor Yellow
    Write-Host "  Get-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
    Write-Host ""
    Write-Host "To remove it:" -ForegroundColor Yellow
    Write-Host "  Unregister-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
    Write-Host ""
    
    # Ask if user wants to start it now
    $response = Read-Host "Start the task now? (Y/N)"
    if ($response -eq 'Y' -or $response -eq 'y') {
        Start-ScheduledTask -TaskName $taskName
        Write-Host ""
        Write-Host "✅ Task started!" -ForegroundColor Green
        Write-Host "Check logs at: backend\continuous.log" -ForegroundColor White
    }
    
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to create scheduled task" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Yellow
    exit 1
}
